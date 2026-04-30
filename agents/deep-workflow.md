---
name: deep-workflow
description: 深度模式 workflow, 包含完整的 specify/clarify/design 流程, 使用 AI 验证器自动检查质量.
---

# deep-workflow

## 角色

编排 deep 模式的完整 skill 调用顺序. 适用于大规模、需分析、涉及架构决策的功能需求.
与 standard 模式的核心差异: **deep 模式包含完整的 clarify 步骤**, 提供更充分的需求澄清.

## workflow 命名约定（统一说明）

- 状态与路由中的 **`flow_mode=deep`** 表示「走本 **agent**（`deep-workflow`）」；**`deep` 不是 skill**，不要以 skill 名调用。
- 本 agent 负责编排；后续各 Step 调用的是 **`reverse-on-demand`**、**`specify`** 等 **skill**，与 `skills/routing`、`agents/complexity-analyzer` 及 express/standard 两个 workflow agent 文档中的约定一致。

## 上游输入（与 `routing` 对齐）

- **`$ARGUMENTS`**：由 `routing`（或等价入口）传入本 workflow 的**同一段用户输入**（通常已去除 `--workflow` 和 `--e2e` 等路由专用参数，见 routing 的「参数预处理」）。
- **`$ENABLE_E2E`**：是否启用E2E测试设计（`true`/`false`，默认 `false`），由 `routing` 解析 `--e2e` 标志后传入。调用 `specify` 和 `design` 时，须将 `$ENABLE_E2E` 注入调用上下文。
- **语义合一**：该 **`$ARGUMENTS` 既是** Step 2 `specify` 的**功能描述**，**也是** Step 0 中 `reverse --target on-demand --requirement` **在 `--requirement` 位置应拼接的内容**（需求 **Markdown 文件路径** 或 **需求描述文本**，须满足 `reverse-on-demand` 对需求编号等约束，见该 Skill 的 `SKILL.md`）。无需也不应再单独传另一路「需求参数」。
- 若 **`$ARGUMENTS` 去除首尾空白后为空**：**中止**本 workflow，提示用户补充需求文件路径或需求描述后再执行。

## 回滚入口

启动时检查 `FEATURE_DIR/.runs/.omnispec-state.json` 中是否存在 `rollback` 字段:

- **存在 rollback**:
  1. 读取 `rollback.target_stage` 和 `rollback.user_feedback`
  2. 将 `completed_stages` 中 `target_stage` 及之后的阶段全部移除
  3. 将 `current_stage` 更新为 `target_stage` 的前一阶段
  4. 清除 `rollback` 字段, 写回状态文件
  5. 输出: `[回滚] 从 <target_stage> 重新执行, 用户反馈: <user_feedback 摘要>`
  6. **跳转**到 `target_stage` 对应的 Step, 将 `user_feedback` 作为额外修改指示注入对应 skill 调用

  阶段到 Step 的映射:
  | target_stage | 跳转到 |
  |---|---|
  | reverse | Step 1 |
  | specify | Step 2 |
  | clarify | Step 3 |
  | design | Step 4 |
  | tasks | Step 5 |

- **不存在 rollback**: 正常从 Step 0 开始执行

## 执行约定

### 工具调用识别规则

> **关键**: 本 workflow 中调用的技能名称（如 `specify`、`reverse-on-demand`、`create-branch`）均与对应 **SKILL.md** 的 `name` 字段一致，均为 **skill**，必须使用 `Skill` 工具调用；按需反构步骤调用的 `reverse-on-demand` 亦为 **Skill**（对应用户侧入口文档 `reverse --target on-demand`，**不要**当作可执行 shell 命令直接跑）。

| 名称格式 | 工具类型 | 正确调用 |
|----------|----------|----------|
| 各技能 `name` | **Skill** | `Skill("<name>")`（与 `skills/<目录>/SKILL.md` 中 `name` 一致） |
| `reverse-on-demand` | **Skill** | `Skill("reverse-on-demand")` |
| `mini-xxx` | **Skill** | `Skill("mini-xxx")`（如 mini-design、mini-implement；聊天仍可用 `/mini-design` 等触发） |
| 其他名称 | 由上下文判断 | 参考上述模式判断 |

> **常见错误**: 将 `tasks` 写成 `Agent("tasks")` 会导致 "Agent type not found" 错误。

### 同步执行规则

> **关键**: 所有 "调用技能" 步骤必须**同步等待**技能完成并返回结果。
>
> - **正确做法**: 使用 `Skill` 工具调用技能，等待返回后再继续下一步
> - **错误做法**: 调用技能后不等结果就继续执行，或自行判断"卡住"后跳过
> - **等待验证**: 技能完成后必须读取 `FEATURE_DIR/.runs/evaluations/evaluation-report.yaml` 或对应的输出文件验证结果

#### 嵌套调用规则

> **关键**: 当 skill A 的 SKILL.md 中指示"调用 skill B"时（如"使用 `specify` 技能"），这构成**嵌套调用链**：
>
> 1. subagent 执行 skill A 时，读取到"调用某技能"
> 2. 必须使用 `Skill("<name>")` 调用该嵌套 skill（`<name>` 与目标 SKILL.md 的 `name` 一致）
> 3. **必须等待嵌套 skill 完成并返回**后，才能继续 skill A 的后续步骤
> 4. 后续步骤（如 `spec-impact-analyze`、`specify-requirement` 等）**不得提前开始**
>
> **典型错误场景**: `specify` 的步骤1是"创建特性分支"，如果 subagent 没等 `create-branch` 完成就开始步骤2-3，会导致文件创建在错误分支
>
> **验证方法**: 嵌套 skill 返回后，检查 `BRANCH_NAME` 环境变量或输出中的分支名是否符合预期，再继续后续步骤

### 技能失败判定

> **重要**: 技能可能以两种方式失败，workflow 必须区分处理：

| 失败类型 | 判断依据 | 处理方式 |
|----------|----------|----------|
| **技能执行失败** | 技能明确报错（如缺少参数、无法找到文件、验证不通过） | **停止并向用户报告**，等待用户补充信息或取消 |
| **产物验证失败** | `evaluation-report.yaml` 或 `design-evaluation-summary.json` 中 score < 95 或 status != pass | **停止并向用户报告**，询问是否调整后重试 |
| **技能自动跳过** | 技能输出明确说明跳过原因（如"已存在，无需更新"） | 继续下一步，更新状态 |

### 技能失败时的报告格式

```
[技能执行失败] <阶段名称> - <技能名称>

失败原因: <技能报告的具体错误>
建议操作:
  1. 补充必要信息后重新执行
  2. 取消当前 workflow

请选择: 1 / 2
```

### 禁止行为

> **严格禁止**: 技能报错后不通知用户就跳过，或在日志中仅记录"skipped"而不向用户展示。

## 流程优先（按顺序执行）

在进入各 Step 细节前，先按执行顺序列出完整流程。**必须严格按序执行，不允许跳步、并行或重排**：

1. Step 1：按需反构 reverse（on-demand）
2. Step 2：规范生成（specify）
3. Step 3：规范澄清（clarify）
4. Step 4：设计规划（design）
5. Step 5：任务分解（tasks，静默执行）
6. Step 6：一致性分析（analyze，静默执行）
7. Step 7：代码实现（implement，静默执行）

仅当前一步**成功完成并通过对应校验**后，才允许进入下一步。

### Step 1: 按需反构reverse（on-demand，在章程与 specify 之前）

> **用户侧等价入口**（由 Agent 按文档解析参数，**非 shell 命令**）：`reverse --target on-demand --requirement <...>`，其中 **`<...>` 与传入本 workflow 的 `$ARGUMENTS` 为同一段内容**（与 `routing` 所述「作为功能描述传递」一致）。

1. 确认 **`$ARGUMENTS` 非空**（规则见上节）；否则中止。
2. 按安装目录下 **`reverse` 命令说明**（如 `claude/commands/reverse.md` 或 `.cursor/commands/reverse.md`）解析与 `on-demand` 相关的通用参数（若 `$ARGUMENTS` 内嵌 `--demand-complexity` 等，一并按该文档解析）。
3. 调用技能 **`reverse-on-demand`**，传入与下列 CLI **语义等价**的参数串（须包含 `--target on-demand`，且 **`--requirement` 的取值等于本 workflow 收到的 `$ARGUMENTS`**；若 `$ARGUMENTS` 已是一条完整 `reverse ...` 风格参数串，则按 `reverse` 文档拆解后调用 Skill，避免重复拼接）：
   - 典型形态：`--target on-demand --requirement "$ARGUMENTS"`（引号与转义按宿主约定）。
4. **必须同步等待**该 Skill 完整结束；失败则按「技能失败判定」处理并**不得**进入 Step 1。
5. **不写** `FEATURE_DIR/.runs/.omnispec-state.json`（本步不纳入 SDD 状态机；状态文件仍自 Step 2 `specify` 成功后由 `specify` 开始管理）。
6. 若按需反构已创建或确定 `FEATURE_DIR` / 分支，则必须将 Step 1 输出变量 **`BRANCH_NAME`、`FEATURE_DIR`** 原样传递给 Step 2 `specify`，并要求 `specify` 走 `create-branch` 复用分支/目录逻辑。
7. 🔴 **禁止行为**：Step 2 不得忽略 Step 1 的 `BRANCH_NAME`/`FEATURE_DIR` 重新生成新分支；如检测到不一致，必须中止并报错，提示用户确认是否改为复用。

### Step 2: 规范生成

> **重要**: `specify` 内部会调用 `create-branch` 创建或复用正确的分支和 `FEATURE_DIR`；若 Step 0 已确定分支与目录，须保持一致。`create-branch` 为强制步骤，**不允许跳过**。

1. 调用技能 `specify`（使用 `$ARGUMENTS` 作为功能描述, 传递 `$ENABLE_E2E` 标志，同时透传 Step 1 的 `BRANCH_NAME`、`FEATURE_DIR` 以复用既有分支与目录）
2. 技能完成后读取 `FEATURE_DIR/.runs/evaluations/evaluation-report.yaml`（stage: specify）：
   - 通过: 在 `FEATURE_DIR` 下创建/更新 state 文件，`current_stage = "specify"`，进入 Step 3
   - 最终失败: 停止并向用户报告

### Step 3: 规范澄清

1. 调用技能 `clarify`
2. 技能完成后读取 `FEATURE_DIR/.runs/evaluations/evaluation-report.yaml`（stage: clarify）：
   - 通过: 继续 Step 4
   - 最终失败: 停止并向用户报告
3. 更新状态文件: `current_stage = "clarify"`, 标记完成

### Step 4: 设计规划

1. 调用技能 `design`（传递 `$ENABLE_E2E` 标志）
   - 确保设计方案完整且与技术决策一致
2. 技能完成后读取 `FEATURE_DIR/.runs/evaluations/design-evaluation-summary.json`：
   - 通过 (无 blocking 且 score >= 95): 继续 Step 5
   - 最终失败: 视严重程度决定
     - 一般问题: 停止并向用户报告
     - 严重 scope 问题: 建议回退到 Step 2 修订 spec
3. 更新状态文件: `current_stage = "design"`, 标记完成

### Step 5: 任务分解（静默执行）

1. 调用技能 `tasks`
2. 更新状态文件: `current_stage = "tasks"`, 标记完成

### Step 6: 一致性分析（静默执行）

1. 调用技能 `analyze`
   - 发现不一致或质量问题时, **由技能直接改制品并迭代修复**, **不得**因「是否修复 / 是否继续 workflow」向用户提问.
   - 与 `analyze` SKILL 中 **统一自动修复行为**（操作约束）一致: **不设修复轮数上限**, 自动修复至收敛; 若仍有残留问题, 技能须**打印完整问题列表**后**正常结束**, workflow **不得**因此停表或判定 analyze 阶段失败, **必须**继续后续步骤.
2. 更新状态文件: `current_stage = "analyze"`, 标记完成

### Step 7: 代码实现（静默执行）

1. 调用技能 `implement`
2. 按 `tasks.md` 中的任务顺序和依赖关系执行
3. 每完成一个任务, 将其从 `- [ ]` 标记为 `- [X]`
4. **重要**：如果存在 `local-ci` skill 则调用 `local-ci [工程目录] -l go`
5. 更新状态文件: `current_stage = "implement"`, 标记完成

## 状态管理

每步完成后更新 `FEATURE_DIR/.runs/.omnispec-state.json`（**自 Step 2 specify 成功后**开始维护；Step 0 按需反构、Step 1 章程不写入该文件）:

```json
{
  "flow_mode": "deep",
  "current_stage": "<当前阶段名>",
  "completed_stages": ["reverse", "specify", "clarify", "design", "tasks", "analyze", "implement"],
  "last_updated": "<ISO8601时间戳>",
  "arguments": "<原始功能描述>",
  "validation_results": {
    "specify": {"score": 96, "status": "passed"},
    "clarify": {"score": 97, "status": "passed"},
    "design": {
      "consistency_check": "passed",
      "quality_score": 98,
      "status": "passed"
    }
  }
}
```

## 最终输出

```
[Deep 模式] workflow 执行完成

分支: <分支名>
AI 验证结果:
  - reverse: ✅ 通过 (score: 95/100)
  - specify: ✅ 通过 (score: 96/100)
  - clarify: ✅ 通过 (score: 97/100)
  - design: ✅ 通过 (一致性: 无问题, 质量: 98/100)
制品路径:
  - reverse（若 Step 0 已生成）: omni-doc/on-demand/logic_architecture.md、omni-doc/on-demand/functions/ 等
  - spec.md: <路径>
  - design.md: <路径>
  - tasks.md: <路径>
任务统计: 总计 N 个任务, 已完成 M 个
关键决策: (列出 clarify 阶段的主要澄清项)
```
