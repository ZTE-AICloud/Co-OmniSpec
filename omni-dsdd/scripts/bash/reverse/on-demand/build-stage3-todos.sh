#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(CDPATH="" cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/../../common.sh"

log_info() { echo "[build-stage3-todos] INFO: $*" >&2; }
log_error() { echo "[build-stage3-todos] ERROR: $*" >&2; }
die() { log_error "$*"; exit 1; }

print_help() {
  cat <<'EOF'
用法:
  build-stage3-todos.sh --feature-dir <FEATURE_DIR> [--repo-root <REPO_ROOT>] [--dry-run]

参数:
  --feature-dir <path>  必填，特性目录（必须位于 changes/<short-name>）
  --repo-root <path>    可选，仓库根目录（未提供则从 feature-dir 推导）
  --dry-run             仅打印统计信息，不写入文件
  --help                显示帮助

输入:
  <FEATURE_DIR>/on-demand/stage2-impact-confirmed.json
  <FEATURE_DIR>/on-demand/stage2-interface-confirmed.json

输出:
  <FEATURE_DIR>/on-demand/stage3-function-todo.json
  <FEATURE_DIR>/on-demand/stage3-interface-todo.json
EOF
}

require_cmd() {
  local cmd="$1"
  command -v "$cmd" >/dev/null 2>&1 || die "缺少依赖命令: $cmd"
}

FEATURE_DIR=""
REPO_ROOT=""
DRY_RUN="false"

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --feature-dir)
        shift
        [[ $# -gt 0 ]] || die "--feature-dir 需要参数"
        FEATURE_DIR="$1"
        ;;
      --repo-root)
        shift
        [[ $# -gt 0 ]] || die "--repo-root 需要参数"
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
        die "未知参数: $1 (使用 --help 查看帮助)"
        ;;
    esac
    shift
  done

  [[ -n "$FEATURE_DIR" ]] || die "必须提供 --feature-dir"

  local repo_root_detected
  repo_root_detected="$(get_repo_root)"

  FEATURE_DIR="$(normalize_path "$FEATURE_DIR" "$repo_root_detected")"
  if [[ -n "$REPO_ROOT" ]]; then
    REPO_ROOT="$(normalize_path "$REPO_ROOT" "$repo_root_detected")"
  else
    REPO_ROOT="$repo_root_detected"
  fi

  [[ -d "$FEATURE_DIR" ]] || die "FEATURE_DIR 不存在: $FEATURE_DIR"
  [[ "$FEATURE_DIR" == "$REPO_ROOT"/changes/* ]] || die "FEATURE_DIR 必须位于 \$REPO_ROOT/changes 下: $FEATURE_DIR"
}

main() {
  require_cmd python3
  parse_args "$@"

  local on_demand_dir="$FEATURE_DIR/on-demand"
  local impact_json="$on_demand_dir/stage2-impact-confirmed.json"
  local interface_json="$on_demand_dir/stage2-interface-confirmed.json"
  local function_todo_json="$on_demand_dir/stage3-function-todo.json"
  local interface_todo_json="$on_demand_dir/stage3-interface-todo.json"

  [[ -f "$impact_json" ]] || die "缺少输入文件: $impact_json"
  [[ -f "$interface_json" ]] || die "缺少输入文件: $interface_json"

  mkdir -p "$on_demand_dir"

  log_info "FEATURE_DIR=$FEATURE_DIR"
  log_info "REPO_ROOT=$REPO_ROOT"
  log_info "生成双轨 Todo 清单..."

  python3 - "$impact_json" "$interface_json" "$function_todo_json" "$interface_todo_json" "$DRY_RUN" <<'PY'
import json
import os
import sys
from datetime import datetime, timezone

impact_json, interface_json, function_todo_json, interface_todo_json, dry_run = sys.argv[1:6]


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def extract_items(obj):
    if isinstance(obj, list):
        return obj
    if isinstance(obj, dict):
        for k in ("items", "functions", "interfaces", "confirmed", "data", "list"):
            v = obj.get(k)
            if isinstance(v, list):
                return v
    return []


def get_key(item, key_candidates):
    if isinstance(item, str):
        return item
    if not isinstance(item, dict):
        return None
    for k in key_candidates:
        v = item.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return None


def unique_todos(raw_items, key_candidates, kind):
    seen = set()
    todos = []
    for item in raw_items:
        key = get_key(item, key_candidates)
        if not key:
            continue
        if key in seen:
            continue
        seen.add(key)
        todos.append(
            {
                "id": key,
                "status": "pending",
                "reason": "",
                "kind": kind,
            }
        )
    return todos


impact_obj = load_json(impact_json)
interface_obj = load_json(interface_json)

function_items = extract_items(impact_obj)
interface_items = extract_items(interface_obj)

function_todos = unique_todos(
    function_items,
    ["function_key", "key", "id", "functionId", "function_name", "name"],
    "function",
)
interface_todos = unique_todos(
    interface_items,
    ["interface_key", "key", "id", "interfaceId", "interface_name", "name"],
    "interface",
)

now = datetime.now(timezone.utc).isoformat()

function_output = {
    "generated_at": now,
    "source_file": impact_json,
    "total": len(function_todos),
    "pending": len(function_todos),
    "done": 0,
    "failed": 0,
    "items": function_todos,
}

interface_output = {
    "generated_at": now,
    "source_file": interface_json,
    "total": len(interface_todos),
    "pending": len(interface_todos),
    "done": 0,
    "failed": 0,
    "items": interface_todos,
}

if dry_run.lower() == "true":
    print(json.dumps({"function_total": len(function_todos), "interface_total": len(interface_todos)}, ensure_ascii=False))
    sys.exit(0)

for path, payload in ((function_todo_json, function_output), (interface_todo_json, interface_output)):
    tmp_path = f"{path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp_path, path)

print(json.dumps({"function_todo_file": function_todo_json, "interface_todo_file": interface_todo_json}, ensure_ascii=False))
PY
}

main "$@"
