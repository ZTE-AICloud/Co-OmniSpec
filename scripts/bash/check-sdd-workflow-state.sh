#!/usr/bin/env bash
# 脚本功能：分析.omnispec-state.json文件状态，生成status.json
# 依赖工具：python3（标准库 json）
# 参数说明：
#   RDC_ID - 必须参数，用于匹配.state文件路径的RDC标识
# 输出文件：changes/status.json

set -e

# 检查参数数量
if [ $# -ne 1 ]; then
    echo "Usage: $0 <RDC_ID>"
    echo "示例：$0 123456"
    exit 1
fi

RDC_ID="$1"

if ! command -v python3 >/dev/null 2>&1; then
    echo "ERROR: 未找到 python3，本脚本使用其标准库解析 JSON" >&2
    exit 1
fi

# 脚本目录计算
SCRIPT_DIR="$(CDPATH="" cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CHANGE_DIR="${SCRIPT_DIR}/../../../changes"

# 查找包含RDC_ID的子目录中的state文件
state_path=$(find "${CHANGE_DIR}/.runs" -type f -name ".omnispec-state.json" -path "*${RDC_ID}*/.omnispec-state.json" | head -1)

if [ -z "$state_path" ]; then
    exit 1
fi

output_path="$CHANGE_DIR/status.json"

python3 - "$state_path" "$output_path" <<'PY'
import json
import re
import sys

state_path, output_path = sys.argv[1], sys.argv[2]
phase_key_re = re.compile(r"^phase[0-9_]+_status$")

with open(state_path, encoding="utf-8") as f:
    data = json.load(f)

current_stage = data.get("current_stage") or ""


def compute_current_state() -> str:
    if current_stage == "implement":
        vr = data.get("validation_results")
        impl = (vr or {}).get("implement") if isinstance(vr, dict) else None
        if not isinstance(impl, dict):
            impl = {}
        vals = [v for k, v in impl.items() if phase_key_re.match(str(k))]
        if not vals:
            return "Proceeding"
        if any(v == "failed" for v in vals):
            return "Failed"
        if any(v == "in_progress" for v in vals):
            return "Proceeding"
        if all(v == "completed" for v in vals):
            return "Success"
        return "Proceeding"

    completed = data.get("completed_stages")
    if not isinstance(completed, list) or not completed:
        return "Proceeding"
    last = completed[-1]
    vr = data.get("validation_results")
    if not isinstance(vr, dict):
        vr = {}
    node = vr.get(last)
    if not isinstance(node, dict):
        node = {}
    if node.get("status") == "failed":
        return "Failed"
    return "Proceeding"


current_state = compute_current_state()
out = {"current_state": current_state, "current_stage": current_stage}

with open(output_path, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
    f.write("\n")
PY

# 同时返回 output_path 文件内容
cat "$output_path"
