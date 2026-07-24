#!/usr/bin/env bash
# specify 分步/全量 Harness 门禁（skills/specify 专用）
set -euo pipefail

SCRIPT_DIR="$(CDPATH="" cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=specify-harness-common.sh
source "${SCRIPT_DIR}/specify-harness-common.sh"

require_python3
exec python3 "$(specify_harness_py)" gate "$@"
