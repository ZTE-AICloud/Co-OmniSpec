#!/usr/bin/env python3

class MethodParser:
    def extract_method_dependencies(self, node, source_code):
        """提取方法体中的依赖关系（如果有方法体）"""
        dependencies = set()
        
        def traverse_for_dependencies(node):
            if node.type == 'call_expression':
                # 提取函数调用、方法调用
                for child in node.children:
                    if child.type == 'identifier':
                        # 直接函数调用
                        func_name = source_code[child.start_byte:child.end_byte].decode('utf8')
                        dependencies.add(func_name)
                    elif child.type == 'field_expression':
                        # 处理成员函数调用 (obj.method())
                        full_call = source_code[child.start_byte:child.end_byte].decode('utf8')
                        dependencies.add(full_call)
                        
                        # 提取对象和方法名
                        obj_name = None
                        method_name = None
                        for subchild in child.children:
                            if subchild.type == 'identifier':
                                obj_name = source_code[subchild.start_byte:subchild.end_byte].decode('utf8')
                            elif subchild.type == 'field_identifier':
                                method_name = source_code[subchild.start_byte:subchild.end_byte].decode('utf8')
                        
                        if obj_name:
                            dependencies.add(obj_name)
                        if method_name:
                            dependencies.add(method_name)
                    elif child.type == 'qualified_identifier':
                        # 处理限定标识符调用 (Class::method())
                        full_qualified = source_code[child.start_byte:child.end_byte].decode('utf8')
                        dependencies.add(full_qualified)
                        
                        if '::' in full_qualified:
                            parts = full_qualified.split('::')
                            dependencies.add(parts[0])  # 类名
                            dependencies.add(parts[-1])  # 方法名
            
            # 关键改进：处理宏调用节点
            elif node.type == 'preproc_call':
                # 提取宏名称
                for child in node.children:
                    if child.type == 'identifier':
                        macro_name = source_code[child.start_byte:child.end_byte].decode('utf8')
                        dependencies.add(macro_name)
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
                                dependencies.add(ident)
            
            # 处理其他节点类型
            elif node.type == 'new_expression':
                # 处理new表达式 (new Class())
                for child in node.children:
                    if child.type == 'type_identifier':
                        class_name = source_code[child.start_byte:child.end_byte].decode('utf8')
                        dependencies.add(class_name)
            elif node.type == 'type_identifier':
                # 处理类型引用
                type_name = source_code[node.start_byte:node.end_byte].decode('utf8')
                if not type_name.startswith(('int', 'char', 'bool', 'float', 'double', 'void', 'unsigned', 'signed')):
                    dependencies.add(type_name)
            elif node.type == 'field_identifier':
                # 处理成员变量访问
                field_name = source_code[node.start_byte:node.end_byte].decode('utf8')
                dependencies.add(field_name)
            elif node.type == 'identifier':
                # 处理普通标识符
                identifier = source_code[node.start_byte:node.end_byte].decode('utf8')
                if not identifier.lower() in ['if', 'else', 'while', 'for', 'return', 'this']:
                    dependencies.add(identifier)
            
            # 递归遍历所有子节点
            for child in node.children:
                traverse_for_dependencies(child)
        
        # 遍历整个方法体或声明
        traverse_for_dependencies(node)
        
        # 过滤掉C++关键字和基本类型
        cpp_keywords = {'if', 'else', 'while', 'for', 'do', 'switch', 'case', 'break', 'continue', 'return',
                       'true', 'false', 'nullptr', 'this', 'int', 'char', 'bool', 'float', 'double', 'void',
                       'unsigned', 'signed', 'const', 'static', 'virtual', 'override', 'final', 'public',
                       'private', 'protected', 'class', 'struct', 'enum', 'union', 'template', 'typename',
                       'namespace', 'using', 'try', 'catch', 'throw', 'noexcept', 'explicit', 'inline',
                       'friend', 'operator', 'sizeof', 'alignof', 'decltype', 'typeid', 'auto', 'register',
                       'extern', 'mutable', 'volatile', 'default', 'delete', 'final', 'override', 'constexpr'}
        
        filtered_deps = {dep for dep in dependencies if dep not in cpp_keywords}
        return list(filtered_deps)
    def parse_method_declaration(self, node, source_code):
        """解析类方法声明"""
        method_info = {
            "name": "",
            "content": source_code[node.start_byte:node.end_byte].decode('utf8'),
            "elem_datatype": "",
            "params": [],
            "dependencies": []  # 添加依赖关系字段
        }

        content = method_info["content"]
        
        # 处理析构函数
        if '~' in content:
            return self.parse_destructor(node, source_code)
        
        # 如果是field_declaration类型，需要特殊处理
        if node.type == 'field_declaration':
            return self.parse_field_declaration_method(node, source_code)

        # 改进的方法声明检查
        def is_method_declaration(node):
            # 检查是否有函数声明器
            has_declarator = False
            # 检查是否有函数体或分号
            has_body_or_semi = False
            
            for n in node.children:
                if n.type == 'function_declarator':
                    has_declarator = True
                elif n.type == 'compound_statement':
                    has_body_or_semi = True
                elif n.type == ';':
                    has_body_or_semi = True
            
            # 对于简单的方法声明，即使没有完整的function_declarator也可能是方法
            if not has_declarator:
                content_str = source_code[node.start_byte:node.end_byte].decode('utf8')
                if ('(' in content_str and ')' in content_str and 
                    (';' in content_str or '{' in content_str)):
                    has_declarator = True
                    has_body_or_semi = True
            
            # 通用改进：检查是否包含任何宏调用
            content_str = source_code[node.start_byte:node.end_byte].decode('utf8')
            
            # 检查是否包含宏调用（更通用的检测）
            has_macro_call = False
            for child in node.children:
                if child.type == 'preproc_call':
                    has_macro_call = True
                    break
            
            # 如果包含宏调用且符合方法特征，也认为是方法
            if has_macro_call and ('(' in content_str and ')' in content_str and 
                (';' in content_str or '{' in content_str)):
                has_declarator = True
                has_body_or_semi = True
            
            return has_declarator and has_body_or_semi

        if not is_method_declaration(node):
            return method_info

        # 解析函数声明
        method_name_found = False
        for child in node.children:
            if child.type == 'function_declarator':
                # 获取函数名
                for subchild in child.children:
                    if subchild.type == 'identifier':
                        method_info["name"] = source_code[subchild.start_byte:subchild.end_byte].decode('utf8')
                        method_name_found = True
                    elif subchild.type == 'parameter_list':
                        # 解析参数列表
                        for param in subchild.children:
                            if param.type == 'parameter_declaration':
                                param_info = self.parse_parameter_declaration(param, source_code)
                                if param_info:
                                    method_info["params"].append(param_info)
            elif child.type in ['primitive_type', 'type_identifier', 'qualified_identifier']:
                # 获取返回类型
                method_info["elem_datatype"] = source_code[child.start_byte:child.end_byte].decode('utf8')

        # 如果没有找到方法名，尝试从内容中解析
        if not method_name_found:
            method_info = self.parse_method_from_content(node, source_code, method_info)

        # 提取方法依赖关系（对于有方法体的内联方法）
        method_info["dependencies"] = self.extract_method_dependencies(node, source_code)

        return method_info

    def parse_field_declaration_method(self, node, source_code):
        """专门解析field_declaration类型的方法声明"""
        method_info = {
            "name": "",
            "content": source_code[node.start_byte:node.end_byte].decode('utf8'),
            "elem_datatype": "",
            "params": [],
            "dependencies": []  # 添加依赖关系字段
        }

        # 检查是否是方法声明
        def is_method_field(node):
            # 检查是否有函数声明器
            has_declarator = False
            # 检查是否有参数列表
            has_params = False
            # 检查是否有函数体或分号
            has_body_or_semi = False    
            
            for n in node.children:
                if n.type == 'function_declarator':
                    has_declarator = True
                    for sub in n.children:
                        if sub.type == 'parameter_list':
                            has_params = True
                elif n.type == 'compound_statement':
                    has_body_or_semi = True
                elif n.type == ';':
                    has_body_or_semi = True
            
            return has_declarator and has_body_or_semi

        if not is_method_field(node):
            return method_info

        # 解析field_declaration的子节点
        for child in node.children:
            if child.type in ['primitive_type', 'type_identifier', 'qualified_identifier']:
                method_info["elem_datatype"] = source_code[child.start_byte:child.end_byte].decode('utf8')
            elif child.type == 'function_declarator':
                # 解析函数声明器
                for subchild in child.children:
                    if subchild.type in ['identifier', 'field_identifier']:  # 添加field_identifier支持
                        method_info["name"] = source_code[subchild.start_byte:subchild.end_byte].decode('utf8')
                    elif subchild.type == 'parameter_list':
                        # 解析参数列表
                        for param in subchild.children:
                            if param.type == 'parameter_declaration':
                                param_info = self.parse_parameter_declaration(param, source_code)
                                if param_info:
                                    method_info["params"].append(param_info)

        # 提取方法依赖关系
        method_info["dependencies"] = self.extract_method_dependencies(node, source_code)

        return method_info

    def parse_parameter_declaration(self, param_node, source_code):
        """解析参数声明，支持复杂类型如 const std::string& msg"""
        param_info = {
            "name": "",
            "datatype": ""
        }
        
        # 存储类型组件
        type_parts = []
        
        def extract_type_info(node):
            """递归提取类型信息"""
            if node.type == 'type_qualifier':
                # const, volatile 等限定符
                type_parts.append(source_code[node.start_byte:node.end_byte].decode('utf8'))
            elif node.type == 'primitive_type':
                # int, void, char 等基本类型
                type_parts.append(source_code[node.start_byte:node.end_byte].decode('utf8'))
            elif node.type == 'type_identifier':
                # 用户定义的类型名
                type_parts.append(source_code[node.start_byte:node.end_byte].decode('utf8'))
            elif node.type == 'qualified_identifier':
                # std::string, namespace::class 等限定标识符
                type_parts.append(source_code[node.start_byte:node.end_byte].decode('utf8'))
            elif node.type == 'reference_declarator':
                # 处理引用声明符 & 或 &&
                for child in node.children:
                    if child.type == 'identifier':
                        param_info["name"] = source_code[child.start_byte:child.end_byte].decode('utf8')
                    elif child.type == '&':
                        type_parts.append('&')
                    elif child.type == '&&':
                        type_parts.append('&&')
            elif node.type == 'pointer_declarator':
                # 处理指针声明符 *
                for child in node.children:
                    if child.type == 'identifier':
                        param_info["name"] = source_code[child.start_byte:child.end_byte].decode('utf8')
                    elif child.type == '*':
                        type_parts.append('*')
            elif node.type == 'identifier':
                # 直接的参数名
                param_info["name"] = source_code[node.start_byte:node.end_byte].decode('utf8')
            else:
                # 递归处理子节点
                for child in node.children:
                    extract_type_info(child)
        
        # 遍历参数声明的所有子节点
        for child in param_node.children:
            extract_type_info(child)
        
        # 组装完整的数据类型
        if type_parts:
            param_info["datatype"] = " ".join(type_parts)
        
        # 如果仍然没有找到参数名，再尝试直接查找identifier
        if not param_info["name"]:
            for child in param_node.children:
                if child.type == 'identifier':
                    param_info["name"] = source_code[child.start_byte:child.end_byte].decode('utf8')
                    break
        
        return param_info if param_info["name"] or param_info["datatype"] else None
    
    def parse_destructor(self, node, source_code):
        """解析析构函数"""
        method_info = {
            "name": "",
            "content": source_code[node.start_byte:node.end_byte].decode('utf8'),
            "elem_datatype": "",
            "params": [],
            "dependencies": []
        }
        
        content = method_info["content"]
        
        # 从内容中提取析构函数名
        if '~' in content:
            # 找到 ~ 后面的标识符
            destructor_start = content.find('~')
            remaining = content[destructor_start+1:]
            
            # 提取类名
            class_name = ""
            for char in remaining:
                if char.isalnum() or char == '_':
                    class_name += char
                else:
                    break
            
            if class_name:
                method_info["name"] = class_name  # 析构函数名不包含 ~
                method_info["is_destructor"] = True
        
        return method_info
    
    def parse_method_from_content(self, node, source_code, method_info):
        """从内容中解析方法信息（当标准解析失败时使用）"""
        content = method_info["content"].strip()
        
        # 尝试匹配常见的方法模式
        import re
        
        # 模式1: 返回类型 方法名(参数) const?;
        pattern1 = r'\s*([\w:]+\s*[*&]*)\s+(\w+)\s*\(([^)]*)\)\s*(const)?\s*[;{]'
        match1 = re.search(pattern1, content)
        
        if match1:
            method_info["elem_datatype"] = match1.group(1).strip()
            method_info["name"] = match1.group(2)
            params_str = match1.group(3)
            
            # 解析参数
            if params_str.strip():
                # 简单的参数解析
                params = [p.strip() for p in params_str.split(',') if p.strip()]
                for param in params:
                    # 简单的参数格式：type name
                    parts = param.split()
                    if len(parts) >= 2:
                        param_info = {
                            "name": parts[-1],
                            "datatype": " ".join(parts[:-1])
                        }
                        method_info["params"].append(param_info)
            
            return method_info
        
        # 模式2: 方法名(参数) - 构造函数或无返回类型
        pattern2 = r'\s*(\w+)\s*\(([^)]*)\)\s*[;:{]'
        match2 = re.search(pattern2, content)
        
        if match2:
            method_info["name"] = match2.group(1)
            params_str = match2.group(2)
            
            # 解析参数
            if params_str.strip():
                params = [p.strip() for p in params_str.split(',') if p.strip()]
                for param in params:
                    parts = param.split()
                    if len(parts) >= 2:
                        param_info = {
                            "name": parts[-1],
                            "datatype": " ".join(parts[:-1])
                        }
                        method_info["params"].append(param_info)
        
        # 模式3: 处理类方法实现 (ClassName::methodName)
        pattern3 = r'(\w+)::(\w+)\s*\(([^)]*)\)\s*\{'
        match3 = re.search(pattern3, content)
        
        if match3:
            class_name = match3.group(1)
            method_name = match3.group(2)
            params_str = match3.group(3)
            
            method_info["name"] = method_name
            method_info["class_name"] = class_name
            
            # 解析参数
            if params_str.strip():
                params = [p.strip() for p in params_str.split(',') if p.strip()]
                for param in params:
                    parts = param.split()
                    if len(parts) >= 2:
                        param_info = {
                            "name": parts[-1],
                            "datatype": " ".join(parts[:-1])
                        }
                        method_info["params"].append(param_info)
            
            return method_info
        
        return method_info