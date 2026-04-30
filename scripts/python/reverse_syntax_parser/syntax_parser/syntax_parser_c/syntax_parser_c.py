#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import json
from pathlib import Path
from .constants import UUID_SEPARATOR

# 导入日志模块 - 使用reverse_syntax_parser的utils
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from utils import get_logger

from .parsers.c_parser import CParser

def make_json_serializable(obj):
    """确保对象可以被JSON序列化"""
    if isinstance(obj, dict):
        return {k: make_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [make_json_serializable(item) for item in obj]
    elif isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    else:
        # 对于其他不可序列化的对象，转换为字符串表示
        return str(obj)

def c_code_syntax_parsing(prj_path: str, output_path: str):
    """
    C语言代码语法解析
    
    Args:
        prj_path: 项目路径
        output_path: 输出路径（必须提供）
    """
    # 初始化日志记录器
    logger = get_logger("syntax_parser_c")
    logger.info("C语言代码语法解析开始")
    
    # 使用提供的输出路径
    codebase_path = output_path
    
    os.makedirs(codebase_path, exist_ok=True)
    logger.info(f"C语法解析输出路径: {codebase_path}")

    parser = CParser()
    logger.info(f"开始解析项目: {prj_path}")
    elements = parser.parse_project(prj_path)
    logger.info(f"项目解析完成，共解析 {len(elements)} 个元素")
    
    # 按类型分类元素 - C语言不包含类和方法
    classified_elements = {
        'function_definition': {},
        'global_variable': {},
        'macro_definition': {},
        'type_definition': {}
    }
    
    # 将元素按类型分类 - C语言简化版本
    for uuid_key, info in elements.items():
        element_type = info.get('type')
        if element_type in classified_elements:
            classified_elements[element_type][uuid_key] = info
    
    # 重建名称到UUID映射表
    parser._rebuild_name_to_uuid_map_after_split(classified_elements)
    
    # 更新依赖关系
    parser._update_dependencies_after_split(classified_elements)
    
    # 检查解析结果统计
    logger.info("解析结果统计:")
    logger.info(f"  函数数量: {len(classified_elements['function_definition'])}")
    logger.info(f"  全局变量数量: {len(classified_elements['global_variable'])}")
    logger.info(f"  宏定义数量: {len(classified_elements['macro_definition'])}")
    logger.info(f"  类型定义数量: {len(classified_elements['type_definition'])}")
    
    # 将每种类型的元素保存到对应的文件中 - C语言版本
    file_mapping = {
        'function_definition': 'all_functions.json',
        'global_variable': 'all_global_vars.json',
        'macro_definition': 'all_macros.json',
        'type_definition': 'all_datatype.json'
    }
    
    logger.info("开始保存分类后的元素到JSON文件")
    for element_type, elements_dict in classified_elements.items():
        output_file_name = file_mapping.get(element_type, f'all_{element_type}.json')
        output_file_path = os.path.join(codebase_path, output_file_name)
        
        logger.info(f'正在保存 {element_type}，包含 {len(elements_dict)} 个元素...')
        try:
            # 清理数据格式
            if element_type == 'type_definition':
                cleaned_elements = {}
                for key, value in elements_dict.items():
                    if 'dependencies' in value and not value['dependencies']:
                        value = dict(value)  # 创建副本
                        del value['dependencies']
                    cleaned_elements[key] = value
                elements_dict = cleaned_elements
            elif element_type == 'global_variable':
                # 清理全局变量格式，移除多余字段
                cleaned_elements = {}
                for key, value in elements_dict.items():
                    value = dict(value)  # 创建副本
                    # 移除多余字段
                    fields_to_remove = ['lineno', 'end_lineno', 'access_modifier', 'is_static', 
                                      'is_const', 'initial_value', 'dependencies', 'uuid']
                    for field in fields_to_remove:
                        if field in value:
                            del value[field]
                    cleaned_elements[key] = value
                elements_dict = cleaned_elements
            
            # 确保数据可以JSON序列化
            safe_elements_dict = make_json_serializable(elements_dict)
            
            with open(output_file_path, 'w', encoding='utf-8') as f:
                json.dump(safe_elements_dict, f, ensure_ascii=False, indent=4)
            logger.info(f'已成功保存 {element_type} 到 {output_file_path}')
            
            # 验证文件完整性
            with open(output_file_path, 'r', encoding='utf-8') as f:
                json.load(f)
            logger.info(f'文件 {output_file_name} JSON 格式验证通过')
            
        except Exception as e:
            logger.error(f'保存 {element_type} 时出错: {e}', exc_info=True)
            raise

    # C语言不支持类和方法，创建空文件以保持格式一致性
    logger.info("创建空的类和方法文件（C语言不支持）")
    try:
        # 创建空的 all_class.json
        all_class_path = os.path.join(codebase_path, 'all_class.json')
        with open(all_class_path, 'w', encoding='utf-8') as f:
            json.dump({}, f, ensure_ascii=False, indent=4)
        logger.info(f'已创建空的 all_class.json')
        
        # 创建空的 all_methods.json
        all_methods_path = os.path.join(codebase_path, 'all_methods.json')
        with open(all_methods_path, 'w', encoding='utf-8') as f:
            json.dump({}, f, ensure_ascii=False, indent=4)
        logger.info(f'已创建空的 all_methods.json')
    except Exception as e:
        logger.error(f'创建空文件时出错: {e}', exc_info=True)

    # 生成 code_type.json 文件 - C语言版本
    code_type_data = {
        "language": "c",
        "description": "C language codebase parsing result",
        "parser_type": "syntax_parser_c",
        "timestamp": None,  # 可以根据需要添加时间戳
        "related_json_files": [
            "all_class.json",
            "all_datatype.json", 
            "all_functions.json",
            "all_global_vars.json",
            "all_macros.json",
            "all_methods.json"
        ],
        "parsed_elements": {
            "function_definition": len(classified_elements['function_definition']),
            "global_variable": len(classified_elements['global_variable']),
            "macro_definition": len(classified_elements['macro_definition']),
            "type_definition": len(classified_elements['type_definition']),
            "class_definition": 0,
            "method_definition": 0
        }
    }
    
    code_type_path = os.path.join(codebase_path, 'code_type.json')
    try:
        with open(code_type_path, 'w', encoding='utf-8') as f:
            json.dump(code_type_data, f, ensure_ascii=False, indent=4)
        logger.info(f'已成功生成 code_type.json 到 {code_type_path}')
    except Exception as e:
        logger.error(f'生成 code_type.json 时出错: {e}', exc_info=True)

    logger.info("C语法解析成功")
    return "C语法解析成功"

if __name__ == '__main__':
    # 初始化日志记录器
    logger = get_logger("syntax_parser_c")
    logger.info("C语法解析工具启动")
    
    if len(sys.argv) < 3:
        logger.error("参数不足")
        logger.error("用法: python syntax_parser_c.py <项目路径> <输出路径>")
        logger.error("示例: python syntax_parser_c.py /path/to/project /path/to/output")
        sys.exit(1)
    
    project_path = sys.argv[1]
    output_path = sys.argv[2]
    
    logger.info(f"项目路径: {project_path}")
    logger.info(f"输出路径: {output_path}")
    
    # 检查项目路径是否存在
    if not os.path.exists(project_path):
        logger.error(f"项目路径不存在: {project_path}")
        sys.exit(1)
    
    c_code_syntax_parsing(project_path, output_path)
