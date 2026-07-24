#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import re
import json
import uuid
from pathlib import Path
from tree_sitter import Language, Parser
import tree_sitter_cpp as tscpp

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
    from .method_parser import MethodParser
    from .class_parser import ClassParser
    from .function_parser import FunctionParser
    from .variable_parser import VariableParser
except ImportError:
    from method_parser import MethodParser
    from class_parser import ClassParser
    from function_parser import FunctionParser
    from variable_parser import VariableParser

class CppParser:
    def __init__(self):
        self.language = Language(tscpp.language())
        self.parser = Parser(self.language)
        self.elements = {}
        self.header_files = []
        self.source_files = []
        self.class_methods = {}  # 存储类方法实现
        self.project_directory = None  # 添加项目根目录属性
        
        # 维护名称到UUID键的映射表 (参考Python解析器)
        self.name_to_uuid_map = {}
        
        # 存储分类后的元素，用于依赖解析
        self.classified_elements = {}
        
        # 初始化日志记录器
        self.logger = get_logger("cpp_parser")
        
        # 初始化各个解析器
        self.method_parser = MethodParser()
        self.class_parser = ClassParser()
        self.function_parser = FunctionParser()
        self.variable_parser = VariableParser()
        self._header_fallback_cache = {}
        self._struct_decl_pattern = re.compile(r'\b(struct|class)\s+([A-Za-z_]\w*)\s*\{', re.MULTILINE)

    def setup_parser(self):
        return self.parser

    def find_files(self, directory):
        """查找所有头文件和源文件，支持多层级目录"""
        self.logger.info(f"开始查找C++文件，根目录: {directory}")
        
        for root, dirs, files in os.walk(directory):
            # 跳过隐藏目录
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            
            for file in files:
                # 跳过隐藏文件
                if file.startswith('.'):
                    continue
                    
                file_path = os.path.join(root, file)
                if file.endswith(('.h', '.hpp')):
                    self.header_files.append(file_path)
                elif file.endswith(('.cpp', '.cc')):
                    self.source_files.append(file_path)
        
        self.logger.info(f"文件查找完成 - 头文件: {len(self.header_files)} 个, 源文件: {len(self.source_files)} 个")

    def merge_class_methods(self):
        """合并类声明和方法实现"""
        self.logger.info("开始合并类方法声明和实现...")
        merged_count = 0
        class_count = 0
        
        for class_key, class_info in self.elements.items():
            if class_info.get("type") == "class_definition":
                class_count += 1
                class_name = class_info.get("name")
                # 如果有对应的方法实现，进行合并
                if class_name and class_name in self.class_methods:
                    implementations = self.class_methods[class_name]
                    self.logger.debug(f"正在合并类 {class_name} 的方法实现，共 {len(implementations)} 个")
                    
                    # 更新方法信息 - 现在methods是字典格式
                    for method_key, method_info in class_info["methods"].items():
                        method_name = method_info["name"]
                        # 在实现中查找匹配的方法
                        for impl_method_key, impl_info in implementations.items():
                            if impl_info["name"] == method_name:
                                # 合并声明和实现
                                method_info["content"] = impl_info["content"]  # 使用实现的完整内容
                                method_info["filename"] = impl_info["filename"]  # 更新为实现文件
                                method_info["dependencies"] = impl_info.get("dependencies", [])  # 添加依赖关系
                                # 保留声明中的参数信息和访问限制，如果实现中有更详细的信息则更新
                                if impl_info["params"]:
                                    method_info["params"] = impl_info["params"]
                                if impl_info["elem_datatype"]:
                                    method_info["elem_datatype"] = impl_info["elem_datatype"]
                                # 保持访问限制信息，这个来自声明而不是实现
                                merged_count += 1
                                break
        
        self.logger.info(f"类方法合并完成 - 共处理 {class_count} 个类，合并 {merged_count} 个方法实现")

    def detect_encoding(self, filepath):
        """检测文件编码"""
        try:
            with open(filepath, 'rb') as f:
                raw_data = f.read()
            
            # 如果文件为空，直接返回
            if not raw_data:
                return 'utf-8', raw_data
                
            # 尝试常见编码，按优先级排序
            encodings_to_try = [
                'utf-8',        # 最常见的现代编码
                'gbk',          # 中文Windows系统常用
                'gb2312',       # 中文标准编码
                'utf-16',       # Unicode 16位编码
                'latin-1',      # 西欧编码，几乎不会失败
                'cp1252',       # Windows西欧编码
                'iso-8859-1'    # 标准西欧编码
            ]
            
            for encoding in encodings_to_try:
                try:
                    # 尝试解码整个文件
                    decoded_text = raw_data.decode(encoding)
                    
                    # 简单的编码质量检查：确保没有太多替换字符
                    replacement_count = decoded_text.count('\ufffd')
                    if replacement_count == 0:
                        return encoding, raw_data
                    elif replacement_count < len(decoded_text) * 0.01:  # 替换字符少于1%
                        return encoding, raw_data
                        
                except UnicodeDecodeError:
                    continue
            
            # 如果所有编码都失败，使用latin-1（几乎不会失败）
            return 'latin-1', raw_data
            
        except Exception as e:
            self.logger.error(f"Error detecting encoding for {filepath}: {e}")
            return 'utf-8', b''

    def process_file(self, filepath, is_header=False):
        """处理单个文件"""
        # 获取相对路径用于日志显示
        if self.project_directory:
            display_path = os.path.relpath(filepath, self.project_directory)
        else:
            display_path = os.path.basename(filepath)
        
        file_type = "头文件" if is_header else "源文件"
        self.logger.debug(f"正在处理{file_type}: {display_path}")
        
        try:
            encoding, raw_data = self.detect_encoding(filepath)
            self.logger.debug(f"  文件编码: {encoding}, 大小: {len(raw_data)} 字节")
            
            # 尝试使用检测到的编码解码
            try:
                source_text = raw_data.decode(encoding)
            except UnicodeDecodeError:
                # 如果解码失败，使用utf-8并忽略错误
                self.logger.warning(f"  解码失败，使用 UTF-8 备用方案: {display_path}")
                source_text = raw_data.decode('utf-8', errors='replace')
            
            # 将文本重新编码为utf-8字节给tree-sitter
            source_code = source_text.encode('utf-8')
            
        except Exception as e:
            self.logger.error(f"  读取文件失败: {display_path}, 错误: {e}")
            return
        
        tree = self.parser.parse(source_code)
        # 计算相对于项目根目录的相对路径，并统一路径分隔符
        if self.project_directory:
            filename = os.path.relpath(filepath, self.project_directory)
            # 统一转换为正斜杠格式，确保跨平台一致性
            filename = filename.replace('\\', '/')
        else:
            filename = os.path.basename(filepath)
        detected_structs = []

        def traverse_node(node, depth=0, inside_class=False):
            if node.type == 'function_definition' and not inside_class:
                function_key, info = self.function_parser.parse_function(node, source_code, filename)
                if function_key and info:
                    self.elements[function_key] = info
                # 处理类方法实现
                result = self.function_parser.parse_class_method_implementation(
                    node, source_code, filename, self.class_methods
                )
                if result is not None:
                    method_key, method_info = result
                    # 如果成功解析了类方法实现，将其添加到elements中
                    if method_key and method_info:
                        self.elements[method_key] = method_info
            elif node.type == 'declaration' and not is_header and depth == 1:
                var_key, info = self.variable_parser.parse_global_variable(node, source_code, filename)
                if var_key and info:
                    self.elements[var_key] = info
            elif node.type == 'preproc_def':
                macro_key, info = self.variable_parser.parse_macro(node, source_code, filename)
                if macro_key and info:
                    self.elements[macro_key] = info
            elif node.type == 'type_definition':
                typedef_key, info = self.variable_parser.parse_typedef_struct(node, source_code, filename)
                if typedef_key and info:
                    self.elements[typedef_key] = info
            elif node.type == 'struct_specifier' and not inside_class:
                # 处理直接定义的结构体（非typedef的struct）
                struct_key, info = self.variable_parser.parse_direct_struct(node, source_code, filename)
                if struct_key and info:
                    self.elements[struct_key] = info
            elif node.type == 'class_specifier':
                class_key, info = self.class_parser.parse_class(node, source_code, filename)
                if class_key and info:
                    self.elements[class_key] = info
                    detected_structs.append(info.get("name"))
                    
                    # 处理类内的方法
                    for method_key, method_info in info.get('methods', {}).items():
                        if method_info and method_info.get('name'):
                            method_info['filename'] = filename
                            method_info['class_key'] = class_key
                            method_info['type'] = 'method_definition'
                            self.elements[method_key] = method_info
                inside_class = True

            for child in node.children:
                traverse_node(child, depth + 1, inside_class)

        try:
            traverse_node(tree.root_node)
        except Exception as e:
            self.logger.error(f"Error parsing file {filename}: {e}")
            # 记录但不中断整个解析流程
            return

        # Fallback: parse header struct methods when tree-sitter missed them (e.g. due to macros)
        if is_header:
            fallback_methods = self._fallback_parse_header_methods(source_text, filename, detected_structs)
            for method_key, method_info in fallback_methods.items():
                if method_key not in self.elements:
                    self.elements[method_key] = method_info

    def _fallback_parse_header_methods(self, source_text, filename, detected_structs):
        """
        当 tree-sitter 因宏定义等原因无法解析头文件时，使用正则降级提取 struct/class 中的方法声明
        """
        results = {}
        existing_pairs = {
            (info.get("class_name"), info.get("name"))
            for info in self.elements.values()
            if info.get("type") == "method_definition"
        }

        for match in self._struct_decl_pattern.finditer(source_text):
            class_name = match.group(2)
            if detected_structs and class_name in detected_structs:
                # 已通过 tree-sitter 解析，无需降级处理
                continue
            body_start = match.end()
            body_end = self._find_matching_brace(source_text, body_start - 1)
            if body_end == -1:
                continue
            body = source_text[body_start:body_end - 1]
            method_candidate = self._extract_method_declarations(body)
            for snippet in method_candidate:
                method_info = {
                    "name": "",
                    "content": snippet,
                    "elem_datatype": "",
                    "params": [],
                    "dependencies": []
                }
                parsed = self.method_parser.parse_method_from_content(None, None, method_info)
                if not parsed or not parsed.get("name"):
                    continue
                method_name = parsed["name"]
                if (class_name, method_name) in existing_pairs:
                    continue
                parsed["filename"] = filename
                parsed["class_name"] = class_name
                parsed["type"] = "method_definition"
                parsed.setdefault("access_modifier", "public")
                parsed["is_inline"] = False
                parsed["is_static"] = "static" in snippet
                parsed["is_virtual"] = "virtual" in snippet
                parsed["is_override"] = "override" in snippet
                parsed["is_final"] = "final" in snippet
                parsed["is_template"] = "template" in snippet
                parsed["is_overloaded"] = False
                parsed["is_destructor"] = parsed.get("name", "").startswith("~")
                parsed["source_filenames"] = [filename]
                parsed["declaration_filename"] = filename
                parsed["implementation_filename"] = ""
                parsed["method_name"] = parsed["name"]
                parsed["uuid"] = str(uuid.uuid4())
                method_key = "{}{}{}".format(parsed["name"], UUID_SEPARATOR, parsed["uuid"])
                results[method_key] = parsed
                existing_pairs.add((class_name, method_name))

        return results

    def _find_matching_brace(self, text, start_index):
        depth = 0
        for index in range(start_index, len(text)):
            char = text[index]
            if char == '{':
                depth += 1
            elif char == '}':
                depth -= 1
                if depth == 0:
                    return index + 1
        return -1

    def _extract_method_declarations(self, body_text):
        """
        简单的分号拆分方式提取方法声明片段
        """
        snippets = []
        current = ""
        for segment in body_text.split(';'):
            if not segment.strip():
                continue
            current += segment
            if current.count('(') == current.count(')') and '(' in current:
                snippet = current.strip() + ';'
                snippets.append(snippet)
                current = ""
            else:
                current += ';'
        return snippets

    def _build_name_to_uuid_map(self):
        """构建名称到UUID键的映射表"""
        self.name_to_uuid_map = {}
        for uuid_key, element_info in self.elements.items():
            element_name = element_info.get('name', '')
            if element_name:
                if element_name not in self.name_to_uuid_map:
                    self.name_to_uuid_map[element_name] = []
                self.name_to_uuid_map[element_name].append(uuid_key)

    def _rebuild_name_to_uuid_map_after_split(self, classified_elements):
        """在方法分离后重建名称到UUID键的映射表"""
        self.name_to_uuid_map = {}
        
        # 遍历所有分类的元素
        for element_type, elements in classified_elements.items():
            for uuid_key, element_info in elements.items():
                element_name = element_info.get('name', '')
                if element_name:
                    if element_name not in self.name_to_uuid_map:
                        self.name_to_uuid_map[element_name] = []
                    self.name_to_uuid_map[element_name].append(uuid_key)

    def _resolve_dependency_to_uuid(self, dep_name):
        """解析依赖名称为UUID，处理各种调用格式"""
        # 1. 直接查找完整名称（函数名、类名、变量名、宏名）
        if dep_name in self.name_to_uuid_map:
            uuid_keys = self.name_to_uuid_map[dep_name]
            if uuid_keys:
                return uuid_keys[0]  # 取第一个匹配的UUID
        
        # 2. 处理类作用域调用 (Class::method)
        if '::' in dep_name:
            parts = dep_name.split('::')
            if len(parts) == 2:
                class_name, method_name = parts
                # 先查找方法名
                if method_name in self.name_to_uuid_map:
                    return self.name_to_uuid_map[method_name][0]
                # 再查找类名
                if class_name in self.name_to_uuid_map:
                    return self.name_to_uuid_map[class_name][0]
        
        # 3. 处理对象方法调用 (obj.method) - 只取方法名部分
        if '.' in dep_name:
            parts = dep_name.split('.')
            method_name = parts[-1]  # 取最后一部分作为方法名
            if method_name in self.name_to_uuid_map:
                return self.name_to_uuid_map[method_name][0]
        
        return None

    def _convert_dependencies_to_uuid(self, dependencies):
        """将依赖名称列表转换为UUID键列表"""
        updated_dependencies = []
        for dep_name in dependencies:
            # 如果已经是UUID键格式，直接保留
            if UUID_SEPARATOR in dep_name:
                if self._is_valid_uuid_key(dep_name):
                    updated_dependencies.append(dep_name)
                continue
            
            # 处理不同格式的依赖名称
            resolved_uuid = self._resolve_dependency_to_uuid(dep_name)
            # 只添加有UUID的依赖（项目内部元素），过滤掉外部库
            if resolved_uuid is not None:
                updated_dependencies.append(resolved_uuid)
        
        return updated_dependencies

    def _is_valid_uuid_key(self, uuid_key):
        """检查UUID键是否有效（在当前解析的元素中存在）"""
        return uuid_key in self.elements or any(
            uuid_key in elements_dict 
            for elements_dict in self.classified_elements.values()
        )

    def _update_dependencies_after_split(self, classified_elements):
        """在方法分离后更新所有elements中的dependencies"""
        self.logger.info("开始更新依赖关系...")
        
        # 创建字典的副本以避免在遍历时修改原字典
        elements_to_update = {}
        
        for element_type, elements_dict in classified_elements.items():
            for element_key, element_info in elements_dict.items():
                # 更新顶层元素的dependencies
                if 'dependencies' in element_info and element_info['dependencies']:
                    # 先收集需要更新的元素，避免在遍历时修改
                    elements_to_update[element_key] = {
                        'type': element_type,
                        'dependencies': element_info['dependencies']
                    }
        
        # 在遍历完成后进行更新
        total_deps = 0
        resolved_deps = 0
        for element_key, update_info in elements_to_update.items():
            element_type = update_info['type']
            old_dependencies = update_info['dependencies']
            new_dependencies = self._convert_dependencies_to_uuid(old_dependencies)
            classified_elements[element_type][element_key]['dependencies'] = new_dependencies
            
            total_deps += len(old_dependencies)
            resolved_deps += len(new_dependencies)
        
        self.logger.info(f"依赖关系更新完成 - 共 {len(elements_to_update)} 个元素，原始依赖 {total_deps} 个，解析成功 {resolved_deps} 个")

    def parse_project(self, directory):
        """解析整个项目"""
        # 设置项目根目录为绝对路径
        self.project_directory = os.path.abspath(directory)
        self.logger.info(f"项目根目录: {self.project_directory}")
        
        self.find_files(directory)
        
        # 先处理头文件
        total_headers = len(self.header_files)
        self.logger.info(f"开始处理 {total_headers} 个头文件...")
        for idx, header in enumerate(self.header_files, 1):
            if idx % 10 == 0 or idx == total_headers:
                self.logger.info(f"  进度: {idx}/{total_headers} 头文件")
            self.process_file(header, is_header=True)
        
        # 再处理源文件
        total_sources = len(self.source_files)
        self.logger.info(f"开始处理 {total_sources} 个源文件...")
        for idx, source in enumerate(self.source_files, 1):
            if idx % 10 == 0 or idx == total_sources:
                self.logger.info(f"  进度: {idx}/{total_sources} 源文件")
            self.process_file(source, is_header=False)

        # 合并类方法声明和实现
        self.merge_class_methods()
        
        # 构建名称到UUID键的映射表
        self.logger.info("构建名称到UUID映射表...")
        self._build_name_to_uuid_map()
        
        # 分类元素
        self.classified_elements = {
            'function_definition': {},
            'class_definition': {},
            'method_definition': {},
            'global_variable': {},
            'macro_definition': {},
            'type_definition': {}
        }
        
        for key, info in self.elements.items():
            element_type = info.get('type')
            if element_type in self.classified_elements:
                self.classified_elements[element_type][key] = info
        
        self.logger.info(f"Found {len(self.elements)} total elements")
        self.logger.info(f"Name to UUID mapping contains {len(self.name_to_uuid_map)} unique names")
        
        # 打印分类统计
        self.logger.info("解析结果统计:")
        self.logger.info(f"  函数数量: {len(self.classified_elements['function_definition'])}")
        self.logger.info(f"  类数量: {len(self.classified_elements['class_definition'])}")
        self.logger.info(f"  方法数量: {len(self.classified_elements['method_definition'])}")
        self.logger.info(f"  全局变量数量: {len(self.classified_elements['global_variable'])}")
        self.logger.info(f"  宏定义数量: {len(self.classified_elements['macro_definition'])}")
        self.logger.info(f"  类型定义数量: {len(self.classified_elements['type_definition'])}")

        return self.elements 