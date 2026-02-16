#!/usr/bin/env bash

set -e

# ============================================================================
# 颜色和输出函数
# ============================================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_error() {
    echo -e "${RED}错误: $1${NC}" >&2
}

print_success() {
    echo -e "${GREEN}成功: $1${NC}"
}

print_info() {
    echo -e "${YELLOW}信息: $1${NC}"
}

# ============================================================================
# 参数校验
# ============================================================================

usage() {
    echo "用法: $0 <zip文件路径>"
    echo "  下载官网最新版本: https://github.com/Linfee/spec-kit-cn  spec-kit中文版"
    echo "  文件名格式: spec-kit-template-claude-sh-*.zip"
    echo ""
    echo "示例:"
    echo "  $0 spec-kit-template-claude-sh-0.0.86.zip"
    echo "  $0 /media/vdc/sdd/omnispec/外部版本/2025-12-01版本对齐/spec-kit-template-claude-sh-0.0.86.zip"
    exit 1
}

validate_arguments() {
    if [ $# -eq 0 ]; then
        print_error "未提供zip文件路径"
        usage
    fi
}

# ============================================================================
# 文件存在性检查
# ============================================================================

check_file_exists() {
    local file_path="$1"
    if [ ! -f "$file_path" ]; then
        print_error "文件不存在: $file_path"
        exit 1
    fi
}

# ============================================================================
# 文件名格式校验
# ============================================================================

validate_filename_format() {
    local filename="$1"
    if [[ ! "$filename" =~ ^spec-kit-template-claude-sh.*\.zip$ ]]; then
        print_error "文件名格式不匹配，需要符合格式: spec-kit-template-claude-sh*.zip"
        print_error "当前文件名: $filename"
        exit 1
    fi
    print_success "文件名格式校验通过: $filename"
}

# ============================================================================
# 工具依赖检查
# ============================================================================

check_unzip_available() {
    if ! command -v unzip &> /dev/null; then
        print_error "未找到unzip命令，请先安装"
        exit 1
    fi
}

# ============================================================================
# 文件解压
# ============================================================================

extract_zip_file() {
    local zip_file="$1"
    local zip_dir="$2"
    local expected_dir="$3"
    local target_dir="${zip_dir}/${expected_dir}"
    
    # 检查目标目录是否已存在
    if [ -d "$target_dir" ]; then
        print_info "目标目录已存在: $target_dir"
        print_info "删除现有目录..."
        rm -rf "$target_dir"
        print_success "已删除现有目录"
    fi
    
    print_info "开始解压文件到目录: $target_dir"
    # 创建目标目录并解压到该目录中
    mkdir -p "$target_dir"
    # 使用 -o 选项自动覆盖，-q 静默模式，-d 指定目标目录
    if unzip -o -q "$zip_file" -d "$target_dir"; then
        print_success "解压完成"
    else
        print_error "解压失败"
        exit 1
    fi
}

# ============================================================================
# 目录操作
# ============================================================================

get_extracted_directory_name() {
    local filename="$1"
    # 在原始目录名后增加 -local 后缀，例如：
    # spec-kit-template-claude-sh-0.0.85.zip -> spec-kit-template-claude-sh-0.0.85-local
    local base_name="${filename%.zip}"
    echo "${base_name}-local"
}

detect_extracted_directory() {
    local zip_file="$1"
    local zip_dir="$2"
    local expected_dir="$3"
    local target_dir="${zip_dir}/${expected_dir}"
    
    # 首先检查预期的目录是否存在
    if [ -d "$target_dir" ]; then
        echo "$target_dir"
        return 0
    fi
    
    # 如果不存在，尝试从zip文件内容中检测第一个顶级目录
    print_info "检测解压后的实际目录名..."
    
    # 方法1: 从zip文件列表获取第一个顶级目录
    local first_entry=$(unzip -l "$zip_file" 2>/dev/null | \
        awk 'NR>3 && NF>=4 {print $NF}' | \
        grep -v '^$' | \
        head -1 | \
        cut -d'/' -f1)
    
    if [ -n "$first_entry" ]; then
        local detected_dir="${zip_dir}/${first_entry}"
        if [ -d "$detected_dir" ]; then
            print_info "检测到目录: $detected_dir"
            echo "$detected_dir"
            return 0
        fi
    fi
    
    # 方法2: 列出zip文件所在目录下的所有目录，取第一个
    local first_dir=$(find "$zip_dir" -maxdepth 1 -type d ! -name "$(basename "$zip_dir")" ! -name '.' | sed "s|^${zip_dir}/||" | sort | head -1)
    if [ -n "$first_dir" ]; then
        local detected_dir="${zip_dir}/${first_dir}"
        if [ -d "$detected_dir" ]; then
            print_info "使用zip文件所在目录下的第一个目录: $detected_dir"
            echo "$detected_dir"
            return 0
        fi
    fi
    
    # 如果都找不到，返回预期的目录名（让后续检查报错）
    echo "$target_dir"
    return 1
}

check_directory_exists() {
    local dir_path="$1"
    if [ ! -d "$dir_path" ]; then
        print_error "目录不存在: $dir_path"
        exit 1
    fi
}

enter_directory() {
    local dir_path="$1"
    print_info "进入目录: $dir_path"
    cd "$dir_path" || exit 1
}

# ============================================================================
# 目录重命名
# ============================================================================

rename_directory_if_exists() {
    local source_dir="$1"
    local target_dir="$2"
    
    if [ -d "$source_dir" ]; then
        print_info "重命名 $source_dir -> $target_dir"
        mv "$source_dir" "$target_dir"
        print_success "$source_dir 已重命名为 $target_dir"
    elif [ -d "$target_dir" ]; then
        print_info "$target_dir 目录已存在，跳过重命名"
    else
        print_error "$source_dir 目录不存在"
        exit 1
    fi
}

rename_claude_to_agent() {
    rename_directory_if_exists ".claude" "agent"
}

rename_specify_directory() {
    rename_directory_if_exists ".specify" "src/specify"
}

# ============================================================================
# 文件重命名
# ============================================================================

rename_speckit_files() {
    local commands_dir="agent/commands"
    
    if [ ! -d "$commands_dir" ]; then
        print_info "agent/commands 目录不存在，跳过文件重命名"
        return 0
    fi
    
    print_info "查找 agent/commands/speckit.*.md 文件"
    local renamed_count=0
    
    for file in "$commands_dir"/speckit.*.md; do
        # 检查文件是否存在（通配符未匹配时会返回字面量）
        if [ -f "$file" ]; then
            local basename=$(basename "$file")
            local new_name="${basename/speckit/omni}"
            local new_path="$commands_dir/$new_name"
            
            print_info "重命名: $basename -> $new_name"
            mv "$file" "$new_path"
            renamed_count=$((renamed_count + 1))
        fi
    done
    
    if [ $renamed_count -gt 0 ]; then
        print_success "已重命名 $renamed_count 个文件"
    else
        print_info "未找到匹配的文件: agent/commands/speckit.*.md"
    fi
}

rename_plan_files() {
    print_info "重命名 plan 相关文件为 design"
    local renamed_count=0
    
    # agent/commands/omni.plan.md -> agent/commands/omni.design.md
    if [ -f "agent/commands/omni.plan.md" ]; then
        print_info "重命名: agent/commands/omni.plan.md -> agent/commands/omni.design.md"
        mv "agent/commands/omni.plan.md" "agent/commands/omni.design.md"
        renamed_count=$((renamed_count + 1))
    fi
    
    # src/specify/templates/plan-template.md -> src/specify/templates/design-template.md
    if [ -f "src/specify/templates/plan-template.md" ]; then
        print_info "重命名: src/specify/templates/plan-template.md -> src/specify/templates/design-template.md"
        mv "src/specify/templates/plan-template.md" "src/specify/templates/design-template.md"
        renamed_count=$((renamed_count + 1))
    fi
    
    # src/specify/scripts/bash/setup-plan.sh -> src/specify/scripts/bash/setup-design.sh
    if [ -f "src/specify/scripts/bash/setup-plan.sh" ]; then
        print_info "重命名: src/specify/scripts/bash/setup-plan.sh -> src/specify/scripts/bash/setup-design.sh"
        mv "src/specify/scripts/bash/setup-plan.sh" "src/specify/scripts/bash/setup-design.sh"
        renamed_count=$((renamed_count + 1))
    fi
    
    if [ $renamed_count -gt 0 ]; then
        print_success "已重命名 $renamed_count 个 plan 文件"
    else
        print_info "未找到需要重命名的 plan 文件"
    fi
}

# ============================================================================
# 文件内容替换
# ============================================================================

# 收集需要处理的文件（agent 和 specify 目录下的指定类型文件）
collect_target_files() {
    local files_to_process=()
    
    if [ -d "agent" ]; then
        while IFS= read -r -d '' file; do
            files_to_process+=("$file")
        done < <(find agent -type f \( -name "*.md" -o -name "*.sh" -o -name "*.txt" -o -name "*.json" -o -name "*.yaml" -o -name "*.yml" \) -print0 2>/dev/null)
    fi
    
    if [ -d "src/specify" ]; then
        while IFS= read -r -d '' file; do
            files_to_process+=("$file")
        done < <(find src/specify -type f \( -name "*.md" -o -name "*.sh" -o -name "*.txt" -o -name "*.json" -o -name "*.yaml" -o -name "*.yml" \) -print0 2>/dev/null)
    fi
    
    # 返回文件数组（通过 echo 输出，调用者需要捕获）
    printf '%s\0' "${files_to_process[@]}"
}

# 通用关键字替换规则：
# 每一项格式为 "原字符串=>新字符串"
# 特殊规则：如果原字符串包含 "plan"（不区分大小写），将自动应用大小写保持替换
# 例如："plan" 会自动替换为 plan/Plan/PLAN -> design/Design/DESIGN
# 你可以在这里按需增加/修改规则，例如：
#   "A=>A1"  "foo=>bar"
REPLACE_RULES=(
    "speckit.=>omni."
    "PLANS=>DESIGNS"
    "_PLAN=>_DESIGN"
    "_Plan=>_Design"
    "_plan=>_design"
    "plan_=>design_"
    "plan=>design"
)

apply_replace_rules_in_files() {
    # 收集需要处理的文件
    local files_to_process=()
    while IFS= read -r -d '' file; do
        files_to_process+=("$file")
    done < <(collect_target_files)

    if [ ${#files_to_process[@]} -eq 0 ] || [ ${#REPLACE_RULES[@]} -eq 0 ]; then
        print_info "无可处理文件或替换规则，跳过通用内容替换"
        return 0
    fi

    local total_replaced_files=0
    local has_plan_rule=0

    # 检查是否有 plan 相关的规则（用于大小写保持替换）
    for rule in "${REPLACE_RULES[@]}"; do
        local from="${rule%%=>*}"
        if [[ "$from" =~ [Pp][Ll][Aa][Nn] ]]; then
            has_plan_rule=1
            break
        fi
    done

    # 遍历文件
    for file in "${files_to_process[@]}"; do
        [ -f "$file" ] || continue

        local need_process=0
        local need_plan_replace=0

        # 先检查是否至少命中一条规则，避免无意义写入
        for rule in "${REPLACE_RULES[@]}"; do
            local from="${rule%%=>*}"
            if grep -q -- "$from" "$file" 2>/dev/null; then
                need_process=1
                # 检查是否需要 plan 的大小写保持替换
                if [ "$has_plan_rule" -eq 1 ] && grep -qi "\bplan\b" "$file" 2>/dev/null; then
                    need_plan_replace=1
                fi
                break
            fi
        done

        # 如果文件包含 plan（不区分大小写），也需要处理
        if [ "$has_plan_rule" -eq 1 ] && grep -qi "\bplan\b" "$file" 2>/dev/null; then
            need_process=1
            need_plan_replace=1
        fi

        [ "$need_process" -eq 1 ] || continue

        print_info "通用替换处理文件: $file"

        if command -v perl &> /dev/null; then
            # 使用 perl 进行替换
            if [ "$need_plan_replace" -eq 1 ]; then
                # 先进行 plan 的大小写保持替换
                perl -i -pe '
                    s/\bPLAN\b/DESIGN/g;
                    s/\bPlan\b/Design/g;
                    s/\bplan\b/design/g;
                ' "$file"
            fi
            
            # 然后应用其他规则
            for rule in "${REPLACE_RULES[@]}"; do
                local from="${rule%%=>*}"
                local to="${rule#*=>}"
                # 跳过 "plan=>design" 规则（已经通过大小写保持替换处理）
                # 但保留其他包含 plan 的规则（如 "_PLAN=>_DESIGN"、"plan_=>design_" 等）
                if [[ "$rule" != "plan=>design" ]]; then
                    perl -i -pe "s/\Q${from}\E/${to}/g" "$file"
                fi
            done
        else
            # 无 perl 时，用临时文件 + sed 依次替换
            local tmp="$(mktemp)"
            cp "$file" "$tmp"
            
            if [ "$need_plan_replace" -eq 1 ]; then
                # 先进行 plan 的大小写保持替换
                local tmp_plan="$(mktemp)"
                sed -e 's/\bPLAN\b/DESIGN/g' \
                    -e 's/\bPlan\b/Design/g' \
                    -e 's/\bplan\b/design/g' \
                    "$tmp" > "$tmp_plan"
                mv "$tmp_plan" "$tmp"
            fi
            
            # 然后应用其他规则
            for rule in "${REPLACE_RULES[@]}"; do
                local from="${rule%%=>*}"
                local to="${rule#*=>}"
                # 跳过 "plan=>design" 规则（已经通过大小写保持替换处理）
                # 但保留其他包含 plan 的规则（如 "_PLAN=>_DESIGN"、"plan_=>design_" 等）
                if [[ "$rule" != "plan=>design" ]]; then
                    local tmp2="$(mktemp)"
                    sed "s|${from//|/\\|}|${to//|/\\|}|g" "$tmp" > "$tmp2"
                    mv "$tmp2" "$tmp"
                fi
            done
            mv "$tmp" "$file"
        fi

        total_replaced_files=$((total_replaced_files + 1))
    done

    if [ $total_replaced_files -gt 0 ]; then
        print_success "通用替换已处理 $total_replaced_files 个文件"
    else
        print_info "未找到需要进行通用替换的文件"
    fi
}


# ============================================================================
# 主流程
# ============================================================================

main() {
    # 参数校验
    validate_arguments "$@"
    local zip_file="$1"
    
    # 文件存在性检查
    check_file_exists "$zip_file"
    
    # 获取zip文件的绝对路径和所在目录
    if [[ "$zip_file" = /* ]]; then
        # 已经是绝对路径
        local zip_abs_path="$zip_file"
    else
        # 相对路径，转换为绝对路径
        local zip_abs_path="$(cd "$(dirname "$zip_file")" && pwd)/$(basename "$zip_file")"
    fi
    local zip_dir="$(dirname "$zip_abs_path")"
    
    # 获取文件名并校验格式
    local filename=$(basename "$zip_abs_path")
    validate_filename_format "$filename"
    
    # 检查工具依赖
    check_unzip_available
    
    # 获取预期的解压后目录名
    local expected_dir=$(get_extracted_directory_name "$filename")
    
    # 解压文件到zip文件所在目录（先检查并处理已存在的目录）
    extract_zip_file "$zip_abs_path" "$zip_dir" "$expected_dir"
    
    # 检测实际的解压后目录名（可能和预期不同）
    local dir_name=$(detect_extracted_directory "$zip_abs_path" "$zip_dir" "$expected_dir")
    
    # 检查解压后的目录是否存在并进入
    check_directory_exists "$dir_name"
    enter_directory "$dir_name"
    
    # 重命名目录
    rename_claude_to_agent
    rename_specify_directory
    
    # 重命名文件
    rename_speckit_files
    rename_plan_files
    
    # 通用内容关键字替换（包括 speckit. -> omni.、plan -> design 等，支持大小写保持）
    apply_replace_rules_in_files
    
    # 完成
    print_success "所有操作完成！"
    print_info "当前目录: $(pwd)"
}

# 执行主流程
main "$@"
