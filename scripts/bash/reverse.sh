#!/usr/bin/env bash

# reverse - 从代码库中反构各种类型的要素，生成标准化的要素文档
#
# 第一阶段支持接口清单（interfaces）反构
#
# Usage: reverse.sh [OPTIONS]
#
# 详细用法请参考 --help

set -e
set -u
set -o pipefail

# 脚本目录
SCRIPT_DIR="$(CDPATH="" cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 加载公共函数
source "$SCRIPT_DIR/common.sh"

# 加载要素类型注册表
source "$SCRIPT_DIR/reverse/element-registry.sh"

# 加载接口辅助函数模块（按需加载）
# 注意：接口辅助函数模块包含所有接口相关的函数，方便后续扩展其他要素类型
# 如果使用了接口相关的辅助命令，或者目标要素类型是interfaces，则加载模块
INTERFACE_HELPERS_LOADED=false
if [[ $# -gt 0 ]]; then
    case "${1:-}" in
        --load-few-shot-template|--extract-identification-rules|--extract-constraints|--extract-format-definition|--extract-interface-types|--format-rules-for-prompt)
            # 辅助命令，需要加载接口辅助函数模块
            if [[ -f "$SCRIPT_DIR/reverse/interfaces/utils/interface-helpers.sh" ]]; then
                source "$SCRIPT_DIR/reverse/interfaces/utils/interface-helpers.sh"
                INTERFACE_HELPERS_LOADED=true
            else
                log_error "接口辅助函数模块不存在: $SCRIPT_DIR/reverse/interfaces/utils/interface-helpers.sh"
                exit 1
            fi
            ;;
    esac
fi

# 获取仓库根目录
REPO_ROOT=$(get_repo_root)

# 错误码定义（参考设计文档 8.4 节）
# 参数和配置错误 (1-10)
ERROR_INVALID_PARAMS=1
ERROR_INVALID_TARGET=2
ERROR_INVALID_INTERFACE_TYPES=3
ERROR_MISSING_REQUIRED_PARAM=4
ERROR_INVALID_PARAM_COMBINATION=5
ERROR_PERMISSION_DENIED=6
ERROR_DISK_FULL=7
ERROR_DEPENDENCY_MISSING=8
ERROR_CACHE_ERROR=9
ERROR_MERGE_CONFLICT=10

# 文件系统错误 (11-20)
ERROR_FILE_NOT_FOUND=11
ERROR_FILE_READ_ERROR=12
ERROR_FILE_WRITE_ERROR=13
ERROR_PERMISSION_DENIED_FS=14
ERROR_DISK_FULL_FS=15
ERROR_DIRECTORY_NOT_FOUND=16

# 分析处理错误 (21-30)
ERROR_ANALYSIS_FAILED=21
ERROR_DEPENDENCY_MISSING_ANALYSIS=22
ERROR_LANGUAGE_NOT_SUPPORTED=23

# 输出和模板错误 (31-40)
ERROR_TEMPLATE_ERROR=31
ERROR_TEMPLATE_NOT_FOUND=32
ERROR_OUTPUT_FAILED=33
ERROR_JSON_OUTPUT_FAILED=34

# 缓存和合并错误 (41-50)
ERROR_CACHE_ERROR_MERGE=41
ERROR_MERGE_CONFLICT_DETAIL=42
ERROR_MERGE_FAILED=43

# 日志函数
log_info() {
    echo "[INFO] $*" >&2
}

log_warn() {
    echo "[WARN] $*" >&2
}

log_error() {
    echo "[ERROR] $*" >&2
}

log_debug() {
    if [[ "${VERBOSE:-false}" == "true" ]]; then
        echo "[DEBUG] $*" >&2
    fi
}

log_success() {
    echo "[SUCCESS] $*" >&2
}

check_tool() {
    local tool="$1"
    local required="${2:-false}"
    
    if command -v "$tool" >/dev/null 2>&1; then
        log_debug "工具检查通过: $tool"
        return 0
    else
        if [[ "$required" == "true" ]]; then
            log_error "必需的工具不存在: $tool"
            log_error "请安装 $tool 后重试"
            return 1
        else
            log_warn "可选工具不存在: $tool（某些功能可能不可用）"
            return 1
        fi
    fi
}

# 检查所有依赖工具
# 返回:
#   0: 所有必需工具都存在
#   1: 有必需工具缺失
check_dependencies() {
    local missing_required=false
    
    # 检查必需工具
    if ! check_tool "jq" true; then
        missing_required=true
    fi
    
    # 检查可选工具
    check_tool "git" false
    
    if [[ "$missing_required" == "true" ]]; then
        log_error "依赖检查失败：缺少必需工具"
        return 1
    fi
    
    log_debug "依赖检查通过"
    return 0
}

# 检测是否为交互式终端
# 返回:
#   0: 是交互式终端
#   1: 不是交互式终端
# 检测是否在 AI Agent 环境中运行
# 返回:
#   0: 在 AI Agent 环境中
#   1: 不在 AI Agent 环境中
is_ai_agent_environment() {
    # 检测常见的 AI Agent 环境变量
    if [[ -n "${CLAUDE_CODE:-}" ]] || \
       [[ -n "${CURSOR_AGENT:-}" ]] || \
       [[ -n "${FLOW_AGENT:-}" ]] || \
       [[ -n "${AI_AGENT:-}" ]] || \
       [[ "${TERM_PROGRAM:-}" == "ClaudeCode" ]] || \
       [[ "${TERM_PROGRAM:-}" == "Cursor" ]] || \
       [[ "${TERM_PROGRAM:-}" == "Flow" ]]; then
        return 0
    fi
    
    # 检测是否在非交互式终端但允许继续（AI Agent 环境特征）
    if ! is_interactive && [[ -n "${OMNI_AI_AGENT_MODE:-}" ]]; then
        return 0
    fi
    
    return 1
}

is_interactive() {
    # 使用 [[ -t 0 ]] 检测标准输入是否为终端
    if [[ -t 0 ]]; then
        return 0
    else
        return 1
    fi
}

# 确认交互模式
# 根据参数和环境确定是否应该使用交互模式
# 返回:
#   0: 应该使用交互模式
#   1: 不应该使用交互模式
should_use_interactive() {
    # 如果指定了 --non-interactive，强制非交互模式
    if [[ "${NON_INTERACTIVE:-false}" == "true" ]]; then
        return 1
    fi
    
    # 如果指定了 --yes，自动接受所有默认选项，非交互模式
    if [[ "${YES:-false}" == "true" ]]; then
        return 1
    fi
    
    # 如果指定了 --interactive，强制交互模式
    if [[ "${INTERACTIVE:-false}" == "true" ]]; then
        # 检查是否在交互式终端
        if is_interactive; then
            return 0
        else
            # 在 AI Agent 环境中，允许继续但给出警告
            if is_ai_agent_environment; then
                log_warn "警告: --interactive 参数已指定，但当前在 AI Agent 环境中"
                log_warn "提示: 将使用非交互模式继续执行（AI Agent 会处理交互）"
                return 1
            else
                log_error "错误: --interactive 参数已指定，但当前不在交互式终端"
                log_error "提示: 在非交互式终端中，请使用 --non-interactive 或 --yes 参数"
                exit $ERROR_INVALID_PARAM_COMBINATION
            fi
        fi
    fi
    
    # 默认情况下，如果在交互式终端，使用交互模式
    if is_interactive; then
        return 0
    else
        return 1
    fi
}

# 注意：接口相关的展示和辅助函数已移至独立的接口辅助函数模块
# 模块路径: reverse/interfaces/utils/interface-helpers.sh
# 这些函数在需要时由 dispatch_element_type 函数自动加载

# 注意：用户交互确认函数已移除
# 所有用户交互应在 AI Agent 层处理
# AI Agent 直接读取 JSON 文件并总结展示，不再使用展示脚本
# 以下函数保留仅用于向后兼容，但不应在主流程中使用

# 展示接口详细信息预览
# 参数:
#   $1: 接口详细信息 JSON 数据（文件路径或 JSON 字符串）
# 返回:
#   0: 成功
#   1: 失败

# 注意：用户交互确认函数已移除
# 所有用户交互应在 AI Agent 层处理
# AI Agent 直接读取 JSON 文件并总结展示，不再使用展示脚本
# 以下函数保留仅用于向后兼容，但不应在主流程中使用

# 显示帮助信息
show_help() {
    cat << 'EOF'
reverse - 从代码库中反构各种类型的要素，生成标准化的要素文档

用法：
  reverse.sh [OPTIONS]

必需参数：
  --target <type>           目标要素类型（第一阶段支持 'interfaces'）

可选参数：
范围指定：
  --path <path1,path2,...>  反构的目录路径（逗号分隔）
  --files <file1,file2,...> 反构的文件路径（逗号分隔）
                           注意：--path 和 --files 至少需要指定一个

接口类型过滤（仅当 --target interfaces 时使用）：
  --interface-types <types> 指定要反构的接口类型（逗号分隔）
                           支持的类型：restful, message, module, cli, rpc, function, other

输出控制：
  --output-dir <dir>        输出目录，默认根据分支类型决定
  --template <file>         模板文件路径，默认使用内置模板
  --preview                 预览模式，不写入文件
  --json                    JSON 格式输出

AI 分析结果（由 AI Agent 传递）：
  --architecture-result <file>   架构识别结果 JSON 文件
  --few-shot-examples <file>    Few-shot 示例 JSON 文件
  --interface-list <file>        接口清单 JSON 文件
  --interface-details <file>     接口详细信息 JSON 文件

交互模式：
  --interactive [yes|no]    启用交互式确认（支持 yes/no 格式，默认为 yes）
  --non-interactive         强制非交互模式
  --yes                     非交互模式，自动接受所有默认选项

增量反构：
  --incremental             增量反构模式
  --git-diff <commit>       基于 Git 提交差异反构（需配合 --incremental）
  --since <date>            基于时间戳反构（需配合 --incremental）
  --merge                   合并到现有清单文件（需配合 --incremental）

其他选项：
  --validate                启用结果校验
  --exclude <pattern>       排除文件模式（可多次使用）
  --clear-cache             清理缓存
  --verbose                 详细输出模式
  --help, -h                显示此帮助信息

智能确认模式：
  --fast-mode               快速模式，跳过所有确认直接生成结果
  --smart-mode              智能模式，仅对低置信度结果进行确认

参数说明：
  --target                  目标要素类型，第一阶段支持 'interfaces'
  --path, --files           至少需要指定一个，可以同时使用（取并集）
  --interface-types         仅当 --target interfaces 时使用，默认反构所有类型
  --incremental             需要配合 --git-diff 或 --since 使用
  --merge                   需要配合 --incremental 使用
  --git-diff, --since       需要配合 --incremental 使用，且不能同时指定
  --interactive             与 --non-interactive/--yes 互斥

使用示例：
  # 反构整个代码库的接口
  reverse.sh --target interfaces --path .

  # 反构指定目录的接口
  reverse.sh --target interfaces --path src/api/,src/services/

  # 仅反构 RESTful 和消息类接口
  reverse.sh --target interfaces --path src/ --interface-types restful,message

  # 反构指定文件的接口
  reverse.sh --target interfaces --files src/api/user.py

  # 交互式反构
  reverse.sh --target interfaces --path src/ --interactive
  reverse.sh --target interfaces --path src/ --interactive yes

  # 预览模式
  reverse.sh --target interfaces --path src/ --preview

  # JSON 输出
  reverse.sh --target interfaces --path src/ --json

  # 增量反构
  reverse.sh --target interfaces --incremental --git-diff HEAD~1 --merge

更多信息：
  请参考设计文档：infra/design/omni_reverse_interface_inventory_design.md

EOF
}

# 参数解析函数（第一阶段：基础框架）
parse_args() {
    # 初始化参数变量
    TARGET=""
    PATHS=""
    FILES=""
    INTERFACE_TYPES=""
    OUTPUT_DIR=""
    TEMPLATE=""
    INTERACTIVE=false
    NON_INTERACTIVE=false
    YES=false
    PREVIEW=false
    INCREMENTAL=false
    GIT_DIFF=""
    SINCE=""
    MERGE=false
    VALIDATE=false
    EXCLUDE_PATTERNS=()
    CLEAR_CACHE=false
    VERBOSE=false
    JSON=false
    HELP=false
    FAST_MODE=false
    SMART_MODE=false
    
    # AI 分析结果文件（由 AI Agent 传递）
    ARCHITECTURE_RESULT=""
    FEW_SHOT_EXAMPLES=""
    INTERFACE_LIST=""
    INTERFACE_DETAILS=""

    # 参数解析循环
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --target)
                if [[ $# -lt 2 ]]; then
                    log_error "参数错误: --target 需要指定值"
                    exit $ERROR_INVALID_PARAMS
                fi
                TARGET="$2"
                shift 2
                ;;
            --path)
                if [[ $# -lt 2 ]]; then
                    log_error "参数错误: --path 需要指定值"
                    exit $ERROR_INVALID_PARAMS
                fi
                PATHS="$2"
                shift 2
                ;;
            --files)
                if [[ $# -lt 2 ]]; then
                    log_error "参数错误: --files 需要指定值"
                    exit $ERROR_INVALID_PARAMS
                fi
                FILES="$2"
                shift 2
                ;;
            --interface-types)
                if [[ $# -lt 2 ]]; then
                    log_error "参数错误: --interface-types 需要指定值"
                    exit $ERROR_INVALID_PARAMS
                fi
                INTERFACE_TYPES="$2"
                shift 2
                ;;
            --output-dir)
                if [[ $# -lt 2 ]]; then
                    log_error "参数错误: --output-dir 需要指定值"
                    exit $ERROR_INVALID_PARAMS
                fi
                OUTPUT_DIR="$2"
                shift 2
                ;;
            --template)
                if [[ $# -lt 2 ]]; then
                    log_error "参数错误: --template 需要指定值"
                    exit $ERROR_INVALID_PARAMS
                fi
                TEMPLATE="$2"
                shift 2
                ;;
            --interactive)
                # 支持 --interactive yes/no 格式（向后兼容）
                if [[ $# -ge 2 ]] && [[ "$2" == "yes" ]]; then
                    INTERACTIVE=true
                    shift 2
                elif [[ $# -ge 2 ]] && [[ "$2" == "no" ]]; then
                    INTERACTIVE=false
                    NON_INTERACTIVE=true
                    shift 2
                else
                    # 默认行为：--interactive 表示启用交互模式
                    INTERACTIVE=true
                    shift
                fi
                ;;
            --non-interactive)
                NON_INTERACTIVE=true
                shift
                ;;
            --yes)
                YES=true
                shift
                ;;
            --preview)
                PREVIEW=true
                shift
                ;;
            --incremental)
                INCREMENTAL=true
                shift
                ;;
            --git-diff)
                if [[ $# -lt 2 ]]; then
                    log_error "参数错误: --git-diff 需要指定值"
                    exit $ERROR_INVALID_PARAMS
                fi
                GIT_DIFF="$2"
                shift 2
                ;;
            --since)
                if [[ $# -lt 2 ]]; then
                    log_error "参数错误: --since 需要指定值"
                    exit $ERROR_INVALID_PARAMS
                fi
                SINCE="$2"
                shift 2
                ;;
            --merge)
                MERGE=true
                shift
                ;;
            --validate)
                VALIDATE=true
                shift
                ;;
            --exclude)
                if [[ $# -lt 2 ]]; then
                    log_error "参数错误: --exclude 需要指定值"
                    exit $ERROR_INVALID_PARAMS
                fi
                EXCLUDE_PATTERNS+=("$2")
                shift 2
                ;;
            --clear-cache)
                CLEAR_CACHE=true
                shift
                ;;
            --verbose)
                VERBOSE=true
                shift
                ;;
            --json)
                JSON=true
                shift
                ;;
            --architecture-result)
                if [[ $# -lt 2 ]]; then
                    log_error "参数错误: --architecture-result 需要指定值"
                    exit $ERROR_INVALID_PARAMS
                fi
                ARCHITECTURE_RESULT="$2"
                shift 2
                ;;
            --few-shot-examples)
                if [[ $# -lt 2 ]]; then
                    log_error "参数错误: --few-shot-examples 需要指定值"
                    exit $ERROR_INVALID_PARAMS
                fi
                FEW_SHOT_EXAMPLES="$2"
                shift 2
                ;;
            --interface-list)
                if [[ $# -lt 2 ]]; then
                    log_error "参数错误: --interface-list 需要指定值"
                    exit $ERROR_INVALID_PARAMS
                fi
                INTERFACE_LIST="$2"
                shift 2
                ;;
            --interface-details)
                if [[ $# -lt 2 ]]; then
                    log_error "参数错误: --interface-details 需要指定值"
                    exit $ERROR_INVALID_PARAMS
                fi
                INTERFACE_DETAILS="$2"
                shift 2
                ;;
            --fast-mode)
                FAST_MODE=true
                shift
                ;;
            --smart-mode)
                SMART_MODE=true
                shift
                ;;
            --help|-h)
                HELP=true
                shift
                ;;
            *)
                log_error "未知参数: $1"
                log_error "使用 --help 查看帮助信息"
                exit $ERROR_INVALID_PARAMS
                ;;
        esac
    done

    log_debug "参数解析完成"
}

# 参数验证函数（第一阶段：基础验证框架）
validate_params() {
    # 显示帮助信息
    if [[ "$HELP" == "true" ]]; then
        show_help
        exit 0
    fi

    # 检查必需参数
    if [[ -z "$TARGET" ]]; then
        log_error "参数错误: --target 必须指定"
        log_error "使用 --help 查看帮助信息"
        exit $ERROR_MISSING_REQUIRED_PARAM
    fi

    # 检查范围参数（--path 和 --files 至少指定一个）
    # 例外：如果提供了 --interface-details（文档生成模式）或 --interface-list（验证模式），则不需要路径参数
    if [[ -z "$INTERFACE_DETAILS" && -z "$INTERFACE_LIST" ]]; then
        if [[ -z "$PATHS" && -z "$FILES" ]]; then
            log_error "参数错误: --path 和 --files 至少需要指定一个"
            log_error "使用 --help 查看帮助信息"
            exit $ERROR_MISSING_REQUIRED_PARAM
        fi
    fi

    # 检查参数组合（交互模式）
    if [[ "$INTERACTIVE" == "true" && "$NON_INTERACTIVE" == "true" ]]; then
        log_error "参数错误: --interactive 和 --non-interactive 不能同时使用"
        exit $ERROR_INVALID_PARAM_COMBINATION
    fi

    if [[ "$INTERACTIVE" == "true" && "$YES" == "true" ]]; then
        log_error "参数错误: --interactive 和 --yes 不能同时使用"
        exit $ERROR_INVALID_PARAM_COMBINATION
    fi

    # 检查参数组合（增量反构）
    # 先检查互斥参数
    if [[ -n "$GIT_DIFF" && -n "$SINCE" ]]; then
        log_error "参数错误: --git-diff 和 --since 不能同时指定"
        exit $ERROR_INVALID_PARAM_COMBINATION
    fi

    # 再检查依赖关系
    if [[ "$MERGE" == "true" && "$INCREMENTAL" != "true" ]]; then
        log_error "参数错误: --merge 需要配合 --incremental 使用"
        exit $ERROR_INVALID_PARAM_COMBINATION
    fi

    if [[ -n "$GIT_DIFF" && "$INCREMENTAL" != "true" ]]; then
        log_error "参数错误: --git-diff 需要配合 --incremental 使用"
        exit $ERROR_INVALID_PARAM_COMBINATION
    fi

    if [[ -n "$SINCE" && "$INCREMENTAL" != "true" ]]; then
        log_error "参数错误: --since 需要配合 --incremental 使用"
        exit $ERROR_INVALID_PARAM_COMBINATION
    fi

    # 验证 --target 是否是有效值（从注册表查找）
    if ! is_valid_element_type "$TARGET"; then
        local valid_types
        valid_types=$(get_all_element_types)
        log_error "参数错误: --target '$TARGET' 不是有效的要素类型"
        log_error "支持的要素类型: $valid_types"
        log_error "使用 --help 查看帮助信息"
        exit $ERROR_INVALID_TARGET
    fi

    # 验证 --interface-types 是否是有效类型（仅当 --target interfaces 时）
    if [[ "$TARGET" == "interfaces" && -n "$INTERFACE_TYPES" ]]; then
        # 定义有效的接口类型
        local valid_interface_types=("restful" "message" "module" "cli" "rpc" "function" "other")
        
        # 将逗号分隔的接口类型字符串分割为数组
        IFS=',' read -ra types_array <<< "$INTERFACE_TYPES"
        
        # 验证每个接口类型
        for interface_type in "${types_array[@]}"; do
            # 去除前后空格
            interface_type=$(echo "$interface_type" | xargs)
            
            # 检查是否在有效类型列表中
            local is_valid=false
            for valid_type in "${valid_interface_types[@]}"; do
                if [[ "$interface_type" == "$valid_type" ]]; then
                    is_valid=true
                    break
                fi
            done
            
            if [[ "$is_valid" == "false" ]]; then
                log_error "参数错误: --interface-types 包含无效类型: '$interface_type'"
                log_error "支持的接口类型: ${valid_interface_types[*]}"
                log_error "使用 --help 查看帮助信息"
                exit $ERROR_INVALID_INTERFACE_TYPES
            fi
        done
    fi

    # 验证路径和文件是否存在
    if [[ -n "$PATHS" ]]; then
        # 将逗号分隔的路径字符串分割为数组
        IFS=',' read -ra paths_array <<< "$PATHS"
        
        for path in "${paths_array[@]}"; do
            # 去除前后空格
            path=$(echo "$path" | xargs)
            
            # 将相对路径转换为绝对路径（基于 REPO_ROOT）
            local abs_path
            if ! abs_path=$(normalize_path "$path" "$REPO_ROOT" 2>/dev/null); then
                log_error "参数错误: 无法规范化路径: $path"
                exit $ERROR_INVALID_PARAMS
            fi
            
            # 检查路径是否存在
            if [[ ! -e "$abs_path" ]]; then
                log_error "参数错误: 路径不存在: $path (解析为: $abs_path)"
                log_error "使用 --help 查看帮助信息"
                exit $ERROR_FILE_NOT_FOUND
            fi
            
            # 检查路径是否是目录（如果是目录，应该存在且是目录类型）
            # 注意：这里不强制要求以/结尾，因为用户可能省略
            # 如果路径存在且是目录，则接受；如果是文件，也接受（可能是通配符或单个文件）
        done
    fi

    if [[ -n "$FILES" ]]; then
        # 将逗号分隔的文件字符串分割为数组
        IFS=',' read -ra files_array <<< "$FILES"
        
        for file in "${files_array[@]}"; do
            # 去除前后空格
            file=$(echo "$file" | xargs)
            
            # 将相对路径转换为绝对路径（基于 REPO_ROOT）
            local abs_file
            if ! abs_file=$(normalize_path "$file" "$REPO_ROOT" 2>/dev/null); then
                log_error "参数错误: 无法规范化文件路径: $file"
                exit $ERROR_INVALID_PARAMS
            fi
            
            # 检查文件是否存在
            if [[ ! -f "$abs_file" ]]; then
                log_error "参数错误: 文件不存在: $file (解析为: $abs_file)"
                log_error "使用 --help 查看帮助信息"
                exit $ERROR_FILE_NOT_FOUND
            fi
        done
    fi

    log_debug "参数验证完成"
}

# 检查文件是否匹配模式
# 参数:
#   $1: 文件路径（绝对路径）
#   $2: 模式（支持 glob 模式，如 **/*test*.py）
#   $3: 仓库根目录（用于将绝对路径转换为相对路径进行匹配）
# 返回:
#   匹配: 返回 0
#   不匹配: 返回 1
matches_pattern() {
    local file_path="$1"
    local pattern="$2"
    local repo_root="$3"
    
    # 将绝对路径转换为相对于仓库根目录的路径
    local rel_path="${file_path#$repo_root/}"
    if [[ "$rel_path" == "$file_path" ]]; then
        # 如果无法转换，说明文件不在仓库内，使用完整路径
        rel_path="$file_path"
    fi
    # 确保路径以 / 开头（用于统一处理）
    if [[ "$rel_path" != /* ]] && [[ -n "$rel_path" ]]; then
        rel_path="$rel_path"
    fi
    
    # 处理包含 ** 的模式（递归匹配）
    if [[ "$pattern" == *\*\** ]]; then
        # 将 ** 替换为正则表达式的 .*
        # 先将 ** 替换为占位符
        local pattern_temp="${pattern//\*\*/__STARSTAR__}"
        
        # 转义特殊字符
        pattern_temp="${pattern_temp//\./\\.}"
        pattern_temp="${pattern_temp//\(/\\(}"
        pattern_temp="${pattern_temp//\)/\\)}"
        pattern_temp="${pattern_temp//\[/\\[}"
        pattern_temp="${pattern_temp//\]/\\]}"
        pattern_temp="${pattern_temp//\+/\\+}"
        pattern_temp="${pattern_temp//\^/\\^}"
        pattern_temp="${pattern_temp//\$/\\$}"
        pattern_temp="${pattern_temp//\|/\\|}"
        
        # 将 glob 元字符转换为正则表达式
        pattern_temp="${pattern_temp//\*/[^/]*}"  # * 匹配除 / 外的任意字符
        pattern_temp="${pattern_temp//\?/[^/]}"   # ? 匹配除 / 外的单个字符
        pattern_temp="${pattern_temp//__STARSTAR__/.*}"  # ** 匹配任意字符（包括 /）
        
        # 使用正则表达式匹配
        if [[ "$rel_path" =~ ^${pattern_temp}$ ]]; then
            return 0
        fi
    else
        # 简单模式匹配（不含 **），使用 bash 的 case 语句
        case "$rel_path" in
            $pattern)
                return 0
                ;;
        esac
    fi
    
    return 1
}

# 文件过滤函数
# 参数:
#   $1: 文件列表（每行一个文件路径，绝对路径）
#   $2: 排除模式数组变量名（如 "EXCLUDE_PATTERNS"）
#   $3: 仓库根目录
# 返回:
#   输出过滤后的文件列表（每行一个文件路径）
filter_files() {
    local files_input="$1"
    local exclude_patterns_var="$2"
    local repo_root="$3"
    
    # 默认排除规则
    local default_exclude_patterns=(
        "**/__pycache__/**"
        "**/node_modules/**"
        "**/target/**"
        "**/build/**"
        "**/.git/**"
    )
    
    # 获取排除模式数组（使用间接引用）
    local exclude_patterns_ref="${exclude_patterns_var}[@]"
    local exclude_array
    eval "exclude_array=(\"\${$exclude_patterns_ref}\")"
    
    # 检查是否是 git 仓库
    local has_git=false
    if has_git 2>/dev/null; then
        has_git=true
    fi
    
    # 读取文件列表并过滤
    while IFS= read -r file_path; do
        [[ -z "$file_path" ]] && continue
        
        local should_exclude=false
        
        # 优先级 1: 检查 .gitignore（最高优先级）
        if [[ "$has_git" == "true" ]]; then
            if git check-ignore -q "$file_path" 2>/dev/null; then
                log_debug "文件被 .gitignore 排除: $file_path"
                should_exclude=true
            fi
        fi
        
        # 优先级 2: 检查默认排除规则
        if [[ "$should_exclude" == "false" ]]; then
            for pattern in "${default_exclude_patterns[@]}"; do
                if matches_pattern "$file_path" "$pattern" "$repo_root"; then
                    log_debug "文件被默认排除规则排除: $file_path (模式: $pattern)"
                    should_exclude=true
                    break
                fi
            done
        fi
        
        # 优先级 3: 检查 --exclude 参数指定的规则
        if [[ "$should_exclude" == "false" ]]; then
            for pattern in "${exclude_array[@]}"; do
                [[ -z "$pattern" ]] && continue
                if matches_pattern "$file_path" "$pattern" "$repo_root"; then
                    log_debug "文件被 --exclude 规则排除: $file_path (模式: $pattern)"
                    should_exclude=true
                    break
                fi
            done
        fi
        
        # 如果文件未被排除，输出
        if [[ "$should_exclude" == "false" ]]; then
            echo "$file_path"
        fi
    done <<< "$files_input"
}

# 范围解析函数
# 参数:
#   $1: PATHS 字符串（逗号分隔的路径列表）
#   $2: FILES 字符串（逗号分隔的文件列表）
#   $3: REPO_ROOT（仓库根目录）
# 返回:
#   通过全局变量设置：
#   - RESOLVED_PATHS: 数组，包含所有规范化的路径（绝对路径）
#   - RESOLVED_FILES: 数组，包含所有规范化的文件路径（绝对路径）
#   函数返回 0 表示成功，非 0 表示失败
resolve_scope() {
    local paths_str="$1"
    local files_str="$2"
    local repo_root="$3"
    
    # 初始化结果数组
    RESOLVED_PATHS=()
    RESOLVED_FILES=()
    
    # 处理 --path 参数
    if [[ -n "$paths_str" ]]; then
        # 将逗号分隔的路径字符串分割为数组
        IFS=',' read -ra paths_array <<< "$paths_str"
        
        for path in "${paths_array[@]}"; do
            # 去除前后空格
            path=$(echo "$path" | xargs)
            [[ -z "$path" ]] && continue
            
            # 将相对路径转换为绝对路径（基于 REPO_ROOT）
            local abs_path
            if ! abs_path=$(normalize_path "$path" "$repo_root" 2>/dev/null); then
                log_error "无法规范化路径: $path"
                return 1
            fi
            
            # 验证路径是否存在（在 validate_params 中已验证，这里再次确认）
            if [[ ! -e "$abs_path" ]]; then
                log_error "路径不存在: $path (解析为: $abs_path)"
                return 1
            fi
            
            # 添加到结果数组
            RESOLVED_PATHS+=("$abs_path")
        done
    fi
    
    # 处理 --files 参数
    if [[ -n "$files_str" ]]; then
        # 将逗号分隔的文件字符串分割为数组
        IFS=',' read -ra files_array <<< "$files_str"
        
        for file in "${files_array[@]}"; do
            # 去除前后空格
            file=$(echo "$file" | xargs)
            [[ -z "$file" ]] && continue
            
            # 将相对路径转换为绝对路径（基于 REPO_ROOT）
            local abs_file
            if ! abs_file=$(normalize_path "$file" "$repo_root" 2>/dev/null); then
                log_error "无法规范化文件路径: $file"
                return 1
            fi
            
            # 验证文件是否存在（在 validate_params 中已验证，这里再次确认）
            if [[ ! -f "$abs_file" ]]; then
                log_error "文件不存在: $file (解析为: $abs_file)"
                return 1
            fi
            
            # 添加到结果数组
            RESOLVED_FILES+=("$abs_file")
        done
    fi
    
    log_debug "范围解析完成: ${#RESOLVED_PATHS[@]} 个路径, ${#RESOLVED_FILES[@]} 个文件"
    return 0
}

get_cache_dir() {
    local repo_root="$1"
    local target="$2"
    
    # 支持通过环境变量指定缓存目录
    if [[ -n "${REVERSE_CACHE_DIR:-}" ]]; then
        local cache_dir
        if ! cache_dir=$(normalize_path "$REVERSE_CACHE_DIR" "$repo_root" 2>/dev/null); then
            log_warn "无法规范化环境变量 REVERSE_CACHE_DIR: $REVERSE_CACHE_DIR，使用默认路径"
            # 获取缓存目录路径
            # 支持通过环境变量指定缓存目录
            if [[ -n "${REVERSE_CACHE_DIR:-}" ]]; then
                local cache_dir
                if ! cache_dir=$(normalize_path "$REVERSE_CACHE_DIR" "$repo_root" 2>/dev/null); then
                    log_warn "无法规范化环境变量 REVERSE_CACHE_DIR: $REVERSE_CACHE_DIR，使用默认路径"
                else
                    echo "$cache_dir"
                fi
            else
                # 默认缓存路径构造：仓库根目录/.reverse/cache/目标要素类型
                echo "${repo_root}/.reverse/cache/${target}"
            fi
        fi
        else
            echo "$cache_dir"
        fi
    else
        echo "${repo_root}/.cache/reverse/${target}"
    fi
}

# 初始化缓存目录
# 参数:
#   $1: 缓存目录路径（绝对路径）
# 返回:
#   0: 成功
#   1: 失败
init_cache_dir() {
    local cache_dir="$1"
    
    if [[ -z "$cache_dir" ]]; then
        log_error "缓存目录路径为空"
        return 1
    fi
    
    # 创建缓存目录（如果不存在）
    if [[ ! -d "$cache_dir" ]]; then
        if ! mkdir -p "$cache_dir" 2>/dev/null; then
            log_error "无法创建缓存目录: $cache_dir"
            return 1
        fi
        log_debug "已创建缓存目录: $cache_dir"
    fi
    
    return 0
}

# 获取缓存状态文件路径
# 参数:
#   $1: 缓存目录路径
# 返回:
#   输出缓存状态文件路径
get_cache_status_file() {
    local cache_dir="$1"
    echo "${cache_dir}/.cache-status.json"
}

# 读取缓存状态
# 参数:
#   $1: 缓存状态文件路径
#   $2: 阶段名称（如 architecture_identification, few_shot_examples 等）
# 返回:
#   0: 已确认
#   1: 未确认或不存在
#   输出: 时间戳（如果存在）
read_cache_status() {
    local status_file="$1"
    local stage="$2"
    
    if [[ ! -f "$status_file" ]]; then
        return 1
    fi
    
    # 检查是否有 jq 工具
    if ! command -v jq >/dev/null 2>&1; then
        log_warn "未检测到 jq 工具，无法读取缓存状态，假设未确认"
        return 1
    fi
    
    # 读取确认状态
    local confirmed
    confirmed=$(jq -r ".${stage}.confirmed // false" "$status_file" 2>/dev/null)
    
    if [[ "$confirmed" == "true" ]]; then
        # 输出时间戳
        jq -r ".${stage}.timestamp // \"\"" "$status_file" 2>/dev/null
        return 0
    else
        return 1
    fi
}

# 更新缓存状态
# 参数:
#   $1: 缓存状态文件路径
#   $2: 阶段名称
#   $3: 确认状态（true/false）
# 返回:
#   0: 成功
#   1: 失败
update_cache_status() {
    local status_file="$1"
    local stage="$2"
    local confirmed="$3"
    local timestamp
    
    # 生成时间戳
    if command -v date >/dev/null 2>&1; then
        timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null)
    else
        timestamp=""
    fi
    
    # 检查是否有 jq 工具
    if ! command -v jq >/dev/null 2>&1; then
        log_warn "未检测到 jq 工具，无法更新缓存状态"
        return 1
    fi
    
    # 读取现有状态（如果存在）
    local status_json
    if [[ -f "$status_file" ]]; then
        status_json=$(cat "$status_file" 2>/dev/null)
    else
        status_json="{}"
    fi
    
    # 更新状态
    local updated_json
    if [[ "$confirmed" == "true" ]]; then
        updated_json=$(echo "$status_json" | jq --arg stage "$stage" --arg ts "$timestamp" \
            ". + {(\$stage): {confirmed: true, timestamp: \$ts}}" 2>/dev/null)
    else
        updated_json=$(echo "$status_json" | jq --arg stage "$stage" \
            ". + {(\$stage): {confirmed: false, timestamp: null}}" 2>/dev/null)
    fi
    
    if [[ -z "$updated_json" ]]; then
        log_error "无法更新缓存状态"
        return 1
    fi
    
    # 写入文件
    echo "$updated_json" > "$status_file" 2>/dev/null
    if [[ $? -ne 0 ]]; then
        log_error "无法写入缓存状态文件: $status_file"
        return 1
    fi
    
    log_debug "已更新缓存状态: $stage = $confirmed"
    return 0
}

# 检查缓存文件是否存在且已确认
# 参数:
#   $1: 缓存文件路径
#   $2: 缓存状态文件路径
#   $3: 阶段名称
# 返回:
#   0: 缓存存在且已确认
#   1: 缓存不存在或未确认
check_cache() {
    local cache_file="$1"
    local status_file="$2"
    local stage="$3"
    
    # 检查缓存文件是否存在
    if [[ ! -f "$cache_file" ]]; then
        log_debug "缓存文件不存在: $cache_file"
        return 1
    fi
    
    # 检查缓存状态
    if read_cache_status "$status_file" "$stage" >/dev/null 2>&1; then
        log_debug "缓存文件存在且已确认: $cache_file"
        return 0
    else
        log_debug "缓存文件存在但未确认: $cache_file"
        return 1
    fi
}

# 清理缓存
# 参数:
#   $1: 缓存目录路径
# 返回:
#   0: 成功
#   1: 失败
clear_cache() {
    local cache_dir="$1"
    
    if [[ -z "$cache_dir" ]]; then
        log_error "缓存目录路径为空"
        return 1
    fi
    
    if [[ ! -d "$cache_dir" ]]; then
        log_info "缓存目录不存在，无需清理: $cache_dir"
        return 0
    fi
    
    log_info "清理缓存目录: $cache_dir"
    
    # 删除缓存目录下的所有文件（保留目录结构）
    if ! rm -rf "${cache_dir}"/* "${cache_dir}"/.cache-status.json 2>/dev/null; then
        log_error "无法清理缓存目录: $cache_dir"
        return 1
    fi
    
    log_success "缓存已清理"
    return 0
}

dispatch_element_type() {
    local target="$1"
    local repo_root="$2"
    local script_dir="$3"
    
    # 从注册表获取要素类型信息
    local element_info
    if ! element_info=$(get_element_type_info "$target"); then
        local valid_types
        valid_types=$(get_all_element_types)
        log_error "不支持的要素类型: $target"
        log_error "支持的要素类型: $valid_types"
        exit $ERROR_INVALID_TARGET
    fi
    
    # 解析要素类型信息
    IFS='|' read -r name scanner analyzer validator merger template output_dir <<< "$element_info"
    
    # 设置全局变量
    ELEMENT_NAME="$name"
    ELEMENT_SCANNER="$scanner"
    ELEMENT_ANALYZER="$analyzer"
    ELEMENT_VALIDATOR="${validator:-null}"
    ELEMENT_MERGER="${merger:-null}"
    ELEMENT_TEMPLATE="$template"
    ELEMENT_OUTPUT_DIR="$output_dir"
    ELEMENT_DIR="$script_dir/reverse/$target"
    
    # 加载接口辅助函数模块（如果目标要素类型是interfaces）
    if [[ "$target" == "interfaces" ]] && [[ "$INTERFACE_HELPERS_LOADED" != "true" ]]; then
        local interface_helpers_module="$script_dir/reverse/interfaces/utils/interface-helpers.sh"
        if [[ -f "$interface_helpers_module" ]]; then
            source "$interface_helpers_module"
            INTERFACE_HELPERS_LOADED=true
            log_debug "已加载接口辅助函数模块: $interface_helpers_module"
        else
            log_warn "接口辅助函数模块不存在: $interface_helpers_module"
            log_warn "某些接口相关功能可能不可用"
        fi
    fi
    
    # 初始化缓存目录
    CACHE_DIR=$(get_cache_dir "$repo_root" "$target")
    CACHE_STATUS_FILE=$(get_cache_status_file "$CACHE_DIR")
    
    if ! init_cache_dir "$CACHE_DIR"; then
        log_error "无法初始化缓存目录"
        return 1
    fi
    
    log_debug "缓存目录: $CACHE_DIR"

    # 验证要素类型模块目录是否存在
    if [[ ! -d "$ELEMENT_DIR" ]]; then
        log_warn "要素类型模块目录不存在: $ELEMENT_DIR"
        log_info "提示：模块将在后续任务中创建（T017-T019）"
        # 第一阶段：不强制要求模块存在，允许框架模式运行
        # exit $ERROR_DEPENDENCY_MISSING
    fi

    # 加载扫描函数模块
    local scan_module=""
    if [[ -n "$ELEMENT_DIR" && -n "$target" ]]; then
        scan_module="$ELEMENT_DIR/scan-${target}.sh"
    fi
    if [[ -f "$scan_module" ]]; then
        source "$scan_module"
        if ! type "$scanner" &>/dev/null; then
            log_warn "扫描函数不存在: $scanner (在模块 $scan_module 中)"
            log_info "提示：扫描函数将在后续任务中实现（T017）"
        else
            log_debug "已加载扫描模块: $scan_module"
        fi
    else
        log_warn "扫描模块不存在: $scan_module (将在后续任务中实现，T017)"
    fi
    
    # 加载分析函数模块
    local analyze_module="$ELEMENT_DIR/analyze-${target}.sh"
    if [[ -f "$analyze_module" ]]; then
        source "$analyze_module"
        if ! type "$analyzer" &>/dev/null; then
            log_warn "分析函数不存在: $analyzer (在模块 $analyze_module 中)"
            log_info "提示：分析函数将在后续任务中实现（T018）"
        else
            log_debug "已加载分析模块: $analyze_module"
        fi
    else
        log_warn "分析模块不存在: $analyze_module (将在后续任务中实现，T018)"
    fi
    
    # 加载验证函数模块（如果存在且启用验证）
    if [[ "$VALIDATE" == "true" ]] && [[ -n "$validator" ]] && [[ "$validator" != "null" ]]; then
        local validate_module="$ELEMENT_DIR/validate-${target}.sh"
        if [[ -f "$validate_module" ]]; then
            source "$validate_module"
            if ! type "$validator" &>/dev/null; then
                log_warn "验证函数不存在: $validator (在模块 $validate_module 中)"
            else
                log_debug "已加载验证模块: $validate_module"
            fi
        else
            log_warn "验证模块不存在: $validate_module (将在后续任务中实现)"
        fi
    fi
    
    # 加载合并函数模块（如果启用增量合并）
    if [[ "$INCREMENTAL" == "true" ]] && [[ "$MERGE" == "true" ]] && [[ -n "$merger" ]] && [[ "$merger" != "null" ]]; then
        local merge_module="$ELEMENT_DIR/merge-${target}.sh"
        if [[ -f "$merge_module" ]]; then
            source "$merge_module"
            if ! type "$merger" &>/dev/null; then
                log_warn "合并函数不存在: $merger (在模块 $merge_module 中)"
            else
                log_debug "已加载合并模块: $merge_module"
            fi
        else
            log_warn "合并模块不存在: $merge_module (将在后续任务中实现)"
        fi
    fi
    
    log_debug "要素类型分发完成: $name ($target)"
    return 0
}

find_template() {
    local user_template="$1"
    local template_filename="$2"
    local repo_root="$3"
    local script_dir="$4"
    
    local searched_paths=()
    
    # 1. 用户指定的模板（优先级最高）
    if [[ -n "$user_template" ]]; then
        local abs_template
        if abs_template=$(normalize_path "$user_template" "$repo_root" 2>/dev/null); then
            searched_paths+=("$abs_template")
            if [[ -f "$abs_template" ]]; then
                echo "$abs_template"
                return 0
            fi
        else
            searched_paths+=("$user_template")
        fi
    fi
    
    # 2. 项目自定义模板
    local project_template="${repo_root}/.infra/templates/${template_filename}"
    searched_paths+=("$project_template")
    if [[ -f "$project_template" ]]; then
        echo "$project_template"
        return 0
    fi
    
    # 3. 系统默认模板（相对于脚本位置）
    local system_template="${script_dir}/../../templates/${template_filename}"
    # 转换为绝对路径
    if [[ -d "$script_dir" ]]; then
        system_template=$(cd "$script_dir/../../templates" 2>/dev/null && pwd)/"${template_filename}"
    fi
    searched_paths+=("$system_template")
    if [[ -f "$system_template" ]]; then
        echo "$system_template"
        return 0
    fi
    
    # 所有模板都找不到，报错
    log_error "模板文件未找到: $template_filename"
    log_error "已查找的路径："
    for path in "${searched_paths[@]}"; do
        log_error "  - $path"
    done
    log_error "请使用 --template 参数指定模板文件路径"
    return $ERROR_TEMPLATE_NOT_FOUND
}

if [[ $# -gt 0 ]]; then
    case "${1:-}" in
        --load-few-shot-template)
            if [[ $# -lt 2 ]]; then
                log_error "参数错误: --load-few-shot-template 需要指定仓库根目录"
                exit $ERROR_INVALID_PARAMS
            fi
            load_few_shot_template "$2"
            exit $?
            ;;
        --extract-identification-rules)
            if [[ $# -lt 3 ]]; then
                log_error "参数错误: --extract-identification-rules 需要指定模板文件和接口类型"
                exit $ERROR_INVALID_PARAMS
            fi
            extract_identification_rules "$2" "$3"
            exit $?
            ;;
        --extract-constraints)
            if [[ $# -lt 3 ]]; then
                log_error "参数错误: --extract-constraints 需要指定模板文件和接口类型"
                exit $ERROR_INVALID_PARAMS
            fi
            extract_constraints "$2" "$3"
            exit $?
            ;;
        --extract-format-definition)
            if [[ $# -lt 2 ]]; then
                log_error "参数错误: --extract-format-definition 需要指定模板文件"
                exit $ERROR_INVALID_PARAMS
            fi
            extract_format_definition "$2"
            exit $?
            ;;
        --extract-interface-types)
            if [[ $# -lt 2 ]]; then
                log_error "参数错误: --extract-interface-types 需要指定模板文件"
                exit $ERROR_INVALID_PARAMS
            fi
            extract_interface_types "$2"
            exit $?
            ;;
        --format-rules-for-prompt)
            if [[ $# -lt 3 ]]; then
                log_error "参数错误: --format-rules-for-prompt 需要指定规则 JSON、接口类型和约束规则（可选）"
                exit $ERROR_INVALID_PARAMS
            fi
            format_rules_for_prompt "$2" "$3" "${4:-[]}" "${5:-[]}"
            exit $?
            ;;
    esac
fi

# 主函数（第一阶段：基础框架）
main() {
    log_info "开始 reverse 命令执行..."

    # 解析参数
    parse_args "$@"

    # 验证参数
    validate_params

    # 检查依赖工具（在参数验证之后，避免在显示帮助时也检查）
    if [[ "$HELP" != "true" ]]; then
        if ! check_dependencies; then
            exit $ERROR_DEPENDENCY_MISSING
        fi
    fi

    # 解析范围
    if ! resolve_scope "$PATHS" "$FILES" "$REPO_ROOT"; then
        log_error "范围解析失败"
        exit $ERROR_INVALID_PARAMS
    fi

    # 要素类型分发
    if ! dispatch_element_type "$TARGET" "$REPO_ROOT" "$SCRIPT_DIR"; then
        log_error "要素类型分发失败"
        exit $ERROR_INVALID_TARGET
    fi

    # 处理清理缓存请求
    if [[ "$CLEAR_CACHE" == "true" ]]; then
        if ! clear_cache "$CACHE_DIR"; then
            log_error "清理缓存失败"
            exit $ERROR_CACHE_ERROR
        fi
        log_success "缓存已清理"
        return 0
    fi

    # 检查是否提供了 AI 分析结果（用于文档生成模式）
    if [[ -n "$INTERFACE_DETAILS" ]]; then
        log_info "检测到接口详细信息文件，进入文档生成模式"
        
        # 验证文件存在
        if [[ ! -f "$INTERFACE_DETAILS" ]]; then
            log_error "错误: 接口详细信息文件不存在: $INTERFACE_DETAILS"
            exit $ERROR_FILE_NOT_FOUND
        fi
        
        # 如果启用验证，先执行规则验证
        if [[ "$VALIDATE" == "true" ]]; then
            log_info "执行规则验证..."
            if ! validate_interface_list "$INTERFACE_DETAILS"; then
                log_error "规则验证失败，停止文档生成"
                exit $ERROR_ANALYSIS_FAILED
            fi
        fi
        
        # 生成文档
        log_info "开始生成接口清单文档..."
        if ! generate_interface_document "$INTERFACE_DETAILS" "$TEMPLATE" "$OUTPUT_DIR"; then
            log_error "文档生成失败"
            exit $ERROR_OUTPUT_FAILED
        fi
        
        log_success "命令执行完成（文档生成模式）"
        return 0
    fi
    
    # 如果提供了接口清单且启用验证，执行规则验证
    if [[ -n "$INTERFACE_LIST" ]] && [[ "$VALIDATE" == "true" ]]; then
        log_info "执行接口清单规则验证..."
        if ! validate_interface_list "$INTERFACE_LIST"; then
            log_error "规则验证失败"
            exit $ERROR_ANALYSIS_FAILED
        fi
        log_success "规则验证完成"
        return 0
    fi
    
    # 检查是否在 AI Agent 环境中或缓存目录存在
    local is_ai_mode=false
    if is_ai_agent_environment; then
        is_ai_mode=true
    elif [[ -d "$CACHE_DIR" ]]; then
        # 如果缓存目录存在，说明 AI Agent 可能正在执行
        is_ai_mode=true
    fi
    
    log_info "目标要素类型: $ELEMENT_NAME ($TARGET)"
    log_info "扫描路径: ${#RESOLVED_PATHS[@]} 个路径"
    log_info "扫描文件: ${#RESOLVED_FILES[@]} 个文件"
    
    if [[ "$is_ai_mode" == "true" ]]; then
        # AI Agent 模式：显示简洁的信息，不显示误导性警告
        log_info ""
        log_info "提示：在 AI Agent 环境中，AI Agent 会执行分析任务"
        log_info "脚本已准备好接收 AI 分析结果"
        log_info ""
        log_info "脚本支持接收以下 AI 分析结果："
        log_info "  --architecture-result <file>   架构识别结果"
        log_info "  --few-shot-examples <file>      Few-shot 示例"
        log_info "  --interface-list <file>          接口清单"
        log_info "  --interface-details <file>       接口详细信息"
        log_success "命令执行完成（AI Agent 模式）"
    else
        # 非 AI Agent 模式：显示完整信息
        log_warn "警告：这是第一阶段的基础框架，具体功能将在后续任务中实现"
        log_info "功能开发进度请参考任务清单：infra/design/omni_reverse_tasks.md"
        log_info ""
        log_info "提示：在 AI Agent 环境中，AI Agent 会执行分析任务并传递结果给脚本"
        log_info "脚本接收 AI 分析结果的方式："
        log_info "  --architecture-result <file>   架构识别结果"
        log_info "  --few-shot-examples <file>      Few-shot 示例"
        log_info "  --interface-list <file>          接口清单"
        log_info "  --interface-details <file>       接口详细信息"
        log_success "命令执行完成（框架模式）"
    fi
}

# 获取确认模式
# 返回: 确认模式字符串
get_confirmation_mode() {
    if [[ "$FAST_MODE" == "true" ]]; then
        echo "fast"
    elif [[ "$SMART_MODE" == "true" ]]; then
        echo "smart"
    else
        echo "normal"
    fi
}

# 智能确认处理
# 参数: 结果文件, 置信度阈值
# 返回: 0表示确认，1表示拒绝
smart_confirmation() {
    local results_file="$1"
    local confidence_threshold="${2:-70}"
    local mode=$(get_confirmation_mode)

    case "$mode" in
        "fast")
            # 快速模式，自动确认所有结果
            log_info "快速模式：自动确认所有结果"
            return 0
            ;;
        "smart")
            # 智能模式，仅确认低置信度结果
            log_info "智能模式：仅确认置信度低于${confidence_threshold}的结果"
            # 这里应该实现智能确认逻辑
            # 暂时返回0表示确认
            return 0
            ;;
        *)
            # 标准模式，需要用户确认
            log_info "标准模式：需要用户确认"
            # 这里应该实现标准确认逻辑
            # 暂时返回0表示确认
            return 0
            ;;
    esac
}

# 执行主函数
main "$@"

