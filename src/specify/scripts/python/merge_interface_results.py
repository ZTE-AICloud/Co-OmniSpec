#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
接口清单批次合并工具
自动合并所有批次接口清单文件，生成最终的接口清单

兼容Windows和Linux系统
使用方法:
    python merge_interface_results.py <repo_root>

参数:
    repo_root: 仓库根目录路径
"""

import os
import sys
import json
import re
from datetime import datetime, timezone
from typing import Dict, Any, List


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


def extract_interface_name_from_id(interface_id: str) -> str:
    """
    从接口ID中提取接口名称部分
    
    参数:
        interface_id: 接口ID，格式为 {前缀}-{序号}-{名称}
    
    返回:
        接口名称部分（去除前缀和序号）
    """
    # 匹配格式: {前缀}-{序号}-{名称}
    match = re.match(r'^[A-Z]+-\d+-(.+)$', interface_id)
    if match:
        return match.group(1)
    # 如果没有匹配到，返回原ID（兼容旧格式）
    return interface_id


def regenerate_interface_ids(interfaces: List[Dict[Any, Any]]) -> List[Dict[Any, Any]]:
    """
    统一重新生成接口ID，按类型分组，每种类型从001开始独立编号
    
    参数:
        interfaces: 接口列表
    
    返回:
        重新生成ID后的接口列表
    """
    type_prefix_map = {
        'RESTful API': 'API',
        '命令行接口': 'CLI',
        '消息类接口': 'MSG',
        '模块间接口': 'MOD',
        'RPC 接口': 'RPC',
        '函数接口': 'FUN',
        'HTTP客户端接口': 'HTTP',
        'Kubernetes API接口': 'K8S',
        '其他': 'OTH'
    }
    
    # 按类型分组接口
    interfaces_by_type = {}
    for interface in interfaces:
        interface_type = interface.get('interface_type', '其他')
        if interface_type not in interfaces_by_type:
            interfaces_by_type[interface_type] = []
        interfaces_by_type[interface_type].append(interface)
    
    # 为每种类型重新生成ID
    result = []
    for interface_type, type_interfaces in interfaces_by_type.items():
        prefix = type_prefix_map.get(interface_type, 'OTH')
        counter = 1
        
        for interface in type_interfaces:
            # 提取原有的接口名称部分
            old_interface_id = interface.get('interface_id', '')
            if old_interface_id:
                # 从旧ID中提取名称部分
                interface_name = extract_interface_name_from_id(old_interface_id)
            else:
                # 如果没有旧ID，从name字段生成
                interface_name = interface.get('name', 'unknown').replace(' ', '_').replace('-', '_')
                interface_name = re.sub(r'[^a-zA-Z0-9_]', '_', interface_name)
            
            # 生成新的接口ID
            new_interface_id = f"{prefix}-{counter:03d}-{interface_name}"
            interface['interface_id'] = new_interface_id
            counter += 1
            
            result.append(interface)
    
    return result


def merge_batch_files(repo_root: str) -> Dict[Any, Any]:
    """合并所有接口清单批次文件"""
    cache_dir = os.path.join(repo_root, '.cache', 'omni-reverse', 'interfaces')

    # 查找所有interface-list-batch文件
    batch_files = []
    for filename in os.listdir(cache_dir):
        if filename.startswith('interface-list-batch-') and filename.endswith('.json'):
            batch_files.append(filename)

    # 按批次号排序
    batch_files.sort(key=lambda x: int(x.replace('interface-list-batch-', '').replace('.json', '')))

    if not batch_files:
        print("警告: 未找到任何接口清单批次文件", file=sys.stderr)
        # 返回空结果
        utc_now = datetime.now(timezone.utc)
        return {
            'version': '1.0',
            'generated_at': utc_now.isoformat().replace('+00:00', 'Z'),
            'scan_scope': repo_root,
            'total_interfaces': 0,
            'metadata': {
                'total_interfaces': 0,
                'scan_time': utc_now.isoformat().replace('+00:00', 'Z'),
                'source': 'interface_scanning_stage',
                'confidence_threshold': 0.8
            },
            'interfaces': [],
            'summary': {
                'by_type': {},
                'by_module': {}
            }
        }

    # 合并所有批次（先收集所有接口，不处理ID）
    merged_interfaces = []
    
    for batch_file in batch_files:
        batch_file_path = os.path.join(cache_dir, batch_file)
        try:
            batch_data = load_json_file(batch_file_path)
            
            # 支持两种格式：直接是数组，或者是包含interfaces字段的对象
            if isinstance(batch_data, list):
                batch_interfaces = batch_data
            elif isinstance(batch_data, dict) and 'interfaces' in batch_data:
                batch_interfaces = batch_data.get('interfaces', [])
            else:
                print(f"警告: 批次文件格式不正确 {batch_file}，跳过", file=sys.stderr)
                continue
            
            # 收集所有接口（保留原有的interface_id，用于提取名称）
            for interface in batch_interfaces:
                # 如果没有interface_id，从name生成一个临时ID（用于提取名称）
                if 'interface_id' not in interface or not interface.get('interface_id'):
                    interface_type = interface.get('interface_type', '其他')
                    type_prefix_map = {
                        'RESTful API': 'API',
                        '命令行接口': 'CLI',
                        '消息类接口': 'MSG',
                        '模块间接口': 'MOD',
                        'RPC 接口': 'RPC',
                        '函数接口': 'FUN',
                        '其他': 'OTH'
                    }
                    prefix = type_prefix_map.get(interface_type, 'OTH')
                    interface_name = interface.get('name', 'unknown').replace(' ', '_').replace('-', '_')
                    interface_name = re.sub(r'[^a-zA-Z0-9_]', '_', interface_name)
                    # 生成临时ID（最终会被重新生成）
                    interface['interface_id'] = f"{prefix}-000-{interface_name}"
                
                merged_interfaces.append(interface)
        except Exception as e:
            print(f"警告: 无法处理批次文件 {batch_file}: {e}", file=sys.stderr)
            continue
    
    # 统一重新生成接口ID（按类型分组，每种类型从001开始）
    merged_interfaces = regenerate_interface_ids(merged_interfaces)

    # 生成最终结果
    total_interfaces = len(merged_interfaces)

    # 计算统计数据
    summary = {
        'by_type': {},
        'by_module': {}
    }

    for interface in merged_interfaces:
        # 按类型统计
        interface_type = interface.get('interface_type', '未知')
        summary['by_type'][interface_type] = summary['by_type'].get(interface_type, 0) + 1

        # 按模块统计
        module = interface.get('module', '未知')
        summary['by_module'][module] = summary['by_module'].get(module, 0) + 1

    # 构造最终结果
    utc_now = datetime.now(timezone.utc)
    result = {
        'version': '1.0',
        'generated_at': utc_now.isoformat().replace('+00:00', 'Z'),
        'scan_scope': repo_root,
        'total_interfaces': total_interfaces,
        'metadata': {
            'total_interfaces': total_interfaces,
            'scan_time': utc_now.isoformat().replace('+00:00', 'Z'),
            'source': 'interface_scanning_stage',
            'confidence_threshold': 0.8
        },
        'interfaces': merged_interfaces,
        'summary': summary
    }

    return result


def main():
    """主函数"""
    if len(sys.argv) != 2:
        print("使用方法: python merge_interface_results.py <repo_root>", file=sys.stderr)
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
        output_file = os.path.join(repo_root, '.cache', 'omni-reverse', 'interfaces', 'interface-list.json')
        save_json_file(result, output_file)

        print(f"成功合并 {result['total_interfaces']} 个接口到 {output_file}")

    except Exception as e:
        print(f"合并过程中发生错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()