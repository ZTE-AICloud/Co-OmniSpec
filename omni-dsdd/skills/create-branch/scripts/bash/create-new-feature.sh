#!/usr/bin/env bash
# 组合入口：按需调用 ensure-git-branch + create-feature-dir（行为与拆分前一致）
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

show_help() {
    echo "$USAGE_MSG"
    echo ""
    echo "Options:"
    echo "  --working-dir <path>  Workspace root (required; from CLAUDE_WORKING_DIR)"
    echo "  --has-git <true|false> Whether workspace is a Git repo (required)"
    echo "  --json                Output in JSON format"
    echo "  --branch-name <name>  Explicit branch name to create or reuse"
    echo "  --feature-dir <dir>   Feature dir: absolute, changes/foo, or basename under changes/"
    echo "  --help, -h            Show this help message"
    echo ""
    echo "Sub-scripts:"
    echo "  ensure-git-branch.sh  Git branch only"
    echo "  create-feature-dir.sh Feature directory only"
}

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
            show_help
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

if [ -z "$WORKING_DIR" ]; then
    echo "Error: --working-dir is required" >&2
    exit 1
fi
if [ ! -d "$WORKING_DIR" ]; then
    echo "Error: --working-dir is not a directory: $WORKING_DIR" >&2
    exit 1
fi
if [ -z "$HAS_GIT" ]; then
    echo "Error: --has-git is required (true or false)" >&2
    exit 1
fi
case "$HAS_GIT" in
    true|false) ;;
    *)
        echo "Error: --has-git must be true or false" >&2
        exit 1
        ;;
esac

CHANGES_DIR="$WORKING_DIR/changes"
mkdir -p "$CHANGES_DIR"

# 特性目录已存在时仅切换分支并返回路径，避免重复 mkdir / 二次建目录
if [ -n "$BRANCH_NAME_INPUT" ]; then
    _reuse_dir=""
    if [ -n "$FEATURE_DIR_INPUT" ]; then
        _reuse_dir="$(create_branch_resolve_feature_dir_path "$FEATURE_DIR_INPUT" "$WORKING_DIR" "$CHANGES_DIR")"
    else
        _reuse_dir="$CHANGES_DIR/$(create_branch_clean_name "$(basename "$BRANCH_NAME_INPUT")")"
    fi
    if [ -n "$_reuse_dir" ] && [ -d "$_reuse_dir" ]; then
        if [ -f "$_reuse_dir/.runs/branch-naming.json" ] || [ -f "$_reuse_dir/spec.md" ]; then
            # shellcheck source=ensure-git-branch.sh
            bash "${SCRIPT_DIR}/ensure-git-branch.sh" \
                --working-dir "$WORKING_DIR" \
                --has-git "$HAS_GIT" \
                --branch-name "$BRANCH_NAME_INPUT"
            create_branch_output_results \
                "$BRANCH_NAME_INPUT" \
                "${_reuse_dir}/spec.md" \
                "$_reuse_dir" \
                "$HAS_GIT" \
                "$JSON_MODE"
            exit 0
        fi
    fi
fi

if [ -z "$BRANCH_NAME_INPUT" ] && [ -z "$FEATURE_DIR_INPUT" ]; then
    echo "$USAGE_MSG" >&2
    echo "Error: one of --branch-name or --feature-dir is required" >&2
    exit 1
fi

if [ -n "$BRANCH_NAME_INPUT" ]; then
    bash "${SCRIPT_DIR}/ensure-git-branch.sh" \
        --working-dir "$WORKING_DIR" \
        --has-git "$HAS_GIT" \
        --branch-name "$BRANCH_NAME_INPUT"
fi

DIR_ARGS=(
    --working-dir "$WORKING_DIR"
    --has-git "$HAS_GIT"
)
if [ "$JSON_MODE" = true ]; then
    DIR_ARGS+=(--json)
fi
if [ -n "$BRANCH_NAME_INPUT" ]; then
    DIR_ARGS+=(--branch-name "$BRANCH_NAME_INPUT")
fi
if [ -n "$FEATURE_DIR_INPUT" ]; then
    DIR_ARGS+=(--feature-dir "$FEATURE_DIR_INPUT")
fi

exec bash "${SCRIPT_DIR}/create-feature-dir.sh" "${DIR_ARGS[@]}"
