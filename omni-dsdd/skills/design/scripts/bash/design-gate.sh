#!/usr/bin/env bash
# design 分步/全量 Harness 门禁（skills/design 专用）
set -euo pipefail

SCRIPT_DIR="$(CDPATH="" cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=design-harness-common.sh
source "${SCRIPT_DIR}/design-harness-common.sh"

require_python3
exec python3 "$(design_harness_py)" gate "$@"
