---
name: tasks
description: 基于可用的设计文档为功能特性生成可执行的、按依赖关系排序的 tasks.md。在用户要求生成任务列表、制定实施计划、从 spec/design 产出 tasks 时使用。
argument-hint: 功能目录或任务生成上下文
context: fork
agent: general-purpose
---

# 生成 tasks.md

## 用户输入

```text
$ARGUMENTS
```

在继续之前，**必须**考虑用户输入（若不空）。

---

## 环境初始化

本技能**所有**路径解析与脚本调用均依赖以下变量。后续步骤不得用裸 `scripts/...`、`.omni-infra/...` 或 Git 仓库根推断路径。

| 变量 | 含义 | 用途 |
|------|------|------|
| `CLAUDE_PLUGIN_ROOT` | Omni 插件安装根目录 | 定位 `check-prerequisites` 等插件脚本 |
| `CLAUDE_WORKING_DIR` | 用户当前工作区目录（可为 Git 仓库子目录） | 定位 `.omni-infra/`、前置检查 cwd |
| `FEATURE_DIR` | 当前特性目录（绝对路径） | 优先 `source env.sh` 或 `paths.json` |
| `TASKS` | 任务清单绝对路径 | `env.sh` / `paths.json` 的 `tasks_file` |
| `FEATURE_SPEC` / `IMPL_DESIGN` | 规范与设计绝对路径 | `env.sh`（design init 写入） |

### 工作区路径约定

**真值顺序**：`source "${FEATURE_DIR}/.runs/env.sh"` → `${FEATURE_DIR}/.runs/paths.json` → `check-prerequisites --json`（均为绝对路径）。

| 符号 | 展开路径 |
|------|----------|
| 任务清单（输出） | `${TASKS}` 或 `${FEATURE_DIR}/tasks.md` |
| 规范 | `${FEATURE_SPEC}` 或 `${FEATURE_DIR}/spec.md` |
| 设计 | `${IMPL_DESIGN}` 或 `${FEATURE_DIR}/design.md` |
| 数据模型 | `${FEATURE_DIR}/data-model.md` |
| 接口契约 | `${FEATURE_DIR}/contracts/` |
| 研究 | `${FEATURE_DIR}/research.md` |
| Quickstart | `${FEATURE_DIR}/quickstart.md` |
| E2E 用例（可选） | `${FEATURE_DIR}/e2e-test.md` |
| 上下文 | `${FEATURE_DIR}/context.md` |
| 任务模板 | `${CLAUDE_WORKING_DIR}/.omni-infra/templates/tasks-template.md` |
| Harness 环境（若存在） | `${FEATURE_DIR}/.runs/env.sh` |

### Step 0.1 检查变量是否已存在

```bash
test -n "${CLAUDE_PLUGIN_ROOT:-}" && test -d "${CLAUDE_PLUGIN_ROOT}"
test -n "${CLAUDE_WORKING_DIR:-}" && test -d "${CLAUDE_WORKING_DIR}"
```

两项均通过 → 若已 `source` 过 `${FEATURE_DIR}/.runs/env.sh` 且 `FEATURE_DIR` 非空，可进入步骤 1；否则由步骤 1 解析。  
任一项失败 → 执行 Step 0.2。

### Step 0.2 补全缺失变量（仅 Agent 层执行一次）

**`CLAUDE_PLUGIN_ROOT`**

1. 若 Claude Code 已注入且目录存在：沿用。
2. 若仍缺失，按顺序降级（须验证 `${路径}/skills/tasks/SKILL.md` 存在）：
   - Skill 加载上下文中的插件安装根；
   - 在 `${CLAUDE_WORKING_DIR}` 或其上级查找含 `.claude-plugin/plugin.json` 的目录；
3. `export CLAUDE_PLUGIN_ROOT="<绝对路径>"`
4. 失败 → 终止并提示配置插件。

**`CLAUDE_WORKING_DIR`**

1. 若已注入且目录存在：沿用。
2. 若缺失：`export CLAUDE_WORKING_DIR="$(pwd)"`（**不用** `git rev-parse --show-toplevel`）
3. 失败 → 终止。

### Step 0.3 校验（必须通过）

```bash
test -f "${CLAUDE_PLUGIN_ROOT}/scripts/bash/check-prerequisites.sh"
test -d "${CLAUDE_WORKING_DIR}"
```

若上游 `design` 已写入 `${FEATURE_DIR}/.runs/env.sh`，**推荐**先执行：

```bash
source "${FEATURE_DIR}/.runs/env.sh"
```

✅ Checkpoint: `CLAUDE_PLUGIN_ROOT=...`, `CLAUDE_WORKING_DIR=...`

### 路径拼接约定

- 插件脚本：`${CLAUDE_PLUGIN_ROOT}/scripts/bash/...`、`${CLAUDE_PLUGIN_ROOT}/scripts/powershell/...`
- 前置检查须在 **`CLAUDE_WORKING_DIR`** 下执行
- 任务规则参考：`${CLAUDE_PLUGIN_ROOT}/skills/tasks/references/task-rules.md`
- **禁止**用 `git rev-parse --show-toplevel` 替代 `CLAUDE_WORKING_DIR`
- **禁止**仅用当前 Git 分支或裸 `check-prerequisites` 推断 `FEATURE_DIR`（须以 `.runs/paths.json` / `env.sh` / JSON 的 `FEATURE_DIR` 为准，与 workflow 一致）

---

## 概述

在 **`design` 已完成** 的前提下，读取 `${FEATURE_DIR}` 下 spec/design 及 design 附属制品，生成可执行的 `${FEATURE_DIR}/tasks.md`。本技能无独立 Harness 脚本，路径与前置检查遵循上文环境初始化约定。

## 依赖链声明

- Step 3 的输出（任务列表 + 修改点检查结果）= Step 4 的输入
- Step 4 的输出（`${FEATURE_DIR}/tasks.md` 初稿）= Step 5 报告的输入
- 禁止在 Step 5 中重新搜索或重新生成内容，必须引用 Step 3/4 的实际产出
- 写入 `tasks.md` 前进行数字一致性交叉验证

### 0. skill 执行开始时间打点记录

开始执行步骤之前，记录本 skill 的执行时间到 `start_time` 字段：

- 判断当前操作系统（Windows / Linux）
- windows: `Get-Date -Format "yyyy-MM-dd HH:mm:ss"`
- linux: `date +"%Y-%m-%d %H:%M:%S"`
- 将时间记录到 `start_time`

### 1. 设置

- 判断当前操作系统（Windows / Linux）
- **解析路径（按优先级，禁止用 Git 分支猜目录）**：
  1. **首选**：`source "${FEATURE_DIR}/.runs/env.sh"`（须含绝对路径的 `FEATURE_DIR`、`TASKS`、`FEATURE_SPEC`、`IMPL_DESIGN`）
  2. 否则读取 `${FEATURE_DIR}/.runs/paths.json` 的 `feature_dir`、`tasks_file`、`spec_file`、`design_file`
  3. 若仍未知：在 **`CLAUDE_WORKING_DIR`** 下运行前置检查（校验 `design.md` 已存在，**不要求** `tasks.md`）：
     - Windows: `pwsh "${CLAUDE_PLUGIN_ROOT}/scripts/powershell/check-prerequisites.ps1" --json --working-dir "${CLAUDE_WORKING_DIR}" --plugin-root "${CLAUDE_PLUGIN_ROOT}"`
     - Linux: `bash "${CLAUDE_PLUGIN_ROOT}/scripts/bash/check-prerequisites.sh" --json --working-dir "${CLAUDE_WORKING_DIR}" --plugin-root "${CLAUDE_PLUGIN_ROOT}"`
  4. 从 JSON 解析 **FEATURE_DIR**、**TASKS**、**IMPL_DESIGN**、**FEATURE_SPEC**、**AVAILABLE_DOCS**（均为绝对路径）
- **Write 目标**：仅写入 `${TASKS}`（勿写到 cwd 或仓库根下裸 `tasks.md`）
- 参数值中含单引号时用转义（如 `'I'\''m Groot'`）或双引号。
- **强制校验**：`FEATURE_DIR` 必须位于 `${CLAUDE_WORKING_DIR}/changes/` 下；若不在，重走 `design` 或 `create-branch`，勿使用 Git 仓库根下错误的 `changes/` 路径。

### 2. 加载设计文档（自 `${FEATURE_DIR}`）

- **必需**: `${FEATURE_DIR}/design.md`（技术栈、库、结构）, `${FEATURE_DIR}/spec.md`（带优先级的场景）
- **design 阶段产物（必需）**: `${FEATURE_DIR}/data-model.md`, `${FEATURE_DIR}/contracts/`, `${FEATURE_DIR}/research.md`, `${FEATURE_DIR}/quickstart.md`
- **可选**: `${FEATURE_DIR}/e2e-test.md`（仅启用 E2E 时）
- **可选上下文**: `${FEATURE_DIR}/context.md`
- 按实际存在的文档生成任务。

### 3. 执行任务生成工作流

- 从 `${IMPL_DESIGN}` 提取技术栈、库、项目结构
- 从 `${FEATURE_SPEC}` 提取带优先级的场景（P1、P2、P3…）
- 若存在 `${FEATURE_DIR}/data-model.md`：提取实体并映射到场景
- 若存在 `${FEATURE_DIR}/contracts/`：将端点映射到场景
- 若存在 `${FEATURE_DIR}/research.md`：提取影响任务设置的决策
- 章程（若任务需对齐 MUST/SHOULD）：`${CLAUDE_WORKING_DIR}/.omni-infra/memory/constitution.md`
- **按场景生成TDD 任务（强制）**：加载 skill `omni-dsdd:tdd-workflow`，每个场景**必须**按 RED → GREEN → REFACTOR 循环生成配对的测试-实现任务。测试任务在实现任务之前，测试与实现必须配对，不可只生成其中之一。具体任务格式与模板见 [task-rules.md](references/task-rules.md)。覆盖率目标遵循 `omni-dsdd:tdd-workflow` 中定义的阈值。
- 生成场景完成顺序的依赖关系图
- 为每个场景给出可并行执行示例
- 验证完整性：每个场景具备所需任务、可独立测试
- **修改点严格检查（强制）**：基于 design/spec/context 提取修改点并逐条校验：
  1. 是否已经支持（已有实现可复用）
  2. 是否遵循利旧原则（复用既有架构与代码实现）
  3. 是否遵循最小化原则（仅生成必要改动任务，避免扩散）

**E2E 测试策略**:

- **TDD 模式**（默认）:
  - 为每个场景生成测试任务
  - 测试任务在实现任务之前
  - 遵循红-绿-重构循环
- **非 TDD 模式**:
  - 测试任务在实现任务之后
  - 关注核心功能的单元测试和集成测试
  - 不强制要求测试先行

### 4. 生成 tasks.md

使用 `${CLAUDE_WORKING_DIR}/.omni-infra/templates/tasks-template.md` 作为结构，**Write** 到 **`${TASKS}`**，填充：

- `${IMPL_DESIGN}` 中的功能名称
- **阶段 1**：设置（项目初始化）
- **阶段 2**：基础任务（所有场景的阻塞先决条件）
- **阶段 3+**：按 `${FEATURE_SPEC}` 优先级顺序，每个场景一个阶段
  - 每阶段含：场景目标、TDD 循环（RED/GREEN/REFACTOR）、独立测试标准、测试（若请求）、实现任务
  - 每任务带清晰 [Scenario] 标签（S1、S2、S3…）
  - 场景内可并行任务标 [P]
  - 每场景阶段后检查点
- **最终阶段**：完善、覆盖率验证（遵循 `omni-dsdd:tdd-workflow` 覆盖率阈值）与横切关注点
- 按执行顺序编号（T001、T002…）、每任务带清晰文件路径
- 依赖关系部分、每场景并行执行示例、实现策略（MVP 优先、增量交付）
- 对每个场景增加「修改点检查任务」（可为任务组或检查项），至少包含：
  - `[ ] [Scenario] 校验修改点支持状态（已支持/部分支持/不支持）`
  - `[ ] [Scenario] 校验利旧实现路径（模块/接口/函数）`
  - `[ ] [Scenario] 校验最小化改动边界（文件与函数范围）`

### 5. 报告

输出生成的 **`${TASKS}`** 路径与摘要：总任务数、每场景任务数、并行机会、每场景独立测试标准、建议 MVP 范围（通常为场景 1）。
同时输出「修改点严格检查摘要」：修改点总数、已支持数量、利旧通过数量、最小化通过数量、需澄清数量。

任务生成上下文: $ARGUMENTS

`tasks.md` 应立即可执行——每项任务足够具体，使 LLM 无需额外上下文即可完成。
若「修改点严格检查」未通过且无合理说明，不得输出为最终可执行版本，必须先回填检查任务并收敛范围。

### 6. 记录本 skill 的运行日志信息

- 若存在 `${FEATURE_DIR}/.runs/env.sh`，执行前：`source "${FEATURE_DIR}/.runs/env.sh"`
- 执行 `omni-dsdd:runlog-record` skill，将 `start_time` 作为参数传入（如 `/omni-dsdd:runlog-record "2026-05-15 10:30:00"`）

### 7. workflow 状态交还

- 本 skill **不得**固定把 `current_stage` 写成 `analyze`。下一阶段必须由 `workflows/${FLOW_MODE}.yaml` 决定：
  - `express` / `standard` / `deep`: `tasks -> analyze`
  - `expert`: `tasks -> implement`
- 若由 `workflow-orchestrator` 调度，本 skill 只需完成 `tasks.md`、`requirements-content.md`、`scenarios-content.md` 与 tasks gate；状态写入由编排器统一执行。
- 若必须在本 skill 内调用 `workflow-update-state.sh`，应先读取 `${FEATURE_DIR}/.runs/.omnispec-state.json` 或 `paths.json` 中的 `flow_mode`，expert 使用 `--current-stage implement --mark-complete tasks`，其他流程使用 `--current-stage analyze --mark-complete tasks`。

## 任务格式与规则

生成任务时**严格遵循** [task-rules.md](references/task-rules.md) 中的：检查清单格式（TaskID、[P]、[Scenario]、文件路径）、任务组织（来自 spec/合约/数据模型/基础设施）、阶段结构。每个场景**强制**生成 TDD 测试任务（RED → GREEN → REFACTOR），测试任务在实现任务之前。

## 参考

| 项 | 路径 |
|----|------|
| 前置检查（bash） | `${CLAUDE_PLUGIN_ROOT}/scripts/bash/check-prerequisites.sh` |
| 前置检查（pwsh） | `${CLAUDE_PLUGIN_ROOT}/scripts/powershell/check-prerequisites.ps1` |
| 任务规则 | `${CLAUDE_PLUGIN_ROOT}/skills/tasks/references/task-rules.md` |
| 本技能 | `${CLAUDE_PLUGIN_ROOT}/skills/tasks/SKILL.md` |
