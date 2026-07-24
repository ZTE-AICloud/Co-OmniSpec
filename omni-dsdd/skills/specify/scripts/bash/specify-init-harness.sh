#!/usr/bin/env bash
# 初始化 specify harness（skills/specify 专用）
set -euo pipefail

SCRIPT_DIR="$(CDPATH="" cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=specify-harness-common.sh
source "${SCRIPT_DIR}/specify-harness-common.sh"

readonly USAGE_MSG="Usage: $0 --plugin-root <path> --working-dir <path> --feature-dir <path> [options]"

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
      echo ""
      echo "Options forwarded to specify_harness.py init:"
      echo "  --branch-name, --spec-file, --doc-dir, --knowledge-dir, --start-time, --run-id"
      exit 0
      ;;
    *)
      EXTRA+=("$1")
      ;;
  esac
  shift
done

if [[ -z "$PLUGIN_ROOT" || -z "$WORKING_DIR" || -z "$FEATURE_DIR" ]]; then
  echo "$USAGE_MSG" >&2
  echo "Error: --plugin-root, --working-dir and --feature-dir are required" >&2
  exit 2
fi

exec python3 "$(specify_harness_py)" init \
  --plugin-root "$PLUGIN_ROOT" \
  --working-dir "$WORKING_DIR" \
  --feature-dir "$FEATURE_DIR" \
  "${EXTRA[@]}"
