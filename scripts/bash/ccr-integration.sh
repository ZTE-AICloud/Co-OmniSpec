#!/bin/bash

################################################################################
# 命令自动执行与输出验证脚本
#
# 功能: 自动按序执行 ccr 集成命令集,每个命令执行后检查预期的输出文件
#       是否存在,如不存在则自动重试(最多3次),并记录详细的执行日志
#
# 版本: 1.0.0
# 作者: OmniSpec Team
# 创建日期: 2025-12-26
# 许可证: MIT
#
# 要求:
#   - Bash 4.0+ (需要关联数组支持)
#   - ccr 命令行工具
#   - 标准 Unix 工具: date, tee, sleep, awk
#
# 使用方法:
#   ./ccr-integration.sh [OPTIONS]
#
# 选项:
#   --help              显示帮助信息
#   --version           显示版本信息
#   --dry-run           模拟执行模式
#   --max-retries N     设置最大重试次数(默认: 3)
#   --retry-delay N     设置重试延迟秒数(默认: 5)
#   --quiet             静默模式
#   --verbose           详细输出模式
#
################################################################################

# Bash 版本检查
if ((BASH_VERSINFO[0] < 4)); then
    echo "错误: 此脚本需要 Bash 4.0 或更高版本" >&2
    echo "当前版本: $BASH_VERSION" >&2
    exit 5
fi

# 严格模式设置
set -u          # 检测未定义变量
set -o pipefail # 管道命令失败检测

################################################################################
# 全局常量定义
################################################################################

readonly SCRIPT_VERSION="1.0.0"
readonly SCRIPT_NAME="命令自动执行脚本"

# 默认配置
MAX_RETRIES=3
RETRY_DELAY=5
DRY_RUN=false
QUIET_MODE=false
VERBOSE_MODE=false
START_FROM=1

################################################################################
# 帮助和版本信息函数
################################################################################

# 显示帮助信息
print_help() {
    cat << EOF
$SCRIPT_NAME v$SCRIPT_VERSION

用法: $0 [选项]

功能: 自动按序执行 ccr 集成命令集,检查输出文件,失败时自动重试

选项:
  -h, --help              显示此帮助信息并退出
  -v, --version           显示版本信息并退出
  -d, --dry-run           模拟执行模式,不实际运行命令
  -r, --max-retries N     设置最大重试次数 (默认: 3, 范围: 0-10)
  -t, --retry-delay N     设置重试延迟秒数 (默认: 5, 范围: 0-300)
  -l, --log-file PATH     指定日志文件路径
  -s, --start-from N      从第 N 个命令开始执行 (默认: 1)
  -q, --quiet             静默模式,只输出错误信息
  --verbose               详细输出模式,显示所有日志

环境变量:
  AUTO_RETRY_MAX_RETRIES  最大重试次数
  AUTO_RETRY_DELAY        重试延迟秒数
  AUTO_RETRY_LOG_LEVEL    日志级别 (DEBUG/INFO/WARN/ERROR)
  AUTO_RETRY_LOG_DIR      日志文件保存目录

示例:
  $0                                    # 使用默认配置运行
  $0 --max-retries 5 --retry-delay 10   # 自定义重试参数
  $0 --dry-run                          # 模拟执行
  $0 --start-from 3                     # 从第3个命令开始
  $0 --quiet                            # 静默模式

退出码:
  0   所有命令执行成功
  1   部分命令失败
  2   所有命令失败
  3   配置错误
  5   依赖错误 (ccr命令不存在)
  130 用户中断 (Ctrl+C)

文档: 详见 README.md 和 changes/ 目录

EOF
}

# 显示版本信息
print_version() {
    cat << EOF
$SCRIPT_NAME v$SCRIPT_VERSION
Bash 版本要求: 4.0+
作者: Auto Retry Commands Team
许可证: MIT
创建日期: 2025-12-26
EOF
}

################################################################################
# 参数解析函数
################################################################################

# 解析命令行参数
parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -h|--help)
                print_help
                exit 0
                ;;
            -v|--version)
                print_version
                exit 0
                ;;
            -d|--dry-run)
                DRY_RUN=true
                shift
                ;;
            -q|--quiet)
                QUIET_MODE=true
                LOG_LEVEL="ERROR"
                shift
                ;;
            --verbose)
                VERBOSE_MODE=true
                LOG_LEVEL="DEBUG"
                shift
                ;;
            -r|--max-retries)
                if [[ -z "$2" ]] || ! [[ "$2" =~ ^[0-9]+$ ]]; then
                    echo "错误: --max-retries 需要一个数字参数" >&2
                    exit 3
                fi
                if [[ "$2" -lt 0 ]] || [[ "$2" -gt 10 ]]; then
                    echo "错误: --max-retries 必须在 0-10 范围内" >&2
                    exit 3
                fi
                MAX_RETRIES="$2"
                shift 2
                ;;
            -t|--retry-delay)
                if [[ -z "$2" ]] || ! [[ "$2" =~ ^[0-9]+$ ]]; then
                    echo "错误: --retry-delay 需要一个数字参数" >&2
                    exit 3
                fi
                if [[ "$2" -lt 0 ]] || [[ "$2" -gt 300 ]]; then
                    echo "错误: --retry-delay 必须在 0-300 范围内" >&2
                    exit 3
                fi
                RETRY_DELAY="$2"
                shift 2
                ;;
            -l|--log-file)
                if [[ -z "$2" ]]; then
                    echo "错误: --log-file 需要一个路径参数" >&2
                    exit 3
                fi
                LOG_FILE="$2"
                shift 2
                ;;
            -s|--start-from)
                if [[ -z "$2" ]] || ! [[ "$2" =~ ^[0-9]+$ ]]; then
                    echo "错误: --start-from 需要一个数字参数" >&2
                    exit 3
                fi
                if [[ "$2" -lt 1 ]]; then
                    echo "错误: --start-from 必须大于等于 1" >&2
                    exit 3
                fi
                START_FROM="$2"
                shift 2
                ;;
            *)
                echo "错误: 未知选项 '$1'" >&2
                echo "使用 --help 查看帮助信息" >&2
                exit 3
                ;;
        esac
    done
    
    # 从环境变量读取配置 (如果未通过参数设置)
    if [[ -n "${AUTO_RETRY_MAX_RETRIES:-}" ]]; then
        MAX_RETRIES="${AUTO_RETRY_MAX_RETRIES}"
    fi
    
    if [[ -n "${AUTO_RETRY_DELAY:-}" ]]; then
        RETRY_DELAY="${AUTO_RETRY_DELAY}"
    fi
}

################################################################################
# 信号处理和清理函数
################################################################################

# 优雅退出标志
INTERRUPTED=false

# 信号处理函数 - 处理Ctrl+C
handle_interrupt() {
    echo ""
    log "收到中断信号,等待当前命令完成..." "WARN"
    INTERRUPTED=true
}

# 清理函数
cleanup() {
    if [[ "$INTERRUPTED" == true ]]; then
        log "脚本被用户中断" "WARN"
        
        # 计算总命令数
        local total_commands=${#COMMANDS[@]}
        
        # 输出部分执行摘要
        echo ""
        echo "========================================"
        echo "执行中断 (已完成 $((SUCCESS_COUNT + FAILURE_COUNT))/$total_commands 命令)"
        echo "========================================"
        echo "成功:       $SUCCESS_COUNT"
        echo "失败:       $FAILURE_COUNT"
        echo "未执行:     $((total_commands - SUCCESS_COUNT - FAILURE_COUNT))"
        echo "日志文件:   $LOG_FILE"
        echo "========================================"
        
        exit 130
    fi
}

# 设置信号处理
trap handle_interrupt SIGINT SIGTERM
trap cleanup EXIT

################################################################################
# 命令配置数组
################################################################################

# 定义ccr集成命令集
COMMANDS=(
    # "ccr code --dangerously-skip-permissions -p /constitution"
    "ccr code --dangerously-skip-permissions -p \"/specify @requirement.md\""
    "ccr code --dangerously-skip-permissions -p \"/clarify 不要询问，使用默认建议\""
    "ccr code --dangerously-skip-permissions -p /design"
    "ccr code --dangerously-skip-permissions -p /tasks"
    "ccr code --dangerously-skip-permissions -p \"/analyze 不要询问，按照建议修复问题\""
    "ccr code --dangerously-skip-permissions -p /implement"
    "ccr code --dangerously-skip-permissions -p /checklist"
)

# 定义每个命令对应的输出文件 (使用关联数组,键为命令,值为输出文件配置)
# 使用 | 分隔多个文件,空字符串表示无需检查
declare -A OUTPUT_FILES
# OUTPUT_FILES["ccr code --dangerously-skip-permissions -p /constitution"]=""
OUTPUT_FILES["ccr code --dangerously-skip-permissions -p \"/specify @requirement.md\""]="changes/001-*/spec.md"
OUTPUT_FILES["ccr code --dangerously-skip-permissions -p \"/clarify 不要询问，使用默认建议\""]=""
OUTPUT_FILES["ccr code --dangerously-skip-permissions -p /design"]="changes/001-*/design.md|changes/001-*/data-model.md|changes/001-*/quickstart.md|changes/001-*/research.md"
OUTPUT_FILES["ccr code --dangerously-skip-permissions -p /tasks"]="changes/001-*/tasks.md"
OUTPUT_FILES["ccr code --dangerously-skip-permissions -p \"/analyze 不要询问，按照建议修复问题\""]=""
OUTPUT_FILES["ccr code --dangerously-skip-permissions -p /implement"]=""
OUTPUT_FILES["ccr code --dangerously-skip-permissions -p /checklist"]=""

################################################################################
# 全局变量和关联数组
################################################################################

# 执行状态关联数组
declare -A EXEC_STATUS       # 命令ID -> 执行状态
declare -A EXEC_RETRIES      # 命令ID -> 重试次数
declare -A EXEC_START_TIME   # 命令ID -> 开始时间戳
declare -A EXEC_END_TIME     # 命令ID -> 结束时间戳

# 全局统计变量
SUCCESS_COUNT=0
FAILURE_COUNT=0
TOTAL_RETRIES=0
SCRIPT_START_TIME=$(date +%s)

# 日志文件
LOG_FILE="command_execution_$(date +%Y%m%d_%H%M%S).log"

# 日志级别配置
LOG_LEVEL="${AUTO_RETRY_LOG_LEVEL:-INFO}"  # 默认INFO级别

################################################################################
# 增强的日志函数
################################################################################

# 日志级别优先级
declare -A LOG_LEVEL_PRIORITY=(
    ["DEBUG"]=0
    ["INFO"]=1
    ["WARN"]=2
    ["ERROR"]=3
)

# 判断日志级别是否应该输出
should_log() {
    local level="$1"
    local current_priority=${LOG_LEVEL_PRIORITY[$LOG_LEVEL]:-1}
    local message_priority=${LOG_LEVEL_PRIORITY[$level]:-1}
    
    [[ $message_priority -ge $current_priority ]]
}

# 增强的日志函数 - 支持日志级别
# 参数:
#   $1: 消息内容
#   $2: 日志级别 (可选,默认INFO: DEBUG/INFO/WARN/ERROR)
#   $3: 命令ID (可选,默认N/A)
log() {
    local message="$1"
    local level="${2:-INFO}"
    local cmd_id="${3:-N/A}"
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    local log_line="[$timestamp] [$level] [CMD-$cmd_id] $message"
    
    # 写入日志文件 (所有级别都写入)
    echo "$log_line" >> "$LOG_FILE"
    
    # 根据日志级别决定是否输出到控制台
    if should_log "$level"; then
        echo "$log_line"
    fi
}

# 命令专用日志函数 - 记录命令相关的详细信息
# 参数:
#   $1: 命令ID
#   $2: 事件类型 (start/success/failure/retry)
#   $3: 额外信息
log_command() {
    local cmd_id="$1"
    local event="$2"
    local extra="${3:-}"
    
    case "$event" in
        start)
            log "开始执行命令" "INFO" "$cmd_id"
            ;;
        success)
            log "命令执行成功 $extra" "INFO" "$cmd_id"
            ;;
        failure)
            log "命令执行失败 $extra" "ERROR" "$cmd_id"
            ;;
        retry)
            log "准备重试 $extra" "WARN" "$cmd_id"
            ;;
        *)
            log "$event $extra" "INFO" "$cmd_id"
            ;;
    esac
}

################################################################################
# 配置验证函数
################################################################################

# 验证配置的完整性和依赖项
validate_config() {
    log "开始配置验证" "INFO"

    # 检查ccr命令是否可用
    if ! command -v ccr &> /dev/null; then
        log "依赖错误: ccr命令未找到,请确保已安装并在PATH中" "ERROR"
        return 1
    fi

    log "配置验证成功" "INFO"
    return 0
}

################################################################################
# 命令执行核心函数
################################################################################

# 执行单个命令
# 参数:
#   $1: 命令字符串
#   $2: 命令ID (用于日志)
# 返回: 命令的退出码
execute_command() {
    local cmd="$1"
    local cmd_id="$2"
    local start_time
    local end_time
    local duration
    local exit_code
    
    start_time=$(date +%s)
    EXEC_START_TIME[$cmd_id]=$start_time
    
    log "执行命令: $cmd" "INFO" "$cmd_id"
    
    # 执行命令并捕获退出码
    eval "$cmd"
    exit_code=$?
    
    end_time=$(date +%s)
    EXEC_END_TIME[$cmd_id]=$end_time
    duration=$((end_time - start_time))
    
    if [[ $exit_code -eq 0 ]]; then
        log "命令执行完成,耗时${duration}秒,退出码:$exit_code" "INFO" "$cmd_id"
    else
        log "命令执行失败,耗时${duration}秒,退出码:$exit_code" "WARN" "$cmd_id"
    fi
    
    return $exit_code
}

################################################################################
# 输出文件验证函数 (支持通配符)
################################################################################

# 检查单个输出文件是否存在 (支持通配符)
# 参数:
#   $1: 文件路径模式 (可包含通配符*)
#   $2: 命令ID (用于日志)
# 返回: 0=存在, 1=不存在
check_output_file() {
    local pattern="$1"
    local cmd_id="$2"
    
    # 启用nullglob和extglob选项
    shopt -s nullglob extglob
    
    # 展开通配符
    local matches=($pattern)
    
    # 恢复默认设置
    shopt -u nullglob extglob
    
    local match_count=${#matches[@]}
    
    if [[ $match_count -eq 0 ]]; then
        # 无匹配
        log "通配符无匹配: $pattern" "DEBUG" "$cmd_id"
        return 1
    elif [[ $match_count -eq 1 ]]; then
        # 单个匹配,验证是否为文件
        if [[ -f "${matches[0]}" ]]; then
            log "通配符匹配到文件: ${matches[0]}" "DEBUG" "$cmd_id"
            return 0
        else
            log "通配符匹配结果不是文件: ${matches[0]}" "DEBUG" "$cmd_id"
            return 1
        fi
    else
        # 多个匹配,根据设计接受多匹配
        log "通配符匹配到${match_count}个文件: ${matches[*]}" "DEBUG" "$cmd_id"
        return 0
    fi
}

# 检查所有输出文件 (支持|分隔的多文件)
# 参数:
#   $1: 输出文件配置字符串 (用|分隔多个文件)
#   $2: 命令ID
# 返回: 0=所有文件存在, 1=至少一个文件不存在
check_all_output_files() {
    local files_config="$1"
    local cmd_id="$2"
    
    # 如果配置为空,表示无需检查
    if [[ -z "$files_config" ]]; then
        log "无需检查输出文件" "INFO" "$cmd_id"
        return 0
    fi
    
    # 分割多个文件路径
    IFS='|' read -ra file_list <<< "$files_config"
    
    local all_exist=true
    local missing_files=()
    
    for file_path in "${file_list[@]}"; do
        if check_output_file "$file_path" "$cmd_id"; then
            log "输出文件验证通过: $file_path" "INFO" "$cmd_id"
        else
            log "输出文件不存在: $file_path" "WARN" "$cmd_id"
            all_exist=false
            missing_files+=("$file_path")
        fi
    done
    
    if [[ "$all_exist" == true ]]; then
        return 0
    else
        log "缺失${#missing_files[@]}个输出文件" "WARN" "$cmd_id"
        return 1
    fi
}

################################################################################
# 重试机制
################################################################################

# 重试命令执行
# 参数:
#   $1: 命令字符串
#   $2: 命令ID
#   $3: 输出文件配置
# 返回: 0=最终成功, 1=重试后仍失败
retry_command() {
    local cmd="$1"
    local cmd_id="$2"
    local output_files="$3"
    local attempt=0
    
    # 初始化重试计数
    EXEC_RETRIES[$cmd_id]=0
    
    while [[ $attempt -lt $MAX_RETRIES ]]; do
        ((attempt++))
        
        if [[ $attempt -gt 1 ]]; then
            log "第${attempt}次尝试 (重试 $((attempt-1))/$((MAX_RETRIES-1)))" "INFO" "$cmd_id"
            ((EXEC_RETRIES[$cmd_id]++))
            ((TOTAL_RETRIES++))
        fi
        
        # 执行命令
        if execute_command "$cmd" "$cmd_id"; then
            # 命令执行成功,检查输出文件
            if check_all_output_files "$output_files" "$cmd_id"; then
                log "命令执行成功,输出文件验证通过" "INFO" "$cmd_id"
                return 0
            else
                # 输出文件不存在
                if [[ $attempt -lt $MAX_RETRIES ]]; then
                    log "输出文件未找到,${RETRY_DELAY}秒后重试..." "WARN" "$cmd_id"
                    sleep "$RETRY_DELAY"
                fi
            fi
        else
            # 命令执行失败
            if [[ $attempt -lt $MAX_RETRIES ]]; then
                log "命令执行失败,${RETRY_DELAY}秒后重试..." "WARN" "$cmd_id"
                sleep "$RETRY_DELAY"
            fi
        fi
    done
    
    log "命令执行失败,已达最大重试次数($MAX_RETRIES)" "ERROR" "$cmd_id"
    return 1
}

################################################################################
# 进度显示函数
################################################################################

# 显示执行进度
# 参数:
#   $1: 当前命令索引 (0-based)
#   $2: 总命令数
#   $3: 命令内容
#   $4: 状态
show_progress() {
    local current=$((${1} + 1))  # 转为1-based显示
    local total="$2"
    local cmd="$3"
    local status="$4"
    
    # 计算百分比
    local percent=$((current * 100 / total))
    
    # 生成进度条
    local filled=$((percent / 5))
    local empty=$((20 - filled))
    local bar=""
    local j  # 使用j而不是i避免与外部循环冲突
    
    for ((j=0; j<filled; j++)); do
        bar+="#"
    done
    for ((j=0; j<empty; j++)); do
        bar+="-"
    done
    
    # 截断命令显示 (最多40字符)
    local cmd_display="${cmd:0:40}"
    if [[ ${#cmd} -gt 40 ]]; then
        cmd_display="${cmd_display}..."
    fi
    
    echo "[$bar] $percent% | [$current/$total] $cmd_display - $status"
}

################################################################################
# 执行摘要函数
################################################################################

# 打印执行摘要
print_summary() {
    local script_end_time
    local total_duration
    local success_rate
    
    script_end_time=$(date +%s)
    total_duration=$((script_end_time - SCRIPT_START_TIME))
    
    # 计算成功率
    local total_commands=$((SUCCESS_COUNT + FAILURE_COUNT))
    if [[ $total_commands -gt 0 ]]; then
        success_rate=$(awk "BEGIN {printf \"%.1f\", $SUCCESS_COUNT*100/$total_commands}")
    else
        success_rate="0.0"
    fi
    
    # 输出到控制台
    echo ""
    echo "========================================"
    echo "           执行摘要报告"
    echo "========================================"
    echo "总命令数:   $total_commands"
    echo "成功:       $SUCCESS_COUNT"
    echo "失败:       $FAILURE_COUNT"
    echo "总重试次数: $TOTAL_RETRIES"
    echo "总耗时:     ${total_duration}秒"
    echo "成功率:     ${success_rate}%"
    echo "日志文件:   $LOG_FILE"
    echo "========================================"
    
    # 写入日志文件
    {
        echo ""
        echo "========================================"
        echo "执行摘要"
        echo "========================================"
        echo "总命令数:   $total_commands"
        echo "成功:       $SUCCESS_COUNT"
        echo "失败:       $FAILURE_COUNT"
        echo "总重试次数: $TOTAL_RETRIES"
        echo "总耗时:     ${total_duration}秒"
        echo "成功率:     ${success_rate}%"
        echo "结束时间:   $(date '+%Y-%m-%d %H:%M:%S')"
        echo "========================================"
    } >> "$LOG_FILE"
}

################################################################################
# 主函数
################################################################################

main() {
    # 解析命令行参数
    parse_arguments "$@"
    
    # 初始化日志文件
    echo "========================================" > "$LOG_FILE"
    echo "脚本执行日志" >> "$LOG_FILE"
    echo "========================================" >> "$LOG_FILE"
    echo "开始时间: $(date '+%Y-%m-%d %H:%M:%S')" >> "$LOG_FILE"
    echo "最大重试次数: $MAX_RETRIES" >> "$LOG_FILE"
    echo "重试延迟: ${RETRY_DELAY}秒" >> "$LOG_FILE"
    if [[ "$DRY_RUN" == true ]]; then
        echo "模式: 模拟执行 (DRY RUN)" >> "$LOG_FILE"
    fi
    if [[ $START_FROM -gt 1 ]]; then
        echo "起始命令: 第 $START_FROM 个" >> "$LOG_FILE"
    fi
    echo "========================================" >> "$LOG_FILE"
    echo "" >> "$LOG_FILE"
    
    # 输出欢迎信息
    echo "========================================"
    echo "$SCRIPT_NAME v$SCRIPT_VERSION"
    if [[ "$DRY_RUN" == true ]]; then
        echo "模式: 模拟执行 (不实际运行命令)"
    fi
    echo "========================================"
    echo "开始时间: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "最大重试次数: $MAX_RETRIES"
    echo "重试延迟: ${RETRY_DELAY}秒"
    if [[ $START_FROM -gt 1 ]]; then
        echo "起始命令: 第 $START_FROM 个"
    fi
    echo "日志文件: $LOG_FILE"
    echo "========================================"
    echo ""
    
    log "开始执行自动化命令脚本" "INFO"
    
    # 验证配置
    if ! validate_config; then
        log "配置验证失败,脚本终止" "ERROR"
        exit 3
    fi
    
    log "脚本初始化完成,准备执行命令" "INFO"
    
    # 主命令执行循环
    local total_commands=${#COMMANDS[@]}
    
    # 验证 START_FROM 是否超过命令总数
    if [[ $START_FROM -gt $total_commands ]]; then
        log "错误: --start-from ($START_FROM) 超过命令总数 ($total_commands)" "ERROR"
        exit 3
    fi
    
    for ((i=0; i<total_commands; i++)); do
        local cmd_id=$((i + 1))  # 命令ID从1开始
        
        # 检查是否跳过此命令
        if [[ $cmd_id -lt $START_FROM ]]; then
            log "跳过命令 $cmd_id (从第 $START_FROM 个开始)" "INFO" "$cmd_id"
            continue
        fi
        
        # 检查是否被中断
        if [[ "$INTERRUPTED" == true ]]; then
            log "检测到中断信号,停止执行后续命令" "WARN"
            break
        fi
        
        local cmd="${COMMANDS[$i]}"
        local output_files="${OUTPUT_FILES[$cmd]:-}"  # 从关联数组获取,不存在则默认为空
        
        echo ""
        log "========== 开始执行命令 $cmd_id/$total_commands ==========" "INFO" "$cmd_id"
        
        # 显示进度
        show_progress "$i" "$total_commands" "$cmd" "执行中"
        
        # 设置初始状态
        EXEC_STATUS[$cmd_id]="RUNNING"
        
        # Dry-run模式
        if [[ "$DRY_RUN" == true ]]; then
            log "[DRY RUN] 将执行: $cmd" "INFO" "$cmd_id"
            log "[DRY RUN] 将检查输出文件: $output_files" "INFO" "$cmd_id"
            EXEC_STATUS[$cmd_id]="SUCCESS"
            ((SUCCESS_COUNT++))
            show_progress "$i" "$total_commands" "$cmd" "✓ 模拟成功"
            continue
        fi
        
        # 执行命令(带重试)
        if retry_command "$cmd" "$cmd_id" "$output_files"; then
            EXEC_STATUS[$cmd_id]="SUCCESS"
            ((SUCCESS_COUNT++))
            
            local retry_count=${EXEC_RETRIES[$cmd_id]}
            if [[ $retry_count -gt 0 ]]; then
                log "命令执行成功 (重试${retry_count}次后成功)" "INFO" "$cmd_id"
                show_progress "$i" "$total_commands" "$cmd" "✓ 成功 (重试${retry_count}次)"
            else
                log "命令执行成功" "INFO" "$cmd_id"
                show_progress "$i" "$total_commands" "$cmd" "✓ 成功"
            fi
        else
            EXEC_STATUS[$cmd_id]="FAILED"
            ((FAILURE_COUNT++))
            
            log "命令执行失败,继续执行下一个命令" "ERROR" "$cmd_id"
            show_progress "$i" "$total_commands" "$cmd" "✗ 失败"
        fi
    done
    
    # 输出执行摘要
    print_summary
    
    # 根据执行结果返回相应的退出码
    if [[ $FAILURE_COUNT -eq 0 ]]; then
        log "所有命令执行成功,脚本结束" "INFO"
        return 0
    elif [[ $SUCCESS_COUNT -eq 0 ]]; then
        log "所有命令执行失败,脚本结束" "ERROR"
        return 2
    else
        log "部分命令失败,脚本结束" "WARN"
        return 1
    fi
}

# 执行主函数
main "$@"

