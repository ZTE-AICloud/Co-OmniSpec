#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
强制校验接口详情文档是否全量生成。

规则：
1. 以 interface-list.json 中 interfaces[] 为唯一真源；
2. 每个接口必须存在一个详情文档：{interface_id}_*.md；
3. 若存在缺失，自动将缺失接口 processing_status 重置为 pending；
4. 若存在缺失，自动将相关批次状态重置为 pending，确保后续可继续分批处理；
5. 退出码：
   - 0: 全部接口文档齐全
   - 2: 存在缺失，已回写状态，需继续处理
   - 1: 脚本执行错误
"""

import argparse
import glob
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Set


INTERFACE_LIST_REL = ".cache/reverse/interfaces/interface-list.json"
MAPPING_CANDIDATES = [
    ".cache/reverse/interfaces/interface-batch-mapping.json",
    ".cache/reverse/interfaces/batch-mapping.json",
]
DETAIL_STATUS_REL = ".cache/reverse/interfaces/interface_detail-batch-status.json"
DETAIL_FILE_GLOB = ".cache/reverse/interfaces/interface-batch-details-*.json"
OUTPUT_REPORT_REL = ".cache/reverse/interfaces/interface-docs-completeness-report.json"
DOCS_DIR_REL = "omni-doc/specs/interfaces"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: str, data: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def resolve_mapping_file(repo_root: str) -> str:
    for rel in MAPPING_CANDIDATES:
        abs_path = os.path.join(repo_root, rel)
        if os.path.exists(abs_path):
            return abs_path
    return ""


def find_doc_exists(docs_dir: str, interface_id: str) -> bool:
    pattern = os.path.join(docs_dir, f"{interface_id}_*.md")
    return len(glob.glob(pattern)) > 0


def collect_missing_interfaces(repo_root: str) -> Dict[str, Any]:
    interface_list_file = os.path.join(repo_root, INTERFACE_LIST_REL)
    docs_dir = os.path.join(repo_root, DOCS_DIR_REL)

    if not os.path.exists(interface_list_file):
        raise FileNotFoundError(f"接口清单不存在: {interface_list_file}")

    interface_list = load_json(interface_list_file)
    interfaces = interface_list.get("interfaces", [])
    if not isinstance(interfaces, list):
        raise ValueError("interface-list.json 格式错误：interfaces 不是数组")

    missing_ids: List[str] = []
    present_count = 0
    for item in interfaces:
        if not isinstance(item, dict):
            continue
        interface_id = str(item.get("interface_id", "")).strip()
        if not interface_id:
            continue
        if find_doc_exists(docs_dir, interface_id):
            present_count += 1
        else:
            missing_ids.append(interface_id)

    return {
        "interface_list": interface_list,
        "total": len(interfaces),
        "present_count": present_count,
        "missing_ids": missing_ids,
    }


def reset_missing_interface_status(interface_list: Dict[str, Any], missing_ids: Set[str]) -> int:
    updated = 0
    for item in interface_list.get("interfaces", []):
        if not isinstance(item, dict):
            continue
        interface_id = str(item.get("interface_id", "")).strip()
        if interface_id in missing_ids:
            item["processing_status"] = "pending"
            # 清理处理完成标记，避免误判已完成
            item.pop("processed_at", None)
            item.pop("processing_time", None)
            updated += 1
    return updated


def collect_batches_for_missing(repo_root: str, missing_ids: Set[str]) -> Set[int]:
    affected_batches: Set[int] = set()
    for abs_path in glob.glob(os.path.join(repo_root, DETAIL_FILE_GLOB)):
        try:
            batch_data = load_json(abs_path)
            batch_no = int(batch_data.get("batch_number", 0))
            interfaces = batch_data.get("interfaces", [])
            for item in interfaces:
                if isinstance(item, dict) and str(item.get("interface_id", "")).strip() in missing_ids:
                    if batch_no > 0:
                        affected_batches.add(batch_no)
                    break
        except Exception:
            # 忽略坏文件，避免阻断
            continue
    return affected_batches


def reset_batch_statuses(repo_root: str, affected_batches: Set[int]) -> Dict[str, int]:
    reset_in_mapping = 0
    reset_in_detail_status = 0

    mapping_file = resolve_mapping_file(repo_root)
    if mapping_file and affected_batches:
        mapping = load_json(mapping_file)
        for item in mapping.get("batches", []):
            if not isinstance(item, dict):
                continue
            batch_no = int(item.get("batch_number", 0))
            if batch_no in affected_batches:
                item["status"] = "pending"
                item.pop("started_at", None)
                item.pop("completed_at", None)
                reset_in_mapping += 1
        save_json(mapping_file, mapping)

    detail_status_file = os.path.join(repo_root, DETAIL_STATUS_REL)
    if os.path.exists(detail_status_file) and affected_batches:
        detail_status = load_json(detail_status_file)
        for item in detail_status.get("batch_mappings", []):
            if not isinstance(item, dict):
                continue
            batch_no = int(item.get("batch_number", 0))
            if batch_no in affected_batches:
                item["status"] = "pending"
                item.pop("started_at", None)
                item.pop("completed_at", None)
                reset_in_detail_status += 1

        # 重新计算聚合字段，避免显示100%但仍有缺失
        batch_mappings = detail_status.get("batch_mappings", [])
        total_batches = len(batch_mappings)
        processed_batches = sum(1 for b in batch_mappings if isinstance(b, dict) and b.get("status") == "completed")
        failed_batches = sum(1 for b in batch_mappings if isinstance(b, dict) and b.get("status") == "failed")
        detail_status["total_batches"] = total_batches
        detail_status["processed_batches"] = processed_batches
        detail_status["failed_batches"] = failed_batches
        detail_status["current_batch"] = 0
        detail_status["status"] = "incomplete" if processed_batches < total_batches else "completed"
        detail_status["last_update"] = utc_now()
        save_json(detail_status_file, detail_status)

    return {
        "reset_in_mapping": reset_in_mapping,
        "reset_in_detail_status": reset_in_detail_status,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="强制校验接口详情文档是否全量生成")
    parser.add_argument("repo_root", help="仓库根目录")
    args = parser.parse_args()

    repo_root = os.path.abspath(args.repo_root)
    if not os.path.isdir(repo_root):
        print(f"错误: 仓库根目录不存在: {repo_root}", file=sys.stderr)
        return 1

    try:
        summary = collect_missing_interfaces(repo_root)
        interface_list = summary["interface_list"]
        total = summary["total"]
        present_count = summary["present_count"]
        missing_ids = summary["missing_ids"]
        missing_set = set(missing_ids)

        interface_list_path = os.path.join(repo_root, INTERFACE_LIST_REL)
        report_path = os.path.join(repo_root, OUTPUT_REPORT_REL)

        interface_status_reset = 0
        batch_reset_result = {"reset_in_mapping": 0, "reset_in_detail_status": 0}
        affected_batches: Set[int] = set()

        if missing_set:
            interface_status_reset = reset_missing_interface_status(interface_list, missing_set)
            save_json(interface_list_path, interface_list)

            affected_batches = collect_batches_for_missing(repo_root, missing_set)
            batch_reset_result = reset_batch_statuses(repo_root, affected_batches)

        report = {
            "version": "1.0",
            "generated_at": utc_now(),
            "total_interfaces": total,
            "expected_interface_count": total,
            "generated_docs_count": present_count,
            "count_match": present_count == total,
            "missing_docs_count": len(missing_ids),
            "missing_interface_ids": missing_ids,
            "affected_batches": sorted(list(affected_batches)),
            "resets": {
                "interface_status_reset": interface_status_reset,
                "batch_mapping_reset": batch_reset_result["reset_in_mapping"],
                "detail_batch_status_reset": batch_reset_result["reset_in_detail_status"],
            },
            "all_generated": len(missing_ids) == 0,
        }
        save_json(report_path, report)

        print(json.dumps({
            "ok": len(missing_ids) == 0,
            "report": report_path,
            "total_interfaces": total,
            "generated_docs_count": present_count,
            "missing_docs_count": len(missing_ids),
        }, ensure_ascii=False))

        return 0 if len(missing_ids) == 0 else 2
    except Exception as exc:
        print(f"错误: 校验失败: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
