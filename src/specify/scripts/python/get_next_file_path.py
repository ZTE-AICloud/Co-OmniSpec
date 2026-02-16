#!/usr/bin/env python3
"""
从批次文件中获取下一个要处理的文件路径

用法:
    python get_next_file_path.py --batch-file <批次文件路径> --file-index <文件索引> --repo-root <仓库根目录>

参数:
    --batch-file: 批次文件路径（如 batch-details-3.json）
    --file-index: 文件在批次中的索引（从0开始）
    --repo-root: 仓库根目录路径

输出:
    输出文件的绝对路径（如果成功）
    如果失败，输出错误信息到stderr并返回非零退出码
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional


def load_batch_file(batch_file_path: str) -> Dict[str, Any]:
    """加载批次文件"""
    try:
        with open(batch_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        print(f"错误: 批次文件不存在: {batch_file_path}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"错误: 批次文件格式错误: {batch_file_path}: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"错误: 无法读取批次文件 {batch_file_path}: {e}", file=sys.stderr)
        sys.exit(1)


def get_file_path_from_batch(
    batch_file_path: str,
    file_index: int,
    repo_root: str
) -> Optional[str]:
    """
    从批次文件中获取指定索引的文件路径并转换为绝对路径
    支持新旧两种格式：
    - 旧格式：files 是字符串数组
    - 新格式：files 是对象数组，每个对象包含 path 和 status 字段
    
    Args:
        batch_file_path: 批次文件路径
        file_index: 文件在批次中的索引（从0开始），如果为-1则自动查找下一个未处理的文件
        repo_root: 仓库根目录路径
    
    Returns:
        文件的绝对路径，如果失败返回None
    """
    # 加载批次文件
    batch_data = load_batch_file(batch_file_path)
    
    # 获取文件列表
    if 'files' not in batch_data:
        print(f"错误: 批次文件中缺少 'files' 字段: {batch_file_path}", file=sys.stderr)
        return None
    
    files = batch_data['files']
    
    if not isinstance(files, list):
        print(f"错误: 批次文件中的 'files' 字段不是数组: {batch_file_path}", file=sys.stderr)
        return None
    
    # 转换为绝对路径的基础路径
    repo_root_path = Path(repo_root).resolve()
    
    # 如果 file_index 为 -1，自动查找下一个未处理的文件（且文件存在）
    if file_index == -1:
        for idx, file_entry in enumerate(files):
            # 支持新旧格式
            if isinstance(file_entry, dict):
                # 新格式：对象包含 path 和 status
                file_status = file_entry.get('status', 'pending')
                relative_file_path = file_entry.get('path', '')
            else:
                # 旧格式：直接是字符串
                file_status = 'pending'
                relative_file_path = file_entry
            
            # 跳过已处理的文件
            if file_status in ('completed', 'failed'):
                continue
            
            # 检查文件路径是否有效
            if not relative_file_path:
                # 如果路径为空，跳过并继续查找下一个
                continue
            
            # 转换为绝对路径并验证文件是否存在
            try:
                absolute_file_path = (repo_root_path / relative_file_path).resolve()
                if absolute_file_path.exists() and absolute_file_path.is_file():
                    # 找到第一个存在且未处理的文件
                    return str(absolute_file_path)
                # 文件不存在，跳过并继续查找下一个
            except Exception:
                # 路径解析失败，跳过并继续查找下一个
                continue
        
        # 没有找到未处理且存在的文件
        print(f"错误: 批次中没有未处理且存在的文件: {batch_file_path}", file=sys.stderr)
        return None
    
    # 检查索引是否有效
    if file_index < 0 or file_index >= len(files):
        print(f"错误: 文件索引 {file_index} 超出范围 [0, {len(files)-1}]", file=sys.stderr)
        return None
    
    # 获取文件路径（支持新旧格式）
    file_entry = files[file_index]
    
    if isinstance(file_entry, dict):
        # 新格式：对象包含 path 和 status
        relative_file_path = file_entry.get('path', '')
        if not relative_file_path:
            print(f"错误: 文件对象中缺少 'path' 字段: {file_entry}", file=sys.stderr)
            return None
    elif isinstance(file_entry, str):
        # 旧格式：直接是字符串
        relative_file_path = file_entry
    else:
        print(f"错误: 文件条目格式无效: {file_entry}", file=sys.stderr)
        return None
    
    # 转换为绝对路径
    absolute_file_path = (repo_root_path / relative_file_path).resolve()
    
    # 验证文件是否存在
    if not absolute_file_path.exists():
        print(f"错误: 文件不存在: {absolute_file_path} (相对路径: {relative_file_path})", file=sys.stderr)
        return None
    
    if not absolute_file_path.is_file():
        print(f"错误: 路径不是文件: {absolute_file_path} (相对路径: {relative_file_path})", file=sys.stderr)
        return None
    
    # 返回绝对路径（字符串格式）
    return str(absolute_file_path)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='从批次文件中获取下一个要处理的文件路径',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    python get_next_file_path.py \\
        --batch-file /path/to/.cache/omni-reverse/interfaces/batch-details-3.json \\
        --file-index 0 \\
        --repo-root /path/to/project
        """
    )
    
    parser.add_argument(
        '--batch-file',
        required=True,
        help='批次文件路径（如 batch-details-3.json）'
    )
    parser.add_argument(
        '--file-index',
        type=int,
        required=True,
        help='文件在批次中的索引（从0开始），如果为-1则自动查找下一个未处理的文件'
    )
    parser.add_argument(
        '--repo-root',
        required=True,
        help='仓库根目录路径'
    )
    
    args = parser.parse_args()
    
    # 验证仓库根目录
    if not os.path.isdir(args.repo_root):
        print(f"错误: 仓库根目录不存在: {args.repo_root}", file=sys.stderr)
        sys.exit(1)
    
    # 获取文件路径
    file_path = get_file_path_from_batch(
        args.batch_file,
        args.file_index,
        args.repo_root
    )
    
    if file_path is None:
        sys.exit(1)
    
    # 输出文件路径（标准输出）
    print(file_path)
    sys.exit(0)


if __name__ == '__main__':
    main()

