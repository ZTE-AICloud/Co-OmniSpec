#!/usr/bin/env bash
# 从 spec-template.md 渲染 spec.md 骨架（skills/specify 专用）
set -euo pipefail

SCRIPT_DIR="$(CDPATH="" cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=specify-harness-common.sh
source "${SCRIPT_DIR}/specify-harness-common.sh"

require_python3
exec python3 "$(specify_harness_py)" render-spec "$@"
