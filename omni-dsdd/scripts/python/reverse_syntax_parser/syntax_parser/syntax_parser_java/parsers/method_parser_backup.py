#!/usr/bin/env python3
import re
import uuid
from typing import Dict, List, Any, Optional, Tuple
from ..constants import UUID_SEPARATOR

class MethodParser:
    """Java方法解析器"""
    
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
    
    def parse_method(self, method_text: str, class_name: str, filename: str) -> Tuple[str, Dict[str, Any]]:
        """解析单个方法"""
        # 方法模式
        method_pattern = r'''
            ((?:@\w+(?:\([^)]*\))?\s*\n?\s*)*)           # 注解
            ((?:public|private|protected)\s+)?          # 访问修饰符
            ((?:static\s+|final\s+|synchronized\s+|native\s+|abstract\s+)*) # 其他修饰符
            (\w+(?:<[^>]*>)?(?:\[\])*)\s+               # 返回类型
            (\w+)\s*                                    # 方法名
            \(([^)]*)\)                                 # 参数列表
            (?:\s*throws\s+([^{]+?))?                   # throws子句
            \s*(\{|;)                                   # 方法体开始或抽象方法分号
        '''
        
        match = re.search(method_pattern, method_text, re.VERBOSE | re.MULTILINE)
        
        if not match:
            return None, None
        
        annotations_text = match.group(1).strip()
        access_modifier = (match.group(2) or "package").strip()
        other_modifiers = match.group(3).strip()
        return_type = match.group(4).strip()
        method_name = match.group(5)
        params_text = match.group(6).strip()
        throws_clause = match.group(7).strip() if match.group(7) else ""
        body_start = match.group(8)
        
        # 生成唯一ID
        unique_id = str(uuid.uuid4())
        method_key = f"{method_name}{UUID_SEPARATOR}{unique_id}"
        
        # 提取完整的方法体
        method_body = method_text
        if body_start == '{':
            method_body = self._extract_complete_method_body(method_text, match.start())
        
        method_info = {
            "type": "method_definition",
            "content": method_body,
            "filename": filename,
            "name": method_name,
            "uuid": unique_id,
            "class_name": class_name,
            "return_type": return_type,
            "params": self._parse_parameters(params_text),
            "access_modifier": access_modifier.replace(" ", "") if access_modifier else "package",
            "is_static": "static" in other_modifiers,
            "is_final": "final" in other_modifiers,
            "is_synchronized": "synchronized" in other_modifiers,
            "is_native": "native" in other_modifiers,
            "is_abstract": "abstract" in other_modifiers or body_start == ';',
            "is_constructor": method_name == class_name,
            "other_modifiers": other_modifiers,
            "throws_clause": throws_clause,
            "annotations": self._parse_annotations(annotations_text),
            "docstring": self._extract_javadoc(method_text, match.start()),
            "dependencies": self._extract_method_dependencies(method_body),
            "lineno": self._calculate_line_number(method_text, match.start()),
            "end_lineno": self._calculate_line_number(method_text, match.start() + len(method_body)),
            "complexity_info": self._analyze_method_complexity(method_body)
        }
        
        return method_key, method_info
    
    def parse_all_methods_from_class(self, class_content: str, class_name: str, filename: str) -> Dict[str, Dict[str, Any]]:
        """从类中解析所有方法（改进版 - 支持更多Java语法形式）"""
        methods = {}
        
        # 改进的方法模式 - 支持更多Java语法形式
        method_pattern = r'''
            # Javadoc（可选）
            ((?:/\*\*[\s\S]*?\*/\s*)?)
            
            # 注解（可选，支持多个和多行）
            ((?:@\w+(?:\([^)]*\))?\s*)*)
            
            # 访问修饰符
            ((?:public|private|protected)\s+)?
            
            # 其他修饰符（支持多个）
            ((?:(?:static|final|synchronized|native|abstract|strictfp|default)\s+)*)
            
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
        
        matches = re.finditer(method_pattern, class_content, re.VERBOSE | re.MULTILINE | re.DOTALL)
        
        for match in matches:
            javadoc = match.group(1) or ""
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
            
            # 生成唯一ID
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
                "params": self._parse_parameters(params_text),
                "access_modifier": access_modifier.replace(" ", "") if access_modifier else "package",
                "is_static": "static" in other_modifiers,
                "is_final": "final" in other_modifiers,
                "is_synchronized": "synchronized" in other_modifiers,
                "is_native": "native" in other_modifiers,
                "is_abstract": "abstract" in other_modifiers or method_body == ';',
                "is_default": "default" in other_modifiers,
                "is_constructor": method_name == class_name,
                "other_modifiers": other_modifiers.strip(),
                "throws_clause": throws_clause.strip(),
                "annotations": self._parse_method_annotations(annotations_text),
                "docstring": self._extract_method_javadoc(javadoc),
                "dependencies": self._extract_method_dependencies(match.group(0)),
                "lineno": self._calculate_line_number(class_content, match.start()),
                "end_lineno": self._calculate_line_number(class_content, match.end()),
                "complexity_info": self._analyze_method_complexity(method_body)
            }
            
            methods[method_key] = method_info
        
        return methods
    
    def _extract_complete_method_body(self, method_text: str, start_pos: int) -> str:
        """提取完整的方法体"""
        # 查找第一个大括号的位置
        brace_start = method_text.find('{', start_pos)
        if brace_start == -1:
            return method_text  # 可能是抽象方法
        
        # 匹配大括号
        brace_count = 0
        method_end = brace_start
        
        for i in range(brace_start, len(method_text)):
            if method_text[i] == '{':
                brace_count += 1
            elif method_text[i] == '}':
                brace_count -= 1
                if brace_count == 0:
                    method_end = i + 1
                    break
        
        return method_text[:method_end]
    
    def _parse_generic_parameters(self, generic_text: str) -> List[str]:
        """解析泛型参数"""
        if not generic_text:
            return []
        
        params = []
        for param in generic_text.split(','):
            param = param.strip()
            if param:
                param_name = param.split()[0]
                params.append(param_name)
        
        return params
    
    def _parse_method_annotations(self, annotations_text: str) -> List[Dict[str, Any]]:
        """解析方法注解"""
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
    
    def _extract_method_javadoc(self, javadoc_text: str) -> str:
        """提取方法Javadoc"""
        if not javadoc_text:
            return ""
        
        javadoc_match = re.search(r'/\*\*([\s\S]*?)\*/', javadoc_text)
        if javadoc_match:
            return javadoc_match.group(1).strip()
        return ""
    
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
    
    def _extract_method_dependencies(self, method_body: str) -> List[str]:
        """提取方法依赖"""
        dependencies = set()
        
        # 提取方法调用
        method_call_pattern = r'(\w+)\.(\w+)\s*\('
        method_matches = re.finditer(method_call_pattern, method_body)
        for match in method_matches:
            class_or_obj = match.group(1)
            method_name = match.group(2)
            
            # 排除this和super
            if class_or_obj not in ['this', 'super']:
                dependencies.add(f"{class_or_obj}.{method_name}")
                # 如果是类名（首字母大写），也添加类依赖
                if class_or_obj[0].isupper():
                    dependencies.add(class_or_obj)
        
        # 提取构造函数调用
        constructor_pattern = r'new\s+(\w+)\s*\('
        constructor_matches = re.finditer(constructor_pattern, method_body)
        for match in constructor_matches:
            class_name = match.group(1)
            dependencies.add(class_name)
        
        # 提取静态字段引用
        static_field_pattern = r'(\w+)\.(\w+)(?!\s*\()'
        static_matches = re.finditer(static_field_pattern, method_body)
        for match in static_matches:
            class_or_obj = match.group(1)
            field_name = match.group(2)
            
            # 排除this和super
            if class_or_obj not in ['this', 'super']:
                dependencies.add(f"{class_or_obj}.{field_name}")
                # 如果是类名（首字母大写），也添加类依赖
                if class_or_obj[0].isupper():
                    dependencies.add(class_or_obj)
        
        # 提取类型引用（局部变量声明、强制转换等）
        type_pattern = r'(?:^|\s)(\w+)(?:<[^>]*>)?\s+\w+\s*[=;]'
        type_matches = re.finditer(type_pattern, method_body)
        for match in type_matches:
            type_name = match.group(1)
            if (type_name not in self.java_keywords and 
                type_name[0].isupper() and 
                type_name not in ['String', 'Integer', 'Boolean', 'Long', 'Double', 'Float']):
                dependencies.add(type_name)
        
        # 提取强制转换
        cast_pattern = r'\(\s*(\w+)\s*\)'
        cast_matches = re.finditer(cast_pattern, method_body)
        for match in cast_matches:
            type_name = match.group(1)
            if (type_name not in self.java_keywords and 
                type_name[0].isupper() and 
                type_name not in ['String', 'Integer', 'Boolean', 'Long', 'Double', 'Float']):
                dependencies.add(type_name)
        
        return list(dependencies)
    
    def _analyze_method_complexity(self, method_body: str) -> Dict[str, Any]:
        """分析方法复杂度"""
        if not method_body:
            return {}
        
        # 计算行数
        line_count = len(method_body.split('\n'))
        
        # 计算圈复杂度
        cyclomatic_complexity = self._calculate_cyclomatic_complexity(method_body)
        
        # 检查是否有嵌套
        has_nested_loops = self._has_nested_loops(method_body)
        has_nested_conditions = self._has_nested_conditions(method_body)
        
        # 计算参数数量（从方法签名中提取）
        param_pattern = r'\([^)]*\)'
        param_match = re.search(param_pattern, method_body)
        parameter_count = 0
        if param_match:
            params_text = param_match.group(0)[1:-1].strip()
            if params_text:
                parameter_count = len(self._split_parameters(params_text))
        
        return {
            "cyclomatic_complexity": cyclomatic_complexity,
            "line_count": line_count,
            "parameter_count": parameter_count,
            "has_nested_loops": has_nested_loops,
            "has_nested_conditions": has_nested_conditions,
            "has_try_catch": "try" in method_body and "catch" in method_body,
            "has_recursion": self._has_recursion(method_body)
        }
    
    def _calculate_cyclomatic_complexity(self, method_body: str) -> int:
        """计算圈复杂度"""
        complexity = 1  # 基础复杂度
        
        # 计算控制流语句
        patterns = [
            r'\bif\s*\(',          # if语句
            r'\belse\s+if\s*\(',   # else if语句
            r'\bwhile\s*\(',       # while循环
            r'\bfor\s*\(',         # for循环
            r'\bdo\s*\{',          # do-while循环
            r'\bswitch\s*\(',      # switch语句
            r'\bcase\s+',          # case分支
            r'\bcatch\s*\(',       # catch块
            r'\?\s*.*?\s*:',       # 三元运算符
            r'\&\&',               # 逻辑与
            r'\|\|'                # 逻辑或
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, method_body)
            complexity += len(list(matches))
        
        return complexity
    
    def _has_nested_loops(self, method_body: str) -> bool:
        """检查是否有嵌套循环"""
        loop_patterns = [r'\bfor\s*\(', r'\bwhile\s*\(', r'\bdo\s*\{']
        
        for pattern in loop_patterns:
            matches = list(re.finditer(pattern, method_body))
            if len(matches) > 1:
                return True
        
        return False
    
    def _has_nested_conditions(self, method_body: str) -> bool:
        """检查是否有嵌套条件"""
        if_count = len(re.findall(r'\bif\s*\(', method_body))
        return if_count > 2
    
    def _has_recursion(self, method_body: str) -> bool:
        """检查是否有递归调用"""
        # 简单检查：查找方法名的调用
        method_name_pattern = r'(\w+)\s*\('
        match = re.search(method_name_pattern, method_body)
        if match:
            method_name = match.group(1)
            return method_name in method_body[match.end():]
        
        return False
    
    def _calculate_line_number(self, content: str, position: int) -> int:
        """计算在内容中指定位置的行号"""
        lines_before = content[:position].count('\n')
        return lines_before + 1
