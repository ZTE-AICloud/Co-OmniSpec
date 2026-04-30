#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(CDPATH="" cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/../../common.sh"

log_info() { echo "[validate-stage3-gate] INFO: $*" >&2; }
log_error() { echo "[validate-stage3-gate] ERROR: $*" >&2; }
die() { log_error "$*"; exit 1; }

print_help() {
  cat <<'EOF'
用法:
  validate-stage3-gate.sh --feature-dir <FEATURE_DIR> [--repo-root <REPO_ROOT>] [--dry-run]

参数:
  --feature-dir <path>  必填，特性目录（必须位于 changes/<short-name>）
  --repo-root <path>    可选，仓库根目录（未提供则自动推导）
  --dry-run             仅校验并输出结果，不回写 stage3-summary.json
  --help                显示帮助

读取文件:
  <FEATURE_DIR>/on-demand/stage3-function-todo.json
  <FEATURE_DIR>/on-demand/stage3-interface-todo.json
  <FEATURE_DIR>/on-demand/stage3-interface-validation-summary.json (可选)
  <FEATURE_DIR>/on-demand/stage3-summary.json (可选，存在则增量更新)

输出:
  标准输出返回 gate 校验 JSON
  默认会回写/生成 <FEATURE_DIR>/on-demand/stage3-summary.json
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
  local function_todo_json="$on_demand_dir/stage3-function-todo.json"
  local interface_todo_json="$on_demand_dir/stage3-interface-todo.json"
  local interface_validation_json="$on_demand_dir/stage3-interface-validation-summary.json"
  local summary_json="$on_demand_dir/stage3-summary.json"

  [[ -f "$function_todo_json" ]] || die "缺少输入文件: $function_todo_json"
  [[ -f "$interface_todo_json" ]] || die "缺少输入文件: $interface_todo_json"

  log_info "FEATURE_DIR=$FEATURE_DIR"
  log_info "REPO_ROOT=$REPO_ROOT"
  log_info "校验步骤6C关口..."

  python3 - "$function_todo_json" "$interface_todo_json" "$interface_validation_json" "$summary_json" "$DRY_RUN" <<'PY'
import json
import os
import sys
from datetime import datetime, timezone

function_todo_json, interface_todo_json, interface_validation_json, summary_json, dry_run = sys.argv[1:6]


def load_json_or_none(path):
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def todo_stats(todo_obj):
    items = []
    if isinstance(todo_obj, dict):
        items = todo_obj.get("items", [])
    elif isinstance(todo_obj, list):
        items = todo_obj

    total = len(items)
    done = 0
    failed = 0
    pending = 0
    failed_items = []
    pending_items = []
    for item in items:
        if not isinstance(item, dict):
            continue
        sid = item.get("id", "")
        status = str(item.get("status", "pending")).lower()
        reason = item.get("reason", "")
        if status == "done":
            done += 1
        elif status == "failed":
            failed += 1
            failed_items.append({"id": sid, "reason": reason})
        else:
            pending += 1
            pending_items.append({"id": sid, "reason": reason})

    return {
        "total": total,
        "done": done,
        "failed": failed,
        "pending": pending,
        "failed_items": failed_items,
        "pending_items": pending_items,
    }


function_todo = load_json_or_none(function_todo_json)
interface_todo = load_json_or_none(interface_todo_json)
interface_validation = load_json_or_none(interface_validation_json) or {}
existing_summary = load_json_or_none(summary_json) or {}

fs = todo_stats(function_todo)
is_ = todo_stats(interface_todo)

validated_interfaces = interface_validation.get("validated_interfaces", is_["done"])
failed_interfaces_validation = interface_validation.get("failed_interfaces", is_["failed"])

gate_passed = (
    fs["failed"] == 0
    and fs["pending"] == 0
    and is_["failed"] == 0
    and is_["pending"] == 0
    and failed_interfaces_validation == 0
)

result = dict(existing_summary)
result.update(
    {
        "validated_at": datetime.now(timezone.utc).isoformat(),
        "function_track": {
            "total_functions": fs["total"],
            "done_functions": fs["done"],
            "failed_functions": fs["failed"],
            "pending_functions": fs["pending"],
        },
        "interface_track": {
            "total_interfaces": is_["total"],
            "validated_interfaces": validated_interfaces,
            "failed_interfaces": failed_interfaces_validation,
            "pending_interfaces": is_["pending"],
        },
        "gate_passed": gate_passed,
        "failed_items": {
            "function_failed": fs["failed_items"],
            "function_pending": fs["pending_items"],
            "interface_failed": is_["failed_items"],
            "interface_pending": is_["pending_items"],
            "interface_validation_failed": interface_validation.get("failed_items", []),
        },
    }
)

if dry_run.lower() != "true":
    tmp = summary_json + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, summary_json)

print(json.dumps(result, ensure_ascii=False))
sys.exit(0 if gate_passed else 2)
PY
}

main "$@"
