#!/usr/bin/env bash
# 阶段2波及检索全量 Harness 校验（= gate --step all --record），含多语言覆盖校验
set -euo pipefail

SCRIPT_DIR="$(CDPATH="" cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ $# -lt 1 ]]; then
  echo "用法: $0 --working-dir <WORKING_DIR> --feature-dir <FEATURE_DIR> [--repo-root <REPO_ROOT>]" >&2
  exit 1
fi

exec "${SCRIPT_DIR}/reverse-on-demand-gate.sh" "$@" --step all --record
