#!/usr/bin/env python3
import os
import re
import sys
import uuid
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

# 导入常量
try:
    from ..constants import UUID_SEPARATOR
except ImportError:
    from constants import UUID_SEPARATOR

# 导入日志模块
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from utils import get_logger

# 导入解析器模块
try:
    from .class_parser import ClassParser
    from .method_parser import MethodParser
    from .function_parser import FunctionParser
    from .variable_parser import VariableParser
    from .annotation_parser import AnnotationParser
except ImportError:
    from class_parser import ClassParser
    from method_parser import MethodParser
    from function_parser import FunctionParser
    from variable_parser import VariableParser
    from annotation_parser import AnnotationParser

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
        
        # 初始化日志记录器
        self.logger = get_logger("java_parser")
        
        # 初始化各个解析器
        self.class_parser = ClassParser()
        self.method_parser = MethodParser()
        self.function_parser = FunctionParser()
        self.variable_parser = VariableParser()
        self.annotation_parser = AnnotationParser()
    
    def find_files(self, directory: str):
        """查找所有Java文件，支持多层级目录和单个文件"""
        # 检查是否是单个文件
        if os.path.isfile(directory) and directory.endswith('.java'):
            self.java_files.append(directory)
            self.logger.info(f"添加单个Java文件: {directory}")
            return
        
        # 检查是否是目录
        if not os.path.isdir(directory):
            self.logger.warning(f"路径既不是文件也不是目录: {directory}")
            return
            
        # 遍历目录
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
                self.logger.warning(f"警告: 无法读取文件 {filepath}")
                return

        # 计算相对于项目根目录的相对路径，并统一路径分隔符
        if self.project_directory and os.path.isdir(self.project_directory):
            filename = os.path.relpath(filepath, self.project_directory)
            # 统一转换为正斜杠格式，确保跨平台一致性
            filename = filename.replace('\\', '/')
        else:
            filename = os.path.basename(filepath)

        try:
            # 解析Java文件中的各种元素
            self._parse_file_elements(source_code, filename)
            
        except Exception as e:
            self.logger.error(f"处理文件 {filepath} 时出错: {e}", exc_info=True)
    
    def _parse_file_elements(self, source_code: str, filename: str):
        """解析文件中的所有元素"""
                
        # 提取包名用于FQN
        package_name = None
        try:
            pkg_match = re.search(r'\bpackage\s+([\w\.]+)\s*;', source_code)
            if pkg_match:
                package_name = pkg_match.group(1)
        except Exception:
            package_name = None
        self.current_file_package = package_name
        # 1. 解析类和接口
        self._parse_classes_and_interfaces(source_code, filename)

        # 1.5 兜底：直接在文件级别扫描 Spring Mapping 注解的方法，避免极端格式导致漏检
        # 这些方法将直接作为 method_definition 注入 elements（后续分类流程会接受）
        try:
            self._extract_mapping_methods_from_file(source_code, filename)
        except Exception as e:
            self.logger.error(f"文件级Mapping方法兜底解析失败: {e}", exc_info=True)
        
        # 2. 解析包级别的注解
        self._parse_package_annotations(source_code, filename)
        
        # 3. 解析导入语句（如果需要的话）
        self._parse_imports(source_code, filename)
    
    def _parse_classes_and_interfaces(self, source_code: str, filename: str):
        """解析类和接口（改进版 - 支持更多Java语法形式）"""
        # 改进的类/接口/枚举/注解/record匹配模式
        # 支持多行声明、复杂泛型、多个接口、sealed/non-sealed、permits
        class_interface_pattern = r'''
            # 匹配完整的声明块
            (
                # Javadoc注释（可选）
                (?:/\*\*[\s\S]*?\*/\s*)?
                
                # 注解（可选，支持多行）
                (?:@\w+(?:\([^)]*\))?\s*)*
                
                # 访问修饰符和其他修饰符
                (?:(?:public|private|protected)\s+)?
                (?:(?:static|final|abstract|strictfp|sealed|non\-sealed)\s+)*
                
                # 声明类型关键字
                (class|interface|enum|@interface|record)\s+
                
                # 名称
                (\w+)
                
                # 泛型参数（可选，支持嵌套）
                (?:<[^<>]*(?:<[^<>]*>[^<>]*)*>)?
                
                # extends子句（可选，支持多行）
                (?:\s+extends\s+[^\{]+?)?
                
                # implements子句（可选，支持多行）
                (?:\s+implements\s+[^\{]+?)?
                
                # permits子句（可选）
                (?:\s+permits\s+[^\{]+?)?
                
                # 开始大括号
                \s*\{
            )
        '''
        
        matches = list(re.finditer(class_interface_pattern, source_code, re.VERBOSE | re.MULTILINE | re.DOTALL))
        
        for match in matches:
            element_type = match.group(2)  # class, interface, enum, @interface
            element_name = match.group(3)
            
            # 提取完整的声明内容
            element_content = self._extract_complete_element(source_code, match.start())
            
            if element_content:
                if element_type == 'class':
                    self._parse_single_class(element_content, filename)
                elif element_type == 'interface':
                    self._parse_single_interface(element_content, filename)
                elif element_type == 'enum':
                    self._parse_single_enum(element_content, filename)
                elif element_type == '@interface':
                    self._parse_single_annotation_definition(element_content, filename)
    
    def _extract_complete_element(self, source_code: str, start_pos: int) -> str:
        """提取完整的类/接口/枚举/注解/record 定义
        关键修复：精确定位声明块的首个 '{'，避免匹配到注解/参数中的花括号导致截断。
        """
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
            if (line.startswith('/**') or line.startswith('@') or 
                any(keyword in line for keyword in ['public', 'private', 'protected', 'class', 'interface', 'enum', '@interface'])):
                # 计算正确的行起始位置
                line_start = sum(len(lines[j]) + 1 for j in range(i))  # +1 for newline
                declaration_start = line_start
                break
        
        # 向后查找到类/接口结束（改进的大括号匹配）
        brace_count = 1  # 从1开始，因为我们在开始大括号后开始计数
        element_end = start_pos
        in_string = False
        in_char = False
        escape_next = False
        
        # 1) 在声明关键字之后定位第一个 '{' 作为块开始
        #    仅在 class|interface|enum|@interface|record 之后查找，以避免命中注解/方法参数中的花括号
        decl_pattern = r'(class|interface|enum|@interface|record)\s+\w[^\{]*\{'
        decl_match = re.search(decl_pattern, source_code[start_pos:], re.MULTILINE)
        brace_start = -1
        if decl_match:
            brace_start = start_pos + decl_match.end() - 1  # 指向 '{'
        else:
            # 回退策略：保持兼容，使用最近的 '{'，但这可能不准确
            brace_start = source_code.find('{', start_pos)
        
        if brace_start == -1:
            return source_code[declaration_start:start_pos + 100]  # 错误情况的回退
        
        # 从开始大括号后的位置开始计数
        for i in range(brace_start + 1, len(source_code)):
            char = source_code[i]
            
            if escape_next:
                escape_next = False
                continue
            
            if char == '\\':
                escape_next = True
                continue
            
            # 处理字符串字面量
            if char == '"' and not in_char:
                in_string = not in_string
                continue
            elif char == "'" and not in_string:
                in_char = not in_char
                continue
            
            # 只在非字符串上下文中计算大括号
            if not in_string and not in_char:
                if char == '{':
                    brace_count += 1
                elif char == '}':
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
            
            # 注入包名与FQN
            pkg = getattr(self, 'current_file_package', None)
            if pkg:
                class_info['package_name'] = pkg
                class_info['class_fqn'] = f"{pkg}.{class_info['name']}"
            else:
                class_info['package_name'] = None
                class_info['class_fqn'] = class_info['name']
            # 解析类中的方法（作为单独的元素存储）
            methods = class_info.get('methods', {})
            
            for method_key, method_info in methods.items():
                # 构建方法FQN（包.类#方法(签名)）
                signature = method_info.get('signature')
                cls_fqn = class_info.get('class_fqn', class_info.get('name'))
                if signature:
                    method_info['method_fqn'] = f"{cls_fqn}#{method_info['name']}{signature}"
                else:
                    method_info['method_fqn'] = f"{cls_fqn}#{method_info['name']}()"
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
            
            # 注入包名与FQN
            pkg = getattr(self, 'current_file_package', None)
            if pkg:
                interface_info['package_name'] = pkg
                interface_info['class_fqn'] = f"{pkg}.{interface_info['name']}"
            else:
                interface_info['package_name'] = None
                interface_info['class_fqn'] = interface_info['name']
            # 解析接口中的方法
            methods = interface_info.get('methods', {})
            for method_key, method_info in methods.items():
                signature = method_info.get('signature')
                cls_fqn = interface_info.get('class_fqn', interface_info.get('name'))
                if signature:
                    method_info['method_fqn'] = f"{cls_fqn}#{method_info['name']}{signature}"
                else:
                    method_info['method_fqn'] = f"{cls_fqn}#{method_info['name']}()"
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
            
            # 注入包名与FQN
            pkg = getattr(self, 'current_file_package', None)
            if pkg:
                enum_info['package_name'] = pkg
                enum_info['class_fqn'] = f"{pkg}.{enum_name}"
            else:
                enum_info['package_name'] = None
                enum_info['class_fqn'] = enum_name
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
    
    def _extract_mapping_methods_from_file(self, source_code: str, filename: str):
        """文件级兜底：提取带有Spring Mapping注解的方法，避免极端格式漏检"""
        try:
            # 首先提取所有静态导入的方法名，用于过滤
            static_import_methods = self._extract_static_import_methods(source_code)
            
            mapping_pattern = r'''
                (                                   # 1) 注解块
                    (?:
                        @[\w\.]*Mapping              # @XxxMapping 或全限定
                        \s*\([^)]*\)\s*
                    )+
                )
                ([\s\S]{0,300}?)                     # 2) 允许注解与签名之间有若干字符
                (                                    # 3) 方法签名整体
                    (?:(?:public|private|protected)\s+)?                                  # 访问修饰符（可选）
                    (?:(?:static|final|synchronized|native|abstract|strictfp|default)\s+)* # 其他修饰符
                    (?:<[^<>]*(?:<[^<>]*>[^<>]*)*>\s+)?                                   # 泛型方法参数（可选）
                    ([\w\.]+(?:<[^<>]*(?:<[^<>]*>[^<>]*)*>)?(?:\[\])*)\s+                 # 返回类型（捕获）
                    (\w+)\s*                                                               # 方法名（捕获）
                    \(([\s\S]*?)\)                                                         # 参数（捕获，允许跨行与嵌套括号）
                    (?:\s*throws\s+[^{;]+)?                                                # throws（可选）
                    \s*(\{|;)                                                              # 方法体开始或分号（捕获）
                )
            '''
            for m in re.finditer(mapping_pattern, source_code, re.VERBOSE | re.MULTILINE | re.DOTALL):
                # 基于上下文寻找最近的类名（向前查找）
                before = source_code[:m.start()]
                cls_match = None
                for cm in re.finditer(r'(class)\s+(\w+)\s*\{', before):
                    cls_match = cm
                class_name = None
                if cls_match:
                    class_name = cls_match.group(2)
                else:
                    # 若找不到，使用文件名去掉扩展名作为类名的保守猜测
                    class_name = (filename.split('/')[-1] if '/' in filename else filename).replace('.java', '')
                
                # 组索引修正：外层第(3)组是"整个方法签名"，内部捕获依次为
                # 4: 返回类型, 5: 方法名, 6: 参数, 7: 方法体开始符号
                return_type = m.group(4) or ""
                method_name = m.group(5)
                params_text = m.group(6) or ""
                body_start_char = m.group(7)
                
                # 过滤静态导入的方法名，防止误识别
                if method_name in static_import_methods:
                    self.logger.error(f"跳过静态导入方法: {method_name}", exc_info=True)
                    continue
                
                # 额外验证：确保真正有Mapping注解存在
                annotation_block = m.group(1)
                if not self._has_mapping_annotation(annotation_block):
                    continue
                
                # 去重：名称+行号
                start_line = self.class_parser.method_parser._calculate_line_number(source_code, m.start(4))
                key_tuple = (method_name, start_line)
                # 如果已经通过类解析加入，跳过
                already = False
                if method_name in self.name_to_uuid_map:
                    for key in self.name_to_uuid_map[method_name]:
                        el = self.elements.get(key, {})
                        if el.get('filename') == filename:
                            already = True
                            break
                if already:
                    continue
                
                # 提取完整方法体（若为 '{'）
                if body_start_char == '{':
                    brace_pos_in_sig = m.group(3).rfind('{')
                    if brace_pos_in_sig == -1:
                        continue
                    brace_abs_pos = m.start(3) + brace_pos_in_sig
                    method_body = self.class_parser.method_parser._extract_complete_method_body_from_position(source_code, brace_abs_pos)
                    if not method_body:
                        continue
                    method_full_text = source_code[m.start(3): brace_abs_pos + len(method_body)]
                else:
                    method_full_text = m.group(3)
                
                # 生成元素
                unique_id = str(uuid.uuid4())
                method_key = f"{method_name}{UUID_SEPARATOR}{unique_id}"
                method_info = {
                    "type": "method_definition",
                    "content": method_full_text,
                    "filename": filename,
                    "name": method_name,
                    "uuid": unique_id,
                    "class_name": class_name or "",
                    "return_type": return_type,
                    "params": self.class_parser.method_parser._parse_parameters(params_text),
                    "access_modifier": "public",
                    "is_static": False,
                    "is_final": False,
                    "is_synchronized": False,
                    "is_native": False,
                    "is_abstract": body_start_char != '{',
                    "other_modifiers": "",
                    "throws_clause": "",
                    "annotations": [],
                    "docstring": "",
                    "dependencies": self.class_parser.method_parser._extract_method_dependencies(method_full_text, method_name),
                    "signature": self.class_parser.method_parser._build_signature(return_type or "", self.class_parser.method_parser._parse_parameters(params_text)),
                    "lineno": start_line,
                    "end_lineno": self.class_parser.method_parser._calculate_line_number(source_code, m.start(3) + len(method_full_text)),
                }
                # 注入包名/FQN信息（若有）
                pkg = getattr(self, 'current_file_package', None)
                if pkg and class_name:
                    method_info['method_fqn'] = f"{pkg}.{class_name}#{method_name}{method_info['signature']}"
                
                self.elements[method_key] = method_info
                self._update_name_mapping(method_name, method_key)
        except Exception as e:
            self.logger.error(f"Mapping方法兜底解析异常: {e}", exc_info=True)
    
    def _extract_static_import_methods(self, source_code):
        """提取静态导入的方法名"""
        static_import_methods = set()
        # 匹配静态导入语句: import static com.package.Class.methodName;
        static_import_pattern = r'import\s+static\s+[\w\.]+\.(\w+)\s*;'
        matches = re.finditer(static_import_pattern, source_code)
        for match in matches:
            method_name = match.group(1)
            static_import_methods.add(method_name)
        return static_import_methods
    
    def _has_mapping_annotation(self, annotation_block):
        """验证注解块是否真的包含Mapping注解"""
        if not annotation_block:
            return False
        # 检查是否包含Spring的Mapping注解
        mapping_annotations = [
            'RequestMapping', 'GetMapping', 'PostMapping', 'PutMapping', 
            'DeleteMapping', 'PatchMapping', 'Mapping'
        ]
        for annotation in mapping_annotations:
            if '@' + annotation in annotation_block:
                return True
        return False
    
    def _update_name_mapping(self, element_name, element_key):
        """更新名称到UUID键的映射"""
        if element_name not in self.name_to_uuid_map:
            self.name_to_uuid_map[element_name] = []
        self.name_to_uuid_map[element_name].append(element_key)
    
    def parse_project(self, project_path: str) -> Dict[str, Any]:
        """解析整个Java项目"""
        self.project_directory = project_path
        self.find_files(project_path)
        
        self.logger.info(f"找到 {len(self.java_files)} 个Java文件")
        
        # 处理所有Java文件
        for filepath in self.java_files:
            self.logger.info(f"处理文件: {filepath}")
            self.process_file(filepath)
        
        # 更新所有dependencies中的名称为UUID键
        self._update_dependencies_with_uuids()
        
        self.logger.info(f"解析完成，共提取 {len(self.elements)} 个代码元素")
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
        """解析依赖名称为UUID（改进版 - 支持对象实例调用）"""
        # 直接查找完整名称
        if dep_name in self.name_to_uuid_map:
            uuid_keys = self.name_to_uuid_map[dep_name]
            if uuid_keys:
                return uuid_keys[0]  # 取第一个匹配的UUID
        
        # 处理类名.方法名或对象.方法名格式
        if '.' in dep_name:
            parts = dep_name.split('.')
            if len(parts) == 2:
                prefix, method_name = parts
                
                # 1. 首先尝试将前缀作为类名进行精确匹配
                if method_name in self.name_to_uuid_map:
                    method_uuid_keys = self.name_to_uuid_map[method_name]
                    
                    # 查找属于指定类的方法（精确匹配）
                    for uuid_key in method_uuid_keys:
                        element_info = self.elements.get(uuid_key)
                        if element_info and element_info.get('class_name') == prefix:
                            return uuid_key
                    
                    # 2. 如果精确匹配失败，尝试模糊匹配（处理对象实例调用）
                    # 例如：dbService.getAlarmForSubnet -> 查找所有getAlarmForSubnet方法
                    for uuid_key in method_uuid_keys:
                        element_info = self.elements.get(uuid_key)
                        if element_info:
                            class_name = element_info.get('class_name', '')
                            # 尝试通过类名模糊匹配（例如 dbService -> DbService, DatabaseService等）
                            if (class_name.lower() == prefix.lower() or 
                                class_name.lower().endswith(prefix.lower()) or
                                prefix.lower() in class_name.lower()):
                                return uuid_key
                    
                    # 3. 如果类名匹配失败，但方法名唯一，返回第一个匹配
                    # 这适用于像getAlarmForSubnet这样的特殊方法名
                    if len(method_uuid_keys) == 1:
                        return method_uuid_keys[0]
                    
                    # 4. 如果有多个同名方法，选择最相关的一个
                    # 可以根据文件路径、包名等进一步筛选
                    for uuid_key in method_uuid_keys:
                        element_info = self.elements.get(uuid_key)
                        if element_info:
                            filename = element_info.get('filename', '')
                            # 优先选择包含相关关键字的文件
                            if any(keyword in filename.lower() for keyword in ['service', 'dao', 'repository']):
                                return uuid_key
                    
                    # 5. 最后回退：返回第一个找到的方法
                    if method_uuid_keys:
                        return method_uuid_keys[0]
                
                # 如果没找到方法，尝试返回类的UUID（处理类名）
                if prefix in self.name_to_uuid_map:
                    class_uuid_keys = self.name_to_uuid_map[prefix]
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
        
        self.logger.info(f"重新构建映射表完成，包含 {len(self.name_to_uuid_map)} 个名称映射")
    
    def _update_dependencies_after_split(self, classified_elements: Dict[str, Dict[str, Any]]):
        """在拆分后重新解析所有依赖关系"""
        self.logger.info("开始重新解析Java依赖关系...")
        
        for element_type, elements_dict in classified_elements.items():
            for uuid_key, element_info in elements_dict.items():
                if 'dependencies' in element_info and element_info['dependencies']:
                    original_deps = element_info['dependencies']
                    updated_deps = self._convert_dependencies_to_uuid(original_deps)
                    element_info['dependencies'] = updated_deps
                    
                    if len(updated_deps) != len(original_deps):
                        self.logger.debug(f"  {element_info.get('name', 'Unknown')}: {len(original_deps)} -> {len(updated_deps)} 依赖")
        
        self.logger.info("Java依赖关系解析完成")
