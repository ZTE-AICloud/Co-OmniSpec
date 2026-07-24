#!/usr/bin/env bash
# Inherit FEATURE_DIR / BRANCH_NAME from specify paths.json (not git branch guess).
set -euo pipefail

SCRIPT_DIR="$(CDPATH="" cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=design-harness-common.sh
source "${SCRIPT_DIR}/design-harness-common.sh"

require_python3

PLUGIN_ROOT=""
WORKING_DIR=""
FEATURE_DIR=""
BRANCH_NAME=""
EXPORT_MODE=false
EXTRA=()

usage() {
  cat <<'EOF'
Usage: design-resolve-context.sh --plugin-root <path> --working-dir <path> [OPTIONS]

Options:
  --feature-dir <path>   Optional override (default: resolve from specify upstream)
  --branch-name <name>   Optional override (default: paths.json / env.sh)
  --json                 Print JSON (default)
  --export               Print export statements for eval
  -h, --help             Show help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --plugin-root)
      shift
      [[ $# -gt 0 ]] || { echo "ERROR: --plugin-root requires a value" >&2; exit 2; }
      PLUGIN_ROOT="$1"
      ;;
    --working-dir)
      shift
      [[ $# -gt 0 ]] || { echo "ERROR: --working-dir requires a value" >&2; exit 2; }
      WORKING_DIR="$1"
      ;;
    --feature-dir)
      shift
      [[ $# -gt 0 ]] || { echo "ERROR: --feature-dir requires a value" >&2; exit 2; }
      FEATURE_DIR="$1"
      ;;
    --branch-name)
      shift
      [[ $# -gt 0 ]] || { echo "ERROR: --branch-name requires a value" >&2; exit 2; }
      BRANCH_NAME="$1"
      ;;
    --export)
      EXPORT_MODE=true
      ;;
    --json)
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      EXTRA+=("$1")
      ;;
  esac
  shift
done

[[ -n "$PLUGIN_ROOT" && -n "$WORKING_DIR" ]] || {
  usage >&2
  echo "ERROR: --plugin-root and --working-dir are required" >&2
  exit 2
}

ARGS=(resolve-context --plugin-root "$PLUGIN_ROOT" --working-dir "$WORKING_DIR")
[[ -n "$FEATURE_DIR" ]] && ARGS+=(--feature-dir "$FEATURE_DIR")
[[ -n "$BRANCH_NAME" ]] && ARGS+=(--branch-name "$BRANCH_NAME")
$EXPORT_MODE && ARGS+=(--export)

exec python3 "$(design_harness_py)" "${ARGS[@]}" "${EXTRA[@]}"
