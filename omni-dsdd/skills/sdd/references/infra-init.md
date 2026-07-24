# SDD 环境初始化

> 对应 SKILL.md 步骤 2

执行初始化（显式传入工作区，**不要**依赖脚本内 `pwd`，**不要**仅 `export` 后无参调用）。

> **`--knowledge-dir` 预提取**：步骤 2 在步骤 3 之前执行，需先从 `$ARGUMENTS` 提取 `--knowledge-dir`（支持 `--key=value`）记为 `$PRESET_KNOWLEDGE_DIR`；**未出现则为空，init 脚本缺省解析为 `${CLAUDE_WORKING_DIR}/omni-doc`**。提取**仅解析不消费**，`$ARGUMENTS` 原样保留给后续步骤。

```bash
# 从 $ARGUMENTS 提取 --knowledge-dir（未出现则空；不修改 $ARGUMENTS）
PRESET_KNOWLEDGE_DIR="$(printf '%s\n' "$ARGUMENTS" | grep -oE -- '--knowledge-dir[= ]+[^ ]+' | head -1 | sed -E 's/^--knowledge-dir[= ]+//')"
bash "${CLAUDE_PLUGIN_ROOT}/scripts/bash/init_omni_infra.sh" \
  --plugin-root "${CLAUDE_PLUGIN_ROOT}" \
  --working-dir "${CLAUDE_WORKING_DIR}" \
  ${PRESET_KNOWLEDGE_DIR:+--knowledge-dir "$PRESET_KNOWLEDGE_DIR"}
```

说明：`init_omni_infra.sh` 将 `${CLAUDE_PLUGIN_ROOT}/omni-infra` 复制为 `${CLAUDE_WORKING_DIR}/.omni-infra`。
- 透传 `--knowledge-dir` 时，脚本向该目录拷贝 `knowledge.config.yaml`（缺失才拷，不覆盖），并把生效的绝对路径写入 `${CLAUDE_WORKING_DIR}/.omni-infra/knowledge.path` 标记文件（供 constitution 读取）；未传则用默认 `${CLAUDE_WORKING_DIR}/omni-doc`。
- 执行过程中会**自动**（幂等）向工作区根目录 `${CLAUDE_WORKING_DIR}/.gitignore` 追加 SDD 运行时产物目录：`changes/` 与知识库目录（默认 `omni-doc/`；若 `--knowledge-dir` 指定其它目录则一并追加，已存在则跳过），避免过程文件被误提交。
- `0`：`.omni-infra` 已存在 → 继续步骤 3
- `1`：工作区**原本无** `.omni-infra`、脚本已首次创建 → **必须** `Task(subagent_type="omni-dsdd:constitution")`，并**透传当前 `$ARGUMENTS`**（含项目/需求/宪章意图）。完整执行并等待 handoff 后再继续步骤 3：

```text
Task(
  subagent_type="omni-dsdd:constitution",
  description="项目章程创建/更新",
  prompt="按 agents/constitution.md 执行。用户输入=<<$ARGUMENTS 原文>>。已注入：CLAUDE_PLUGIN_ROOT=<绝对路径> CLAUDE_PROJECT_DIR=<CLAUDE_WORKING_DIR 绝对路径>。仅返回 KEY=value handoff（status=ok|skipped|failed）。"
)
```

- handoff `status=failed` → 终止；`ok` 或 `skipped` → 继续步骤 3

- `2`：失败 → 终止流程  

## 完成判据

- `init_omni_infra.sh` 退出码为 `0` 或 `1`（`2` 则终止）
- 退出码为 `1` 时，已调用 `Skill(constitution)` 并等待其返回
