#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
接口数量质量闸门校验工具
校验 interface-list.json 的实际数量与预估数量是否基本一致，并输出全量检查与建议。

使用方法:
    python validate_interface_quality_gate.py <repo_root> [--lower 0.9] [--upper 1.3]
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict


ESTIMATION_PATH = ".cache/reverse/interfaces/interface-estimation.json"
INTERFACE_LIST_PATH = ".cache/reverse/interfaces/interface-list.json"
OUTPUT_REPORT_PATH = ".cache/reverse/interfaces/interface-quality-report.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: str, data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def count_by_type(interface_list: Dict[str, Any]) -> Dict[str, int]:
    result: Dict[str, int] = {}
    for item in interface_list.get("interfaces", []):
        t = str(item.get("interface_type", "其他"))
        result[t] = result.get(t, 0) + 1
    return result


def has_full_list(interface_list: Dict[str, Any]) -> bool:
    interfaces = interface_list.get("interfaces")
    if not isinstance(interfaces, list):
        return False
    # 至少要求每项有 interface_id 和 name，避免“示例化”产物混入
    for item in interfaces:
        if not isinstance(item, dict):
            return False
        if not item.get("interface_id") or not item.get("name"):
            return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="接口数量质量闸门校验工具")
    parser.add_argument("repo_root", help="仓库根目录")
    parser.add_argument("--lower", type=float, default=0.9, help="下限系数")
    parser.add_argument("--upper", type=float, default=1.3, help="上限系数")
    args = parser.parse_args()

    repo_root = os.path.abspath(args.repo_root)
    if not os.path.isdir(repo_root):
        print(f"错误: 仓库根目录不存在: {repo_root}", file=sys.stderr)
        return 1

    estimation_file = os.path.join(repo_root, ESTIMATION_PATH)
    interface_list_file = os.path.join(repo_root, INTERFACE_LIST_PATH)
    output_report_file = os.path.join(repo_root, OUTPUT_REPORT_PATH)

    if not os.path.exists(estimation_file):
        print(f"错误: 预估文件不存在: {estimation_file}", file=sys.stderr)
        return 1
    if not os.path.exists(interface_list_file):
        print(f"错误: 接口清单不存在: {interface_list_file}", file=sys.stderr)
        return 1

    estimation = load_json(estimation_file)
    interface_list = load_json(interface_list_file)

    estimated_total = int(estimation.get("estimated_total_interfaces", 0))
    baseline_min = int(estimation.get("baseline_min_interfaces", 0))
    actual_total = len(interface_list.get("interfaces", []))

    lower_bound = int(round(estimated_total * args.lower))
    upper_bound = int(round(estimated_total * args.upper))
    full_list_generated = has_full_list(interface_list)
    actual_by_type = count_by_type(interface_list)

    status = "pass"
    recommendations = []
    mandatory_flags = {
        "estimation_generated": True,
        "quantity_validation_done": True,
        "rescan_if_needed_done": False,
        "full_list_generated": full_list_generated,
        "quality_gate_passed": False
    }

    if actual_total < max(baseline_min, lower_bound):
        status = "too_few"
        recommendations = [
            "当前识别数量低于预估下限，建议放宽约束规则后重扫",
            "建议扩大扫描范围；若仍不足，开启全文件扫描",
            "交互模式下可由用户调整接口类型权重或手动指定路径/类型"
        ]
    elif actual_total > upper_bound:
        status = "too_many"
        recommendations = [
            "当前识别数量高于预估上限，建议提高置信度阈值并重筛",
            "建议按核心接口类型组合筛选（REST/RPC/消息等）",
            "交互模式下支持用户注入筛选规则后重新生成清单"
        ]
    elif not full_list_generated:
        status = "invalid_list"
        recommendations = [
            "interface-list.json 未通过全量清单校验（字段不完整或存在示例化输出）",
            "请重新生成全量接口清单，确保每个接口包含 interface_id 和 name"
        ]

    if status != "pass":
        mandatory_flags["rescan_if_needed_done"] = True
        mandatory_flags["quality_gate_passed"] = False
    else:
        mandatory_flags["rescan_if_needed_done"] = True
        mandatory_flags["quality_gate_passed"] = True

    report = {
        "version": "1.0",
        "generated_at": utc_now(),
        "estimated_total_interfaces": estimated_total,
        "baseline_min_interfaces": baseline_min,
        "actual_total_interfaces": actual_total,
        "estimated_bounds": {
            "lower": lower_bound,
            "upper": upper_bound
        },
        "actual_by_type": actual_by_type,
        "status": status,
        "recommendations": recommendations,
        "mandatory_flags": mandatory_flags
    }

    save_json(output_report_file, report)
    print(json.dumps({
        "ok": status == "pass",
        "status": status,
        "report": output_report_file,
        "actual_total_interfaces": actual_total,
        "estimated_total_interfaces": estimated_total
    }, ensure_ascii=False))

    return 0 if status == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
