import pathlib
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

# 导入日志模块
sys.path.append(str(Path(__file__).parent.parent.parent / "utils"))
from sys import path
path.insert(0, str(pathlib.Path(__file__).parent.parent.parent.parent))
from utils import get_logger

class VariableParser:
    def __init__(self):
        self.logger = get_logger("variable_parser")

    def parse_variable(self, node, source_code, file_path):
        """解析C语言全局变量声明"""
        variable_info = {
            'type': 'global_variable',
            'content': '',
            'filename': file_path,
            'datatype': '',
            'name': ''
        }

        try:
            # 使用字节安全的方法
            source_bytes = source_code.encode('utf-8')
            
            # 获取变量声明内容
            var_bytes = source_bytes[node.start_byte:node.end_byte]
            variable_info['content'] = var_bytes.decode('utf-8', errors='ignore')
            
            # 解析变量类型和名称
            for child in node.children:
                if child.type in ['type_specifier', 'primitive_type']:
                    # 获取变量数据类型
                    type_bytes = source_bytes[child.start_byte:child.end_byte]
                    variable_info['datatype'] = type_bytes.decode('utf-8', errors='ignore').strip()
                elif child.type == 'init_declarator':
                    # 处理带初始化的声明
                    self._parse_init_declarator(child, source_code, source_bytes, variable_info)
                elif child.type == 'identifier':
                    # 直接的标识符
                    name_bytes = source_bytes[child.start_byte:child.end_byte]
                    variable_info['name'] = name_bytes.decode('utf-8', errors='ignore').strip()
            
            # 如果没有获取到变量名，返回None
            if not variable_info['name']:
                return None
                
            return variable_info
            
        except Exception as e:
            self.logger.error(f"解析变量时出错: {e}", exc_info=True)
            return None

    def _parse_init_declarator(self, init_declarator_node, source_code, source_bytes, variable_info):
        """解析带初始化的声明器"""
        for child in init_declarator_node.children:
            if child.type == 'identifier':
                name_bytes = source_bytes[child.start_byte:child.end_byte]
                variable_info['name'] = name_bytes.decode('utf-8', errors='ignore').strip()
            elif child.type == 'pointer_declarator':
                # 处理指针类型
                variable_info['datatype'] += '*'
                for subchild in child.children:
                    if subchild.type == 'identifier':
                        name_bytes = source_bytes[subchild.start_byte:subchild.end_byte]
                        variable_info['name'] = name_bytes.decode('utf-8', errors='ignore').strip()

    def parse_struct_member(self, node, source_code, file_path):
        """解析结构体成员变量"""
        member_info = {
            'name': '',
            'type': '',
            'content': '',
            'filename': file_path,
            'lineno': node.start_point[0] + 1,
            'end_lineno': node.end_point[0] + 1,
            'is_array': False,
            'array_size': None
        }

        try:
            # 获取成员内容
            member_info['content'] = source_code[node.start_byte:node.end_byte]
            
            for child in node.children:
                if child.type in ['type_specifier', 'primitive_type']:
                    member_info['type'] = source_code[child.start_byte:child.end_byte]
                elif child.type == 'field_declarator':
                    self._parse_field_declarator(child, source_code, member_info)
                elif child.type == 'identifier':
                    member_info['name'] = source_code[child.start_byte:child.end_byte]
            
            return member_info if member_info['name'] else None
            
        except Exception as e:
            self.logger.error(f"解析结构体成员时出错: {e}", exc_info=True)
            return None

    def _parse_field_declarator(self, field_declarator_node, source_code, member_info):
        """解析字段声明器"""
        for child in field_declarator_node.children:
            if child.type == 'identifier':
                member_info['name'] = source_code[child.start_byte:child.end_byte]
            elif child.type == 'array_declarator':
                # 处理数组成员
                member_info['is_array'] = True
                for subchild in child.children:
                    if subchild.type == 'identifier':
                        member_info['name'] = source_code[subchild.start_byte:subchild.end_byte]
                    elif subchild.type == 'number_literal':
                        member_info['array_size'] = source_code[subchild.start_byte:subchild.end_byte]
            elif child.type == 'pointer_declarator':
                # 处理指针成员
                member_info['type'] += '*'
                for subchild in child.children:
                    if subchild.type == 'identifier':
                        member_info['name'] = source_code[subchild.start_byte:subchild.end_byte]
