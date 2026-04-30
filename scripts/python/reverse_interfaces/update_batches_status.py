#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量更新批次处理状态工具
批量更新批次映射文件中指定批次的处理状态

兼容Windows和Linux系统
使用方法:
    python update_batches_status.py <repo_root> <batch_updates_json>

参数:
    repo_root: 仓库根目录路径
    batch_updates_json: 批次更新信息的JSON字符串，格式为 [{"batch_number": 1, "status": "completed"}, ...]
"""

import os
import sys
import json
import argparse
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone


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


def update_batch_status(repo_root: str, batch_number: int, status: str) -> bool:
    """更新单个批次的状态（内部函数）"""
    cache_dir = os.path.join(repo_root, '.cache', 'reverse', 'interfaces')
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    updated = False

    # 更新批次映射文件
    batch_mapping_file = os.path.join(cache_dir, 'batch-mapping.json')
    if os.path.exists(batch_mapping_file):
        try:
            batch_mapping = load_json_file(batch_mapping_file)

            for batch_info in batch_mapping.get('batches', []):
                if batch_info.get('batch_number') == batch_number:
                    batch_info['status'] = status
                    batch_info['last_updated'] = timestamp
                    updated = True
                    break

            if updated:
                save_json_file(batch_mapping, batch_mapping_file)
        except Exception as e:
            print(f"警告: 无法更新批次映射文件: {e}", file=sys.stderr)

    # 更新批次详细文件
    batch_details_file = os.path.join(cache_dir, f'batch-details-{batch_number}.json')
    if os.path.exists(batch_details_file):
        try:
            batch_details = load_json_file(batch_details_file)
            batch_details['status'] = status
            batch_details['last_updated'] = timestamp
            save_json_file(batch_details, batch_details_file)
        except Exception as e:
            print(f"警告: 无法更新批次详细文件: {e}", file=sys.stderr)

    # 更新批次状态文件
    batch_status_file = os.path.join(cache_dir, 'interface_scanning-batch-status.json')
    if os.path.exists(batch_status_file):
        try:
            batch_status = load_json_file(batch_status_file)

            # 更新总体状态
            if status == 'completed':
                batch_status['processed_batches'] = batch_status.get('processed_batches', 0) + 1
                batch_status['current_batch'] = batch_number
            elif status == 'failed':
                batch_status['failed_batches'] = batch_status.get('failed_batches', 0) + 1

            batch_status['last_update'] = timestamp

            # 更新批次映射信息
            if 'batch_mappings' in batch_status:
                for batch_mapping in batch_status['batch_mappings']:
                    if batch_mapping.get('batch_number') == batch_number:
                        batch_mapping['status'] = status
                        break

            save_json_file(batch_status, batch_status_file)
        except Exception as e:
            print(f"警告: 无法更新批次状态文件: {e}", file=sys.stderr)

    return updated


def update_batches_status(repo_root: str, batch_updates: List[Dict[Any, Any]]) -> Dict[str, Any]:
    """批量更新批次状态"""
    results = {
        'success': [],
        'failed': []
    }

    for update_info in batch_updates:
        batch_number = update_info.get('batch_number')
        status = update_info.get('status')

        if batch_number is None or not status:
            results['failed'].append({
                'batch_number': batch_number,
                'error': '缺少批次编号或状态'
            })
            continue

        # 验证状态
        valid_statuses = ['pending', 'processing', 'completed', 'failed']
        if status not in valid_statuses:
            results['failed'].append({
                'batch_number': batch_number,
                'error': f'无效的状态 "{status}"'
            })
            continue

        # 更新状态
        try:
            success = update_batch_status(repo_root, batch_number, status)
            if success:
                results['success'].append({
                    'batch_number': batch_number,
                    'status': status
                })
            else:
                results['failed'].append({
                    'batch_number': batch_number,
                    'error': '未找到指定的批次'
                })
        except Exception as e:
            results['failed'].append({
                'batch_number': batch_number,
                'error': str(e)
            })

    return results


def main():
    """主函数"""
    # 兼容两种调用方式：
    # 1) 旧方式（位置参数）：python update_batches_status.py <repo_root> '<json>'
    # 2) 新方式（flag）：python update_batches_status.py --repo-root <repo_root> --batch-updates '<json>'
    parser = argparse.ArgumentParser(
        description='批量更新批次处理状态工具（兼容位置参数与flag参数）',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例（位置参数）:
  python update_batches_status.py /path/to/repo '[{"batch_number": 1, "status": "processing"}]'

示例（flag参数）:
  python update_batches_status.py --repo-root /path/to/repo --batch-updates '[{"batch_number": 1, "status": "processing"}]'
        """.strip()
    )

    parser.add_argument('repo_root_pos', nargs='?', help='仓库根目录路径（位置参数兼容）')
    parser.add_argument('batch_updates_json_pos', nargs='?', help='批次更新JSON字符串（位置参数兼容）')
    parser.add_argument('--repo-root', dest='repo_root_flag', help='仓库根目录路径（flag参数）')
    parser.add_argument(
        '--batch-updates',
        dest='batch_updates_json_flag',
        help='批次更新JSON字符串（flag参数），格式为 [{"batch_number": 1, "status": "completed"}, ...]'
    )

    args = parser.parse_args()

    repo_root: Optional[str] = args.repo_root_flag or args.repo_root_pos
    batch_updates_json: Optional[str] = args.batch_updates_json_flag or args.batch_updates_json_pos

    if not repo_root or not batch_updates_json:
        print("使用方法: python update_batches_status.py <repo_root> <batch_updates_json>", file=sys.stderr)
        print("或: python update_batches_status.py --repo-root <repo_root> --batch-updates <batch_updates_json>", file=sys.stderr)
        print("批次更新JSON格式: [{\"batch_number\": 1, \"status\": \"completed\"}, ...]", file=sys.stderr)
        print("状态选项: pending, processing, completed, failed", file=sys.stderr)
        sys.exit(1)

    # 验证仓库根目录
    if not os.path.exists(repo_root):
        print(f"错误: 仓库根目录不存在 {repo_root}", file=sys.stderr)
        sys.exit(1)

    # 解析批次更新信息
    try:
        batch_updates = json.loads(batch_updates_json)
        if not isinstance(batch_updates, list):
            raise ValueError("批次更新信息必须是数组格式")
    except json.JSONDecodeError as e:
        print(f"错误: 无效的JSON格式: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"错误: 解析批次更新信息时发生错误: {e}", file=sys.stderr)
        sys.exit(1)

    # 批量更新批次状态
    try:
        results = update_batches_status(repo_root, batch_updates)

        # 输出结果
        print(json.dumps(results, ensure_ascii=False))

        # 如果有任何失败，返回非零退出码
        if results['failed']:
            sys.exit(1)

    except Exception as e:
        print(f"批量更新批次状态过程中发生错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()