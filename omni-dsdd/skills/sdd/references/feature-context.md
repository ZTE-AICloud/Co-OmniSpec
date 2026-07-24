# 特性上下文合并解析（传参 + 全局变量，不生效）

> 对应 SKILL.md 步骤 3

在调用 `routing` 前，**一次完成**传参与全局变量的合并解析：

| 变量 | 有 `$ARGUMENTS` 传参时 | 无传参时 |
|------|------------------------|----------|
| `FEATURE_DIR` | 以 `--feature-dir` 为准 | 读 `OMNISPEC_FEATURE_DIR` → `FEATURE_DIR`（export） |
| `BRANCH_NAME` | 以 `--branch-name` 为准 | 读 `BRANCH_NAME`（export） |
| 仅有一个 | 传参优先；另一个由脚本推导补全 | export 优先；另一个由脚本推导补全 |
| 二者皆无 | — | `FEATURE_CONTEXT_PRESET=false`，后续 allocate |
| `KNOWLEDGE_DIR` | 以 `--knowledge-dir` 为准 | 读 `KNOWLEDGE_DIR`（export）；皆无则默认 `${CLAUDE_WORKING_DIR}/omni-doc` |

**执行步骤**：

1. 从 `$ARGUMENTS` 提取 `--feature-dir` / `--branch-name`（支持 `--key=value`），分别记为 `$PRESET_FEATURE_DIR`、`$PRESET_BRANCH_NAME`；**未出现则保持为空，禁止填占位符或臆造值**
2. 从 `$ARGUMENTS` 提取 `--knowledge-dir`（支持 `--key=value`），记为 `$PRESET_KNOWLEDGE_DIR`；未出现则为空，由脚本读 export；皆无则默认 `${CLAUDE_WORKING_DIR}/omni-doc`
3. 调用 `resolve-feature-context.sh`：**仅当提取到非空传参时才追加对应 CLI 选项**；无传参时由脚本读 shell export

```bash
# 合并（有传参→传参；无传参→export；皆无→preset=false）
eval "$(bash "${CLAUDE_PLUGIN_ROOT}/scripts/bash/resolve-feature-context.sh" \
  --working-dir "${CLAUDE_WORKING_DIR}" \
  ${PRESET_FEATURE_DIR:+--feature-dir "$PRESET_FEATURE_DIR"} \
  ${PRESET_BRANCH_NAME:+--branch-name "$PRESET_BRANCH_NAME"} \
  ${PRESET_KNOWLEDGE_DIR:+--knowledge-dir "$PRESET_KNOWLEDGE_DIR"} \
  --export)"
```

- `eval --export` 将解析结果**正式赋值**到当前会话：`FEATURE_DIR`、`OMNISPEC_FEATURE_DIR`、`BRANCH_NAME`、`SPEC_FILE`、`FEATURE_CONTEXT_PRESET`、`KNOWLEDGE_DIR`；**不等于**落盘 `env.sh`
- **禁止**在本步骤 `mkdir`、`git checkout` 或 Write `.runs/env.sh`
- 打印日志：`sdd 特性预解析 FEATURE_DIR=${FEATURE_DIR:-}, BRANCH_NAME=${BRANCH_NAME:-}, KNOWLEDGE_DIR=${KNOWLEDGE_DIR:-}, FEATURE_CONTEXT_PRESET=${FEATURE_CONTEXT_PRESET:-}, PRESET_CLI=<dir:${PRESET_FEATURE_DIR:-NONE} branch:${PRESET_BRANCH_NAME:-NONE} kb:${PRESET_KNOWLEDGE_DIR:-NONE}>`

**向下游传递（`FEATURE_CONTEXT_PRESET=true` 时必做）**：

| 来源 | 条件 | 行为 |
|------|------|------|
| 用户传参 | `$PRESET_*` 非空 | 以传参解析结果赋值并传递 |
| **仅全局变量** | `$PRESET_*` 为空，export 解析成功 | **同样**赋值 `FEATURE_DIR`/`BRANCH_NAME` 并传递给 `routing` → workflow → `specify`；`source=env`，**不得**因无 CLI 而改走 allocate |
| 皆无 | export 亦空 | `FEATURE_CONTEXT_PRESET=false`，后续 allocate |

- 步骤 4 调用 `routing` 时：**不必**在 `$ARGUMENTS` 中追加 `--feature-dir`/`--branch-name`；下游通过会话变量 + 各自合并解析读取已赋值的 `FEATURE_DIR`/`BRANCH_NAME`
- 磁盘/Git 最终生效点仍为 `specify` 步骤 2 `create-branch`；步骤 3 赋值仅供全链路会话传递

## 完成判据

- `resolve-feature-context.sh --export` 已执行，会话变量已 eval 赋值
- **未** `mkdir` / `git checkout` / Write `.runs/env.sh`
