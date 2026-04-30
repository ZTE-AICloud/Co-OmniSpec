#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import json
import uuid
from pathlib import Path
from .constants import UUID_SEPARATOR

# 导入日志模块 - 使用reverse_syntax_parser的utils
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from utils import get_logger

from .parsers.java_parser import JavaParser

def make_json_serializable(obj):
    """递归地将对象转换为JSON可序列化的格式"""
    if isinstance(obj, dict):
        return {k: make_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [make_json_serializable(item) for item in obj]
    elif isinstance(obj, bytes):
        try:
            # 尝试解码为字符串
            return f"b'{obj.decode('utf-8', errors='ignore')}'"
        except:
            return f"b'<{len(obj)} bytes>'"
    elif isinstance(obj, (int, float, str, bool, type(None))):
        return obj
    else:
        # 对于其他不可序列化的对象，转换为字符串表示
        return str(obj)

def java_code_syntax_parsing(prj_path: str, output_path: str):
    """
    Java代码语法解析
    
    Args:
        prj_path: 项目路径
        output_path: 输出路径（必须提供）
    """
    # 初始化日志记录器
    logger = get_logger("syntax_parser_java")
    logger.info("Java代码语法解析开始")
    
    # 使用提供的输出路径
    codebase_path = output_path
    
    os.makedirs(codebase_path, exist_ok=True)
    logger.info(f"Java语法解析输出路径: {codebase_path}")
    
    parser = JavaParser()
    logger.info(f"开始解析项目: {prj_path}")
    elements = parser.parse_project(prj_path)
    logger.info(f"项目解析完成，共解析 {len(elements)} 个元素")
    
    # 按类型分类元素
    classified_elements = {
        'class_definition': {},
        'method_definition': {},
        'annotation_definition': {},
        'import_statement': {}
    }
    
    # 将元素按类型分类，同时提取方法
    for name, info in elements.items():
        element_type = info.get('type')
        
        if element_type == 'class_definition':
            # 处理类：提取方法和内部类并修改类结构
            class_info = info.copy()
            class_uuid = class_info.get('uuid')
            methods = class_info.get('methods', {})
            inner_classes = class_info.get('inner_classes', {})
            
            # 提取方法到单独的分类
            for method_key, method_info in methods.items():
                # 为方法添加所属类的信息
                method_info = method_info.copy()
                class_name = class_info.get('name')
                class_key = f"{class_name}{UUID_SEPARATOR}{class_uuid}"
                method_info['class_key'] = class_key
                method_info['type'] = 'method_definition'
                classified_elements['method_definition'][method_key] = method_info
            
            # 提取内部类到单独的分类
            inner_class_keys = []
            for inner_class_key, inner_class_info in inner_classes.items():
                # 内部类作为独立的类定义
                inner_class_info = inner_class_info.copy()
                inner_class_info['type'] = 'class_definition'
                inner_class_info['outer_class'] = f"{class_info.get('name')}{UUID_SEPARATOR}{class_uuid}"
                classified_elements['class_definition'][inner_class_key] = inner_class_info
                inner_class_keys.append(inner_class_key)
            
            # 修改类信息：移除methods和inner_classes字段，添加键列表
            method_keys = list(methods.keys())
            class_info['method_keys'] = method_keys
            class_info['inner_class_keys'] = inner_class_keys  # 只保存内部类的键引用
            
            if 'methods' in class_info:
                del class_info['methods']
            if 'inner_classes' in class_info:
                del class_info['inner_classes']  # 移除完整的内部类信息
            
            classified_elements['class_definition'][name] = class_info
            
        elif element_type == 'interface_definition':
            # 处理接口：将接口归类为类定义
            interface_info = info.copy()
            interface_uuid = interface_info.get('uuid')
            methods = interface_info.get('methods', {})
            constants = interface_info.get('constants', {})
            
            # 提取接口方法
            for method_key, method_info in methods.items():
                method_info = method_info.copy()
                interface_name = interface_info.get('name')
                interface_key = f"{interface_name}{UUID_SEPARATOR}{interface_uuid}"
                method_info['class_key'] = interface_key  # 接口也使用class_key字段
                method_info['type'] = 'method_definition'
                classified_elements['method_definition'][method_key] = method_info
            
            # Java接口中的常量是类成员，不需要单独处理
            
            # 修改接口信息
            method_keys = list(methods.keys())
            interface_info['method_keys'] = method_keys
            if 'methods' in interface_info:
                del interface_info['methods']
            if 'constants' in interface_info:
                del interface_info['constants']
            
            # 接口归类为类定义
            classified_elements['class_definition'][name] = interface_info
            
        elif element_type == 'enum_definition':
            # 枚举归类为类定义
            classified_elements['class_definition'][name] = info
            
        elif element_type == 'function_definition':
            # Java中的静态方法归类为方法定义
            info['type'] = 'method_definition'
            classified_elements['method_definition'][name] = info
            
        elif element_type in ['constant_definition', 'instance_variable', 'class_variable', 'local_variable', 'parameter']:
            # Java中没有独立的全局变量，这些都是类成员，跳过处理
            continue
            
        elif element_type == 'annotation_definition':
            # 处理注解：如果是注解实例集合，需要拆分为独立的注解条目
            if 'annotations' in info and isinstance(info['annotations'], list):
                # 这是注解使用实例的集合，需要拆分
                for i, annotation in enumerate(info['annotations']):
                    # 为每个注解创建独立的条目
                    unique_id = str(uuid.uuid4())
                    annotation_key = f"{annotation['name']}{UUID_SEPARATOR}{unique_id}"
                    
                    annotation_entry = {
                        "type": "annotation_definition",
                        "content": annotation.get('raw_text', ''),
                        "filename": info.get('filename', ''),
                        "name": annotation['name'],
                        "uuid": unique_id,
                        "target_type": info.get('target_type', 'unknown'),
                        "target_name": info.get('target_name', ''),
                        "access_modifier": "public",  # 注解默认public
                        "params": annotation.get('params', {}),
                        "annotation_type": annotation.get('type', 'custom'),
                        "dependencies": [],
                        "lineno": info.get('lineno', 0),
                        "end_lineno": info.get('end_lineno', 0)
                    }
                    
                    classified_elements['annotation_definition'][annotation_key] = annotation_entry
            elif 'meta_annotations' in info:
                # 这是注解定义类（@interface），直接保存
                classified_elements['annotation_definition'][name] = info
            else:
                # 其他注解相关信息
                classified_elements['annotation_definition'][name] = info
                
        elif element_type in classified_elements:
            classified_elements[element_type][name] = info
    
    # 重新构建映射表，包含拆分后的方法信息
    parser._rebuild_name_to_uuid_map_after_split(classified_elements)
    
    # 重新解析所有依赖关系（包括函数与方法间的调用）
    parser._update_dependencies_after_split(classified_elements)
    
    # 将每种类型的元素保存到对应的文件中
    file_mapping = {
        'class_definition': 'all_class.json',
        'method_definition': 'all_methods.json',
        'import_statement': 'all_imports.json',
        'annotation_definition': 'all_annotations.json',
        'function_definition': 'all_functions.json'  # Java中函数定义为空（Java没有独立函数）
    }
    
    # 添加空的 function_definition（Java中没有独立的全局函数）
    classified_elements['function_definition'] = {}
    
    for element_type, elements_dict in classified_elements.items():
        output_file_name = file_mapping.get(element_type, f'all_{element_type}.json')
        output_file_path = os.path.join(codebase_path, output_file_name)
        
        logger.info(f"正在保存 {element_type}，包含 {len(elements_dict)} 个元素...")
        try:
            # 确保数据可以JSON序列化
            safe_elements_dict = make_json_serializable(elements_dict)
            
            with open(output_file_path, 'w', encoding='utf-8') as f:
                json.dump(safe_elements_dict, f, ensure_ascii=False, indent=4)
            logger.info(f"已成功保存 {element_type} 到 {output_file_path}")
            
            # 验证文件完整性
            with open(output_file_path, 'r', encoding='utf-8') as f:
                json.load(f)
            logger.info(f"文件 {output_file_name} JSON 格式验证通过")
            
        except Exception as e:
            logger.error(f"保存 {element_type} 时出错: {e}", exc_info=True)
            raise

    # 生成 code_type.json 文件
    code_type_data = {
        "language": "java",
        "description": "Java language codebase parsing result",
        "parser_type": "syntax_parser_java",
        "timestamp": None,  # 可以根据需要添加时间戳
        "related_json_files": [
            "all_annotations.json",
            "all_class.json",
            "all_functions.json",
            "all_imports.json",
            "all_methods.json"
        ],
        "parsed_elements": {
            "class_definition": len(classified_elements['class_definition']),
            "method_definition": len(classified_elements['method_definition']),
            "annotation_definition": len(classified_elements['annotation_definition']),
            "import_statement": len(classified_elements['import_statement']),
            "function_definition": len(classified_elements['function_definition'])
        }
    }
    
    code_type_path = os.path.join(codebase_path, 'code_type.json')
    try:
        with open(code_type_path, 'w', encoding='utf-8') as f:
            json.dump(code_type_data, f, ensure_ascii=False, indent=4)
        logger.info(f"已成功生成 code_type.json 到 {code_type_path}")
    except Exception as e:
        logger.error(f"生成 code_type.json 时出错: {e}", exc_info=True)

    logger.info("Java语法解析成功")
    return "Java语法解析成功"

if __name__ == '__main__':
    # 初始化日志记录器
    logger = get_logger("syntax_parser_java")
    logger.info("Java语法解析工具启动")
    
    if len(sys.argv) < 3:
        logger.error("参数不足")
        logger.error("用法: python syntax_parser_java.py <项目路径> <输出路径>")
        logger.error("示例: python syntax_parser_java.py /path/to/project /path/to/output")
        sys.exit(1)
    
    project_path = sys.argv[1]
    output_path = sys.argv[2]
    
    logger.info(f"项目路径: {project_path}")
    logger.info(f"输出路径: {output_path}")
    
    # 检查项目路径是否存在
    if not os.path.exists(project_path):
        logger.error(f"项目路径不存在: {project_path}")
        sys.exit(1)
    
    java_code_syntax_parsing(project_path, output_path)
