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

class TypeParser:
    def __init__(self):
        self.logger = get_logger("type_parser")

    def parse_struct(self, node, source_code, file_path):
        """解析C语言结构体定义"""
        struct_info = {
            'name': '',
            'content': '',
            'members': [],
            'filename': file_path,
            'lineno': node.start_point[0] + 1,
            'end_lineno': node.end_point[0] + 1,
            'size': None,
            'dependencies': []
        }

        try:
            # 使用字节安全的方法
            source_bytes = source_code.encode('utf-8')
            
            # 获取结构体内容
            struct_bytes = source_bytes[node.start_byte:node.end_byte]
            struct_info['content'] = struct_bytes.decode('utf-8', errors='ignore')
            
            # 解析结构体名称和成员
            for child in node.children:
                if child.type == 'type_identifier':
                    # 获取结构体名称
                    name_bytes = source_bytes[child.start_byte:child.end_byte]
                    struct_info['name'] = name_bytes.decode('utf-8', errors='ignore').strip()
                elif child.type == 'field_declaration_list':
                    # 解析成员列表
                    struct_info['members'] = self._parse_struct_members(child, source_code, source_bytes, file_path)
            
            return struct_info if struct_info['name'] else None
            
        except Exception as e:
            self.logger.error(f"解析结构体时出错: {e}", exc_info=True)
            return None

    def _parse_struct_members(self, field_list_node, source_code, source_bytes, file_path):
        """解析结构体成员列表"""
        members = []
        
        for child in field_list_node.children:
            if child.type == 'field_declaration':
                member_info = self._parse_struct_member(child, source_code, source_bytes, file_path)
                if member_info:
                    members.append(member_info)
        
        return members

    def _parse_struct_member(self, field_node, source_code, source_bytes, file_path):
        """解析结构体成员"""
        member_info = {
            'name': '',
            'type': '',
            'content': '',
            'is_array': False,
            'array_size': None,
            'is_pointer': False
        }

        try:
            # 获取成员内容
            member_bytes = source_bytes[field_node.start_byte:field_node.end_byte]
            member_info['content'] = member_bytes.decode('utf-8', errors='ignore')
            
            for child in field_node.children:
                if child.type in ['type_specifier', 'primitive_type']:
                    type_bytes = source_bytes[child.start_byte:child.end_byte]
                    member_info['type'] = type_bytes.decode('utf-8', errors='ignore').strip()
                elif child.type == 'field_declarator':
                    self._parse_field_declarator(child, source_code, source_bytes, member_info)
                elif child.type == 'identifier':
                    name_bytes = source_bytes[child.start_byte:child.end_byte]
                    member_info['name'] = name_bytes.decode('utf-8', errors='ignore').strip()
            
            return member_info if member_info['name'] else None
            
        except Exception as e:
            self.logger.error(f"解析结构体成员时出错: {e}", exc_info=True)
            return None

    def _parse_field_declarator(self, declarator_node, source_code, source_bytes, member_info):
        """解析字段声明器"""
        for child in declarator_node.children:
            if child.type == 'identifier':
                name_bytes = source_bytes[child.start_byte:child.end_byte]
                member_info['name'] = name_bytes.decode('utf-8', errors='ignore').strip()
            elif child.type == 'array_declarator':
                member_info['is_array'] = True
                for subchild in child.children:
                    if subchild.type == 'identifier':
                        name_bytes = source_bytes[subchild.start_byte:subchild.end_byte]
                        member_info['name'] = name_bytes.decode('utf-8', errors='ignore').strip()
                    elif subchild.type == 'number_literal':
                        size_bytes = source_bytes[subchild.start_byte:subchild.end_byte]
                        member_info['array_size'] = size_bytes.decode('utf-8', errors='ignore').strip()
            elif child.type == 'pointer_declarator':
                member_info['is_pointer'] = True
                member_info['type'] += '*'
                for subchild in child.children:
                    if subchild.type == 'identifier':
                        name_bytes = source_bytes[subchild.start_byte:subchild.end_byte]
                        member_info['name'] = name_bytes.decode('utf-8', errors='ignore').strip()

    def parse_union(self, node, source_code, file_path):
        """解析C语言联合体定义"""
        union_info = {
            'name': '',
            'content': '',
            'members': [],
            'filename': file_path,
            'lineno': node.start_point[0] + 1,
            'end_lineno': node.end_point[0] + 1,
            'dependencies': []
        }

        try:
            # 获取联合体内容
            union_info['content'] = source_code[node.start_byte:node.end_byte]
            
            # 解析联合体名称和成员
            for child in node.children:
                if child.type == 'type_identifier':
                    union_info['name'] = source_code[child.start_byte:child.end_byte]
                elif child.type == 'field_declaration_list':
                    union_info['members'] = self._parse_struct_members(child, source_code, file_path)
            
            return union_info if union_info['name'] else None
            
        except Exception as e:
            self.logger.error(f"解析联合体时出错: {e}", exc_info=True)
            return None

    def parse_typedef(self, node, source_code, file_path):
        """解析typedef定义"""
        typedef_info = {
            'type': 'type_definition',
            'content': '',
            'filename': file_path,
            'field_list': []
        }

        try:
            # 使用字节安全的方法
            source_bytes = source_code.encode('utf-8')
            
            # 获取typedef内容
            typedef_bytes = source_bytes[node.start_byte:node.end_byte]
            typedef_info['content'] = typedef_bytes.decode('utf-8', errors='ignore')
            
            # 解析typedef的各个部分
            typedef_name = ''
            struct_node = None
            
            for child in node.children:
                if child.type == 'type_identifier':
                    # 新类型名称（通常是最后一个type_identifier）
                    name_bytes = source_bytes[child.start_byte:child.end_byte]
                    typedef_name = name_bytes.decode('utf-8', errors='ignore').strip()
                elif child.type == 'struct_specifier':
                    # 结构体typedef
                    struct_node = child
            
            if not typedef_name:
                return None
            
            # 解析结构体成员（如果是结构体typedef）
            if struct_node:
                typedef_info['field_list'] = self._parse_struct_fields_for_typedef(struct_node, source_bytes)
            
            # 移除空的dependencies字段
            if 'dependencies' in typedef_info and not typedef_info['dependencies']:
                del typedef_info['dependencies']
            
            return typedef_info
            
        except Exception as e:
            self.logger.error(f"解析typedef时出错: {e}", exc_info=True)
            return None

    def _parse_struct_fields_for_typedef(self, struct_node, source_bytes):
        """为typedef解析结构体字段列表"""
        fields = []
        
        for child in struct_node.children:
            if child.type == 'field_declaration_list':
                for field_child in child.children:
                    if field_child.type == 'field_declaration':
                        field_info = self._extract_field_info(field_child, source_bytes)
                        if field_info:
                            fields.append(field_info)
        
        return fields
    
    def _extract_field_info(self, field_node, source_bytes):
        """提取字段信息"""
        field_info = {
            'name': '',
            'datatype': ''
        }
        
        try:
            # 解析字段类型和名称
            for child in field_node.children:
                if child.type in ['type_specifier', 'primitive_type']:
                    # 获取数据类型
                    type_bytes = source_bytes[child.start_byte:child.end_byte]
                    field_info['datatype'] = type_bytes.decode('utf-8', errors='ignore').strip()
                elif child.type == 'field_identifier':
                    # 字段标识符
                    name_bytes = source_bytes[child.start_byte:child.end_byte]
                    field_info['name'] = name_bytes.decode('utf-8', errors='ignore').strip()
                elif child.type == 'array_declarator':
                    # 数组字段，提取名称
                    field_info['name'] = self._extract_array_field_name(child, source_bytes)
                elif child.type == 'field_declarator':
                    # 获取字段名称
                    field_info['name'] = self._extract_field_name(child, source_bytes)
                elif child.type == 'identifier':
                    # 直接的标识符
                    name_bytes = source_bytes[child.start_byte:child.end_byte]
                    field_info['name'] = name_bytes.decode('utf-8', errors='ignore').strip()
            
            # 处理数组类型的字段
            if '[' in field_info['name']:
                # 例如：name[50] -> 保持原样但处理datatype
                pass
            
            return field_info if field_info['name'] and field_info['datatype'] else None
            
        except Exception as e:
            self.logger.error(f"提取字段信息时出错: {e}", exc_info=True)
            return None
    
    def _extract_field_name(self, declarator_node, source_bytes):
        """从声明器中提取字段名称"""
        for child in declarator_node.children:
            if child.type == 'identifier':
                name_bytes = source_bytes[child.start_byte:child.end_byte]
                return name_bytes.decode('utf-8', errors='ignore').strip()
            elif child.type == 'array_declarator':
                # 处理数组声明器
                for subchild in child.children:
                    if subchild.type == 'identifier':
                        name_bytes = source_bytes[subchild.start_byte:subchild.end_byte]
                        return name_bytes.decode('utf-8', errors='ignore').strip()
        return ''
    
    def _extract_array_field_name(self, array_declarator_node, source_bytes):
        """从数组声明器中提取字段名称"""
        for child in array_declarator_node.children:
            if child.type == 'field_identifier':
                name_bytes = source_bytes[child.start_byte:child.end_byte]
                return name_bytes.decode('utf-8', errors='ignore').strip()
        return ''

    def parse_enum(self, node, source_code, file_path):
        """解析枚举定义"""
        enum_info = {
            'name': '',
            'content': '',
            'values': [],
            'filename': file_path,
            'lineno': node.start_point[0] + 1,
            'end_lineno': node.end_point[0] + 1,
            'dependencies': []
        }

        try:
            # 获取枚举内容
            enum_info['content'] = source_code[node.start_byte:node.end_byte]
            
            # 解析枚举名称和值
            for child in node.children:
                if child.type == 'type_identifier':
                    enum_info['name'] = source_code[child.start_byte:child.end_byte]
                elif child.type == 'enumerator_list':
                    enum_info['values'] = self._parse_enum_values(child, source_code)
            
            return enum_info if enum_info['name'] else None
            
        except Exception as e:
            self.logger.error(f"解析枚举时出错: {e}", exc_info=True)
            return None

    def _parse_enum_values(self, enum_list_node, source_code):
        """解析枚举值列表"""
        values = []
        
        for child in enum_list_node.children:
            if child.type == 'enumerator':
                enum_value = self._parse_enum_value(child, source_code)
                if enum_value:
                    values.append(enum_value)
        
        return values

    def _parse_enum_value(self, enum_value_node, source_code):
        """解析单个枚举值"""
        value_info = {
            'name': '',
            'value': None
        }
        
        try:
            for child in enum_value_node.children:
                if child.type == 'identifier':
                    value_info['name'] = source_code[child.start_byte:child.end_byte]
                elif child.type == 'number_literal':
                    value_info['value'] = source_code[child.start_byte:child.end_byte]
            
            return value_info if value_info['name'] else None
            
        except Exception as e:
            self.logger.error(f"解析枚举值时出错: {e}", exc_info=True)
            return None
