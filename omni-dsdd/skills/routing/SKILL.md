---
name: routing
argument-hint: 功能描述（支持 @文件路径 引用） --workflow <express|standard|deep|expert> --e2e [--feature-dir <dir>] [--branch-name <name>]
description: 智能路由编排器. 分析功能描述复杂度, 将 flow_mode（express/standard/deep/expert）映射到对应 YAML 工作流定义并启动 workflow-orchestrator skill 执行。触发词: /routing, 智能编排, 路由模式.
user-invokable: false
allowed-tools: Agent, AskUserQuestion, Bash, Read
---

# routing

## 执行约定

### workflow 模式、flow_mode 与编排方式（统一约定）

- **`--workflow`模式**: `express`、`standard`、`deep`、`expert` 是写入状态或路由逻辑`flow_mode`枚举值，语义上对应 **四套 YAML 工作流定义**，**不是** skill 名称，也**不得**当作 skill 去调用。

| flow_mode | YAML 定义文件 | 编排方式 |
| --------- | ------------- | -------- |
| `express` | `workflows/express.yaml` | `Skill("workflow-orchestrator")`，注入 `FLOW_MODE=express` |
| `standard` | `workflows/standard.yaml` | `Skill("workflow-orchestrator")`，注入 `FLOW_MODE=standard` |
| `deep` | `workflows/deep.yaml` | `Skill("workflow-orchestrator")`，注入 `FLOW_MODE=deep` |
| `expert` | `workflows/expert.yaml` | `Skill("workflow-orchestrator")`，注入 `FLOW_MODE=expert` |

- **`routing` 本身是 skill**：负责参数预处理、状态机与选择/恢复 `flow_mode`；
- **`workflow-orchestrator` skill** 读取 YAML 并按 `stage.type` 派发各阶段（`skill` 直接触发 / `agent` 经 Task 隔离）。
- **`complexity-analyzer` 是 agent**：仅在未强制 `--workflow` 时产出推荐 `flow_mode` 字符串，供本 skill 读取后选择对应 YAML 文件并启动 `workflow-orchestrator` skill。
- `expert` 只能由用户显式 `--workflow expert` 或既有 expert 状态选择；自动复杂度判定与非 forced pending 状态不得新增/推荐 expert。

### 禁止行为

1. **严格禁止**在 routing 阶段创建分支/特性目录/工作目录/`.omnispec-state.json` 文件
2. **严格禁止**跳过 `create-branch`（specify 内部强制调用）
3. **严格禁止**在 `create-branch` 执行前落盘关键产物（`spec.md`、`design.md`、`tasks.md`、状态文件）
4. **严格禁止**因无 CLI 跳过特性上下文传递或改走 allocate
5. **严格禁止**假设分支已创建或将临时探测值向下游传播
6. **严格禁止**workflow 层自行 mkdir 或 Write `.runs/env.sh`
7. **严格禁止**在退出码 `10`/`11` 且未补跑完成时宣称 SDD 完成

## 用户输入

```text
$ARGUMENTS
```

## 环境初始化

本技能的路径解析与状态探测依赖以下变量（与 SDD 全链路一致）：

| 变量 | 含义 | 用途 |
|------|------|------|
| `CLAUDE_PLUGIN_ROOT` | Omni 插件安装根 | `omnispec_state.py`、`check-prerequisites` 等 |
| `CLAUDE_WORKING_DIR` | 用户当前工作区（可为 Git 子目录） | `changes/`、`.omni-infra/`、`.active-feature` |
| `FEATURE_DIR` | 当前特性目录（可选） | 已由 workflow 创建时优先解析状态 |

### Step 0.1 检查变量

```bash
test -n "${CLAUDE_PLUGIN_ROOT:-}" && test -d "${CLAUDE_PLUGIN_ROOT}"
test -n "${CLAUDE_WORKING_DIR:-}" && test -d "${CLAUDE_WORKING_DIR}"
```

任一项失败时补全：`CLAUDE_WORKING_DIR` 缺失则 `export CLAUDE_WORKING_DIR="$(pwd)"`（**不用** `git rev-parse --show-toplevel` 抬到仓库根）。

### Step 0.2 状态探测（唯一允许的脚本调用）

判断当前操作系统（windows / linux）。在 **Git Bash 或等价 shell** 下执行（须显式传插件根与工作区，禁止用脚本 `__file__` 推断仓库根）：

```bash
bash "${CLAUDE_PLUGIN_ROOT}/skills/routing/scripts/check-routing-state.sh" \
  --plugin-root "${CLAUDE_PLUGIN_ROOT}" \
  --working-dir "${CLAUDE_WORKING_DIR}"
```

- 脚本在 **`CLAUDE_WORKING_DIR`** 下解析 `changes/.active-feature`、`changes/*/.runs/.omnispec-state.json` 及环境变量 `FEATURE_DIR`
- **不在** routing 主流程中直接调用 `check-prerequisites.*`

路径约定：

- 特性目录 = `${FEATURE_DIR}` 或 `${CLAUDE_WORKING_DIR}/changes/<branch>`；
- 状态文件 = `${FEATURE_DIR}/.runs/.omnispec-state.json`；
- 脚本返回的 `state_file_base_dir` 即已解析的 **FEATURE_DIR** 绝对路径。**参见「执行约定 > 禁止行为」**

## 参数预处理

在任何状态检测之前，先解析 `用户输入` 中的可选参数和 @ 文件引用：

- `--workflow <express|standard|deep|expert>`
- `--workflow=<express|standard|deep|expert>`
- `--e2e`：启用E2E测试设计（默认关闭）
- `--feature-dir <dir>` / `--feature-dir=<dir>`：用户指定特性目录
- `--branch-name <name>` / `--branch-name=<name>`：用户指定 Git 分支名
- `@路径/文件名`：文件引用

处理规则：

1. **展开 @ 文件引用**: 如果 `用户输入` 包含 `@` 开头的文件引用，使用 `Read` 工具读取文件内容并替换引用。routing 收到的 `用户输入` 可能来自 sdd（已展开）或直接来自用户（未展开），均应检查并展开
2. 提取 `--workflow` 参数值，记为 `$FORCED_FLOW_MODE`
3. 兼容旧输入中的 `--forced` 或 `--force` 标志，记为 `$WORKFLOW_FORCED`（包含时为 `true`，否则为 `false`）。用户无需提供该标志；若 `$FORCED_FLOW_MODE == "expert"`，即使用户未显式携带 `--forced`，写 pending 时也必须按 forced 语义处理。
4. 检查是否包含 `--e2e` 标志，记为 `$ENABLE_E2E`（包含时为 `true`，否则为 `false`）
5. 提取 `--feature-dir` 参数值，记为 `$PRESET_FEATURE_DIR`（支持 `--feature-dir foo` 与 `--feature-dir=foo`）
6. 提取 `--branch-name` 参数值，记为 `$PRESET_BRANCH_NAME`（支持 `--branch-name foo` 与 `--branch-name=foo`）
7. 将 `--workflow`、`--forced`、`--force`、`--e2e`、`--feature-dir`、`--branch-name` 从 `用户输入` 中移除，剩余文本作为真实功能描述继续传递
8. 若 `--workflow` 参数值非法（非 `express|standard|deep|expert`），立即报错并提示用户修正
9. 若未提供 `--workflow` 参数，记 `$FORCED_FLOW_MODE=""`
10. **特性上下文合并解析**：规则同 **`sdd` 步骤 1.5**（`有传参 → 传参 > 无传参 → export > 推导 > allocate`）。从 `用户输入` 提取 `$PRESET_FEATURE_DIR` / `$PRESET_BRANCH_NAME`；**未出现则保持为空，禁止填占位符或臆造值**；**参见「执行约定 > 禁止行为」**
11. 参数预处理完成后，必须打印并写入上下文日志

- `workflow 参数: <$FORCED_FLOW_MODE 或 EMPTY>`
- `forced 参数: <$WORKFLOW_FORCED>（兼容旧输入；expert 会自动视为 forced）`
- `E2E 参数: <$ENABLE_E2E>`
- `特性参数 CLI: dir=<$PRESET_FEATURE_DIR 或 NONE> branch=<$PRESET_BRANCH_NAME 或 NONE>`
- `routing 特性预解析: FEATURE_DIR=... BRANCH_NAME=... FEATURE_CONTEXT_PRESET=... source=...`
- `routing 输入参数: <用户输入>`

12. 执行合并解析并注入 workflow prompt（**参见「执行约定 > 禁止行为」**）：

- **跳过条件**：`$PRESET_FEATURE_DIR` 与 `$PRESET_BRANCH_NAME` **均为空**，且 `${FEATURE_CONTEXT_PRESET:-}` **已由上游赋值**（通常来自 `sdd` 步骤 1.5 `eval --export`）→ **沿用**会话变量，打印 `routing 特性预解析: (沿用上游赋值) FEATURE_DIR=... BRANCH_NAME=... FEATURE_CONTEXT_PRESET=...`
- **否则**执行：

```bash
eval "$(bash "${CLAUDE_PLUGIN_ROOT}/scripts/bash/resolve-feature-context.sh" \
  --working-dir "${CLAUDE_WORKING_DIR}" \
  ${PRESET_FEATURE_DIR:+--feature-dir "$PRESET_FEATURE_DIR"} \
  ${PRESET_BRANCH_NAME:+--branch-name "$PRESET_BRANCH_NAME"} \
  --export)"
```

- **向下游传递**：`FEATURE_CONTEXT_PRESET=true` 时，将已赋值的 `FEATURE_DIR`/`BRANCH_NAME` 注入 workflow prompt；workflow 调用 `specify` 时由 Step 0 从会话变量拼 `$PRESET_SPECIFY_ARGS`；**物理生效仍由 specify → create-branch 完成**

✅ **Checkpoint 参数与环境就绪**: 参数已解析, 特性上下文已合并, 环境变量已确认

## 状态检测与路由

使用 Step 0.2 命令统一检测状态文件，按以下三种情况处理：

- 若脚本返回 `状态文件.omnispec-state.json不存在`，进入情况 A
- `check-routing-state.sh` 在 **`CLAUDE_WORKING_DIR`** 下调用 `${CLAUDE_PLUGIN_ROOT}/scripts/python/omnispec_state.py` 的 `resolve_feature_dir`（优先 `FEATURE_DIR` 环境变量、`changes/.active-feature`、`paths.json` 与最新 state）
- 若脚本返回 JSON，则进入情况 B 或情况 C（基于 `state_file_content.completed_stages` 判定）

### 情况 A: 状态文件不存在 → 首次执行

- 若 `$FORCED_FLOW_MODE` 非空：直接将 `flow_mode` 设为该值并立即路由到对应 workflow，跳过整个复杂度判定块（严禁调用 `complexity-analyzer`）
- 否则：继续下方"复杂度判定"流程

### 情况 B: 状态文件存在, workflow 未完成 → 断点续跑

判定条件: `state_file_content.completed_stages` **不包含** `implement`

1. 读取 `flow_mode` 和 `current_stage`
2. 向用户展示: "检测到未完成的 [flow_mode] workflow, 当前在 [current_stage] 阶段"
3. 使用 `AskUserQuestion`: "继续执行" / "从头开始"
   - 继续 -> 跳转到 `workflow-orchestrator` skill，从 `current_stage` 的下一阶段开始
   - **续跑约束**: 若 `completed_stages` **不含** `implement`，workflow-orchestrator **必须**执行至 `implement`（及后续 `review`）完成
   - 从头开始 ->
     - 若 `$FORCED_FLOW_MODE` 非空：删除状态文件后继承本次 `--workflow` 取值，直接路由到 `workflow-orchestrator`，严禁调用复杂度判定/`complexity-analyzer`
     - 否则：删除状态文件后继续下方"复杂度判定"

### 情况 C: 状态文件存在, workflow 已完成 → 自动回滚

判定条件: `state_file_content.completed_stages` **包含** `implement`

用户的 `用户输入` 是**问题描述/修改诉求**, 而非新功能描述。全自动执行, 无需用户确认。

1. **确定回滚目标阶段**, 按优先级:

   a. **关键词匹配**（从 `用户输入` 推断）:

   | 用户描述关键词 | 回滚目标 |
   | --- | --- |
   | 需求/规范/spec/功能描述/业务需求/场景/用户故事 | specify |
   | 澄清/clarify/模糊/歧义/不明确/补充 | clarify（standard/deep）|
   | 设计/design/方案/架构/接口/数据模型/契约 | design |
   | 任务/tasks/分解/拆分/实现步骤 | tasks |

   b. **产物文件检测**（关键词无法匹配时使用）:

   | 检测文件 | 条件 | 回滚目标 |
   | --- | --- | --- |
   | `evaluations/eval-specify-report.yaml` (stage: specify) | score < 95 或 status != pass | specify |
   | `evaluations/eval-specify-report.yaml` (stage: clarify) | score < 95 或 status != pass | clarify |
   | `evaluations/eval-design-summary.json` | score < 95 或 blocking_count > 0 | design |

   c. **冲突解决**: 若多个阶段都有问题, 回滚到**最早**的有问题阶段

2. **写入回滚信息到状态文件**:

   ```json
   { "rollback": { "target_stage": "<回滚目标>", "reason": "<判定依据>", "user_feedback": "<用户输入原文>", "triggered_at": "<ISO8601>" } }
   ```

3. **输出日志**: `[回滚] 检测到上轮 workflow(<flow_mode>)已完成, 回退到 <target_stage> 重新执行`
4. **直接路由**到状态文件中 `flow_mode` 对应的 workflow agent（不询问用户）

✅ **Checkpoint 状态路由**: 已判定进入 情况A/B/C, flow_mode 来源已确定

---

## 复杂度判定

仅在"情况 A: 首次执行"或"情况 B: 从头开始"时进入（且 `$FORCED_FLOW_MODE` 为空时）。

硬性约束：

- 只要 `$FORCED_FLOW_MODE` 非空，就必须跳过该块；不得用复杂度判定结果覆盖/修改 `--workflow` 指定的模式。
- 若需要写入 `changes/.pending-workflow.json`，`$FORCED_FLOW_MODE` 来源必须带 forced 语义写入，等价于 `omnispec_state.py pending-write --flow-mode "$FORCED_FLOW_MODE" --forced`；复杂度判定结果写入时不得带 `--forced`。
- 路由到 workflow-orchestrator 时须同时注入 `WORKFLOW_FORCED=true|false`。当 `$FORCED_FLOW_MODE == "expert"` 时，注入值必须视为 `true`。

使用 `omni-dsdd:complexity-analyzer` agent, 按其指引:

1. 分析 `用户输入` 的三个维度(规模/清晰度/发散意愿)
2. 得出推荐 flow_mode
3. 直接使用该 flow_mode, 无需用户确认

## flow_mode 优先级

1. `$FORCED_FLOW_MODE`（来自 `--workflow` 参数）
2. 状态文件中的 `flow_mode`（断点续跑/回滚场景）
3. 复杂度判定结果（默认路径）

补充约束：

- `--workflow` 在情况 A（状态文件不存在）生效
- `--workflow` 在情况 B 的"从头开始"（即删除状态文件后）生效
- 情况 B 的"继续执行"和情况 C（回滚）一律按状态文件继续，不受 `--workflow` 影响

**flow_mode 一致性校验（路由分发前强制）**:
在启动 workflow-orchestrator 前，必须验证当前 `flow_mode` 变量值属于 `{express, standard, deep, expert}` 之一。若值非法（为空/为其他字符串），立即报错并输出当前阶段上下文，禁止跳过此校验直接路由。

✅ **Checkpoint flow_mode 确认**: flow_mode 已校验为合法值, 进入路由分发

## 路由分发

按上方「workflow 模式与编排方式」映射表，根据 flow_mode 必须使用 `Skill` 工具调用，例如 `Skill("workflow-orchestrator", args="--flow-mode express --requirement '...' ")`。

- **正常流程**: 将预处理后的 `用户输入`（已移除路由参数）和 `$ENABLE_E2E` 传递给下游, 作为后续 specify 等步骤的功能描述输入
  - **forced 语义**: 将 `$WORKFLOW_FORCED` 注入 workflow prompt；若 `$FORCED_FLOW_MODE == "expert"`，即使用户未显式带 `--forced`，也必须注入 `WORKFLOW_FORCED=true`。
  - **特性上下文**: 若 `FEATURE_CONTEXT_PRESET=true`，在 agent prompt 中注入已赋值的会话变量；workflow Step 0 从会话变量拼 `$PRESET_SPECIFY_ARGS`（**勿再调用** `resolve-feature-context.sh`）：

    ```bash
    if [[ "${FEATURE_CONTEXT_PRESET:-}" == "true" ]]; then
      PRESET_SPECIFY_ARGS="--feature-dir $(printf '%q' "$FEATURE_DIR") --branch-name $(printf '%q' "$BRANCH_NAME")"
    else
      PRESET_SPECIFY_ARGS=""
    fi
    ```

  - **deep 模式专属约定**: 同一段 `用户输入` **同时**视为 `reverse --target on-demand --requirement` 时 `--requirement` 位置应拼接的内容；路由层无需再单独传需求参数
- **回滚流程**: `workflow-orchestrator` skill 自行读取状态文件中的 `rollback` 字段执行回退

### workflow-orchestrator 返回后的完成性校验（**禁止误报 SDD 完成**）

> `workflow-orchestrator` 应按 YAML 顺序一次跑完全部 stage。返回后 routing **不得**立即输出「SDD 执行完成」；须用脚本校验，未完成则**同轮**补跑 orchestrator。

1. 解析 `FEATURE_DIR`（`source "$FEATURE_DIR/.runs/env.sh"` 或 `python3 scripts/python/omnispec_state.py resolve`）
2. 循环检测与补跑（直至 `workflow-check-incomplete` 返回 `0` 或 orchestrator 明确失败）：

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/bash/workflow-check-incomplete.sh" \
  --feature-dir "$FEATURE_DIR"
```

| 退出码 | 处理方式 |
|--------|----------|
| `0` | 允许 routing 结束；`sdd` 可输出最终摘要（须过 `workflow-complete` gate） |
| `10` | `implement` 未完成：**同轮再次** `Skill("workflow-orchestrator")` 从断点续跑 |
| `11` | `review` 未完成：同上，**同轮再次**调用 orchestrator |
| `12` | `local-sandbox-fix` 未完成（expert 验证阶段）：同上，**同轮再次**调用 orchestrator |

3. **禁止输出**（在退出码为 `10`/`11` 且尚未补跑完成时）：`SDD 执行完成` / 仅含 specify/tasks/analyze 而无 implement/review 的「全流程完成」表格
4. 输出最终摘要前：

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/bash/workflow-gate.sh" \
  --feature-dir "$FEATURE_DIR" --check workflow-complete --record
```

## 状态文件格式

`<state_file_base_dir>/<state_file_relative_path>`（由 `check-routing-state.sh` 返回目录值与相对路径后拼接得到）:

```json
{
  "flow_mode": "express|standard|deep|expert",
  "current_stage": "specify|clarify|design|tasks|analyze|implement",
  "completed_stages": [],
  "last_updated": "ISO8601",
  "arguments": "用户输入原文",
  "rollback": null
}
```

## 本技能使用的 Agent 与 Skill

- `complexity-analyzer` - 复杂度分析 agent，必须使用 `Agent(subagent_type="complexity-analyzer", ...)` 调用
- `workflow-orchestrator` - 统一工作流编排 skill，必须使用 `Skill("workflow-orchestrator")` 调用

## 脚本依赖

| 脚本 | 路径前缀 | 用途 |
| ------ | ---------- | ---- |
| `check-routing-state.sh` | `skills/routing/scripts/` | 路由状态探测（必填 `--plugin-root`、`--working-dir`） |
| `omnispec_state.py` | `scripts/python/` | 特性目录解析（由状态脚本加载） |
| `workflow-check-incomplete.sh` | `scripts/bash/` | workflow 返回后续跑检测（routing 必用） |
| `workflow-gate.sh` | `scripts/bash/` | 最终完成性校验 |
