#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
场景清单批次合并工具
自动合并所有批次场景清单文件，生成最终的场景清单

兼容Windows和Linux系统
使用方法:
    python merge_scenario_results.py <repo_root>

参数:
    repo_root: 仓库根目录路径
"""

import os
import sys
import json
from datetime import datetime, timezone
from typing import Dict, Any


def load_json_file(file_path: str) -> Dict[Any, Any]:
    """安全加载JSON文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
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


def merge_batch_files(repo_root: str) -> Dict[Any, Any]:
    """合并所有批次文件"""
    cache_dir = os.path.join(repo_root, '.cache', 'omni-reverse', 'scenarios')

    # 读取批次映射文件
    batch_mapping_file = os.path.join(cache_dir, 'batch-mapping.json')
    if not os.path.exists(batch_mapping_file):
        print(f"错误: 批次映射文件不存在 {batch_mapping_file}", file=sys.stderr)
        sys.exit(1)

    batch_mapping = load_json_file(batch_mapping_file)

    # 初始化合并结果
    merged_scenarios = []
    scenario_counter = 1  # 用于生成全局唯一的场景ID
    seen_scenarios = set()  # 用于去重

    # 按顺序处理所有批次
    for batch_info in batch_mapping.get('batches', []):
        batch_file = batch_info.get('batch_file', '')
        if not batch_file:
            continue

        # 从batch-details文件名构造scenario-list-batch文件名
        # batch-details-X.json -> scenario-list-batch-X.json
        if batch_file.startswith('batch-details-'):
            scenario_list_file = batch_file.replace('batch-details-', 'scenario-list-batch-')
        else:
            scenario_list_file = batch_file

        batch_file_path = os.path.join(cache_dir, scenario_list_file)
        if not os.path.exists(batch_file_path):
            print(f"警告: 场景清单批次文件不存在 {batch_file_path}", file=sys.stderr)
            continue

        # 读取批次数据
        batch_data = load_json_file(batch_file_path)
        batch_scenarios = batch_data.get('scenarios', [])

        # 合并场景数据并重新编号
        for scenario in batch_scenarios:
            # 使用场景名称和源文件作为去重键
            scenario_key = (
                scenario.get('scenario_name', ''),
                tuple(sorted(scenario.get('source_files', [])))
            )

            # 如果场景已存在，跳过（去重）
            if scenario_key in seen_scenarios:
                continue

            seen_scenarios.add(scenario_key)

            # 生成全局唯一的场景ID
            scenario['scenario_id'] = f"SCN-{scenario_counter:03d}"
            merged_scenarios.append(scenario)
            scenario_counter += 1

    # 生成最终结果
    total_scenarios = len(merged_scenarios)

    # 计算统计数据
    summary = {
        'by_domain': {},
        'by_type': {},
        'by_priority': {}
    }

    for scenario in merged_scenarios:
        # 按业务领域统计
        business_domain = scenario.get('business_domain', '未知')
        summary['by_domain'][business_domain] = summary['by_domain'].get(business_domain, 0) + 1

        # 按场景类型统计
        scenario_type = scenario.get('scenario_type', '未知')
        summary['by_type'][scenario_type] = summary['by_type'].get(scenario_type, 0) + 1

        # 按优先级统计
        priority = scenario.get('priority', '未知')
        summary['by_priority'][priority] = summary['by_priority'].get(priority, 0) + 1

    # 构造最终结果
    utc_now = datetime.now(timezone.utc)
    result = {
        'version': '1.0',
        'generated_at': utc_now.isoformat().replace('+00:00', 'Z'),
        'scan_scope': repo_root,
        'total_scenarios': total_scenarios,
        'metadata': {
            'total_scenarios': total_scenarios,
            'scan_time': utc_now.isoformat().replace('+00:00', 'Z'),
            'source': 'scenario_scanning_stage',
            'confidence_threshold': 0.8
        },
        'scenarios': merged_scenarios,
        'summary': summary
    }

    return result


def main():
    """主函数"""
    if len(sys.argv) != 2:
        print("使用方法: python merge_scenario_results.py <repo_root>", file=sys.stderr)
        sys.exit(1)

    repo_root = sys.argv[1]

    # 验证仓库根目录
    if not os.path.exists(repo_root):
        print(f"错误: 仓库根目录不存在 {repo_root}", file=sys.stderr)
        sys.exit(1)

    # 执行合并
    try:
        result = merge_batch_files(repo_root)

        # 保存结果 - 与批次文件在同一目录下
        output_file = os.path.join(repo_root, '.cache', 'omni-reverse', 'scenarios', 'scenario-list.json')
        save_json_file(result, output_file)

        print(f"成功合并 {result['total_scenarios']} 个场景到 {output_file}")

    except Exception as e:
        print(f"合并过程中发生错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()

