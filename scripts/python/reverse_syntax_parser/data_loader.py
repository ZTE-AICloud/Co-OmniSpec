"""
数据加载器 - 基于路径的简单配置
input_base_dir 下: internal/syntax_parser/, internal/semantics_parser/
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class SimplePathConfig:
    """基于 input_base_dir 的简单路径配置"""

    def __init__(self, input_base_dir: str, output_base_dir: str = None):
        self.input_base = Path(input_base_dir)
        self.output_base = Path(output_base_dir or input_base_dir)
        self.max_concurrent = 20

    def get_input_path(self, key: str) -> Path:
        mapping = {
            "call_tree": "internal/semantics_parser/call_tree_list.json",
            "all_methods": "internal/syntax_parser/all_methods.json",
            "all_functions": "internal/syntax_parser/all_functions.json",
            "all_classes": "internal/syntax_parser/all_class.json",
        }
        rel = mapping.get(key)
        if not rel:
            raise KeyError(f"未知输入键: {key}")
        return self.input_base / rel

    def get_output_path(self, key: str) -> Path:
        if key == "interface_identification":
            return self.output_base / "internal" / "interface_identification"
        raise KeyError(f"未知输出键: {key}")


class DataLoader:
    def __init__(self, config: SimplePathConfig):
        self.config = config
        self._cache = {}

    def load_call_tree(self) -> List[Dict[str, Any]]:
        return self._load_json("call_tree")

    def load_all_methods(self) -> Dict[str, Any]:
        return self._load_json("all_methods")

    def load_all_functions(self) -> Dict[str, Any]:
        return self._load_json("all_functions")

    def load_all_classes(self) -> Dict[str, Any]:
        return self._load_json("all_classes")

    def _load_json(self, key: str) -> Any:
        if key in self._cache:
            return self._cache[key]
        path = self.config.get_input_path(key)
        if not path.exists():
            raise FileNotFoundError(f"数据文件不存在: {path}")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self._cache[key] = data
        return data
