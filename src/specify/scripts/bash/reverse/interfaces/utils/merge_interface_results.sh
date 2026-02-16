#!/bin/bash
# -*- coding: utf-8 -*-
#
# 接口清单合并工具包装脚本 (Bash)
# 调用Python脚本执行接口清单批次合并
#
# 使用方法:
#   ./merge_interface_results.sh [--verbose] [--validate]
#

set -e  # 遇到错误立即退出
set -u  # 未定义变量时报错
set -o pipefail  # 管道命令失败时退出

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/../../../../python/merge_interface_results.py"
ENHANCED_PYTHON_SCRIPT="$SCRIPT_DIR/../../../../python/merge_interface_results_enhanced.py"

# 检查Python脚本是否存在
if [[ ! -f "$PYTHON_SCRIPT" ]]; then
    echo "错误: Python脚本不存在: $PYTHON_SCRIPT" >&2
    exit 1
fi

if [[ ! -f "$ENHANCED_PYTHON_SCRIPT" ]]; then
    echo "错误: 增强版Python脚本不存在: $ENHANCED_PYTHON_SCRIPT" >&2
    exit 1
fi

# 检查Python环境
if ! command -v python3 &>/dev/null; then
    echo "错误: 未找到python3命令" >&2
    exit 1
fi

# 解析参数
VERBOSE=false
VALIDATE=false
USE_ENHANCED=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --validate)
            VALIDATE=true
            shift
            ;;
        --enhanced|-e)
            USE_ENHANCED=true
            shift
            ;;
        --help|-h)
            echo "使用方法: $0 [--verbose] [--validate] [--enhanced] [repo_root]"
            echo ""
            echo "参数:"
            echo "  --verbose, -v    显示详细处理信息"
            echo "  --validate       验证合并结果"
            echo "  --enhanced, -e   使用增强版脚本"
            echo "  repo_root        仓库根目录路径 (可选，默认为当前目录)"
            echo "  --help, -h       显示此帮助信息"
            exit 0
            ;;
        *)
            break
            ;;
    esac
done

# 获取仓库根目录
REPO_ROOT="${1:-$(pwd)}"

# 验证仓库根目录
if [[ ! -d "$REPO_ROOT" ]]; then
    echo "错误: 仓库根目录不存在: $REPO_ROOT" >&2
    exit 1
fi

# 转换为绝对路径
REPO_ROOT=$(cd "$REPO_ROOT" && pwd)

# 构造Python脚本参数
PYTHON_ARGS=("$REPO_ROOT")

if [[ "$VERBOSE" == true ]]; then
    PYTHON_ARGS+=("--verbose")
fi

if [[ "$VALIDATE" == true ]]; then
    PYTHON_ARGS+=("--validate")
fi

# 选择要使用的脚本
if [[ "$USE_ENHANCED" == true ]]; then
    SCRIPT_TO_USE="$ENHANCED_PYTHON_SCRIPT"
    SCRIPT_NAME="增强版接口清单合并工具"
else
    SCRIPT_TO_USE="$PYTHON_SCRIPT"
    SCRIPT_NAME="接口清单合并工具"
fi

# 执行合并
echo "使用 $SCRIPT_NAME 合并接口清单..."
if [[ "$VERBOSE" == true ]]; then
    python3 "$SCRIPT_TO_USE" "${PYTHON_ARGS[@]}"
else
    python3 "$SCRIPT_TO_USE" "${PYTHON_ARGS[@]}" 2>/dev/null
fi

if [[ $? -eq 0 ]]; then
    echo "接口清单合并完成"
else
    echo "接口清单合并失败" >&2
    exit 1
fi