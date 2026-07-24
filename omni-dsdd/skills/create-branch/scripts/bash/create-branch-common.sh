#!/usr/bin/env bash
# create-branch 公共函数（由同目录脚本 source，勿直接执行）

create_branch_clean_name() {
    echo "$1" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g; s/-\+/-/g; s/^-//; s/-$//'
}

create_branch_resolve_feature_dir_path() {
    local input="$1"
    local working_dir="$2"
    local changes_dir="$3"

    input="$(echo "$input" | sed 's:/*$::')"

    if [ -z "$input" ]; then
        echo ""
    elif [[ "$input" = /* ]]; then
        echo "$input"
    elif [[ "$input" = changes/* ]]; then
        echo "$working_dir/$input"
    else
        echo "$changes_dir/$input"
    fi
}

create_branch_output_results() {
    local branch_name="$1"
    local spec_file="$2"
    local feature_dir="$3"
    local has_git="$4"
    local json_mode="$5"

    if [ "$json_mode" = true ]; then
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

create_branch_require_working_dir() {
    if [ -z "$WORKING_DIR" ]; then
        echo "Error: --working-dir is required" >&2
        return 1
    fi
    if [ ! -d "$WORKING_DIR" ]; then
        echo "Error: --working-dir is not a directory: $WORKING_DIR" >&2
        return 1
    fi
    WORKING_DIR="$(CDPATH="" cd "$WORKING_DIR" && pwd)"
    return 0
}

create_branch_require_has_git() {
    if [ -z "$HAS_GIT" ]; then
        echo "Error: --has-git is required (true or false)" >&2
        return 1
    fi
    case "$HAS_GIT" in
        true|false) return 0 ;;
        *)
            echo "Error: --has-git must be true or false" >&2
            return 1
            ;;
    esac
}
