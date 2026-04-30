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

class FunctionParser:
    def __init__(self):
        self.method_parser = MethodParser()

    def extract_function_calls(self, node, source_code):
        """提取函数体中调用的其他函数、方法、宏、类实例化等"""
        function_calls = set()
        
        def traverse_for_calls(node):
            if node.type == 'call_expression':
                # 提取函数调用、方法调用
                for child in node.children:
                    if child.type == 'identifier':
                        func_name = source_code[child.start_byte:child.end_byte].decode('utf8')
                        function_calls.add(func_name)
                        break
                    elif child.type == 'field_expression':
                        # 处理成员函数调用，如 obj.method()
                        full_call = source_code[child.start_byte:child.end_byte].decode('utf8')
                        function_calls.add(full_call)  # 保留完整调用
                        
                        # 同时提取方法名
                        for subchild in child.children:
                            if subchild.type == 'field_identifier':
                                method_name = source_code[subchild.start_byte:subchild.end_byte].decode('utf8')
                                function_calls.add(method_name)
                                break
                    elif child.type == 'qualified_identifier':
                        # 处理限定标识符调用，如 namespace::function() 或 Class::method()
                        full_qualified = source_code[child.start_byte:child.end_byte].decode('utf8')
                        function_calls.add(full_qualified)  # 保留完整限定名
                        
                        # 提取类名和方法名
                        if '::' in full_qualified:
                            parts = full_qualified.split('::')
                            class_name = parts[0]
                            method_name = parts[-1]
                            function_calls.add(class_name)  # 添加类依赖
                            function_calls.add(method_name)  # 添加方法依赖
                        break
            
            elif node.type == 'type_identifier':
                # 处理类型引用（如变量声明、类实例化）
                type_name = source_code[node.start_byte:node.end_byte].decode('utf8')
                function_calls.add(type_name)
            
            elif node.type == 'sized_type_specifier':
                # 处理结构体类型引用
                for child in node.children:
                    if child.type == 'type_identifier':
                        type_name = source_code[child.start_byte:child.end_byte].decode('utf8')
                        function_calls.add(type_name)
            
            elif node.type == 'preproc_ifdef' or node.type == 'preproc_ifndef':
                # 处理宏使用
                for child in node.children:
                    if child.type == 'identifier':
                        macro_name = source_code[child.start_byte:child.end_byte].decode('utf8')
                        function_calls.add(macro_name)
                        break
            
            # 关键改进：处理宏调用节点
            elif node.type == 'preproc_call':
                # 提取宏名称
                for child in node.children:
                    if child.type == 'identifier':
                        macro_name = source_code[child.start_byte:child.end_byte].decode('utf8')
                        function_calls.add(macro_name)
                        break
                # 提取宏参数中的标识符
                for child in node.children:
                    if child.type == 'preproc_arg':
                        arg_content = source_code[child.start_byte:child.end_byte].decode('utf8')
                        # 解析宏参数中的标识符
                        import re
                        identifiers = re.findall(r'\b[A-Za-z_][A-Za-z0-9_]*\b', arg_content)
                        for ident in identifiers:
                            if not ident.lower() in ['int', 'char', 'void', 'bool', 'float', 'double']:
                                function_calls.add(ident)
            
            elif node.type == 'new_expression':
                # 处理new表达式中的类型引用
                for child in node.children:
                    if child.type == 'type_identifier':
                        type_name = source_code[child.start_byte:child.end_byte].decode('utf8')
                        function_calls.add(type_name)
            
            # 递归遍历所有子节点
            for child in node.children:
                traverse_for_calls(child)
        
        # 只遍历函数体部分
        for child in node.children:
            if child.type == 'compound_statement':
                traverse_for_calls(child)
                break
        
        return list(function_calls)

    def parse_function(self, node, source_code, filename):
        """解析函数定义"""
        function_name = None
        # 生成唯一的UUID作为key的一部分
        unique_id = str(uuid.uuid4())
        
        function_info = {
            "type": "function_definition",
            "content": source_code[node.start_byte:node.end_byte].decode('utf8'),
            "filename": filename,
            "name": "",  # 将在后面设置
            "uuid": unique_id,
            "elem_datatype": "",
            "params": [],
            "dependencies": []
        }

        # 首先尝试获取函数名，然后检查是否是类方法实现
        is_class_method = False
        for child in node.children:
            if child.type == 'function_declarator':
                for subchild in child.children:
                    if subchild.type == 'qualified_identifier':
                        # 如果函数声明器包含qualified_identifier，说明是类方法实现
                        qualified_name = source_code[subchild.start_byte:subchild.end_byte].decode('utf8')
                        if '::' in qualified_name:
                            is_class_method = True
                        break
                    elif subchild.type == 'identifier':
                        # 普通函数的情况
                        break
                break
        
        if is_class_method:
            # 这是一个类方法实现，需要单独处理
            return None, None

        # 获取返回类型
        for child in node.children:
            if child.type == 'primitive_type' or child.type == 'type_identifier':
                function_info["elem_datatype"] = source_code[child.start_byte:child.end_byte].decode('utf8')
                break

        # 获取函数名和参数
        for child in node.children:
            if child.type == 'function_declarator':
                for subchild in child.children:
                    if subchild.type == 'identifier':
                        function_name = source_code[subchild.start_byte:subchild.end_byte].decode('utf8')
                        function_info["name"] = function_name
                    elif subchild.type == 'parameter_list':
                        for param in subchild.children:
                            if param.type == 'parameter_declaration':
                                param_info = self.method_parser.parse_parameter_declaration(param, source_code)
                                if param_info:
                                    function_info["params"].append(param_info)

        if function_name is None:
            return None, None
        
        # 提取函数依赖关系
        function_info["dependencies"] = self.extract_function_calls(node, source_code)
        
        # 使用UUID键格式返回
        function_key = "{}{}{}".format(function_name, UUID_SEPARATOR, unique_id)
        return function_key, function_info

    def parse_class_method_implementation(self, node, source_code, filename, class_methods):
        """解析类方法实现"""
        # 生成唯一的UUID作为key的一部分
        unique_id = str(uuid.uuid4())
        
        method_info = {
            "type": "method_definition",  # 改为method_definition，这样会被保存到all_methods.json
            "content": source_code[node.start_byte:node.end_byte].decode('utf8'),
            "filename": filename,
            "name": "",
            "uuid": unique_id,
            "elem_datatype": "",
            "params": [],
            "class_name": "",
            "method_name": "",
            "dependencies": [],  # 添加依赖关系字段
            "is_virtual": False,
            "is_override": False,
            "is_final": False,
            "is_static": False,
            "is_inline": False,
            "is_destructor": False
        }

        # 检查函数声明中的特殊关键字
        content = source_code[node.start_byte:node.end_byte].decode('utf8')
        method_info["is_virtual"] = 'virtual' in content
        method_info["is_override"] = 'override' in content
        method_info["is_final"] = 'final' in content
        method_info["is_static"] = 'static' in content
        method_info["is_inline"] = 'inline' in content
        method_info["is_destructor"] = '~' in content

        # 首先检查是否是类方法实现
        is_class_method = False
        qualified_name = None
        is_constructor = False
        
        for child in node.children:
            if child.type == 'function_declarator':
                for subchild in child.children:
                    if subchild.type == 'qualified_identifier':
                        qualified_name = source_code[subchild.start_byte:subchild.end_byte].decode('utf8')
                        if '::' in qualified_name:
                            is_class_method = True
                            # 检查是否是构造函数
                            parts = qualified_name.split('::')
                            if len(parts) == 2 and parts[0] == parts[1]:
                                is_constructor = True
                                method_info["name"] = parts[1]
                                method_info["method_name"] = parts[1]  # 添加这行
                                method_info["class_name"] = parts[0]
                            break
                    elif subchild.type == 'identifier':
                        # 检查是否是析构函数
                        name = source_code[subchild.start_byte:subchild.end_byte].decode('utf8')
                        if name.startswith('~'):
                            method_info["is_destructor"] = True
                            name = name[1:]  # 去掉~
                            method_info["name"] = name
                break
        
        # 如果不是类方法实现，但在类的上下文中，可能是内联方法
        if not is_class_method and not qualified_name:
            return

        # 获取返回类型
        for child in node.children:
            if child.type in ['primitive_type', 'type_identifier', 'qualified_identifier']:
                method_info["elem_datatype"] = source_code[child.start_byte:child.end_byte].decode('utf8')
                break

        # 获取函数名和参数
        for child in node.children:
            if child.type == 'function_declarator':
                for subchild in child.children:
                    if subchild.type == 'qualified_identifier':
                        # 解析 ClassName::methodName
                        qualified_name = source_code[subchild.start_byte:subchild.end_byte].decode('utf8')
                        if '::' in qualified_name:
                            parts = qualified_name.split('::')
                            method_info["class_name"] = parts[0]
                            method_info["method_name"] = parts[1]
                    elif subchild.type == 'parameter_list':
                        for param in subchild.children:
                            if param.type == 'parameter_declaration':
                                param_info = self.method_parser.parse_parameter_declaration(param, source_code)
                                if param_info:
                                    method_info["params"].append(param_info)

        # 提取方法依赖关系
        method_info["dependencies"] = self.extract_function_calls(node, source_code)
        
        # 特殊处理：如果是构造函数，提取初始化列表中的依赖
        if is_constructor:
            # 从内容中提取初始化列表的依赖
            content = source_code[node.start_byte:node.end_byte].decode('utf8')
            import re
            
            # 提取初始化列表
            init_list_pattern = r':\s*([^{]+)'
            init_match = re.search(init_list_pattern, content)
            if init_match:
                init_list = init_match.group(1).strip()
                
                # 提取模板类名
                template_pattern = r'(\w+)<([^>]+)>'
                template_match = re.search(template_pattern, init_list)
                if template_match:
                    template_class = template_match.group(1)
                    template_args = template_match.group(2)
                    if template_class not in method_info["dependencies"]:
                        method_info["dependencies"].append(template_class)
                    
                    # 提取模板参数
                    for arg in template_args.split(','):
                        arg = arg.strip()
                        if arg and not arg.lower() in ['int', 'char', 'void', 'bool', 'float', 'double']:
                            if arg not in method_info["dependencies"]:
                                method_info["dependencies"].append(arg)
                
                # 提取函数调用
                func_call_pattern = r'(\w+)\s*\('
                func_calls = re.findall(func_call_pattern, init_list)
                for func_call in func_calls:
                    if not func_call.lower() in ['int', 'char', 'void', 'bool', 'float', 'double']:
                        if func_call not in method_info["dependencies"]:
                            method_info["dependencies"].append(func_call)
        
        # 设置完整方法名
        if method_info["method_name"]:
            method_info["name"] = method_info["method_name"]
        
        # 将方法实现添加到class_methods字典中
        if method_info["class_name"] and (method_info["method_name"] or is_constructor):
            class_name = method_info["class_name"]
            method_name = method_info["method_name"] if method_info["method_name"] else class_name
            
            if class_name not in class_methods:
                class_methods[class_name] = {}
            
            # 使用UUID键格式存储方法
            method_key = "{}{}{}".format(method_name, UUID_SEPARATOR, unique_id)
            class_methods[class_name][method_key] = {
                "name": method_name,
                "uuid": unique_id,
                "content": method_info["content"],
                "filename": filename,
                "elem_datatype": method_info["elem_datatype"],
                "params": method_info["params"],
                "dependencies": method_info["dependencies"],
                "class_name": class_name
            }
            
            # 方法实现已添加到class_methods中，不需要返回
            return method_key, method_info
        
        return None, None 