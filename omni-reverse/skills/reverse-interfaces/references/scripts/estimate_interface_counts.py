#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
接口数量预估工具
基于扫描范围代码行数与已识别接口类型，输出接口类型预估和总量下限（千分之2基线）。

使用方法:
    python estimate_interface_counts.py <repo_root> [--file-list <json>] [--output <json>]
"""

import argparse
import json
import math
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple


DEFAULT_OUTPUT = ".cache/reverse/interfaces/interface-estimation.json"
DEFAULT_FILE_LIST = ".cache/reverse/interfaces/file_list.json"
DEFAULT_INTERFACE_TYPES = ".cache/reverse/interfaces/interface-types.json"
DEFAULT_PATTERNS = ".cache/reverse/interfaces/interface-patterns.json"

CODE_EXTENSIONS = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".go", ".c", ".cc", ".cpp", ".h", ".hpp",
    ".cs", ".php", ".rb", ".rs", ".kt", ".kts", ".scala", ".swift", ".sh", ".ps1",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: str, data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def count_lines(path: str) -> int:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return sum(1 for _ in f)
    except Exception:
        return 0


def resolve_file_list(repo_root: str, file_list_path: str) -> List[str]:
    abs_path = file_list_path if os.path.isabs(file_list_path) else os.path.join(repo_root, file_list_path)
    if os.path.exists(abs_path):
        data = load_json(abs_path)
        if isinstance(data, list):
            return [str(x) for x in data]
        if isinstance(data, dict):
            if isinstance(data.get("files"), list):
                files: List[str] = []
                for item in data["files"]:
                    if isinstance(item, str):
                        files.append(item)
                    elif isinstance(item, dict) and item.get("path"):
                        files.append(str(item["path"]))
                return files
    # 回退：遍历仓库代码文件
    result: List[str] = []
    for root, dirs, files in os.walk(repo_root):
        # 轻量排除常见目录
        dirs[:] = [d for d in dirs if d not in {".git", "node_modules", ".cache", "build", "dist", ".idea", ".vscode"}]
        for name in files:
            ext = os.path.splitext(name)[1].lower()
            if ext in CODE_EXTENSIONS:
                result.append(os.path.join(root, name))
    return result


def to_abs(repo_root: str, path: str) -> str:
    return path if os.path.isabs(path) else os.path.join(repo_root, path)


def read_interface_types(repo_root: str) -> List[str]:
    path = to_abs(repo_root, DEFAULT_INTERFACE_TYPES)
    if not os.path.exists(path):
        return ["RESTful API", "RPC 接口", "消息类接口", "模块间接口", "函数接口", "命令行接口", "其他"]
    data = load_json(path)
    if isinstance(data, list):
        return [str(x) for x in data if str(x).strip()]
    if isinstance(data, dict):
        if isinstance(data.get("selected_types"), list):
            return [str(x) for x in data["selected_types"] if str(x).strip()]
        if isinstance(data.get("types"), list):
            return [str(x) for x in data["types"] if str(x).strip()]
    return ["RESTful API", "RPC 接口", "消息类接口", "模块间接口", "函数接口", "命令行接口", "其他"]


def read_pattern_hits(repo_root: str, interface_types: List[str]) -> Dict[str, int]:
    path = to_abs(repo_root, DEFAULT_PATTERNS)
    hits = {t: 0 for t in interface_types}
    if not os.path.exists(path):
        return hits
    try:
        data = load_json(path)
        text = json.dumps(data, ensure_ascii=False)
        for t in interface_types:
            hits[t] = text.count(t)
    except Exception:
        pass
    return hits


def estimate_by_type(interface_types: List[str], baseline_min: int, pattern_hits: Dict[str, int]) -> Dict[str, int]:
    # 先按模式命中分配，再做基线兜底
    total_hits = sum(max(0, v) for v in pattern_hits.values())
    estimates: Dict[str, int] = {}
    if total_hits > 0:
        for t in interface_types:
            ratio = max(0, pattern_hits.get(t, 0)) / total_hits
            estimates[t] = max(0, int(round(baseline_min * ratio)))
    else:
        per = max(1, baseline_min // max(1, len(interface_types)))
        for t in interface_types:
            estimates[t] = per

    # 补齐到 baseline_min
    current = sum(estimates.values())
    i = 0
    while current < baseline_min and interface_types:
        t = interface_types[i % len(interface_types)]
        estimates[t] += 1
        current += 1
        i += 1
    return estimates


def apply_top1_floor(
    estimates: Dict[str, int],
    top1_min: int
) -> Tuple[Dict[str, int], str]:
    """
    强制约束：
    排名第一的接口类型数量不得低于 top1_min（代码行数千分之一）。
    """
    if not estimates:
        return estimates, ""

    top_type = max(estimates, key=estimates.get)
    if estimates[top_type] < top1_min:
        estimates[top_type] = top1_min
    return estimates, top_type


def main() -> int:
    parser = argparse.ArgumentParser(description="接口数量预估工具")
    parser.add_argument("repo_root", help="仓库根目录")
    parser.add_argument("--file-list", default=DEFAULT_FILE_LIST, help="扫描文件列表JSON")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="输出JSON路径")
    args = parser.parse_args()

    repo_root = os.path.abspath(args.repo_root)
    if not os.path.isdir(repo_root):
        print(f"错误: 仓库根目录不存在: {repo_root}", file=sys.stderr)
        return 1

    files = resolve_file_list(repo_root, args.file_list)
    abs_files = [p if os.path.isabs(p) else os.path.join(repo_root, p) for p in files]
    total_lines = sum(count_lines(p) for p in abs_files)
    baseline_min = max(1, int(math.ceil(total_lines * 0.002)))
    top1_floor_min = max(1, int(math.ceil(total_lines * 0.001)))

    interface_types = read_interface_types(repo_root)
    pattern_hits = read_pattern_hits(repo_root, interface_types)
    by_type = estimate_by_type(interface_types, baseline_min, pattern_hits)
    by_type, top_type = apply_top1_floor(by_type, top1_floor_min)
    estimated_total = max(baseline_min, sum(by_type.values()))

    result = {
        "version": "1.0",
        "generated_at": utc_now(),
        "total_code_lines": total_lines,
        "baseline_ratio": 0.002,
        "baseline_min_interfaces": baseline_min,
        "top1_ratio": 0.001,
        "top1_min_interfaces": top1_floor_min,
        "top1_interface_type": top_type,
        "top1_interface_estimated_count": by_type.get(top_type, 0) if top_type else 0,
        "top1_floor_applied": bool(top_type and by_type.get(top_type, 0) >= top1_floor_min),
        "estimated_by_type": by_type,
        "estimated_total_interfaces": estimated_total,
        "under_estimated": estimated_total < baseline_min,
        "mandatory_flags": {
            "estimation_generated": True,
            "estimation_confirmed": False
        },
        "recommendations_if_low": [
            "放宽约束规则并重扫关键模块",
            "扩大扫描路径范围",
            "开启全文件扫描"
        ]
    }

    output_path = args.output if os.path.isabs(args.output) else os.path.join(repo_root, args.output)
    save_json(output_path, result)
    print(json.dumps({
        "ok": True,
        "output": output_path,
        "total_code_lines": total_lines,
        "baseline_min_interfaces": baseline_min,
        "estimated_total_interfaces": estimated_total
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
