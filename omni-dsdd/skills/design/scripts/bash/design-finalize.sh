#!/usr/bin/env bash
# design 完成后同步 omnispec-state（skills/design 专用）
set -euo pipefail

SCRIPT_DIR="$(CDPATH="" cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=design-harness-common.sh
source "${SCRIPT_DIR}/design-harness-common.sh"

require_python3
exec python3 "$(design_harness_py)" finalize "$@"
