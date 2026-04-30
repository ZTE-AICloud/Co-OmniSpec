#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将 reverse_syntax_parser 接口识别输出转换为 interface-list.json 格式

将 interface_functions_checklist.json（方式B 调用链扫描输出）转换为
reverse 阶段4 所需的 interface-list.json 标准格式。

使用方法:
    python convert_reverse_interface_checklist.py --repo-root <repo_root> \\
        --input <interface_functions_checklist.json路径> \\
        [--output <输出路径>]

参数:
    --repo-root: 仓库根目录
    --input: reverse_syntax_parser 输出的 interface_functions_checklist.json 路径
    --output: 可选，输出 interface-list.json 路径，默认写入 .cache/reverse/interfaces/
"""

import os
import sys
import json
import re
import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List


def load_json_file(file_path: str) -> Any:
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
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"错误: 无法保存文件 {file_path}: {e}", file=sys.stderr)
        sys.exit(1)


def infer_language_from_path(file_path: str) -> str:
    """从文件路径推断编程语言"""
    ext_map = {
        '.py': 'Python',
        '.java': 'Java',
        '.js': 'JavaScript',
        '.ts': 'TypeScript',
        '.go': 'Go',
        '.cpp': 'C++',
        '.cc': 'C++',
        '.cxx': 'C++',
        '.c': 'C',
        '.h': 'C/C++',
        '.hpp': 'C++',
    }
    ext = Path(file_path).suffix.lower()
    return ext_map.get(ext, '未知')


def extract_module_from_path(file_path: str) -> str:
    """从文件路径提取模块名"""
    path = Path(file_path)
    parts = path.parts
    if len(parts) >= 2:
        return str(Path(*parts[:-1]))
    return path.parent.name or '未知'


def map_interface_type(reverse_type: str) -> str:
    """将 reverse 接口类型映射到标准类型"""
    type_map = {
        '未知': '其他',
        'RESTful API': 'RESTful API',
        'HTTP API': 'RESTful API',
        'RESTful接口': 'RESTful API',
        'REST接口': 'RESTful API',
        'CLI': '命令行接口',
        '命令行接口': '命令行接口',
        'RPC': 'RPC 接口',
        'RPC接口': 'RPC 接口',
        '消息': '消息类接口',
        '消息类': '消息类接口',
        '消息接口': '消息类接口',
        '消息类接口': '消息类接口',
        '模块间': '模块间接口',
        '模块间接口': '模块间接口',
        '函数': '函数接口',
        '函数接口': '函数接口',
        'OpenStack插件接口': '插件接口',
        '插件接口': '插件接口',
    }
    return type_map.get(reverse_type, reverse_type if reverse_type else '其他')


def convert_checklist_to_interface_list(
    checklist: List[Dict[str, Any]],
    repo_root: str,
) -> Dict[str, Any]:
    """
    将 interface_functions_checklist 转换为 interface-list.json 格式
    """
    interfaces = []
    type_prefix_map = {
        'RESTful API': 'API',
        '命令行接口': 'CLI',
        '消息类接口': 'MSG',
        '模块间接口': 'MOD',
        'RPC 接口': 'RPC',
        '函数接口': 'FUN',
        '插件接口': 'PLG',
        '其他': 'OTH',
    }

    for i, item in enumerate(checklist):
        reverse_type = item.get('interface_type', '未知')
        std_type = map_interface_type(reverse_type)
        prefix = type_prefix_map.get(std_type, 'OTH')

        # 生成 interface_id
        name_part = item.get('interface_function', 'unknown')
        name_part = re.sub(r'[^a-zA-Z0-9_]', '_', str(name_part))
        interface_id = f"{prefix}-{i+1:03d}-{name_part}"

        source_file = item.get('belonging_file', '')
        path_method = ''
        if item.get('http_method') and item.get('endpoint'):
            path_method = f"{item['http_method']} {item['endpoint']}"
        elif item.get('endpoint'):
            path_method = item['endpoint']

        interface_obj = {
            'interface_id': interface_id,
            'name': item.get('interface_function', ''),
            'business_name': item.get('interface_function', ''),
            'business_domain': '',
            'business_function': '',
            'interface_type': std_type,
            'source_file': source_file,
            'path_method': path_method,
            'parameters': [],
            'returns': '',
            'description': '',
            'module': extract_module_from_path(source_file) if source_file else '未知',
            'layer': '',
            'language': infer_language_from_path(source_file) if source_file else '未知',
            'confidence': 1.0,
            'tags': [],
            'annotations': [],
            # 保留 reverse 特有字段供下游参考
            'uuid': item.get('uuid', ''),
            'endpoint': item.get('endpoint', ''),
            'http_method': item.get('http_method', ''),
        }
        interfaces.append(interface_obj)

    # 构造与 merge_interface_results 一致的输出结构
    summary = {'by_type': {}, 'by_module': {}}
    for iface in interfaces:
        t = iface.get('interface_type', '未知')
        summary['by_type'][t] = summary['by_type'].get(t, 0) + 1
        m = iface.get('module', '未知')
        summary['by_module'][m] = summary['by_module'].get(m, 0) + 1

    utc_now = datetime.now(timezone.utc)
    return {
        'version': '1.0',
        'generated_at': utc_now.isoformat().replace('+00:00', 'Z'),
        'scan_scope': repo_root,
        'total_interfaces': len(interfaces),
        'metadata': {
            'total_interfaces': len(interfaces),
            'scan_time': utc_now.isoformat().replace('+00:00', 'Z'),
            'source': 'reverse_call_chain_scan',
            'confidence_threshold': 1.0,
        },
        'interfaces': interfaces,
        'summary': summary,
    }


def main():
    parser = argparse.ArgumentParser(description='将 reverse_syntax_parser 接口清单转换为 interface-list.json')
    parser.add_argument('--repo-root', required=True, help='仓库根目录')
    parser.add_argument('--input', required=True, help='interface_functions_checklist.json 路径')
    parser.add_argument(
        '--output',
        default=None,
        help='输出路径，默认: {repo_root}/.cache/reverse/interfaces/interface-list.json',
    )
    args = parser.parse_args()

    repo_root = args.repo_root
    input_path = args.input
    output_path = args.output or os.path.join(
        repo_root, '.cache', 'reverse', 'interfaces', 'interface-list.json'
    )

    if not os.path.exists(repo_root):
        print(f"错误: 仓库根目录不存在 {repo_root}", file=sys.stderr)
        sys.exit(1)

    if not os.path.exists(input_path):
        print(f"错误: 输入文件不存在 {input_path}", file=sys.stderr)
        sys.exit(1)

    checklist = load_json_file(input_path)
    if not isinstance(checklist, list):
        print("错误: 输入文件应为 JSON 数组格式", file=sys.stderr)
        sys.exit(1)

    result = convert_checklist_to_interface_list(checklist, repo_root)
    save_json_file(result, output_path)
    print(f"成功转换 {result['total_interfaces']} 个接口到 {output_path}")


if __name__ == '__main__':
    main()
