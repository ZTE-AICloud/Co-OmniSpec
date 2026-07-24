#!/usr/bin/env bash
# 机械重试控制器（非 LLM）：按 max_retries 判定 通过/重试/耗尽。
#
# 用法:
#   workflow-converge.sh --feature-dir <dir> --flow-mode <mode> --stage <stage> [--reset]
#
# 退出码（编排器机械行事，不得自行决定停止）:
#   0  CONVERGED  verdict PASS → mark-complete 推进
#   1  RETRY      FAIL 且 attempts < max → 必须再次增量派发该阶段
#   2  EXHAUSTED  FAIL 且 attempts >= max → 停止报告，不推进
#   3  NO_VERDICT 未跑 check-eval-score → 先跑门禁
#
# 配合:
#   - check-eval-score.sh 落 .gate-verdict-<stage>.json
#   - workflow-update-state.sh 守卫拒绝 FAIL 的 mark-complete（即使本脚本未用，也推不过）
set -euo pipefail

SCRIPT_DIR="$(CDPATH="" cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -n "${CLAUDE_PLUGIN_ROOT:-}" && -d "${CLAUDE_PLUGIN_ROOT}" ]]; then
  PLUGIN_ROOT="$(CDPATH="" cd "${CLAUDE_PLUGIN_ROOT}" && pwd)"
else
  PLUGIN_ROOT="$(CDPATH="" cd "$SCRIPT_DIR/.." && pwd)"
fi

FEATURE_DIR=""; FLOW_MODE=""; STAGE=""; RESET=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --feature-dir) FEATURE_DIR="$2"; shift 2 ;;
    --flow-mode)   FLOW_MODE="$2"; shift 2 ;;
    --stage)       STAGE="$2"; shift 2 ;;
    --reset)       RESET=1; shift ;;
    -h|--help)
      sed -n '2,18p' "${BASH_SOURCE[0]:-$0}"; exit 0 ;;
    *) echo "未知参数: $1" >&2; exit 2 ;;
  esac
done

[[ -n "$FEATURE_DIR" && -n "$FLOW_MODE" && -n "$STAGE" ]] || {
  echo "用法: $0 --feature-dir <dir> --flow-mode <mode> --stage <stage> [--reset]" >&2
  exit 2
}

RESET_ARG=()
[[ -n "$RESET" ]] && RESET_ARG=(--reset)

python3 "${PLUGIN_ROOT}/scripts/python/workflow_converge.py" \
  --feature-dir "$FEATURE_DIR" --flow-mode "$FLOW_MODE" \
  --stage "$STAGE" --plugin-root "$PLUGIN_ROOT" "${RESET_ARG[@]}"
