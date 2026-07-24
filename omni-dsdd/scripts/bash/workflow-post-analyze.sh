#!/usr/bin/env bash
# analyze 技能结束时：落盘状态、跑 gate，并指示 agent 必须继续 implement
set -euo pipefail

SCRIPT_DIR="$(CDPATH="" cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -n "${CLAUDE_PLUGIN_ROOT:-}" && -d "${CLAUDE_PLUGIN_ROOT}" ]]; then
  PLUGIN_ROOT="$(CDPATH="" cd "${CLAUDE_PLUGIN_ROOT}" && pwd)"
else
  PLUGIN_ROOT="$(CDPATH="" cd "$SCRIPT_DIR/../.." && pwd)"
fi

UPDATE_STATE="$PLUGIN_ROOT/scripts/bash/workflow-update-state.sh"
UPDATE_PROGRESS="$PLUGIN_ROOT/scripts/bash/workflow-update-progress.sh"
GATE_SH="$PLUGIN_ROOT/scripts/bash/workflow-gate.sh"

show_help() {
  cat <<'EOF'
用法:
  workflow-post-analyze.sh --feature-dir <path>

说明:
  在 analyze 技能修复循环结束后调用：
  1. 标记 analyze 完成，current_stage=implement
  2. 更新 workflow-progress.md
  3. 运行 pre-implement gate
  4. 始终以退出码 0 结束（implement/review 由编排器按 YAML 下一阶段同轮继续）

退出码:
  0  成功（analyze 已落盘）
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

ARGS=(--feature-dir "$FEATURE_DIR" --current-stage implement --mark-complete analyze)
[[ -n "$FLOW_MODE" ]] && ARGS+=(--flow-mode "$FLOW_MODE")

bash "$UPDATE_STATE" "${ARGS[@]}"
bash "$UPDATE_PROGRESS" \
  --feature-dir "$FEATURE_DIR" \
  --step "Step 4: analyze 完成（post-analyze）" \
  --note "analyze 已完成；implement 由编排器 YAML 下一阶段继续"

bash "$GATE_SH" --feature-dir "$FEATURE_DIR" --check pre-implement --record

exit 0
