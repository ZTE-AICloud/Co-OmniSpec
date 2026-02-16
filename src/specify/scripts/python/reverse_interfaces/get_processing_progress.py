#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
获取接口处理进度工具
实时统计已处理的接口数量和待处理的接口数量，计算处理进度

兼容Windows和Linux系统
使用方法:
    python get_processing_progress.py <repo_root> [--format <format>]

参数:
    repo_root: 仓库根目录路径
    --format: 输出格式 (json/text)，默认为text
"""
import os
import sys
import json
import argparse
from typing import Dict, Any, Tuple
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


def calculate_processing_progress(repo_root: str) -> Dict[str, Any]:
    """计算接口处理进度"""
    cache_dir = os.path.join(repo_root, '.cache', 'omni-reverse', 'interfaces')
    interface_list_file = os.path.join(cache_dir, 'interface-list.json')

    # 检查接口清单文件是否存在
    if not os.path.exists(interface_list_file):
        print(f"错误: 接口清单文件不存在 {interface_list_file}", file=sys.stderr)
        sys.exit(1)

    # 读取接口清单
    interface_data = load_json_file(interface_list_file)
    interfaces = interface_data.get('interfaces', [])

    # 初始化计数器
    total_interfaces = len(interfaces)
    pending_count = 0
    processing_count = 0
    completed_count = 0
    failed_count = 0

    # 统计各种状态的接口数量
    for interface in interfaces:
        status = interface.get('processing_status', 'pending')
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
    if total_interfaces > 0:
        progress_percentage = (processed_count / total_interfaces) * 100
    else:
        progress_percentage = 0

    # 估算剩余时间（基于已完成接口的平均处理时间）
    estimated_remaining_time = "未知"
    if completed_count > 0 and 'interfaces' in interface_data:
        # 计算已完成接口的平均处理时间
        total_processing_time = 0
        completed_interfaces = 0

        for interface in interface_data['interfaces']:
            if interface.get('processing_status') == 'completed' and 'processing_time' in interface:
                total_processing_time += interface['processing_time']
                completed_interfaces += 1

        if completed_interfaces > 0:
            average_processing_time = total_processing_time / completed_interfaces
            remaining_interfaces = pending_count + processing_count
            estimated_seconds = average_processing_time * remaining_interfaces

            # 格式化时间显示
            if estimated_seconds < 60:
                estimated_remaining_time = f"{estimated_seconds:.0f}秒"
            elif estimated_seconds < 3600:
                estimated_remaining_time = f"{estimated_seconds/60:.1f}分钟"
            else:
                estimated_remaining_time = f"{estimated_seconds/3600:.1f}小时"

    # 构造进度信息
    progress_info = {
        'total_interfaces': total_interfaces,
        'pending_count': pending_count,
        'processing_count': processing_count,
        'completed_count': completed_count,
        'failed_count': failed_count,
        'processed_count': processed_count,
        'progress_percentage': round(progress_percentage, 2),
        'estimated_remaining_time': estimated_remaining_time
    }

    return progress_info


def format_progress_text(progress_info: Dict[str, Any]) -> str:
    """格式化进度信息为文本格式"""
    text = f"接口处理进度报告:\n"
    text += f"  总接口数: {progress_info['total_interfaces']}\n"
    text += f"  已完成: {progress_info['completed_count']}\n"
    text += f"  处理中: {progress_info['processing_count']}\n"
    text += f"  待处理: {progress_info['pending_count']}\n"
    text += f"  失败: {progress_info['failed_count']}\n"
    text += f"  总进度: {progress_info['progress_percentage']:.2f}%\n"

    if progress_info['estimated_remaining_time'] != "未知":
        text += f"  预计剩余时间: {progress_info['estimated_remaining_time']}\n"
    else:
        text += f"  预计剩余时间: {progress_info['estimated_remaining_time']}\n"

    return text


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='获取接口处理进度工具')
    parser.add_argument('repo_root', help='仓库根目录路径')
    parser.add_argument('--format', choices=['json', 'text'], default='text',
                       help='输出格式 (json/text)，默认为text')

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