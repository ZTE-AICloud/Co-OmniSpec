#!/bin/bash
# -*- coding: utf-8 -*-
#
# 单场景文档生成进度跟踪工具（Bash 包装）
# 调用同 skill 内的 Python 脚本。
#
# 使用方法:
#   get_scenario_detail_progress.sh <repo_root> [--format <format>]
#

set -e
set -u
set -o pipefail

# 获取脚本所在目录（bash/），定位同级 python/ 目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/../python/get_scenario_detail_progress.py"

if [[ ! -f "$PYTHON_SCRIPT" ]]; then
    echo "错误: Python脚本不存在: $PYTHON_SCRIPT" >&2
    exit 1
fi

if ! command -v python3 &>/dev/null; then
    echo "错误: 未找到python3命令" >&2
    exit 1
fi

exec python3 "$PYTHON_SCRIPT" "$@"
