#!/usr/bin/env bash
# 接口扫描批次信息获取工具 (Bash版本)
# 在AI Agent循环处理批次时，获取要处理的批次信息

set -e

# 初始化变量
REPO_ROOT=""
ACTION=""
BATCH_NUMBER=""
STATUS=""

# 显示帮助信息
show_help() {
    cat << 'EOF'
接口扫描批次信息获取工具 (Bash版本)
在AI Agent循环处理批次时，获取要处理的批次信息

使用方法:
    ./get-next-batch.sh --repo-root <repo_root> --action <action> [--batch-number <number>] [--status <status>]

参数:
    --repo-root: 仓库根目录路径
    --action: 操作类型（get-next-batch, update-batch-status, get-batch-info, get-summary）
    --batch-number: 批次编号（用于更新状态或获取信息时）
    --status: 批次状态（用于更新状态时）
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
        --action)
            ACTION="$2"
            shift 2
            ;;
        --batch-number)
            BATCH_NUMBER="$2"
            shift 2
            ;;
        --status)
            STATUS="$2"
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
if [[ -z "$REPO_ROOT" ]] || [[ -z "$ACTION" ]]; then
    echo "错误: 必须提供 --repo-root 和 --action 参数" >&2
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

CACHE_DIR="$REPO_ROOT/.cache/reverse/interfaces"

# 获取下一个待处理的批次
get_next_pending_batch() {
    local batch_mapping_file="$CACHE_DIR/batch-mapping.json"

    if [[ ! -f "$batch_mapping_file" ]]; then
        echo "错误: 批次映射文件不存在 $batch_mapping_file" >&2
        echo "{}"
        return
    fi

    # 使用jq查找第一个状态为pending的批次
    local batch_info
    batch_info=$(jq -r '[.batches[] | select(.status == "pending")] | .[0] // empty' "$batch_mapping_file" 2>/dev/null)

    # 如果没有找到pending的批次，查找状态为initialized的批次
    if [[ -z "$batch_info" ]] || [[ "$batch_info" == "null" ]]; then
        batch_info=$(jq -r '[.batches[] | select(.status == "initialized")] | .[0] // empty' "$batch_mapping_file" 2>/dev/null)
    fi

    if [[ -n "$batch_info" ]]; then
        echo "$batch_info"
    else
        echo "{}"  # 返回空对象表示没有更多批次
    fi
}

# 更新批次状态
update_batch_status() {
    local batch_number="$1"
    local status="$2"
    local updated=false

    # 更新批次映射文件
    local batch_mapping_file="$CACHE_DIR/batch-mapping.json"
    if [[ -f "$batch_mapping_file" ]]; then
        # 使用jq更新批次状态
        if jq --arg bn "$batch_number" --arg st "$status" --arg lu "$(date -u +%Y-%m-%dT%H:%M:%SZ)" '
            .batches |= map(if (.batch_number | tostring) == $bn then .status = $st | .last_updated = $lu else . end)
        ' "$batch_mapping_file" > "$batch_mapping_file.tmp" 2>/dev/null; then
            mv "$batch_mapping_file.tmp" "$batch_mapping_file"
            updated=true
        else
            rm -f "$batch_mapping_file.tmp"
        fi
    fi

    # 更新批次详细文件
    local batch_details_file="$CACHE_DIR/batch-details-$batch_number.json"
    if [[ -f "$batch_details_file" ]]; then
        if jq --arg st "$status" --arg lu "$(date -u +%Y-%m-%dT%H:%M:%SZ)" '
            .status = $st | .last_updated = $lu
        ' "$batch_details_file" > "$batch_details_file.tmp" 2>/dev/null; then
            mv "$batch_details_file.tmp" "$batch_details_file"
        else
            rm -f "$batch_details_file.tmp"
        fi
    fi

    # 更新批次状态文件
    local batch_status_file="$CACHE_DIR/interface_scanning-batch-status.json"
    if [[ -f "$batch_status_file" ]]; then
        local update_expr=""
        case "$status" in
            "completed")
                update_expr='.processed_batches += 1 | .current_batch = ($bn | tonumber)'
                ;;
            "failed")
                update_expr='.failed_batches += 1'
                ;;
        esac

        if [[ -n "$update_expr" ]]; then
            if jq --arg bn "$batch_number" --arg st "$status" --arg lu "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "
                $update_expr | .last_update = \$lu |
                .batch_mappings |= map(if (.batch_number | tostring) == \$bn then .status = \$st else . end)
            " "$batch_status_file" > "$batch_status_file.tmp" 2>/dev/null; then
                mv "$batch_status_file.tmp" "$batch_status_file"
            else
                rm -f "$batch_status_file.tmp"
            fi
        else
            # 只更新最后更新时间
            if jq --arg lu "$(date -u +%Y-%m-%dT%H:%M:%SZ)" '
                .last_update = $lu
            ' "$batch_status_file" > "$batch_status_file.tmp" 2>/dev/null; then
                mv "$batch_status_file.tmp" "$batch_status_file"
            else
                rm -f "$batch_status_file.tmp"
            fi
        fi
    fi

    # 输出结果
    echo "{\"success\": $updated, \"batch_number\": $batch_number, \"status\": \"$status\"}"
}

# 获取指定批次的详细信息
get_batch_info() {
    local batch_number="$1"
    local batch_details_file="$CACHE_DIR/batch-details-$batch_number.json"

    if [[ ! -f "$batch_details_file" ]]; then
        echo "错误: 批次详细文件不存在 $batch_details_file" >&2
        echo "{}"
        return
    fi

    cat "$batch_details_file"
}

# 获取批次处理摘要
get_batch_summary() {
    local batch_mapping_file="$CACHE_DIR/batch-mapping.json"

    local total_batches=0
    local pending_batches=0
    local completed_batches=0
    local failed_batches=0
    local processing_batches=0

    if [[ -f "$batch_mapping_file" ]]; then
        total_batches=$(jq -r '.total_batches // 0' "$batch_mapping_file" 2>/dev/null || echo "0")

        pending_batches=$(jq -r '[.batches[] | select(.status == "pending")] | length' "$batch_mapping_file" 2>/dev/null || echo "0")
        completed_batches=$(jq -r '[.batches[] | select(.status == "completed")] | length' "$batch_mapping_file" 2>/dev/null || echo "0")
        failed_batches=$(jq -r '[.batches[] | select(.status == "failed")] | length' "$batch_mapping_file" 2>/dev/null || echo "0")
        processing_batches=$(jq -r '[.batches[] | select(.status == "processing")] | length' "$batch_mapping_file" 2>/dev/null || echo "0")
    fi

    cat << EOF
{
  "total_batches": $total_batches,
  "pending_batches": $pending_batches,
  "completed_batches": $completed_batches,
  "failed_batches": $failed_batches,
  "processing_batches": $processing_batches
}
EOF
}

# 主函数
main() {
    case "$ACTION" in
        "get-next-batch")
            get_next_pending_batch
            ;;

        "update-batch-status")
            if [[ -z "$BATCH_NUMBER" ]] || [[ -z "$STATUS" ]]; then
                echo "错误: 更新批次状态需要提供 --batch-number 和 --status 参数" >&2
                exit 1
            fi
            update_batch_status "$BATCH_NUMBER" "$STATUS"
            ;;

        "get-batch-info")
            if [[ -z "$BATCH_NUMBER" ]]; then
                echo "错误: 获取批次信息需要提供 --batch-number 参数" >&2
                exit 1
            fi
            get_batch_info "$BATCH_NUMBER"
            ;;

        "get-summary")
            get_batch_summary
            ;;

        *)
            echo "错误: 未知的操作类型 $ACTION" >&2
            exit 1
            ;;
    esac
}

# 执行主函数
main