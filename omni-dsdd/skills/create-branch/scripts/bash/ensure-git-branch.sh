#!/usr/bin/env bash
# 创建/复用/切换 Git 特性分支（不含目录创建）
set -euo pipefail

SCRIPT_DIR="$(CDPATH="" cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=create-branch-common.sh
source "${SCRIPT_DIR}/create-branch-common.sh"

readonly USAGE_MSG="Usage: $0 --working-dir <path> --has-git <true|false> --branch-name <name>"

WORKING_DIR=""
HAS_GIT=""
BRANCH_NAME=""

while [ $# -gt 0 ]; do
    case "$1" in
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
            BRANCH_NAME="$1"
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

if [ -z "$BRANCH_NAME" ]; then
    echo "Error: --branch-name is required" >&2
    exit 1
fi

ensure_git_branch() {
    local branch_name="$1"
    local working_dir="$2"
    local has_git="$3"

    if [ "$has_git" != true ]; then
        echo "[create-branch] Warning: Git not enabled; skipped branch operation for $branch_name" >&2
        return 0
    fi

    if git -C "$working_dir" show-ref --verify --quiet "refs/heads/$branch_name"; then
        git -C "$working_dir" checkout "$branch_name" >/dev/null 2>&1 || git -C "$working_dir" checkout "$branch_name"
    elif git -C "$working_dir" ls-remote --exit-code --heads origin "$branch_name" >/dev/null 2>&1; then
        git -C "$working_dir" checkout -b "$branch_name" --track "origin/$branch_name" >/dev/null 2>&1 \
            || git -C "$working_dir" checkout -b "$branch_name" --track "origin/$branch_name"
    else
        git -C "$working_dir" checkout -b "$branch_name" >/dev/null 2>&1 || git -C "$working_dir" checkout -b "$branch_name"
    fi
}

ensure_git_branch "$BRANCH_NAME" "$WORKING_DIR" "$HAS_GIT"
export SPECIFY_FEATURE="$BRANCH_NAME"
