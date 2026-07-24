#!/usr/bin/env python3
import re
import uuid
from typing import Dict, List, Any, Optional, Tuple

# 导入常量
try:
    from ..constants import UUID_SEPARATOR
except ImportError:
    from constants import UUID_SEPARATOR

class FunctionParser:
    """Java函数解析器（主要处理静态方法和独立函数）"""
    
    def __init__(self):
        self.java_keywords = {
            'abstract', 'assert', 'boolean', 'break', 'byte', 'case', 'catch', 'char',
            'class', 'const', 'continue', 'default', 'do', 'double', 'else', 'enum',
            'extends', 'final', 'finally', 'float', 'for', 'goto', 'if', 'implements',
            'import', 'instanceof', 'int', 'interface', 'long', 'native', 'new',
            'package', 'private', 'protected', 'public', 'return', 'short', 'static',
            'strictfp', 'super', 'switch', 'synchronized', 'this', 'throw', 'throws',
            'transient', 'try', 'void', 'volatile', 'while'
        }
    
    def parse_static_methods(self, class_content: str, class_name: str, filename: str, class_uuid: str = None) -> Dict[str, Dict[str, Any]]:
        """解析静态方法（可作为函数处理）"""
        functions = {}
        
        # 静态方法模式
        static_method_pattern = r'''
            ((?:@\w+(?:\([^)]*\))?\s*\n?\s*)*)           # 注解
            ((?:public|private|protected)\s+)?          # 访问修饰符
            static\s+                                   # static关键字
            ((?:final\s+|synchronized\s+|native\s+)*)   # 其他修饰符
            (\w+(?:<[^>]*>)?(?:\[\])*)\s+               # 返回类型
            (\w+)\s*                                    # 方法名
            \(([^)]*)\)                                 # 参数列表
            (?:\s*throws\s+([^{]+?))?                   # throws子句
            \s*\{                                       # 方法体开始
        '''
        
        matches = re.finditer(static_method_pattern, class_content, re.VERBOSE | re.MULTILINE)
        
        for match in matches:
            annotations_text = match.group(1).strip()
            access_modifier = (match.group(2) or "package").strip()
            other_modifiers = match.group(3).strip()
            return_type = match.group(4).strip()
            function_name = match.group(5)
            params_text = match.group(6).strip()
            throws_clause = match.group(7).strip() if match.group(7) else ""
            
            # 查找完整的方法体
            method_start = match.start()
            method_body = self._extract_method_body(class_content, method_start)
            
            # 生成唯一ID
            unique_id = str(uuid.uuid4())
            function_key = f"{function_name}{UUID_SEPARATOR}{unique_id}"
            
            function_info = {
                "type": "function_definition",
                "content": method_body,
                "filename": filename,
                "name": function_name,
                "uuid": unique_id,
                "class_name": class_name,
                "class_key": f"{class_name}{UUID_SEPARATOR}{class_uuid}" if class_uuid else f"{class_name}{UUID_SEPARATOR}{str(uuid.uuid4())}",
                "return_type": return_type,
                "params": self._parse_parameters(params_text),
                "access_modifier": access_modifier.replace(" ", "") if access_modifier else "package",
                "is_static": True,
                "other_modifiers": other_modifiers,
                "throws_clause": throws_clause,
                "annotations": self._parse_annotations(annotations_text),
                "docstring": self._extract_javadoc(class_content, method_start),
                "dependencies": self._extract_method_dependencies(method_body, function_name),
                "lineno": self._calculate_line_number(class_content, method_start),
                "end_lineno": self._calculate_line_number(class_content, method_start + len(method_body))
            }
            
            functions[function_key] = function_info
        
        return functions
    
    def parse_main_method(self, class_content: str, class_name: str, filename: str, class_uuid: str = None) -> Dict[str, Dict[str, Any]]:
        """解析main方法"""
        functions = {}
        
        # main方法模式
        main_pattern = r'''
            ((?:@\w+(?:\([^)]*\))?\s*\n?\s*)*)           # 注解
            public\s+static\s+void\s+main\s*            # public static void main
            \(String(?:\[\]|\s+\[\])\s+(\w+)\)          # (String[] args)
            (?:\s*throws\s+([^{]+?))?                   # throws子句
            \s*\{                                       # 方法体开始
        '''
        
        match = re.search(main_pattern, class_content, re.VERBOSE | re.MULTILINE)
        
        if match:
            annotations_text = match.group(1).strip()
            args_name = match.group(2)
            throws_clause = match.group(3).strip() if match.group(3) else ""
            
            # 查找完整的方法体
            method_start = match.start()
            method_body = self._extract_method_body(class_content, method_start)
            
            # 生成唯一ID
            unique_id = str(uuid.uuid4())
            function_key = f"main{UUID_SEPARATOR}{unique_id}"
            
            function_info = {
                "type": "function_definition",
                "content": method_body,
                "filename": filename,
                "name": "main",
                "uuid": unique_id,
                "class_name": class_name,
                "class_key": f"{class_name}{UUID_SEPARATOR}{class_uuid}" if class_uuid else f"{class_name}{UUID_SEPARATOR}{str(uuid.uuid4())}",
                "return_type": "void",
                "params": [{"name": args_name, "datatype": "String[]", "is_varargs": True}],
                "access_modifier": "public",
                "is_static": True,
                "is_main": True,
                "throws_clause": throws_clause,
                "annotations": self._parse_annotations(annotations_text),
                "docstring": self._extract_javadoc(class_content, method_start),
                "dependencies": self._extract_method_dependencies(method_body, "main"),
                "lineno": self._calculate_line_number(class_content, method_start),
                "end_lineno": self._calculate_line_number(class_content, method_start + len(method_body))
            }
            
            functions[function_key] = function_info
        
        return functions
    
    def _extract_method_body(self, content: str, start_pos: int) -> str:
        """提取完整的方法体"""
        # 从方法开始位置查找完整的大括号匹配
        brace_count = 0
        method_start = content.find('{', start_pos)
        
        if method_start == -1:
            return ""
        
        method_end = method_start
        for i in range(method_start, len(content)):
            if content[i] == '{':
                brace_count += 1
            elif content[i] == '}':
                brace_count -= 1
                if brace_count == 0:
                    method_end = i + 1
                    break
        
        # 向前查找方法声明的开始
        declaration_start = start_pos
        lines = content[:start_pos].split('\n')
        
        # 向前查找注解和方法声明
        for i in range(len(lines) - 1, -1, -1):
            line = lines[i].strip()
            if not line or line.startswith('@') or line.startswith('//') or line.startswith('/*'):
                continue
            if any(keyword in line for keyword in ['public', 'private', 'protected', 'static']):
                declaration_start = content.find(lines[i])
                break
        
        return content[declaration_start:method_end]
    
    def _parse_parameters(self, params_text: str) -> List[Dict[str, Any]]:
        """解析方法参数"""
        if not params_text.strip():
            return []
        
        params = []
        
        # 分割参数，考虑泛型中的逗号
        param_parts = self._split_parameters(params_text)
        
        for part in param_parts:
            part = part.strip()
            if not part:
                continue
            
            # 解析单个参数
            param_info = self._parse_single_parameter(part)
            if param_info:
                params.append(param_info)
        
        return params
    
    def _split_parameters(self, params_text: str) -> List[str]:
        """智能分割参数列表，考虑泛型"""
        params = []
        current_param = ""
        bracket_count = 0
        
        for char in params_text:
            if char == '<':
                bracket_count += 1
            elif char == '>':
                bracket_count -= 1
            elif char == ',' and bracket_count == 0:
                params.append(current_param.strip())
                current_param = ""
                continue
            
            current_param += char
        
        if current_param.strip():
            params.append(current_param.strip())
        
        return params
    
    def _parse_single_parameter(self, param_text: str) -> Optional[Dict[str, Any]]:
        """解析单个参数"""
        # 参数模式：[final] [annotations] type name
        param_pattern = r'''
            (?:final\s+)?                              # 可选final
            (?:@\w+(?:\([^)]*\))?\s*)*                 # 可选注解
            (\w+(?:<[^>]*>)?(?:\.\.\.|(?:\[\])*)?)\s+  # 类型（支持泛型、可变参数、数组）
            (\w+)                                      # 参数名
        '''
        
        match = re.search(param_pattern, param_text.strip(), re.VERBOSE)
        if match:
            param_type = match.group(1)
            param_name = match.group(2)
            
            return {
                "name": param_name,
                "datatype": param_type,
                "is_final": "final" in param_text,
                "is_varargs": "..." in param_type,
                "annotations": self._extract_parameter_annotations(param_text)
            }
        
        return None
    
    def _extract_parameter_annotations(self, param_text: str) -> List[str]:
        """提取参数注解"""
        annotations = []
        annotation_pattern = r'@(\w+)(?:\([^)]*\))?'
        matches = re.finditer(annotation_pattern, param_text)
        
        for match in matches:
            annotations.append(match.group(1))
        
        return annotations
    
    def _parse_annotations(self, annotations_text: str) -> List[Dict[str, Any]]:
        """解析注解"""
        if not annotations_text.strip():
            return []
        
        annotations = []
        annotation_pattern = r'@(\w+(?:\.\w+)*)(?:\s*\(([^)]*)\))?'
        matches = re.finditer(annotation_pattern, annotations_text)
        
        for match in matches:
            annotation_name = match.group(1)
            annotation_params = match.group(2) if match.group(2) else ""
            
            annotations.append({
                "name": annotation_name,
                "params": annotation_params
            })
        
        return annotations
    
    def _extract_javadoc(self, content: str, method_start: int) -> str:
        """提取Javadoc注释"""
        # 向前查找Javadoc注释
        before_method = content[:method_start]
        javadoc_pattern = r'/\*\*(.*?)\*/'
        
        matches = list(re.finditer(javadoc_pattern, before_method, re.DOTALL))
        if matches:
            last_match = matches[-1]
            # 检查Javadoc是否紧邻方法
            between_text = before_method[last_match.end():].strip()
            if not between_text or all(line.strip().startswith('@') for line in between_text.split('\n')):
                return last_match.group(1).strip()
        
        return ""
    
    def _extract_method_dependencies(self, method_body: str, current_method_name: str = None) -> List[str]:
        """提取方法依赖"""
        dependencies = set()
        
        # 提取方法调用
        method_call_pattern = r'(\w+)\.(\w+)\s*\('
        method_matches = re.finditer(method_call_pattern, method_body)
        for match in method_matches:
            class_name = match.group(1)
            method_name = match.group(2)
            dependencies.add(f"{class_name}.{method_name}")
            dependencies.add(class_name)
        
        # 提取new关键字（构造函数调用）
        constructor_pattern = r'new\s+(\w+)\s*\('
        constructor_matches = re.finditer(constructor_pattern, method_body)
        for match in constructor_matches:
            class_name = match.group(1)
            dependencies.add(class_name)
        
        # 提取静态字段引用
        static_field_pattern = r'(\w+)\.(\w+)(?!\s*\()'
        static_matches = re.finditer(static_field_pattern, method_body)
        for match in static_matches:
            class_name = match.group(1)
            field_name = match.group(2)
            # 排除this和super
            if class_name not in ['this', 'super']:
                dependencies.add(f"{class_name}.{field_name}")
                dependencies.add(class_name)
        
        # 提取局部变量的类型
        local_var_pattern = r'(?:^|\s)(\w+)(?:<[^>]*>)?\s+\w+\s*='
        var_matches = re.finditer(local_var_pattern, method_body)
        for match in var_matches:
            type_name = match.group(1)
            if type_name not in self.java_keywords and type_name[0].isupper():
                dependencies.add(type_name)
        
        # 过滤掉自己（递归调用）
        if current_method_name:
            dependencies = {dep for dep in dependencies 
                          if dep != current_method_name}
        
        return list(dependencies)
    
    def _calculate_line_number(self, content: str, position: int) -> int:
        """计算在内容中指定位置的行号"""
        lines_before = content[:position].count('\n')
        return lines_before + 1
    
    def extract_all_functions_from_class(self, class_content: str, class_name: str, filename: str, class_uuid: str = None) -> Dict[str, Dict[str, Any]]:
        """从类中提取所有函数（静态方法和main方法）"""
        all_functions = {}
        
        # 提取静态方法
        static_functions = self.parse_static_methods(class_content, class_name, filename, class_uuid)
        all_functions.update(static_functions)
        
        # 提取main方法
        main_functions = self.parse_main_method(class_content, class_name, filename, class_uuid)
        all_functions.update(main_functions)
        
        return all_functions
