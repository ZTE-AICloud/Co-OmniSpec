#!/usr/bin/env bash
# workflow agent 更新 SDD 状态（禁止 LLM 手写 .omnispec-state.json）
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
  ${CLAUDE_PLUGIN_ROOT}/scripts/bash/workflow-update-state.sh --feature-dir <path> --current-stage <stage> \
    [--flow-mode express|standard|deep] \
    [--mark-complete <stage>]... \
    [--step "<描述>"] [--note "<备注>"] [--no-sync-progress] \
    [--arguments "<text>"]

示例（review 通过后）:
  ${CLAUDE_PLUGIN_ROOT}/scripts/bash/workflow-update-state.sh --feature-dir "$FEATURE_DIR" --flow-mode express \
    --current-stage review --mark-complete review \
    --step "Step 6: review 完成"

说明: 默认在更新 .omnispec-state.json 后同步刷新 workflow-progress.md

退出码: 0 成功；非 0 失败
EOF
}

FEATURE_DIR=""
CURRENT_STAGE=""
FLOW_MODE=""
MARK_COMPLETE=()
ARGUMENTS=""
VALIDATION_JSON=""
STEP=""
NOTE=""
NO_SYNC_PROGRESS=""
IGNORE_GATE_GUARD=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --feature-dir) FEATURE_DIR="$2"; shift 2 ;;
    --current-stage) CURRENT_STAGE="$2"; shift 2 ;;
    --flow-mode) FLOW_MODE="$2"; shift 2 ;;
    --mark-complete) MARK_COMPLETE+=("$2"); shift 2 ;;
    --arguments) ARGUMENTS="$2"; shift 2 ;;
    --validation-json) VALIDATION_JSON="$2"; shift 2 ;;
    --step) STEP="$2"; shift 2 ;;
    --note) NOTE="$2"; shift 2 ;;
    --no-sync-progress) NO_SYNC_PROGRESS=1; shift ;;
    --ignore-gate-guard) IGNORE_GATE_GUARD=1; shift ;;
    -h|--help) show_help; exit 0 ;;
    *) echo "未知参数: $1" >&2; show_help; exit 2 ;;
  esac
done

if [[ -z "$FEATURE_DIR" || -z "$CURRENT_STAGE" ]]; then
  echo "错误: 必须提供 --feature-dir 与 --current-stage" >&2
  show_help
  exit 2
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 is required" >&2
  exit 1
fi

if [[ -z "$FLOW_MODE" ]]; then
  FLOW_MODE="$(python3 "$STATE_PY" resolve-flow-mode --feature-dir "$FEATURE_DIR" | python3 -c "import json,sys; print(json.load(sys.stdin)['flow_mode'])")"
fi

# P1c：--ignore-gate-guard 已完全禁用。门禁为硬约束，任何情况下不可跳过。
# 传入该参数仅为向后兼容识别并拒绝（不再有任何放行路径）。
if [[ -n "$IGNORE_GATE_GUARD" ]]; then
  echo "ERROR: --ignore-gate-guard 已禁用。分数门禁为硬约束，不可跳过。" >&2
  echo "       若门禁异常，必须修复 eval / check-eval-score 后重跑该阶段直至 verdict 真实 PASS，不得绕过。" >&2
  exit 2
fi

# 机械门禁守卫（非 LLM）：--mark-complete 的每个 blocking 阶段必须先有 PASS verdict。
# 日志实拍：orchestrator 拿到 check-eval-score exit 1（82<95）仍自行继续。此处把门禁结果
# 变成 state 推进的硬条件——blocking 门禁未过则拒绝标记完成，LLM 绕不过。
if [[ ${#MARK_COMPLETE[@]} -gt 0 ]]; then
  GATE_GUARD_PY="$PLUGIN_ROOT/scripts/python/workflow_gate_guard.py"
  for stage in "${MARK_COMPLETE[@]}"; do
    if ! python3 "$GATE_GUARD_PY" \
        --feature-dir "$FEATURE_DIR" --flow-mode "$FLOW_MODE" \
        --stage "$stage" --plugin-root "$PLUGIN_ROOT"; then
      echo "ERROR: 拒绝更新状态——stage '$stage' 分数门禁未通过。" >&2
      echo "       （恢复方式：重跑该阶段提分，使 check-eval-score verdict 真实 PASS；门禁不可跳过）" >&2
      exit 1
    fi
  done
fi

ARGS=(update --feature-dir "$FEATURE_DIR" --current-stage "$CURRENT_STAGE")
[[ -n "$FLOW_MODE" ]] && ARGS+=(--flow-mode "$FLOW_MODE")
[[ -n "$ARGUMENTS" ]] && ARGS+=(--arguments "$ARGUMENTS")
[[ -n "$VALIDATION_JSON" ]] && ARGS+=(--validation-json "$VALIDATION_JSON")
[[ -n "$STEP" ]] && ARGS+=(--step "$STEP")
[[ -n "$NOTE" ]] && ARGS+=(--note "$NOTE")
[[ -n "$NO_SYNC_PROGRESS" ]] && ARGS+=(--no-sync-progress)
for stage in "${MARK_COMPLETE[@]}"; do
  ARGS+=(--mark-complete "$stage")
done

exec python3 "$STATE_PY" "${ARGS[@]}"
