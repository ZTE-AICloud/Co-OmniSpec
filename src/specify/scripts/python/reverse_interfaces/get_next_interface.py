#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
获取下一个要处理的接口工具
从Interface-list.json文件中读取接口清单，找出下一个状态为"pending"的接口并返回

兼容Windows和Linux系统
使用方法:
    python get_next_interface.py <repo_root>

参数:
    repo_root: 仓库根目录路径
"""

import os
import sys
import json
from typing import Dict, Any, Optional


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


def get_next_pending_interface(repo_root: str) -> Optional[Dict[Any, Any]]:
    """获取下一个待处理的接口"""
    cache_dir = os.path.join(repo_root, '.cache', 'omni-reverse', 'interfaces')
    interface_list_file = os.path.join(cache_dir, 'interface-list.json')

    # 检查接口清单文件是否存在
    if not os.path.exists(interface_list_file):
        print(f"错误: 接口清单文件不存在 {interface_list_file}", file=sys.stderr)
        sys.exit(1)

    # 读取接口清单
    interface_data = load_json_file(interface_list_file)
    interfaces = interface_data.get('interfaces', [])

    # 查找第一个状态为pending的接口
    for interface in interfaces:
        # 检查processing_status字段
        if 'processing_status' in interface:
            status = interface['processing_status']
        # 如果没有processing_status字段，检查status字段
        elif 'status' in interface:
            status = interface['status']
        # 如果两个字段都没有，默认为pending
        else:
            status = 'pending'

        if status == 'pending':
            return interface

    # 没有找到待处理的接口
    return None


def main():
    """主函数"""
    if len(sys.argv) != 2:
        print("使用方法: python get_next_interface.py <repo_root>", file=sys.stderr)
        sys.exit(1)

    repo_root = sys.argv[1]

    # 验证仓库根目录
    if not os.path.exists(repo_root):
        print(f"错误: 仓库根目录不存在 {repo_root}", file=sys.stderr)
        sys.exit(1)

    # 获取下一个待处理的接口
    try:
        next_interface = get_next_pending_interface(repo_root)

        if next_interface:
            # 输出接口信息为JSON格式
            print(json.dumps(next_interface, ensure_ascii=False))
        else:
            # 没有更多接口需要处理
            print("{}")

    except Exception as e:
        print(f"获取接口过程中发生错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()