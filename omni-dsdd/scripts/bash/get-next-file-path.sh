#!/usr/bin/env bash
set -e
set -u
set -o pipefail

# 从批次文件中获取下一个要处理的文件路径
#
# 用法:
#   get-next-file-path.sh --batch-file <批次文件路径> --file-index <文件索引> --repo-root <仓库根目录>
#
# 参数:
#   --batch-file: 批次文件路径（如 batch-details-3.json）
#   --file-index: 文件在批次中的索引（从0开始），如果为-1则自动查找下一个未处理的文件
#   --repo-root: 仓库根目录路径
#
# 输出:
#   输出文件的绝对路径（如果成功）
#   如果失败，输出错误信息到stderr并返回非零退出码

log_error() {
    echo "[ERROR] $*" >&2
}

# 解析参数
BATCH_FILE=""
FILE_INDEX=""
REPO_ROOT=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --batch-file)
            BATCH_FILE="$2"
            shift 2
            ;;
        --file-index)
            FILE_INDEX="$2"
            shift 2
            ;;
        --repo-root)
            REPO_ROOT="$2"
            shift 2
            ;;
        --help|-h)
            echo "用法: $0 --batch-file <批次文件路径> --file-index <文件索引> --repo-root <仓库根目录>"
            exit 0
            ;;
        *)
            log_error "未知参数: $1"
            exit 1
            ;;
    esac
done

# 验证必需参数
if [[ -z "$BATCH_FILE" ]]; then
    log_error "缺少必需参数: --batch-file"
    exit 1
fi

if [[ -z "$FILE_INDEX" ]]; then
    log_error "缺少必需参数: --file-index"
    exit 1
fi

if [[ -z "$REPO_ROOT" ]]; then
    log_error "缺少必需参数: --repo-root"
    exit 1
fi

# 验证仓库根目录
if [[ ! -d "$REPO_ROOT" ]]; then
    log_error "仓库根目录不存在: $REPO_ROOT"
    exit 1
fi

# 验证批次文件是否存在
if [[ ! -f "$BATCH_FILE" ]]; then
    log_error "批次文件不存在: $BATCH_FILE"
    exit 1
fi

# 使用jq或python提取文件路径（支持新旧格式）
if command -v jq >/dev/null 2>&1; then
    # 如果 file_index 为 -1，自动查找下一个未处理的文件（且文件存在）
    if [[ "$FILE_INDEX" == "-1" ]]; then
        # 使用jq查找所有未处理的文件，然后检查哪个存在
        # 注意：jq无法直接检查文件是否存在，所以我们需要使用python3来处理
        # 如果只有jq可用，则回退到原来的逻辑（但会在后续步骤中检查文件存在性）
        if command -v python3 >/dev/null 2>&1; then
            # 使用python3来查找第一个存在且未处理的文件
            RELATIVE_FILE_PATH=$(python3 -c "
import json
import os
import sys
from pathlib import Path

try:
    with open('$BATCH_FILE', 'r', encoding='utf-8') as f:
        data = json.load(f)
    if 'files' not in data:
        print('ERROR: 批次文件中缺少 files 字段', file=sys.stderr)
        sys.exit(1)
    files = data['files']
    if not isinstance(files, list):
        print('ERROR: 批次文件中的 files 字段不是数组', file=sys.stderr)
        sys.exit(1)
    
    repo_root = Path('$REPO_ROOT').resolve()
    
    for file_entry in files:
        if isinstance(file_entry, dict):
            file_status = file_entry.get('status', 'pending')
            if file_status not in ('completed', 'failed'):
                relative_path = file_entry.get('path', '')
                if relative_path:
                    try:
                        absolute_path = (repo_root / relative_path).resolve()
                        if absolute_path.exists() and absolute_path.is_file():
                            print(relative_path)
                            sys.exit(0)
                    except Exception:
                        continue
        else:
            # 旧格式：直接是字符串
            if file_entry:
                try:
                    absolute_path = (repo_root / file_entry).resolve()
                    if absolute_path.exists() and absolute_path.is_file():
                        print(file_entry)
                        sys.exit(0)
                except Exception:
                    continue
    
    print('ERROR: 批次中没有未处理且存在的文件', file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f'ERROR: {e}', file=sys.stderr)
    sys.exit(1)
" 2>&1)
            
            if [[ $? -ne 0 ]]; then
                log_error "$RELATIVE_FILE_PATH"
                exit 1
            fi
        else
            # 回退到jq方式（不检查文件存在性，会在后续步骤中检查）
            RELATIVE_FILE_PATH=$(jq -r '.files[] | select(.status != "completed" and .status != "failed") | .path // .' "$BATCH_FILE" 2>/dev/null | head -n 1)
            
            if [[ -z "$RELATIVE_FILE_PATH" ]] || [[ "$RELATIVE_FILE_PATH" == "null" ]]; then
                log_error "批次中没有未处理的文件"
                exit 1
            fi
        fi
    else
        # 使用jq提取指定索引的文件路径（支持新旧格式）
        FILE_ENTRY=$(jq -r --argjson index "$FILE_INDEX" '.files[$index] // empty' "$BATCH_FILE" 2>/dev/null)
        
        if [[ -z "$FILE_ENTRY" ]] || [[ "$FILE_ENTRY" == "null" ]]; then
            log_error "文件索引 $FILE_INDEX 超出范围或无效"
            exit 1
        fi
        
        # 判断是新格式（对象）还是旧格式（字符串）
        if echo "$FILE_ENTRY" | jq -e 'type == "object"' >/dev/null 2>&1; then
            # 新格式：对象包含 path 字段
            RELATIVE_FILE_PATH=$(echo "$FILE_ENTRY" | jq -r '.path // empty' 2>/dev/null)
        else
            # 旧格式：直接是字符串
            RELATIVE_FILE_PATH="$FILE_ENTRY"
        fi
        
        if [[ -z "$RELATIVE_FILE_PATH" ]] || [[ "$RELATIVE_FILE_PATH" == "null" ]]; then
            log_error "无法从文件条目中提取路径: $FILE_ENTRY"
            exit 1
        fi
    fi
elif command -v python3 >/dev/null 2>&1; then
    # 使用python3提取文件路径（支持新旧格式和自动查找）
    RELATIVE_FILE_PATH=$(python3 -c "
import json
import sys
try:
    with open('$BATCH_FILE', 'r', encoding='utf-8') as f:
        data = json.load(f)
    if 'files' not in data:
        print('ERROR: 批次文件中缺少 files 字段', file=sys.stderr)
        sys.exit(1)
    files = data['files']
    if not isinstance(files, list):
        print('ERROR: 批次文件中的 files 字段不是数组', file=sys.stderr)
        sys.exit(1)
    
    file_index = int('$FILE_INDEX')
    
    # 如果 file_index 为 -1，自动查找下一个未处理的文件（且文件存在）
    if file_index == -1:
        import os
        from pathlib import Path
        repo_root = Path('$REPO_ROOT').resolve()
        
        for file_entry in files:
            if isinstance(file_entry, dict):
                # 新格式：对象包含 path 和 status
                file_status = file_entry.get('status', 'pending')
                if file_status not in ('completed', 'failed'):
                    relative_path = file_entry.get('path', '')
                    if relative_path:
                        try:
                            absolute_path = (repo_root / relative_path).resolve()
                            if absolute_path.exists() and absolute_path.is_file():
                                print(relative_path)
                                sys.exit(0)
                        except Exception:
                            continue
            else:
                # 旧格式：直接是字符串，默认未处理
                if file_entry:
                    try:
                        absolute_path = (repo_root / file_entry).resolve()
                        if absolute_path.exists() and absolute_path.is_file():
                            print(file_entry)
                            sys.exit(0)
                    except Exception:
                        continue
        print('ERROR: 批次中没有未处理且存在的文件', file=sys.stderr)
        sys.exit(1)
    else:
        # 使用指定索引
        if file_index < 0 or file_index >= len(files):
            print(f'ERROR: 文件索引 {file_index} 超出范围 [0, {len(files)-1}]', file=sys.stderr)
            sys.exit(1)
        
        file_entry = files[file_index]
        if isinstance(file_entry, dict):
            # 新格式：对象包含 path 字段
            relative_path = file_entry.get('path', '')
            if not relative_path:
                print('ERROR: 文件对象中缺少 path 字段', file=sys.stderr)
                sys.exit(1)
            print(relative_path)
        elif isinstance(file_entry, str):
            # 旧格式：直接是字符串
            print(file_entry)
        else:
            print(f'ERROR: 文件条目格式无效: {file_entry}', file=sys.stderr)
            sys.exit(1)
except Exception as e:
    print(f'ERROR: {e}', file=sys.stderr)
    sys.exit(1)
" 2>&1)
    
    if [[ $? -ne 0 ]]; then
        log_error "$RELATIVE_FILE_PATH"
        exit 1
    fi
else
    log_error "需要 jq 或 python3 来解析JSON文件"
    exit 1
fi

# 转换为绝对路径
ABSOLUTE_FILE_PATH=$(cd "$REPO_ROOT" && realpath "$RELATIVE_FILE_PATH" 2>/dev/null || echo "")

if [[ -z "$ABSOLUTE_FILE_PATH" ]]; then
    log_error "无法解析文件路径: $RELATIVE_FILE_PATH (基于仓库根目录: $REPO_ROOT)"
    exit 1
fi

# 验证文件是否存在
if [[ ! -f "$ABSOLUTE_FILE_PATH" ]]; then
    log_error "文件不存在: $ABSOLUTE_FILE_PATH (相对路径: $RELATIVE_FILE_PATH)"
    exit 1
fi

# 输出绝对路径
echo "$ABSOLUTE_FILE_PATH"
exit 0

