#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
更新场景批次状态工具
根据传入的批次更新信息（JSON），批量更新场景批次的处理状态。

会同步更新：
  - scenario_detail-batch-status.json 中的 batch_mappings 状态与计数
  - 对应的 scenario-batch-details-{n}.json 中的 status 字段

兼容 Windows 和 Linux 系统。

使用方法:
    python update_scenario_detail_batches_status.py <repo_root> --batch-updates '<batch_updates_json>'

参数:
    repo_root:     仓库根目录路径
    --batch-updates: 批次更新信息的 JSON 字符串，例如：
                     '[{"batch_number": 1, "status": "completed"}, {"batch_number": 2, "status": "failed"}]'

合法状态：pending / processing / completed / failed
"""
import os
import sys
import json
import argparse
from datetime import datetime, timezone
from typing import Dict, Any, List

VALID_STATUSES = {'pending', 'processing', 'completed', 'failed'}


def load_json_file(file_path: str) -> Dict[Any, Any]:
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
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"错误: 无法保存文件 {file_path}: {e}", file=sys.stderr)
        sys.exit(1)


def update_single_batch_status(repo_root: str, batch_number: int, status: str) -> bool:
    """更新单个批次的 status：同步状态文件、映射与批次详情文件。"""
    if status not in VALID_STATUSES:
        print(f"错误: 非法状态 '{status}'（合法: {sorted(VALID_STATUSES)}）", file=sys.stderr)
        return False

    cache_dir = os.path.join(repo_root, '.cache', 'reverse', 'scenarios')
    batch_status_file = os.path.join(cache_dir, 'scenario_detail-batch-status.json')

    if not os.path.exists(batch_status_file):
        print(f"错误: 批次状态文件不存在 {batch_status_file}", file=sys.stderr)
        return False

    batch_status = load_json_file(batch_status_file)
    now = datetime.now(timezone.utc).isoformat()

    # 更新 batch_mappings 中对应批次的状态
    found = False
    for batch_info in batch_status.get('batch_mappings', []):
        if batch_info.get('batch_number') == batch_number:
            batch_info['status'] = status
            if status == 'processing':
                batch_info['start_time'] = now
            elif status in ('completed', 'failed'):
                batch_info['end_time'] = now
            found = True
            break

    if not found:
        print(f"警告: 未在状态文件中找到批次 {batch_number}", file=sys.stderr)
        return False

    # 更新汇总计数
    if status == 'processing':
        batch_status['current_batch'] = batch_number
    elif status == 'completed':
        batch_status['processed_batches'] = batch_status.get('processed_batches', 0) + 1
        batch_status['current_batch'] = 0
    elif status == 'failed':
        batch_status['failed_batches'] = batch_status.get('failed_batches', 0) + 1
    batch_status['last_update'] = now
    batch_status['status'] = 'in_progress'

    save_json_file(batch_status, batch_status_file)

    # 同步更新批次详情文件中的 status
    batch_details_file = os.path.join(cache_dir, f'scenario-batch-details-{batch_number}.json')
    if os.path.exists(batch_details_file):
        details = load_json_file(batch_details_file)
        details['status'] = status
        if status == 'processing':
            details['start_time'] = now
        elif status in ('completed', 'failed'):
            details['end_time'] = now
        save_json_file(details, batch_details_file)

    return True


def update_batches_status(repo_root: str, batch_updates: str) -> Dict[str, Any]:
    """批量更新批次状态，返回结果汇总。"""
    try:
        updates: List[Dict[str, Any]] = json.loads(batch_updates)
    except json.JSONDecodeError as e:
        print(f"错误: batch-updates JSON 解析失败: {e}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(updates, list):
        print("错误: batch-updates 必须是 JSON 数组", file=sys.stderr)
        sys.exit(1)

    results: List[Dict[str, Any]] = []
    success_count = 0
    for item in updates:
        batch_number = item.get('batch_number')
        status = item.get('status')
        if batch_number is None or status is None:
            results.append({'batch_number': batch_number, 'status': status, 'success': False,
                            'message': '缺少 batch_number 或 status'})
            continue
        ok = update_single_batch_status(repo_root, int(batch_number), str(status))
        results.append({'batch_number': int(batch_number), 'status': status, 'success': ok})
        if ok:
            success_count += 1

    return {'total': len(updates), 'success': success_count, 'results': results}


def main():
    parser = argparse.ArgumentParser(description='更新场景批次状态工具')
    parser.add_argument('--repo-root', required=True, dest='repo_root', help='仓库根目录路径')
    parser.add_argument('--batch-updates', required=True, help='批次更新信息的JSON字符串')
    args = parser.parse_args()

    if not os.path.exists(args.repo_root):
        print(f"错误: 仓库根目录不存在 {args.repo_root}", file=sys.stderr)
        sys.exit(1)

    try:
        result = update_batches_status(args.repo_root, args.batch_updates)
        print(json.dumps(result, ensure_ascii=False))
    except Exception as e:
        print(f"更新批次状态过程中发生错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
