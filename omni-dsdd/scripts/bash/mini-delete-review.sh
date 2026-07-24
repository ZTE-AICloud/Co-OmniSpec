#!/usr/bin/env bash

set -e

# Parse command line arguments
IS_DESIGN=false
IS_IMPLEMENT=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --design)
            IS_DESIGN=true
            shift
            ;;
        --implement)
            IS_IMPLEMENT=true
            shift
            ;;
        *)
            shift
            ;;
    esac
done

# Source common functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

# Get feature paths and validate branch
eval $(get_feature_paths)
check_feature_branch "$CURRENT_BRANCH" "$HAS_GIT" || exit 1

if [[ ! -d "$FEATURE_DIR" ]]; then
    echo "ERROR: Feature directory not found: $FEATURE_DIR" >&2
    echo "Run /specify first to create the feature structure." >&2
    exit 1
fi

if [[ -f "$FEATURE_DIR/review-result.md" ]]; then
    rm "$FEATURE_DIR/review-result.md"
fi

# Handle design review times tracking
if [[ "$IS_DESIGN" == "true" ]]; then
    DESIGN_REVIEW_FILE="$FEATURE_DIR/design-review-times.md"
    if [[ -f "$DESIGN_REVIEW_FILE" ]]; then
        # Read current value and increment by 1
        current_value=$(cat "$DESIGN_REVIEW_FILE")
        new_value=$((current_value + 1))
        echo "$new_value" > "$DESIGN_REVIEW_FILE"
    else
        # Create file with initial value 1
        echo "1" > "$DESIGN_REVIEW_FILE"
    fi
fi
if [[ "$IS_IMPLEMENT" == "true" ]]; then
    IMPLEMENT_REVIEW_FILE="$FEATURE_DIR/implement-review-times.md"
    if [[ -f "$IMPLEMENT_REVIEW_FILE" ]]; then
        # Read current value and increment by 1
        current_value=$(cat "$IMPLEMENT_REVIEW_FILE")
        new_value=$((current_value + 1))
        echo "$new_value" > "$IMPLEMENT_REVIEW_FILE"
    else
        # Create file with initial value 1
        echo "1" > "$IMPLEMENT_REVIEW_FILE"
    fi
fi