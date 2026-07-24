#!/usr/bin/env bash
# specify Harness 公共路径（bash 封装层）
set -euo pipefail

_specify_harness_script_dir() {
  CDPATH="" cd "$(dirname "${BASH_SOURCE[0]}")" && pwd
}

specify_harness_py() {
  local script_dir
  script_dir="$(_specify_harness_script_dir)"
  echo "${script_dir}/../python/specify_harness.py"
}

require_python3() {
  if ! command -v python3 >/dev/null 2>&1; then
    echo "ERROR: python3 is required" >&2
    exit 1
  fi
}
