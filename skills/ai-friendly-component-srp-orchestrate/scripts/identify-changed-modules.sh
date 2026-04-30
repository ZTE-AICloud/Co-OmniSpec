#!/usr/bin/env bash
# -*- coding: utf-8 -*-
#识别 git diff 涉及的模块，输出 changed-modules.json
#支持：已跟踪文件变更 + untracked 新增文件 + staged 变更
#修复：untracked 遗漏、前缀误判、HEREDOC 注入、空模块/删除文件归属

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"

usage() {
    echo "Usage: $0 \\"
    echo "  --project-path <path> \\"
    echo "  --modules-json <path> \\"
    echo "  --output <path> \\"
    echo "  --base-commit <commit> \\"
    echo "  [--target-commit <commit>] \\"
    echo "  [--detect-untracked] \\"
    echo "  [--detect-staged]"
    exit 1
}

PROJECT_PATH=""
MODULES_JSON=""
OUTPUT=""
BASE_COMMIT=""
TARGET_COMMIT="HEAD"
DETECT_UNTRACKED="true"
DETECT_STAGED="false"

while [[ $# -gt 0 ]]; do
    case $1 in
        --project-path)   PROJECT_PATH="$2";       shift 2 ;;
        --modules-json)   MODULES_JSON="$2";        shift 2 ;;
        --output)         OUTPUT="$2";               shift 2 ;;
        --base-commit)    BASE_COMMIT="$2";          shift 2 ;;
        --target-commit)  TARGET_COMMIT="$2";        shift 2 ;;
        --detect-untracked) DETECT_UNTRACKED="true";  shift ;;
        --no-detect-untracked) DETECT_UNTRACKED="false"; shift ;;
        --detect-staged)  DETECT_STAGED="true";     shift ;;
        --no-detect-staged) DETECT_STAGED="false";   shift ;;
        *) usage ;;
    esac
done

[[ -z "$PROJECT_PATH" || -z "$MODULES_JSON" || -z "$OUTPUT" || -z "$BASE_COMMIT" ]] && usage

cd "$PROJECT_PATH"

# ── 1. 收集变更文件 ────────────────────────────────────────────
# 已跟踪文件的 diff（工作区 vs 目标 commit）
DIFF_FILES=$(git diff --name-only "$BASE_COMMIT" "$TARGET_COMMIT" 2>/dev/null || echo "")

# Staged 变更（已 git add 但未 commit）
STAGED_FILES=""
if [[ "$DETECT_STAGED" == "true" ]]; then
    STAGED_FILES=$(git diff --cached --name-only 2>/dev/null || echo "")
fi

# Untracked 新增文件
UNTRACKED_FILES=""
if [[ "$DETECT_UNTRACKED" == "true" ]]; then
    UNTRACKED_FILES=$(git ls-files --others --exclude-standard 2>/dev/null || echo "")
fi

# 合并所有文件，去重
ALL_CHANGED=$(printf '%s\n%s\n%s\n' "$DIFF_FILES" "$STAGED_FILES" "$UNTRACKED_FILES" | grep -s . || true)
if [[ -z "$ALL_CHANGED" ]]; then
    cat > "$OUTPUT" <<'EMPTY'
{
  "mode": "incremental",
  "base_commit": "",
  "target_commit": "",
  "modules": {},
  "orphan_files": [],
  "statistics": {
    "total_changed_modules": 0,
    "total_changed_files": 0,
    "orphan_files_count": 0
  }
}
EMPTY
    # 替换占位符
    sed -i "s/\"base_commit\": \"\"/\"base_commit\": \"$BASE_COMMIT\"/" "$OUTPUT"
    sed -i "s/\"target_commit\": \"\"/\"target_commit\": \"$TARGET_COMMIT\"/" "$OUTPUT"
    echo "[ok] No changes detected"
    exit 0
fi

# ── 2. 通过 tempfile 传递数据给 Python（避免 HEREDOC 注入） ────
TEMP_CHANGED=$(mktemp)
TEMP_MODULES=$(mktemp)
TEMP_OUTPUT=$(mktemp)
trap 'rm -f "$TEMP_CHANGED" "$TEMP_MODULES" "$TEMP_OUTPUT"' EXIT

# 将变更文件列表写入临时文件
printf '%s\n' "$ALL_CHANGED" > "$TEMP_CHANGED"

# 将 modules.json 内容复制到临时文件
cp "$MODULES_JSON" "$TEMP_MODULES"

# ── 3. Python：模块匹配 + orphan 追踪 ──────────────────────────
# 通过环境变量传递标量参数，文件路径传递通过 temp 文件
export BASE_COMMIT TARGET_COMMIT TEMP_CHANGED TEMP_MODULES TEMP_OUTPUT

python3 - <<'PYEOF'
import os
import json
from pathlib import Path

temp_changed = os.environ['TEMP_CHANGED']
temp_modules  = os.environ['TEMP_MODULES']
temp_output   = os.environ['TEMP_OUTPUT']
base_commit   = os.environ.get('BASE_COMMIT', '')
target_commit = os.environ.get('TARGET_COMMIT', '')

# 读取 modules.json
with open(temp_modules, 'r', encoding='utf-8') as f:
    all_modules = json.load(f)

# 读取变更文件列表（去空行）
with open(temp_changed, 'r', encoding='utf-8') as f:
    changed_files = [line.rstrip('\n') for line in f if line.strip()]

# ── 构建模块路径集合 ──────────────────────────────────────────
# 精确匹配：mod_path 必须是变更文件路径的某一层路径前缀
# 例如：模块 "src/utils"，变更文件 "src/utils/helper.py"
#       Path("src/utils/helper.py").parts = ("src","utils","helper.py")
#       依次检查 "src/utils"（匹配）、"src"（匹配，但取第一个即最长的）
#       → 最短路径优先（第一层匹配即 break）

module_paths = set()
module_map   = {}

for category, module_list in all_modules.get('modules', {}).items():
    for mod in module_list:
        mp = mod['path']
        module_paths.add(mp)
        module_map[mp] = {
            'name': mod['name'],
            'category': category,
            'files': mod.get('files', [])
        }

matched_files = set()
changed_modules = {}

for f in changed_files:
    f_normalized = f.replace('\\', '/')
    parts = Path(f_normalized).parts

    # 从文件所在目录往上逐层查找，找最近的模块匹配
    best_match = None
    for i in range(len(parts) - 1, -1, -1):
        candidate = str(Path(*parts[:i+1]))
        if candidate in module_paths:
            best_match = candidate
            break   # 第一个匹配即最短路径，最精确

    if best_match:
        matched_files.add(f)
        category = module_map[best_match]['category']
        if category not in changed_modules:
            changed_modules[category] = []
        # 避免同一模块重复追加
        existing = {m['path'] for m in changed_modules[category]}
        if best_match not in existing:
            changed_modules[category].append({
                'name': module_map[best_match]['name'],
                'path': best_match,
                'changed_files': [],
                'files': module_map[best_match]['files']
            })
        for m in changed_modules[category]:
            if m['path'] == best_match:
                m['changed_files'].append(f)
                break

total_changed_modules = sum(len(v) for v in changed_modules.values())
total_changed_files   = len(matched_files)
orphan_files = sorted(set(changed_files) - matched_files)

result = {
    'mode': 'incremental',
    'base_commit': base_commit,
    'target_commit': target_commit,
    'modules': changed_modules,
    'orphan_files': orphan_files,
    'statistics': {
        'total_changed_modules': total_changed_modules,
        'total_changed_files': total_changed_files,
        'orphan_files_count': len(orphan_files)
    }
}

Path(temp_output).parent.mkdir(parents=True, exist_ok=True)
with open(temp_output, 'w', encoding='utf-8') as fp:
    json.dump(result, fp, ensure_ascii=False, indent=2)

print(f"{total_changed_modules} changed modules, {total_changed_files} changed files, {len(orphan_files)} orphan files")
PYEOF

PY_RET=$?

if [[ $PY_RET -ne 0 ]]; then
    echo "[error] Python matching failed" >&2
    exit 1
fi

# ── 4. 移动临时输出到目标路径 ──────────────────────────────────
mv "$TEMP_OUTPUT" "$OUTPUT"
echo "[ok] changed modules written to $OUTPUT"
