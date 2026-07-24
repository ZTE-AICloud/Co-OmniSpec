#!/usr/bin/env bash
# specify 全量产物门禁（skills/specify 专用）
set -euo pipefail

SCRIPT_DIR="$(CDPATH="" cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=specify-harness-common.sh
source "${SCRIPT_DIR}/specify-harness-common.sh"

FEATURE_DIR=""
MIN_BYTES=64
EXTRA=()

show_help() {
  cat <<'EOF'
specify 阶段产物完整性校验（全量门禁）

用法:
  skills/specify/scripts/bash/verify-specify-artifacts.sh --feature-dir <path> [--min-bytes N]

等价于:
  python3 skills/specify/scripts/python/specify_harness.py gate --feature-dir <path> --step all

退出码:
  0  全部必需产物通过结构门禁
  1  门禁失败
  2  参数错误
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --feature-dir)
      FEATURE_DIR="$2"
      shift 2
      ;;
    --min-bytes)
      MIN_BYTES="$2"
      shift 2
      ;;
    -h|--help)
      show_help
      exit 0
      ;;
    *)
      EXTRA+=("$1")
      shift
      ;;
  esac
done

if [[ -z "$FEATURE_DIR" ]]; then
  echo "错误: 必须提供 --feature-dir" >&2
  show_help
  exit 2
fi

require_python3
python3 "$(specify_harness_py)" gate --feature-dir "$FEATURE_DIR" --step all --min-bytes "$MIN_BYTES" "${EXTRA[@]}"
exit $?
