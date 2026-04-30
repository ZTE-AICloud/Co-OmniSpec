#!/usr/bin/env python3
"""
Eval: ai-friendly-component-srp-orchestrate / gate-check.py
验证门禁脚本的阈值判定契约。
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).parent.parent / "scripts" / "gate-check.py"


def run(script_path: Path, *args) -> tuple[int, str, str]:
    result = subprocess.run(
        [sys.executable, str(script_path), *args],
        capture_output=True, text=True
    )
    return result.returncode, result.stdout, result.stderr


def eval_gate():
    passed, failed = [], []

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        config_path = tmpdir / "gate.json"
        input_path = tmpdir / "summary.json"
        output_path = tmpdir / "gate-result.json"

        # ── Case 1: 通过门禁（满足所有阈值）────────────────────────────────
        config_path.write_text(json.dumps({
            "min_avg_score": 0.7,
            "max_avg_violation_count": 5,
            "min_confidence": 0.6
        }))
        input_path.write_text(json.dumps({
            "core_metrics": {
                "total_score": 0.85,
                "total_violation_count": 3,
                "confidence_score": 0.8
            }
        }))

        rc, out, err = run(SCRIPT,
            "--input", str(input_path),
            "--config", str(config_path),
            "--output", str(output_path)
        )
        if rc == 0 and output_path.exists():
            result = json.loads(output_path.read_text())
            if result.get("gate_passed") is True:
                passed.append("Case1: 满足阈值时 gate_passed=true，exit=0")
            else:
                failed.append(f"Case1: 应通过但 gate_passed={result.get('gate_passed')}")
        else:
            failed.append(f"Case1: rc={rc}")

        # ── Case 2: 分数低于阈值时应失败 ───────────────────────────────────
        input_path.write_text(json.dumps({
            "core_metrics": {
                "total_score": 0.5,   # < 0.7
                "total_violation_count": 2,
                "confidence_score": 0.8
            }
        }))
        rc2, _, err2 = run(SCRIPT,
            "--input", str(input_path),
            "--config", str(config_path),
            "--output", str(output_path)
        )
        if rc2 != 0 and output_path.exists():
            result2 = json.loads(output_path.read_text())
            if result2.get("gate_passed") is False:
                passed.append("Case2: 分数 < 0.7 时 gate_passed=false，exit=1")
            else:
                failed.append("Case2: 分数低于阈值应失败")
        else:
            failed.append("Case2: 脚本应返回非零退出码")

        # ── Case 3: 违规数超过阈值时应失败 ──────────────────────────────────
        input_path.write_text(json.dumps({
            "core_metrics": {
                "total_score": 0.85,
                "total_violation_count": 10,  # > 5
                "confidence_score": 0.8
            }
        }))
        rc3, _, _ = run(SCRIPT,
            "--input", str(input_path),
            "--config", str(config_path),
            "--output", str(output_path)
        )
        if rc3 != 0:
            passed.append("Case3: total_violation_count > max 时失败")
        else:
            failed.append("Case3: 违规数超限应返回非零退出码")

        # ── Case 4: 置信度低于阈值时应失败 ──────────────────────────────────
        input_path.write_text(json.dumps({
            "core_metrics": {
                "total_score": 0.85,
                "total_violation_count": 2,
                "confidence_score": 0.4   # < 0.6
            }
        }))
        rc4, _, _ = run(SCRIPT,
            "--input", str(input_path),
            "--config", str(config_path),
            "--output", str(output_path)
        )
        if rc4 != 0:
            passed.append("Case4: confidence_score < 0.6 时失败")
        else:
            failed.append("Case4: 置信度低于阈值应返回非零退出码")

        # ── Case 5: 配置文件不存在时使用默认值并继续 ───────────────────────
        # 使用独立临时目录避免与其他 case 共享 input_path
        import tempfile as tp5
        with tp5.TemporaryDirectory() as t5:
            t5 = Path(t5)
            case5_input = t5 / "summary5.json"
            case5_output = t5 / "gate-result5.json"
            case5_input.write_text(json.dumps({
                "core_metrics": {
                    "total_score": 0.85,
                    "total_violation_count": 3,
                    "confidence_score": 0.8
                }
            }))
            rc5, _, _ = run(SCRIPT,
                "--input", str(case5_input),
                "--config", str(t5 / "nonexistent.json"),
                "--output", str(case5_output)
            )
            if rc5 == 0 and case5_output.exists():
                result5 = json.loads(case5_output.read_text())
                thresholds5 = result5.get("thresholds", {})
                if thresholds5.get("min_avg_score") == 0.7:
                    passed.append("Case5: 配置文件缺失时使用默认值（min_avg_score=0.7）")
                else:
                    failed.append(f"Case5: 默认阈值错误 thresholds={thresholds5}")
            else:
                failed.append(f"Case5: rc={rc5} output_exists={case5_output.exists()}")

        # ── Case 6: 输出包含 actual_values ─────────────────────────────────
        if output_path.exists():
            result6 = json.loads(output_path.read_text())
            if "actual_values" in result6 and "thresholds" in result6:
                passed.append("Case6: 输出包含 actual_values 和 thresholds")
            else:
                failed.append("Case6: 输出缺少 actual_values 或 thresholds")

        # ── Case 7: violations 字段列出失败原因 ─────────────────────────────
        input_path.write_text(json.dumps({
            "core_metrics": {
                "total_score": 0.3,
                "total_violation_count": 100,
                "confidence_score": 0.1
            }
        }))
        rc7, _, _ = run(SCRIPT,
            "--input", str(input_path),
            "--config", str(config_path),
            "--output", str(output_path)
        )
        if output_path.exists():
            result7 = json.loads(output_path.read_text())
            violations7 = result7.get("violations", [])
            if len(violations7) >= 3:
                passed.append(f"Case7: violations 列出所有失败原因（{len(violations7)} 条）")
            else:
                failed.append(f"Case7: violations 应列出 3 条原因，实际 {len(violations7)} 条")
        else:
            failed.append("Case7: gate-result.json 未生成")

    return passed, failed


if __name__ == "__main__":
    p, f = eval_gate()
    print("=" * 60)
    print("Eval: ai-friendly-component-srp-orchestrate / gate-check.py")
    print("=" * 60)
    for t in p:
        print(f"  [PASS] {t}")
    for t in f:
        print(f"  [FAIL] {t}")
    print()
    if f:
        print(f"Result: {len(p)} passed, {len(f)} failed")
        sys.exit(1)
    else:
        print(f"Result: {len(p)} passed, 0 failed — ALL PASSED")
        sys.exit(0)
