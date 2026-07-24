---
name: workflow-orchestrator
argument-hint: <flow_mode> --requirement "<功能描述>" [--enable-e2e] [--feature-dir <dir>] [--branch-name <name>]
description: 统一工作流编排器。读取 YAML 工作流定义，按 stage.type 派发：skill 直接 Skill 触发，agent 经 Task(general-purpose) 隔离执行。
user-invokable: false
allowed-tools: Task, Skill, Read, Bash, Grep, Glob, AskUserQuestion
---

# workflow-orchestrator

## 角色

统一编排器，替代原先的 `express-workflow`、`standard-workflow`、`deep-workflow` 三个 agent。
读取 `${CLAUDE_PLUGIN_ROOT}/workflows/${FLOW_MODE}.yaml` 中声明的阶段列表，按 `stage.type` 派发：

| `stage.type` | 派发方式 |
|--------------|----------|
| `skill` | 编排器 **直接** `Skill("<stage.skill>")`（同会话，适合人机交互型 skill如 brainstorming） |
| `agent` | **Task(general-purpose)** 子代理 Read 并执行 `skills/<skill>/SKILL.md`（上下文隔离） |
| `parallel_agents` | 多个 **Task(general-purpose)** 并行 |

完成后通过 `workflow-update-state.sh` 更新 `.omnispec-state.json`。

## 上游参数（由 routing 注入）

| 参数 | 来源 | 用途 |
| ------ | ------ | ------ |
| `$FLOW_MODE` | routing 按复杂度或 `--workflow` 设定 | 选择 `workflows/${FLOW_MODE}.yaml` |
| `$ARGUMENTS` | routing 剥离路由参数后的功能描述 | specify 等技能的功能描述输入 |
| `$WORKFLOW_FORCED` | routing 解析 `--forced` 或 `--workflow=expert` | 写 pending workflow 时传递 forced 语义 |
| `$ENABLE_E2E` | routing 解析 `--e2e` | 注入 specify / design 调用 |
| `$FEATURE_DIR` | routing `resolve-feature-context.sh` 或 specify→create-branch | 状态文件、制品根 |
| `$BRANCH_NAME` | routing `resolve-feature-context.sh` 或 specify→create-branch | Git 分支 |
| `$FEATURE_CONTEXT_PRESET` | routing `eval --export` | 是否有预设特性上下文 |

## 执行约定

### 工具调用识别规则

YAML `stage.skill` 支持命名空间形式（如 `omni-dsdd:design`）。编排器调用 Skill/Task 时保留 YAML 原值；读取本地文件、拼接 gate 脚本路径时使用冒号后的本地 skill 名（如 `design` → `skills/design/SKILL.md`）。编排器**不得**使用 `Agent(subagent_type="omni:<skill>")`（`agents/` 下无 SDD 阶段 agent 注册）。

| `stage.type` | 工具 | 调用 |
|--------------|------|------|
| `skill` | **Skill** | `Skill("<stage.skill>", args=...)` — **编排器本层直接触发**，禁止再包 Task |
| `agent` | **Task** | `Task(subagent_type="general-purpose", prompt=...)`，prompt 要求 Read 并完整执行 `skills/<skill>/SKILL.md` |
| `parallel_agents` | **Task** × N | 对 `stage.skills[]` 各启一个 `Task(general-purpose)` |
| `agents/` 已注册（非 SDD stage） | **Task** 或 **Agent** | 优先 `Task(general-purpose)` 读 `agents/<name>.md` |

> **`type: skill` vs `type: agent`**：`skill` 留在编排器同会话（如 brainstorming 需与用户逐轮对话）；`agent` 用 Task 隔离上下文与 token（如 specify/design/implement）。

### 同步执行规则

- 每个 stage（无论 Skill 或 Task）必须**同步等待**完成后再进入下一阶段
- 禁止不等结果就继续下一步
- agent 完成后必须读取对应评测文件验证结果
- **`type: skill` 阶段完成后**：编排器**必须在本轮同一次回复内**继续 §Step 1–N 循环（状态更新 → 下一 stage），**禁止**仅输出「返回 orchestrator」后结束本轮、等用户下一条消息再跑

### 嵌套调用规则

- **`type: agent`**：编排器只管 Task 级调度；子代理内部可 `Skill("create-branch")` 等嵌套调用
- **`type: skill`**：编排器即执行主体，按 SKILL.md 完整执行；该 skill 内部仍可嵌套其它 Skill
- 验证方法：阶段完成后检查 `FEATURE_DIR`、制品文件或 eval 结果是否符合预期

### 技能失败判定

| 失败类型 | 判断依据 | 处理方式 |
| ---------- | ---------- | ---------- |
| **技能执行失败** | 技能明确报错 | **停止并向用户报告** |
| **产物验证失败** | eval 文件 score < 95 或 status != pass | **按 auto_converge 重试**；无 auto_converge 则停止报告 |
| **技能自动跳过** | 技能输出说明跳过原因 | 继续下一步，更新状态 |

### 禁止行为

- **严格禁止**手写 `.omnispec-state.json`（必须通过 `workflow-update-state.sh`）
- **严格禁止**无 implement 报 workflow 完成
- **严格禁止**跳过 `create-branch`（specify 内部强制调用）
- **严格禁止**在编排器层自行 mkdir 或 Write `.runs/env.sh`
- **严格禁止**子代理/`type: skill` 阶段报错后不通知用户就跳过
- **`type: agent` 阶段**：**禁止**编排器本层 `Skill(stage.skill)` 绕过 Task（须 Task 隔离上下文）
- **`type: skill` 阶段**：**禁止**用 Task 包装（须编排器直接 `Skill(stage.skill)`）

## 主流程

### Step 0: 启动

#### 0.1 加载工作流定义

```md
Read ${CLAUDE_PLUGIN_ROOT}/workflows/${FLOW_MODE}.yaml
```

解析 `stages` 列表，构建执行计划。

#### 0.2 特性上下文

```bash
# routing prompt 已注入 FEATURE_DIR / BRANCH_NAME / FEATURE_CONTEXT_PRESET；勿再调用 resolve
if [[ "${FEATURE_CONTEXT_PRESET:-}" == "true" ]]; then
  PRESET_SPECIFY_ARGS="--feature-dir $(printf '%q' "$FEATURE_DIR") --branch-name $(printf '%q' "$BRANCH_NAME")"
else
  PRESET_SPECIFY_ARGS=""
fi
```

- preset 时：**禁止**自行 Write `.runs/env.sh` 或 `mkdir`；物理生效由 specify → create-branch 传参完成
- 续跑时解析 `FEATURE_DIR`：`source "$FEATURE_DIR/.runs/env.sh"` 或 `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/python/omnispec_state.py" resolve`

##### 0.2.1 flow_mode 落盘（派发 specify 前必做，禁止跳过）

> 防止「orchestrator 跑 standard、state 却被写成 express」的不一致（日志实拍事故）。
> 须在派发 specify 前显式落盘 flow_mode，让 specify init 能读到正确值，而非回退默认 express。

```bash
# 首次执行（FEATURE_CONTEXT_PRESET=false）：写 pending，specify init 会 consume
PENDING_FORCED_ARGS=()
if [[ "${FLOW_MODE}" == "expert" ]]; then
  # expert 只能由显式 --workflow 或既有 expert 状态进入；pending-write 必须带 --forced，否则会按自动 flow 校验拒绝 expert。
  PENDING_FORCED_ARGS+=(--forced)
fi

python3 "${CLAUDE_PLUGIN_ROOT}/scripts/python/omnispec_state.py" pending-write \
  --working-dir "${CLAUDE_WORKING_DIR}" --flow-mode "${FLOW_MODE}" --arguments "${ARGUMENTS}" \
  "${PENDING_FORCED_ARGS[@]}"

# 续跑或 preset（FEATURE_DIR 已存在）：直接更新 state
if [[ -n "${FEATURE_DIR:-}" && -f "${FEATURE_DIR}/.runs/.omnispec-state.json" ]]; then
  bash "${CLAUDE_PLUGIN_ROOT}/scripts/bash/workflow-update-state.sh" \
    --feature-dir "$FEATURE_DIR" --flow-mode "${FLOW_MODE}" --current-stage init
fi
```

并在每个 `type: agent` 阶段的 Task prompt 中注入 `export FLOW_MODE="${FLOW_MODE}"`，使 specify harness 的 `resolve_flow_mode(cli_override=$FLOW_MODE)` 命中正确值。

#### 0.3 回滚检测

读取 `FEATURE_DIR/.runs/.omnispec-state.json` 中是否存在 `rollback` 字段：

- **存在 rollback**：
  1. 读取 `rollback.target_stage` 和 `rollback.user_feedback`
  2. 使用 YAML 中的 `rollback_stage_map` 定位目标 stage 索引
  3. 将执行计划从 `target_stage` 对应的索引开始（之前阶段标记为已完成）
  4. 清除 `rollback` 字段，通过 `workflow-update-state.sh` 写回
  5. 输出: `[回滚] 从 <target_stage> 重新执行, 用户反馈: <摘要>`
  6. 将 `user_feedback` 注入目标 stage 的派发上下文（`type: skill` → Skill args；`type: agent` → Task prompt）

- **不存在 rollback**：进入续跑检测

#### 0.4 续跑检测

读取 `state_file_content.completed_stages`：

- 已完成阶段跳过，从第一个未完成阶段开始
- 按 YAML `stages` 顺序继续执行，直至全部 stage 完成或用户中断（**不因 flow_mode 提前结束本轮**）
- 若所有 stage 均已在 `completed_stages` 中，仅执行完成校验后输出摘要

### Step 1–N: 阶段执行循环

遍历 `stages`（跳过已完成阶段），对每个 stage 执行以下流程。

#### 0. 派发方式判定（每个 stage 必做，禁止跳过）

**在调用任何 Skill/Task 之前**，从当前 YAML stage 读取 `type`（**禁止**沿用上一 stage 的派发方式；**禁止**因 `stage.skill` 名称而猜测工具）：

```text
switch (stage.type):
  "skill"            → 编排器本层 Skill(stage.skill) ONLY
  "agent" | 缺失     → Task(general-purpose) ONLY（子代理 Read skills/<local_skill>/SKILL.md）
  "parallel_agents"  → 对 stage.skills[] 各启 Task(general-purpose)
```

`local_skill = stage.skill` 去掉命名空间前缀后的名字（例如 `omni-dsdd:brainstorming-sdd-bridge` → `brainstorming-sdd-bridge`）；`stage.skills[]` 与 `stage.gate.skill` 同理。

**常见误判（必须避免）**：

| stage.name | YAML `type` | ❌ 错误 | ✅ 正确 |
|------------|-------------|--------|--------|
| `tasks` | `agent` | `Skill("tasks")` / `Skill("sdd:tasks")` | `Task(general-purpose, description="SDD stage: tasks", ...)` |
| `analyze` | `agent` | `Skill("analyze")` | `Task(general-purpose, description="SDD stage: analyze", ...)` |
| `design` | `agent` | `Skill("design")` | `Task(general-purpose, ...)` |
| `brainstorming` | `skill` | `Task(general-purpose, ...)` | `Skill("brainstorming", ...)` |

**硬性规则**：

- `stage.name` 与 `stage.skill` 同名（如 `tasks`）**仍按 `type` 派发**；`type: agent` 时 **never** 编排器层 `Skill(stage.skill)`
- `silent: true` **只**减少用户可见 chatter，**不改变**派发方式；`tasks`/`analyze`/`implement` 等 `silent` stage 仍须 Task（当 `type: agent`）
- 上一 stage 为 `type: skill`（如 brainstorming）后，下一 stage **必须**重新读 YAML `type`；

✅ **Checkpoint 派发判定**: 已读取 `stage.name` + `stage.type` + `stage.skill`，工具选择已与 YAML 一致

#### 1. 环境加载

若 `stage.requires_env == true`：

```bash
source "$FEATURE_DIR/.runs/env.sh"
```

并在 Task prompt 中注入 `FEATURE_DIR`、`BRANCH_NAME`。

#### 2. 上游产物继承

若 stage 有 `inherit_from_previous`（如 specify 继承 reverse 的 `BRANCH_NAME`/`FEATURE_DIR`）：

- 读取上一 stage 输出变量，覆盖 preset 中的同名参数
- 若检测到不一致，**中止并报错**

#### 3. Stage 派发

**再次确认**：本小节执行方式 **必须**与 §Step 1–N/0 判定一致；若与 YAML `type` 冲突，以 YAML 为准并修正调用。

根据 `stage.type` 选择派发方式（**不可混用**）：

**`type: skill`**（编排器直接触发）：

1. Read `${CLAUDE_PLUGIN_ROOT}/skills/<local_skill>/SKILL.md`（若尚未加载）
2. 使用 **Skill** 工具：`Skill("<stage.skill>", args="<上下文>")`
3. prompt/args 注入：`FEATURE_DIR`、`BRANCH_NAME`、`$ARGUMENTS`；若有 `pass_context` / `args_template` 同 agent 规则
4. **必须同步等待** skill 完成（含人机交互环，如 brainstorming 用户批准）
5. **禁止**对该 stage 再包 `Task(general-purpose)`
7. **Skill 阶段交还（handoff）** — 用户批准等人机环节结束后**立即**：
   1. 执行 §10 `workflow-update-state.sh --mark-complete <stage.complete_marker>`
   2. **同轮、不等待用户**继续 §Step 1–N/0，对 YAML 下一 stage 派发
   3. **禁止**只打印「阶段结束，返回 orchestrator」后停表；编排器即 orchestrator，交还 = 继续循环，不是结束回复

**`type: agent`**（Task 隔离执行 — **含 `tasks`、`analyze`、`design`、`specify`、`implement` 等全部 SDD 阶段 skill**）：

```md
Task(subagent_type="general-purpose", description="SDD stage: <stage.name>", prompt=stage_context)
```

- **禁止**编排器本层 `Skill("<stage.skill>")`（即使用户/系统可见名为 `Skill(sdd:tasks)` 也属违规）

- prompt **必须**包含：Read `${CLAUDE_PLUGIN_ROOT}/skills/<local_skill>/SKILL.md` 并完整执行
- prompt 注入：`FEATURE_DIR`、`BRANCH_NAME`、`ARGUMENTS`，以及 stage 配置的上下文变量
- 若 stage 有 `prompt_inject`：
  - 值为 `clarify-auto-decision` 时：Read `${CLAUDE_PLUGIN_ROOT}/skills/workflow-orchestrator/references/clarify-auto-decision-prompt.md`，将全文追加到 Task prompt（standard/deep 的 clarify 阶段；express 无 clarify）
  - 值为其他非空字符串时：原样追加到 Task prompt
- 若 stage 有 `args_template`，按模板拼接参数（替换 `$ARGUMENTS` 等变量）
- 若 `pass_context` 包含 `PRESET_SPECIFY_ARGS`，追加 `$PRESET_SPECIFY_ARGS`
- 若 `pass_context` 包含 `ENABLE_E2E` 且 `$ENABLE_E2E == "true"`，追加 `--e2e`
- **必须同步等待** Task 返回

##### `local-sandbox-fix` 派发硬约束

当 `stage.name == local-sandbox-fix` 时，Task prompt **必须**追加以下硬约束，且不得注入与其冲突的测试命令：

- 只允许通过 `local-sandbox-fix` harness 执行：先跑 `local-sandbox-fix-init-harness.sh`，再 `source "${FEATURE_DIR}/.runs/local-sandbox-fix/env.sh"`，再跑 `local-sandbox-fix-gate.sh --step 0-init --record`。
- 若 gate `0-init` 返回 `next_action=skip` 或写出 `skipped=true` 的 success status，必须立即结束本 stage；**禁止**再执行 `pytest`、`go test`、`npm test`、`tox`、`local-ci` 或任何手工 CI/test 命令；**禁止**修改业务代码或测试代码。
- 只有 gate `0-init` 明确要求继续主循环时，才可按 `local-sandbox-fix` SKILL.md 的 pending gate 顺序执行后续步骤。
- 子代理返回后，编排器本层必须执行 YAML 声明的 `local-sandbox-fix-workflow-gate.sh --check complete`；该 gate 通过前禁止 `workflow-update-state.sh --mark-complete local-sandbox-fix`。

**`type: parallel_agents`**（并行 Task）：

- 对 `stage.skills` 中每个 skill 各启动一个 `Task(general-purpose)`，prompt 要求按 `<local_skill>` Read 对应 SKILL.md
- 等待所有完成
- 若 `critical_fix_and_rereview: true` 且审查发现 CRITICAL 问题：
  - 自动修复后重新审查

#### 4. Gate 检查

若 stage 有 `gate`：

```bash
GATE_SKILL="${stage.gate.skill}"   # 如 omni-dsdd:specify、omni-dsdd:design
GATE_LOCAL_SKILL="${GATE_SKILL##*:}"
GATE_SCRIPT="${CLAUDE_PLUGIN_ROOT}/skills/${GATE_LOCAL_SKILL}/scripts/bash/${stage.gate.script}"
GATE_CMD=(bash "$GATE_SCRIPT" --feature-dir "$FEATURE_DIR")
# 分步 harness（*-gate.sh）必须带 --step；阶段结束全量校验用 verify-*-artifacts.sh 或显式 step: all
if [[ -n "${stage.gate.check:-}" ]]; then
  GATE_CMD+=(--check "${stage.gate.check}")
elif [[ -n "${stage.gate.step:-}" ]]; then
  GATE_CMD+=(--step "${stage.gate.step}")
elif [[ "${stage.gate.script}" == *-gate.sh ]]; then
  GATE_CMD+=(--step all)
fi
"${GATE_CMD[@]}"
```

stage gate 是 `workflow-update-state.sh --mark-complete <stage>` 之前的硬约束；gate 未执行或 exit 非 0 时禁止标记完成。`local-sandbox-fix` 不允许把 gate 交给子代理口头说明，必须由编排器本层执行。

| `gate.script` 类型 | YAML 写法 | 编排器行为 |
| -------------------- | ----------- | ------------ |
| `verify-*-artifacts.sh` | `skill` + `script` | 仅 `--feature-dir`（脚本内已 `--step all`） |
| `*-workflow-gate.sh` 检查项 | `skill` + `script` + `check: complete` | 追加 `--check complete` |
| `*-gate.sh` 全量 | `skill` + `script` + `step: all` | 追加 `--step all` |
| `*-gate.sh` 单步 | `skill` + `script` + `step: "6"` | 追加 `--step 6` |

**确定性分数门禁（必须执行，禁止用 LLM 自行读 eval 判断）**：

> 日志实拍：specify 91/100、design 80.4/100 均低于阈值，orchestrator 却因 `gate exit 0`（结构门禁）
> 误判通过。`verify-*-artifacts.sh` 仅校验文件存在，**不查分数**。故分数校验必须用下面的脚本。

```bash
# 结构门禁通过后，立即跑确定性分数门禁
bash "${CLAUDE_PLUGIN_ROOT}/scripts/bash/check-eval-score.sh" \
  --feature-dir "$FEATURE_DIR" \
  --stage "${stage.name}" \
  --min-score "${stage.gate.min_score}"
# exit 0 = 通过；exit 1 = 分数未达标或 status=fail
```

- `check-eval-score.sh` exit 0：通过，进入下一阶段
- `check-eval-score.sh` exit 1 且 `stage.gate.blocking == true`：进入 auto_converge（如有）或停止报告
- `check-eval-score.sh` exit 1 且 `stage.gate.blocking == false`（如 design）：记录警告后继续，但在摘要中显式标注"分数未达标"
- eval 文件缺失（exit 1, `EVAL_FILE_NOT_FOUND`）且 `blocking == true`：**视为未通过**，禁止"没 eval 就算通过"

> 🔒 **机械强制（非 LLM，不可跳过）**：`check-eval-score.sh` 会落盘 `.runs/evaluations/.gate-verdict-<stage>.json`（带 `source:"check-eval-score"` 签名）；
> `workflow-update-state.sh --mark-complete <blocking阶段>` 会调守卫 `workflow_gate_guard.py` 校验该 verdict（含来源签名），
> **未通过则拒绝标记完成（exit 1）**——即使编排器想继续，state 也推不进、下一阶段无法基于 `completed_stages` 启动。
> **门禁为硬约束，任何情况下不可跳过**：`--ignore-gate-guard` 已禁用（传入即 exit 2 拒绝）；手写/伪造 verdict 会被守卫的来源签名校验拒绝。
> 若 check-eval-score 或 eval 异常，必须修复后重跑该阶段直至 verdict 真实 PASS，严禁任何形式绕过。

#### 5. 自动收敛（auto_converge）—— 机械重试，禁止 LLM 自行决定停止

> 日志实拍：LLM 在第 2 次重试就放弃（未到 max_retries）。故"何时停止重试"**改由脚本
> `workflow-converge.sh` 按 max_retries 机械判定**，编排器只执行其判决，**禁止自行决定"放弃/停止"**。

**阶段开始时**先重置计数器（每个 blocking 阶段入口调一次）：

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/bash/workflow-converge.sh" \
  --feature-dir "$FEATURE_DIR" --flow-mode "$FLOW_MODE" --stage "${stage.name}" --reset
```

**每次 `check-eval-score.sh` 跑完后**，调控制器并**按 exit code 机械行事（不得偏离）**：

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/bash/workflow-converge.sh" \
  --feature-dir "$FEATURE_DIR" --flow-mode "$FLOW_MODE" --stage "${stage.name}"
```

| exit code | 含义 | 编排器必须执行的动作 |
|-----------|------|----------------------|
| `0` CONVERGED | verdict PASS | 调 `workflow-update-state.sh --mark-complete`（守卫验证 verdict PASS 放行），进入下一阶段 |
| `1` RETRY N/max | FAIL 且未到上限 | **必须**再次 `Task(general-purpose)` 增量派发该阶段：注入 eval 扣分点（读 `${eval_file}` 的未达标项）、**Edit 现有制品**（禁止推翻重写）；重跑 `check-eval-score.sh`；再调本控制器——**循环**。**禁止停止、禁止 mark-complete** |
| `2` EXHAUSTED | FAIL 且已达 max_retries | 停止向用户报告（附 eval 扣分点 + 已重试次数）；**不 mark-complete、不进下一阶段** |
| `3` NO_VERDICT | 未跑门禁 | 先跑 `check-eval-score.sh` |

> 双重机械保障：① `workflow-update-state.sh` 守卫拒绝 FAIL 的 mark-complete（推不过）；
> ② `workflow-converge.sh` 按计数强制 RETRY 至 max_retries。LLM 既不能提前推进，也不能在第 2 次放弃——
> 必须重试满 `max_retries` 次仍不过才停。所有 blocking 分数门禁阶段（specify / clarify / design）均适用。

#### 6. 通用 Eval 检查（非 gate 场景）

若 stage 有 `eval_file` 但无 `gate`（如 clarify、design）：

**同样必须用确定性脚本校验，禁止 LLM 自行读 eval**：

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/bash/check-eval-score.sh" \
  --feature-dir "$FEATURE_DIR" \
  --stage "${stage.name}" \
  --min-score "${stage.min_score}"
```

- `check-eval-score.sh` exit 0：通过
- exit 1 且 `blocking: true`（如 clarify）：进入 auto_converge 或停止
- exit 1 且 `blocking: false`（如 design）：记录"分数未达标"警告后继续（与原语义一致，但警告不再被吞掉）

#### 7. Post-script 处理

若 stage 有 `post_script`：

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/bash/${stage.post_script}" \
  --feature-dir "$FEATURE_DIR"
```

若 stage 配置了 `post_script_exit_map`（可选）：

- 退出码映射到目标 stage → 同轮立即执行该 stage
- **默认无 exit_map**：post_script 仅落盘/门禁，成功后**继续** YAML 下一 stage（如 analyze 的 `workflow-post-analyze.sh` 后继续 implement → review）

#### 8. 任务勾选

若 `stage.checklist == true`：

- 按 `tasks.md` 中的任务顺序和依赖关系执行
- 每完成一个任务，将其从 `- [ ]` 标记为 `- [X]`
- checklist 阶段不得自动调用 `local-ci` 或手工测试命令；测试/CI 必须来自当前 stage 的显式 gate，或后续 `local-sandbox-fix` harness。

#### 9. 自动修复（auto_fix_unlimited）

若 `stage.auto_fix_unlimited == true`：

- 发现不一致或质量问题时，由技能直接改制品并迭代修复
- **不设修复轮数上限**，自动修复至收敛
- 若仍有残留问题，技能打印完整问题列表后正常结束
- 编排器**不得**因此停表或判定阶段失败

#### 10. 状态更新

若 `stage.no_state_write != true`：

先从 YAML stage 列表计算当前 stage 的下一个 stage 名，记为 `NEXT_STAGE`；若当前 stage 是最后一个 stage，则 `NEXT_STAGE="${stage.complete_marker}"`（最终完成另由 Final gate 置为 `workflow-complete`）。**不得由某个 skill 硬编码下一阶段**，例如 expert 中 `tasks` 的下一阶段必须来自 YAML，为 `implement`，不是 `analyze`。

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/bash/workflow-update-state.sh" \
  --feature-dir "$FEATURE_DIR" \
  --flow-mode "${FLOW_MODE}" \
  --current-stage "${NEXT_STAGE}" \
  --mark-complete "${stage.complete_marker}"
```

### Final: 完成校验与摘要

**所有 stage 完成后**（含最后一个 review stage）：

```bash
source "$FEATURE_DIR/.runs/env.sh"
bash "${CLAUDE_PLUGIN_ROOT}/scripts/bash/workflow-gate.sh" \
  --feature-dir "$FEATURE_DIR" --check workflow-complete --record
# gate 通过后将 current_stage 置为终态 workflow-complete，避免停留在最后一个 stage 误读为"未完成"
bash "${CLAUDE_PLUGIN_ROOT}/scripts/bash/workflow-update-state.sh" \
  --feature-dir "$FEATURE_DIR" --current-stage workflow-complete
bash "${CLAUDE_PLUGIN_ROOT}/scripts/bash/workflow-update-progress.sh" \
  --feature-dir "$FEATURE_DIR" --step "workflow 完成"
```

gate 通过后，**再** Read `${CLAUDE_PLUGIN_ROOT}/skills/workflow-orchestrator/references/completion-summary.md`，按 `$FLOW_MODE` 输出用户可见摘要。  
Step 0–N 执行过程中**禁止** Read 该文件（渐进加载，避免过程中消耗 token）。

## 状态管理

- 真值路径：`source "$FEATURE_DIR/.runs/env.sh"`
- **禁止** 用 `check-prerequisites.sh` 推断目录
- **禁止** Write 手写 `.omnispec-state.json`
- 每步完成后执行 `workflow-update-state.sh`（**禁止** LLM Edit JSON）

## 脚本依赖

| 脚本 | 路径前缀 | 用途 |
| ------ | ---------- | ------ |
| `workflow-update-state.sh` | `scripts/bash/` | 更新 `.omnispec-state.json` |
| `workflow-gate.sh` | `scripts/bash/` | 阶段门禁检查 |
| `workflow-update-progress.sh` | `scripts/bash/` | 进度 Markdown |
| `workflow-post-analyze.sh` | `scripts/bash/` | analyze 收尾落盘与 pre-implement gate |
| `verify-specify-artifacts.sh` | `skills/specify/scripts/bash/` | 编排层 specify 全量 gate（YAML `gate.script`） |
| `omnispec_state.py` | `scripts/python/` | 状态文件核心操作 |
