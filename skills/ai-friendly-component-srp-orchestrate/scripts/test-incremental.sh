#!/usr/bin/env bash
# -*- coding: utf-8 -*-
# 增量模块识别端到端测试（针对 identify-changed-modules.sh 的修复验证）
# 测试场景：
#   A - untracked 新增文件归属已有模块
#   B - untracked 新增文件无匹配模块 → orphan
#   C - 路径相近目录误判（src/utils vs src/utils-extra）
#   D - 特殊字符文件名（单引号、美元符）
#   E - 删除文件进入 orphan
#   F - --no-detect-untracked 跳过新增文件
# 用法：./test-incremental.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"
IDENTIFY_SCRIPT="$SKILL_DIR/scripts/identify-changed-modules.sh"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

passed=0
failed=0

pass() { echo -e "  ${GREEN}[PASS]${NC} $1"; passed=$((passed+1)); }
fail() { echo -e "  ${RED}[FAIL]${NC} $1"; failed=$((failed+1)); }
info() { echo -e "  ${YELLOW}[INFO]${NC} $1"; }

# ── 创建临时 git 仓库 ─────────────────────────────────────────
TEST_DIR=$(mktemp -d)
PROJECT_DIR="$TEST_DIR/repo"
mkdir -p "$PROJECT_DIR"
cd "$PROJECT_DIR"
git init -q
git config user.email "test@test.com"
git config user.name "Test"

# 初始 commit（避免 detached HEAD）
mkdir -p src/utils
printf "print('init')\n" > src/utils/__init__.py
git add src/
git commit -q -m "initial commit"
BASE_COMMIT=$(git rev-parse HEAD)

# ── 准备 modules.json ────────────────────────────────────────
MODULES_JSON="$TEST_DIR/modules.json"
mkdir -p "$PROJECT_DIR/state"

cat > "$MODULES_JSON" <<'JSON'
{
  "modules": {
    "核心业务域": [
      {
        "path": "src/utils",
        "name": "utils",
        "depth": 2,
        "files": [{"name": "__init__.py", "lines": 1}]
      }
    ],
    "基础设施层": [],
    "数据持久层": [],
    "接口适配层": [],
    "公共工具层": []
  }
}
JSON

OUTPUT_JSON="$TEST_DIR/changed-modules.json"

# ── 辅助函数 ──────────────────────────────────────────────────
run_script() {
    bash "$IDENTIFY_SCRIPT" \
        --project-path "$PROJECT_DIR" \
        --modules-json "$MODULES_JSON" \
        --output "$OUTPUT_JSON" \
        --base-commit "$BASE_COMMIT" \
        --target-commit HEAD > /dev/null 2>&1
}

has_orphan_file() {
    python3 -c "
import json, sys
d = json.load(open('$OUTPUT_JSON'))
print(any('$1' in f for f in d.get('orphan_files', [])))
" 2>/dev/null
}

orphan_count() {
    python3 -c "
import json
d = json.load(open('$OUTPUT_JSON'))
print(d.get('statistics', {}).get('orphan_files_count', -1))
" 2>/dev/null
}

in_module_changed_files() {
    python3 -c "
import json
d = json.load(open('$OUTPUT_JSON'))
for cats in d.get('modules', {}).values():
    for m in cats:
        if m.get('path') == '$1':
            print(m.get('changed_files', []))
" 2>/dev/null
}

is_orphan() {
    python3 -c "
import json
d = json.load(open('$OUTPUT_JSON'))
found = any('$1' in f for f in d.get('orphan_files', []))
print(found)
" 2>/dev/null
}

is_in_module() {
    python3 -c "
import json
d = json.load(open('$OUTPUT_JSON'))
for cats in d.get('modules', {}).values():
    for m in cats:
        if m.get('path') == '$1':
            print(any('$2' in f for f in m.get('changed_files', [])))
" 2>/dev/null
}

# ═══════════════════════════════════════════════════════════════
echo ""
info "────────────────────────────────────────────"
info "  场景 A：untracked 文件归属已有模块"
info "────────────────────────────────────────────"
mkdir -p "$PROJECT_DIR/src/utils"
printf "# new\n" > "$PROJECT_DIR/src/utils/new.py"
run_script

A_IN_MODULE=$(is_in_module "src/utils" "new.py")
A_ORPHAN_COUNT=$(orphan_count)
if [[ "$A_IN_MODULE" == "True" && "$A_ORPHAN_COUNT" -eq 0 ]]; then
    pass "场景 A：src/utils/new.py 归属到 src/utils，orphan_files_count=0"
elif [[ "$A_IN_MODULE" == "True" ]]; then
    fail "场景 A：文件归属正确但 orphan_files_count=$A_ORPHAN_COUNT（期望 0）"
else
    fail "场景 A：untracked 文件 new.py 未被归属到 src/utils"
fi

# ═══════════════════════════════════════════════════════════════
echo ""
info "────────────────────────────────────────────"
info "  场景 B：新增模块不在 modules.json → orphan"
info "────────────────────────────────────────────"
git add -A > /dev/null 2>&1 || true; git commit -q -m "commit A" > /dev/null 2>&1 || true
mkdir -p "$PROJECT_DIR/brand/new-module"
printf "# brand new\n" > "$PROJECT_DIR/brand/new-module/mod.py"
BASE_COMMIT=$(git rev-parse HEAD)
run_script
B_COUNT=$(orphan_count)
if [[ "$B_COUNT" -gt 0 ]]; then
    pass "场景 B：orphan_files_count=$B_COUNT（新增模块 brand/new-module 进入 orphan）"
else
    fail "场景 B：orphan_files_count=$B_COUNT，期望 > 0"
fi

# ═══════════════════════════════════════════════════════════════
echo ""
info "────────────────────────────────────────────"
info "  场景 C：路径相近目录误判（src/utils vs src/utils-extra）"
info "────────────────────────────────────────────"
git add -A > /dev/null 2>&1 || true; git commit -q -m "commit B" > /dev/null 2>&1 || true
mkdir -p "$PROJECT_DIR/src/utils-extra"
printf "# fake\n" > "$PROJECT_DIR/src/utils-extra/fake.py"
git add src/utils-extra/
git commit -q -m "add utils-extra"
TARGET_COMMIT=$(git rev-parse HEAD)
BASE_COMMIT=$(git rev-parse HEAD~1)

bash "$IDENTIFY_SCRIPT" \
    --project-path "$PROJECT_DIR" \
    --modules-json "$MODULES_JSON" \
    --output "$OUTPUT_JSON" \
    --base-commit "$BASE_COMMIT" \
    --target-commit "$TARGET_COMMIT" > /dev/null 2>&1

UTILS_EXTRA_IN_UTILS=$(python3 -c "
import json
d = json.load(open('$OUTPUT_JSON'))
for cats in d.get('modules', {}).values():
    for m in cats:
        if m.get('path') == 'src/utils':
            print(any('utils-extra' in f for f in m.get('changed_files', [])))
" 2>/dev/null)
if [[ "$UTILS_EXTRA_IN_UTILS" != "True" ]]; then
    pass "场景 C：src/utils-extra 未被误归属到 src/utils"
else
    fail "场景 C：src/utils-extra 被错误归属到 src/utils"
fi

# ═══════════════════════════════════════════════════════════════
echo ""
info "────────────────────────────────────────────"
info "  场景 D：特殊字符文件名（单引号、美元符）"
info "────────────────────────────────────────────"
git add -A > /dev/null 2>&1 || true; git commit -q -m "commit C" > /dev/null 2>&1 || true
mkdir -p "$PROJECT_DIR/src/utils"
# 文件名含单引号和美元符
touch "$PROJECT_DIR/src/utils/file'tick.py"
touch "$PROJECT_DIR/src/utils/fileDollar.py"
# 记录 commit 前状态（用于 diff 比对）
BEFORE_D=$(git rev-parse HEAD)
git add src/utils/
git commit -q -m "add special files"
AFTER_D=$(git rev-parse HEAD)

D_RET=0
bash "$IDENTIFY_SCRIPT" \
    --project-path "$PROJECT_DIR" \
    --modules-json "$MODULES_JSON" \
    --output "$OUTPUT_JSON" \
    --base-commit "$BEFORE_D" \
    --target-commit "$AFTER_D" > /dev/null 2>&1 || D_RET=$?

if [[ $D_RET -eq 0 ]]; then
    pass "场景 D：含单引号/美元符的文件名未导致脚本报错"
else
    fail "场景 D：特殊字符导致脚本返回错误码 $D_RET"
fi

# ═══════════════════════════════════════════════════════════════
echo ""
info "────────────────────────────────────────────"
info "  场景 E：删除文件进入 orphan"
info "────────────────────────────────────────────"
# 添加一个模块外文件后删除
mkdir -p "$PROJECT_DIR/temp/deleted"
printf "# temp\n" > "$PROJECT_DIR/temp/deleted/t.py"
git add temp/
git commit -q -m "add temp"
COMMIT_BEFORE=$(git rev-parse HEAD)
git rm -q -r temp/
git commit -q -m "delete temp"
COMMIT_AFTER=$(git rev-parse HEAD)

bash "$IDENTIFY_SCRIPT" \
    --project-path "$PROJECT_DIR" \
    --modules-json "$MODULES_JSON" \
    --output "$OUTPUT_JSON" \
    --base-commit "$COMMIT_BEFORE" \
    --target-commit "$COMMIT_AFTER" > /dev/null 2>&1

E_ORPHAN=$(is_orphan "temp/deleted")
if [[ "$E_ORPHAN" == "True" ]]; then
    pass "场景 E：删除文件 temp/deleted/t.py 进入 orphan_files"
else
    fail "场景 E：删除文件未被记录到 orphan_files"
fi

# ═══════════════════════════════════════════════════════════════
echo ""
info "────────────────────────────────────────────"
info "  场景 F：--no-detect-untracked 跳过新增文件"
info "────────────────────────────────────────────"
git add -A > /dev/null 2>&1 || true; git commit -q -m "commit E" > /dev/null 2>&1 || true
mkdir -p "$PROJECT_DIR/brand/extra"
printf "# extra\n" > "$PROJECT_DIR/brand/extra/e.py"

bash "$IDENTIFY_SCRIPT" \
    --project-path "$PROJECT_DIR" \
    --modules-json "$MODULES_JSON" \
    --output "$OUTPUT_JSON" \
    --base-commit "$COMMIT_AFTER" \
    --target-commit HEAD \
    --no-detect-untracked > /dev/null 2>&1

F_ORPHAN=$(orphan_count)
if [[ "$F_ORPHAN" -eq 0 ]]; then
    pass "场景 F：--no-detect-untracked 正确跳过 brand/extra/e.py"
else
    fail "场景 F：--no-detect-untracked 未生效（orphan_files_count=$F_ORPHAN）"
fi

# ═══════════════════════════════════════════════════════════════
echo ""
info "────────────────────────────────────────────"
info "  场景 G：--detect-staged 检测已 staged 未 commit 变更"
info "────────────────────────────────────────────"
git add -A > /dev/null 2>&1 || true; git commit -q -m "commit F" > /dev/null 2>&1 || true
BEFORE_G=$(git rev-parse HEAD)
mkdir -p "$PROJECT_DIR/src/utils"
printf "# staged change\n" > "$PROJECT_DIR/src/utils/staged.py"
git add src/utils/staged.py
# 注意：不 commit

G_RET=0
bash "$IDENTIFY_SCRIPT" \
    --project-path "$PROJECT_DIR" \
    --modules-json "$MODULES_JSON" \
    --output "$OUTPUT_JSON" \
    --base-commit "$BEFORE_G" \
    --target-commit HEAD \
    --detect-staged > /dev/null 2>&1 || G_RET=$?

G_STAGED_IN=$(python3 -c "
import json
d = json.load(open('$OUTPUT_JSON'))
for cats in d.get('modules', {}).values():
    for m in cats:
        if m.get('path') == 'src/utils':
            print(any('staged.py' in f for f in m.get('changed_files', [])))
" 2>/dev/null)

if [[ "$G_STAGED_IN" == "True" ]]; then
    pass "场景 G：--detect-staged 正确检测到已 staged 的 src/utils/staged.py"
elif [[ $G_RET -ne 0 ]]; then
    fail "场景 G：--detect-staged 脚本返回错误码 $G_RET"
else
    fail "场景 G：--detect-staged 未检测到 staged 文件"
fi

# ═══════════════════════════════════════════════════════════════
# 清理
rm -rf "$TEST_DIR"

# ═══════════════════════════════════════════════════════════════
echo ""
info "────────────────────────────────────────────"
echo -e "  测试完成：${GREEN}$passed 通过${NC}，${RED}$failed 失败${NC}"
info "────────────────────────────────────────────"

if [[ $failed -eq 0 ]]; then
    echo -e "  ${GREEN}全部通过！${NC}"
    exit 0
else
    echo -e "  ${RED}有 $failed 项测试失败，请检查。${NC}"
    exit 1
fi
