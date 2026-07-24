#!/usr/bin/env bash
# 自动续跑检查器：检测 analyze 后是否必须继续 implement/review（不执行 Skill，由 agent 调用）
# 退出码 10/11 时，编排方必须同步调用 Skill("implement") 或 review 技能，禁止输出「SDD 执行完成」
set -euo pipefail

SCRIPT_DIR="$(CDPATH="" cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -n "${CLAUDE_PLUGIN_ROOT:-}" && -d "${CLAUDE_PLUGIN_ROOT}" ]]; then
  PLUGIN_ROOT="$(CDPATH="" cd "${CLAUDE_PLUGIN_ROOT}" && pwd)"
else
  PLUGIN_ROOT="$(CDPATH="" cd "$SCRIPT_DIR/../.." && pwd)"
fi

show_help() {
  cat <<'EOF'
用法:
  workflow-autocontinue.sh --feature-dir <path> [--trigger-step <name>]

说明:
  包装 workflow-check-incomplete.sh；不执行 implement（Skill 只能由 agent 调用）。

退出码:
  0  无需续跑或 workflow 已完成
  10 必须立即 Skill("implement")
  11 必须继续 security-review + code-review
EOF
}

FEATURE_DIR=""
TRIGGER_STEP="analyze"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --feature-dir) FEATURE_DIR="$2"; shift 2 ;;
    --trigger-step) TRIGGER_STEP="$2"; shift 2 ;;
    -h|--help) show_help; exit 0 ;;
    *) echo "未知参数: $1" >&2; show_help; exit 2 ;;
  esac
done

if [[ -z "$FEATURE_DIR" ]]; then
  echo "错误: 必须提供 --feature-dir" >&2
  show_help
  exit 2
fi

CHECK_SH="$PLUGIN_ROOT/scripts/bash/workflow-check-incomplete.sh"
set +e
result="$(bash "$CHECK_SH" --feature-dir "$FEATURE_DIR")"
code=$?
set -e

echo "$result"

if [[ "$code" -eq 10 ]]; then
  echo "[workflow-autocontinue] trigger=$TRIGGER_STEP -> MUST call Skill(\"implement\") now" >&2
  exit 10
fi
if [[ "$code" -eq 11 ]]; then
  echo "[workflow-autocontinue] trigger=$TRIGGER_STEP -> MUST call security-review + code-review" >&2
  exit 11
fi

exit "$code"
