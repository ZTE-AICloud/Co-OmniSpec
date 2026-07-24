# 阶段 4：code-review（Agent + gate `6-code-review-gate`）

## Agent — 执行 code-review

同步调用：

```
Skill("code-review")
```

环境变量（与 code-review 对齐）：

```bash
test -n "${CLAUDE_PLUGIN_ROOT:-}" && test -d "${CLAUDE_PLUGIN_ROOT}"
test -n "${CLAUDE_WORKING_DIR:-}" && test -d "${CLAUDE_WORKING_DIR}"
```

可选继承 FEATURE_DIR：

```bash
eval "$(bash "${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/bash/design-resolve-context.sh" \
  --plugin-root "${CLAUDE_PLUGIN_ROOT}" \
  --working-dir "${CLAUDE_WORKING_DIR}" \
  ${FEATURE_DIR:+--feature-dir "$FEATURE_DIR"} \
  --export)" 2>/dev/null || true
```

## gate 6 — 验收报告

```bash
bash "${CLAUDE_PLUGIN_ROOT}/skills/local-sandbox-fix/scripts/bash/local-sandbox-fix-gate.sh" \
  --harness-dir "${HARNESS_DIR}" \
  --step "6-code-review-gate" \
  --record
```

验收：报告文件存在且 mtime > fix_started_at；VERDICT=BLOCK 则失败。
