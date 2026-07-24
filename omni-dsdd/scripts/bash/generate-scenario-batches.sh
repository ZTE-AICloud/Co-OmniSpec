#!/usr/bin/env bash
# 场景扫描批次生成工具 (Bash版本)
# 基于AI Agent的各种规则过滤后，把要检索的文件基于文件数量进行分批，生成批次文件

set -e

# 初始化变量
REPO_ROOT=""
FILE_LIST=""
BATCH_SIZE=20
MAX_TOKENS=150000
FORCE_REGENERATE=false

# 显示帮助信息
show_help() {
    cat << 'EOF'
场景扫描批次生成工具 (Bash版本)
基于AI Agent的各种规则过滤后，把要检索的文件基于文件数量进行分批，生成批次文件

使用方法:
    ./generate-scenario-batches.sh --repo-root <repo_root> --file-list <file_list_json> [--batch-size <size>] [--max-tokens <tokens>] [--force]

参数:
    --repo-root: 仓库根目录路径
    --file-list: 要处理的文件列表（JSON格式）
    --batch-size: 每批文件数量（可选，默认20）
    --max-tokens: 每批最大Token数（可选，默认150000）
    --force: 强制重新生成批次（可选，默认false）
    --help, -h: 显示此帮助信息
EOF
}

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --repo-root)
            REPO_ROOT="$2"
            shift 2
            ;;
        --file-list)
            FILE_LIST="$2"
            shift 2
            ;;
        --batch-size)
            BATCH_SIZE="$2"
            shift 2
            ;;
        --max-tokens)
            MAX_TOKENS="$2"
            shift 2
            ;;
        --force)
            FORCE_REGENERATE=true
            shift
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
if [[ -z "$REPO_ROOT" ]] || [[ -z "$FILE_LIST" ]]; then
    echo "错误: 必须提供 --repo-root 和 --file-list 参数" >&2
    show_help
    exit 1
fi

# 验证仓库根目录
if [[ ! -d "$REPO_ROOT" ]]; then
    echo "错误: 仓库根目录不存在 $REPO_ROOT" >&2
    exit 1
fi

# 验证文件列表文件
if [[ ! -f "$FILE_LIST" ]]; then
    echo "错误: 文件列表文件不存在 $FILE_LIST" >&2
    exit 1
fi

# 导入通用函数
SCRIPT_DIR="$(CDPATH="" cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "$SCRIPT_DIR/common.sh" ]]; then
    source "$SCRIPT_DIR/common.sh"
fi

# 创建缓存目录
CACHE_DIR="$REPO_ROOT/.cache/reverse/scenarios"
mkdir -p "$CACHE_DIR"

# 估算文件的Token数量
estimate_tokens_for_file() {
    local file_path="$1"

    # 检查文件是否存在
    if [[ ! -f "$file_path" ]]; then
        echo "1000"  # 保守估计
        return
    fi

    # 计算行数并估算tokens（每行约5个tokens）
    local line_count
    line_count=$(wc -l < "$file_path" 2>/dev/null || echo "0")
    echo $((line_count * 5))
}

# 从JSON文件中提取文件列表
extract_file_list() {
    local file_list_path="$1"

    # 尝试多种格式
    local files
    files=$(jq -r '.files[]?' "$file_list_path" 2>/dev/null) || \
    files=$(jq -r '.[]?' "$file_list_path" 2>/dev/null)

    if [[ -z "$files" ]]; then
        echo "错误: 无法从 $file_list_path 中提取文件列表" >&2
        return 1
    fi

    echo "$files"
}

# 检查是否已有有效的批次文件
check_existing_batches() {
    local batch_mapping_file="$CACHE_DIR/batch-mapping.json"
    local batch_status_file="$CACHE_DIR/scenario_scanning-batch-status.json"

    # 检查批次映射文件是否存在
    if [[ ! -f "$batch_mapping_file" ]]; then
        echo "批次映射文件不存在，需要重新生成"
        return 1
    fi

    # 检查批次状态文件是否存在
    if [[ ! -f "$batch_status_file" ]]; then
        echo "批次状态文件不存在，需要重新生成"
        return 1
    fi

    # 检查批次映射文件是否有效
    local total_batches
    total_batches=$(jq -r '.total_batches // 0' "$batch_mapping_file" 2>/dev/null || echo "0")
    if [[ $total_batches -eq 0 ]]; then
        echo "批次映射文件无效，需要重新生成"
        return 1
    fi

    # 检查是否有任何已完成的批次
    local completed_batches
    completed_batches=$(jq -r '[.batches[] | select(.status == "completed")] | length' "$batch_mapping_file" 2>/dev/null || echo "0")

    if [[ $completed_batches -gt 0 ]]; then
        echo "检测到已有 $completed_batches 个已完成的批次，支持断点续执行"
        return 0
    fi

    # 检查是否有正在进行的批次
    local processing_batches
    processing_batches=$(jq -r '[.batches[] | select(.status == "processing")] | length' "$batch_mapping_file" 2>/dev/null || echo "0")

    if [[ $processing_batches -gt 0 ]]; then
        echo "检测到已有 $processing_batches 个正在进行的批次，支持断点续执行"
        return 0
    fi

    # 检查是否有待处理的批次
    local pending_batches
    pending_batches=$(jq -r '[.batches[] | select(.status == "pending")] | length' "$batch_mapping_file" 2>/dev/null || echo "0")

    if [[ $pending_batches -gt 0 ]]; then
        echo "检测到已有 $pending_batches 个待处理的批次，支持断点续执行"
        return 0
    fi

    echo "未检测到有效的批次状态，需要重新生成"
    return 1
}

# 主函数
main() {
    echo "开始生成场景扫描批次..."

    # 检查是否需要强制重新生成
    if [[ "$FORCE_REGENERATE" == false ]]; then
        echo "检查现有批次文件..."
        if check_existing_batches; then
            echo "已有有效的批次文件，无需重新生成"
            echo "如需强制重新生成，请使用 --force 参数"
            exit 0
        fi
    else
        echo "强制重新生成批次文件..."
    fi

    # 提取文件列表
    local files
    files=$(extract_file_list "$FILE_LIST")
    local file_count
    file_count=$(echo "$files" | wc -l)
    echo "找到 $file_count 个文件需要处理"

    if [[ $file_count -eq 0 ]]; then
        echo "警告: 文件列表为空" >&2
        exit 0
    fi

    # 创建批次
    local batch_number=1
    local current_batch_files=()
    local current_tokens=0
    local batch_mappings=()
    local total_batches=0

    # 处理每个文件
    while IFS= read -r file_path; do
        # 估算文件Token数量
        local file_tokens
        file_tokens=$(estimate_tokens_for_file "$file_path")

        # 检查是否需要创建新批次
        if [[ ${#current_batch_files[@]} -ge $BATCH_SIZE ]] || \
           [[ $((current_tokens + file_tokens)) -gt $MAX_TOKENS ]] && \
           [[ ${#current_batch_files[@]} -gt 0 ]]; then

            # 创建当前批次
            local batch_file_name="batch-details-$batch_number.json"
            local batch_file_path="$CACHE_DIR/$batch_file_name"

            # 创建批次JSON
            {
                echo "{"
                echo "  \"batch_number\": $batch_number,"
                echo "  \"files\": ["

                local first_file=true
                for batch_file in "${current_batch_files[@]}"; do
                    if [[ "$first_file" = true ]]; then
                        echo "    \"$batch_file\""
                        first_file=false
                    else
                        echo "    ,\"$batch_file\""
                    fi
                done

                echo "  ],"
                echo "  \"estimated_tokens\": $current_tokens,"
                echo "  \"complexity_score\": $((current_tokens / 1000)),"
                echo "  \"status\": \"pending\""
                echo "}"
            } > "$batch_file_path"

            # 添加到映射列表
            batch_mappings+=("{\"batch_number\": $batch_number, \"batch_file\": \"$batch_file_name\", \"status\": \"pending\", \"estimated_tokens\": $current_tokens}")

            echo "已创建批次文件: $batch_file_path"

            # 重置批次
            current_batch_files=()
            current_tokens=0
            ((batch_number++))
        fi

        # 添加文件到当前批次
        current_batch_files+=("$file_path")
        current_tokens=$((current_tokens + file_tokens))

    done <<< "$files"

    # 处理最后一个批次
    if [[ ${#current_batch_files[@]} -gt 0 ]]; then
        local batch_file_name="batch-details-$batch_number.json"
        local batch_file_path="$CACHE_DIR/$batch_file_name"

        # 创建批次JSON
        {
            echo "{"
            echo "  \"batch_number\": $batch_number,"
            echo "  \"files\": ["

            local first_file=true
            for batch_file in "${current_batch_files[@]}"; do
                if [[ "$first_file" = true ]]; then
                    echo "    \"$batch_file\""
                    first_file=false
                else
                    echo "    ,\"$batch_file\""
                fi
            done

            echo "  ],"
            echo "  \"estimated_tokens\": $current_tokens,"
            echo "  \"complexity_score\": $((current_tokens / 1000)),"
            echo "  \"status\": \"pending\""
            echo "}"
        } > "$batch_file_path"

        # 添加到映射列表
        batch_mappings+=("{\"batch_number\": $batch_number, \"batch_file\": \"$batch_file_name\", \"status\": \"pending\", \"estimated_tokens\": $current_tokens}")

        echo "已创建批次文件: $batch_file_path"
        ((batch_number++))
    fi

    total_batches=$((batch_number - 1))
    echo "创建了 $total_batches 个批次"

    # 创建批次映射文件
    local batch_mapping_file="$CACHE_DIR/batch-mapping.json"
    {
        echo "{"
        echo "  \"total_batches\": $total_batches,"
        echo "  \"batch_size\": $BATCH_SIZE,"
        echo "  \"batches\": ["

        local first_batch=true
        for batch_mapping in "${batch_mappings[@]}"; do
            if [[ "$first_batch" = true ]]; then
                echo "    $batch_mapping"
                first_batch=false
            else
                echo "    ,$batch_mapping"
            fi
        done

        echo "  ]"
        echo "}"
    } > "$batch_mapping_file"

    echo "已创建批次映射文件: $batch_mapping_file"

    # 初始化批次状态文件
    local batch_status_file="$CACHE_DIR/scenario_scanning-batch-status.json"
    {
        echo "{"
        echo "  \"version\": \"1.1\","
        echo "  \"stage\": \"scenario_scanning\","
        echo "  \"total_items\": $file_count,"
        echo "  \"batch_size\": $BATCH_SIZE,"
        echo "  \"total_batches\": $total_batches,"
        echo "  \"processed_batches\": 0,"
        echo "  \"current_batch\": 0,"
        echo "  \"failed_batches\": 0,"
        echo "  \"start_time\": \"\","
        echo "  \"last_update\": \"\","
        echo "  \"status\": \"initialized\","
        echo "  \"batch_mappings\": ["

        local first_batch=true
        for batch_mapping in "${batch_mappings[@]}"; do
            # 移除外部的大括号和引号，以便正确嵌入
            local clean_mapping=$(echo "$batch_mapping" | sed 's/^"\(.*\)"$/\1/' | sed 's/\\\"/"/g')
            if [[ "$first_batch" = true ]]; then
                echo "    $clean_mapping"
                first_batch=false
            else
                echo "    ,$clean_mapping"
            fi
        done

        echo "  ]"
        echo "}"
    } > "$batch_status_file"

    echo "已初始化批次状态文件: $batch_status_file"
    echo "批次生成完成，总共创建了 $total_batches 个批次"
}

# 执行主函数
main

