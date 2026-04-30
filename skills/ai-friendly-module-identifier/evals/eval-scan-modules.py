#!/usr/bin/env python3
"""
Eval: ai-friendly-module-identifier / scan_modules.py
验证模块扫描脚本的输入/输出契约。
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).parent.parent / "scripts" / "scan_modules.py"


def run(script_path: Path, *args) -> tuple[int, str, str]:
    result = subprocess.run(
        [sys.executable, str(script_path), *args],
        capture_output=True, text=True
    )
    return result.returncode, result.stdout, result.stderr


def eval_scan():
    passed, failed = [], []

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # 创建测试项目结构
        (tmpdir / "src").mkdir()
        (tmpdir / "src" / "main.py").write_text("def main(): pass\nprint('hello')\n")
        (tmpdir / "src" / "utils.py").write_text("def helper(): pass\ndef format(): pass\n")
        (tmpdir / "src" / "sub").mkdir()
        (tmpdir / "src" / "sub" / "module.py").write_text("class Foo: pass\ndef bar(): pass\n")
        # 隐藏文件应被跳过
        (tmpdir / "src" / ".hidden.py").write_text("secret = True\n")
        # 二进制文件应被跳过
        (tmpdir / "src" / "binary.dat").write_bytes(b"\x00\x01\x02 binary content")

        # ── Case 1: 正常扫描 ────────────────────────────────────────────────
        rc, out, err = run(SCRIPT, str(tmpdir))
        if rc == 0 and out.strip():
            try:
                modules = json.loads(out)
                if isinstance(modules, list) and len(modules) >= 2:
                    passed.append(f"Case1: 正常扫描成功，识别 {len(modules)} 个模块")
                else:
                    failed.append(f"Case1: modules 应为非空列表，实际: {modules}")
            except json.JSONDecodeError:
                failed.append("Case1: 输出不是合法 JSON")
        else:
            failed.append(f"Case1: rc={rc} 或输出为空")

        # ── Case 2: 每个模块包含必填字段 ─────────────────────────────────────
        if rc == 0:
            modules = json.loads(out)
            for mod in modules:
                missing = [f for f in ["path", "name", "depth", "files"] if f not in mod]
                if missing:
                    failed.append(f"Case2: 模块 {mod.get('name')} 缺少字段 {missing}")
                    break
                for f in mod.get("files", []):
                    if "name" not in f or "lines" not in f:
                        failed.append(f"Case2: 文件缺少 name/lines: {f}")
                        break
            else:
                passed.append("Case2: 所有模块和文件包含必填字段")

        # ── Case 3: 隐藏文件和目录被跳过 ────────────────────────────────────
        if rc == 0:
            modules = json.loads(out)
            names = [m["name"] for m in modules]
            file_names_flat = [f["name"] for m in modules for f in m.get("files", [])]
            if ".hidden.py" not in file_names_flat and ".hidden" not in names:
                passed.append("Case3: 隐藏文件/目录被正确跳过")
            else:
                failed.append("Case3: 隐藏文件或目录未被跳过")

        # ── Case 4: 二进制文件被跳过 ────────────────────────────────────────
        if rc == 0:
            modules = json.loads(out)
            file_names_flat = [f["name"] for m in modules for f in m.get("files", [])]
            if "binary.dat" not in file_names_flat:
                passed.append("Case4: 二进制文件被正确跳过")
            else:
                failed.append("Case4: 二进制文件未被跳过")

        # ── Case 5: 深度限制生效 ────────────────────────────────────────────
        rc5, out5, _ = run(SCRIPT, str(tmpdir), "--depth", "1")
        if rc5 == 0:
            modules5 = json.loads(out5)
            depths = [m["depth"] for m in modules5]
            if depths and max(depths) <= 1:
                passed.append("Case5: --depth 1 限制生效")
            else:
                failed.append(f"Case5: depth 应 ≤ 1，实际 depths={depths}")
        else:
            failed.append("Case5: 深度限制扫描失败")

        # ── Case 6: 不存在的项目路径返回非零退出码 ──────────────────────────
        rc6, _, err6 = run(SCRIPT, str(tmpdir / "nonexistent"))
        if rc6 != 0:
            passed.append("Case6: 不存在的路径返回非零退出码")
        else:
            failed.append("Case6: 不存在的路径应返回非零退出码")

    return passed, failed


if __name__ == "__main__":
    p, f = eval_scan()
    print("=" * 60)
    print("Eval: ai-friendly-module-identifier / scan_modules.py")
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
