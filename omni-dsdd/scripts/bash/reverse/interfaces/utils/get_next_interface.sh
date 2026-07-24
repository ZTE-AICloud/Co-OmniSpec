#!/bin/bash
# -*- coding: utf-8 -*-
#
# 获取下一个要处理的接口工具包装脚本 (Bash)
# 调用Python脚本获取下一个待处理的接口
#
# 使用方法:
#   ./get_next_interface.sh [repo_root]
#

set -e  # 遇到错误立即退出
set -u  # 未定义变量时报错
set -o pipefail  # 管道命令失败时退出

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/../../../../python/reverse_interfaces/get_next_interface.py"

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

# 获取仓库根目录
REPO_ROOT="${1:-$(pwd)}"

# 验证仓库根目录
if [[ ! -d "$REPO_ROOT" ]]; then
    echo "错误: 仓库根目录不存在: $REPO_ROOT" >&2
    exit 1
fi

# 转换为绝对路径
REPO_ROOT=$(cd "$REPO_ROOT" && pwd)

# 执行Python脚本
python3 "$PYTHON_SCRIPT" "$REPO_ROOT"