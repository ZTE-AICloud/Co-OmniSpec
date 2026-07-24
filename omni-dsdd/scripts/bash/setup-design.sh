#!/usr/bin/env bash

set -e

# Parse command line arguments
JSON_MODE=false
ARGS=()

for arg in "$@"; do
    case "$arg" in
        --json) 
            JSON_MODE=true 
            ;;
        --help|-h) 
            echo "Usage: $0 [--json]"
            echo "  --json    Output results in JSON format"
            echo "  --help    Show this help message"
            exit 0 
            ;;
        *) 
            ARGS+=("$arg") 
            ;;
    esac
done

# Get script directory and load common functions
SCRIPT_DIR="$(CDPATH="" cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

# Get all paths and variables from common functions
eval $(get_feature_paths)

# Check if we're on a proper feature branch (only for git repos)
check_feature_branch "$CURRENT_BRANCH" "$HAS_GIT" || exit 1

# Ensure the feature directory and design artifact dirs exist
mkdir -p "$FEATURE_DIR" \
    "$FEATURE_DIR/contracts" \
    "$FEATURE_DIR/.runs/evaluations" \
    "$FEATURE_DIR/.runs/metrics" \
    "$FEATURE_DIR/.runs/internal"

# Copy design template if it exists (.omni-infra or omni-infra)
TEMPLATE=""
for _infra_dir in ".omni-infra" "omni-infra"; do
    _candidate="$WORKING_DIR/${_infra_dir}/templates/design-template.md"
    if [[ -f "$_candidate" ]]; then
        TEMPLATE="$_candidate"
        break
    fi
done
if [[ -n "$TEMPLATE" ]]; then
    cp "$TEMPLATE" "$IMPL_DESIGN"
    # 替换常见占位符，避免 gate 将未替换模板判为失败
    _date="$(date +%Y-%m-%d 2>/dev/null || echo '1970-01-01')"
    sed -i \
        -e "s|\[FEATURE\]|${CURRENT_BRANCH}|g" \
        -e "s|\[###-feature-name\]|${CURRENT_BRANCH}|g" \
        -e "s|\[DATE\]|${_date}|g" \
        -e "s|\[link\]|spec.md|g" \
        "$IMPL_DESIGN" 2>/dev/null || true
    echo "Copied design template to $IMPL_DESIGN"
else
    echo "Warning: Design template not found under .omni-infra/ or omni-infra/templates/"
    touch "$IMPL_DESIGN"
fi

# Output results
if $JSON_MODE; then
    printf '{"FEATURE_SPEC":"%s","IMPL_DESIGN":"%s","CHANGES_DIR":"%s","BRANCH":"%s","HAS_GIT":"%s"}\n' \
        "$FEATURE_SPEC" "$IMPL_DESIGN" "$FEATURE_DIR" "$CURRENT_BRANCH" "$HAS_GIT"
else
    echo "FEATURE_SPEC: $FEATURE_SPEC"
    echo "IMPL_DESIGN: $IMPL_DESIGN" 
    echo "CHANGES_DIR: $FEATURE_DIR"
    echo "BRANCH: $CURRENT_BRANCH"
    echo "HAS_GIT: $HAS_GIT"
fi

