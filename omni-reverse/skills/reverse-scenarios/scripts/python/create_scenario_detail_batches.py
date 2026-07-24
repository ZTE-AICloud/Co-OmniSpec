#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
单场景批次创建工具
基于场景清单（scenario-list.json），按"每批5个场景"动态分组，生成批次文件，
供 reverse-scenarios 阶段3（单场景文档生成）的批处理调度使用。

兼容 Windows 和 Linux 系统。

使用方法:
    python create_scenario_detail_batches.py <repo_root> [--force]

参数:
    repo_root: 仓库根目录路径
    --force:   强制重新生成批次文件，即使已存在

产出（写入 {repo_root}/.cache/reverse/scenarios/）:
    - scenario-batch-mapping.json       批次映射（含 total_batches、各批次基本信息）
    - scenario_detail-batch-status.json 批次状态（初始化为 pending）
    - scenario-batch-details-{n}.json   每个批次的详细场景列表
"""
import os
import sys
import json
import argparse
from typing import Dict, Any, List

# 场景每批默认大小（reverse-scenarios 阶段3 约定：>5 个场景走分批，每批5个）
DEFAULT_BATCH_SIZE = 5


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


def save_json_file(data: Dict[Any, Any], file_path: str) -> None:
    """安全保存 JSON 文件"""
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"错误: 无法保存文件 {file_path}: {e}", file=sys.stderr)
        sys.exit(1)


def is_valid_batch_mapping(mapping: Dict[Any, Any]) -> bool:
    """检查批次映射文件是否有效（包含批次信息）"""
    if not isinstance(mapping, dict):
        return False
    batches = mapping.get('batches', [])
    return isinstance(batches, list) and len(batches) > 0


def create_batches(scenarios: List[Dict[Any, Any]], batch_size: int = DEFAULT_BATCH_SIZE) -> List[Dict[str, Any]]:
    """将场景列表按 batch_size 切分为多个批次"""
    batches = []
    for idx in range(0, len(scenarios), batch_size):
        chunk = scenarios[idx: idx + batch_size]
        batch_number = (idx // batch_size) + 1
        batches.append({
            'batch_number': batch_number,
            'scenarios': chunk,
            'scenario_count': len(chunk),
            'status': 'pending',
        })
    return batches


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='单场景批次创建工具')
    parser.add_argument('--repo-root', required=True, dest='repo_root', help='仓库根目录路径')
    parser.add_argument('--force', action='store_true', help='强制重新生成批次文件，即使已存在')
    parser.add_argument('--batch-size', type=int, default=DEFAULT_BATCH_SIZE,
                        help=f'每批场景数量（默认 {DEFAULT_BATCH_SIZE}）')

    args = parser.parse_args()
    repo_root = args.repo_root
    force = args.force
    batch_size = args.batch_size

    # 验证仓库根目录
    if not os.path.exists(repo_root):
        print(f"错误: 仓库根目录不存在 {repo_root}", file=sys.stderr)
        sys.exit(1)

    cache_dir = os.path.join(repo_root, '.cache', 'reverse', 'scenarios')
    os.makedirs(cache_dir, exist_ok=True)

    batch_mapping_file = os.path.join(cache_dir, 'scenario-batch-mapping.json')
    batch_status_file = os.path.join(cache_dir, 'scenario_detail-batch-status.json')

    # 前置检查：批次映射已存在且有效时跳过创建（除非 --force）
    if not force and os.path.exists(batch_mapping_file):
        existing = load_json_file(batch_mapping_file)
        if is_valid_batch_mapping(existing):
            total = existing.get('total_batches', len(existing.get('batches', [])))
            print(f"批次映射文件已存在且有效，跳过创建（共 {total} 个批次）。如需重新生成请加 --force。")
            return

    # 读取场景清单
    scenario_list_file = os.path.join(cache_dir, 'scenario-list.json')
    if not os.path.exists(scenario_list_file):
        print(f"错误: 场景清单文件不存在 {scenario_list_file}", file=sys.stderr)
        sys.exit(1)

    scenario_data = load_json_file(scenario_list_file)
    scenarios = scenario_data.get('scenarios', [])
    total_scenarios = len(scenarios)

    if total_scenarios == 0:
        print("警告: 场景清单为空，无需创建批次", file=sys.stderr)
        sys.exit(0)

    # 创建批次
    batches = create_batches(scenarios, batch_size)
    total_batches = len(batches)

    # 写每个批次的详细文件 + 收集映射摘要
    batch_mappings: List[Dict[str, Any]] = []
    for batch in batches:
        batch_number = batch['batch_number']
        batch_details_file = os.path.join(cache_dir, f'scenario-batch-details-{batch_number}.json')
        save_json_file(batch, batch_details_file)
        print(f"已创建批次详细文件: {batch_details_file}")
        batch_mappings.append({
            'batch_number': batch_number,
            'batch_file': f'scenario-batch-details-{batch_number}.json',
            'scenario_count': batch['scenario_count'],
            'status': batch['status'],
        })

    # 写批次映射文件
    mapping = {
        'total_batches': total_batches,
        'total_scenarios': total_scenarios,
        'batch_size': batch_size,
        'batches': batch_mappings,
    }
    save_json_file(mapping, batch_mapping_file)
    print(f"已创建批次映射文件: {batch_mapping_file}")

    # 初始化批次状态文件
    status = {
        'version': '1.1',
        'stage': 'scenario_detail',
        'total_items': total_scenarios,
        'batch_size': batch_size,
        'total_batches': total_batches,
        'processed_batches': 0,
        'current_batch': 0,
        'failed_batches': 0,
        'start_time': '',
        'last_update': '',
        'status': 'initialized',
        'batch_mappings': batch_mappings,
    }
    save_json_file(status, batch_status_file)
    print(f"已初始化批次状态文件: {batch_status_file}")

    print(f"批次生成完成，总共创建了 {total_batches} 个批次（共 {total_scenarios} 个场景）。")


if __name__ == '__main__':
    main()
