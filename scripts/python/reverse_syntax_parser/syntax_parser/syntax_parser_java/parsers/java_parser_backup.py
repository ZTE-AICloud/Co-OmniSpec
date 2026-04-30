#!/usr/bin/env python3
import os
import re
import uuid
from typing import Dict, List, Any, Optional, Tuple
from ..constants import UUID_SEPARATOR

from src.infrastructure.logging.task_log import get_skill_logger

try:
    from skills.syntax_parser_java.parsers.class_parser import ClassParser
    from skills.syntax_parser_java.parsers.method_parser import MethodParser
    from skills.syntax_parser_java.parsers.function_parser import FunctionParser
    from skills.syntax_parser_java.parsers.variable_parser import VariableParser
    from skills.syntax_parser_java.parsers.annotation_parser import AnnotationParser
except ImportError:
    # 相对导入，用于直接运行时
    from .class_parser import ClassParser
    from .method_parser import MethodParser
    from .function_parser import FunctionParser
    from .variable_parser import VariableParser
    from .annotation_parser import AnnotationParser

class JavaParser:
    """Java主解析器"""
    
    def __init__(self):
        self.elements = {}
        self.java_files = []
        self.project_directory = None
        
        # 维护名称到UUID键的映射表
        self.name_to_uuid_map = {}
        
        # 存储分类后的元素，用于依赖解析
        self.classified_elements = {}
        
        # 初始化各个解析器
        self.class_parser = ClassParser()
        self.method_parser = MethodParser()
        self.function_parser = FunctionParser()
        self.variable_parser = VariableParser()
        self.annotation_parser = AnnotationParser()
    
    def find_files(self, directory: str):
        """查找所有Java文件，支持多层级目录"""
        for root, dirs, files in os.walk(directory):
            # 跳过隐藏目录和常见的构建目录
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['target', 'build', 'out', 'bin']]
            
            for file in files:
                # 跳过隐藏文件
                if file.startswith('.'):
                    continue
                    
                file_path = os.path.join(root, file)
                if file.endswith('.java'):
                    self.java_files.append(file_path)
    
    def process_file(self, filepath: str):
        """处理单个Java文件"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                source_code = f.read()
        except UnicodeDecodeError:
            # 尝试其他编码
            try:
                with open(filepath, 'r', encoding='gbk') as f:
                    source_code = f.read()
            except:
                get_skill_logger(__name__).warning(f"警告: 无法读取文件 {filepath}")
                return

        # 计算相对于项目根目录的相对路径，并统一路径分隔符
        if self.project_directory:
            filename = os.path.relpath(filepath, self.project_directory)
            # 统一转换为正斜杠格式，确保跨平台一致性
            filename = filename.replace('\\', '/')
        else:
            filename = os.path.basename(filepath)

        try:
            # 解析Java文件中的各种元素
            self._parse_file_elements(source_code, filename)
            
        except Exception as e:
            get_skill_logger(__name__).error(f"处理文件 {filepath} 时出错: {e}")
    
    def _parse_file_elements(self, source_code: str, filename: str):
        """解析文件中的所有元素"""
        # 1. 解析类和接口
        self._parse_classes_and_interfaces(source_code, filename)
        
        # 2. 解析包级别的注解
        self._parse_package_annotations(source_code, filename)
        
        # 3. 解析导入语句（如果需要的话）
        self._parse_imports(source_code, filename)
    
    def _parse_classes_and_interfaces(self, source_code: str, filename: str):
        """解析类和接口"""
        # 找到所有顶级类和接口
        class_interface_pattern = r'''
            (?:^|\n)\s*                                 # 行开始
            (?:/\*\*[\s\S]*?\*/\s*)?                    # 可选Javadoc
            (?:@\w+(?:\([^)]*\))?\s*\n?\s*)*            # 注解
            (?:public\s+|private\s+|protected\s+)?      # 访问修饰符
            (?:static\s+|final\s+|abstract\s+)*         # 其他修饰符
            (class|interface|enum|@interface)\s+        # 类型关键字
            (\w+)                                       # 名称
            (?:<[^>]+>)?                               # 可选泛型
            (?:\s+extends\s+[^{]+?)?                   # 可选extends
            (?:\s+implements\s+[^{]+?)?                # 可选implements
            \s*\{                                      # 开始大括号
        '''
        
        matches = list(re.finditer(class_interface_pattern, source_code, re.VERBOSE | re.MULTILINE))
        
        for match in matches:
            element_type = match.group(1)  # class, interface, 或 enum
            element_name = match.group(2)
            
            # 检查是否已经存在同名元素（避免重复解析内部类）
            existing_keys = [key for key in self.elements.keys() if key.startswith(f"{element_name}{UUID_SEPARATOR}")]
            if existing_keys:
                # 如果已经存在同名元素，跳过重复解析
                continue
            
            # 提取完整的类/接口内容
            element_content = self._extract_complete_element(source_code, match.start())
            
            if element_type == 'class':
                self._parse_single_class(element_content, filename)
            elif element_type == 'interface':
                self._parse_single_interface(element_content, filename)
            elif element_type == 'enum':
                self._parse_single_enum(element_content, filename)
            elif element_type == '@interface':
                self._parse_single_annotation_definition(element_content, filename)
    
    def _extract_complete_element(self, source_code: str, start_pos: int) -> str:
        """提取完整的类/接口/枚举定义"""
        # 向前查找到声明开始（包括注解和注释）
        lines = source_code[:start_pos].split('\n')
        declaration_start = start_pos
        
        # 向前查找包含注解、注释的完整声明
        for i in range(len(lines) - 1, -1, -1):
            line = lines[i].strip()
            if not line:
                continue
            if line.startswith('package ') or line.startswith('import ') or line.endswith(';'):
                break
            if line.startswith('/**') or line.startswith('@') or any(keyword in line for keyword in ['public', 'private', 'protected', 'class', 'interface', 'enum', '@interface']):
                # 计算正确的行起始位置
                line_start = sum(len(lines[j]) + 1 for j in range(i))  # +1 for newline
                declaration_start = line_start
                break
        
        # 向后查找到类/接口结束
        brace_count = 0
        element_end = start_pos
        
        brace_start = source_code.find('{', start_pos)
        if brace_start == -1:
            return source_code[declaration_start:start_pos + 100]  # 错误情况的回退
        
        for i in range(brace_start, len(source_code)):
            if source_code[i] == '{':
                brace_count += 1
            elif source_code[i] == '}':
                brace_count -= 1
                if brace_count == 0:
                    element_end = i + 1
                    break
        
        return source_code[declaration_start:element_end]
    
    def _parse_single_class(self, class_content: str, filename: str):
        """解析单个类"""
        class_key, class_info = self.class_parser.parse_class(class_content, filename)
        
        if class_key and class_info:
            self.elements[class_key] = class_info
            self._update_name_mapping(class_info['name'], class_key)
            
            # 解析类中的方法（作为单独的元素存储）
            methods = class_info.get('methods', {})
            for method_key, method_info in methods.items():
                self.elements[method_key] = method_info
                self._update_name_mapping(method_info['name'], method_key)
            
            # 解析类中的字段变量
            field_variables = self.variable_parser.parse_field_variables(class_content, class_info['name'], filename)
            for var_key, var_info in field_variables.items():
                self.elements[var_key] = var_info
                self._update_name_mapping(var_info['name'], var_key)
            
            # 注意：静态方法已经在上面的 methods 中包含了，不需要重复解析
            
            # 解析注解
            annotations = self.annotation_parser.extract_all_annotations_from_file(class_content, filename)
            for annotation_key, annotation_info in annotations.items():
                self.elements[annotation_key] = annotation_info
                self._update_name_mapping(annotation_info['name'], annotation_key)
    
    def _parse_single_interface(self, interface_content: str, filename: str):
        """解析单个接口"""
        interface_key, interface_info = self.class_parser.parse_interface(interface_content, filename)
        
        if interface_key and interface_info:
            self.elements[interface_key] = interface_info
            self._update_name_mapping(interface_info['name'], interface_key)
            
            # 解析接口中的方法
            methods = interface_info.get('methods', {})
            for method_key, method_info in methods.items():
                self.elements[method_key] = method_info
                self._update_name_mapping(method_info['name'], method_key)
            
            # 解析接口中的常量
            constants = interface_info.get('constants', {})
            for const_key, const_info in constants.items():
                self.elements[const_key] = const_info
                self._update_name_mapping(const_info['name'], const_key)
    
    def _parse_single_enum(self, enum_content: str, filename: str):
        """解析枚举（简化处理，作为特殊的类）"""
        # 枚举模式
        enum_pattern = r'''
            ((?:/\*\*[\s\S]*?\*/\s*)?                   # 可选Javadoc
            (?:@\w+(?:\([^)]*\))?\s*\n?\s*)*)           # 注解
            ((?:public|private|protected)\s+)?          # 访问修饰符
            enum\s+                                     # enum关键字
            (\w+)                                       # 枚举名
            (?:\s+implements\s+[^{]+?)?                # 可选接口实现
            \s*\{                                      # 枚举体开始
        '''
        
        match = re.search(enum_pattern, enum_content, re.VERBOSE | re.MULTILINE)
        
        if match:
            javadoc = self.class_parser._extract_javadoc(match.group(1) or "")
            annotations_text = match.group(1) or ""
            access_modifier = (match.group(2) or "package").strip()
            enum_name = match.group(3)
            
            # 生成唯一ID
            unique_id = str(uuid.uuid4())
            enum_key = f"{enum_name}{UUID_SEPARATOR}{unique_id}"
            
            enum_info = {
                "type": "enum_definition",
                "content": enum_content,
                "filename": filename,
                "name": enum_name,
                "uuid": unique_id,
                "access_modifier": access_modifier.replace(" ", "") if access_modifier else "package",
                "docstring": javadoc,
                "annotations": self.class_parser._parse_class_annotations(annotations_text),
                "enum_values": self._parse_enum_values(enum_content),
                "dependencies": [],
                "lineno": self.class_parser._calculate_line_number(enum_content, match.start()),
                "end_lineno": self.class_parser._calculate_line_number(enum_content, match.start() + len(enum_content))
            }
            
            self.elements[enum_key] = enum_info
            self._update_name_mapping(enum_name, enum_key)
    
    def _parse_single_annotation_definition(self, annotation_content: str, filename: str):
        """解析注解定义"""
        # 注解定义模式
        annotation_pattern = r'''
            ((?:/\*\*[\s\S]*?\*/\s*)?                   # 可选Javadoc
            (?:@\w+(?:\([^)]*\))?\s*\n?\s*)*)           # 元注解
            ((?:public|private|protected)\s+)?          # 访问修饰符
            @interface\s+                               # @interface关键字
            (\w+)                                       # 注解名
            \s*\{                                      # 注解体开始
        '''
        
        match = re.search(annotation_pattern, annotation_content, re.VERBOSE | re.MULTILINE)
        
        if match:
            javadoc = self.class_parser._extract_javadoc(annotation_content)
            annotations_text = match.group(1) or ""
            access_modifier = (match.group(2) or "package").strip()
            annotation_name = match.group(3)
            
            # 生成唯一ID
            unique_id = str(uuid.uuid4())
            annotation_key = f"{annotation_name}{UUID_SEPARATOR}{unique_id}"
            
            annotation_info = {
                "type": "annotation_definition",
                "content": annotation_content,
                "filename": filename,
                "name": annotation_name,
                "uuid": unique_id,
                "access_modifier": access_modifier.replace(" ", "") if access_modifier else "package",
                "docstring": javadoc,
                "meta_annotations": self.class_parser._parse_class_annotations(annotations_text),
                "annotation_methods": self._parse_annotation_methods(annotation_content),
                "dependencies": [],
                "lineno": self.class_parser._calculate_line_number(annotation_content, match.start()),
                "end_lineno": self.class_parser._calculate_line_number(annotation_content, match.start() + len(annotation_content))
            }
            
            self.elements[annotation_key] = annotation_info
            self._update_name_mapping(annotation_name, annotation_key)
    
    def _parse_annotation_methods(self, annotation_content: str) -> Dict[str, Any]:
        """解析注解中的方法（属性）"""
        methods = {}
        
        # 注解方法模式
        method_pattern = r'(\w+(?:<[^>]*>)?(?:\[\])?)\s+(\w+)\s*\(\s*\)(?:\s+default\s+([^;]+))?;'
        matches = re.finditer(method_pattern, annotation_content)
        
        for match in matches:
            return_type = match.group(1)
            method_name = match.group(2)
            default_value = match.group(3).strip() if match.group(3) else None
            
            unique_id = str(uuid.uuid4())
            method_key = f"{method_name}{UUID_SEPARATOR}{unique_id}"
            
            methods[method_key] = {
                "name": method_name,
                "return_type": return_type,
                "default_value": default_value,
                "uuid": unique_id
            }
        
        return methods
    
    def _parse_enum_values(self, enum_content: str) -> List[str]:
        """解析枚举值"""
        enum_values = []
        
        # 查找枚举体
        body_start = enum_content.find('{')
        body_end = enum_content.rfind('}')
        
        if body_start != -1 and body_end != -1:
            enum_body = enum_content[body_start + 1:body_end]
            
            # 查找枚举值（通常在第一个分号之前）
            semicolon_pos = enum_body.find(';')
            if semicolon_pos != -1:
                values_section = enum_body[:semicolon_pos]
            else:
                values_section = enum_body
            
            # 提取枚举值
            value_pattern = r'([A-Z_][A-Z0-9_]*)\s*(?:\([^)]*\))?'
            matches = re.finditer(value_pattern, values_section)
            
            for match in matches:
                enum_values.append(match.group(1))
        
        return enum_values
    
    def _parse_package_annotations(self, source_code: str, filename: str):
        """解析包级别的注解"""
        package_annotation_pattern = r'''
            ^@\w+(?:\([^)]*\))?\s*\n
            package\s+[\w.]+\s*;
        '''
        
        matches = re.finditer(package_annotation_pattern, source_code, re.MULTILINE | re.VERBOSE)
        
        for match in matches:
            annotation_text = match.group(0)
            annotations = self.annotation_parser.extract_annotations_from_text(annotation_text)
            
            for annotation in annotations:
                unique_id = str(uuid.uuid4())
                annotation_key = f"package_annotation_{annotation['name']}{UUID_SEPARATOR}{unique_id}"
                
                annotation_info = {
                    "type": "annotation_definition",
                    "target_type": "package",
                    "filename": filename,
                    "name": f"package_annotation_{annotation['name']}",
                    "uuid": unique_id,
                    "annotations": [annotation],
                    "content": annotation_text.strip()
                }
                
                self.elements[annotation_key] = annotation_info
                self._update_name_mapping(annotation_info['name'], annotation_key)
    
    def _parse_imports(self, source_code: str, filename: str):
        """解析导入语句"""
        import_pattern = r'import\s+(?:static\s+)?([^;]+)\s*;'
        matches = re.finditer(import_pattern, source_code)
        
        for match in matches:
            import_path = match.group(1).strip()
            
            # 提取导入的名称（最后一部分）
            if import_path.endswith('*'):
                # 通配符导入，使用包名的最后部分
                import_name = import_path.split('.')[-2] if '.' in import_path else import_path.replace('*', '').strip()
            else:
                # 具体类导入，使用类名
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
                "is_wildcard": import_path.endswith('*'),
                "lineno": self.class_parser._calculate_line_number(source_code, match.start())
            }
            
            self.elements[import_key] = import_info
            self._update_name_mapping(import_info['name'], import_key)
    
    def _update_name_mapping(self, element_name: str, element_key: str):
        """更新名称到UUID键的映射"""
        if element_name not in self.name_to_uuid_map:
            self.name_to_uuid_map[element_name] = []
        self.name_to_uuid_map[element_name].append(element_key)
    
    def parse_project(self, project_path: str) -> Dict[str, Any]:
        """解析整个Java项目"""
        self.project_directory = project_path
        self.find_files(project_path)
        
        get_skill_logger(__name__).info(f"找到 {len(self.java_files)} 个Java文件")
        
        # 处理所有Java文件
        for filepath in self.java_files:
            get_skill_logger(__name__).info(f"处理文件: {filepath}")
            self.process_file(filepath)
        
        # 更新所有dependencies中的名称为UUID键
        self._update_dependencies_with_uuids()
        
        get_skill_logger(__name__).info(f"解析完成，共提取 {len(self.elements)} 个代码元素")
        return self.elements
    
    def _update_dependencies_with_uuids(self):
        """更新所有elements中的dependencies，将名称替换为UUID键"""
        for element_key, element_info in self.elements.items():
            if 'dependencies' in element_info and element_info['dependencies']:
                element_info['dependencies'] = self._convert_dependencies_to_uuid(element_info['dependencies'])
    
    def _convert_dependencies_to_uuid(self, dependencies: List[str]) -> List[str]:
        """将依赖名称列表转换为UUID键列表"""
        updated_dependencies = []
        
        for dep_name in dependencies:
            # 如果已经是UUID键格式，直接保留
            if UUID_SEPARATOR in dep_name:
                updated_dependencies.append(dep_name)
                continue
            
            # 查找对应的UUID键
            resolved_uuid = self._resolve_dependency_to_uuid(dep_name)
            if resolved_uuid:
                updated_dependencies.append(resolved_uuid)
        
        return updated_dependencies
    
    def _resolve_dependency_to_uuid(self, dep_name: str) -> Optional[str]:
        """解析依赖名称为UUID"""
        # 直接查找完整名称
        if dep_name in self.name_to_uuid_map:
            uuid_keys = self.name_to_uuid_map[dep_name]
            if uuid_keys:
                return uuid_keys[0]  # 取第一个匹配的UUID
        
        # 处理类名.方法名格式
        if '.' in dep_name:
            parts = dep_name.split('.')
            if len(parts) == 2:
                class_name, method_name = parts
                
                # 查找方法名
                if method_name in self.name_to_uuid_map:
                    method_uuid_keys = self.name_to_uuid_map[method_name]
                    # 查找属于指定类的方法
                    for uuid_key in method_uuid_keys:
                        element_info = self.elements.get(uuid_key)
                        if element_info and element_info.get('class_name') == class_name:
                            return uuid_key
                
                # 如果没找到方法，返回类的UUID
                if class_name in self.name_to_uuid_map:
                    class_uuid_keys = self.name_to_uuid_map[class_name]
                    if class_uuid_keys:
                        return class_uuid_keys[0]
        
        return None
    
    def _rebuild_name_to_uuid_map_after_split(self, classified_elements: Dict[str, Dict[str, Any]]):
        """重新构建名称到UUID的映射表"""
        self.name_to_uuid_map = {}
        self.classified_elements = classified_elements
        
        for element_type, elements_dict in classified_elements.items():
            for uuid_key, element_info in elements_dict.items():
                element_name = element_info.get('name')
                if element_name:
                    if element_name not in self.name_to_uuid_map:
                        self.name_to_uuid_map[element_name] = []
                    self.name_to_uuid_map[element_name].append(uuid_key)
        
        get_skill_logger(__name__).info(f"重新构建映射表完成，包含 {len(self.name_to_uuid_map)} 个名称映射")
    
    def _update_dependencies_after_split(self, classified_elements: Dict[str, Dict[str, Any]]):
        """在拆分后重新解析所有依赖关系"""
        get_skill_logger(__name__).info("开始重新解析Java依赖关系...")
        
        for element_type, elements_dict in classified_elements.items():
            for uuid_key, element_info in elements_dict.items():
                if 'dependencies' in element_info and element_info['dependencies']:
                    original_deps = element_info['dependencies']
                    updated_deps = self._convert_dependencies_to_uuid(original_deps)
                    element_info['dependencies'] = updated_deps
                    
                    if len(updated_deps) != len(original_deps):
                        get_skill_logger(__name__).info(f"  {element_info.get('name', 'Unknown')}: {len(original_deps)} -> {len(updated_deps)} 依赖")
        
        get_skill_logger(__name__).info("Java依赖关系解析完成")
