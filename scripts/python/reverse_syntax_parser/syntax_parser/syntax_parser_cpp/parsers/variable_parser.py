#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import uuid

try:
    from ..constants import UUID_SEPARATOR
except ImportError:
    from constants import UUID_SEPARATOR

class VariableParser:
    def parse_global_variable(self, node, source_code, filename):
        """解析全局变量"""
        # 生成唯一的UUID作为key的一部分
        unique_id = str(uuid.uuid4())
        
        var_info = {
            "type": "global_variable",
            "content": source_code[node.start_byte:node.end_byte].decode('utf8'),
            "filename": filename,
            "name": "",
            "uuid": unique_id,
            "datatype": "",
            "dependencies": []  # 添加依赖关系字段
        }

        for child in node.children:
            if child.type == 'primitive_type':
                var_info["datatype"] = source_code[child.start_byte:child.end_byte].decode('utf8')
            elif child.type == 'type_identifier':
                var_info["datatype"] = source_code[child.start_byte:child.end_byte].decode('utf8')
            elif child.type == 'qualified_identifier':
                var_info["datatype"] = source_code[child.start_byte:child.end_byte].decode('utf8')
            elif child.type == 'init_declarator':
                for subchild in child.children:
                    if subchild.type == 'identifier':
                        var_info["name"] = source_code[subchild.start_byte:subchild.end_byte].decode('utf8')
                        break

        # 使用UUID键格式返回
        if var_info["name"]:
            var_key = "{}{}{}".format(var_info['name'], UUID_SEPARATOR, unique_id)
            return var_key, var_info
        else:
            return None, None

    def parse_macro(self, node, source_code, filename):
        """解析宏定义"""
        # 生成唯一的UUID作为key的一部分
        unique_id = str(uuid.uuid4())
        
        macro_info = {
            "type": "macro_definition",
            "content": source_code[node.start_byte:node.end_byte].decode('utf8'),
            "filename": filename,
            "name": "",
            "uuid": unique_id,
            "dependencies": []  # 添加依赖关系字段
        }

        for child in node.children:
            if child.type == 'identifier':
                macro_info["name"] = source_code[child.start_byte:child.end_byte].decode('utf8')
                break

        # 使用UUID键格式返回
        if macro_info["name"]:
            macro_key = "{}{}{}".format(macro_info['name'], UUID_SEPARATOR, unique_id)
            return macro_key, macro_info
        else:
            return None, None

    def parse_typedef_struct(self, node, source_code, filename):
        """解析typedef struct定义"""
        # 生成唯一的UUID作为key的一部分
        unique_id = str(uuid.uuid4())
        
        typedef_info = {
            "type": "type_definition",
            "content": source_code[node.start_byte:node.end_byte].decode('utf8'),
            "filename": filename,
            "name": "",
            "uuid": unique_id,
            "field_list": [],
            "dependencies": []  # 添加依赖关系字段
        }
        
        typedef_name = None
        
        # 遍历typedef的子节点
        for child in node.children:
            if child.type == 'struct_specifier':
                # 解析结构体字段
                self.parse_struct_fields(child, source_code, typedef_info)
            elif child.type == 'type_identifier':
                # 这是typedef后面的类型名
                typedef_name = source_code[child.start_byte:child.end_byte].decode('utf8')
                typedef_info["name"] = typedef_name
        
        # 使用UUID键格式返回
        if typedef_name:
            typedef_key = "{}{}{}".format(typedef_name, UUID_SEPARATOR, unique_id)
            return typedef_key, typedef_info
        else:
            return None, None
    
    def parse_struct_fields(self, struct_node, source_code, typedef_info):
        """解析结构体字段"""
        for child in struct_node.children:
            if child.type == 'field_declaration_list':
                # 解析字段声明列表
                for field_child in child.children:
                    if field_child.type == 'field_declaration':
                        field_info = self.parse_struct_field_declaration(field_child, source_code)
                        if field_info:
                            typedef_info["field_list"].append(field_info)
    
    def parse_struct_field_declaration(self, field_node, source_code):
        """解析单个结构体字段声明"""
        field_info = {
            "name": "",
            "datatype": ""
        }
        
        datatype_parts = []
        field_name = ""
        
        # 递归解析字段声明
        def extract_field_info(node):
            nonlocal datatype_parts, field_name
            
            if node.type in ['primitive_type', 'type_identifier', 'qualified_identifier']:
                # 数据类型
                datatype_parts.append(source_code[node.start_byte:node.end_byte].decode('utf8'))
            elif node.type == 'field_identifier':
                # 字段名
                field_name = source_code[node.start_byte:node.end_byte].decode('utf8')
            elif node.type == 'identifier':
                # 备用字段名获取方式
                if not field_name:
                    field_name = source_code[node.start_byte:node.end_byte].decode('utf8')
            elif node.type == '*':
                # 指针符号
                datatype_parts.append('*')
            else:
                # 递归处理子节点
                for child in node.children:
                    extract_field_info(child)
        
        # 遍历字段声明的所有子节点
        extract_field_info(field_node)
        
        if field_name and datatype_parts:
            field_info["name"] = field_name
            field_info["datatype"] = " ".join(datatype_parts)
            return field_info
        elif field_name:
            # 如果有字段名但没有明确的数据类型，尝试从内容中提取
            content = source_code[field_node.start_byte:field_node.end_byte].decode('utf8').strip()
            if content.endswith(';'):
                content = content[:-1].strip()
            
            # 简单的类型推断：取第一个词作为类型，最后一个词作为字段名
            parts = content.split()
            if len(parts) >= 2:
                field_info["datatype"] = parts[0]
                field_info["name"] = parts[-1]
                return field_info
        
        return None

    def parse_direct_struct(self, node, source_code, filename):
        """解析直接定义的结构体（非typedef的struct）"""
        # 生成唯一的UUID作为key的一部分
        unique_id = str(uuid.uuid4())
        
        struct_info = {
            "type": "type_definition",
            "content": source_code[node.start_byte:node.end_byte].decode('utf8'),
            "filename": filename,
            "name": "",
            "uuid": unique_id,
            "field_list": [],
            "dependencies": []  # 添加依赖关系字段
        }
        
        struct_name = None
        
        # 遍历struct的子节点查找名称
        for child in node.children:
            if child.type == 'type_identifier':
                # 这是struct的名称
                struct_name = source_code[child.start_byte:child.end_byte].decode('utf8')
                struct_info["name"] = struct_name
                break
        
        # 如果没有找到明确的名称，可能是匿名结构体，尝试从父节点获取
        if not struct_name:
            # 检查是否有声明部分（可能包含变量名）
            parent = node.parent if hasattr(node, 'parent') else None
            if parent and parent.type == 'declaration':
                for sibling in parent.children:
                    if sibling.type == 'init_declarator':
                        for child in sibling.children:
                            if child.type == 'identifier':
                                struct_name = source_code[child.start_byte:child.end_byte].decode('utf8')
                                struct_info["name"] = struct_name
                                break
                        if struct_name:
                            break
        
        # 解析结构体字段
        self.parse_struct_fields(node, source_code, struct_info)
        
        # 使用UUID键格式返回，如果没有名称则使用"AnonymousStruct"
        if not struct_name:
            struct_name = "AnonymousStruct"
            struct_info["name"] = struct_name
        
        struct_key = "{}{}{}".format(struct_name, UUID_SEPARATOR, unique_id)
        return struct_key, struct_info 