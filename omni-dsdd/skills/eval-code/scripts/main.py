#!/usr/bin/env python3
"""
OmniEval 综合代码评测技能
整合代码变更采集和第三方模型评测功能
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path
from typing import Optional, Tuple


def plugin_root() -> Path:
    root = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if root and Path(root).is_dir():
        return Path(root).resolve()
    return Path(__file__).resolve().parents[3]


def working_dir() -> Path:
    wd = os.environ.get("CLAUDE_WORKING_DIR")
    if wd:
        return Path(wd).resolve()
    return Path.cwd().resolve()


def feature_dir() -> Optional[Path]:
    fd = os.environ.get("FEATURE_DIR")
    if fd:
        return Path(fd).resolve()
    return None


def run_collect(target_dir: str) -> tuple:
    script = plugin_root() / "skills/eval-code-collector/scripts/collect.py"
    cmd = [
        sys.executable,
        str(script),
        "--working-dir",
        str(working_dir()),
        "--target-dir",
        target_dir,
    ]
    fd = feature_dir()
    if fd:
        cmd.extend(["--feature-dir", str(fd)])
    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )
    return result.returncode == 0, result.stdout, result.stderr


def run_evaluate(config_path: Path, output_path: Path) -> tuple:
    script = plugin_root() / "skills/eval-code-evaluator/scripts/evaluate_code.py"
    cmd = [
        sys.executable,
        str(script),
        "--config",
        str(config_path),
        "--output",
        str(output_path),
    ]
    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )
    return result.returncode == 0, result.stdout, result.stderr


def find_branch_name() -> Optional[str]:
    try:
        result = subprocess.run(
            ["git", "-C", str(working_dir()), "branch", "--show-current"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )
        if result.returncode == 0:
            return result.stdout.strip() or None
    except Exception:
        pass
    return None


def detect_target_directory() -> str:
    wd = working_dir()
    priority_dirs = ["code", "src", "lib"]
    skip = {"changes", ".claude", ".git", "doc", "scripts", "etc", "omni-doc", ".omni-infra"}

    for dir_name in priority_dirs:
        p = wd / dir_name
        if p.is_dir() and any(p.iterdir()):
            print(f"检测到主要代码目录: {dir_name}")
            return dir_name

    for item in wd.iterdir():
        if not item.is_dir() or item.name.startswith(".") or item.name in skip:
            continue
        has_code = False
        for root, _dirs, files in os.walk(item):
            for file in files:
                if file.endswith(
                    (".py", ".java", ".cpp", ".c", ".h", ".js", ".ts", ".go", ".rs")
                ):
                    has_code = True
                    break
            if has_code:
                break
        if has_code:
            print(f"检测到代码目录: {item.name}")
            return item.name

    print("未找到特定的代码目录，将使用当前目录")
    return "."


def resolve_eval_paths(branch_name: Optional[str]) -> Tuple[Optional[Path], Optional[Path]]:
    fd = feature_dir()
    if fd:
        config = fd / ".runs/evaluations/code.diff.json"
        result = fd / ".runs/evaluations/eval-code-report.txt"
        if config.exists():
            return config, result
    if branch_name:
        base = working_dir() / "changes" / branch_name / ".runs/evaluations"
        config = base / "code.diff.json"
        if config.exists():
            return config, base / "eval-code-report.txt"
    return None, None


def main():
    parser = argparse.ArgumentParser(description="OmniEval 综合代码评测")
    parser.add_argument(
        "target_dir", nargs="?", help="目标目录 (不指定则自动检测)"
    )
    args = parser.parse_args()

    if not args.target_dir:
        args.target_dir = detect_target_directory()

    print("=" * 60)
    print("OmniEval 综合代码评测开始")
    print("=" * 60)
    print(f"- 工作区: {working_dir()}")
    if feature_dir():
        print(f"- 特性目录: {feature_dir()}")

    print("\n第一步：采集代码变更信息")
    print("-" * 40)

    branch_name = find_branch_name()
    if branch_name:
        print(f"- 当前分支: {branch_name}")
    print(f"- 目标目录: {args.target_dir}")

    success, stdout, stderr = run_collect(args.target_dir)
    if not success:
        print(f"\n❌ 代码采集失败: {stderr}")
        sys.exit(1)

    print("\n✅ 代码采集完成")
    print(stdout)

    config_path, result_path = resolve_eval_paths(branch_name)
    if not config_path:
        print("\n❌ 未找到 code.diff.json，请确认 FEATURE_DIR 或采集是否成功")
        sys.exit(1)

    if result_path is None:
        result_path = config_path.parent / "eval-code-report.txt"

    print(f"\n找到评测数据文件: {config_path}")

    print("\n第二步：执行代码质量评测")
    print("-" * 40)

    success, stdout, stderr = run_evaluate(config_path, result_path)
    if not success:
        print(f"\n❌ 代码评测失败: {stderr}")
        sys.exit(1)

    print("\n✅ 代码评测完成")
    print("\n" + "=" * 60)
    print("评测结果")
    print("=" * 60)
    if stdout.strip():
        print(stdout)
    if result_path.exists():
        print(f"\n结果已保存到: {result_path}")

    print("\n" + "=" * 60)
    print("评测完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
