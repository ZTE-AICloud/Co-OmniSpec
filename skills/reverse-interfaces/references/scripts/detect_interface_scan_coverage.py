#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
扫描文件覆盖度检测（接口清单阶段）

当「file_list.json 覆盖文件数」与「仓库可扫代码文件总数」相比明显偏少，
且「实际识别接口数」低于预估下限时，判定为「疑似扫描覆盖不足」，
可自动将 file_list.json 扩展为全仓代码文件列表，供全量重扫。

使用方法:
    python detect_interface_scan_coverage.py <repo_root> [选项]

选项:
    --coverage-threshold FLOAT   低于该比例视为覆盖不足（默认 0.5）
    --count-ratio FLOAT        实际/预估 低于该比例时参与判定（默认 0.9）
    --apply-full-file-list     将 file_list.json 重写为全仓代码文件（相对路径数组）
    --dry-run                  与 --apply-full-file-list 联用时只打印不写文件

退出码:
    0  无需全量扩展（覆盖充足或数量已达标）
    2  疑似覆盖不足且实际数量偏低（需交互确认后重扫，或配合 --apply-full-file-list）
    1  执行错误
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Set

DEFAULT_FILE_LIST = ".cache/reverse/interfaces/file_list.json"
ESTIMATION_PATH = ".cache/reverse/interfaces/interface-estimation.json"
INTERFACE_LIST_PATH = ".cache/reverse/interfaces/interface-list.json"
REPORT_PATH = ".cache/reverse/interfaces/interface-scan-coverage-report.json"

CODE_EXTENSIONS = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".go", ".c", ".cc", ".cpp", ".h", ".hpp",
    ".cs", ".php", ".rb", ".rs", ".kt", ".kts", ".scala", ".swift", ".sh", ".ps1",
}

SKIP_DIRS = {".git", "node_modules", ".cache", "build", "dist", ".idea", ".vscode"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: str, data: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def collect_repo_code_files_rel(repo_root: str) -> List[str]:
    """仓库内全部可扫代码文件，相对路径 posix 风格，已去重排序。"""
    repo_root = os.path.abspath(repo_root)
    found: Set[str] = set()
    for root, dirs, files in os.walk(repo_root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for name in files:
            ext = os.path.splitext(name)[1].lower()
            if ext not in CODE_EXTENSIONS:
                continue
            abs_path = os.path.join(root, name)
            rel = os.path.relpath(abs_path, repo_root)
            found.add(rel.replace("\\", "/"))
    return sorted(found)


def parse_file_list_entries(repo_root: str, file_list_path: str) -> List[str]:
    abs_path = file_list_path if os.path.isabs(file_list_path) else os.path.join(repo_root, file_list_path)
    if not os.path.isfile(abs_path):
        return []
    data = load_json(abs_path)
    out: List[str] = []
    if isinstance(data, list):
        for x in data:
            if isinstance(x, str) and x.strip():
                out.append(x.strip().replace("\\", "/"))
    elif isinstance(data, dict) and isinstance(data.get("files"), list):
        for item in data["files"]:
            if isinstance(item, str) and item.strip():
                out.append(item.strip().replace("\\", "/"))
            elif isinstance(item, dict) and item.get("path"):
                out.append(str(item["path"]).strip().replace("\\", "/"))
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="接口扫描文件覆盖度检测")
    parser.add_argument("repo_root", help="仓库根目录")
    parser.add_argument(
        "--file-list",
        default=DEFAULT_FILE_LIST,
        help="file_list.json 相对仓库根路径",
    )
    parser.add_argument(
        "--coverage-threshold",
        type=float,
        default=0.5,
        help="file_list 数量 / 仓库代码文件数 低于该值视为覆盖可能不足",
    )
    parser.add_argument(
        "--count-ratio",
        type=float,
        default=0.9,
        help="实际接口数 / 预估总数 低于该值时与覆盖度联合判定",
    )
    parser.add_argument(
        "--apply-full-file-list",
        action="store_true",
        help="将 file_list.json 写为全仓代码文件列表（相对路径 JSON 数组）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅报告，即使指定 --apply-full-file-list 也不写 file_list",
    )
    args = parser.parse_args()

    repo_root = os.path.abspath(args.repo_root)
    if not os.path.isdir(repo_root):
        print(f"错误: 仓库根目录不存在: {repo_root}", file=sys.stderr)
        return 1

    file_list_rel = args.file_list
    file_list_abs = file_list_rel if os.path.isabs(file_list_rel) else os.path.join(repo_root, file_list_rel)

    repo_files = collect_repo_code_files_rel(repo_root)
    repo_total = len(repo_files)

    listed = parse_file_list_entries(repo_root, file_list_rel)
    listed_valid: List[str] = []
    seen: Set[str] = set()
    for p in listed:
        norm = p.replace("\\", "/")
        if norm in seen:
            continue
        seen.add(norm)
        full = os.path.join(repo_root, norm)
        if not os.path.isfile(full):
            continue
        ext = os.path.splitext(norm)[1].lower()
        if ext not in CODE_EXTENSIONS:
            continue
        listed_valid.append(norm)

    file_list_count = len(listed_valid)
    coverage_ratio = (file_list_count / repo_total) if repo_total > 0 else 1.0

    estimation_file = os.path.join(repo_root, ESTIMATION_PATH)
    interface_list_file = os.path.join(repo_root, INTERFACE_LIST_PATH)
    report_file = os.path.join(repo_root, REPORT_PATH)

    estimated_total = 0
    baseline_min = 0
    if os.path.isfile(estimation_file):
        try:
            est = load_json(estimation_file)
            estimated_total = int(est.get("estimated_total_interfaces", 0) or 0)
            baseline_min = int(est.get("baseline_min_interfaces", 0) or 0)
        except Exception:
            pass

    actual_total = 0
    if os.path.isfile(interface_list_file):
        try:
            data = load_json(interface_list_file)
            actual_total = len(data.get("interfaces", [])) if isinstance(data.get("interfaces"), list) else 0
        except Exception:
            pass

    # 低于预估：与质量闸门口径一致，取 max(预估*ratio, baseline_min) 为下限
    count_floor = 0
    if estimated_total > 0:
        count_floor = max(int(round(estimated_total * args.count_ratio)), baseline_min)
    elif baseline_min > 0:
        count_floor = baseline_min

    below_estimated = count_floor > 0 and actual_total < count_floor
    low_coverage = repo_total > 0 and coverage_ratio < args.coverage_threshold
    likely_insufficient_coverage = bool(below_estimated and low_coverage)

    report: Dict[str, Any] = {
        "version": "1.0",
        "generated_at": utc_now(),
        "repo_root": repo_root,
        "file_list_path": file_list_rel,
        "file_list_count": file_list_count,
        "repo_code_file_count": repo_total,
        "coverage_ratio": round(coverage_ratio, 6),
        "coverage_threshold": args.coverage_threshold,
        "estimated_total_interfaces": estimated_total,
        "baseline_min_interfaces": baseline_min,
        "actual_total_interfaces": actual_total,
        "count_ratio_threshold": args.count_ratio,
        "count_floor_used": count_floor,
        "below_estimated_count": below_estimated,
        "low_file_coverage": low_coverage,
        "likely_insufficient_coverage": likely_insufficient_coverage,
        "recommend_full_file_list_rescan": likely_insufficient_coverage,
        "apply_full_file_list_requested": bool(args.apply_full_file_list),
        "apply_full_file_list_done": False,
    }

    exit_code = 0
    if likely_insufficient_coverage:
        exit_code = 2

    if args.apply_full_file_list and not args.dry_run and likely_insufficient_coverage:
        save_json(file_list_abs, repo_files)
        report["apply_full_file_list_done"] = True
        report["file_list_count_after_apply"] = len(repo_files)
        report["coverage_ratio_after_apply"] = 1.0 if repo_total else 0.0
        # 已扩展文件列表，后续需强制重建批次并重扫；本脚本视为恢复动作成功
        exit_code = 0

    save_json(report_file, report)

    summary = {
        "ok": exit_code == 0,
        "exit_hint": exit_code,
        "report": report_file,
        "likely_insufficient_coverage": likely_insufficient_coverage,
        "recommend_full_file_list_rescan": likely_insufficient_coverage,
        "file_list_count": file_list_count,
        "repo_code_file_count": repo_total,
        "coverage_ratio": coverage_ratio,
        "actual_total_interfaces": actual_total,
        "estimated_total_interfaces": estimated_total,
        "apply_full_file_list_done": report.get("apply_full_file_list_done", False),
    }
    print(json.dumps(summary, ensure_ascii=False))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
