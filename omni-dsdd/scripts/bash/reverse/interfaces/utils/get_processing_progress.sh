#!/bin/bash
# -*- coding: utf-8 -*-
#
# 获取接口处理进度工具包装脚本 (Bash)
# 调用Python脚本获取接口处理进度
#
# 使用方法:
#   ./get_processing_progress.sh [repo_root] [--format json|text]
#

set -e  # 遇到错误立即退出
set -u  # 未定义变量时报错
set -o pipefail  # 管道命令失败时退出

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/../../../../python/reverse_interfaces/get_processing_progress.py"

# 检查Python脚本是否存在
if [[ ! -f "$PYTHON_SCRIPT" ]]; then
    echo "错误: Python脚本不存在: $PYTHON_SCRIPT" >&2
    exit 1
fi

# 检查Python环境
if ! command -v python3 &>/dev/null; then
    echo "错误: 未找到python3命令" >&2
    exit 1
fi

# 解析参数
REPO_ROOT="$(pwd)"
FORMAT="text"

while [[ $# -gt 0 ]]; do
    case $1 in
        --format)
            FORMAT="$2"
            shift 2
            ;;
        -*)
            echo "未知选项: $1" >&2
            echo "使用方法: $0 [repo_root] [--format json|text]" >&2
            exit 1
            ;;
        *)
            REPO_ROOT="$1"
            shift
            ;;
    esac
done

# 验证仓库根目录
if [[ ! -d "$REPO_ROOT" ]]; then
    echo "错误: 仓库根目录不存在: $REPO_ROOT" >&2
    exit 1
fi

# 转换为绝对路径
REPO_ROOT=$(cd "$REPO_ROOT" && pwd)

# 执行Python脚本
if [[ "$FORMAT" == "json" ]]; then
    python3 "$PYTHON_SCRIPT" "$REPO_ROOT" --format json
else
    python3 "$PYTHON_SCRIPT" "$REPO_ROOT"
fi