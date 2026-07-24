#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成批次接口清单工具
从临时文件中读取接口数据，合并生成批次接口清单文件

兼容Windows和Linux系统
使用方法:
    python generate_batch_interface_list.py --repo-root <repo_root> --batch-number <batch_number>

参数:
    --repo-root: 仓库根目录路径
    --batch-number: 批次编号
"""

import os
import sys
import json
import argparse
import re
from datetime import datetime, timezone
from typing import Dict, Any, List, Tuple

try:
    # 可选依赖：用于在合并批次清单后自动回写 batch-details 文件内每个文件条目的状态
    from update_batch_details_file_status import update_batch_details_status  # type: ignore
except Exception:
    update_batch_details_status = None  # type: ignore


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


def validate_interface(interface: Dict[Any, Any]) -> Tuple[bool, str]:
    """验证接口数据的完整性和格式正确性"""
    required_fields = ['name', 'interface_type', 'source_file']
    
    for field in required_fields:
        if field not in interface:
            return False, f"缺少必需字段: {field}"
    
    # 验证字段类型
    if not isinstance(interface.get('name'), str):
        return False, "字段 name 必须是字符串类型"
    
    if not isinstance(interface.get('interface_type'), str):
        return False, "字段 interface_type 必须是字符串类型"
    
    if not isinstance(interface.get('source_file'), str):
        return False, "字段 source_file 必须是字符串类型"
    
    return True, ""


def get_total_batches(cache_dir: str) -> int:
    """从batch-mapping.json获取总批次数"""
    batch_mapping_file = os.path.join(cache_dir, 'batch-mapping.json')
    if os.path.exists(batch_mapping_file):
        try:
            batch_mapping = load_json_file(batch_mapping_file)
            return batch_mapping.get('total_batches', 0)
        except Exception:
            pass
    return 0


def collect_temp_files(cache_dir: str, batch_number: int) -> List[str]:
    """收集指定批次的所有临时文件"""
    temp_dir = os.path.join(cache_dir, 'temp')
    if not os.path.exists(temp_dir):
        return []
    
    temp_files = []
    prefix = f"interface-{batch_number}-"
    
    # 遍历临时目录，查找匹配的临时文件
    for filename in os.listdir(temp_dir):
        if filename.startswith(prefix) and filename.endswith('.json'):
            file_path = os.path.join(temp_dir, filename)
            if os.path.isfile(file_path):
                temp_files.append(file_path)
    
    # 按文件索引排序
    temp_files.sort(key=lambda x: int(
        os.path.basename(x).replace(prefix, '').replace('.json', '')
    ))
    
    return temp_files


def merge_interfaces_from_temp_files(temp_files: List[str], batch_number: int) -> List[Dict[Any, Any]]:
    """
    从临时文件中合并接口数据
    
    参数:
        temp_files: 临时文件列表
        batch_number: 批次编号
    
    注意: 接口ID将在合并时统一重新生成，这里只使用批次内临时序号
    """
    all_interfaces = []
    # 按接口类型分组计数，用于生成临时interface_id（批次内序号）
    type_counters = {
        'RESTful API': 0,
        '命令行接口': 0,
        '消息类接口': 0,
        '模块间接口': 0,
        'RPC 接口': 0,
        '函数接口': 0,
        '其他': 0
    }
    type_prefix_map = {
        'RESTful API': 'API',
        '命令行接口': 'CLI',
        '消息类接口': 'MSG',
        '模块间接口': 'MOD',
        'RPC 接口': 'RPC',
        '函数接口': 'FUN',
        '其他': 'OTH'
    }
    
    for temp_file in temp_files:
        try:
            # 读取临时文件（应该是接口数组）
            temp_data = load_json_file(temp_file)
            
            # 支持两种格式：直接是数组，或者是包含interfaces字段的对象
            if isinstance(temp_data, list):
                interfaces = temp_data
            elif isinstance(temp_data, dict) and 'interfaces' in temp_data:
                interfaces = temp_data['interfaces']
            else:
                print(f"警告: 临时文件格式不正确 {temp_file}，跳过", file=sys.stderr)
                continue
            
            # 处理每个接口
            for interface in interfaces:
                # 验证接口数据
                is_valid, error_msg = validate_interface(interface)
                if not is_valid:
                    print(f"警告: 接口数据无效，跳过: {error_msg}", file=sys.stderr)
                    continue
                
                # 如果接口已有interface_id，保留它；否则生成临时ID（批次内序号）
                # 注意：这个ID只是临时的，最终会在合并时重新生成
                if 'interface_id' not in interface or not interface.get('interface_id'):
                    interface_type = interface.get('interface_type', '其他')
                    type_counters[interface_type] = type_counters.get(interface_type, 0) + 1
                    prefix = type_prefix_map.get(interface_type, 'OTH')
                    interface_name = interface.get('name', 'unknown').replace(' ', '_').replace('-', '_')
                    # 去除特殊字符，只保留字母、数字、下划线
                    interface_name = re.sub(r'[^a-zA-Z0-9_]', '_', interface_name)
                    # 使用批次内临时序号（最终会在合并时重新生成）
                    interface['interface_id'] = f"{prefix}-{type_counters[interface_type]:03d}-{interface_name}"
                
                all_interfaces.append(interface)
                
        except Exception as e:
            print(f"警告: 无法处理临时文件 {temp_file}: {e}，跳过", file=sys.stderr)
            continue
    
    return all_interfaces


def generate_batch_interface_list(repo_root: str, batch_number: int) -> None:
    """生成批次接口清单"""
    cache_dir = os.path.join(repo_root, '.cache', 'reverse', 'interfaces')
    
    # 读取批次详情文件获取批次信息
    batch_details_file = os.path.join(cache_dir, f'batch-details-{batch_number}.json')
    if not os.path.exists(batch_details_file):
        print(f"错误: 批次详情文件不存在 {batch_details_file}", file=sys.stderr)
        sys.exit(1)
    
    batch_details = load_json_file(batch_details_file)
    
    # 获取总批次数（优先从batch-details，否则从batch-mapping）
    total_batches = batch_details.get('total_batches', 0)
    if total_batches == 0:
        total_batches = get_total_batches(cache_dir)
    
    # 收集所有临时文件
    temp_files = collect_temp_files(cache_dir, batch_number)
    
    if not temp_files:
        print(f"警告: 未找到批次 {batch_number} 的临时文件", file=sys.stderr)
        # 生成空的批次接口清单
        all_interfaces = []
    else:
        # 合并所有接口（使用批次内临时序号，最终在合并时统一重新生成）
        all_interfaces = merge_interfaces_from_temp_files(temp_files, batch_number)
    
    # 生成批次接口清单
    utc_now = datetime.now(timezone.utc)
    batch_interface_list = {
        'batch_number': batch_number,
        'total_batches': total_batches,
        'generated_at': utc_now.isoformat().replace('+00:00', 'Z'),
        'interfaces': all_interfaces
    }
    
    # 保存批次接口清单文件
    output_file = os.path.join(cache_dir, f'interface-list-batch-{batch_number}.json')
    save_json_file(batch_interface_list, output_file)
    
    # 自动回写 batch-details-{n}.json 内的文件状态（若脚本可用）
    if update_batch_details_status is not None:
        try:
            update_batch_details_status(repo_root, batch_number, dry_run=False)
        except Exception as e:
            # 不阻塞主流程：仅告警
            print(f"警告: 回写批次文件状态失败: {e}", file=sys.stderr)

    print(f"成功生成批次接口清单: {output_file}")
    print(f"包含 {len(all_interfaces)} 个接口")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='生成批次接口清单工具')
    parser.add_argument('--repo-root', required=True, help='仓库根目录路径')
    parser.add_argument('--batch-number', type=int, required=True, help='批次编号')
    
    args = parser.parse_args()
    
    repo_root = args.repo_root
    batch_number = args.batch_number
    
    # 验证仓库根目录
    if not os.path.exists(repo_root):
        print(f"错误: 仓库根目录不存在 {repo_root}", file=sys.stderr)
        sys.exit(1)
    
    # 验证批次编号
    if batch_number < 1:
        print(f"错误: 批次编号必须大于0: {batch_number}", file=sys.stderr)
        sys.exit(1)
    
    # 执行生成
    try:
        generate_batch_interface_list(repo_root, batch_number)
    except Exception as e:
        print(f"生成批次接口清单过程中发生错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()

