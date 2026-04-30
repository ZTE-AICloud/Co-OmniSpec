#!/usr/bin/env bash
set -e
set -u
set -o pipefail

# build-on-demand-index.sh
# 构建 on-demand 关系索引：
# - branch-function.json（分支 -> 功能标识列表）
# - function-interface.json（功能 -> 接口标识列表）
# - branch-interface.json（分支 -> 接口标识列表）
# 数据源：on-demand 主汇总文档 + functions/*.md + interfaces/*.md

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
  <REPO_ROOT>/omni-doc/on-demand/relations/branch-function.json
  <REPO_ROOT>/omni-doc/on-demand/relations/function-interface.json
  <REPO_ROOT>/omni-doc/on-demand/relations/branch-interface.json

说明:
  - 全量重建：扫描所有主汇总文档 on-demand/on-demand-existing-function-analysis-*.md
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

extract_branch_name() {
  local doc_path="$1"
  local bn
  bn="$(basename "$doc_path")"
  local branch
  branch="$(printf "%s\n" "$bn" | sed -nE 's/^on-demand-existing-function-analysis-(.+)\.md$/\1/p')"
  if [[ -n "$branch" ]]; then
    printf "%s" "$branch"
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

validate_interface_key() {
  local k="$1"
  [[ "$k" =~ ^[a-z0-9_-]+$ ]]
}

extract_interface_keys_from_function_doc() {
  # 从功能文档中提取接口链接：
  # - ../interfaces/<interface_key>.md
  # - on-demand/interfaces/<interface_key>.md
  # 参数1：功能文档路径
  # 参数2：输出文件路径（每行一个 interface_key）
  local function_doc="$1"
  local out_file="$2"

  python3 -c '
import re, sys
doc_path, out_file = sys.argv[1], sys.argv[2]
txt = open(doc_path, "r", encoding="utf-8").read()
pat = re.compile(r"(?:\.\./interfaces/|on-demand/interfaces/)([a-z0-9_-]+)\.md")
keys = sorted(set(pat.findall(txt)))
with open(out_file, "w", encoding="utf-8") as f:
    for k in keys:
        f.write(k + "\n")
' "$function_doc" "$out_file"
}

build_pairs_tsv() {
  local repo_root="$1"
  local pairs_tsv="$2"

  local sk_dir="$repo_root/omni-doc"
  local main_glob="$sk_dir/on-demand/on-demand-existing-function-analysis-"'*.md'
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

    local branch=""
    if ! branch="$(extract_branch_name "$doc")"; then
      log_warn "无法提取 branch_name，跳过：$doc"
      continue
    fi

    extract_function_keys_from_main_doc "$tmp_keys" <<<"$content"

    while IFS= read -r raw_key; do
      local key
      key="$(echo "$raw_key" | sed -E 's/^[[:space:]]+//;s/[[:space:]]+$//')"
      [[ -n "$key" ]] || continue

      if ! validate_function_key "$key"; then
        log_warn "function_key 非法（仅允许 [a-z0-9_-]+），跳过：branch=$branch key=$key doc=$(basename "$doc")"
        continue
      fi

      local fdoc="$functions_dir/$key.md"
      if [[ ! -f "$fdoc" ]]; then
        log_warn "功能文档不存在，跳过：branch=$branch key=$key expected=$fdoc"
        continue
      fi

      printf "%s\t%s\n" "$branch" "$key" >>"$pairs_tsv"
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

  # TSV -> JSON（按 source 聚合 + targets 去重排序）
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

write_branch_interface_json_atomically() {
  local branch_function_tsv="$1"
  local function_interface_tsv="$2"
  local out_json="$3"
  local out_dir
  out_dir="$(dirname "$out_json")"
  mkdir -p "$out_dir"

  local tmp_json
  tmp_json="$out_json.tmp"

python3 - "$branch_function_tsv" "$function_interface_tsv" "$tmp_json" <<'PY'
import json
import sys
from collections import defaultdict

bf_path, fi_path, out_path = sys.argv[1], sys.argv[2], sys.argv[3]

branch_to_functions = defaultdict(set)
func_to_interfaces = defaultdict(set)

with open(bf_path, "r", encoding="utf-8") as f:
    for line in f:
        line = line.rstrip("\n")
        if not line:
            continue
        try:
            branch, fkey = line.split("\t", 1)
        except ValueError:
            continue
        branch, fkey = branch.strip(), fkey.strip()
        if branch and fkey:
            branch_to_functions[branch].add(fkey)

with open(fi_path, "r", encoding="utf-8") as f:
    for line in f:
        line = line.rstrip("\n")
        if not line:
            continue
        try:
            fkey, ikey = line.split("\t", 1)
        except ValueError:
            continue
        fkey, ikey = fkey.strip(), ikey.strip()
        if fkey and ikey:
            func_to_interfaces[fkey].add(ikey)

relations = []
for branch in sorted(branch_to_functions.keys()):
    interfaces = set()
    for fkey in branch_to_functions[branch]:
        interfaces.update(func_to_interfaces.get(fkey, set()))
    relations.append({"source": branch, "targets": sorted(interfaces)})

with open(out_path, "w", encoding="utf-8") as f:
    json.dump(relations, f, ensure_ascii=False, indent=2)
    f.write("\n")
json.load(open(out_path, "r", encoding="utf-8"))
PY

  mv -f "$tmp_json" "$out_json"
}

build_function_interface_tsv() {
  local repo_root="$1"
  local out_tsv="$2"

  local functions_dir="$repo_root/omni-doc/on-demand/functions"
  local interfaces_dir="$repo_root/omni-doc/on-demand/interfaces"

  : >"$out_tsv"
  [[ -d "$functions_dir" ]] || { log_warn "功能文档目录不存在：$functions_dir"; return 0; }
  [[ -d "$interfaces_dir" ]] || log_warn "接口文档目录不存在：$interfaces_dir（将导致接口索引为空）"

  local tmp_keys
  tmp_keys="$(mktemp)"

  shopt -s nullglob
  local function_docs=("$functions_dir"/*.md)
  shopt -u nullglob

  for fdoc in "${function_docs[@]}"; do
    local fkey
    fkey="$(basename "$fdoc" .md)"
    if ! validate_function_key "$fkey"; then
      log_warn "功能文档文件名非法，跳过：$fdoc"
      continue
    fi

    extract_interface_keys_from_function_doc "$fdoc" "$tmp_keys"
    while IFS= read -r ikey; do
      [[ -n "$ikey" ]] || continue
      if ! validate_interface_key "$ikey"; then
        log_warn "interface_key 非法（仅允许 [a-z0-9_-]+），跳过：fkey=$fkey ikey=$ikey"
        continue
      fi
      local idoc="$interfaces_dir/$ikey.md"
      if [[ ! -f "$idoc" ]]; then
        log_warn "接口文档不存在，跳过：fkey=$fkey ikey=$ikey expected=$idoc"
        continue
      fi
      printf "%s\t%s\n" "$fkey" "$ikey" >>"$out_tsv"
    done <"$tmp_keys"
  done

  rm -f "$tmp_keys"
}

main() {
  require_cmd python3
  parse_args "$@"

  local bf_json="$REPO_ROOT/omni-doc/on-demand/relations/branch-function.json"
  local fi_json="$REPO_ROOT/omni-doc/on-demand/relations/function-interface.json"
  local bi_json="$REPO_ROOT/omni-doc/on-demand/relations/branch-interface.json"
  local legacy_rf_json="$REPO_ROOT/omni-doc/on-demand/relations/requirement-function.json"
  local legacy_ri_json="$REPO_ROOT/omni-doc/on-demand/relations/requirement-interface.json"
  local bf_tsv
  local fi_tsv
  bf_tsv="$(mktemp)"
  fi_tsv="$(mktemp)"

  log_info "开始构建关系文件（全量重建）"
  log_info "REPO_ROOT=$REPO_ROOT"

  build_pairs_tsv "$REPO_ROOT" "$bf_tsv"
  build_function_interface_tsv "$REPO_ROOT" "$fi_tsv"

  local rf_count
  local fi_count
  rf_count="$(wc -l <"$bf_tsv" | tr -d ' ')"
  fi_count="$(wc -l <"$fi_tsv" | tr -d ' ')"
  log_info "收集到 (branch_name, function_key) 记录数：$rf_count"
  log_info "收集到 (function_key, interface_key) 记录数：$fi_count"

  if [[ "$DRY_RUN" == "true" ]]; then
    log_info "--dry-run：不落盘写入"
    log_info "目标文件：$bf_json"
    log_info "目标文件：$fi_json"
    log_info "目标文件：$bi_json"
    log_info "兼容文件：$legacy_rf_json"
    log_info "兼容文件：$legacy_ri_json"
    rm -f "$bf_tsv" "$fi_tsv"
    return 0
  fi

  write_relations_json_atomically "$bf_tsv" "$bf_json"
  write_relations_json_atomically "$fi_tsv" "$fi_json"
  write_branch_interface_json_atomically "$bf_tsv" "$fi_tsv" "$bi_json"
  # 兼容旧调用方：保留 requirement-* 文件（内容与 branch-* 一致）
  cp "$bf_json" "$legacy_rf_json"
  cp "$bi_json" "$legacy_ri_json"
  rm -f "$bf_tsv" "$fi_tsv"

  log_info "写入完成：$bf_json"
  log_info "写入完成：$fi_json"
  log_info "写入完成：$bi_json"
  log_info "兼容写入完成：$legacy_rf_json"
  log_info "兼容写入完成：$legacy_ri_json"
}

main "$@"


