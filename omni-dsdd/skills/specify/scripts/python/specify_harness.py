#!/usr/bin/env python3
"""specify 阶段 Harness：初始化、分步门禁、run manifest、SDD 状态同步、context 渲染。"""

import argparse
import importlib.util
import json
import os
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from specify_template_gate import (  # noqa: E402
    has_heading,
    load_contract,
    render_requirements_checklist_skeleton,
    render_spec_skeleton,
    section_body,
    validate_artifact,
)

_OMNI_STATE = None  # type: ignore


def _try_load_omnispec(feature_dir: Path) -> None:
    """gate 等路径未带 --plugin-root 时，从 paths.json 或仓库内嵌插件根加载。"""
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
    "spec.md",
    "context.md",
    "checklists/requirements.md",
    ".runs/evaluations/eval-specify-report.yaml",
    ".runs/metrics/omni-metrics-log.json",
]

STEP_ARTIFACT = {
    "1": ".runs/paths.json",
    "3": "context.md",
    "6": "spec.md",
    "8": "checklists/requirements.md",
    "9": ".runs/evaluations/eval-specify-report.yaml",
    "11": ".runs/metrics/omni-metrics-log.json",
    "11.5": ".runs/.omnispec-state.json",
}

GATE_STEPS = ("1", "3", "6", "8", "9", "11", "11.5")

CONTEXT_REQUIRED_HEADINGS = [
    "## 功能描述",
    "## 相关反构文档",
    "## 架构分析与设计参考",
    "## 术语对齐",
    "## 约束和假设",
]

# 二级钳制：spec-impact-analyze 在知识源就绪时须真实派发 knowledge-retrieval-agent，
# 并把结论写入 context.payload.json 的 knowledge_retrieval 字段。specify _gate_step_3 对该字段
# 做宽松兜底（payload 完全无该字段时不报错，兼容旧版；字段存在但不合规才拦截）。
_KR_VALID_MODES = ("enhance", "baseline")

_TEMPLATE_CONTRACT = None


def _contract() -> dict:
    global _TEMPLATE_CONTRACT
    if _TEMPLATE_CONTRACT is None:
        _TEMPLATE_CONTRACT = load_contract()
    return _TEMPLATE_CONTRACT


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _template_errors(rel_path: str, path: Path) -> List[str]:
    if not path.is_file():
        return []
    return validate_artifact(rel_path, _read_text(path), _contract())


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


def _load_run(feature_dir: Path) -> Dict[str, Any]:
    run_path = feature_dir / ".runs" / "specify-run.json"
    if run_path.is_file():
        return _read_json(run_path)
    return {
        "run_id": str(uuid.uuid4()),
        "stage": "specify",
        "started_at": _utc_now(),
        "last_updated": _utc_now(),
        "steps": {},
        "artifacts_required": ARTIFACTS_REQUIRED,
    }


def _save_run(feature_dir: Path, run: Dict[str, Any]) -> None:
    run["last_updated"] = _utc_now()
    _write_json(feature_dir / ".runs" / "specify-run.json", run)


def cmd_init(args: argparse.Namespace) -> int:
    plugin_root = _require_path(args.plugin_root, "--plugin-root")
    working_dir = _require_path(args.working_dir, "--working-dir")
    _load_omnispec_state(plugin_root)

    feature_dir = Path(args.feature_dir).resolve()
    path_err = _OMNI_STATE.validate_feature_dir_under_changes(working_dir, feature_dir)
    if path_err:
        print("ERROR: {0}".format(path_err), file=sys.stderr)
        return 2
    feature_dir.mkdir(parents=True, exist_ok=True)
    for sub in (
        "checklists",
        ".runs/internal",
        ".runs/evaluations",
        ".runs/metrics",
    ):
        (feature_dir / sub).mkdir(parents=True, exist_ok=True)

    spec_file = _OMNI_STATE.resolve_path_under_base(
        feature_dir, args.spec_file, "spec.md"
    )
    wd = str(working_dir)
    tasks_file = _OMNI_STATE.resolve_path_under_base(feature_dir, "", "tasks.md")
    paths = {
        "branch_name": args.branch_name or "",
        "feature_dir": str(feature_dir),
        "spec_file": str(spec_file),
        "tasks_file": str(tasks_file),
        "working_dir": wd,
        "plugin_root": str(plugin_root),
        "repo_root": wd,
        "start_time": args.start_time or "",
        "initialized_at": _utc_now(),
    }
    paths.update(_OMNI_STATE.doc_dir_paths(working_dir, args.doc_dir))
    # KNOWLEDGE_DIR：私域知识库根目录（独立于 DOC_DIR）。缺省 omni-doc；相对路径基于 working_dir。
    # 解析优先级：CLI(--knowledge-dir) > env KNOWLEDGE_DIR（sdd Step1.5 export 的会话变量）> 默认 omni-doc。
    # 仿 FLOW_MODE 的 env 回退：specify init 创建 env.sh时尚无文件可读，故从会话 env 取上游已解析值。
    knowledge_dir_arg = args.knowledge_dir or os.environ.get("KNOWLEDGE_DIR") or None
    paths["knowledge_dir"] = str(
        _OMNI_STATE.resolve_doc_dir(working_dir, knowledge_dir_arg)
    )
    # flow_mode 解析：env FLOW_MODE（上游 prompt/harness 注入）> state > paths > pending > default。
    # 显式读取 env 作为 cli_override，避免上游已决定 standard 却因未落盘而回退默认值。
    env_flow_mode = os.environ.get("FLOW_MODE") or os.environ.get("OMNISPEC_FLOW_MODE")
    flow_mode = _OMNI_STATE.resolve_flow_mode(
        feature_dir, cli_override=env_flow_mode, working_dir=working_dir
    )
    paths["flow_mode"] = flow_mode
    _write_json(feature_dir / ".runs" / "paths.json", paths)

    env_sh = feature_dir / ".runs" / "env.sh"
    env_sh.write_text(
        "\n".join(
            [
                "# Auto-generated by skills/specify/scripts/python/specify_harness.py — source before each step",
                f'export FEATURE_DIR="{feature_dir}"',
                f'export SPEC_FILE="{paths["spec_file"]}"',
                f'export TASKS="{paths["tasks_file"]}"',
                f'export BRANCH_NAME="{paths["branch_name"]}"',
                f'export FLOW_MODE="{flow_mode}"',
                f'export DOC_DIR="{paths["doc_dir"]}"',
                f'export DOC_SPECS_DIR="{paths["doc_specs_dir"]}"',
                f'export DOC_RULES_DIR="{paths["doc_rules_dir"]}"',
                f'export DOC_NAVIGATIONS_DIR="{paths["doc_navigations_dir"]}"',
                f'export DOC_ON_DEMAND_DIR="{paths["doc_on_demand_dir"]}"',
                f'export KNOWLEDGE_DIR="{paths["knowledge_dir"]}"',
                f'export CLAUDE_WORKING_DIR="{wd}"',
                f'export CLAUDE_PLUGIN_ROOT="{plugin_root}"',
                "",
            ]
        ),
        encoding="utf-8",
    )

    run = _load_run(feature_dir)
    run["run_id"] = args.run_id or run.get("run_id") or str(uuid.uuid4())
    run["started_at"] = _utc_now()
    _save_run(feature_dir, run)

    _OMNI_STATE.init_stub_state(feature_dir, flow_mode=flow_mode)
    # 尽早写入活动特性指针，便于 workflow/脚本用 omnispec_state.resolve 命中当前目录，
    # 避免评测重试或外层再次调用 specify 时未透传路径而又 allocate 出第二套 changes/00N-*。
    _OMNI_STATE.write_active_feature(working_dir, feature_dir)

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
            abs_keys = (
                "feature_dir",
                "spec_file",
                "tasks_file",
                "doc_dir",
                "doc_specs_dir",
                "doc_rules_dir",
                "doc_navigations_dir",
                "doc_on_demand_dir",
                "knowledge_dir",
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


def _knowledge_retrieval_errors(feature_dir: Path) -> List[str]:
    """二级钳制：宽松校验 context.payload.json 的 knowledge_retrieval 字段。

    设计为兜底而非强约束来源（强约束在 spec-impact-analyze 的 impact_gate.py）：
      - payload 完全无 knowledge_retrieval 字段 → 不报错（兼容未升级的旧 payload）；
      - 字段存在但「知识源就绪却 executed=false」或 executed=true 时关键字段缺失 → 报错。
    知识源就绪判定：KNOWLEDGE_DIR 解析成功（paths.json > env > working_dir/omni-doc）
      且目录存在且非空且其下 knowledge.config.yaml 存在。
    """
    payload_path = feature_dir / ".runs" / "internal" / "context.payload.json"
    if not payload_path.is_file():
        return []  # specify 自身可能在 context.md 直接 Write 时无 payload，不强制
    try:
        payload = _read_json(payload_path)
    except json.JSONDecodeError:
        return []  # 结构问题交给 spec-impact-gate；specify 不重复报
    kr = payload.get("knowledge_retrieval")
    if kr is None:
        return []  # 宽松：无字段不拦
    if not isinstance(kr, dict):
        return ["context.payload.json: knowledge_retrieval must be an object"]

    # 解析 KNOWLEDGE_DIR 判定是否就绪
    paths = _paths_from_feature(feature_dir)
    kd_raw = (paths.get("knowledge_dir") or os.environ.get("KNOWLEDGE_DIR") or "").strip()
    if not kd_raw:
        wd_raw = (paths.get("working_dir") or "").strip()
        if wd_raw:
            kd_raw = str(Path(wd_raw) / "omni-doc")
    knowledge_dir = Path(kd_raw).expanduser() if kd_raw else None
    source_ready = bool(
        knowledge_dir
        and knowledge_dir.is_dir()
        and any(knowledge_dir.iterdir())
        and (knowledge_dir / "knowledge.config.yaml").is_file()
    )

    errors: List[str] = []
    executed = kr.get("executed")
    if not isinstance(executed, bool):
        errors.append("knowledge_retrieval.executed: must be bool")
    else:
        if source_ready and not executed:
            errors.append(
                "knowledge_retrieval.executed: false while knowledge source ready "
                "(spec-impact-analyze must dispatch knowledge-retrieval-agent)"
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
    return errors


def _gate_step_3(feature_dir: Path, min_bytes: int) -> List[str]:
    errors: List[str] = []
    path = feature_dir / "context.md"
    ok, msg = _file_ok(path, min_bytes)
    if not ok:
        errors.append(f"context.md: {msg}")
        return errors
    text = _read_text(path)
    for heading in CONTEXT_REQUIRED_HEADINGS:
        if heading not in text:
            errors.append(f"context.md: missing section {heading}")
    found = sum(1 for h in CONTEXT_REQUIRED_HEADINGS if h in text)
    if found < len(CONTEXT_REQUIRED_HEADINGS):
        errors.append(f"context.md: sections {found}/{len(CONTEXT_REQUIRED_HEADINGS)}")
    for msg in _template_errors("context.md", path):
        errors.append(msg)
    # 二级钳制：spec-impact-analyze 的 knowledge_retrieval 留痕（宽松校验）
    errors.extend(_knowledge_retrieval_errors(feature_dir))
    return errors


def _gate_step_6(feature_dir: Path, min_bytes: int) -> List[str]:
    errors: List[str] = []
    path = feature_dir / "spec.md"
    ok, msg = _file_ok(path, min_bytes)
    if not ok:
        errors.append(f"spec.md: {msg}")
        return errors
    text = _read_text(path)
    if not re.search(r"^#\s+", text, re.MULTILINE) and "##" not in text:
        errors.append("spec.md: no markdown headings detected")
    for msg in _template_errors("spec.md", path):
        errors.append(msg)
    sources = _contract().get("template_sources", {})
    if errors:
        errors.append(
            "spec.md: fix against templates — "
            + ", ".join(f"{k}={v}" for k, v in sources.items() if k in ("spec", "requirement_metamodel", "scenario_metamodel"))
        )
    return errors


def _gate_step_8(feature_dir: Path, min_bytes: int) -> List[str]:
    errors: List[str] = []
    path = feature_dir / "checklists/requirements.md"
    ok, msg = _file_ok(path, min_bytes)
    if not ok:
        errors.append(f"checklists/requirements.md: {msg}")
        return errors
    text = _read_text(path)
    checks = len(re.findall(r"^- \[[ xX]\]", text, re.MULTILINE))
    if checks < 3:
        errors.append(f"checklists/requirements.md: checkbox items {checks} < 3")
    for msg in _template_errors("checklists/requirements.md", path):
        errors.append(msg)
    return errors


def _gate_step_9(feature_dir: Path, min_bytes: int) -> List[str]:
    errors: List[str] = []
    path = feature_dir / ".runs/evaluations/eval-specify-report.yaml"
    ok, msg = _file_ok(path, min_bytes)
    if not ok:
        errors.append(f"eval-specify-report.yaml: {msg}")
        return errors
    text = _read_text(path)
    for msg in _template_errors(".runs/evaluations/eval-specify-report.yaml", path):
        errors.append(msg if msg.startswith("evaluation") else f"eval-specify-report.yaml: {msg}")
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
        errors.append(f"omni-metrics-log.json: too_small")
    return errors


def _gate_step_11_5(feature_dir: Path, min_bytes: int) -> List[str]:
    del min_bytes  # state gate is structural, not size-based
    if _OMNI_STATE is None:
        data = _paths_from_feature(feature_dir)
        plugin = data.get("plugin_root", "")
        if plugin:
            _load_omnispec_state(Path(plugin))
    if _OMNI_STATE is None:
        return ["omnispec-state: plugin_root not loaded; run finalize or init first"]
    return _OMNI_STATE.gate_state(feature_dir, required_in_completed="specify")


def _gate_all(feature_dir: Path, min_bytes: int) -> List[str]:
    errors: List[str] = []
    for step in GATE_STEPS:
        errors.extend(_gate_step_handlers[step](feature_dir, min_bytes))
    return errors


_gate_step_handlers = {
    "1": _gate_step_1,
    "3": _gate_step_3,
    "6": _gate_step_6,
    "8": _gate_step_8,
    "9": _gate_step_9,
    "11": _gate_step_11,
    "11.5": _gate_step_11_5,
}


def cmd_gate(args: argparse.Namespace) -> int:
    feature_dir = Path(args.feature_dir).resolve()
    min_bytes = args.min_bytes
    step = args.step

    if step == "all":
        errors = _gate_all(feature_dir, min_bytes)
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
        "template_contract": _contract().get("version", "unknown"),
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


def cmd_render_spec(args: argparse.Namespace) -> int:
    """从工作区 .omni-infra/templates/spec-template.md 初始化 spec.md 骨架（不覆盖已有需求/场景章节）。"""
    feature_dir = Path(args.feature_dir).resolve()
    working_dir = _resolve_working_dir(args, feature_dir)
    plugin_root = _resolve_plugin_root(args, feature_dir)
    _load_omnispec_state(plugin_root)
    paths_file = feature_dir / ".runs/paths.json"
    branch_name = args.branch_name or ""
    spec_arg = args.spec_file or ""
    if paths_file.is_file():
        try:
            paths = _read_json(paths_file)
            branch_name = branch_name or paths.get("branch_name", "")
            if not (spec_arg or "").strip():
                spec_arg = paths.get("spec_file", "") or ""
        except json.JSONDecodeError:
            pass

    spec_path = _OMNI_STATE.resolve_path_under_base(feature_dir, spec_arg, "spec.md")
    existing = _read_text(spec_path) if spec_path.is_file() else ""

    if existing and not args.force:
        if has_heading(existing, "成功标准") and has_heading(existing, "需求") and has_heading(existing, "场景"):
            print(
                json.dumps(
                    {"status": "skipped", "reason": "spec.md already has template sections", "output": str(spec_path)},
                    ensure_ascii=False,
                )
            )
            return 0

    skeleton = render_spec_skeleton(
        feature_name=args.feature_name or "未命名功能",
        branch_name=branch_name,
        user_input=args.user_intent or "",
        working_dir=working_dir,
    )

    if not existing or args.force:
        out = skeleton
    elif args.merge:
        blocks: List[str] = [existing.rstrip(), ""]
        for title in ("成功标准", "与既有架构对齐", "关键实体"):
            if not has_heading(existing, title):
                body = section_body(skeleton, title)
                if body:
                    blocks.append(f"## {title}\n\n{body}")
        out = "\n".join(blocks).rstrip() + "\n"
    else:
        out = existing.rstrip() + "\n\n" + skeleton

    spec_path.parent.mkdir(parents=True, exist_ok=True)
    spec_path.write_text(out, encoding="utf-8")
    print(json.dumps({"status": "ok", "output": str(spec_path)}, ensure_ascii=False))
    return 0


def cmd_render_checklist(args: argparse.Namespace) -> int:
    """从工作区 requirements-template.md 生成 checklists/requirements.md 骨架。"""
    feature_dir = Path(args.feature_dir).resolve()
    working_dir = _resolve_working_dir(args, feature_dir)
    out_path = feature_dir / "checklists" / "requirements.md"
    if out_path.is_file() and not args.force:
        text = _read_text(out_path)
        if has_heading(text, "内容质量") and len(re.findall(r"^- \[[ xX]\]", text, re.MULTILINE)) >= 12:
            print(
                json.dumps(
                    {"status": "skipped", "reason": "checklist already from template", "output": str(out_path)},
                    ensure_ascii=False,
                )
            )
            return 0

    out_path.parent.mkdir(parents=True, exist_ok=True)
    content = render_requirements_checklist_skeleton(
        feature_name=args.feature_name or "未命名功能",
        spec_rel_link=args.spec_link or "../spec.md",
        working_dir=working_dir,
    )
    out_path.write_text(content, encoding="utf-8")
    print(json.dumps({"status": "ok", "output": str(out_path)}, ensure_ascii=False))
    return 0


def cmd_render_context(args: argparse.Namespace) -> int:
    """从 internal/context.payload.json 渲染 context.md（降级/最小模板）。"""
    feature_dir = Path(args.feature_dir).resolve()
    payload_path = feature_dir / ".runs/internal/context.payload.json"
    out_path = feature_dir / "context.md"

    if payload_path.is_file():
        try:
            payload = _read_json(payload_path)
        except json.JSONDecodeError:
            payload = {"error": "invalid context.payload.json"}
    else:
        payload = {
            "context_mode": "default",
            "degraded": True,
            "reason": "context.payload.json missing",
            "user_intent": args.user_intent or "",
        }

    mode = payload.get("context_mode", "default")
    intent = payload.get("user_intent") or payload.get("feature_description") or ""
    degraded = payload.get("degraded", False)
    reason = payload.get("reason", payload.get("error", ""))

    def section(title: str, body: Any) -> str:
        if isinstance(body, dict):
            body = json.dumps(body, ensure_ascii=False, indent=2)
        elif isinstance(body, list):
            body = "\n".join(f"- {x}" for x in body) if body else "（未识别到相关内容）"
        text = str(body).strip() if body else "（未识别到相关内容）"
        return f"## {title}\n\n{text}\n"

    parts = [
        "# 上下文: specify harness 渲染\n",
        f"**context_mode**: `{mode}`",
        f"**渲染时间**: {_utc_now()}",
    ]
    if degraded:
        parts.append(f"**降级**: 是 — {reason}")
    parts.append("")
    parts.append(section("功能描述", intent or payload.get("sections", {}).get("功能描述", "（未识别到相关内容）")))

    rev_docs = payload.get("sections", {}).get("相关反构文档") or payload.get("related_docs", "（未识别到相关内容）")
    parts.append(section("相关反构文档", rev_docs))

    arch = payload.get("sections", {}).get("架构分析与设计参考") or payload.get("architecture_analysis", "（未识别到相关内容）")
    parts.append(section("架构分析与设计参考", arch))

    terms = payload.get("sections", {}).get("术语对齐") or payload.get("terminology", "（未识别到相关内容）")
    parts.append(section("术语对齐", terms))

    constraints = payload.get("sections", {}).get("约束和假设") or payload.get("constraints", "（未识别到相关内容）")
    parts.append(section("约束和假设", constraints))

    out_path.write_text("\n".join(parts) + "\n", encoding="utf-8")
    print(json.dumps({"status": "ok", "output": str(out_path)}, ensure_ascii=False))
    return 0


def cmd_finalize(args: argparse.Namespace) -> int:
    """更新 .runs/.omnispec-state.json，将 specify 记入 completed_stages。"""
    feature_dir = Path(args.feature_dir).resolve()
    plugin_root = _resolve_plugin_root(args, feature_dir)
    working_dir = _resolve_working_dir(args, feature_dir)
    _load_omnispec_state(plugin_root)
    cli_fm = (args.flow_mode or "").strip()
    flow_mode = _OMNI_STATE.resolve_flow_mode(
        feature_dir,
        cli_override=cli_fm or None,
        working_dir=working_dir,
    )
    next_stage = (args.next_stage or "").strip()
    if not next_stage:
        next_stage = "design" if flow_mode == "express" else "clarify"
    state = _OMNI_STATE.update_state(
        feature_dir,
        current_stage=next_stage,
        mark_complete=["specify"],
        flow_mode=flow_mode,
        arguments=args.arguments or None,
    )
    _OMNI_STATE.consume_pending_workflow(working_dir)
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


def cmd_resume(args: argparse.Namespace) -> int:
    """列出尚未 passed 的步骤，供断点续跑。"""
    feature_dir = Path(args.feature_dir).resolve()
    run = _load_run(feature_dir)
    pending = []
    for step in GATE_STEPS:
        info = run.get("steps", {}).get(step, {})
        if info.get("status") != "passed" or info.get("gate_exit", 1) != 0:
            pending.append(step)
    print(json.dumps({"pending_steps": pending, "run_id": run.get("run_id")}, ensure_ascii=False))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="specify harness")
    sub = parser.add_subparsers(dest="command")

    p_init = sub.add_parser("init", help="初始化 harness 目录与 paths/env/run")
    p_init.add_argument("--plugin-root", required=True)
    p_init.add_argument("--working-dir", required=True)
    p_init.add_argument("--feature-dir", required=True)
    p_init.add_argument("--branch-name", default="")
    p_init.add_argument("--spec-file", default="")
    p_init.add_argument("--doc-dir", default="omni-doc")
    p_init.add_argument("--knowledge-dir", default="",
                        help="私域知识库根目录（缺省同 doc-dir/omni-doc；相对路径基于 working-dir）")
    p_init.add_argument("--repo-root", default="", help=argparse.SUPPRESS)
    p_init.add_argument("--start-time", default="")
    p_init.add_argument("--run-id", default="")

    p_gate = sub.add_parser("gate", help="分步或全量结构门禁")
    p_gate.add_argument("--feature-dir", required=True)
    p_gate.add_argument("--step", required=True, choices=[*GATE_STEPS, "all"])
    p_gate.add_argument("--min-bytes", type=int, default=MIN_BYTES_DEFAULT)
    p_gate.add_argument("--record", action="store_true", help="将结果写入 specify-run.json")
    p_gate.add_argument("--retries", type=int, default=0)

    p_rec = sub.add_parser("record", help="手动记录步骤状态")
    p_rec.add_argument("--feature-dir", required=True)
    p_rec.add_argument("--step", required=True)
    p_rec.add_argument("--status", required=True, choices=["passed", "failed", "skipped"])
    p_rec.add_argument("--gate-exit", type=int, required=True)
    p_rec.add_argument("--retries", type=int, default=0)
    p_rec.add_argument("--notes", default="")

    p_render = sub.add_parser("render-context", help="从 payload JSON 渲染 context.md")
    p_render.add_argument("--feature-dir", required=True)
    p_render.add_argument("--user-intent", default="")

    p_rspec = sub.add_parser("render-spec", help="从 spec-template.md 初始化/补齐 spec.md 骨架")
    p_rspec.add_argument("--feature-dir", required=True)
    p_rspec.add_argument("--working-dir", default="")
    p_rspec.add_argument("--spec-file", default="")
    p_rspec.add_argument("--branch-name", default="")
    p_rspec.add_argument("--feature-name", default="")
    p_rspec.add_argument("--user-intent", default="")
    p_rspec.add_argument("--merge", action="store_true", help="仅补齐缺失章节，不覆盖已有内容")
    p_rspec.add_argument("--force", action="store_true")

    p_rchk = sub.add_parser("render-checklist", help="从 requirements-template.md 生成检查清单")
    p_rchk.add_argument("--feature-dir", required=True)
    p_rchk.add_argument("--working-dir", default="")
    p_rchk.add_argument("--feature-name", default="")
    p_rchk.add_argument("--spec-link", default="../spec.md")
    p_rchk.add_argument("--force", action="store_true")

    p_fin = sub.add_parser("finalize", help="写入 omnispec-state completed_stages")
    p_fin.add_argument("--feature-dir", required=True)
    p_fin.add_argument("--plugin-root", default="")
    p_fin.add_argument("--working-dir", default="")
    p_fin.add_argument("--flow-mode", default="")
    p_fin.add_argument("--next-stage", default="")
    p_fin.add_argument("--arguments", default="")

    p_res = sub.add_parser("resume", help="查询待重跑步骤")
    p_res.add_argument("--feature-dir", required=True)

    args = parser.parse_args()
    if not getattr(args, "command", None):
        parser.error("command is required")
    handlers = {
        "init": cmd_init,
        "gate": cmd_gate,
        "record": cmd_record,
        "render-context": cmd_render_context,
        "render-spec": cmd_render_spec,
        "render-checklist": cmd_render_checklist,
        "finalize": cmd_finalize,
        "resume": cmd_resume,
    }
    return handlers[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
