---
name: routing
description: 智能路由编排器. 分析功能描述复杂度, 将 flow_mode（express/standard/deep）映射到对应 workflow agent 并启动执行；三者为 agent 选择符，整条链路由 agent 编排而非同名 skill。触发词: /routing, 智能编排, 路由模式.
user-invokable: false
---

# routing

## workflow 模式、flow_mode 与 agent（统一约定）

- `express`、`standard`、`deep` 是写入状态或路由逻辑的 **`flow_mode` 取值**，语义上对应 **三类 workflow agent**，**不是** skill 名称，也**不得**当作 `express`/`standard`/`deep` 等 skill 去调用。
- 路由结果必须落到 **Task/subagent 形式的 workflow agent**：

| flow_mode | 必须由该 agent 执行 |
| --------- | ------------------- |
| `express` | `express-workflow` |
| `standard` | `standard-workflow` |
| `deep` | `deep-workflow` |

- **`routing` 本身是 skill**：负责参数预处理、状态机与**选择/恢复** `flow_mode`；真正按模式跑通 SDD 步骤的是上表中的 **workflow agent**，agent 内部再按需调用各 **skill**（如 `specify`）。
- **`complexity-analyzer` 是 agent**：仅在未强制 `--workflow` 时产出推荐 `flow_mode` 字符串，供本 skill 读取后仍须按上表启动对应 **workflow agent**，而不是启动名为 `express` 的 skill。

## 用户输入

```text
$ARGUMENTS
```

## 参数预处理

在任何状态检测之前，先解析 `$ARGUMENTS` 中的可选参数：

- `--workflow <express|standard|deep>`
- `--workflow=<express|standard|deep>`
- `--e2e`：启用E2E测试设计（默认关闭）

处理规则：

1. 提取 `--workflow` 参数值，记为 `$FORCED_FLOW_MODE`
2. 检查是否包含 `--e2e` 标志，记为 `$ENABLE_E2E`（包含时为 `true`，否则为 `false`）
3. 将 `--workflow` 和 `--e2e` 从 `$ARGUMENTS` 中移除，剩余文本作为真实功能描述继续传递
4. 若 `--workflow` 参数值非法（非 `express|standard|deep`），立即报错并提示用户修正
5. 若未提供 `--workflow` 参数，记 `$FORCED_FLOW_MODE=""`
6. 参数预处理完成后，必须打印并写入上下文日志：
   - `workflow 参数: <$FORCED_FLOW_MODE 或 EMPTY>`
   - `E2E 参数: <$ENABLE_E2E>`
   - `routing 输入参数: <$ARGUMENTS>`

参数说明：
- `--workflow` 仅接受 `express|standard|deep`
- `--e2e` 为开关标志，不需要值，启用后 specify 和 design 阶段会执行 E2E 测试设计
- 推荐在用户希望明确控制 workflow 或启用E2E测试时使用这些参数
- 未提供参数时，按默认动态判定流程执行，E2E默认关闭

## 环境初始化

1. 判断当前操作系统(windows/linux)
2. 从仓库根目录运行脚本获取配置:
   - linux: `scripts/bash/check-prerequisites.sh --json --paths-only`
   - windows: `scripts/powershell/check-prerequisites.ps1 --json --paths-only`
3. 解析 JSON 获取: `FEATURE_DIR`, `FEATURE_SPEC`, `IMPL_DESIGN`, `TASKS`

### 环境初始化语义约束（强制）

- `check-prerequisites.sh --paths-only` 在 routing 阶段仅用于提供**临时路径上下文**（如 `REPO_ROOT`、候选 `FEATURE_DIR`），**不是最终分支决策依据**。
- routing 阶段**不得创建分支**，也**不得创建 `changes/<branch>` 分支目录**。
- routing 阶段**不得在任何路径下创建分支目录、特性目录或等价工作目录**，不限于 `changes/`，也包括 `.infra/` 或其他自定义目录下的分支工作路径。
- routing 阶段**不得假设**已生成最终 `BRANCH_NAME` / `FEATURE_DIR`；此时获取到的分支与目录信息仅可用于只读探测与状态判断。
- 在 `create-branch` 执行前，严禁基于该临时 `FEATURE_DIR` 落盘关键产物（如 `spec.md`、`design.md`、`tasks.md`、状态文件）。
- 若 `BRANCH` 命中 `master/main`：
  - 仅允许用于读取历史状态或做只读判定；
  - 禁止用于创建/写入特性目录内容；
  - 必须在后续 `specify` 中通过 `create-branch` 产生或复用安全特性分支后，才允许写入。

## 状态检测与路由

检查 `FEATURE_DIR/.runs/.omnispec-state.json` 是否存在, 按以下三种情况处理:

### 情况 A: 状态文件不存在 → 首次执行

- 若 `$FORCED_FLOW_MODE` 非空：直接将 `flow_mode` 设为该值并立即路由到对应 workflow agent，跳过整个复杂度判定块（严禁调用 `complexity-analyzer`）
- 否则：继续下方"复杂度判定"流程

### 情况 B: 状态文件存在, workflow 未完成 → 断点续跑

判定条件: `completed_stages` **不包含** `implement`

1. 读取 `flow_mode` 和 `current_stage`
2. 向用户展示: "检测到未完成的 [flow_mode] workflow, 当前在 [current_stage] 阶段"
3. 使用 `AskUserQuestion`: "继续执行" / "从头开始"
   - 继续 -> 跳转到对应 workflow agent, 从 `current_stage` 的下一阶段开始
   - 从头开始 ->
     - 若 `$FORCED_FLOW_MODE` 非空：删除状态文件后仍必须继承本次 `--workflow` 的取值，直接路由到对应 workflow agent，严禁调用复杂度判定/`complexity-analyzer`
     - 否则：删除状态文件后继续下方"复杂度判定"

### 情况 C: 状态文件存在, workflow 已完成 → 自动回滚

判定条件: `completed_stages` **包含** `implement`

此时用户的 `$ARGUMENTS` 是**问题描述/修改诉求**, 而非新功能描述. 全自动执行, 无需用户确认:

1. **确定回滚目标阶段**, 按优先级:

   a. **关键词匹配**（从用户 `$ARGUMENTS` 推断）:

   | 用户描述中的关键词 | 回滚目标 |
   | --- | --- |
   | 需求/规范/spec/功能描述/业务需求/场景/用户故事 | specify |
   | 澄清/clarify/模糊/歧义/不明确/补充 | clarify |
   | 设计/design/方案/架构/接口/数据模型/契约 | design |
   | 任务/tasks/分解/拆分/实现步骤 | tasks |

   b. **产物文件检测**（辅助佐证, 关键词无法匹配时使用）:

   | 检测文件 | 检测条件 | 回滚目标 |
   | --- | --- | --- |
   | `FEATURE_DIR/.runs/evaluations/evaluation-report.yaml` (stage: specify) | score < 95 或 status != pass | specify |
   | `FEATURE_DIR/.runs/evaluations/evaluation-report.yaml` (stage: clarify) | score < 95 或 status != pass | clarify |
   | `FEATURE_DIR/.runs/evaluations/design-evaluation-summary.json` | score < 95 或 blocking_count > 0 | design |

   c. **冲突解决**: 若多个阶段都有问题, 回滚到**最早**的有问题阶段.

2. **写入回滚信息到状态文件**:

   ```json
   {
     "rollback": {
       "target_stage": "<回滚目标阶段>",
       "reason": "<判定依据摘要>",
       "user_feedback": "<用户 $ARGUMENTS 原文>",
       "triggered_at": "<ISO8601>"
     }
   }
   ```

3. **输出日志**: `[回滚] 检测到上轮 workflow(<flow_mode>)已完成, 回退到 <target_stage> 重新执行`

4. **直接路由**到状态文件中 `flow_mode` 对应的 workflow agent（不询问用户）.

---

## 复杂度判定

仅在"情况 A: 首次执行"或"情况 B: 从头开始"时进入（且 `$FORCED_FLOW_MODE` 为空时）。

硬性约束：
- 只要 `$FORCED_FLOW_MODE` 非空，就必须跳过该块；不得用复杂度判定结果覆盖/修改 `--workflow` 指定的模式。

若 `$FORCED_FLOW_MODE` 非空，则在情况 A 或情况 B（从头开始）均**结束本节**。

使用 `complexity-analyzer` agent, 按其指引:

1. 分析 `$ARGUMENTS` 的三个维度(规模/清晰度/发散意愿)
2. 得出推荐 flow_mode
3. 直接使用该 flow_mode, 无需用户确认

## flow_mode 优先级

1. `$FORCED_FLOW_MODE`（来自 `--workflow` 参数）
2. 状态文件中的 `flow_mode`（断点续跑/回滚场景）
3. 复杂度判定结果（默认路径）

补充约束：
- `--workflow` 在情况 A（状态文件不存在）生效
- `--workflow` 在情况 B 的“从头开始”（即删除状态文件后）生效
- 当 `$FORCED_FLOW_MODE` 非空且满足上述两个场景时，优先级 3（复杂度判定结果）永远不触发
- 情况 B 的“继续执行”和情况 C（回滚）一律按状态文件继续，不受 `--workflow` 影响

## 路由分发

> **执行约定**: 所有 workflow agent 必须使用 `run_in_background: false`（前台运行），禁止后台执行。

> **禁止行为**:
> - **严格禁止**在本步骤之前创建任何分支目录、特性目录、工作目录或 `.omnispec-state.json` 文件（不限于 `changes/`，也包括 `.infra/` 等路径示例）
> - 目录和状态文件应由 `create-branch`（在 `specify` 内部调用）创建
> - 若当前已在特性分支上下文中，`check-prerequisites.sh` 应返回对应特性分支；若异常返回 `master/main`，应视为分支探测异常并触发重试/修复，而不是继续使用主干分支
> - **严格禁止**跳过 `create-branch`：无论是新建还是复用分支，均必须执行 `create-branch` 并以其输出为准
> - **严格禁止**在 routing 阶段假设“分支已创建”或“分支目录已创建”，不得将临时探测值当作最终分支信息向后续写入流程传播

根据 flow_mode, 使用对应 subagent 执行:

| flow_mode | Agent                          |
| --------- | ------------------------------ |
| express   | `express-workflow`    |
| standard  | `standard-workflow`   |
| deep      | `deep-workflow`                |

- **正常流程**: 将预处理后的 `$ARGUMENTS`（已移除 `--workflow` 和 `--e2e` 后的剩余文本）和 `$ENABLE_E2E` 标志传递给 workflow agent.
  - **通用**: 各 workflow 均将该字符串作为后续 **specify** 等步骤的**功能描述**输入，并在调用 `specify` 和 `design` 时将 `$ENABLE_E2E` 注入调用上下文。
  - **`deep-workflow` 专属约定**: 同一段 `$ARGUMENTS` **同时**视为用户若执行 `reverse --target on-demand --requirement` 时、**`--requirement` 位置应拼接的内容**（需求文件路径或需求描述文本，须满足 `reverse-on-demand` 约束）。路由层**无需**再单独传「需求参数」；deep workflow 的 Step 0 与 Step 2 共用此输入。
- **回滚流程**: workflow agent 自行读取状态文件中的 `rollback` 字段执行回退.

## 状态文件格式

`FEATURE_DIR/.runs/.omnispec-state.json`:

```json
{
  "flow_mode": "express|standard|deep",
  "current_stage": "specify|clarify|design|tasks|analyze|implement",
  "completed_stages": [],
  "last_updated": "ISO8601",
  "arguments": "$ARGUMENTS 原文",
  "rollback": null
}
```

## 本技能使用的 Agent

- `complexity-analyzer` - 复杂度分析 agent，产出推荐 `flow_mode`（`express`/`standard`/`deep` 字符串）；**执行**仍交给下方 workflow agent
- `express-workflow` - `flow_mode=express` 时的 workflow agent
- `standard-workflow` - `flow_mode=standard` 时的 workflow agent
- `deep-workflow` - `flow_mode=deep` 时的 workflow agent
