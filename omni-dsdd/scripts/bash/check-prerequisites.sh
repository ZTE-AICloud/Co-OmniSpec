#!/usr/bin/env bash

# Consolidated prerequisite checking script
#
# Usage: check-prerequisites.sh [OPTIONS]
#
# OPTIONS:
#   --working-dir <path>   Workspace root (CLAUDE_WORKING_DIR); default env or pwd
#   --plugin-root <path>   Plugin root (CLAUDE_PLUGIN_ROOT); default env or script tree
#   --json                 Output in JSON format
#   --require-tasks        Require tasks.md to exist (for implementation phase)
#   --include-tasks        Include tasks.md in AVAILABLE_DOCS list
#   --paths-only           Only output path variables (no validation)
#   --help, -h             Show help message

set -e

JSON_MODE=false
REQUIRE_TASKS=false
INCLUDE_TASKS=false
PATHS_ONLY=false
WORKING_DIR_ARG=""
PLUGIN_ROOT_ARG=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --json)
            JSON_MODE=true
            shift
            ;;
        --require-tasks)
            REQUIRE_TASKS=true
            shift
            ;;
        --include-tasks)
            INCLUDE_TASKS=true
            shift
            ;;
        --paths-only)
            PATHS_ONLY=true
            shift
            ;;
        --working-dir)
            [[ $# -gt 1 ]] || { echo "ERROR: --working-dir requires a value" >&2; exit 1; }
            WORKING_DIR_ARG="$2"
            shift 2
            ;;
        --plugin-root)
            [[ $# -gt 1 ]] || { echo "ERROR: --plugin-root requires a value" >&2; exit 1; }
            PLUGIN_ROOT_ARG="$2"
            shift 2
            ;;
        --help|-h)
            cat << 'EOF'
Usage: check-prerequisites.sh [OPTIONS]

OPTIONS:
  --working-dir <path>  Workspace root (CLAUDE_WORKING_DIR)
  --plugin-root <path>  Plugin install root (CLAUDE_PLUGIN_ROOT)
  --json                Output in JSON format
  --require-tasks       Require tasks.md (implement phase)
  --include-tasks       Include tasks.md in AVAILABLE_DOCS
  --paths-only          Paths only, no validation
  --help, -h            This message

EXAMPLES:
  check-prerequisites.sh --json --working-dir "$CLAUDE_WORKING_DIR"
  check-prerequisites.sh --paths-only --plugin-root "$CLAUDE_PLUGIN_ROOT" --working-dir "$CLAUDE_WORKING_DIR"
EOF
            exit 0
            ;;
        *)
            echo "ERROR: Unknown option '$1'. Use --help for usage information." >&2
            exit 1
            ;;
    esac
done

SCRIPT_DIR="$(CDPATH="" cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

if [[ -n "$WORKING_DIR_ARG" ]]; then
    export CLAUDE_WORKING_DIR="$(CDPATH="" cd "$WORKING_DIR_ARG" && pwd)"
fi
if [[ -n "$PLUGIN_ROOT_ARG" ]]; then
    export CLAUDE_PLUGIN_ROOT="$(CDPATH="" cd "$PLUGIN_ROOT_ARG" && pwd)"
fi

eval "$(get_feature_paths)"

if $PATHS_ONLY; then
    if $JSON_MODE; then
        printf '{"PLUGIN_ROOT":"%s","WORKING_DIR":"%s","REPO_ROOT":"%s","BRANCH":"%s","FEATURE_DIR":"%s","FEATURE_SPEC":"%s","IMPL_DESIGN":"%s","TASKS":"%s","DOC_DIR":"%s","DOC_SPECS_DIR":"%s","DOC_RULES_DIR":"%s","DOC_NAVIGATIONS_DIR":"%s","DOC_ON_DEMAND_DIR":"%s"}\n' \
            "$PLUGIN_ROOT" "$WORKING_DIR" "$REPO_ROOT" "$CURRENT_BRANCH" "$FEATURE_DIR" "$FEATURE_SPEC" "$IMPL_DESIGN" "$TASKS" "$DOC_DIR" "$DOC_SPECS_DIR" "$DOC_RULES_DIR" "$DOC_NAVIGATIONS_DIR" "$DOC_ON_DEMAND_DIR"
    else
        echo "PLUGIN_ROOT: $PLUGIN_ROOT"
        echo "WORKING_DIR: $WORKING_DIR"
        echo "REPO_ROOT: $REPO_ROOT"
        echo "BRANCH: $CURRENT_BRANCH"
        echo "FEATURE_DIR: $FEATURE_DIR"
        echo "FEATURE_SPEC: $FEATURE_SPEC"
        echo "IMPL_DESIGN: $IMPL_DESIGN"
        echo "TASKS: $TASKS"
        echo "DOC_DIR: $DOC_DIR"
        echo "DOC_SPECS_DIR: $DOC_SPECS_DIR"
        echo "DOC_RULES_DIR: $DOC_RULES_DIR"
        echo "DOC_NAVIGATIONS_DIR: $DOC_NAVIGATIONS_DIR"
    fi
    exit 0
fi

PRESET_MODE="false"
if is_feature_context_preset; then
    PRESET_MODE="true"
fi

BRANCH_FOR_CHECK="${BRANCH_NAME:-$CURRENT_BRANCH}"
check_feature_branch "$BRANCH_FOR_CHECK" "$HAS_GIT" "$PRESET_MODE" || exit 1

if [[ ! -d "$FEATURE_DIR" ]]; then
    if [[ "$PRESET_MODE" == "true" ]]; then
        echo "ERROR: Feature directory not found: $FEATURE_DIR" >&2
        echo "Preset FEATURE_DIR is set but directory missing. Run /specify to create it." >&2
    else
        echo "ERROR: Feature directory not found: $FEATURE_DIR" >&2
        echo "Run /specify first to create the feature structure." >&2
    fi
    exit 1
fi

if [[ ! -f "$IMPL_DESIGN" ]]; then
    echo "ERROR: design.md not found in $FEATURE_DIR" >&2
    echo "Run /design first to create the implementation design." >&2
    exit 1
fi

if $REQUIRE_TASKS && [[ ! -f "$TASKS" ]]; then
    echo "ERROR: tasks.md not found in $FEATURE_DIR" >&2
    echo "Run /tasks first to create the task list." >&2
    exit 1
fi

docs=()

[[ -f "$RESEARCH" ]] && docs+=("research.md")
[[ -f "$DATA_MODEL" ]] && docs+=("data-model.md")

if [[ -d "$CONTRACTS_DIR" ]] && [[ -n "$(ls -A "$CONTRACTS_DIR" 2>/dev/null)" ]]; then
    docs+=("contracts/")
fi

[[ -f "$QUICKSTART" ]] && docs+=("quickstart.md")

if $INCLUDE_TASKS && [[ -f "$TASKS" ]]; then
    docs+=("tasks.md")
fi

if $JSON_MODE; then
    if [[ ${#docs[@]} -eq 0 ]]; then
        json_docs="[]"
    else
        json_docs=$(printf '"%s",' "${docs[@]}")
        json_docs="[${json_docs%,}]"
    fi

    printf '{"FEATURE_DIR":"%s","WORKING_DIR":"%s","FEATURE_SPEC":"%s","IMPL_DESIGN":"%s","TASKS":"%s","AVAILABLE_DOCS":%s,"DOC_DIR":"%s","DOC_SPECS_DIR":"%s","DOC_RULES_DIR":"%s","DOC_NAVIGATIONS_DIR":"%s","DOC_ON_DEMAND_DIR":"%s"}\n' \
        "$FEATURE_DIR" "$WORKING_DIR" "$FEATURE_SPEC" "$IMPL_DESIGN" "$TASKS" "$json_docs" "$DOC_DIR" "$DOC_SPECS_DIR" "$DOC_RULES_DIR" "$DOC_NAVIGATIONS_DIR" "$DOC_ON_DEMAND_DIR"
else
    echo "FEATURE_DIR:$FEATURE_DIR"
    echo "WORKING_DIR:$WORKING_DIR"
    echo "AVAILABLE_DOCS:"

    check_file "$RESEARCH" "research.md"
    check_file "$DATA_MODEL" "data-model.md"
    check_dir "$CONTRACTS_DIR" "contracts/"
    check_file "$QUICKSTART" "quickstart.md"

    if $INCLUDE_TASKS; then
        check_file "$TASKS" "tasks.md"
    fi
fi
