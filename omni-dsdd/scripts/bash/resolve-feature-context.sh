#!/usr/bin/env bash
# Resolve FEATURE_DIR / BRANCH_NAME from CLI + shell env (CLI > export > derive).
# Usage:
#   resolve-feature-context.sh --working-dir <path> [--feature-dir ...] [--branch-name ...] [--json|--export]
set -euo pipefail

SCRIPT_DIR="$(CDPATH="" cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

WORKING_DIR_ARG=""
CLI_FEATURE_DIR=""
CLI_BRANCH_NAME=""
CLI_KNOWLEDGE_DIR=""
OUTPUT_MODE="json"

usage() {
    cat <<'EOF'
Usage: resolve-feature-context.sh --working-dir <path> [OPTIONS]

Options:
  --working-dir <path>   Workspace root (required)
  --feature-dir <dir>    CLI override (priority over export)
  --branch-name <name>   CLI override (priority over export)
  --knowledge-dir <dir>  私域知识库根目录 CLI override（优先级高于 KNOWLEDGE_DIR export）
  --json                 Print JSON result (default)
  --export               Print export statements for eval
  --help, -h             Show help

Priority per variable:
  FEATURE_DIR/BRANCH_NAME: CLI > OMNISPEC_FEATURE_DIR/FEATURE_DIR > BRANCH_NAME env > derive > allocate (preset=false)
  KNOWLEDGE_DIR: CLI(--knowledge-dir) > KNOWLEDGE_DIR env > default omni-doc
Final activation: specify step (pass --knowledge-dir to specify_harness init).
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --working-dir)
            [[ $# -gt 1 ]] || { echo "ERROR: --working-dir requires a value" >&2; exit 1; }
            WORKING_DIR_ARG="$2"
            shift 2
            ;;
        --feature-dir)
            [[ $# -gt 1 ]] || { echo "ERROR: --feature-dir requires a value" >&2; exit 1; }
            CLI_FEATURE_DIR="$2"
            shift 2
            ;;
        --branch-name)
            [[ $# -gt 1 ]] || { echo "ERROR: --branch-name requires a value" >&2; exit 1; }
            CLI_BRANCH_NAME="$2"
            shift 2
            ;;
        --knowledge-dir)
            [[ $# -gt 1 ]] || { echo "ERROR: --knowledge-dir requires a value" >&2; exit 1; }
            CLI_KNOWLEDGE_DIR="$2"
            shift 2
            ;;
        --json) OUTPUT_MODE="json"; shift ;;
        --export) OUTPUT_MODE="export"; shift ;;
        --help|-h) usage; exit 0 ;;
        *)
            echo "ERROR: Unknown option '$1'" >&2
            usage >&2
            exit 1
            ;;
    esac
done

[[ -n "$WORKING_DIR_ARG" ]] || { echo "ERROR: --working-dir is required" >&2; exit 1; }
WORKING_DIR="$(CDPATH="" cd "$WORKING_DIR_ARG" && pwd)"

# Resolve KNOWLEDGE_DIR (CLI > env > default omni-doc); relative path resolved against WORKING_DIR.
# 仅会话级解析（供 --export eval），不落盘；物理落盘由 specify 阶段 specify_harness init 完成。
# 兜底：非交互 bash 不自动 source ~/.bashrc，主动从 ~/.bashrc 提取（env 已有值则不覆盖）
load_knowledge_dir_from_bashrc
KNOWLEDGE_DIR_RAW=""
if [[ -n "$CLI_KNOWLEDGE_DIR" ]]; then
    KNOWLEDGE_DIR_RAW="$CLI_KNOWLEDGE_DIR"
elif [[ -n "${KNOWLEDGE_DIR:-}" ]]; then
    KNOWLEDGE_DIR_RAW="$KNOWLEDGE_DIR"
else
    KNOWLEDGE_DIR_RAW="omni-doc"
fi
if [[ "$KNOWLEDGE_DIR_RAW" = /* ]]; then
    KNOWLEDGE_DIR="$KNOWLEDGE_DIR_RAW"
else
    KNOWLEDGE_DIR="${WORKING_DIR}/${KNOWLEDGE_DIR_RAW}"
fi

# Collect raw values (CLI > env)
FEATURE_DIR_RAW=""
BRANCH_NAME_RAW=""
FEATURE_DIR_SOURCE=""
BRANCH_NAME_SOURCE=""

if [[ -n "$CLI_FEATURE_DIR" ]]; then
    FEATURE_DIR_RAW="$CLI_FEATURE_DIR"
    FEATURE_DIR_SOURCE="cli"
elif [[ -n "${OMNISPEC_FEATURE_DIR:-}" ]]; then
    FEATURE_DIR_RAW="$OMNISPEC_FEATURE_DIR"
    FEATURE_DIR_SOURCE="env"
elif [[ -n "${FEATURE_DIR:-}" ]]; then
    FEATURE_DIR_RAW="$FEATURE_DIR"
    FEATURE_DIR_SOURCE="env"
fi

if [[ -n "$CLI_BRANCH_NAME" ]]; then
    BRANCH_NAME_RAW="$CLI_BRANCH_NAME"
    BRANCH_NAME_SOURCE="cli"
elif [[ -n "${BRANCH_NAME:-}" ]]; then
    BRANCH_NAME_RAW="$BRANCH_NAME"
    BRANCH_NAME_SOURCE="env"
fi

FEATURE_DIR=""
BRANCH_NAME=""
FEATURE_CONTEXT_PRESET="false"

if [[ -n "$FEATURE_DIR_RAW" && -n "$BRANCH_NAME_RAW" ]]; then
    FEATURE_DIR="$(normalize_feature_dir_path "$FEATURE_DIR_RAW" "$WORKING_DIR")"
    BRANCH_NAME="$BRANCH_NAME_RAW"
elif [[ -n "$FEATURE_DIR_RAW" ]]; then
    FEATURE_DIR="$(normalize_feature_dir_path "$FEATURE_DIR_RAW" "$WORKING_DIR")"
    BRANCH_NAME="$(basename "$FEATURE_DIR")"
    BRANCH_NAME_SOURCE="derived"
elif [[ -n "$BRANCH_NAME_RAW" ]]; then
    BRANCH_NAME="$BRANCH_NAME_RAW"
    FEATURE_DIR="$(normalize_feature_dir_path "changes/${BRANCH_NAME}" "$WORKING_DIR")"
    FEATURE_DIR_SOURCE="derived"
fi

if [[ -n "$FEATURE_DIR" && -n "$BRANCH_NAME" ]]; then
    # Preset (CLI/env/derive): only require path under changes/; use values as-is
    if ! feature_dir_under_changes "$FEATURE_DIR" "$WORKING_DIR"; then
        echo "ERROR: FEATURE_DIR must be under ${WORKING_DIR}/changes/: $FEATURE_DIR" >&2
        exit 1
    fi
    FEATURE_CONTEXT_PRESET="true"
fi

SPEC_FILE=""
if [[ -n "$FEATURE_DIR" ]]; then
    SPEC_FILE="${FEATURE_DIR}/spec.md"
fi

SOURCE="${FEATURE_DIR_SOURCE}"
if [[ "$BRANCH_NAME_SOURCE" != "$FEATURE_DIR_SOURCE" && -n "$BRANCH_NAME_SOURCE" ]]; then
    SOURCE="${FEATURE_DIR_SOURCE}|${BRANCH_NAME_SOURCE}"
fi

emit_exports() {
    cat <<EOF
export FEATURE_DIR="${FEATURE_DIR}"
export OMNISPEC_FEATURE_DIR="${FEATURE_DIR}"
export BRANCH_NAME="${BRANCH_NAME}"
export SPEC_FILE="${SPEC_FILE}"
export FEATURE_CONTEXT_PRESET="${FEATURE_CONTEXT_PRESET}"
export KNOWLEDGE_DIR="${KNOWLEDGE_DIR}"
EOF
}

case "$OUTPUT_MODE" in
    export)
        emit_exports
        ;;
    json|*)
        printf '{"feature_context_preset":%s,"feature_dir":"%s","branch_name":"%s","spec_file":"%s","feature_dir_source":"%s","branch_name_source":"%s","source":"%s","working_dir":"%s","knowledge_dir":"%s"}\n' \
            "$( [[ "$FEATURE_CONTEXT_PRESET" == "true" ]] && echo true || echo false )" \
            "$FEATURE_DIR" \
            "$BRANCH_NAME" \
            "$SPEC_FILE" \
            "$FEATURE_DIR_SOURCE" \
            "$BRANCH_NAME_SOURCE" \
            "$SOURCE" \
            "$WORKING_DIR" \
            "$KNOWLEDGE_DIR"
        ;;
esac

echo "[resolve-feature-context] FEATURE_CONTEXT_PRESET=${FEATURE_CONTEXT_PRESET} FEATURE_DIR=${FEATURE_DIR:-} BRANCH_NAME=${BRANCH_NAME:-} KNOWLEDGE_DIR=${KNOWLEDGE_DIR:-} source=${SOURCE:-none}" >&2
