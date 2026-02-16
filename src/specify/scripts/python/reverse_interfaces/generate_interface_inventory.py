#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
生成接口清单脚本
用途: 收集所有已生成的接口详情文档信息，根据模板生成汇总接口清单文档
"""

import argparse
import os
import json
import re
import time
from datetime import datetime
from pathlib import Path


def log_info(message):
    """输出信息日志"""
    print(f"[INFO] {message}")


def log_warn(message):
    """输出警告日志"""
    print(f"[WARN] {message}")


def log_error(message):
    """输出错误日志"""
    print(f"[ERROR] {message}")


def read_template(template_file):
    """读取模板文件"""
    try:
        with open(template_file, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        log_error(f"读取模板文件失败: {e}")
        return None


def get_interface_stats(interface_list_file):
    """从接口列表文件获取统计数据"""
    if not os.path.exists(interface_list_file):
        log_warn(f"接口列表文件不存在: {interface_list_file}")
        return 0, []

    try:
        with open(interface_list_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 获取接口总数
        total_count = len(data.get('interfaces', []))

        # 获取接口类型统计
        type_statistics = []
        if total_count > 0:
            interfaces = data.get('interfaces', [])
            type_counts = {}

            for interface in interfaces:
                interface_type = interface.get('interface_type', 'Unknown')
                type_counts[interface_type] = type_counts.get(interface_type, 0) + 1

            for type_name, count in type_counts.items():
                type_statistics.append(f"- **{type_name}接口**: {count} 个")

        return total_count, type_statistics
    except Exception as e:
        log_warn(f"解析接口列表文件失败: {e}")
        return 0, []


def collect_interface_info(output_dir):
    """收集接口详情信息"""
    interfaces_table = []

    # 查找所有接口详情文档（排除接口清单本身）
    try:
        interface_files = list(Path(output_dir).glob("*.md"))
        interface_files = [f for f in interface_files if f.name != "接口清单.md"]
        interface_files.sort()
    except Exception as e:
        log_warn(f"查找接口详情文件失败: {e}")
        return interfaces_table

    for file_path in interface_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 从文件名提取接口ID和接口名称
            filename = file_path.stem

            # 提取接口信息
            interface_id = "N/A"
            interface_name = filename
            interface_type = "N/A"
            source_file = "N/A"

            # 提取接口ID
            id_match = re.search(r'^\- \*\*接口ID\*\*: (.+)$', content, re.MULTILINE)
            if id_match:
                interface_id = id_match.group(1)

            # 提取接口名称
            name_match = re.search(r'^\- \*\*接口名称\*\*: (.+)$', content, re.MULTILINE)
            if name_match:
                interface_name = name_match.group(1)

            # 提取接口类型
            type_match = re.search(r'^\- \*\*接口类型\*\*: (.+)$', content, re.MULTILINE)
            if type_match:
                interface_type = type_match.group(1)

            # 提取所属文件
            source_match = re.search(r'^\- \*\*所属文件\*\*: (.+)$', content, re.MULTILINE)
            if source_match:
                source_file = source_match.group(1)

            # 提取业务名称（如果存在）
            business_name_match = re.search(r'^\- \*\*业务名称\*\*: (.+)$', content, re.MULTILINE)
            if business_name_match:
                business_name = business_name_match.group(1)
            else:
                business_name = interface_name

            # 提取业务领域（如果存在）
            business_domain_match = re.search(r'^\- \*\*业务领域\*\*: (.+)$', content, re.MULTILINE)
            if business_domain_match:
                business_domain = business_domain_match.group(1)
            else:
                business_domain = "N/A"

            # 如果从文件内容无法提取到有效ID，则使用文件名
            if interface_id == "N/A" or not interface_id:
                interface_id = filename

            # 生成相对路径用于链接
            relative_file = f"./{file_path.name}"

            # 添加到表格
            interfaces_table.append({
                'interface_id': interface_id,
                'interface_name': business_name,
                'interface_type': interface_type,
                'source_file': business_domain,
                'relative_file': relative_file
            })
        except Exception as e:
            log_warn(f"读取文件 {file_path} 失败: {e}")

    return interfaces_table


def generate_inventory_content(template_content, generated_at, total_count, type_statistics, interfaces_table):
    """生成接口清单内容"""
    # 替换模板变量
    content = template_content
    content = content.replace('{{generated_at}}', generated_at)
    content = content.replace('{{total_count}}', str(total_count))

    # 处理类型统计部分
    if type_statistics:
        type_stats_content = '\n'.join(type_statistics)
        # 使用正则表达式替换整个块
        content = re.sub(r'\{\{#type_statistics\}\}.*?\{\{/type_statistics\}\}',
                        type_stats_content, content, flags=re.DOTALL)
    else:
        # 如果没有类型统计，删除占位符
        content = re.sub(r'\{\{#type_statistics\}\}.*?\{\{/type_statistics\}\}',
                        '', content, flags=re.DOTALL)

    # 处理接口列表部分
    if interfaces_table:
        interfaces_rows = []
        for interface in interfaces_table:
            row = f"| {interface['interface_id']} | {interface['interface_name']} | {interface['interface_type']} | {interface['source_file']} | [{interface['interface_name']}]({interface['relative_file']}) |"
            interfaces_rows.append(row)

        interfaces_content = '\n'.join(interfaces_rows)
        # 使用正则表达式替换整个块
        content = re.sub(r'\{\{#interfaces\}\}.*?\{\{/interfaces\}\}',
                        interfaces_content, content, flags=re.DOTALL)
    else:
        # 如果没有接口列表，删除占位符
        content = re.sub(r'\{\{#interfaces\}\}.*?\{\{/interfaces\}\}',
                        '', content, flags=re.DOTALL)

    return content


def write_with_retry(file_path, content, max_retries=3):
    """带重试机制的文件写入"""
    for retry_count in range(max_retries):
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except Exception as e:
            log_warn(f"写入失败 (第 {retry_count + 1}/{max_retries} 次): {e}")
            if retry_count < max_retries - 1:
                time.sleep(2 ** (retry_count + 1))  # 指数退避
            else:
                log_error(f"写入文件失败，已重试 {max_retries} 次")
                return False
    return False


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='生成接口清单')
    parser.add_argument('--repo-root', required=True, help='仓库根目录')
    parser.add_argument('--help', action='help', help='显示帮助信息')

    args = parser.parse_args()

    repo_root = args.repo_root

    # 检查目录是否存在
    if not os.path.isdir(repo_root):
        log_error(f"仓库根目录不存在: {repo_root}")
        return 1

    # 定义路径
    # 使用 find_template_file 查找模板文件（支持按项目查找）
    # 首先尝试项目特定模板，然后尝试默认模板
    template_file = None
    
    # 1. 尝试项目特定模板（如果配置了项目名称）
    project_name = os.environ.get('OMNISPEC_PROJECT_NAME', '')
    if not project_name:
        # 尝试从配置文件读取
        config_file = os.path.join(repo_root, '.specify', 'config.yaml')
        if os.path.exists(config_file):
            try:
                import yaml
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                    if config and 'project_name' in config:
                        project_name = config['project_name']
            except Exception:
                pass
    
    if project_name:
        project_template = os.path.join(repo_root, '.specify', 'templates', project_name, 'reverse-interface-inventory-template.md')
        if os.path.exists(project_template):
            template_file = project_template
    
    # 2. 尝试项目根目录下的默认模板（向后兼容）
    if not template_file:
        project_default = os.path.join(repo_root, '.specify', 'templates', 'reverse-interface-inventory-template.md')
        if os.path.exists(project_default):
            template_file = project_default
    
    # 3. 尝试项目根目录下的 default 子目录模板
    if not template_file:
        project_default_dir = os.path.join(repo_root, '.specify', 'templates', 'default', 'reverse-interface-inventory-template.md')
        if os.path.exists(project_default_dir):
            template_file = project_default_dir
    
    # 4. 尝试系统默认模板
    if not template_file:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        omnispec_root = os.path.abspath(os.path.join(script_dir, '../../../../..'))
        system_default = os.path.join(omnispec_root, 'specify', 'templates', 'default', 'reverse-interface-inventory-template.md')
        if os.path.exists(system_default):
            template_file = system_default
        else:
            # 向后兼容：系统根目录下的模板
            system_template = os.path.join(omnispec_root, 'specify', 'templates', 'reverse-interface-inventory-template.md')
            if os.path.exists(system_template):
                template_file = system_template
    
    if not template_file or not os.path.exists(template_file):
        log_error(f"接口清单模板文件未找到")
        return 1
    
    # 默认输出目录：{REPO_ROOT}/omni-doc/interfaces
    output_dir = os.path.join(repo_root, 'omni-doc', 'interfaces')
    inventory_file = os.path.join(output_dir, '接口清单.md')
    interface_list_file = os.path.join(repo_root, '.cache', 'omni-reverse', 'interfaces', 'interface-list.json')

    # 检查输出目录是否存在，不存在则创建
    os.makedirs(output_dir, exist_ok=True)

    log_info("开始生成接口清单...")

    # 获取生成时间
    generated_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # 获取统计数据
    total_count, type_statistics = get_interface_stats(interface_list_file)

    # 如果从接口列表文件无法获取统计信息，则通过扫描output目录来统计
    if total_count == 0:
        try:
            interface_files = list(Path(output_dir).glob("*.md"))
            interface_files = [f for f in interface_files if f.name != "接口清单.md"]
            total_count = len(interface_files)
        except Exception as e:
            log_warn(f"统计接口文件数量失败: {e}")

    # 收集接口详情信息
    interfaces_table = collect_interface_info(output_dir)

    # 如果通过扫描获得了更多接口信息，则更新总数
    if len(interfaces_table) > total_count:
        total_count = len(interfaces_table)

    # 读取模板内容
    template_content = read_template(template_file)
    if template_content is None:
        return 1

    # 生成接口清单内容
    final_content = generate_inventory_content(template_content, generated_at, total_count, type_statistics, interfaces_table)

    # 写入重试机制
    if write_with_retry(inventory_file, final_content):
        # 验证生成的文件
        if os.path.exists(inventory_file):
            try:
                file_size = os.path.getsize(inventory_file)
                if file_size > 0:
                    log_info(f"接口清单生成完成，文件大小: {file_size} 字节")
                    print(f"接口清单已生成到: {inventory_file}")
                    return 0
                else:
                    log_error("生成的接口清单文件为空")
                    return 1
            except Exception as e:
                log_error(f"验证生成文件失败: {e}")
                return 1
        else:
            log_error(f"接口清单文件未找到: {inventory_file}")
            return 1
    else:
        return 1


if __name__ == '__main__':
    exit(main())