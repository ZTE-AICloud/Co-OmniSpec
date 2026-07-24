#!/usr/bin/env bash
# 探测 SDD 路由状态；特性目录在 CLAUDE_WORKING_DIR 下解析，插件脚本在 CLAUDE_PLUGIN_ROOT 下定位。

set -euo pipefail

readonly USAGE_MSG="Usage: $0 --plugin-root <path> --working-dir <path>"

PLUGIN_ROOT=""
WORKING_DIR=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --plugin-root)
      [[ $# -gt 0 ]] || { echo "Error: --plugin-root requires a value" >&2; exit 2; }
      PLUGIN_ROOT="$2"
      shift 2
      ;;
    --working-dir)
      [[ $# -gt 0 ]] || { echo "Error: --working-dir requires a value" >&2; exit 2; }
      WORKING_DIR="$2"
      shift 2
      ;;
    -h|--help)
      echo "$USAGE_MSG"
      echo "  Or set CLAUDE_PLUGIN_ROOT and CLAUDE_WORKING_DIR."
      exit 0
      ;;
    *)
      echo "ERROR: Unknown option: $1" >&2
      echo "$USAGE_MSG" >&2
      exit 2
      ;;
  esac
done

if [[ -z "$PLUGIN_ROOT" && -n "${CLAUDE_PLUGIN_ROOT:-}" ]]; then
  PLUGIN_ROOT="$CLAUDE_PLUGIN_ROOT"
fi
if [[ -z "$WORKING_DIR" && -n "${CLAUDE_WORKING_DIR:-}" ]]; then
  WORKING_DIR="$CLAUDE_WORKING_DIR"
fi

if [[ -z "$PLUGIN_ROOT" || -z "$WORKING_DIR" ]]; then
  echo "ERROR: --plugin-root and --working-dir are required (or set CLAUDE_* env)" >&2
  echo "$USAGE_MSG" >&2
  exit 2
fi

if [[ ! -d "$PLUGIN_ROOT" ]]; then
  echo "ERROR: plugin root is not a directory: $PLUGIN_ROOT" >&2
  exit 2
fi
if [[ ! -d "$WORKING_DIR" ]]; then
  echo "ERROR: working dir is not a directory: $WORKING_DIR" >&2
  exit 2
fi

STATE_PY="$PLUGIN_ROOT/scripts/python/omnispec_state.py"

if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 is required" >&2
  exit 1
fi

if [[ ! -f "$STATE_PY" ]]; then
  echo "ERROR: missing omnispec_state.py: $STATE_PY" >&2
  exit 1
fi

python3 - "$WORKING_DIR" "$STATE_PY" <<'PY'
import json
import sys
from pathlib import Path

working_dir = Path(sys.argv[1]).resolve()
state_py = Path(sys.argv[2])

import importlib.util

spec = importlib.util.spec_from_file_location("omnispec_state", state_py)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

state_rel_path = Path(".runs/.omnispec-state.json")
# routing 仅探测状态，不通过 check-prerequisites 回退（避免将 working_dir 误当作 plugin 根）
feature_dir = mod.resolve_feature_dir(working_dir, use_prerequisites=False)

if feature_dir is None:
    print("状态文件.omnispec-state.json不存在")
    sys.exit(0)

state_abs_path = feature_dir / state_rel_path
if not state_abs_path.exists():
    print("状态文件.omnispec-state.json不存在")
    sys.exit(0)

try:
    state_data = json.loads(state_abs_path.read_text(encoding="utf-8"))
except json.JSONDecodeError:
    state_data = state_abs_path.read_text(encoding="utf-8")

output = {
    "state_file_base_dir": str(feature_dir),
    "state_file_relative_path": str(state_rel_path),
    "state_file_content": state_data,
    "working_dir": str(working_dir),
    "resolved_via": "omnispec_state.resolve_feature_dir",
}
print(json.dumps(output, ensure_ascii=False, indent=2))
PY
