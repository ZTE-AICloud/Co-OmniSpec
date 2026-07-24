#!/usr/bin/env bash
# 批次完成状态验证工具 (Bash版本)
# 验证批次是否真正完成，包括状态文件、输出文件和时间戳验证

set -e

# 初始化变量
REPO_ROOT=""
BATCH_NUMBERS=""
STAGE_TYPE=""
OUTPUT_FILE_PATTERN=""

# 显示帮助信息
show_help() {
    cat << 'EOF'
批次完成状态验证工具 (Bash版本)
验证批次是否真正完成，包括状态文件、输出文件和时间戳验证

使用方法:
    ./verify-batches-completion.sh --repo-root <repo_root> --batch-numbers '<batch_numbers_json>' [--stage-type <stage_type>] [--output-pattern <pattern>]

参数:
    --repo-root: 仓库根目录路径
    --batch-numbers: 批次编号数组的JSON字符串，格式为 [1, 2, 3]
    --stage-type: 阶段类型（scenarios/interfaces/functions/call-chain/function-identification），用于确定缓存目录和状态文件名
    --output-pattern: 输出文件模式，如 "scenario-list-batch-{batch_number}.json"（可选，会根据stage-type自动推断）
    --help, -h: 显示此帮助信息

示例:
    ./verify-batches-completion.sh --repo-root /path/to/repo --batch-numbers '[1,2,3]' --stage-type scenarios
EOF
}

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --repo-root)
            REPO_ROOT="$2"
            shift 2
            ;;
        --batch-numbers)
            BATCH_NUMBERS="$2"
            shift 2
            ;;
        --stage-type)
            STAGE_TYPE="$2"
            shift 2
            ;;
        --output-pattern)
            OUTPUT_FILE_PATTERN="$2"
            shift 2
            ;;
        --help|-h)
            show_help
            exit 0
            ;;
        *)
            echo "未知参数: $1" >&2
            show_help
            exit 1
            ;;
    esac
done

# 验证必需参数
if [[ -z "$REPO_ROOT" ]] || [[ -z "$BATCH_NUMBERS" ]]; then
    echo "错误: 必须提供 --repo-root 和 --batch-numbers 参数" >&2
    show_help
    exit 1
fi

# 验证仓库根目录
if [[ ! -d "$REPO_ROOT" ]]; then
    echo "错误: 仓库根目录不存在 $REPO_ROOT" >&2
    exit 1
fi

# 导入通用函数
SCRIPT_DIR="$(CDPATH="" cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

# 根据阶段类型确定缓存目录和状态文件名
determine_cache_info() {
    local stage_type="$1"
    local cache_dir=""
    local status_file=""
    local output_pattern=""

    case "$stage_type" in
        "scenarios")
            cache_dir="$REPO_ROOT/.cache/reverse/scenarios"
            status_file="scenario_scanning-batch-status.json"
            output_pattern="scenario-list-batch-{batch_number}.json"
            ;;
        "interfaces")
            cache_dir="$REPO_ROOT/.cache/reverse/interfaces"
            status_file="interface_scanning-batch-status.json"
            output_pattern="interface-list-batch-{batch_number}.json"
            ;;
        "call-chain")
            cache_dir="$REPO_ROOT/.cache/reverse/functions/call-chain-analysis"
            status_file="call_chain_analysis-batch-status.json"
            output_pattern="call-chains-batch-{batch_number}.json"
            ;;
        "function-identification")
            cache_dir="$REPO_ROOT/.cache/reverse/functions/function-identification"
            status_file="function_identification-batch-status.json"
            output_pattern="functions-batch-{batch_number}.json"
            ;;
        "test-case-analysis")
            cache_dir="$REPO_ROOT/.cache/reverse/functions/test-case-analysis"
            status_file="test_case_analysis-batch-status.json"
            output_pattern="test-cases-analysis-batch-{batch_number}.json"
            ;;
        *)
            # 默认使用interfaces（向后兼容）
            cache_dir="$REPO_ROOT/.cache/reverse/interfaces"
            status_file="interface_scanning-batch-status.json"
            output_pattern="interface-list-batch-{batch_number}.json"
            ;;
    esac

    echo "$cache_dir|$status_file|$output_pattern"
}

# 验证批次是否完成
verify_batch_completion() {
    local batch_number="$1"
    local cache_dir="$2"
    local status_file="$3"
    local output_pattern="$4"
    local results=()

    # 替换输出文件模式中的 {batch_number}
    local output_file="${output_pattern//\{batch_number\}/$batch_number}"
    local output_file_path="$cache_dir/$output_file"

    # 1. 检查批次状态文件中的状态
    local batch_status_file="$cache_dir/$status_file"
    local status_in_file=""
    local last_updated=""

    if [[ -f "$batch_status_file" ]]; then
        # 从批次状态文件中查找批次状态
        status_in_file=$(jq -r --arg bn "$batch_number" '
            .batch_mappings[]? | select(.batch_number == ($bn | tonumber)) | .status // empty
        ' "$batch_status_file" 2>/dev/null || echo "")

        # 如果batch_mappings中没有，尝试从batch-mapping.json中查找
        if [[ -z "$status_in_file" ]]; then
            local batch_mapping_file="$cache_dir/batch-mapping.json"
            if [[ -f "$batch_mapping_file" ]]; then
                status_in_file=$(jq -r --arg bn "$batch_number" '
                    .batches[]? | select(.batch_number == ($bn | tonumber)) | .status // empty
                ' "$batch_mapping_file" 2>/dev/null || echo "")
                last_updated=$(jq -r --arg bn "$batch_number" '
                    .batches[]? | select(.batch_number == ($bn | tonumber)) | .last_updated // empty
                ' "$batch_mapping_file" 2>/dev/null || echo "")
            fi
        fi
    fi

    # 2. 检查输出文件是否存在
    local output_file_exists=false
    local output_file_valid=false
    if [[ -f "$output_file_path" ]]; then
        output_file_exists=true
        # 验证JSON格式
        if jq empty "$output_file_path" 2>/dev/null; then
            output_file_valid=true
        fi
    fi

    # 3. 检查批次详细文件中的状态
    local batch_details_file="$cache_dir/batch-details-$batch_number.json"
    local status_in_details=""
    if [[ -f "$batch_details_file" ]]; then
        status_in_details=$(jq -r '.status // empty' "$batch_details_file" 2>/dev/null || echo "")
        if [[ -z "$last_updated" ]]; then
            last_updated=$(jq -r '.last_updated // empty' "$batch_details_file" 2>/dev/null || echo "")
        fi
    fi

    # 4. 验证时间戳（如果存在）
    local timestamp_valid=true
    if [[ -n "$last_updated" ]]; then
        # 检查时间戳格式是否为ISO 8601
        if [[ ! "$last_updated" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z?$ ]]; then
            timestamp_valid=false
        fi
    fi

    # 5. 综合判断批次是否完成
    local is_completed=false
    local completion_reason=""

    # 状态必须为"completed"
    if [[ "$status_in_file" == "completed" ]] || [[ "$status_in_details" == "completed" ]]; then
        # 输出文件必须存在且有效
        if [[ "$output_file_exists" == true ]] && [[ "$output_file_valid" == true ]]; then
            is_completed=true
            completion_reason="状态为completed且输出文件存在且有效"
        else
            completion_reason="状态为completed但输出文件不存在或无效"
        fi
    else
        if [[ -z "$status_in_file" ]] && [[ -z "$status_in_details" ]]; then
            completion_reason="未找到批次状态信息"
        else
            completion_reason="状态为'${status_in_file:-$status_in_details}'，不是completed"
        fi
    fi

    # 构建结果JSON
    local result_json
    result_json=$(jq -n \
        --arg bn "$batch_number" \
        --arg completed "$is_completed" \
        --arg reason "$completion_reason" \
        --arg status_file "$status_in_file" \
        --arg status_details "$status_in_details" \
        --arg output_exists "$output_file_exists" \
        --arg output_valid "$output_file_valid" \
        --arg timestamp_valid "$timestamp_valid" \
        --arg output_file "$output_file_path" \
        '{
            batch_number: ($bn | tonumber),
            completed: ($completed == "true"),
            reason: $reason,
            status_in_file: $status_file,
            status_in_details: $status_details,
            output_file_exists: ($output_exists == "true"),
            output_file_valid: ($output_valid == "true"),
            timestamp_valid: ($timestamp_valid == "true"),
            output_file_path: $output_file
        }')

    echo "$result_json"
}

# 主函数
main() {
    # 确定缓存目录和状态文件
    local cache_info
    cache_info=$(determine_cache_info "$STAGE_TYPE")
    local cache_dir
    cache_dir=$(echo "$cache_info" | cut -d'|' -f1)
    local status_file
    status_file=$(echo "$cache_info" | cut -d'|' -f2)
    local default_output_pattern
    default_output_pattern=$(echo "$cache_info" | cut -d'|' -f3)

    # 使用用户指定的输出模式或默认模式
    local output_pattern="${OUTPUT_FILE_PATTERN:-$default_output_pattern}"

    # 验证批次编号JSON格式
    if ! echo "$BATCH_NUMBERS" | jq empty 2>/dev/null; then
        echo "错误: 无效的批次编号JSON格式" >&2
        exit 1
    fi

    # 检查是否为数组
    if ! echo "$BATCH_NUMBERS" | jq -e 'type == "array"' >/dev/null 2>&1; then
        echo "错误: 批次编号必须是数组格式" >&2
        exit 1
    fi

    # 初始化结果数组
    local results="[]"
    local all_completed=true
    local completed_count=0
    local total_count=0

    # 遍历所有批次编号
    local length
    length=$(echo "$BATCH_NUMBERS" | jq 'length')

    for ((i=0; i<length; i++)); do
        local batch_number
        batch_number=$(echo "$BATCH_NUMBERS" | jq -r ".[$i]")

        # 验证批次编号
        if [[ "$batch_number" == "null" ]] || [[ -z "$batch_number" ]]; then
            continue
        fi

        total_count=$((total_count + 1))

        # 验证批次完成状态
        local result
        result=$(verify_batch_completion "$batch_number" "$cache_dir" "$status_file" "$output_pattern")

        # 检查是否完成
        local is_completed
        is_completed=$(echo "$result" | jq -r '.completed')

        if [[ "$is_completed" == "true" ]]; then
            completed_count=$((completed_count + 1))
        else
            all_completed=false
        fi

        # 添加到结果数组
        results=$(echo "$results" | jq ". += [$result]")
    done

    # 输出最终结果
    local final_result
    final_result=$(jq -n \
        --argjson results "$results" \
        --arg all_completed "$all_completed" \
        --argjson completed_count "$completed_count" \
        --argjson total_count "$total_count" \
        '{
            all_completed: ($all_completed == "true"),
            completed_count: $completed_count,
            total_count: $total_count,
            batches: $results
        }')

    echo "$final_result"

    # 如果有未完成的批次，返回非零退出码
    if [[ "$all_completed" != "true" ]]; then
        exit 1
    fi
}

# 执行主函数
main

