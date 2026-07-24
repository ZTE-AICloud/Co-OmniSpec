#!/usr/bin/env bash
# Build --feature-dir / --branch-name CLI suffix for specify skill invocation.
# Wraps resolve-feature-context.sh; outputs empty when not in preset mode.
# Note: SDD 主链路（sdd → routing → workflow）已改为会话变量拼 PRESET_SPECIFY_ARGS；
# 本脚本保留供独立调用与 test_resolve_feature_context.sh 验收。
#
# Usage:
#   PRESET_ARGS=$(bash build-specify-feature-args.sh \
#     --working-dir "${CLAUDE_WORKING_DIR}" \
#     [--feature-dir "<routing PRESET>"] \
#     [--branch-name "<routing PRESET>"])
#   Skill("specify") with: "$ARGUMENTS $PRESET_ARGS"
set -euo pipefail

SCRIPT_DIR="$(CDPATH="" cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

WORKING_DIR=""
CLI_FEATURE_DIR=""
CLI_BRANCH_NAME=""

usage() {
    cat <<'EOF'
Usage: build-specify-feature-args.sh --working-dir <path> [OPTIONS]

Options:
  --working-dir <path>   Workspace root (required)
  --feature-dir <dir>    Routing PRESET (optional; empty = read shell env)
  --branch-name <name>   Routing PRESET (optional; empty = read shell env)
  --help, -h             Show help

Outputs a shell-quoted CLI suffix for specify (e.g. --feature-dir '...' --branch-name '...'),
or nothing when feature_context_preset=false.
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --working-dir)
            [[ $# -gt 1 ]] || { echo "ERROR: --working-dir requires a value" >&2; exit 1; }
            WORKING_DIR="$2"
            shift 2
            ;;
        --feature-dir)
            [[ $# -gt 1 ]] || { echo "ERROR: --feature-dir requires a value" >&2; exit 1; }
            CLI_FEATURE_DIR="$2"
            shift 2
            ;;
        --branch-name)
            [[ $# -gt 1 ]] || { echo "ERROR: --branch-name requires a value" >&2; exit 1; }
            CLI_BRANCH_NAME="$2"
            shift 2
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        *)
            echo "ERROR: Unknown option '$1'" >&2
            usage >&2
            exit 1
            ;;
    esac
done

[[ -n "$WORKING_DIR" ]] || { echo "ERROR: --working-dir is required" >&2; exit 1; }

resolve_args=(--working-dir "$WORKING_DIR")
[[ -n "$CLI_FEATURE_DIR" ]] && resolve_args+=(--feature-dir "$CLI_FEATURE_DIR")
[[ -n "$CLI_BRANCH_NAME" ]] && resolve_args+=(--branch-name "$CLI_BRANCH_NAME")

json="$(
    bash "${SCRIPT_DIR}/resolve-feature-context.sh" \
        "${resolve_args[@]}" \
        --json 2>/dev/null
)"

python3 -c '
import json
import shlex
import sys

raw = sys.stdin.read().strip()
if not raw:
    sys.exit(0)

data = json.loads(raw)
if not data.get("feature_context_preset"):
    sys.exit(0)

parts = []
feature_dir = (data.get("feature_dir") or "").strip()
branch_name = (data.get("branch_name") or "").strip()
if feature_dir:
    parts.extend(["--feature-dir", feature_dir])
if branch_name:
    parts.extend(["--branch-name", branch_name])
if parts:
    print(" ".join(shlex.quote(p) for p in parts))
' <<<"$json"
