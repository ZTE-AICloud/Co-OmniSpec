#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import json
import uuid
import re
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from multiprocessing import cpu_count
from tree_sitter import Language, Parser
import tree_sitter_c as tsc

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
    from .function_parser import FunctionParser
    from .variable_parser_c import VariableParser
    from .macro_parser import MacroParser
    from .type_parser import TypeParser
except ImportError:
    from function_parser import FunctionParser
    from variable_parser_c import VariableParser
    from macro_parser import MacroParser
    from type_parser import TypeParser

class CParser:
    def __init__(self):
        self.language = Language(tsc.language())
        self.parser = Parser(self.language)
        self.elements = {}
        self.header_files = []
        self.source_files = []
        self.project_directory = None
        
        # 维护名称到UUID键的映射表
        self.name_to_uuid_map = {}
        
        # 存储分类后的元素，用于依赖解析
        self.classified_elements = {}
        
        # 初始化日志记录器
        self.logger = get_logger("c_parser")
        
        # 初始化各个解析器 - C语言版本，不包含类和方法解析器
        self.function_parser = FunctionParser()
        self.variable_parser = VariableParser()
        self.macro_parser = MacroParser()
        self.type_parser = TypeParser()
        self.function_like_macros = ["UPF_HELP_REG"]

    def setup_parser(self):
        return self.parser

    def find_files(self, directory):
        """查找所有C语言头文件和源文件，支持多层级目录"""
        for root, dirs, files in os.walk(directory):
            # 跳过隐藏目录
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            
            for file in files:
                file_path = os.path.join(root, file)
                if file.endswith('.h'):
                    self.header_files.append(file_path)
                elif file.endswith('.c'):
                    self.source_files.append(file_path)

    def parse_file(self, file_path):
        """解析单个C语言文件"""
        try:
            # 使用相对于项目根目录的路径
            if self.project_directory:
                relative_path = os.path.relpath(file_path, self.project_directory)
            else:
                relative_path = file_path
            
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                source_code = file.read()
            
            source_code = self._preprocess_source_code(source_code)
            
            tree = self.parser.parse(bytes(source_code, 'utf8'))
            root_node = tree.root_node
            
            # 解析各种C语言元素
            self._parse_functions(root_node, source_code, relative_path)
            self._parse_variables(root_node, source_code, relative_path)
            self._parse_macros(root_node, source_code, relative_path)
            self._parse_types(root_node, source_code, relative_path)
            
        except Exception as e:
            self.logger.error(f"解析文件 {file_path} 时出错: {e}", exc_info=True)

    def _parse_functions(self, root_node, source_code, file_path):
        """解析函数定义"""
        query = self.language.query("""
        (function_definition) @function
        """)
        
        captures = query.captures(root_node)
        for capture_name, nodes in captures.items():
            for node in nodes:
                try:
                    function_info = self.function_parser.parse_function(node, source_code, file_path)
                    if function_info:
                        # 生成UUID键
                        function_name = function_info.get('name', 'unknown')
                        unique_id = str(uuid.uuid4())
                        uuid_key = f"{function_name}{UUID_SEPARATOR}{unique_id}"
                        
                        function_info['uuid'] = unique_id
                        function_info['type'] = 'function_definition'
                        
                        self.elements[uuid_key] = function_info
                        self.name_to_uuid_map[function_name] = uuid_key
                        
                except Exception as e:
                    self.logger.error(f"解析函数时出错: {e}", exc_info=True)

    def _parse_variables(self, root_node, source_code, file_path):
        """解析全局变量"""
        query = self.language.query("""
        (declaration) @declaration
        """)
        
        captures = query.captures(root_node)
        for capture_name, nodes in captures.items():
            if capture_name == "declaration":
                for declaration_node in nodes:
                    try:
                        # 检查是否为全局变量（不在函数内部）
                        parent = declaration_node.parent
                        while parent:
                            if parent.type == 'function_definition':
                                break
                            parent = parent.parent
                        else:
                            # 这是全局变量
                            variable_info = self.variable_parser.parse_variable(declaration_node, source_code, file_path)
                            if variable_info:
                                # 使用变量名作为键
                                variable_name = variable_info.get('name', 'unknown')
                                
                                self.elements[variable_name] = variable_info
                                self.name_to_uuid_map[variable_name] = variable_name
                                    
                    except Exception as e:
                        self.logger.error(f"解析变量时出错: {e}", exc_info=True)

    def _parse_macros(self, root_node, source_code, file_path):
        """解析宏定义"""
        query = self.language.query("""
        (preproc_def
          name: (identifier) @macro_name
        ) @macro
        """)
        
        captures = query.captures(root_node)
        for capture_name, nodes in captures.items():
            if capture_name == "macro":
                for node in nodes:
                    try:
                        macro_info = self.macro_parser.parse_macro(node, source_code, file_path)
                        if macro_info:
                            # 生成UUID键
                            macro_name = macro_info.get('name', 'unknown')
                            unique_id = str(uuid.uuid4())
                            uuid_key = f"{macro_name}{UUID_SEPARATOR}{unique_id}"
                            
                            macro_info['uuid'] = unique_id
                            macro_info['type'] = 'macro_definition'
                            
                            self.elements[uuid_key] = macro_info
                            self.name_to_uuid_map[macro_name] = uuid_key
                            
                    except Exception as e:
                        self.logger.error(f"解析宏时出错: {e}", exc_info=True)

    def _parse_types(self, root_node, source_code, file_path):
        """解析类型定义（struct, union, typedef等）"""
        # 解析结构体定义
        struct_query = self.language.query("""
        (struct_specifier) @struct
        """)
        
        captures = struct_query.captures(root_node)
        for capture_name, nodes in captures.items():
            if capture_name == "struct":
                for node in nodes:
                    try:
                        type_info = self.type_parser.parse_struct(node, source_code, file_path)
                        if type_info:
                            # 生成UUID键
                            type_name = type_info.get('name', 'unknown')
                            unique_id = str(uuid.uuid4())
                            uuid_key = f"{type_name}{UUID_SEPARATOR}{unique_id}"
                            
                            type_info['uuid'] = unique_id
                            type_info['type'] = 'type_definition'
                            
                            self.elements[uuid_key] = type_info
                            self.name_to_uuid_map[type_name] = uuid_key
                            
                    except Exception as e:
                        self.logger.error(f"解析结构体时出错: {e}", exc_info=True)
        
        # 解析typedef定义
        typedef_query = self.language.query("""
        (type_definition) @typedef
        """)
        
        captures = typedef_query.captures(root_node)
        for capture_name, nodes in captures.items():
            if capture_name == "typedef":
                for node in nodes:
                    try:
                        type_info = self.type_parser.parse_typedef(node, source_code, file_path)
                        if type_info:
                            # 从typedef内容中提取类型名称
                            type_name = self._extract_typedef_name(node, source_code)
                            if type_name:
                                unique_id = str(uuid.uuid4())
                                uuid_key = f"{type_name}{UUID_SEPARATOR}{unique_id}"
                                
                                self.elements[uuid_key] = type_info
                                self.name_to_uuid_map[type_name] = uuid_key
                            
                    except Exception as e:
                        self.logger.error(f"解析typedef时出错: {e}", exc_info=True)

    def _extract_typedef_name(self, node, source_code):
        """从typedef节点中提取类型名称"""
        try:
            source_bytes = source_code.encode('utf-8')
            for child in node.children:
                if child.type == 'type_identifier':
                    name_bytes = source_bytes[child.start_byte:child.end_byte]
                    return name_bytes.decode('utf-8', errors='ignore').strip()
            return None
        except:
            return None

    def parse_project(self, project_path):
        """解析整个C语言项目"""
        self.project_directory = os.path.abspath(project_path)
        self.logger.info(f"开始解析C语言项目: {self.project_directory}")
        
        # 查找所有C语言文件
        self.find_files(project_path)
        
        self.logger.info(f"找到 {len(self.header_files)} 个头文件")
        self.logger.info(f"找到 {len(self.source_files)} 个源文件")
        
        # 解析所有文件
        all_files = self.header_files + self.source_files
        for file_path in all_files:
            self.logger.info(f"正在解析: {file_path}")
            self.parse_file(file_path)
        
        self.logger.info(f"解析完成，共找到 {len(self.elements)} 个元素")
        
        return self.elements

    def _preprocess_source_code(self, source_code):
        """
        Expand known macros that wrap function definitions into plain function declarations
        so tree-sitter can parse them correctly.
        """
        processed = source_code
        for macro_name in self.function_like_macros:
            processed = self._replace_macro_function_signature(processed, macro_name)
        processed = self._strip_gnu_attributes(processed)
        return processed

    def _replace_macro_function_signature(self, source_code, macro_name):
        """
        Replace occurrences of MACRO_NAME(arg1, arg2, <function signature>) with the function signature.
        """
        pattern = re.compile(rf'\b{re.escape(macro_name)}\b')
        result = []
        search_pos = 0
        length = len(source_code)

        while search_pos < length:
            match = pattern.search(source_code, search_pos)
            if not match:
                result.append(source_code[search_pos:])
                break

            macro_start = match.start()
            result.append(source_code[search_pos:macro_start])

            pos = match.end()
            while pos < length and source_code[pos].isspace():
                pos += 1

            if pos >= length or source_code[pos] != '(':
                # Not a macro invocation we know how to process; keep original text.
                result.append(source_code[macro_start:pos])
                search_pos = pos
                continue

            closing = self._find_matching_paren(source_code, pos)
            if closing == -1:
                # Unbalanced parentheses, keep the rest.
                result.append(source_code[macro_start:])
                search_pos = length
                break

            inner = source_code[pos + 1:closing]
            signature = self._extract_signature_from_macro(inner)

            if signature:
                result.append(signature)
            else:
                # Fallback to original macro text if we cannot safely extract the signature.
                result.append(source_code[macro_start:closing + 1])

            search_pos = closing + 1

        return ''.join(result)

    def _find_matching_paren(self, text, open_paren_index):
        """Find the matching closing parenthesis for the '(' at open_paren_index."""
        depth = 0
        in_string = None
        escape = False

        for idx in range(open_paren_index, len(text)):
            ch = text[idx]
            if in_string:
                if escape:
                    escape = False
                elif ch == '\\':
                    escape = True
                elif ch == in_string:
                    in_string = None
                continue

            if ch == '"' or ch == "'":
                in_string = ch
                continue

            if ch == '(':
                depth += 1
            elif ch == ')':
                depth -= 1
                if depth == 0:
                    return idx

        return -1

    def _extract_signature_from_macro(self, inner_content):
        """Return the last argument if it looks like a standalone function signature."""
        args = self._split_macro_arguments(inner_content)
        if not args:
            return None

        candidate = args[-1].strip()
        if self._looks_like_function_signature(candidate):
            return candidate

        return None
    
    def _strip_gnu_attributes(self, source_code):
        """
        移除GNU扩展属性（如__attribute__((weak)))，避免tree-sitter把带属性的函数解析成普通声明。
        这些属性不会影响函数签名提取，所以可以安全删除。
        """
        attribute_pattern = re.compile(r'__attribute__\s*\(\([^()]*\)\)\s*')
        return attribute_pattern.sub('', source_code)

    def _split_macro_arguments(self, content):
        """Split macro arguments while respecting nested parentheses and strings."""
        args = []
        current = []
        depth = 0
        in_string = None
        escape = False

        for ch in content:
            if in_string:
                current.append(ch)
                if escape:
                    escape = False
                    continue
                if ch == '\\':
                    escape = True
                elif ch == in_string:
                    in_string = None
                continue

            if ch == '"' or ch == "'":
                in_string = ch
                current.append(ch)
                continue

            if ch == '(':
                depth += 1
                current.append(ch)
            elif ch == ')':
                if depth > 0:
                    depth -= 1
                current.append(ch)
            elif ch == ',' and depth == 0:
                args.append(''.join(current).strip())
                current = []
            else:
                current.append(ch)

        if current:
            args.append(''.join(current).strip())

        return args

    def _looks_like_function_signature(self, candidate):
        """Heuristic check to make sure the candidate argument is a function signature."""
        if '(' not in candidate or ')' not in candidate:
            return False

        # Ensure there is an identifier followed by '(' which is not part of a cast.
        match = re.search(r'([A-Za-z_]\w*)\s*\(', candidate)
        if not match:
            return False

        # Very short names or likely macro placeholders are ignored.
        name = match.group(1)
        return bool(name) and name.isidentifier()


    def _rebuild_name_to_uuid_map_after_split(self, classified_elements):
        """重建名称到UUID映射表（C语言版本，简化版）"""
        self.logger.info("开始重建名称到UUID映射表...")
        self.name_to_uuid_map = {}
        
        # C语言只关注函数定义类型
        function_elements = classified_elements.get('function_definition', {})
        total_elements = len(function_elements)
        processed_count = 0
        
        if function_elements:
            self.logger.info(f"正在处理 function_definition 类型，共 {total_elements} 个元素")
            for uuid_key, element_info in function_elements.items():
                name = element_info.get('name')
                if name:
                    self.name_to_uuid_map[name] = uuid_key
                processed_count += 1
                # 每处理100个元素输出一次进度
                if processed_count % 100 == 0:
                    self.logger.info(f"重建映射表进度: {processed_count}/{total_elements} ({processed_count*100//total_elements}%)")
        else:
            self.logger.info("未找到 function_definition 类型的元素")
        
        self.logger.info(f"名称到UUID映射表重建完成，共映射 {len(self.name_to_uuid_map)} 个函数名称")

    def _update_dependencies_after_split(self, classified_elements):
        """更新依赖关系（C语言版本，简化版）"""
        # C语言只关注函数定义的依赖关系（函数调用关系）
        self.logger.info("开始更新依赖关系（仅处理 function_definition 类型）...")
        
        # 只处理函数定义类型
        function_elements = classified_elements.get('function_definition', {})
        total_elements = len(function_elements)
        
        if total_elements == 0:
            self.logger.info("未找到 function_definition 类型的元素，跳过依赖关系分析")
            return
        
        # 优化：预先准备名称列表，避免重复访问字典
        if not self.name_to_uuid_map:
            self.logger.info("名称映射表为空，跳过依赖关系分析")
            return
        
        # 将名称映射转换为列表，保持原有匹配逻辑（name in content）
        # 按名称长度降序排序，优先检查长名称（可能提高早期匹配概率，但不改变匹配结果）
        name_uuid_pairs = sorted(self.name_to_uuid_map.items(), key=lambda x: len(x[0]), reverse=True)
        
        # 优化：构建名称首字符集合，用于快速预过滤
        # 如果 content 中不包含任何名称的首字符，可以快速跳过
        name_first_chars = set()
        name_lengths = set()
        for name, _ in name_uuid_pairs:
            if name:
                name_first_chars.add(name[0])
                name_lengths.add(len(name))
        
        self.logger.info(f"开始分析依赖关系，共 {len(name_uuid_pairs)} 个可匹配函数名称")
        
        # 只收集函数定义类型的元素
        all_elements = []
        
        for uuid_key, element_info in function_elements.items():
            if 'dependencies' not in element_info:
                element_info['dependencies'] = []
            all_elements.append((uuid_key, element_info, 'function_definition'))
        
        # 使用线程池并发处理
        # 根据元素数量决定线程数，但不超过合理范围
        cpu_cores = cpu_count() or 4
        max_workers = min(cpu_cores, len(all_elements), 16)  # 最多16个线程
        
        # 如果元素数量较少，使用串行处理避免并发开销
        use_concurrent = len(all_elements) > 50 and max_workers > 1
        
        if use_concurrent:
            self.logger.info(f"使用 {max_workers} 个线程并发分析依赖关系")
            
            # 用于线程安全的进度计数
            processed_count = [0]  # 使用列表以便在闭包中修改
            total_dependencies = [0]  # 使用列表以便在闭包中修改
            progress_lock = Lock()
            
            def analyze_element_dependencies(args):
                """分析单个元素的依赖关系（用于并发处理）"""
                uuid_key, element_info, element_type = args
                content = element_info.get('content', '')
                dependencies = set()
                
                # 保持原有逻辑：使用 name in content 进行子字符串匹配
                if content:
                    # 优化1：快速预过滤 - 如果 content 中不包含任何名称的首字符，快速跳过
                    content_chars = set(content)
                    if not content_chars.intersection(name_first_chars):
                        return (uuid_key, element_type, list(dependencies))
                    
                    # 优化2：如果 content 长度小于最短名称长度，快速跳过
                    if len(content) < min(name_lengths):
                        return (uuid_key, element_type, list(dependencies))
                    
                    # 遍历所有名称，检查是否在 content 中（保持原有匹配逻辑）
                    for name, dep_uuid_key in name_uuid_pairs:
                        # 保持原有条件：排除自身，且名称在内容中
                        if dep_uuid_key != uuid_key and name in content:
                            dependencies.add(dep_uuid_key)
                
                return (uuid_key, element_type, list(dependencies))
            
            # 使用线程池并发处理
            results_dict = {}
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # 提交所有任务
                future_to_element = {
                    executor.submit(analyze_element_dependencies, elem): elem[0]
                    for elem in all_elements
                }
                
                # 处理完成的任务并更新进度
                for future in as_completed(future_to_element):
                    try:
                        uuid_key, element_type, dependencies = future.result()
                        # 更新结果
                        classified_elements[element_type][uuid_key]['dependencies'] = dependencies
                        results_dict[uuid_key] = dependencies
                        
                        # 线程安全地更新进度
                        with progress_lock:
                            processed_count[0] += 1
                            total_dependencies[0] += len(dependencies)
                            current_count = processed_count[0]
                            
                            # 每处理100个元素输出一次进度
                            if current_count % 100 == 0 or current_count == total_elements:
                                percentage = current_count * 100 // total_elements
                                self.logger.info(f"依赖关系分析进度: {current_count}/{total_elements} ({percentage}%)")
                    except Exception as e:
                        self.logger.error(f"处理元素时出错: {e}", exc_info=True)
            
            # 验证结果完整性
            if len(results_dict) != len(all_elements):
                self.logger.warning(f"警告：处理结果数量不匹配！期望 {len(all_elements)} 个，实际 {len(results_dict)} 个")
            else:
                self.logger.debug(f"结果验证通过：所有 {len(all_elements)} 个元素都已处理")
            
            final_processed = processed_count[0]
            final_dependencies = total_dependencies[0]
        else:
            # 元素数量较少时，使用串行处理（避免并发开销）
            self.logger.info("使用串行处理（元素数量较少）")
            processed_count = 0
            total_dependencies = 0
            
            # 只处理函数定义类型
            self.logger.info(f"正在分析 function_definition 类型的依赖关系，共 {len(function_elements)} 个元素")
            for uuid_key, element_info in function_elements.items():
                if 'dependencies' not in element_info:
                    element_info['dependencies'] = []
                
                # 根据element的内容分析依赖关系
                content = element_info.get('content', '')
                dependencies = set()
                
                # 保持原有逻辑：使用 name in content 进行子字符串匹配
                # 优化：如果 content 为空，直接跳过循环
                if content:
                    # 优化：快速预过滤 - 如果 content 中不包含任何名称的首字符，快速跳过
                    content_chars = set(content)
                    if content_chars.intersection(name_first_chars):
                        # 优化：如果 content 长度小于最短名称长度，快速跳过
                        if len(content) >= min(name_lengths):
                            # 遍历所有名称，检查是否在 content 中（保持原有匹配逻辑）
                            for name, dep_uuid_key in name_uuid_pairs:
                                # 保持原有条件：排除自身，且名称在内容中
                                if dep_uuid_key != uuid_key and name in content:
                                    dependencies.add(dep_uuid_key)
                
                element_info['dependencies'] = list(dependencies)
                total_dependencies += len(dependencies)
                processed_count += 1
                # 每处理100个元素输出一次进度
                if processed_count % 100 == 0:
                    self.logger.info(f"依赖关系分析进度: {processed_count}/{total_elements} ({processed_count*100//total_elements}%)")
            
            final_processed = processed_count
            final_dependencies = total_dependencies
        
        self.logger.info(f"依赖关系更新完成，共处理 {final_processed} 个元素，发现 {final_dependencies} 个依赖关系")

if __name__ == "__main__":
    # 测试代码
    parser = CParser()
    # parser.parse_project("demo")
