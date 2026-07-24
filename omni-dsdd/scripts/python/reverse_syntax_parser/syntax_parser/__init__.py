# -*- coding: utf-8 -*-
"""
语法解析器包
支持多种编程语言的语法解析
"""

# 导入各种语言的语法解析器
from .syntax_parser_python.syntax_parser_python import python_code_syntax_parsing

# 尝试导入C++解析器
try:
    from .syntax_parser_cpp.syntax_parser_cpp import cpp_code_syntax_parsing
    CPP_PARSER_AVAILABLE = True
except ImportError as e:
    def cpp_code_syntax_parsing(*args, **kwargs):
        raise ImportError(f"C++ 解析器不可用: {str(e)}")
    CPP_PARSER_AVAILABLE = False

# 尝试导入C解析器
try:
    from .syntax_parser_c.syntax_parser_c import c_code_syntax_parsing
    C_PARSER_AVAILABLE = True
except ImportError as e:
    def c_code_syntax_parsing(*args, **kwargs):
        raise ImportError(f"C 解析器不可用: {str(e)}")
    C_PARSER_AVAILABLE = False

# 尝试导入Java解析器
try:
    from .syntax_parser_java.syntax_parser_java import java_code_syntax_parsing
    JAVA_PARSER_AVAILABLE = True
except ImportError as e:
    def java_code_syntax_parsing(*args, **kwargs):
        raise ImportError(f"Java 解析器不可用: {str(e)}")
    JAVA_PARSER_AVAILABLE = False

__all__ = [
    "python_code_syntax_parsing",
    "cpp_code_syntax_parsing",
    "java_code_syntax_parsing",
    "c_code_syntax_parsing",
    "CPP_PARSER_AVAILABLE",
    "C_PARSER_AVAILABLE",
    "JAVA_PARSER_AVAILABLE"
]