#!/usr/bin/env bash
# 统一解析 omni-dsdd 共享层根目录。
# 前提：omni-reverse 与 omni-dsdd 安装在同一 marketplace 下且目录并列。
# 用法：DSDD="$(bash "${CLAUDE_PLUGIN_ROOT}/scripts/resolve-dsdd-root.sh")" || exit 1
set -euo pipefail

resolve_dsdd_root() {
  local candidate
  # 优先用插件运行期变量（=omni-reverse 根），向上一级即 marketplace 根
  if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ]; then
    candidate="${CLAUDE_PLUGIN_ROOT}/../omni-dsdd"
  else
    # 回退：从本脚本位置推算 omni-reverse/lib -> ../.. -> marketplace 根
    local here
    here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    candidate="$here/../../omni-dsdd"
  fi
  candidate="$(cd "$candidate" 2>/dev/null && pwd)" || candidate=""

  if [ -z "$candidate" ] || [ ! -d "$candidate/scripts" ] || [ ! -d "$candidate/omni-infra" ]; then
    echo "ERROR: 未找到共享插件 omni-dsdd（期望与 omni-reverse 同 marketplace 并列安装）。" >&2
    echo "       omni-reverse 依赖 omni-dsdd 提供共享脚本与 omni-infra，请一并安装。" >&2
    return 1
  fi
  printf '%s' "$candidate"
}

# 直接执行时打印路径，便于 $(...) 捕获
[ "${BASH_SOURCE[0]}" = "$0" ] && resolve_dsdd_root
