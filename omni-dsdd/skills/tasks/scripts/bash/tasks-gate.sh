#!/usr/bin/env bash
# Tasks 阶段门禁脚本 - 验证任务清单和产物完整性

set -euo pipefail

# 解析命令行参数
JSON_MODE=false
STEP="all"
RECORD=false
RETRIES=0
ENABLE_E2E=false

for arg in "$@"; do
    case "$arg" in
        --json) JSON_MODE=true ;;
        --step) shift ;;
        --step=*) STEP="${arg#--step=}" ;;
        --record) RECORD=true ;;
        --retries=*) RETRIES="${arg#--retries=}" ;;
        --enable-e2e) ENABLE_E2E=true ;;
        --feature-dir) shift ;;
        --help|-h)
            echo "Usage: $0 --feature-dir <dir> [--step <step>] [--json] [--record]"
            echo "  --step    指定门禁步骤 (init|context|requirements|scenarios|quality|all)"
            echo "  --json    输出 JSON 格式"
            echo "  --record  记录门禁结果到 tasks-run.json"
            exit 0
            ;;
    esac
done

# 获取脚本目录
SCRIPT_DIR="$(CDPATH="" cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HARNESS_SCRIPT="$SCRIPT_DIR/../python/tasks_harness.py"

# 检查 harness 是否存在
if [[ ! -f "$HARNESS_SCRIPT" ]]; then
    echo "ERROR: tasks_harness.py not found at $HARNESS_SCRIPT" >&2
    exit 1
fi

# 提取 feature-dir 参数
FEATURE_DIR=""
for ((i=1; i<=$#; i++)); do
    if [[ "${!i}" == "--feature-dir" ]]; then
        ((i++))
        FEATURE_DIR="${!i}"
        break
    elif [[ "${!i}" == --feature-dir=* ]]; then
        FEATURE_DIR="${!i#--feature-dir=}"
        break
    fi
done

if [[ -z "$FEATURE_DIR" ]]; then
    echo "ERROR: --feature-dir is required" >&2
    exit 1
fi

# 调用 Python harness 执行门禁
exec python3 "$HARNESS_SCRIPT" gate \
    --feature-dir "$FEATURE_DIR" \
    --step "$STEP" \
    ${RECORD:+--record} \
    ${ENABLE_E2E:+--enable-e2e} \
    ${JSON_MODE:+--json}