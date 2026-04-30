#!/usr/bin/env bash
# 要素类型注册表
# 定义OmniSpec支持的各种反构要素类型及其相关信息

set -e
set -u
set -o pipefail

# 日志函数
log_debug() {
    if [[ "${VERBOSE:-false}" == "true" ]]; then
        echo "[DEBUG] $*" >&2
    fi
}

# 要素类型信息格式:
# 名称|扫描函数|分析函数|验证函数|合并函数|模板文件|输出目录

# 注册要素类型
# 参数:
#   $1: 要素类型标识符（如 interfaces, functions, business_entities）
#   $2: 扫描函数名
#   $3: 分析函数名
#   $4: 验证函数名（可选，默认为 null）
#   $5: 合并函数名（可选，默认为 null）
#   $6: 模板文件名
#   $7: 输出目录子路径
register_element_type() {
    local element_type="$1"
    local scanner="$2"
    local analyzer="$3"
    local validator="${4:-null}"
    local merger="${5:-null}"
    local template="$6"
    local output_dir="$7"

    # 将要素类型信息存储在关联数组中
    ELEMENT_TYPES["$element_type"]="${element_type}|${scanner}|${analyzer}|${validator}|${merger}|${template}|${output_dir}"

    log_debug "已注册要素类型: $element_type"
}

# 获取所有已注册的要素类型
# 返回:
#   空格分隔的要素类型列表
get_all_element_types() {
    echo "${!ELEMENT_TYPES[@]}"
}

# 获取要素类型信息
# 参数:
#   $1: 要素类型标识符
# 返回:
#   要素类型信息字符串，格式为: 名称|扫描函数|分析函数|验证函数|合并函数|模板文件|输出目录
#   如果要素类型不存在，返回非零退出码
get_element_type_info() {
    local element_type="$1"

    if [[ -n "${ELEMENT_TYPES[$element_type]:-}" ]]; then
        echo "${ELEMENT_TYPES[$element_type]}"
        return 0
    else
        return 1
    fi
}

# 检查要素类型是否有效
# 参数:
#   $1: 要素类型标识符
# 返回:
#   0: 有效
#   1: 无效
is_valid_element_type() {
    local element_type="$1"

    if [[ -n "${ELEMENT_TYPES[$element_type]:-}" ]]; then
        return 0
    else
        return 1
    fi
}

# 初始化要素类型数组
declare -A ELEMENT_TYPES

# 注册默认要素类型
# 接口要素类型
register_element_type "interfaces" \
    "scan_interfaces" \
    "analyze_interfaces" \
    "validate_interfaces" \
    "merge_interfaces" \
    "reverse-interface-detail-template.md" \
    "interfaces"

# 功能要素类型
register_element_type "functions" \
    "scan_functions" \
    "analyze_functions" \
    "validate_functions" \
    "merge_functions" \
    "reverse-function-detail-template.md" \
    "functions"

# 业务实体要素类型（新增）
register_element_type "business_entities" \
    "scan_business_entities" \
    "analyze_business_entities" \
    "validate_business_entities" \
    "merge_business_entities" \
    "reverse-business-entity-template.md" \
    "business_entities"

# 外部依赖接口要素类型（输出到 omni-doc/external-interfaces）
register_element_type "external_interfaces" \
    "scan_external_imports" \
    "analyze_external_calls" \
    "null" \
    "null" \
    "reverse-external-interface-detail-template.md" \
    "external-interfaces"

log_debug "要素类型注册表初始化完成"