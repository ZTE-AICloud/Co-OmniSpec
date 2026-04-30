#!/usr/bin/env python3
"""
Eval: ai-friendly-arch-measure / resolve-skills.py
验证 skill 解析的输入/输出契约。
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).parent.parent / "scripts" / "resolve-skills.py"


def run(script_path: Path, *args) -> tuple[int, str, str]:
    result = subprocess.run(
        [sys.executable, str(script_path), *args],
        capture_output=True, text=True
    )
    return result.returncode, result.stdout, result.stderr


def eval_resolve():
    passed, failed = [], []

    registry = {
        "version": "1.0",
        "dimensions": ["结构可导航性", "上下文窗口适配性"],
        "metrics": [
            {"skill_id": "skill-a", "display_name": "Skill A", "dimension": "结构可导航性", "tags": ["default"], "enabled": True, "output_path_hint": "output/a/summary.json"},
            {"skill_id": "skill-b", "display_name": "Skill B", "dimension": "上下文窗口适配性", "tags": ["default"], "enabled": False, "output_path_hint": "output/b/summary.json"},
            {"skill_id": "skill-c", "display_name": "Skill C", "dimension": "结构可导航性", "tags": ["extra"], "enabled": True, "output_path_hint": "output/c/summary.json"},
        ]
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        registry_path = tmpdir / "registry.json"
        output_path = tmpdir / "resolved.json"
        registry_path.write_text(json.dumps(registry))

        # ── Case 1: 默认模式 - 仅 default tag + enabled ───────────────────────
        rc, out, err = run(SCRIPT,
            "--registry", str(registry_path),
            "--output", str(output_path)
        )
        if rc == 0 and output_path.exists():
            data = json.loads(output_path.read_text())
            resolved_ids = [s["skill_id"] for s in data["resolved"]]
            if resolved_ids == ["skill-a"]:
                passed.append("Case1: 默认模式仅执行 default tag + enabled skill (skill-a)")
            else:
                failed.append(f"Case1: resolved={resolved_ids}，期望 ['skill-a']")
        else:
            failed.append(f"Case1: rc={rc} err={err.strip()}")

        # ── Case 2: --all 模式 ───────────────────────────────────────────────
        rc2, _, _ = run(SCRIPT,
            "--registry", str(registry_path),
            "--output", str(output_path),
            "--all"
        )
        if rc2 == 0:
            data2 = json.loads(output_path.read_text())
            resolved_ids2 = [s["skill_id"] for s in data2["resolved"]]
            if resolved_ids2 == ["skill-a", "skill-c"]:
                passed.append("Case2: --all 模式执行所有 enabled skill (skill-a, skill-c)")
            else:
                failed.append(f"Case2: resolved={resolved_ids2}，期望 skill-a, skill-c")
        else:
            failed.append("Case2: --all 模式失败")

        # ── Case 3: --dimension 模式 - 合法维度 ──────────────────────────────
        # skill-a 和 skill-c 都属于"结构可导航性"且 enabled=true
        rc3, _, _ = run(SCRIPT,
            "--registry", str(registry_path),
            "--output", str(output_path),
            "--dimension", "结构可导航性"
        )
        if rc3 == 0:
            data3 = json.loads(output_path.read_text())
            resolved_ids3 = [s["skill_id"] for s in data3["resolved"]]
            if resolved_ids3 == ["skill-a", "skill-c"]:
                passed.append("Case3: --dimension 过滤到正确 skill（skill-a, skill-c）")
            else:
                failed.append(f"Case3: resolved={resolved_ids3}，期望 ['skill-a', 'skill-c']")
        else:
            failed.append("Case3: --dimension 模式失败")

        # ── Case 4: --dimension 模式 - 非法维度应非零退出 ───────────────────
        rc4, _, err4 = run(SCRIPT,
            "--registry", str(registry_path),
            "--output", str(output_path),
            "--dimension", "不存在的维度"
        )
        if rc4 != 0:
            passed.append("Case4: 非法维度返回非零退出码")
        else:
            failed.append("Case4: 非法维度应返回非零退出码")

        # ── Case 5: --skills 模式 - 强制执行忽略 enabled ────────────────────
        rc5, _, _ = run(SCRIPT,
            "--registry", str(registry_path),
            "--output", str(output_path),
            "--skills", "skill-b"
        )
        if rc5 == 0:
            data5 = json.loads(output_path.read_text())
            resolved_ids5 = [s["skill_id"] for s in data5["resolved"]]
            if "skill-b" in resolved_ids5:
                passed.append("Case5: --skills 模式强制执行 skill-b（enabled: false）")
            else:
                failed.append(f"Case5: skill-b 未被解析，resolved={resolved_ids5}")
        else:
            failed.append("Case5: --skills 模式失败")

        # ── Case 6: 输出包含 execute_mode 字段 ──────────────────────────────
        if output_path.exists():
            data6 = json.loads(output_path.read_text())
            if "execute_mode" in data6 and "resolved" in data6 and "skipped" in data6:
                passed.append("Case6: 输出包含 execute_mode, resolved, skipped 字段")
            else:
                failed.append("Case6: 输出缺少必要字段")

        # ── Case 7: resolved 条目包含 dimension 和 output_path_hint ──────────
        if output_path.exists():
            data7 = json.loads(output_path.read_text())
            for entry in data7["resolved"]:
                if "dimension" not in entry or "output_path_hint" not in entry:
                    failed.append(f"Case7: resolved 条目缺少字段: {entry}")
                    break
            else:
                passed.append("Case7: resolved 条目包含 dimension 和 output_path_hint")

    return passed, failed


if __name__ == "__main__":
    p, f = eval_resolve()
    print("=" * 60)
    print("Eval: ai-friendly-arch-measure / resolve-skills.py")
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
