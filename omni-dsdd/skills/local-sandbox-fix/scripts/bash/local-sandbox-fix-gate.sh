#!/usr/bin/env bash
# local-sandbox-fix 分步 Harness 门禁
set -euo pipefail

SCRIPT_DIR="$(CDPATH="" cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=local-sandbox-fix-common.sh
source "${SCRIPT_DIR}/local-sandbox-fix-common.sh"

require_python3
exec "$PYTHON3" "$(local_sandbox_fix_harness_py)" gate "$@"
