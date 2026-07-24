#!/usr/bin/env bash
# express/SDD workflow 与 local-sandbox-fix harness 衔接门禁
set -euo pipefail

SCRIPT_DIR="$(CDPATH="" cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=local-sandbox-fix-common.sh
source "${SCRIPT_DIR}/local-sandbox-fix-common.sh"

readonly USAGE_MSG="Usage: $0 --feature-dir <path> --check pre|complete [--working-dir <path>]"

require_python3

FEATURE_DIR=""
WORKING_DIR=""
CHECK=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --feature-dir)
      shift
      [[ $# -gt 0 ]] || { echo "Error: --feature-dir requires a value" >&2; exit 2; }
      FEATURE_DIR="$1"
      ;;
    --working-dir)
      shift
      [[ $# -gt 0 ]] || { echo "Error: --working-dir requires a value" >&2; exit 2; }
      WORKING_DIR="$1"
      ;;
    --check)
      shift
      [[ $# -gt 0 ]] || { echo "Error: --check requires a value" >&2; exit 2; }
      CHECK="$1"
      ;;
    -h|--help)
      echo "$USAGE_MSG"
      exit 0
      ;;
    *)
      echo "未知参数: $1" >&2
      echo "$USAGE_MSG" >&2
      exit 2
      ;;
  esac
  shift
done

[[ -n "$FEATURE_DIR" && -n "$CHECK" ]] || {
  echo "$USAGE_MSG" >&2
  exit 2
}

ARGS=(workflow-gate --feature-dir "$FEATURE_DIR" --check "$CHECK")
[[ -n "$WORKING_DIR" ]] && ARGS+=(--working-dir "$WORKING_DIR")

exec "$PYTHON3" "$(local_sandbox_fix_harness_py)" "${ARGS[@]}"
