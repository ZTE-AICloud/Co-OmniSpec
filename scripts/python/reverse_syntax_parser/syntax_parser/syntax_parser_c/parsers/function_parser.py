#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
from pathlib import Path

# 导入日志模块
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from utils import get_logger

class FunctionParser:
    def __init__(self):
        self.logger = get_logger("function_parser")

    def parse_function(self, node, source_code, file_path):
        """解析C语言函数定义"""
        function_info = {
            'name': '',
            'return_type': '',
            'elem_datatype': '',  # 新增字段：函数返回类型
            'parameters': [],
            'content': '',
            'filename': file_path,
            'lineno': node.start_point[0] + 1,
            'end_lineno': node.end_point[0] + 1,
            'access_modifier': 'public',  # C语言中所有函数默认为public
            'is_static': False,
            'dependencies': []
        }

        try:
            # 将源码转换为字节以确保正确的边界
            source_bytes = source_code.encode('utf-8')
            
            # 获取函数内容（使用字节索引）
            function_bytes = source_bytes[node.start_byte:node.end_byte]
            function_info['content'] = function_bytes.decode('utf-8', errors='ignore')
            
            # 解析函数声明部分
            declarator = None
            pointer_depth = 0
            return_type_node = None
            
            for child in node.children:
                if child.type == 'function_declarator':
                    declarator = child
                elif child.type == 'pointer_declarator':
                    declarator, pointer_depth = self._find_function_declarator(child)
                elif child.type in ['type_specifier', 'primitive_type']:
                    return_type_node = child
                elif child.type == 'storage_class_specifier':
                    # 检查是否为static
                    storage_bytes = source_bytes[child.start_byte:child.end_byte]
                    storage_class = storage_bytes.decode('utf-8', errors='ignore')
                    if storage_class.strip() == 'static':
                        function_info['is_static'] = True
            
            if not declarator:
                declarator, pointer_depth = self._find_function_declarator(node)
            
            # 检查是否找到了declarator
            if not declarator:
                self.logger.warning(f"无法找到函数声明符，跳过函数解析: {file_path}:{node.start_point[0] + 1}")
                return None
            
            # 获取函数名
            for child in declarator.children:
                if child.type == 'identifier':
                    name_bytes = source_bytes[child.start_byte:child.end_byte]
                    function_info['name'] = name_bytes.decode('utf-8', errors='ignore').strip()
                    break
            
            # 获取返回类型
            if return_type_node:
                type_bytes = source_bytes[return_type_node.start_byte:return_type_node.end_byte]
                return_type = type_bytes.decode('utf-8', errors='ignore').strip()
                if pointer_depth:
                    return_type = f"{return_type} {'*' * pointer_depth}".strip()
                function_info['return_type'] = return_type
                function_info['elem_datatype'] = return_type  # 设置elem_datatype为返回类型
            
            # 获取参数列表
            for child in declarator.children:
                if child.type == 'parameter_list':
                    function_info['parameters'] = self._parse_parameters(child, source_code, source_bytes)
                    break
            
            # 验证函数名是否有效
            if not function_info['name'] or not function_info['name'].replace('_', '').replace(' ', '').isalnum():
                return None
                
            return function_info
            
        except Exception as e:
            self.logger.error(f"解析函数时出错: {e}", exc_info=True)
            return None

    def _parse_parameters(self, parameter_list_node, source_code, source_bytes):
        """解析函数参数列表"""
        parameters = []
        
        for child in parameter_list_node.children:
            if child.type == 'parameter_declaration':
                param_info = self._parse_parameter(child, source_code, source_bytes)
                if param_info:
                    parameters.append(param_info)
        
        return parameters

    def _parse_parameter(self, param_node, source_code, source_bytes):
        """解析单个函数参数"""
        param_info = {
            'name': '',
            'type': '',
            'default_value': None
        }
        
        try:
            # 获取参数类型和名称
            for child in param_node.children:
                if child.type in ['type_specifier', 'primitive_type']:
                    type_bytes = source_bytes[child.start_byte:child.end_byte]
                    param_info['type'] = type_bytes.decode('utf-8', errors='ignore').strip()
                elif child.type == 'identifier':
                    name_bytes = source_bytes[child.start_byte:child.end_byte]
                    param_info['name'] = name_bytes.decode('utf-8', errors='ignore').strip()
                elif child.type == 'pointer_declarator':
                    # 处理指针类型
                    param_info['type'] += '*'
                    for subchild in child.children:
                        if subchild.type == 'identifier':
                            name_bytes = source_bytes[subchild.start_byte:subchild.end_byte]
                            param_info['name'] = name_bytes.decode('utf-8', errors='ignore').strip()
            
            return param_info
            
        except Exception as e:
            self.logger.error(f"解析参数时出错: {e}", exc_info=True)
            return None

    def _find_function_declarator(self, node, pointer_depth=0):
        """递归查找function_declarator，并统计指针层级"""
        if node.type == 'function_declarator':
            return node, pointer_depth
        for child in node.children:
            additional_depth = pointer_depth + 1 if child.type == 'pointer_declarator' else pointer_depth
            result, depth = self._find_function_declarator(child, additional_depth)
            if result:
                return result, depth
        return None, pointer_depth
