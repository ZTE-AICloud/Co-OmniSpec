#!/usr/bin/env bash
# 已迁移至 skills/specify/scripts/ — 本文件为兼容转发
set -euo pipefail
SCRIPT_DIR="$(CDPATH="" cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(CDPATH="" cd "$SCRIPT_DIR/../.." && pwd)"
exec "$REPO_ROOT/skills/specify/scripts/bash/specify-render-context.sh" "$@"
