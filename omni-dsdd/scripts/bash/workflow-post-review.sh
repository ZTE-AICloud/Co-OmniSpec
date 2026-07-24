#!/usr/bin/env bash
# review 技能结束时：落盘状态、同步 workflow-progress.md
set -euo pipefail

SCRIPT_DIR="$(CDPATH="" cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -n "${CLAUDE_PLUGIN_ROOT:-}" && -d "${CLAUDE_PLUGIN_ROOT}" ]]; then
  PLUGIN_ROOT="$(CDPATH="" cd "${CLAUDE_PLUGIN_ROOT}" && pwd)"
else
  PLUGIN_ROOT="$(CDPATH="" cd "$SCRIPT_DIR/../.." && pwd)"
fi

UPDATE_STATE="$PLUGIN_ROOT/scripts/bash/workflow-update-state.sh"

show_help() {
  cat <<'EOF'
用法:
  workflow-post-review.sh --feature-dir <path>

说明:
  在 security-review + code-review 结束后调用：
  1. 标记 review 完成
  2. 同步 workflow-progress.md

退出码:
  0  成功
  1  失败
EOF
}

FEATURE_DIR=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --feature-dir) FEATURE_DIR="$2"; shift 2 ;;
    -h|--help) show_help; exit 0 ;;
    *) echo "未知参数: $1" >&2; show_help; exit 2 ;;
  esac
done

if [[ -z "$FEATURE_DIR" ]]; then
  echo "错误: 必须提供 --feature-dir" >&2
  show_help
  exit 2
fi

FEATURE_DIR="$(CDPATH="" cd "$FEATURE_DIR" && pwd)"
STATE_FILE="$FEATURE_DIR/.runs/.omnispec-state.json"

FLOW_MODE=""
if [[ -f "$STATE_FILE" ]]; then
  FLOW_MODE="$(python3 -c "import json; print(json.load(open('$STATE_FILE'))['flow_mode'] or '')" 2>/dev/null || true)"
fi

ARGS=(
  --feature-dir "$FEATURE_DIR"
  --current-stage review
  --mark-complete review
  --step "Step 6: review 完成（post-review）"
  --note "review 完成"
)
[[ -n "$FLOW_MODE" ]] && ARGS+=(--flow-mode "$FLOW_MODE")

bash "$UPDATE_STATE" "${ARGS[@]}"

exit 0
