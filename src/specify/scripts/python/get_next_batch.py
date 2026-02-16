#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
接口扫描批次信息获取工具
在AI Agent循环处理批次时，获取要处理的批次信息

兼容Windows和Linux系统
使用方法:
    python get_next_batch.py --repo-root <repo_root> --action <action> [--batch-number <number>]

参数:
    --repo-root: 仓库根目录路径
    --action: 操作类型（get-next-batch, update-batch-status, get-batch-info）
    --batch-number: 批次编号（用于更新状态或获取信息时）
    --status: 批次状态（用于更新状态时）
"""
import os
import sys
import json
import argparse
from datetime import datetime, timezone
from typing import Dict, Any, Optional


def load_json_file(file_path: str) -> Dict[Any, Any]:
    """安全加载JSON文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"错误: 无法读取文件 {file_path}: {e}", file=sys.stderr)
        raise


def save_json_file(data: Dict[Any, Any], file_path: str) -> None:
    """安全保存JSON文件"""
    try:
        # 确保目录存在
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"错误: 无法保存文件 {file_path}: {e}", file=sys.stderr)
        raise


def get_next_pending_batch(cache_dir: str) -> Optional[Dict[Any, Any]]:
    """获取下一个待处理的批次"""
    # 读取批次映射文件
    batch_mapping_file = os.path.join(cache_dir, 'batch-mapping.json')
    if not os.path.exists(batch_mapping_file):
        print(f"错误: 批次映射文件不存在 {batch_mapping_file}", file=sys.stderr)
        return None

    batch_mapping = load_json_file(batch_mapping_file)

    # 查找第一个状态为pending的批次
    for batch_info in batch_mapping.get('batches', []):
        if batch_info.get('status') == 'pending':
            return batch_info

    # 如果没有找到pending的批次，查找状态为initialized的批次
    for batch_info in batch_mapping.get('batches', []):
        if batch_info.get('status') == 'initialized':
            return batch_info

    return None


def update_batch_status(cache_dir: str, batch_number: int, status: str) -> bool:
    """更新批次状态"""
    updated = False

    # 更新批次映射文件
    batch_mapping_file = os.path.join(cache_dir, 'batch-mapping.json')
    if os.path.exists(batch_mapping_file):
        try:
            batch_mapping = load_json_file(batch_mapping_file)

            for batch_info in batch_mapping.get('batches', []):
                if batch_info.get('batch_number') == batch_number:
                    batch_info['status'] = status
                    batch_info['last_updated'] = datetime.now(timezone.utc).isoformat()
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
            batch_details['last_updated'] = datetime.now(timezone.utc).isoformat()
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

            if status == 'failed':
                batch_status['failed_batches'] = batch_status.get('failed_batches', 0) + 1

            batch_status['last_update'] = datetime.now(timezone.utc).isoformat()

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


def get_batch_info(cache_dir: str, batch_number: int) -> Optional[Dict[Any, Any]]:
    """获取指定批次的详细信息"""
    batch_details_file = os.path.join(cache_dir, f'batch-details-{batch_number}.json')
    if not os.path.exists(batch_details_file):
        print(f"错误: 批次详细文件不存在 {batch_details_file}", file=sys.stderr)
        return None

    return load_json_file(batch_details_file)


def get_batch_summary(cache_dir: str) -> Dict[Any, Any]:
    """获取批次处理摘要"""
    summary = {
        'total_batches': 0,
        'pending_batches': 0,
        'completed_batches': 0,
        'failed_batches': 0,
        'processing_batches': 0
    }

    # 读取批次映射文件
    batch_mapping_file = os.path.join(cache_dir, 'batch-mapping.json')
    if os.path.exists(batch_mapping_file):
        try:
            batch_mapping = load_json_file(batch_mapping_file)
            summary['total_batches'] = batch_mapping.get('total_batches', 0)

            for batch_info in batch_mapping.get('batches', []):
                status = batch_info.get('status', 'unknown')
                if status == 'pending':
                    summary['pending_batches'] += 1
                elif status == 'completed':
                    summary['completed_batches'] += 1
                elif status == 'failed':
                    summary['failed_batches'] += 1
                elif status == 'processing':
                    summary['processing_batches'] += 1
        except Exception as e:
            print(f"警告: 无法读取批次映射文件: {e}", file=sys.stderr)

    return summary


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='接口扫描批次信息获取工具')
    parser.add_argument('--repo-root', required=True, help='仓库根目录路径')
    parser.add_argument('--action', required=True,
                       choices=['get-next-batch', 'update-batch-status', 'get-batch-info', 'get-summary'],
                       help='操作类型')
    parser.add_argument('--batch-number', type=int, help='批次编号')
    parser.add_argument('--status', help='批次状态（用于更新状态时）')

    args = parser.parse_args()

    repo_root = args.repo_root
    action = args.action
    batch_number = args.batch_number
    status = args.status

    # 验证仓库根目录
    if not os.path.exists(repo_root):
        print(f"错误: 仓库根目录不存在 {repo_root}", file=sys.stderr)
        sys.exit(1)

    cache_dir = os.path.join(repo_root, '.cache', 'omni-reverse', 'interfaces')

    try:
        if action == 'get-next-batch':
            batch_info = get_next_pending_batch(cache_dir)
            if batch_info:
                print(json.dumps(batch_info, ensure_ascii=False))
            else:
                print("{}")  # 返回空对象表示没有更多批次

        elif action == 'update-batch-status':
            if batch_number is None or status is None:
                print("错误: 更新批次状态需要提供 --batch-number 和 --status 参数", file=sys.stderr)
                sys.exit(1)

            success = update_batch_status(cache_dir, batch_number, status)
            result = {'success': success, 'batch_number': batch_number, 'status': status}
            print(json.dumps(result, ensure_ascii=False))

        elif action == 'get-batch-info':
            if batch_number is None:
                print("错误: 获取批次信息需要提供 --batch-number 参数", file=sys.stderr)
                sys.exit(1)

            batch_info = get_batch_info(cache_dir, batch_number)
            if batch_info:
                print(json.dumps(batch_info, ensure_ascii=False))
            else:
                print("{}")  # 返回空对象表示未找到批次

        elif action == 'get-summary':
            summary = get_batch_summary(cache_dir)
            print(json.dumps(summary, ensure_ascii=False))

    except Exception as e:
        print(f"处理过程中发生错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()