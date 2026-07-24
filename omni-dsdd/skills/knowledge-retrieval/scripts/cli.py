import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Optional

from .knowledge_base import KnowledgeBase
from . import api


def _emit(obj, pretty: bool) -> None:
    if pretty:
        print(json.dumps(obj, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(obj, ensure_ascii=False))


def _find_config(args) -> Path:
    """级联查找：--config（显式，最高优先级）> KNOWLEDGE_CONFIG > 从 CWD 逐级向上。"""
    import os

    # 1. 显式 --config，确定性最强，优先级最高
    if args.config:
        p = Path(args.config).expanduser().resolve()
        if p.is_file():
            return p
        print(f"--config 指定的文件不存在: {p}", file=sys.stderr)
        sys.exit(2)

    # 2. 环境变量（适合 skill 注入）
    env_path = os.environ.get("KNOWLEDGE_CONFIG")
    if env_path:
        p = Path(env_path).expanduser().resolve()
        if p.is_file():
            return p
        print(f"KNOWLEDGE_CONFIG 指定的文件不存在: {p}", file=sys.stderr)
        sys.exit(2)

    # 3. 从 CWD 逐级向上查找
    cwd = Path.cwd()
    for d in [cwd, *cwd.parents]:
        candidate = d / "knowledge.config.yaml"
        if candidate.is_file():
            return candidate

    print("knowledge.config.yaml not found. Options:", file=sys.stderr)
    print("  1. 在项目目录（或其上级）放置 knowledge.config.yaml", file=sys.stderr)
    print("  2. export KNOWLEDGE_CONFIG=/path/to/config.yaml", file=sys.stderr)
    print("  3. --config /path/to/config.yaml", file=sys.stderr)
    print(f"  当前 CWD={cwd}", file=sys.stderr)
    sys.exit(2)

def _load_kb(args) -> KnowledgeBase:
    cfg = _find_config(args)
    args.resolved_config = cfg          # 关键：保留真实路径
    return KnowledgeBase.from_config_file(cfg)


def _graphify_graph_file() -> Path:
    """图谱产物固定约定：CWD 下的 ./graphify-out/graph.json（由 graphify 构建）。
    与 config 解耦——不再从 config 读取 graph_path；存在性即就绪判据。"""
    return Path.cwd() / "graphify-out" / "graph.json"


# ── kb-config：管理宿主 shell 配置文件中的持久化 KNOWLEDGE_DIR ──
# 不依赖 config.yaml / KB 产物；只增删改 shell 配置里的一行 export，绝不整体重写。
_MANAGED_SUFFIX = "  # managed by omni-dsdd knowledge-retrieval (kb-config)"
_KB_LINE_RE = re.compile(r'^\s*(?:export\s+)?KNOWLEDGE_DIR\s*=\s*(.*)$')


def _detect_shell_file(explicit: Optional[str]) -> Path:
    """默认探测顺序：显式 --shell-file > $BASH_RC > ~/.bashrc。"""
    if explicit:
        return Path(explicit).expanduser()
    env_rc = os.environ.get("BASH_RC")
    if env_rc:
        return Path(env_rc).expanduser()
    return Path.home() / ".bashrc"


def _resolve_kb_path(raw: str) -> str:
    """相对路径转绝对路径（~/.bashrc 是跨项目全局的，相对路径无意义）。"""
    p = Path(raw).expanduser()
    if not p.is_absolute():
        p = (Path.cwd() / p).resolve()
    return str(p)


def _read_lines(shell_file: Path) -> list:
    return shell_file.read_text(encoding="utf-8").splitlines() if shell_file.is_file() else []


def kb_config_set(shell_file: Path, raw_path: str) -> dict:
    abs_path = _resolve_kb_path(raw_path)
    new_line = 'export KNOWLEDGE_DIR="{}"{}'.format(abs_path, _MANAGED_SUFFIX)
    lines = _read_lines(shell_file)
    action = "appended"
    for i, line in enumerate(lines):
        if _KB_LINE_RE.match(line):
            lines[i] = new_line
            action = "updated"
            break
    else:
        if lines and lines[-1].strip():
            lines.append("")
        lines.append(new_line)
    shell_file.parent.mkdir(parents=True, exist_ok=True)
    shell_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {
        "action": action,
        "shell_file": str(shell_file),
        "knowledge_dir": abs_path,
        "hint": "新开终端，或执行 source {} 后生效".format(shell_file),
    }


def kb_config_unset(shell_file: Path) -> dict:
    lines = _read_lines(shell_file)
    before = len(lines)
    lines = [l for l in lines if not _KB_LINE_RE.match(l)]
    removed = before - len(lines)
    if removed:
        shell_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {
        "action": "removed" if removed else "noop",
        "shell_file": str(shell_file),
        "removed_lines": removed,
    }


def kb_config_show(shell_file: Path) -> dict:
    persisted = None
    for line in _read_lines(shell_file):
        m = _KB_LINE_RE.match(line)
        if m:
            val = m.group(1).strip()
            # set 写入形如: KNOWLEDGE_DIR="/path"  # managed by ...
            # 精确剥离本工具写入的 managed 后缀，再剥引号（不误切路径中可能的 #）
            if val.endswith(_MANAGED_SUFFIX.strip()):
                val = val[: -len(_MANAGED_SUFFIX.strip())].strip()
            persisted = val.strip().strip('"').strip("'") or None
            break
    effective = os.environ.get("KNOWLEDGE_DIR")
    return {
        "shell_file": str(shell_file),
        "shell_file_exists": shell_file.is_file(),
        "persisted_knowledge_dir": persisted,
        "effective_knowledge_dir": effective or "(unset, 将走默认 omni-doc)",
        "priority": "CLI --knowledge-dir > KNOWLEDGE_DIR env(~/.bashrc) > 默认 omni-doc",
        "consistent": persisted is not None and persisted == effective,
    }


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="kb")
    p.add_argument("--config", default=None, help="配置文件路径（默认级联查找：环境变量 → --config → ./knowledge.config.yaml）")
    p.add_argument("--pretty", action="store_true")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list-entity-types")

    sp = sub.add_parser("describe-entity-type")
    sp.add_argument("type_id")

    sp = sub.add_parser("list-instances")
    sp.add_argument("type_id")
    sp.add_argument("--filter", default=None)

    sp = sub.add_parser("get-instance")
    sp.add_argument("instance_id")
    sp.add_argument("--attributes", nargs="*", default=None)

    sp = sub.add_parser("get-attribute")
    sp.add_argument("instance_id")
    sp.add_argument("attribute_name")

    sp = sub.add_parser("vector-search")
    sp.add_argument("query")
    sp.add_argument("--type-ids", nargs="*", default=None)
    sp.add_argument("--attributes", nargs="*", default=None)
    sp.add_argument("--top-k", type=int, default=None)
    sp.add_argument("--min-score", type=float, default=None)

    sub.add_parser("list-searchable-attributes")

    sp = sub.add_parser("build-vector-index")
    sp.add_argument("--force", action="store_true")

    sp = sub.add_parser("fuzzy-search")
    sp.add_argument("query")
    sp.add_argument("--type-ids", nargs="*", default=None)
    sp.add_argument("--top-k", type=int, default=10)

    sub.add_parser("stats")
    sub.add_parser("validate")
    sub.add_parser("config-info")
    
    sub.add_parser("list-documents")

    sp = sub.add_parser("kb-config", help="管理持久化 KNOWLEDGE_DIR（写入/查看/删除 shell 配置）")
    kbsp = sp.add_subparsers(dest="kb_cmd", required=True)
    setp = kbsp.add_parser("set", help="设置/修改持久化 KNOWLEDGE_DIR（自动转绝对路径）")
    setp.add_argument("path")
    setp.add_argument("--shell-file", default=None)
    showp = kbsp.add_parser("show", help="查看持久化值与当前生效值")
    showp.add_argument("--shell-file", default=None)
    unsetp = kbsp.add_parser("unset", help="从 shell 配置删除持久化 KNOWLEDGE_DIR")
    unsetp.add_argument("--shell-file", default=None)

    args = p.parse_args(argv)


    # kb-config 与 config-info 一样是轻量自检：只操作 shell 配置不加载 KB
    if args.cmd == "kb-config":
        shell_file = _detect_shell_file(args.shell_file)
        if args.kb_cmd == "set":
            _emit(kb_config_set(shell_file, args.path), args.pretty)
        elif args.kb_cmd == "show":
            _emit(kb_config_show(shell_file), args.pretty)
        elif args.kb_cmd == "unset":
            _emit(kb_config_unset(shell_file), args.pretty)
        return 0

    # config-info 是轻量自检：只解析配置路径，不加载整个 KB
    if args.cmd == "config-info":
        cfg = _find_config(args)               # 只做路径查找，不构建 KB
        import yaml
        cfg_data = yaml.safe_load(cfg.read_text(encoding="utf-8")) or {}
        km = cfg_data.get("knowledge_model", {}) or {}
        mode = "enhance" if km.get("enabled", False) else "baseline"
        retrievers = cfg_data.get("retrievers", {})
        vec_cfg = retrievers.get("vector") or {}
        vec_enabled = vec_cfg.get("enabled", False)
        graph_cfg = retrievers.get("graph") or {}
        graph_enabled = graph_cfg.get("enabled", False)
        graph_file = _graphify_graph_file()     # 固定 ./graphify-out/graph.json
        cache_dir = Path(cfg_data.get("cache_dir", ".knowledge-cache"))
        vec_matrix = cfg.parent / cache_dir / "vectors" / "matrix.npy"
        _emit({
            "config_path": str(cfg),
            "config_dir": str(cfg.parent),
            "cwd": str(Path.cwd()),
            "mode": mode,                                  # 路由总开关
            "raw_knowledge_dir": cfg_data.get("raw_knowledge_dir"),
            "vector_enabled": vec_enabled,
            "vector_index_exists": vec_matrix.is_file(),   # 索引产物就绪判据
            "graph_enabled": graph_enabled,
            "graph_path": str(graph_file),
            "graph_exists": graph_file.is_file(),
        }, args.pretty)
        return 0

    kb = _load_kb(args)
    
    # 模式门控：typed 原语仅 enhance，文档枚举仅 baseline
    ENHANCE_ONLY = {
        "list-entity-types", "describe-entity-type", "list-instances",
        "get-instance", "get-attribute", "list-searchable-attributes", "traverse",
        "validate", "stats"
    }
    BASELINE_ONLY = {"list-documents"}
    if kb.mode == "baseline" and args.cmd in ENHANCE_ONLY:
        _emit({
            "error": "unavailable_in_baseline_mode",
            "message": f"{args.cmd} 仅在 enhance 模式可用（需知识模型）。"
                       f"baseline 请用 vector-search / list-documents / fuzzy-search / /graphify query。",
        }, args.pretty)
        return 0
    if kb.mode == "enhance" and args.cmd in BASELINE_ONLY:
        _emit({
            "error": "unavailable_in_enhance_mode",
            "message": f"{args.cmd} 仅在 baseline 模式可用；enhance 请用 list-instances。",
        }, args.pretty)
        return 0
    
    if args.cmd == "list-entity-types":
        _emit(api.list_entity_types(kb), args.pretty)
    elif args.cmd == "describe-entity-type":
        _emit(api.describe_entity_type(kb, args.type_id), args.pretty)
    elif args.cmd == "list-instances":
        flt = json.loads(args.filter) if args.filter else None
        _emit(api.list_instances(kb, args.type_id, flt), args.pretty)
    elif args.cmd == "get-instance":
        _emit(api.get_instance(kb, args.instance_id, args.attributes), args.pretty)
    elif args.cmd == "get-attribute":
        _emit(api.get_attribute(kb, args.instance_id, args.attribute_name), args.pretty)
    elif args.cmd == "vector-search":
        _emit(
            api.vector_search(
                kb,
                query=args.query,
                type_ids=args.type_ids,
                attributes=args.attributes,
                top_k=args.top_k,
                min_score=args.min_score,
            ),
            args.pretty,
        )
    elif args.cmd == "list-searchable-attributes":
        _emit(api.list_searchable_attributes(kb), args.pretty)
    elif args.cmd == "fuzzy-search":
        _emit(
            api.fuzzy_search(
                kb,
                query=args.query,
                type_ids=args.type_ids,
                top_k=args.top_k,
            ),
            args.pretty,
        )
    elif args.cmd == "list-documents":
        _emit(api.list_documents(kb), args.pretty)
    
    elif args.cmd == "build-vector-index":
        if kb.vector is None:
            _emit({"error": "vector retriever disabled"}, args.pretty)
        else:
            _emit(kb.vector.build_index(force=args.force), args.pretty)
    elif args.cmd == "stats":
        _emit(
            {
                "type_counts": kb.metadata.type_counts(),
                "instances_with_warnings": [
                    {
                        "id": d.id,
                        "warnings": d.warnings,
                        "missing": d.missing_attributes,
                    }
                    for d in kb.instances
                    if d.warnings or d.missing_attributes
                ],
                "vector_enabled": kb.vector is not None,
            },
            args.pretty,
        )
    elif args.cmd == "validate":
        _emit(
            {
                "unknown_sections": [
                    {"id": d.id, "unknown": list(d.unknown_sections.keys())}
                    for d in kb.instances
                    if d.unknown_sections
                ],
                "missing_required": [
                    {"id": d.id, "missing": d.missing_attributes}
                    for d in kb.instances
                    if d.missing_attributes
                ],
                "instance_warnings": [
                    {"id": d.id, "warnings": d.warnings}
                    for d in kb.instances
                    if d.warnings
                ],
            },
            args.pretty,
        )
    else:
        p.error(f"unknown cmd: {args.cmd}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
