#!/usr/bin/env bash
# 从 requirements-template.md 渲染检查清单（skills/specify 专用）
set -euo pipefail

SCRIPT_DIR="$(CDPATH="" cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=specify-harness-common.sh
source "${SCRIPT_DIR}/specify-harness-common.sh"

require_python3
exec python3 "$(specify_harness_py)" render-checklist "$@"
