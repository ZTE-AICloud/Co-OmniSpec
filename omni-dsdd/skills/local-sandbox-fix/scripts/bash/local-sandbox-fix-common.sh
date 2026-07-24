#!/usr/bin/env bash
# local-sandbox-fix Harness 公共路径（bash 封装层）
set -euo pipefail

_local_sandbox_fix_harness_script_dir() {
  CDPATH="" cd "$(dirname "${BASH_SOURCE[0]}")" && pwd
}

local_sandbox_fix_harness_py() {
  local script_dir
  script_dir="$(_local_sandbox_fix_harness_script_dir)"
  echo "${script_dir}/../python/local_sandbox_fix_harness.py"
}

require_python3() {
  if command -v python3.8 >/dev/null 2>&1; then
    PYTHON3=python3.8
  elif command -v python3 >/dev/null 2>&1; then
    PYTHON3=python3
  else
    echo "ERROR: python3 is required" >&2
    exit 1
  fi
}
