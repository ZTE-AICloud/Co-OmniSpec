import pathlib
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

# 导入日志模块
sys.path.append(str(Path(__file__).parent.parent.parent / "utils"))
from sys import path
path.insert(0, str(pathlib.Path(__file__).parent.parent.parent.parent))
from utils import get_logger

class MacroParser:
    def __init__(self):
        self.logger = get_logger("macro_parser")

    def parse_macro(self, node, source_code, file_path):
        """解析C语言宏定义"""
        macro_info = {
            'name': '',
            'content': '',
            'value': '',
            'parameters': [],
            'filename': file_path,
            'lineno': node.start_point[0] + 1,
            'end_lineno': node.end_point[0] + 1,
            'is_function_like': False,
            'dependencies': []
        }

        try:
            # 获取宏定义内容
            macro_info['content'] = source_code[node.start_byte:node.end_byte]
            
            # 解析宏的各个部分
            for child in node.children:
                if child.type == 'identifier':
                    # 获取宏名称
                    macro_info['name'] = source_code[child.start_byte:child.end_byte]
                elif child.type == 'preproc_params':
                    # 函数式宏的参数列表
                    macro_info['is_function_like'] = True
                    macro_info['parameters'] = self._parse_macro_parameters(child, source_code)
                elif child.type == 'preproc_arg':
                    # 宏的值/定义
                    macro_info['value'] = source_code[child.start_byte:child.end_byte].strip()
            
            # 如果没有显式的值，从内容中提取
            if not macro_info['value'] and macro_info['content']:
                # 提取#define之后的部分作为值
                content_parts = macro_info['content'].split()
                if len(content_parts) > 2:  # #define NAME VALUE
                    if macro_info['is_function_like']:
                        # 对于函数式宏，需要跳过参数部分
                        define_idx = macro_info['content'].find('#define')
                        if define_idx != -1:
                            after_define = macro_info['content'][define_idx + 7:].strip()
                            paren_idx = after_define.find(')')
                            if paren_idx != -1:
                                macro_info['value'] = after_define[paren_idx + 1:].strip()
                    else:
                        # 简单宏，取第三个部分开始的所有内容
                        macro_info['value'] = ' '.join(content_parts[2:])
            
            return macro_info if macro_info['name'] else None
            
        except Exception as e:
            self.logger.error(f"解析宏时出错: {e}", exc_info=True)
            return None

    def _parse_macro_parameters(self, params_node, source_code):
        """解析宏参数列表"""
        parameters = []
        
        for child in params_node.children:
            if child.type == 'identifier':
                param_name = source_code[child.start_byte:child.end_byte]
                parameters.append({
                    'name': param_name,
                    'type': 'macro_param'
                })
        
        return parameters

    def parse_include(self, node, source_code, file_path):
        """解析#include指令"""
        include_info = {
            'name': '',
            'content': '',
            'include_path': '',
            'filename': file_path,
            'lineno': node.start_point[0] + 1,
            'end_lineno': node.end_point[0] + 1,
            'is_system_header': False,
            'dependencies': []
        }

        try:
            # 获取include内容
            include_info['content'] = source_code[node.start_byte:node.end_byte]
            
            for child in node.children:
                if child.type == 'string_literal':
                    # 用户头文件 #include "file.h"
                    include_path = source_code[child.start_byte:child.end_byte]
                    include_info['include_path'] = include_path.strip('"')
                    include_info['name'] = include_info['include_path']
                    include_info['is_system_header'] = False
                elif child.type == 'system_lib_string':
                    # 系统头文件 #include <file.h>
                    include_path = source_code[child.start_byte:child.end_byte]
                    include_info['include_path'] = include_path.strip('<>')
                    include_info['name'] = include_info['include_path']
                    include_info['is_system_header'] = True
            
            return include_info if include_info['name'] else None
            
        except Exception as e:
            self.logger.error(f"解析include时出错: {e}", exc_info=True)
            return None

    def parse_ifdef(self, node, source_code, file_path):
        """解析#ifdef/#ifndef等条件编译指令"""
        ifdef_info = {
            'name': '',
            'content': '',
            'condition': '',
            'filename': file_path,
            'lineno': node.start_point[0] + 1,
            'end_lineno': node.end_point[0] + 1,
            'directive_type': '',
            'dependencies': []
        }

        try:
            # 获取指令内容
            ifdef_info['content'] = source_code[node.start_byte:node.end_byte]
            
            # 确定指令类型
            content_lines = ifdef_info['content'].split('\n')
            if content_lines:
                first_line = content_lines[0].strip()
                if first_line.startswith('#ifdef'):
                    ifdef_info['directive_type'] = 'ifdef'
                    ifdef_info['condition'] = first_line[6:].strip()
                elif first_line.startswith('#ifndef'):
                    ifdef_info['directive_type'] = 'ifndef'
                    ifdef_info['condition'] = first_line[7:].strip()
                elif first_line.startswith('#if'):
                    ifdef_info['directive_type'] = 'if'
                    ifdef_info['condition'] = first_line[3:].strip()
                
                ifdef_info['name'] = f"{ifdef_info['directive_type']}_{ifdef_info['condition']}"
            
            return ifdef_info if ifdef_info['name'] else None
            
        except Exception as e:
            self.logger.error(f"解析条件编译指令时出错: {e}", exc_info=True)
            return None
