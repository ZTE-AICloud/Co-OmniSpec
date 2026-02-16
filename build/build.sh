#!/bin/bash

# OmniSpec 构建脚本
# 功能：创建带时间戳的打包目录，运行安装脚本，并压缩为 zip 文件

set -e  # 遇到错误立即退出

# 显示使用说明
show_usage() {
    cat << EOF
OmniSpec 构建脚本

使用方法:
  $0 [指定AGENT名称] [选项]

参数说明:
  [指定AGENT名称]  (可选)
      指定 agent 名称，默认为 "claude"
      如果输入的名称不带点号，会自动添加点号前缀
      例如:
        - 输入 "claude"   -> 复制到 .claude
        - 输入 ".claude"  -> 复制到 .claude (不会重复添加点号)
        - 输入 "cursor"  -> 复制到 .cursor

  选项:
    -h, --help           显示此帮助信息
    -v, --version <版本> 指定版本号（默认：v1.0.0），必须为三段式格式：vX.Y.Z（如：v1.0.0, v2.1.3）
    -o, --output <路径>  指定输出路径（构建目录和 zip 文件将生成到此路径）
    --clean, --remove    压缩完成后删除构建目录（默认不删除）

示例:
  # 使用默认的 claude，不删除构建目录
  $0

  # 指定自定义的 agent
  $0 claude
  $0 .claude
  $0 cursor

  # 指定版本号
  $0 --version v2.0.0
  $0 claude --version v1.5.3

  # 指定输出路径
  $0 --output /tmp/builds
  $0 claude --output ./output

  # 压缩完成后删除构建目录
  $0 --clean
  $0 claude --clean
  $0 --version v1.0.0 --output /tmp/builds --clean

功能说明:
  1. 获取当前时间戳（年月日时分秒格式）
  2. 在当前目录下创建 omnispec-version-agent-timestamp 文件夹
  3. 运行安装脚本（install.sh），将 agent 和 specify 目录复制到 omnispec-version-agent-timestamp 文件夹
  4. 将 omnispec-version-agent-timestamp 文件夹压缩为 omnispec-version-agent-timestamp.zip 文件
  5. 默认保留构建目录，使用 --clean 选项可删除构建目录

ZIP 文件使用说明:
  生成的 omnispec-version-agent-timestamp.zip 文件使用方法：
  1. cd 到目标代码工程路径
  2. 解压 zip 文件即可直接展开 agent（如.claude） 和 .specify 两个文件夹
     例如: unzip omnispec-v1.0.0-claude-20251206123456.zip
     解压后会直接在目标路径下得到 agent（如.claude） 和 .specify 文件夹

注意事项:
  - 默认情况下，构建目录会在压缩完成后保留
  - 使用 --clean 或 --remove 选项可以在压缩完成后删除构建目录
  - 构建目录名称格式：omnispec-version-agent-timestamp

EOF
}

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 加载版本号工具函数
source "$SCRIPT_DIR/version-utils.sh"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 打印信息
info() {
    echo -e "${GREEN}[INFO]${NC} $1" >&2
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1" >&2
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

# 获取安装脚本路径
get_install_script() {
    echo "$SCRIPT_DIR/install.sh"
}

# 检查安装脚本是否存在
check_install_script() {
    local install_script="$1"
    local script_name="$(basename "$install_script")"
    
    if [ ! -f "$install_script" ]; then
        error "$script_name 脚本不存在: $install_script"
        exit 1
    fi
    
    if [ ! -x "$install_script" ]; then
        warn "$script_name 没有可执行权限，正在设置..."
        chmod +x "$install_script"
    fi
}

# 获取时间戳（年月日时分秒格式：YYYYMMDDHHMMSS）
get_timestamp() {
    date +"%Y%m%d%H%M%S"
}

# 获取统一的名称（用于文件夹和zip文件名：omnispec-version-agent-timestamp）
get_build_name() {
    local agent_name="$1"
    local timestamp="$2"
    local version="$3"
    
    # 从agent名称中去掉点号前缀
    local agent_for_name="${agent_name#.}"
    
    # 统一名称格式：omnispec-version-agent-timestamp
    echo "omnispec-${version}-${agent_for_name}-${timestamp}"
}

# 写入版本信息文件到打包目录的 .specify 文件夹
write_version_info() {
    local build_dir="$1"
    local agent_name="$2"
    local timestamp="$3"
    local version="$4"
    local build_date="$5"
    
    local specify_dir="$build_dir/.specify"
    local version_file="$specify_dir/VERSION.md"
    
    # 确保 .specify 目录存在
    if [ ! -d "$specify_dir" ]; then
        warn ".specify 目录不存在，正在创建..."
        mkdir -p "$specify_dir"
    fi
    
    info "写入版本信息文件..."
    cat > "$version_file" << EOF
OmniSpec 版本信息
==================

版本号: $version
构建时间: $build_date
时间戳: $timestamp
Agent: $agent_name

此文件由 OmniSpec 构建脚本自动生成
EOF
    
    info "版本信息已写入: $version_file"
}

# 复制版本发布说明文件到 .specify 文件夹
copy_release_notes() {
    local build_dir="$1"
    
    # 源文件路径：build 目录的上一级目录下的 src/specify/版本发布说明.md
    local project_root="$(cd "$SCRIPT_DIR/.." && pwd)"
    local source_file="$project_root/src/specify/版本发布说明.md"
    local specify_dir="$build_dir/.specify"
    local target_file="$specify_dir/版本发布说明.md"
    
    # 检查源文件是否存在
    if [ ! -f "$source_file" ]; then
        warn "版本发布说明文件不存在: $source_file"
        warn "跳过复制版本发布说明文件"
        return
    fi
    
    # 确保 .specify 目录存在
    if [ ! -d "$specify_dir" ]; then
        info ".specify 目录不存在，正在创建..."
        mkdir -p "$specify_dir"
    fi
    
    info "正在复制版本发布说明文件..."
    info "  源文件: $source_file"
    info "  目标文件: $target_file"
    
    # 复制文件
    cp "$source_file" "$target_file"
    
    if [ $? -eq 0 ]; then
        info "版本发布说明文件已复制: $target_file"
    else
        error "复制版本发布说明文件失败"
        return 1
    fi
}

# 生成安装版本开发视图文件
generate_spec_file_list() {
    local build_dir="$1"
    local agent_name="$2"
    local version="$3"
    local build_date="$4"
    
    # 将文件生成到构建目录根目录
    local spec_file="$build_dir/omni_spec_file_list.md"
    
    # 从 agent_name 中提取 agent 名称（去掉点号前缀）
    local agent_name_clean="${agent_name#.}"
    
    info "正在生成安装版本开发视图文件..."
    info "  目标文件: $spec_file"
    info "  版本号: $version"
    
    # 生成文件树清单（使用 find 命令）
    local file_tree=""
    file_tree=$(cd "$build_dir" && find . -type f | sort | sed 's|^\./||' || echo "find 命令执行失败")
    
    # 生成文件内容
    cat > "$spec_file" << EOF
# OmniSpec 安装版本开发视图

## 版本信息

- **版本号**: $version
- **安装时间**: $build_date
- **Agent**: $agent_name_clean

## 文件列表

\`\`\`text
$file_tree
\`\`\`

此文件由 OmniSpec 构建脚本自动生成
EOF
    
    info "安装版本开发视图文件已生成: $spec_file"
}

# 创建打包目录
create_build_dir() {
    local build_name="$1"  # 统一的构建名称
    local output_path="$2"  # 输出路径（可选）
    
    local build_dir
    if [ -n "$output_path" ]; then
        # 如果指定了输出路径，使用输出路径
        # 转换为绝对路径
        if [ ! -d "$output_path" ]; then
            info "输出路径不存在，正在创建: $output_path"
            mkdir -p "$output_path"
            if [ $? -ne 0 ]; then
                error "无法创建输出路径: $output_path"
                exit 1
            fi
        fi
        local abs_output_path="$(cd "$output_path" && pwd)"
        build_dir="$abs_output_path/$build_name"
    else
        # 默认使用脚本所在目录
        build_dir="$SCRIPT_DIR/$build_name"
    fi
    
    if [ -d "$build_dir" ]; then
        error "构建目录已存在: $build_dir"
        exit 1
    fi
    
    mkdir -p "$build_dir"
    info "创建构建目录: $build_dir"
    echo "$build_dir"
}

# 运行安装脚本
run_install_script() {
    local install_script="$1"
    local build_dir="$2"
    local target_agent="$3"
    
    info "运行安装脚本..."
    info "  脚本: $(basename "$install_script")"
    info "  目标目录: $build_dir"
    info "  Agent 目录名: $target_agent"
    
    # 检查脚本扩展名
    local script_ext="${install_script##*.}"
    if [ "$script_ext" = "ps1" ]; then
        # PowerShell 脚本，尝试通过 pwsh 或 powershell 执行
        if command -v pwsh &> /dev/null; then
            pwsh "$install_script" "$target_agent" "$build_dir"
        elif command -v powershell &> /dev/null; then
            powershell -File "$install_script" "$target_agent" "$build_dir"
        else
            error "无法执行 PowerShell 脚本，请安装 PowerShell (pwsh 或 powershell)"
            exit 1
        fi
    else
        # Bash 脚本，直接执行
        "$install_script" "$target_agent" "$build_dir"
    fi
}

# 压缩目录
create_zip() {
    local build_dir="$1"
    local build_name="$2"   # 统一的构建名称
    local output_path="$3"  # 输出路径（可选）
    
    # 生成zip文件名：使用与文件夹相同的名称
    local zip_file
    if [ -n "$output_path" ]; then
        # 如果指定了输出路径，使用输出路径
        local abs_output_path="$(cd "$output_path" && pwd)"
        zip_file="$abs_output_path/${build_name}.zip"
    else
        # 默认使用脚本所在目录
        zip_file="$SCRIPT_DIR/${build_name}.zip"
    fi
    
    if [ -f "$zip_file" ]; then
        warn "ZIP 文件已存在，将被覆盖: $zip_file"
        rm -f "$zip_file"
    fi
    
    info "正在压缩目录..."
    info "  源目录: $build_dir"
    info "  目标文件: $zip_file"
    
    # 进入构建目录内部，压缩目录内容（不包含目录本身）
    local zip_dir="$(dirname "$zip_file")"
    local zip_basename="$(basename "$zip_file")"
    
    # 确保 zip 文件所在目录存在
    mkdir -p "$zip_dir"
    
    cd "$build_dir"
    if command -v zip &> /dev/null; then
        # 压缩当前目录的所有内容（agent 和 specify），不包含父目录名
        # zip 文件直接创建在目标路径
        zip -r "$zip_file" . > /dev/null
    else
        error "未找到 zip 命令，请安装 zip 工具"
        exit 1
    fi
    
    info "压缩完成: $zip_file"
    echo "$zip_file"
}

# 删除构建目录
remove_build_dir() {
    local build_dir="$1"
    
    if [ ! -d "$build_dir" ]; then
        warn "构建目录不存在，跳过删除: $build_dir"
        return
    fi
    
    info "正在删除构建目录: $build_dir"
    rm -rf "$build_dir"
    
    if [ -d "$build_dir" ]; then
        error "构建目录删除失败: $build_dir"
        exit 1
    else
        info "构建目录已删除"
    fi
}

# 主函数
main() {
    # 解析参数
    local clean_build_dir=false
    local target_agent=""
    local output_path=""
    local version=""  # 版本号，优先从 --version 参数获取，否则从 build/version 文件读取
    
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
                    error "版本号格式错误: $2"
                    error "版本号必须为三段式格式：vX.Y.Z（如：v1.0.0, v2.1.3）"
                    exit 1
                fi
                version="$2"
                shift 2
                ;;
            -o|--output)
                if [ -z "$2" ]; then
                    error "--output 选项需要指定路径"
                    error "使用 '$0 -h' 或 '$0 --help' 查看详细使用说明"
                    exit 1
                fi
                output_path="$2"
                shift 2
                ;;
            --clean|--remove)
                clean_build_dir=true
                shift
                ;;
            *)
                # 第一个非选项参数作为 agent 名称
                if [ -z "$target_agent" ]; then
                    target_agent="$1"
                else
                    error "未知参数: $1"
                    error "使用 '$0 -h' 或 '$0 --help' 查看详细使用说明"
                    exit 1
                fi
                shift
                ;;
        esac
    done
    
    # 如果未提供 agent 名称，使用默认值
    TARGET_AGENT="${target_agent:-claude}"
    
    # 如果目录名不以点号开头，则添加点号
    if [[ ! "$TARGET_AGENT" =~ ^\. ]]; then
        TARGET_AGENT=".$TARGET_AGENT"
    fi
    
    echo "=========================================="
    echo "  OmniSpec 构建脚本"
    echo "=========================================="
    echo
    
    # 获取版本号（优先级：用户输入 > 文件 > 默认值）
    version=$(get_version "$version")
    
    # 验证版本号格式
    if ! validate_version "$version"; then
        error "版本号格式错误: $version"
        error "版本号必须为三段式格式：vX.Y.Z（如：v1.0.0, v2.1.3）"
        exit 1
    fi
    
    # 获取安装脚本路径
    INSTALL_SCRIPT=$(get_install_script)
    
    # 检查安装脚本是否存在
    check_install_script "$INSTALL_SCRIPT"
    
    # 获取时间戳
    TIMESTAMP=$(get_timestamp)
    info "时间戳: $TIMESTAMP"
    info "版本号: $version"
    
    # 生成统一的构建名称（用于文件夹和zip文件名）
    BUILD_NAME=$(get_build_name "$TARGET_AGENT" "$TIMESTAMP" "$version")
    info "构建名称: $BUILD_NAME"
    
    # 获取版本号（与构建名称相同）
    VERSION="$BUILD_NAME"
    info "版本号: $VERSION"
    
    # 生成构建时间（统一生成，多点使用）
    BUILD_DATE=$(date +"%Y-%m-%d %H:%M:%S")
    info "构建时间: $BUILD_DATE"
    
    echo
    
    # 显示输出路径信息
    if [ -n "$output_path" ]; then
        local abs_output_path="$(cd "$output_path" && pwd)"
        info "输出路径: $abs_output_path"
        echo
    fi
    
    # 创建构建目录（使用统一的构建名称）
    BUILD_DIR=$(create_build_dir "$BUILD_NAME" "$output_path")
    
    echo
    
    # 运行安装脚本
    run_install_script "$INSTALL_SCRIPT" "$BUILD_DIR" "$TARGET_AGENT"
    
    echo
    
    # 复制版本发布说明文件到 .specify 文件夹
    copy_release_notes "$BUILD_DIR"
    
    echo
    
    # 生成安装版本开发视图文件
    generate_spec_file_list "$BUILD_DIR" "$TARGET_AGENT" "$VERSION" "$BUILD_DATE"
    
    echo
    
    # 压缩目录（使用统一的构建名称）
    ZIP_FILE=$(create_zip "$BUILD_DIR" "$BUILD_NAME" "$output_path")
    
    echo
    
    # 根据参数决定是否删除构建目录
    if [ "$clean_build_dir" = true ]; then
        # 删除构建目录
        remove_build_dir "$BUILD_DIR"
        echo
    else
        info "构建目录已保留: $BUILD_DIR"
        echo
    fi
    
    echo "=========================================="
    info "构建完成！"
    echo "=========================================="
    echo
    info "ZIP 文件: $ZIP_FILE"
    if [ "$clean_build_dir" = false ]; then
        info "构建目录: $BUILD_DIR"
    fi
    echo
}

# 执行主函数
main "$@"

