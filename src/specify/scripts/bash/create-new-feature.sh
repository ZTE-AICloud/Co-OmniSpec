#!/usr/bin/env bash

set -e

# ============================================================================
# 参数解析模块
# ============================================================================

# Usage 消息（常量）
readonly USAGE_MSG="Usage: $0 [--json] [--short-name <name>] [--number N]"

# 显示帮助信息
show_help() {
    echo "$USAGE_MSG"
    echo ""
    echo "Options:"
    echo "  --json              Output in JSON format"
    echo "  --short-name <name> Provide a custom short name (2-4 words) for the branch"
    echo "  --number N          Specify branch number manually (overrides auto-detection)"
    echo "  --help, -h          Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 --short-name 'user-auth'"
    echo "  $0 --short-name 'user-auth' --number 5"
}

# 获取选项参数值（辅助函数，封装重复逻辑）
# 输入: option_name, current_index, total_args, args_array (通过 "$@" 传递)
# 输出: 下一个参数的值，如果无效则退出
_get_option_value() {
    local option_name="$1"
    local current_index="$2"
    local total_args="$3"
    shift 3
    local args=("$@")
    
    if [ $((current_index + 1)) -gt $total_args ]; then
        echo "Error: $option_name requires a value" >&2
        exit 1
    fi
    
    local next_index=$((current_index + 1))
    local next_arg="${args[$((next_index - 1))]}"
    
    # Check if the next argument is another option (starts with --)
    if [[ "$next_arg" == --* ]]; then
        echo "Error: $option_name requires a value" >&2
        exit 1
    fi
    
    echo "$next_index|$next_arg"
}

# 解析命令行参数
# 输出: 通过全局变量设置 JSON_MODE, SHORT_NAME, BRANCH_NUMBER
parse_arguments() {
    JSON_MODE=false
    SHORT_NAME=""
    BRANCH_NUMBER=""
    local i=1
    
    while [ $i -le $# ]; do
        local arg="${!i}"
        case "$arg" in
            --json) 
                JSON_MODE=true 
                ;;
            --short-name)
                result=$(_get_option_value "--short-name" $i $# "$@")
                next_index=$(echo "$result" | cut -d'|' -f1)
                SHORT_NAME=$(echo "$result" | cut -d'|' -f2)
                i=$next_index
                ;;
            --number)
                result=$(_get_option_value "--number" $i $# "$@")
                next_index=$(echo "$result" | cut -d'|' -f1)
                BRANCH_NUMBER=$(echo "$result" | cut -d'|' -f2)
                i=$next_index
                ;;
            --help|-h) 
                show_help
                exit 0
                ;;
            *) 
                echo "$USAGE_MSG" >&2
                echo "Error: Unknown argument: $arg" >&2
                exit 1
                ;;
        esac
        i=$((i + 1))
    done
    
    # short-name 是必需的
    if [ -z "$SHORT_NAME" ]; then
        echo "$USAGE_MSG" >&2
        echo "Error: --short-name is required" >&2
        exit 1
    fi
}

# ============================================================================
# 仓库发现模块
# ============================================================================

# 通过搜索项目标记查找仓库根目录
find_repo_root() {
    local dir="$1"
    while [ "$dir" != "/" ]; do
        if [ -d "$dir/.git" ] || [ -d "$dir/.specify" ]; then
            echo "$dir"
            return 0
        fi
        dir="$(dirname "$dir")"
    done
    return 1
}

# 解析仓库根目录
# 输出: REPO_ROOT (全局变量), HAS_GIT (全局变量)
resolve_repository_root() {
    local SCRIPT_DIR="$(CDPATH="" cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    
    if git rev-parse --show-toplevel >/dev/null 2>&1; then
        REPO_ROOT=$(git rev-parse --show-toplevel)
        HAS_GIT=true
    else
        REPO_ROOT="$(find_repo_root "$SCRIPT_DIR")"
        if [ -z "$REPO_ROOT" ]; then
            echo "Error: Could not determine repository root. Please run this script from within the repository." >&2
            exit 1
        fi
        HAS_GIT=false
    fi
    
    cd "$REPO_ROOT"
    
    CHANGES_DIR="$REPO_ROOT/changes"
    
    # 确保 changes 目录存在
    mkdir -p "$CHANGES_DIR"
}

# ============================================================================
# 分支编号管理模块
# ============================================================================

# 从数字列表中获取最大值（辅助函数）
# 输入: 数字列表（空格分隔，可以是三位数字字符串或整数）
# 输出: 最大值（数字），如果列表为空返回0
_get_max_from_numbers() {
    local max_num=0
    for num in "$@"; do
        if [ -n "$num" ]; then
            # 验证是否为数字（可以是任意位数）
            if echo "$num" | grep -qE '^[0-9]+$'; then
                # 强制将数字解释为十进制（去除前导零的影响）
                local decimal_num=$((10#$num))
                # 验证算术转换是否成功（避免溢出或无效数字）
                if [ "$decimal_num" -ge 0 ] 2>/dev/null && [ "$decimal_num" -gt "$max_num" ]; then
                    max_num=$decimal_num
                fi
            fi
        fi
    done
    echo $max_num
}

# 从目录名提取数字（辅助函数）
# 输入: 目录路径
# 输出: 提取的数字（仅匹配 NNN- 格式），如果无效则输出空
_extract_number_from_dirname() {
    local dir="$1"
    [ -d "$dir" ] || return
    local dirname=$(basename "$dir")
    # 严格匹配三位数字+连字符格式：NNN-
    # 只提取符合 001-xxx, 123-xxx 等格式的数字部分
    if echo "$dirname" | grep -qE '^[0-9]{3}-'; then
        echo "$dirname" | grep -oE '^[0-9]{3}' || echo ""
    else
        echo ""
    fi
}

# 构建分支匹配模式（辅助函数）
# 输入: base_pattern, short_name (可选)
# 输出: 完整的匹配模式（严格三位数字格式）
_build_branch_pattern() {
    local base_pattern="$1"
    local short_name="${2:-}"
    
    if [ -n "$short_name" ]; then
        # 严格匹配三位数字：NNN-short-name
        echo "${base_pattern}{3}-${short_name}\$"
    else
        # 严格匹配三位数字：NNN-
        echo "${base_pattern}{3}-"
    fi
}

# 从远程分支获取最大编号（封装实现）
# 输入: short_name (可选，如果提供则只匹配该短名称的分支)
# 输出: 最大编号（数字），不存在返回0
get_max_number_from_remote_branches() {
    local short_name="${1:-}"
    
    # Fetch all remotes to get latest branch info (suppress errors if no remotes)
    git fetch --all --prune >/dev/null 2>&1 || true
    
    # Build pattern for matching branches (严格三位数字格式)
    local pattern=$(_build_branch_pattern "refs/heads/[0-9]" "$short_name")
    
    # Find all branches matching the pattern using git ls-remote (more reliable)
    # 提取三位数字部分：NNN-xxx
    local remote_branches=$(git ls-remote --heads origin 2>/dev/null | grep -E "$pattern" | sed 's/.*\/\([0-9]\{3\}\)-.*/\1/' | sort -n)
    
    # Get the highest number
    _get_max_from_numbers $remote_branches
}

# 从本地分支获取最大编号（封装实现）
# 输入: short_name (可选，如果提供则只匹配该短名称的分支)
# 输出: 最大编号（数字），不存在返回0
get_max_number_from_local_branches() {
    local short_name="${1:-}"
    
    # Build pattern for matching branches (严格三位数字格式)
    local pattern=$(_build_branch_pattern "^[* ]*[0-9]" "$short_name")
    
    # Check local branches
    # 提取三位数字部分：NNN-xxx
    local local_branches=$(git branch 2>/dev/null | grep -E "$pattern" | sed 's/^[* ]*//' | sed 's/^\([0-9]\{3\}\)-.*/\1/' | sort -n)
    
    # Get the highest number
    _get_max_from_numbers $local_branches
}

# 从 changes 目录获取最大编号（封装实现）
# 输入: CHANGES_DIR, short_name (可选，如果提供则只匹配该短名称的目录)
# 输出: 最大编号（数字），不存在返回0
get_max_number_from_CHANGES_DIR() {
    local CHANGES_DIR="$1"
    local short_name="${2:-}"
    
    local max_num=0
    
    if [ ! -d "$CHANGES_DIR" ]; then
        echo $max_num
        return 0
    fi
    
    # 收集所有匹配的数字
    local numbers=""
    
    # 如果提供了短名称，匹配特定模式；否则匹配所有带编号的目录
    if [ -n "$short_name" ]; then
        # 匹配特定短名称的目录：如 001-user-auth（严格三位数字格式）
        # 使用 find -print0 处理包含空格或特殊字符的路径
        while IFS= read -r -d '' dir; do
            local number=$(_extract_number_from_dirname "$dir")
            if [ -n "$number" ]; then
                numbers="${numbers}${numbers:+ }${number}"
            fi
        done < <(find "$CHANGES_DIR" -maxdepth 1 -type d -name "[0-9][0-9][0-9]-${short_name}" -print0 2>/dev/null)
    else
        # 匹配所有带三位数字编号的目录：如 001-*, 002-* 等
        for dir in "$CHANGES_DIR"/*; do
            local number=$(_extract_number_from_dirname "$dir")
            if [ -n "$number" ]; then
                numbers="${numbers}${numbers:+ }${number}"
            fi
        done
    fi
    
    # 从收集的数字中获取最大值
    if [ -n "$numbers" ]; then
        _get_max_from_numbers $numbers
    else
        echo $max_num
    fi
}

# 查找已存在分支的最大编号（如果不存在返回0）
# 输入: CHANGES_DIR, short_name
# 输出: 最大编号（数字），不存在返回0
find_existing_branch_max_number() {
    local CHANGES_DIR="$1"
    local short_name="$2"
    
    # 从三个来源获取最大编号
    local remote_max=$(get_max_number_from_remote_branches "$short_name")
    local local_max=$(get_max_number_from_local_branches "$short_name")
    local changes_max=$(get_max_number_from_CHANGES_DIR "$CHANGES_DIR" "$short_name")

    # 找出三个来源中的最大值
    _get_max_from_numbers $remote_max $local_max $changes_max
}

# 确定分支编号（使用全局编号）
# 输入: branch_number (可选，可能带前导零), branch_suffix, has_git, CHANGES_DIR
# 输出: 分支编号（十进制整数，无前导零）
# 注意: 创建新分支时使用全局编号，确保编号唯一且连续
determine_branch_number() {
    local branch_number="$1"
    local branch_suffix="$2"
    local has_git="$3"
    local CHANGES_DIR="$4"
    
    if [ -z "$branch_number" ]; then
        if [ "$has_git" = true ]; then
            # 使用全局编号：查找所有分支的最大编号（不限定短名称）
            # 这样可以确保不同功能的分支编号唯一且连续
            local highest=$(find_existing_branch_max_number "$CHANGES_DIR" "$branch_suffix")
            branch_number=$((highest + 1))
        else
            # Fall back to local directory check (already uses global numbering)
            local highest=$(get_max_number_from_CHANGES_DIR "$CHANGES_DIR" "")
            branch_number=$((highest + 1))
        fi
    else
        # 用户手动指定了编号，需要规范化为十进制整数
        # 处理可能的前导零（如用户输入 001 或 010）
        branch_number=$((10#$branch_number))
    fi
    
    echo "$branch_number"
}

# ============================================================================
# 分支名生成模块
# ============================================================================

# 清理和格式化分支名
clean_branch_name() {
    local name="$1"
    echo "$name" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g' | sed 's/-\+/-/g' | sed 's/^-//' | sed 's/-$//'
}

# 截断分支名以符合长度限制
# 输入: branch_name, max_length
# 输出: 截断后的分支名（通过全局变量 BRANCH_NAME 设置）
truncate_branch_name() {
    local branch_name="$1"
    local max_length="$2"
    local feature_num="$3"
    
    if [ ${#branch_name} -gt $max_length ]; then
        # Calculate how much we need to trim from suffix
        # Account for: feature number (3) + hyphen (1) = 4 chars
        local max_suffix_length=$((max_length - 4))
        
        # Extract suffix (everything after "###-")
        local suffix="${branch_name#*-}"
        
        # Truncate suffix at word boundary if possible
        local truncated_suffix=$(echo "$suffix" | cut -c1-$max_suffix_length)
        # Remove trailing hyphen if truncation created one
        truncated_suffix=$(echo "$truncated_suffix" | sed 's/-$//')
        
        local original_branch_name="$branch_name"
        branch_name="${feature_num}-${truncated_suffix}"
        
        >&2 echo "[specify] Warning: Branch name exceeded GitHub's 244-byte limit"
        >&2 echo "[specify] Original: $original_branch_name (${#original_branch_name} bytes)"
        >&2 echo "[specify] Truncated to: $branch_name (${#branch_name} bytes)"
    fi
    
    echo "$branch_name"
}

# 生成完整分支名
# 输入: short_name, branch_number, has_git, CHANGES_DIR
# 输出: BRANCH_NAME (全局变量), BRANCH_SUFFIX (全局变量), FEATURE_NUM (全局变量), BRANCH_NUMBER (全局变量)
generate_full_branch_name() {
    local short_name="$1"
    local branch_number="$2"
    local has_git="$3"
    local CHANGES_DIR="$4"
    
    # Generate branch suffix from short name
    local branch_suffix=$(clean_branch_name "$short_name")
    
    # Determine branch number (已规范化为十进制整数)
    branch_number=$(determine_branch_number "$branch_number" "$branch_suffix" "$has_git" "$CHANGES_DIR")
    
    # Format feature number with zero padding
    # branch_number 已由 determine_branch_number 规范化为十进制整数，无需 10#
    local feature_num=$(printf "%03d" "$branch_number")
    
    # Generate full branch name
    local branch_name="${feature_num}-${branch_suffix}"
    
    # Truncate if necessary (GitHub enforces 244-byte limit)
    local max_branch_length=244
    branch_name=$(truncate_branch_name "$branch_name" "$max_branch_length" "$feature_num")
    
    # 设置全局变量
    BRANCH_NAME="$branch_name"
    BRANCH_SUFFIX="$branch_suffix"
    FEATURE_NUM="$feature_num"
    BRANCH_NUMBER="$branch_number"
}

# ============================================================================
# Git 操作模块
# ============================================================================

# 创建 git 分支
# 输入: branch_name, has_git
create_git_branch() {
    local branch_name="$1"
    local has_git="$2"
    
    if [ "$has_git" = true ]; then
        git checkout -b "$branch_name"
    else
        >&2 echo "[specify] Warning: Git repository not detected; skipped branch creation for $branch_name"
    fi
}

# ============================================================================
# 文件系统操作模块
# ============================================================================

# 获取 spec 模板路径（辅助函数）
# 输入: repo_root
# 输出: 模板文件路径
_get_spec_template_path() {
    local repo_root="$1"
    echo "$repo_root/.specify/templates/spec-template.md"
}

# 创建 feature 目录
# 输入: CHANGES_DIR, branch_name
# 输出: feature_dir 路径
create_feature_directory() {
    local CHANGES_DIR="$1"
    local branch_name="$2"
    
    local feature_dir="$CHANGES_DIR/$branch_name"
    mkdir -p "$feature_dir"
    echo "$feature_dir"
}

# 创建或复制 spec 文件（辅助函数，封装重复逻辑）
# 输入: change_file_path, template_path
# 输出: change_file 路径
_create_change_file_internal() {
    local change_file="$1"
    local template="$2"
    
    if [ -f "$template" ]; then
        cp "$template" "$change_file"
    else
        touch "$change_file"
    fi
    
    echo "$change_file"
}

# 创建 spec 文件
# 输入: feature_dir, repo_root
# 输出: change_file 路径
create_change_file() {
    local feature_dir="$1"
    local repo_root="$2"
    
    local template=$(_get_spec_template_path "$repo_root")
    local change_file="$feature_dir/spec.md"
    
    _create_change_file_internal "$change_file" "$template"
}

# ============================================================================
# 分支创建模块
# ============================================================================

# 创建新的 feature 分支
# 输入: short_name, branch_number, has_git, CHANGES_DIR, repo_root, json_mode
# 输出: 始终返回0并输出结果
create_new_feature_branch() {
    local short_name="$1"
    local branch_number="$2"
    local has_git="$3"
    local CHANGES_DIR="$4"
    local repo_root="$5"
    local json_mode="$6"
    
    # 生成完整分支名
    generate_full_branch_name "$short_name" "$branch_number" "$has_git" "$CHANGES_DIR"
    
    # 创建 git 分支
    create_git_branch "$BRANCH_NAME" "$has_git"
    
    # 创建文件系统结构
    local feature_dir=$(create_feature_directory "$CHANGES_DIR" "$BRANCH_NAME")
    local change_file=$(create_change_file "$feature_dir" "$repo_root")
    
    # 设置环境变量
    export SPECIFY_FEATURE="$BRANCH_NAME"
    
    # 输出结果
    output_results "$json_mode" "$BRANCH_NAME" "$change_file" "$FEATURE_NUM"
    
    return 0
}

# ============================================================================
# 输出格式化模块
# ============================================================================

# JSON 格式输出
format_json_output() {
    local branch_name="$1"
    local change_file="$2"
    local feature_num="$3"

    printf '{"BRANCH_NAME":"%s","change_file":"%s","FEATURE_NUM":"%s"}\n' \
        "$branch_name" "$change_file" "$feature_num"
}

# 标准格式输出
format_standard_output() {
    local branch_name="$1"
    local change_file="$2"
    local feature_num="$3"
    
    echo "BRANCH_NAME: $branch_name"
    echo "change_file: $change_file"
    echo "FEATURE_NUM: $feature_num"
    echo "SPECIFY_FEATURE environment variable set to: $branch_name"
}

# 输出结果
output_results() {
    local json_mode="$1"
    local branch_name="$2"
    local change_file="$3"
    local feature_num="$4"
    
    if [ "$json_mode" = true ]; then
        format_json_output "$branch_name" "$change_file" "$feature_num"
    else
        format_standard_output "$branch_name" "$change_file" "$feature_num"
    fi
}

# ============================================================================
# 主流程控制
# ============================================================================

main() {
    # 1. 解析参数
    parse_arguments "$@"
    
    # 2. 发现仓库
    resolve_repository_root

    # 3. 创建新的 feature 分支
    create_new_feature_branch "$SHORT_NAME" "$BRANCH_NUMBER" "$HAS_GIT" "$CHANGES_DIR" "$REPO_ROOT" "$JSON_MODE"
}

# 执行主函数
main "$@"
