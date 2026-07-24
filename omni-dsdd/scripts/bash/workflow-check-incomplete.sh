#!/usr/bin/env bash
# 检查 SDD workflow 是否仍有未完成阶段；供 routing/sdd/analyze 后置续跑使用
set -euo pipefail

SCRIPT_DIR="$(CDPATH="" cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -n "${CLAUDE_PLUGIN_ROOT:-}" && -d "${CLAUDE_PLUGIN_ROOT}" ]]; then
  PLUGIN_ROOT="$(CDPATH="" cd "${CLAUDE_PLUGIN_ROOT}" && pwd)"
else
  PLUGIN_ROOT="$(CDPATH="" cd "$SCRIPT_DIR/../.." && pwd)"
fi

STATE_PY="$PLUGIN_ROOT/scripts/python/omnispec_state.py"
GATE_SH="$PLUGIN_ROOT/scripts/bash/workflow-gate.sh"

show_help() {
  cat <<'EOF'
用法:
  workflow-check-incomplete.sh [--feature-dir <path>]

说明:
  检查 .omnispec-state.json 的 completed_stages，判断 workflow 是否仍需继续。

退出码:
  0  workflow 已完成（implement + review 均在 completed_stages）
  10 需要继续执行 implement（expert: tasks 已完成；其他: analyze 已完成或 tasks 已就绪；但 implement 未完成）
  11 需要继续执行 review（implement 已完成但 review 未完成）
  12 需要继续执行 local-sandbox-fix（expert 已 review 但 sandbox 未完成）
  1  状态文件缺失或无法解析

stdout: JSON 一行，含 next_skill、feature_dir、completed_stages 等
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

if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 is required" >&2
  exit 1
fi

if [[ -z "$FEATURE_DIR" ]]; then
  resolved="$(python3 "$STATE_PY" resolve 2>/dev/null || true)"
  FEATURE_DIR="$(python3 -c "import json,sys; d=json.loads(sys.argv[1]); print(d.get('FEATURE_DIR') or '')" "$resolved" 2>/dev/null || true)"
fi

if [[ -z "$FEATURE_DIR" || ! -d "$FEATURE_DIR" ]]; then
  echo '{"status":"error","reason":"feature_dir_unresolved"}'
  exit 1
fi

FEATURE_DIR="$(CDPATH="" cd "$FEATURE_DIR" && pwd)"
STATE_FILE="$FEATURE_DIR/.runs/.omnispec-state.json"

if [[ ! -f "$STATE_FILE" ]]; then
  echo "{\"status\":\"error\",\"reason\":\"state_missing\",\"feature_dir\":\"$FEATURE_DIR\"}"
  exit 1
fi

read_state() {
  python3 - "$STATE_FILE" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as f:
    state = json.load(f)
completed = list(state.get("completed_stages") or [])
print(json.dumps({
    "flow_mode": state.get("flow_mode") or "",
    "current_stage": state.get("current_stage") or "",
    "completed_stages": completed,
}, ensure_ascii=False))
PY
}

STATE_JSON="$(read_state)"
COMPLETED="$(python3 -c "import json,sys; print(','.join(json.loads(sys.argv[1])['completed_stages']))" "$STATE_JSON")"
FLOW_MODE="$(python3 -c "import json,sys; print(json.loads(sys.argv[1])['flow_mode'])" "$STATE_JSON")"

has_stage() {
  echo ",$COMPLETED," | grep -q ",$1,"
}

# workflow 完整交付
if has_stage implement && has_stage review; then
  if [[ "$FLOW_MODE" == "expert" ]] && ! has_stage local-sandbox-fix; then
    echo "{\"status\":\"incomplete\",\"next_skill\":\"local-sandbox-fix\",\"feature_dir\":\"$FEATURE_DIR\",\"flow_mode\":\"$FLOW_MODE\",\"forbidden_summary\":true,\"message\":\"expert workflow 已完成 review 但 local-sandbox-fix 未完成，禁止输出 SDD 执行完成\"}"
    exit 12
  fi
  echo "{\"status\":\"complete\",\"feature_dir\":\"$FEATURE_DIR\",\"flow_mode\":\"$FLOW_MODE\",\"completed_stages\":$(python3 -c "import json,sys; print(json.dumps(json.loads(sys.argv[1])['completed_stages']))" "$STATE_JSON")}"
  exit 0
fi

if has_stage implement && ! has_stage review; then
  echo "{\"status\":\"incomplete\",\"next_skill\":\"review\",\"next_skills\":[\"security-review\",\"code-review\"],\"feature_dir\":\"$FEATURE_DIR\",\"flow_mode\":\"$FLOW_MODE\",\"forbidden_summary\":true}"
  exit 11
fi

# implement 未完成：expert 在 tasks 后直接进入 implement；其他流程兼容 analyze/tasks 就绪态。
if [[ "$FLOW_MODE" == "expert" ]]; then
  if has_stage tasks; then
    echo "{\"status\":\"incomplete\",\"next_skill\":\"implement\",\"feature_dir\":\"$FEATURE_DIR\",\"flow_mode\":\"$FLOW_MODE\",\"forbidden_summary\":true,\"message\":\"expert tasks 已完成但 implement 未完成，禁止输出 SDD 执行完成\"}"
    exit 10
  fi
elif has_stage analyze || has_stage tasks; then
  echo "{\"status\":\"incomplete\",\"next_skill\":\"implement\",\"feature_dir\":\"$FEATURE_DIR\",\"flow_mode\":\"$FLOW_MODE\",\"forbidden_summary\":true,\"message\":\"analyze/tasks 已完成但 implement 未完成，禁止输出 SDD 执行完成\"}"
  exit 10
fi

echo "{\"status\":\"incomplete\",\"next_skill\":\"unknown\",\"feature_dir\":\"$FEATURE_DIR\",\"flow_mode\":\"$FLOW_MODE\",\"completed_stages\":$(python3 -c "import json,sys; print(json.dumps(json.loads(sys.argv[1])['completed_stages']))" "$STATE_JSON")}"
exit 10
