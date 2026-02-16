#!/usr/bin/env bash

# OmniSpec 软链接安装脚本
# 功能：将 src/agent/commands 和 src/specify 目录软链接到目标代码工程路径
# 详细使用说明请运行: ./install-link.sh -h 或 ./install-link.sh --help

set -e          # 遇到错误立即退出
set -u          # 使用未定义变量时报错
set -o pipefail # 管道命令失败时退出

# 显示使用说明
show_usage() {
    cat << EOF
OmniSpec 软链接安装脚本

使用方法:
  $0 [选项]

功能说明:
  1. 提示用户输入目标项目目录
  2. 提示用户选择 agent 类型（AI-IDE、cursor、claude code）
  3. 在目标项目目录下创建对应的目录（.flow、.cursor 或 .claude）
  4. 将 OmniSpec/src/agent/commands 软链接到 项目目录/.{agent_type}/commands
  5. 将 OmniSpec/specify 软链接到 项目目录/.specify

Agent 类型映射:
  - AI-IDE      -> .flow 目录
  - cursor      -> .cursor 目录
  - claude code -> .claude 目录

示例:
  $0
  $0 --project-dir /path/to/project --agent-type cursor

选项:
  -h, --help              显示此帮助信息
  -p, --project-dir DIR   指定目标项目目录（可选，不指定则提示输入）
  -a, --agent-type TYPE   指定 agent 类型（可选，不指定则提示选择）
                         支持的值: AI-IDE, cursor, claude-code

注意事项:
  - 如果目标目录已存在，会提示用户确认是否覆盖
  - 如果软链接已存在，会提示用户确认是否重新创建
  - 脚本必须在 OmniSpec 代码库根目录下执行

EOF
}

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# SOURCE_DIR 指向 build 的父目录（OmniSpec），以便找到 agent 和 specify 目录
SOURCE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

SOURCE_AGENT_COMMANDS_DIR="$SOURCE_DIR/src/agent/commands"
SOURCE_SPECIFY_DIR="$SOURCE_DIR/src/specify"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# 打印信息
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# 打印分隔线
print_separator() {
    echo "=========================================="
}

# 打印标题
print_title() {
    echo -e "${BOLD}${CYAN}$1${NC}"
}

# 检查源目录是否存在
check_source_dirs() {
    if [ ! -d "$SOURCE_AGENT_COMMANDS_DIR" ]; then
        log_error "agent/commands 目录不存在: $SOURCE_AGENT_COMMANDS_DIR"
        exit 1
    fi
    
    if [ ! -d "$SOURCE_SPECIFY_DIR" ]; then
        log_error "specify 目录不存在: $SOURCE_SPECIFY_DIR"
        exit 1
    fi
}

# 验证并获取目标项目目录
get_target_project_dir() {
    local input_dir="$1"
    
    if [ -z "$input_dir" ]; then
        return 1
    fi
    
    # 如果路径不存在
    if [ ! -d "$input_dir" ]; then
        return 1
    fi
    
    # 转换为绝对路径
    local abs_path
    abs_path="$(cd "$input_dir" && pwd)"
    echo "$abs_path"
}

# 根据 agent 类型获取目录名
get_agent_dir_name() {
    local agent_type="$1"
    
    case "$agent_type" in
        "AI-IDE")
            echo ".flow"
            ;;
        "cursor")
            echo ".cursor"
            ;;
        "claude code")
            echo ".claude"
            ;;
        *)
            log_error "不支持的 agent 类型: $agent_type"
            return 1
            ;;
    esac
}

# 去除字符串首尾空格
trim_string() {
    echo "$1" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//'
}

# 获取绝对路径
get_absolute_path() {
    local path="$1"
    if [ -d "$path" ]; then
        cd "$path" && pwd
    else
        echo "$(cd "$(dirname "$path")" && pwd)/$(basename "$path")"
    fi
}

# 提示用户确认
prompt_confirm() {
    local message="$1"
    echo -e "${YELLOW}${message}${NC}"
    read -r -n 1 reply
    echo
    [[ "$reply" =~ ^[Yy]$ ]]
}

# 根据序号获取 agent 类型
get_agent_type_by_number() {
    local number="$1"
    
    case "$number" in
        1)
            echo "AI-IDE"
            ;;
        2)
            echo "cursor"
            ;;
        3)
            echo "claude code"
            ;;
        *)
            return 1
            ;;
    esac
}

# 提示用户输入项目目录
prompt_project_dir() {
    while true; do
        # 提示信息输出到 stderr，避免被命令替换捕获
        echo >&2
        echo -e "${BOLD}${BLUE}步骤 1/2: 输入项目代码目录${NC}" >&2
        echo -e "${BLUE}请输出项目代码目录：${NC}" >&2
        read -r project_dir
        
        # 去除首尾空格
        project_dir=$(trim_string "$project_dir")
        
        if [ -z "$project_dir" ]; then
            log_error "项目目录不能为空，请重新输入"
            echo >&2
            continue
        fi
        
        local abs_dir
        if abs_dir=$(get_target_project_dir "$project_dir" 2>/dev/null); then
            echo >&2
            log_info "项目目录验证成功: $abs_dir" >&2
            # 只输出结果到 stdout，供命令替换使用
            echo "$abs_dir"
            return 0
        else
            log_error "项目目录不存在或无法访问: $project_dir"
            if ! prompt_confirm "是否重新输入？(Y/n):" >&2; then
                return 1
            fi
            echo >&2
        fi
    done
}

# 提示用户选择 agent 类型
prompt_agent_type() {
    # 提示信息输出到 stderr，避免被命令替换捕获
    echo >&2
    echo -e "${BOLD}${BLUE}步骤 2/2: 选择 Agent 类型${NC}" >&2
    echo -e "${BLUE}请选择 agent 类型:${NC}" >&2
    echo >&2
    echo "  1) AI-IDE" >&2
    echo "  2) cursor" >&2
    echo "  3) claude code" >&2
    echo >&2
    
    while true; do
        echo -e "${BLUE}请输入选项序号 (1-3):${NC}" >&2
        read -r choice
        
        # 去除首尾空格
        choice=$(trim_string "$choice")
        
        if [ -z "$choice" ]; then
            log_error "选项不能为空，请重新输入"
            echo >&2
            continue
        fi
        
        local agent_type
        if agent_type=$(get_agent_type_by_number "$choice"); then
            echo >&2
            log_info "已选择 Agent 类型: $agent_type" >&2
            # 只输出结果到 stdout，供命令替换使用
            echo "$agent_type"
            return 0
        else
            log_error "无效的选项，请输入 1、2 或 3"
            echo >&2
        fi
    done
}

# 创建目录（如果不存在）
create_directory() {
    local dir_path="$1"
    local dir_name="$2"
    
    if [ -d "$dir_path" ]; then
        log_info "$dir_name 目录已存在: $dir_path"
        return 0
    fi
    
    log_info "正在创建 $dir_name 目录: $dir_path"
    mkdir -p "$dir_path"
    log_success "$dir_name 目录创建成功"
}

# 创建软链接
create_symlink() {
    local source_path="$1"
    local target_path="$2"
    local link_name="$3"
    
    # 转换为绝对路径
    local source_abs
    source_abs="$(get_absolute_path "$source_path")"
    
    # 如果目标路径已存在
    if [ -e "$target_path" ]; then
        # 检查是否是软链接
        if [ -L "$target_path" ]; then
            local current_target
            current_target="$(readlink -f "$target_path")"
            if [ "$current_target" = "$source_abs" ]; then
                log_info "$link_name 软链接已存在且指向正确: $target_path"
                return 0
            else
                log_warn "$link_name 软链接已存在但指向不同的位置: $target_path"
                log_warn "  当前指向: $current_target"
                log_warn "  应该指向: $source_abs"
                if ! prompt_confirm "是否删除并重新创建软链接？(y/N):"; then
                    log_warn "跳过 $link_name 软链接的创建"
                    return 0
                fi
                rm -f "$target_path"
            fi
        else
            # 是文件或目录，不是软链接
            log_warn "$link_name 目标路径已存在且不是软链接: $target_path"
            if ! prompt_confirm "是否删除并创建软链接？(y/N):"; then
                log_warn "跳过 $link_name 软链接的创建"
                return 0
            fi
            rm -rf "$target_path"
        fi
    fi
    
    # 创建软链接
    log_info "正在创建 $link_name 软链接..."
    log_info "  源路径: $source_path"
    log_info "  目标路径: $target_path"
    
    # 确保目标路径的父目录存在
    local target_parent
    target_parent="$(dirname "$target_path")"
    if [ ! -d "$target_parent" ]; then
        mkdir -p "$target_parent"
    fi
    
    # 转换为绝对路径
    local target_abs
    target_abs="$(get_absolute_path "$target_path")"
    
    # 使用绝对路径创建软链接（简单可靠）
    ln -sf "$source_abs" "$target_abs"
    log_success "$link_name 软链接创建成功"
}

# 主函数
main() {
    local project_dir=""
    local agent_type=""
    
    # 解析命令行参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_usage
                exit 0
                ;;
            -p|--project-dir)
                if [ -z "${2:-}" ]; then
                    log_error "选项 $1 需要指定项目目录"
                    show_usage
                    exit 1
                fi
                project_dir="$2"
                shift 2
                ;;
            -a|--agent-type)
                if [ -z "${2:-}" ]; then
                    log_error "选项 $1 需要指定 agent 类型"
                    show_usage
                    exit 1
                fi
                agent_type="$2"
                shift 2
                ;;
            *)
                log_error "未知选项: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    # 显示标题
    print_separator
    print_title "  OmniSpec 软链接安装脚本"
    print_separator
    echo
    
    # 检查源目录
    log_info "正在检查源目录..."
    check_source_dirs
    log_success "源目录检查通过"
    echo
    
    # 获取目标项目目录
    if [ -z "$project_dir" ]; then
        project_dir=$(prompt_project_dir)
        if [ $? -ne 0 ] || [ -z "$project_dir" ]; then
            log_error "用户取消操作"
            exit 1
        fi
    else
        log_info "使用命令行参数指定的项目目录: $project_dir"
        if ! project_dir=$(get_target_project_dir "$project_dir" 2>/dev/null); then
            log_error "无效的目标项目目录: $project_dir"
            exit 1
        fi
        log_info "项目目录验证成功: $project_dir"
    fi
    
    # 获取 agent 类型
    if [ -z "$agent_type" ]; then
        agent_type=$(prompt_agent_type)
    else
        log_info "使用命令行参数指定的 Agent 类型: $agent_type"
    fi
    
    # 验证 agent 类型并获取目录名
    local agent_dir_name
    if ! agent_dir_name=$(get_agent_dir_name "$agent_type"); then
        exit 1
    fi
    
    echo
    print_separator
    log_info "开始安装..."
    print_separator
    echo
    log_info "配置信息:"
    log_info "  项目目录: $project_dir"
    log_info "  Agent 类型: $agent_type"
    log_info "  Agent 目录: $agent_dir_name"
    echo
    
    # 创建 agent 目录
    local agent_dir="$project_dir/$agent_dir_name"
    create_directory "$agent_dir" "Agent ($agent_dir_name)"
    echo
    
    # 创建软链接：agent/commands -> .{agent_type}/commands
    local commands_link_target="$agent_dir/commands"
    create_symlink \
        "$SOURCE_AGENT_COMMANDS_DIR" \
        "$commands_link_target" \
        "agent/commands"
    echo
    
    # 创建软链接：specify -> .specify
    local specify_link_target="$project_dir/.specify"
    create_symlink \
        "$SOURCE_SPECIFY_DIR" \
        "$specify_link_target" \
        "specify"
    echo
    
    print_separator
    log_success "安装完成！"
    print_separator
    echo
    log_info "安装摘要:"
    log_info "  项目目录: $project_dir"
    log_info "  Agent 目录: $agent_dir"
    log_info "  软链接:"
    log_info "    - $commands_link_target -> $SOURCE_AGENT_COMMANDS_DIR"
    log_info "    - $specify_link_target -> $SOURCE_SPECIFY_DIR"
    echo
}

# 执行主函数
main "$@"
