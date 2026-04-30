#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
为方式B（reverse 调用链扫描）自动生成前置依赖文件

执行语法解析和语义解析，生成 call_tree_list.json、all_methods.json、all_functions.json，
供接口识别使用。

使用方法:
    python3 prepare_reverse_input.py --repo-root <repo_root> \\
        [--codebase <代码库路径，默认=repo_root>] \\
        [--output-dir <输出目录，默认=.cache/reverse/reverse-input>]

前置依赖:
    使用 scripts/python/reverse_syntax_parser/ 中的语法解析和语义解析
"""
from __future__ import print_function

import sys
if sys.version_info < (3, 6):
    sys.stderr.write("此脚本需要 Python 3.6+，请使用: python3 prepare_reverse_input.py ...\n")
    sys.exit(1)

import os
import subprocess
import argparse
from pathlib import Path


def prepare(repo_root, codebase, output_dir):
    """
    生成前置依赖文件
    返回 output_dir 的绝对路径（即 input_base_dir）
    """
    repo_root = os.path.abspath(repo_root)
    codebase = os.path.abspath(codebase or repo_root)
    output_dir = os.path.abspath(
        output_dir or os.path.join(repo_root, ".cache", "reverse", "reverse-input")
    )

    if not os.path.isdir(codebase):
        raise OSError("代码库路径不存在: {}".format(codebase))

    os.makedirs(output_dir, exist_ok=True)

    # 使用 reverse_syntax_parser 的 main.py 执行 prepare
    repository_root = Path(repo_root).resolve()

    # 优先 `.infra/scripts/python/`（安装布局），其次仓库根 `scripts/python/`（OmniSpec 源码树）
    possible_locations = [
        repository_root / ".infra" / "scripts" / "python" / "reverse_syntax_parser",
        repository_root / "scripts" / "python" / "reverse_syntax_parser",
        Path(__file__).resolve().parent / "reverse_syntax_parser",
    ]

    main_py = None
    for location in possible_locations:
        candidate = location / "main.py"
        if candidate.exists():
            main_py = candidate
            break

    if not main_py:
        raise OSError(
            "reverse_syntax_parser 不存在，请检查以下位置：\n" +
            "\n".join([str(loc) for loc in possible_locations])
        )

    subprocess.run(
        [
            sys.executable,
            str(main_py),
            "--step",
            "prepare",
            "--input-base-dir",
            output_dir,
            "--codebase",
            codebase,
        ],
        check=True,
        cwd=str(main_py.parent),
    )

    return output_dir


def main():
    parser = argparse.ArgumentParser(description="为方式B生成前置依赖（语法解析+调用链）")
    parser.add_argument("--repo-root", required=True, help="仓库根目录")
    parser.add_argument("--codebase", default=None, help="代码库路径，默认=repo-root")
    parser.add_argument(
        "--output-dir",
        default=None,
        help="输出目录，默认=.cache/reverse/reverse-input",
    )
    args = parser.parse_args()

    try:
        out = prepare(args.repo_root, args.codebase, args.output_dir)
        print("前置依赖已生成，input_base_dir={}".format(out))
        print("  - {}/internal/syntax_parser/all_methods.json".format(out))
        print("  - {}/internal/syntax_parser/all_functions.json".format(out))
        print("  - {}/internal/semantics_parser/call_tree_list.json".format(out))
    except Exception as e:
        sys.stderr.write("错误: {}\n".format(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
