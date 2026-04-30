---
name: reverse-on-demand
description: 按需反构（基于需求意图）的编排Skill. 当 reverse 的 --target 为 on-demand 时触发.
---

# 按需反构Skill（on-demand）

## 准备：

**SDD环境初始化**： 执行`bash ${CLAUDE_PLUGIN_ROOT}/scripts/bash/init_infra.sh ${CLAUDE_PLUGIN_ROOT} !`pwd` `
根据返回值进行处理：
- 0: 已经准备好了，继续后续步骤
- 其他：执行失败，终止后续内容
---

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

## 与 `reverse` 命令的关系

- `reverse` 负责：
  - 解析 `$ARGUMENTS`，包括 `--requirement`、`--intent`、`--demand-complexity` 等；
  - 解析交互模式（语言要求始终为中文）；
  - 激活本 Skill 并传入参数。
- 本 Skill 负责：
  - 严格按阶段文件的说明执行；
  - 在需要时调用通用分支管理与按需反构阶段脚本/子 Agent。

## 阶段总览

本 Skill 按以下阶段执行，阶段详细说明见本目录下 `references/stages/`：

1. **阶段1：分支和特性准备**
2. **阶段2：深度架构识别**
3. **阶段3：按需反构执行（根据需求复杂度 simple/complex 分支到 3a/3b）**

## 阶段1：分支和特性准备

- **阶段说明来源**：
  - 通用分支管理：调用 Skill `create-branch`（`skills/create-branch/SKILL.md`）
  - 按需检查已有产物：本 Skill 内 [references/stages/01.5-check-existing-products.md](references/stages/01.5-check-existing-products.md)
- **目标**：
  - 确定或创建特性分支与特性目录 `FEATURE_DIR`；
  - 检查是否已有完整按需反构产物，必要时允许用户选择中止或重录。
- **关键输出变量**：
  - `REPO_ROOT`：仓库根目录（绝对路径）
  - `BRANCH_NAME`：特性分支名
  - `FEATURE_DIR`：特性目录（绝对路径）
  - `SPEC_FILE`：由 `create-branch` 返回（仅记录路径，不作为 on-demand 依赖）
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
- **目标**：为复杂需求提供阶段化产出、用户确认点与逐功能深度分析。
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

执行复杂流程步骤5或简单流程步骤2.6中的波及检索时，除各 stage 文档既有要求外，**必须**同时遵守 [references/stages/03b-complex-on-demand-reverse.md](references/stages/03b-complex-on-demand-reverse.md) 中「波及功能分析强制补充步骤」：

1. **核心目录完整文件清单**：对已识别为核心分析范围的目录，先用 `ls`（或递归列出）得到完整文件清单，不遗漏同目录成员。
2. **扩大搜索路径**：全文检索（grep 等）须覆盖脚本、配置、公共模块、构建/部署相关路径等需求常关联位置，以及架构与需求线索指向的路径；不得在无证据时默认将检索范围收窄为单一子树。
3. **按调用链与资源引用向下追溯**：发现代码引用外部资源（配置、模板、数据或静态资源文件等）后，须立即检索该资源所在目录并沿配置/资源依赖继续追溯，纳入候选波及范围。

## 子 Agent 调用统一约束

- 子 Agent 只能在阶段文档规定的步骤中被调用：
  - 简单需求：`simple-on-demand-reverse-agent`
  - 复杂需求：`complex-on-demand-function-analyzer`
- 禁止：
  - 直接将 stage 文档当作 Agent；
  - 跳过 preflight/确认步骤直接批量调用子 Agent。

## 参考文档（本 Skill 内）

本 Skill 的详细规范位于本目录下 `references/`，分支管理由 Skill `create-branch` 提供：

- 阶段 1 分支管理：调用 Skill `create-branch`
- 阶段 1 检查已有产物：[references/stages/01.5-check-existing-products.md](references/stages/01.5-check-existing-products.md)
- 阶段 2：[references/stages/02-deep-architecture-identification.md](references/stages/02-deep-architecture-identification.md)
- 阶段 3a：[references/stages/03a-simple-on-demand-reverse.md](references/stages/03a-simple-on-demand-reverse.md)
- 阶段 3b：[references/stages/03b-complex-on-demand-reverse.md](references/stages/03b-complex-on-demand-reverse.md)

执行本 Skill 时，AI Agent 必须读取上述文档并严格按照其中的说明与约束执行。

