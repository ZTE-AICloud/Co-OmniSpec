#!/usr/bin/env bash

set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: load-private-specs.sh <path> <keyword1> [keyword2 ...]

在指定路径中检索关键字，返回匹配行的上下20行内容。
多个关键字是并集（OR）。

参数:
  <path>      文件或目录路径
  <keyword>   关键字（可多个）

示例:
  load-private-specs.sh doc/specs/设计文档.md "接口" "逻辑实体"
USAGE
}

if [[ $# -lt 2 ]]; then
  usage
  exit 1
fi

TARGET="$1"
shift
KEYWORDS=("$@")

if [[ ! -e "$TARGET" ]]; then
  echo "[]"
  exit 0
fi

# 搜索并去重
TMP=$(mktemp)
for kw in "${KEYWORDS[@]}"; do
  if [[ -d "$TARGET" ]]; then
    grep -Rni --include="*.md" -- "$kw" "$TARGET" 2>/dev/null || true
  else
    grep -nH -- "$kw" "$TARGET" 2>/dev/null || true
  fi
done | sort -u -t: -k1,1 -k2,2n > "$TMP"

# 生成 JSON
echo "["
first=true

while IFS=: read -r file line rest; do
  [[ -z "$file" || -z "$line" ]] && continue
  
  # 获取上下20行
  start=$((line - 20))
  [[ $start -lt 1 ]] && start=1
  end=$((line + 20))
  
  # 读取内容并转义
  context=$(sed -n "${start},${end}p" "$file" | \
    sed 's/\\/\\\\/g' | \
    sed 's/"/\\"/g' | \
    awk 'BEGIN{ORS=""} {if(NR>1) printf "\\n"; printf "%s", $0}')
  
  # 输出 JSON 对象
  if $first; then
    first=false
  else
    echo ","
  fi
  
  printf '  {"line":%d,"context":"%s"}' "$line" "$context"
done < "$TMP"

echo ""
echo "]"

rm -f "$TMP"
