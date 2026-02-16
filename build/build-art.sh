#!/usr/bin/env bash

# OmniSpec 版本制品发布脚本

set -e
set -u
set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/version-utils.sh"

# 颜色输出
info()  { echo -e "\033[0;32m[INFO]\033[0m $1"; }
warn()  { echo -e "\033[1;33m[WARN]\033[0m $1"; }
error() { echo -e "\033[0;31m[ERROR]\033[0m $1" >&2; }

show_usage() {
    cat << EOF
OmniSpec 版本制品发布脚本

使用方法: $0 [选项]

功能说明:
  调用 build-release.sh 为所有 agent 生成发布制品，并生成简化版本（去时间戳）

  输出路径规则：
    - 不指定 --release-repo：输出到本地 <项目根目录>/output/release/
    - 指定 --release-repo：先构建到本地 output/ 临时目录，再合并拷贝到指定路径

  输出结构：<输出路径>/release/<agent>/
    ├── omnispec-vX.Y.Z-<agent>.zip          (推荐，不含时间戳)
    ├── omnispec-vX.Y.Z-<agent>-TIMESTAMP.zip (含时间戳)
    └── omnispec-vX.Y.Z/                     (构建目录)

选项:
  -h, --help                 显示帮助信息
  -r, --release-repo <路径>  制品输出路径（可选，默认输出到本地 output/release/）
  -v, --version <版本>       版本号（可选，默认从 build/version 读取）
  --clean, --remove          构建完成后清理临时目录（仅指定 --release-repo 时有效）
  --clean-output             先删除目标输出目录再生成

示例:
  $0                                                        # 输出到 ./output/release/
  $0 --release-repo /path/to/output                         # 发布到指定路径
  $0 --release-repo /path/to/output --version v2.0.0        # 指定版本号
  $0 --release-repo /path/to/output --clean --clean-output  # 清理后构建

EOF
}

# 简化版本生成：遍历所有 agent，cp 去时间戳 ZIP，mv 重命名目录
simplify_releases() {
    local release_dir="$1/release"
    [ ! -d "$release_dir" ] && { error "Release 目录不存在: $release_dir"; return 1; }

    info "开始生成简化版本..."
    local agents=("cursor" "claude" "codex" "flow")
    local success=0 failed=0

    for agent in "${agents[@]}"; do
        local agent_dir="${release_dir}/${agent}"
        [ ! -d "$agent_dir" ] && continue

        # 查找带时间戳的目录
        while IFS= read -r -d '' tdir; do
            local dname=$(basename "$tdir")
            # 提取版本号: omnispec-v2.0.0-claude-20260209 -> v2.0.0
            local ver=$(echo "$dname" | sed -E "s/^omnispec-(v[0-9]+\.[0-9]+\.[0-9]+)-${agent}-[0-9]+$/\1/")
            [ "$ver" == "$dname" ] && { warn "  无法提取版本号，跳过: $dname"; continue; }

            local simple_zip="${agent_dir}/omnispec-${ver}-${agent}.zip"
            local simple_dir="${agent_dir}/omnispec-${ver}"

            info "  ${agent}: ${dname}"

            # cp ZIP（去时间戳，保留 agent）
            if [ -f "${agent_dir}/${dname}.zip" ] && cp "${agent_dir}/${dname}.zip" "$simple_zip"; then
                info "    ✓ omnispec-${ver}-${agent}.zip"
            else
                warn "    ✗ ZIP 复制失败"; failed=$((failed+1)); continue
            fi

            # mv 目录（去 agent 和时间戳）
            [ -d "$simple_dir" ] && rm -rf "$simple_dir"
            if mv "$tdir" "$simple_dir"; then
                info "    ✓ omnispec-${ver}/"
                success=$((success+1))
            else
                error "    ✗ 目录重命名失败"; failed=$((failed+1))
            fi
        done < <(find "$agent_dir" -maxdepth 1 -type d -name "omnispec-v*-${agent}-[0-9]*" -print0 2>/dev/null)
    done

    info "简化完成: 成功=$success 失败=$failed"
    echo
}

# 调用 build-release.sh 构建 + 简化处理
build_and_simplify() {
    local dev_repo_path="$1"
    local version="$2"
    local output_dir="$3"

    local build_script="${dev_repo_path}/build/build-release.sh"
    [ ! -f "$build_script" ] && { error "build-release.sh 不存在: $build_script"; return 1; }
    [ ! -x "$build_script" ] && chmod +x "$build_script"

    info "调用 build-release.sh (version=$version, output=$output_dir)..."
    if ! (cd "$dev_repo_path" && "$build_script" --version "$version" --output "$output_dir" --clean-output); then
        error "构建失败"
        return 1
    fi
    info "构建成功"
    echo

    simplify_releases "$output_dir"
}

# 合并拷贝到目标路径
merge_to_release() {
    local src="$1/release"
    local dst="$2/release"

    [ ! -d "$src" ] && { error "源目录不存在: $src"; return 1; }
    mkdir -p "$dst"

    info "合并拷贝: $src -> $dst"
    cp -a "$src"/. "$dst"/
    info "合并完成"
    echo
}

# 主函数
main() {
    local release_repo_path="" version="" clean=false clean_output=false

    while [[ $# -gt 0 ]]; do
        case "$1" in
            -h|--help) show_usage; exit 0 ;;
            -r|--release-repo)
                [ -z "${2:-}" ] && { error "--release-repo 需要指定路径"; exit 1; }
                release_repo_path="$2"; shift 2 ;;
            -v|--version)
                [ -z "${2:-}" ] || [[ "${2:-}" =~ ^- ]] && { error "--version 需要指定版本号"; exit 1; }
                validate_version "$2" || exit 1
                version="$2"; shift 2 ;;
            --clean|--remove) clean=true; shift ;;
            --clean-output) clean_output=true; shift ;;
            *) error "未知参数: $1"; exit 1 ;;
        esac
    done

    echo "=========================================="
    echo "  OmniSpec 版本制品发布脚本"
    echo "=========================================="
    echo

    local dev_repo_path="$(cd "$SCRIPT_DIR/.." && pwd)"

    # 版本号
    [ -z "$version" ] && info "未指定版本号，从 build/version 文件读取..."
    version=$(get_version "$version" "${dev_repo_path}/build/version")
    validate_version "$version" || { error "版本号格式错误: $version"; exit 1; }

    # 输出路径：不指定时输出到本地 output 目录
    local need_transfer=false
    local build_output_dir="${dev_repo_path}/output"
    if [ -z "$release_repo_path" ]; then
        release_repo_path="$dev_repo_path/output"
    else
        release_repo_path="$(cd "$release_repo_path" && pwd)"
        [ ! -d "$release_repo_path" ] && { error "Release repo 路径不存在: $release_repo_path"; exit 1; }
        # 指定了外部路径时需要中转
        if [ "$release_repo_path" != "${dev_repo_path}/output" ]; then
            need_transfer=true
        fi
    fi

    info "版本号: $version"
    info "输出路径: $release_repo_path/release"
    [ "$need_transfer" = true ] && info "临时目录: $build_output_dir"
    if [ "$clean" = true ]; then
        if [ "$need_transfer" = true ]; then
            info "构建后清理: 是"
        else
            warn "--clean 参数在本地模式下无效（输出即最终目录），已忽略"
            clean=false
        fi
    fi
    [ "$clean_output" = true ] && info "清理目标输出: 是"
    echo

    # clean-output：先删除目标路径
    if [ "$clean_output" = true ] && [ -d "$release_repo_path/release" ]; then
        info "清理目标输出目录: $release_repo_path/release"
        rm -rf "$release_repo_path/release"
        echo
    fi

    # 构建 + 简化
    mkdir -p "$build_output_dir"
    if ! build_and_simplify "$dev_repo_path" "$version" "$build_output_dir"; then
        error "制作开发版本失败"; exit 1
    fi

    # 中转模式：合并拷贝 + 清理临时目录
    if [ "$need_transfer" = true ]; then
        merge_to_release "$build_output_dir" "$release_repo_path" || { error "合并拷贝失败"; exit 1; }
        if [ "$clean" = true ] && [ -d "$build_output_dir" ]; then
            info "清理临时目录: $build_output_dir"
            rm -rf "$build_output_dir"
            echo
        fi
    fi

    info "版本制品发布完成！"
    info "输出: $release_repo_path/release/<agent>/"
    info "  - omnispec-vX.Y.Z-<agent>.zip (推荐)"
    info "  - omnispec-vX.Y.Z-<agent>-TIMESTAMP.zip"
    info "  - omnispec-vX.Y.Z/ (构建目录)"
    echo
}

main "$@"
