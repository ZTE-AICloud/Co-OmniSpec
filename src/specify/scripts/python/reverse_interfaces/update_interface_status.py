#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
更新接口处理状态工具
更新Interface-list.json文件中指定接口的处理状态

兼容Windows和Linux系统
使用方法:
    python update_interface_status.py <repo_root> <interface_id> <status>

参数:
    repo_root: 仓库根目录路径
    interface_id: 接口ID
    status: 新的状态 (processing/completed/failed)
"""

import os
import sys
import json
from typing import Dict, Any


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


def update_interface_status(repo_root: str, interface_id: str, status: str) -> bool:
    """更新接口处理状态"""
    cache_dir = os.path.join(repo_root, '.cache', 'omni-reverse', 'interfaces')
    interface_list_file = os.path.join(cache_dir, 'interface-list.json')

    # 检查接口清单文件是否存在
    if not os.path.exists(interface_list_file):
        print(f"错误: 接口清单文件不存在 {interface_list_file}", file=sys.stderr)
        return False

    # 读取接口清单
    interface_data = load_json_file(interface_list_file)
    interfaces = interface_data.get('interfaces', [])

    # 查找并更新指定接口的状态
    updated = False
    for interface in interfaces:
        if interface.get('interface_id') == interface_id:
            # 统一使用processing_status字段
            interface['processing_status'] = status
            interface['processed_at'] = __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat().replace('+00:00', 'Z')
            updated = True
            break

    if updated:
        # 保存更新后的接口清单
        save_json_file(interface_data, interface_list_file)
        return True
    else:
        print(f"错误: 未找到接口ID为 {interface_id} 的接口", file=sys.stderr)
        return False


def main():
    """主函数"""
    if len(sys.argv) != 4:
        print("使用方法: python update_interface_status.py <repo_root> <interface_id> <status>", file=sys.stderr)
        print("状态选项: pending, processing, completed, failed", file=sys.stderr)
        sys.exit(1)

    repo_root = sys.argv[1]
    interface_id = sys.argv[2]
    status = sys.argv[3]

    # 验证参数
    valid_statuses = ['pending', 'processing', 'completed', 'failed']
    if status not in valid_statuses:
        print(f"错误: 无效的状态 '{status}'。有效状态: {', '.join(valid_statuses)}", file=sys.stderr)
        sys.exit(1)

    # 验证仓库根目录
    if not os.path.exists(repo_root):
        print(f"错误: 仓库根目录不存在 {repo_root}", file=sys.stderr)
        sys.exit(1)

    # 更新接口状态
    try:
        success = update_interface_status(repo_root, interface_id, status)

        if success:
            print(f"成功更新接口 {interface_id} 的状态为 {status}")
        else:
            sys.exit(1)

    except Exception as e:
        print(f"更新接口状态过程中发生错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()