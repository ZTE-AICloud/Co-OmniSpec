#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
逻辑实体融合器 - 方案D实现
从接口抽取的实体文档中读取所有实体，通过多轮迭代进行融合、去重和关联性分析。

处理流程：
  第0步：规则去重（基于entity_id）
  第N轮迭代：
    步骤1：基本信息融合（批次40，并发20）
    步骤2：类图整合（仅合并组，并发20）
    步骤3：合并结果，准备下一轮
  最终：生成融合后的实体列表

兼容Windows和Linux系统
使用方法:
    python entity_consolidator.py --repo-root <repo_root> [--input-dir <dir>] [--output-dir <dir>] [--step <step>] [--round <round>] [--max-workers <num>]

参数:
    repo-root: 仓库根目录路径（必需）
    input-dir: 输入目录（可选，默认从缓存目录读取）
    output-dir: 输出目录（可选，默认使用缓存目录）
    step: 执行步骤（可选，可选值：rule-dedup, basic-merge, class-diagram-merge, value-evaluation, generate-result, all）
    round: 融合轮次（可选，仅在 step=basic-merge 或 class-diagram-merge 时使用）
    max-workers: 最大并发数（可选，默认20）
"""

import json
import logging
import os
import sys
import re
import time
import argparse
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class EntityConsolidator:
    """逻辑实体融合器"""
    
    def __init__(
        self,
        llm_caller,
        repo_root: str,
        input_dir: str,
        output_dir: str,
        max_workers: int = 20,
        batch_size: int = 40
    ):
        """
        初始化融合器
        
        Args:
            llm_caller: LLM调用器
            repo_root: 仓库根目录
            input_dir: 输入目录（实体抽取输出目录）
            output_dir: 输出目录（实体融合输出目录）
            max_workers: 最大并发数，默认20
            batch_size: 批次大小，默认40
        """
        self.llm_caller = llm_caller
        self.repo_root = Path(repo_root)
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.max_workers = max_workers
        self.batch_size = batch_size
        self.lineage_map: Dict[str, List[str]] = {}
        self.entity_lineage_records: List[Dict[str, Any]] = []
        
    def load_lineage_map(self) -> Dict[str, List[str]]:
        """加载接口与实体的溯源信息"""
        lineage_dir = self.input_dir / "lineage"
        if not lineage_dir.exists():
            logger.warning(f"未找到溯源目录: {lineage_dir}")
            return {}
        
        lineage_map: Dict[str, List[str]] = {}
        for lineage_file in lineage_dir.glob("*.json"):
            try:
                with open(lineage_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                entities = data.get("entities", [])
                for entity in entities:
                    entity_id = entity.get("entity_id", "")
                    if not entity_id:
                        continue
                    iface_list = entity.get("interfaces") or data.get("interfaces", [])
                    lineage_map[entity_id.lower().strip()] = sorted(
                        {iface.upper() for iface in iface_list if iface}
                    )
            except Exception as exc:
                logger.error(f"读取溯源文件失败 {lineage_file}: {exc}")
        
        self.lineage_map = lineage_map
        return lineage_map
    
    def load_entities_from_batch_index(self) -> List[Dict[str, Any]]:
        """
        从批次结果索引文件加载所有实体
        
        Returns:
            实体列表
        """
        index_file = self.input_dir / "entities-index.json"
        if not index_file.exists():
            logger.error(f"批次结果索引文件不存在: {index_file}")
            raise FileNotFoundError(f"批次结果索引文件不存在: {index_file}")
        
        try:
            with open(index_file, 'r', encoding='utf-8') as f:
                index_data = json.load(f)
        except Exception as e:
            logger.error(f"读取批次索引文件失败: {e}")
            raise
        
        all_entities = []
        batches = index_data.get('batches', [])
        
        logger.info(f"从批次索引文件读取到 {len(batches)} 个批次")
        
        for batch in batches:
            if batch.get('status') != 'completed':
                logger.warning(f"批次 {batch.get('batch_id')} 状态为 {batch.get('status')}，跳过")
                continue
            
            entity_files = batch.get('entity_files', [])
            for entity_file_rel in entity_files:
                # 实体文件路径是相对路径，需要转换为绝对路径
                if entity_file_rel.startswith('entity-extraction/'):
                    entity_file_name = entity_file_rel.replace('entity-extraction/', '')
                else:
                    entity_file_name = Path(entity_file_rel).name
                
                entity_file_path = self.input_dir / entity_file_name
                
                if not entity_file_path.exists():
                    logger.warning(f"实体文件不存在: {entity_file_path}")
                    continue
                
                entities = self.parse_entities_from_md(entity_file_path)
                all_entities.extend(entities)
        
        logger.info(f"从批次索引文件收集到 {len(all_entities)} 个实体")
        return all_entities
    
    def parse_entities_from_md(self, md_file: Path) -> List[Dict[str, Any]]:
        """从MD文件中解析实体信息"""
        entities = []
        
        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            logger.error(f"读取实体文件失败 {md_file}: {e}")
            return []
        
        # 分割实体（每个实体以 ## 逻辑实体 N: 开头）
        entity_blocks = re.split(r'\n## 逻辑实体 \d+:', content)
        
        for block in entity_blocks[1:]:  # 跳过第一个空块
            entity = self._parse_entity_block(block)
            if entity:
                entities.append(entity)
        
        return entities
    
    def _parse_entity_block(self, block: str) -> Dict[str, Any]:
        """解析单个实体块"""
        entity = {}
        
        # 提取业务名称（第一行）
        lines = block.strip().split('\n')
        if lines:
            entity['entity_name_cn'] = lines[0].strip()
        
        # 提取基本信息
        basic_info_match = re.search(
            r'### 基本信息\n(.*?)\n###',
            block,
            re.DOTALL
        )
        
        if basic_info_match:
            info_text = basic_info_match.group(1)
            
            # 提取各个字段
            entity['entity_id'] = self._extract_field(info_text, '实体标识')
            entity['entity_name_cn'] = self._extract_field(info_text, '业务名称') or entity.get('entity_name_cn', '')
            entity['entity_type'] = self._extract_field(info_text, '实体类型')
            entity['domain'] = self._extract_field(info_text, '所属领域')
            entity['related_files'] = self._extract_field(info_text, '关联文件')
            entity['responsibility'] = self._extract_field(info_text, '关键职责')
        
        # 提取类图
        class_diagram_match = re.search(
            r'```mermaid\n(.*?)\n```',
            block,
            re.DOTALL
        )
        
        if class_diagram_match:
            entity['class_diagram'] = class_diagram_match.group(1).strip()
        else:
            entity['class_diagram'] = ''
        
        entity_id = entity.get('entity_id', '')
        entity['source_interfaces'] = self._get_interfaces_for_entity(entity_id)
        
        return entity if entity_id else None

    def _get_interfaces_for_entity(self, entity_id: str) -> List[str]:
        """根据实体标识获取关联接口列表"""
        if not entity_id:
            return []
        return self.lineage_map.get(entity_id.lower().strip(), [])
    
    def _extract_field(self, text: str, field_name: str) -> str:
        """从文本中提取字段值"""
        pattern = rf'- \*\*{field_name}\*\*:\s*(.+?)(?=\n-|\n\n|$)'
        match = re.search(pattern, text, re.DOTALL)
        return match.group(1).strip() if match else ''
    
    def rule_deduplication(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """第0步：基于entity_id的规则去重"""
        logger.info("=" * 60)
        logger.info("第0步 - 规则去重（基于entity_id）")
        logger.info("=" * 60)
        logger.info(f"输入: {len(entities)} 个实体\n")
        
        seen = {}
        for entity in entities:
            entity_id = entity.get('entity_id', '').lower().strip()
            if not entity_id:
                continue
                
            if entity_id not in seen:
                seen[entity_id] = entity
            else:
                # 合并关联文件
                existing = seen[entity_id]
                existing_files = set(f.strip() for f in existing.get('related_files', '').split(',') if f.strip())
                new_files = set(f.strip() for f in entity.get('related_files', '').split(',') if f.strip())
                combined_files = sorted(existing_files | new_files)
                existing['related_files'] = ', '.join(combined_files)
                
                # 合并接口列表
                existing_interfaces = set(existing.get('source_interfaces', []))
                new_interfaces = set(entity.get('source_interfaces', []))
                existing['source_interfaces'] = sorted(existing_interfaces | new_interfaces)
        
        result = list(seen.values())
        dedup_rate = round((1 - len(result) / len(entities)) * 100, 2) if entities else 0
        logger.info(f"规则去重完成: {len(entities)} -> {len(result)} 个实体 (去重率: {dedup_rate}%)\n")
        
        return result
    
    def consolidate_entities(self, entities: List[Dict[str, Any]], max_rounds: int = 3) -> List[Dict[str, Any]]:
        """多轮融合实体"""
        current_entities = entities
        
        for round_num in range(1, max_rounds + 1):
            logger.info("=" * 60)
            logger.info(f"第{round_num}轮融合")
            logger.info("=" * 60)
            logger.info(f"输入: {len(current_entities)} 个实体\n")
            
            round_start = time.time()
            
            # 步骤1：基本信息融合
            merge_result = self._batch_merge_basic_info(current_entities, round_num)
            
            # 步骤2：类图整合（仅合并组）
            final_entities = self._merge_class_diagrams(merge_result, round_num)
            
            # 统计
            round_time = time.time() - round_start
            merge_rate = round((1 - len(final_entities) / len(current_entities)) * 100, 2) if current_entities else 0
            
            logger.info(f"第{round_num}轮完成:")
            logger.info(f"  ├─ {len(current_entities)} -> {len(final_entities)} 个实体")
            logger.info(f"  ├─ 融合率: {merge_rate}%")
            logger.info(f"  └─ 耗时: {round_time:.1f}秒\n")
            
            # 检查收敛
            if len(final_entities) == len(current_entities):
                logger.info(f"✓ 已收敛，停止迭代\n")
                break
            
            current_entities = final_entities
        
        return current_entities
    
    def _batch_merge_basic_info(self, entities: List[Dict[str, Any]], round_num: int) -> Dict[str, Any]:
        """步骤1：批次并发处理基本信息融合"""
        logger.info(f"步骤1 - 基本信息融合 (批次大小: {self.batch_size}, 最大并发: {self.max_workers}):")
        
        # 分批
        batches = [entities[i:i + self.batch_size] for i in range(0, len(entities), self.batch_size)]
        logger.info(f"  ├─ 分成 {len(batches)} 个批次")
        
        # 并发处理
        batch_results = []
        step_start = time.time()
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(self._process_basic_info_batch, batch, round_num, idx): idx
                for idx, batch in enumerate(batches, 1)
            }
            
            for future in as_completed(futures):
                batch_idx = futures[future]
                try:
                    result = future.result()
                    batch_results.append(result)
                    logger.info(f"  ├─ ✓ 批次 {batch_idx}/{len(batches)} 完成")
                except Exception as e:
                    logger.error(f"  ├─ ✗ 批次 {batch_idx}/{len(batches)} 失败: {e}")
                    # 失败时返回原始实体
                    batch_results.append({
                        'merged_groups': [],
                        'standalone_entities': [self._entity_basic_with_interfaces(e) for e in batches[batch_idx - 1]]
                    })
        
        # 合并所有批次的结果
        all_merged_groups = []
        all_standalone = []
        
        for result in batch_results:
            all_merged_groups.extend(result.get('merged_groups', []))
            all_standalone.extend(result.get('standalone_entities', []))
        
        step_time = time.time() - step_start
        total_merged = sum(len(g['source_entity_ids']) for g in all_merged_groups)
        
        logger.info(f"  └─ 步骤1完成:")
        logger.info(f"      ├─ 合并组: {len(all_merged_groups)} 个 (涉及 {total_merged} 个实体)")
        logger.info(f"      ├─ 独立实体: {len(all_standalone)} 个")
        logger.info(f"      └─ 耗时: {step_time:.1f}秒\n")
        
        return {
            'merged_groups': all_merged_groups,
            'standalone_entities': all_standalone,
            'original_entities': entities  # 保留原始实体（用于查找类图）
        }
    
    def _process_basic_info_batch(self, batch: List[Dict[str, Any]], round_num: int, batch_idx: int) -> Dict[str, Any]:
        """处理单个批次的基本信息融合"""
        # 准备输入（只包含基本信息，不含类图）
        entities_json = json.dumps([
            self._entity_to_basic_info(e) for e in batch
        ], ensure_ascii=False, indent=2)
        
        source_interface_map = {
            e.get('entity_id', '').lower(): e.get('source_interfaces', [])
            for e in batch
        }

        # 调用LLM
        try:
            response = self.llm_caller.call_with_template(
                'entity_consolidation_basic',
                entities_json=entities_json,
                round_num=round_num
            )
        except Exception as e:
            logger.error(f"LLM调用失败: {e}")
            raise
        
        # 解析响应
        result = self._parse_basic_info_response(response, batch, source_interface_map)
        
        return result

    def _entity_basic_with_interfaces(self, entity: Dict[str, Any]) -> Dict[str, Any]:
        """保留source_interfaces的基础信息"""
        data = self._entity_to_basic_info(entity)
        data['source_interfaces'] = entity.get('source_interfaces', [])
        return data
    
    def _entity_to_basic_info(self, entity: Dict[str, Any]) -> Dict[str, str]:
        """提取实体的基本信息（不含类图）"""
        return {
            'entity_id': entity.get('entity_id', ''),
            'entity_name_cn': entity.get('entity_name_cn', ''),
            'entity_type': entity.get('entity_type', ''),
            'domain': entity.get('domain', ''),
            'related_files': entity.get('related_files', ''),
            'responsibility': entity.get('responsibility', '')
        }
    
    def _parse_basic_info_response(
        self,
        response: str,
        original_batch: List[Dict[str, Any]],
        source_interface_map: Dict[str, List[str]]
    ) -> Dict[str, Any]:
        """解析基本信息融合的LLM响应"""
        try:
            # 提取JSON
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', response, re.DOTALL)
            if not json_match:
                json_match = re.search(r'\{.*?"merged_groups".*?\}', response, re.DOTALL)
            
            if json_match:
                json_str = json_match.group(1) if '```' in response else json_match.group(0)
                data = json.loads(json_str)
                
                merged_groups = data.get('merged_groups', [])
                standalone_entities = data.get('standalone_entities', [])

                for group in merged_groups:
                    interfaces = set()
                    for source_id in group.get('source_entity_ids', []):
                        interfaces.update(source_interface_map.get(source_id.lower(), []))
                    group.setdefault('merged_entity', {})['source_interfaces'] = sorted(interfaces)
                
                for entity in standalone_entities:
                    eid = entity.get('entity_id', '').lower()
                    entity['source_interfaces'] = source_interface_map.get(eid, [])
                
                return {
                    'merged_groups': merged_groups,
                    'standalone_entities': standalone_entities
                }
            else:
                logger.warning("无法从LLM响应中提取JSON，返回原始批次为独立实体")
                return {
                    'merged_groups': [],
                    'standalone_entities': [self._entity_basic_with_interfaces(e) for e in original_batch]
                }
                
        except Exception as e:
            logger.error(f"解析基本信息融合响应失败: {e}")
            return {
                'merged_groups': [],
                'standalone_entities': [self._entity_basic_with_interfaces(e) for e in original_batch]
            }
    
    def _merge_class_diagrams(self, merge_result: Dict[str, Any], round_num: int) -> List[Dict[str, Any]]:
        """步骤2：并发整合类图（仅合并组）"""
        merged_groups = merge_result['merged_groups']
        standalone_entities = merge_result['standalone_entities']
        original_entities = merge_result['original_entities']
        
        logger.info(f"步骤2 - 类图整合 (最大并发: {self.max_workers}):")
        logger.info(f"  ├─ 需要整合的合并组: {len(merged_groups)} 个")
        
        if not merged_groups:
            logger.info(f"  └─ 无需整合，直接使用原始类图\n")
            # 为独立实体恢复类图
            return self._restore_diagrams_for_standalone(standalone_entities, original_entities)
        
        # 并发整合类图
        step_start = time.time()
        merged_with_diagrams = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(
                    self._integrate_single_group_diagram, 
                    group, 
                    original_entities,
                    round_num,
                    idx
                ): idx
                for idx, group in enumerate(merged_groups, 1)
            }
            
            for future in as_completed(futures):
                group_idx = futures[future]
                try:
                    result = future.result()
                    merged_with_diagrams.append(result)
                    logger.info(f"  ├─ ✓ 合并组 {group_idx}/{len(merged_groups)} 类图整合完成")
                except Exception as e:
                    logger.error(f"  ├─ ✗ 合并组 {group_idx}/{len(merged_groups)} 失败: {e}")
                    # 失败时使用第一个实体的类图
                    group = merged_groups[group_idx - 1]
                    entity = group['merged_entity'].copy()
                    source_ids = group['source_entity_ids']
                    first_diagram = self._find_diagram_by_id(source_ids[0], original_entities)
                    entity['class_diagram'] = first_diagram
                    merged_with_diagrams.append(entity)
        
        # 为独立实体恢复类图
        standalone_with_diagrams = self._restore_diagrams_for_standalone(standalone_entities, original_entities)
        
        step_time = time.time() - step_start
        logger.info(f"  └─ 步骤2完成:")
        logger.info(f"      ├─ 整合类图: {len(merged_with_diagrams)} 个")
        logger.info(f"      ├─ 独立实体: {len(standalone_with_diagrams)} 个")
        logger.info(f"      └─ 耗时: {step_time:.1f}秒\n")
        
        # 合并结果
        return merged_with_diagrams + standalone_with_diagrams
    
    def _integrate_single_group_diagram(
        self, 
        group: Dict[str, Any], 
        original_entities: List[Dict[str, Any]],
        round_num: int,
        group_idx: int
    ) -> Dict[str, Any]:
        """整合单个合并组的类图"""
        merged_entity = group['merged_entity']
        source_ids = group['source_entity_ids']
        
        # 收集所有源实体的类图
        source_diagrams = []
        for entity_id in source_ids:
            diagram = self._find_diagram_by_id(entity_id, original_entities)
            if diagram:
                source_diagrams.append({
                    'entity_id': entity_id,
                    'diagram': diagram
                })
        
        merged_entity.setdefault('source_interfaces', group.get('merged_entity', {}).get('source_interfaces', []))

        if len(source_diagrams) <= 1:
            # 只有一个类图，直接使用
            result = merged_entity.copy()
            result['class_diagram'] = source_diagrams[0]['diagram'] if source_diagrams else ''
            return result
        
        # 调用LLM整合多个类图
        diagrams_json = json.dumps(source_diagrams, ensure_ascii=False, indent=2)
        merged_info = json.dumps(merged_entity, ensure_ascii=False, indent=2)
        
        try:
            response = self.llm_caller.call_with_template(
                'entity_class_diagram_merge',
                source_diagrams=diagrams_json,
                merged_entity_info=merged_info,
                round_num=round_num,
                group_idx=group_idx
            )
        except Exception as e:
            logger.error(f"LLM调用失败: {e}")
            # 失败时使用第一个类图
            result = merged_entity.copy()
            result['class_diagram'] = source_diagrams[0]['diagram'] if source_diagrams else ''
            return result
        
        # 提取整合后的类图
        integrated_diagram = self._extract_mermaid_diagram(response)
        
        result = merged_entity.copy()
        result['class_diagram'] = integrated_diagram
        
        return result
    
    def _find_diagram_by_id(self, entity_id: str, entities: List[Dict[str, Any]]) -> str:
        """根据entity_id查找类图"""
        entity_id_lower = entity_id.lower().strip()
        for entity in entities:
            if entity.get('entity_id', '').lower().strip() == entity_id_lower:
                return entity.get('class_diagram', '')
        return ''
    
    def _restore_diagrams_for_standalone(
        self, 
        standalone_entities: List[Dict[str, Any]], 
        original_entities: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """为独立实体恢复类图"""
        result = []
        for entity in standalone_entities:
            entity_with_diagram = entity.copy()
            diagram = self._find_diagram_by_id(entity['entity_id'], original_entities)
            entity_with_diagram['class_diagram'] = diagram
            result.append(entity_with_diagram)
        return result
    
    def _extract_mermaid_diagram(self, response: str) -> str:
        """从LLM响应中提取Mermaid类图"""
        match = re.search(r'```mermaid\s*\n(.*?)\n```', response, re.DOTALL)
        if match:
            return match.group(1).strip()
        
        # 尝试直接查找classDiagram
        match = re.search(r'classDiagram\s*\n(.*?)(?=\n```|\n##|\Z)', response, re.DOTALL)
        if match:
            return 'classDiagram\n' + match.group(1).strip()
        
        logger.warning("无法从响应中提取Mermaid类图")
        return ''
    
    def evaluate_entities(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """评估实体价值，过滤低价值实体"""
        logger.info("=" * 60)
        logger.info("实体价值评估")
        logger.info("=" * 60)
        logger.info(f"输入: {len(entities)} 个实体\n")
        
        # 分批评估
        batch_size = 30  # 评估批次可以大一点
        batches = [entities[i:i + batch_size] for i in range(0, len(entities), batch_size)]
        logger.info(f"分成 {len(batches)} 个批次进行评估\n")
        
        all_valuable = []
        all_filtered = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(self._evaluate_batch, batch, idx): idx
                for idx, batch in enumerate(batches, 1)
            }
            
            for future in as_completed(futures):
                batch_idx = futures[future]
                try:
                    valuable, filtered = future.result()
                    all_valuable.extend(valuable)
                    all_filtered.extend(filtered)
                    logger.info(f"  ✓ 批次 {batch_idx}/{len(batches)}: 保留 {len(valuable)} 个, 过滤 {len(filtered)} 个")
                except Exception as e:
                    logger.error(f"  ✗ 批次 {batch_idx}/{len(batches)} 评估失败: {e}")
                    # 失败时保留所有实体
                    all_valuable.extend(batches[batch_idx - 1])
        
        filter_rate = round(len(all_filtered) / len(entities) * 100, 2) if entities else 0
        
        logger.info(f"\n评估完成:")
        logger.info(f"  ├─ 保留实体: {len(all_valuable)} 个")
        logger.info(f"  ├─ 过滤实体: {len(all_filtered)} 个")
        logger.info(f"  └─ 过滤率: {filter_rate}%\n")
        
        # 记录被过滤的实体
        if all_filtered:
            logger.info("被过滤的实体:")
            for entity in all_filtered[:10]:  # 只显示前10个
                logger.info(f"  - {entity.get('entity_name_cn')} ({entity.get('entity_id')})")
            if len(all_filtered) > 10:
                logger.info(f"  ... 还有 {len(all_filtered) - 10} 个")
            logger.info("")
        
        return all_valuable
    
    def _evaluate_batch(self, batch: List[Dict[str, Any]], batch_idx: int) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """评估单个批次的实体"""
        # 准备输入（只需要基本信息）
        entities_json = json.dumps([
            self._entity_to_basic_info(e) for e in batch
        ], ensure_ascii=False, indent=2)
        
        # 调用LLM
        try:
            response = self.llm_caller.call_with_template(
                'entity_value_evaluation',
                entities_json=entities_json
            )
        except Exception as e:
            logger.error(f"LLM调用失败: {e}")
            # 失败时保留所有实体
            return batch, []
        
        # 解析响应
        valuable_ids, filtered_ids = self._parse_evaluation_response(response, batch)
        
        # 分类实体
        valuable = []
        filtered = []
        
        for entity in batch:
            entity_id = entity.get('entity_id', '').lower()
            if entity_id in valuable_ids:
                valuable.append(entity)
            else:
                filtered.append(entity)
        
        return valuable, filtered
    
    def _parse_evaluation_response(self, response: str, original_batch: List[Dict[str, Any]]) -> Tuple[set, set]:
        """解析评估响应，返回(valuable_ids, filtered_ids)"""
        try:
            # 提取JSON
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', response, re.DOTALL)
            if not json_match:
                json_match = re.search(r'\{.*?"valuable_entities".*?\}', response, re.DOTALL)
            
            if json_match:
                json_str = json_match.group(1) if '```' in response else json_match.group(0)
                data = json.loads(json_str)
                
                valuable_ids = {e['entity_id'].lower() for e in data.get('valuable_entities', [])}
                filtered_ids = {e['entity_id'].lower() for e in data.get('filtered_entities', [])}
                
                return valuable_ids, filtered_ids
            else:
                logger.warning("无法从评估响应中提取JSON，保留所有实体")
                return {e.get('entity_id', '').lower() for e in original_batch}, set()
                
        except Exception as e:
            logger.error(f"解析评估响应失败: {e}")
            return {e.get('entity_id', '').lower() for e in original_batch}, set()
    
    def save_consolidated_entities(self, entities: List[Dict[str, Any]]) -> None:
        """保存融合后的实体列表"""
        output_file = self.output_dir / "consolidated-entities.json"
        
        # 去重：基于 entity_id 去重，保留第一个出现的实体
        seen = {}
        unique_entities = []
        for entity in entities:
            entity_id = entity.get('entity_id', '').lower().strip()
            if not entity_id:
                # 如果没有 entity_id，直接添加（这种情况应该很少）
                unique_entities.append(entity)
                continue
            
            if entity_id not in seen:
                seen[entity_id] = entity
                unique_entities.append(entity)
            else:
                # 发现重复，合并 source_interfaces
                existing = seen[entity_id]
                existing_interfaces = set(existing.get('source_interfaces', []))
                new_interfaces = set(entity.get('source_interfaces', []))
                existing['source_interfaces'] = sorted(existing_interfaces | new_interfaces)
                logger.warning(f"发现重复实体 {entity_id}，已合并接口列表")
        
        if len(unique_entities) < len(entities):
            dup_count = len(entities) - len(unique_entities)
            logger.info(f"去重: {len(entities)} -> {len(unique_entities)} 个实体 (移除 {dup_count} 个重复)")
        
        # 保存为JSON
        output_data = {
            'version': '1.0',
            'total_entities': len(unique_entities),
            'entities': unique_entities
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"融合后的实体列表已保存: {output_file}")
    
    def save_entity_lineage(self) -> None:
        """保存实体到接口的溯源映射"""
        if not self.entity_lineage_records:
            logger.warning("未记录到实体与接口的关系映射")
            return
        
        lineage_map = {
            record["entity_file_id"]: {
                "entity_doc": record["entity_doc"],
                "entity_name": record["entity_name"],
                "entity_identifier": record["entity_identifier"],
                "source_interfaces": record["source_interfaces"]
            }
            for record in self.entity_lineage_records
        }
        
        lineage_file = self.output_dir / "entities_lineage.json"
        
        output_data = {
            'version': '1.0',
            'entities': [
                {
                    'entity_id': record["entity_file_id"],
                    'entity_name_cn': record["entity_name"],
                    'source_interfaces': record["source_interfaces"],
                    'extraction_timestamp': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
                }
                for record in self.entity_lineage_records
            ]
        }
        
        with open(lineage_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"实体溯源信息已保存: {lineage_file}")
    
    def save_consolidation_stats(
        self,
        original_count: int,
        deduplicated_count: int,
        consolidated_count: int,
        final_count: int,
        merge_rate: float,
        filter_rate: float,
        total_compression_rate: float,
        total_time: float,
        rounds: int
    ) -> None:
        """保存融合统计信息"""
        stats_file = self.output_dir / "consolidation_stats.json"
        
        stats = {
            'version': '1.0',
            'total_time_seconds': round(total_time, 1),
            'original_count': original_count,
            'deduplicated_count': deduplicated_count,
            'consolidated_count': consolidated_count,
            'final_count': final_count,
            'merge_rate': merge_rate,
            'filter_rate': filter_rate,
            'total_compression_rate': total_compression_rate,
            'rounds': rounds
        }
        
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
        
        logger.info(f"融合统计信息已保存: {stats_file}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='逻辑实体融合器 - 方案D')
    parser.add_argument(
        '--repo-root',
        type=str,
        required=True,
        help='仓库根目录路径'
    )
    parser.add_argument(
        '--input-dir',
        type=str,
        default=None,
        help='输入目录（可选，默认从缓存目录读取）'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default=None,
        help='输出目录（可选，默认使用缓存目录）'
    )
    parser.add_argument(
        '--step',
        type=str,
        default='all',
        choices=['rule-dedup', 'basic-merge', 'class-diagram-merge', 'value-evaluation', 'generate-result', 'all'],
        help='执行步骤（可选，默认all）'
    )
    parser.add_argument(
        '--round',
        type=int,
        default=1,
        help='融合轮次（可选，仅在 step=basic-merge 或 class-diagram-merge 时使用）'
    )
    parser.add_argument(
        '--max-rounds',
        type=int,
        default=3,
        help='最大融合轮次（可选，默认3）'
    )
    parser.add_argument(
        '--max-workers',
        type=int,
        default=20,
        help='最大并发数，默认20'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=40,
        help='批次大小，默认40'
    )
    
    args = parser.parse_args()
    
    # 验证仓库根目录
    repo_root = Path(args.repo_root)
    if not repo_root.exists():
        logger.error(f"仓库根目录不存在: {repo_root}")
        sys.exit(1)
    
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    try:
        logger.info("=" * 60)
        logger.info("逻辑实体融合器 - 方案D")
        logger.info("=" * 60)
        logger.info(f"仓库根目录: {repo_root}")
        logger.info(f"执行步骤: {args.step}")
        if args.step in ['basic-merge', 'class-diagram-merge']:
            logger.info(f"融合轮次: {args.round}")
        logger.info("")
        
        # 确定输入目录
        if args.input_dir:
            input_dir = Path(args.input_dir)
        else:
            # 默认路径：实体抽取缓存目录
            input_dir = repo_root / ".cache" / "reverse" / "entities" / "entity-extraction"
        
        if not input_dir.exists():
            logger.error(f"输入目录不存在: {input_dir}")
            sys.exit(1)
        
        # 确定输出目录
        if args.output_dir:
            output_dir = Path(args.output_dir)
        else:
            # 默认路径：实体融合缓存目录
            output_dir = repo_root / ".cache" / "reverse" / "entities" / "entity-consolidation"
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"输入目录: {input_dir}")
        logger.info(f"输出目录: {output_dir}")
        logger.info("")
        
        # 初始化LLM调用器（仅在需要AI分析时）
        llm_caller = None
        if args.step in ['basic-merge', 'class-diagram-merge', 'value-evaluation', 'all']:
            logger.info("初始化LLM调用器...")
            
            # 导入本地工具模块
            try:
                from .utils import ConfigLoader, PromptLoader, LLMCaller
            except ImportError:
                # 如果相对导入失败，尝试绝对导入
                utils_path = Path(__file__).parent
                if str(utils_path) not in sys.path:
                    sys.path.insert(0, str(utils_path))
                from utils import ConfigLoader, PromptLoader, LLMCaller
            
            repo_root_abs = repo_root.resolve()
            
            # 确定提示词模板目录
            prompt_dir = repo_root_abs / "reverse" / "tools" / "prompts"
            
            if not prompt_dir.exists():
                logger.error(f"提示词模板目录不存在: {prompt_dir}")
                sys.exit(1)
            
            logger.info(f"  ├─ Prompt目录: {prompt_dir}")
            
            # 创建配置加载器
            config = ConfigLoader(repo_root=repo_root_abs)
            config_file = repo_root_abs / "reverse" / "tools" / "config.yaml"
            if config_file.exists():
                logger.info(f"  ├─ 配置文件: {config_file}")
            else:
                logger.info(f"  ├─ 使用环境变量配置（配置文件不存在: {config_file}）")
            
            prompt_loader = PromptLoader(str(prompt_dir))
            llm_caller = LLMCaller(config, prompt_loader, repo_root=repo_root_abs)
            
            logger.info(f"  └─ ✓ LLM调用器初始化成功\n")
        
        # 创建融合器
        consolidator = EntityConsolidator(
            llm_caller=llm_caller,
            repo_root=str(repo_root),
            input_dir=str(input_dir),
            output_dir=str(output_dir),
            max_workers=args.max_workers,
            batch_size=args.batch_size
        )
        
        # 加载溯源映射
        logger.info("加载溯源映射...")
        consolidator.load_lineage_map()
        logger.info(f"  └─ ✓ 已加载 {len(consolidator.lineage_map)} 个实体的溯源信息\n")
        
        total_start = time.time()
        
        # 根据步骤执行
        if args.step == 'rule-dedup':
            # 只执行规则去重
            logger.info("执行步骤: 规则去重\n")
            entities = consolidator.load_entities_from_batch_index()
            deduplicated = consolidator.rule_deduplication(entities)
            
            # 保存去重后的实体（临时文件）
            temp_file = output_dir / "deduplicated-entities.json"
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(deduplicated, f, ensure_ascii=False, indent=2)
            logger.info(f"去重后的实体已保存: {temp_file}\n")
            
        elif args.step == 'basic-merge':
            # 只执行基本信息融合（需要从临时文件读取）
            logger.info(f"执行步骤: 基本信息融合（第{args.round}轮）\n")
            # 这里需要从临时文件读取去重后的实体，实际实现中可能需要更复杂的逻辑
            logger.warning("单独执行 basic-merge 步骤需要先执行 rule-dedup，请使用 --step all 执行完整流程")
            
        elif args.step == 'class-diagram-merge':
            # 只执行类图整合（需要从临时文件读取）
            logger.info(f"执行步骤: 类图整合（第{args.round}轮）\n")
            logger.warning("单独执行 class-diagram-merge 步骤需要先执行 basic-merge，请使用 --step all 执行完整流程")
            
        elif args.step == 'value-evaluation':
            # 只执行价值评估（需要从临时文件读取）
            logger.info("执行步骤: 实体价值评估\n")
            logger.warning("单独执行 value-evaluation 步骤需要先执行融合，请使用 --step all 执行完整流程")
            
        elif args.step == 'generate-result':
            # 只生成结果（需要从临时文件读取）
            logger.info("执行步骤: 生成融合结果\n")
            logger.warning("单独执行 generate-result 步骤需要先执行完整融合流程，请使用 --step all 执行完整流程")
            
        elif args.step == 'all':
            # 执行完整流程
            logger.info("执行完整融合流程\n")
            
            # 读取所有实体
            logger.info("步骤1: 读取实体文档...")
            entities = consolidator.load_entities_from_batch_index()
            logger.info(f"  └─ ✓ 读取到 {len(entities)} 个实体\n")
            
            original_count = len(entities)
            
            # 第0步：规则去重
            deduplicated = consolidator.rule_deduplication(entities)
            deduplicated_count = len(deduplicated)
            
            # 多轮融合
            consolidated = consolidator.consolidate_entities(deduplicated, args.max_rounds)
            consolidated_count = len(consolidated)
            rounds = args.max_rounds  # 实际轮数可能更少（如果提前收敛）
            
            # 评估实体价值（过滤低价值实体）
            logger.info("步骤3: 评估实体价值...")
            valuable_entities = consolidator.evaluate_entities(consolidated)
            final_count = len(valuable_entities)
            
            # 生成结果
            logger.info("步骤4: 生成融合结果...")
            consolidator.save_consolidated_entities(valuable_entities)
            consolidator.save_entity_lineage()
            
            # 统计
            total_time = time.time() - total_start
            merge_rate = round((1 - consolidated_count / deduplicated_count) * 100, 2) if deduplicated_count > 0 else 0
            filter_rate = round((1 - final_count / consolidated_count) * 100, 2) if consolidated_count > 0 else 0
            final_rate = round((1 - final_count / original_count) * 100, 2) if original_count > 0 else 0
            
            consolidator.save_consolidation_stats(
                original_count=original_count,
                deduplicated_count=deduplicated_count,
                consolidated_count=consolidated_count,
                final_count=final_count,
                merge_rate=merge_rate,
                filter_rate=filter_rate,
                total_compression_rate=final_rate,
                total_time=total_time,
                rounds=rounds
            )
            
            # 输出最终总结
            logger.info("=" * 60)
            logger.info("全部完成")
            logger.info("=" * 60)
            logger.info(f"总耗时: {total_time:.1f}秒 ({total_time/60:.1f}分钟)")
            logger.info(f"原始实体: {original_count} 个")
            logger.info(f"去重后: {deduplicated_count} 个 (去重率: {round((1-deduplicated_count/original_count)*100, 2)}%)")
            logger.info(f"融合后: {consolidated_count} 个 (融合率: {merge_rate}%)")
            logger.info(f"过滤后: {final_count} 个 (过滤率: {filter_rate}%)")
            logger.info(f"总压缩率: {final_rate}%")
            logger.info(f"输出目录: {output_dir}")
            logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"融合失败: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    sys.exit(main())

