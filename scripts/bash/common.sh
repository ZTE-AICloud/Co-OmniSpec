#!/usr/bin/env bash
# Common functions and variables for all scripts

# Get repository root, with fallback for non-git repositories
get_repo_root() {
    if git rev-parse --show-toplevel >/dev/null 2>&1; then
        git rev-parse --show-toplevel
    else
        # Fall back to script location for non-git repos
        local script_dir="$(CDPATH="" cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
        (cd "$script_dir/../../.." && pwd)
    fi
}

# Get current branch, with fallback for non-git repositories
# Usage: get_current_branch [repo_root]
get_current_branch() {
    local repo_root="${1:-}"

    # First check if SPECIFY_FEATURE environment variable is set
    if [[ -n "${SPECIFY_FEATURE:-}" ]]; then
        echo "$SPECIFY_FEATURE"
        return
    fi

    # Then check git if available (prefer running inside repo_root when provided)
    if [[ -n "$repo_root" && -d "$repo_root" ]]; then
        if (cd "$repo_root" && git rev-parse --abbrev-ref HEAD >/dev/null 2>&1); then
            (cd "$repo_root" && git rev-parse --abbrev-ref HEAD)
            return
        fi
    elif git rev-parse --abbrev-ref HEAD >/dev/null 2>&1; then
        git rev-parse --abbrev-ref HEAD
        return
    fi

    # For non-git repos, try to find the latest feature directory
    local repo_root=$(get_repo_root)
    local changes_dir="$repo_root/changes"

    if [[ -d "$changes_dir" ]]; then
        local latest_feature=""
        local highest=0

        for dir in "$changes_dir"/*; do
            if [[ -d "$dir" ]]; then
                local dirname=$(basename "$dir")
                if [[ "$dirname" =~ ^([0-9]{3})- ]]; then
                    local number=${BASH_REMATCH[1]}
                    number=$((10#$number))
                    if [[ "$number" -gt "$highest" ]]; then
                        highest=$number
                        latest_feature=$dirname
                    fi
                fi
            fi
        done

        if [[ -n "$latest_feature" ]]; then
            echo "$latest_feature"
            return
        fi
    fi

    echo "main"  # Final fallback
}

# Check if we have git available
has_git() {
    git rev-parse --show-toplevel >/dev/null 2>&1
}

check_feature_branch() {
    local branch="$1"
    local has_git_repo="$2"

    # For non-git repos, we can't enforce branch naming but still provide output
    if [[ "$has_git_repo" != "true" ]]; then
        echo "[specify] Warning: Git repository not detected; skipped branch validation" >&2
        return 0
    fi

    if [[ ! "$branch" =~ ^[0-9]{3}- ]]; then
        echo "ERROR: Not on a feature branch. Current branch: $branch" >&2
        echo "Feature branches should be named like: 001-feature-name" >&2
        return 1
    fi

    return 0
}

get_feature_dir() { echo "$1/changes/$2"; }

# Get document directory, with fallback
# Priority: 1. Environment variable SPECIFY_DOC_DIR, 2. Config file, 3. Default "omni-doc"
get_doc_dir() {
    # 1. Check environment variable
    if [[ -n "${SPECIFY_DOC_DIR:-}" ]]; then
        echo "${SPECIFY_DOC_DIR}"
        return
    fi
    
    # 2. Check config file
    local repo_root=$(get_repo_root)
    local config_file="$repo_root/.infra/config"
    if [[ -f "$config_file" ]]; then
        # 读取配置，跳过注释行（以 # 开头）和空行
        local doc_dir=$(grep -vE "^\s*#" "$config_file" 2>/dev/null | grep -E "^DOC_DIR=" | head -n1 | cut -d'=' -f2- | sed "s/^[\"']//;s/[\"']$//" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
        if [[ -n "$doc_dir" ]]; then
            echo "$doc_dir"
            return
        fi
    fi
    
    # 3. Default value
    echo "omni-doc"
}

# Find feature directory by numeric prefix instead of exact branch match
# This allows multiple branches to work on the same spec (e.g., 004-fix-bug, 004-add-feature)
find_feature_dir_by_prefix() {
    local repo_root="$1"
    local branch_name="$2"
    local changes_dir="$repo_root/changes"

    # Extract numeric prefix from branch (e.g., "004" from "004-whatever")
    if [[ ! "$branch_name" =~ ^([0-9]{3})- ]]; then
        # If branch doesn't have numeric prefix, fall back to exact match
        echo "$changes_dir/$branch_name"
        return
    fi

    local prefix="${BASH_REMATCH[1]}"

    # Search for directories in changes/ that start with this prefix
    local matches=()
    if [[ -d "$changes_dir" ]]; then
        for dir in "$changes_dir"/"$prefix"-*; do
            if [[ -d "$dir" ]]; then
                matches+=("$(basename "$dir")")
            fi
        done
    fi

    # Handle results
    if [[ ${#matches[@]} -eq 0 ]]; then
        # No match found - return the branch name path (will fail later with clear error)
        echo "$changes_dir/$branch_name"
    elif [[ ${#matches[@]} -eq 1 ]]; then
        # Exactly one match - perfect!
        echo "$changes_dir/${matches[0]}"
    else
        # Multiple matches - this shouldn't happen with proper naming convention
        echo "ERROR: Multiple spec directories found with prefix '$prefix': ${matches[*]}" >&2
        echo "Please ensure only one spec directory exists per numeric prefix." >&2
        echo "$changes_dir/$branch_name"  # Return something to avoid breaking the script
    fi
}

get_feature_paths() {
    local repo_root=$(get_repo_root)
    local current_branch=$(get_current_branch "$repo_root")
    local has_git_repo="false"

    if has_git; then
        has_git_repo="true"
    fi

    # Use prefix-based lookup to support multiple branches per spec
    local feature_dir=$(find_feature_dir_by_prefix "$repo_root" "$current_branch")

    # Get document directory configuration
    local doc_dir=$(get_doc_dir)

    cat <<EOF
REPO_ROOT='$repo_root'
CURRENT_BRANCH='$current_branch'
HAS_GIT='$has_git_repo'
FEATURE_DIR='$feature_dir'
FEATURE_SPEC='$feature_dir/spec.md'
IMPL_DESIGN='$feature_dir/design.md'
TASKS='$feature_dir/tasks.md'
RESEARCH='$feature_dir/research.md'
DATA_MODEL='$feature_dir/data-model.md'
QUICKSTART='$feature_dir/quickstart.md'
CONTRACTS_DIR='$feature_dir/contracts'
DOC_DIR='$doc_dir'
DOC_SPECS_DIR='$repo_root/$doc_dir/specs'
DOC_RULES_DIR='$repo_root/$doc_dir/rules'
DOC_NAVIGATIONS_DIR='$repo_root/$doc_dir/navigations'
EOF
}

check_file() { [[ -f "$1" ]] && echo "  ✓ $2" || echo "  ✗ $2"; }
check_dir() { [[ -d "$1" && -n $(ls -A "$1" 2>/dev/null) ]] && echo "  ✓ $2" || echo "  ✗ $2"; }

# 规范化路径（转换为绝对路径）
# 参数:
#   $1: 要规范化的路径（相对路径、绝对路径或 ~ 开头的路径）
#   $2: 基准路径（用于相对路径转换，默认为 REPO_ROOT）
# 返回:
#   输出规范化后的绝对路径
normalize_path() {
    local path="$1"
    local base_path="${2:-$(get_repo_root)}"
    
    # 处理空路径
    if [[ -z "$path" ]]; then
        return 1
    fi
    
    # 展开 ~ 为用户主目录
    if [[ "$path" == ~* ]]; then
        path="${path/#\~/$HOME}"
    fi
    
    # 如果是绝对路径，直接返回（规范化后）
    if [[ "$path" == /* ]]; then
        # 使用 realpath 或 readlink -f 来规范化绝对路径
        if command -v realpath >/dev/null 2>&1; then
            realpath -m "$path" 2>/dev/null || echo "$path"
        elif command -v readlink >/dev/null 2>&1; then
            readlink -f "$path" 2>/dev/null || echo "$path"
        else
            # 手动处理 .. 和 .
            local result=""
            local IFS='/'
            local parts=()
            for part in $path; do
                if [[ "$part" == ".." ]]; then
                    # 移除最后一个部分
                    parts=("${parts[@]:0:$((${#parts[@]}-1))}")
                elif [[ "$part" != "." && -n "$part" ]]; then
                    parts+=("$part")
                fi
            done
            result="/$(IFS='/'; echo "${parts[*]}")"
            echo "$result"
        fi
        return
    fi
    
    # 处理相对路径（基于基准路径）
    local full_path="$base_path/$path"
    
    # 规范化路径（移除 .. 和 .，移除末尾的 /）
    if command -v realpath >/dev/null 2>&1; then
        realpath -m "$full_path" 2>/dev/null || echo "$full_path"
    elif command -v readlink >/dev/null 2>&1; then
        readlink -f "$full_path" 2>/dev/null || echo "$full_path"
    else
        # 手动处理相对路径
        local result=""
        local IFS='/'
        local parts=()
        for part in $full_path; do
            if [[ "$part" == ".." ]]; then
                # 移除最后一个部分
                parts=("${parts[@]:0:$((${#parts[@]}-1))}")
            elif [[ "$part" != "." && -n "$part" ]]; then
                parts+=("$part")
            fi
        done
        result="$(IFS='/'; echo "${parts[*]}")"
        # 移除末尾的 /
        result="${result%/}"
        echo "$result"
    fi
}

# 获取输出目录
# 参数:
#   $1: 用户指定的输出目录（可选）
#   $2: 要素类型的输出子目录（如 reverse/interfaces）
#   $3: CURRENT_BRANCH（当前分支名，用于判断是否在特性分支下）
#   $4: FEATURE_DIR（特性目录，如果存在）
#   $5: REPO_ROOT（仓库根目录）
# 返回:
#   输出规范化后的绝对路径（如果目录不存在会自动创建）
get_output_dir() {
    local user_output_dir="$1"
    local element_output_dir="$2"
    local current_branch="$3"
    local feature_dir="$4"
    local repo_root="$5"
    
    # 如果用户指定了输出目录，优先使用（转换为绝对路径）
    if [[ -n "$user_output_dir" ]]; then
        local output_dir
        output_dir=$(normalize_path "$user_output_dir" "$repo_root")
        # 自动创建目录（如果不存在）
        if [[ ! -d "$output_dir" ]]; then
            mkdir -p "$output_dir" || return 1
        fi
        echo "$output_dir"
        return
    fi
    
    # 构建默认输出目录
    local output_dir=""
    
    # 判断是否在特性分支下（分支名匹配 ^[0-9]{3}- 模式）
    if [[ -n "$current_branch" && "$current_branch" =~ ^[0-9]{3}- ]] && [[ -n "$feature_dir" ]]; then
        # 特性分支：输出到特性目录
        output_dir="$feature_dir/$element_output_dir"
    else
        # 非特性分支：输出到omni-doc目录
        output_dir="$repo_root/omni-doc/$element_output_dir"
    fi
    
    # 规范化路径（移除 .. 和 .，移除末尾的 /）
    output_dir=$(normalize_path "$output_dir" "$repo_root")
    
    # 自动创建目录（如果不存在）
    if [[ ! -d "$output_dir" ]]; then
        mkdir -p "$output_dir" || return 1
    fi
    
    echo "$output_dir"
}

# 等待批次完成（带超时和轮询）
# 参数:
#   $1: 仓库根目录路径
#   $2: 批次编号数组的JSON字符串，格式为 [1, 2, 3]
#   $3: 阶段类型（scenarios/interfaces/functions/call-chain/function-identification）
#   $4: 最大等待时间（分钟，默认30）
#   $5: 检查间隔（秒，默认30）
# 返回:
#   0: 所有批次完成
#   1: 超时或部分批次未完成
wait_for_batches_completion() {
    local repo_root="$1"
    local batch_numbers_json="$2"
    local stage_type="$3"
    local max_wait_minutes="${4:-30}"
    local check_interval_seconds="${5:-30}"

    # 验证参数
    if [[ -z "$repo_root" ]] || [[ -z "$batch_numbers_json" ]] || [[ -z "$stage_type" ]]; then
        echo "错误: wait_for_batches_completion 需要 repo_root, batch_numbers_json 和 stage_type 参数" >&2
        return 1
    fi

    # 获取脚本目录
    local script_dir="$(CDPATH="" cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    local verify_script="$script_dir/verify-batches-completion.sh"

    if [[ ! -f "$verify_script" ]]; then
        echo "错误: 批次验证脚本不存在: $verify_script" >&2
        return 1
    fi

    # 计算最大等待秒数
    local max_wait_seconds=$((max_wait_minutes * 60))
    local elapsed_seconds=0
    local iteration=0

    echo "开始等待批次完成，最多等待 ${max_wait_minutes} 分钟，每 ${check_interval_seconds} 秒检查一次..." >&2

    while [[ $elapsed_seconds -lt $max_wait_seconds ]]; do
        iteration=$((iteration + 1))
        
        # 调用验证脚本
        local verify_result
        if verify_result=$("$verify_script" --repo-root "$repo_root" --batch-numbers "$batch_numbers_json" --stage-type "$stage_type" 2>&1); then
            # 所有批次完成
            local completed_count
            completed_count=$(echo "$verify_result" | jq -r '.completed_count // 0')
            local total_count
            total_count=$(echo "$verify_result" | jq -r '.total_count // 0')
            echo "所有批次已完成！(${completed_count}/${total_count})" >&2
            return 0
        else
            # 部分批次未完成，检查详细信息
            local completed_count
            completed_count=$(echo "$verify_result" | jq -r '.completed_count // 0')
            local total_count
            total_count=$(echo "$verify_result" | jq -r '.total_count // 0')
            local remaining=$((total_count - completed_count))
            
            if [[ $iteration -eq 1 ]] || [[ $((iteration % 2)) -eq 0 ]]; then
                echo "等待中... 已完成 ${completed_count}/${total_count} 个批次，剩余 ${remaining} 个批次..." >&2
            fi
        fi

        # 等待指定间隔
        sleep "$check_interval_seconds"
        elapsed_seconds=$((elapsed_seconds + check_interval_seconds))
    done

    # 超时
    echo "错误: 等待批次完成超时（${max_wait_minutes} 分钟）" >&2
    
    # 输出最终状态
    local final_result
    final_result=$("$verify_script" --repo-root "$repo_root" --batch-numbers "$batch_numbers_json" --stage-type "$stage_type" 2>&1 || true)
    echo "$final_result" | jq '.' >&2
    
    return 1
}

# 获取项目名称
# 参数:
#   $1: 仓库根目录路径
# 返回:
#   项目名称，如果未配置则返回空字符串
get_project_name() {
    local repo_root="$1"
    
    # 1. 从环境变量读取（优先级最高）
    if [[ -n "${OMNISPEC_PROJECT_NAME:-}" ]]; then
        echo "$OMNISPEC_PROJECT_NAME"
        return 0
    fi
    
    # 2. 从配置文件读取
    local config_file="${repo_root}/.infra/config.yaml"
    if [[ -f "$config_file" ]]; then
        # 尝试从 YAML 文件中提取 project_name
        local project_name
        if command -v yq >/dev/null 2>&1; then
            project_name=$(yq -r '.project_name // empty' "$config_file" 2>/dev/null)
        elif command -v python3 >/dev/null 2>&1; then
            project_name=$(python3 -c "import yaml, sys; data = yaml.safe_load(open('$config_file')); print(data.get('project_name', '') if data else '')" 2>/dev/null)
        else
            # 简单的 grep 提取
            project_name=$(grep -E '^project_name\s*:' "$config_file" 2>/dev/null | sed 's/^project_name\s*:\s*\(.*\)/\1/' | sed "s/^['\"]//;s/['\"]$//")
        fi
        if [[ -n "$project_name" ]]; then
            echo "$project_name"
            return 0
        fi
    fi
    
    # 3. 从简单的文本文件读取
    local project_name_file="${repo_root}/.infra/project-name"
    if [[ -f "$project_name_file" ]]; then
        local project_name
        project_name=$(head -n 1 "$project_name_file" 2>/dev/null | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
        if [[ -n "$project_name" ]]; then
            echo "$project_name"
            return 0
        fi
    fi
    
    # 未找到项目名称
    return 1
}

# 查找模板文件（支持按项目查找）
# 参数:
#   $1: 模板文件名（如 reverse-interface-detail-template.md）
#   $2: 仓库根目录路径
#   $3: 用户指定的模板路径（可选）
#   $4: OmniSpec 根目录路径（可选，用于查找系统默认模板）
# 返回:
#   输出模板文件的绝对路径，如果未找到则返回非零退出码
find_template_file() {
    local template_filename="$1"
    local repo_root="$2"
    local user_template="${3:-}"
    local omnispec_root="${4:-}"
    
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
    
    # 2. 项目特定模板（如果配置了项目名称）
    local project_name
    if project_name=$(get_project_name "$repo_root" 2>/dev/null); then
        local project_template="${repo_root}/.infra/templates/${project_name}/${template_filename}"
        searched_paths+=("$project_template")
        if [[ -f "$project_template" ]]; then
            echo "$project_template"
            return 0
        fi
    fi
    
    # 3. 项目根目录下的默认模板（向后兼容）
    local project_default_template="${repo_root}/.infra/templates/${template_filename}"
    searched_paths+=("$project_default_template")
    if [[ -f "$project_default_template" ]]; then
        echo "$project_default_template"
        return 0
    fi
    
    # 4. 项目根目录下的 default 子目录模板
    local project_default_dir_template="${repo_root}/.infra/templates/default/${template_filename}"
    searched_paths+=("$project_default_dir_template")
    if [[ -f "$project_default_dir_template" ]]; then
        echo "$project_default_dir_template"
        return 0
    fi
    
    # 5. 系统默认模板（OmniSpec 根目录）
    if [[ -n "$omnispec_root" ]]; then
        local system_default_template="${omnispec_root}/specify/templates/default/${template_filename}"
        searched_paths+=("$system_default_template")
        if [[ -f "$system_default_template" ]]; then
            echo "$system_default_template"
            return 0
        fi
        
        # 向后兼容：系统根目录下的模板
        local system_template="${omnispec_root}/specify/templates/${template_filename}"
        searched_paths+=("$system_template")
        if [[ -f "$system_template" ]]; then
            echo "$system_template"
            return 0
        fi
    fi
    
    # 所有模板都找不到，报错
    echo "错误: 模板文件未找到: $template_filename" >&2
    echo "已查找的路径：" >&2
    for path in "${searched_paths[@]}"; do
        echo "  - $path" >&2
    done
    return 1
}

# 判断是否需要用户确认
# 参数: 从 $ARGUMENTS 环境变量或命令行参数中读取
# 返回: 0 需要确认, 1 不需要确认
should_require_confirmation() {
    local args="${1:-${ARGUMENTS:-}}"
    
    # 如果指定了 --non-interactive 或 --yes，不需要确认
    if [[ "$args" =~ --non-interactive ]] || [[ "$args" =~ --yes ]]; then
        return 1
    fi
    
    # 解析 --interactive yes/no 格式
    # 支持格式：--interactive yes、--interactive no、--interactive（默认yes）
    if [[ "$args" =~ --interactive[[:space:]]+no ]]; then
        # --interactive no 明确禁用交互模式
        return 1
    elif [[ "$args" =~ --interactive[[:space:]]+yes ]] || [[ "$args" =~ --interactive[[:space:]]*$ ]]; then
        # --interactive yes 或 --interactive（无参数，默认yes）启用交互模式
        return 0
    fi
    
    # 默认：不需要确认（全自动模式）
    return 1
}

