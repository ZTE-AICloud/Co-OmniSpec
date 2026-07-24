#!/usr/bin/env bash
# spec-impact-analyze 私域知识检索门禁（skills/spec-impact-analyze 专用）
# 强约束：私域知识源就绪时，knowledge-retrieval-agent 必须真派发并写入 payload 的
# knowledge_retrieval 字段；缺失 config 时就地自愈。防止"知识存在却跳过检索"。
set -euo pipefail

SCRIPT_DIR="$(CDPATH="" cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=spec-impact-harness-common.sh
source "${SCRIPT_DIR}/spec-impact-harness-common.sh"

require_python3
exec python3 "$(impact_gate_py)" gate "$@"
