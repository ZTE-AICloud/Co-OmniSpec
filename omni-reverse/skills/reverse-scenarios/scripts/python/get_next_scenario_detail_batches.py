#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
获取下一批待处理场景批次工具
从批次状态文件中获取下一批待处理的场景批次（最多 batch-count 个）。

优先返回 processing 状态的批次（断点续执行场景）；若无，则返回 pending 状态的批次。
注意：本工具只读取并返回批次信息，不修改状态。状态的 processing/completed/failed
变更由 update_scenario_detail_batches_status.py 负责。

兼容 Windows 和 Linux 系统。

使用方法:
    python get_next_scenario_detail_batches.py <repo_root> [--batch-count <count>]

参数:
    repo_root:   仓库根目录路径
    --batch-count: 要获取的批次数量（默认 3）
"""
import os
import sys
import json
import argparse
from typing import Dict, Any, List


def load_json_file(file_path: str) -> Dict[Any, Any]:
    """安全加载 JSON 文件"""
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


def get_next_pending_batches(repo_root: str, batch_count: int = 3) -> List[Dict[str, Any]]:
    """获取下一批待处理的场景批次。

    优先返回 processing 批次（断点续执行），其次返回 pending 批次。
    """
    cache_dir = os.path.join(repo_root, '.cache', 'reverse', 'scenarios')
    batch_status_file = os.path.join(cache_dir, 'scenario_detail-batch-status.json')

    if not os.path.exists(batch_status_file):
        print(f"错误: 批次状态文件不存在 {batch_status_file}（请先执行 create_scenario_detail_batches.py）",
              file=sys.stderr)
        sys.exit(1)

    status_data = load_json_file(batch_status_file)
    batch_mappings = status_data.get('batch_mappings', [])

    # 优先查找 processing 批次（断点续执行）
    processing_batches: List[Dict[str, Any]] = []
    for batch in batch_mappings:
        if batch.get('status') == 'processing':
            processing_batches.append(batch)
            if len(processing_batches) >= batch_count:
                break
    if processing_batches:
        return processing_batches

    # 其次查找 pending 批次
    pending_batches: List[Dict[str, Any]] = []
    for batch in batch_mappings:
        if batch.get('status') == 'pending':
            pending_batches.append(batch)
            if len(pending_batches) >= batch_count:
                break
    return pending_batches


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='获取下一批待处理场景批次工具')
    parser.add_argument('--repo-root', required=True, dest='repo_root', help='仓库根目录路径')
    parser.add_argument('--batch-count', type=int, default=3, help='要获取的批次数量（默认 3）')

    args = parser.parse_args()
    repo_root = args.repo_root
    batch_count = args.batch_count

    if not os.path.exists(repo_root):
        print(f"错误: 仓库根目录不存在 {repo_root}", file=sys.stderr)
        sys.exit(1)

    try:
        next_batches = get_next_pending_batches(repo_root, batch_count)
        if next_batches:
            print(json.dumps(next_batches, ensure_ascii=False))
        else:
            print("[]")
    except Exception as e:
        print(f"获取批次过程中发生错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
