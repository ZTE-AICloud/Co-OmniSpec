#!/usr/bin/env bash

# Consolidated prerequisite checking script
#
# This script provides unified prerequisite checking for Spec-Driven Development workflow.
# It replaces the functionality previously spread across multiple scripts.
#
# Usage: ./check-prerequisites.sh [OPTIONS]
#
# OPTIONS:
#   --json              Output in JSON format
#   --help, -h          Show help message
#
# OUTPUTS:
#   JSON mode: {"FEATURE_DIR":"...", "AVAILABLE_DOCS":["..."]}
#   Text mode: FEATURE_DIR:... \n AVAILABLE_DOCS: \n ✓/✗ file.md
#   Paths only: REPO_DIR: ... \n BRANCH: ... \n FEATURE_DIR: ... etc.

set -e

# Parse command line arguments
JSON_MODE=false


for arg in "$@"; do
    case "$arg" in
        --json)
            JSON_MODE=true
            ;;
        --help|-h)
            cat << 'EOF'
Usage: check-prerequisites.sh [OPTIONS]

Consolidated prerequisite checking for Spec-Driven Development workflow.

OPTIONS:
  --json              Output in JSON format
  --help, -h          Show this help message

EXAMPLES:
  # Check task prerequisites (design.mdrequired)
  ./mini-implement-check.sh --json
EOF
            exit 0
            ;;
        *)
            echo "ERROR: Unknown option '$arg'. Use --help for usage information." >&2
            exit 1
            ;;
    esac
done

# Get current branch, with fallback for non-git repositories
# Args: repo_dir - the repository directory path
get_current_branch() {
    local repo_dir="$1"
    
    # First check if FEATURE_BRANCH environment variable is set
    if [[ -n "${FEATURE_BRANCH:-}" ]]; then
        echo "$FEATURE_BRANCH"
        return
    fi

    # Then check git if available
    if git rev-parse --abbrev-ref HEAD >/dev/null 2>&1; then
        git rev-parse --abbrev-ref HEAD
        return
    fi

    # For non-git repos, try to find the latest feature directory
    local changes_dir="$repo_dir/changes"

    if [[ -d "$changes_dir" ]]; then
        local latest_feature=""
        local highest=0

        for dir in "$changes_dir"/*; do
            if [[ -d "$dir" ]]; then
                local dirname=$(basename "$dir")
                if [[ "$dirname" =~ ^([0-9]{3})- ]]; then
                    local number=${BASH_REMATCH[1]}
                    number=$((10#$number))
                    if [[ "$number" -gt "$highest" ]]; then
                        highest=$number
                        latest_feature=$dirname
                    fi
                fi
            fi
        done

        if [[ -n "$latest_feature" ]]; then
            echo "$latest_feature"
            return
        fi
    fi

    echo "main"  # Final fallback
}

get_feature_paths() {
    local repo_dir=$(pwd)
    local current_branch=$(get_current_branch "$repo_dir")
    local feature_dir="$repo_dir/changes/$current_branch"

    if git rev-parse --show-toplevel >/dev/null 2>&1; then
        has_git=true
    else
        has_git=false
    fi

    cat <<EOF
REPO_DIR='$repo_dir'
CURRENT_BRANCH='$current_branch'
FEATURE_DIR='$feature_dir'
HAS_GIT='$has_git'
DESIGN_FILE='$feature_dir/design.md'
EOF
}

check_feature_branch() {
    local branch="$1"
    local has_git="$2"

    # For non-git repos, we can't enforce branch naming but still provide output
    if [[ "$has_git" != "true" ]]; then
        echo "Warning: Git repository not detected; skipped branch validation" >&2
        return 0
    fi

    if [[ ! "$branch" =~ ^[0-9]{3}- ]]; then
        echo "ERROR: Not on a feature branch. Current branch: $branch" >&2
        echo "Feature branches should be named like: 001-feature-name" >&2
        return 1
    fi

    return 0
}

# Get feature paths and validate branch
eval $(get_feature_paths)
check_feature_branch "$CURRENT_BRANCH" "$HAS_GIT" || exit 1

if [[ ! -d "$FEATURE_DIR" ]]; then
    echo "ERROR: Feature directory not found: $FEATURE_DIR" >&2
    echo "Run /mini-design first to create the feature structure." >&2
    exit 1
fi

# If paths-only mode, output paths and exit (support JSON + paths-only combined)

if $JSON_MODE; then
    # Minimal JSON paths payload (no validation performed)
    printf '{"REPO_DIR":"%s","BRANCH":"%s","FEATURE_DIR":"%s","DESIGN_FILE":"%s"}\n' \
        "$REPO_DIR" "$CURRENT_BRANCH" "$FEATURE_DIR" "$DESIGN_FILE"
else
    echo "REPO_DIR: $REPO_DIR"
    echo "BRANCH: $CURRENT_BRANCH"
    echo "FEATURE_DIR: $FEATURE_DIR"
    echo "DESIGN_FILE: $DESIGN_FILE"
fi



