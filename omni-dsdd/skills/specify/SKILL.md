---
name: specify
argument-hint: [功能描述文本] [--feature-dir <dir>] [--branch-name <name>] [--e2e]
description: 从自然语言功能描述生成功能规范文档（SDD）。当用户输入 /specify 或提供功能需求描述时自动触发。执行上下文收集、需求分析、场景提取，生成规范文件。适用于需要从需求生成规范，建立功能说明等场景。触发关键词：/specify、规范生成、功能描述、spec.md、SDD。
context: fork
agent: general-purpose
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, TaskCreate, TaskList, TaskUpdate, TaskGet, TaskOutput, Skill, TodoWrite
when_to_use: 用户执行 /specify 或要求从需求生成 spec.md / SDD 功能规范时。
---
# specify

## 行为准则

以下规则在整个会话期间有效，不因对话长度而放松：

1. ❗ 每个步骤必须按顺序执行，不得跳过或截断执行
2. ❗ 步骤 1 预解析结果仅用于确定传入 `omni-dsdd:create-branch` 的参数；**后续步骤唯一基准**为 `omni-dsdd:create-branch` 返回的 `BRANCH_NAME`、`FEATURE_DIR`、`SPEC_FILE`；**不得跳过** `omni-dsdd:create-branch`
3. ❗ 每执行完一个步骤，必须立即将对应 Todo 项标记为已完成，不得在全部结束后一次性补勾选
4. ❗ **产物落盘优先于对话输出** — 子技能返回的结构化内容必须用 **Write/Edit** 写入约定路径；**禁止**仅在回复中展示内容却未落盘；**禁止**在产物文件缺失时将对应 Todo 标为已完成
5. ❗ **Harness 门禁优先于 Todo 勾选** — 每步须运行 `specify-gate` 且 `gate_exit=0` 后方可勾选 Todo；**禁止**未跑门禁即标完成

---

## 环境初始化

本技能**所有**路径拼接与脚本调用，均依赖以下两个变量。后续步骤不得绕过它们自行推断路径。

| 变量 | 含义 | 用途 |
|------|------|------|
| `CLAUDE_PLUGIN_ROOT` | Omni 插件安装根目录 | 定位本技能脚本、`check-prerequisites`、插件内模板契约 |
| `CLAUDE_WORKING_DIR` | 用户当前工作区目录（可为 Git 仓库子目录） | 定位 `changes/`、`.omni-infra/`、Harness 落盘 |

### 工作区路径约定（全文统一使用）

| 符号 | 展开路径 |
|------|----------|
| 特性目录 | `${FEATURE_DIR}`（来自 create-branch，应位于 `${CLAUDE_WORKING_DIR}/changes/...`） |
| 规范文件 | `${SPEC_FILE}` 或 `${FEATURE_DIR}/spec.md` |
| 上下文 | `${FEATURE_DIR}/context.md` |
| 项目模板 | `${CLAUDE_WORKING_DIR}/.omni-infra/templates/...` |
| 项目章程 | `${CLAUDE_WORKING_DIR}/.omni-infra/memory/constitution.md` |
| Harness 状态 | `${FEATURE_DIR}/.runs/...` |
| 插件脚本（Linux/bash） | `${CLAUDE_PLUGIN_ROOT}/skills/specify/scripts/bash/...` |
| 插件脚本（Windows/pwsh） | `${CLAUDE_PLUGIN_ROOT}/skills/specify/scripts/powershell/...` |
| Harness 核心（Python） | `${CLAUDE_PLUGIN_ROOT}/skills/specify/scripts/python/specify_harness.py` |
| 插件级前置检查 | `${CLAUDE_PLUGIN_ROOT}/scripts/bash/check-prerequisites.sh` |

### Step 0.1 检查变量是否已存在

```bash
test -n "${CLAUDE_PLUGIN_ROOT:-}" && test -d "${CLAUDE_PLUGIN_ROOT}"
test -n "${CLAUDE_WORKING_DIR:-}" && test -d "${CLAUDE_WORKING_DIR}"
```

两项均通过 → 进入「执行流程」步骤 0。  
任一项失败 → 执行 Step 0.2。

### Step 0.2 补全缺失变量（仅 Agent 层执行一次）

**`CLAUDE_PLUGIN_ROOT`**

1. 若 Claude Code 已注入且目录存在：沿用。
2. 若仍缺失，按顺序降级（须验证 `${路径}/skills/specify/SKILL.md` 存在）：
   - Skill 加载上下文中的插件安装根；
   - 在 `${CLAUDE_WORKING_DIR}` 或其上级查找含 `.claude-plugin/plugin.json` 的目录；
3. `export CLAUDE_PLUGIN_ROOT="<绝对路径>"`
4. 失败 → 终止并提示配置插件。

**`CLAUDE_WORKING_DIR`**

1. 若已注入且目录存在：沿用。
2. 若缺失：`export CLAUDE_WORKING_DIR="$(pwd)"`（**不用** `git rev-parse --show-toplevel`，避免子目录工作区被抬到仓库根）
3. 失败 → 终止。

### Step 0.3 校验（必须通过）

```bash
test -f "${CLAUDE_PLUGIN_ROOT}/skills/specify/scripts/python/specify_harness.py"
test -f "${CLAUDE_PLUGIN_ROOT}/skills/specify/scripts/bash/specify-init-harness.sh"
test -f "${CLAUDE_PLUGIN_ROOT}/skills/specify/scripts/powershell/specify-init-harness.ps1"
test -d "${CLAUDE_WORKING_DIR}"
mkdir -p "${CLAUDE_WORKING_DIR}/changes"
```

✅ Checkpoint: `CLAUDE_PLUGIN_ROOT=...`, `CLAUDE_WORKING_DIR=...`

### 路径拼接约定

- 插件内脚本（按类型分目录）：
  - `scripts/bash/` — `specify-init-harness.sh`、`specify-gate.sh`、`specify-render-*.sh`、`specify-finalize.sh`、`verify-specify-artifacts.sh`、`specify-harness-common.sh`
  - `scripts/python/` — `specify_harness.py`、`specify_template_gate.py`
  - `scripts/powershell/` — 与 bash 同名的 `.ps1` 封装 + `Specify-HarnessCommon.ps1`
- 工作区数据：`${CLAUDE_WORKING_DIR}/changes/...`、`.omni-infra/...`
- 调用 init 封装时**必须**传入 `--plugin-root`、`--working-dir`、`--feature-dir`
- render/finalize 可从 `${FEATURE_DIR}/.runs/paths.json` 读取 `working_dir`/`plugin_root`；未 init 时须显式传参
- **禁止**在业务脚本内用 `pwd`、`git rev-parse`、`__file__.parents` 推断插件根或工作区根

### 平台脚本选择

| 平台 | 初始化 | 门禁 | 渲染 / 收尾 |
|------|--------|------|-------------|
| Linux / macOS / Git Bash | `scripts/bash/specify-init-harness.sh` | `scripts/bash/specify-gate.sh` | `scripts/bash/specify-render-*.sh`、`specify-finalize.sh` |
| Windows (pwsh) | `scripts/powershell/specify-init-harness.ps1` | `scripts/powershell/specify-gate.ps1` | `scripts/powershell/specify-render-*.ps1`、`specify-finalize.ps1` |

断点续跑、高级子命令可直接调用 `scripts/python/specify_harness.py`（参数与 bash 封装一致）。

---

## 特性上下文用户指定

合并规则与 **`sdd` 步骤 1.5** 一致（`有传参 → 传参 > 无传参 → export > 推导 > allocate`）。步骤 1 为 **直连 `/specify` 或 workflow 后的权威预解析入口**；**物理生效唯一入口**为步骤 2 `omni-dsdd:create-branch`，后续以 **`omni-dsdd:create-branch` 返回值** 为真值。

- **输入**：CLI `--feature-dir` / `--branch-name`，或 export `OMNISPEC_FEATURE_DIR`/`FEATURE_DIR`/`BRANCH_NAME`
- **预设**（`FEATURE_CONTEXT_PRESET=true`）：步骤 2 显式传 create-branch，禁止 allocate；`FEATURE_DIR` 须在 `changes/` 下
- **自动**（`false`）：步骤 2 走 allocate；步骤 3 起**只使用 create-branch 返回的路径**

示例见 `sdd` SKILL「`--feature-dir` / `--branch-name` 与 export 全局变量」一节。

---

## Harness 执行契约（必守，不含 --e2e）

**编排 / 落盘 / 校验分离**：LLM 产出 payload → **Write** 文件 → **脚本 gate** 判定 → 更新 `specify-run.json`。

### 机器可读状态

| 文件 | 用途 |
|------|------|
| `${FEATURE_DIR}/.runs/paths.json` | 唯一路径真值源（分支、目录、SPEC_FILE、DOC_DIR、DOC_SPECS_DIR 等、working_dir、plugin_root，均为绝对路径） |
| `${FEATURE_DIR}/.runs/env.sh` | `source` 后导出 `FEATURE_DIR`、`CLAUDE_WORKING_DIR`、`CLAUDE_PLUGIN_ROOT`、`DOC_DIR`、`KNOWLEDGE_DIR` 等 |
| `${FEATURE_DIR}/.runs/specify-run.json` | 分步门禁结果、断点续跑 |
| `${FEATURE_DIR}/.runs/.omnispec-state.json` | SDD 阶段状态（routing 读取 `completed_stages`） |
| `${FEATURE_DIR}/.runs/internal/context.payload.json` | spec-impact 结构化中间态（可选，推荐） |

### 硬性交付物与分步门禁

| SKILL 步骤 | 目标文件 | 落盘 + 门禁（`gate --step` 保持脚本既有编号） |
|------------|----------|-----------------------------------------------|
| 4 | `.runs/paths.json`、`.runs/env.sh` | `specify-init-harness.sh` → `gate --step 1 --record` |
| 6 | `context.md` | 先 Write `context.payload.json` → `specify-render-context.sh`（或按模板 Write md）→ `gate --step 3 --record`（**模板契约**：5 个 `##` 章节） |
| 7→9 | `spec.md` | **先** `specify-render-spec.sh --merge` 铺骨架 → 步骤 8 追加需求/场景 → Write/Edit → `gate --step 6 --record`（**模板契约**：章节 + REQ/SCN/EARS/GWT） |
| 11 | `checklists/requirements.md` | **先** `specify-render-checklist.sh` 从模板生成 → 填写勾选 → `gate --step 8 --record`（**模板契约**：3 个 `##` + ≥12 检查项） |
| 12 | `.runs/evaluations/eval-specify-report.yaml` | Write → `gate --step 9 --record` |
| 15 | `.runs/metrics/omni-metrics-log.json` | 追加 → `gate --step 11 --record` |
| 13 | 全部 | `verify-specify-artifacts.sh`（= `gate --step all`） |
| 16 | `.runs/.omnispec-state.json` | `specify-finalize.sh` → `gate --step 11.5 --record` |

### 统一门禁命令

**Linux / bash：**

```bash
# 初始化（步骤 4 通过后立即执行）
bash "${CLAUDE_PLUGIN_ROOT}/skills/specify/scripts/bash/specify-init-harness.sh" \
  --plugin-root "${CLAUDE_PLUGIN_ROOT}" \
  --working-dir "${CLAUDE_WORKING_DIR}" \
  --feature-dir "$FEATURE_DIR" \
  --branch-name "$BRANCH_NAME" \
  --spec-file "$SPEC_FILE" \
  --doc-dir "$DOC_DIR" \
  --start-time "$start_time"

source "$FEATURE_DIR/.runs/env.sh"

bash "${CLAUDE_PLUGIN_ROOT}/skills/specify/scripts/bash/specify-gate.sh" \
  --feature-dir "$FEATURE_DIR" --step STEP --record

bash "${CLAUDE_PLUGIN_ROOT}/skills/specify/scripts/bash/verify-specify-artifacts.sh" \
  --feature-dir "$FEATURE_DIR"

bash "${CLAUDE_PLUGIN_ROOT}/skills/specify/scripts/bash/specify-finalize.sh" \
  --feature-dir "$FEATURE_DIR" --flow-mode <flow_mode> --next-stage <next_stage>

python3 "${CLAUDE_PLUGIN_ROOT}/skills/specify/scripts/python/specify_harness.py" resume \
  --feature-dir "$FEATURE_DIR"

bash "${CLAUDE_PLUGIN_ROOT}/skills/specify/scripts/bash/specify-render-spec.sh" \
  --feature-dir "$FEATURE_DIR" --user-intent "<业务意图摘要>" --merge
bash "${CLAUDE_PLUGIN_ROOT}/skills/specify/scripts/bash/specify-render-checklist.sh" \
  --feature-dir "$FEATURE_DIR" --feature-name "<功能名>"
```

**Windows / pwsh：** 将上述 `bash .../scripts/bash/*.sh` 换为 `pwsh .../scripts/powershell/*.ps1`（参数名相同）。

### 模板契约门禁（`template-contract.json`）

**契约文件**：`${CLAUDE_PLUGIN_ROOT}/skills/specify/references/template-contract.json`（由 `specify_template_gate.py` 在 `gate` 步骤 3/6/8/9 执行）。

| 产物 | 模板来源 | 门禁校验要点 |
|------|----------|----------------|
| `context.md` | `spec-impact-analyze/templates/context-template.md` | 5 个必需 `##` 章节；占位内容过多则失败 |
| `spec.md` | `${CLAUDE_WORKING_DIR}/.omni-infra/templates/spec-template.md` + 需求/场景子技能 | `## 成功标准`、`## 与既有架构对齐`、`## 需求`、`## 场景`；元数据行；`REQ-XXX`/`SCN-XXX`/`系统 shall`/GWT；需求与场景章节最小字数 |
| `checklists/requirements.md` | `${CLAUDE_WORKING_DIR}/.omni-infra/templates/requirements-template.md` | `## 内容质量`、`## 需求完整性`、`## 功能准备就绪`；≥12 条 `- [ ]` |
| `eval-specify-report.yaml` | `omni-dsdd:eval-specify` | `report_version`/`metadata`/`evaluations`/`stage`/`overall_score` |

- `gate_exit=0`：允许勾选该步 Todo并进入下一步
- `gate_exit=1`：**不得**勾选 Todo；阅读 JSON `errors` 按模板补齐后重跑 gate（每步最多 2 次）；**禁止**在未通过 gate 时标 Todo 完成
- `gate_exit=1` 时推荐修复顺序：① `render-*` 脚本铺骨架 → ② 按 `errors` 与对应 SKILL 子技能补内容 → ③ 再 `gate --step N --record`
- 步骤 14 **完成报告**必须引用步骤 13 的 `gate_exit=0` 作为 `claim_type: structural` 的 evidence

### Checkpoint 格式（每步门禁通过后输出）

```text
✅ Checkpoint 步骤{N}: artifact={路径}, gate_exit=0, bytes={大小}, sections={M}/{M}（如适用）
```

### 子技能不写文件的契约

- `omni-dsdd:spec-impact-analyze`：返回结构 → specify 写入 `context.payload.json` 并渲染/写入 `context.md`
- `omni-dsdd:eval-specify`：只定义量规 → specify 步骤 9 必须 Write `eval-specify-report.yaml`

## 技能依赖

**调用方式**：使用 Skill 工具加载下列技能（如 `/omni-dsdd:create-branch`），须完整执行并等待返回后再继续下一步。

| 技能 | 步骤 | 必需/可选 |
|------|------|-----------|
| `omni-dsdd:create-branch` | 2 | 必需 |
| `omni-dsdd:spec-impact-analyze` | 6 | 必需 |
| `omni-dsdd:specify-requirement` | 8 | 必需 |
| `omni-dsdd:specify-scenario` | 8 | 必需 |
| `omni-dsdd:e2e-specify` | 10 | 可选（`ENABLE_E2E=true`） |
| `omni-dsdd:eval-specify` | 12 | 必需 |
| `omni-dsdd:runlog-record` | 15 | 必需 |

## 用户输入

> 下文步骤说明保留原 `/specify` 命令逻辑，不做额外拆分。

```text
$ARGUMENTS
```

在继续之前, 你**必须**考虑用户输入(如果不为空).

## 概述

用户在触发消息中 `/specify` 后输入的文本**就是** `业务意图`. 假设你始终可以在本次对话中访问它, 即使下面字面上显示 `$ARGUMENTS`. 除非用户提供了空命令, 否则不要要求用户重复.

**注意**: 此流程会自动执行上下文收集和规范生成：扫描反构文档、计算关联度、构建关联关系图、进行架构分析，生成 `context.md`，再基于上下文生成功能规范.

## 执行流程

0. 开始执行步骤之前，使用 TodoWrite 工具创建本次执行的 TodoList（用于过程可视化与完成确认）：
   - [ ] 步骤 0：记录 `start_time`
   - [ ] 步骤 1：特性上下文合并解析（传参 + 全局变量）
   - [ ] 步骤 2：加载 skill `omni-dsdd:create-branch`
   - [ ] 步骤 3：路径校验
   - [ ] 步骤 4：初始化 Harness（paths/env/run）
   - [ ] 步骤 5：获取文档目录配置
   - [ ] 步骤 6：加载 skill `omni-dsdd:spec-impact-analyze` 并写入 `context.md`
   - [ ] 步骤 7：加载上下文
   - [ ] 步骤 8：按流程生成需求/场景等内容
   - [ ] 步骤 9：写入 `SPEC_FILE`
   - [ ] 步骤 10：执行（或跳过）E2E 测试分析与设计
   - [ ] 步骤 11：执行规范质量验证
   - [ ] 步骤 12：加载 skill `omni-dsdd:eval-specify`
   - [ ] 步骤 13：运行产物完整性校验脚本
   - [ ] 步骤 14：输出完成报告
   - [ ] 步骤 15：加载 skill `omni-dsdd:runlog-record`
   - [ ] 步骤 16：同步 `.omnispec-state.json`（completed_stages）
   - **强制要求**：每步须在 **`specify-gate` 通过（`gate_exit=0`）后** 才勾选对应 Todo，不得在全部结束后一次性补勾选。

   - 创建 Todo 后立即记录 `start_time`：
     - Windows: `Get-Date -Format "yyyy-MM-dd HH:mm:ss"`
     - Linux: `date +"%Y-%m-%d %H:%M:%S"`

1. **特性上下文合并解析（传参 + 全局变量）**：
   - **必须**先执行（与 `sdd` 步骤 1.5、`routing` 参数预处理同一规则）：
     1. 从 `$ARGUMENTS` 提取 `--feature-dir` / `--branch-name`（支持 `--key=value`），记为 `$PRESET_FEATURE_DIR`、`$PRESET_BRANCH_NAME`；**未出现则保持为空，禁止填占位符或臆造值**
     2. 合并解析：**有传参以传参为准，无传参以 export 为准**；仅非空传参才追加 CLI 选项
     ```bash
     eval "$(bash "${CLAUDE_PLUGIN_ROOT}/scripts/bash/resolve-feature-context.sh" \
       --working-dir "${CLAUDE_WORKING_DIR}" \
       ${PRESET_FEATURE_DIR:+--feature-dir "$PRESET_FEATURE_DIR"} \
       ${PRESET_BRANCH_NAME:+--branch-name "$PRESET_BRANCH_NAME"} \
       --export)"
     ```
   - 从 `$ARGUMENTS` 剥离 `--feature-dir` / `--branch-name` 得 `$USER_INTENT`
   - 预解析**不创建目录**；`FEATURE_CONTEXT_PRESET=true` 时步骤 2 显式传 create-branch，禁止 allocate
   - 日志：`特性上下文预解析: FEATURE_DIR=${FEATURE_DIR:-}, BRANCH_NAME=${BRANCH_NAME:-}, FEATURE_CONTEXT_PRESET=${FEATURE_CONTEXT_PRESET:-}, PRESET_CLI=<dir:${PRESET_FEATURE_DIR:-NONE} branch:${PRESET_BRANCH_NAME:-NONE}>`

2. 加载 skill `omni-dsdd:create-branch`，为功能开发准备工作环境（**唯一物理生效点**）:

   **若 `FEATURE_CONTEXT_PRESET=true`（步骤 1 已补全）**：
   - 调用 `omni-dsdd:create-branch` 时**显式透传** `--feature-dir "${FEATURE_DIR}"` 与 `--branch-name "${BRANCH_NAME}"`
   - **禁止** `allocate`；目录已存在 → `resolve` + `git checkout`；目录不存在 → `create-new-feature` 显式创建

   **若 `FEATURE_CONTEXT_PRESET=false`**：
   - **续跑 / 外层重试**：若目录已存在 `.runs/paths.json` 或 `spec.md` 或 `.runs/branch-naming.json`，则**不得** `allocate` 新建另一目录；应先 `resolve`
   - 否则走 **`allocate` + `create-new-feature`**

   **通用约束**：
   - **强制要求**：`omni-dsdd:create-branch` 必须被完整调用并等待返回；以返回的 `BRANCH_NAME`、`FEATURE_DIR`、`SPEC_FILE` 作为后续**唯一基准**
   - 返回后 `FEATURE_DIR` 须位于 **`${CLAUDE_WORKING_DIR}/changes/`** 下，否则重走 `omni-dsdd:create-branch`
   - **禁止**在同一次 specify 内连续两次完整执行 `omni-dsdd:create-branch`（除非第一次明确失败且未创建目录）

3. **路径校验（`omni-dsdd:create-branch` 返回后立即执行）**：
   - 以步骤 2 返回的 `BRANCH_NAME`、`FEATURE_DIR` 为准（**不再**使用步骤 1 预解析值）
   - **仅校验**：`FEATURE_DIR` 位于 `${CLAUDE_WORKING_DIR}/changes/` 下
   - **`FEATURE_CONTEXT_PRESET=true`**：跳过 `001-` 序号格式、Git 分支集合比对、受保护分支等 allocate 路径门禁
   - **`FEATURE_CONTEXT_PRESET=false`**：`omni-dsdd:create-branch` / allocate 已产出合规分支名；仍仅额外确认 `changes/` 路径
   - 若 `FEATURE_DIR` 不在 `changes/` 下：重走 `omni-dsdd:create-branch`；连续失败则终止并输出中文错误

4. **初始化 Harness（步骤 2/3 通过后立即执行）**：
   - 执行 `specify-init-harness.sh`（参数见「Harness 执行契约」，**必须**含 `--plugin-root`、`--working-dir`）
   - 执行 `specify-gate.sh --feature-dir "$FEATURE_DIR" --step 1 --record`
   - `gate_exit=1` 时重试 init 最多 2 次；仍失败则终止
   - 输出 Checkpoint：`步骤4: paths.json + env.sh, gate_exit=0`
   - 后续所有步骤开始前执行：`source "$FEATURE_DIR/.runs/env.sh"`

5. **获取文档目录配置**:
   - 判断当前操作系统（Windows 或 Linux）
   - 在 **`CLAUDE_WORKING_DIR`** 下运行插件前置检查脚本获取配置：
     - Windows: `bash "${CLAUDE_PLUGIN_ROOT}/scripts/powershell/check-prerequisites.ps1" --json --paths-only` → 失败时使用默认 DOC_DIR `omni-doc` 继续
     - Linux: `(cd "${CLAUDE_WORKING_DIR}" && bash "${CLAUDE_PLUGIN_ROOT}/scripts/bash/check-prerequisites.sh" --json --paths-only)` → 失败时使用默认 DOC_DIR `omni-doc` 继续
   - 解析 JSON 输出获取 **DOC_DIR** 变量（如果未设置则默认为 `omni-doc`）；步骤 4 init 后须 `source env.sh`，此时 **DOC_DIR 为绝对路径**（`paths.json` 真值源）
   - **KNOWLEDGE_DIR**（私域知识库根目录，与 DOC_DIR 独立）：步骤 4 init 从会话 env `KNOWLEDGE_DIR`（sdd Step1.5 export）回退读取并写入 env.sh/paths.json，**无需 CLI 透传**；未设置则默认 `omni-doc`。仿 `FLOW_MODE` 的 env 回退机制
   - **重要**: 步骤 4 之后读存量库用 `source` 后的 `DOC_DIR`；init 之前可用 check-prerequisites 返回的 **DOC_SPECS_DIR**（已为绝对路径）

6. **需求波及分析**:
   - 加载 skill `omni-dsdd:spec-impact-analyze`，分析 `${DOC_DIR}/specs` 中的已有规格文档以及代码内容，识别可复用的组件和需要变更的范围（**须在步骤 4 之后**，且已 `source env.sh`）
   - **推荐落盘顺序**（Harness）：
     1. **Write** `FEATURE_DIR/.runs/internal/context.payload.json`（spec-impact 返回的结构化对象，含 `context_mode`、`sections` 或等价字段）
     2. 执行 `specify-render-context.sh --feature-dir "$FEATURE_DIR" --user-intent "<业务意图摘要>"`  
        或按 `spec-impact-analyze/templates/context-template.md` **Write** `context.md`
     3. 执行 `specify-gate.sh --feature-dir "$FEATURE_DIR" --step 3 --record`
   - **禁止**仅在对话中输出分析结果而不写文件
   - 若子技能执行失败：Write 降级 `context.payload.json`（`degraded: true`、`reason`）→ 仍执行 render → gate；**不得**跳过
   - **等式验收**：`context.md` 必需章节数 == 5（功能描述、相关反构文档、架构分析与设计参考、术语对齐、约束和假设）
   - `gate_exit=0` 后输出 Checkpoint 并勾选步骤 6 Todo

7. **加载上下文并初始化 spec 骨架**:
   - 读取 `${CLAUDE_WORKING_DIR}/.omni-infra/templates/spec-template.md` 和 `${CLAUDE_WORKING_DIR}/.omni-infra/memory/constitution.md`
   - 执行 `specify-render-spec.sh --feature-dir "$FEATURE_DIR" --user-intent "<业务意图>" --merge`，确保 `spec.md` 含模板必需章节后再进入步骤 8
   - **读取上下文文件**:
     - 读取步骤 6 生成的 `FEATURE_DIR/context.md` 作为上下文参考
     - 若 `context.md` 仍不存在：立即回退步骤 6 补写，**不得**在无 `context.md` 时将步骤 6 标为完成

8. 遵循此执行流程:
   1. 从输入解析 `业务意图`
      如果为空: 错误 "未提供业务意图"
   2. 参考上下文文件 (`FEATURE_DIR/context.md`) 中的架构分析、可复用模式、术语对齐等信息
   3. 从 `业务意图`和上下文中提取关键概念，识别: 参与者、操作、数据、约束
   4. 对于不明确的方面:
      - 基于上下文和行业标准做出有根据的猜测
      - 仅在以下情况下标记为 [NEEDS CLARIFICATION: 具体问题]:
        - 选择显著影响功能范围或用户体验
        - 存在多个合理的解释且有不同的含义
        - 没有合理的默认值
      - **限制: 最多 3 个 [NEEDS CLARIFICATION] 标记**
      - 按影响优先级排序: 范围 > 安全/隐私 > 用户体验 > 技术细节
      - 优先参考上下文文件中的约束和假设
   5. 加载 skill `omni-dsdd:specify-requirement`，从系统视角分析业务意图对既有需求的影响，并追加到 `FEATURE_DIR/spec.md` 末尾
   6. 加载 skill `omni-dsdd:specify-scenario`，分析业务意图对既有场景的影响，并追加到 `FEATURE_DIR/spec.md` 末尾
   7. 定义成功标准
      创建可衡量的、技术无关的结果
      包括定量指标(时间、性能、数量)和定性措施(用户满意度、任务完成)
      每个标准必须无需实现细节即可验证
   8. 识别关键实体(如果涉及数据)
      参考上下文文件中的逻辑实体文档
   9. 返回: 成功(规范准备好进行规划)

   **规范 schema 定义**: SPEC_FILE 输出须符合 `${CLAUDE_WORKING_DIR}/.omni-infra/templates/spec-template.md` 的章节结构，包括：
   - 功能名称、描述、类型
   - 参与者、操作、数据流、约束
   - 成功标准、关键实体、依赖关系
   - 风险与假设

9. 使用模板结构将规范写入 SPEC_FILE, 用 `业务意图`和上下文文件派生的具体细节替换占位符, 同时保持章节顺序和标题.
   - 写入后执行 `specify-gate.sh --feature-dir "$FEATURE_DIR" --step 6 --record`
   - `gate_exit=0` 后输出 Checkpoint（含 `spec.md` 字节数）并勾选步骤 9 Todo

10. 执行测试分析与设计（仅当 `$ENABLE_E2E=true` 时执行）
   - **参数来源**：通过 `--e2e` 标志传递（如 `/specify 功能描述 --e2e`）
   - **判断条件**：检查传入的 `$ENABLE_E2E` 参数
     - 若 `$ENABLE_E2E=true`：执行本步骤
     - 若 `$ENABLE_E2E=false` 或未设置：跳过本步骤，直接进入步骤 11
   - **强制要求**：当执行时，必须严格按照 `omni-dsdd:e2e-specify` 技能文件中定义的流程执行，不得跳过或修改任何步骤。
   - 加载 skill `omni-dsdd:e2e-specify`：传递规范文件与特性目录上下文，按该技能全文执行 MFQ&PPDCS 测试分析与 TCON 黑盒用例设计，并验证 `test-analysis.md`、`e2e-test.md`
   - 执行完本步骤后，将生成以下文档：
      - `test-analysis.md`：测试分析报告（包含 KYM、TCO、MFQ 建模、测试点清单、Issues）
      - `e2e-test.md`：黑盒测试用例文档（包含用例清单、用例详情、测试数据、追溯性矩阵）

   **注意**: 如果测试分析与设计验证失败且无法继续（如 agent 执行失败、文档未生成），应记录错误信息并继续执行步骤 11（不阻塞整体流程）。

11. **规范质量验证**: 编写初始规范后, 根据质量标准进行验证:

   a. **创建规范质量检查清单**: 先执行 `specify-render-checklist.sh --feature-dir "$FEATURE_DIR"` 从 `${CLAUDE_WORKING_DIR}/.omni-infra/templates/requirements-template.md` 落盘骨架，再据规范填写勾选状态（**禁止**手写与模板结构无关的检查清单）

   b. **运行验证检查**: 根据每个检查清单项目审查规范:

   - 对于每个项目, 确定是否通过或失败
   - 记录发现的具体问题(引用相关规范章节)

   c. **处理验证结果**:

   - **如果所有项目都通过**: 标记检查清单完成并继续步骤 12
   - **如果项目失败(不包括 [NEEDS CLARIFICATION])**:

     1. 列出失败的项目和具体问题
     2. 更新规范以解决每个问题
     3. 重新运行验证直到所有项目都通过(最多 3 次迭代)
     4. 如果 3 次迭代后仍然失败, 在检查清单备注中记录剩余问题并警告用户
   - **如果 [NEEDS CLARIFICATION] 标记仍然存在**:

     1. 从规范中提取所有 [NEEDS CLARIFICATION: ...] 标记
     2. **限制检查**: 如果存在超过 3 个标记, 仅保留 3 个最关键的(按范围/安全/用户体验影响)并为其余部分做出有根据的猜测
     3. 对于每个需要的澄清(最多 3 个), 以以下格式向用户呈现选项:

        ```markdown
        ## 问题 [N]: [主题]

        **上下文**: [引用相关规范章节]

        **我们需要了解**: [来自 NEEDS CLARIFICATION 标记的具体问题]

        **建议答案**:

        | 选项   | 答案             | 含义                     |
        | ------ | ---------------- | ------------------------ |
        | A      | [第一个建议答案] | [这对功能意味着什么]     |
        | B      | [第二个建议答案] | [这对功能意味着什么]     |
        | C      | [第三个建议答案] | [这对功能意味着什么]     |
        | 自定义 | 提供你自己的答案 | [解释如何提供自定义输入] |

        **你的选择**: _[等待用户响应]_
        ```
     4. **关键 - 表格格式**: 确保 markdown 表格格式正确:

        - 使用一致的间距, 管道符对齐
        - 每个单元格内容周围应有空格: `| 内容 |` 而不是 `|内容|`
        - 标题分隔符必须至少有 3 个破折号: `|--------|`
        - 测试表格在 markdown 预览中正确渲染
     5. 按顺序编号问题(Q1、Q2、Q3 - 最多 3 个)
     6. 在等待响应之前一起呈现所有问题
     7. 等待用户响应所有问题的选择(例如, "Q1: A, Q2: 自定义 - [详情], Q3: B")
     8. 通过用用户选择或提供的答案替换每个 [NEEDS CLARIFICATION] 标记来更新规范
     9. 在所有澄清解决后重新运行验证

   d. **更新检查清单**: 每次验证迭代后, 使用当前的通过/失败状态更新检查清单文件
   e. **强制落盘**：步骤 11 结束前必须用 Write 确保 `FEATURE_DIR/checklists/requirements.md` 存在
   f. **Harness 门禁**：`specify-gate.sh --step 8 --record`；**等式验收**：检查项行数（`- [ ]` / `- [x]`）≥ 3
   g. `gate_exit=0` 后勾选步骤 11 Todo

9. **AI 质量评测**: 加载 skill `omni-dsdd:eval-specify`，对 SPEC_FILE 进行四维量规评测
   - 通过标准: overall_score >= 95
   - 若不通过: 根据 `eval-specify-report.yaml`，修复对应维度问题后重新评测（最多 2 轮，复用步骤 11 的迭代逻辑）
   - **Harness 门禁**：`specify-gate.sh --step 9 --record`（yaml 须含 `stage:`、`overall_score`）
   - `gate_exit=0` 后勾选步骤 12 Todo（质量分 < 95 可 warning，但**文件必须存在**）

13. **产物完整性校验**（步骤 14 的前置门控）:
   - 执行：`verify-specify-artifacts.sh --feature-dir "$FEATURE_DIR"`（`gate --step all`）
   - 可选：`python3 "${CLAUDE_PLUGIN_ROOT}/skills/specify/scripts/python/specify_harness.py" resume --feature-dir "$FEATURE_DIR"` 列出 `pending_steps` 后逐项补跑
   - 校验通过（`gate_exit=0`）后方可进入步骤 14；失败则按 `errors` 回退重做（每类最多 2 次）

14. **报告完成情况**
    - **前置条件**：步骤 13 `gate_exit=0`（须在报告中写明 `evidence: verify-specify-artifacts.sh exit 0`）
    - 报告分支名称、上下文文件路径、规范文件路径、检查清单结果、AI 评测结果（score/status）以及下一阶段（`/clarify` 或 `/design`）的准备就绪状态
    - 若步骤 10 已执行：报告 `test-analysis.md`、`e2e-test.md` 路径
    - 若步骤 10 已跳过（未启用 `--e2e`）：
      - E2E 测试分析与设计已跳过（未启用 --e2e）
      - 后续在 `design` 阶段也会相应跳过 `e2e-design`（因为缺少 e2e-test.md 依赖）
      - 如需测试设计，可重新执行 `/specify --e2e` 或在执行 `design` 前单独加载 skill `omni-dsdd:e2e-specify`

15. **记录运行日志**：
    - 执行前：`source "$FEATURE_DIR/.runs/env.sh"`（已含 `FEATURE_DIR`）
    - 加载 skill `omni-dsdd:runlog-record`，将前面获取的 `start_time` 作为参数传入
    - **参数传递方式**：`/omni-dsdd:runlog-record [start_time]`（如 `/omni-dsdd:runlog-record "2026-05-15 10:30:00"`）
    - **强制落盘**：追加 `omni-metrics-log.json` 后执行 `specify-gate.sh --step 11 --record`
    - 若 `omni-dsdd:runlog-record` 失败：用 Write 直接向 JSON 追加条目 → 再跑 gate；`gate_exit=1` 不得勾选步骤 15

16. **同步 SDD 状态（routing 闭环，阻塞步骤）**：
    - 从上游 workflow 读取 `flow_mode`（express/standard/deep），**禁止**写死为 standard
    - express：`specify-finalize.sh --flow-mode express --next-stage design`
    - standard：`specify-finalize.sh --flow-mode standard --next-stage clarify`
    - deep：与 standard 相同或按 `workflows/deep.yaml` 约定
    - 执行 `specify-gate.sh --step 11.5 --record`；`gate_exit=1` 时**不得**标步骤 16 完成，**不得**输出 specify 完成报告
    - 输出 Checkpoint：`步骤16: omnispec-state updated, completed_stages includes specify`

**流程注意**:
- 上下文收集在规范生成之前执行，生成 `FEATURE_DIR/context.md`
- 规范生成参考上下文中的架构分析、可复用模式、术语对齐等信息

## 错误处理

### 常见错误

| 步骤 | 错误场景 | 处理方式 |
|------|----------|----------|
| 步骤1 | 特性上下文合并解析失败（如不在 changes/ 下） | 报错终止 |
| 步骤2 | `omni-dsdd:create-branch` 执行失败 | 重试或输出中文错误信息 |
| 步骤5 | 脚本执行失败/超时 | 使用默认 DOC_DIR (`omni-doc`) 继续 |
| 步骤5 | 脚本不存在 | 提示用户检查 `${CLAUDE_PLUGIN_ROOT}/scripts/` 目录配置 |
| 步骤6 | `omni-dsdd:spec-impact-analyze` 失败 | 写入降级版 `context.md`，不得跳过落盘 |
| 步骤10 | `omni-dsdd:e2e-specify` 失败 | 记录错误，继续步骤 11（不阻塞整体流程） |
| 步骤11 | 验证失败（3次迭代后） | 仍须写入 `checklists/requirements.md`；在清单备注中记录剩余问题并警告用户 |
| 步骤12 | AI评测不通过（2次迭代后） | 仍须写入 `eval-specify-report.yaml`；在报告中记录未达标状态 |
| 步骤4 | harness init 失败 | 重试 2 次后终止 |
| 步骤6/9/11/12/15 | 分步 gate 失败 | 按 `specify-run.json` 与 `resume` 输出回退该步，不得勾选 Todo |
| 步骤13 | 全量 gate 失败 | 回退重做缺失步骤（每类最多 2 次），不得输出完成报告 |
| 步骤15 | `omni-dsdd:runlog-record` 失败 | Write 追加日志 → 再跑 `gate --step 11` |
| 步骤16 | finalize 失败 | 重试；仍失败则警告并手动补写 `omnispec-state.json` |

## 参考文档

### OmniSpec 项目模板（工作区）
- 规范模板：`${CLAUDE_WORKING_DIR}/.omni-infra/templates/spec-template.md`
- 规范检查清单模板：`${CLAUDE_WORKING_DIR}/.omni-infra/templates/requirements-template.md`
- 项目章程：`${CLAUDE_WORKING_DIR}/.omni-infra/memory/constitution.md`

### 配置与 Harness 脚本
- Bash 前置检查：`${CLAUDE_PLUGIN_ROOT}/scripts/bash/check-prerequisites.sh`（须在 `CLAUDE_WORKING_DIR` 下执行）
- PowerShell 前置检查：`${CLAUDE_PLUGIN_ROOT}/scripts/powershell/check-prerequisites.ps1`
- **specify 专用 Harness**：
  - `scripts/python/specify_harness.py` — init / gate / record / render-* / finalize / resume
  - `scripts/python/specify_template_gate.py` — 模板契约校验
  - `scripts/bash/`、`scripts/powershell/` — 平台封装（与 create-branch 目录布局一致）
  - `references/template-contract.json` — 产物与模板的机器可读契约

## 写作指南

### 快速原则

- 专注于用户需要**什么**和**为什么**
- 避免如何实现（不涉及技术栈、API、代码结构）
- 为业务利益相关者编写，而不是为开发者
- 不要创建嵌入规范中的任何检查清单，那将是一个单独的命令

### 章节要求

- **必需章节**: 每个功能必须完成
- **可选章节**: 仅在与功能相关时包含
- 当章节不适用时, 完全删除它(不要保留为 "N/A")

### AI 生成

当从用户提示创建此规范时:

1. **做出有根据的猜测**: 使用上下文、行业标准和常见模式来填补空白
2. **记录假设**: 在假设章节中记录合理的默认值
3. **限制澄清**: 最多 3 个 [NEEDS CLARIFICATION] 标记 - 仅用于关键决策:
   - 显著影响功能范围或用户体验
   - 存在多个合理的解释且有不同的含义
   - 缺乏任何合理的默认值
4. **优先澄清**: 范围 > 安全/隐私 > 用户体验 > 技术细节
5. **像测试人员一样思考**: 每个模糊的需求都应该在"可测试且明确"的检查清单项目上失败
6. **NEEDS CLARIFICATION 的常见领域**(仅在没有合理默认值时):
   - 功能范围和边界(包含/排除特定用例)
   - 用户类型和权限(如果可能存在多个冲突的解释)
   - 安全/合规要求(当具有法律/财务重要性时)

**合理默认值的示例**(不要询问这些):

- 数据保留: 该行业的行业标准实践
- 性能目标: 标准 Web/移动应用期望, 除非另有说明
- 错误处理: 用户友好的消息和适当的回退
- 认证方法: Web 应用的标准基于会话或 OAuth2
- 集成模式: RESTful API, 除非另有说明

### 成功标准指南

成功标准必须是:

1. **可衡量的**: 包括具体指标(时间、百分比、计数、速率)
2. **技术无关的**: 不提及框架、语言、数据库或工具
3. **以用户为中心的**: 从用户/业务角度描述结果, 而不是系统内部
4. **可验证的**: 无需了解实现细节即可测试/验证

**好的示例**:

- "用户可以在 3 分钟内完成结账"
- "系统支持 10,000 个并发用户"
- "95% 的搜索在 1 秒内返回结果"
- "任务完成率提高 40%"

**坏的示例**(以实现为中心):

- "API 响应时间在 200ms 以下"(太技术化, 使用"用户立即看到结果")
- "数据库可以处理 1000 TPS"(实现细节, 使用面向用户的指标)
- "React 组件高效渲染"(框架特定)
- "Redis 缓存命中率超过 80%"(技术特定)

## 上下文管理

### Todo 集成
- 步骤 0 使用 TodoWrite 工具创建 TodoList，跟踪步骤 0 至 16 的执行进度
- 每个步骤完成后立即将对应 Todo 项标记为已完成
- 步骤间的中间结果通过 TodoList 的任务描述传递

### 阶段间数据传递（Harness：只传路径，不传全文）
- **步骤1 → 步骤2**：预解析得到的 `FEATURE_DIR` / `BRANCH_NAME` 传入 `omni-dsdd:create-branch`；步骤 3 起以 `omni-dsdd:create-branch` **返回值**为准
- **步骤2 → 步骤4**：`paths.json` + `env.sh` 为唯一真值源；禁止用对话记忆替代路径
- **步骤6 → 步骤7**：`context.md`（优先）或 `context.payload.json`
- **步骤8 → 步骤9**：`spec.md` 通过文件传递
- **步骤13 → 步骤14**：`verify-specify-artifacts.sh` 的 `gate_exit` 作为完成证据
- **步骤16 → routing**：`.omnispec-state.json` 的 `completed_stages`

### 错误恢复与断点续跑
- `python3 "${CLAUDE_PLUGIN_ROOT}/skills/specify/scripts/python/specify_harness.py" resume --feature-dir "$FEATURE_DIR"` 获取 `pending_steps`
- 仅重跑 `pending_steps` 对应步骤，已 `passed` 步骤**禁止**重复生成覆盖
- DOC_DIR 脚本失败仍可用默认 `omni-doc`（步骤 5 例外，不跳过落盘类步骤）
