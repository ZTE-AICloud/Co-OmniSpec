#!/usr/bin/env bash
# 分配稳定分支名（含序号前缀）— create-branch harness 封装
set -euo pipefail

WORKING_DIR=""
PLUGIN_ROOT=""
HARNESS_ARGS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --working-dir)
      WORKING_DIR="$2"
      shift 2
      ;;
    --plugin-root)
      PLUGIN_ROOT="$2"
      shift 2
      ;;
    -h|--help)
      echo "Usage: $0 --working-dir <path> --plugin-root <path> allocate [harness options...]" >&2
      exit 0
      ;;
    *)
      HARNESS_ARGS+=("$1")
      shift
      ;;
  esac
done

if [[ -z "$WORKING_DIR" || -z "$PLUGIN_ROOT" ]]; then
  echo "ERROR: --working-dir and --plugin-root are required" >&2
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 is required" >&2
  exit 1
fi

HARNESS_PY="${PLUGIN_ROOT}/skills/create-branch/scripts/python/create_branch_harness.py"
if [[ ! -f "$HARNESS_PY" ]]; then
  echo "ERROR: harness not found: $HARNESS_PY" >&2
  exit 1
fi

exec python3 "$HARNESS_PY" --working-dir "$WORKING_DIR" "${HARNESS_ARGS[@]}"
