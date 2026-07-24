#!/usr/bin/env bash
# 创建 changes/ 下功能目录并输出 BRANCH_NAME / FEATURE_DIR / SPEC_FILE
set -euo pipefail

SCRIPT_DIR="$(CDPATH="" cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=create-branch-common.sh
source "${SCRIPT_DIR}/create-branch-common.sh"

readonly USAGE_MSG="Usage: $0 --working-dir <path> --has-git <true|false> [--json] [--branch-name <name>] [--feature-dir <dir>]"

JSON_MODE=false
WORKING_DIR=""
HAS_GIT=""
BRANCH_NAME_INPUT=""
FEATURE_DIR_INPUT=""

while [ $# -gt 0 ]; do
    case "$1" in
        --json)
            JSON_MODE=true
            ;;
        --working-dir)
            shift
            [ $# -gt 0 ] || { echo "Error: --working-dir requires a value" >&2; exit 1; }
            WORKING_DIR="$1"
            ;;
        --has-git)
            shift
            [ $# -gt 0 ] || { echo "Error: --has-git requires a value" >&2; exit 1; }
            HAS_GIT="$1"
            ;;
        --branch-name)
            shift
            [ $# -gt 0 ] || { echo "Error: --branch-name requires a value" >&2; exit 1; }
            BRANCH_NAME_INPUT="$1"
            ;;
        --feature-dir)
            shift
            [ $# -gt 0 ] || { echo "Error: --feature-dir requires a value" >&2; exit 1; }
            FEATURE_DIR_INPUT="$1"
            ;;
        --help|-h)
            echo "$USAGE_MSG"
            exit 0
            ;;
        *)
            echo "$USAGE_MSG" >&2
            echo "Error: Unknown argument: $1" >&2
            exit 1
            ;;
    esac
    shift
done

create_branch_require_working_dir || exit 1
create_branch_require_has_git || exit 1

if [ -z "$BRANCH_NAME_INPUT" ] && [ -z "$FEATURE_DIR_INPUT" ]; then
    echo "$USAGE_MSG" >&2
    echo "Error: one of --branch-name or --feature-dir is required" >&2
    exit 1
fi

CHANGES_DIR="$WORKING_DIR/changes"
mkdir -p "$CHANGES_DIR"

branch_name="$BRANCH_NAME_INPUT"
feature_dir="$FEATURE_DIR_INPUT"
spec_file=""

if [ -n "$feature_dir" ]; then
    feature_dir="$(create_branch_resolve_feature_dir_path "$feature_dir" "$WORKING_DIR" "$CHANGES_DIR")"
elif [ -n "$branch_name" ]; then
    feature_dir="$CHANGES_DIR/$(create_branch_clean_name "$(basename "$branch_name")")"
fi

if [ -n "$feature_dir" ]; then
    mkdir -p "$feature_dir"
    spec_file="${feature_dir}/spec.md"
fi

create_branch_output_results "$branch_name" "$spec_file" "$feature_dir" "$HAS_GIT" "$JSON_MODE"
