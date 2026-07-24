#!/usr/bin/env bash
# 分数门禁（确定性）：读取阶段 eval 文件，比对 min_score，不达标 exit 1。
#
# 替代 orchestrator LLM 软约束（日志实拍：specify 91、design 80.4 均低于阈值却放行）。
# 退出码：0 通过 / 1 未通过 / 2 参数错误。
#
# 用法:
#   check-eval-score.sh --feature-dir <FEATURE_DIR> --stage specify [--min-score 95]
#   check-eval-score.sh --eval-file <path> [--min-score 95] [--format json|yaml|md]
#
# --stage 取值对应的默认 eval 文件（位于 $FEATURE_DIR/.runs/evaluations/）：
#   specify -> eval-specify-report.yaml
#   clarify -> eval-specify-report.yaml  (同文件，含 clarify stage 评分)
#   design  -> eval-design-summary.json
set -euo pipefail

SCRIPT_DIR="$(CDPATH="" cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(CDPATH="" cd "${SCRIPT_DIR}/../.." && pwd)"

FEATURE_DIR=""
EVAL_FILE=""
STAGE=""
MIN_SCORE="95"
FORMAT=""

show_help() {
  cat <<'EOF'
分数门禁（确定性 eval 校验）

用法:
  check-eval-score.sh --feature-dir <dir> --stage specify [--min-score 95] [--format yaml]
  check-eval-score.sh --eval-file <path> [--min-score 95] [--format json]

--stage 默认 eval 文件（$FEATURE_DIR/.runs/evaluations/）:
  specify | clarify -> eval-specify-report.yaml
  design           -> eval-design-summary.json
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --feature-dir) FEATURE_DIR="$2"; shift 2 ;;
    --eval-file)   EVAL_FILE="$2"; shift 2 ;;
    --stage)       STAGE="$2"; shift 2 ;;
    --min-score)   MIN_SCORE="$2"; shift 2 ;;
    --format)      FORMAT="$2"; shift 2 ;;
    -h|--help)     show_help; exit 0 ;;
    *) echo "未知参数: $1" >&2; show_help; exit 2 ;;
  esac
done

# 解析 eval 文件路径
if [[ -z "$EVAL_FILE" ]]; then
  if [[ -z "$FEATURE_DIR" || -z "$STAGE" ]]; then
    echo "错误: 必须提供 --eval-file，或同时提供 --feature-dir 与 --stage" >&2
    show_help; exit 2
  fi
  case "$STAGE" in
    specify|clarify) EVAL_FILE="${FEATURE_DIR}/.runs/evaluations/eval-specify-report.yaml" ;;
    design)          EVAL_FILE="${FEATURE_DIR}/.runs/evaluations/eval-design-summary.json" ;;
    *)
      echo "错误: 未知 stage '${STAGE}'，请用 --eval-file 显式指定" >&2
      exit 2 ;;
  esac
fi

if [[ ! -f "$EVAL_FILE" ]]; then
  echo "[check-eval-score] EVAL_FILE_NOT_FOUND: $EVAL_FILE" >&2
  exit 1  # eval 文件缺失视为未通过（阻断），避免 LLM 误判"没 eval 就算通过"
fi

FORMAT_ARG=()
[[ -n "$FORMAT" ]] && FORMAT_ARG=(--format "$FORMAT")

# P2：--eval-file 模式下若缺 feature-dir/stage，从 eval 文件路径反推，保证 verdict 必然落盘。
# 修 wsm-8 类问题：orchestrator 用 --eval-file 调用时 verdict 没生成 → 守卫读不到。
if [[ -z "$FEATURE_DIR" ]]; then
  FEATURE_DIR="$(cd "$(dirname "$EVAL_FILE")/../.." 2>/dev/null && pwd)"
fi
if [[ -z "$STAGE" ]]; then
  case "$(basename "$EVAL_FILE")" in
    eval-specify*) STAGE="specify" ;;
    eval-clarify*) STAGE="clarify" ;;
    eval-design*)  STAGE="design"  ;;
  esac
fi

# 透传 --feature-dir + --stage，让 check_eval_score.py 落盘 verdict 标记（守卫读取用）
VERDICT_ARG=()
[[ -n "$FEATURE_DIR" && -n "$STAGE" ]] && VERDICT_ARG=(--feature-dir "$FEATURE_DIR" --stage "$STAGE")

python3 "${PLUGIN_ROOT}/scripts/python/check_eval_score.py" \
  --eval-file "$EVAL_FILE" \
  --min-score "$MIN_SCORE" \
  "${FORMAT_ARG[@]}" \
  "${VERDICT_ARG[@]}"
