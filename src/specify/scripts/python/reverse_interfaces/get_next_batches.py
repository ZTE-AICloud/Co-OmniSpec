#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
获取下一个要处理的多个批次工具
从批次映射文件中读取，找出多个状态为"pending"的批次并返回

兼容Windows和Linux系统
使用方法:
    python get_next_batches.py <repo_root> [--batch-count <count>]

参数:
    repo_root: 仓库根目录路径
    --batch-count: 要获取的批次数量（默认5）
"""

import os
import sys
import json
import argparse
from typing import List, Dict, Any


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


def get_next_pending_batches(repo_root: str, batch_count: int = 5) -> List[Dict[Any, Any]]:
    """获取多个待处理的批次"""
    cache_dir = os.path.join(repo_root, '.cache', 'omni-reverse', 'interfaces')
    batch_mapping_file = os.path.join(cache_dir, 'batch-mapping.json')

    # 检查批次映射文件是否存在
    if not os.path.exists(batch_mapping_file):
        print(f"错误: 批次映射文件不存在 {batch_mapping_file}", file=sys.stderr)
        sys.exit(1)

    # 读取批次映射
    batch_mapping = load_json_file(batch_mapping_file)
    batches = batch_mapping.get('batches', [])

    # 查找状态为pending的批次
    pending_batches = []
    for batch in batches:
        if batch.get('status') == 'pending':
            pending_batches.append(batch)
            # 达到指定数量就停止
            if len(pending_batches) >= batch_count:
                break

    return pending_batches


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='获取下一个要处理的多个批次工具')
    parser.add_argument('repo_root', help='仓库根目录路径')
    parser.add_argument('--batch-count', type=int, default=5, help='要获取的批次数量（默认5）')

    args = parser.parse_args()
    repo_root = args.repo_root
    batch_count = args.batch_count

    # 验证仓库根目录
    if not os.path.exists(repo_root):
        print(f"错误: 仓库根目录不存在 {repo_root}", file=sys.stderr)
        sys.exit(1)

    # 获取多个待处理的批次
    try:
        next_batches = get_next_pending_batches(repo_root, batch_count)

        if next_batches:
            # 输出批次信息为JSON格式
            print(json.dumps(next_batches, ensure_ascii=False))
        else:
            # 没有更多批次需要处理
            print("[]")

    except Exception as e:
        print(f"获取批次过程中发生错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()