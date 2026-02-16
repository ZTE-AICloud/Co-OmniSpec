#!/bin/bash

# OmniSpec 发布构建脚本
# 功能：为所有类型和 agent 组合执行构建

set -e  # 遇到错误立即退出

# 显示使用说明
show_usage() {
    cat << EOF
OmniSpec 发布构建脚本

使用方法:
  $0 [选项]

功能说明:
  为所有 agent（cursor, claude, codex, flow）执行构建（Linux 构建，使用 install.sh）
  路径规则：默认路径为 release，二级目录为 agent 名（如 flow），不再嵌套 OmniSpecVersion 层
  默认行为：构建前不会清理输出目录（使用 --clean-output 参数才会清理）

选项:
  -h, --help             显示此帮助信息
  -v, --version <版本>  指定版本号（默认从 build/version 文件读取），必须为三段式格式：vX.Y.Z（如：v1.0.0, v2.1.3）
  -o, --output <路径>    指定基础输出路径（默认：release），完整路径为：<基础路径>/release/<agent>
  --clean, --remove      压缩完成后删除构建目录（默认不删除）
  --clean-output         清理输出目录（默认不清理）
  --ai-ide               启用 AI-IDE 版本后置处理，重组目录结构为 AI-IDE 格式

示例:
  # 执行所有组合的构建（默认不清理输出目录）
  $0

  # 指定版本号
  $0 --version v2.0.0
  $0 --version v1.5.3 --output /tmp/publish

  # 指定基础输出路径（默认：release）
  $0 --output /tmp/publish
  $0 --output ./custom-output

  # 执行构建并删除构建目录
  $0 --clean

  # 清理输出目录
  $0 --clean-output

  # 组合使用
  $0 --version v2.0.0 --output /tmp/publish --clean
  $0 --version v1.5.3 --output ./custom-output --clean-output --clean

  # 启用 AI-IDE 版本后置处理
  $0 --ai-ide
  $0 --version v2.0.0 --ai-ide
  ./build/build-release.sh --ai-ide --version v1.1.0 --output /media/vdc/sdd/omni-spec/20251231/omni-spec

EOF
}

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_SCRIPT="$SCRIPT_DIR/build.sh"
VERSION_FILE="$SCRIPT_DIR/version"
DEFAULT_BASE_OUTPUT_DIR="$SCRIPT_DIR/.."

# 加载版本号工具函数
source "$SCRIPT_DIR/version-utils.sh"

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

# 生成 agent 的完整输出路径
# 格式：<base_path>/release/<agent>
get_agent_output_path() {
    local base_path="$1"
    local version="$2"
    local agent="$3"
    
    local full_path="${base_path}/release/${agent}"
    
    # 转换为绝对路径
    if [[ "$full_path" = /* ]]; then
        echo "$full_path"
    else
        echo "$(pwd)/${full_path}"
    fi
}

# 检查 build.sh 是否存在
check_build_script() {
    if [ ! -f "$BUILD_SCRIPT" ]; then
        error "build.sh 脚本不存在: $BUILD_SCRIPT"
        exit 1
    fi
    
    if [ ! -x "$BUILD_SCRIPT" ]; then
        warn "build.sh 没有可执行权限，正在设置..."
        chmod +x "$BUILD_SCRIPT"
    fi
}

# 清理输出目录
clean_output_dir() {
    local output_dir="$1"
    
    if [ ! -d "$output_dir" ]; then
        info "输出目录不存在，无需清理: $output_dir"
        return 0
    fi
    
    # 检查目录是否为空
    if [ -z "$(ls -A "$output_dir" 2>/dev/null)" ]; then
        info "输出目录为空，无需清理: $output_dir"
        return 0
    fi
    
    warn "正在清理输出目录: $output_dir"
    warn "此操作将删除目录下的所有文件和文件夹"
    
    # 统计要删除的文件数量
    local file_count=$(find "$output_dir" -mindepth 1 -maxdepth 1 | wc -l)
    info "将删除 $file_count 个项目"
    
    # 删除目录下的所有内容
    rm -rf "${output_dir}"/*
    rm -rf "${output_dir}"/.[!.]* "${output_dir}"/..?* 2>/dev/null || true
    
    # 验证清理结果
    if [ -z "$(ls -A "$output_dir" 2>/dev/null)" ]; then
        info "输出目录清理完成"
    else
        error "输出目录清理失败，仍有文件残留"
        return 1
    fi
}

# 执行单个构建
run_build() {
    local agent="$1"
    local base_output_path="$2"
    local clean_flag="$3"
    local version="$4"
    
    # 生成 agent 的完整输出路径
    local agent_output_path=$(get_agent_output_path "$base_output_path" "$version" "$agent")
    
    info "=========================================="
    info "构建: agent=$agent, version=$version"
    info "输出路径: $agent_output_path"
    info "=========================================="
    
    local build_cmd="$BUILD_SCRIPT $agent --version \"$version\" --output \"$agent_output_path\""
    if [ "$clean_flag" = true ]; then
        build_cmd="$build_cmd --clean"
    fi
    
    eval "$build_cmd"
    
    if [ $? -eq 0 ]; then
        info "构建成功: agent=$agent, version=$version"
    else
        error "构建失败: agent=$agent, version=$version"
        return 1
    fi
    
    echo
}

# AI-IDE 版本后置处理：重组目录结构
# 从 release/<agent>/omnispec-<版本>-<agent>-<timestamp>/
# 转换为 release/<agent>/omnispec-<版本>/
reorganize_for_ai_ide() {
    local base_output_dir="$1"
    local version="$2"
    
    local source_dir="${base_output_dir}/release"
    local target_base_dir="${base_output_dir}/release"
    
    info "=========================================="
    info "开始 AI-IDE 版本后置处理"
    info "源目录: $source_dir"
    info "目标基础目录: $target_base_dir"
    info "=========================================="
    echo
    
    # 检查源目录是否存在
    if [ ! -d "$source_dir" ]; then
        error "源目录不存在: $source_dir"
        return 1
    fi
    
    # 定义 agent 列表
    local agents=("cursor" "claude" "codex" "flow")
    
    # 遍历每个 agent
    for agent in "${agents[@]}"; do
        local agent_source_dir="${source_dir}/${agent}"
        local agent_target_dir="${target_base_dir}/${agent}"
        
        # 检查 agent 源目录是否存在
        if [ ! -d "$agent_source_dir" ]; then
            warn "Agent 源目录不存在，跳过: $agent_source_dir"
            continue
        fi
        
        info "处理 agent: $agent"
        info "  源目录: $agent_source_dir"
        info "  目标目录: $agent_target_dir"
        
        # 查找匹配的目录：omnispec-<version>-<agent>-<timestamp>
        # 例如：omnispec-v1.0.0-claude-20251207204358
        # 注意：build.sh 生成的目录名包含完整的版本号（包含 v 前缀）
        local pattern="omnispec-${version}-${agent}-*"
        
        # 查找匹配的目录
        local found_dirs=()
        while IFS= read -r -d '' dir; do
            if [ -d "$dir" ]; then
                found_dirs+=("$dir")
            fi
        done < <(find "$agent_source_dir" -maxdepth 1 -type d -name "$pattern" -print0 2>/dev/null)
        
        if [ ${#found_dirs[@]} -eq 0 ]; then
            warn "  未找到匹配的目录: $pattern"
            continue
        fi
        
        # 如果找到多个目录，使用第一个（通常只有一个）
        local source_build_dir="${found_dirs[0]}"
        local dir_name=$(basename "$source_build_dir")
        # 新目录名：omnispec-<version>（去掉时间戳部分，保留完整版本号包含 v 前缀）
        # 例如：omnispec-v1.0.0-claude-20251207204358 -> omnispec-v1.0.0
        local new_dir_name="omnispec-${version}"
        local temp_dir="${agent_source_dir}/${new_dir_name}"
        
        info "  找到构建目录: $dir_name"
        info "  新目录名: $new_dir_name"
        
        # 重命名目录（去掉时间戳部分）
        if [ "$dir_name" != "$new_dir_name" ]; then
            if [ -d "$temp_dir" ]; then
                warn "  目标目录已存在，先删除: $temp_dir"
                rm -rf "$temp_dir"
            fi
            info "  重命名目录: $dir_name -> $new_dir_name"
            mv "$source_build_dir" "$temp_dir"
        else
            temp_dir="$source_build_dir"
        fi
        
        # 创建目标 agent 目录
        if ! mkdir -p "$agent_target_dir"; then
            error "  无法创建目标目录: $agent_target_dir"
            continue
        fi
        
        # 移动重命名后的目录到目标位置
        local final_target_dir="${agent_target_dir}/${new_dir_name}"
        if [ "$temp_dir" != "$final_target_dir" ]; then
            if [ -d "$final_target_dir" ]; then
                warn "  目标目录已存在，先删除: $final_target_dir"
                rm -rf "$final_target_dir"
            fi
            info "  移动目录到: $final_target_dir"
            mv "$temp_dir" "$final_target_dir"
        else
            info "  目录已在目标位置: $final_target_dir"
        fi
        
        # 移动 zip 文件（如果存在）
        # zip 文件名格式：omnispec-<version>-<agent>-<timestamp>.zip
        local zip_pattern="omnispec-${version}-${agent}-*.zip"
        while IFS= read -r -d '' zip_file; do
            if [ -f "$zip_file" ]; then
                local zip_name=$(basename "$zip_file")
                local zip_target="${agent_target_dir}/${zip_name}"
                info "  移动 zip 文件: $zip_name"
                mv "$zip_file" "$zip_target"
            fi
        done < <(find "$agent_source_dir" -maxdepth 1 -type f -name "$zip_pattern" -print0 2>/dev/null)
        
        info "  Agent $agent 处理完成"
        echo
    done
    
    info "AI-IDE 版本后置处理完成"
    echo
}

# 获取并准备基础输出目录
get_base_output_dir() {
    local base_output_path="$1"
    
    # 如果未指定基础输出路径，使用默认路径
    if [ -z "$base_output_path" ]; then
        base_output_path="$DEFAULT_BASE_OUTPUT_DIR"
    fi
    
    # 先尝试创建目录（mkdir -p 不会报错如果目录已存在）
    info "准备基础输出路径: $base_output_path" >&2
    if ! mkdir -p "$base_output_path" 2>/dev/null; then
        error "无法创建基础输出路径: $base_output_path"
        exit 1
    fi
    
    # 验证目录是否真的存在
    if [ ! -d "$base_output_path" ]; then
        error "基础输出路径创建失败或不是目录: $base_output_path"
        exit 1
    fi
    
    # 转换为绝对路径（必须在目录存在后才能执行）
    local abs_path
    if ! abs_path="$(cd "$base_output_path" && pwd)"; then
        error "无法访问基础输出路径: $base_output_path"
        exit 1
    fi
    
    # 如果目录是新创建的，给出提示（输出到 stderr，避免被捕获）
    if [ ! "$(ls -A "$abs_path" 2>/dev/null)" ]; then
        info "基础输出目录已创建: $abs_path" >&2
    else
        info "基础输出目录已存在: $abs_path" >&2
    fi
    
    # 只输出绝对路径到标准输出
    echo "$abs_path"
}

# 主函数
main() {
    # 解析参数
    local clean_build_dir=false
    local clean_output=false  # 默认不清理输出目录
    local base_output_path=""  # 基础输出路径
    local version=""  # 版本号，优先从 --version 参数获取，否则从 build/version 文件读取
    local ai_ide_mode=false  # AI-IDE 模式标志
    
    # 解析所有参数
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -h|--help)
                show_usage
                exit 0
                ;;
            -v|--version)
                if [ -z "$2" ]; then
                    error "--version 选项需要指定版本号"
                    error "使用 '$0 -h' 或 '$0 --help' 查看详细使用说明"
                    exit 1
                fi
                if ! validate_version "$2"; then
                    exit 1
                fi
                version="$2"
                shift 2
                ;;
            -o|--output)
                if [ -z "$2" ]; then
                    error "--output 选项需要指定基础路径"
                    error "使用 '$0 -h' 或 '$0 --help' 查看详细使用说明"
                    exit 1
                fi
                base_output_path="$2"
                shift 2
                ;;
            --clean|--remove)
                clean_build_dir=true
                shift
                ;;
            --clean-output)
                clean_output=true
                shift
                ;;
            --ai-ide)
                ai_ide_mode=true
                shift
                ;;
            *)
                error "未知参数: $1"
                error "使用 '$0 -h' 或 '$0 --help' 查看详细使用说明"
                exit 1
                ;;
        esac
    done
    
    echo "=========================================="
    echo "  OmniSpec 发布构建脚本"
    echo "=========================================="
    echo
    
    # 检查 build.sh 是否存在
    check_build_script
    
    # 获取版本号（优先级：用户输入 > 文件 > 默认值）
    version=$(get_version "$version")
    
    # 验证版本号格式
    if ! validate_version "$version"; then
        error "版本号格式错误: $version"
        error "版本号必须为三段式格式：vX.Y.Z（如：v1.0.0, v2.1.3）"
        exit 1
    fi
    
    # 获取并准备基础输出目录（如果不存在会自动创建）
    BASE_OUTPUT_DIR=$(get_base_output_dir "$base_output_path")
    info "基础输出目录: $BASE_OUTPUT_DIR"
    info "版本号: $version"
    info "路径规则: $BASE_OUTPUT_DIR/release/<agent>"
    echo
    
    # 如果指定了清理输出目录，先清理当前版本的目录
    if [ "$clean_output" = true ]; then
        local clean_agents=("cursor" "claude" "codex" "flow")
        for agent in "${clean_agents[@]}"; do
            local agent_dir="$BASE_OUTPUT_DIR/release/$agent"
            if [ -d "$agent_dir" ]; then
                warn "清理 agent 目录: $agent_dir"
                rm -rf "$agent_dir"
                info "已清理: $agent_dir"
            fi
        done
        echo
    fi
    
    # 定义 agent 列表
    local agents=("cursor" "claude" "codex" "flow")
    
    # 统计信息
    local total_builds=${#agents[@]}
    local success_count=0
    local fail_count=0
    
    info "开始执行发布构建..."
    info "构建数量: $total_builds"
    echo
    
    # 遍历所有 agent
    for agent in "${agents[@]}"; do
        if run_build "$agent" "$BASE_OUTPUT_DIR" "$clean_build_dir" "$version"; then
            success_count=$((success_count + 1))
        else
            fail_count=$((fail_count + 1))
        fi
    done
    
    echo
    echo "=========================================="
    info "发布构建完成！"
    echo "=========================================="
    echo
    info "总构建数: $total_builds"
    info "成功: $success_count"
    if [ $fail_count -gt 0 ]; then
        error "失败: $fail_count"
    else
        info "失败: $fail_count"
    fi
    echo
    
    # 如果启用了 AI-IDE 模式，执行后置处理
    if [ "$ai_ide_mode" = true ]; then
        echo
        if reorganize_for_ai_ide "$BASE_OUTPUT_DIR" "$version"; then
            info "AI-IDE 版本后置处理成功完成"
            info "重组后的路径: $BASE_OUTPUT_DIR/release/<agent>/omnispec-${version}/"
        else
            error "AI-IDE 版本后置处理失败"
        fi
        echo
    else
        info "基础输出目录: $BASE_OUTPUT_DIR"
        info "完整路径: $BASE_OUTPUT_DIR/release/<agent>"
    fi
    echo
}

# 执行主函数
main "$@"

