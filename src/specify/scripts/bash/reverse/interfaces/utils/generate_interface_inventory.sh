#!/bin/bash

# 生成接口清单脚本
# 用途: 收集所有已生成的接口详情文档信息，根据模板生成汇总接口清单文档

set -euo pipefail

# 加载公共函数
SCRIPT_DIR="$(CDPATH="" cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMMON_SCRIPT="$SCRIPT_DIR/../../../../bash/common.sh"
if [[ -f "$COMMON_SCRIPT" ]]; then
    source "$COMMON_SCRIPT"
else
    echo "错误: 无法加载公共函数脚本: $COMMON_SCRIPT" >&2
    exit 1
fi

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 将中文业务名称转换为英文slug
convert_to_english_slug() {
    local chinese_name="$1"

    # 简单的中英文映射（可以根据需要扩展）
    case "$chinese_name" in
        *"获取"* | *"查询"*) echo "get" ;;
        *"创建"* | *"新增"*) echo "create" ;;
        *"更新"* | *"修改"*) echo "update" ;;
        *"删除"* | *"移除"*) echo "delete" ;;
        *"发送"*) echo "send" ;;
        *"处理"*) echo "process" ;;
        *"验证"*) echo "validate" ;;
        *"计算"*) echo "calculate" ;;
        *"导入"*) echo "import" ;;
        *"导出"*) echo "export" ;;
        *) echo "unknown" ;;
    esac
}

# 将中文业务名称转换为拼音slug
convert_to_pinyin_slug() {
    local chinese_name="$1"

    # 简单的拼音转换（实际应用中可以使用专门的拼音库）
    # 这里只是一个示例，实际应用中应该使用更完善的拼音转换
    echo "$chinese_name" | sed 's/根据//g' | sed 's/用户/user/g' | sed 's/订单/order/g' | sed 's/商品/product/g' | sed 's/信息/info/g' | sed 's/列表/list/g' | sed 's/ID/id/g' | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g' | sed 's/^-//' | sed 's/-$//' | sed 's/--*/-/g'
}

# 显示使用方法
show_usage() {
    echo "用法: $0 --repo-root <仓库根目录>"
    echo "示例: $0 --repo-root /path/to/project"
}

# 解析命令行参数
REPO_ROOT=""
while [[ $# -gt 0 ]]; do
    case $1 in
        --repo-root)
            REPO_ROOT="$2"
            shift 2
            ;;
        --help|-h)
            show_usage
            exit 0
            ;;
        *)
            log_error "未知参数: $1"
            show_usage
            exit 1
            ;;
    esac
done

# 检查必需参数
if [[ -z "$REPO_ROOT" ]]; then
    log_error "缺少必需参数 --repo-root"
    show_usage
    exit 1
fi

# 检查目录是否存在
if [[ ! -d "$REPO_ROOT" ]]; then
    log_error "仓库根目录不存在: $REPO_ROOT"
    exit 1
fi

# 定义路径
# 使用 find_template_file 查找模板文件（支持按项目查找）
OMNISPEC_ROOT="$(CDPATH="" cd "$SCRIPT_DIR/../../../../../.." && pwd)"
TEMPLATE_FILE=$(find_template_file "reverse-interface-inventory-template.md" "$REPO_ROOT" "" "$OMNISPEC_ROOT")
if [[ -z "$TEMPLATE_FILE" ]] || [[ ! -f "$TEMPLATE_FILE" ]]; then
    log_error "接口清单模板文件未找到"
    exit 1
fi

# 默认输出目录：{REPO_ROOT}/omni-doc/interfaces
OUTPUT_DIR="$REPO_ROOT/omni-doc/interfaces"
INVENTORY_FILE="$OUTPUT_DIR/接口清单.md"
INTERFACE_LIST_FILE="$REPO_ROOT/.cache/omni-reverse/interfaces/interface-list.json"

# 检查输出目录是否存在，不存在则创建
if [[ ! -d "$OUTPUT_DIR" ]]; then
    log_info "创建输出目录: $OUTPUT_DIR"
    mkdir -p "$OUTPUT_DIR"
fi

log_info "开始生成接口清单..."

# 获取生成时间
GENERATED_AT=$(date '+%Y-%m-%d %H:%M:%S')

# 初始化统计数据
TOTAL_COUNT=0
TYPE_STATISTICS=()
DOMAIN_STATISTICS=()

# 如果接口列表文件存在，则从中获取统计数据
if [[ -f "$INTERFACE_LIST_FILE" ]]; then
    log_info "从接口列表文件获取统计数据: $INTERFACE_LIST_FILE"

    # 获取接口总数
    TOTAL_COUNT=$(jq '.interfaces | length' "$INTERFACE_LIST_FILE" 2>/dev/null || echo "0")

    # 获取接口类型统计
    if [[ $TOTAL_COUNT -gt 0 ]]; then
        # 使用jq获取类型统计
        TYPE_STATS_JSON=$(jq -r '.interfaces | group_by(.interface_type) | map({type_name: .[0].interface_type, count: length}) | .[] | "- **\(.type_name)接口**: \(.count) 个"' "$INTERFACE_LIST_FILE" 2>/dev/null || echo "")

        # 将JSON结果转换为数组
        while IFS= read -r line; do
            [[ -n "$line" ]] && TYPE_STATISTICS+=("$line")
        done <<< "$TYPE_STATS_JSON"

        # 获取业务领域统计
        DOMAIN_STATS_JSON=$(jq -r '.interfaces | group_by(.business_domain) | map({domain_name: .[0].business_domain, count: length}) | .[] | "- **\(.domain_name)**: \(.count) 个"' "$INTERFACE_LIST_FILE" 2>/dev/null || echo "")

        # 将JSON结果转换为数组
        while IFS= read -r line; do
            [[ -n "$line" ]] && DOMAIN_STATISTICS+=("$line")
        done <<< "$DOMAIN_STATS_JSON"
    fi
else
    log_warn "接口列表文件不存在: $INTERFACE_LIST_FILE"
    # 通过扫描output目录下的接口文件来统计
    INTERFACE_FILES_COUNT=$(find "$OUTPUT_DIR" -name "*.md" -not -name "接口清单.md" | wc -l)
    TOTAL_COUNT=$INTERFACE_FILES_COUNT
fi

# 收集接口列表信息
INTERFACES_TABLE=""

# 查找所有接口详情文档（排除接口清单本身）
INTERFACE_DETAIL_FILES=$(find "$OUTPUT_DIR" -name "*.md" -not -name "接口清单.md" | sort)

if [[ -n "$INTERFACE_DETAIL_FILES" ]]; then
    while IFS= read -r file; do
        [[ -z "$file" ]] && continue

        # 从文件名提取接口ID和接口名称
        filename=$(basename "$file" .md)

        # 尝试从文件内容提取接口信息
        if [[ -f "$file" ]]; then
            # 提取接口ID
            interface_id=$(grep -E '^\- \*\*接口ID\*\*: ' "$file" | head -1 | sed 's/^- \*\*接口ID\*\*: //' || echo "N/A")

            # 提取接口名称
            interface_name=$(grep -E '^\- \*\*接口名称\*\*: ' "$file" | head -1 | sed 's/^- \*\*接口名称\*\*: //' || echo "$filename")

            # 提取接口类型
            interface_type=$(grep -E '^\- \*\*接口类型\*\*: ' "$file" | head -1 | sed 's/^- \*\*接口类型\*\*: //' || echo "N/A")

            # 提取所属文件
            source_file=$(grep -E '^\- \*\*所属文件\*\*: ' "$file" | head -1 | sed 's/^- \*\*所属文件\*\*: //' || echo "N/A")

            # 如果从文件内容无法提取到有效ID，则使用文件名
            if [[ "$interface_id" == "N/A" || -z "$interface_id" ]]; then
                interface_id="$filename"
            fi

            # 生成相对路径用于链接
            relative_file="./$(basename "$file")"

            # 提取业务名称（如果存在）
            business_name=$(grep -E '^\- \*\*业务名称\*\*: ' "$file" | head -1 | sed 's/^- \*\*业务名称\*\*: //' || echo "$interface_name")

            # 提取业务领域（如果存在）
            business_domain=$(grep -E '^\- \*\*业务领域\*\*: ' "$file" | head -1 | sed 's/^- \*\*业务领域\*\*: //' || echo "N/A")

            # 添加到表格
            INTERFACES_TABLE="${INTERFACES_TABLE}| ${interface_id} | ${business_name} | ${interface_type} | ${business_domain} | [${business_name}](${relative_file}) |\n"
        fi
    done <<< "$INTERFACE_DETAIL_FILES"
fi

# 读取模板内容
TEMPLATE_CONTENT=$(cat "$TEMPLATE_FILE")

# 替换模板变量
FINAL_CONTENT="$TEMPLATE_CONTENT"
FINAL_CONTENT="${FINAL_CONTENT//\{\{generated_at\}\}/$GENERATED_AT}"
FINAL_CONTENT="${FINAL_CONTENT//\{\{total_count\}\}/$TOTAL_COUNT}"

# 处理类型统计部分
if [[ ${#TYPE_STATISTICS[@]} -gt 0 ]]; then
    TYPE_STATS_CONTENT=""
    for stat in "${TYPE_STATISTICS[@]}"; do
        TYPE_STATS_CONTENT="${TYPE_STATS_CONTENT}${stat}"$'\n'
    done
    # 移除最后的换行符
    TYPE_STATS_CONTENT="${TYPE_STATS_CONTENT%$'\n'}"

    # 替换类型统计部分 - 使用字符串替换
    # 先找到占位符的位置
    BEFORE_TYPE_STATS=$(echo "$FINAL_CONTENT" | sed '/{{#type_statistics}}/q' | sed '$d')
    AFTER_TYPE_STATS=$(echo "$FINAL_CONTENT" | sed '1,/{{\/type_statistics}}/d')

    FINAL_CONTENT="${BEFORE_TYPE_STATS}"$'\n'"${TYPE_STATS_CONTENT}"$'\n'"${AFTER_TYPE_STATS}"
else
    # 如果没有类型统计，删除占位符块
    FINAL_CONTENT=$(echo "$FINAL_CONTENT" | sed '/{{#type_statistics}}/,/{{\/type_statistics}}/d')
fi

# 处理业务领域统计部分
if [[ ${#DOMAIN_STATISTICS[@]} -gt 0 ]]; then
    DOMAIN_STATS_CONTENT=""
    for stat in "${DOMAIN_STATISTICS[@]}"; do
        DOMAIN_STATS_CONTENT="${DOMAIN_STATS_CONTENT}${stat}"$'\n'
    done
    # 移除最后的换行符
    DOMAIN_STATS_CONTENT="${DOMAIN_STATS_CONTENT%$'\n'}"

    # 替换业务领域统计部分 - 使用字符串替换
    # 先找到占位符的位置
    BEFORE_DOMAIN_STATS=$(echo "$FINAL_CONTENT" | sed '/{{#domain_statistics}}/q' | sed '$d')
    AFTER_DOMAIN_STATS=$(echo "$FINAL_CONTENT" | sed '1,/{{\/domain_statistics}}/d')

    FINAL_CONTENT="${BEFORE_DOMAIN_STATS}"$'\n'"${DOMAIN_STATS_CONTENT}"$'\n'"${AFTER_DOMAIN_STATS}"
else
    # 如果没有业务领域统计，删除占位符块
    FINAL_CONTENT=$(echo "$FINAL_CONTENT" | sed '/{{#domain_statistics}}/,/{{\/domain_statistics}}/d')
fi

# 处理接口列表部分
if [[ -n "$INTERFACES_TABLE" ]]; then
    # 替换接口列表部分 - 使用字符串替换
    # 先找到占位符的位置
    BEFORE_INTERFACES=$(echo "$FINAL_CONTENT" | sed '/{{#interfaces}}/q' | sed '$d')
    AFTER_INTERFACES=$(echo "$FINAL_CONTENT" | sed '1,/{{\/interfaces}}/d')

    # 处理换行符
    PROCESSED_INTERFACES_TABLE=$(echo "$INTERFACES_TABLE" | sed 's/\\n/\n/g')

    FINAL_CONTENT="${BEFORE_INTERFACES}"$'\n'"${PROCESSED_INTERFACES_TABLE}"$'\n'"${AFTER_INTERFACES}"
else
    # 如果没有接口列表，删除占位符块
    FINAL_CONTENT=$(echo "$FINAL_CONTENT" | sed '/{{#interfaces}}/,/{{\/interfaces}}/d')
fi

# 写入重试机制
MAX_RETRIES=3
RETRY_COUNT=0
SUCCESS=false

while [[ $RETRY_COUNT -lt $MAX_RETRIES && "$SUCCESS" == "false" ]]; do
    RETRY_COUNT=$((RETRY_COUNT + 1))
    log_info "尝试写入接口清单文件 (第 $RETRY_COUNT/$MAX_RETRIES 次)..."

    # 尝试写入文件
    if echo "$FINAL_CONTENT" > "$INVENTORY_FILE"; then
        SUCCESS=true
        log_info "接口清单文件生成成功: $INVENTORY_FILE"
    else
        log_warn "写入失败，$((2**RETRY_COUNT))秒后重试..."
        sleep $((2**RETRY_COUNT))
    fi
done

if [[ "$SUCCESS" == "false" ]]; then
    log_error "写入接口清单文件失败，已重试 $MAX_RETRIES 次"
    exit 1
fi

# 验证生成的文件
if [[ -f "$INVENTORY_FILE" ]]; then
    GENERATED_SIZE=$(stat -c%s "$INVENTORY_FILE" 2>/dev/null || stat -f%z "$INVENTORY_FILE" 2>/dev/null || echo "0")
    if [[ $GENERATED_SIZE -gt 0 ]]; then
        log_info "接口清单生成完成，文件大小: ${GENERATED_SIZE} 字节"
        echo "接口清单已生成到: $INVENTORY_FILE"
        exit 0
    else
        log_error "生成的接口清单文件为空"
        exit 1
    fi
else
    log_error "接口清单文件未找到: $INVENTORY_FILE"
    exit 1
fi