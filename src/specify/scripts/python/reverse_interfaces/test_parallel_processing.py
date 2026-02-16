#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试并行处理脚本
测试get_next_batches.py和update_batches_status.py脚本的功能
"""

import os
import sys
import json
import subprocess
import tempfile
import shutil
from typing import Dict, Any


def create_test_environment():
    """创建测试环境"""
    # 创建临时目录
    test_dir = tempfile.mkdtemp(prefix="omnispec_test_")
    cache_dir = os.path.join(test_dir, ".cache", "omni-reverse", "interfaces")
    os.makedirs(cache_dir, exist_ok=True)

    # 创建测试批次映射文件
    batch_mapping = {
        "total_batches": 3,
        "batch_size": 3,
        "batches": [
            {"batch_number": 1, "batch_file": "batch-details-1.json", "status": "pending"},
            {"batch_number": 2, "batch_file": "batch-details-2.json", "status": "pending"},
            {"batch_number": 3, "batch_file": "batch-details-3.json", "status": "pending"}
        ]
    }

    batch_mapping_file = os.path.join(cache_dir, "batch-mapping.json")
    with open(batch_mapping_file, 'w', encoding='utf-8') as f:
        json.dump(batch_mapping, f, ensure_ascii=False, indent=2)

    # 创建测试批次详细文件
    for i in range(1, 4):
        batch_details = {
            "batch_number": i,
            "files": [f"/test/file{i}_1.java", f"/test/file{i}_2.java"],
            "estimated_tokens": 10000,
            "complexity_score": 5.0,
            "status": "pending"
        }
        batch_details_file = os.path.join(cache_dir, f"batch-details-{i}.json")
        with open(batch_details_file, 'w', encoding='utf-8') as f:
            json.dump(batch_details, f, ensure_ascii=False, indent=2)

    # 创建批次状态文件
    batch_status = {
        "version": "1.1",
        "stage": "interface_scanning",
        "total_items": 6,
        "batch_size": 20,
        "total_batches": 3,
        "processed_batches": 0,
        "current_batch": 0,
        "failed_batches": 0,
        "start_time": "",
        "last_update": "",
        "status": "initialized",
        "batch_mappings": [
            {"batch_number": 1, "batch_file": "batch-details-1.json", "status": "pending", "estimated_tokens": 10000},
            {"batch_number": 2, "batch_file": "batch-details-2.json", "status": "pending", "estimated_tokens": 10000},
            {"batch_number": 3, "batch_file": "batch-details-3.json", "status": "pending", "estimated_tokens": 10000}
        ]
    }

    batch_status_file = os.path.join(cache_dir, "interface_scanning-batch-status.json")
    with open(batch_status_file, 'w', encoding='utf-8') as f:
        json.dump(batch_status, f, ensure_ascii=False, indent=2)

    return test_dir


def test_get_next_batches(test_dir: str):
    """测试获取下一个批次脚本"""
    print("测试 get_next_batches.py 脚本...")

    script_path = os.path.join(os.path.dirname(__file__), "get_next_batches.py")
    if not os.path.exists(script_path):
        print(f"错误: 脚本文件不存在 {script_path}")
        return False

    try:
        # 执行脚本
        result = subprocess.run([
            sys.executable, script_path, test_dir, "--batch-count", "2"
        ], capture_output=True, text=True, cwd=os.path.dirname(script_path))

        if result.returncode != 0:
            print(f"脚本执行失败: {result.stderr}")
            return False

        # 解析输出
        batches = json.loads(result.stdout)
        print(f"获取到 {len(batches)} 个批次:")
        for batch in batches:
            print(f"  批次 {batch['batch_number']}: {batch['status']}")

        return len(batches) > 0
    except Exception as e:
        print(f"测试过程中发生错误: {e}")
        return False


def test_update_batches_status(test_dir: str):
    """测试批量更新批次状态脚本"""
    print("\n测试 update_batches_status.py 脚本...")

    script_path = os.path.join(os.path.dirname(__file__), "update_batches_status.py")
    if not os.path.exists(script_path):
        print(f"错误: 脚本文件不存在 {script_path}")
        return False

    # 准备更新数据
    batch_updates = [
        {"batch_number": 1, "status": "processing"},
        {"batch_number": 2, "status": "processing"}
    ]

    try:
        # 执行脚本
        result = subprocess.run([
            sys.executable, script_path, test_dir, json.dumps(batch_updates)
        ], capture_output=True, text=True, cwd=os.path.dirname(script_path))

        if result.returncode != 0:
            print(f"脚本执行失败: {result.stderr}")
            return False

        # 解析输出
        results = json.loads(result.stdout)
        print(f"更新结果: {results}")

        # 验证更新是否成功
        if results.get('success'):
            print("批次状态更新成功")
            return True
        else:
            print("批次状态更新失败")
            return False
    except Exception as e:
        print(f"测试过程中发生错误: {e}")
        return False


def cleanup_test_environment(test_dir: str):
    """清理测试环境"""
    try:
        shutil.rmtree(test_dir)
        print(f"已清理测试环境: {test_dir}")
    except Exception as e:
        print(f"清理测试环境时发生错误: {e}")


def main():
    """主函数"""
    print("开始测试并行处理脚本...")

    # 创建测试环境
    test_dir = create_test_environment()
    print(f"已创建测试环境: {test_dir}")

    try:
        # 测试获取批次脚本
        success1 = test_get_next_batches(test_dir)

        # 测试更新批次状态脚本
        success2 = test_update_batches_status(test_dir)

        if success1 and success2:
            print("\n✅ 所有测试通过!")
            return 0
        else:
            print("\n❌ 部分测试失败!")
            return 1
    finally:
        # 清理测试环境
        cleanup_test_environment(test_dir)


if __name__ == '__main__':
    sys.exit(main())