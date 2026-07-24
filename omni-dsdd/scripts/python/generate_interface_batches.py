#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
接口扫描批次生成工具
基于AI Agent的各种规则过滤后，把要检索的文件基于文件数量进行分批，生成批次文件

兼容Windows和Linux系统
使用方法:
    python generate_interface_batches.py --repo-root <repo_root> --file-list <file_list_json> [--batch-size <size>] [--max-tokens <tokens>]

参数:
    --repo-root: 仓库根目录路径
    --file-list: 要处理的文件列表（JSON格式）
    --batch-size: 每批文件数量（可选，默认20）
    --max-tokens: 每批最大Token数（可选，默认150000）
"""
import os
import sys
import json
import argparse
from typing import List, Dict, Any


def estimate_tokens_for_file(file_path: str) -> int:
    """估算文件的Token数量（简化估算：每行约5个tokens）"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = sum(1 for line in f)
        return lines * 5
    except Exception:
        # 如果无法读取文件，给出一个保守估计
        return 1000


def load_file_list(file_list_path: str) -> List[str]:
    """加载文件列表"""
    try:
        with open(file_list_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 支持多种格式的文件列表
        if isinstance(data, list):
            return data
        elif isinstance(data, dict) and 'files' in data:
            return data['files']
        else:
            raise ValueError("Invalid file list format")
    except Exception as e:
        print(f"错误: 无法读取文件列表 {file_list_path}: {e}", file=sys.stderr)
        raise


def create_batches(files: List[str], batch_size: int = 20, max_tokens: int = 150000) -> List[Dict[str, Any]]:
    """创建批次"""
    batches = []
    current_batch = []
    current_tokens = 0
    batch_number = 1

    for file_path in files:
        # 估算文件Token数量
        file_tokens = estimate_tokens_for_file(file_path)

        # 检查是否需要创建新批次
        if (len(current_batch) >= batch_size or
            current_tokens + file_tokens > max_tokens) and current_batch:
            # 创建当前批次
            batch_info = {
                'batch_number': batch_number,
                'files': current_batch.copy(),
                'estimated_tokens': current_tokens,
                'complexity_score': current_tokens / 1000,  # 简化的复杂度评分
                'status': 'pending'
            }
            batches.append(batch_info)

            # 重置批次
            current_batch = []
            current_tokens = 0
            batch_number += 1

        # 添加文件到当前批次（使用对象格式，包含path和status）
        file_entry = {
            'path': file_path,
            'status': 'pending'
        }
        current_batch.append(file_entry)
        current_tokens += file_tokens

    # 处理最后一个批次
    if current_batch:
        batch_info = {
            'batch_number': batch_number,
            'files': current_batch,
            'estimated_tokens': current_tokens,
            'complexity_score': current_tokens / 1000,
            'status': 'pending'
        }
        batches.append(batch_info)

    return batches


def save_batch_files(batches: List[Dict[str, Any]], cache_dir: str) -> List[Dict[str, Any]]:
    """保存批次文件"""
    batch_mappings = []

    for batch in batches:
        batch_number = batch['batch_number']
        batch_file_name = f'batch-details-{batch_number}.json'
        batch_file_path = os.path.join(cache_dir, batch_file_name)

        try:
            # 保存批次详细文件
            with open(batch_file_path, 'w', encoding='utf-8') as f:
                json.dump(batch, f, ensure_ascii=False, indent=2)

            # 添加到映射列表
            batch_mappings.append({
                'batch_number': batch_number,
                'batch_file': batch_file_name,
                'status': batch['status'],
                'estimated_tokens': batch['estimated_tokens']
            })

            print(f"已创建批次文件: {batch_file_path}")
        except Exception as e:
            print(f"错误: 无法保存批次文件 {batch_file_path}: {e}", file=sys.stderr)
            raise

    return batch_mappings


def save_batch_mapping(batch_mappings: List[Dict[str, Any]], cache_dir: str, total_batches: int) -> None:
    """保存批次映射文件"""
    batch_mapping = {
        'total_batches': total_batches,
        'batch_size': len(batch_mappings),
        'batches': batch_mappings
    }

    batch_mapping_file = os.path.join(cache_dir, 'batch-mapping.json')

    try:
        with open(batch_mapping_file, 'w', encoding='utf-8') as f:
            json.dump(batch_mapping, f, ensure_ascii=False, indent=2)
        print(f"已创建批次映射文件: {batch_mapping_file}")
    except Exception as e:
        print(f"错误: 无法保存批次映射文件 {batch_mapping_file}: {e}", file=sys.stderr)
        raise


def cleanup_legacy_interface_batch_mapping(cache_dir: str) -> None:
    """
    清理扫描阶段遗留/兼容的 interface-batch-mapping.json（仅当它实际指向 batch-details-*.json 时）。

    说明：
    - interface-batch-mapping.json 正常用于“接口详情提取阶段”（对应 interface-batch-details-*.json）
    - 若其 batches[].batch_file 指向 batch-details-*.json，则属于旧/兼容产物，会与 batch-mapping.json 重复并造成工具选择混乱
    """
    legacy_path = os.path.join(cache_dir, "interface-batch-mapping.json")
    if not os.path.exists(legacy_path):
        return

    try:
        with open(legacy_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        batches = data.get("batches", [])
        if not isinstance(batches, list) or not batches:
            return
        batch_files = [b.get("batch_file", "") for b in batches if isinstance(b, dict)]
        if batch_files and all(isinstance(x, str) and x.startswith("batch-details-") for x in batch_files):
            os.remove(legacy_path)
            print("已清理遗留的 interface-batch-mapping.json（扫描阶段重复映射）", file=sys.stderr)
    except Exception:
        # 不阻塞主流程
        return


def initialize_batch_status(cache_dir: str, total_items: int, total_batches: int) -> None:
    """初始化批次状态文件"""
    batch_status_file = os.path.join(cache_dir, 'interface_scanning-batch-status.json')

    batch_status = {
        'version': '1.1',
        'stage': 'interface_scanning',
        'total_items': total_items,
        'batch_size': 20,  # 默认批次大小
        'total_batches': total_batches,
        'processed_batches': 0,
        'current_batch': 0,
        'failed_batches': 0,
        'start_time': '',
        'last_update': '',
        'status': 'initialized',
        'batch_mappings': []  # 这将在后续步骤中填充
    }

    try:
        with open(batch_status_file, 'w', encoding='utf-8') as f:
            json.dump(batch_status, f, ensure_ascii=False, indent=2)
        print(f"已初始化批次状态文件: {batch_status_file}")
    except Exception as e:
        print(f"错误: 无法初始化批次状态文件 {batch_status_file}: {e}", file=sys.stderr)
        raise


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='接口扫描批次生成工具')
    parser.add_argument('--repo-root', required=True, help='仓库根目录路径')
    parser.add_argument('--file-list', required=True, help='要处理的文件列表（JSON格式）')
    parser.add_argument('--batch-size', type=int, default=20, help='每批文件数量（默认20）')
    parser.add_argument('--max-tokens', type=int, default=150000, help='每批最大Token数（默认150000）')

    args = parser.parse_args()

    repo_root = args.repo_root
    file_list_path = args.file_list
    batch_size = args.batch_size
    max_tokens = args.max_tokens

    # 验证仓库根目录
    if not os.path.exists(repo_root):
        print(f"错误: 仓库根目录不存在 {repo_root}", file=sys.stderr)
        sys.exit(1)

    # 创建缓存目录
    cache_dir = os.path.join(repo_root, '.cache', 'reverse', 'interfaces')
    os.makedirs(cache_dir, exist_ok=True)

    try:
        # 加载文件列表
        files = load_file_list(file_list_path)
        print(f"找到 {len(files)} 个文件需要处理")

        if not files:
            print("警告: 文件列表为空", file=sys.stderr)
            sys.exit(0)

        # 创建批次
        batches = create_batches(files, batch_size, max_tokens)
        total_batches = len(batches)
        print(f"创建了 {total_batches} 个批次")

        # 保存批次文件
        batch_mappings = save_batch_files(batches, cache_dir)

        # 保存批次映射文件
        save_batch_mapping(batch_mappings, cache_dir, total_batches)

        # 清理可能存在的遗留 interface-batch-mapping.json（避免与 batch-mapping.json 重复）
        cleanup_legacy_interface_batch_mapping(cache_dir)

        # 初始化批次状态文件
        initialize_batch_status(cache_dir, len(files), total_batches)

        print(f"批次生成完成，总共创建了 {total_batches} 个批次")

    except Exception as e:
        print(f"批次生成过程中发生错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()