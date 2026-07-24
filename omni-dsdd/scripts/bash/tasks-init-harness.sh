#!/usr/bin/env bash

set -e

# Initialize tasks harness for a feature
# This script sets up the environment for tasks phase execution

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

# Ensure the feature directory and tasks artifact dirs exist
mkdir -p "$FEATURE_DIR" \
    "$FEATURE_DIR/contracts" \
    "$FEATURE_DIR/.runs/evaluations" \
    "$FEATURE_DIR/.runs/metrics" \
    "$FEATURE_DIR/.runs/internal" \
    "$FEATURE_DIR/checklists"

# Copy tasks template if it exists (.omni-infra or omni-infra)
TEMPLATE=""
for _infra_dir in ".omni-infra" "omni-infra"; do
    _candidate="$WORKING_DIR/${_infra_dir}/templates/tasks-template.md"
    if [[ -f "$_candidate" ]]; then
        TEMPLATE="$_candidate"
        break
    fi
done
if [[ -n "$TEMPLATE" ]]; then
    _tasks_file="$FEATURE_DIR/tasks.md"
    cp "$TEMPLATE" "$_tasks_file"
    # 替换常见占位符
    _date="$(date +%Y-%m-%d 2>/dev/null || echo '1970-01-01')"
    sed -i \
        -e "s|\[FEATURE\]|${CURRENT_BRANCH}|g" \
        -e "s|\[###-feature-name\]|${CURRENT_BRANCH}|g" \
        -e "s|\[DATE\]|${_date}|g" \
        -e "s|\[link\]|spec.md|g" \
        "$_tasks_file" 2>/dev/null || true
    echo "Copied tasks template to $_tasks_file"
else
    echo "Warning: Tasks template not found under .omni-infra/ or omni-infra/templates/"
    # Create empty tasks.md placeholder
    touch "$FEATURE_DIR/tasks.md"
fi

# Create initial state file for tasks phase
STATE_FILE="$FEATURE_DIR/.runs/tasks-run.json"
cat > "$STATE_FILE" << EOF
{
  "phase": "tasks",
  "status": "initialized",
  "branch": "${CURRENT_BRANCH}",
  "feature_dir": "${FEATURE_DIR}",
  "tasks_file": "${FEATURE_DIR}/tasks.md",
  "spec_file": "${FEATURE_DIR}/spec.md",
  "design_file": "${FEATURE_DIR}/design.md",
  "completed_stages": [],
  "current_stage": null,
  "created_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || echo '1970-01-01T00:00:00Z')"
}
EOF

# Output results
if $JSON_MODE; then
    printf '{"TASKS_FILE":"%s","STATE_FILE":"%s","CHANGES_DIR":"%s","BRANCH":"%s","HAS_GIT":"%s"}\n' \
        "$FEATURE_DIR/tasks.md" "$STATE_FILE" "$FEATURE_DIR" "$CURRENT_BRANCH" "$HAS_GIT"
else
    echo "TASKS_FILE: $FEATURE_DIR/tasks.md"
    echo "STATE_FILE: $STATE_FILE"
    echo "CHANGES_DIR: $FEATURE_DIR"
    echo "BRANCH: $CURRENT_BRANCH"
    echo "HAS_GIT: $HAS_GIT"
fi