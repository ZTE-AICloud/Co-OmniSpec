#!/usr/bin/env python3
"""Python 语法解析入口"""
import os
import json
import sys
from pathlib import Path

from .constants import UUID_SEPARATOR
from .parsers import PythonParser
# 导入日志模块 - 添加更多父目录以找到utils
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from utils import get_logger


def make_json_serializable(obj):
    if isinstance(obj, dict):
        return {k: make_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [make_json_serializable(i) for i in obj]
    elif isinstance(obj, bytes):
        try:
            return f"b'{obj.decode('utf-8', errors='ignore')}'"
        except Exception:
            return f"b'<{len(obj)} bytes>'"
    elif isinstance(obj, (int, float, str, bool, type(None))):
        return obj
    return str(obj)


def python_code_syntax_parsing(prj_path: str, output_path: str) -> str:
    logger = get_logger("syntax_parser_python")
    if not output_path:
        logger.error("必须提供输出路径")
        sys.exit(1)
    codebase_path = output_path
    os.makedirs(codebase_path, exist_ok=True)

    parser = PythonParser()
    elements = parser.parse_project(prj_path)

    classified_elements = {
        "function_definition": {},
        "global_variable": {},
        "class_definition": {},
        "method_definition": {},
        "import_statement": {},
    }

    for name, info in elements.items():
        et = info.get("type")
        if et == "constant_definition":
            classified_elements["global_variable"][name] = info
        elif et == "class_definition":
            class_info = info.copy()
            methods = class_info.get("methods", {})
            for method_key, method_info in methods.items():
                method_info = method_info.copy()
                class_key = f"{class_info.get('name')}{UUID_SEPARATOR}{class_info.get('uuid')}"
                method_info["class_key"] = class_key
                method_info["type"] = "method_definition"
                classified_elements["method_definition"][method_key] = method_info
            class_info["method_keys"] = list(methods.keys())
            del class_info["methods"]
            classified_elements["class_definition"][name] = class_info
        elif et in classified_elements:
            classified_elements[et][name] = info

    parser._rebuild_name_to_uuid_map_after_split(classified_elements)
    parser._update_dependencies_after_split(classified_elements)

    file_mapping = {
        "function_definition": "all_functions.json",
        "class_definition": "all_class.json",
        "method_definition": "all_methods.json",
        "global_variable": "all_global_vars.json",
        "import_statement": "all_imports.json",
    }

    for element_type, elements_dict in classified_elements.items():
        fname = file_mapping.get(element_type, f"all_{element_type}.json")
        fpath = os.path.join(codebase_path, fname)
        safe_data = make_json_serializable(elements_dict)
        with open(fpath, "w", encoding="utf-8") as f:
            json.dump(safe_data, f, ensure_ascii=False, indent=4)

    code_type_data = {
        "language": "python",
        "description": "Python language codebase parsing result",
        "parser_type": "syntax_parser_python",
        "related_json_files": [
            "all_class.json",
            "all_functions.json",
            "all_global_vars.json",
            "all_imports.json",
            "all_methods.json",
        ],
    }
    with open(os.path.join(codebase_path, "code_type.json"), "w", encoding="utf-8") as f:
        json.dump(code_type_data, f, ensure_ascii=False, indent=4)

    return "Python语法解析成功"


if __name__ == "__main__":
    logger = get_logger("syntax_parser_python")
    if len(sys.argv) < 3:
        logger.error("用法: python syntax_parser_python.py <项目路径> <输出路径>")
        sys.exit(1)
    python_code_syntax_parsing(sys.argv[1], sys.argv[2])
