#!/bin/bash

# OmniSpec 安装脚本
# 功能：将 agent 和 specify 目录复制到目标代码工程路径
# 详细使用说明请运行: ./install.sh -h 或 ./install.sh --help

set -e  # 遇到错误立即退出

# 显示使用说明
show_usage() {
    cat << EOF
OmniSpec 安装脚本

使用方法:
  $0 <目标AGENT目录名> <目标代码工程路径> [项目名称]

参数说明:
  <目标AGENT目录名>  (必需)
      指定 agent 目录的目标名称
      如果输入的名称不带点号，会自动添加点号前缀
      例如:
        - 输入 "claude"   -> 复制到 .claude
        - 输入 ".claude"  -> 复制到 .claude (不会重复添加点号)
        - 输入 "cursor"  -> 复制到 .cursor

  <目标代码工程路径>  (必需)
      目标代码工程的绝对路径或相对路径
      例如: /path/to/project 或 ./myproject

  [项目名称]  (可选)
      指定项目名称，用于选择对应的 skill 项目目录下的 SKILL.md
      如果指定，会优先使用 {skill-name}/{项目名称}/SKILL.md
      如果项目目录不存在，会回退到 default 目录或根目录
      例如: example-project

示例:
  $0 claude /path/to/project
  $0 .claude /path/to/project
  $0 cursor /path/to/project
  $0 claude /path/to/project example-project

功能说明:
  1. 检查源目录 (agent 和 specify) 是否存在
  2. 将 agent 目录复制到目标工程的 <目标AGENT目录名> 目录（增量覆盖，保留目标目录中的额外文件）
     - 包括 commands 目录（命令定义文件）
     - 包括 agents 目录（agent 定义文件，与 commands 目录平级）
     - 注意：skills 目录会被单独处理，根据项目参数选择对应的 SKILL.md
  3. 安装 skills 目录（根据项目参数选择对应的 SKILL.md）
     - 如果指定了项目名称，优先使用 {skill-name}/{项目名称}/SKILL.md
     - 如果项目目录不存在，回退到 {skill-name}/default/SKILL.md
     - 如果 default 目录也不存在，使用 {skill-name}/SKILL.md
     - 最终安装到 {target}/.claude/skills/{skill-name}/SKILL.md（不嵌套项目路径）
  4. 将 specify 目录复制到目标工程的 .specify 目录（先删除再完整拷贝）
  5. 安装模板文件（根据项目参数选择对应的模板）
     - 如果指定了项目名称，优先使用 templates/{项目名称}/ 目录下的模板
     - 如果项目目录不存在，回退到 templates/default/ 目录下的模板
     - 最终安装到 {target}/.specify/templates/ 目录（扁平结构，不嵌套项目路径）
  6. 生成用户注入配置模板（user_input目录和示例文件）
  7. 自动设置 .specify/scripts 目录下所有 .sh 和 .ps1 脚本的可执行权限
  8. 如果目标目录已存在，会提示用户确认是否覆盖

注意事项:
  - 如果目标路径不存在，脚本会自动创建
  - 如果目标目录已存在，会询问是否覆盖
  - 优先使用 rsync 进行复制（如果可用），否则使用 cp
  - agent 目录采用增量覆盖模式（不删除目标目录中的额外文件）
  - specify 目录采用先删除再完整拷贝模式（会删除目标目录中的所有文件后重新拷贝）

选项:
  -h, --help    显示此帮助信息

EOF
}

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# SOURCE_DIR 指向 build 的父目录（omnispec-sh），以便找到 agent 和 specify 目录
SOURCE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

SOURCE_AGENT_DIR="$SOURCE_DIR/src/agent"
SOURCE_SPECIFY_DIR="$SOURCE_DIR/src/specify"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 打印信息
info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

# 检查源目录是否存在
check_source_dirs() {
    if [ ! -d "$SOURCE_AGENT_DIR" ]; then
        error "agent 目录不存在: $SOURCE_AGENT_DIR"
        exit 1
    fi
    
    if [ ! -d "$SOURCE_SPECIFY_DIR" ]; then
        error "specify 目录不存在: $SOURCE_SPECIFY_DIR"
        exit 1
    fi
    
    info "源目录检查通过"
}

# 获取目标路径
get_target_path() {
    if [ -z "$1" ]; then
        error "未提供目标代码工程路径"
        error "使用 '$0 -h' 或 '$0 --help' 查看详细使用说明"
        exit 1
    fi
    
    local input_path="$1"
    
    # 如果路径不存在，创建它
    if [ ! -d "$input_path" ]; then
        info "目标路径不存在，正在创建: $input_path" >&2
        mkdir -p "$input_path"
        if [ $? -ne 0 ]; then
            error "无法创建目标路径: $input_path"
            exit 1
        fi
        info "已创建目标路径: $input_path" >&2
    fi
    
    # 转换为绝对路径
    local abs_path="$(cd "$input_path" && pwd)"
    info "代码工程路径: $abs_path" >&2
    echo "$abs_path"
}

# 复制目录（完全同步，删除目标目录中的额外文件）
copy_directory_sync() {
    local src="$1"
    local dst="$2"
    local name="$3"
    
    if [ -d "$dst" ]; then
        warn "$name 目录已存在，将被完全同步（会删除目标目录中的额外文件）: $dst"
        read -p "是否继续？(y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            warn "跳过 $name 目录的复制"
            return
        fi
    fi
    
    info "正在复制 $name 目录..."
    info "  源路径: $src"
    info "  目标路径: $dst"
    
    # 使用 rsync 或 cp 复制
    if command -v rsync &> /dev/null; then
        rsync -av --delete "$src/" "$dst/"
    else
        rm -rf "$dst"
        cp -r "$src" "$dst"
    fi
    
    info "$name 目录复制完成"
}

# 复制目录（增量覆盖，保留目标目录中的额外文件）
copy_directory_incremental() {
    local src="$1"
    local dst="$2"
    local name="$3"
    local exclude_pattern="$4"  # 排除模式（可选）
    
    if [ -d "$dst" ]; then
        warn "$name 目录已存在，将被增量覆盖（保留目标目录中的额外文件）: $dst"
        read -p "是否继续？(y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            warn "跳过 $name 目录的复制"
            return
        fi
    fi
    
    info "正在复制 $name 目录..."
    info "  源路径: $src"
    info "  目标路径: $dst"
    
    # 使用 rsync 或 cp 复制（增量覆盖）
    if command -v rsync &> /dev/null; then
        if [ -n "$exclude_pattern" ]; then
            rsync -av --exclude="$exclude_pattern" "$src/" "$dst/"
        else
            rsync -av "$src/" "$dst/"
        fi
    else
        mkdir -p "$dst"
        if [ -n "$exclude_pattern" ]; then
            # 使用 find 和 cp 排除指定目录
            find "$src" -mindepth 1 -maxdepth 1 ! -name "$exclude_pattern" -exec cp -r {} "$dst/" \; 2>/dev/null || true
        else
            cp -r "$src"/* "$dst/" 2>/dev/null || true
        fi
    fi
    
    info "$name 目录复制完成"
}

# 复制目录（先删除再完整拷贝）
copy_directory_replace() {
    local src="$1"
    local dst="$2"
    local name="$3"
    
    if [ -d "$dst" ]; then
        warn "$name 目录已存在，将被删除后重新拷贝（会删除目标目录中的所有文件）: $dst"
        read -p "是否继续？(y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            warn "跳过 $name 目录的复制"
            return
        fi
    fi
    
    info "正在复制 $name 目录..."
    info "  源路径: $src"
    info "  目标路径: $dst"
    
    # 先删除目标目录（如果存在）
    if [ -d "$dst" ]; then
        info "正在删除目标目录: $dst"
        rm -rf "$dst"
    fi
    
    # 完整拷贝
    if command -v rsync &> /dev/null; then
        rsync -av "$src/" "$dst/"
    else
        cp -r "$src" "$dst"
    fi
    
    info "$name 目录复制完成"
}

# 设置脚本可执行权限
set_script_permissions() {
    local target_path="$1"
    local scripts_base_dir="$target_path/.specify/scripts"
    
    if [ ! -d "$scripts_base_dir" ]; then
        warn ".specify/scripts 目录不存在: $scripts_base_dir"
        return
    fi
    
    info "正在设置脚本可执行权限..."
    info "  目标目录: $scripts_base_dir"
    
    # 查找所有 .sh 和 .ps1 文件并设置可执行权限
    local count=0
    while IFS= read -r -d '' file; do
        chmod +x "$file"
        count=$((count + 1))
    done < <(find "$scripts_base_dir" -type f \( -name "*.sh" -o -name "*.ps1" \) -print0 2>/dev/null)
    
    if [ $count -gt 0 ]; then
        info "已为 $count 个脚本文件设置可执行权限"
    else
        warn "未找到任何 .sh 或 .ps1 文件"
    fi
}

# 更新 agent 的配置文件
update_agent_config() {
    local target_path="$1"
    local target_agent="$2"
    local design_file="$target_path/$target_agent/commands/omni.design.md"
    
    if [ ! -f "$design_file" ]; then
        warn "omni.design.md 文件不存在: $design_file"
        return
    fi
    
    # 从 target_agent 中提取 agent 名称（去掉点号前缀）
    local agent_name="${target_agent#.}"
    
    # 根据 agent 类型确定替换参数
    # cursor -> cursor-agent，其他直接使用原名称
    local replace_param
    if [ "$agent_name" = "cursor" ]; then
        replace_param="cursor-agent"
    else
        replace_param="$agent_name"
    fi
    
    info "正在更新 $agent_name agent 配置文件..."
    info "  目标文件: $design_file"
    info "  替换参数: $replace_param"
    
    # 备份原文件
    local backup_file="${design_file}.bak"
    cp "$design_file" "$backup_file"
    
    # 执行替换：只替换 agent 名称
    # 匹配格式：.specify/scripts/{{OS_NAME}}/update-agent-context.{{OS_EXT}} --agent-type claude
    # 规则1: 替换 --agent-type 后面的 agent 名称（只替换一次，避免重复）
    sed -i \
        -e "s|\(\.specify/scripts/[^[:space:]]*update-agent-context\.[^[:space:]]* --agent-type \)[a-z-]*|\1$replace_param|g" \
        "$design_file"
    
    # 规则2: 处理旧格式（没有 --agent-type），添加 --agent-type 参数
    # 只处理不包含 --agent-type 的行，且脚本路径后直接跟 agent 名称的情况
    sed -i \
        -e "/--agent-type/! { s|\(\.specify/scripts/[^[:space:]]*update-agent-context\.[^[:space:]]*\)[[:space:]]\+[a-z-]\+|\1 --agent-type $replace_param|g; }" \
        "$design_file"
    
    # 规则3: 如果行尾没有参数，添加 --agent-type 参数
    sed -i \
        -e "/--agent-type/! { s|\(\.specify/scripts/[^[:space:]]*update-agent-context\.[^[:space:]]*\)[[:space:]]*$|\1 --agent-type $replace_param|g; }" \
        "$design_file"
    
    # 检查是否有修改
    if ! diff -q "$design_file" "$backup_file" > /dev/null; then
        rm "$backup_file"
        info "$agent_name agent 配置文件更新完成"
    else
        mv "$backup_file" "$design_file"
        warn "未找到需要替换的内容"
    fi
}

# 验证 agents 目录是否被正确复制
verify_agents_directory() {
    local target_path="$1"
    local target_agent="$2"
    local target_agent_dir="$target_path/$target_agent"
    local target_agents_dir="$target_agent_dir/agents"
    
    if [ ! -d "$target_agents_dir" ]; then
        warn "agents 目录不存在，正在尝试修复..."
        # 如果 agents 目录不存在，但源目录存在，则复制它
        local source_agents_dir="$SOURCE_AGENT_DIR/agents"
        if [ -d "$source_agents_dir" ]; then
            info "正在复制 agents 目录..."
            if command -v rsync &> /dev/null; then
                rsync -av "$source_agents_dir/" "$target_agents_dir/"
            else
                mkdir -p "$target_agents_dir"
                cp -r "$source_agents_dir"/* "$target_agents_dir/" 2>/dev/null || true
            fi
            info "agents 目录已复制: $target_agents_dir"
        else
            warn "源 agents 目录不存在，跳过: $source_agents_dir"
        fi
    else
        info "验证通过：agents 目录已存在: $target_agents_dir"
    fi
}

# 安装模板文件
install_templates() {
    local source_specify_dir="$1"
    local target_path="$2"
    local project_name="$3"  # 项目名称（可选）
    
    local source_templates_dir="$source_specify_dir/templates"
    local target_templates_dir="$target_path/.specify/templates"
    
    # 检查源 templates 目录是否存在
    if [ ! -d "$source_templates_dir" ]; then
        warn "源 templates 目录不存在，跳过: $source_templates_dir"
        return
    fi
    
    info "正在安装模板文件..."
    info "  源路径: $source_templates_dir"
    info "  目标路径: $target_templates_dir"
    if [ -n "$project_name" ]; then
        info "  项目名称: $project_name"
    fi
    
    # 删除目标 templates 目录（如果存在），准备重新安装
    if [ -d "$target_templates_dir" ]; then
        info "  删除现有模板目录，准备重新安装..."
        rm -rf "$target_templates_dir"
    fi
    
    # 确保目标 templates 目录存在
    mkdir -p "$target_templates_dir"
    
    # 确定 default 模板目录
    local default_templates_dir="$source_templates_dir/default"
    if [ ! -d "$default_templates_dir" ]; then
        warn "  default 模板目录不存在: templates/default/"
        return
    fi
    
    # 确定项目模板目录（如果指定了项目名称）
    local project_templates_dir=""
    if [ -n "$project_name" ]; then
        project_templates_dir="$source_templates_dir/$project_name"
        if [ -d "$project_templates_dir" ]; then
            info "  项目模板目录存在: templates/$project_name/"
        else
            info "  项目模板目录不存在: templates/$project_name/，将全部使用 default 目录"
        fi
    fi
    
    # 第一步：复制 templates 根目录下的所有模板文件（排除 default 和项目目录）
    # 优先级：根目录文件 > 项目目录 > default 目录
    local root_template_count=0
    local root_template_installed=0
    
    info "  第一步：复制 templates 根目录下的模板文件..."
    while IFS= read -r -d '' template_file; do
        # 排除 default 目录和项目目录下的文件
        local file_dir="$(dirname "$template_file")"
        if [ "$file_dir" = "$default_templates_dir" ]; then
            continue
        fi
        if [ -n "$project_templates_dir" ] && [ "$file_dir" = "$project_templates_dir" ]; then
            continue
        fi
        
        root_template_count=$((root_template_count + 1))
        local template_filename="$(basename "$template_file")"
        local target_template_file="$target_templates_dir/$template_filename"
        
        # 复制根目录的模板文件
        if cp "$template_file" "$target_template_file" 2>/dev/null; then
            root_template_installed=$((root_template_installed + 1))
            info "  已安装（根目录）: $template_filename"
        else
            warn "  复制失败: $template_filename"
        fi
    done < <(find "$source_templates_dir" -maxdepth 1 -type f \( -name "*.md" -o -name "*.yaml" -o -name "*.json" \) -print0 2>/dev/null)
    
    if [ $root_template_count -gt 0 ]; then
        info "  根目录模板安装完成: $root_template_installed/$root_template_count 个模板已安装"
    fi
    
    # 第二步：从 default 目录获取所有模板文件列表，按优先级复制
    # 优先级：项目目录 > default 目录（根目录文件已复制，如果存在则跳过）
    local template_count=0
    local template_installed=0
    local project_template_count=0
    
    info "  第二步：安装 default 目录下的模板文件（按优先级）..."
    while IFS= read -r -d '' template_file; do
        template_count=$((template_count + 1))
        local template_filename="$(basename "$template_file")"
        local target_template_file="$target_templates_dir/$template_filename"
        local source_template_file=""
        
        # 如果目标文件已存在（来自根目录），跳过
        if [ -f "$target_template_file" ]; then
            info "  跳过（根目录已存在）: $template_filename"
            continue
        fi
        
        # 优先级：项目目录 > default 目录
        # 如果项目目录存在且包含该模板文件，使用项目目录的文件
        if [ -n "$project_templates_dir" ] && [ -d "$project_templates_dir" ]; then
            local project_template_file="$project_templates_dir/$template_filename"
            if [ -f "$project_template_file" ]; then
                source_template_file="$project_template_file"
                project_template_count=$((project_template_count + 1))
            fi
        fi
        
        # 如果项目目录中没有该文件，使用 default 目录的文件
        if [ -z "$source_template_file" ]; then
            source_template_file="$template_file"
        fi
        
        # 复制模板文件
        if cp "$source_template_file" "$target_template_file" 2>/dev/null; then
            template_installed=$((template_installed + 1))
            if [ "$source_template_file" != "$template_file" ]; then
                info "  已安装（项目特定）: $template_filename"
            else
                info "  已安装（默认）: $template_filename"
            fi
        else
            warn "  复制失败: $template_filename"
        fi
    done < <(find "$default_templates_dir" -maxdepth 1 -type f \( -name "*.md" -o -name "*.yaml" -o -name "*.json" \) -print0 2>/dev/null)
    
    local total_installed=$((root_template_installed + template_installed))
    local total_count=$((root_template_count + template_count))
    
    if [ $total_count -gt 0 ]; then
        info "模板安装完成: $total_installed/$total_count 个模板已安装"
        if [ $root_template_installed -gt 0 ]; then
            info "  - 根目录模板: $root_template_installed 个"
        fi
        if [ $template_installed -gt 0 ]; then
            if [ $project_template_count -gt 0 ]; then
                info "  - default 目录模板: $template_installed 个（其中 $project_template_count 个使用了项目特定模板）"
            else
                info "  - default 目录模板: $template_installed 个"
            fi
        fi
    else
        warn "未找到任何模板文件"
    fi
}

# 安装 skills 目录
install_skills() {
    local source_agent_dir="$1"
    local target_path="$2"
    local target_agent="$3"
    local project_name="$4"  # 项目名称（可选）
    
    local source_skills_dir="$source_agent_dir/skills"
    local target_skills_dir="$target_path/$target_agent/skills"
    
    # 检查源 skills 目录是否存在
    if [ ! -d "$source_skills_dir" ]; then
        warn "源 skills 目录不存在，跳过: $source_skills_dir"
        return
    fi
    
    info "正在安装 skills 目录..."
    info "  源路径: $source_skills_dir"
    info "  目标路径: $target_skills_dir"
    if [ -n "$project_name" ]; then
        info "  项目名称: $project_name"
    fi
    
    # 确保目标 skills 目录存在
    mkdir -p "$target_skills_dir"
    
    # 遍历每个 skill 目录
    local skill_count=0
    local skill_installed=0
    
    for skill_dir in "$source_skills_dir"/*; do
        # 检查是否为目录
        if [ ! -d "$skill_dir" ]; then
            continue
        fi
        
        local skill_name="$(basename "$skill_dir")"
        local target_skill_dir="$target_skills_dir/$skill_name"
        local skill_md_source=""
        
        skill_count=$((skill_count + 1))
        
        # 确定要使用的 SKILL.md 源文件
        # 优先级：项目目录 > default 目录 > 根目录
        if [ -n "$project_name" ]; then
            # 如果提供了项目参数，先检查项目目录
            local project_skill_md="$skill_dir/$project_name/SKILL.md"
            if [ -f "$project_skill_md" ]; then
                skill_md_source="$project_skill_md"
                info "  使用项目目录: $skill_name/$project_name/SKILL.md"
            else
                # 明确说明项目目录不存在，将回退
                if [ -d "$skill_dir/$project_name" ]; then
                    warn "  项目目录存在但 SKILL.md 不存在: $skill_name/$project_name/，将回退到 default 或根目录"
                else
                    info "  项目目录不存在: $skill_name/$project_name/，将回退到 default 或根目录"
                fi
            fi
        fi
        
        # 如果项目目录不存在或未提供项目参数，检查 default 目录
        if [ -z "$skill_md_source" ]; then
            local default_skill_md="$skill_dir/default/SKILL.md"
            if [ -f "$default_skill_md" ]; then
                skill_md_source="$default_skill_md"
                if [ -n "$project_name" ]; then
                    info "  使用 default 目录（项目目录不存在）: $skill_name/default/SKILL.md"
                else
                    info "  使用 default 目录: $skill_name/default/SKILL.md"
                fi
            fi
        fi
        
        # 如果 default 目录也不存在，检查根目录
        if [ -z "$skill_md_source" ]; then
            local root_skill_md="$skill_dir/SKILL.md"
            if [ -f "$root_skill_md" ]; then
                skill_md_source="$root_skill_md"
                if [ -n "$project_name" ]; then
                    info "  使用根目录（项目目录和 default 目录都不存在）: $skill_name/SKILL.md"
                else
                    info "  使用根目录: $skill_name/SKILL.md"
                fi
            fi
        fi
        
        # 如果找到了 SKILL.md，复制它
        if [ -n "$skill_md_source" ]; then
            mkdir -p "$target_skill_dir"
            cp "$skill_md_source" "$target_skill_dir/SKILL.md"
            if [ $? -eq 0 ]; then
                skill_installed=$((skill_installed + 1))
                info "  已安装: $skill_name/SKILL.md"
            else
                warn "  复制失败: $skill_name/SKILL.md"
            fi
        else
            warn "  跳过（未找到 SKILL.md）: $skill_name"
        fi
    done
    
    if [ $skill_count -gt 0 ]; then
        info "skills 安装完成: $skill_installed/$skill_count 个 skill 已安装"
    else
        warn "未找到任何 skill 目录"
    fi
}

# 安装用户注入配置模板
install_user_injection_templates() {
    local target_path="$1"
    local source_specify_dir="$2"
    local user_input_dir="$target_path/user_input"
    
    info "正在生成用户注入配置模板..."
    
    # 创建 user_input 目录
    if [ ! -d "$user_input_dir" ]; then
        mkdir -p "$user_input_dir"
        info "已创建用户输入目录: $user_input_dir"
    else
        info "用户输入目录已存在: $user_input_dir"
    fi
    
    # 生成简化版配置文件模板（推荐，更简单易用）
    local simple_template="$source_specify_dir/templates/interface-config-simple.md"
    local simple_target="$user_input_dir/interface-config.md"
    
    if [[ -f "$simple_template" ]]; then
        if [[ ! -f "$simple_target" ]]; then
            cp "$simple_template" "$simple_target"
            info "已生成简化版配置模板: $simple_target"
        else
            info "简化版配置模板已存在，跳过生成: $simple_target"
        fi
    else
        warn "简化版配置模板不存在，跳过生成: $simple_template"
    fi
    
    # 生成YAML配置文件模板（向后兼容，高级用户使用）
    local yaml_template="$source_specify_dir/templates/interface-identification-rules.yaml"
    local yaml_target="$user_input_dir/interface-identification-rules.yaml"
    
    if [[ -f "$yaml_template" ]]; then
        if [[ ! -f "$yaml_target" ]]; then
            cp "$yaml_template" "$yaml_target"
            info "已生成YAML配置模板（高级）: $yaml_target"
        else
            info "YAML配置模板已存在，跳过生成: $yaml_target"
        fi
    else
        warn "YAML配置模板不存在，跳过生成: $yaml_template"
    fi
    
    # 生成用户配置说明文档
    local readme_file="$user_input_dir/README.md"
    if [[ ! -f "$readme_file" ]]; then
        cat > "$readme_file" << 'EOF'
# 用户注入配置说明

## 接口反构配置

支持两种配置文件格式，推荐使用简化版（Markdown格式），更简单易用。

### 方式1：简化版配置（推荐）

**配置文件**：`user_input/interface-config.md`

**特点**：
- ✅ 使用Markdown格式，简单直观
- ✅ 类似交互式向导的风格，易于理解
- ✅ 直接填写接口类型和约束规则，无需复杂的YAML结构

**使用步骤**：

1. **编辑配置文件**：
   ```bash
   # 配置文件已自动生成在 user_input/interface-config.md
   # 直接编辑此文件，填写您的配置
   ```

2. **配置接口类型**：
   ```
   您的选择：restful,module,cli
   ```

3. **配置约束规则**（可选）：
   ```
   # 文件路径过滤
   src/api/*
   **/controllers/*.py
   
   # 函数名模式
   get_*
   post_*
   
   # 排除模式
   **/test/**
   **/*_test.py
   ```

4. **运行反构命令**：
   ```bash
   omni.reverse --target interfaces --path <your-path>
   ```
   系统会自动读取并使用您的配置，跳过交互式配置步骤。

**配置示例**：参考 `.specify/templates/interface-config-simple-example.md`

### 方式2：YAML配置（高级，向后兼容）

**配置文件**：`user_input/interface-identification-rules.yaml`

**特点**：
- 使用YAML格式，支持更复杂的配置
- 适合需要精细控制的场景
- 支持自然语言描述的约束规则

**使用步骤**：

1. **编辑配置文件**：
   ```bash
   # 配置文件已自动生成在 user_input/interface-identification-rules.yaml
   # 根据项目需求修改配置
   ```

2. **配置接口类型和约束规则**：
   ```yaml
   identification_rules:
     interface_types:
       module:
         constraints:
           - description: "在每个目录下 zenic_xx_plugin.py 文件中，create_、delete_、update_ 开头的函数"
   ```

3. **运行反构命令**：
   ```bash
   omni.reverse --target interfaces --path <your-path>
   ```

### 配置文件优先级

1. **简化版配置**（`interface-config.md`）：最高优先级，如果存在则优先使用
2. **YAML配置**（`interface-identification-rules.yaml`）：如果简化版不存在，使用此配置
3. **交互式配置**：如果配置文件都不存在，使用交互式向导

### 支持的接口类型

- `restful`: RESTful API 接口
- `message`: 消息类接口（MQ、事件等）
- `module`: 模块间接口（模块内部调用）
- `cli`: 命令行接口（CLI命令）
- `rpc`: RPC 接口（远程过程调用）
- `function`: 函数接口（普通函数调用）
- `other`: 其他类型接口

### 配置模板位置

- **简化版模板**：`.specify/templates/interface-config-simple.md`（推荐）
- **简化版示例**：`.specify/templates/interface-config-simple-example.md`
- **YAML模板**：`.specify/templates/interface-identification-rules.yaml`（高级）
- **YAML完整模板**：`.specify/templates/interface-identification-rules-default.yaml`（参考）
EOF
        info "已生成用户配置说明文档: $readme_file"
    else
        info "用户配置说明文档已存在，跳过生成: $readme_file"
    fi
}

# 主函数
main() {
    # 检查是否需要显示帮助信息
    if [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
        show_usage
        exit 0
    fi
    
    echo "=========================================="
    echo "  OmniSpec 安装脚本"
    echo "=========================================="
    echo
    
    # 检查源目录
    check_source_dirs
    
    # 检查参数数量
    if [ $# -lt 2 ]; then
        error "缺少必需参数"
        error "使用 '$0 -h' 或 '$0 --help' 查看详细使用说明"
        exit 1
    fi
    
    # 获取目标 AGENT 目录名（第一个参数）
    TARGET_AGENT="$1"
    
    # 如果目录名不以点号开头，则添加点号
    if [[ ! "$TARGET_AGENT" =~ ^\. ]]; then
        TARGET_AGENT=".$TARGET_AGENT"
    fi
    
    # 获取目标路径（第二个参数）
    TARGET_PATH=$(get_target_path "$2")
    
    # 获取项目名称（第三个参数，可选）
    PROJECT_NAME="${3:-}"
    
    echo
    info "开始安装..."
    echo

    # 复制 .specify 目录（先删除再完整拷贝）
    copy_directory_replace \
        "$SOURCE_SPECIFY_DIR" \
        "$TARGET_PATH/.specify" \
        "specify"
    
    echo
    
    # 生成用户注入配置模板
    install_user_injection_templates "$TARGET_PATH" "$SOURCE_SPECIFY_DIR"
    
    echo
    
    # 安装模板文件（根据项目参数选择对应的模板）
    # 注意：这会覆盖复制 specify 目录时带来的 templates 目录
    install_templates \
        "$SOURCE_SPECIFY_DIR" \
        "$TARGET_PATH" \
        "$PROJECT_NAME"
    
    echo
    
    # 复制 agent 目录（增量覆盖，排除 skills 目录）
    copy_directory_incremental \
        "$SOURCE_AGENT_DIR" \
        "$TARGET_PATH/$TARGET_AGENT" \
        "agent" \
        "skills"
    
    echo
    
    # 安装 skills 目录（根据项目参数选择对应的 SKILL.md）
    install_skills \
        "$SOURCE_AGENT_DIR" \
        "$TARGET_PATH" \
        "$TARGET_AGENT" \
        "$PROJECT_NAME"
    
    echo
    
    # 验证 agents 目录是否被正确复制
    verify_agents_directory "$TARGET_PATH" "$TARGET_AGENT"
    
    echo
    
    # 更新 agent 配置文件
    update_agent_config "$TARGET_PATH" "$TARGET_AGENT"
    
    echo
    
    # 设置脚本可执行权限
    set_script_permissions "$TARGET_PATH"
    
    echo
    echo "=========================================="
    info "安装完成！"
    echo "=========================================="
    echo
    info "代码工程路径: $TARGET_PATH"
    info "agent 目录已复制到: $TARGET_PATH/$TARGET_AGENT"
    info "  - commands 目录: $TARGET_PATH/$TARGET_AGENT/commands"
    info "  - agents 目录: $TARGET_PATH/$TARGET_AGENT/agents"
    info "specify 目录已复制到: $TARGET_PATH/.specify"
    info "用户注入配置模板已生成到: $TARGET_PATH/user_input/"
    echo
    info "提示：要自定义接口识别规则，请参考: $TARGET_PATH/user_input/README.md"
    echo
}

# 执行主函数
main "$@"

