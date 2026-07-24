#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
接口批次创建工具
基于接口清单文件，按“批次大小 + Token预算”动态分组接口，降低单次请求上下文超限风险。

兼容Windows和Linux系统
使用方法:
    python create_interface_batches.py <repo_root>

参数:
    repo_root: 仓库根目录路径
"""

import os
import sys
import json
import argparse
from typing import Dict, Any, List, Tuple, Optional
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


def check_existing_batches(cache_dir: str) -> bool:
    """检查是否已有有效的批次文件"""
    batch_mapping_file = os.path.join(cache_dir, 'interface-batch-mapping.json')
    batch_status_file = os.path.join(cache_dir, 'interface_detail-batch-status.json')

    # 检查批次映射文件是否存在
    if not os.path.exists(batch_mapping_file):
        return False

    # 检查批次状态文件是否存在
    if not os.path.exists(batch_status_file):
        return False

    try:
        # 读取批次映射文件
        batch_mapping = load_json_file(batch_mapping_file)

        # 检查批次映射文件是否有效
        total_batches = batch_mapping.get('total_batches', 0)
        if total_batches == 0:
            return False

        # 检查是否有任何已完成的批次
        batches = batch_mapping.get('batches', [])
        completed_batches = sum(1 for b in batches if b.get('status') == 'completed')
        if completed_batches > 0:
            print(f"检测到已有 {completed_batches} 个已完成的批次，支持断点续执行", file=sys.stdout)
            return True

        # 检查是否有正在进行的批次
        processing_batches = sum(1 for b in batches if b.get('status') == 'processing')
        if processing_batches > 0:
            print(f"检测到已有 {processing_batches} 个正在进行的批次，支持断点续执行", file=sys.stdout)
            return True

        # 检查是否有待处理的批次
        pending_batches = sum(1 for b in batches if b.get('status') == 'pending')
        if pending_batches > 0:
            print(f"检测到已有 {pending_batches} 个待处理的批次，支持断点续执行", file=sys.stdout)
            return True

        return False
    except Exception:
        # 如果读取失败，认为批次文件无效
        return False


def estimate_interface_tokens(repo_root: str, interface_item: Dict[str, Any]) -> int:
    """
    估算单接口分析的Token消耗。
    规则（保守估算）：
    - 基础开销：1200
    - source_file 行数 * 2（上限 16000）
    """
    base = 1200
    source_file = str(interface_item.get("source_file", "")).strip()
    if not source_file:
        return base

    abs_path = source_file if os.path.isabs(source_file) else os.path.join(repo_root, source_file)
    if not os.path.exists(abs_path):
        return base + 800

    try:
        with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
            line_count = sum(1 for _ in f)
        return min(base + line_count * 2, 16000)
    except Exception:
        return base + 800


def build_batches_by_budget(
    repo_root: str,
    interfaces: List[Dict[str, Any]],
    batch_size: int,
    max_tokens_per_batch: int
) -> List[Tuple[List[Dict[str, Any]], int]]:
    """按批次大小和Token预算构建批次"""
    batches: List[Tuple[List[Dict[str, Any]], int]] = []
    current_items: List[Dict[str, Any]] = []
    current_tokens = 0

    for item in interfaces:
        item_tokens = estimate_interface_tokens(repo_root, item)
        # 如果单接口估算已超过预算，仍单独成批，避免卡死
        if item_tokens > max_tokens_per_batch:
            if current_items:
                batches.append((current_items, current_tokens))
                current_items = []
                current_tokens = 0
            batches.append(([item], item_tokens))
            continue

        will_exceed_size = len(current_items) >= batch_size
        will_exceed_tokens = (current_tokens + item_tokens) > max_tokens_per_batch

        if current_items and (will_exceed_size or will_exceed_tokens):
            batches.append((current_items, current_tokens))
            current_items = [item]
            current_tokens = item_tokens
        else:
            current_items.append(item)
            current_tokens += item_tokens

    if current_items:
        batches.append((current_items, current_tokens))

    return batches


def interface_id_sort_key(item: Dict[str, Any]) -> Tuple[int, str]:
    """
    按 interface_id 的数字部分升序排序，确保阶段4生成顺序与 interface-list.json 序号一致。
    支持接口ID形态：API_001 / API-001 / 其他包含数字的形式。
    """
    interface_id = str(item.get("interface_id", "")).strip()
    # 抽取连续数字；若没有数字则排到后面
    num: Optional[int] = None
    current = ""
    for ch in interface_id:
        if ch.isdigit():
            current += ch
        elif current:
            break
    if current:
        try:
            num = int(current)
        except Exception:
            num = None
    return (num if num is not None else 10**18, interface_id)


def create_interface_batches(
    repo_root: str,
    batch_size: int = 2,
    max_tokens_per_batch: int = 12000,
    force: bool = False
) -> None:
    """创建接口批次文件"""
    cache_dir = os.path.join(repo_root, '.cache', 'reverse', 'interfaces')
    output_dir = os.path.join(repo_root, 'omni-doc', 'interfaces')

    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)

    # 检查是否已有有效的批次文件
    if not force:
        if check_existing_batches(cache_dir):
            print("已有有效的批次文件，跳过创建。如需强制重新生成，请使用 --force 参数", file=sys.stdout)
            return

    interface_list_file = os.path.join(cache_dir, 'interface-list.json')

    # 检查接口清单文件是否存在
    if not os.path.exists(interface_list_file):
        print(f"错误: 接口清单文件不存在 {interface_list_file}", file=sys.stderr)
        sys.exit(1)

    # 读取接口清单
    interface_data = load_json_file(interface_list_file)
    interfaces = interface_data.get('interfaces', [])

    if not interfaces:
        print("警告: 接口清单为空", file=sys.stderr)
        return

    # 接口清单的 interface_id 序号必须被固定并在后续继承：
    # 阶段4“按顺序生成文件”通过“按 interface_id 升序组织批次”实现。
    if not isinstance(interfaces, list):
        print("错误: interface-list.json interfaces 不是数组", file=sys.stderr)
        sys.exit(1)
    interface_ids = [str(i.get("interface_id", "")).strip() for i in interfaces if isinstance(i, dict)]
    non_empty_ids = [iid for iid in interface_ids if iid]
    dup_check = len(non_empty_ids) != len(set(non_empty_ids))
    if dup_check:
        print("错误: interface-list.json 存在重复 interface_id，不允许继续生成批次（否则会重复文件/冲突）。", file=sys.stderr)
        sys.exit(1)

    interfaces_sorted = sorted(interfaces, key=interface_id_sort_key)
    grouped = build_batches_by_budget(repo_root, interfaces_sorted, batch_size, max_tokens_per_batch)
    batches = []
    for idx, (batch_interfaces, estimated_tokens) in enumerate(grouped, start=1):
        batch_number = idx
        complexity_score = estimated_tokens / 1000.0

        batch = {
            "batch_number": batch_number,
            "interfaces": batch_interfaces,
            "estimated_tokens": estimated_tokens,
            "complexity_score": complexity_score,
            "status": "pending"
        }

        batches.append(batch)

        # 创建批次详细文件
        batch_details_file = os.path.join(cache_dir, f'interface-batch-details-{batch_number}.json')
        save_json_file(batch, batch_details_file)
        print(f"已创建批次详细文件: {batch_details_file}")

    # 创建批次映射文件
    batch_mapping = {
        "total_batches": len(batches),
        "batch_size": batch_size,
        "batches": [
            {
                "batch_number": batch["batch_number"],
                "batch_file": f"interface-batch-details-{batch['batch_number']}.json",
                "status": "pending"
            }
            for batch in batches
        ]
    }

    batch_mapping_file = os.path.join(cache_dir, 'interface-batch-mapping.json')
    save_json_file(batch_mapping, batch_mapping_file)
    print(f"已创建批次映射文件: {batch_mapping_file}")

    # 初始化批次状态文件
    utc_now = datetime.now(timezone.utc)
    batch_status = {
        "version": "1.1",
        "stage": "interface_detail_analysis",
        "total_items": len(interfaces),
        "batch_size": batch_size,
        "total_batches": len(batches),
        "processed_batches": 0,
        "current_batch": 0,
        "failed_batches": 0,
        "start_time": utc_now.isoformat().replace('+00:00', 'Z'),
        "last_update": utc_now.isoformat().replace('+00:00', 'Z'),
        "status": "initialized",
        "batch_mappings": [
            {
                "batch_number": batch["batch_number"],
                "batch_file": f"interface-batch-details-{batch['batch_number']}.json",
                "status": "pending",
                "estimated_tokens": batch["estimated_tokens"]
            }
            for batch in batches
        ]
    }

    batch_status_file = os.path.join(cache_dir, 'interface_detail-batch-status.json')
    save_json_file(batch_status, batch_status_file)
    print(f"已初始化批次状态文件: {batch_status_file}")
    print(f"批次创建完成，总共创建了 {len(batches)} 个批次")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='创建接口批次文件工具')
    parser.add_argument('repo_root', help='仓库根目录路径')
    parser.add_argument('--force', action='store_true', help='强制重新生成批次文件，即使已存在')
    parser.add_argument('--batch-size', type=int, default=int(os.getenv('INTERFACE_DETAIL_BATCH_SIZE', '2')),
                        help='每批最大接口数量（默认2，可通过环境变量 INTERFACE_DETAIL_BATCH_SIZE 设置）')
    parser.add_argument('--max-tokens-per-batch', type=int, default=int(os.getenv('INTERFACE_DETAIL_MAX_TOKENS', '12000')),
                        help='每批最大估算Token（默认12000，可通过环境变量 INTERFACE_DETAIL_MAX_TOKENS 设置）')

    args = parser.parse_args()
    repo_root = args.repo_root
    force = args.force
    batch_size = max(1, args.batch_size)
    max_tokens_per_batch = max(2000, args.max_tokens_per_batch)

    # 验证仓库根目录
    if not os.path.exists(repo_root):
        print(f"错误: 仓库根目录不存在 {repo_root}", file=sys.stderr)
        sys.exit(1)

    # 创建接口批次
    try:
        create_interface_batches(
            repo_root,
            batch_size=batch_size,
            max_tokens_per_batch=max_tokens_per_batch,
            force=force
        )
    except Exception as e:
        print(f"创建接口批次过程中发生错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()