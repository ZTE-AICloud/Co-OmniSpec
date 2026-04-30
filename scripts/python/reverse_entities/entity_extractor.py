#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从接口聚合文件中抽取逻辑实体

从接口聚合文件目录中的MD文件读取接口信息，
使用LLM抽取出符合要求的逻辑实体，生成实体文档。

兼容Windows和Linux系统
使用方法:
    python entity_extractor.py --repo-root <repo_root> [--batch-id <batch_id>] [--interface-aggregation-dir <dir>] [--user-terminology <file>] [--output-dir <dir>] [--max-workers <num>]

参数:
    repo_root: 仓库根目录路径（必需）
    batch_id: 批次ID（可选，如果指定则只处理该批次）
    interface-aggregation-dir: 接口聚合文件目录（可选，默认从缓存目录读取）
    user-terminology: 用户术语文件路径（可选）
    output-dir: 输出目录（可选，默认使用缓存目录）
    max-workers: 最大并发数（可选，默认20）
"""

import json
import logging
import os
import sys
import threading
import time
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import re

logger = logging.getLogger(__name__)


class InterfaceEntityExtractor:
    """从接口聚合文件抽取逻辑实体"""
    
    def __init__(
        self,
        llm_caller,
        repo_root: str,
        interface_aggregation_dir: str,
        output_dir: str,
        user_terminology_file: Optional[str] = None,
        max_workers: int = 20,
        batch_id: Optional[int] = None
    ):
        """
        初始化抽取器
        
        Args:
            llm_caller: LLM调用器（在main函数中动态导入）
            repo_root: 仓库根目录
            interface_aggregation_dir: 接口聚合文件目录
            output_dir: 输出目录
            user_terminology_file: 用户术语文件路径（可选）
            max_workers: 最大并发数，默认20
            batch_id: 批次ID（可选，如果指定则只处理该批次）
        """
        self.llm_caller = llm_caller
        self.repo_root = Path(repo_root)
        self.interface_aggregation_dir = Path(interface_aggregation_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.lineage_dir = self.output_dir / "lineage"
        self.lineage_dir.mkdir(parents=True, exist_ok=True)
        self.max_workers = max_workers
        self.batch_id = batch_id
        self.log_lock = threading.Lock()  # 用于保护日志输出
        self.processed_files = []  # 记录处理过的文件信息，用于更新批次索引
        
        # 加载用户规范术语
        self.user_terminology = self._load_user_terminology(user_terminology_file)
    
    def _load_user_terminology(self, terminology_file: Optional[str] = None) -> str:
        """
        加载用户规范术语文件
        
        Args:
            terminology_file: 用户术语文件路径（可选）
            
        Returns:
            如果文件存在，返回格式化的规范术语要求字符串；否则返回空字符串
        """
        # 确定术语文件路径
        if terminology_file:
            terminology_path = Path(terminology_file)
        else:
            # 默认路径：{REPO_ROOT}/user_input/user_terminology.md
            terminology_path = self.repo_root / "user_input" / "user_terminology.md"
        
        if not terminology_path.exists():
            logger.info(f"用户术语文件不存在: {terminology_path}，将不使用规范术语")
            return ""
        
        try:
            with open(terminology_path, 'r', encoding='utf-8') as f:
                terminology_content = f.read().strip()
            
            if not terminology_content:
                logger.info("用户术语文件为空，将不使用规范术语")
                return ""
            
            logger.info(f"已加载用户规范术语文件: {terminology_path}")
            
            # 构建规范术语要求
            terminology_requirement = f"""
### 规范术语要求

**重要**：在描述逻辑实体时，请优先使用以下用户定义的规范术语。当代码中的概念与规范术语表中的术语匹配时，必须使用规范术语进行描述。

{terminology_content}

**使用规则**：
1. 业务名称（entity_name_cn）必须优先使用规范术语
2. 关键职责描述中涉及的概念应使用规范术语
3. 如果代码中的英文名称在术语表的"代码块"列中，对应的中文描述必须使用"术语"列的名称
"""
            return terminology_requirement
            
        except Exception as e:
            logger.warning(f"加载用户术语文件失败: {e}，将不使用规范术语")
            return ""
    
    def extract_entities(self) -> Dict[str, Any]:
        """
        批量抽取实体
        
        Returns:
            抽取统计信息
        """
        logger.info("=" * 60)
        logger.info("开始从接口聚合文件抽取逻辑实体")
        logger.info("=" * 60)
        logger.info(f"仓库根目录: {self.repo_root}")
        logger.info(f"接口聚合文件目录: {self.interface_aggregation_dir}")
        logger.info(f"输出目录: {self.output_dir}")
        if self.batch_id:
            logger.info(f"批次ID: {self.batch_id}")
        logger.info("")
        
        # 获取要处理的文件列表
        if self.batch_id:
            # 批次处理模式：从批次索引文件读取文件列表
            files_to_process = self._get_batch_files()
        else:
            # 单批处理模式：扫描目录获取所有MD文件
            files_to_process = list(self.interface_aggregation_dir.glob("*.md"))
        
        if not files_to_process:
            logger.warning("没有找到要处理的MD文件")
            return {"total": 0, "success": 0, "failed": 0, "entities": []}
        
        logger.info(f"发现 {len(files_to_process)} 个MD文件\n")
        
        success_count = 0
        failed_count = 0
        failed_files = []
        all_entities = []
        processed_files = []  # 记录所有处理过的文件信息，用于更新批次索引
        
        start_time = time.time()
        
        # 使用线程池并发处理
        logger.info(f"使用并发处理 (最大并发数: {self.max_workers})\n")
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有任务
            futures = {
                executor.submit(self._process_single_file, md_file, idx, len(files_to_process)): idx
                for idx, md_file in enumerate(files_to_process, 1)
            }
            
            # 处理完成的任务
            for future in as_completed(futures):
                idx = futures[future]
                try:
                    result = future.result()
                    processed_files.append(result)  # 记录处理结果
                    if result['success']:
                        success_count += 1
                        if 'entities' in result:
                            all_entities.extend(result['entities'])
                    else:
                        failed_count += 1
                        failed_files.append({
                            "file": result['file_name'],
                            "error": result['error']
                        })
                except Exception as e:
                    failed_count += 1
                    with self.log_lock:
                        logger.error(f"  ✗ 任务 {idx} 处理异常: {e}")
                    failed_files.append({
                        "file": f"unknown_{idx}",
                        "error": str(e)
                    })
                    processed_files.append({
                        'success': False,
                        'file_name': f"unknown_{idx}",
                        'error': str(e)
                    })
        
        # 输出统计
        total_time = time.time() - start_time
        avg_time = total_time / len(files_to_process) if files_to_process else 0
        
        logger.info("=" * 60)
        logger.info("抽取完成")
        logger.info("=" * 60)
        logger.info(f"总耗时: {total_time:.1f}秒 ({total_time/60:.1f}分钟)")
        logger.info(f"平均耗时: {avg_time:.1f}秒/文件")
        logger.info("")
        logger.info(f"抽取结果:")
        logger.info(f"  ├─ 成功: {success_count} 个")
        logger.info(f"  └─ 失败: {failed_count} 个")
        
        if failed_files:
            logger.warning("\n失败的文件列表：")
            for ff in failed_files:
                logger.warning(f"  ✗ {ff['file']}")
                logger.warning(f"    原因: {ff['error']}")
        
        logger.info(f"\n✓ 文档已保存到: {self.output_dir}")
        
        stats = {
            "total": len(files_to_process),
            "success": success_count,
            "failed": failed_count,
            "total_time_seconds": total_time,
            "average_time_seconds": avg_time,
            "failed_files": failed_files,
            "entities": all_entities
        }
        
        # 保存处理过的文件信息，用于更新批次索引
        self.processed_files = processed_files
        
        return stats
    
    def _get_batch_files(self) -> List[Path]:
        """
        从批次索引文件获取要处理的文件列表
        
        Returns:
            文件路径列表
        """
        # 读取批次索引文件
        cache_dir = self.repo_root / ".cache" / "reverse" / "entities" / "entity-extraction"
        index_file = cache_dir / "entities-index.json"
        
        if not index_file.exists():
            logger.error(f"批次索引文件不存在: {index_file}")
            return []
        
        try:
            with open(index_file, 'r', encoding='utf-8') as f:
                index_data = json.load(f)
            
            # 查找指定批次
            batches = index_data.get('batches', [])
            batch_info = None
            for batch in batches:
                if batch.get('batch_id') == self.batch_id:
                    batch_info = batch
                    break
            
            if not batch_info:
                logger.error(f"未找到批次ID为 {self.batch_id} 的批次信息")
                return []
            
            # 获取批次文件列表
            source_files = batch_info.get('source_files', [])
            files_to_process = []
            
            for source_file in source_files:
                # source_file 可能是相对路径或绝对路径
                if Path(source_file).is_absolute():
                    file_path = Path(source_file)
                else:
                    # 相对路径：从接口聚合文件目录解析
                    file_path = self.interface_aggregation_dir / Path(source_file).name
            
                if file_path.exists():
                    files_to_process.append(file_path)
                else:
                    logger.warning(f"批次文件不存在: {file_path}")
            
            return files_to_process
            
        except Exception as e:
            logger.error(f"读取批次索引文件失败: {e}")
            return []
    
    def _process_single_file(self, md_file: Path, idx: int, total: int) -> Dict[str, Any]:
        """
        处理单个文件（用于并发执行）
        
        Args:
            md_file: 要处理的MD文件
            idx: 文件索引
            total: 总文件数
            
        Returns:
            处理结果字典，包含 success, file_name, error, entities 等字段
        """
        file_name = md_file.name
        file_start = time.time()
        
        with self.log_lock:
            logger.info(f"[{idx}/{total}] 处理文件: {file_name}")
        
        try:
            # 读取文件内容
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()
            interface_ids = self._extract_interface_ids(content)
            
            with self.log_lock:
                logger.info(f"  [{idx}/{total}] ├─ 文件大小: {len(content)} 字符")
                logger.info(f"  [{idx}/{total}] ├─ 调用LLM抽取实体...")
            
            # 调用LLM抽取实体
            entities_doc = self._extract_from_file(content)
            entities_info = self._parse_entities_from_doc(entities_doc, interface_ids)
            
            # 保存溯源元数据
            self._save_lineage_metadata(
                output_filename=f"ENTITIES-{md_file.name}",
                source_file=str(md_file.name),
                interface_ids=interface_ids,
                entities_info=entities_info
            )
            
            # 保存文档
            output_file = self.output_dir / f"ENTITIES-{file_name}"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(entities_doc)
            
            file_time = time.time() - file_start
            with self.log_lock:
                logger.info(f"  [{idx}/{total}] └─ ✓ 成功 (耗时: {file_time:.1f}秒, 实体数: {len(entities_info)})")
            
            return {
                'success': True,
                'file_name': file_name,
                'time': file_time,
                'entities': entities_info
            }
            
        except Exception as e:
            file_time = time.time() - file_start
            with self.log_lock:
                logger.error(f"  [{idx}/{total}] └─ ✗ 失败: {e} (耗时: {file_time:.1f}秒)")
            
            return {
                'success': False,
                'file_name': file_name,
                'error': str(e),
                'time': file_time
            }
    
    def _extract_from_file(self, content: str) -> str:
        """
        从单个文件内容中抽取实体
        
        Args:
            content: 文件内容
            
        Returns:
            实体文档内容
        """
        # 调用LLM，传入规范术语要求（如果存在）
        response = self.llm_caller.call_with_template(
            'entity_extraction_from_interface',
            interface_content=content,
            terminology_requirement=self.user_terminology
        )
        
        return response

    def _extract_interface_ids(self, content: str) -> List[str]:
        """从接口聚合文件内容中提取接口ID"""
        pattern = re.compile(r'- \*\*接口ID\*\*:\s*(API-\d+)', re.IGNORECASE)
        ids = pattern.findall(content)
        # 去重并保持排序
        seen = []
        for api_id in ids:
            api_id_upper = api_id.strip().upper()
            if api_id_upper not in seen:
                seen.append(api_id_upper)
        return seen

    def _parse_entities_from_doc(self, doc: str, interface_ids: List[str]) -> List[Dict[str, Any]]:
        """从LLM输出的实体文档中解析实体信息"""
        if not doc:
            return []

        sections = re.split(r'\n## 逻辑实体 \d+:', doc)
        entities = []
        for index, block in enumerate(sections[1:], start=1):
            entity_info = self._parse_entity_block(block)
            if not entity_info:
                continue
            entity_info['index'] = index
            entity_info['interfaces'] = interface_ids
            entities.append(entity_info)
        return entities

    def _parse_entity_block(self, block: str) -> Dict[str, Any]:
        """解析单个实体块，提取实体标识和标题"""
        lines = block.strip().split('\n')
        if not lines:
            return {}

        entity_title = lines[0].strip()
        basic_info_match = re.search(
            r'### 基本信息\n(.*?)(?:\n###|\Z)',
            block,
            re.DOTALL
        )

        entity_id = ""
        if basic_info_match:
            entity_id = self._extract_field(basic_info_match.group(1), '实体标识')

        return {
            "entity_id": entity_id.strip(),
            "title": entity_title
        } if entity_id else {}

    def _extract_field(self, text: str, field_name: str) -> str:
        """提取基本信息字段"""
        pattern = rf'- \*\*{field_name}\*\*:\s*(.+?)(?=\n-|\n\n|\Z)'
        match = re.search(pattern, text, re.DOTALL)
        return match.group(1).strip() if match else ''

    def _save_lineage_metadata(
        self,
        output_filename: str,
        source_file: str,
        interface_ids: List[str],
        entities_info: List[Dict[str, Any]]
    ) -> None:
        """保存接口与实体的溯源元数据"""
        lineage_file = self.lineage_dir / f"{Path(output_filename).stem}.json"
        data = {
            "source_file": source_file,
            "output_entities_file": output_filename,
            "interfaces": interface_ids,
            "entities": [
                {
                    "entity_id": entity.get("entity_id", ""),
                    "title": entity.get("title", ""),
                    "index": entity.get("index", 0),
                    "interfaces": entity.get("interfaces", interface_ids)
                }
                for entity in entities_info if entity.get("entity_id")
            ]
        }

        with open(lineage_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def update_batch_index(self, stats: Dict[str, Any], processed_files: List[Dict[str, Any]]) -> None:
        """
        更新批次结果索引文件
        
        Args:
            stats: 抽取统计信息
            processed_files: 已处理的文件信息列表，每个元素包含 file_name, entities 等字段
        """
        if not self.batch_id:
            # 非批次处理模式，不需要更新索引
            return
        
        cache_dir = self.repo_root / ".cache" / "reverse" / "entities" / "entity-extraction"
        index_file = cache_dir / "entities-index.json"
        
        if not index_file.exists():
            logger.warning(f"批次索引文件不存在: {index_file}，无法更新")
            return
        
        try:
            # 读取现有索引
            with open(index_file, 'r', encoding='utf-8') as f:
                index_data = json.load(f)
            
            # 查找并更新批次信息
            batches = index_data.get('batches', [])
            batch_updated = False
            
            for batch in batches:
                if batch.get('batch_id') == self.batch_id:
                    # 更新批次状态
                    batch['status'] = 'completed' if stats['failed'] == 0 else 'failed'
                    batch['timestamp'] = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
                    
                    # 收集实体文件列表和溯源文件列表
                    entity_files = []
                    lineage_files = []
                    entity_count = 0
                    
                    # 基于实际处理的文件更新索引
                    for file_info in processed_files:
                        if file_info.get('success'):
                            file_name = file_info.get('file_name', '')
                            entity_file_name = f"ENTITIES-{file_name}"
                            lineage_file_name = f"{Path(file_name).stem}.json"
                            
                            # 检查文件是否存在
                            entity_file_path = self.output_dir / entity_file_name
                            lineage_file_path = self.lineage_dir / lineage_file_name
                            
                            if entity_file_path.exists():
                                entity_files.append(f"entity-extraction/{entity_file_name}")
                                # 统计实体数量
                                entities = file_info.get('entities', [])
                                entity_count += len(entities)
                            
                            if lineage_file_path.exists():
                                lineage_files.append(f"entity-extraction/lineage/{lineage_file_name}")
                    
                    batch['entity_files'] = entity_files
                    batch['lineage_files'] = lineage_files
                    batch['entity_count'] = entity_count
                    
                    # 更新总实体数（重新计算所有已完成的批次）
                    total_entities = sum(b.get('entity_count', 0) for b in batches if 'entity_count' in b)
                    index_data['total_entities'] = total_entities
                    
                    batch_updated = True
                    break
            
            if batch_updated:
                # 保存更新后的索引
                with open(index_file, 'w', encoding='utf-8') as f:
                    json.dump(index_data, f, ensure_ascii=False, indent=2)
                logger.info(f"已更新批次 {self.batch_id} 的索引信息")
            else:
                logger.warning(f"未找到批次ID为 {self.batch_id} 的批次信息")
                
        except Exception as e:
            logger.error(f"更新批次索引文件失败: {e}")


def load_json_file(file_path: str) -> Dict[Any, Any]:
    """安全加载JSON文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"错误: 文件不存在 {file_path}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"错误: JSON格式错误 {file_path}: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"错误: 无法读取文件 {file_path}: {e}", file=sys.stderr)
        sys.exit(1)


def save_json_file(data: Dict[Any, Any], file_path: str) -> None:
    """安全保存JSON文件"""
    try:
        # 确保目录存在
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"错误: 无法保存文件 {file_path}: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='从接口聚合文件抽取逻辑实体')
    parser.add_argument(
        '--repo-root',
        type=str,
        required=True,
        help='仓库根目录路径'
    )
    parser.add_argument(
        '--batch-id',
        type=int,
        default=None,
        help='批次ID（可选，如果指定则只处理该批次）'
    )
    parser.add_argument(
        '--interface-aggregation-dir',
        type=str,
        default=None,
        help='接口聚合文件目录（可选，默认从缓存目录读取）'
    )
    parser.add_argument(
        '--user-terminology',
        type=str,
        default=None,
        help='用户术语文件路径（可选，默认使用 {REPO_ROOT}/user_input/user_terminology.md）'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default=None,
        help='输出目录（可选，默认使用 {REPO_ROOT}/.cache/reverse/entities/entity-extraction/）'
    )
    parser.add_argument(
        '--max-workers',
        type=int,
        default=20,
        help='最大并发数，默认20'
    )
    
    args = parser.parse_args()
    
    # 验证仓库根目录
    repo_root = Path(args.repo_root)
    if not repo_root.exists():
        print(f"错误: 仓库根目录不存在: {repo_root}", file=sys.stderr)
        sys.exit(1)
    
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    try:
        logger.info("=" * 60)
        logger.info("实体抽取器")
        logger.info("=" * 60)
        logger.info(f"仓库根目录: {repo_root}")
        logger.info("")
        
        # 确定接口聚合文件目录
        if args.interface_aggregation_dir:
            interface_aggregation_dir = Path(args.interface_aggregation_dir)
        else:
            # 默认路径：从接口反构的缓存目录读取
            interface_aggregation_dir = repo_root / ".cache" / "reverse" / "interfaces" / "interface-aggregation"
        
        if not interface_aggregation_dir.exists():
            logger.error(f"接口聚合文件目录不存在: {interface_aggregation_dir}")
            sys.exit(1)
        
        # 确定输出目录
        if args.output_dir:
            output_dir = Path(args.output_dir)
        else:
            # 默认路径：实体抽取缓存目录
            output_dir = repo_root / ".cache" / "reverse" / "entities" / "entity-extraction"
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"接口聚合文件目录: {interface_aggregation_dir}")
        logger.info(f"输出目录: {output_dir}")
        if args.batch_id:
            logger.info(f"批次ID: {args.batch_id}")
        logger.info("")
        
        # 初始化LLM调用器
        logger.info("步骤1: 初始化LLM调用器...")
        
        # 使用独立的工具模块（不依赖 reverse 目录的代码结构）
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
        
        # 确定提示词模板目录（从 reverse/tools/prompts 读取，但不依赖其代码）
        prompt_dir = repo_root_abs / "reverse" / "tools" / "prompts"
        
        if not prompt_dir.exists():
            logger.error(f"提示词模板目录不存在: {prompt_dir}")
            sys.exit(1)
        
        logger.info(f"  ├─ Prompt目录: {prompt_dir}")
        
        # 创建配置加载器（使用独立工具模块）
        config = ConfigLoader(repo_root=repo_root_abs)
        config_file = repo_root_abs / "reverse" / "tools" / "config.yaml"
        if config_file.exists():
            logger.info(f"  ├─ 配置文件: {config_file}")
        else:
            logger.info(f"  ├─ 使用环境变量配置（配置文件不存在: {config_file}）")
        
        prompt_loader = PromptLoader(str(prompt_dir))
        llm_caller = LLMCaller(config, prompt_loader, repo_root=repo_root_abs)
        
        logger.info(f"  └─ ✓ LLM调用器初始化成功\n")
        
        # 创建抽取器
        logger.info("步骤2: 创建实体抽取器...")
        extractor = InterfaceEntityExtractor(
            llm_caller=llm_caller,
            repo_root=str(repo_root),
            interface_aggregation_dir=str(interface_aggregation_dir),
            output_dir=str(output_dir),
            user_terminology_file=args.user_terminology,
            max_workers=args.max_workers,
            batch_id=args.batch_id
        )
        logger.info(f"  ├─ 最大并发数: {args.max_workers}")
        logger.info("  └─ ✓ 抽取器已创建\n")
        
        # 抽取实体
        logger.info("步骤3: 批量抽取逻辑实体...\n")
        stats = extractor.extract_entities()
        
        # 更新批次索引（如果是批次处理模式）
        if args.batch_id:
            logger.info("\n步骤4: 更新批次结果索引...")
            extractor.update_batch_index(stats, extractor.processed_files)
            logger.info("  ✓ 批次索引已更新")
        
        # 保存统计信息
        logger.info("\n步骤5: 保存统计信息...")
        stats_file = output_dir / "extraction_stats.json"
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
        
        logger.info(f"  ✓ 统计信息已保存: {stats_file}")
        
        # 输出最终总结
        logger.info("\n" + "=" * 60)
        logger.info("全部完成！")
        logger.info("=" * 60)
        logger.info(f"成功处理 {stats['success']} 个文件")
        if stats['failed'] > 0:
            logger.warning(f"失败 {stats['failed']} 个")
        logger.info(f"文档目录: {output_dir}")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"抽取失败: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()