#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实体关系构建工具

基于实体溯源映射和已有关系文件，构建：
- 接口 → 实体 关系（interface-to-entity）
- 实体 → 接口 关系（entity-to-interface）
- 功能 → 实体 关系（function-to-entity）

兼容 Windows 和 Linux。

示例用法：
    # 接口 → 实体
    python entity_relationship_builder.py \
        --repo-root <repo_root> \
        --relation-type interface-to-entity \
        --entity-lineage <entity_lineage_file> \
        --interfaces-dir <interfaces_dir> \
        --output <output_file>

    # 实体 → 接口
    python entity_relationship_builder.py \
        --repo-root <repo_root> \
        --relation-type entity-to-interface \
        --entity-lineage <entity_lineage_file> \
        --output <output_file>

    # 功能 → 实体
    python entity_relationship_builder.py \
        --repo-root <repo_root> \
        --relation-type function-to-entity \
        --function-interface-relations <function_interface_file> \
        --interface-entity-relations <interface_entity_file> \
        --output <output_file>
"""

import argparse
import json
import logging
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Any


logger = logging.getLogger(__name__)


def load_entity_lineage(lineage_file: Path) -> Dict[str, Any]:
    """加载实体溯源映射数据"""
    if not lineage_file.exists():
        raise FileNotFoundError(f"未找到实体溯源映射文件: {lineage_file}")

    with lineage_file.open("r", encoding="utf-8") as f:
        data = json.load(f)

    # 支持两种格式：
    # 1) 旧格式：{ "ENTITY-001": {...}, ... }
    # 2) 新格式：{ "version": "...", "entities": [ {...}, ... ] }
    if isinstance(data, dict) and "entities" in data:
        entities = data.get("entities") or []
        lineage: Dict[str, Dict[str, Any]] = {}
        for item in entities:
            entity_id = item.get("entity_id") or item.get("entity_file_id")
            if not entity_id:
                continue
            lineage[entity_id] = item
        logger.info("读取实体溯源记录: %d 条 (entities 数组格式)", len(lineage))
        return lineage

    logger.info("读取实体溯源记录: %d 条 (字典映射格式)", len(data))
    return data


def load_interface_ids(interfaces_dir: Path) -> List[str]:
    """
    从接口文档目录中提取接口ID列表（可选，用于校验和补全接口清单）

    支持格式：在 Markdown 中出现 `# 接口ID: API-001`
    """
    if not interfaces_dir.exists():
        logger.warning("接口目录不存在: %s", interfaces_dir)
        return []

    interface_ids = set()
    pattern = re.compile(r"#\s*接口ID:\s*(API-\d+)", re.IGNORECASE)

    for md_file in interfaces_dir.glob("API_*.md"):
        try:
            content = md_file.read_text(encoding="utf-8")
            match = pattern.search(content)
            if match:
                interface_ids.add(match.group(1).upper())
        except Exception as exc:  # noqa: BLE001
            logger.error("读取接口文件失败 %s: %s", md_file, exc)

    sorted_ids = sorted(interface_ids)
    logger.info("发现 %d 个接口文档", len(sorted_ids))
    return sorted_ids


def build_interface_to_entity(entity_lineage: Dict[str, Dict[str, Any]]) -> Dict[str, List[str]]:
    """从实体溯源数据构建 接口 → 实体 映射"""
    relations: Dict[str, List[str]] = defaultdict(list)

    for entity_id, meta in entity_lineage.items():
        # 支持两种字段名：source_interfaces 或 interfaces
        interfaces = meta.get("source_interfaces") or meta.get("interfaces") or []
        for api_id in interfaces:
            if not api_id:
                continue
            relations[api_id.upper().strip()].append(entity_id)

    # 去重并排序
    for api_id, entity_ids in relations.items():
        relations[api_id] = sorted(set(entity_ids))

    return relations


def build_entity_to_interface(entity_lineage: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """从实体溯源数据构建 实体 → 接口 关系列表"""
    result: List[Dict[str, Any]] = []

    for entity_id, meta in entity_lineage.items():
        interfaces = meta.get("source_interfaces") or meta.get("interfaces") or []
        if not interfaces:
            continue

        cleaned = [api_id.upper().strip() for api_id in interfaces if api_id]
        if not cleaned:
            continue

        unique_interfaces = sorted(set(cleaned))
        result.append(
            {
                "source": entity_id,
                "targets": unique_interfaces,
            }
        )

    logger.info("构建实体 → 接口关系: %d 个实体", len(result))
    return result


def save_relation_list(relations: List[Dict[str, Any]], output_file: Path) -> None:
    """保存关系列表到 JSON 文件"""
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open("w", encoding="utf-8") as f:
        json.dump(relations, f, ensure_ascii=False, indent=2)
    logger.info("关系文件已生成: %s (共 %d 条记录)", output_file, len(relations))


def save_interface_entity_relations(
    interface_ids: List[str],
    relations: Dict[str, List[str]],
    output_file: Path,
) -> None:
    """保存 接口 → 实体 关系列表"""
    relation_list: List[Dict[str, Any]] = []
    seen_interfaces = set(interface_ids)

    # 先写入接口目录中已知的接口
    for api_id in interface_ids:
        relation_list.append(
            {
                "source": api_id,
                "targets": relations.get(api_id, []),
            }
        )

    # 再写入仅在溯源映射中出现的接口
    for api_id, targets in relations.items():
        if api_id in seen_interfaces:
            continue
        relation_list.append(
            {
                "source": api_id,
                "targets": targets,
            }
        )

    save_relation_list(relation_list, output_file)


def load_relation_file(file_path: Path) -> List[Dict[str, Any]]:
    """加载关系 JSON 文件（function-interface 或 interface-entity）"""
    if not file_path.exists():
        raise FileNotFoundError(f"未找到关系文件: {file_path}")

    with file_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError(f"关系文件格式错误，应为 JSON 数组: {file_path}")

    logger.info("读取关系文件: %s, 记录数: %d", file_path, len(data))
    return data


def build_function_to_entity_relations(
    function_interface_relations: List[Dict[str, Any]],
    interface_entity_relations: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    通过接口作为中间节点，构建 功能 → 实体 关系
    FUNC -> API -> ENTITY
    """
    # 构建接口到实体的映射
    api_to_entities: Dict[str, List[str]] = {}
    for rel in interface_entity_relations:
        api_id = (rel.get("source") or "").upper()
        entities = rel.get("targets") or []
        if api_id and entities:
            api_to_entities[api_id] = list(entities)

    # 构建功能到实体的映射
    func_to_entities: Dict[str, set] = defaultdict(set)

    for rel in function_interface_relations:
        func_id = rel.get("source") or ""
        if not func_id:
            continue
        api_ids = rel.get("targets") or []
        if not api_ids:
            continue

        for api_id in api_ids:
            api_upper = (api_id or "").upper()
            if api_upper in api_to_entities:
                func_to_entities[func_id].update(api_to_entities[api_upper])

    result: List[Dict[str, Any]] = []
    for func_id in sorted(func_to_entities.keys()):
        entities = sorted(func_to_entities[func_id])
        if entities:
            result.append(
                {
                    "source": func_id,
                    "targets": entities,
                }
            )

    logger.info("构建功能 → 实体关系: %d 个功能", len(result))
    return result


def main() -> int:
    """命令行入口"""
    parser = argparse.ArgumentParser(description="实体关系构建工具")
    parser.add_argument(
        "--repo-root",
        type=str,
        required=True,
        help="仓库根目录路径",
    )
    parser.add_argument(
        "--relation-type",
        type=str,
        required=True,
        choices=["interface-to-entity", "entity-to-interface", "function-to-entity"],
        help="关系类型: interface-to-entity | entity-to-interface | function-to-entity",
    )

    # 通用：实体溯源映射
    parser.add_argument(
        "--entity-lineage",
        type=str,
        default=None,
        help="实体溯源映射文件路径 "
        "(默认 {REPO_ROOT}/.cache/omni-reverse/entities/entity-consolidation/entities_lineage.json)",
    )

    # 接口 → 实体 额外参数
    parser.add_argument(
        "--interfaces-dir",
        type=str,
        default=None,
        help="接口文档目录（可选，用于验证接口ID）",
    )

    # 功能 → 实体 额外参数
    parser.add_argument(
        "--function-interface-relations",
        type=str,
        default=None,
        help="功能-接口关系文件路径 "
        "(默认 {REPO_ROOT}/output/relations/function-interface.json)",
    )
    parser.add_argument(
        "--interface-entity-relations",
        type=str,
        default=None,
        help="接口-实体关系文件路径 "
        "(默认 {REPO_ROOT}/output/relations/interface-entity.json)",
    )

    # 输出
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="输出关系文件路径 "
        "(默认根据 relation-type 写入 {REPO_ROOT}/output/relations/*.json)",
    )

    args = parser.parse_args()

    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    try:
        repo_root = Path(args.repo_root)
        if not repo_root.exists():
            logger.error("仓库根目录不存在: %s", repo_root)
            return 1

        relations_dir = repo_root / "output" / "relations"

        # 实体溯源映射默认路径
        if args.entity_lineage:
            entity_lineage_path = Path(args.entity_lineage)
        else:
            entity_lineage_path = (
                repo_root
                / ".cache"
                / "omni-reverse"
                / "entities"
                / "entity-consolidation"
                / "entities_lineage.json"
            )

        relation_type = args.relation_type

        if relation_type == "interface-to-entity":
            # 默认接口目录：接口反构输出的接口文档目录或接口聚合目录
            if args.interfaces_dir:
                interfaces_dir = Path(args.interfaces_dir)
            else:
                # 优先使用 output/interfaces，其次使用接口聚合缓存目录
                interfaces_dir = repo_root / "output" / "interfaces"
                if not interfaces_dir.exists():
                    interfaces_dir = (
                        repo_root
                        / ".cache"
                        / "omni-reverse"
                        / "interfaces"
                        / "interface-aggregation"
                    )

            # 默认输出文件
            if args.output:
                output_file = Path(args.output)
            else:
                output_file = relations_dir / "interface-entity.json"

            logger.info("关系类型: 接口 → 实体")
            logger.info("实体溯源映射: %s", entity_lineage_path)
            logger.info("接口目录: %s", interfaces_dir)
            logger.info("输出文件: %s", output_file)

            lineage = load_entity_lineage(entity_lineage_path)
            interface_ids = load_interface_ids(interfaces_dir)
            interface_to_entity = build_interface_to_entity(lineage)
            save_interface_entity_relations(interface_ids, interface_to_entity, output_file)

        elif relation_type == "entity-to-interface":
            if args.output:
                output_file = Path(args.output)
            else:
                output_file = relations_dir / "entity-interface.json"

            logger.info("关系类型: 实体 → 接口")
            logger.info("实体溯源映射: %s", entity_lineage_path)
            logger.info("输出文件: %s", output_file)

            lineage = load_entity_lineage(entity_lineage_path)
            relations = build_entity_to_interface(lineage)
            save_relation_list(relations, output_file)

        elif relation_type == "function-to-entity":
            # 默认功能-接口关系文件
            if args.function_interface_relations:
                func_iface_path = Path(args.function_interface_relations)
            else:
                func_iface_path = relations_dir / "function-interface.json"

            # 默认接口-实体关系文件
            if args.interface_entity_relations:
                iface_entity_path = Path(args.interface_entity_relations)
            else:
                iface_entity_path = relations_dir / "interface-entity.json"

            # 默认输出文件
            if args.output:
                output_file = Path(args.output)
            else:
                output_file = relations_dir / "function-entity.json"

            logger.info("关系类型: 功能 → 实体")
            logger.info("功能-接口关系文件: %s", func_iface_path)
            logger.info("接口-实体关系文件: %s", iface_entity_path)
            logger.info("输出文件: %s", output_file)

            func_iface_rel = load_relation_file(func_iface_path)
            iface_entity_rel = load_relation_file(iface_entity_path)
            relations = build_function_to_entity_relations(func_iface_rel, iface_entity_rel)
            save_relation_list(relations, output_file)

        logger.info("关系构建完成: %s", relation_type)
        return 0

    except Exception as exc:  # noqa: BLE001
        logger.error("关系构建失败: %s", exc, exc_info=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())


