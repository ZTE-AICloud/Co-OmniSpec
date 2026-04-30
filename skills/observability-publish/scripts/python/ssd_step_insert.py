#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
从可观测性结果 JSON（主路径）或同结构的执行结果步骤数组写入 ssd_step_info。

主路径：omni-observability-result.json（含 step_results）。也接受根为步骤对象数组的 omni-execution-log.json。
可选：Markdown 内第一个 ```json ... ``` 代码块（兼容，非主流程）。

表字段：branch, sdd_step, start_time, end_time, execute_duration (BIGINT, 毫秒),
execute_result (success|failed|abort), input, output

用法:
  python ssd_step_insert.py --input-file path/to/omni-observability-result.json
  python ssd_step_insert.py --input-file path/to/omni-execution-log.json --dry-run
  python ssd_step_insert.py -i omni-observability-result.json --default-branch 002-xxx
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import pymysql

DB_CONFIG = {
    "host": "10.239.246.26",
    "port": 3306,
    "user": "bda_web",
    "password": "Wpdbv3.0@TEST",
    "database": "ssd_test",
    "charset": "utf8mb4",
    "autocommit": False,
}

INSERT_SQL = """
INSERT INTO ssd_step_info
(branch, sdd_step, start_time, end_time, execute_duration, execute_result, input, output)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
"""

_DATETIME_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}"
)


def _to_datetime_str(value: Any) -> str | None:
    """转为 MySQL DATETIME 可接受的 YYYY-MM-DD HH:MM:SS 字符串。"""
    if value is None:
        return None
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return None
        if _DATETIME_RE.match(s):
            try:
                dt = datetime.strptime(s.replace("T", " ")[:19], "%Y-%m-%d %H:%M:%S")
                return dt.strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                return None
    return None


def _to_time_str(value: Any) -> str | None:
    """转为 MySQL TIME 可接受的 HH:MM:SS 字符串。"""
    if value is None:
        return None
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return None
        dt = _to_datetime_str(s)
        if dt:
            return dt.split(" ", 1)[1]
        # 已是 HH:MM:SS 或 HH:MM
        parts = s.split(":")
        if len(parts) >= 2:
            try:
                h, m = int(parts[0]), int(parts[1])
                sec = int(parts[2]) if len(parts) > 2 else 0
                return f"{h:02d}:{m:02d}:{sec:02d}"
            except ValueError:
                return None
        return None
    return None


def _parse_duration_ms(value: Any, start: Any, end: Any) -> int | None:
    """执行时长统一为毫秒（BIGINT），与历史 insert 中毫秒语义一致。"""
    if value is not None:
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return int(value)
        if isinstance(value, str):
            s = value.strip().lower()
            if not s:
                pass
            elif s.isdigit():
                return int(s)
            else:
                # "2 min 2 sec" / "2min2sec" / "2 min"
                total_ms = 0
                m_min = re.search(r"(\d+)\s*min", s)
                m_sec = re.search(r"(\d+)\s*sec", s)
                if m_min:
                    total_ms += int(m_min.group(1)) * 60 * 1000
                if m_sec:
                    total_ms += int(m_sec.group(1)) * 1000
                if total_ms > 0:
                    return total_ms
    # 用起止时间推算：优先完整日期时间，其次回退到仅时分秒
    ds = None
    de = None
    dts = _to_datetime_str(start)
    dte = _to_datetime_str(end)
    if dts and dte:
        try:
            ds = datetime.strptime(dts, "%Y-%m-%d %H:%M:%S")
            de = datetime.strptime(dte, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            ds = None
            de = None
    if ds and de:
        sec = (de - ds).total_seconds()
        if sec < 0:
            return None
        return int(sec * 1000)

    # 回退：仅时分秒
    ts = _to_time_str(start)
    te = _to_time_str(end)
    if ts and te:
        try:
            # 同日假设
            ds = datetime.strptime(ts, "%H:%M:%S")
            de = datetime.strptime(te, "%H:%M:%S")
            delta = de - ds
            sec = delta.total_seconds()
            if sec < 0:
                sec += 24 * 3600
            return int(sec * 1000)
        except ValueError:
            pass
    return None


def _json_field(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, ensure_ascii=False)
    except TypeError:
        return str(value)


def _to_db_row(
    item: dict[str, Any],
    default_branch: str | None,
) -> tuple[Any, ...] | None:
    branch = item.get("branch")
    if branch is None or (isinstance(branch, str) and not str(branch).strip()):
        branch = default_branch
    if branch is None or (isinstance(branch, str) and not str(branch).strip()):
        return None
    branch = str(branch).strip()

    step = item.get("sdd_step")
    if step is None or (isinstance(step, str) and not str(step).strip()):
        step = item.get("step_name")
    if step is None or (isinstance(step, str) and not str(step).strip()):
        return None
    step = str(step).strip()

    raw_result = item.get("execute_result")
    if raw_result is None or (isinstance(raw_result, str) and not str(raw_result).strip()):
        return None
    result = str(raw_result).strip()

    raw_start = item.get("start_time")
    raw_end = item.get("end_time")
    start_value = (
        str(raw_start).strip()
        if raw_start is not None and str(raw_start).strip()
        else None
    )
    end_value = (
        str(raw_end).strip()
        if raw_end is not None and str(raw_end).strip()
        else None
    )
    if not start_value or not end_value:
        return None

    duration = _parse_duration_ms(item.get("execute_duration"), raw_start, raw_end)
    if duration is None:
        return None

    return (
        branch,
        step,
        start_value,
        end_value,
        duration,
        result,
        _json_field(item.get("input")),
        _json_field(item.get("output")),
    )


_JSON_FENCE_RE = re.compile(
    r"```\s*json\s*\n([\s\S]*?)```",
    re.IGNORECASE,
)


def _load_json_payload_from_path(path: Path) -> Any:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".md":
        m = _JSON_FENCE_RE.search(text)
        if not m:
            raise ValueError("Markdown 中未找到 ```json ... ``` 代码块")
        return json.loads(m.group(1).strip())
    return json.loads(text)


def load_step_rows(path: Path, default_branch: str | None) -> list[tuple[Any, ...]]:
    raw = _load_json_payload_from_path(path)
    outer_branch: str | None = None
    if isinstance(raw, dict):
        outer_branch = raw.get("branch") or raw.get("feature_desc")
        if "step_results" in raw:
            items = raw["step_results"]
        else:
            raise ValueError(
                "JSON 对象须包含 step_results 数组，或直接使用步骤数组作为根"
            )
    elif isinstance(raw, list):
        items = raw
    else:
        raise ValueError("JSON 须为对象（含 step_results）或步骤数组")

    if not isinstance(items, list):
        raise ValueError("step_results / 根数组 必须为列表")

    eff_default = (str(outer_branch).strip() if outer_branch else None) or default_branch

    rows: list[tuple[Any, ...]] = []
    skipped = 0
    for i, obj in enumerate(items):
        if not isinstance(obj, dict):
            skipped += 1
            print(f"跳过非对象项 index={i}", file=sys.stderr)
            continue
        row = _to_db_row(obj, eff_default)
        if row is None:
            skipped += 1
            print(f"跳过无效项 index={i}（缺 branch/sdd_step/时间/时长/execute_result）", file=sys.stderr)
            continue
        rows.append(row)

    if skipped:
        print(f"共计跳过 {skipped} 条无效项，待插入 {len(rows)} 条", file=sys.stderr)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(
        description="将步骤执行 JSON（或含 JSON 块的 md）写入 ssd_step_info"
    )
    parser.add_argument(
        "--input-file",
        "-i",
        required=True,
        type=Path,
        help="omni-observability-result.json（推荐）或 omni-execution-log.json（步骤数组）；可选 .md（内嵌 json 块）",
    )
    parser.add_argument(
        "--default-branch",
        default=None,
        help="当行内无 branch 且根对象无 branch/feature_desc 时使用的分支名",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只解析并校验，不连接数据库、不写入",
    )
    args = parser.parse_args()

    if not args.input_file.is_file():
        print(f"文件不存在: {args.input_file}", file=sys.stderr)
        sys.exit(1)

    rows = load_step_rows(args.input_file, args.default_branch)
    if not rows:
        print("没有可插入的记录", file=sys.stderr)
        sys.exit(1)

    if args.dry_run:
        print(f"[dry-run] 将插入 {len(rows)} 条，不入库")
        return

    connection = pymysql.connect(**DB_CONFIG)
    try:
        with connection.cursor() as cursor:
            cursor.executemany(INSERT_SQL, rows)
        connection.commit()
        print(f"插入成功，条数: {len(rows)}")
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


if __name__ == "__main__":
    main()
