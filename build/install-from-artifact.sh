#!/usr/bin/env bash

set -euo pipefail

BASE_URL="https://artnj.zte.com.cn:443/artifactory/omnispec-release-generic/snapshot"

usage() {
  cat <<EOF
用法: $0 <artifact-zip-name> <project-root-dir>

示例:
  $0 omnispec-v1.1.0-claude-20251210144014.zip /path/to/your-project

说明:
- 通过 zip 文件名自动解析出制品库路径:
    ${BASE_URL}/<agent>/<artifact-zip-name>
  例如:
    ${BASE_URL}/claude/omnispec-v1.1.0-claude-20251210144014.zip
- 在指定工程目录下完成下载、解压、权限设置和版本校验
EOF
}

error() {
  echo "错误: $*" >&2
  exit 1
}

if [[ "${1-}" == "-h" || "${1-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ $# -ne 2 ]]; then
  usage
  exit 1
fi

ARTIFACT_NAME="$1"     # 例如: omnispec-v1.1.0-claude-20251210144014.zip
PROJECT_ROOT="$2"      # 例如: /path/to/your-project

# 只保留文件名部分，防止用户传入带路径的 zip
ARTIFACT_FILE="$(basename "$ARTIFACT_NAME")"

# 从文件名中解析 agent (xxx)，例如: claude / cursor / flow
# 期望格式: omnispec-v<version>-<agent>-<timestamp>.zip
AGENT="$(echo "$ARTIFACT_FILE" | sed -E 's/^omnispec-v[0-9.]+-([^-]+)-[0-9]+\.zip$/\1/')" || true

if [[ -z "$AGENT" || "$AGENT" == "$ARTIFACT_FILE" ]]; then
  error "无法从文件名解析 agent。期望格式: omnispec-v<version>-<agent>-<timestamp>.zip
示例: omnispec-v1.1.0-claude-20251210144014.zip"
fi

ARTIFACT_URL="${BASE_URL}/${AGENT}/${ARTIFACT_FILE}"

echo "=============================="
echo "准备从制品库安装 omnispec 规范环境"
echo "  工程目录  : ${PROJECT_ROOT}"
echo "  制品文件  : ${ARTIFACT_FILE}"
echo "  解析出的 agent: ${AGENT}"
echo "  制品库地址: ${ARTIFACT_URL}"
echo "=============================="

# 步骤 0: 基础校验
command -v curl >/dev/null 2>&1 || error "未找到 curl，请先安装 curl"
command -v unzip >/dev/null 2>&1 || error "未找到 unzip，请先安装 unzip"

if [[ ! -d "$PROJECT_ROOT" ]]; then
  error "工程目录不存在: ${PROJECT_ROOT}"
fi

cd "$PROJECT_ROOT"

echo
echo "#### 步骤 1: 从制品库下载发布包"
echo "cd ${PROJECT_ROOT}"
echo "curl -O ${ARTIFACT_URL}"

# 为了与手工测试行为一致，这里不使用 -L/-f，只做最简单的下载
curl -O "$ARTIFACT_URL" || error "下载失败，请检查网络或制品路径是否正确"

echo
echo "#### 步骤 2: 解压到工程目录"
echo "unzip ${ARTIFACT_FILE}"

unzip -o "$ARTIFACT_FILE" >/dev/null

echo "当前目录下的 .claude/ 与 .specify/ 结构（若存在）:"
if [[ -d ".claude" ]]; then
  ls -la .claude/ || true
else
  echo "  未找到 .claude/ 目录"
fi

if [[ -d ".specify" ]]; then
  ls -la .specify/ || true
else
  echo "  未找到 .specify/ 目录"
fi

echo
echo "#### 步骤 3: 设置脚本执行权限"
if [[ -d ".specify/scripts/bash" ]]; then
  chmod +x .specify/scripts/bash/*.sh 2>/dev/null || true
  echo "脚本权限如下:"
  ls -l .specify/scripts/bash/ || true
else
  echo "  未找到 .specify/scripts/bash/ 目录，跳过权限设置"
fi

echo
echo "#### 步骤 4: 验证安装版本"
if [[ -f ".specify/版本发布说明.md" ]]; then
  echo "版本发布说明文件存在，显示版本发布信息:"
  # 提取版本发布部分（从 "## 版本发布" 开始到文件末尾或下一个 "##" 之前）
  if grep -q "## 版本发布" .specify/版本发布说明.md; then
    # 找到 "## 版本发布" 的行号
    start_line=$(grep -n "## 版本发布" .specify/版本发布说明.md | head -1 | cut -d: -f1)
    # 找到下一个 "##" 开头的行号（排除 "## 版本发布"）
    next_section=$(awk -v start="$start_line" 'NR > start && /^## / && !/^## 版本发布/ {print NR; exit}' .specify/版本发布说明.md)
    if [[ -n "$next_section" ]]; then
      # 显示从 "## 版本发布" 到下一个 "##" 之前的内容
      sed -n "${start_line},$((next_section - 1))p" .specify/版本发布说明.md
    else
      # 如果没有下一个 "##"，显示到文件末尾
      sed -n "${start_line},\$p" .specify/版本发布说明.md
    fi
  else
    echo "  版本发布说明文件中未找到版本发布部分"
    echo "  文件前 50 行内容:"
    head -n 50 .specify/版本发布说明.md
  fi
elif [[ -f ".specify/VERSION.md" ]]; then
  # 兼容旧版本，如果存在 VERSION.md 也显示
  echo "VERSION.md 内容（兼容旧版本）:"
  cat .specify/VERSION.md
else
  echo "  未找到 .specify/版本发布说明.md 或 .specify/VERSION.md，无法校验版本"
fi

echo
echo "安装流程完成。"


