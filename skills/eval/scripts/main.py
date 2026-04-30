#!/usr/bin/env python3
"""
OmniEval 综合代码评测技能
整合代码变更采集和第三方模型评测功能
"""

import os
import sys
import json
import subprocess
import argparse
from pathlib import Path

def run_skill_command(skill_name, args=None):
    """运行指定的 skill 命令"""
    cmd = f"/{skill_name}"
    if args:
        cmd += f" {args}"

    print(f"\n执行命令: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

    return result.returncode == 0, result.stdout, result.stderr

def find_branch_name():
    """查找当前分支名称"""
    try:
        result = subprocess.run(
            "git branch --show-current",
            shell=True,
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None

def detect_target_directory():
    """自动检测目标目录"""
    # 按优先级顺序检测目录
    priority_dirs = ['networking_zte', 'src', 'lib']

    # 首先尝试优先级目录
    for dir_name in priority_dirs:
        if os.path.isdir(dir_name) and os.listdir(dir_name):
            print(f"检测到主要代码目录: {dir_name}")
            return dir_name

    # 如果优先级目录都没有，查找当前目录下第一个包含代码文件的目录
    for item in os.listdir('.'):
        if os.path.isdir(item) and not item.startswith('.') and item not in ['changes', '.claude', '.git', 'doc', 'scripts', 'etc', 'omni-doc']:
            # 检查是否包含代码文件
            has_code = False
            for root, dirs, files in os.walk(item):
                for file in files:
                    if file.endswith(('.py', '.java', '.cpp', '.c', '.h', '.js', '.ts', '.go', '.rs')):
                        has_code = True
                        break
                if has_code:
                    break
            if has_code:
                print(f"检测到代码目录: {item}")
                return item

    # 如果都没找到，使用当前目录
    print("未找到特定的代码目录，将使用当前目录")
    return "."

def find_eval_file(branch_name):
    """查找 eval.result.json 文件"""
    possible_paths = [
        f"changes/{branch_name}/evalset/eval.result.json",
        f"changes/{branch_name}/evalset/config.result.json",
        f"FEATURE_DIR/evalset/eval.result.json",
        f"FEATURE_DIR/evalset/config.result.json"
    ]

    for path in possible_paths:
        if os.path.exists(path):
            return path
    return None

def save_result(output_text, branch_name):
    """保存评测结果到文件"""
    evalset_dir = f"changes/{branch_name}/evalset"
    if not os.path.exists(evalset_dir):
        os.makedirs(evalset_dir, exist_ok=True)

    result_file = f"{evalset_dir}/result.txt"
    with open(result_file, 'w', encoding='utf-8') as f:
        f.write(output_text)

    return result_file

def main():
    parser = argparse.ArgumentParser(description='OmniEval 综合代码评测')
    parser.add_argument('target_dir', nargs='?',
                       help='目标目录 (不指定则自动检测)')
    args = parser.parse_args()

    # 如果用户没有指定目录，则自动检测
    if not args.target_dir:
        args.target_dir = detect_target_directory()

    print("=" * 60)
    print("OmniEval 综合代码评测开始")
    print("=" * 60)

    # 阶段1：代码变更采集
    print("\n第一步：采集代码变更信息")
    print("-" * 40)

    branch_name = find_branch_name()
    if branch_name:
        print(f"- 当前分支: {branch_name}")

    print(f"- 目标目录: {args.target_dir}")

    # 调用 eval-collector
    success, stdout, stderr = run_skill_command("eval-collector", args.target_dir)

    if not success:
        print(f"\n❌ 代码采集失败: {stderr}")
        sys.exit(1)

    print("\n✅ 代码采集完成")
    print(stdout)

    # 等待一下确保文件写入完成
    import time
    time.sleep(1)

    # 查找生成的 eval 文件
    eval_file = None
    if branch_name:
        eval_file = find_eval_file(branch_name)

    if not eval_file:
        print("\n⚠️  未找到 eval.result.json 文件，尝试从 FEATURE_DIR 查找...")
        eval_file = find_eval_file(None)

    if not eval_file:
        print("\n❌ 未找到评测数据文件，请先确保代码采集成功")
        sys.exit(1)

    print(f"\n找到评测数据文件: {eval_file}")

    # 阶段2：代码质量评测
    print("\n第二步：执行代码质量评测")
    print("-" * 40)

    # 调用 eval-evaluator 对采集的数据进行评测
    success, stdout, stderr = run_skill_command("eval-evaluator", eval_file)

    if not success:
        print(f"\n❌ 代码评测失败: {stderr}")
        sys.exit(1)

    print("\n✅ 代码评测完成")

    # 输出评测结果到控制台
    print("\n" + "=" * 60)
    print("评测结果")
    print("=" * 60)
    print(stdout)

    # 保存结果到文件
    if branch_name:
        result_file = save_result(stdout, branch_name)
        print(f"\n结果已保存到: {result_file}")

    print("\n" + "=" * 60)
    print("评测完成！")
    print("=" * 60)

if __name__ == "__main__":
    main()