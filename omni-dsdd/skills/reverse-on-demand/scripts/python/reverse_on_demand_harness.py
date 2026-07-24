#!/usr/bin/env python3
"""reverse-on-demand Harness：阶段2波及检索四项强制约束的门禁校验。"""

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone
from fnmatch import fnmatch
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

# 仓库顶层默认排除（不参与"必须扫描"计数，但须在 coverage 中声明）
DEFAULT_TOP_LEVEL_EXCLUDES = frozenset(
    {
        ".git",
        "node_modules",
        "vendor",
        "__pycache__",
        ".venv",
        "venv",
        "dist",
        "build",
        "target",
        ".idea",
        ".cursor",
        ".runs",
        # harness 中间产物目录（JSON 非源码语言文件）
        "on-demand",
    }
)

# 未达到最小深度时禁止使用的停止原因
PREMATURE_STOP_REASONS = frozenset(
    {
        "depth_limit",
        "manual_stop",
        "token_budget",
        "agent_stop",
        "shallow_cutoff",
        "budget_stop",
    }
)

ALLOWED_EARLY_STOP_REASONS = frozenset(
    {
        "leaf_no_callees",
        "max_depth_cap_with_evidence",
        "external_boundary",
        "non_code_boundary",
    }
)

CONFIG_SUFFIXES = frozenset(
    {
        ".yaml",
        ".yml",
        ".json",
        ".toml",
        ".properties",
        ".ini",
        ".env",
        ".conf",
        ".config",
        ".xml",
    }
)

# 扩展名 → 代码语言映射（用于多语言覆盖自动发现）
# 仅收录"应被当作代码语言分析"的扩展名；未知扩展名不在此表 = 不强制声明，避免误报
CODE_LANGUAGE_MAP: Dict[str, str] = {
    ".py": "Python",
    ".java": "Java",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".kt": "Kotlin",
    ".kt": "Kotlin",
    ".scala": "Scala",
    ".go": "Go",
    ".rs": "Rust",
    ".c": "C",
    ".h": "C",
    ".cpp": "C++",
    ".cc": "C++",
    ".cxx": "C++",
    ".hpp": "C++",
    ".cs": "C#",
    ".rb": "Ruby",
    ".php": "PHP",
    ".swift": "Swift",
    ".m": "Objective-C",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".lua": "Lua",
    ".sh": "Shell",
    ".bash": "Shell",
    ".zsh": "Shell",
    ".sql": "SQL",
    ".proto": "Protocol Buffers",
    ".thrift": "Thrift",
    ".groovy": "Groovy",
    ".pl": "Perl",
    ".r": "R",
    ".dart": "Dart",
    ".el": "Emacs Lisp",
    ".clj": "Clojure",
    ".erl": "Erlang",
    ".ex": "Elixir",
    ".exs": "Elixir",
    ".vim": "Vim Script",
    ".ps1": "PowerShell",
}

GATE_STEPS = ("stage2", "all")


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _repo_top_level_dirs(repo_root: Path) -> Set[str]:
    if not repo_root.is_dir():
        return set()
    return {
        p.name
        for p in repo_root.iterdir()
        if p.is_dir() and p.name not in DEFAULT_TOP_LEVEL_EXCLUDES
    }


def _path_excluded(rel_path: str, exclude_globs: List[str]) -> bool:
    """判断相对路径是否命中排除 glob（路径级或 basename 级）。"""
    if not exclude_globs:
        return False
    name = Path(rel_path).name
    for patt in exclude_globs:
        if fnmatch(rel_path, patt) or fnmatch(name, patt):
            return True
    return False


def _repo_code_languages(
    repo_root: Path,
    scope_paths: Optional[List[str]] = None,
    exclude_globs: Optional[List[str]] = None,
) -> Set[str]:
    """自动发现仓库实际出现的代码语言集合（基于扩展名白名单）。

    优先用 rg（快）；rg 不可用时回退到 pathlib 递归。
    受 DEFAULT_TOP_LEVEL_EXCLUDES 与 exclude_globs 共同约束；
    scoped 模式下仅扫描 scope_paths 范围。
    """
    exclude_globs = exclude_globs or []
    scope_paths = scope_paths or []
    found: Set[str] = set()

    search_dirs: List[Path] = []
    if scope_paths:
        for sp in scope_paths:
            p = Path(sp)
            if p.is_dir():
                search_dirs.append(p)
    else:
        if repo_root.is_dir():
            for entry in repo_root.iterdir():
                if entry.is_dir() and entry.name not in DEFAULT_TOP_LEVEL_EXCLUDES:
                    search_dirs.append(entry)
            # 顶层散落文件也纳入（如根目录脚本）
            search_dirs.append(repo_root)

    # 收集扩展名：rg 优先
    exts: Set[str] = set()
    used_rg = False
    import shutil

    rg = shutil.which("rg")
    if rg:
        for d in search_dirs:
            if not d.exists():
                continue
            import subprocess

            try:
                proc = subprocess.run(
                    [rg, "--files", "--no-ignore-vcs", "-g", "!**/.git/**"],
                    cwd=str(repo_root),
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
            except Exception:
                proc = None
            if proc and proc.returncode == 0:
                used_rg = True
                for line in proc.stdout.splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    rel = line
                    # scoped：仅保留 scope 内
                    if scope_paths:
                        try:
                            abs_p = str((repo_root / line).resolve())
                            if not any(
                                abs_p.startswith(str(Path(sp).resolve()))
                                for sp in scope_paths
                            ):
                                continue
                        except Exception:
                            continue
                    # 顶层排除目录
                    top = rel.split("/", 1)[0]
                    if top in DEFAULT_TOP_LEVEL_EXCLUDES:
                        continue
                    if _path_excluded(rel, exclude_globs):
                        continue
                    suffix = Path(rel).suffix.lower()
                    if suffix:
                        exts.add(suffix)
                break  # rg 一次列出全仓，避免重复

    if not used_rg:
        # 回退：pathlib 递归
        for d in search_dirs:
            if not d.exists():
                continue
            for p in d.rglob("*"):
                if p.is_dir():
                    continue
                try:
                    rel = str(p.relative_to(repo_root))
                except ValueError:
                    rel = str(p)
                top = rel.split("/", 1)[0]
                if top in DEFAULT_TOP_LEVEL_EXCLUDES:
                    continue
                if _path_excluded(rel, exclude_globs):
                    continue
                suffix = p.suffix.lower()
                if suffix:
                    exts.add(suffix)

    for ext in exts:
        lang = CODE_LANGUAGE_MAP.get(ext)
        if lang:
            found.add(lang)
    return found


def _parse_csv_arg(raw: str) -> List[str]:
    if not raw:
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


def _normalize_scope_paths(raw_paths: List[str], repo_root: Path) -> List[str]:
    normalized: List[str] = []
    seen: Set[str] = set()
    for raw in raw_paths:
        p = Path(raw)
        if not p.is_absolute():
            p = (repo_root / p).resolve()
        else:
            p = p.resolve()
        try:
            p.relative_to(repo_root.resolve())
        except ValueError:
            # 作用域路径必须在仓库内，越界路径在 gate 阶段报错
            normalized.append(str(p))
            continue
        key = str(p)
        if key not in seen:
            normalized.append(key)
            seen.add(key)
    return normalized


def _skeleton_search_coverage(
    repo_root: str, scope_paths: Optional[List[str]] = None, exclude_globs: Optional[List[str]] = None
) -> Dict[str, Any]:
    scoped = bool(scope_paths)
    scope_paths = scope_paths or []
    exclude_globs = exclude_globs or []
    return {
        "schema_version": "1",
        "repo_root": repo_root,
        "scan_mode": "scoped" if scoped else "full_repo",
        "focused_dirs_only": scoped,
        "scope": {
            "include_paths": scope_paths,
            "exclude_globs": exclude_globs,
        },
        "full_repo_scan": {
            "tool": "rg",
            "search_root": repo_root,
            "exclude_globs": [
                ".git/**",
                "node_modules/**",
                "vendor/**",
                "**/__pycache__/**",
            ] + exclude_globs,
            "keywords_used": [],
            "top_level_entries_scanned": [],
            "subset_only_dirs": [],
        },
        "scoped_scan": {
            "tool": "rg",
            "search_root": repo_root,
            "include_paths": scope_paths,
            "exclude_globs": exclude_globs,
            "keywords_used": [],
            "covered_paths": [],
        },
        "narrow_scan_detected": False,
        "languages": [],
        "file_type_stats": [],
        "notes": "REPLACE: 根据 scope 选择 full_repo/scoped 检索，并记录覆盖证明；languages 须枚举仓库全部语言（含附属语言），每项含 name/role(primary|auxiliary)/coverage_status(covered|degraded)/analysis_method；degraded 须含 degraded_rationale；auxiliary 须含 impact_status(hit|no_hit)，no_hit 须含 no_impact_rationale；file_type_stats 须含全仓文件后缀统计（extension/category/file_count/percentage/associated_language），代码类后缀关联 languages 中声明的语言；gate 将自动扫盘校验漏报并对波及清单做语言命中校验",
    }


def _skeleton_call_trace() -> Dict[str, Any]:
    return {
        "schema_version": "1",
        "min_required_depth": 8,
        "max_depth_cap": 32,
        "traces": [],
        "premature_stop_count": 0,
        "notes": "REPLACE: 每条入口根符号一条 trace；禁止浅层自动停止",
    }


def _skeleton_static_asset_scan() -> Dict[str, Any]:
    return {
        "schema_version": "1",
        "config_files": [],
        "other_static_assets": [],
        "notes": "REPLACE: 每个配置文件必须 parse_status=parsed 且含 extracted_keys",
    }


def cmd_init(args: argparse.Namespace) -> int:
    working_dir = Path(args.working_dir).resolve()
    if not working_dir.is_dir():
        print(json.dumps({"errors": [f"WORKING_DIR 不存在: {working_dir}"]}))
        return 1

    feature_dir = Path(args.feature_dir).resolve()
    on_demand = feature_dir / "on-demand"
    runs = feature_dir / ".runs"
    runs.mkdir(parents=True, exist_ok=True)
    on_demand.mkdir(parents=True, exist_ok=True)

    repo_root_path = Path(args.repo_root).resolve() if args.repo_root else working_dir
    repo_root = str(repo_root_path)
    scope_paths = _normalize_scope_paths(_parse_csv_arg(args.scope_paths), repo_root_path)
    exclude_globs = _parse_csv_arg(args.exclude_globs)

    for name, skeleton in (
        ("stage2-search-coverage.json", _skeleton_search_coverage(repo_root, scope_paths, exclude_globs)),
        ("stage2-call-trace.json", _skeleton_call_trace()),
        ("stage2-static-asset-scan.json", _skeleton_static_asset_scan()),
    ):
        path = on_demand / name
        if not path.is_file():
            _write_json(path, skeleton)

    run_path = runs / "reverse-on-demand-run.json"
    if not run_path.is_file():
        _write_json(
            run_path,
            {
                "run_id": str(uuid.uuid4()),
                "created_at": _utc_now(),
                "gates": {},
            },
        )

    paths_path = runs / "paths.json"
    if not paths_path.is_file():
        _write_json(
            paths_path,
            {
                "working_dir": str(working_dir),
                "feature_dir": str(feature_dir),
                "repo_root": repo_root,
                "on_demand_dir": str(on_demand),
                "scope_paths": scope_paths,
                "exclude_globs": exclude_globs,
            },
        )

    print(json.dumps({"feature_dir": str(feature_dir), "initialized": True}, ensure_ascii=False))
    return 0


def _gate_full_repo_search(
    coverage: Dict[str, Any], repo_root: Path, errors: List[str]
) -> None:
    if coverage.get("schema_version") != "1":
        errors.append("stage2-search-coverage.json: schema_version 必须为 1")

    if coverage.get("scan_mode") != "full_repo":
        errors.append(
            "stage2-search-coverage.json: scan_mode 必须为 full_repo（禁止仅查重点目录）"
        )

    if coverage.get("focused_dirs_only") is True:
        errors.append(
            "stage2-search-coverage.json: focused_dirs_only=true 违规（必须全仓库检索）"
        )

    if coverage.get("narrow_scan_detected") is True:
        errors.append(
            "stage2-search-coverage.json: narrow_scan_detected=true（检测到收窄检索）"
        )

    full = coverage.get("full_repo_scan")
    if not isinstance(full, dict):
        errors.append("stage2-search-coverage.json: 缺少 full_repo_scan 对象")
        return

    search_root = full.get("search_root", "")
    if not search_root:
        errors.append("stage2-search-coverage.json: full_repo_scan.search_root 为空")
    else:
        try:
            if Path(search_root).resolve() != repo_root.resolve():
                errors.append(
                    "stage2-search-coverage.json: search_root 必须等于 REPO_ROOT 绝对路径"
                )
        except OSError:
            errors.append("stage2-search-coverage.json: search_root 路径无效")

    keywords = full.get("keywords_used")
    if not isinstance(keywords, list) or len(keywords) < 1:
        errors.append(
            "stage2-search-coverage.json: keywords_used 须为非空数组（记录实际检索词）"
        )

    tool = full.get("tool")
    if not tool:
        errors.append("stage2-search-coverage.json: full_repo_scan.tool 未记录（如 rg）")

    scanned = full.get("top_level_entries_scanned")
    if not isinstance(scanned, list):
        errors.append(
            "stage2-search-coverage.json: top_level_entries_scanned 须为数组"
        )
        return

    expected = _repo_top_level_dirs(repo_root)
    scanned_set = {str(x) for x in scanned}
    missing = expected - scanned_set
    if missing:
        errors.append(
            "stage2-search-coverage.json: 顶层目录未全覆盖，缺失: "
            + ", ".join(sorted(missing))
        )

    subset = full.get("subset_only_dirs")
    if isinstance(subset, list) and len(subset) > 0:
        for item in subset:
            if not isinstance(item, dict):
                errors.append("stage2-search-coverage.json: subset_only_dirs 项格式错误")
                continue
            rationale = (item.get("exclusion_rationale") or "").strip()
            if not rationale:
                errors.append(
                    f"stage2-search-coverage.json: subset_only_dirs[{item.get('dir')}] "
                    "缺少 exclusion_rationale"
                )

    focused = coverage.get("focused_dirs") or coverage.get("priority_dirs_only")
    if isinstance(focused, list) and len(focused) > 0 and len(scanned_set) < max(
        3, len(expected) // 2
    ):
        errors.append(
            "stage2-search-coverage.json: 疑似仅检索重点目录（focused_dirs 有值但顶层覆盖不足）"
        )


def _gate_scoped_search(
    coverage: Dict[str, Any], repo_root: Path, scope_paths: List[str], exclude_globs: List[str], errors: List[str]
) -> None:
    if coverage.get("schema_version") != "1":
        errors.append("stage2-search-coverage.json: schema_version 必须为 1")
    if coverage.get("scan_mode") != "scoped":
        errors.append("stage2-search-coverage.json: 启用 scope 后 scan_mode 必须为 scoped")

    scope_obj = coverage.get("scope")
    if not isinstance(scope_obj, dict):
        errors.append("stage2-search-coverage.json: 启用 scope 后必须包含 scope 对象")
        return

    recorded_paths = scope_obj.get("include_paths")
    if not isinstance(recorded_paths, list) or len(recorded_paths) == 0:
        errors.append("stage2-search-coverage.json: scope.include_paths 必须为非空数组")
    else:
        recorded_norm = sorted(str(Path(p).resolve()) for p in recorded_paths)
        expected_norm = sorted(str(Path(p).resolve()) for p in scope_paths)
        if recorded_norm != expected_norm:
            errors.append("stage2-search-coverage.json: scope.include_paths 与输入参数不一致")
        for p in recorded_norm:
            try:
                Path(p).resolve().relative_to(repo_root.resolve())
            except ValueError:
                errors.append(f"stage2-search-coverage.json: scope.include_paths 存在越界路径: {p}")

    recorded_excludes = scope_obj.get("exclude_globs")
    if not isinstance(recorded_excludes, list):
        errors.append("stage2-search-coverage.json: scope.exclude_globs 必须为数组")
    else:
        if sorted(str(x) for x in recorded_excludes) != sorted(exclude_globs):
            errors.append("stage2-search-coverage.json: scope.exclude_globs 与输入参数不一致")

    scoped_scan = coverage.get("scoped_scan")
    if not isinstance(scoped_scan, dict):
        errors.append("stage2-search-coverage.json: 启用 scope 后缺少 scoped_scan 对象")
        return

    keywords = scoped_scan.get("keywords_used")
    if not isinstance(keywords, list) or len(keywords) < 1:
        errors.append("stage2-search-coverage.json: scoped_scan.keywords_used 须为非空数组")

    covered_paths = scoped_scan.get("covered_paths")
    if not isinstance(covered_paths, list):
        errors.append("stage2-search-coverage.json: scoped_scan.covered_paths 须为数组")
    elif scope_paths:
        covered_norm = {str(Path(p).resolve()) for p in covered_paths}
        for expected in scope_paths:
            if str(Path(expected).resolve()) not in covered_norm:
                errors.append(f"stage2-search-coverage.json: scoped_scan.covered_paths 缺少 {expected}")

    for item in covered_paths or []:
        text = str(item)
        for patt in exclude_globs:
            if fnmatch(text, patt) or fnmatch(Path(text).name, patt):
                errors.append(f"stage2-search-coverage.json: covered_paths 命中排除模式 {patt}: {text}")
                break


def _collect_trace_roots(feature_dir: Path) -> List[str]:
    roots: List[str] = []
    candidates = feature_dir / "on-demand" / "stage2-impact-candidates.json"
    if not candidates.is_file():
        return roots
    try:
        data = _read_json(candidates)
    except (json.JSONDecodeError, OSError):
        return roots
    items = data.get("functions") or data.get("items") or data
    if isinstance(items, dict):
        items = list(items.values())
    if not isinstance(items, list):
        return roots
    for item in items:
        if not isinstance(item, dict):
            continue
        sym = item.get("code_symbol") or item.get("entry_symbol")
        clues = item.get("entry_clues")
        if sym:
            roots.append(str(sym))
        elif isinstance(clues, dict) and clues.get("symbol"):
            roots.append(str(clues["symbol"]))
        elif isinstance(clues, str) and clues.strip():
            roots.append(clues.strip())
    return roots


def _gate_call_chain_depth(
    trace_doc: Dict[str, Any], feature_dir: Path, errors: List[str]
) -> None:
    if trace_doc.get("schema_version") != "1":
        errors.append("stage2-call-trace.json: schema_version 必须为 1")

    min_depth = int(trace_doc.get("min_required_depth", 8))
    max_cap = int(trace_doc.get("max_depth_cap", 32))
    if min_depth < 1:
        errors.append("stage2-call-trace.json: min_required_depth 无效")
    if max_cap < min_depth:
        errors.append(
            "stage2-call-trace.json: max_depth_cap 必须 >= min_required_depth"
        )

    traces = trace_doc.get("traces")
    if not isinstance(traces, list) or len(traces) == 0:
        errors.append("stage2-call-trace.json: traces 须为非空数组")
        return

    required_roots = _collect_trace_roots(feature_dir)
    seen_roots: Set[str] = set()
    premature = 0

    for idx, tr in enumerate(traces):
        if not isinstance(tr, dict):
            errors.append(f"stage2-call-trace.json: traces[{idx}] 非对象")
            continue
        root = tr.get("root_symbol") or tr.get("root_id") or ""
        if root:
            seen_roots.add(str(root))
        depth = int(tr.get("max_depth_achieved", 0))
        reason = str(tr.get("stopped_reason", "")).strip()
        leaf = (tr.get("leaf_evidence") or "").strip()
        premature_flag = tr.get("premature_stop", False)

        if premature_flag is True:
            premature += 1

        if reason in PREMATURE_STOP_REASONS:
            if depth < min_depth and not leaf:
                errors.append(
                    f"stage2-call-trace.json: trace[{root or idx}] 在深度 {depth} "
                    f"以 {reason} 停止，未达 min_required_depth={min_depth} 且无 leaf_evidence"
                )
                premature += 1
        elif reason and reason not in ALLOWED_EARLY_STOP_REASONS:
            if depth < min_depth and not leaf:
                errors.append(
                    f"stage2-call-trace.json: trace[{root or idx}] stopped_reason="
                    f"{reason!r} 未在允许列表且深度不足"
                )

    doc_premature = int(trace_doc.get("premature_stop_count", 0))
    if premature > 0 and doc_premature < premature:
        errors.append(
            "stage2-call-trace.json: premature_stop_count 低于实际检出违规数"
        )

    if required_roots:
        missing_roots = set(required_roots) - seen_roots
        if missing_roots and len(traces) < len(required_roots):
            errors.append(
                "stage2-call-trace.json: 缺少入口 trace: "
                + ", ".join(sorted(missing_roots)[:10])
            )


def _iter_config_entries(scan: Dict[str, Any]) -> List[Dict[str, Any]]:
    entries: List[Dict[str, Any]] = []
    for key in ("config_files", "parsed_configs", "assets"):
        block = scan.get(key)
        if isinstance(block, list):
            for item in block:
                if isinstance(item, dict):
                    entries.append(item)
    return entries


def _is_config_path(path: str) -> bool:
    lower = path.lower()
    return any(lower.endswith(suf) for suf in CONFIG_SUFFIXES)


def _gate_config_parse(scan: Dict[str, Any], errors: List[str]) -> None:
    if scan.get("schema_version") != "1":
        errors.append("stage2-static-asset-scan.json: schema_version 必须为 1")

    entries = _iter_config_entries(scan)
    if not entries:
        errors.append(
            "stage2-static-asset-scan.json: 无 config_files/资产记录（须解析配置文件）"
        )
        return

    config_like = [e for e in entries if _is_config_path(str(e.get("file_path", "")))]
    if not config_like:
        config_like = [e for e in entries if e.get("asset_type") == "config"]

    if not config_like:
        errors.append(
            "stage2-static-asset-scan.json: 未包含配置文件条目（.yaml/.json/.toml 等）"
        )
        return

    for idx, item in enumerate(config_like):
        path = item.get("file_path") or item.get("path") or f"#{idx}"
        status = str(item.get("parse_status", "")).lower()
        if status in ("listed_only", "skipped", "not_parsed", ""):
            errors.append(
                f"stage2-static-asset-scan.json: {path} parse_status={status!r} "
                "违规（必须真正解析，不得仅列路径）"
            )
            continue
        if status != "parsed":
            errors.append(
                f"stage2-static-asset-scan.json: {path} parse_status 必须为 parsed"
            )
            continue

        method = (item.get("parse_method") or "").strip()
        if not method:
            errors.append(
                f"stage2-static-asset-scan.json: {path} 缺少 parse_method"
            )

        keys = item.get("extracted_keys")
        summary = (item.get("structure_summary") or "").strip()
        if not isinstance(keys, list) or len(keys) < 1:
            if len(summary) < 20:
                errors.append(
                    f"stage2-static-asset-scan.json: {path} 须含 extracted_keys "
                    "或足够长的 structure_summary（证明已解析内容）"
                )

        consumers = item.get("consumer_refs") or item.get("runtime_consumers")
        if not consumers:
            errors.append(
                f"stage2-static-asset-scan.json: {path} 缺少 consumer_refs 或 "
                "runtime_consumers（配置读取/消费方）"
            )


def _lang_of_file(file_path: str) -> Optional[str]:
    """从文件路径扩展名推断其所属代码语言（基于白名单）。"""
    suffix = Path(file_path).suffix.lower()
    return CODE_LANGUAGE_MAP.get(suffix)


def _impact_languages(feature_dir: Path) -> Set[str]:
    """从波及清单 stage2-impact-candidates.json 收集已出现的语言集合。

    优先用功能项显式标注的 language 字段；缺失时回退到 code_file_path/evidence 推断。
    容错：文件不存在/格式异常时返回空集（由调用方决定如何处理）。
    """
    candidates = feature_dir / "on-demand" / "stage2-impact-candidates.json"
    if not candidates.is_file():
        return set()
    try:
        data = _read_json(candidates)
    except (json.JSONDecodeError, OSError):
        return set()
    items = data.get("functions") or data.get("items") or data
    if isinstance(items, dict):
        items = list(items.values())
    if not isinstance(items, list):
        return set()

    langs: Set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        # 1) 显式 language 字段
        lang = str(item.get("language") or "").strip()
        if lang:
            langs.add(lang)
            continue
        # 2) 从 code_file_path / evidence 路径推断
        for key in ("code_file_path", "file_path", "path"):
            fp = item.get(key)
            if isinstance(fp, str) and fp:
                inferred = _lang_of_file(fp)
                if inferred:
                    langs.add(inferred)
                    break
        else:
            # 3) evidence 可能是路径字符串或列表
            ev = item.get("evidence")
            paths: List[str] = []
            if isinstance(ev, str):
                paths = [ev]
            elif isinstance(ev, list):
                paths = [str(x) for x in ev if isinstance(x, str)]
            for fp in paths:
                inferred = _lang_of_file(fp)
                if inferred:
                    langs.add(inferred)
                    break
    return langs


def _gate_polyglot_coverage(
    coverage: Dict[str, Any],
    repo_root: Path,
    feature_dir: Path,
    scope_paths: Optional[List[str]],
    exclude_globs: Optional[List[str]],
    errors: List[str],
) -> None:
    """多语言覆盖强制约束（第 4 项）。

    - coverage["languages"] 必须是非空数组；
    - 每项须含 role(primary|auxiliary)、coverage_status(covered|degraded)、analysis_method；
    - degraded 必须含非空 degraded_rationale（禁止裸 uncovered）；
    - gate 自动扫盘发现仓库实际语言，漏报语言即失败（scoped 模式限定 scope）；
    - 波及校验：附属语言要么在波及清单出现（impact_status=hit），要么显式声明
      impact_status=no_hit 且附 no_impact_rationale（禁止沉默遗漏）。
    """
    languages = coverage.get("languages")
    if not isinstance(languages, list) or len(languages) == 0:
        errors.append(
            "stage2-search-coverage.json: 缺少 languages（多语言覆盖清单，"
            "禁止只分析主语言）"
        )
        return

    declared: Set[str] = set()
    primary_count = 0
    auxiliary_impact_required: List[tuple] = []  # [(name, impact_status)]
    for idx, lang in enumerate(languages):
        if not isinstance(lang, dict):
            errors.append(f"stage2-search-coverage.json: languages[{idx}] 非对象")
            continue
        name = (lang.get("name") or "").strip()
        if not name:
            errors.append(f"stage2-search-coverage.json: languages[{idx}] 缺少 name")
            continue
        declared.add(name)

        role = str(lang.get("role", "")).strip()
        if role not in ("primary", "auxiliary"):
            errors.append(
                f"stage2-search-coverage.json: languages[{name}] role 必须为 "
                "primary 或 auxiliary"
            )
        if role == "primary":
            primary_count += 1

        status = str(lang.get("coverage_status", "")).strip()
        method = str(lang.get("analysis_method", "")).strip()
        if status not in ("covered", "degraded"):
            errors.append(
                f"stage2-search-coverage.json: languages[{name}] coverage_status="
                f"{status!r} 违规（必须 covered 或 degraded，禁止裸 uncovered）"
            )
        if not method:
            errors.append(
                f"stage2-search-coverage.json: languages[{name}] 缺少 "
                "analysis_method（lsp/grep/read/manual）"
            )
        if status == "degraded":
            rationale = (lang.get("degraded_rationale") or "").strip()
            if not rationale:
                errors.append(
                    f"stage2-search-coverage.json: languages[{name}] 为 degraded "
                    "但缺少 degraded_rationale"
                )

        # 波及校验登记：附属语言须显式声明是否在波及清单出现
        if role == "auxiliary":
            impact_status = str(lang.get("impact_status", "")).strip()
            auxiliary_impact_required.append((name, impact_status))

    if primary_count == 0:
        errors.append(
            "stage2-search-coverage.json: languages 至少须有一个 role=primary"
        )

    # 自动发现：仓库实际语言必须全部声明（漏报即失败）
    actual = _repo_code_languages(repo_root, scope_paths, exclude_globs)
    undeclared = actual - declared
    if undeclared:
        errors.append(
            "stage2-search-coverage.json: 仓库实际含以下语言未在 languages 中声明: "
            + ", ".join(sorted(undeclared))
        )

    # 波及多语言机器校验：附属语言要么在波及清单命中，要么显式声明 no_hit + 理由
    impact_langs = _impact_languages(feature_dir)
    for name, impact_status in auxiliary_impact_required:
        if impact_status == "hit":
            if name not in impact_langs:
                errors.append(
                    f"stage2-search-coverage.json: languages[{name}] impact_status=hit "
                    f"但波及清单未出现该语言命中（检查 language/code_file_path 字段）"
                )
        elif impact_status == "no_hit":
            # 波及清单确实未命中该语言时，须与事实一致
            if name in impact_langs:
                errors.append(
                    f"stage2-search-coverage.json: languages[{name}] impact_status=no_hit "
                    f"但波及清单实际含该语言命中（状态矛盾）"
                )
            # 必须给出未命中理由（禁止沉默遗漏）
            # rationale 在 languages 项里查
        else:
            errors.append(
                f"stage2-search-coverage.json: languages[{name}] 缺少 impact_status"
                f"（附属语言须声明 hit 或 no_hit，禁止沉默）"
            )

    # impact_status=no_hit 必须附 no_impact_rationale（二次遍历取 rationale）
    for lang in languages:
        if not isinstance(lang, dict):
            continue
        if str(lang.get("impact_status", "")).strip() == "no_hit":
            rationale = (lang.get("no_impact_rationale") or "").strip()
            if not rationale:
                name = lang.get("name", "?")
                errors.append(
                    f"stage2-search-coverage.json: languages[{name}] impact_status=no_hit "
                    f"但缺少 no_impact_rationale（须说明为何未波及该附属语言）"
                )


def _gate_step_stage2(
    feature_dir: Path, repo_root: Path, scope_paths: Optional[List[str]] = None, exclude_globs: Optional[List[str]] = None
) -> List[str]:
    errors: List[str] = []
    scope_paths = scope_paths or []
    exclude_globs = exclude_globs or []
    on_demand = feature_dir / "on-demand"

    coverage_path = on_demand / "stage2-search-coverage.json"
    trace_path = on_demand / "stage2-call-trace.json"
    static_path = on_demand / "stage2-static-asset-scan.json"

    for path, label in (
        (coverage_path, "stage2-search-coverage.json"),
        (trace_path, "stage2-call-trace.json"),
        (static_path, "stage2-static-asset-scan.json"),
    ):
        if not path.is_file():
            errors.append(f"缺少 Harness 产物: {label}")
            return errors

    try:
        coverage = _read_json(coverage_path)
        trace_doc = _read_json(trace_path)
        static_scan = _read_json(static_path)
    except json.JSONDecodeError as exc:
        errors.append(f"JSON 解析失败: {exc}")
        return errors

    if scope_paths:
        _gate_scoped_search(coverage, repo_root, scope_paths, exclude_globs, errors)
    else:
        _gate_full_repo_search(coverage, repo_root, errors)
    _gate_call_chain_depth(trace_doc, feature_dir, errors)
    _gate_config_parse(static_scan, errors)
    _gate_polyglot_coverage(coverage, repo_root, feature_dir, scope_paths, exclude_globs, errors)

    impact = on_demand / "stage2-impact-candidates.json"
    if not impact.is_file():
        errors.append("缺少 stage2-impact-candidates.json")

    return errors


def cmd_gate(args: argparse.Namespace) -> int:
    working_dir = Path(args.working_dir).resolve()
    if not working_dir.is_dir():
        print(json.dumps({"errors": [f"WORKING_DIR 不存在: {working_dir}"]}))
        return 1

    feature_dir = Path(args.feature_dir).resolve()
    if not feature_dir.is_dir():
        print(json.dumps({"errors": [f"FEATURE_DIR 不存在: {feature_dir}"]}))
        return 1

    repo_root = Path(args.repo_root).resolve() if args.repo_root else working_dir
    scope_paths = _normalize_scope_paths(_parse_csv_arg(args.scope_paths), repo_root)
    exclude_globs = _parse_csv_arg(args.exclude_globs)
    step = args.step

    errors: List[str] = []
    if step in ("stage2", "all"):
        errors.extend(_gate_step_stage2(feature_dir, repo_root, scope_paths, exclude_globs))

    result = {
        "step": step,
        "working_dir": str(working_dir),
        "feature_dir": str(feature_dir),
        "repo_root": str(repo_root),
        "validated_at": _utc_now(),
        "gate_passed": len(errors) == 0,
        "errors": errors,
        "constraints_checked": [
            "scoped_search" if scope_paths else "full_repo_search",
            "call_chain_depth",
            "config_parse",
            "polyglot_coverage",
        ],
    }

    if args.record:
        run_path = feature_dir / ".runs" / "reverse-on-demand-run.json"
        if run_path.is_file():
            try:
                run_data = _read_json(run_path)
            except (json.JSONDecodeError, OSError):
                run_data = {"gates": {}}
        else:
            run_data = {"gates": {}}
        gates = run_data.setdefault("gates", {})
        gates[step] = {
            "validated_at": result["validated_at"],
            "gate_passed": result["gate_passed"],
            "errors": errors,
        }
        _write_json(run_path, run_data)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["gate_passed"] else 1


def cmd_resume(args: argparse.Namespace) -> int:
    working_dir = Path(args.working_dir).resolve()
    if not working_dir.is_dir():
        print(json.dumps({"errors": [f"WORKING_DIR 不存在: {working_dir}"]}))
        return 1

    feature_dir = Path(args.feature_dir).resolve()
    run_path = feature_dir / ".runs" / "reverse-on-demand-run.json"
    pending = ["stage2"]
    if run_path.is_file():
        try:
            run_data = _read_json(run_path)
            for step, info in (run_data.get("gates") or {}).items():
                if info.get("gate_passed"):
                    if step in pending:
                        pending.remove(step)
        except (json.JSONDecodeError, OSError):
            pass
    print(
        json.dumps(
            {"working_dir": str(working_dir), "pending_steps": pending},
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="reverse-on-demand harness")
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="初始化 Harness 目录与阶段2契约骨架")
    p_init.add_argument("--working-dir", required=True)
    p_init.add_argument("--feature-dir", required=True)
    p_init.add_argument("--repo-root", default="")
    p_init.add_argument("--scope-paths", default="")
    p_init.add_argument("--exclude-globs", default="")

    p_gate = sub.add_parser("gate", help="分步门禁")
    p_gate.add_argument("--working-dir", required=True)
    p_gate.add_argument("--feature-dir", required=True)
    p_gate.add_argument("--repo-root", default="")
    p_gate.add_argument("--scope-paths", default="")
    p_gate.add_argument("--exclude-globs", default="")
    p_gate.add_argument("--step", choices=GATE_STEPS, default="stage2")
    p_gate.add_argument("--record", action="store_true")

    p_resume = sub.add_parser("resume", help="断点续跑：列出未通过门禁的步骤")
    p_resume.add_argument("--working-dir", required=True)
    p_resume.add_argument("--feature-dir", required=True)

    args = parser.parse_args()
    if args.command == "init":
        return cmd_init(args)
    if args.command == "gate":
        return cmd_gate(args)
    if args.command == "resume":
        return cmd_resume(args)
    return 1


if __name__ == "__main__":
    sys.exit(main())
