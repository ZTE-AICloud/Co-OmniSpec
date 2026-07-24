#!/usr/bin/env bash
# SDD workflow 阶段门禁：防止未执行 implement/review 即宣告 workflow 结束
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
  workflow-gate.sh --feature-dir <path> --check <name> [--record]

检查项 (--check):
  pre-implement   非 expert 要求 analyze 已完成；expert 要求 tasks 已完成；且 FEATURE_DIR/tasks.md 存在
  post-implement  implement 已在 completed_stages（Step 5 结束后）
  pre-review      同 post-implement（进入 Step 6 前）
  must-continue-after-analyze  analyze 已完成但 implement 未完成时返回失败（禁止误结束）
  workflow-complete  implement 与 review 均已完成；expert 还要求 local-sandbox-fix 状态与 harness 产物均成功（输出最终摘要前）

选项:
  --record  校验通过后向 stderr 打印 [workflow-gate] OK: <check>

退出码: 0 通过；1 未通过
EOF
}

FEATURE_DIR=""
CHECK=""
RECORD=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --feature-dir) FEATURE_DIR="$2"; shift 2 ;;
    --check) CHECK="$2"; shift 2 ;;
    --record) RECORD=1; shift ;;
    -h|--help) show_help; exit 0 ;;
    *) echo "未知参数: $1" >&2; show_help; exit 2 ;;
  esac
done

if [[ -z "$FEATURE_DIR" || -z "$CHECK" ]]; then
  echo "错误: 必须提供 --feature-dir 与 --check" >&2
  show_help
  exit 2
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 is required" >&2
  exit 1
fi

FEATURE_DIR="$(CDPATH="" cd "$FEATURE_DIR" && pwd)"

gate_one() {
  local stage="$1"
  python3 "$STATE_PY" gate --feature-dir "$FEATURE_DIR" --require-completed "$stage" >/dev/null
}

flow_mode() {
  python3 - "$FEATURE_DIR/.runs/.omnispec-state.json" <<'PY'
import json
import sys

try:
    with open(sys.argv[1], "r", encoding="utf-8") as f:
        print((json.load(f).get("flow_mode") or "").strip())
except Exception:
    print("")
PY
}

local_sandbox_complete_gate() {
  local gate_script="$PLUGIN_ROOT/skills/local-sandbox-fix/scripts/bash/local-sandbox-fix-workflow-gate.sh"
  local output
  [[ -f "$gate_script" ]] || {
    echo "local-sandbox-fix workflow gate 不存在: $gate_script" >&2
    return 1
  }
  if ! output="$(bash "$gate_script" --feature-dir "$FEATURE_DIR" --check complete 2>&1)"; then
    printf '%s\n' "$output" >&2
    return 1
  fi
}

fail() {
  echo "workflow-gate [$CHECK] FAILED: $*" >&2
  exit 1
}

pass_msg() {
  if [[ "$RECORD" -eq 1 ]]; then
    echo "[workflow-gate] OK: $CHECK (feature-dir=$FEATURE_DIR)" >&2
  fi
}

case "$CHECK" in
  pre-implement)
    [[ -f "$FEATURE_DIR/tasks.md" ]] || fail "tasks.md 不存在（请先完成 Step 3 tasks）"
    if [[ "$(flow_mode)" == "expert" ]]; then
      gate_one tasks || fail "expert completed_stages 须包含 tasks（请先完成 tasks）"
    else
      gate_one analyze || fail "completed_stages 须包含 analyze（请先完成 Step 4）"
    fi
    ;;
  post-implement|pre-review)
    gate_one implement || fail "completed_stages 须包含 implement（必须先执行 Step 5 implement）"
    ;;
  must-continue-after-analyze)
    if gate_one analyze; then
      if gate_one implement; then
        :
      else
        fail "analyze 已完成但 implement 未完成（必须继续执行 Step 5 implement，禁止结束 workflow）"
      fi
    fi
    ;;
  workflow-complete)
    gate_one implement || fail "workflow 未完成 implement，禁止输出最终摘要"
    gate_one review || fail "workflow 未完成 review，禁止输出最终摘要"
    if [[ "$(flow_mode)" == "expert" ]]; then
      gate_one local-sandbox-fix || fail "expert workflow 未完成 local-sandbox-fix，禁止输出最终摘要"
      local_sandbox_complete_gate || fail "expert local-sandbox-fix 产物门禁未通过，禁止输出最终摘要"
    fi
    # 兜底：仅在 --record（Final 段正式校验）时把 current_stage 置为终态 workflow-complete，
    # 避免停留在最后一个 stage 被误读为"未完成"。探测性调用（无 --record）不写文件。
    if [[ "$RECORD" -eq 1 ]]; then
      python3 "$STATE_PY" update \
        --feature-dir "$FEATURE_DIR" --current-stage workflow-complete --no-sync-progress >/dev/null 2>&1 || true
    fi
    ;;
  *)
    echo "未知 --check: $CHECK" >&2
    show_help
    exit 2
    ;;
esac

pass_msg
exit 0
