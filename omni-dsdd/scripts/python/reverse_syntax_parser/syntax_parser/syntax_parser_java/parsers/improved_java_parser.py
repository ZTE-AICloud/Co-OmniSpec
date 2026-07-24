#!/usr/bin/env python3
"""
改进的Java解析器 - 支持更多Java语法形式
解决类/接口和方法识别不全的问题
"""
import os
import re
import uuid
from typing import Dict, List, Any, Optional, Tuple
from src.infrastructure.logging.task_log import get_skill_logger

UUID_SEPARATOR = "###"

class ImprovedJavaParser:
    """改进的Java解析器"""
    
    def __init__(self):
        self.elements = {}
        self.java_files = []
        self.project_directory = None
        self.name_to_uuid_map = {}
        
    def find_files(self, directory: str):
        """查找所有Java文件"""
        for root, dirs, files in os.walk(directory):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['target', 'build', 'out', 'bin']]
            
            for file in files:
                if file.startswith('.'):
                    continue
                    
                file_path = os.path.join(root, file)
                if file.endswith('.java'):
                    self.java_files.append(file_path)
    
    def parse_project(self, project_path: str) -> Dict[str, Any]:
        """解析整个Java项目"""
        self.project_directory = project_path
        self.find_files(project_path)
        
        get_skill_logger(__name__).info(f"找到 {len(self.java_files)} 个Java文件")
        
        for filepath in self.java_files:
            get_skill_logger(__name__).info(f"处理文件: {filepath}")
            self.process_file(filepath)
        
        get_skill_logger(__name__).info(f"解析完成，共提取 {len(self.elements)} 个代码元素")
        return self.elements
    
    def process_file(self, filepath: str):
        """处理单个Java文件"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                source_code = f.read()
        except UnicodeDecodeError:
            try:
                with open(filepath, 'r', encoding='gbk') as f:
                    source_code = f.read()
            except:
                get_skill_logger(__name__).warning(f"警告: 无法读取文件 {filepath}")
                return

        if self.project_directory:
            filename = os.path.relpath(filepath, self.project_directory)
            filename = filename.replace('\\', '/')
        else:
            filename = os.path.basename(filepath)

        try:
            self._parse_file_elements(source_code, filename)
        except Exception as e:
            get_skill_logger(__name__).error(f"处理文件 {filepath} 时出错: {e}")
    
    def _parse_file_elements(self, source_code: str, filename: str):
        """解析文件中的所有元素"""
        # 1. 预处理：移除字符串和注释中的干扰内容
        cleaned_code = self._preprocess_code(source_code)
        
        # 2. 解析顶级类和接口（改进的模式）
        self._parse_top_level_declarations(source_code, filename)
        
        # 3. 解析导入语句
        self._parse_imports(source_code, filename)
    
    def _preprocess_code(self, source_code: str) -> str:
        """预处理代码，移除字符串和注释中的干扰内容"""
        # 移除单行注释
        code = re.sub(r'//.*$', '', source_code, flags=re.MULTILINE)
        
        # 移除多行注释（保留Javadoc）
        code = re.sub(r'/\*(?!\*).*?\*/', '', code, flags=re.DOTALL)
        
        # 移除字符串字面量中的内容（保留引号）
        code = re.sub(r'"[^"]*"', '""', code)
        code = re.sub(r"'[^']*'", "''", code)
        
        return code
    
    def _parse_top_level_declarations(self, source_code: str, filename: str):
        """解析顶级声明（类、接口、枚举、注解）"""
        
        # 改进的类/接口/枚举/注解匹配模式
        # 支持多行声明、复杂泛型、多个接口等
        declaration_pattern = r'''
            # 匹配完整的声明块
            (
                # Javadoc注释（可选）
                (?:/\*\*[\s\S]*?\*/\s*)?
                
                # 注解（可选，支持多行）
                (?:@\w+(?:\([^)]*\))?\s*)*
                
                # 访问修饰符和其他修饰符
                (?:(?:public|private|protected)\s+)?
                (?:(?:static|final|abstract|strictfp)\s+)*
                
                # 声明类型关键字
                (class|interface|enum|@interface)\s+
                
                # 名称
                (\w+)
                
                # 泛型参数（可选，支持嵌套）
                (?:<[^<>]*(?:<[^<>]*>[^<>]*)*>)?
                
                # extends子句（可选，支持多行）
                (?:\s+extends\s+[^{]+?)?
                
                # implements子句（可选，支持多行）
                (?:\s+implements\s+[^{]+?)?
                
                # 开始大括号
                \s*\{
            )
        '''
        
        matches = list(re.finditer(declaration_pattern, source_code, re.VERBOSE | re.MULTILINE | re.DOTALL))
        
        for match in matches:
            declaration_type = match.group(2)  # class, interface, enum, @interface
            element_name = match.group(3)
            
            # 提取完整的声明内容
            element_content = self._extract_complete_block(source_code, match.start())
            
            if element_content:
                if declaration_type == 'class':
                    self._parse_class_declaration(element_content, filename)
                elif declaration_type == 'interface':
                    self._parse_interface_declaration(element_content, filename)
                elif declaration_type == 'enum':
                    self._parse_enum_declaration(element_content, filename)
                elif declaration_type == '@interface':
                    self._parse_annotation_declaration(element_content, filename)
    
    def _extract_complete_block(self, source_code: str, start_pos: int) -> str:
        """提取完整的代码块（支持嵌套大括号）"""
        # 向前查找声明开始（包括注释和注解）
        lines = source_code[:start_pos].split('\n')
        declaration_start = start_pos
        
        # 向前查找包含注解、注释的完整声明
        for i in range(len(lines) - 1, -1, -1):
            line = lines[i].strip()
            if not line:
                continue
            if line.startswith('package ') or line.startswith('import ') or line.endswith(';'):
                break
            if (line.startswith('/**') or line.startswith('@') or 
                any(keyword in line for keyword in ['public', 'private', 'protected', 'class', 'interface', 'enum', '@interface'])):
                line_start = sum(len(lines[j]) + 1 for j in range(i))
                declaration_start = line_start
                break
        
        # 向后查找到块结束
        brace_count = 0
        element_end = start_pos
        in_string = False
        escape_next = False
        
        brace_start = source_code.find('{', start_pos)
        if brace_start == -1:
            return source_code[declaration_start:start_pos + 100]
        
        for i in range(brace_start, len(source_code)):
            char = source_code[i]
            
            if escape_next:
                escape_next = False
                continue
            
            if char == '\\':
                escape_next = True
                continue
            
            if char == '"' and not in_string:
                in_string = True
                continue
            elif char == '"' and in_string:
                in_string = False
                continue
            
            if not in_string:
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        element_end = i + 1
                        break
        
        return source_code[declaration_start:element_end]
    
    def _parse_class_declaration(self, class_content: str, filename: str):
        """解析类声明"""
        # 改进的类声明模式
        class_pattern = r'''
            # Javadoc（可选）
            ((?:/\*\*[\s\S]*?\*/\s*)?)
            
            # 注解（可选，支持多个）
            ((?:@\w+(?:\([^)]*\))?\s*)*)
            
            # 修饰符
            ((?:(?:public|private|protected)\s+)?)
            ((?:(?:static|final|abstract|strictfp)\s+)*)
            
            # class关键字和名称
            class\s+(\w+)
            
            # 泛型参数（可选）
            (?:<([^<>]*(?:<[^<>]*>[^<>]*)*)>)?
            
            # extends子句（可选）
            (?:\s+extends\s+([^{]+?))?
            
            # implements子句（可选）
            (?:\s+implements\s+([^{]+?))?
            
            \s*\{
        '''
        
        match = re.search(class_pattern, class_content, re.VERBOSE | re.MULTILINE | re.DOTALL)
        
        if match:
            javadoc = self._extract_javadoc(match.group(1) or "")
            annotations_text = match.group(2) or ""
            access_modifier = (match.group(3) or "package").strip()
            other_modifiers = match.group(4) or ""
            class_name = match.group(5)
            generic_params = match.group(6)
            extends_class = match.group(7)
            implements_interfaces = match.group(8)
            
            unique_id = str(uuid.uuid4())
            class_key = f"{class_name}{UUID_SEPARATOR}{unique_id}"
            
            # 提取类体
            class_body = self._extract_class_body(class_content)
            
            class_info = {
                "type": "class_definition",
                "content": class_content,
                "filename": filename,
                "name": class_name,
                "uuid": unique_id,
                "access_modifier": access_modifier.replace(" ", "") if access_modifier else "package",
                "is_static": "static" in other_modifiers,
                "is_final": "final" in other_modifiers,
                "is_abstract": "abstract" in other_modifiers,
                "other_modifiers": other_modifiers.strip(),
                "generic_parameters": self._parse_generic_parameters(generic_params),
                "base_classes": self._parse_base_classes(extends_class),
                "implemented_interfaces": self._parse_implemented_interfaces(implements_interfaces),
                "docstring": javadoc,
                "annotations": self._parse_annotations(annotations_text),
                "methods": self._parse_all_methods(class_body, class_name, filename),
                "fields": self._parse_fields(class_body, class_name, filename),
                "inner_classes": self._parse_inner_classes(class_body, filename),
                "dependencies": self._extract_dependencies(class_content, class_name),
                "lineno": self._calculate_line_number(class_content, match.start()),
                "end_lineno": self._calculate_line_number(class_content, len(class_content))
            }
            
            self.elements[class_key] = class_info
            self._update_name_mapping(class_name, class_key)
            
            # 将方法作为独立元素存储
            for method_key, method_info in class_info['methods'].items():
                method_info['class_key'] = class_key
                self.elements[method_key] = method_info
                self._update_name_mapping(method_info['name'], method_key)
    
    def _parse_interface_declaration(self, interface_content: str, filename: str):
        """解析接口声明"""
        # 改进的接口声明模式
        interface_pattern = r'''
            # Javadoc（可选）
            ((?:/\*\*[\s\S]*?\*/\s*)?)
            
            # 注解（可选）
            ((?:@\w+(?:\([^)]*\))?\s*)*)
            
            # 修饰符
            ((?:(?:public|private|protected)\s+)?)
            ((?:static\s+)*)
            
            # interface关键字和名称
            interface\s+(\w+)
            
            # 泛型参数（可选）
            (?:<([^<>]*(?:<[^<>]*>[^<>]*)*)>)?
            
            # extends子句（可选）
            (?:\s+extends\s+([^{]+?))?
            
            \s*\{
        '''
        
        match = re.search(interface_pattern, interface_content, re.VERBOSE | re.MULTILINE | re.DOTALL)
        
        if match:
            javadoc = self._extract_javadoc(match.group(1) or "")
            annotations_text = match.group(2) or ""
            access_modifier = (match.group(3) or "package").strip()
            other_modifiers = match.group(4) or ""
            interface_name = match.group(5)
            generic_params = match.group(6)
            extends_interfaces = match.group(7)
            
            unique_id = str(uuid.uuid4())
            interface_key = f"{interface_name}{UUID_SEPARATOR}{unique_id}"
            
            # 提取接口体
            interface_body = self._extract_class_body(interface_content)
            
            interface_info = {
                "type": "interface_definition",
                "content": interface_content,
                "filename": filename,
                "name": interface_name,
                "uuid": unique_id,
                "access_modifier": access_modifier.replace(" ", "") if access_modifier else "package",
                "is_static": "static" in other_modifiers,
                "other_modifiers": other_modifiers.strip(),
                "generic_parameters": self._parse_generic_parameters(generic_params),
                "extended_interfaces": self._parse_implemented_interfaces(extends_interfaces),
                "docstring": javadoc,
                "annotations": self._parse_annotations(annotations_text),
                "methods": self._parse_interface_methods(interface_body, interface_name, filename),
                "constants": self._parse_interface_constants(interface_body, interface_name, filename),
                "dependencies": self._extract_dependencies(interface_content, interface_name),
                "lineno": self._calculate_line_number(interface_content, match.start()),
                "end_lineno": self._calculate_line_number(interface_content, len(interface_content))
            }
            
            self.elements[interface_key] = interface_info
            self._update_name_mapping(interface_name, interface_key)
            
            # 将方法作为独立元素存储
            for method_key, method_info in interface_info['methods'].items():
                method_info['class_key'] = interface_key
                self.elements[method_key] = method_info
                self._update_name_mapping(method_info['name'], method_key)
    
    def _parse_all_methods(self, class_body: str, class_name: str, filename: str) -> Dict[str, Dict[str, Any]]:
        """解析类中的所有方法（改进版）"""
        methods = {}
        
        # 改进的方法匹配模式 - 支持更多Java语法形式
        method_pattern = r'''
            # Javadoc（可选）
            ((?:/\*\*[\s\S]*?\*/\s*)?)
            
            # 注解（可选，支持多个和多行）
            ((?:@\w+(?:\([^)]*\))?\s*)*)
            
            # 访问修饰符
            ((?:public|private|protected)\s+)?
            
            # 其他修饰符（支持多个）
            ((?:(?:static|final|synchronized|native|abstract|strictfp)\s+)*)
            
            # 泛型方法参数（可选）
            (?:<([^<>]*(?:<[^<>]*>[^<>]*)*)>\s+)?
            
            # 返回类型（支持泛型和数组）
            (\w+(?:<[^<>]*(?:<[^<>]*>[^<>]*)*>)?(?:\[\])*)\s+
            
            # 方法名
            (\w+)\s*
            
            # 参数列表（支持复杂参数）
            \(([^)]*)\)
            
            # throws子句（可选）
            (?:\s*throws\s+([^{;]+?))?
            
            # 方法体开始或抽象方法分号
            \s*(\{[\s\S]*?\}|;)
        '''
        
        matches = re.finditer(method_pattern, class_body, re.VERBOSE | re.MULTILINE | re.DOTALL)
        
        for match in matches:
            javadoc = self._extract_javadoc(match.group(1) or "")
            annotations_text = match.group(2) or ""
            access_modifier = (match.group(3) or "package").strip()
            other_modifiers = match.group(4) or ""
            generic_params = match.group(5)
            return_type = match.group(6)
            method_name = match.group(7)
            params_text = match.group(8)
            throws_clause = match.group(9) or ""
            method_body = match.group(10)
            
            # 跳过字段声明（误识别为方法）
            if method_body == ';' and '(' not in match.group(0).split(';')[0]:
                continue
            
            unique_id = str(uuid.uuid4())
            method_key = f"{method_name}{UUID_SEPARATOR}{unique_id}"
            
            method_info = {
                "type": "method_definition",
                "content": match.group(0),
                "filename": filename,
                "name": method_name,
                "uuid": unique_id,
                "class_name": class_name,
                "return_type": return_type,
                "generic_parameters": self._parse_generic_parameters(generic_params),
                "params": self._parse_method_parameters(params_text),
                "access_modifier": access_modifier.replace(" ", "") if access_modifier else "package",
                "is_static": "static" in other_modifiers,
                "is_final": "final" in other_modifiers,
                "is_synchronized": "synchronized" in other_modifiers,
                "is_native": "native" in other_modifiers,
                "is_abstract": "abstract" in other_modifiers or method_body == ';',
                "is_constructor": method_name == class_name,
                "other_modifiers": other_modifiers.strip(),
                "throws_clause": throws_clause.strip(),
                "annotations": self._parse_annotations(annotations_text),
                "docstring": javadoc,
                "dependencies": self._extract_method_dependencies(match.group(0), method_name),
                "lineno": self._calculate_line_number(class_body, match.start()),
                "end_lineno": self._calculate_line_number(class_body, match.end())
            }
            
            methods[method_key] = method_info
        
        return methods
    
    def _parse_interface_methods(self, interface_body: str, interface_name: str, filename: str) -> Dict[str, Dict[str, Any]]:
        """解析接口中的方法（包括default和static方法）"""
        methods = {}
        
        # 接口方法模式（支持default和static方法）
        interface_method_pattern = r'''
            # Javadoc（可选）
            ((?:/\*\*[\s\S]*?\*/\s*)?)
            
            # 注解（可选）
            ((?:@\w+(?:\([^)]*\))?\s*)*)
            
            # 修饰符（接口方法可以是default或static）
            ((?:(?:public|default|static)\s+)*)
            
            # 泛型方法参数（可选）
            (?:<([^<>]*(?:<[^<>]*>[^<>]*)*)>\s+)?
            
            # 返回类型
            (\w+(?:<[^<>]*(?:<[^<>]*>[^<>]*)*>)?(?:\[\])*)\s+
            
            # 方法名
            (\w+)\s*
            
            # 参数列表
            \(([^)]*)\)
            
            # throws子句（可选）
            (?:\s*throws\s+([^{;]+?))?
            
            # 方法体或分号
            \s*(\{[\s\S]*?\}|;)
        '''
        
        matches = re.finditer(interface_method_pattern, interface_body, re.VERBOSE | re.MULTILINE | re.DOTALL)
        
        for match in matches:
            javadoc = self._extract_javadoc(match.group(1) or "")
            annotations_text = match.group(2) or ""
            modifiers = match.group(3) or ""
            generic_params = match.group(4)
            return_type = match.group(5)
            method_name = match.group(6)
            params_text = match.group(7)
            throws_clause = match.group(8) or ""
            method_body = match.group(9)
            
            unique_id = str(uuid.uuid4())
            method_key = f"{method_name}{UUID_SEPARATOR}{unique_id}"
            
            method_info = {
                "type": "method_definition",
                "content": match.group(0),
                "filename": filename,
                "name": method_name,
                "uuid": unique_id,
                "interface_name": interface_name,
                "return_type": return_type,
                "generic_parameters": self._parse_generic_parameters(generic_params),
                "params": self._parse_method_parameters(params_text),
                "access_modifier": "public",  # 接口方法默认public
                "is_static": "static" in modifiers,
                "is_default": "default" in modifiers,
                "is_abstract": method_body == ';' and "default" not in modifiers and "static" not in modifiers,
                "other_modifiers": modifiers.strip(),
                "throws_clause": throws_clause.strip(),
                "annotations": self._parse_annotations(annotations_text),
                "docstring": javadoc,
                "dependencies": self._extract_method_dependencies(match.group(0), method_name),
                "lineno": self._calculate_line_number(interface_body, match.start()),
                "end_lineno": self._calculate_line_number(interface_body, match.end())
            }
            
            methods[method_key] = method_info
        
        return methods
    
    # 辅助方法实现
    def _extract_javadoc(self, text: str) -> str:
        """提取Javadoc注释"""
        javadoc_match = re.search(r'/\*\*([\s\S]*?)\*/', text)
        if javadoc_match:
            return javadoc_match.group(1).strip()
        return ""
    
    def _parse_annotations(self, annotations_text: str) -> List[Dict[str, Any]]:
        """解析注解"""
        annotations = []
        annotation_pattern = r'@(\w+)(?:\(([^)]*)\))?'
        matches = re.finditer(annotation_pattern, annotations_text)
        
        for match in matches:
            annotation_name = match.group(1)
            annotation_params = match.group(2) or ""
            
            annotations.append({
                "name": annotation_name,
                "params": annotation_params,
                "raw_text": match.group(0)
            })
        
        return annotations
    
    def _parse_generic_parameters(self, generic_text: str) -> List[str]:
        """解析泛型参数"""
        if not generic_text:
            return []
        
        # 简单的泛型参数解析
        params = []
        for param in generic_text.split(','):
            param = param.strip()
            if param:
                # 移除extends子句，只保留参数名
                param_name = param.split()[0]
                params.append(param_name)
        
        return params
    
    def _parse_base_classes(self, extends_text: str) -> List[str]:
        """解析父类"""
        if not extends_text:
            return []
        
        # 移除泛型部分，提取类名
        base_class = re.sub(r'<[^>]*>', '', extends_text.strip())
        return [base_class] if base_class else []
    
    def _parse_implemented_interfaces(self, implements_text: str) -> List[str]:
        """解析实现的接口"""
        if not implements_text:
            return []
        
        interfaces = []
        for interface in implements_text.split(','):
            interface = interface.strip()
            # 移除泛型部分
            interface_name = re.sub(r'<[^>]*>', '', interface)
            if interface_name:
                interfaces.append(interface_name)
        
        return interfaces
    
    def _parse_method_parameters(self, params_text: str) -> List[Dict[str, Any]]:
        """解析方法参数"""
        if not params_text.strip():
            return []
        
        params = []
        # 简单的参数解析（可以进一步改进）
        param_parts = params_text.split(',')
        
        for param in param_parts:
            param = param.strip()
            if param:
                # 分割类型和名称
                parts = param.split()
                if len(parts) >= 2:
                    param_type = ' '.join(parts[:-1])
                    param_name = parts[-1]
                    
                    params.append({
                        "type": param_type,
                        "name": param_name,
                        "is_varargs": param_type.endswith("...")
                    })
        
        return params
    
    def _extract_class_body(self, class_content: str) -> str:
        """提取类体内容"""
        brace_start = class_content.find('{')
        brace_end = class_content.rfind('}')
        
        if brace_start != -1 and brace_end != -1:
            return class_content[brace_start + 1:brace_end]
        return ""
    
    def _parse_fields(self, class_body: str, class_name: str, filename: str) -> List[Dict[str, Any]]:
        """解析类字段"""
        fields = []
        
        # 字段模式
        field_pattern = r'''
            # 注解（可选）
            ((?:@\w+(?:\([^)]*\))?\s*)*)
            
            # 修饰符
            ((?:(?:public|private|protected)\s+)?)
            ((?:(?:static|final|transient|volatile)\s+)*)
            
            # 类型
            (\w+(?:<[^>]*>)?(?:\[\])*)\s+
            
            # 字段名（可能有初始化）
            (\w+)(?:\s*=\s*[^;]+)?\s*;
        '''
        
        matches = re.finditer(field_pattern, class_body, re.VERBOSE | re.MULTILINE)
        
        for match in matches:
            annotations_text = match.group(1) or ""
            access_modifier = (match.group(2) or "package").strip()
            other_modifiers = match.group(3) or ""
            field_type = match.group(4)
            field_name = match.group(5)
            
            fields.append({
                "name": field_name,
                "type": field_type,
                "access_modifier": access_modifier.replace(" ", "") if access_modifier else "package",
                "is_static": "static" in other_modifiers,
                "is_final": "final" in other_modifiers,
                "is_transient": "transient" in other_modifiers,
                "is_volatile": "volatile" in other_modifiers,
                "annotations": self._parse_annotations(annotations_text)
            })
        
        return fields
    
    def _parse_inner_classes(self, class_body: str, filename: str) -> Dict[str, Dict[str, Any]]:
        """解析内部类"""
        inner_classes = {}
        
        # 内部类模式（简化版）
        inner_class_pattern = r'''
            ((?:public|private|protected)\s+)?
            ((?:static\s+)?)
            (class|interface|enum)\s+
            (\w+)
            [^{]*\{
        '''
        
        matches = re.finditer(inner_class_pattern, class_body, re.VERBOSE | re.MULTILINE)
        
        for match in matches:
            access_modifier = (match.group(1) or "package").strip()
            is_static = bool(match.group(2))
            inner_type = match.group(3)
            inner_name = match.group(4)
            
            unique_id = str(uuid.uuid4())
            inner_key = f"{inner_name}{UUID_SEPARATOR}{unique_id}"
            
            inner_classes[inner_key] = {
                "type": f"{inner_type}_definition",
                "name": inner_name,
                "uuid": unique_id,
                "access_modifier": access_modifier.replace(" ", "") if access_modifier else "package",
                "is_static": is_static,
                "is_inner": True
            }
        
        return inner_classes
    
    def _parse_interface_constants(self, interface_body: str, interface_name: str, filename: str) -> Dict[str, Dict[str, Any]]:
        """解析接口常量"""
        constants = {}
        
        # 接口常量模式
        constant_pattern = r'''
            (\w+(?:<[^>]*>)?(?:\[\])*)\s+  # 类型
            (\w+)\s*=\s*([^;]+);           # 名称和值
        '''
        
        matches = re.finditer(constant_pattern, interface_body, re.VERBOSE | re.MULTILINE)
        
        for match in matches:
            constant_type = match.group(1)
            constant_name = match.group(2)
            constant_value = match.group(3).strip()
            
            unique_id = str(uuid.uuid4())
            constant_key = f"{constant_name}{UUID_SEPARATOR}{unique_id}"
            
            constants[constant_key] = {
                "type": "constant_definition",
                "name": constant_name,
                "uuid": unique_id,
                "data_type": constant_type,
                "value": constant_value,
                "access_modifier": "public",
                "is_static": True,
                "is_final": True
            }
        
        return constants
    
    def _extract_dependencies(self, content: str, current_name: str) -> List[str]:
        """提取依赖关系"""
        dependencies = set()
        
        # 提取类型引用
        type_pattern = r'\b([A-Z]\w+)(?:<[^>]*>)?\b'
        matches = re.finditer(type_pattern, content)
        
        for match in matches:
            type_name = match.group(1)
            if type_name != current_name and type_name not in ['String', 'Object', 'Class', 'System']:
                dependencies.add(type_name)
        
        return list(dependencies)
    
    def _extract_method_dependencies(self, method_content: str, current_method_name: str = None) -> List[str]:
        """提取方法依赖"""
        dependencies = set()
        
        # 方法调用模式
        method_call_pattern = r'(\w+)\.(\w+)\s*\('
        matches = re.finditer(method_call_pattern, method_content)
        
        for match in matches:
            class_name = match.group(1)
            method_name = match.group(2)
            dependencies.add(f"{class_name}.{method_name}")
        
        # 过滤掉自己（递归调用）
        if current_method_name:
            dependencies = {dep for dep in dependencies 
                          if dep != current_method_name}
        
        return list(dependencies)
    
    def _calculate_line_number(self, content: str, position: int) -> int:
        """计算行号"""
        return content[:position].count('\n') + 1
    
    def _update_name_mapping(self, element_name: str, element_key: str):
        """更新名称映射"""
        if element_name not in self.name_to_uuid_map:
            self.name_to_uuid_map[element_name] = []
        self.name_to_uuid_map[element_name].append(element_key)
    
    def _parse_enum_declaration(self, enum_content: str, filename: str):
        """解析枚举声明"""
        # 简化的枚举解析
        enum_pattern = r'enum\s+(\w+)\s*\{'
        match = re.search(enum_pattern, enum_content)
        
        if match:
            enum_name = match.group(1)
            unique_id = str(uuid.uuid4())
            enum_key = f"{enum_name}{UUID_SEPARATOR}{unique_id}"
            
            enum_info = {
                "type": "enum_definition",
                "content": enum_content,
                "filename": filename,
                "name": enum_name,
                "uuid": unique_id,
                "access_modifier": "public",
                "enum_values": self._parse_enum_values(enum_content),
                "methods": self._parse_all_methods(self._extract_class_body(enum_content), enum_name, filename)
            }
            
            self.elements[enum_key] = enum_info
            self._update_name_mapping(enum_name, enum_key)
    
    def _parse_annotation_declaration(self, annotation_content: str, filename: str):
        """解析注解声明"""
        # 简化的注解解析
        annotation_pattern = r'@interface\s+(\w+)\s*\{'
        match = re.search(annotation_pattern, annotation_content)
        
        if match:
            annotation_name = match.group(1)
            unique_id = str(uuid.uuid4())
            annotation_key = f"{annotation_name}{UUID_SEPARATOR}{unique_id}"
            
            annotation_info = {
                "type": "annotation_definition",
                "content": annotation_content,
                "filename": filename,
                "name": annotation_name,
                "uuid": unique_id,
                "access_modifier": "public"
            }
            
            self.elements[annotation_key] = annotation_info
            self._update_name_mapping(annotation_name, annotation_key)
    
    def _parse_enum_values(self, enum_content: str) -> List[str]:
        """解析枚举值"""
        values = []
        body_start = enum_content.find('{')
        body_end = enum_content.find(';', body_start) if ';' in enum_content[body_start:] else enum_content.rfind('}')
        
        if body_start != -1 and body_end != -1:
            values_section = enum_content[body_start + 1:body_end]
            value_pattern = r'([A-Z_][A-Z0-9_]*)\s*(?:\([^)]*\))?'
            matches = re.finditer(value_pattern, values_section)
            
            for match in matches:
                values.append(match.group(1))
        
        return values
    
    def _parse_imports(self, source_code: str, filename: str):
        """解析导入语句"""
        import_pattern = r'import\s+(?:static\s+)?([^;]+)\s*;'
        matches = re.finditer(import_pattern, source_code)
        
        for match in matches:
            import_path = match.group(1).strip()
            
            if import_path.endswith('*'):
                import_name = import_path.split('.')[-2] if '.' in import_path else import_path.replace('*', '').strip()
            else:
                import_name = import_path.split('.')[-1]
            
            unique_id = str(uuid.uuid4())
            import_key = f"{import_name}{UUID_SEPARATOR}{unique_id}"
            
            import_info = {
                "type": "import_statement",
                "content": match.group(0).strip(),
                "filename": filename,
                "name": import_name,
                "uuid": unique_id,
                "import_path": import_path,
                "is_static": "static" in match.group(0),
                "is_wildcard": import_path.endswith('*')
            }
            
            self.elements[import_key] = import_info
            self._update_name_mapping(import_name, import_key)

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        parser = ImprovedJavaParser()
        elements = parser.parse_project(sys.argv[1])
        
        get_skill_logger(__name__).info(f"\n=== 解析结果统计 ===")
        get_skill_logger(__name__).info(f"总元素数量: {len(elements)}")
        
        # 按类型分类统计
        type_counts = {}
        for key, element in elements.items():
            element_type = element.get('type', 'unknown')
            type_counts[element_type] = type_counts.get(element_type, 0) + 1
        
        get_skill_logger(__name__).info("\n按类型统计:")
        for element_type, count in sorted(type_counts.items()):
            get_skill_logger(__name__).info(f"  {element_type}: {count}")
    else:
        get_skill_logger(__name__).info("请提供项目路径作为参数")
