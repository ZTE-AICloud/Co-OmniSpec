#!/usr/bin/env python3
"""
Eval: ai-friendly-arch-measure / aggregate-metrics.py
验证脚本的输入/输出契约是否正确。
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).parent.parent / "scripts" / "aggregate-metrics.py"
SKILL_DIR = SCRIPT.parent.parent


def run(script_path: Path, *args) -> tuple[int, str, str]:
    result = subprocess.run(
        [sys.executable, str(script_path), *args],
        capture_output=True, text=True
    )
    return result.returncode, result.stdout, result.stderr


def eval_aggregate():
    passed, failed = [], []

    # ── 准备临时目录 ──────────────────────────────────────────────────────────
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        state_dir = tmpdir / "state"
        output_dir = tmpdir / "output"
        state_dir.mkdir()
        output_dir.mkdir()

        # ── Case 1: 正常场景 - 单一成功 skill ─────────────────────────────────
        (output_dir / "srp").mkdir()
        (output_dir / "srp" / "summary.json").write_text(json.dumps({
            "identity_info": {"skill_id": "ai-friendly-component-srp-orchestrate", "arch_dimension": "结构可导航性"},
            "execution_ctx": {"skill_version": "v1.0", "scan_mode": "full", "execute_status": "success", "start_time": "", "end_time": "", "duration_ms": 100},
            "core_metrics": {"total_score": 0.85, "confidence_score": 0.8, "total_violation_count": 5, "p0_violation_count": 0, "p1_violation_count": 5},
            "evaluation_details": {},
            "violation_records": {"level_summary": {"P0": 0, "P1": 5}, "violation_infos": [], "exempt_infos": []},
            "scan_statistics": {"total_units": {"modules": 10}, "violation_units": {"modules": 2}, "valid_units": {"modules": 8}}
        }, ensure_ascii=False))

        (state_dir / "resolved-skills.json").write_text(json.dumps({
            "execute_mode": "default",
            "resolved": [{"skill_id": "ai-friendly-component-srp-orchestrate", "dimension": "结构可导航性", "output_path_hint": "output/srp/summary.json"}],
            "skipped": []
        }))

        rc, out, err = run(SCRIPT,
            "--resolved-skills", str(state_dir / "resolved-skills.json"),
            "--output-dir", str(output_dir),
            "--output", str(output_dir / "arch-measure-report.json"),
            "--project-path", "/test/project",
            "--project-id", "test-project",
            "--component-id", "test-component"
        )

        if rc == 0 and (output_dir / "arch-measure-report.json").exists():
            report = json.loads((output_dir / "arch-measure-report.json").read_text())
            if "aia_metric_fact" in report and "aia_component_summary" in report:
                passed.append("Case1: 正常场景输出包含两个 top-level key")
            else:
                failed.append("Case1: 输出缺少 aia_metric_fact 或 aia_component_summary")
        else:
            failed.append(f"Case1: 脚本失败 rc={rc} err={err.strip()}")

        # ── Case 2: aia_component_summary.identity_info 字段完整 ───────────────
        if "aia_component_summary" in locals() or (output_dir / "arch-measure-report.json").exists():
            report = json.loads((output_dir / "arch-measure-report.json").read_text())
            identity = report["aia_component_summary"]["identity_info"]
            required = ["project_id", "component_id", "component_name", "component_repo", "tool_version"]
            missing = [f for f in required if f not in identity]
            if not missing:
                passed.append("Case2: aia_component_summary.identity_info 字段完整")
            else:
                failed.append(f"Case2: identity_info 缺少字段 {missing}")

        # ── Case 3: aia_metric_fact 包含完整详情（不截断） ────────────────────
        if (output_dir / "arch-measure-report.json").exists():
            report = json.loads((output_dir / "arch-measure-report.json").read_text())
            fact = report["aia_metric_fact"][0]
            if "violation_records" in fact and "evaluation_details" in fact:
                passed.append("Case3: aia_metric_fact 保留 violation_records 和 evaluation_details")
            else:
                failed.append("Case3: aia_metric_fact 丢失了详情字段")

        # ── Case 4: total_score_avg 仅统计 success skill ──────────────────────
        (output_dir / "srp" / "summary.json").write_text(json.dumps({
            "identity_info": {"skill_id": "s1", "arch_dimension": "结构可导航性"},
            "execution_ctx": {"skill_version": "v1.0", "scan_mode": "full", "execute_status": "success", "start_time": "", "end_time": "", "duration_ms": 0},
            "core_metrics": {"total_score": 0.9, "confidence_score": 0.8, "total_violation_count": 0, "p0_violation_count": 0, "p1_violation_count": 0},
            "evaluation_details": {}, "violation_records": {}, "scan_statistics": {}
        }))
        (output_dir / "failed").mkdir()
        (output_dir / "failed" / "summary.json").write_text(json.dumps({
            "identity_info": {"skill_id": "s2-failed", "arch_dimension": "上下文窗口适配性"},
            "execution_ctx": {"skill_version": "v1.0", "scan_mode": "full", "execute_status": "failed", "start_time": "", "end_time": "", "duration_ms": 0},
            "core_metrics": {"total_score": 0.3, "confidence_score": 0.0, "total_violation_count": 10, "p0_violation_count": 0, "p1_violation_count": 0},
            "evaluation_details": {}, "violation_records": {}, "scan_statistics": {}
        }))
        (state_dir / "resolved-skills.json").write_text(json.dumps({
            "execute_mode": "default",
            "resolved": [
                {"skill_id": "s1", "dimension": "结构可导航性", "output_path_hint": "output/srp/summary.json"},
                {"skill_id": "s2-failed", "dimension": "上下文窗口适配性", "output_path_hint": "output/failed/summary.json"}
            ],
            "skipped": []
        }))

        rc2, _, _ = run(SCRIPT,
            "--resolved-skills", str(state_dir / "resolved-skills.json"),
            "--output-dir", str(output_dir),
            "--output", str(output_dir / "arch-measure-report.json"),
            "--project-path", "/test"
        )
        if rc2 == 0:
            report2 = json.loads((output_dir / "arch-measure-report.json").read_text())
            avg = report2["aia_component_summary"]["scan_result"]["total_score_avg"]
            if abs(avg - 0.9) < 0.001:
                passed.append("Case4: total_score_avg 仅统计 success skill (0.9)，不含 failed (0.3)")
            else:
                failed.append(f"Case4: total_score_avg={avg}，期望 0.9")
        else:
            failed.append("Case4: 脚本执行失败")

        # ── Case 5: skill 输出文件不存在时生成最小占位 fact ──────────────────
        (state_dir / "resolved-skills.json").write_text(json.dumps({
            "execute_mode": "default",
            "resolved": [{"skill_id": "ghost-skill", "dimension": "测试维度", "output_path_hint": "output/ghost/summary.json"}],
            "skipped": []
        }))
        rc3, _, _ = run(SCRIPT,
            "--resolved-skills", str(state_dir / "resolved-skills.json"),
            "--output-dir", str(output_dir),
            "--output", str(output_dir / "arch-measure-report.json"),
            "--project-path", "/test"
        )
        if rc3 == 0:
            report3 = json.loads((output_dir / "arch-measure-report.json").read_text())
            ghost_fact = next((f for f in report3["aia_metric_fact"] if f["identity_info"]["skill_id"] == "ghost-skill"), None)
            if ghost_fact and ghost_fact["execution_ctx"]["execute_status"] == "failed":
                passed.append("Case5: 输出文件不存在时生成 failed 占位 fact")
            else:
                failed.append("Case5: 缺失 skill 未生成占位 fact")
        else:
            failed.append("Case5: 脚本失败")

        # ── Case 6: skipped skill 追加到 aia_metric_fact 列表 ───────────────
        (output_dir / "srp" / "summary.json").write_text(json.dumps({
            "identity_info": {"skill_id": "s1", "arch_dimension": "结构可导航性"},
            "execution_ctx": {"skill_version": "v1.0", "scan_mode": "full", "execute_status": "success", "start_time": "", "end_time": "", "duration_ms": 0},
            "core_metrics": {"total_score": 0.7, "confidence_score": 0.8, "total_violation_count": 0, "p0_violation_count": 0, "p1_violation_count": 0},
            "evaluation_details": {}, "violation_records": {}, "scan_statistics": {}
        }))
        (state_dir / "resolved-skills.json").write_text(json.dumps({
            "execute_mode": "default",
            "resolved": [{"skill_id": "s1", "dimension": "结构可导航性", "output_path_hint": "output/srp/summary.json"}],
            "skipped": [{"skill_id": "ai-friendly-metric-token-count"}]
        }))
        rc4, _, _ = run(SCRIPT,
            "--resolved-skills", str(state_dir / "resolved-skills.json"),
            "--output-dir", str(output_dir),
            "--output", str(output_dir / "arch-measure-report.json"),
            "--project-path", "/test"
        )
        if rc4 == 0:
            report4 = json.loads((output_dir / "arch-measure-report.json").read_text())
            skipped_fact = next((f for f in report4["aia_metric_fact"] if f["identity_info"]["skill_id"] == "ai-friendly-metric-token-count"), None)
            if skipped_fact and skipped_fact["execution_ctx"]["execute_status"] == "skipped":
                passed.append("Case6: skipped skill 追加到 aia_metric_fact，status=skipped")
            else:
                failed.append("Case6: skipped skill 未正确追加到 fact 列表")
        else:
            failed.append("Case6: 脚本失败")

    # ── Case 7: resolved-skills.json 不存在时以非零退出码退出 ───────────────
    rc5, _, err5 = run(SCRIPT,
        "--resolved-skills", "/nonexistent/resolved-skills.json",
        "--output-dir", str(tmpdir / "output"),
        "--output", str(tmpdir / "output" / "report.json"),
        "--project-path", "/test"
    )
    if rc5 != 0:
        passed.append("Case7: resolved-skills.json 不存在时非零退出")
    else:
        failed.append("Case7: 应该返回非零退出码")

    return passed, failed


if __name__ == "__main__":
    p, f = eval_aggregate()
    print("=" * 60)
    print("Eval: ai-friendly-arch-measure / aggregate-metrics.py")
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
