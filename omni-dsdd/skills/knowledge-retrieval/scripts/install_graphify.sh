#!/bin/bash
# Graphify 一键安装脚本 (Linux / macOS)
# 使用方法: ./install_graphify.sh [platform]
#   - 不带参数: 默认安装 Claude Code 平台
#   - 带参数:   安装指定平台 (codebuddy/codex/opencode/claw/droid/trae/trae-cn)

set -e

PLATFORM="$1"

# 解析参数 - 支持 --platform 风格
if [[ "$1" == "--platform" ]]; then
    PLATFORM="$2"
fi

echo "=========================================="
echo "  Graphify 安装脚本"
echo "=========================================="

# 1. 检查 Python 版本
echo ""
echo "[1/3] 检查 Python 版本..."
PYTHON_VERSION=$(python --version 2>&1 | grep -oP '\d+\.\d+' || echo "0")
PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)

if [[ "$PYTHON_MAJOR" -lt 3 ]] || [[ "$PYTHON_MAJOR" -eq 3 && "$PYTHON_MINOR" -lt 10 ]]; then
    echo "错误: 需要 Python 3.10 或更高版本，当前版本: $(python --version 2>&1)"
    exit 1
fi
echo "  Python 版本检查通过: $(python --version 2>&1)"

# 2. 安装 graphify
echo ""
echo "[2/3] 安装 graphify (公共源)..."
python -m pip install --user \
    graphify

if [ $? -eq 0 ]; then
    echo "  graphify 安装成功!"
else
    echo "错误: graphify 安装失败"
    exit 1
fi

# 3. 注册 skill
echo ""
echo "[3/3] 注册 Graphify Skill..."

# 检测 graphify 命令位置
GRAPHIFY_CMD=""
if command -v graphify &> /dev/null; then
    GRAPHIFY_CMD="graphify"
elif [ -f "$HOME/.local/bin/graphify" ]; then
    GRAPHIFY_CMD="$HOME/.local/bin/graphify"
elif [ -f "$HOME/.local/bin/graphify.exe" ]; then
    GRAPHIFY_CMD="$HOME/.local/bin/graphify.exe"
fi

if [ -z "$GRAPHIFY_CMD" ]; then
    echo "错误: 未找到 graphify 命令，请确保 pip 安装成功"
    exit 1
fi

# 执行注册
if [ -n "$PLATFORM" ]; then
    echo "  指定平台: $PLATFORM"
    $GRAPHIFY_CMD install --platform "$PLATFORM"
    REGISTERED_PLATFORM="$PLATFORM"
else
    $GRAPHIFY_CMD install
    REGISTERED_PLATFORM="claude-code"
fi

if [ $? -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "  安装完成!"
    echo "=========================================="
    echo ""
    echo "使用 graphify 命令开始知识图谱构建:"
    echo "  graphify"
    echo ""
    echo "已注册平台: $REGISTERED_PLATFORM"
else
    echo "错误: Skill 注册失败"
    exit 1
fi
