#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
方式 B（reverse 调用链扫描）接口识别入口

职责：
- 在给定 input_base_dir 下执行“接口识别”步骤，生成 interface_functions_checklist.json；
- 仅依赖 scripts/python/ 目录下的 `reverse_syntax_parser` 模块，不再直接依赖 `reverse/` 目录；
- 要求 input_base_dir 已包含：
  - internal/semantics_parser/call_tree_list.json
  - internal/syntax_parser/all_methods.json
  - internal/syntax_parser/all_functions.json
- 调用完成后，必须生成：
  - {output_base_dir}/internal/interface_identification/interface_functions_checklist.json

用法示例：

```bash
python3 scripts/python/reverse_by_call_chain/run_reverse_identify.py \
  --repo-root /path/to/repo \
  --input-base-dir /path/to/repo/.cache/reverse/reverse-input
```
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def _ensure_non_empty_file(path: Path) -> None:
    if (not path.exists()) or path.stat().st_size == 0:
        raise FileNotFoundError(f"接口清单未生成或为空: {path}")


def run_reverse_identify(repo_root: str, input_base_dir: str, output_base_dir: str | None = None, no_llm: bool = False) -> Path:
    """
    使用 scripts/python/reverse_syntax_parser 下的实现完成接口识别，
    返回 interface_functions_checklist.json 的路径。
    """
    repo_root_path = Path(repo_root).resolve()
    input_base = Path(input_base_dir).resolve()
    output_base = Path(output_base_dir).resolve() if output_base_dir else input_base

    if not repo_root_path.exists():
        raise FileNotFoundError(f"仓库根目录不存在: {repo_root_path}")

    if not input_base.exists():
        raise FileNotFoundError(f"input_base_dir 不存在: {input_base}")

    # 1. 解析 reverse_syntax_parser/main.py 脚本路径（优先 specify/scripts/python/）
    # 先检查specify目录，再检查旧位置的符号链接
    scripts_root_candidates = [
        repo_root_path / "specify" / "scripts" / "python",
        repo_root_path / ".infra" / "scripts" / "python",
    ]
    main_py: Path | None = None
    for root in scripts_root_candidates:
        candidate = root / "reverse_syntax_parser" / "main.py"
        if candidate.exists():
            main_py = candidate
            break

    if not main_py:
        raise FileNotFoundError(
            f"未找到 reverse_syntax_parser/main.py，请确认已安装到 .scripts/python/ 或存在于 scripts/python/ 下"
        )

    # 2. 调用 reverse_syntax_parser 的 identify 步骤
    cmd = [
        sys.executable,
        str(main_py),
        "--step",
        "identify",
        "--input-base-dir",
        str(input_base),
    ]
    if no_llm:
        cmd.append("--no-llm")

    import subprocess

    env = os.environ.copy()
    if no_llm:
        env["OPENAI_API_KEY"] = ""

    result = subprocess.run(cmd, cwd=str(main_py.parent.parent), env=env, check=False)
    if result.returncode != 0:
        raise RuntimeError(
            f"reverse_syntax_parser 接口识别执行失败，退出码={result.returncode}，命令={' '.join(cmd)}"
        )

    # 3. 校验输出文件是否存在且非空（与 03-interface-list-scanning.md 中 3B.2 描述保持一致）
    checklist_path = output_base / "internal" / "interface_identification" / "interface_functions_checklist.json"
    _ensure_non_empty_file(checklist_path)

    return checklist_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="方式 B：调用 reverse 接口分析器生成 interface_functions_checklist.json"
    )
    parser.add_argument("--repo-root", required=True, help="仓库根目录")
    parser.add_argument(
        "--input-base-dir",
        required=True,
        help="前置依赖目录（含 internal/syntax_parser, internal/semantics_parser）",
    )
    parser.add_argument(
        "--output-base-dir",
        default=None,
        help="输出基础目录，默认与 --input-base-dir 相同",
    )
    parser.add_argument(
        "--no-llm",
        action="store_true",
        default=False,
        help="禁用 LLM 调用，仅使用启发式识别（速度快但精度较低）",
    )
    args = parser.parse_args()

    try:
        checklist = run_reverse_identify(
            repo_root=args.repo_root,
            input_base_dir=args.input_base_dir,
            output_base_dir=args.output_base_dir,
            no_llm=args.no_llm,
        )
        print(f"接口识别完成，已生成: {checklist}")
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(f"错误: {exc}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()

