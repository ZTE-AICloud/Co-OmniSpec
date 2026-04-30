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
#   Paths only: REPO_ROOT: ... \n BRANCH: ... \n FEATURE_DIR: ... etc.

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
  ./mini-check.sh --json
 
  
EOF
            exit 0
            ;;
        *)
            echo "ERROR: Unknown option '$arg'. Use --help for usage information." >&2
            exit 1
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

if [[ ! -f "$IMPL_DESIGN" ]]; then
    echo "ERROR: design.md not found in $FEATURE_DIR" >&2
    echo "Run /design first to create the implementation plan." >&2
    exit 1
fi

# If paths-only mode, output paths and exit (support JSON + paths-only combined)

if $JSON_MODE; then
    # Minimal JSON paths payload (no validation performed)
    printf '{"REPO_ROOT":"%s","BRANCH":"%s","FEATURE_DIR":"%s","DESIGN":"%s"}\n' \
        "$REPO_ROOT" "$CURRENT_BRANCH" "$FEATURE_DIR" "$IMPL_DESIGN" 
else
    echo "REPO_ROOT: $REPO_ROOT"
    echo "BRANCH: $CURRENT_BRANCH"
    echo "FEATURE_DIR: $FEATURE_DIR"    
    echo "DESIGN: $IMPL_DESIGN"    
fi



