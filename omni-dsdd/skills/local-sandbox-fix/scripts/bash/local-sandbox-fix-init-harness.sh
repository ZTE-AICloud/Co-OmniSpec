#!/usr/bin/env bash
# 初始化 local-sandbox-fix harness
set -euo pipefail

SCRIPT_DIR="$(CDPATH="" cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=local-sandbox-fix-common.sh
source "${SCRIPT_DIR}/local-sandbox-fix-common.sh"

readonly USAGE_MSG="Usage: $0 --plugin-root <path> --working-dir <path> [--feature-dir <path>]"

require_python3

PLUGIN_ROOT=""
WORKING_DIR=""
FEATURE_DIR=""
EXTRA=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --plugin-root)
      shift
      [[ $# -gt 0 ]] || { echo "Error: --plugin-root requires a value" >&2; exit 2; }
      PLUGIN_ROOT="$1"
      ;;
    --working-dir)
      shift
      [[ $# -gt 0 ]] || { echo "Error: --working-dir requires a value" >&2; exit 2; }
      WORKING_DIR="$1"
      ;;
    --feature-dir)
      shift
      [[ $# -gt 0 ]] || { echo "Error: --feature-dir requires a value" >&2; exit 2; }
      FEATURE_DIR="$1"
      ;;
    -h|--help)
      echo "$USAGE_MSG"
      exit 0
      ;;
    *)
      EXTRA+=("$1")
      ;;
  esac
  shift
done

if [[ -z "$PLUGIN_ROOT" || -z "$WORKING_DIR" ]]; then
  echo "$USAGE_MSG" >&2
  echo "Error: --plugin-root and --working-dir are required" >&2
  exit 2
fi

INIT_ARGS=(
  init
  --plugin-root "$PLUGIN_ROOT"
  --working-dir "$WORKING_DIR"
)
[[ -n "$FEATURE_DIR" ]] && INIT_ARGS+=(--feature-dir "$FEATURE_DIR")

exec "$PYTHON3" "$(local_sandbox_fix_harness_py)" "${INIT_ARGS[@]}" "${EXTRA[@]}"
