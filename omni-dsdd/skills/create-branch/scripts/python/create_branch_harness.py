#!/usr/bin/env python3
"""create-branch Harness：稳定分配/复用分支名（尤其三位序号前缀）。"""

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

_PENDING_FILE = "changes/.branch-naming-pending.json"
_BRANCH_NAMING_FILE = ".runs/branch-naming.json"

BUSINESS_PREFIX_RE = re.compile(r"(feature|fix|chore):[^\s/]+", re.IGNORECASE)
NUM_PREFIX_3_RE = re.compile(r"^(\d{3})-")
LEADING_NUM_RE = re.compile(r"^(\d+)")


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _require_working_dir(explicit: str) -> Path:
    if not (explicit or "").strip():
        print("ERROR: --working-dir is required", file=sys.stderr)
        sys.exit(1)
    path = Path(explicit).resolve()
    if not path.is_dir():
        print(f"ERROR: --working-dir is not a directory: {path}", file=sys.stderr)
        sys.exit(1)
    return path


def _clean_core(name: str) -> str:
    lowered = name.lower()
    cleaned = re.sub(r"[^a-z0-9]+", "-", lowered)
    cleaned = re.sub(r"-+", "-", cleaned).strip("-")
    return cleaned


def _fingerprint(description: str, short_core: str) -> str:
    payload = f"{description.strip()}\n{short_core.strip().lower()}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _pending_path(working_dir: Path) -> Path:
    return working_dir / _PENDING_FILE


def _load_pending(working_dir: Path) -> Dict[str, Any]:
    path = _pending_path(working_dir)
    if not path.is_file():
        return {"version": 1, "pending": {}}
    try:
        data = _read_json(path)
    except json.JSONDecodeError:
        return {"version": 1, "pending": {}}
    data.setdefault("pending", {})
    return data


def _save_pending(working_dir: Path, data: Dict[str, Any]) -> None:
    _write_json(_pending_path(working_dir), data)


def _extract_business_prefix(description: str) -> Optional[str]:
    match = BUSINESS_PREFIX_RE.search(description)
    if not match:
        return None
    return match.group(0)


def _collect_numeric_max(working_dir: Path) -> int:
    highest = 0
    changes_dir = working_dir / "changes"
    if changes_dir.is_dir():
        for entry in changes_dir.iterdir():
            if not entry.is_dir() or entry.name.startswith("."):
                continue
            match = LEADING_NUM_RE.match(entry.name)
            if match:
                highest = max(highest, int(match.group(1), 10))

    try:
        proc = subprocess.run(
            ["git", "branch", "--list", "--format=%(refname:short)"],
            cwd=str(working_dir),
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )
        for line in proc.stdout.splitlines():
            branch = line.strip()
            if not branch:
                continue
            match = LEADING_NUM_RE.match(branch)
            if match:
                highest = max(highest, int(match.group(1), 10))
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    return highest


def _next_feature_num(working_dir: Path) -> str:
    return f"{_collect_numeric_max(working_dir) + 1:03d}"


def _compose_business_branch(prefix: str, short_core: str) -> str:
    core = _clean_core(short_core) if short_core else ""
    if not core:
        return prefix
    if core in prefix.lower().replace(":", "-"):
        return prefix
    return f"{prefix}-{core}"


def _compose_sequential_branch(feature_num: str, short_core: str) -> str:
    core = _clean_core(short_core)
    if not core:
        raise ValueError("short_core is required for sequential branch naming")
    return f"{feature_num}-{core}"


def _find_existing_by_fingerprint(working_dir: Path, idem_key: str) -> Optional[Dict[str, Any]]:
    changes = working_dir / "changes"
    if not changes.is_dir() or not idem_key:
        return None
    for entry in sorted(changes.iterdir()):
        if not entry.is_dir() or entry.name.startswith("."):
            continue
        naming = entry / _BRANCH_NAMING_FILE
        if not naming.is_file():
            continue
        try:
            data = _read_json(naming)
        except json.JSONDecodeError:
            continue
        if data.get("description_fingerprint") == idem_key or data.get("idempotency_key") == idem_key:
            out = dict(data)
            out["source"] = "existing_fingerprint"
            out["feature_dir"] = str(entry.resolve())
            out["feature_dir_basename"] = entry.name
            return out
    return None


def _find_existing_by_short_core(working_dir: Path, short_core: str) -> Optional[Dict[str, Any]]:
    core = _clean_core(short_core)
    if not core:
        return None
    changes = working_dir / "changes"
    if not changes.is_dir():
        return None
    for entry in sorted(changes.iterdir(), reverse=True):
        if not entry.is_dir() or entry.name.startswith("."):
            continue
        if entry.name == core or entry.name.endswith("-" + core) or ("-" + core + "-") in ("-" + entry.name + "-"):
            reused = _try_reuse_existing_feature_dir(working_dir, entry.name)
            if reused:
                return reused
    return None


def _try_reuse_existing_feature_dir(working_dir: Path, branch_name: str) -> Optional[Dict[str, Any]]:
    """若 changes/<branch_name> 已存在，禁止再次 allocate 递增编号。"""
    feature_path = working_dir / "changes" / branch_name
    if not feature_path.is_dir():
        return None
    naming_file = feature_path / _BRANCH_NAMING_FILE
    if naming_file.is_file():
        try:
            data = _read_json(naming_file)
            recorded = (data.get("branch_name") or "").strip()
            if recorded and recorded != branch_name:
                return None
            out = dict(data)
            out["source"] = "existing_feature_dir"
            out["feature_dir"] = str(feature_path)
            out["feature_dir_basename"] = feature_path.name
            return out
        except json.JSONDecodeError:
            pass
    result = _parse_existing_branch(branch_name)
    result["source"] = "existing_feature_dir"
    result["feature_dir"] = str(feature_path)
    result["feature_dir_basename"] = feature_path.name
    return result


def _parse_existing_branch(branch_name: str) -> Dict[str, Any]:
    business = _extract_business_prefix(branch_name)
    if business:
        return {
            "naming_kind": "business_prefix",
            "branch_name": branch_name,
            "feature_num": "",
            "feature_dir_basename": branch_name,
            "business_prefix": business,
        }
    match = NUM_PREFIX_3_RE.match(branch_name)
    if match:
        return {
            "naming_kind": "sequential",
            "branch_name": branch_name,
            "feature_num": match.group(1),
            "feature_dir_basename": branch_name,
            "business_prefix": None,
        }
    return {
        "naming_kind": "explicit",
        "branch_name": branch_name,
        "feature_num": "",
        "feature_dir_basename": branch_name,
        "business_prefix": None,
    }


def cmd_allocate(args: argparse.Namespace) -> int:
    working_dir = _require_working_dir(args.working_dir)
    description = (args.description or "").strip()
    short_core = (args.short_core or "").strip()
    explicit_branch = (args.branch_name or "").strip()

    if explicit_branch:
        result = _parse_existing_branch(explicit_branch)
        result["source"] = "explicit"
        result["idempotency_key"] = args.idempotency_key or ""
        print(json.dumps(result, ensure_ascii=False))
        return 0

    if not description and not short_core:
        print("ERROR: --description or --short-core required when --branch-name is omitted", file=sys.stderr)
        return 1

    idem_key = args.idempotency_key or _fingerprint(description, short_core)
    pending_data = _load_pending(working_dir)
    existing = pending_data["pending"].get(idem_key)
    if existing:
        existing = dict(existing)
        existing["source"] = "pending_reuse"
        existing["idempotency_key"] = idem_key
        print(json.dumps(existing, ensure_ascii=False))
        return 0

    by_fp = _find_existing_by_fingerprint(working_dir, idem_key)
    if by_fp:
        by_fp["idempotency_key"] = idem_key
        print(json.dumps(by_fp, ensure_ascii=False))
        return 0

    if short_core:
        by_core = _find_existing_by_short_core(working_dir, short_core)
        if by_core:
            by_core["idempotency_key"] = idem_key
            print(json.dumps(by_core, ensure_ascii=False))
            return 0

    business = _extract_business_prefix(description)
    if business:
        branch_name = _compose_business_branch(business, short_core)
        result = {
            "naming_kind": "business_prefix",
            "branch_name": branch_name,
            "feature_num": "",
            "feature_dir_basename": branch_name,
            "business_prefix": business,
            "short_core": _clean_core(short_core) if short_core else "",
            "source": "allocated",
            "idempotency_key": idem_key,
            "allocated_at": _utc_now(),
        }
        reused = _try_reuse_existing_feature_dir(working_dir, branch_name)
        if reused:
            reused["idempotency_key"] = idem_key
            print(json.dumps(reused, ensure_ascii=False))
            return 0
    else:
        if not short_core:
            print(
                "ERROR: --short-core is required when description has no feature:/fix:/chore: prefix",
                file=sys.stderr,
            )
            return 1
        feature_num = _next_feature_num(working_dir)
        branch_name = _compose_sequential_branch(feature_num, short_core)
        result = {
            "naming_kind": "sequential",
            "branch_name": branch_name,
            "feature_num": feature_num,
            "feature_dir_basename": branch_name,
            "business_prefix": None,
            "short_core": _clean_core(short_core),
            "source": "allocated",
            "idempotency_key": idem_key,
            "allocated_at": _utc_now(),
        }
        reused = _try_reuse_existing_feature_dir(working_dir, branch_name)
        if reused:
            reused["idempotency_key"] = idem_key
            print(json.dumps(reused, ensure_ascii=False))
            return 0

    pending_data["pending"][idem_key] = {k: v for k, v in result.items() if k != "source"}
    pending_data["pending"][idem_key]["description_fingerprint"] = idem_key
    _save_pending(working_dir, pending_data)
    print(json.dumps(result, ensure_ascii=False))
    return 0


def _validate_feature_dir_under_changes(
    feature_dir: Path, working_dir: Optional[Path]
) -> Optional[str]:
    p = feature_dir.resolve()
    if not p.is_dir():
        return "feature_dir is not a directory: {0}".format(p)
    if p.parent.name != "changes":
        return "feature_dir must be <WORKING_DIR>/changes/<name>, got: {0}".format(p)
    if working_dir is not None:
        try:
            p.relative_to(working_dir.resolve() / "changes")
        except ValueError:
            return "feature_dir must be under {0}/changes/, got: {1}".format(
                working_dir.resolve(), p
            )
    return None


def cmd_record(args: argparse.Namespace) -> int:
    working_dir = _require_working_dir(args.working_dir)
    feature_dir = Path(args.feature_dir).resolve()
    path_err = _validate_feature_dir_under_changes(feature_dir, working_dir)
    if path_err:
        print("ERROR: {0}".format(path_err), file=sys.stderr)
        return 1
    branch_name = (args.branch_name or "").strip()
    if not branch_name:
        print("ERROR: --branch-name is required for record", file=sys.stderr)
        return 1

    parsed = _parse_existing_branch(branch_name)
    if args.feature_num:
        parsed["feature_num"] = args.feature_num
    if args.short_core:
        parsed["short_core"] = _clean_core(args.short_core)

    idem_key = args.idempotency_key or ""
    record = {
        **parsed,
        "feature_dir": str(feature_dir),
        "recorded_at": _utc_now(),
        "idempotency_key": idem_key,
        "description_fingerprint": idem_key,
    }
    _write_json(feature_dir / _BRANCH_NAMING_FILE, record)

    if idem_key:
        pending_data = _load_pending(working_dir)
        pending_data["pending"].pop(idem_key, None)
        _save_pending(working_dir, pending_data)

    print(json.dumps({"status": "ok", "branch_naming": str(feature_dir / _BRANCH_NAMING_FILE)}, ensure_ascii=False))
    return 0


def cmd_resolve(args: argparse.Namespace) -> int:
    feature_dir = Path(args.feature_dir).resolve()
    naming_file = feature_dir / _BRANCH_NAMING_FILE
    if naming_file.is_file():
        data = _read_json(naming_file)
        data["source"] = "branch-naming.json"
        print(json.dumps(data, ensure_ascii=False))
        return 0

    paths_file = feature_dir / ".runs" / "paths.json"
    if paths_file.is_file():
        try:
            paths = _read_json(paths_file)
            branch_name = (paths.get("branch_name") or "").strip()
            if branch_name:
                result = _parse_existing_branch(branch_name)
                result["source"] = "paths.json"
                result["feature_dir"] = str(feature_dir)
                print(json.dumps(result, ensure_ascii=False))
                return 0
        except json.JSONDecodeError:
            pass

    basename = feature_dir.name
    if basename and basename != "changes":
        result = _parse_existing_branch(basename)
        result["source"] = "feature_dir_basename"
        result["feature_dir"] = str(feature_dir)
        print(json.dumps(result, ensure_ascii=False))
        return 0

    print("ERROR: cannot resolve branch naming for feature directory", file=sys.stderr)
    return 1


def cmd_gate(args: argparse.Namespace) -> int:
    feature_dir = Path(args.feature_dir).resolve()
    branch_name = (args.branch_name or "").strip()
    errors: List[str] = []

    wd = (
        feature_dir.parent.parent
        if feature_dir.resolve().parent.name == "changes"
        else None
    )
    path_err = _validate_feature_dir_under_changes(feature_dir, wd)
    if path_err:
        errors.append(path_err)

    naming_file = feature_dir / _BRANCH_NAMING_FILE
    if not naming_file.is_file():
        errors.append(f"{_BRANCH_NAMING_FILE}: missing")
    else:
        try:
            data = _read_json(naming_file)
            recorded = (data.get("branch_name") or "").strip()
            if branch_name and recorded != branch_name:
                errors.append(f"branch_name mismatch: record={recorded} arg={branch_name}")
            if data.get("naming_kind") == "sequential" and not data.get("feature_num"):
                errors.append("sequential naming requires feature_num in branch-naming.json")
        except json.JSONDecodeError:
            errors.append(f"{_BRANCH_NAMING_FILE}: invalid JSON")

    if errors:
        print(json.dumps({"status": "fail", "errors": errors}, ensure_ascii=False))
        return 1
    print(json.dumps({"status": "ok"}, ensure_ascii=False))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="create-branch harness")
    parser.add_argument(
        "--working-dir",
        default="",
        help="工作区根目录（allocate/record 必填；由调用方传入，禁止脚本内推断）",
    )
    sub = parser.add_subparsers(dest="command")

    p_alloc = sub.add_parser("allocate", help="分配或复用待创建分支名（含稳定编号）")
    p_alloc.add_argument("--description", default="")
    p_alloc.add_argument("--short-core", default="", help="英文短核心名，如 thread-table-aging")
    p_alloc.add_argument("--branch-name", default="", help="显式分支名（不重新分配编号）")
    p_alloc.add_argument("--idempotency-key", default="")

    p_record = sub.add_parser("record", help="创建成功后写入 branch-naming 真值")
    p_record.add_argument("--feature-dir", required=True)
    p_record.add_argument("--branch-name", required=True)
    p_record.add_argument("--feature-num", default="")
    p_record.add_argument("--short-core", default="")
    p_record.add_argument("--idempotency-key", default="")

    p_resolve = sub.add_parser("resolve", help="从特性目录解析已持久化的分支名")
    p_resolve.add_argument("--feature-dir", required=True)

    p_gate = sub.add_parser("gate", help="校验 branch-naming 真值")
    p_gate.add_argument("--feature-dir", required=True)
    p_gate.add_argument("--branch-name", default="")

    args = parser.parse_args()
    if not args.command:
        parser.error("the following arguments are required: {allocate,record,resolve,gate}")
    handlers = {
        "allocate": cmd_allocate,
        "record": cmd_record,
        "resolve": cmd_resolve,
        "gate": cmd_gate,
    }
    return handlers[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
