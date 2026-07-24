#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
单场景文档生成进度跟踪工具
统计场景清单中各状态（pending/processing/completed/failed）的场景数量与处理进度，
供 reverse-scenarios 阶段3（单场景文档生成）的批处理调度使用。

兼容 Windows 和 Linux 系统。

使用方法:
    python get_scenario_detail_progress.py <repo_root> [--format <format>]

参数:
    repo_root: 仓库根目录路径
    --format:  输出格式 (json/text)，默认为 text
"""
import os
import sys
import json
import argparse
from typing import Dict, Any


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


def calculate_processing_progress(repo_root: str) -> Dict[str, Any]:
    """计算单场景文档生成进度"""
    cache_dir = os.path.join(repo_root, '.cache', 'reverse', 'scenarios')
    scenario_list_file = os.path.join(cache_dir, 'scenario-list.json')

    # 检查场景清单文件是否存在
    if not os.path.exists(scenario_list_file):
        print(f"错误: 场景清单文件不存在 {scenario_list_file}", file=sys.stderr)
        sys.exit(1)

    # 读取场景清单
    scenario_data = load_json_file(scenario_list_file)
    scenarios = scenario_data.get('scenarios', [])

    # 初始化计数器
    total_scenarios = len(scenarios)
    pending_count = 0
    processing_count = 0
    completed_count = 0
    failed_count = 0

    # 统计各种状态的场景数量
    for scenario in scenarios:
        status = scenario.get('processing_status', 'pending')
        if status == 'pending':
            pending_count += 1
        elif status == 'processing':
            processing_count += 1
        elif status == 'completed':
            completed_count += 1
        elif status == 'failed':
            failed_count += 1

    # 计算进度百分比
    processed_count = completed_count + failed_count
    if total_scenarios > 0:
        progress_percentage = (processed_count / total_scenarios) * 100
    else:
        progress_percentage = 0

    # 是否存在断点续执行（有 processing 状态的场景）
    has_interrupted = processing_count > 0

    # 构造进度信息
    progress_info = {
        'total_scenarios': total_scenarios,
        'pending_count': pending_count,
        'processing_count': processing_count,
        'completed_count': completed_count,
        'failed_count': failed_count,
        'processed_count': processed_count,
        'progress_percentage': round(progress_percentage, 2),
        'has_interrupted': has_interrupted,
        'need_batching': total_scenarios > 5,  # >5 走分批模式
    }

    return progress_info


def format_progress_text(progress_info: Dict[str, Any]) -> str:
    """格式化进度信息为文本格式"""
    text = "单场景文档生成进度报告:\n"
    text += f"  总场景数: {progress_info['total_scenarios']}\n"
    text += f"  已完成: {progress_info['completed_count']}\n"
    text += f"  处理中: {progress_info['processing_count']}\n"
    text += f"  待处理: {progress_info['pending_count']}\n"
    text += f"  失败: {progress_info['failed_count']}\n"
    text += f"  总进度: {progress_info['progress_percentage']:.2f}%\n"
    text += f"  断点续执行: {'是' if progress_info['has_interrupted'] else '否'}\n"
    text += f"  处理模式: {'分批' if progress_info['need_batching'] else '单批'}\n"
    return text


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='单场景文档生成进度跟踪工具')
    parser.add_argument('repo_root', help='仓库根目录路径')
    parser.add_argument('--format', choices=['json', 'text'], default='text',
                        help='输出格式 (json/text)，默认为 text')

    args = parser.parse_args()
    repo_root = args.repo_root
    output_format = args.format

    # 验证仓库根目录
    if not os.path.exists(repo_root):
        print(f"错误: 仓库根目录不存在 {repo_root}", file=sys.stderr)
        sys.exit(1)

    # 计算处理进度
    try:
        progress_info = calculate_processing_progress(repo_root)

        if output_format == 'json':
            print(json.dumps(progress_info, ensure_ascii=False))
        else:
            print(format_progress_text(progress_info))

    except Exception as e:
        print(f"计算处理进度过程中发生错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
