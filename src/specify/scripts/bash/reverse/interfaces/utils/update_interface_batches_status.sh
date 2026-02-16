#!/bin/bash
# -*- coding: utf-8 -*-
#
# 批量更新接口批次状态工具包装脚本 (Bash)
# 调用Python脚本批量更新接口批次状态
#
# 使用方法:
#   ./update_interface_batches_status.sh --repo-root <repo_root> --batch-updates '<batch_updates_json>'
#

set -e  # 遇到错误立即退出
set -u  # 未定义变量时报错
set -o pipefail  # 管道命令失败时退出

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/../../../../python/reverse_interfaces/update_interface_batches_status.py"

# 检查Python脚本是否存在
if [[ ! -f "$PYTHON_SCRIPT" ]]; then
    echo "错误: Python脚本不存在: $PYTHON_SCRIPT" >&2
    exit 1
fi

# 检查Python环境
if ! command -v python3 &>/dev/null; then
    echo "错误: 未找到python3命令" >&2
    exit 1
fi

# 初始化变量
REPO_ROOT=""
BATCH_UPDATES=""

# 解析参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --repo-root)
            REPO_ROOT="$2"
            shift 2
            ;;
        --batch-updates)
            BATCH_UPDATES="$2"
            shift 2
            ;;
        --help|-h)
            echo "使用方法: $0 --repo-root <repo_root> --batch-updates '<batch_updates_json>'" >&2
            echo "参数:" >&2
            echo "  --repo-root: 仓库根目录路径" >&2
            echo "  --batch-updates: 批次更新信息的JSON字符串，格式为 [{\"batch_number\": 1, \"status\": \"completed\"}, ...]" >&2
            exit 0
            ;;
        *)
            echo "未知参数: $1" >&2
            echo "使用方法: $0 --repo-root <repo_root> --batch-updates '<batch_updates_json>'" >&2
            exit 1
            ;;
    esac
done

# 验证必需参数
if [[ -z "$REPO_ROOT" ]] || [[ -z "$BATCH_UPDATES" ]]; then
    echo "错误: 必须提供 --repo-root 和 --batch-updates 参数" >&2
    echo "使用方法: $0 --repo-root <repo_root> --batch-updates '<batch_updates_json>'" >&2
    exit 1
fi

# 验证仓库根目录
if [[ ! -d "$REPO_ROOT" ]]; then
    echo "错误: 仓库根目录不存在: $REPO_ROOT" >&2
    exit 1
fi

# 转换为绝对路径
REPO_ROOT=$(cd "$REPO_ROOT" && pwd)

# 执行Python脚本
python3 "$PYTHON_SCRIPT" "$REPO_ROOT" --batch-updates "$BATCH_UPDATES"