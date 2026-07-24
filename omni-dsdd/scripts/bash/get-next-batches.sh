#!/usr/bin/env bash
# 接口扫描批次信息批量获取工具 (Bash版本)
# 在AI Agent批量处理批次时，获取要处理的多个批次信息

set -e

# 初始化变量
REPO_ROOT=""
ACTION=""
BATCH_COUNT=5

# 显示帮助信息
show_help() {
    cat << 'EOF'
接口扫描批次信息批量获取工具 (Bash版本)
在AI Agent批量处理批次时，获取要处理的多个批次信息

使用方法:
    ./get-next-batches.sh --repo-root <repo_root> --batch-count <count>

参数:
    --repo-root: 仓库根目录路径
    --batch-count: 要获取的批次数量（默认5）
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
        --batch-count)
            BATCH_COUNT="$2"
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
if [[ -z "$REPO_ROOT" ]]; then
    echo "错误: 必须提供 --repo-root 参数" >&2
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

# 获取多个待处理的批次
get_next_pending_batches() {
    local batch_count="$1"
    local batch_mapping_file="$CACHE_DIR/batch-mapping.json"

    if [[ ! -f "$batch_mapping_file" ]]; then
        echo "错误: 批次映射文件不存在 $batch_mapping_file" >&2
        echo "[]"
        return
    fi

    # 使用jq查找多个状态为pending的批次
    local batches_info
    batches_info=$(jq -r --argjson count "$batch_count" '
        [.batches[] | select(.status == "pending")] | .[0:$count]
    ' "$batch_mapping_file" 2>/dev/null)

    # 如果没有找到足够的pending批次，查找状态为initialized的批次作为补充
    if [[ -z "$batches_info" ]] || [[ "$batches_info" == "null" ]] || [[ "$batches_info" == "[]" ]]; then
        batches_info=$(jq -r --argjson count "$batch_count" '
            [.batches[] | select(.status == "initialized")] | .[0:$count]
        ' "$batch_mapping_file" 2>/dev/null)
    fi

    if [[ -n "$batches_info" ]]; then
        echo "$batches_info"
    else
        echo "[]"  # 返回空数组表示没有更多批次
    fi
}

# 主函数
main() {
    # 获取多个待处理的批次
    get_next_pending_batches "$BATCH_COUNT"
}

# 执行主函数
main