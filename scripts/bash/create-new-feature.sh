#!/usr/bin/env bash

set -euo pipefail

readonly USAGE_MSG="Usage: $0 [--json] [--branch-name <name>] [--feature-dir <dir>]"

show_help() {
    echo "$USAGE_MSG"
    echo ""
    echo "Options:"
    echo "  --json               Output in JSON format"
    echo "  --branch-name <name> Explicit branch name to create or reuse"
    echo "  --feature-dir <dir>  Explicit feature directory (absolute path, changes/foo, or foo)"
    echo "  --help, -h           Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 --branch-name 'feature/session-delete-ack'"
    echo "  $0 --feature-dir 'changes/session-delete-ack'"
    echo "  $0 --branch-name 'feature/session-delete-ack' --feature-dir 'session-delete-ack' --json"
}

parse_arguments() {
    JSON_MODE=false
    BRANCH_NAME_INPUT=""
    FEATURE_DIR_INPUT=""

    while [ $# -gt 0 ]; do
        case "$1" in
            --json)
                JSON_MODE=true
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

    if [ -z "$BRANCH_NAME_INPUT" ] && [ -z "$FEATURE_DIR_INPUT" ]; then
        echo "$USAGE_MSG" >&2
        echo "Error: one of --branch-name or --feature-dir is required" >&2
        exit 1
    fi
}

find_repo_root() {
    local dir="$1"
    while [ "$dir" != "/" ]; do
        if [ -d "$dir/.git" ] || [ -d "$dir/.infra" ]; then
            echo "$dir"
            return 0
        fi
        dir="$(dirname "$dir")"
    done
    return 1
}

resolve_repository_root() {
    local script_dir
    script_dir="$(CDPATH="" cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

    if git rev-parse --show-toplevel >/dev/null 2>&1; then
        REPO_ROOT="$(git rev-parse --show-toplevel)"
        HAS_GIT=true
    else
        REPO_ROOT="$(find_repo_root "$script_dir")"
        [ -n "$REPO_ROOT" ] || {
            echo "Error: Could not determine repository root. Please run this script from within the repository." >&2
            exit 1
        }
        HAS_GIT=false
    fi

    cd "$REPO_ROOT"
    CHANGES_DIR="$REPO_ROOT/changes"
    mkdir -p "$CHANGES_DIR"
}

clean_name() {
    echo "$1" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g; s/-\+/-/g; s/^-//; s/-$//'
}

resolve_feature_dir_path() {
    local input="$1"
    local repo_root="$2"
    local changes_dir="$3"

    input="$(echo "$input" | sed 's:/*$::')"

    if [ -z "$input" ]; then
        echo ""
    elif [[ "$input" = /* ]]; then
        echo "$input"
    elif [[ "$input" = changes/* ]]; then
        echo "$repo_root/$input"
    else
        echo "$changes_dir/$input"
    fi
}

ensure_git_branch() {
    local branch_name="$1"
    local has_git="$2"

    [ -n "$branch_name" ] || return 0

    if [ "$has_git" != true ]; then
        echo "[specify] Warning: Git repository not detected; skipped branch creation for $branch_name" >&2
        return 0
    fi

    if git show-ref --verify --quiet "refs/heads/$branch_name"; then
        git checkout "$branch_name" >/dev/null 2>&1 || git checkout "$branch_name"
    elif git ls-remote --exit-code --heads origin "$branch_name" >/dev/null 2>&1; then
        git checkout -b "$branch_name" --track "origin/$branch_name" >/dev/null 2>&1 || git checkout -b "$branch_name" --track "origin/$branch_name"
    else
        git checkout -b "$branch_name" >/dev/null 2>&1 || git checkout -b "$branch_name"
    fi
}

output_results() {
    local branch_name="$1"
    local spec_file="$2"
    local feature_dir="$3"
    local has_git="$4"

    if [ "$JSON_MODE" = true ]; then
        printf '{"BRANCH_NAME":"%s","SPEC_FILE":"%s","FEATURE_DIR":"%s","change_file":"%s","FEATURE_NUM":"","HAS_GIT":"%s"}\n' \
            "$branch_name" "$spec_file" "$feature_dir" "$spec_file" "$has_git"
    else
        echo "BRANCH_NAME: $branch_name"
        echo "SPEC_FILE: $spec_file"
        echo "FEATURE_DIR: $feature_dir"
        echo "change_file: $spec_file"
        echo "FEATURE_NUM: "
        echo "HAS_GIT: $has_git"
        if [ -n "$branch_name" ]; then
            echo "SPECIFY_FEATURE environment variable set to: $branch_name"
        fi
    fi
}

main() {
    parse_arguments "$@"
    resolve_repository_root

    local branch_name="$BRANCH_NAME_INPUT"
    local feature_dir="$FEATURE_DIR_INPUT"
    local spec_file=""

    if [ -n "$branch_name" ]; then
        ensure_git_branch "$branch_name" "$HAS_GIT"
        export SPECIFY_FEATURE="$branch_name"
    fi

    if [ -n "$feature_dir" ]; then
        feature_dir="$(resolve_feature_dir_path "$feature_dir" "$REPO_ROOT" "$CHANGES_DIR")"
    elif [ -n "$branch_name" ]; then
        feature_dir="$CHANGES_DIR/$(clean_name "$(basename "$branch_name")")"
    fi

    if [ -n "$feature_dir" ]; then
        mkdir -p "$feature_dir"
    fi

    output_results "$branch_name" "$spec_file" "$feature_dir" "$HAS_GIT"
}

main "$@"
