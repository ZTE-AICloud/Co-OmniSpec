#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
独立调用链解析器
从语法解析输出生成调用链 call_tree_list.json
"""

import os
import json
import argparse
import sys
from pathlib import Path
from typing import Dict, List, Set, Any, Optional

from utils import get_logger

UUID_SEPARATOR = "###"


def read_json_file(file_path: str, logger) -> Dict[str, Any]:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error("读取JSON失败: %s - %s", file_path, e)
        return {}


def save_json_file(data: Any, file_path: str, logger) -> bool:
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error("保存JSON失败: %s - %s", file_path, e)
        return False


def derive_processing_batches(
    nodes_dependency: Dict[str, List[str]],
    all_nodes: Dict[str, Any],
    logger,
) -> List[List[Dict[str, Any]]]:
    remaining = set(nodes_dependency.keys())
    processing_batches = []
    node_dep_count = {
        n: len([d for d in deps if d != n and d in nodes_dependency])
        for n, deps in nodes_dependency.items()
    }
    max_iter = len(remaining) + 10
    iter_count = 0

    while remaining:
        iter_count += 1
        if iter_count > max_iter:
            processing_batches.append(list(remaining))
            break
        current_batch = []
        for node_name in list(remaining):
            deps = nodes_dependency.get(node_name, [])
            all_done = all(
                d == node_name or d not in remaining for d in deps
            )
            if all_done:
                current_batch.append(node_name)
        if not current_batch and remaining:
            best = min(remaining, key=lambda n: node_dep_count.get(n, 0))
            current_batch.append(best)
        if not current_batch:
            break
        processing_batches.append(current_batch)
        for n in current_batch:
            remaining.discard(n)

    return [
        [all_nodes[n] for n in batch if n in all_nodes]
        for batch in processing_batches
    ]


def get_code_type_info(codebase_path: str, logger) -> tuple:
    ct_file = os.path.join(codebase_path, "code_type.json")
    if os.path.exists(ct_file):
        try:
            with open(ct_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("language", "unknown"), data.get("related_json_files", [])
        except Exception as e:
            logger.error("读取code_type.json失败: %s", e)
    return None, []


def load_nodes_from_codebase(codebase_path: str, logger) -> Dict[str, Any]:
    language, related_files = get_code_type_info(codebase_path, logger)
    if not language or not related_files:
        logger.error("无法从code_type.json获取语言或相关文件列表")
        return {}

    file_type_mapping = {
        "all_class.json": "class_definition",
        "all_functions.json": "function_definition",
        "all_methods.json": "method_definition",
        "all_global_vars.json": "global_variable",
        "all_imports.json": "import_definition",
    }
    all_node = {}

    def process_node(node_uuid_key, node_info, node_type=None):
        node_info = node_info.copy()
        node_info["uuid_key"] = node_uuid_key
        node_info["original_name"] = node_uuid_key.split(UUID_SEPARATOR)[0] if UUID_SEPARATOR in node_uuid_key else node_uuid_key
        node_info["name"] = node_uuid_key
        node_info.setdefault("type", node_type or "unknown")
        node_info.setdefault("content", "")
        node_info.setdefault("dependencies", [])
        return node_info

    for fname in related_files:
        fpath = os.path.join(codebase_path, fname)
        if os.path.exists(fpath):
            data = read_json_file(fpath, logger)
            node_type = file_type_mapping.get(fname, "unknown")
            for k, v in data.items():
                all_node[k] = process_node(k, v, node_type)

    return all_node


def get_call_tree_list(
    processing_batches: List[List[Dict[str, Any]]],
    all_node: Dict[str, Any],
    output_path: str,
    logger,
    max_depth: int = 10,
) -> List[Dict[str, Any]]:
    call_tree_list = []
    processed = set()
    allowed_types = {"method_definition", "function_definition"}

    def get_all_deps(tree, dependencies, depth, visited=None):
        if visited is None:
            visited = set()
        node_name = tree.get("name")
        if not node_name or node_name in visited or depth <= 0 or not dependencies:
            return
        visited.add(node_name)
        if len(visited) > 10000:
            return
        for dep_key in dependencies:
            if dep_key == node_name:
                continue
            dep_node = all_node.get(dep_key)
            if dep_node and dep_node.get("type") in allowed_types and dep_key != node_name and dep_key not in visited:
                processed.add(dep_key)
                child_tree = {"name": dep_key, "type": dep_node.get("type", ""), "children": []}
                tree["children"].append(child_tree)
                get_all_deps(child_tree, dep_node.get("dependencies", []), depth - 1, visited)

    for batch in processing_batches:
        for node in batch:
            node_key = node.get("name")
            if node_key in processed:
                continue
            processed.add(node_key)
            node_type = all_node.get(node_key, {}).get("type", "unknown")
            if node_type not in allowed_types:
                continue
            tree = {"name": node_key, "type": node_type, "children": []}
            get_all_deps(tree, node.get("dependencies", []), max_depth)
            call_tree_list.append(tree)

    call_tree_file = os.path.join(output_path, "call_tree_list.json")
    save_json_file(call_tree_list, call_tree_file, logger)
    return call_tree_list


def generate_call_tree(codebase_path: str, output_path: str, logger) -> bool:
    try:
        all_node = load_nodes_from_codebase(codebase_path, logger)
        if not all_node:
            return False
        node_dependency = {k: v.get("dependencies", []) for k, v in all_node.items()}
        excluded = set()
        allowed_types = {"method_definition", "function_definition"}
        for k, v in all_node.items():
            if v.get("type") not in allowed_types:
                excluded.add(k)
        class_file = os.path.join(codebase_path, "all_class.json")
        if os.path.exists(class_file):
            excluded.update(read_json_file(class_file, logger).keys())
        call_tree_node_dep = {}
        call_tree_all_node = {}
        for k, v in all_node.items():
            if v.get("type") not in allowed_types:
                continue
            filtered = [d for d in v.get("dependencies", []) if d not in excluded]
            call_tree_node_dep[k] = filtered
            call_tree_all_node[k] = v
        batches = derive_processing_batches(call_tree_node_dep, call_tree_all_node, logger)
        get_call_tree_list(batches[::-1], call_tree_all_node, output_path, logger, max_depth=10)
        return True
    except Exception as e:
        logger.error("生成调用链失败: %s", e, exc_info=True)
        return False


def main():
    logger = get_logger("semantics_parser")
    parser = argparse.ArgumentParser(description="独立调用链解析器")
    parser.add_argument("codebase", help="代码库路径（语法解析输出目录）")
    parser.add_argument("output", help="输出路径")
    args = parser.parse_args()

    if not os.path.exists(args.codebase):
        logger.error("代码库路径不存在: %s", args.codebase)
        sys.exit(1)
    ct_file = os.path.join(args.codebase, "code_type.json")
    if not os.path.exists(ct_file):
        logger.error("缺少code_type.json，请先运行语法解析器")
        sys.exit(1)
    os.makedirs(args.output, exist_ok=True)
    if not generate_call_tree(args.codebase, args.output, logger):
        sys.exit(1)


if __name__ == "__main__":
    main()
