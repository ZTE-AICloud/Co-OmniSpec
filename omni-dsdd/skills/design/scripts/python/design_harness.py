#!/usr/bin/env python3
"""design 阶段 Harness：初始化、分步门禁、run manifest、SDD 状态同步、断点续跑。"""

import argparse
import importlib.util
import json
import re
import shutil
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from design_template_gate import (  # noqa: E402
    load_contract,
    normalize_for_token,
    render_api_contract_skeleton,
    render_design_skeleton,
    render_from_infra_template,
    validate_artifact,
    validate_gate_step,
)

_OMNI_STATE = None  # type: ignore


def _try_load_omnispec(feature_dir: Path) -> None:
    global _OMNI_STATE
    if _OMNI_STATE is not None:
        return
    paths_file = feature_dir / ".runs/paths.json"
    if paths_file.is_file():
        try:
            pr = (_read_json(paths_file).get("plugin_root") or "").strip()
            if pr and Path(pr).is_dir():
                _load_omnispec_state(Path(pr))
                return
        except json.JSONDecodeError:
            pass
    embedded = Path(__file__).resolve().parents[4]
    if (embedded / "scripts" / "python" / "omnispec_state.py").is_file():
        _load_omnispec_state(embedded)


def _load_omnispec_state(plugin_root: Path):
    global _OMNI_STATE
    lib_path = plugin_root / "scripts" / "python" / "omnispec_state.py"
    if not lib_path.is_file():
        raise RuntimeError(f"cannot find omnispec_state.py under plugin root: {lib_path}")
    spec = importlib.util.spec_from_file_location("omnispec_state", lib_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load omnispec_state from {lib_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    _OMNI_STATE = module
    return module


def _require_path(value: str, flag: str) -> Path:
    if not (value or "").strip():
        print(f"ERROR: {flag} is required", file=sys.stderr)
        sys.exit(2)
    path = Path(value).resolve()
    if not path.is_dir():
        print(f"ERROR: {flag} is not a directory: {path}", file=sys.stderr)
        sys.exit(2)
    return path


def _paths_from_feature(feature_dir: Path) -> Dict[str, Any]:
    paths_file = feature_dir / ".runs" / "paths.json"
    if not paths_file.is_file():
        return {}
    try:
        return _read_json(paths_file)
    except json.JSONDecodeError:
        return {}


def _branch_name_from_upstream(feature_dir: Path) -> str:
    data = _paths_from_feature(feature_dir)
    branch_name = (data.get("branch_name") or "").strip()
    if branch_name:
        return branch_name
    env_sh = feature_dir / ".runs" / "env.sh"
    if env_sh.is_file():
        match = re.search(
            r'export\s+BRANCH_NAME="([^"]*)"',
            env_sh.read_text(encoding="utf-8"),
        )
        if match:
            return match.group(1).strip()
    return ""


def _resolve_upstream_context(
    plugin_root: Path,
    working_dir: Path,
    *,
    feature_dir_arg: str = "",
    branch_name_arg: str = "",
) -> Tuple[Path, str, Dict[str, Any]]:
    """Inherit FEATURE_DIR / BRANCH_NAME from specify paths.json or env (not git)."""
    _load_omnispec_state(plugin_root)
    if (feature_dir_arg or "").strip():
        feature_dir = Path(feature_dir_arg).resolve()
    else:
        resolved = _OMNI_STATE.resolve_feature_dir(
            working_dir=working_dir,
            plugin_root=plugin_root,
            use_prerequisites=False,
        )
        if resolved is None:
            print(
                "ERROR: FEATURE_DIR not resolved; run specify/create-branch first",
                file=sys.stderr,
            )
            sys.exit(2)
        feature_dir = resolved

    path_err = _OMNI_STATE.validate_feature_dir_under_changes(working_dir, feature_dir)
    if path_err:
        print("ERROR: {0}".format(path_err), file=sys.stderr)
        sys.exit(2)

    paths_file = feature_dir / ".runs" / "paths.json"
    spec_file = feature_dir / "spec.md"
    if not paths_file.is_file() and not spec_file.is_file():
        print(
            "ERROR: no upstream paths.json or spec.md; run specify first",
            file=sys.stderr,
        )
        sys.exit(2)

    existing = _paths_from_feature(feature_dir)
    branch_name = (branch_name_arg or "").strip() or _branch_name_from_upstream(feature_dir)
    if not branch_name:
        print("ERROR: BRANCH_NAME missing in upstream paths.json/env.sh", file=sys.stderr)
        sys.exit(2)

    return feature_dir, branch_name, existing


def _write_env_from_paths(
    feature_dir: Path,
    paths: Dict[str, Any],
    *,
    enable_e2e: bool,
) -> None:
    e2e_flag = "true" if enable_e2e else "false"
    env_sh = feature_dir / ".runs" / "env.sh"
    lines = [
        "# Merged by skills/design/scripts/python/design_harness.py (extends specify env)",
        'export FEATURE_DIR="{0}"'.format(paths.get("feature_dir") or str(feature_dir)),
        'export FEATURE_SPEC="{0}"'.format(paths.get("spec_file", "")),
        'export IMPL_DESIGN="{0}"'.format(paths.get("design_file", "")),
        'export TASKS="{0}"'.format(paths.get("tasks_file", "")),
        'export BRANCH_NAME="{0}"'.format(paths.get("branch_name", "")),
        'export DOC_DIR="{0}"'.format(paths.get("doc_dir", "")),
        'export DOC_SPECS_DIR="{0}"'.format(paths.get("doc_specs_dir", "")),
        'export DOC_RULES_DIR="{0}"'.format(paths.get("doc_rules_dir", "")),
        'export DOC_NAVIGATIONS_DIR="{0}"'.format(paths.get("doc_navigations_dir", "")),
        'export DOC_ON_DEMAND_DIR="{0}"'.format(paths.get("doc_on_demand_dir", "")),
        'export KNOWLEDGE_DIR="{0}"'.format(paths.get("knowledge_dir", "")),
        'export ENABLE_E2E="{0}"'.format(e2e_flag),
        'export CLAUDE_WORKING_DIR="{0}"'.format(paths.get("working_dir", "")),
        'export CLAUDE_PLUGIN_ROOT="{0}"'.format(paths.get("plugin_root", "")),
        "",
    ]
    env_sh.parent.mkdir(parents=True, exist_ok=True)
    env_sh.write_text("\n".join(lines), encoding="utf-8")


def _resolve_plugin_root(args: argparse.Namespace, feature_dir: Path) -> Path:
    explicit = getattr(args, "plugin_root", None) or ""
    if explicit.strip():
        return _require_path(explicit, "--plugin-root")
    data = _paths_from_feature(feature_dir)
    cached = data.get("plugin_root") or ""
    if cached.strip():
        return _require_path(cached, "paths.json plugin_root")
    print("ERROR: --plugin-root is required (or run init with paths.json)", file=sys.stderr)
    sys.exit(2)


def _resolve_working_dir(args: argparse.Namespace, feature_dir: Path) -> Path:
    explicit = getattr(args, "working_dir", None) or ""
    if explicit.strip():
        return _require_path(explicit, "--working-dir")
    data = _paths_from_feature(feature_dir)
    cached = data.get("working_dir") or data.get("repo_root") or ""
    if cached.strip():
        return _require_path(cached, "paths.json working_dir")
    print("ERROR: --working-dir is required (or run init with paths.json)", file=sys.stderr)
    sys.exit(2)

MIN_BYTES_DEFAULT = 64

ARTIFACTS_REQUIRED = [
    "design.md",
    "research.md",
    "data-model.md",
    "contracts/api-contract.md",
    "quickstart.md",
    ".runs/evaluations/eval-design-summary.json",
    ".runs/evaluations/eval-design-report.md",
    ".runs/metrics/omni-metrics-log.json",
]

ARTIFACTS_E2E = ["e2e-impl-design.md"]

STEP_ARTIFACT = {
    "1": ".runs/paths.json",
    "0": "research.md",
    "3": "design.md",
    "1a": "design.md#功能",
    "1b": "data-model.md",
    "1c": "contracts/api-contract.md",
    "1d": "quickstart.md",
    "9": "design.md#修改点严格检查",
    "8": ".runs/evaluations/eval-design-summary.json",
    "11": ".runs/metrics/omni-metrics-log.json",
    "4": "e2e-impl-design.md",
    "kr": ".runs/internal/knowledge-retrieval.json",
}

RESUME_STEPS = ("1", "0", "kr", "3", "1a", "1b", "1c", "1d", "9", "8", "11")

QUICKSTART_REQUIRED_HEADINGS = ("## 前置条件", "## 验证步骤", "## 期望结果")

RESEARCH_TOKENS = ("Details:", "Rationale:", "Reference:")

# 私域知识检索强约束（与 spec-impact-analyze 的 knowledge_retrieval schema 一致）：
# Step 2.2 在知识源就绪（ready/self_healed）时必须真实派发 knowledge-retrieval-agent，
# 并把派发结论写入 .runs/internal/knowledge-retrieval.json 的 knowledge_retrieval 字段。
_KR_JSON_REL = ".runs/internal/knowledge-retrieval.json"
_KR_CONFIG_NAME = "knowledge.config.yaml"
_KR_CONFIG_TEMPLATE_REL = "skills/knowledge-retrieval/knowledge.config.yaml"
_KR_FIELDS = ("executed", "hits", "config_hit", "vector_built", "graph_built", "mode", "skip_reason")
_KR_VALID_MODES = ("enhance", "baseline")

_TEMPLATE_CONTRACT: Optional[Dict[str, Any]] = None


def _contract() -> Dict[str, Any]:
    global _TEMPLATE_CONTRACT
    if _TEMPLATE_CONTRACT is None:
        _TEMPLATE_CONTRACT = load_contract()
    return _TEMPLATE_CONTRACT


def _template_errors(rel_path: str, path: Path, gate_step: Optional[str] = None) -> List[str]:
    if not path.is_file():
        return []
    step = gate_step if rel_path == "design.md" else None
    return validate_artifact(rel_path, _read_text(path), _contract(), gate_step=step)


def _gate_template_step(gate_step: str, feature_dir: Path) -> List[str]:
    return validate_gate_step(gate_step, feature_dir, _contract())

STUB_RESEARCH = """# Research

> Harness 占位 — 阶段 0 须替换为真实研究结论。

## Details: TBD
## Rationale: TBD
## Reference: TBD
"""

STUB_DATA_MODEL = """# Data Model

> Harness 占位 — design-entity 完成后须替换为真实数据模型。
"""

STUB_API_CONTRACT = """# API Contract

> Harness 占位 — design-interface 完成后须替换为真实接口契约。
"""

STUB_QUICKSTART = """# Quickstart

> Harness 占位 — 阶段 1 完成后须替换为可执行的集成验证路径。

## 前置条件

- TBD（环境、依赖、配置、数据）

## 验证步骤

1. TBD（第一步操作）
2. TBD（第二步操作）

## 期望结果

- TBD（可观测的成功标准）
"""


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _file_ok(path: Path, min_bytes: int) -> Tuple[bool, str]:
    if not path.is_file():
        return False, "missing"
    size = path.stat().st_size
    if size < min_bytes:
        return False, f"too_small ({size} < {min_bytes})"
    return True, f"{size} bytes"


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _load_run(feature_dir: Path) -> Dict[str, Any]:
    run_path = feature_dir / ".runs" / "design-run.json"
    if run_path.is_file():
        return _read_json(run_path)
    return {
        "run_id": str(uuid.uuid4()),
        "stage": "design",
        "started_at": _utc_now(),
        "last_updated": _utc_now(),
        "steps": {},
        "artifacts_required": ARTIFACTS_REQUIRED,
    }


def _save_run(feature_dir: Path, run: Dict[str, Any]) -> None:
    run["last_updated"] = _utc_now()
    _write_json(feature_dir / ".runs" / "design-run.json", run)


def _seed_stub(path: Path, content: str) -> None:
    if not path.is_file() or path.stat().st_size < MIN_BYTES_DEFAULT:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def _seed_design_from_template(
    design_file: Path,
    *,
    branch_name: str,
    spec_file: Path,
    working_dir: Path,
) -> None:
    if design_file.is_file() and design_file.stat().st_size >= MIN_BYTES_DEFAULT:
        return
    spec_link = spec_file.name if spec_file.is_file() else "spec.md"
    try:
        content = render_design_skeleton(
            feature_name=branch_name.replace("-", " ").strip() or "功能",
            branch_name=branch_name or "000-feature",
            spec_link=spec_link,
            working_dir=working_dir,
        )
    except FileNotFoundError:
        return
    design_file.parent.mkdir(parents=True, exist_ok=True)
    design_file.write_text(content, encoding="utf-8")


def _seed_artifact_template(
    path: Path,
    template_name: str,
    *,
    working_dir: Path,
    fallback: str,
) -> None:
    if path.is_file() and path.stat().st_size >= MIN_BYTES_DEFAULT:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.write_text(
            render_from_infra_template(template_name, working_dir=working_dir),
            encoding="utf-8",
        )
    except FileNotFoundError:
        path.write_text(fallback, encoding="utf-8")


def cmd_resolve_context(args: argparse.Namespace) -> int:
    plugin_root = _require_path(args.plugin_root, "--plugin-root")
    working_dir = _require_path(args.working_dir, "--working-dir")
    feature_dir, branch_name, existing = _resolve_upstream_context(
        plugin_root,
        working_dir,
        feature_dir_arg=getattr(args, "feature_dir", "") or "",
        branch_name_arg=getattr(args, "branch_name", "") or "",
    )
    spec_file = _OMNI_STATE.resolve_path_under_base(
        feature_dir, existing.get("spec_file") or args.spec_file, "spec.md"
    )
    design_file = _OMNI_STATE.resolve_path_under_base(
        feature_dir, existing.get("design_file") or args.design_file, "design.md"
    )
    doc_dir = (existing.get("doc_dir") or getattr(args, "doc_dir", "") or "omni-doc").strip()
    payload = {
        "feature_dir": str(feature_dir),
        "branch_name": branch_name,
        "spec_file": str(spec_file),
        "design_file": str(design_file),
        "doc_dir": doc_dir,
        "upstream": "specify",
        "resolved": True,
    }
    if getattr(args, "export_mode", False):
        print('export FEATURE_DIR="{0}"'.format(feature_dir))
        print('export BRANCH_NAME="{0}"'.format(branch_name))
        print('export FEATURE_SPEC="{0}"'.format(spec_file))
        print('export IMPL_DESIGN="{0}"'.format(design_file))
        print('export DOC_DIR="{0}"'.format(doc_dir))
        return 0
    print(json.dumps(payload, ensure_ascii=False))
    return 0


def cmd_init(args: argparse.Namespace) -> int:
    plugin_root = _require_path(args.plugin_root, "--plugin-root")
    working_dir = _require_path(args.working_dir, "--working-dir")

    feature_dir, branch_name, existing = _resolve_upstream_context(
        plugin_root,
        working_dir,
        feature_dir_arg=getattr(args, "feature_dir", "") or "",
        branch_name_arg=getattr(args, "branch_name", "") or "",
    )
    _load_omnispec_state(plugin_root)

    for sub in ("contracts", ".runs/evaluations", ".runs/metrics", ".runs/internal"):
        (feature_dir / sub).mkdir(parents=True, exist_ok=True)

    design_file = _OMNI_STATE.resolve_path_under_base(
        feature_dir, args.design_file or existing.get("design_file"), "design.md"
    )
    spec_file = _OMNI_STATE.resolve_path_under_base(
        feature_dir, args.spec_file or existing.get("spec_file"), "spec.md"
    )

    _seed_design_from_template(
        design_file,
        branch_name=branch_name,
        spec_file=spec_file,
        working_dir=working_dir,
    )
    _seed_stub(feature_dir / "research.md", STUB_RESEARCH)
    _seed_artifact_template(
        feature_dir / "data-model.md",
        "data-model-template.md",
        working_dir=working_dir,
        fallback=STUB_DATA_MODEL,
    )
    api_path = feature_dir / "contracts" / "api-contract.md"
    if not api_path.is_file() or api_path.stat().st_size < MIN_BYTES_DEFAULT:
        api_path.parent.mkdir(parents=True, exist_ok=True)
        api_path.write_text(render_api_contract_skeleton(), encoding="utf-8")
    _seed_artifact_template(
        feature_dir / "quickstart.md",
        "quickstart-template.md",
        working_dir=working_dir,
        fallback=STUB_QUICKSTART,
    )

    wd = str(working_dir)
    tasks_file = _OMNI_STATE.resolve_path_under_base(
        feature_dir, existing.get("tasks_file"), "tasks.md"
    )
    enable_e2e = bool(args.enable_e2e) or bool(existing.get("enable_e2e"))
    doc_dir_arg = (args.doc_dir or existing.get("doc_dir") or "omni-doc").strip()

    paths = dict(existing)
    paths.update(
        {
            "branch_name": branch_name,
            "feature_dir": str(feature_dir),
            "spec_file": str(spec_file),
            "design_file": str(design_file),
            "tasks_file": str(tasks_file),
            "working_dir": paths.get("working_dir") or wd,
            "plugin_root": paths.get("plugin_root") or str(plugin_root),
            "repo_root": paths.get("repo_root") or wd,
            "start_time": args.start_time or paths.get("start_time") or "",
            "enable_e2e": enable_e2e,
            "design_initialized_at": _utc_now(),
        }
    )
    paths.update(_OMNI_STATE.doc_dir_paths(working_dir, doc_dir_arg))
    _write_json(feature_dir / ".runs" / "paths.json", paths)

    _write_env_from_paths(feature_dir, paths, enable_e2e=enable_e2e)

    run = _load_run(feature_dir)
    run["run_id"] = args.run_id or run.get("run_id") or str(uuid.uuid4())
    run["started_at"] = _utc_now()
    if args.enable_e2e:
        run["artifacts_required"] = ARTIFACTS_REQUIRED + ARTIFACTS_E2E
    _save_run(feature_dir, run)

    print(json.dumps({"status": "ok", "paths": str(feature_dir / ".runs/paths.json")}, ensure_ascii=False))
    return 0


def cmd_record(args: argparse.Namespace) -> int:
    feature_dir = Path(args.feature_dir).resolve()
    run = _load_run(feature_dir)
    step = str(args.step)
    run["steps"][step] = {
        "status": args.status,
        "gate_exit": args.gate_exit,
        "artifact": STEP_ARTIFACT.get(step, ""),
        "retries": args.retries,
        "notes": args.notes or "",
        "updated_at": _utc_now(),
    }
    _save_run(feature_dir, run)
    return 0


def _gate_step_1(feature_dir: Path, min_bytes: int) -> List[str]:
    _try_load_omnispec(feature_dir)
    errors: List[str] = []
    for rel in (".runs/paths.json", ".runs/env.sh"):
        ok, msg = _file_ok(feature_dir / rel, 16)
        if not ok:
            errors.append(f"{rel}: {msg}")
    paths_file = feature_dir / ".runs/paths.json"
    if paths_file.is_file():
        try:
            data = _read_json(paths_file)
            wd_raw = (data.get("working_dir") or data.get("repo_root") or "").strip()
            wd = Path(wd_raw) if wd_raw else feature_dir.parent.parent
            if _OMNI_STATE is not None:
                path_err = _OMNI_STATE.validate_feature_dir_under_changes(wd, feature_dir)
                if path_err:
                    errors.append(path_err)
            elif "changes" not in feature_dir.resolve().parts:
                errors.append(
                    "feature_dir must be under <WORKING_DIR>/changes/, got: {0}".format(
                        feature_dir.resolve()
                    )
                )
            if Path(data.get("feature_dir", "")).resolve() != feature_dir.resolve():
                errors.append("paths.json: feature_dir mismatch")
            if not data.get("design_file"):
                errors.append("paths.json: missing design_file")
            abs_keys = (
                "feature_dir",
                "spec_file",
                "design_file",
                "tasks_file",
                "doc_dir",
                "doc_specs_dir",
                "doc_rules_dir",
                "doc_navigations_dir",
                "doc_on_demand_dir",
                "working_dir",
                "plugin_root",
            )
            for key in abs_keys:
                val = (data.get(key) or "").strip()
                if val and not Path(val).is_absolute():
                    errors.append(f"paths.json: {key} must be absolute path")
        except json.JSONDecodeError:
            errors.append("paths.json: invalid JSON")
    return errors


def _kr_plugin_root(feature_dir: Path) -> Optional[Path]:
    """gate 命令无 --plugin-root 时，从 paths.json 解析插件根（用于 config 自愈）。"""
    data = _paths_from_feature(feature_dir)
    pr = (data.get("plugin_root") or "").strip()
    if pr and Path(pr).is_dir():
        return Path(pr)
    pr_env = __import__("os").environ.get("CLAUDE_PLUGIN_ROOT", "").strip()
    if pr_env and Path(pr_env).is_dir():
        return Path(pr_env)
    return None


def _kr_knowledge_dir(feature_dir: Path) -> Optional[Path]:
    """解析 KNOWLEDGE_DIR：paths.json > env > working_dir/omni-doc。"""
    import os

    data = _paths_from_feature(feature_dir)
    kd = (data.get("knowledge_dir") or "").strip()
    if not kd:
        kd = (os.environ.get("KNOWLEDGE_DIR") or "").strip()
    if not kd:
        wd = (data.get("working_dir") or "").strip()
        if wd:
            kd = str(Path(wd) / "omni-doc")
    if not kd:
        return None
    return Path(kd).expanduser().resolve()


def _kr_is_empty_dir(path: Path) -> bool:
    if not path.is_dir():
        return True
    return not any(path.iterdir())


def _kr_self_heal(knowledge_dir: Path, plugin_root: Path) -> Tuple[bool, str]:
    """config 缺失时从插件模板拷贝并把 raw_knowledge_dir 设为 .（对齐 init_omni_infra.sh）。"""
    target = knowledge_dir / _KR_CONFIG_NAME
    if target.is_file():
        return False, "already_exists"
    source = plugin_root / _KR_CONFIG_TEMPLATE_REL
    if not source.is_file():
        return False, f"template_missing:{source}"
    knowledge_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    text = target.read_text(encoding="utf-8")
    lines = []
    saw = False
    for line in text.splitlines():
        if line.startswith("raw_knowledge_dir:"):
            lines.append("raw_knowledge_dir: .")
            saw = True
        else:
            lines.append(line)
    if not saw:
        lines.append("raw_knowledge_dir: .")
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return True, f"copied_from:{source}"


def _kr_check_source(knowledge_dir: Optional[Path], plugin_root: Optional[Path]) -> Dict[str, Any]:
    """机器闸门 + 就地自愈。三态：ready / self_healed / skip。"""
    result: Dict[str, Any] = {
        "status": "skip",
        "knowledge_dir": str(knowledge_dir) if knowledge_dir else "",
        "config_path": "",
        "self_healed": False,
        "skip_reason": "",
    }
    if knowledge_dir is None:
        result["skip_reason"] = "knowledge_dir_unresolved"
        return result
    result["config_path"] = str(knowledge_dir / _KR_CONFIG_NAME)
    if not knowledge_dir.exists() or _kr_is_empty_dir(knowledge_dir):
        result["skip_reason"] = f"dir_missing_or_empty:{knowledge_dir}"
        return result
    if (knowledge_dir / _KR_CONFIG_NAME).is_file():
        result["status"] = "ready"
        return result
    # config 缺失 → 就地自愈
    if plugin_root is None:
        result["skip_reason"] = "config_missing_and_plugin_root_unresolved"
        return result
    healed, note = _kr_self_heal(knowledge_dir, plugin_root)
    if healed:
        result["status"] = "self_healed"
        result["self_healed"] = True
        return result
    result["skip_reason"] = f"self_heal_failed:{note}"
    return result


def _kr_check_payload(payload_path: Path, source: Dict[str, Any]) -> Tuple[List[str], Optional[Dict[str, Any]]]:
    """校验 knowledge-retrieval.json 的 knowledge_retrieval 字段。"""
    errors: List[str] = []
    must_dispatch = source.get("status") in ("ready", "self_healed")
    if not payload_path.is_file():
        if must_dispatch:
            errors.append(f"knowledge-retrieval.json: missing ({payload_path})")
        return errors, None
    try:
        payload = _read_json(payload_path)
    except json.JSONDecodeError:
        errors.append("knowledge-retrieval.json: invalid JSON")
        return errors, None

    kr = payload.get("knowledge_retrieval")
    if kr is None:
        if must_dispatch:
            errors.append(
                "knowledge_retrieval: missing while knowledge source ready "
                "(dispatch knowledge-retrieval-agent and record knowledge_retrieval)"
            )
        return errors, None
    if not isinstance(kr, dict):
        errors.append("knowledge_retrieval: must be an object")
        return errors, None

    executed = kr.get("executed")
    if not isinstance(executed, bool):
        errors.append("knowledge_retrieval.executed: must be bool")
    else:
        if must_dispatch and not executed:
            errors.append(
                "knowledge_retrieval.executed: false while knowledge source ready "
                "(must dispatch knowledge-retrieval-agent)"
            )
        if not executed and not (kr.get("skip_reason") or "").strip():
            errors.append("knowledge_retrieval.skip_reason: required when executed=false")
    if executed is True:
        if not isinstance(kr.get("hits"), int) or kr.get("hits", -1) < 0:
            errors.append("knowledge_retrieval.hits: must be non-negative int")
        for key in ("config_hit", "vector_built", "graph_built"):
            if not isinstance(kr.get(key), bool):
                errors.append(f"knowledge_retrieval.{key}: must be bool")
        if kr.get("mode") not in _KR_VALID_MODES:
            errors.append(f"knowledge_retrieval.mode: must be one of {_KR_VALID_MODES}")
    return errors, kr


def _gate_step_kr(feature_dir: Path, min_bytes: int) -> List[str]:
    """私域知识检索门禁：机器闸门 +愈 + knowledge_retrieval 字段钳制。"""
    del min_bytes  # kr gate 不做字节判定
    errors: List[str] = []
    plugin_root = _kr_plugin_root(feature_dir)
    knowledge_dir = _kr_knowledge_dir(feature_dir)
    source = _kr_check_source(knowledge_dir, plugin_root)
    if source["status"] == "self_heal_failed":
        errors.append(f"knowledge_source: self_heal_failed — {source['skip_reason']}")
    payload_path = feature_dir / _KR_JSON_REL
    payload_errors, _kr = _kr_check_payload(payload_path, source)
    errors.extend(payload_errors)
    return errors


def _gate_step_0(feature_dir: Path, min_bytes: int) -> List[str]:
    errors: List[str] = []
    path = feature_dir / "research.md"
    ok, msg = _file_ok(path, min_bytes)
    if not ok:
        errors.append(f"research.md: {msg}")
        return errors
    text = _read_text(path)
    if "Harness 占位" in text and "TBD" in text:
        errors.append("research.md: still harness placeholder (run stage 0)")
    # token 匹配对加粗/全角宽容，与 design_template_gate 保持一致。
    normalized = normalize_for_token(text)
    for token in RESEARCH_TOKENS:
        if token not in normalized:
            errors.append(f"research.md: missing {token}")
    for msg in _gate_template_step("0", feature_dir):
        errors.append(msg)
    return errors


def _gate_step_3(feature_dir: Path, min_bytes: int) -> List[str]:
    errors: List[str] = []
    path = feature_dir / "design.md"
    ok, msg = _file_ok(path, min_bytes)
    if not ok:
        errors.append(f"design.md: {msg}")
        return errors
    text = _read_text(path)
    for heading in ("## 技术背景", "## 章程检查"):
        if heading not in text:
            errors.append(f"design.md: missing section {heading}")
    for msg in _gate_template_step("3", feature_dir):
        errors.append(msg)
    return errors


def _gate_step_1a(feature_dir: Path, min_bytes: int) -> List[str]:
    errors: List[str] = []
    path = feature_dir / "design.md"
    ok, msg = _file_ok(path, min_bytes)
    if not ok:
        errors.append(f"design.md: {msg}")
        return errors
    text = _read_text(path)
    if "## 功能" not in text:
        errors.append("design.md: missing section ## 功能")
    elif len(re.findall(r"FUNC-\d{3}", text)) < 1:
        errors.append("design.md: no FUNC-xxx id under ## 功能")
    for msg in _gate_template_step("1a", feature_dir):
        errors.append(msg)
    return errors


def _gate_step_1b(feature_dir: Path, min_bytes: int) -> List[str]:
    errors: List[str] = []
    dm = feature_dir / "data-model.md"
    ok, msg = _file_ok(dm, min_bytes)
    if not ok:
        errors.append(f"data-model.md: {msg}")
    else:
        text = _read_text(dm)
        if "Harness 占位" in text:
            errors.append("data-model.md: still harness placeholder (run design-entity)")
    design = feature_dir / "design.md"
    if design.is_file():
        text = _read_text(design)
        if "## 逻辑实体" not in text:
            errors.append("design.md: missing section ## 逻辑实体")
    else:
        errors.append("design.md: missing")
    for msg in _gate_template_step("1b", feature_dir):
        errors.append(msg)
    return errors


def _gate_step_1c(feature_dir: Path, min_bytes: int) -> List[str]:
    errors: List[str] = []
    path = feature_dir / "contracts" / "api-contract.md"
    ok, msg = _file_ok(path, min_bytes)
    if not ok:
        errors.append(f"contracts/api-contract.md: {msg}")
        return errors
    text = _read_text(path)
    if "Harness 占位" in text:
        errors.append("contracts/api-contract.md: still harness placeholder (run design-interface)")
    if not re.search(r"API-\d{3}|IFACE-\d{3}|##\s+对外接口|##\s+内部接口", text, re.IGNORECASE):
        errors.append("contracts/api-contract.md: no API-xxx/IFACE-xxx or interface section detected")
    for msg in _gate_template_step("1c", feature_dir):
        errors.append(msg)
    return errors


def _gate_step_1d(feature_dir: Path, min_bytes: int) -> List[str]:
    errors: List[str] = []
    path = feature_dir / "quickstart.md"
    ok, msg = _file_ok(path, min_bytes)
    if not ok:
        errors.append(f"quickstart.md: {msg}")
        return errors
    text = _read_text(path)
    if "Harness 占位" in text:
        errors.append("quickstart.md: still harness placeholder (write real quickstart)")
    for heading in QUICKSTART_REQUIRED_HEADINGS:
        if heading not in text:
            errors.append(f"quickstart.md: missing section {heading}")
    steps = len(re.findall(r"^\s*\d+\.\s+\S", text, re.MULTILINE))
    if steps < 2:
        errors.append(f"quickstart.md: numbered verification steps {steps} < 2")
    if re.search(r"\bTBD\b", text) and text.count("TBD") >= 3:
        errors.append("quickstart.md: too many TBD placeholders (fill verification path)")
    for msg in _gate_template_step("1d", feature_dir):
        errors.append(msg)
    return errors


def _gate_step_9(feature_dir: Path, min_bytes: int) -> List[str]:
    errors: List[str] = []
    path = feature_dir / "design.md"
    ok, msg = _file_ok(path, min_bytes)
    if not ok:
        errors.append(f"design.md: {msg}")
        return errors
    text = _read_text(path)
    if "## 修改点严格检查" not in text:
        errors.append("design.md: missing section ## 修改点严格检查")
        return errors
    rows = len(re.findall(r"^\|[^|]+\|", text, re.MULTILINE))
    if rows < 3:
        errors.append("design.md: 修改点严格检查 table rows < 3")
    for msg in _gate_template_step("9", feature_dir):
        errors.append(msg)
    return errors


def _gate_step_8(feature_dir: Path, min_bytes: int) -> List[str]:
    errors: List[str] = []
    summary = feature_dir / ".runs/evaluations/eval-design-summary.json"
    ok, msg = _file_ok(summary, min_bytes)
    if not ok:
        errors.append(f"eval-design-summary.json: {msg}")
    else:
        try:
            data = _read_json(summary)
            if "overall_score" not in data and "scores" not in data:
                errors.append("eval-design-summary.json: missing overall_score/scores")
        except json.JSONDecodeError:
            errors.append("eval-design-summary.json: invalid JSON")
    report = feature_dir / ".runs/evaluations/eval-design-report.md"
    ok, msg = _file_ok(report, min_bytes)
    if not ok:
        errors.append(f"eval-design-report.md: {msg}")
    return errors


def _gate_step_11(feature_dir: Path, min_bytes: int) -> List[str]:
    errors: List[str] = []
    path = feature_dir / ".runs/metrics/omni-metrics-log.json"
    if not path.is_file():
        errors.append("omni-metrics-log.json: missing")
        return errors
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        errors.append("omni-metrics-log.json: invalid JSON")
        return errors
    if not isinstance(data, list) or len(data) < 1:
        errors.append("omni-metrics-log.json: expected non-empty JSON array")
    elif path.stat().st_size < min_bytes:
        errors.append("omni-metrics-log.json: too_small")
    return errors


def _gate_step_4(feature_dir: Path, min_bytes: int) -> List[str]:
    errors: List[str] = []
    path = feature_dir / "e2e-impl-design.md"
    ok, msg = _file_ok(path, min_bytes)
    if not ok:
        errors.append(f"e2e-impl-design.md: {msg}")
        return errors
    for msg in _gate_template_step("4", feature_dir):
        errors.append(msg)
    return errors


_gate_step_handlers = {
    "1": _gate_step_1,
    "0": _gate_step_0,
    "kr": _gate_step_kr,
    "3": _gate_step_3,
    "1a": _gate_step_1a,
    "1b": _gate_step_1b,
    "1c": _gate_step_1c,
    "1d": _gate_step_1d,
    "9": _gate_step_9,
    "8": _gate_step_8,
    "11": _gate_step_11,
    "4": _gate_step_4,
}

GATE_STEP_CHOICES = ["1", "0", "kr", "3", "1a", "1b", "1c", "1d", "9", "8", "11", "4", "all"]


def _e2e_enabled(feature_dir: Path, cli_flag: bool) -> bool:
    if cli_flag:
        return True
    paths = feature_dir / ".runs/paths.json"
    if paths.is_file():
        try:
            return bool(_read_json(paths).get("enable_e2e"))
        except json.JSONDecodeError:
            pass
    env = feature_dir / ".runs/env.sh"
    if env.is_file():
        return 'ENABLE_E2E="true"' in env.read_text(encoding="utf-8")
    return False


def _gate_all(feature_dir: Path, min_bytes: int, enable_e2e: bool) -> List[str]:
    errors: List[str] = []
    for step in RESUME_STEPS:
        errors.extend(_gate_step_handlers[step](feature_dir, min_bytes))
    if enable_e2e:
        errors.extend(_gate_step_4(feature_dir, min_bytes))
    return errors


def cmd_gate(args: argparse.Namespace) -> int:
    feature_dir = Path(args.feature_dir).resolve()
    min_bytes = args.min_bytes
    step = args.step
    enable_e2e = _e2e_enabled(feature_dir, getattr(args, "enable_e2e", False))

    if step == "all":
        errors = _gate_all(feature_dir, min_bytes, enable_e2e)
    elif step in _gate_step_handlers:
        errors = _gate_step_handlers[step](feature_dir, min_bytes)
    else:
        print(f"ERROR: unknown step {step}", file=sys.stderr)
        return 2

    result = {
        "feature_dir": str(feature_dir),
        "step": step,
        "gate_exit": 0 if not errors else 1,
        "errors": errors,
        "artifact": STEP_ARTIFACT.get(step, "multiple") if step != "all" else "all",
        "enable_e2e": enable_e2e,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if args.record and step != "all":
        run = _load_run(feature_dir)
        run["steps"][step] = {
            "status": "passed" if not errors else "failed",
            "gate_exit": result["gate_exit"],
            "artifact": STEP_ARTIFACT.get(step, ""),
            "retries": args.retries,
            "notes": "; ".join(errors) if errors else "ok",
            "updated_at": _utc_now(),
        }
        _save_run(feature_dir, run)

    return result["gate_exit"]


def cmd_finalize(args: argparse.Namespace) -> int:
    feature_dir = Path(args.feature_dir).resolve()
    plugin_root = _resolve_plugin_root(args, feature_dir)
    working_dir = _resolve_working_dir(args, feature_dir)
    _load_omnispec_state(plugin_root)
    state = _OMNI_STATE.update_state(
        feature_dir,
        current_stage=args.next_stage or "tasks",
        mark_complete=["design"],
        flow_mode=args.flow_mode or None,
        arguments=args.arguments or None,
    )
    _OMNI_STATE.write_active_feature(working_dir, feature_dir)

    run = _load_run(feature_dir)
    run["finalized_at"] = _utc_now()
    run["omnispec_state"] = str(feature_dir / ".runs/.omnispec-state.json")
    _save_run(feature_dir, run)

    print(
        json.dumps(
            {"status": "ok", "completed_stages": state.get("completed_stages")},
            ensure_ascii=False,
        )
    )
    return 0


def cmd_render_design(args: argparse.Namespace) -> int:
    feature_dir = Path(args.feature_dir).resolve()
    working_dir = _resolve_working_dir(args, feature_dir)
    _load_omnispec_state(_resolve_plugin_root(args, feature_dir))
    design_file = _OMNI_STATE.resolve_path_under_base(
        feature_dir, args.design_file, "design.md"
    )
    spec_file = _OMNI_STATE.resolve_path_under_base(
        feature_dir, args.spec_file, "spec.md"
    )
    branch = (args.branch_name or "").strip() or _branch_name_from_upstream(feature_dir)
    content = render_design_skeleton(
        feature_name=args.feature_name or branch.replace("-", " ") or "功能",
        branch_name=branch or "000-feature",
        spec_link=args.spec_link or (spec_file.name if spec_file.is_file() else "spec.md"),
        working_dir=working_dir,
    )
    design_file.parent.mkdir(parents=True, exist_ok=True)
    design_file.write_text(content, encoding="utf-8")
    print(json.dumps({"status": "ok", "design_file": str(design_file)}, ensure_ascii=False))
    return 0


def cmd_resume(args: argparse.Namespace) -> int:
    feature_dir = Path(args.feature_dir).resolve()
    run = _load_run(feature_dir)
    pending = []
    for step in RESUME_STEPS:
        info = run.get("steps", {}).get(step, {})
        if info.get("status") != "passed" or info.get("gate_exit", 1) != 0:
            pending.append(step)
    if _e2e_enabled(feature_dir, False):
        info = run.get("steps", {}).get("4", {})
        if info.get("status") != "passed" or info.get("gate_exit", 1) != 0:
            pending.append("4")
    print(json.dumps({"pending_steps": pending, "run_id": run.get("run_id")}, ensure_ascii=False))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="design harness")
    sub = parser.add_subparsers(dest="command")

    p_resolve = sub.add_parser(
        "resolve-context", help="继承 specify 的 FEATURE_DIR/BRANCH_NAME（不创建目录）"
    )
    p_resolve.add_argument("--plugin-root", required=True)
    p_resolve.add_argument("--working-dir", required=True)
    p_resolve.add_argument("--feature-dir", default="")
    p_resolve.add_argument("--branch-name", default="")
    p_resolve.add_argument("--spec-file", default="")
    p_resolve.add_argument("--design-file", default="")
    p_resolve.add_argument("--doc-dir", default="")
    p_resolve.add_argument("--export", dest="export_mode", action="store_true")

    p_init = sub.add_parser("init", help="初始化 harness 目录与占位产物")
    p_init.add_argument("--plugin-root", required=True)
    p_init.add_argument("--working-dir", required=True)
    p_init.add_argument("--feature-dir", default="")
    p_init.add_argument("--branch-name", default="")
    p_init.add_argument("--spec-file", default="")
    p_init.add_argument("--design-file", default="")
    p_init.add_argument("--doc-dir", default="omni-doc")
    p_init.add_argument("--repo-root", default="", help=argparse.SUPPRESS)
    p_init.add_argument("--start-time", default="")
    p_init.add_argument("--run-id", default="")
    p_init.add_argument("--enable-e2e", action="store_true")

    p_gate = sub.add_parser("gate", help="分步或全量结构门禁")
    p_gate.add_argument("--feature-dir", required=True)
    p_gate.add_argument("--step", required=True, choices=GATE_STEP_CHOICES)
    p_gate.add_argument("--min-bytes", type=int, default=MIN_BYTES_DEFAULT)
    p_gate.add_argument("--record", action="store_true")
    p_gate.add_argument("--retries", type=int, default=0)
    p_gate.add_argument("--enable-e2e", action="store_true")

    p_rec = sub.add_parser("record", help="手动记录步骤状态")
    p_rec.add_argument("--feature-dir", required=True)
    p_rec.add_argument("--step", required=True)
    p_rec.add_argument("--status", required=True, choices=["passed", "failed", "skipped"])
    p_rec.add_argument("--gate-exit", type=int, required=True)
    p_rec.add_argument("--retries", type=int, default=0)
    p_rec.add_argument("--notes", default="")

    p_fin = sub.add_parser("finalize", help="写入 omnispec-state completed_stages")
    p_fin.add_argument("--feature-dir", required=True)
    p_fin.add_argument("--plugin-root", default="")
    p_fin.add_argument("--working-dir", default="")
    p_fin.add_argument("--flow-mode", default="")
    p_fin.add_argument("--next-stage", default="tasks")
    p_fin.add_argument("--arguments", default="")

    p_res = sub.add_parser("resume", help="查询待重跑步骤")
    p_res.add_argument("--feature-dir", required=True)

    p_render = sub.add_parser("render-design", help="从 design-template.md 渲染 design.md 骨架")
    p_render.add_argument("--feature-dir", required=True)
    p_render.add_argument("--working-dir", default="")
    p_render.add_argument("--design-file", default="")
    p_render.add_argument("--spec-file", default="")
    p_render.add_argument("--branch-name", default="")
    p_render.add_argument("--feature-name", default="")
    p_render.add_argument("--spec-link", default="")

    args = parser.parse_args()
    if not getattr(args, "command", None):
        parser.error("command is required")
    handlers = {
        "resolve-context": cmd_resolve_context,
        "init": cmd_init,
        "gate": cmd_gate,
        "record": cmd_record,
        "finalize": cmd_finalize,
        "resume": cmd_resume,
        "render-design": cmd_render_design,
    }
    return handlers[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
