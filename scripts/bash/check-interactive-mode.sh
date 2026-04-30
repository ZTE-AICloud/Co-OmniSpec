#!/usr/bin/env bash
# 检查交互模式状态脚本
# 用于 AI Agent 判断是否需要用户确认

# 获取脚本所在目录
SCRIPT_DIR="$(CDPATH="" cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 加载公共函数
source "$SCRIPT_DIR/common.sh"

# 获取参数（从命令行参数或环境变量）
args="${1:-${ARGUMENTS:-}}"

# 判断是否需要确认
if should_require_confirmation "$args"; then
    echo '{"interactive": true, "auto_confirm": false, "mode": "interactive"}'
else
    echo '{"interactive": false, "auto_confirm": true, "mode": "auto"}'
fi

