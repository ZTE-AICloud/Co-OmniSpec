#!/usr/bin/env bash
# SDD 工作区清理：切回主干、删除数字编号特性分支、清理 changes/、恢复误删文件、可选重启 Claude。
#
# 典型用法（在目标工程目录）：
#   bash "${CLAUDE_PLUGIN_ROOT}/scripts/dev/reset-sdd-workspace.sh"
#   bash "${CLAUDE_PLUGIN_ROOT}/scripts/dev/reset-sdd-workspace.sh" --repo-dir /path/to/project -y
#
set -euo pipefail

SCRIPT_DIR="$(CDPATH="" cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../bash/common.sh
source "${SCRIPT_DIR}/../bash/common.sh"

REPO_DIR=""
BASE_BRANCH=""
DRY_RUN=false
ASSUME_YES=false
START_CLAUDE=true
CLEAN_CHANGES=true
RESTORE_TRACKED=true
BRANCH_PATTERN='^[0-9]+-'

usage() {
    cat <<'EOF'
Usage: reset-sdd-workspace.sh [OPTIONS]

SDD 工作区清理：checkout 主干 → 删除本地「数字编号-」分支 → 清理 changes/ → 可选启动 claude。

Options:
  --repo-dir <path>     目标 Git 工程根（默认: CLAUDE_WORKING_DIR 或当前目录）
  --base-branch <name>  主干分支名（默认: 自动检测 master，否则 main）
  --branch-pattern <re> 待删分支名正则（默认: ^[0-9]+- ，如 001-foo、002-bar）
  --no-clean-changes    不删除 changes/ 目录
  --no-restore-tracked  不执行 git restore 恢复已删除的已跟踪文件
  --no-claude           清理后不启动 claude
  --dry-run             仅打印将执行的操作
  -y, --yes             跳过确认提示
  -h, --help            显示帮助

保留分支（永不删除）: master, main, HEAD

示例:
  reset-sdd-workspace.sh -y
  reset-sdd-workspace.sh --repo-dir /path/to/project --dry-run
EOF
}

log() { printf '%s\n' "$*"; }
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

run() {
    if [[ "$DRY_RUN" == true ]]; then
        log "[dry-run] $*"
    else
        log "+ $*"
        "$@"
    fi
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --repo-dir) REPO_DIR="${2:?}"; shift 2 ;;
        --base-branch) BASE_BRANCH="${2:?}"; shift 2 ;;
        --branch-pattern) BRANCH_PATTERN="${2:?}"; shift 2 ;;
        --no-clean-changes) CLEAN_CHANGES=false; shift ;;
        --no-restore-tracked) RESTORE_TRACKED=false; shift ;;
        --no-claude) START_CLAUDE=false; shift ;;
        --dry-run) DRY_RUN=true; shift ;;
        -y|--yes) ASSUME_YES=true; shift ;;
        -h|--help) usage; exit 0 ;;
        *) die "未知参数: $1（使用 --help）" ;;
    esac
done

if [[ -z "$REPO_DIR" ]]; then
    REPO_DIR="$(get_working_dir)"
fi
REPO_DIR="$(CDPATH="" cd "$REPO_DIR" && pwd)"

git -C "$REPO_DIR" rev-parse --git-dir >/dev/null 2>&1 || die "不是 Git 仓库: $REPO_DIR"

if [[ -z "$BASE_BRANCH" ]]; then
    if git -C "$REPO_DIR" rev-parse --verify vnfp >/dev/null 2>&1; then
        BASE_BRANCH=vnfp
    elif git -C "$REPO_DIR" rev-parse --verify master >/dev/null 2>&1; then
        BASE_BRANCH=master
    elif git -C "$REPO_DIR" rev-parse --verify main >/dev/null 2>&1; then
        BASE_BRANCH=main
    else
        die "未找到 vnfp、master 或 main 分支，请用 --base-branch 指定"
    fi
fi

git -C "$REPO_DIR" rev-parse --verify "$BASE_BRANCH" >/dev/null 2>&1 \
    || die "主干分支不存在: $BASE_BRANCH"

# 收集待删分支：本地分支名匹配数字编号前缀，排除 master/main
mapfile -t ALL_LOCAL < <(git -C "$REPO_DIR" branch --format='%(refname:short)')
TO_DELETE=()
for b in "${ALL_LOCAL[@]}"; do
    [[ "$b" == "$BASE_BRANCH" || "$b" == "master" || "$b" == "main" ]] && continue
    if [[ "$b" =~ $BRANCH_PATTERN ]]; then
        TO_DELETE+=("$b")
    fi
done

log "== 工作区清理 =="
log "仓库:       $REPO_DIR"
log "主干:       $BASE_BRANCH"
log "分支规则:   $BRANCH_PATTERN"
log "删除分支:   ${#TO_DELETE[@]} 个"
if ((${#TO_DELETE[@]} > 0)); then
    printf '  - %s\n' "${TO_DELETE[@]}"
fi
[[ "$CLEAN_CHANGES" == true ]] && log "清理:       changes/"
[[ "$RESTORE_TRACKED" == true ]] && log "恢复:       git restore（已跟踪文件的删除）"
[[ "$START_CLAUDE" == true ]] && log "重启:       claude --dangerously-skip-permissions"

if [[ "$ASSUME_YES" != true && "$DRY_RUN" != true ]]; then
    printf '确认执行？[y/N] '
    read -r ans
    [[ "$ans" == [yY] || "$ans" == [yY][eE][sS] ]] || die "已取消"
fi

# 1. 切到主干
CURRENT="$(git -C "$REPO_DIR" rev-parse --abbrev-ref HEAD)"
if [[ "$CURRENT" != "$BASE_BRANCH" ]]; then
    run git -C "$REPO_DIR" checkout "$BASE_BRANCH"
else
    log "已在分支 $BASE_BRANCH，跳过 checkout"
fi

# 2. 删除数字编号分支
for b in "${TO_DELETE[@]}"; do
    run git -C "$REPO_DIR" branch -D "$b"
done

# 3. 恢复误删的已跟踪文件（如 .specstory/.gitignore）
if [[ "$RESTORE_TRACKED" == true ]]; then
    if [[ "$DRY_RUN" == true ]]; then
        deleted="$(git -C "$REPO_DIR" status --porcelain | grep '^ D' || true)"
        if [[ -n "$deleted" ]]; then
            log "[dry-run] git -C \"$REPO_DIR\" restore <deleted tracked files>"
            printf '%s\n' "$deleted"
        fi
    else
        mapfile -t DELETED_TRACKED < <(git -C "$REPO_DIR" diff --name-only --diff-filter=D || true)
        if ((${#DELETED_TRACKED[@]} > 0)); then
            run git -C "$REPO_DIR" restore -- "${DELETED_TRACKED[@]}"
        fi
    fi
fi

# 4. 清理 SDD 特性目录
if [[ "$CLEAN_CHANGES" == true ]]; then
    if [[ -d "$REPO_DIR/changes" ]]; then
        run rm -rf "$REPO_DIR/changes"
    else
        log "changes/ 不存在，跳过"
    fi
fi

# 5. 状态摘要
if [[ "$DRY_RUN" != true ]]; then
    log ""
    log "== 清理完成 =="
    git -C "$REPO_DIR" status -sb || true
    log ""
    if git -C "$REPO_DIR" rev-parse "@{u}" >/dev/null 2>&1; then
        AHEAD="$(git -C "$REPO_DIR" rev-list --count "@{u}..HEAD" 2>/dev/null || echo 0)"
        BEHIND="$(git -C "$REPO_DIR" rev-list --count "HEAD..@{u}" 2>/dev/null || echo 0)"
        if [[ "$AHEAD" != "0" || "$BEHIND" != "0" ]]; then
            log "提示: 与 origin/$BASE_BRANCH 偏离（本地超前 $AHEAD，落后 $BEHIND）；如需同步请手动 git pull"
        fi
    fi
fi

# 6. 重启 Claude
if [[ "$START_CLAUDE" == true ]]; then
    if [[ "$DRY_RUN" == true ]]; then
        log "[dry-run] exec claude --dangerously-skip-permissions"
    else
        if ! command -v claude >/dev/null 2>&1; then
            die "未找到 claude 命令，请安装或使用 --no-claude"
        fi
        log "启动 claude ..."
        cd "$REPO_DIR"
        exec claude --dangerously-skip-permissions
    fi
fi
