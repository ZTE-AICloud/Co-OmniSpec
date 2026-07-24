---
name: reverse-on-demand
description: 按需反构编排Skill。基于需求意图执行代码架构分析，支持简单/复杂需求场景。当 reverse --target on-demand 时触发。
argument-hint: --requirement=<文本>|--intent=<文本> [--demand-complexity=<simple|complex>] [--path=<dir1,dir2,...>] [--exclude=<glob1,glob2,...>] [--mode=<silent|interactive>]
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash
  - TaskCreate
  - TaskUpdate
  - TaskList
  - Agent
when_to_use: 当用户执行 reverse --target on-demand 或需要基于需求意图进行代码架构分析时触发
---

# 按需反构Skill（on-demand）

## 行为准则

以下规则在整个会话期间有效，不因对话长度而放松：

1. ❗ **每个阶段发现必须引用来源**（文件路径 + 行号）— 适用所有阶段。每次输出前自检此条。
2. ❗ **阶段间依赖必须显式传递**（环境变量/文件路径），不得在后续阶段重新推导目录或分支名。每次输出前自检此条。
3. ❗ **交互模式确认规则** — `--mode=interactive` 时：步骤3b 步骤5.7 的用户确认点必须等待响应后方可继续。`静默模式（默认）`下无需等待，所有确认点自动通过（保留全部功能），直接继续后续步骤。每次输出前自检此条。

> ❗ 标记规则 ≤3 条已达标。

## Step 0：初始化（仅 Agent/MD 层）

### 0.1 核心全局变量（2+1）

| 变量 | 谁设置 | 含义 | 用途 |
|------|--------|------|------|
| `CLAUDE_PLUGIN_ROOT` | 运行时注入，或 Step 0.2 补全 | Omni 插件安装根（含 `skills/`、`scripts/`） | 拼插件脚本路径；调用封装脚本时传 `--plugin-root` |
| `CLAUDE_WORKING_DIR` | 运行时注入，或 Step 0.2 补全 | 当前工作区目录（可为仓库子目录） | `changes/`、Harness 落盘、Git/目录操作工作区根 |
| `CREATE_BRANCH_HAS_GIT` | Step 0.3 探测 | `true` / `false` | 传给 `create-new-feature` 的 `--has-git` |

> 已废弃：脚本内自推 `REPO_ROOT`、`__file__`/`parents[n]` 推根、业务脚本内 `pwd`/`git rev-parse` 推根目录。

### 0.2 变量补全（仅此层允许“解析一次”）

- `CLAUDE_PLUGIN_ROOT` 补全顺序：
  1. 运行时已有则直接使用；
  2. Skill 上下文中的插件根；
  3. 在 `CLAUDE_WORKING_DIR` 上级查找 `.claude-plugin/plugin.json`（内嵌开发态）；
  4. 仍失败则终止。
- `CLAUDE_WORKING_DIR` 补全：
  1. 运行时已有则直接使用；
  2. 缺失时执行 `export CLAUDE_WORKING_DIR="$(pwd)"`（禁止使用 `git rev-parse --show-toplevel`）。

### 0.3 校验与一次性探测

```bash
# 校验目录变量存在且可用
test -d "${CLAUDE_PLUGIN_ROOT}"
test -d "${CLAUDE_WORKING_DIR}"

# 创建工作区下 changes
mkdir -p "${CLAUDE_WORKING_DIR}/changes"

# 仅探测一次是否存在 Git 工作区
if git -C "${CLAUDE_WORKING_DIR}" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  export CREATE_BRANCH_HAS_GIT=true
else
  export CREATE_BRANCH_HAS_GIT=false
fi
```

### 0.4 SDD 环境初始化

执行初始化（显式传入工作区，**不要**依赖脚本内 `pwd`，**不要**仅 `export` 后无参调用）：

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/bash/init_omni_infra.sh" \
  --plugin-root "${CLAUDE_PLUGIN_ROOT}" \
  --working-dir "${CLAUDE_WORKING_DIR}"
```

说明：`init_omni_infra.sh` 将 `${CLAUDE_PLUGIN_ROOT}/omni-infra` 复制为 `${CLAUDE_WORKING_DIR}/.omni-infra`；返回码 `1` 表示首次创建成功，按需 `Task(omni-dsdd:constitution)` 后继续；`0` 表示已存在；`2` 为失败。

### 0.5 两层分工与路径拼接（强制）

- **SKILL.md 编排层**：
  - 插件路径统一使用 `${CLAUDE_PLUGIN_ROOT}/...`
  - 工作区数据路径统一使用 `${CLAUDE_WORKING_DIR}/...`
- **业务脚本层**：
  - 只消费参数，不在脚本内重新推导根目录
  - 目录/Git/落盘必须使用 `--working-dir`（必填）
- **调用参数约定**：
  - Harness：`python3 ... --working-dir "${CLAUDE_WORKING_DIR}" ...`
  - 封装脚本：`bash ... --plugin-root "${CLAUDE_PLUGIN_ROOT}" --working-dir "${CLAUDE_WORKING_DIR}" ...`

### 0.6 执行模式解析（强制）

- **执行模式**：`--mode=silent`（默认）或 `--mode=interactive`
- **静默模式（默认）**：自动进行直至完成，无需用户交互确认。所有波及功能/接口清单默认全部保留（`impact_status=hit`），直接进入步骤6后续处理。
- **交互模式**：每个阶段完成后需要用户显式确认（特别是阶段3b 步骤5.7 的波及清单确认），用户可保留/剔除/补充功能信息。
- **默认值**：未指定 `--mode` 时默认为 `silent`。
- **模式影响范围**：
  - 阶段3b 步骤5.7（波及清单确认）：静默模式自动全部保留，跳过用户交互；交互模式等待用户输入。
  - 阶段3a 无用户确认点，模式不影响执行路径。
  - 阶段1/阶段2 全程无用户交互，模式不影响。

## 概览（职责与输入输出）

- **职责**：基于需求意图（SDD 文档或自然语言），执行按需反构流程：
  - 分支与特性准备（基于 create-branch 的分支/目录复用与创建）
  - 深度架构识别
  - 简单需求 / 复杂需求的按需反构执行（含波及功能分析、接口分析与逐功能分析）
- **输入前提**：
  - 用户通过 `reverse --target on-demand ...` 触发
  - 用户输入需包含可解析的业务意图描述
  - 本流程不要求 `spec.md` 存在，也不会创建/修改 `changes/<feature>/spec.md`
- **输出产物**：
  - `{FEATURE_DIR}/on-demand/`：按需反构中间产物/缓存
  - `{REPO_ROOT}/omni-doc/on-demand/on-demand-existing-function-analysis-{BRANCH_NAME}.md`：主汇总文档
  - `{REPO_ROOT}/omni-doc/on-demand/functions/{function_key}.md`：逐功能分析文档（简单/复杂流程共用目录）
  - `{REPO_ROOT}/omni-doc/on-demand/interfaces/{interface_key}.md`：逐接口分析文档（接口独立产物，功能文档通过引用关联）

> 本 Skill 对应原 `reverse-on-demand.md` 中的阶段化流程和子 Agent 调用约定，仅把入口改为 Skill。

## Harness 执行契约（阶段2波及检索 · 四项强制约束）

阶段 3a 步骤 2.6 / 阶段 3b 步骤 5.6 **落盘后、进入用户确认或步骤 6 之前**，必须执行 Harness 门禁；**`gate_exit≠0` 时不得继续**。

| 约束 | 解决的问题 | 必落盘产物 | 门禁校验要点 |
|------|-----------|-----------|-------------|
| **检索范围约束** | 检索范围过大导致耗时和 token 过高，或范围失控导致漏检 | `stage2-search-coverage.json` | 未指定 `--path` 时：`scan_mode=full_repo`；指定 `--path` 时：`scan_mode=scoped` 且 `scope.include_paths` 与输入一致；`--exclude` 必须透传到 `scope.exclude_globs` |
| **调用链深度** | 追踪过深时自动浅层停止 | `stage2-call-trace.json` | 每入口根符号一条 `trace`；禁止 `depth_limit`/`token_budget` 等在未达 `min_required_depth`（默认 8）且无 `leaf_evidence` 时停止 |
| **配置解析** | 配置文件只列路径未解析 | `stage2-static-asset-scan.json` | 每个配置文件 `parse_status=parsed`；含 `extracted_keys` 或足够 `structure_summary`；含 `consumer_refs` |
| **多语言覆盖** | 主用语言外的附属语言（Lua/Shell/SQL/proto 等）被忽略 | `stage2-search-coverage.json`（`languages` 子结构） | `languages` 必须枚举仓库全部语言（Harness 自动扫盘校验，漏报即失败）；每项含 `role`(primary/auxiliary)/`coverage_status`(covered/degraded)/`analysis_method`(lsp/grep/read/manual)；禁止裸 uncovered，degraded 须含 `degraded_rationale`；至少一个 primary；**波及校验**：auxiliary 须含 `impact_status`(hit/no_hit)，hit 时波及清单须出现该语言命中，no_hit 须含 `no_impact_rationale` 且清单不得命中该语言 |

契约文件：[references/harness-contract.json](references/harness-contract.json)

### 统一门禁命令

```bash
# 阶段1完成后、阶段3波及检索开始前（生成骨架，可选但推荐）
bash "${CLAUDE_PLUGIN_ROOT}/skills/reverse-on-demand/scripts/bash/reverse-on-demand-init-harness.sh" \
  --working-dir "$CLAUDE_WORKING_DIR" \
  --feature-dir "$FEATURE_DIR" \
  --repo-root "$REPO_ROOT" \
  --scope-paths "$SCOPE_PATHS_CSV" \
  --exclude-globs "$EXCLUDE_GLOBS_CSV"

# 步骤 2.6 / 5.6 落盘全部 stage2 产物后（强制）
bash "${CLAUDE_PLUGIN_ROOT}/skills/reverse-on-demand/scripts/bash/reverse-on-demand-gate.sh" \
  --working-dir "$CLAUDE_WORKING_DIR" \
  --feature-dir "$FEATURE_DIR" \
  --repo-root "$REPO_ROOT" \
  --scope-paths "$SCOPE_PATHS_CSV" \
  --exclude-globs "$EXCLUDE_GLOBS_CSV" \
  --step stage2 \
  --record
```

```powershell
# 阶段1完成后、阶段3波及检索开始前（生成骨架，可选但推荐）
powershell -File "${CLAUDE_PLUGIN_ROOT}/skills/reverse-on-demand/scripts/powershell/Reverse-On-Demand-InitHarness.ps1" `
  --working-dir "$CLAUDE_WORKING_DIR" `
  --feature-dir "$FEATURE_DIR" `
  --repo-root "$REPO_ROOT" `
  --scope-paths "$SCOPE_PATHS_CSV" `
  --exclude-globs "$EXCLUDE_GLOBS_CSV"

# 步骤 2.6 / 5.6 落盘全部 stage2 产物后（强制）
powershell -File "${CLAUDE_PLUGIN_ROOT}/skills/reverse-on-demand/scripts/powershell/Reverse-On-Demand-Gate.ps1" `
  --working-dir "$CLAUDE_WORKING_DIR" `
  --feature-dir "$FEATURE_DIR" `
  --repo-root "$REPO_ROOT" `
  --scope-paths "$SCOPE_PATHS_CSV" `
  --exclude-globs "$EXCLUDE_GLOBS_CSV" `
  --step stage2 `
  --record
```

- `gate_exit=0`：允许进入 3b 步骤 5.7（静默模式直接自动通过，交互模式等待用户确认）或 3a 步骤 3 子 Agent
- `gate_exit=1`：**不得**勾选 Todo / 不得进入后续步骤；按 JSON `errors` 补齐产物（检索范围/调用链/配置解析/多语言覆盖）后重跑 gate（每步最多 2 次）

### Checkpoint 格式（阶段2 Harness 通过后）

```text
✅ Checkpoint 阶段2-Harness: gate_exit=0, artifacts=search-coverage+call-trace+static-asset-scan+languages
```

## 与 `reverse` 命令的关系

- `reverse` 负责：
  - 解析 `$ARGUMENTS`，包括 `--requirement`、`--intent`、`--demand-complexity`、`--path`、`--exclude`、`--mode` 等；
  - 将 `--path` 归一化为 `SCOPE_PATHS_CSV`，将 `--exclude` 归一化为 `EXCLUDE_GLOBS_CSV`，并在阶段2/阶段3全程透传；
  - 将 `--mode`（silent/interactive）透传给本 Skill；未指定时默认 `silent`；
  - 解析交互模式（语言要求始终为中文）；
  - 激活本 Skill 并传入参数。
- 本 Skill 负责：
  - 严格按阶段文件的说明执行；
  - 在需要时调用通用分支管理与按需反构阶段脚本/子 Agent。

## 阶段总览

本 Skill 按以下阶段执行，阶段详细说明见本目录下 `references/stages/`：

1. **阶段1：分支和特性准备**
   ✅ Checkpoint: 变量 REPO_ROOT / BRANCH_NAME / FEATURE_DIR 已设置
   失败路径: 变量缺失 → 终止
2. **阶段2：深度架构识别**
   ✅ Checkpoint: deep_architecture_result 已设置
   失败路径: 架构结果缺失 → 终止
3. **阶段3：按需反构执行（根据需求复杂度 simple/complex 分支到 3a/3b）**
   ✅ Checkpoint: 主汇总文档已生成
   失败路径: 详见各 stage 文档

## 阶段1：分支和特性准备

- **阶段说明来源**：
  - 通用分支管理：调用 Skill `omni-dsdd:create-branch`（`skills/create-branch/SKILL.md`）
  - 按需检查已有产物：本 Skill 内 [references/stages/01-check-existing-products.md](references/stages/01-check-existing-products.md)
- **目标**：
  - 确定或创建特性分支与特性目录 `FEATURE_DIR`；
  - 检查是否已有完整按需反构产物，必要时允许用户选择中止或重录。
- **关键输出变量**：
  - `REPO_ROOT`：仓库根目录（绝对路径）
  - `BRANCH_NAME`：特性分支名
  - `FEATURE_DIR`：特性目录（绝对路径）
  - `SPEC_FILE`：由 `create-branch` 返回（仅记录路径，不作为 on-demand 依赖）
- **调用约束（强制）**：
  - create-branch 相关脚本调用必须传 `--working-dir "${CLAUDE_WORKING_DIR}"`；
  - 若通过插件内封装脚本调用，必须同时传 `--plugin-root "${CLAUDE_PLUGIN_ROOT}"`；
  - `--has-git` 必须使用 Step 0.3 得到的 `CREATE_BRANCH_HAS_GIT`，禁止在业务脚本层重复探测。
- **硬性路径约束（强制）**：
  - `FEATURE_DIR` 必须位于 `{REPO_ROOT}/changes/` 目录下（形如 `{REPO_ROOT}/changes/<short-name>`）。
  - 若 `FEATURE_DIR` 不在 `changes/` 下（例如落到 `specs/`、`features/`），必须立即报错终止，不得继续阶段2/阶段3。
  - 阶段2/阶段3与所有子 Agent 必须复用阶段1同一组输出变量（`REPO_ROOT`、`BRANCH_NAME`、`FEATURE_DIR`），不得重新推导目录或分支名。

## 阶段2：深度架构识别

- **阶段说明来源**：本 Skill 内 [references/stages/02-deep-architecture-identification.md](references/stages/02-deep-architecture-identification.md)
- **目标**：执行深度架构分析，生成后续按需反构的稳定架构上下文。
- **关键输出**：
  - `deep_architecture_result`：通常为 `{REPO_ROOT}/omni-doc/on-demand/logic_architecture.md`
- **要点**：
  - 支持缓存与重用已有架构识别结果；
  - 若架构结果缺失或不可用，则必须中止按需反构流程。

## 阶段3：按需反构执行（simple / complex）

### 3.1 解析需求复杂度参数

- 从 `$ARGUMENTS` 中解析 `--demand-complexity=<simple|complex>`；
- 默认值为 `simple`。

### 3.1.1 可选范围过滤参数（兼容模式）

- 从 `$ARGUMENTS` 中解析 `--path`（逗号分隔目录）与 `--exclude`（逗号分隔 glob）；
- **默认兼容**：当未提供 `--path/--exclude` 时，执行路径与现有流程完全一致（阶段2为 `full_repo`）；
- **全流程生效**：当提供 `--path` 和/或 `--exclude` 时，阶段2检索、阶段3分析、文档产出、门禁校验都必须遵从同一范围；
- **优先级**：先按 `--path` 限定候选，再应用 `--exclude` 排除；
- **异常处理**：若过滤后候选为空，按“零结果与幻觉防护”输出 `evidence不足`，不得虚构结果。

### 3.2 分支 3a：简单需求（simple）

- **阶段说明来源**：本 Skill 内 [references/stages/03a-simple-on-demand-reverse.md](references/stages/03a-simple-on-demand-reverse.md)
- **目标**：对简单需求执行一次性按需反构，生成汇总与逐功能文档。
- **执行方式（保持原有约束）**：
  - 读取 stage 文档：本 Skill 内 `references/stages/03a-simple-on-demand-reverse.md`（安装后路径可能为 `{REPO_ROOT}/.claude/skills/reverse-on-demand/references/stages/03a-simple-on-demand-reverse.md`，安装脚本会将 `.claude/` 替换为实际的 agent 目录，例如 `.claude/` 或 `.cursor/`）；
  - 按文档中步骤逐条执行，不将 stage 文档当作 Agent；
  - 在指定步骤通过 Task 工具调用子 Agent `simple-on-demand-reverse-agent`；
  - 传递的上下文变量包括：`FEATURE_DIR`、`REPO_ROOT`、`arguments`、`constitution_path`（可选）、`deep_architecture_result`。
- **输出**：
  - `{FEATURE_DIR}/on-demand/` 中的中间产物；
  - 主汇总文档、逐功能文档与逐接口文档。

### 3.3 分支 3b：复杂需求（complex）

- **阶段说明来源**：本 Skill 内 [references/stages/03b-complex-on-demand-reverse.md](references/stages/03b-complex-on-demand-reverse.md)
- **目标**：为复杂需求提供阶段化产出、用户确认点（仅交互模式）与逐功能深度分析。静默模式下清单自动全部保留，无需等待用户确认。
- **执行方式（保持原有约束）**：
  - 读取 stage 文档：本 Skill 内 `references/stages/03b-complex-on-demand-reverse.md`；
  - 按文档步骤执行：预检查、需求理解、波及功能/接口检索与清单确认、步骤6双轨并行执行与关口校验；
  - 在步骤6A通过 Task 工具调用子 Agent `complex-on-demand-function-analyzer`，遍历波及功能清单；
  - 在步骤6B基于 `function-interface-map.json` 逐接口生成并校验接口文档；
  - 在步骤6C调用关口校验脚本汇总双轨结果并执行阻断判定（`gate_passed=false` 时禁止进入步骤7）；
  - 步骤6.0必须调用分发脚本生成双轨待办：`{REPO_ROOT}/scripts/bash/reverse/on-demand/build-stage3-todos.sh`；
  - 步骤6C必须调用门禁脚本：`{REPO_ROOT}/scripts/bash/reverse/on-demand/validate-stage3-gate.sh`；
  - 使用与简单流程相同的一组上下文变量。
- **输出**：
  - `{FEATURE_DIR}/on-demand/`：阶段性产出与缓存（中间过程路径不可擅自更改）；
  - `{REPO_ROOT}/omni-doc/on-demand/functions/`：各波及功能独立文档；
  - `{REPO_ROOT}/omni-doc/on-demand/interfaces/`：各波及接口独立文档；
  - `{REPO_ROOT}/omni-doc/on-demand/on-demand-existing-function-analysis-{BRANCH_NAME}.md`：最终汇总文档（simple/complex 统一命名）。

## 接口独立文档策略（方案一）

- 按需反构采用“接口独立成文档、功能按引用关联”的策略：
  - 接口事实（定义、描述、参数、函数定位）仅在接口文档维护，避免在多个功能文档重复维护；
  - 功能文档仅保留接口摘要与链接引用；
  - 通过 `{FEATURE_DIR}/on-demand/stage3/function-interface-map.json` 固化功能-接口关系。
- 接口识别阶段约束：
  - simple：在阶段 3a 的步骤 2.6 与步骤 3 中完成接口候选识别与接口文档落盘；
- complex：在阶段 3b 的步骤 5、5.6、5.7 完成接口候选识别、缓存落盘与确认；在步骤 6A 执行功能轨分析、步骤 6B 执行接口轨文档生成/校验、步骤 6C 完成关口判定后方可进入步骤7。

## 图表渲染规范（强制）

- 接口文档必须使用 PlantUML 图描述接口使用流程（建议时序流程），并保证可渲染。
- 功能文档必须使用 PlantUML 活动图描述主处理流程，并保证可渲染。
- 图表输出前必须执行最小语法检查：
  - 必须包含 `@startuml` 和 `@enduml`
  - 代码块必须闭合
  - 不得混入 Markdown 表格分隔符等易导致渲染失败的内容

## 波及功能分析补充约束（simple / complex 共用）

执行复杂流程步骤5或简单流程步骤2.6中的波及检索时，除各 stage 文档既有要求外，**必须**同时遵守 [references/stages/03b-complex-on-demand-reverse.md](references/stages/03b-complex-on-demand-reverse.md) 中「波及功能分析强制补充步骤」，且 **Harness 四项约束全部通过**（见上文「Harness 执行契约」）：

1. **全仓库检索（非重点目录抽检）**：在 `REPO_ROOT` 执行全量文本检索并落盘 `stage2-search-coverage.json`；禁止仅以 `src/`、`pkg/` 等少数目录代替全仓扫描。
2. **核心目录完整文件清单**：对已识别为核心分析范围的目录，先用 `ls`（或递归列出）得到完整文件清单，不遗漏同目录成员。
3. **调用链深度可追溯**：落盘 `stage2-call-trace.json`；默认 `min_required_depth=8`；禁止浅层 `depth_limit`/`token_budget` 自动停止。
4. **配置文件必须解析**：落盘 `stage2-static-asset-scan.json`；每个命中配置须 `parse_status=parsed` 并提取 key/结构，记录消费方。
5. **按调用链与资源引用向下追溯**：发现代码引用外部资源（配置、模板、数据或静态资源文件等）后，须立即检索该资源所在目录并沿配置/资源依赖继续追溯，纳入候选波及范围。

## 子 Agent 调用统一约束

- 子 Agent 只能在阶段文档规定的步骤中被调用：
  - 简单需求：`simple-on-demand-reverse-agent`
  - 复杂需求：`complex-on-demand-function-analyzer`
- 禁止：
  - 直接将 stage 文档当作 Agent；
  - 跳过 preflight/确认步骤直接批量调用子 Agent。

### 子Agent调用规范

**委派约束**:
- 委派 prompt 必须复制 stage 文档中的原始约束，不转述
- 输入集共 N 项，必须全部处理
- 只负责 X，不涉及 Y

| 子Agent名称 | 用途 | 调用阶段 | 必需参数 |
|------------|------|----------|----------|
| simple-on-demand-reverse-agent | 简单需求反构 | 阶段3a | FEATURE_DIR、REPO_ROOT、arguments、deep_architecture_result |
| complex-on-demand-function-analyzer | 复杂需求功能分析 | 阶段3b | FEATURE_DIR、REPO_ROOT、arguments、function_key、function_item |
| requirement-similarity-analyzer | 相似需求检索 | 阶段3b（可选） | FEATURE_DIR、REPO_ROOT |

合并检查（强制）:
- 去重：多个子 Agent 结果中相同内容合并为一条
- 一致性：不同子 Agent 结论矛盾时，优先采用 stage 文档指定的 source of truth
- 计数验证：各子 Agent 处理项数之和 == 待办清单总项数

### 参数传递说明
- **FEATURE_DIR**：特性目录绝对路径（由阶段1确定）
- **REPO_ROOT**：仓库根目录绝对路径（由阶段1确定）
- **arguments**：用户原始输入，包含需求描述
- **path/exclude（可选）**：通过 `arguments` 向阶段3子流程透传；仅在显式传参时启用过滤
- **deep_architecture_result**：架构识别结果文件路径
- **function_key**：功能唯一标识
- **function_item**：功能详情对象
- **constitution_path**：知识库路径（可选）

## 参考文档（本 Skill 内）

本 Skill 的详细规范位于本目录下 `references/`，分支管理由 Skill `omni-dsdd:create-branch` 提供：

- 阶段 1 分支管理：调用 Skill `omni-dsdd:create-branch`
- 阶段 1 检查已有产物：[references/stages/01-check-existing-products.md](references/stages/01-check-existing-products.md)
- 阶段 2：[references/stages/02-deep-architecture-identification.md](references/stages/02-deep-architecture-identification.md)
- 阶段 3a：[references/stages/03a-simple-on-demand-reverse.md](references/stages/03a-simple-on-demand-reverse.md)
- 阶段 3b：[references/stages/03b-complex-on-demand-reverse.md](references/stages/03b-complex-on-demand-reverse.md)

执行本 Skill 时，AI Agent 必须读取上述文档并严格按照其中的说明与约束执行。

## 上下文管理

### Token 预算分配
- 阶段1（分支准备）：5K tokens
- 阶段2（架构识别）：30K tokens
- 阶段3a/3b（按需反构）：按需求复杂度分配

### 缓存策略
- 架构识别结果缓存：`omni-doc/on-demand/logic_architecture.md`
- 各阶段中间结果缓存：`<FEATURE_DIR>/on-demand/stage*/`

### 阶段间数据传递
- 通过环境变量传递：REPO_ROOT、BRANCH_NAME、FEATURE_DIR
- 通过环境变量传递（全局）：CLAUDE_PLUGIN_ROOT、CLAUDE_WORKING_DIR、CREATE_BRANCH_HAS_GIT
- 通过文件传递：各stage的缓存JSON文件
- **写入前交叉验证**：写入文件前，校验路径一致性和数量匹配（如：功能项数 == 功能文档数）

## 零结果与幻觉防护

**来源引用要求**: 所有阶段结论必须引用具体来源（文件路径+行号或工具返回），无来源 = 不输出。

**零结果处理**:
| 场景 | 正确输出 | 禁止输出 |
|------|---------|---------|
| 检索无结果 | "未发现相关功能/接口，标记为 evidence不足" | 推断/补充不存在的内容 |
| 文件不存在 | "目标文件不存在，路径: X" | 假设文件存在继续执行 |
| 缓存缺失 | "缓存不存在，将重新生成" | 使用旧缓存或不报错继续 |

**结果分级标注**:
- 确认结果：无标注
- 降级分析：标注"⚠️ 降级: [原因]"
- 通用建议：标注"💡 通用建议"

## 故障排除

### 常见问题

**问题1：阶段执行失败**
- 原因：前置条件未满足
- 解决：检查REPO_ROOT、BRANCH_NAME、FEATURE_DIR是否正确设置

**问题2：子Agent调用失败**
- 原因：Agent配置问题或超时
- 解决：检查Agent类型是否正确，查看错误日志

**问题3：缓存文件冲突**
- 原因：重新执行时使用了旧缓存
- 解决：删除对应缓存文件后重新执行

## 使用示例

### 简单需求反构
```
/reverse-on-demand --requirement="分析用户认证模块" --demand-complexity=simple
```

### 简单需求反构（仅分析指定目录）
```
/reverse-on-demand --requirement="分析用户认证模块" --demand-complexity=simple --path="src/auth,src/common"
```

### 简单需求反构（排除目录）
```
/reverse-on-demand --requirement="分析用户认证模块" --demand-complexity=simple --exclude="**/test/**,**/build/**"
```

### 复杂需求反构
```
/reverse-on-demand --requirement="重构订单处理流程" --demand-complexity=complex
```

### 带需求文档引用
```
/reverse-on-demand @requirements/auth.md --demand-complexity=complex
```
