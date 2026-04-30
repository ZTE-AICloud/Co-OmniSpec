#!/bin/bash
# -*- coding: utf-8 -*-
#
# 创建接口批次文件工具包装脚本 (Bash)
# 调用Python脚本创建接口批次文件
#
# 使用方法:
#   ./create_interface_batches.sh --repo-root <repo_root> [--force]
#

set -e  # 遇到错误立即退出
set -u  # 未定义变量时报错
set -o pipefail  # 管道命令失败时退出

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/../../../../python/reverse_interfaces/create_interface_batches.py"

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

# 初始化变量
REPO_ROOT=""
FORCE=false

# 解析参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --repo-root)
            REPO_ROOT="$2"
            shift 2
            ;;
        --force)
            FORCE=true
            shift
            ;;
        --help|-h)
            echo "使用方法: $0 --repo-root <repo_root> [--force]" >&2
            echo "参数:" >&2
            echo "  --repo-root: 仓库根目录路径" >&2
            echo "  --force: 强制重新生成批次文件，即使已存在" >&2
            exit 0
            ;;
        *)
            echo "未知参数: $1" >&2
            echo "使用方法: $0 --repo-root <repo_root> [--force]" >&2
            exit 1
            ;;
    esac
done

# 验证必需参数
if [[ -z "$REPO_ROOT" ]]; then
    echo "错误: 必须提供 --repo-root 参数" >&2
    echo "使用方法: $0 --repo-root <repo_root> [--force]" >&2
    exit 1
fi

# 验证仓库根目录
if [[ ! -d "$REPO_ROOT" ]]; then
    echo "错误: 仓库根目录不存在: $REPO_ROOT" >&2
    exit 1
fi

# 转换为绝对路径
REPO_ROOT=$(cd "$REPO_ROOT" && pwd)

# 执行Python脚本
if [[ "$FORCE" == true ]]; then
    python3 "$PYTHON_SCRIPT" "$REPO_ROOT" --force
else
    python3 "$PYTHON_SCRIPT" "$REPO_ROOT"
fi

