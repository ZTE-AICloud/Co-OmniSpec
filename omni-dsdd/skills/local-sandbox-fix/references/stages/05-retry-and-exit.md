# 阶段 5：循环重测（gate `7-record-iteration`）

## 执行

```bash
bash "${CLAUDE_PLUGIN_ROOT}/skills/local-sandbox-fix/scripts/bash/local-sandbox-fix-gate.sh" \
  --harness-dir "${HARNESS_DIR}" \
  --step "7-record-iteration" \
  --record
```

## 行为

- `iteration += 1`
- 若超过 `max_iterations`（默认 3）→ exit 20
- 否则 `next_action=next_iteration`，回到主循环首步（`2-start-ci`）

## 断点续跑

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/local-sandbox-fix/scripts/python/local_sandbox_fix_harness.py" \
  resume --harness-dir "${HARNESS_DIR}"
```
