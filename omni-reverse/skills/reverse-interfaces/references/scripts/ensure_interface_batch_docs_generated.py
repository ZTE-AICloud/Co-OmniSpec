#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
强制校验“单个接口批次”的详情文档是否全生成（按 interface-list.json 真源 + 批次明细真源）

用途：
- 在阶段4“按批次生成接口详情文档”时，子agent完成后必须校验该批次下每个接口详情文档都确实存在
- 若缺失：重置对应接口的 processing_status 为 pending，并将对应批次状态重置为 pending（允许重试）

退出码：
- 0：该批次文档全量存在
- 2：缺失若干接口文档（已回写状态，需重试该批次）
- 1：脚本执行错误
"""

import argparse
import glob
import json
import os
import re
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple


DOCS_DIR_REL = "omni-doc/specs/interfaces"
INTERFACE_LIST_REL = ".cache/reverse/interfaces/interface-list.json"

# 两套兼容命名
INTERFACE_BATCH_MAPPING_CANDIDATES = [
    ".cache/reverse/interfaces/interface-batch-mapping.json",
    ".cache/reverse/interfaces/batch-mapping.json",
]
INTERFACE_DETAIL_BATCH_STATUS_REL = ".cache/reverse/interfaces/interface_detail-batch-status.json"

REPORT_REL = ".cache/reverse/interfaces/interface-batch-docs-validation-report.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: str, data: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def resolve_first_existing(repo_root: str, candidates: List[str]) -> str:
    for rel in candidates:
        abs_path = os.path.join(repo_root, rel)
        if os.path.exists(abs_path):
            return abs_path
    return ""


def parse_batch_details_file_for_batch_number(batch_details_path: str) -> int:
    base = os.path.basename(batch_details_path)
    m = re.match(r"interface-batch-details-(\d+)\.json$", base)
    if m:
        return int(m.group(1))
    return 0


def find_interface_ids_from_batch_details(batch_details: Dict[str, Any]) -> List[str]:
    ids: List[str] = []
    interfaces = batch_details.get("interfaces", [])
    if not isinstance(interfaces, list):
        return ids
    for it in interfaces:
        if isinstance(it, dict) and it.get("interface_id"):
            ids.append(str(it.get("interface_id")).strip())
    # 去重但保序
    seen: Set[str] = set()
    uniq: List[str] = []
    for iid in ids:
        if iid and iid not in seen:
            uniq.append(iid)
            seen.add(iid)
    return uniq


def interface_doc_exists(docs_dir: str, interface_id: str) -> bool:
    pattern = os.path.join(docs_dir, f"{interface_id}_*.md")
    return len(glob.glob(pattern)) > 0


def reset_interface_status(interface_list: Dict[str, Any], interface_ids: Set[str]) -> int:
    updated = 0
    for item in interface_list.get("interfaces", []):
        if not isinstance(item, dict):
            continue
        iid = str(item.get("interface_id", "")).strip()
        if iid in interface_ids:
            item["processing_status"] = "pending"
            item.pop("processed_at", None)
            item.pop("processing_time", None)
            updated += 1
    return updated


def reset_batch_status(repo_root: str, batch_number: int) -> Tuple[int, int]:
    """
    返回：mapping_reset_count, detail_status_reset_count
    """
    mapping_path = resolve_first_existing(repo_root, INTERFACE_BATCH_MAPPING_CANDIDATES)
    detail_status_path = os.path.join(repo_root, INTERFACE_DETAIL_BATCH_STATUS_REL)

    mapping_reset = 0
    detail_reset = 0

    if mapping_path and batch_number > 0:
        try:
            mapping = load_json(mapping_path)
            for b in mapping.get("batches", []):
                if isinstance(b, dict) and int(b.get("batch_number", -1)) == batch_number:
                    b["status"] = "pending"
                    b.pop("started_at", None)
                    b.pop("completed_at", None)
                    mapping_reset += 1
            save_json(mapping_path, mapping)
        except Exception:
            pass

    if os.path.exists(detail_status_path) and batch_number > 0:
        try:
            detail = load_json(detail_status_path)
            batch_mappings = detail.get("batch_mappings", [])
            for bm in batch_mappings:
                if isinstance(bm, dict) and int(bm.get("batch_number", -1)) == batch_number:
                    bm["status"] = "pending"
                    bm.pop("started_at", None)
                    bm.pop("completed_at", None)
                    detail_reset += 1

            # 重算聚合字段（避免显示“已完成”但仍缺失）
            total_batches = len(batch_mappings) if isinstance(batch_mappings, list) else 0
            processed_batches = 0
            failed_batches = 0
            if isinstance(batch_mappings, list):
                for bm in batch_mappings:
                    if not isinstance(bm, dict):
                        continue
                    st = bm.get("status")
                    if st == "completed":
                        processed_batches += 1
                    if st == "failed":
                        failed_batches += 1

            detail["total_batches"] = total_batches
            detail["processed_batches"] = processed_batches
            detail["failed_batches"] = failed_batches
            detail["current_batch"] = 0
            detail["status"] = "incomplete" if processed_batches < total_batches else "completed"
            detail["last_update"] = utc_now()
            save_json(detail_status_path, detail)
        except Exception:
            pass

    return mapping_reset, detail_reset


def main() -> int:
    parser = argparse.ArgumentParser(description="强制校验单个批次文档是否全生成")
    parser.add_argument("repo_root", help="仓库根目录")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--batch-number", type=int, help="接口批次号")
    group.add_argument("--batch-details-file", type=str, help="接口批次明细文件路径（相对或绝对）")
    args = parser.parse_args()

    repo_root = os.path.abspath(args.repo_root)
    if not os.path.isdir(repo_root):
        print(f"错误: 仓库根目录不存在: {repo_root}", file=sys.stderr)
        return 1

    docs_dir = os.path.join(repo_root, DOCS_DIR_REL)
    interface_list_path = os.path.join(repo_root, INTERFACE_LIST_REL)
    if not os.path.exists(interface_list_path):
        print(f"错误: interface-list.json 不存在: {interface_list_path}", file=sys.stderr)
        return 1
    if not os.path.isdir(docs_dir):
        print(f"错误: 文档目录不存在: {docs_dir}", file=sys.stderr)
        return 1

    if args.batch_number:
        batch_number = int(args.batch_number)
        batch_details_path = os.path.join(
            repo_root,
            ".cache/reverse/interfaces",
            f"interface-batch-details-{batch_number}.json",
        )
    else:
        batch_details_path = args.batch_details_file
        if not os.path.isabs(batch_details_path):
            batch_details_path = os.path.join(repo_root, batch_details_path)
        batch_number = parse_batch_details_file_for_batch_number(batch_details_path)

    if not os.path.isfile(batch_details_path):
        print(f"错误: 批次明细文件不存在: {batch_details_path}", file=sys.stderr)
        return 1

    interface_list = load_json(interface_list_path)
    batch_details = load_json(batch_details_path)
    interface_ids = set(find_interface_ids_from_batch_details(batch_details))

    if not interface_ids:
        print("错误: 批次明细中未找到 interface_id", file=sys.stderr)
        return 1

    missing_ids: List[str] = []
    for iid in sorted(interface_ids):
        if not interface_doc_exists(docs_dir, iid):
            missing_ids.append(iid)

    all_ok = len(missing_ids) == 0

    report_path = os.path.join(repo_root, REPORT_REL)
    report = {
        "version": "1.0",
        "generated_at": utc_now(),
        "batch_number": batch_number,
        "batch_details_file": os.path.relpath(batch_details_path, repo_root),
        "batch_interface_count": len(interface_ids),
        "missing_docs_count": len(missing_ids),
        "missing_interface_ids": missing_ids,
        "all_generated": all_ok,
    }

    if not all_ok:
        # 1) 回写缺失接口状态为 pending
        reset_cnt = reset_interface_status(interface_list, set(missing_ids))
        save_json(interface_list_path, interface_list)

        # 2) 回写批次状态为 pending（确保主流程能重试该批次）
        mapping_reset, detail_reset = reset_batch_status(repo_root, batch_number)
        report["reset_interface_status_count"] = reset_cnt
        report["reset_batch_mapping_count"] = mapping_reset
        report["reset_detail_batch_status_count"] = detail_reset

        save_json(report_path, report)
        print(json.dumps({"ok": False, "report": report_path, "batch_number": batch_number, "missing_docs_count": len(missing_ids)}, ensure_ascii=False))
        return 2

    save_json(report_path, report)
    print(json.dumps({"ok": True, "report": report_path, "batch_number": batch_number, "missing_docs_count": 0}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

