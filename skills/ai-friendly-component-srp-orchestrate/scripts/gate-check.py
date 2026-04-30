#!/usr/bin/env python3
"""
门禁判定脚本：根据阈值判定 SRP 分析结果是否通过
"""
import argparse
import json
import sys
from pathlib import Path


def load_config(config_path: str) -> dict:
    """加载门禁配置"""
    if not Path(config_path).exists():
        return {
            "min_avg_score": 70,
            "max_avg_violation_count": 5,
            "min_confidence": 0.6
        }
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def check_gate(summary: dict, thresholds: dict):
    """执行门禁检查，返回 (passed: bool, violations: list)"""
    core = summary.get("core_metrics", {})
    violations = []

    avg_score = core.get("total_score", 0.0)
    avg_violation = core.get("total_violation_count", 0)
    avg_confidence = core.get("confidence_score", 0.0)

    if avg_score < thresholds["min_avg_score"]:
        violations.append(f"total_score {avg_score:.4f} < {thresholds['min_avg_score']}")

    if avg_violation > thresholds["max_avg_violation_count"]:
        violations.append(f"total_violation_count {avg_violation} > {thresholds['max_avg_violation_count']}")

    if avg_confidence < thresholds["min_confidence"]:
        violations.append(f"confidence_score {avg_confidence:.4f} < {thresholds['min_confidence']}")

    return len(violations) == 0, violations


def main():
    parser = argparse.ArgumentParser(description="Gate check for SRP analysis")
    parser.add_argument("--input", required=True, help="summary.json path")
    parser.add_argument("--config", default=".gate-config.json", help="Gate config path")
    parser.add_argument("--output", default="output/gate-result.json", help="Output gate result")
    args = parser.parse_args()

    with open(args.input, 'r', encoding='utf-8') as f:
        summary = json.load(f)

    thresholds = load_config(args.config)
    passed, violations = check_gate(summary, thresholds)

    result = {
        "gate_passed": passed,
        "thresholds": thresholds,
        "actual_values": {
            "total_score": summary.get("core_metrics", {}).get("total_score", 0.0),
            "total_violation_count": summary.get("core_metrics", {}).get("total_violation_count", 0),
            "confidence_score": summary.get("core_metrics", {}).get("confidence_score", 0.0)
        },
        "violations": violations
    }

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    if passed:
        print(f"[ok] Gate passed")
        sys.exit(0)
    else:
        print(f"[error] Gate failed: {', '.join(violations)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
