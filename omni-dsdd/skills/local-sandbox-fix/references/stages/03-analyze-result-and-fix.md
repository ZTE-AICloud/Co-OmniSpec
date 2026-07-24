# 阶段 3：解析结果并修码（gate `4-parse-result` + Agent fix + gate `5-fix-verify`）

## gate 4 — 解析 result.json

```bash
bash "${CLAUDE_PLUGIN_ROOT}/skills/local-sandbox-fix/scripts/bash/local-sandbox-fix-gate.sh" \
  --harness-dir "${HARNESS_DIR}" \
  --step "4-parse-result" \
  --record
```

解析 gate stdout JSON 的 `next_action`：

| next_action | Agent 行为 |
|-------------|------------|
| `finalize` | CI 已通过，流程结束 |
| `fix` | 继续下方修码步骤 |

## Agent 修码（仅 next_action=fix）

1. 读 `${HARNESS_DIR}/fix-context.json`
2. 遵循 [fix-guidelines.md](../fix-guidelines.md)

## gate 5 — 验证修码

```bash
bash "${CLAUDE_PLUGIN_ROOT}/skills/local-sandbox-fix/scripts/bash/local-sandbox-fix-gate.sh" \
  --harness-dir "${HARNESS_DIR}" \
  --step "5-fix-verify" \
  --record
```

成功时 `next_action=code-review`。
