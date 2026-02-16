#!/usr/bin/env bash
set -e
set -u
set -o pipefail

# build-on-demand-index.sh
# 构建 omni-doc/relations/requirement-function.json（需求 -> 功能标识列表）
# 数据源：omni-doc/on-demand-existing-function-analysis-*.md + omni-doc/on-demand/functions/*.md

SCRIPT_DIR="$(CDPATH="" cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/../../common.sh"

log_info() { echo "[build-on-demand-index] INFO: $*" >&2; }
log_warn() { echo "[build-on-demand-index] WARN: $*" >&2; }
log_error() { echo "[build-on-demand-index] ERROR: $*" >&2; }
die() { log_error "$*"; exit 1; }

print_help() {
  cat <<'EOF'
用法:
  build-on-demand-index.sh --repo-root <REPO_ROOT> [--dry-run]

参数:
  --repo-root <path>   仓库根目录（绝对路径或相对路径均可）
  --dry-run            仅打印将写入的目标路径与统计信息，不落盘写文件
  --help               显示帮助

产物:
  <REPO_ROOT>/omni-doc/relations/requirement-function.json

说明:
  - 全量重建：扫描所有主汇总文档 on-demand-existing-function-analysis-*.md
  - 仅收录存在功能文档的 function_key：omni-doc/on-demand/functions/<function_key>.md
  - function_key 仅允许 [a-z0-9_-]+
  - 原子写入：先写 *.tmp，校验 JSON 后 rename 覆盖
EOF
}

require_cmd() {
  local cmd="$1"
  command -v "$cmd" >/dev/null 2>&1 || die "缺少依赖命令：$cmd"
}

parse_args() {
  REPO_ROOT=""
  DRY_RUN="false"

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --repo-root)
        shift
        [[ $# -gt 0 ]] || die "--repo-root 需要一个参数"
        REPO_ROOT="$1"
        ;;
      --dry-run)
        DRY_RUN="true"
        ;;
      --help|-h)
        print_help
        exit 0
        ;;
      *)
        die "未知参数：$1（使用 --help 查看用法）"
        ;;
    esac
    shift
  done

  [[ -n "$REPO_ROOT" ]] || die "必须提供 --repo-root"
  # 归一化为绝对路径（不要求仓库是 git）
  REPO_ROOT="$(CDPATH="" cd "$REPO_ROOT" && pwd)"
}

extract_requirement_id() {
  local doc_path="$1"
  local content="$2"

  local rid=""
  # 优先：文档元数据中 **需求ID**: TCF-xxxx
  rid="$(printf "%s\n" "$content" | grep -m1 -oE '\*\*需求ID\*\*:[[:space:]]*[A-Za-z]+-[0-9]+' | sed -E 's/.*\*\*需求ID\*\*:[[:space:]]*//')"

  if [[ -n "$rid" ]]; then
    printf "%s" "$rid"
    return 0
  fi

  # 兜底：从文件名提取 TCF-xxxx
  rid="$(basename "$doc_path" | grep -oE '[A-Za-z]+-[0-9]+' | head -n 1 || true)"
  if [[ -n "$rid" ]]; then
    printf "%s" "$rid"
    return 0
  fi

  return 1
}

extract_function_keys_from_main_doc() {
  # 从主汇总文档内容中解析“2.1 功能清单”表格的“功能标识”列
  # - 文档内容从 stdin 读取
  # - 参数1：输出文件路径
  local out_file="$1"

  # 输出每行一个 function_key（可能包含重复；后续统一去重）
  # 解析策略：
  # - 找到包含“2.1 功能清单”的行作为起点
  # - 在其后捕获 markdown 表格（以 | 开头）
  # - 读取表头，定位“功能标识”列索引
  # - 逐行取出该列的值，trim 后输出
  python3 -c '
import re, sys
out_file = sys.argv[1]
content = sys.stdin.read().splitlines()

start = None
for i, line in enumerate(content):
    if "2.1" in line and "功能清单" in line:
        start = i
        break

keys = []
if start is not None:
    header_i = None
    for j in range(start + 1, len(content)):
        if content[j].lstrip().startswith("|"):
            header_i = j
            break
        if re.match(r"^\s*#{1,6}\s+", content[j]):
            break

    if header_i is not None and header_i + 1 < len(content):
        header = [c.strip() for c in content[header_i].strip().strip("|").split("|")]
        sep = content[header_i + 1].strip()
        if sep.lstrip().startswith("|") and "---" in sep:
            try:
                idx = header.index("功能标识")
            except ValueError:
                idx = None

            if idx is not None:
                for k in range(header_i + 2, len(content)):
                    line = content[k].strip()
                    if not line.startswith("|"):
                        break
                    cols = [c.strip() for c in line.strip().strip("|").split("|")]
                    if idx < len(cols):
                        v = cols[idx].strip()
                        if v:
                            keys.append(v)

with open(out_file, "w", encoding="utf-8") as f:
    for k in keys:
        f.write(k + "\n")
' "$out_file"
}

validate_function_key() {
  local k="$1"
  [[ "$k" =~ ^[a-z0-9_-]+$ ]]
}

build_pairs_tsv() {
  local repo_root="$1"
  local pairs_tsv="$2"

  local sk_dir="$repo_root/omni-doc"
  local main_glob="$sk_dir/on-demand-existing-function-analysis-"'*.md'
  local functions_dir="$sk_dir/on-demand/functions"

  [[ -d "$sk_dir" ]] || die "目录不存在：$sk_dir"
  [[ -d "$functions_dir" ]] || log_warn "功能文档目录不存在：$functions_dir（将导致 targets 为空）"

  : >"$pairs_tsv"

  shopt -s nullglob
  local main_docs=($main_glob)
  shopt -u nullglob

  if [[ ${#main_docs[@]} -eq 0 ]]; then
    log_warn "未找到主汇总文档：$main_glob"
    return 0
  fi

  local tmp_keys
  tmp_keys="$(mktemp)"

  for doc in "${main_docs[@]}"; do
    local content
    content="$(cat "$doc")"

    local rid=""
    if ! rid="$(extract_requirement_id "$doc" "$content")"; then
      log_warn "无法提取 requirement_id，跳过：$doc"
      continue
    fi

    extract_function_keys_from_main_doc "$tmp_keys" <<<"$content"

    while IFS= read -r raw_key; do
      local key
      key="$(echo "$raw_key" | sed -E 's/^[[:space:]]+//;s/[[:space:]]+$//')"
      [[ -n "$key" ]] || continue

      if ! validate_function_key "$key"; then
        log_warn "function_key 非法（仅允许 [a-z0-9_-]+），跳过：rid=$rid key=$key doc=$(basename "$doc")"
        continue
      fi

      local fdoc="$functions_dir/$key.md"
      if [[ ! -f "$fdoc" ]]; then
        log_warn "功能文档不存在，跳过：rid=$rid key=$key expected=$fdoc"
        continue
      fi

      printf "%s\t%s\n" "$rid" "$key" >>"$pairs_tsv"
    done <"$tmp_keys"
  done

  rm -f "$tmp_keys"
}

write_relations_json_atomically() {
  local pairs_tsv="$1"
  local out_json="$2"

  local out_dir
  out_dir="$(dirname "$out_json")"
  mkdir -p "$out_dir"

  local tmp_json
  tmp_json="$out_json.tmp"

  # TSV -> JSON（按 requirement_id 聚合 + targets 去重排序）
  python3 - "$pairs_tsv" "$tmp_json" <<'PY'
import json
import sys
from collections import defaultdict

pairs_tsv, out_path = sys.argv[1], sys.argv[2]
mp = defaultdict(set)

with open(pairs_tsv, "r", encoding="utf-8") as f:
    for line in f:
        line = line.rstrip("\n")
        if not line:
            continue
        try:
            rid, key = line.split("\t", 1)
        except ValueError:
            continue
        rid = rid.strip()
        key = key.strip()
        if rid and key:
            mp[rid].add(key)

relations = []
for rid in sorted(mp.keys()):
    targets = sorted(mp[rid])
    relations.append({"source": rid, "targets": targets})

with open(out_path, "w", encoding="utf-8") as f:
    json.dump(relations, f, ensure_ascii=False, indent=2)
    f.write("\n")

# basic parse check (already dumped, but keep explicit)
with open(out_path, "r", encoding="utf-8") as f:
    json.load(f)
PY

  # 原子覆盖
  mv -f "$tmp_json" "$out_json"
}

main() {
  require_cmd python3
  parse_args "$@"

  local out_json="$REPO_ROOT/omni-doc/relations/requirement-function.json"
  local pairs_tsv
  pairs_tsv="$(mktemp)"

  log_info "开始构建关系文件（全量重建）"
  log_info "REPO_ROOT=$REPO_ROOT"

  build_pairs_tsv "$REPO_ROOT" "$pairs_tsv"

  local pair_count
  pair_count="$(wc -l <"$pairs_tsv" | tr -d ' ')"
  log_info "收集到 (requirement_id, function_key) 记录数：$pair_count"

  if [[ "$DRY_RUN" == "true" ]]; then
    log_info "--dry-run：不落盘写入"
    log_info "目标文件：$out_json"
    rm -f "$pairs_tsv"
    return 0
  fi

  write_relations_json_atomically "$pairs_tsv" "$out_json"
  rm -f "$pairs_tsv"

  log_info "写入完成：$out_json"
}

main "$@"


