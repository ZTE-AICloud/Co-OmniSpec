# 阶段 2：触发 CI 并等待（gate `2-start-ci` + `3-wait-ci`）

## gate 2 — 启动 CI

**Agent 不手工 nohup**。调用：

```bash
bash "${CLAUDE_PLUGIN_ROOT}/skills/local-sandbox-fix/scripts/bash/local-sandbox-fix-gate.sh" \
  --harness-dir "${HARNESS_DIR}" \
  --step "2-start-ci" \
  --record
```

Harness 内执行：`run_local_ci.py "${CLAUDE_WORKING_DIR}"`（后台）。

## gate 3 — 阻塞等待（禁止 Agent 替代）

```bash
bash "${CLAUDE_PLUGIN_ROOT}/skills/local-sandbox-fix/scripts/bash/local-sandbox-fix-gate.sh" \
  --harness-dir "${HARNESS_DIR}" \
  --step "3-wait-ci" \
  --record
```

- 最长阻塞 90min
- run.log 120s 无更新 → exit 10
- **gate 2～3 之间禁止修改代码**

## Checkpoint

```
✅ Checkpoint local-sandbox-fix: step=3-wait-ci, gate_exit=0, next_action=continue
```
