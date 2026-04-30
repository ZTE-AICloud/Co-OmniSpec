#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
根据 omni-execution-log.json（根为步骤对象数组）清洗生成 omni-observability-result.json。

输出结构与输入保持一致：根为步骤对象数组。

规则：按 sdd_step（无则 step_name）分组，同一键多条时取最后一次：
  1) end_time 可比 → 取最大 end_time；
  2) 否则 start_time 可比 → 取最大 start_time；
  3) 否则取数组中下标最大者。

用法:
  python omni_build_observability_result.py -i changes/xxx/omni-execution-log.json
  python omni_build_observability_result.py -i omni-execution-log.json -o out.json
  python omni_build_observability_result.py -i omni-execution-log.json --default-branch 002-foo
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any

# 与 ssd_step_insert 一致：可入库的枚举
_EXECUTE_RESULT_ALIASES: dict[str, str] = {
    "success": "success",
    "failed": "failed",
    "failure": "failed",
    "fail": "failed",
    "error": "failed",
    "abort": "abort",
    "aborted": "abort",
    "completed": "success",
    "complete": "success",
    "done": "success",
    "ok": "success",
}


def _normalize_execute_result(raw: str | None) -> str | None:
    if raw is None or not str(raw).strip():
        return None
    return _EXECUTE_RESULT_ALIASES.get(str(raw).strip().lower())


def _step_key(rec: dict[str, Any]) -> str | None:
    s = rec.get("sdd_step")
    if s is not None and str(s).strip():
        return str(s).strip()
    s = rec.get("step_name")
    if s is not None and str(s).strip():
        return str(s).strip()
    return None


def parse_datetime(val: Any) -> datetime | None:
    if val is None:
        return None
    s = str(val).strip()
    if not s:
        return None
    s = s.replace("Z", "").split(".")[0]
    s = s.replace("T", " ", 1)
    if len(s) >= 19:
        s = s[:19]
    try:
        return datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


def _pick_winner(
    indexed: list[tuple[int, dict[str, Any]]],
) -> tuple[dict[str, Any], str]:
    """返回 (胜出记录的副本（将补全 sdd_step）, selected_from)。"""
    if len(indexed) == 1:
        _, rec = indexed[0]
        out = deepcopy(rec)
        sk = _step_key(rec)
        if sk:
            out["sdd_step"] = sk
        return out, "single"

    with_end = [(i, r) for i, r in indexed if parse_datetime(r.get("end_time"))]
    if with_end:
        i, rec = max(
            with_end,
            key=lambda x: (
                parse_datetime(x[1]["end_time"]) or datetime.min,
                parse_datetime(x[1].get("start_time")) or datetime.min,
                x[0],
            ),
        )
        out = deepcopy(rec)
        out["sdd_step"] = _step_key(rec) or ""
        return out, "end_time"

    with_start = [(i, r) for i, r in indexed if parse_datetime(r.get("start_time"))]
    if with_start:
        i, rec = max(
            with_start,
            key=lambda x: (
                parse_datetime(x[1]["start_time"]) or datetime.min,
                x[0],
            ),
        )
        out = deepcopy(rec)
        out["sdd_step"] = _step_key(rec) or ""
        return out, "start_time"

    i, rec = max(indexed, key=lambda x: x[0])
    out = deepcopy(rec)
    out["sdd_step"] = _step_key(rec) or ""
    return out, "array_order"


def build_observability(
    items: list[dict[str, Any]],
    *,
    default_branch: str | None,
) -> list[dict[str, Any]]:
    dedupe_candidates: list[tuple[int, dict[str, Any]]] = []

    for idx, raw in enumerate(items):
        if not isinstance(raw, dict):
            print(f"跳过非对象元素 index={idx}", file=sys.stderr)
            continue
        sk = _step_key(raw)
        if not sk:
            print(
                f"跳过缺少 sdd_step/step_name 的元素 index={idx}",
                file=sys.stderr,
            )
            continue
        dedupe_candidates.append((idx, raw))

    groups: dict[str, list[tuple[int, dict[str, Any]]]] = defaultdict(list)
    for i, r in dedupe_candidates:
        groups[_step_key(r) or ""].append((i, r))

    step_results: list[dict[str, Any]] = []
    for key in sorted(groups.keys()):
        grp = groups[key]
        winner, _selected_from = _pick_winner(grp)
        # 规范化 execute_result；无法映射时保留原值，不在本阶段丢弃记录
        if winner.get("execute_result") is not None:
            n = _normalize_execute_result(str(winner["execute_result"]).strip())
            if n:
                winner["execute_result"] = n
        step_results.append(winner)

    # 若记录缺 branch，可按入参补默认 branch（保持步骤对象结构不变）
    if default_branch:
        for rec in step_results:
            if rec.get("branch") is None or not str(rec.get("branch")).strip():
                rec["branch"] = default_branch

    return step_results


def main() -> None:
    parser = argparse.ArgumentParser(
        description="从 omni-execution-log.json 生成 omni-observability-result.json"
    )
    parser.add_argument(
        "-i",
        "--input",
        required=True,
        type=Path,
        help="omni-execution-log.json 路径",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="输出路径，默认与输入同目录下的 omni-observability-result.json",
    )
    parser.add_argument(
        "--default-branch",
        default=None,
        help="当日志中无 branch 时写入根级 branch",
    )
    args = parser.parse_args()

    if not args.input.is_file():
        print(f"文件不存在: {args.input}", file=sys.stderr)
        sys.exit(1)

    raw = json.loads(args.input.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        print("执行日志须为 JSON 数组", file=sys.stderr)
        sys.exit(1)

    items: list[dict[str, Any]] = []
    for i, x in enumerate(raw):
        if isinstance(x, dict):
            items.append(x)
        else:
            print(f"跳过非对象元素 index={i}", file=sys.stderr)

    out_path = args.output
    if out_path is None:
        out_path = args.input.parent / "omni-observability-result.json"

    payload = build_observability(
        items,
        default_branch=args.default_branch,
    )

    # 若已存在旧结果文件，先删除再重建，避免残留内容影响判断
    if out_path.exists():
        out_path.unlink()

    out_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"已写入: {out_path}（records={len(payload)}）")


if __name__ == "__main__":
    main()
