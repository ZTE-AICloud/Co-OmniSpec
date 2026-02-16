#!/usr/bin/env bash

# OmniSpec 版本号工具函数
# 功能：提供统一的版本号读取和验证函数，避免在多个脚本中重复实现

# 默认版本号（当无法从文件读取时使用）
readonly DEFAULT_VERSION="v2.0.0"

# 验证版本号格式（三段式：vX.Y.Z）
validate_version() {
    local version="$1"
    
    # 检查格式：必须以 v 开头，后跟三段数字，用点分隔
    if [[ ! "$version" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        return 1
    fi
    
    return 0
}

# 从 version 文件读取版本号
# 参数：
#   $1 - version 文件路径（可选，默认为脚本所在目录的 version 文件）
# 返回：
#   成功：输出版本号到 stdout，返回 0
#   失败：输出默认版本号到 stdout，返回 0（不会失败）
read_version_from_file() {
    local version_file="${1:-}"
    
    # 如果未指定文件路径，尝试自动检测
    if [ -z "$version_file" ]; then
        # 尝试从调用者的 SCRIPT_DIR 获取
        if [ -n "${SCRIPT_DIR:-}" ]; then
            version_file="${SCRIPT_DIR}/version"
        else
            # 尝试从当前脚本目录获取
            local this_script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
            version_file="${this_script_dir}/version"
        fi
    fi
    
    # 检查文件是否存在
    if [ ! -f "$version_file" ]; then
        echo "$DEFAULT_VERSION"
        return 0
    fi
    
    # 读取 version= 开头的行，提取版本号
    local version_line=$(grep -E "^version=" "$version_file" | head -n 1)
    
    if [ -z "$version_line" ]; then
        echo "$DEFAULT_VERSION"
        return 0
    fi
    
    # 提取版本号（去掉 version= 前缀）
    local version="${version_line#version=}"
    
    # 去除可能的空白字符
    version=$(echo "$version" | tr -d '[:space:]')
    
    # 验证版本号格式
    if [ -z "$version" ] || ! validate_version "$version"; then
        echo "$DEFAULT_VERSION"
        return 0
    fi
    
    echo "$version"
    return 0
}

# 获取版本号（优先级：参数 > 文件 > 默认值）
# 参数：
#   $1 - 指定的版本号（可选）
#   $2 - version 文件路径（可选）
# 返回：
#   输出版本号到 stdout
get_version() {
    local specified_version="${1:-}"
    local version_file="${2:-}"
    
    # 如果指定了版本号，验证后直接使用
    if [ -n "$specified_version" ]; then
        if validate_version "$specified_version"; then
            echo "$specified_version"
            return 0
        else
            # 格式错误，回退到文件读取
            >&2 echo "警告：指定的版本号格式错误: $specified_version"
        fi
    fi
    
    # 从文件读取
    read_version_from_file "$version_file"
}

# 使用示例（供其他脚本参考）:
#
# # 在脚本开头 source 此文件
# SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# source "$SCRIPT_DIR/version-utils.sh"
#
# # 方式 1: 直接读取文件
# version=$(read_version_from_file)
# version=$(read_version_from_file "$SCRIPT_DIR/version")
#
# # 方式 2: 使用 get_version（推荐）
# version=$(get_version)                           # 从文件读取
# version=$(get_version "$user_specified_version") # 优先使用参数
# version=$(get_version "" "$custom_version_file") # 使用自定义文件
#
# # 方式 3: 验证版本号
# if validate_version "$version"; then
#     echo "版本号格式正确"
# fi
