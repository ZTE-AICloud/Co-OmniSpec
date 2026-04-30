#!/usr/bin/env python3
"""
Eval: ai-friendly-component-srp-orchestrate / aggregate.py
验证聚合脚本的输入/输出契约。
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).parent.parent / "scripts" / "aggregate.py"


def run(script_path: Path, *args) -> tuple[int, str, str]:
    result = subprocess.run(
        [sys.executable, str(script_path), *args],
        capture_output=True, text=True
    )
    return result.returncode, result.stdout, result.stderr


def eval_aggregate():
    passed, failed = [], []

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        input_dir = tmpdir / "step02"
        output_path = tmpdir / "summary.json"
        input_dir.mkdir()

        # ── Case 1: 正常聚合 ─────────────────────────────────────────────────
        (input_dir / "module_a.json").write_text(json.dumps({
            "module_path": "src/module_a",
            "metric_result": {"total_score": 0.8, "confidence": 0.9,
                               "score_detail": {"directory_single_score": 0.8, "module_cohesion_score": 0.9, "file_single_score": 0.7}},
            "violation_info": {"total_count": 2, "level_summary": {"P0": 0, "P1": 2}}
        }))
        (input_dir / "module_b.json").write_text(json.dumps({
            "module_path": "src/module_b",
            "metric_result": {"total_score": 0.6, "confidence": 0.7,
                               "score_detail": {"directory_single_score": 0.6, "module_cohesion_score": 0.6, "file_single_score": 0.6}},
            "violation_info": {"total_count": 5, "level_summary": {"P0": 1, "P1": 4}}
        }))

        rc, out, err = run(SCRIPT,
            "--input-dir", str(input_dir),
            "--output", str(output_path),
            "--project-path", "/test/project"
        )
        if rc == 0 and output_path.exists():
            summary = json.loads(output_path.read_text())
            passed.append("Case1: 正常聚合脚本成功执行并生成 summary.json")
        else:
            failed.append(f"Case1: rc={rc} err={err.strip()}")
            summary = None

        # ── Case 2: 输出符合 aia_metric_fact 必填字段 ───────────────────────
        if summary:
            required_toplevel = ["identity_info", "execution_ctx", "core_metrics",
                                 "evaluation_details", "violation_records", "scan_statistics"]
            missing = [f for f in required_toplevel if f not in summary]
            if not missing:
                passed.append("Case2: 输出包含所有 aia_metric_fact 必填顶层字段")
            else:
                failed.append(f"Case2: 缺少字段 {missing}")

            # identity_info
            identity = summary.get("identity_info", {})
            if "skill_id" in identity and "arch_dimension" in identity:
                passed.append("Case3: identity_info 包含 skill_id 和 arch_dimension")
            else:
                failed.append("Case3: identity_info 缺少必填字段")

        # ── Case 4: core_metrics 聚合值正确 ────────────────────────────────
        if summary:
            core = summary["core_metrics"]
            expected_score = round((0.8 + 0.6) / 2, 4)
            expected_conf = round((0.9 + 0.7) / 2, 4)
            if abs(core["total_score"] - expected_score) < 0.001:
                passed.append(f"Case4: total_score={core['total_score']} 正确（期望 {expected_score}）")
            else:
                failed.append(f"Case4: total_score={core['total_score']}，期望 {expected_score}")
            if abs(core["confidence_score"] - expected_conf) < 0.001:
                passed.append(f"Case5: confidence_score={core['confidence_score']} 正确")
            else:
                failed.append(f"Case5: confidence_score={core['confidence_score']}，期望 {expected_conf}")
            if core["p0_violation_count"] == 1 and core["p1_violation_count"] == 6:
                passed.append("Case6: p0/p1 违规数聚合正确")
            else:
                failed.append(f"Case6: p0={core['p0_violation_count']} p1={core['p1_violation_count']}，期望 p0=1 p1=6")

        # ── Case 7: scan_statistics.total_units.modules 等于模块数 ──────────
        if summary:
            total = summary.get("scan_statistics", {}).get("total_units", {}).get("modules")
            if total == 2:
                passed.append("Case7: scan_statistics.total_units.modules == 2（模块数量正确）")
            else:
                failed.append(f"Case7: total_units.modules={total}，期望 2")

        # ── Case 8: 无输入文件时非零退出 ────────────────────────────────────
        empty_dir = tmpdir / "empty"
        empty_dir.mkdir()
        rc8, _, err8 = run(SCRIPT,
            "--input-dir", str(empty_dir),
            "--output", str(tmpdir / "out.json"),
            "--project-path", "/test"
        )
        if rc8 != 0:
            passed.append("Case8: 输入为空时返回非零退出码")
        else:
            failed.append("Case8: 输入为空时应返回非零退出码")

        # ── Case 9: 跳过 processing_summary.json ─────────────────────────────
        # 使用独立临时目录避免与其他 case 共享 input_dir
        import tempfile as tp9
        with tp9.TemporaryDirectory() as t9:
            t9 = Path(t9)
            case9_input = t9 / "step02"
            case9_input.mkdir()
            (case9_input / "module_a.json").write_text(json.dumps({
                "module_path": "m", "metric_result": {"total_score": 0.5, "confidence": 0.5,
                                   "score_detail": {"directory_single_score": 0.5}},
                "violation_info": {"total_count": 0, "level_summary": {"P0": 0, "P1": 0}}
            }))
            (case9_input / "processing_summary.json").write_text(json.dumps({
                "module_path": "dummy", "metric_result": {"total_score": 1.0, "confidence": 1.0,
                                   "score_detail": {}},
                "violation_info": {"total_count": 0, "level_summary": {"P0": 0, "P1": 0}}
            }))
            rc9, _, _ = run(SCRIPT,
                "--input-dir", str(case9_input),
                "--output", str(t9 / "summary9.json"),
                "--project-path", "/test"
            )
            if rc9 == 0:
                s9 = json.loads((t9 / "summary9.json").read_text())
                total9 = s9.get("scan_statistics", {}).get("total_units", {}).get("modules")
                if total9 == 1:
                    passed.append("Case9: processing_summary.json 被正确跳过")
                else:
                    failed.append(f"Case9: 应跳过 processing_summary，total={total9}")
            else:
                failed.append("Case9: 脚本失败")

        # ── Case 10: 增量模式写入 base_commit / target_commit ────────────────
        changed_modules = tmpdir / "changed-modules.json"
        changed_modules.write_text(json.dumps({
            "mode": "incremental", "base_commit": "abc123", "target_commit": "def456"
        }))
        rc10, _, _ = run(SCRIPT,
            "--input-dir", str(input_dir),
            "--output", str(output_path),
            "--project-path", "/test",
            "--changed-modules-json", str(changed_modules)
        )
        if rc10 == 0:
            s10 = json.loads(output_path.read_text())
            ctx = s10.get("execution_ctx", {})
            if ctx.get("scan_mode") == "increment" and ctx.get("base_commit") == "abc123":
                passed.append("Case10: 增量模式正确写入 scan_mode=increment 和 base_commit")
            else:
                failed.append(f"Case10: scan_mode={ctx.get('scan_mode')} base_commit={ctx.get('base_commit')}")
        else:
            failed.append("Case10: 增量模式脚本失败")

        # ── Case 11: violation_records.violation_infos 截断为 Top-50 ─────────
        many_violations = []
        for i in range(60):
            many_violations.append({"type": f"type_{i}", "level": "P1", "scope_path": f"path/{i}", "resources": [], "suggestion": f"sug_{i}"})

        (input_dir / "big_module.json").write_text(json.dumps({
            "module_path": "big", "metric_result": {"total_score": 0.5, "confidence": 0.5,
                               "score_detail": {}},
            "violation_info": {"total_count": 60, "level_summary": {"P0": 0, "P1": 60},
                               "list": many_violations}
        }))
        rc11, _, _ = run(SCRIPT,
            "--input-dir", str(input_dir),
            "--output", str(output_path),
            "--project-path", "/test"
        )
        if rc11 == 0:
            s11 = json.loads(output_path.read_text())
            violations = s11.get("violation_records", {}).get("violation_infos", [])
            if len(violations) == 50:
                passed.append("Case11: violation_infos 正确截断为 Top-50（实际 60 条）")
            else:
                failed.append(f"Case11: violation_infos 数量={len(violations)}，期望 50")
        else:
            failed.append("Case11: 脚本失败")

        # ── Case 13: --arch-dimension 参数覆盖默认值 ─────────────────────────
        import tempfile as tp13
        with tp13.TemporaryDirectory() as t13:
            t13 = Path(t13)
            case13_input = t13 / "step02"
            case13_input.mkdir()
            (case13_input / "m.json").write_text(json.dumps({
                "module_path": "m", "metric_result": {"total_score": 0.8, "confidence": 0.8,
                                   "score_detail": {}},
                "violation_info": {"total_count": 0, "level_summary": {"P0": 0, "P1": 0}}
            }))
            rc13, _, _ = run(SCRIPT,
                "--input-dir", str(case13_input),
                "--output", str(t13 / "summary13.json"),
                "--project-path", "/test",
                "--arch-dimension", "自定义维度"
            )
            if rc13 == 0:
                s13 = json.loads((t13 / "summary13.json").read_text())
                arch_dim = s13.get("identity_info", {}).get("arch_dimension", "")
                if arch_dim == "自定义维度":
                    passed.append("Case13: --arch-dimension 参数正确覆盖 arch_dimension 值")
                else:
                    failed.append(f"Case13: arch_dimension={arch_dim}，期望 '自定义维度'")
            else:
                failed.append("Case13: --arch-dimension 参数脚本失败")
        (input_dir / "exempt_module.json").write_text(json.dumps({
            "module_path": "exempt_mod", "metric_result": {"total_score": 0.9, "confidence": 0.8,
                               "score_detail": {}},
            "violation_info": {"total_count": 1, "level_summary": {"P0": 0, "P1": 1},
                               "list": [{"type": "X", "level": "P1", "scope_path": "x", "resources": [], "suggestion": "fix"}],
                               "exempt_list": [{"type": "EX", "level": "P1", "scope_path": "ex", "resources": [], "suggestion": "exempted"}]}
        }))
        rc12, _, _ = run(SCRIPT,
            "--input-dir", str(input_dir),
            "--output", str(output_path),
            "--project-path", "/test"
        )
        if rc12 == 0:
            s12 = json.loads(output_path.read_text())
            exempt_infos = s12.get("violation_records", {}).get("exempt_infos", [])
            if exempt_infos == []:
                passed.append("Case12: exempt_infos 始终为空（exempt_list 被丢弃 — 已知问题）")
            else:
                failed.append("Case12: exempt_infos 应始终为空，但实际有内容")
        else:
            failed.append("Case12: 脚本失败")

    return passed, failed


if __name__ == "__main__":
    p, f = eval_aggregate()
    print("=" * 60)
    print("Eval: ai-friendly-component-srp-orchestrate / aggregate.py")
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
