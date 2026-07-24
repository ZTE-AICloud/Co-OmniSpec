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

from .parsers.cpp_parser import CppParser

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

def cpp_code_syntax_parsing(prj_path: str, output_path: str):
    """
    C++代码语法解析
    
    Args:
        prj_path: 项目路径
        output_path: 输出路径（必须提供）
    """
    # 初始化日志记录器
    logger = get_logger("syntax_parser_cpp")
    logger.info("C++代码语法解析开始")
    
    # 使用提供的输出路径
    codebase_path = output_path
    
    os.makedirs(codebase_path, exist_ok=True)
    logger.info(f"C++语法解析输出路径: {codebase_path}")

    parser = CppParser()
    logger.info(f"开始解析项目: {prj_path}")
    elements = parser.parse_project(prj_path)
    logger.info(f"项目解析完成，共解析 {len(elements)} 个元素")
    
    # 按类型分类元素
    classified_elements = {
        'function_definition': {},
        'global_variable': {},
        'macro_definition': {},
        'class_definition': {},
        'method_definition': {},  # 新增方法分类
        'type_definition': {}
    }
    
    # 将元素按类型分类，同时提取方法
    # 先收集所有需要处理的数据，避免在遍历时修改字典
    elements_to_process = []
    methods_to_add = []
    
    for uuid_key, info in elements.items():
        element_type = info.get('type')
        if element_type == 'class_definition':
            # 处理类，提取其中的方法
            class_info = info.copy()
            class_uuid = class_info.get('uuid')
            methods = class_info.get('methods', {})
            
            # 收集需要添加的方法
            for method_key, method_info in methods.items():
                method_info = method_info.copy()
                class_name = class_info.get('name')
                class_key = "{}{}{}".format(class_name, UUID_SEPARATOR, class_uuid)
                method_info['class_key'] = class_key
                method_info['type'] = 'method_definition'
                
                # 确保每个方法都有filename和dependencies字段
                if 'filename' not in method_info:
                    method_info['filename'] = class_info.get('filename', '')
                if 'dependencies' not in method_info:
                    method_info['dependencies'] = []
                    
                methods_to_add.append((method_key, method_info))
            
            # 更新类信息，改为method_keys列表
            method_keys = list(methods.keys())
            class_info['method_keys'] = method_keys
            if 'methods' in class_info:  # 安全删除
                del class_info['methods']
            
            elements_to_process.append(('class_definition', uuid_key, class_info))
        elif element_type in classified_elements:
            elements_to_process.append((element_type, uuid_key, info))
    
    # 在遍历完成后进行更新
    for element_type, uuid_key, info in elements_to_process:
        classified_elements[element_type][uuid_key] = info
    
    # 添加方法到分类元素中
    for method_key, method_info in methods_to_add:
        classified_elements['method_definition'][method_key] = method_info
    
    # 重建名称到UUID映射表以包含分离后的方法（如果有方法的话）
    parser._rebuild_name_to_uuid_map_after_split(classified_elements)
    
    # 更新依赖关系
    parser._update_dependencies_after_split(classified_elements)
    
    # 检查解析结果统计
    logger.info("解析结果统计:")
    logger.info(f"  函数数量: {len(classified_elements['function_definition'])}")
    logger.info(f"  类数量: {len(classified_elements['class_definition'])}")
    logger.info(f"  方法数量: {len(classified_elements['method_definition'])}")
    logger.info(f"  全局变量数量: {len(classified_elements['global_variable'])}")
    logger.info(f"  宏定义数量: {len(classified_elements['macro_definition'])}")
    logger.info(f"  类型定义数量: {len(classified_elements['type_definition'])}")
    
    # 将每种类型的元素保存到对应的文件中
    file_mapping = {
        'function_definition': 'all_functions.json',
        'class_definition': 'all_class.json',
        'method_definition': 'all_methods.json',  # 新增方法文件
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

    # 生成 code_type.json 文件
    code_type_data = {
        "language": "cpp",
        "description": "C++ language codebase parsing result",
        "parser_type": "syntax_parser_cpp",
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
            "class_definition": len(classified_elements['class_definition']),
            "method_definition": len(classified_elements['method_definition']),
            "global_variable": len(classified_elements['global_variable']),
            "macro_definition": len(classified_elements['macro_definition']),
            "type_definition": len(classified_elements['type_definition'])
        }
    }
    
    code_type_path = os.path.join(codebase_path, 'code_type.json')
    try:
        with open(code_type_path, 'w', encoding='utf-8') as f:
            json.dump(code_type_data, f, ensure_ascii=False, indent=4)
        logger.info(f'已成功生成 code_type.json 到 {code_type_path}')
    except Exception as e:
        logger.error(f'生成 code_type.json 时出错: {e}', exc_info=True)

    logger.info("C++语法解析成功")
    return "C++语法解析成功"

if __name__ == '__main__':
    # 初始化日志记录器
    logger = get_logger("syntax_parser_cpp")
    logger.info("C++语法解析工具启动")
    
    if len(sys.argv) < 3:
        logger.error("参数不足")
        logger.error("用法: python syntax_parser_cpp.py <项目路径> <输出路径>")
        logger.error("示例: python syntax_parser_cpp.py /path/to/project /path/to/output")
        sys.exit(1)
    
    project_path = sys.argv[1]
    output_path = sys.argv[2]
    
    logger.info(f"项目路径: {project_path}")
    logger.info(f"输出路径: {output_path}")
    
    # 检查项目路径是否存在
    if not os.path.exists(project_path):
        logger.error(f"项目路径不存在: {project_path}")
        sys.exit(1)
    
    cpp_code_syntax_parsing(project_path, output_path) 