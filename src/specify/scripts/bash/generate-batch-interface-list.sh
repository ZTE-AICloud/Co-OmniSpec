#!/usr/bin/env bash
set -e
set -u
set -o pipefail

# 生成批次接口清单工具
# 从临时文件中读取接口数据，合并生成批次接口清单文件
#
# 用法:
#   generate-batch-interface-list.sh --repo-root <仓库根目录> --batch-number <批次编号>
#
# 参数:
#   --repo-root: 仓库根目录路径
#   --batch-number: 批次编号

log_error() {
    echo "[ERROR] $*" >&2
}

log_info() {
    echo "[INFO] $*"
}

# 解析参数
REPO_ROOT=""
BATCH_NUMBER=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --repo-root)
            REPO_ROOT="$2"
            shift 2
            ;;
        --batch-number)
            BATCH_NUMBER="$2"
            shift 2
            ;;
        --help|-h)
            echo "用法: $0 --repo-root <仓库根目录> --batch-number <批次编号>"
            exit 0
            ;;
        *)
            log_error "未知参数: $1"
            exit 1
            ;;
    esac
done

# 验证必需参数
if [[ -z "$REPO_ROOT" ]]; then
    log_error "缺少必需参数: --repo-root"
    exit 1
fi

if [[ -z "$BATCH_NUMBER" ]]; then
    log_error "缺少必需参数: --batch-number"
    exit 1
fi

# 验证仓库根目录
if [[ ! -d "$REPO_ROOT" ]]; then
    log_error "仓库根目录不存在: $REPO_ROOT"
    exit 1
fi

# 验证批次编号
if [[ ! "$BATCH_NUMBER" =~ ^[1-9][0-9]*$ ]]; then
    log_error "批次编号必须为正整数: $BATCH_NUMBER"
    exit 1
fi

# 设置路径
CACHE_DIR="$REPO_ROOT/.cache/omni-reverse/interfaces"
TEMP_DIR="$CACHE_DIR/temp"
BATCH_DETAILS_FILE="$CACHE_DIR/batch-details-${BATCH_NUMBER}.json"
OUTPUT_FILE="$CACHE_DIR/interface-list-batch-${BATCH_NUMBER}.json"

# 验证批次详情文件是否存在
if [[ ! -f "$BATCH_DETAILS_FILE" ]]; then
    log_error "批次详情文件不存在: $BATCH_DETAILS_FILE"
    exit 1
fi

# 检查是否有jq或python3
if ! command -v jq >/dev/null 2>&1 && ! command -v python3 >/dev/null 2>&1; then
    log_error "需要 jq 或 python3 来解析JSON文件"
    exit 1
fi

# 获取总批次数（优先从batch-details，否则从batch-mapping）
get_total_batches() {
    local total_batches=0
    
    # 先从batch-details获取
    if command -v jq >/dev/null 2>&1; then
        total_batches=$(jq -r '.total_batches // 0' "$BATCH_DETAILS_FILE" 2>/dev/null || echo "0")
    elif command -v python3 >/dev/null 2>&1; then
        total_batches=$(python3 -c "
import json
import sys
try:
    with open('$BATCH_DETAILS_FILE', 'r', encoding='utf-8') as f:
        data = json.load(f)
    print(data.get('total_batches', 0))
except:
    print(0)
" 2>/dev/null)
    fi
    
    # 如果为0，尝试从batch-mapping获取
    if [[ "$total_batches" == "0" ]]; then
        local batch_mapping_file="$CACHE_DIR/batch-mapping.json"
        if [[ -f "$batch_mapping_file" ]]; then
            if command -v jq >/dev/null 2>&1; then
                total_batches=$(jq -r '.total_batches // 0' "$batch_mapping_file" 2>/dev/null || echo "0")
            elif command -v python3 >/dev/null 2>&1; then
                total_batches=$(python3 -c "
import json
import sys
try:
    with open('$batch_mapping_file', 'r', encoding='utf-8') as f:
        data = json.load(f)
    print(data.get('total_batches', 0))
except:
    print(0)
" 2>/dev/null)
            fi
        fi
    fi
    
    echo "$total_batches"
}

# 收集临时文件
collect_temp_files() {
    if [[ ! -d "$TEMP_DIR" ]]; then
        return
    fi
    
    local prefix="interface-${BATCH_NUMBER}-"
    local temp_files=()
    
    # 查找匹配的临时文件
    for file in "$TEMP_DIR"/${prefix}*.json; do
        if [[ -f "$file" ]]; then
            temp_files+=("$file")
        fi
    done
    
    # 按文件索引排序
    printf '%s\n' "${temp_files[@]}" | sort -t'-' -k3 -n
}

# 合并接口数据（使用jq）
merge_interfaces_with_jq() {
    local temp_files=("$@")
    
    # 合并所有临时文件，统一处理
    # 先提取所有接口到一个数组，过滤掉无效接口
    jq -s --arg batch "$BATCH_NUMBER" \
        '[.[] | if type == "array" then .[] elif .interfaces then .interfaces[] else empty end] | 
        map(select(.name != null and .interface_type != null and .source_file != null)) |
        to_entries | 
        map(.value + {interface_id: ("API-" + $batch + "-" + ((.key + 1) | tostring | ("000" + .) | .[-3:]))}) |
        map(.value)' \
        "${temp_files[@]}" 2>/dev/null
}

# 主处理逻辑
main() {
    log_info "开始生成批次 ${BATCH_NUMBER} 的接口清单..."
    
    # 获取总批次数
    TOTAL_BATCHES=$(get_total_batches)
    if [[ "$TOTAL_BATCHES" == "0" ]]; then
        log_error "无法获取总批次数"
        exit 1
    fi
    
    # 收集临时文件
    mapfile -t TEMP_FILES < <(collect_temp_files)
    
    if [[ ${#TEMP_FILES[@]} -eq 0 ]]; then
        log_info "警告: 未找到批次 ${BATCH_NUMBER} 的临时文件，生成空清单"
        ALL_INTERFACES_JSON="[]"
    else
        log_info "找到 ${#TEMP_FILES[@]} 个临时文件"
        
        # 合并接口数据
        if command -v jq >/dev/null 2>&1; then
            # 使用jq合并所有临时文件并生成interface_id
            ALL_INTERFACES_JSON=$(merge_interfaces_with_jq "${TEMP_FILES[@]}")
            if [[ -z "$ALL_INTERFACES_JSON" ]]; then
                ALL_INTERFACES_JSON="[]"
            fi
        else
            log_error "需要 jq 来处理接口合并，建议安装 jq 或使用 Python 脚本"
            exit 1
        fi
    fi
    
    # 生成批次接口清单JSON
    GENERATED_AT=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    
    if command -v jq >/dev/null 2>&1; then
        jq -n \
            --argjson batch_number "$BATCH_NUMBER" \
            --argjson total_batches "$TOTAL_BATCHES" \
            --arg generated_at "$GENERATED_AT" \
            --argjson interfaces "$ALL_INTERFACES_JSON" \
            '{
                batch_number: $batch_number,
                total_batches: $total_batches,
                generated_at: $generated_at,
                interfaces: $interfaces
            }' > "$OUTPUT_FILE"
    else
        log_error "需要 jq 来生成JSON文件，建议安装 jq 或使用 Python 脚本"
        exit 1
    fi
    
    # 统计接口数量
    INTERFACE_COUNT=$(echo "$ALL_INTERFACES_JSON" | jq 'length')
    
    log_info "成功生成批次接口清单: $OUTPUT_FILE"
    log_info "包含 $INTERFACE_COUNT 个接口"

    # 回写 batch-details-{n}.json 中每个文件条目的状态（根据 temp/interface-{batch}-{idx}.json 是否存在）
    # 说明：这是断点续跑与状态追踪的关键，否则 batch-details 文件内 files[].status 会一直停留在 pending。
    local status_updater=""
    if [[ -f "$REPO_ROOT/specify/scripts/python/update_batch_details_file_status.py" ]]; then
        status_updater="$REPO_ROOT/specify/scripts/python/update_batch_details_file_status.py"
    elif [[ -f "$REPO_ROOT/.specify/scripts/python/update_batch_details_file_status.py" ]]; then
        # 向后兼容：部分发行版可能使用 .specify 目录
        status_updater="$REPO_ROOT/.specify/scripts/python/update_batch_details_file_status.py"
    fi

    if command -v python3 >/dev/null 2>&1 && [[ -n "$status_updater" ]]; then
        # 不阻塞主流程：回写失败仅告警
        if ! python3 "$status_updater" --repo-root "$REPO_ROOT" --batch-number "$BATCH_NUMBER" >/dev/null 2>&1; then
            log_info "警告: 回写批次文件状态失败（不影响接口清单生成）"
        fi
    else
        log_info "警告: 未找到 python3 或状态回写脚本，跳过 batch-details 状态回写"
    fi
}

# 执行主函数
main

