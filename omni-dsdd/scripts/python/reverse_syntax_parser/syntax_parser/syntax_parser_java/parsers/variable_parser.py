#!/usr/bin/env python3
import re
import uuid
from typing import Dict, List, Any, Optional, Tuple

# 导入常量
try:
    from ..constants import UUID_SEPARATOR
except ImportError:
    from constants import UUID_SEPARATOR

class VariableParser:
    """Java变量解析器"""
    
    def __init__(self):
        self.primitive_types = {
            'byte', 'short', 'int', 'long', 'float', 'double', 'boolean', 'char'
        }
        self.common_types = {
            'String', 'Integer', 'Long', 'Double', 'Float', 'Boolean', 'Character',
            'List', 'ArrayList', 'LinkedList', 'Set', 'HashSet', 'LinkedHashSet',
            'Map', 'HashMap', 'LinkedHashMap', 'TreeMap', 'Date', 'LocalDate',
            'LocalDateTime', 'BigDecimal', 'BigInteger', 'Object'
        }
    
    def parse_field_variables(self, class_content: str, class_name: str, filename: str) -> Dict[str, Dict[str, Any]]:
        """解析类字段变量"""
        variables = {}
        
        # 字段模式 - 更精确的匹配
        field_pattern = r'''
            (?:^|\n)\s*                                    # 行开始
            (?:@\w+(?:\([^)]*\))?\s*\n?\s*)*               # 可选注解
            (public|private|protected)?\s*                  # 访问修饰符
            (static\s+)?                                   # static关键字
            (final\s+)?                                    # final关键字
            (volatile\s+|transient\s+)?                    # 其他修饰符
            (\w+(?:<[^>]*>)?(?:\[\])*)\s+                  # 类型（支持泛型和数组）
            (\w+)                                          # 变量名
            (?:\s*=\s*([^;]+?))?                          # 可选的初始值
            \s*;                                          # 分号结束
        '''
        
        matches = re.finditer(field_pattern, class_content, re.VERBOSE | re.MULTILINE)
        
        for match in matches:
            access_modifier = match.group(1) or "package"
            is_static = bool(match.group(2))
            is_final = bool(match.group(3))
            other_modifiers = match.group(4) or ""
            data_type = match.group(5).strip()
            var_name = match.group(6)
            initial_value = match.group(7).strip() if match.group(7) else None
            
            # 生成唯一ID
            unique_id = str(uuid.uuid4())
            var_key = f"{var_name}{UUID_SEPARATOR}{unique_id}"
            
            # 确定变量类型
            var_type = "class_variable" if is_static else "instance_variable"
            if is_final and is_static:
                var_type = "constant_definition"
            
            variable_info = {
                "type": var_type,
                "content": match.group(0).strip(),
                "filename": filename,
                "name": var_name,
                "uuid": unique_id,
                "datatype": data_type,
                "value": self._parse_initial_value(initial_value),
                "access_modifier": access_modifier,
                "is_static": is_static,
                "is_final": is_final,
                "other_modifiers": other_modifiers.strip(),
                "class_name": class_name,
                "lineno": self._calculate_line_number(class_content, match.start()),
                "dependencies": self._extract_field_dependencies(initial_value, data_type)
            }
            
            variables[var_key] = variable_info
        
        return variables
    
    def parse_local_variables(self, method_content: str, method_name: str, class_name: str, filename: str) -> Dict[str, Dict[str, Any]]:
        """解析方法内的局部变量"""
        variables = {}
        
        # 局部变量模式
        local_var_pattern = r'''
            (?:^|\n|\{|\;)\s*                              # 语句开始
            (?:final\s+)?                                  # 可选final
            (\w+(?:<[^>]*>)?(?:\[\])*)\s+                  # 类型
            (\w+)                                          # 变量名
            (?:\s*=\s*([^;,}]+?))?                        # 可选初始值
            \s*[;,}]                                      # 结束符
        '''
        
        matches = re.finditer(local_var_pattern, method_content, re.VERBOSE | re.MULTILINE)
        
        for match in matches:
            data_type = match.group(1).strip()
            var_name = match.group(2)
            initial_value = match.group(3).strip() if match.group(3) else None
            
            # 跳过一些常见的非变量声明
            if var_name in {'if', 'for', 'while', 'switch', 'try', 'catch', 'return', 'new', 'this', 'super'}:
                continue
            
            # 跳过方法调用
            if '(' in var_name or ')' in var_name:
                continue
            
            # 生成唯一ID
            unique_id = str(uuid.uuid4())
            var_key = f"{var_name}{UUID_SEPARATOR}{unique_id}"
            
            variable_info = {
                "type": "local_variable",
                "content": match.group(0).strip(),
                "filename": filename,
                "name": var_name,
                "uuid": unique_id,
                "datatype": data_type,
                "value": self._parse_initial_value(initial_value),
                "access_modifier": "local",
                "method_name": method_name,
                "class_name": class_name,
                "lineno": self._calculate_line_number(method_content, match.start()),
                "dependencies": self._extract_field_dependencies(initial_value, data_type)
            }
            
            variables[var_key] = variable_info
        
        return variables
    
    def parse_parameters(self, method_signature: str, method_name: str, class_name: str, filename: str) -> Dict[str, Dict[str, Any]]:
        """解析方法参数"""
        variables = {}
        
        # 提取参数列表
        param_pattern = r'\(([^)]*)\)'
        param_match = re.search(param_pattern, method_signature)
        
        if not param_match or not param_match.group(1).strip():
            return variables
        
        params_text = param_match.group(1)
        
        # 解析各个参数
        param_item_pattern = r'(?:final\s+)?(\w+(?:<[^>]*>)?(?:\[\])*)\s+(\w+)(?:\s*,|\s*$)'
        param_matches = re.finditer(param_item_pattern, params_text)
        
        for match in param_matches:
            data_type = match.group(1).strip()
            param_name = match.group(2)
            
            # 生成唯一ID
            unique_id = str(uuid.uuid4())
            var_key = f"{param_name}{UUID_SEPARATOR}{unique_id}"
            
            variable_info = {
                "type": "parameter",
                "content": f"{data_type} {param_name}",
                "filename": filename,
                "name": param_name,
                "uuid": unique_id,
                "datatype": data_type,
                "value": None,
                "access_modifier": "parameter",
                "method_name": method_name,
                "class_name": class_name,
                "dependencies": self._extract_field_dependencies(None, data_type)
            }
            
            variables[var_key] = variable_info
        
        return variables
    
    def _parse_initial_value(self, value_text: Optional[str]) -> Any:
        """解析初始值"""
        if not value_text:
            return None
        
        value_text = value_text.strip()
        
        # 处理各种类型的值
        if value_text in ['null', 'NULL']:
            return None
        elif value_text in ['true', 'false']:
            return value_text == 'true'
        elif value_text.startswith('"') and value_text.endswith('"'):
            return value_text[1:-1]  # 字符串字面量
        elif value_text.startswith("'") and value_text.endswith("'"):
            return value_text[1:-1]  # 字符字面量
        elif re.match(r'^-?\d+$', value_text):
            return int(value_text)  # 整数
        elif re.match(r'^-?\d+\.\d+[fF]?$', value_text):
            return float(value_text.rstrip('fF'))  # 浮点数
        elif value_text.startswith('new '):
            return f"new_instance({value_text[4:]})"  # 对象实例化
        elif '(' in value_text and ')' in value_text:
            return f"method_call({value_text})"  # 方法调用
        else:
            return value_text  # 其他情况保持原样
    
    def _extract_field_dependencies(self, initial_value: Optional[str], data_type: str) -> List[str]:
        """提取字段的依赖关系"""
        dependencies = set()
        
        # 从数据类型中提取依赖
        type_dependencies = self._extract_type_dependencies(data_type)
        dependencies.update(type_dependencies)
        
        # 从初始值中提取依赖
        if initial_value:
            value_dependencies = self._extract_value_dependencies(initial_value)
            dependencies.update(value_dependencies)
        
        return list(dependencies)
    
    def _extract_type_dependencies(self, data_type: str) -> List[str]:
        """从数据类型中提取依赖"""
        dependencies = []
        
        # 移除数组标记
        clean_type = re.sub(r'\[\]', '', data_type)
        
        # 处理泛型类型
        generic_pattern = r'(\w+)<([^>]+)>'
        generic_match = re.search(generic_pattern, clean_type)
        
        if generic_match:
            main_type = generic_match.group(1)
            generic_types = generic_match.group(2)
            
            # 添加主类型
            if main_type not in self.primitive_types:
                dependencies.append(main_type)
            
            # 添加泛型参数类型
            for generic_type in re.split(r'[,\s]+', generic_types):
                generic_type = generic_type.strip()
                if generic_type and generic_type not in self.primitive_types:
                    dependencies.append(generic_type)
        else:
            # 简单类型
            if clean_type not in self.primitive_types:
                dependencies.append(clean_type)
        
        return dependencies
    
    def _extract_value_dependencies(self, value_text: str) -> List[str]:
        """从初始值中提取依赖"""
        dependencies = []
        
        # 查找方法调用
        method_call_pattern = r'(\w+)\.(\w+)\s*\('
        method_matches = re.finditer(method_call_pattern, value_text)
        for match in method_matches:
            class_name = match.group(1)
            method_name = match.group(2)
            dependencies.extend([class_name, f"{class_name}.{method_name}"])
        
        # 查找构造函数调用
        constructor_pattern = r'new\s+(\w+)\s*\('
        constructor_matches = re.finditer(constructor_pattern, value_text)
        for match in constructor_matches:
            class_name = match.group(1)
            dependencies.append(class_name)
        
        # 查找静态字段引用
        static_field_pattern = r'(\w+)\.(\w+)(?!\s*\()'
        static_matches = re.finditer(static_field_pattern, value_text)
        for match in static_matches:
            class_name = match.group(1)
            field_name = match.group(2)
            dependencies.extend([class_name, f"{class_name}.{field_name}"])
        
        return dependencies
    
    def _calculate_line_number(self, content: str, position: int) -> int:
        """计算在内容中指定位置的行号"""
        lines_before = content[:position].count('\n')
        return lines_before + 1
    
    def _determine_access_modifier(self, modifiers_text: str) -> str:
        """确定访问修饰符"""
        modifiers_text = modifiers_text.lower()
        if 'public' in modifiers_text:
            return 'public'
        elif 'private' in modifiers_text:
            return 'private'
        elif 'protected' in modifiers_text:
            return 'protected'
        else:
            return 'package'  # Java默认包访问权限
    
    def extract_all_variables_from_class(self, class_content: str, class_name: str, filename: str) -> Dict[str, Dict[str, Any]]:
        """从类中提取所有变量（字段、局部变量、参数）"""
        all_variables = {}
        
        # 提取类字段
        field_variables = self.parse_field_variables(class_content, class_name, filename)
        all_variables.update(field_variables)
        
        # 提取方法中的局部变量和参数
        method_pattern = r'((?:public|private|protected)?\s*(?:static\s+)?(?:final\s+)?(?:synchronized\s+)?(?:abstract\s+)?(?:\w+(?:<[^>]*>)?(?:\[\])?\s+)?(\w+)\s*\([^)]*\)\s*(?:throws\s+[^{]+)?\s*\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})'
        
        method_matches = re.finditer(method_pattern, class_content)
        
        for method_match in method_matches:
            method_content = method_match.group(1)
            method_name = method_match.group(2)
            
            # 跳过构造函数（通常首字母大写）
            if method_name[0].isupper():
                continue
            
            # 提取方法参数
            param_variables = self.parse_parameters(method_content, method_name, class_name, filename)
            all_variables.update(param_variables)
            
            # 提取局部变量
            local_variables = self.parse_local_variables(method_content, method_name, class_name, filename)
            all_variables.update(local_variables)
        
        return all_variables
