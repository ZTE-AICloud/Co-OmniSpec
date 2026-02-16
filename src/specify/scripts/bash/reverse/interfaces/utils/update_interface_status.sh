#!/bin/bash
# -*- coding: utf-8 -*-
#
# 更新接口处理状态工具包装脚本 (Bash)
# 调用Python脚本更新接口处理状态
#
# 使用方法:
#   ./update_interface_status.sh <interface_id> <status> [repo_root]
#

set -e  # 遇到错误立即退出
set -u  # 未定义变量时报错
set -o pipefail  # 管道命令失败时退出

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/../../../../python/reverse_interfaces/update_interface_status.py"

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
if [[ $# -lt 2 ]]; then
    echo "使用方法: $0 <interface_id> <status> [repo_root]" >&2
    echo "状态选项: pending, processing, completed, failed" >&2
    exit 1
fi

INTERFACE_ID="$1"
STATUS="$2"
REPO_ROOT="${3:-$(pwd)}"

# 验证参数
case "$STATUS" in
    pending|processing|completed|failed)
        ;;
    *)
        echo "错误: 无效的状态 '$STATUS'。有效状态: pending, processing, completed, failed" >&2
        exit 1
        ;;
esac

# 验证仓库根目录
if [[ ! -d "$REPO_ROOT" ]]; then
    echo "错误: 仓库根目录不存在: $REPO_ROOT" >&2
    exit 1
fi

# 转换为绝对路径
REPO_ROOT=$(cd "$REPO_ROOT" && pwd)

# 执行Python脚本
python3 "$PYTHON_SCRIPT" "$REPO_ROOT" "$INTERFACE_ID" "$STATUS"