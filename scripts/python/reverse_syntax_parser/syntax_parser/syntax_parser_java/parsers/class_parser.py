#!/usr/bin/env python3
import re
import sys
import uuid
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

# 导入常量
try:
    from ..constants import UUID_SEPARATOR
except ImportError:
    from constants import UUID_SEPARATOR

# 导入日志模块
sys.path.append(str(Path(__file__).parent.parent.parent / "utils"))
from utils import get_logger

# 导入解析器模块
try:
    from .method_parser import MethodParser
    from .variable_parser import VariableParser
    from .annotation_parser import AnnotationParser
except ImportError:
    from method_parser import MethodParser
    from variable_parser import VariableParser
    from annotation_parser import AnnotationParser

class ClassParser:
    """Java类解析器"""
    
    def __init__(self):
        self.logger = get_logger("class_parser")
        self.method_parser = MethodParser()
        self.variable_parser = VariableParser()
        self.annotation_parser = AnnotationParser()
    
    def parse_class(self, class_content: str, filename: str) -> Tuple[str, Dict[str, Any]]:
        """解析Java类（改进版 - 支持更多语法形式）"""
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
            
            # 泛型参数（可选，支持嵌套）
            (?:<([^<>]*(?:<[^<>]*>[^<>]*)*)>)?
            
            # extends子句（可选，支持复杂继承）
            (?:\s+extends\s+([^{]+?))?
            
            # implements子句（可选，支持多接口）
            (?:\s+implements\s+([^{]+?))?
            
            \s*\{
        '''
        
        match = re.search(class_pattern, class_content, re.VERBOSE | re.MULTILINE | re.DOTALL)
        
        if not match:
            return None, None
        
        javadoc = self._extract_javadoc(match.group(1) or "")
        annotations_text = match.group(2) or ""
        access_modifier = (match.group(3) or "package").strip()
        other_modifiers = match.group(4) or ""
        class_name = match.group(5)
        generic_params = match.group(6)
        extends_class = match.group(7)
        implements_interfaces = match.group(8)
        
        # 生成唯一ID
        unique_id = str(uuid.uuid4())
        class_key = f"{class_name}{UUID_SEPARATOR}{unique_id}"
        
        # 提取类体
        class_body = self._extract_class_body(class_content, match.end() - 1)
        
        # 解析类的各个部分
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
            "other_modifiers": other_modifiers,
            "generic_parameters": self._parse_generic_parameters(generic_params),
            "base_classes": self._parse_base_classes(extends_class),
            "implemented_interfaces": self._parse_implemented_interfaces(implements_interfaces),
            "docstring": javadoc,
            "annotations": self._parse_class_annotations(annotations_text),
            "dependencies": self._extract_class_dependencies(class_content, extends_class, implements_interfaces, class_name),
            "methods": self._parse_methods(class_body, class_name, filename, unique_id, class_content),
            "field_list": self._parse_fields(class_body, class_name, filename),
            "inner_classes": self._parse_inner_classes(class_body, filename),
            "lineno": self._calculate_line_number(class_content, match.start()),
            "end_lineno": self._calculate_line_number(class_content, match.start() + len(class_content)),
            "complexity_info": self._analyze_class_complexity(class_body)
        }
        
        return class_key, class_info
    
    def parse_interface(self, interface_content: str, filename: str) -> Tuple[str, Dict[str, Any]]:
        """解析Java接口（改进版 - 支持更多语法形式）"""
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
            
            # 泛型参数（可选，支持嵌套）
            (?:<([^<>]*(?:<[^<>]*>[^<>]*)*)>)?
            (?:\s+extends\s+([^{]+?))?                # 可选父接口
            \s*\{                                     # 接口体开始
        '''
        
        match = re.search(interface_pattern, interface_content, re.VERBOSE | re.MULTILINE | re.DOTALL)
        
        if not match:
            return None, None
        
        javadoc = self._extract_javadoc(match.group(1) or "")
        annotations_text = match.group(2) or ""
        access_modifier = (match.group(3) or "package").strip()
        other_modifiers = match.group(4) or ""
        interface_name = match.group(5)
        generic_params = match.group(6)
        extends_interfaces = match.group(7)
        
        # 生成唯一ID
        unique_id = str(uuid.uuid4())
        interface_key = f"{interface_name}{UUID_SEPARATOR}{unique_id}"
        
        # 提取接口体
        interface_body = self._extract_class_body(interface_content, match.end() - 1)
        
        interface_info = {
            "type": "interface_definition",
            "content": interface_content,
            "filename": filename,
            "name": interface_name,
            "uuid": unique_id,
            "access_modifier": access_modifier.replace(" ", "") if access_modifier else "package",
            "is_static": "static" in other_modifiers,
            "other_modifiers": other_modifiers,
            "generic_parameters": self._parse_generic_parameters(generic_params),
            "extended_interfaces": self._parse_implemented_interfaces(extends_interfaces),
            "docstring": javadoc,
            "annotations": self._parse_class_annotations(annotations_text),
            "dependencies": self._extract_interface_dependencies(interface_content, extends_interfaces, interface_name),
            "methods": self._parse_interface_methods(interface_body, interface_name, filename, unique_id),
            "constants": self._parse_interface_constants(interface_body, interface_name, filename),
            "lineno": self._calculate_line_number(interface_content, match.start()),
            "end_lineno": self._calculate_line_number(interface_content, match.start() + len(interface_content))
        }
        
        return interface_key, interface_info
    
    def _extract_class_body(self, content: str, start_pos: int) -> str:
        """提取类体内容"""
        brace_count = 0
        class_start = start_pos
        class_end = start_pos
        
        for i in range(start_pos, len(content)):
            if content[i] == '{':
                brace_count += 1
            elif content[i] == '}':
                brace_count -= 1
                if brace_count == 0:
                    class_end = i
                    break
        
        return content[class_start:class_end + 1]
    
    def _parse_generic_parameters(self, generic_params: Optional[str]) -> List[str]:
        """解析泛型参数"""
        if not generic_params:
            return []
        
        # 分割泛型参数
        params = []
        param_parts = re.split(r',\s*', generic_params.strip())
        
        for part in param_parts:
            # 提取泛型参数名（可能包含extends子句）
            param_match = re.match(r'(\w+)(?:\s+extends\s+[\w.]+)?', part.strip())
            if param_match:
                params.append(param_match.group(1))
        
        return params
    
    def _parse_base_classes(self, extends_clause: Optional[str]) -> List[str]:
        """解析父类"""
        if not extends_clause:
            return []
        
        # Java只支持单继承
        base_class = extends_clause.strip()
        # 移除泛型部分进行简化
        base_class = re.sub(r'<[^>]*>', '', base_class)
        return [base_class]
    
    def _parse_implemented_interfaces(self, implements_clause: Optional[str]) -> List[str]:
        """解析实现的接口"""
        if not implements_clause:
            return []
        
        interfaces = []
        interface_parts = re.split(r',\s*', implements_clause.strip())
        
        for part in interface_parts:
            # 移除泛型部分进行简化
            interface_name = re.sub(r'<[^>]*>', '', part.strip())
            if interface_name:
                interfaces.append(interface_name)
        
        return interfaces
    
    def _parse_class_annotations(self, annotations_text: str) -> List[Dict[str, Any]]:
        """解析类注解"""
        return self.annotation_parser.extract_annotations_from_text(annotations_text)
    
    def _extract_class_dependencies(self, class_content: str, extends_class: Optional[str], implements_interfaces: Optional[str], current_class_name: str = None) -> List[str]:
        """提取类级别的依赖关系"""
        dependencies = set()
        
        # 添加父类依赖
        if extends_class:
            base_class = re.sub(r'<[^>]*>', '', extends_class.strip())
            # 不要依赖自己
            if base_class != current_class_name:
                dependencies.add(base_class)
        
        # 添加接口依赖
        if implements_interfaces:
            interfaces = self._parse_implemented_interfaces(implements_interfaces)
            for interface in interfaces:
                # 不要依赖自己
                if interface != current_class_name:
                    dependencies.add(interface)
        
        # 提取import语句
        import_pattern = r'import\s+(?:static\s+)?([^;]+);'
        import_matches = re.finditer(import_pattern, class_content)
        for match in import_matches:
            import_path = match.group(1).strip()
            # 提取类名（最后一部分）
            if '.' in import_path:
                class_name = import_path.split('.')[-1]
                if not import_path.endswith('*'):  # 排除通配符导入
                    # 不要依赖自己
                    if class_name != current_class_name:
                        dependencies.add(class_name)
        
        # 提取类体中的直接类型引用
        type_pattern = r'\b([A-Z]\w+)(?:<[^>]*>)?\s+'
        type_matches = re.finditer(type_pattern, class_content)
        for match in type_matches:
            type_name = match.group(1)
            # 排除Java关键字、基本类型和当前类自己
            if (type_name not in ['String', 'Object', 'Class', 'System', 'Math'] and 
                type_name != current_class_name):
                dependencies.add(type_name)
        
        return list(dependencies)
    
    def _extract_interface_dependencies(self, interface_content: str, extends_interfaces: Optional[str], current_interface_name: str = None) -> List[str]:
        """提取接口级别的依赖关系"""
        dependencies = set()
        
        # 添加父接口依赖
        if extends_interfaces:
            interfaces = self._parse_implemented_interfaces(extends_interfaces)
            for interface in interfaces:
                # 不要依赖自己
                if interface != current_interface_name:
                    dependencies.add(interface)
        
        # 提取import语句
        import_pattern = r'import\s+(?:static\s+)?([^;]+);'
        import_matches = re.finditer(import_pattern, interface_content)
        for match in import_matches:
            import_path = match.group(1).strip()
            if '.' in import_path:
                class_name = import_path.split('.')[-1]
                if not import_path.endswith('*'):
                    # 不要依赖自己
                    if class_name != current_interface_name:
                        dependencies.add(class_name)
        
        # 提取接口体中的直接类型引用
        type_pattern = r'\b([A-Z]\w+)(?:<[^>]*>)?\s+'
        type_matches = re.finditer(type_pattern, interface_content)
        for match in type_matches:
            type_name = match.group(1)
            # 排除Java关键字、基本类型和当前接口自己
            if (type_name not in ['String', 'Object', 'Class', 'System', 'Math'] and 
                type_name != current_interface_name):
                dependencies.add(type_name)
        
        return list(dependencies)
    
    def _parse_methods(self, class_body: str, class_name: str, filename: str, class_uuid: str = None, full_content: str = None) -> Dict[str, Dict[str, Any]]:
        """解析类方法"""
        # 使用完整类内容提取静态导入方法列表，兜底使用类体
        source_for_static_import = full_content if full_content is not None else class_body
        static_import_methods = self._extract_static_import_methods(source_for_static_import)
        methods = self.method_parser.parse_all_methods_from_class(class_body, class_name, filename, static_import_methods)
        
        # 为每个方法添加class_key信息
        for method_key, method_info in methods.items():
            if class_uuid:
                method_info['class_key'] = f"{class_name}{UUID_SEPARATOR}{class_uuid}"
            else:
                # 如果没有提供class_uuid，尝试从name_to_uuid_map中获取
                method_info['class_key'] = f"{class_name}{UUID_SEPARATOR}{str(uuid.uuid4())}"
        
        return methods
    
    def _parse_interface_methods(self, interface_body: str, interface_name: str, filename: str, interface_uuid: str = None) -> Dict[str, Dict[str, Any]]:
        """解析接口方法"""
        methods = {}
        
        # 接口方法模式（通常是抽象的）
        method_pattern = r'''
            ((?:@\w+(?:\([^)]*\))?\s*\n?\s*)*)           # 注解
            (?:public\s+)?                              # 可选public（接口方法默认public）
            (?:abstract\s+)?                            # 可选abstract
            (?:default\s+|static\s+)?                   # default或static方法
            (\w+(?:<[^>]*>)?(?:\[\])*)\s+               # 返回类型
            (\w+)\s*                                    # 方法名
            \(([^)]*)\)                                 # 参数列表
            (?:\s*throws\s+([^{;]+?))?                  # throws子句
            \s*(\{[\s\S]*?\}|;)                        # 方法体或分号
        '''
        
        matches = re.finditer(method_pattern, interface_body, re.VERBOSE | re.MULTILINE)
        
        for match in matches:
            annotations_text = match.group(1).strip()
            return_type = match.group(2).strip()
            method_name = match.group(3)
            params_text = match.group(4).strip()
            throws_clause = match.group(5).strip() if match.group(5) else ""
            body_or_semicolon = match.group(6)
            
            # 生成唯一ID
            unique_id = str(uuid.uuid4())
            method_key = f"{method_name}{UUID_SEPARATOR}{unique_id}"
            
            method_info = {
                "type": "method_definition",
                "content": match.group(0),
                "filename": filename,
                "name": method_name,
                "uuid": unique_id,
                "class_name": interface_name,
                "class_key": f"{interface_name}{UUID_SEPARATOR}{interface_uuid}" if interface_uuid else f"{interface_name}{UUID_SEPARATOR}{str(uuid.uuid4())}",
                "return_type": return_type,
                "params": self.method_parser._parse_parameters(params_text),
                "access_modifier": "public",  # 接口方法默认public
                "is_abstract": body_or_semicolon == ';',
                "is_default": "default" in match.group(0),
                "is_static": "static" in match.group(0),
                "throws_clause": throws_clause,
                "annotations": self.method_parser._parse_annotations(annotations_text),
                "dependencies": [],
                "lineno": self._calculate_line_number(interface_body, match.start()),
                "end_lineno": self._calculate_line_number(interface_body, match.end())
            }
            
            methods[method_key] = method_info
        
        return methods
    
    def _parse_fields(self, class_body: str, class_name: str, filename: str) -> List[Dict[str, Any]]:
        """解析类字段"""
        fields = []
        field_variables = self.variable_parser.parse_field_variables(class_body, class_name, filename)
        
        for field_key, field_info in field_variables.items():
            # 转换为字段列表格式
            field_entry = {
                "name": field_info["name"],
                "type": field_info["type"],
                "datatype": field_info["datatype"],
                "value": field_info["value"],
                "access_modifier": field_info["access_modifier"],
                "is_static": field_info["is_static"],
                "is_final": field_info["is_final"],
                "lineno": field_info["lineno"]
            }
            fields.append(field_entry)
        
        # 按行号排序
        fields.sort(key=lambda x: x["lineno"])
        
        return fields
    
    def _parse_interface_constants(self, interface_body: str, interface_name: str, filename: str) -> Dict[str, Dict[str, Any]]:
        """解析接口常量"""
        constants = {}
        
        # 接口常量模式（默认public static final）
        constant_pattern = r'''
            (?:public\s+)?(?:static\s+)?(?:final\s+)?   # 可选修饰符（接口中默认）
            (\w+(?:<[^>]*>)?(?:\[\])*)\s+               # 类型
            (\w+)\s*                                    # 常量名
            =\s*([^;]+)                                # 值
            \s*;                                       # 分号
        '''
        
        matches = re.finditer(constant_pattern, interface_body, re.VERBOSE | re.MULTILINE)
        
        for match in matches:
            data_type = match.group(1).strip()
            constant_name = match.group(2)
            constant_value = match.group(3).strip()
            
            # 生成唯一ID
            unique_id = str(uuid.uuid4())
            constant_key = f"{constant_name}{UUID_SEPARATOR}{unique_id}"
            
            constant_info = {
                "type": "constant_definition",
                "content": match.group(0),
                "filename": filename,
                "name": constant_name,
                "uuid": unique_id,
                "datatype": data_type,
                "value": self.variable_parser._parse_initial_value(constant_value),
                "access_modifier": "public",
                "is_static": True,
                "is_final": True,
                "interface_name": interface_name,
                "lineno": self._calculate_line_number(interface_body, match.start())
            }
            
            constants[constant_key] = constant_info
        
        return constants
    
    def _parse_inner_classes(self, class_body: str, filename: str) -> Dict[str, Dict[str, Any]]:
        """解析内部类"""
        inner_classes = {}
        
        # 内部类模式
        inner_class_pattern = r'''
            ((?:public|private|protected)\s+)?          # 访问修饰符
            ((?:static\s+|final\s+|abstract\s+)*)       # 其他修饰符
            (?:class|interface)\s+                      # class或interface关键字
            (\w+)                                       # 类名
            (?:\s+extends\s+\w+)?                      # 可选父类
            (?:\s+implements\s+[^{]+?)?                # 可选接口
            \s*\{                                      # 类体开始
        '''
        
        matches = re.finditer(inner_class_pattern, class_body, re.VERBOSE | re.MULTILINE)
        
        for match in matches:
            access_modifier = (match.group(1) or "package").strip()
            other_modifiers = match.group(2).strip()
            inner_class_name = match.group(3)
            
            # 生成唯一ID
            unique_id = str(uuid.uuid4())
            inner_class_key = f"{inner_class_name}{UUID_SEPARATOR}{unique_id}"
            
            # 提取内部类体
            inner_class_body = self._extract_class_body(class_body, match.end() - 1)
            
            inner_class_info = {
                "type": "inner_class_definition",
                "content": inner_class_body,
                "filename": filename,
                "name": inner_class_name,
                "uuid": unique_id,
                "access_modifier": access_modifier.replace(" ", "") if access_modifier else "package",
                "is_static": "static" in other_modifiers,
                "is_final": "final" in other_modifiers,
                "is_abstract": "abstract" in other_modifiers,
                "lineno": self._calculate_line_number(class_body, match.start())
            }
            
            inner_classes[inner_class_key] = inner_class_info
        
        return inner_classes
    
    def _analyze_class_complexity(self, class_body: str) -> Dict[str, Any]:
        """分析类复杂度"""
        # 计算方法数量
        method_count = len(re.findall(r'(?:public|private|protected)?\s*(?:static\s+)?[\w<>\[\]]+\s+\w+\s*\([^)]*\)\s*\{', class_body))
        
        # 计算字段数量
        field_count = len(re.findall(r'(?:public|private|protected)?\s*(?:static\s+)?(?:final\s+)?[\w<>\[\]]+\s+\w+\s*[=;]', class_body))
        
        # 计算内部类数量
        inner_class_count = len(re.findall(r'(?:public|private|protected)?\s*(?:static\s+)?class\s+\w+', class_body))
        
        # 计算行数
        line_count = len(class_body.split('\n'))
        
        return {
            "method_count": method_count,
            "field_count": field_count,
            "inner_class_count": inner_class_count,
            "line_count": line_count,
            "has_inheritance": "extends" in class_body,
            "has_interfaces": "implements" in class_body,
            "has_generics": "<" in class_body and ">" in class_body
        }
    
    def _extract_javadoc(self, text: str) -> str:
        """提取Javadoc注释"""
        javadoc_pattern = r'/\*\*(.*?)\*/'
        match = re.search(javadoc_pattern, text, re.DOTALL)
        if match:
            return match.group(1).strip()
        return ""
    
    def _calculate_line_number(self, content: str, position: int) -> int:
        """计算在内容中指定位置的行号"""
        lines_before = content[:position].count('\n')
        return lines_before + 1

    
    def _extract_static_import_methods(self, class_content):
        """从类内容中提取静态导入的方法名"""
        static_import_methods = set()
        # 匹配静态导入语句: import static com.package.Class.methodName;
        static_import_pattern = r'import\s+static\s+[\w\.]+\.(\w+)\s*;'
        matches = re.finditer(static_import_pattern, class_content)
        for match in matches:
            method_name = match.group(1)
            static_import_methods.add(method_name)
        return static_import_methods