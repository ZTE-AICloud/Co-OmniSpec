#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import uuid

try:
    from ..constants import UUID_SEPARATOR
except ImportError:
    from constants import UUID_SEPARATOR

try:
    from .method_parser import MethodParser
except ImportError:
    from method_parser import MethodParser

class ClassParser:
    def __init__(self):
        self.method_parser = MethodParser()

    def parse_class(self, node, source_code, filename):
        """解析类定义"""
        # 生成唯一的UUID作为key的一部分
        unique_id = str(uuid.uuid4())
        
        class_info = {
            "type": "class_definition",
            "content": source_code[node.start_byte:node.end_byte].decode('utf8'),
            "filename": filename,
            "name": "",
            "uuid": unique_id,
            "base_class": "",
            "methods": {},  # 改为字典格式，使用UUID键
            "method_keys": [],  # 存储方法的UUID键列表
            "field_list": [],
            "dependencies": []  # 添加依赖关系字段
        }

        # 获取类名
        for child in node.children:
            if child.type == 'type_identifier':
                class_info["name"] = source_code[child.start_byte:child.end_byte].decode('utf8')
                break

        # 获取基类
        for child in node.children:
            if child.type == 'base_class_clause':
                base_class_name = source_code[child.start_byte:child.end_byte].decode('utf8')
                class_info["base_class"] = base_class_name
                # 将基类作为依赖关系
                if base_class_name.strip():
                    # 清理格式，只取类名部分
                    clean_base_name = base_class_name.replace('public', '').replace('private', '').replace('protected', '').strip()
                    if clean_base_name:
                        class_info["dependencies"].append(clean_base_name)

        # 解析类成员
        for child in node.children:
            if child.type == 'field_declaration_list':
                self.parse_class_members(child, source_code, filename, class_info)

        # 构建method_keys列表
        class_info["method_keys"] = list(class_info["methods"].keys())

        # 使用UUID键格式返回
        if class_info["name"]:
            class_key = "{}{}{}".format(class_info['name'], UUID_SEPARATOR, unique_id)
            return class_key, class_info
        else:
            return None, None

    def parse_class_field(self, field_node, source_code, access_modifier):
        """解析类成员变量"""
        field_info = {
            "name": "",
            "datatype": "",
            "access_modifier": access_modifier
        }
        
        # 解析字段声明的内容
        content = source_code[field_node.start_byte:field_node.end_byte].decode('utf8').strip()
        if content.endswith(';'):
            content = content[:-1].strip()
        
        # 遍历节点提取类型和名称
        datatype_parts = []
        field_name = ""
        
        def extract_field_parts(node):
            nonlocal datatype_parts, field_name
            
            if node.type in ['primitive_type', 'type_identifier', 'qualified_identifier']:
                datatype_parts.append(source_code[node.start_byte:node.end_byte].decode('utf8'))
            elif node.type == 'field_identifier':
                field_name = source_code[node.start_byte:node.end_byte].decode('utf8')
            elif node.type == 'identifier':
                if not field_name:  # 备用字段名获取方式
                    field_name = source_code[node.start_byte:node.end_byte].decode('utf8')
            elif node.type == '*':
                datatype_parts.append('*')
            elif node.type == '&':
                datatype_parts.append('&')
            else:
                for child in node.children:
                    extract_field_parts(child)
        
        # 提取字段信息
        extract_field_parts(field_node)
        
        # 如果从节点解析不成功，尝试从内容字符串解析
        if not field_name or not datatype_parts:
            # 简单解析：假设格式为 "type name" 或 "type* name" 等
            parts = content.split()
            if len(parts) >= 2:
                # 最后一个部分是变量名
                field_name = parts[-1]
                # 前面的部分组成数据类型
                datatype_parts = parts[:-1]
        
        if field_name and datatype_parts:
            field_info["name"] = field_name
            field_info["datatype"] = " ".join(datatype_parts)
            return field_info
        
        return None

    def parse_class_members(self, field_list_node, source_code, filename, class_info):
        """解析类成员（方法和字段）"""
        current_access = "private"  # C++类默认访问限制为private
        
        for child in field_list_node.children:
            if child.type == 'access_specifier':
                # 更新当前访问限制
                access_text = source_code[child.start_byte:child.end_byte].decode('utf8')
                current_access = access_text.strip().rstrip(':')
                continue
            elif child.type in [':', '{', '}']:
                # 跳过分隔符
                continue
                
            # 处理类成员
            if child.type in ['field_declaration', 'declaration', 'function_definition', 'template_declaration']:
                self.process_class_member(child, source_code, filename, class_info, current_access)
    
    def process_class_member(self, child, source_code, filename, class_info, current_access):
        """处理单个类成员"""
        content = source_code[child.start_byte:child.end_byte].decode('utf8')
        
        # 改进的方法识别逻辑
        def is_method_candidate(node, content_str):
            """判断是否为方法候选者"""
            # 检查节点类型
            is_function_type = node.type in ['function_definition', 'declaration', 'field_declaration']
            
            # 检查是否包含函数特征
            has_function_signature = '(' in content_str and ')' in content_str
            
            # 检查特殊关键字
            has_special_keywords = any(kw in content_str for kw in ['virtual', 'static', 'inline', 'override', 'final', '~', 'const'])
            
            # 检查是否是构造函数或析构函数
            class_name = class_info.get('name', '')
            is_constructor = class_name and class_name in content_str and '(' in content_str
            is_destructor = '~' in content_str and class_name in content_str
            
            # 检查方法结束符
            has_method_end = ';' in content_str or '{' in content_str
            
            # 通用改进：检查是否包含宏调用
            has_macro_call = False
            for child in node.children:
                if child.type == 'preproc_call':
                    has_macro_call = True
                    break
            
            # 排除明显的非方法成员
            is_simple_variable = (not has_function_signature and 
                                not has_special_keywords and 
                                not is_constructor and 
                                not is_destructor and
                                not has_macro_call and
                                content_str.count(';') == 1 and 
                                '{' not in content_str and 
                                ')' not in content_str)
            
            # 判断条件
            is_method = ((has_function_signature and has_method_end) or 
                        has_special_keywords or 
                        is_constructor or 
                        is_destructor or
                        has_macro_call) and not is_simple_variable
            
            return is_method
        
        # 判断是否是方法
        is_method = is_method_candidate(child, content)
        
        if is_method:
            # 这是一个方法声明或定义
            method_info = self.method_parser.parse_method_declaration(child, source_code)
            if not method_info or not method_info.get('name'):
                return  # 跳过无效的方法声明
                
            method_info["filename"] = filename
            method_info["access_modifier"] = current_access
            
            # 检查是否是析构函数
            if content.strip().startswith('~'):
                method_info["is_destructor"] = True
                if method_info["name"].startswith('~'):
                    method_info["name"] = method_info["name"][1:]
            
            # 检查特殊属性
            method_info["is_virtual"] = 'virtual' in content
            method_info["is_override"] = 'override' in content
            method_info["is_final"] = 'final' in content
            method_info["is_static"] = 'static' in content
            method_info["is_inline"] = ('inline' in content) or ('{' in content and ';' not in content) or child.type == 'function_definition'
            method_info["is_template"] = child.type == 'template_declaration'
            
            # 检查是否是重载方法
            method_info["is_overloaded"] = False
            method_name = method_info["name"]
            for existing_key in class_info["methods"]:
                existing_method = class_info["methods"][existing_key]
                if existing_method["name"] == method_name:
                    method_info["is_overloaded"] = True
                    existing_method["is_overloaded"] = True
                    break
            
            # 确保dependencies字段存在并提取依赖
            if "dependencies" not in method_info:
                method_info["dependencies"] = []
            
            # 提取方法体中的依赖
            if child.type == 'function_definition':
                for n in child.children:
                    if n.type == 'compound_statement':
                        method_info["dependencies"].extend(
                            self.method_parser.extract_method_dependencies(n, source_code)
                        )
            
            # 生成UUID键并存储方法
            method_uuid = str(uuid.uuid4())
            method_key = "{}{}{}".format(method_info['name'], UUID_SEPARATOR, method_uuid)
            method_info["uuid"] = method_uuid
            method_info["type"] = "method_definition"
            class_info["methods"][method_key] = method_info
        else:
            # 这是一个成员变量
            field_info = self.parse_class_field(child, source_code, current_access)
            if field_info:
                class_info["field_list"].append(field_info)