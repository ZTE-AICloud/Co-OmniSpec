#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
获取下一个接口批次工具
从批次映射文件中读取批次信息，找出下一个状态为"pending"的批次并返回

兼容Windows和Linux系统
使用方法:
    python get_next_interface_batches.py <repo_root> [--batch-count <count>]

参数:
    repo_root: 仓库根目录路径
    --batch-count: 要获取的批次数量（默认5）
"""

import os
import sys
import json
import argparse
from typing import Dict, Any, List, Optional


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


def get_next_pending_batches(repo_root: str, batch_count: int) -> List[Dict[Any, Any]]:
    """获取下一个待处理的批次
    
    优先返回processing状态的批次（断点续执行场景），
    然后返回pending状态的批次（首次执行场景）
    """
    cache_dir = os.path.join(repo_root, '.cache', 'reverse', 'interfaces')
    # 兼容两种批次映射文件命名：
    # - 新/标准：batch-mapping.json（由 generate_interface_batches.* 生成）
    # - 旧/接口批次工具链：interface-batch-mapping.json（reverse_interfaces 工具链使用）
    interface_batch_mapping_file = os.path.join(cache_dir, 'interface-batch-mapping.json')
    batch_mapping_file = os.path.join(cache_dir, 'batch-mapping.json')

    mapping_file_to_use = None
    # 选择优先级说明：
    # - 若同时存在 batch-mapping.json 与 interface-batch-mapping.json：
    #   - 当 interface-batch-mapping.json 真实用于“接口详情提取阶段”时（batch_file 以 interface-batch-details- 开头），优先使用它
    #   - 若 interface-batch-mapping.json 实际指向 batch-details-*.json（扫描阶段遗留/兼容产物），优先使用 batch-mapping.json，避免误用与重复
    if os.path.exists(interface_batch_mapping_file):
        try:
            legacy_data = load_json_file(interface_batch_mapping_file)
            legacy_batches = legacy_data.get('batches', [])
            legacy_files = []
            for b in legacy_batches:
                if isinstance(b, dict):
                    legacy_files.append(str(b.get('batch_file', '')))
            has_interface_batch_details = any(x.startswith('interface-batch-details-') for x in legacy_files)
            has_scan_batch_details = any(x.startswith('batch-details-') for x in legacy_files)
        except Exception:
            has_interface_batch_details = False
            has_scan_batch_details = False
    else:
        has_interface_batch_details = False
        has_scan_batch_details = False

    if has_interface_batch_details:
        mapping_file_to_use = interface_batch_mapping_file
    elif os.path.exists(batch_mapping_file):
        mapping_file_to_use = batch_mapping_file
        if os.path.exists(interface_batch_mapping_file) and has_scan_batch_details:
            print(
                f"警告: 检测到扫描阶段遗留的 {interface_batch_mapping_file}（指向 batch-details-*.json），已优先使用 {batch_mapping_file}",
                file=sys.stderr
            )
    elif os.path.exists(interface_batch_mapping_file):
        mapping_file_to_use = interface_batch_mapping_file
        if has_scan_batch_details:
            print(
                f"警告: 未找到 {batch_mapping_file}，将回退使用 {interface_batch_mapping_file}",
                file=sys.stderr
            )
    else:
        print(f"错误: 批次映射文件不存在 {interface_batch_mapping_file}", file=sys.stderr)
        print(f"错误: 批次映射文件不存在 {batch_mapping_file}", file=sys.stderr)
        return []

    # 检查批次映射文件是否存在
    if mapping_file_to_use is None:
        return []

    # 读取批次映射
    batch_mapping = load_json_file(mapping_file_to_use)
    batches = batch_mapping.get('batches', [])

    # 优先查找状态为processing的批次（断点续执行场景）
    processing_batches = []
    for batch in batches:
        if batch.get('status') == 'processing':
            processing_batches.append(batch)
            if len(processing_batches) >= batch_count:
                break

    # 如果找到了processing的批次，返回它们
    if processing_batches:
        return processing_batches

    # 如果没有processing的批次，查找状态为pending的批次（首次执行场景）
    pending_batches = []
    for batch in batches:
        if batch.get('status') == 'pending':
            pending_batches.append(batch)
            if len(pending_batches) >= batch_count:
                break

    return pending_batches


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='获取下一个接口批次工具')
    parser.add_argument('repo_root', help='仓库根目录路径')
    parser.add_argument('--batch-count', type=int, default=5, help='要获取的批次数量（默认5）')

    args = parser.parse_args()
    repo_root = args.repo_root
    batch_count = args.batch_count

    # 验证仓库根目录
    if not os.path.exists(repo_root):
        print(f"错误: 仓库根目录不存在 {repo_root}", file=sys.stderr)
        sys.exit(1)

    # 获取下一个待处理的批次
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