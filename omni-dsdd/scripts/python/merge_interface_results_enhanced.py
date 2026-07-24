#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版接口清单批次合并工具
自动合并所有批次接口清单文件，生成最终的接口清单，带进度显示和验证功能

兼容Windows和Linux系统
使用方法:
    python merge_interface_results_enhanced.py <repo_root> [--verbose] [--validate]

参数:
    repo_root: 仓库根目录路径
    --verbose: 显示详细处理信息
    --validate: 验证合并结果
"""

import copy
import os
import sys
import json
import argparse
from datetime import datetime, timezone
from typing import Dict, Any, Set, Tuple


def load_json_file(file_path: str) -> Dict[Any, Any]:
    """安全加载JSON文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"错误: 无法读取文件 {file_path}: {e}", file=sys.stderr)
        raise


def save_json_file(data: Dict[Any, Any], file_path: str) -> None:
    """安全保存JSON文件"""
    try:
        # 确保目录存在
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"错误: 无法保存文件 {file_path}: {e}", file=sys.stderr)
        raise


def validate_batch_file(batch_data: Dict[Any, Any], batch_number: int) -> bool:
    """验证批次文件格式"""
    required_fields = ['batch_number', 'interfaces']
    for field in required_fields:
        if field not in batch_data:
            print(f"警告: 批次 {batch_number} 缺少必要字段 {field}", file=sys.stderr)
            return False

    if batch_data.get('batch_number') != batch_number:
        print(f"警告: 批次编号不匹配: 期望 {batch_number}, 实际 {batch_data.get('batch_number')}", file=sys.stderr)
        return False

    return True


def validate_interface(interface: Dict[Any, Any]) -> Tuple[bool, str]:
    """验证接口数据格式"""
    required_fields = ['interface_id', 'name', 'interface_type', 'source_file']
    for field in required_fields:
        if field not in interface or not interface[field]:
            return False, f"缺少必要字段 {field} 或字段为空"

    return True, ""


def build_dedup_key(interface: Dict[Any, Any]) -> Tuple[str, str, str]:
    """构建接口去重键，避免跨批次重复接口导致编号冲突。"""
    source_file = str(interface.get('source_file', '')).strip()
    path_method = str(interface.get('path_method', '')).strip()
    name = str(interface.get('name', '')).strip()
    return (source_file, path_method, name)


def merge_batch_files(repo_root: str, verbose: bool = False) -> Dict[Any, Any]:
    """合并所有批次文件"""
    cache_dir = os.path.join(repo_root, '.cache', 'reverse', 'interfaces')

    # 读取批次映射文件
    batch_mapping_file = os.path.join(cache_dir, 'batch-mapping.json')
    if not os.path.exists(batch_mapping_file):
        raise FileNotFoundError(f"批次映射文件不存在 {batch_mapping_file}")

    if verbose:
        print(f"读取批次映射文件: {batch_mapping_file}")

    batch_mapping = load_json_file(batch_mapping_file)

    # 初始化合并结果
    merged_interfaces = []
    dedup_keys: Set[Tuple[str, str, str]] = set()
    total_batches = len(batch_mapping.get('batches', []))
    processed_batches = 0

    if verbose:
        print(f"开始处理 {total_batches} 个批次...")

    # 按顺序处理所有批次
    for i, batch_info in enumerate(batch_mapping.get('batches', [])):
        batch_file = batch_info.get('batch_file', '')
        batch_number = batch_info.get('batch_number', i + 1)

        if verbose:
            print(f"处理批次 {batch_number}/{total_batches}: {batch_file}")

        if not batch_file:
            if verbose:
                print(f"  跳过空批次文件名")
            continue

        batch_file_path = os.path.join(cache_dir, batch_file)
        if not os.path.exists(batch_file_path):
            print(f"警告: 批次文件不存在 {batch_file_path}", file=sys.stderr)
            continue

        # 读取批次数据
        try:
            batch_data = load_json_file(batch_file_path)
        except Exception as e:
            print(f"警告: 无法读取批次文件 {batch_file_path}: {e}", file=sys.stderr)
            continue

        # 验证批次文件格式
        if not validate_batch_file(batch_data, batch_number):
            print(f"警告: 批次文件格式无效 {batch_file_path}", file=sys.stderr)
            continue

        batch_interfaces = batch_data.get('interfaces', [])
        batch_interface_count = len(batch_interfaces)

        if verbose:
            print(f"  找到 {batch_interface_count} 个接口")

        # 合并接口数据并去重
        added_count = 0
        for interface in batch_interfaces:
            # 验证接口数据
            is_valid, error_msg = validate_interface(interface)
            if not is_valid:
                print("警告: 接口数据无效: {}".format(error_msg), file=sys.stderr)
                continue

            dedup_key = build_dedup_key(interface)
            if dedup_key in dedup_keys:
                continue

            dedup_keys.add(dedup_key)
            merged_interfaces.append(copy.deepcopy(interface))
            added_count += 1

        if verbose:
            print(f"  添加了 {added_count} 个新接口 (重复 {batch_interface_count - added_count} 个)")

        processed_batches += 1
        if verbose:
            print(f"  批次 {batch_number} 处理完成 ({processed_batches}/{total_batches})")

    if verbose:
        print(f"批次处理完成: 总共处理 {processed_batches}/{total_batches} 个批次")

    # 统一编号：全局连续，格式 API_001、API_002...
    for idx, interface in enumerate(merged_interfaces, start=1):
        interface['interface_id'] = f"API_{idx:03d}"

    # 生成最终结果
    total_interfaces = len(merged_interfaces)

    if verbose:
        print(f"总共合并了 {total_interfaces} 个唯一接口")

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


def validate_result(result: Dict[Any, Any], repo_root: str) -> bool:
    """验证合并结果"""
    print("验证合并结果...")

    # 检查必要字段
    required_fields = ['version', 'generated_at', 'total_interfaces', 'interfaces', 'summary']
    for field in required_fields:
        if field not in result:
            print(f"错误: 结果缺少必要字段 {field}", file=sys.stderr)
            return False

    # 验证扫描范围
    if result.get('scan_scope') != repo_root:
        print(f"警告: 扫描范围不匹配: 期望 {repo_root}, 实际 {result.get('scan_scope')}", file=sys.stderr)

    # 检查接口数据
    interfaces = result.get('interfaces', [])
    total_interfaces = result.get('total_interfaces', 0)

    if len(interfaces) != total_interfaces:
        print(f"警告: 接口数量不匹配: 声称 {total_interfaces}, 实际 {len(interfaces)}", file=sys.stderr)

    # 检查重复接口
    interface_ids = set()
    duplicate_count = 0
    for interface in interfaces:
        interface_id = interface.get('interface_id', '')
        if interface_id in interface_ids:
            duplicate_count += 1
        else:
            interface_ids.add(interface_id)

    if duplicate_count > 0:
        print(f"警告: 发现 {duplicate_count} 个重复接口", file=sys.stderr)

    # 验证统计数据
    summary = result.get('summary', {})
    by_type = summary.get('by_type', {})
    by_module = summary.get('by_module', {})

    type_total = sum(by_type.values())
    module_total = sum(by_module.values())

    if type_total != total_interfaces:
        print(f"警告: 按类型统计数量不匹配: 统计 {type_total}, 总数 {total_interfaces}", file=sys.stderr)

    if module_total != total_interfaces:
        print(f"警告: 按模块统计数量不匹配: 统计 {module_total}, 总数 {total_interfaces}", file=sys.stderr)

    print("验证完成")
    return True


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='增强版接口清单批次合并工具')
    parser.add_argument('repo_root', help='仓库根目录路径')
    parser.add_argument('--verbose', '-v', action='store_true', help='显示详细处理信息')
    parser.add_argument('--validate', action='store_true', help='验证合并结果')

    args = parser.parse_args()

    repo_root = args.repo_root
    verbose = args.verbose
    validate = args.validate

    # 验证仓库根目录
    if not os.path.exists(repo_root):
        print(f"错误: 仓库根目录不存在 {repo_root}", file=sys.stderr)
        sys.exit(1)

    if verbose:
        print(f"开始合并接口清单批次文件...")
        print(f"仓库根目录: {repo_root}")

    # 执行合并
    try:
        result = merge_batch_files(repo_root, verbose)

        # 保存结果 - 与批次文件在同一目录下
        output_file = os.path.join(repo_root, '.cache', 'reverse', 'interfaces', 'interface-list.json')

        if verbose:
            print(f"保存合并结果到: {output_file}")

        save_json_file(result, output_file)

        print(f"成功合并 {result['total_interfaces']} 个接口到 {output_file}")

        # 验证结果
        if validate:
            validate_result(result, repo_root)

    except Exception as e:
        print(f"合并过程中发生错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()