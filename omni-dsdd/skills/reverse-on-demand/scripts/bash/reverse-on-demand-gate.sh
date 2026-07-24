#!/usr/bin/env bash
# reverse-on-demand 阶段2 Harness 门禁（全仓检索 / 调用链深度 / 配置解析 / 多语言覆盖）
set -euo pipefail

SCRIPT_DIR="$(CDPATH="" cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HARNESS_PY="${SCRIPT_DIR}/../python/reverse_on_demand_harness.py"

if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 is required" >&2
  exit 1
fi

if [[ $# -lt 1 ]]; then
  echo "用法: $0 --working-dir <WORKING_DIR> --feature-dir <FEATURE_DIR> [--repo-root <REPO_ROOT>] [--step <stage2|all>] [--record]" >&2
  exit 1
fi

exec python3 "$HARNESS_PY" gate "$@"
