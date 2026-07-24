#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(CDPATH="" cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(CDPATH="" cd "$SCRIPT_DIR/../../../.." && pwd)"

exec "$REPO_ROOT/skills/reverse-on-demand/scripts/reverse-on-demand-gate.sh" "$@"
