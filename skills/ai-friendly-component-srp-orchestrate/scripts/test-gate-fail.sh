#!/usr/bin/env bash
set -euo pipefail

# 测试门禁失败场景

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== 测试门禁失败场景 ==="

# 创建低分模块分析结果
cat > "$SKILL_DIR/state/step02-analyze-modules/bad-module.json" <<'EOF'
{
  "module_path": "pdmcli/bad",
  "metric_result": {
    "total_score": 0.4,
    "confidence": 0.5,
    "score_detail": {
      "directory_single_score": 0.3,
      "module_cohesion_score": 0.4,
      "file_single_score": 0.5
    }
  },
  "violation_info": {
    "total_count": 10
  }
}
EOF

# 重新聚合
python3 "$SCRIPT_DIR/aggregate.py" \
  --input-dir "$SKILL_DIR/state/step02-analyze-modules" \
  --output "$SKILL_DIR/output/summary-fail.json" \
  --project-path "/test/project"

# 测试门禁（应该失败）
python3 "$SCRIPT_DIR/gate-check.py" \
  --input "$SKILL_DIR/output/summary-fail.json" \
  --config "$SKILL_DIR/.gate-config.json" \
  --output "$SKILL_DIR/output/gate-result-fail.json" || true

if [[ -f "$SKILL_DIR/output/gate-result-fail.json" ]]; then
    if grep -q '"gate_passed": false' "$SKILL_DIR/output/gate-result-fail.json"; then
        echo "[ok] 门禁正确识别失败场景"
    else
        echo "[error] 门禁应该失败但通过了"
        exit 1
    fi
else
    echo "[error] gate-result-fail.json 未生成"
    exit 1
fi

echo "[ok] 门禁失败场景测试通过"
