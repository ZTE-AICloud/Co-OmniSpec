#!/usr/bin/env python3
"""spec-impact-analyze 阶段 Harness：私域知识检索门禁。

强约束目标：在私域知识源就绪时，确保 knowledge-retrieval-agent 真正被派发，
并把派发结论（executed / hits / config_hit / vector_built / graph_built / mode / skip_reason）
写入 context.payload.json 的 knowledge_retrieval 字段，供：
  - 本技能一级门禁（gate --step kr）机器校验；
  - specify _gate_step_3 二级钳制（payload 字段写得不合规时报错）。

设计对标 specify_harness.py / design_harness.py（bash 薄封装 → python 内核），
但本技能目前只有一个门禁步骤（kr = knowledge-retrieval），不引入 run manifest 全量状态机，
仅做最小留痕：--record 时把门禁结论追加到 spec-impact-run.json 的 gates[]。
"""

import argparse
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# 私域知识检索配置模板（init_omni_infra.sh 的 prepare_knowledge_config 同源）
_KNOWLEDGE_CONFIG_TEMPLATE_REL = "skills/knowledge-retrieval/knowledge.config.yaml"
_KNOWLEDGE_CONFIG_NAME = "knowledge.config.yaml"

# knowledge_retrieval 字段完整 schema（与 SKILL.md Step 5/6 第 7 节一致）
KR_FIELDS = ("executed", "hits", "config_hit", "vector_built", "graph_built", "mode", "skip_reason")
KR_VALID_MODES = ("enhance", "baseline")


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _resolve_plugin_root(feature_dir: Path) -> Optional[Path]:
    """从 paths.json / env.sh / 仓库内嵌插件根定位 CLAUDE_PLUGIN_ROOT。"""
    for candidate in (feature_dir / ".runs" / "paths.json",):
        if candidate.is_file():
            try:
                pr = (_read_json(candidate).get("plugin_root") or "").strip()
                if pr and Path(pr).is_dir():
                    return Path(pr)
            except json.JSONDecodeError:
                pass
    # 仓库内嵌：scripts/python/impact_gate.py → parents[4] = omni-dsdd 插件根
    embedded = Path(__file__).resolve().parents[4]
    if (embedded / "skills" / "spec-impact-analyze" / "SKILL.md").is_file():
        return embedded
    # env 注入
    pr = (os.environ.get("CLAUDE_PLUGIN_ROOT") or "").strip()
    if pr and Path(pr).is_dir():
        return Path(pr)
    return None


def _resolve_knowledge_dir(args: argparse.Namespace, feature_dir: Path, plugin_root: Optional[Path]) -> Optional[Path]:
    """解析 KNOWLEDGE_DIR：CLI > env > paths.json > working_dir/omni-doc。"""
    # 1. CLI 显式
    if (args.knowledge_dir or "").strip():
        return Path(args.knowledge_dir).expanduser().resolve()
    # 2. env
    env_kd = (os.environ.get("KNOWLEDGE_DIR") or "").strip()
    if env_kd:
        return Path(env_kd).expanduser().resolve()
    # 3. paths.json（specify init 已写入绝对路径）
    paths_file = feature_dir / ".runs" / "paths.json"
    if paths_file.is_file():
        try:
            kd = (_read_json(paths_file).get("knowledge_dir") or "").strip()
            if kd:
                return Path(kd).resolve()
        except json.JSONDecodeError:
            pass
    # 4. 默认 working_dir/omni-doc
    wd = ""
    if paths_file.is_file():
        try:
            wd = (_read_json(paths_file).get("working_dir") or "").strip()
        except json.JSONDecodeError:
            pass
    wd = wd or (os.environ.get("CLAUDE_WORKING_DIR") or "").strip()
    if not wd:
        return None
    return (Path(wd) / "omni-doc").resolve()


def _resolve_payload_path(args: argparse.Namespace, feature_dir: Path) -> Path:
    if (args.payload or "").strip():
        return Path(args.payload).expanduser().resolve()
    return feature_dir / ".runs" / "internal" / "context.payload.json"


def _is_empty_dir(path: Path) -> bool:
    if not path.is_dir():
        return True
    return not any(path.iterdir())


def _self_heal_config(knowledge_dir: Path, plugin_root: Path) -> Tuple[bool, str]:
    """config 缺失时从插件模板拷贝并把 raw_knowledge_dir 设为 . （对齐 init_omni_infra.sh）。

    返回 (是否自愈, 说明)。
    """
    target = knowledge_dir / _KNOWLEDGE_CONFIG_NAME
    if target.is_file():
        return False, "already_exists"
    source = plugin_root / _KNOWLEDGE_CONFIG_TEMPLATE_REL
    if not source.is_file():
        return False, f"template_missing:{source}"
    knowledge_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    # raw_knowledge_dir 设为 . （相对 config 解析为知识库目录自身），幂等
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


def _check_knowledge_source(knowledge_dir: Optional[Path], plugin_root: Optional[Path]) -> Dict[str, Any]:
    """机器闸门 + 就地自愈。返回判定结构。

    状态：
      ready       — 目录存在且 config 存在（或自愈后），必须派发检索
      self_healed — 目录存在但 config 缺失，已就地自愈，必须派发检索
      skip        — 目录不存在或为空，唯一合法跳过路径
    """
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
    result["config_path"] = str(knowledge_dir / _KNOWLEDGE_CONFIG_NAME)
    if not knowledge_dir.exists() or _is_empty_dir(knowledge_dir):
        result["skip_reason"] = f"dir_missing_or_empty:{knowledge_dir}"
        return result
    # 目录存在 → 检查 config
    config_path = knowledge_dir / _KNOWLEDGE_CONFIG_NAME
    if config_path.is_file():
        result["status"] = "ready"
        return result
    # config 缺失 → 就地自愈
    if plugin_root is None:
        result["status"] = "self_heal_failed"
        result["skip_reason"] = "config_missing_and_plugin_root_unresolved"
        return result
    healed, note = _self_heal_config(knowledge_dir, plugin_root)
    if healed:
        result["status"] = "self_healed"
        result["self_healed"] = True
        result["config_path"] = str(config_path)
        return result
    # 自愈失败（模板缺失等）→ 降级为 skip 但记明原因（非合法跳过，属于降级）
    result["skip_reason"] = f"self_heal_failed:{note}"
    return result


def _check_payload(payload_path: Path, source: Dict[str, Any]) -> Tuple[List[str], Optional[Dict[str, Any]]]:
    """校验 context.payload.json 的 knowledge_retrieval 字段。

    返回 (errors, kr_dict_or_none)。
    """
    errors: List[str] = []
    source_status = source.get("status", "skip")
    must_dispatch = source_status in ("ready", "self_healed")
    if not payload_path.is_file():
        # payload 缺失：仅当知识源就绪（必须派发）时报错；合法跳过时 payload 可选
        if must_dispatch:
            errors.append(f"context.payload.json: missing ({payload_path})")
        return errors, None
    try:
        payload = _read_json(payload_path)
    except json.JSONDecodeError:
        errors.append("context.payload.json: invalid JSON")
        return errors, None

    kr = payload.get("knowledge_retrieval")

    if kr is None:
        if must_dispatch:
            errors.append(
                "knowledge_retrieval: missing in payload while knowledge source ready "
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

    # executed=true 时其余字段必须齐备且类型正确（区分真零结果 vs 中途降级）
    if executed is True:
        hits = kr.get("hits")
        if not isinstance(hits, int) or hits < 0:
            errors.append("knowledge_retrieval.hits: must be non-negative int")
        for key in ("config_hit", "vector_built", "graph_built"):
            if not isinstance(kr.get(key), bool):
                errors.append(f"knowledge_retrieval.{key}: must be bool")
        mode = kr.get("mode")
        if mode not in KR_VALID_MODES:
            errors.append(f"knowledge_retrieval.mode: must be one of {KR_VALID_MODES}")

    return errors, kr


def cmd_gate(args: argparse.Namespace) -> int:
    feature_dir = Path(args.feature_dir).resolve()
    plugin_root = _resolve_plugin_root(feature_dir)
    knowledge_dir = _resolve_knowledge_dir(args, feature_dir, plugin_root)
    payload_path = _resolve_payload_path(args, feature_dir)

    errors: List[str] = []
    source = _check_knowledge_source(knowledge_dir, plugin_root)

    # 自愈失败属于异常降级，记为 error（非合法 skip）
    if source["status"] == "self_heal_failed":
        errors.append(f"knowledge_source: self_heal_failed — {source['skip_reason']}")

    payload_errors, kr = _check_payload(payload_path, source)
    errors.extend(payload_errors)

    gate_exit = 0 if not errors else 1
    result: Dict[str, Any] = {
        "feature_dir": str(feature_dir),
        "step": "kr",
        "knowledge_source": {
            "status": source["status"],
            "knowledge_dir": source["knowledge_dir"],
            "config_path": source["config_path"],
            "self_healed": source["self_healed"],
            "skip_reason": source["skip_reason"],
        },
        "payload": str(payload_path),
        "knowledge_retrieval": kr,
        "gate_exit": gate_exit,
        "errors": errors,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if args.record:
        run_path = feature_dir / ".runs" / "spec-impact-run.json"
        run: Dict[str, Any]
        if run_path.is_file():
            try:
                run = _read_json(run_path)
            except json.JSONDecodeError:
                run = {"stage": "spec-impact-analyze", "gates": []}
        else:
            run = {"stage": "spec-impact-analyze", "gates": []}
        run.setdefault("gates", []).append(
            {
                "step": "kr",
                "gate_exit": gate_exit,
                "status": "passed" if gate_exit == 0 else "failed",
                "knowledge_source_status": source["status"],
                "self_healed": source["self_healed"],
                "executed": kr.get("executed") if isinstance(kr, dict) else None,
                "hits": kr.get("hits") if isinstance(kr, dict) else None,
                "errors": errors,
                "updated_at": _utc_now(),
            }
        )
        run["last_updated"] = _utc_now()
        _write_json(run_path, run)

    return gate_exit


def main() -> int:
    parser = argparse.ArgumentParser(description="spec-impact-analyze knowledge-retrieval gate")
    sub = parser.add_subparsers(dest="command")

    p_gate = sub.add_parser("gate", help="私域知识检索门禁（payload knowledge_retrieval 字段 + 知识源就绪）")
    p_gate.add_argument("--feature-dir", required=True)
    p_gate.add_argument("--knowledge-dir", default="", help="私域知识库根目录（缺省从 env/paths.json 解析）")
    p_gate.add_argument("--payload", default="", help="context.payload.json 路径（缺省 FEATURE_DIR/.runs/internal/）")
    p_gate.add_argument("--record", action="store_true", help="把门禁结论写入 spec-impact-run.json")

    args = parser.parse_args()
    if not getattr(args, "command", None):
        parser.error("command is required")
    handlers = {"gate": cmd_gate}
    return handlers[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
