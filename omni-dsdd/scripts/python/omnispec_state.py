#!/usr/bin/env python3
"""SDD workflow 状态文件 (.omnispec-state.json) 与特性目录解析的统一实现。"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def _utc_now():
    # type: () -> str
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path):
    # type: (Path) -> Dict[str, Any]
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path, data):
    # type: (Path, Dict[str, Any]) -> None
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def plugin_root_from_env():
    # type: () -> Path
    raw = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if raw:
        return Path(raw).resolve()
    return Path(__file__).resolve().parent.parent.parent


def working_dir_from_env():
    # type: () -> Path
    raw = os.environ.get("CLAUDE_WORKING_DIR")
    if raw:
        return Path(raw).resolve()
    return Path.cwd().resolve()


def resolve_doc_dir(working_dir, doc_dir=None):
    # type: (Path, Optional[str]) -> Path
    """Resolve DOC_DIR to an absolute path under working_dir when relative."""
    raw = (doc_dir or "omni-doc").strip() or "omni-doc"
    path = Path(raw)
    if path.is_absolute():
        return path.resolve()
    return (working_dir.resolve() / path).resolve()


def resolve_path_under_base(base_dir, path_arg=None, default_rel=None):
    # type: (Path, Optional[str], Optional[str]) -> Path
    """Resolve a file path under base_dir; relative path_arg is not cwd-relative."""
    base = base_dir.resolve()
    raw = (path_arg or "").strip()
    if raw:
        p = Path(raw)
        if p.is_absolute():
            return p.resolve()
        return (base / p).resolve()
    if default_rel:
        return (base / default_rel).resolve()
    raise ValueError("path_arg or default_rel is required")


def doc_dir_paths(working_dir, doc_dir=None):
    # type: (Path, Optional[str]) -> Dict[str, str]
    """Absolute DOC_DIR and standard subdirectories for paths.json / env.sh."""
    root = resolve_doc_dir(working_dir, doc_dir)
    return {
        "doc_dir": str(root),
        "doc_specs_dir": str((root / "specs").resolve()),
        "doc_rules_dir": str((root / "rules").resolve()),
        "doc_navigations_dir": str((root / "navigations").resolve()),
        "doc_on_demand_dir": str((root / "on-demand").resolve()),
    }


def repo_root_from_script():
    # type: () -> Path
    """Deprecated alias: returns plugin root (historical misnomer)."""
    return plugin_root_from_env()


def infer_working_dir_from_feature(feature_dir):
    # type: (Path) -> Path
    p = feature_dir.resolve()
    if p.parent.name == "changes":
        return p.parent.parent
    return working_dir_from_env()


def active_feature_pointer(working_dir):
    # type: (Path) -> Path
    return working_dir / "changes" / ".active-feature"


def write_active_feature(working_dir, feature_dir):
    # type: (Path, Path) -> None
    pointer = active_feature_pointer(working_dir)
    pointer.parent.mkdir(parents=True, exist_ok=True)
    pointer.write_text(str(feature_dir.resolve()) + "\n", encoding="utf-8")


def read_active_feature(working_dir):
    # type: (Path) -> Optional[Path]
    pointer = active_feature_pointer(working_dir)
    if not pointer.is_file():
        return None
    raw = pointer.read_text(encoding="utf-8").strip()
    if not raw:
        return None
    path = Path(raw).resolve()
    return path if path.is_dir() else None


def _changes_root(working_dir):
    # type: (Path) -> Path
    return (working_dir.resolve() / "changes").resolve()


def feature_dir_in_working_changes(working_dir, feature_dir):
    # type: (Path, Path) -> bool
    """特性目录必须位于 <working_dir>/changes/<name> 下（防跨工作区误读状态）。"""
    try:
        feature_dir.resolve().relative_to(_changes_root(working_dir))
    except ValueError:
        return False
    return feature_dir.resolve().is_dir()


def validate_feature_dir_under_changes(working_dir, feature_dir):
    # type: (Optional[Path], Path) -> Optional[str]
    """校验 FEATURE_DIR 为 <working_dir>/changes/<子目录>/<name>。通过返回 None，否则返回错误说明。"""
    fd = Path(feature_dir).resolve()
    if not fd.is_dir():
        return "feature_dir is not a directory: {0}".format(fd)
    if "changes" not in fd.parts:
        return "feature_dir must be under <WORKING_DIR>/changes/, got: {0}".format(fd)
    wd = Path(working_dir).resolve() if working_dir is not None else fd.parent.parent
    if not feature_dir_in_working_changes(wd, fd):
        return "feature_dir must be under {0}/changes/, got: {1}".format(wd, fd)
    return None


def _accept_feature_dir(working_dir, feature_dir):
    # type: (Path, Optional[Path]) -> Optional[Path]
    if feature_dir is None:
        return None
    path = feature_dir.resolve()
    if not path.is_dir():
        return None
    if not feature_dir_in_working_changes(working_dir, path):
        return None
    return path


def _feature_dir_from_paths_json(paths_file, working_dir=None):
    # type: (Path, Optional[Path]) -> Optional[Path]
    if not paths_file.is_file():
        return None
    try:
        data = _read_json(paths_file)
    except json.JSONDecodeError:
        return None
    raw = data.get("feature_dir") or data.get("FEATURE_DIR")
    if not raw:
        return None
    path = Path(raw).resolve()
    if not path.is_dir():
        return None
    if working_dir is not None:
        return _accept_feature_dir(working_dir, path)
    return path


def _run_prerequisites_json(working_dir, plugin_root=None):
    # type: (Path, Optional[Path]) -> Optional[Dict[str, Any]]
    import subprocess

    plugin_root = (plugin_root or plugin_root_from_env()).resolve()
    working_dir = working_dir.resolve()
    prereq = plugin_root / "scripts" / "bash" / "check-prerequisites.sh"
    if not prereq.is_file():
        return None
    try:
        proc = subprocess.run(
            [
                "bash",
                str(prereq),
                "--json",
                "--paths-only",
                "--working-dir",
                str(working_dir),
                "--plugin-root",
                str(plugin_root),
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            cwd=str(working_dir),
        )
        return json.loads(proc.stdout)
    except (subprocess.CalledProcessError, json.JSONDecodeError, OSError):
        return None


def resolve_feature_dir(
    working_dir=None,
    env_override=None,
    use_prerequisites=True,
    plugin_root=None,
    repo_root=None,
):
    # type: (Optional[Path], Optional[str], bool, Optional[Path], Optional[Path]) -> Optional[Path]
    """解析当前特性目录。优先级: 显式参数 > 环境变量 > .active-feature > 最新 state > check-prerequisites。

    所有候选路径必须落在 <working_dir>/changes/ 下，否则忽略并尝试下一来源。
    """
    if repo_root is not None and working_dir is None:
        working_dir = repo_root
    root = (working_dir or working_dir_from_env()).resolve()
    plugin = (plugin_root or plugin_root_from_env()).resolve()

    for candidate in (
        env_override,
        os.environ.get("OMNISPEC_FEATURE_DIR"),
        os.environ.get("FEATURE_DIR"),
    ):
        if candidate:
            path = Path(candidate).resolve()
            if path.is_dir() and (path / ".runs").is_dir():
                accepted = _accept_feature_dir(root, path)
                if accepted is not None:
                    return accepted

    active = read_active_feature(root)
    accepted = _accept_feature_dir(root, active)
    if accepted is not None:
        return accepted

    state_files = sorted(
        root.glob("changes/*/.runs/.omnispec-state.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for state_path in state_files:
        feature_dir = state_path.parent.parent
        if not feature_dir.is_dir():
            continue
        resolved = _feature_dir_from_paths_json(
            feature_dir / ".runs" / "paths.json", working_dir=root
        )
        accepted = _accept_feature_dir(root, resolved or feature_dir.resolve())
        if accepted is not None:
            return accepted

    if use_prerequisites:
        info = _run_prerequisites_json(root, plugin)
        if info:
            raw = info.get("FEATURE_DIR")
            if raw:
                accepted = _accept_feature_dir(root, Path(raw).resolve())
                if accepted is not None:
                    return accepted

    return None


VALID_FLOW_MODES = ("express", "standard", "deep")
EXPLICIT_FLOW_MODES = VALID_FLOW_MODES + ("expert",)
DEFAULT_FLOW_MODE = "express"


def pending_workflow_path(working_dir):
    # type: (Path) -> Path
    return Path(working_dir).resolve() / "changes" / ".pending-workflow.json"


def _normalize_flow_mode(raw):
    # type: (Optional[str]) -> str
    fm = (raw or "").strip().lower()
    if fm in VALID_FLOW_MODES:
        return fm
    return ""


def _normalize_explicit_flow_mode(raw):
    # type: (Optional[str]) -> str
    fm = (raw or "").strip().lower()
    if fm in EXPLICIT_FLOW_MODES:
        return fm
    return ""


def write_pending_workflow(working_dir, flow_mode, arguments="", forced=False):
    # type: (Path, str, str, bool) -> Path
    """routing 确定 flow_mode 后写入工作区，供 specify init 合并（特性目录尚未创建时）。"""
    fm = (
        _normalize_explicit_flow_mode(flow_mode)
        if forced
        else _normalize_flow_mode(flow_mode)
    ) or DEFAULT_FLOW_MODE
    path = pending_workflow_path(working_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    _write_json(
        path,
        {
            "flow_mode": fm,
            "arguments": arguments or "",
            "forced": bool(forced),
            "set_at": _utc_now(),
            "consumed": False,
        },
    )
    return path


def read_pending_workflow(working_dir):
    # type: (Path) -> Dict[str, Any]
    path = pending_workflow_path(working_dir)
    if not path.is_file():
        return {}
    try:
        data = _read_json(path)
    except json.JSONDecodeError:
        return {}
    if data.get("consumed"):
        return {}
    return data


def consume_pending_workflow(working_dir):
    # type: (Path) -> None
    path = pending_workflow_path(working_dir)
    if not path.is_file():
        return
    try:
        data = _read_json(path)
    except json.JSONDecodeError:
        try:
            path.unlink()
        except OSError:
            pass
        return
    data["consumed"] = True
    data["consumed_at"] = _utc_now()
    _write_json(path, data)


def resolve_flow_mode(feature_dir, cli_override=None, working_dir=None, default=DEFAULT_FLOW_MODE):
    # type: (Path, Optional[str], Optional[Path], str) -> str
    """CLI > state.json > paths.json > pending > default（express）。"""
    cli = _normalize_explicit_flow_mode(cli_override)
    if cli:
        return cli

    feature_dir = feature_dir.resolve()
    state_path = feature_dir / ".runs" / ".omnispec-state.json"
    if state_path.is_file():
        try:
            fm = _normalize_explicit_flow_mode(_read_json(state_path).get("flow_mode"))
            if fm:
                return fm
        except json.JSONDecodeError:
            pass

    paths_path = feature_dir / ".runs" / "paths.json"
    if paths_path.is_file():
        try:
            fm = _normalize_explicit_flow_mode(_read_json(paths_path).get("flow_mode"))
            if fm:
                return fm
        except json.JSONDecodeError:
            pass

    wd = Path(working_dir).resolve() if working_dir is not None else infer_working_dir_from_feature(feature_dir)
    pending = read_pending_workflow(wd)
    fm = (
        _normalize_explicit_flow_mode(pending.get("flow_mode"))
        if pending.get("forced")
        else _normalize_flow_mode(pending.get("flow_mode"))
    )
    if fm:
        return fm

    return _normalize_flow_mode(default) or DEFAULT_FLOW_MODE


def sync_flow_mode_to_paths(feature_dir, flow_mode):
    # type: (Path, str) -> None
    fm = _normalize_explicit_flow_mode(flow_mode)
    if not fm:
        return
    feature_dir = feature_dir.resolve()
    paths_file = feature_dir / ".runs" / "paths.json"
    if paths_file.is_file():
        try:
            paths = _read_json(paths_file)
        except json.JSONDecodeError:
            paths = {}
        paths["flow_mode"] = fm
        _write_json(paths_file, paths)

    env_sh = feature_dir / ".runs" / "env.sh"
    if env_sh.is_file():
        export_line = 'export FLOW_MODE="{0}"'.format(fm)
        lines = env_sh.read_text(encoding="utf-8").splitlines()
        out = []  # type: List[str]
        found = False
        for line in lines:
            if line.startswith("export FLOW_MODE="):
                out.append(export_line)
                found = True
            else:
                out.append(line)
        if not found:
            out.append(export_line)
        env_sh.write_text("\n".join(out) + "\n", encoding="utf-8")


def init_stub_state(feature_dir, flow_mode=""):
    # type: (Path, str) -> Path
    state_path = feature_dir / ".runs" / ".omnispec-state.json"
    if state_path.is_file():
        return state_path
    _write_json(
        state_path,
        {
            "flow_mode": flow_mode,
            "current_stage": "init",
            "completed_stages": [],
            "last_updated": _utc_now(),
        },
    )
    return state_path


def update_state(
    feature_dir,
    current_stage,
    mark_complete=None,
    flow_mode=None,
    arguments=None,
    validation_patch=None,
):
    # type: (Path, str, Optional[List[str]], Optional[str], Optional[str], Optional[Dict[str, Any]]) -> Dict[str, Any]
    feature_dir = feature_dir.resolve()
    state_path = feature_dir / ".runs" / ".omnispec-state.json"

    if state_path.is_file():
        try:
            state = _read_json(state_path)
        except json.JSONDecodeError:
            state = {}
    else:
        state = {
            "flow_mode": flow_mode or "",
            "current_stage": "init",
            "completed_stages": [],
        }

    if flow_mode:
        state["flow_mode"] = flow_mode
    state["current_stage"] = current_stage

    completed = list(state.get("completed_stages") or [])
    for stage in mark_complete or []:
        if stage and stage not in completed:
            completed.append(stage)
    state["completed_stages"] = completed
    state["last_updated"] = _utc_now()

    if arguments is not None:
        state["arguments"] = arguments

    if validation_patch:
        vr = dict(state.get("validation_results") or {})
        vr.update(validation_patch)
        state["validation_results"] = vr

    _write_json(state_path, state)
    fm_sync = _normalize_explicit_flow_mode(state.get("flow_mode"))
    if fm_sync:
        sync_flow_mode_to_paths(feature_dir, fm_sync)
    write_active_feature(infer_working_dir_from_feature(feature_dir), feature_dir)
    return state


def gate_state(feature_dir, required_in_completed):
    # type: (Path, str) -> List[str]
    errors = []  # type: List[str]
    state_path = feature_dir / ".runs" / ".omnispec-state.json"
    if not state_path.is_file():
        errors.append(".omnispec-state.json: missing (run specify-finalize.sh or workflow-update-state.sh)")
        return errors
    try:
        state = _read_json(state_path)
    except json.JSONDecodeError:
        errors.append(".omnispec-state.json: invalid JSON")
        return errors

    completed = state.get("completed_stages") or []
    if required_in_completed not in completed:
        errors.append(
            ".omnispec-state.json: completed_stages missing '{0}'".format(required_in_completed)
        )

    paths_file = feature_dir / ".runs" / "paths.json"
    if paths_file.is_file():
        try:
            paths = _read_json(paths_file)
            recorded = paths.get("feature_dir") or ""
            if recorded and Path(recorded).resolve() != feature_dir.resolve():
                errors.append("paths.json: feature_dir mismatch with --feature-dir")
        except json.JSONDecodeError:
            errors.append("paths.json: invalid JSON")

    return errors


def cmd_resolve(args):
    # type: (argparse.Namespace) -> int
    if args.working_dir:
        root = Path(args.working_dir).resolve()
    elif args.repo_root:
        root = Path(args.repo_root).resolve()
    else:
        root = working_dir_from_env()
    plugin = Path(args.plugin_root).resolve() if args.plugin_root else plugin_root_from_env()
    feature_dir = resolve_feature_dir(
        working_dir=root,
        env_override=args.feature_dir,
        use_prerequisites=not args.no_prerequisites,
        plugin_root=plugin,
    )
    if feature_dir is None:
        print(json.dumps({"FEATURE_DIR": None, "resolved": False}, ensure_ascii=False))
        return 1
    print(
        json.dumps(
            {"FEATURE_DIR": str(feature_dir), "resolved": True},
            ensure_ascii=False,
        )
    )
    return 0


def cmd_update(args):
    # type: (argparse.Namespace) -> int
    feature_dir = Path(args.feature_dir).resolve()
    if not feature_dir.is_dir():
        print("ERROR: feature dir not found: {0}".format(feature_dir), file=sys.stderr)
        return 2

    validation_patch = None
    if args.validation_json:
        validation_patch = json.loads(args.validation_json)

    flow_mode = _normalize_explicit_flow_mode(args.flow_mode) or None
    if not flow_mode:
        wd = Path(args.working_dir).resolve() if args.working_dir else None
        flow_mode = resolve_flow_mode(feature_dir, working_dir=wd)

    state = update_state(
        feature_dir,
        current_stage=args.current_stage,
        mark_complete=args.mark_complete or None,
        flow_mode=flow_mode,
        arguments=args.arguments,
        validation_patch=validation_patch,
    )
    result = {"status": "ok", "state": state}  # type: Dict[str, Any]
    if not getattr(args, "no_sync_progress", False):
        progress_path = write_workflow_progress_md(
            feature_dir,
            note=getattr(args, "note", "") or "",
            step_label=getattr(args, "step", "") or "",
        )
        result["progress_file"] = str(progress_path)
    print(json.dumps(result, ensure_ascii=False))
    return 0


def cmd_gate(args):
    # type: (argparse.Namespace) -> int
    feature_dir = Path(args.feature_dir).resolve()
    errors = gate_state(feature_dir, required_in_completed=args.require_completed)
    result = {"gate_exit": 0 if not errors else 1, "errors": errors}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result["gate_exit"]


# express / standard / deep 共用 SDD 阶段（standard/deep 含 clarify）
WORKFLOW_PROGRESS_STAGES = [
    ("specify", "规范生成"),
    ("clarify", "规范澄清"),
    ("design", "设计规划"),
    ("tasks", "任务分解"),
    ("analyze", "一致性分析"),
    ("implement", "代码实现"),
    ("review", "安全与代码审查"),
]  # type: List[Tuple[str, str]]

EXPERT_PROGRESS_STAGES = [
    ("create-branch", "特性目录与分支"),
    ("brainstorming", "头脑风暴设计"),
    ("brainstorming-sdd-bridge", "强结构接口桥接"),
    ("tasks", "任务分解"),
    ("implement", "代码实现"),
    ("review", "安全与代码审查"),
    ("local-sandbox-fix", "本地沙盒验证"),
]  # type: List[Tuple[str, str]]

# express-workflow Step 1–6（与 agents/express-workflow.md 一致）
EXPRESS_PROGRESS_STAGES = [
    (1, "specify", "规范生成"),
    (2, "design", "设计规划"),
    (3, "tasks", "任务分解"),
    (4, "analyze", "一致性分析"),
    (5, "implement", "代码实现"),
    (6, "review", "安全与代码审查"),
]  # type: List[Tuple[int, str, str]]


def _stage_checklist_line(mark, stage_id, stage_title, suffix, express_step=None):
    # type: (str, str, str, str, Optional[int]) -> str
    if express_step is not None:
        return "- [{0}] **Step {1} {2}** — {3}{4}".format(
            mark, express_step, stage_id, stage_title, suffix
        )
    return "- [{0}] **{1}** — {2}{3}".format(mark, stage_id, stage_title, suffix)


def write_workflow_progress_md(
    feature_dir,
    note="",
    step_label="",
):
    # type: (Path, str, str) -> Path
    """根据 .omnispec-state.json 生成/覆盖 workflow-progress.md（人类可读进度）。"""
    feature_dir = feature_dir.resolve()
    state_path = feature_dir / ".runs" / ".omnispec-state.json"
    progress_path = feature_dir / ".runs" / "workflow-progress.md"

    state = {}  # type: Dict[str, Any]
    if state_path.is_file():
        try:
            state = _read_json(state_path)
        except json.JSONDecodeError:
            state = {}

    flow_mode = str(state.get("flow_mode") or "unknown")
    current_stage = str(state.get("current_stage") or "")
    completed = set(state.get("completed_stages") or [])
    last_updated = str(state.get("last_updated") or _utc_now())
    is_express = flow_mode == "express"
    is_expert = flow_mode == "expert"
    is_complete = current_stage == "workflow-complete"

    current_stage_display = (
        "{0} ✅ 全部阶段已完成".format(current_stage)
        if is_complete
        else current_stage
    )

    lines = [
        "# SDD Workflow 进度",
        "",
        "- **flow_mode**: `{0}`".format(flow_mode),
        "- **FEATURE_DIR**: `{0}`".format(feature_dir),
        "- **current_stage**: `{0}`".format(current_stage_display),
        "- **last_updated**: {0}".format(last_updated),
    ]
    if step_label:
        lines.append("- **最近完成 Step**: {0}".format(step_label))
    if note:
        lines.append("- **备注**: {0}".format(note))

    if is_express:
        lines.extend(["", "## 阶段清单（express Step 1–6）", ""])
        for step_no, stage_id, stage_title in EXPRESS_PROGRESS_STAGES:
            if stage_id in completed:
                mark = "x"
                suffix = ""
            else:
                mark = " "
                suffix = " ← 待执行" if stage_id == current_stage else ""
            lines.append(
                _stage_checklist_line(mark, stage_id, stage_title, suffix, express_step=step_no)
            )
        completion_lines = [
            "",
            "## 完成判定（express）",
            "",
            "- express **未完成**：Step 5 `implement` 未勾选",
            "- express **可输出最终摘要**：Step 1–6 全部勾选",
            "- **权威完成标志**：`current_stage == workflow-complete`",
        ]
    else:
        stages = EXPERT_PROGRESS_STAGES if is_expert else WORKFLOW_PROGRESS_STAGES
        section_title = "## 阶段清单（expert）" if is_expert else "## 阶段清单"
        lines.extend(["", section_title, ""])
        for stage_id, stage_title in stages:
            if stage_id in completed:
                mark = "x"
                suffix = ""
            else:
                mark = " "
                suffix = " ← 待执行" if stage_id == current_stage else ""
            lines.append(_stage_checklist_line(mark, stage_id, stage_title, suffix))
        if is_expert:
            completion_lines = [
                "",
                "## 完成判定（expert）",
                "",
                "- expert **未完成**：`completed_stages` 不含 `implement`、`review` 或 `local-sandbox-fix`",
                "- expert **可输出最终摘要**：`completed_stages` 含 `implement`、`review` 与 `local-sandbox-fix`",
                "- **权威完成标志**：`current_stage == workflow-complete`",
            ]
        else:
            completion_lines = [
                "",
                "## 完成判定",
                "",
                "- workflow **未完成**：`completed_stages` 不含 `implement`",
                "- workflow **可输出最终摘要**：`completed_stages` 含 `implement` 与 `review`",
                "- **权威完成标志**：`current_stage == workflow-complete`",
            ]

    lines.extend(
        completion_lines
        + [
            "",
            "_由 `workflow-update-progress.sh` / `omnispec_state.py progress` 于 {0} 生成_".format(
                _utc_now()
            ),
            "",
        ]
    )

    progress_path.parent.mkdir(parents=True, exist_ok=True)
    progress_path.write_text("\n".join(lines), encoding="utf-8")
    return progress_path


def cmd_progress(args):
    # type: (argparse.Namespace) -> int
    feature_dir = Path(args.feature_dir).resolve()
    if not feature_dir.is_dir():
        print("ERROR: feature dir not found: {0}".format(feature_dir), file=sys.stderr)
        return 2
    path = write_workflow_progress_md(
        feature_dir,
        note=args.note or "",
        step_label=args.step or "",
    )
    print(json.dumps({"status": "ok", "progress_file": str(path)}, ensure_ascii=False))
    return 0


def cmd_resolve_flow_mode(args):
    # type: (argparse.Namespace) -> int
    feature_dir = Path(args.feature_dir).resolve()
    if not feature_dir.is_dir():
        print("ERROR: feature dir not found: {0}".format(feature_dir), file=sys.stderr)
        return 2
    wd = Path(args.working_dir).resolve() if args.working_dir else None
    fm = resolve_flow_mode(
        feature_dir,
        cli_override=args.cli_override or None,
        working_dir=wd,
    )
    print(json.dumps({"flow_mode": fm}, ensure_ascii=False))
    return 0


def cmd_pending_write(args):
    # type: (argparse.Namespace) -> int
    if args.working_dir:
        wd = Path(args.working_dir).resolve()
    else:
        wd = working_dir_from_env()
    fm = (
        _normalize_explicit_flow_mode(args.flow_mode)
        if args.forced
        else _normalize_flow_mode(args.flow_mode)
    )
    if not fm:
        allowed = "express|standard|deep|expert" if args.forced else "express|standard|deep"
        print(f"ERROR: --flow-mode must be {allowed}", file=sys.stderr)
        return 2
    path = write_pending_workflow(
        wd,
        fm,
        arguments=args.arguments or "",
        forced=bool(args.forced),
    )
    print(
        json.dumps(
            {"status": "ok", "pending_file": str(path), "flow_mode": fm},
            ensure_ascii=False,
        )
    )
    return 0


def cmd_pending_consume(args):
    # type: (argparse.Namespace) -> int
    if args.working_dir:
        wd = Path(args.working_dir).resolve()
    else:
        wd = working_dir_from_env()
    consume_pending_workflow(wd)
    print(json.dumps({"status": "ok"}, ensure_ascii=False))
    return 0


def main():
    # type: () -> int
    parser = argparse.ArgumentParser(description="OmniSpec SDD state utilities")
    sub = parser.add_subparsers(dest="command")

    p_res = sub.add_parser("resolve", help="解析当前 FEATURE_DIR")
    p_res.add_argument("--feature-dir", default="", help="显式特性目录（优先）")
    p_res.add_argument("--working-dir", default="", help="工作区根 (CLAUDE_WORKING_DIR)")
    p_res.add_argument("--plugin-root", default="", help="插件根 (CLAUDE_PLUGIN_ROOT)")
    p_res.add_argument("--repo-root", default="", help="(已废弃) 等同 --working-dir")
    p_res.add_argument("--no-prerequisites", action="store_true")

    p_up = sub.add_parser("update", help="更新 .omnispec-state.json")
    p_up.add_argument("--feature-dir", required=True)
    p_up.add_argument("--current-stage", required=True)
    p_up.add_argument("--mark-complete", action="append", default=[])
    p_up.add_argument("--flow-mode", default="")
    p_up.add_argument("--working-dir", default="", help="resolve flow_mode 时的工作区根")
    p_up.add_argument("--arguments", default="")
    p_up.add_argument("--validation-json", default="")
    p_up.add_argument("--step", default="", help="同步 workflow-progress.md 时写入「最近完成 Step」")
    p_up.add_argument("--note", default="", help="同步 workflow-progress.md 时的备注")
    p_up.add_argument(
        "--no-sync-progress",
        action="store_true",
        help="更新 state 后不刷新 workflow-progress.md",
    )

    p_rfm = sub.add_parser("resolve-flow-mode", help="解析 flow_mode（CLI>state>paths>pending>express）")
    p_rfm.add_argument("--feature-dir", required=True)
    p_rfm.add_argument("--cli-override", default="")
    p_rfm.add_argument("--working-dir", default="")

    p_pw = sub.add_parser("pending-write", help="routing 写入 changes/.pending-workflow.json")
    p_pw.add_argument("--working-dir", default="")
    p_pw.add_argument("--flow-mode", required=True)
    p_pw.add_argument("--arguments", default="")
    p_pw.add_argument("--forced", action="store_true")

    p_pc = sub.add_parser("pending-consume", help="specify finalize 后消费 pending 文件")
    p_pc.add_argument("--working-dir", default="")

    p_gate = sub.add_parser("gate", help="校验状态文件")
    p_gate.add_argument("--feature-dir", required=True)
    p_gate.add_argument("--require-completed", default="specify")

    p_prog = sub.add_parser("progress", help="生成 workflow-progress.md")
    p_prog.add_argument("--feature-dir", required=True)
    p_prog.add_argument("--step", default="", help="最近完成的 Step 描述")
    p_prog.add_argument("--note", default="", help="附加备注")

    args = parser.parse_args()
    if not args.command:
        parser.error(
            "too few arguments: missing subcommand "
            "(resolve, update, gate, progress, resolve-flow-mode, pending-write, pending-consume)"
        )

    handlers = {
        "resolve": cmd_resolve,
        "update": cmd_update,
        "gate": cmd_gate,
        "progress": cmd_progress,
        "resolve-flow-mode": cmd_resolve_flow_mode,
        "pending-write": cmd_pending_write,
        "pending-consume": cmd_pending_consume,
    }
    return handlers[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
