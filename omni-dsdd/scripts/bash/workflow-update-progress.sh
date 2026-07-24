#!/usr/bin/env bash
# 根据 .omnispec-state.json 生成/更新 FEATURE_DIR/.runs/workflow-progress.md
set -euo pipefail

SCRIPT_DIR="$(CDPATH="" cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -n "${CLAUDE_PLUGIN_ROOT:-}" && -d "${CLAUDE_PLUGIN_ROOT}" ]]; then
  PLUGIN_ROOT="$(CDPATH="" cd "${CLAUDE_PLUGIN_ROOT}" && pwd)"
else
  PLUGIN_ROOT="$(CDPATH="" cd "$SCRIPT_DIR/../.." && pwd)"
fi
STATE_PY="$PLUGIN_ROOT/scripts/python/omnispec_state.py"

show_help() {
  cat <<'EOF'
用法:
  workflow-update-progress.sh --feature-dir <path> [--step "<描述>"] [--note "<备注>"]

说明:
  在 workflow-update-state.sh 之后调用，将机器可读状态同步为人类可读进度文件:
  <FEATURE_DIR>/.runs/workflow-progress.md

退出码: 0 成功；非 0 失败
EOF
}

FEATURE_DIR=""
STEP=""
NOTE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --feature-dir) FEATURE_DIR="$2"; shift 2 ;;
    --step) STEP="$2"; shift 2 ;;
    --note) NOTE="$2"; shift 2 ;;
    -h|--help) show_help; exit 0 ;;
    *) echo "未知参数: $1" >&2; show_help; exit 2 ;;
  esac
done

if [[ -z "$FEATURE_DIR" ]]; then
  echo "错误: 必须提供 --feature-dir" >&2
  show_help
  exit 2
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 is required" >&2
  exit 1
fi

ARGS=(progress --feature-dir "$FEATURE_DIR")
[[ -n "$STEP" ]] && ARGS+=(--step "$STEP")
[[ -n "$NOTE" ]] && ARGS+=(--note "$NOTE")

exec python3 "$STATE_PY" "${ARGS[@]}"
