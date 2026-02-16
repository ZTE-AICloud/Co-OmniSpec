#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实体清单生成工具

从实体文档目录中扫描实体文件（通常为 ENTITY-*.md），解析实体信息，
生成包含统计信息和实体列表表格的 Markdown 清单文件。

兼容 Windows 和 Linux 系统。

使用方法:
    python entity_list_generator.py --repo-root <repo_root> [--entity-dir <dir>] [--output <file>]

参数说明:
    --repo-root: 仓库根目录路径（必需）
    --entity-dir: 实体文档目录（可选，默认 {REPO_ROOT}/output/entities）
    --output: 输出清单文件路径（可选，默认为实体目录下的 "实体清单.md"）
"""

import argparse
import logging
import re
from pathlib import Path
from typing import List, Dict, Any, Optional


logger = logging.getLogger(__name__)


class EntityListGenerator:
    """逻辑实体清单生成器"""

    def __init__(self, entity_dir: str, output_file: Optional[str] = None) -> None:
        """
        初始化生成器

        Args:
            entity_dir: 逻辑实体文件目录
            output_file: 输出文件路径，如果为 None 则输出到实体目录下的 "实体清单.md"
        """
        self.entity_dir = Path(entity_dir)
        if output_file:
            self.output_file = Path(output_file)
        else:
            self.output_file = self.entity_dir / "实体清单.md"

    def _extract_field(self, text: str, field_name: str) -> str:
        """从文本中提取字段值（适配实体模板中的 `- **字段名**: 值` 格式）"""
        # 匹配格式: - **字段名**: 值
        pattern = rf'- \*\*{re.escape(field_name)}\*\*:\s*(.+?)(?=\n-|\n\n|$)'
        match = re.search(pattern, text, re.DOTALL | re.MULTILINE)
        if not match:
            return ""

        value = match.group(1).strip()
        # 移除多余换行，压缩为单行，便于生成表格
        value = " ".join(value.split())
        return value

    def _parse_entity_block(self, block: str, entity_file: Path) -> Optional[Dict[str, Any]]:
        """
        解析单个实体块

        Args:
            block: 实体块内容
            entity_file: 实体文件路径

        Returns:
            实体信息字典；如果无法解析则返回 None
        """
        entity: Dict[str, Any] = {}

        # 提取业务名称（实体标题下的第一行）
        lines = block.strip().split("\n")
        if lines:
            entity["entity_name_cn"] = lines[0].strip()

        # 提取“基本信息”段落
        basic_info_match = re.search(
            r"### 基本信息\n(.*?)(?:\n###|\Z)",
            block,
            re.DOTALL,
        )

        if basic_info_match:
            info_text = basic_info_match.group(1)

            # 提取各个字段（字段名与实体模板保持一致）
            entity["entity_id"] = self._extract_field(info_text, "实体标识")
            entity["entity_name_cn"] = (
                self._extract_field(info_text, "业务名称")
                or entity.get("entity_name_cn", "")
            )
            entity["entity_type"] = self._extract_field(info_text, "实体类型")
            entity["domain"] = self._extract_field(info_text, "所属领域")
            entity["related_files"] = self._extract_field(info_text, "关联文件")
            entity["responsibility"] = self._extract_field(info_text, "关键职责")

        # 如果没有实体标识，视为无效实体
        if not entity.get("entity_id"):
            return None

        # 添加文件信息（用于生成链接）
        entity["source_file"] = entity_file.name
        entity["file_path"] = str(entity_file.relative_to(self.entity_dir))

        return entity

    def _parse_entity_file(self, entity_file: Path) -> List[Dict[str, Any]]:
        """
        解析单个实体文件

        支持以下两种格式：
        1. 一个文件一个实体（典型的 ENTITY-xxx-名称.md）
        2. 一个文件包含多个实体块（以 `## 逻辑实体` 开头分隔）
        """
        entities: List[Dict[str, Any]] = []

        try:
            with open(entity_file, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as exc:
            logger.warning(f"解析文件失败 {entity_file.name}: {exc}")
            return entities

        # 分割实体：
        # - 支持：## 逻辑实体 N:
        # - 支持：## 逻辑实体:
        # - 支持：## 逻辑实体: xxx
        entity_blocks = re.split(r"\n## 逻辑实体(?:\s+\d+)?:?\s*", content)

        if len(entity_blocks) == 1:
            # 整个文件作为一个实体（常见于 ENTITY-*.md）
            entity = self._parse_entity_block(content, entity_file)
            if entity:
                entities.append(entity)
        else:
            # 多个实体块
            for block in entity_blocks[1:]:
                entity = self._parse_entity_block(block, entity_file)
                if entity:
                    entities.append(entity)

        return entities

    def _write_list_file(self, entities: List[Dict[str, Any]]) -> None:
        """
        写入清单文件

        内容结构：
        - 标题与摘要
        - 统计信息（按实体类型、所属领域）
        - 实体列表表格
        """
        # 确保输出目录存在
        self.output_file.parent.mkdir(parents=True, exist_ok=True)

        from datetime import datetime

        with open(self.output_file, "w", encoding="utf-8") as f:
            # 标题
            f.write("# 逻辑实体清单\n\n")
            f.write(f"本文档列出了所有已识别的逻辑实体，共 **{len(entities)}** 个。\n\n")

            # 统计信息
            f.write("## 统计信息\n\n")

            # 按实体类型统计
            type_count: Dict[str, int] = {}
            for entity in entities:
                entity_type = entity.get("entity_type") or "未知类型"
                type_count[entity_type] = type_count.get(entity_type, 0) + 1

            f.write("### 按实体类型统计\n\n")
            f.write("| 实体类型 | 数量 |\n")
            f.write("|---------|------|\n")
            for entity_type, count in sorted(
                type_count.items(), key=lambda x: x[1], reverse=True
            ):
                f.write(f"| {entity_type} | {count} |\n")
            f.write("\n")

            # 按所属领域统计
            domain_count: Dict[str, int] = {}
            for entity in entities:
                domain = entity.get("domain") or "未知领域"
                domain_count[domain] = domain_count.get(domain, 0) + 1

            f.write("### 按所属领域统计\n\n")
            f.write("| 所属领域 | 数量 |\n")
            f.write("|---------|------|\n")
            for domain, count in sorted(
                domain_count.items(), key=lambda x: x[1], reverse=True
            ):
                f.write(f"| {domain} | {count} |\n")
            f.write("\n")

            # 实体列表
            f.write("## 实体列表\n\n")
            f.write(
                "| 序号 | 实体标识 | 业务名称 | 实体类型 | 所属领域 | 关联文件 | 实体文件 |\n"
            )
            f.write(
                "|------|---------|---------|---------|---------|---------|----------|\n"
            )

            for idx, entity in enumerate(entities, 1):
                entity_id = (entity.get("entity_id") or "").replace("|", r"\|")
                entity_name = (entity.get("entity_name_cn") or "").replace("|", r"\|")
                entity_type = (entity.get("entity_type") or "").replace("|", r"\|")
                domain = (entity.get("domain") or "").replace("|", r"\|")
                related_files = (entity.get("related_files") or "").replace(
                    "|", r"\|"
                )
                source_file = entity.get("source_file") or ""

                # 处理过长的关联文件字段
                if len(related_files) > 50:
                    related_files = related_files[:47] + "..."

                file_path = entity.get("file_path") or source_file
                file_link = f"[{source_file}](./{file_path})"

                f.write(
                    f"| {idx} | {entity_id} | {entity_name} | {entity_type} | {domain} | {related_files} | {file_link} |\n"
                )

            f.write("\n")
            f.write("---\n\n")
            f.write(f"*生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n")

    def generate_list(self) -> List[Dict[str, Any]]:
        """
        生成实体清单

        Returns:
            实体信息列表
        """
        logger.info("=" * 60)
        logger.info("生成逻辑实体清单")
        logger.info("=" * 60)
        logger.info(f"实体目录: {self.entity_dir}")
        logger.info(f"输出文件: {self.output_file}\n")

        if not self.entity_dir.exists():
            logger.error(f"实体目录不存在: {self.entity_dir}")
            return []

        # 扫描所有实体文件（默认使用 ENTITY-*.md 命名）
        entity_files = sorted(self.entity_dir.glob("ENTITY-*.md"))

        if not entity_files:
            logger.warning(f"未找到实体文件 (ENTITY-*.md) 在目录: {self.entity_dir}")
            return []

        logger.info(f"发现 {len(entity_files)} 个实体文件\n")

        all_entities: List[Dict[str, Any]] = []

        # 解析所有实体文件
        for idx, entity_file in enumerate(entity_files, 1):
            logger.info(f"[{idx}/{len(entity_files)}] 解析: {entity_file.name}")
            entities = self._parse_entity_file(entity_file)
            all_entities.extend(entities)
            logger.info(f"  └─ 提取到 {len(entities)} 个实体")

        logger.info(f"\n共提取到 {len(all_entities)} 个逻辑实体\n")

        # 按实体标识排序，保持输出稳定
        all_entities.sort(key=lambda x: x.get("entity_id", "").lower())

        # 生成清单文件
        self._write_list_file(all_entities)

        logger.info(f"✓ 实体清单已生成: {self.output_file}")
        logger.info("=" * 60)

        return all_entities


def main() -> int:
    """命令行入口"""
    parser = argparse.ArgumentParser(description="生成逻辑实体清单")
    parser.add_argument(
        "--repo-root",
        type=str,
        required=True,
        help="仓库根目录路径",
    )
    parser.add_argument(
        "--entity-dir",
        type=str,
        default=None,
        help="实体文档目录（可选，默认 {REPO_ROOT}/output/entities）",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="输出文件路径（可选，默认为实体目录下的 '实体清单.md'）",
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
            logger.error(f"仓库根目录不存在: {repo_root}")
            return 1

        # 确定实体目录
        if args.entity_dir:
            entity_dir = Path(args.entity_dir)
        else:
            # 默认：最终实体文档目录
            entity_dir = repo_root / "output" / "entities"

        generator = EntityListGenerator(
            entity_dir=str(entity_dir),
            output_file=args.output,
        )

        entities = generator.generate_list()

        if not entities:
            logger.warning("未找到任何实体，清单文件可能为空")
            return 1

        logger.info(f"\n成功生成实体清单，共 {len(entities)} 个实体")
        return 0

    except Exception as exc:  # noqa: BLE001
        logger.error(f"生成清单失败: {exc}", exc_info=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())


