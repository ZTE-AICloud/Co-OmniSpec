#!/usr/bin/env bash
# design Harness 公共路径（bash 封装层）
set -euo pipefail

_design_harness_script_dir() {
  CDPATH="" cd "$(dirname "${BASH_SOURCE[0]}")" && pwd
}

design_harness_py() {
  local script_dir
  script_dir="$(_design_harness_script_dir)"
  echo "${script_dir}/../python/design_harness.py"
}

require_python3() {
  if ! command -v python3 >/dev/null 2>&1; then
    echo "ERROR: python3 is required" >&2
    exit 1
  fi
}
