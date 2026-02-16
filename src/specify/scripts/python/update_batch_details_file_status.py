#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
根据接口识别的临时产出文件回写 batch-details-{n}.json 中每个文件的处理状态。

场景（接口清单识别阶段 / interface-recognizer）：
- 输入批次文件：{REPO_ROOT}/.cache/omni-reverse/interfaces/batch-details-{batch_number}.json
- 临时产出文件：{REPO_ROOT}/.cache/omni-reverse/interfaces/temp/interface-{batch_number}-{file_index}.json

规则：
- 若对应临时文件存在且可解析为JSON（dict/list均可），将该文件条目状态置为 completed
- 若临时文件不存在，不修改（保留 pending/processing 以支持断点续跑）
- 若临时文件存在但JSON不可解析，将状态置为 failed（可选：便于快速定位坏文件）

用法：
  python3 update_batch_details_file_status.py --repo-root <repo_root> --batch-number <n> [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union


JsonObj = Dict[str, Any]
FileEntry = Union[str, JsonObj]


def _utc_ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_json(path: str, data: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _is_valid_temp_json(path: str) -> Tuple[bool, str]:
    try:
        data = _load_json(path)
    except Exception as e:
        return False, str(e)
    if isinstance(data, (dict, list)):
        return True, ""
    return False, f"unexpected_json_type:{type(data).__name__}"


def _normalize_files(files: Any) -> List[JsonObj]:
    """
    统一为对象数组格式：[{path, status}, ...]
    - 旧格式：["a.py", "b.py"]
    - 新格式：[{"path":"a.py","status":"pending"}, ...]
    """
    if not isinstance(files, list):
        raise ValueError("batch-details.files 必须是数组")

    normalized: List[JsonObj] = []
    for entry in files:
        if isinstance(entry, str):
            normalized.append({"path": entry, "status": "pending"})
        elif isinstance(entry, dict):
            path = entry.get("path")
            if not isinstance(path, str) or not path:
                raise ValueError(f"files 条目缺少有效 path: {entry}")
            status = entry.get("status", "pending")
            if not isinstance(status, str) or not status:
                status = "pending"
            normalized.append({"path": path, "status": status})
        else:
            raise ValueError(f"files 条目类型不支持: {type(entry).__name__}")
    return normalized


def _derive_batch_status(file_statuses: List[str]) -> str:
    """
    根据文件条目状态推导批次状态：
    - 全 pending -> pending
    - 存在 pending/processing 且存在 completed/failed -> processing
    - 全 completed/failed，且至少一个 completed -> completed
    - 全 failed -> failed
    """
    if not file_statuses:
        return "pending"

    unique = set(file_statuses)
    if unique == {"pending"}:
        return "pending"
    if "processing" in unique:
        return "processing"
    if "pending" in unique:
        # 既有已完成/失败，也有待处理
        return "processing"
    if unique.issubset({"completed", "failed"}):
        if "completed" in unique:
            return "completed"
        return "failed"
    # 兜底：尽量不报错，避免阻塞流水线
    return "processing"


@dataclass
class UpdateResult:
    changed: bool
    updated_files: int
    failed_files: int
    skipped_files: int


def update_batch_details_status(repo_root: str, batch_number: int, dry_run: bool = False) -> UpdateResult:
    cache_dir = os.path.join(repo_root, ".cache", "omni-reverse", "interfaces")
    batch_details_path = os.path.join(cache_dir, f"batch-details-{batch_number}.json")
    temp_dir = os.path.join(cache_dir, "temp")

    if not os.path.exists(batch_details_path):
        raise FileNotFoundError(f"批次详情文件不存在: {batch_details_path}")

    batch_details = _load_json(batch_details_path)
    files = _normalize_files(batch_details.get("files", []))

    updated_files = 0
    failed_files = 0
    skipped_files = 0
    changed = False

    for idx, entry in enumerate(files):
        temp_path = os.path.join(temp_dir, f"interface-{batch_number}-{idx}.json")
        if not os.path.exists(temp_path):
            skipped_files += 1
            continue

        ok, err = _is_valid_temp_json(temp_path)
        if ok:
            if entry.get("status") != "completed":
                entry["status"] = "completed"
                updated_files += 1
                changed = True
        else:
            # 临时文件存在但无法解析 -> failed（便于排查坏文件）
            if entry.get("status") != "failed":
                entry["status"] = "failed"
                entry["error"] = f"invalid_temp_json:{err}"
                failed_files += 1
                changed = True

    # 回写 files（保持对象数组格式）
    batch_details["files"] = files

    # 推导并回写批次 status/last_updated
    new_batch_status = _derive_batch_status([e.get("status", "pending") for e in files])
    if batch_details.get("status") != new_batch_status:
        batch_details["status"] = new_batch_status
        changed = True
    batch_details["last_updated"] = _utc_ts()

    if changed and not dry_run:
        _save_json(batch_details_path, batch_details)

    return UpdateResult(
        changed=changed,
        updated_files=updated_files,
        failed_files=failed_files,
        skipped_files=skipped_files,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="回写 batch-details 文件内每个文件条目的处理状态")
    parser.add_argument("--repo-root", required=True, help="仓库根目录路径")
    parser.add_argument("--batch-number", type=int, required=True, help="批次编号（>=1）")
    parser.add_argument("--dry-run", action="store_true", help="仅计算变更，不写入文件")
    args = parser.parse_args()

    repo_root = args.repo_root
    batch_number = args.batch_number

    if not os.path.isdir(repo_root):
        print(f"错误: 仓库根目录不存在: {repo_root}", file=sys.stderr)
        sys.exit(1)
    if batch_number < 1:
        print(f"错误: batch-number 必须 >= 1: {batch_number}", file=sys.stderr)
        sys.exit(1)

    try:
        result = update_batch_details_status(repo_root, batch_number, dry_run=args.dry_run)
        print(
            json.dumps(
                {
                    "ok": True,
                    "batch_number": batch_number,
                    "changed": result.changed,
                    "updated_files": result.updated_files,
                    "failed_files": result.failed_files,
                    "skipped_files": result.skipped_files,
                },
                ensure_ascii=False,
            )
        )
    except Exception as e:
        print(json.dumps({"ok": False, "batch_number": batch_number, "error": str(e)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()


