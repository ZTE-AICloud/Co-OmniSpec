#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量更新接口批次状态工具
更新接口批次映射文件和批次状态文件中的批次状态

兼容Windows和Linux系统
使用方法:
    python update_interface_batches_status.py <repo_root> --batch-updates '<batch_updates_json>'

参数:
    repo_root: 仓库根目录路径
    --batch-updates: 批次更新信息的JSON字符串
"""

import os
import sys
import json
import argparse
from typing import Dict, Any
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


def update_single_batch_status(repo_root: str, batch_number: int, status: str) -> bool:
    """更新单个批次状态"""
    cache_dir = os.path.join(repo_root, '.cache', 'reverse', 'interfaces')
    timestamp = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')

    updated = False

    # 更新批次映射文件
    batch_mapping_file = os.path.join(cache_dir, 'interface-batch-mapping.json')
    if os.path.exists(batch_mapping_file):
        batch_mapping = load_json_file(batch_mapping_file)

        for batch_info in batch_mapping.get('batches', []):
            if batch_info.get('batch_number') == batch_number:
                batch_info['status'] = status
                batch_info['last_updated'] = timestamp
                updated = True
                break

        if updated:
            save_json_file(batch_mapping, batch_mapping_file)

    # 更新批次详细文件
    batch_details_file = os.path.join(cache_dir, f'interface-batch-details-{batch_number}.json')
    if os.path.exists(batch_details_file):
        batch_details = load_json_file(batch_details_file)
        batch_details['status'] = status
        batch_details['last_updated'] = timestamp
        save_json_file(batch_details, batch_details_file)

    # 更新批次状态文件
    batch_status_file = os.path.join(cache_dir, 'interface_detail-batch-status.json')
    if os.path.exists(batch_status_file):
        batch_status = load_json_file(batch_status_file)

        # 更新统计信息
        if status == 'completed':
            batch_status['processed_batches'] = batch_status.get('processed_batches', 0) + 1
            batch_status['current_batch'] = batch_number
        elif status == 'failed':
            batch_status['failed_batches'] = batch_status.get('failed_batches', 0) + 1

        # 更新批次映射信息
        for batch_mapping in batch_status.get('batch_mappings', []):
            if batch_mapping.get('batch_number') == batch_number:
                batch_mapping['status'] = status
                break

        batch_status['last_update'] = timestamp
        save_json_file(batch_status, batch_status_file)

    return updated


def update_batches_status(repo_root: str, batch_updates: str) -> Dict[str, Any]:
    """批量更新批次状态"""
    try:
        updates = json.loads(batch_updates)
    except json.JSONDecodeError as e:
        print(f"错误: 无效的JSON格式: {e}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(updates, list):
        print("错误: 批次更新信息必须是数组格式", file=sys.stderr)
        sys.exit(1)

    results = []
    success_count = 0
    failed_count = 0

    for update_item in updates:
        batch_number = update_item.get('batch_number')
        status = update_item.get('status')

        # 验证必需字段
        if batch_number is None or status is None:
            results.append({
                "batch_number": batch_number,
                "error": "缺少批次编号或状态",
                "success": False
            })
            failed_count += 1
            continue

        # 验证状态
        valid_statuses = ['pending', 'processing', 'completed', 'failed']
        if status not in valid_statuses:
            results.append({
                "batch_number": batch_number,
                "error": f"无效的状态 '{status}'",
                "success": False
            })
            failed_count += 1
            continue

        # 更新批次状态
        success = update_single_batch_status(repo_root, batch_number, status)

        if success:
            results.append({
                "batch_number": batch_number,
                "status": status,
                "success": True
            })
            success_count += 1
        else:
            results.append({
                "batch_number": batch_number,
                "error": "未找到指定的批次",
                "success": False
            })
            failed_count += 1

    return {
        "success": success_count,
        "failed": failed_count,
        "details": results
    }


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='批量更新接口批次状态工具')
    parser.add_argument('repo_root', help='仓库根目录路径')
    parser.add_argument('--batch-updates', required=True, help='批次更新信息的JSON字符串')

    args = parser.parse_args()
    repo_root = args.repo_root
    batch_updates = args.batch_updates

    # 验证仓库根目录
    if not os.path.exists(repo_root):
        print(f"错误: 仓库根目录不存在 {repo_root}", file=sys.stderr)
        sys.exit(1)

    # 更新批次状态
    try:
        result = update_batches_status(repo_root, batch_updates)
        print(json.dumps(result, ensure_ascii=False))

        # 如果有任何失败，返回非零退出码
        if result['failed'] > 0:
            sys.exit(1)

    except Exception as e:
        print(f"更新批次状态过程中发生错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()