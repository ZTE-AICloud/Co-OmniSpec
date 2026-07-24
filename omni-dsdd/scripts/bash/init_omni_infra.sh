#!/usr/bin/env bash
# 将插件 omni-infra/ 种子同步到工作区 .omni-infra/（禁止脚本内用 pwd 推断工作区）
set -euo pipefail

readonly USAGE_MSG="Usage: $0 --plugin-root <path> --working-dir <path> [--knowledge-dir <path>]"

PLUGIN_ROOT=""
WORKING_DIR=""
KNOWLEDGE_DIR=""
EXIT_CODE=0  # 0=已存在 1=首次创建 2=错误（由各步骤按需设置，末尾统一退出）

while [[ $# -gt 0 ]]; do
  case "$1" in
    --plugin-root)
      shift
      [[ $# -gt 0 ]] || { echo "Error: --plugin-root requires a value" >&2; exit 2; }
      PLUGIN_ROOT="$1"
      ;;
    --working-dir)
      shift
      [[ $# -gt 0 ]] || { echo "Error: --working-dir requires a value" >&2; exit 2; }
      WORKING_DIR="$1"
      ;;
    --knowledge-dir)
      shift
      [[ $# -gt 0 ]] || { echo "Error: --knowledge-dir requires a value" >&2; exit 2; }
      KNOWLEDGE_DIR="$1"
      ;;
    -h|--help)
      echo "$USAGE_MSG"
      echo ""
      echo "Options:"
      echo "  --knowledge-dir <path>  私域知识库根目录（相对路径基于 --working-dir；缺省 omni-doc）"
      echo ""
      echo "Exit codes:"
      echo "  0  .omni-infra already exists in working dir"
      echo "  1  .omni-infra need to be created (run Task(subagent_type="omni-dsdd:constitution") next)"
      echo "  2  error"
      exit 0
      ;;
    *)
      # 兼容旧版位置参数：init_omni_infra.sh <plugin_root> <working_dir>
      if [[ -z "$PLUGIN_ROOT" ]]; then
        PLUGIN_ROOT="$1"
      elif [[ -z "$WORKING_DIR" ]]; then
        WORKING_DIR="$1"
      else
        echo "$USAGE_MSG" >&2
        echo "Error: unknown argument: $1" >&2
        exit 2
      fi
      ;;
  esac
  shift
done

if [[ -z "$PLUGIN_ROOT" || -z "$WORKING_DIR" ]]; then
  echo "$USAGE_MSG" >&2
  echo "Error: --plugin-root and --working-dir are required" >&2
  exit 2
fi

if [[ ! -d "$PLUGIN_ROOT" ]]; then
  echo "[错误]插件根目录不存在: $PLUGIN_ROOT" >&2
  exit 2
fi
if [[ ! -d "$WORKING_DIR" ]]; then
  echo "[错误]工作区目录不存在: $WORKING_DIR" >&2
  exit 2
fi

PLUGIN_ROOT="$(CDPATH="" cd "$PLUGIN_ROOT" && pwd)"
WORKING_DIR="$(CDPATH="" cd "$WORKING_DIR" && pwd)"

# 兜底：非交互 bash 不自动 source ~/.bashrc，主动从 ~/.bashrc 提取 KNOWLEDGE_DIR。
# 仅当 CLI 未传 --knowledge-dir（$KNOWLEDGE_DIR 为空）且进程 env 无值时提取；绝不 source ~/.bashrc。
if [[ -z "$KNOWLEDGE_DIR" && -n "${HOME:-}" && -f "${HOME}/.bashrc" ]]; then
  _kb_from_rc="$(grep -E '^[[:space:]]*(export[[:space:]]+)?KNOWLEDGE_DIR=' "${HOME}/.bashrc" 2>/dev/null | tail -1 || true)"
  if [[ -n "$_kb_from_rc" ]]; then
    _kb_from_rc="$(printf '%s' "$_kb_from_rc" | sed -E 's/^[[:space:]]*(export[[:space:]]+)?KNOWLEDGE_DIR=//; s/^["'\'']//; s/["'\'']([[:space:]]+#.*)?$//')"
    if [[ -n "$_kb_from_rc" ]]; then KNOWLEDGE_DIR="$_kb_from_rc"; fi
  fi
  unset _kb_from_rc
fi

# 解析 KNOWLEDGE_DIR 为绝对路径：缺省 omni-doc；相对路径基于 WORKING_DIR；绝对路径直接用。
# 仅做路径规范化，不创建目录（目录存在性由 prepare_knowledge_config 守卫处理）。
resolve_knowledge_dir() {
  local raw="${1:-omni-doc}"
  raw="${raw:-omni-doc}"
  local base
  if [[ "$raw" = /* ]]; then
    base="$raw"
  else
    base="${WORKING_DIR}/${raw}"
  fi
  # 已存在的目录用 cd -P 拿真实绝对路径；不存在则拼规范化路径（去重复/斜杠，不 resolve 符号链接）
  if [[ -d "$base" ]]; then
    (CDPATH="" cd "$base" && pwd)
  else
    local norm="${base//\/\//\/}"
    while [[ "$norm" == */ ]]; do norm="${norm%/}"; done
    printf '%s\n' "$norm"
  fi
}
KNOWLEDGE_DIR="$(resolve_knowledge_dir "$KNOWLEDGE_DIR")"

git_init() {
  if ! git -C "$WORKING_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    git -C "$WORKING_DIR" init . >/dev/null 2>&1 || git -C "$WORKING_DIR" init .
  fi
}

prepare_infra() {
  local plugin_infra="${PLUGIN_ROOT}/omni-infra"
  local project_infra="${WORKING_DIR}/.omni-infra"

  if [[ ! -d "$plugin_infra" ]]; then
    echo "[错误]插件数据不全：$plugin_infra" >&2
    exit 2
  fi

  if [[ ! -d "$project_infra" ]]; then
    cp -r "${plugin_infra}" "${project_infra}"
    if git -C "$WORKING_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
      git -C "$WORKING_DIR" add ".omni-infra" >/dev/null 2>&1 || true
      git -C "$WORKING_DIR" commit -m "[SDD] add .omni-infra for SDD" >/dev/null 2>&1 || true
    fi
    EXIT_CODE=1  # 首次创建：标记状态码，但继续执行后续步骤（知识配置准备）后再退出
    return 0
  fi
}

prepare_cache() {
  local plugin_cache="${PLUGIN_ROOT}/.cache"
  local project_cache="${WORKING_DIR}/.cache"

  if [[ ! -d "$plugin_cache" ]]; then
    echo "[错误]插件数据不全：$plugin_cache" >&2
    exit 2
  fi

  if [[ ! -d "$project_cache" ]]; then
    cp -r "${plugin_cache}" "${project_cache}"
  else
    echo "工作区缓存目录已存在: $project_cache" >&2
  fi
}

ensure_gitignore_entries() {
  # SDD 运行时产物目录，应排除在版本控制之外。
  # changes/ 固定；知识库目录随 --knowledge-dir 动态（默认 omni-doc/，自定义则追加对应条目）。
  local -a entries=( "changes/" )

  # 把 KNOWLEDGE_DIR 转为 .gitignore 条目：WORKING_DIR 内则相对，否则绝对；均以 / 结尾匹配目录。
  local kb="$KNOWLEDGE_DIR"
  local kb_entry
  if [[ "$kb" == "$WORKING_DIR"/* ]]; then
    kb_entry="${kb#"$WORKING_DIR"/}/"
  else
    kb_entry="${kb}/"
  fi
  entries+=( "$kb_entry" )
  # 默认 omni-doc/ 始终保留（历史兼容，且反构文档库默认就在此）
  if [[ "$kb_entry" != "omni-doc/" ]]; then
    entries+=( "omni-doc/" )
  fi

  # 非 git 工作区不做处理
  git -C "$WORKING_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1 || return 0

  local gitignore_file="${WORKING_DIR}/.gitignore"
  local marker_line="# OmniSpec SDD 运行时产物（由 init_omni_infra.sh 自动维护，请勿提交）"
  local need_write=0

  # 仅当至少一个条目缺失时才写入，避免无谓改动
  local entry
  for entry in "${entries[@]}"; do
    if ! grep -qxF "$entry" "$gitignore_file" 2>/dev/null; then
      need_write=1
      break
    fi
  done

  [[ "$need_write" -eq 0 ]] && return 0

  # 追加分区注释 + 缺失条目
  {
    [[ -s "$gitignore_file" ]] && echo ""
    echo "$marker_line"
    for entry in "${entries[@]}"; do
      grep -qxF "$entry" "$gitignore_file" 2>/dev/null || echo "$entry"
    done
  } >> "$gitignore_file"

  git -C "$WORKING_DIR" add ".gitignore" >/dev/null 2>&1 || true
}

prepare_knowledge_config() {
  # 知识检索配置准备：若 ${KNOWLEDGE_DIR}（由 --knowledge-dir 解析，缺省 ${WORKING_DIR}/omni-doc）
  # 存在且其下无 knowledge.config.yaml，则拷贝插件模板并将 raw_knowledge_dir 指向该目录自身。
  # 无论目录是否存在，都把生效的 KNOWLEDGE_DIR 绝对路径写入 .omni-infra/knowledge.path 标记文件，
  # 供 constitution（早于 specify/env.sh 执行）读取。可选增强，失败不影响主流程。
  local knowledge_dir="$KNOWLEDGE_DIR"
  local target_config="${knowledge_dir}/knowledge.config.yaml"
  local source_config="${PLUGIN_ROOT}/skills/knowledge-retrieval/knowledge.config.yaml"

  # 写标记文件：记录生效的知识库绝对路径（供 constitution 等早于 env.sh 的 skill 读取）
  # .omni-infra 此时已由 prepare_infra 创建；若仍缺失则跳过标记写入
  if [[ -d "${WORKING_DIR}/.omni-infra" ]]; then
    printf '%s\n' "$knowledge_dir" > "${WORKING_DIR}/.omni-infra/knowledge.path"
  fi

  # 知识源目录不存在则跳过拷贝（由用户按需创建，脚本不主动建目录）
  [[ -d "$knowledge_dir" ]] || return 0

  # 目标配置已存在则保留用户配置，不覆盖
  if [[ -f "$target_config" ]]; then
    echo "知识检索配置已存在，跳过拷贝: $target_config" >&2
    return 0
  fi

  # 源模板缺失：仅提示，不视为错误（可选增强）
  if [[ ! -f "$source_config" ]]; then
    echo "[警告]知识检索配置模板缺失，跳过: $source_config" >&2
    return 0
  fi

  cp "$source_config" "$target_config"
  # raw_knowledge_dir 设为 . （相对 config 解析为知识库目录自身）；幂等，未命中也无妨
  sed -i 's|^raw_knowledge_dir:.*|raw_knowledge_dir: .|' "$target_config"
  echo "已生成知识检索配置: $target_config"
}

# 顺序：prepare_infra 必须先跑（创建 .omni-infra），prepare_knowledge_config 依赖它写 knowledge.path
git_init
ensure_gitignore_entries
prepare_cache
prepare_infra
prepare_knowledge_config

exit "$EXIT_CODE"
