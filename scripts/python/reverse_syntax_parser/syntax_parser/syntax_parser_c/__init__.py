#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
C 语法解析器模块
"""

__version__ = "1.0.0"
__author__ = "Spec Team"

from .syntax_parser_c import c_code_syntax_parsing

__all__ = ["c_code_syntax_parsing"]