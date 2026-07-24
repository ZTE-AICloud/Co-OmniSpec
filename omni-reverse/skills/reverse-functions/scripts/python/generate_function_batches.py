#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
功能划分批次生成工具
基于输入列表（--scenario-list）按"批次大小 + Token预算"动态分组，生成批次文件。
供 reverse-functions 对应阶段使用。

兼容 Windows 和 Linux 系统。
使用方法:
    python generate_function_batches.py --repo-root <repo_root> --scenario-list <list_json> [--batch-size <size>] [--max-tokens <tokens>]

参数:
    --repo-root:  仓库根目录路径
    --scenario-list:     场景列表（JSON 格式：数组，或 {"items": [...]} / {"files": [...]}）
    --batch-size: 每批数量（可选，默认 20）
    --max-tokens: 每批最大 Token 数（可选，默认 150000）

产出（写入 {repo_root}/.cache/reverse/functions/）:
    - batch-mapping.json
    - batch-details-{n}.json
    - function_partitioning-batch-status.json
"""
import os
import sys
import json
import argparse
from typing import List, Dict, Any

STAGE = "function_partitioning"


def estimate_tokens_for_item(item) -> int:
    """估算单个条目的 Token 数。若 item 是文件路径则按行数估算，否则给保守值。"""
    if isinstance(item, str) and os.path.exists(item):
        try:
            with open(item, 'r', encoding='utf-8') as f:
                return sum(1 for _ in f) * 5
        except Exception:
            return 1000
    return 1000


def load_list(list_path: str) -> List[Any]:
    """加载输入列表，支持纯数组或 {items/files/scenarios/...: [...]} 形式。"""
    try:
        with open(list_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"错误: 无法读取列表 {list_path}: {e}", file=sys.stderr)
        sys.exit(1)
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ('items', 'files', 'scenarios', 'functions', 'entries'):
            if key in data and isinstance(data[key], list):
                return data[key]
    print(f"错误: 不支持的列表格式 {list_path}", file=sys.stderr)
    sys.exit(1)


def create_batches(items: List[Any], batch_size: int = 20, max_tokens: int = 150000) -> List[Dict[str, Any]]:
    batches = []
    current, current_tokens, batch_number = [], 0, 1
    for item in items:
        item_tokens = estimate_tokens_for_item(item)
        if (len(current) >= batch_size or current_tokens + item_tokens > max_tokens) and current:
            batches.append({
                'batch_number': batch_number,
                'items': current.copy(),
                'item_count': len(current),
                'estimated_tokens': current_tokens,
                'complexity_score': current_tokens / 1000,
                'status': 'pending',
            })
            current, current_tokens, batch_number = [], 0, batch_number + 1
        current.append(item)
        current_tokens += item_tokens
    if current:
        batches.append({
            'batch_number': batch_number,
            'items': current,
            'item_count': len(current),
            'estimated_tokens': current_tokens,
            'complexity_score': current_tokens / 1000,
            'status': 'pending',
        })
    return batches


def save_batch_files(batches, cache_dir):
    mappings = []
    for batch in batches:
        n = batch['batch_number']
        path = os.path.join(cache_dir, f'batch-details-{n}.json')
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(batch, f, ensure_ascii=False, indent=2)
        mappings.append({
            'batch_number': n,
            'batch_file': f'batch-details-{n}.json',
            'status': batch['status'],
            'estimated_tokens': batch['estimated_tokens'],
        })
        print(f"已创建批次文件: {path}")
    return mappings


def main():
    parser = argparse.ArgumentParser(description='功能划分批次生成工具')
    parser.add_argument('--repo-root', required=True, help='仓库根目录路径')
    parser.add_argument('--scenario-list', required=True, help='场景列表（JSON 格式）')
    parser.add_argument('--batch-size', type=int, default=20, help='每批数量（默认 20）')
    parser.add_argument('--max-tokens', type=int, default=150000, help='每批最大 Token 数（默认 150000）')
    args = parser.parse_args()

    if not os.path.exists(args.repo_root):
        print(f"错误: 仓库根目录不存在 {args.repo_root}", file=sys.stderr)
        sys.exit(1)

    cache_dir = os.path.join(args.repo_root, '.cache', 'reverse', 'functions')
    os.makedirs(cache_dir, exist_ok=True)

    list_attr = getattr(args, 'scenario-list'.replace('-', '_'))
    items = load_list(list_attr)
    print(f"找到 {len(items)} 个场景需要处理")
    if not items:
        print("警告: 列表为空", file=sys.stderr)
        sys.exit(0)

    batches = create_batches(items, args.batch_size, args.max_tokens)
    total_batches = len(batches)
    print(f"创建了 {total_batches} 个批次")

    mappings = save_batch_files(batches, cache_dir)

    mapping = {'total_batches': total_batches, 'total_items': len(items),
               'batch_size': args.batch_size, 'batches': mappings}
    mapping_file = os.path.join(cache_dir, 'batch-mapping.json')
    with open(mapping_file, 'w', encoding='utf-8') as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)
    print(f"已创建批次映射文件: {mapping_file}")

    status = {
        'version': '1.1', 'stage': STAGE, 'total_items': len(items),
        'batch_size': args.batch_size, 'total_batches': total_batches,
        'processed_batches': 0, 'current_batch': 0, 'failed_batches': 0,
        'start_time': '', 'last_update': '', 'status': 'initialized',
        'batch_mappings': mappings,
    }
    status_file = os.path.join(cache_dir, f'{STAGE}-batch-status.json')
    with open(status_file, 'w', encoding='utf-8') as f:
        json.dump(status, f, ensure_ascii=False, indent=2)
    print(f"已初始化批次状态文件: {status_file}")
    print(f"批次生成完成，总共创建了 {total_batches} 个批次（共 {len(items)} 个场景）。")


if __name__ == '__main__':
    main()
