# routing 返回后的完成性校验（强制）

> 对应 SKILL.md 步骤 5

`routing` 在 `workflow-orchestrator` skill 返回后应已执行 `workflow-check-incomplete.sh` 完成性校验；若未完成则**同轮**补跑 orchestrator。
`sdd` 在输出任何「SDD 执行完成」摘要前**必须**再次确认：

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/bash/workflow-gate.sh" \
  --feature-dir "$FEATURE_DIR" --check workflow-complete --record
```

- gate 未通过 → **禁止**输出完成摘要；提示 workflow 仍在进行（implement/review/local-sandbox-fix 未完成）
- gate 通过 → 允许输出简洁完成摘要（须含 implement、review 与 local-sandbox-fix）

## 完成判据

- `workflow-gate.sh --check workflow-complete` 已执行
- gate 通过时方可输出完成摘要；未通过则阻断，不报完成
