---
name: reverse-interfaces
description: 接口清单与接口详情反构的编排Skill. 当 reverse 的 --target 为 interfaces 或 all 的接口阶段时触发. 依赖 omni-doc/specs/logic_architecture/architecture.json（由 reverse-logic-architecture 生成）.
user-invokable: false
---

# 接口反构Skill（接口清单 + 详情文档）

## 概览（职责与输入输出）

- **职责**：从代码库中反构接口要素，生成：
  - 接口清单 JSON / Markdown
  - 单接口详情 Markdown 文档
- **输入前提**：
  - 用户通过 `reverse --target interfaces ...` 或 `--target all` 触发
  - 已根据 `--path` / `--files` / `--exclude` 等参数确定扫描范围
- **输出产物**：
  - 缓存目录：`{REPO_ROOT}/.cache/reverse/interfaces/`
    - `few-shot-examples.json`
    - `interface-list.json` 等
    - 状态文件：`.cache-status.json`
  - **逻辑架构输入（只读，由 `reverse-logic-architecture` 生成）**：
    - `{REPO_ROOT}/omni-doc/specs/logic_architecture/architecture.json`
  - 文档目录：
    - 接口详情：`{REPO_ROOT}/omni-doc/specs/interfaces/{接口ID}_{中文业务简要总结}.md`
    - 清单文档：`{REPO_ROOT}/omni-doc/specs/interfaces/接口清单.md`

> 本 Skill 仅重构“编排形式”，所有阶段逻辑、Token 管理与脚本调用方式，沿用原有阶段文档约定。

## 与 `reverse` 命令的关系

- `reverse` 负责：
  - 解析 `$ARGUMENTS`，统一处理 `--target`、`--path`、`--files`、`--exclude` 等参数；
  - 获取 `REPO_ROOT` 与全局缓存目录；
  - 当 `--target interfaces` 或 `--target all` 的接口阶段时，激活本 Skill。
- 本 Skill 负责：
  - 按阶段顺序驱动接口反构；
  - 调用接口识别/详情相关的基础 Skills 和脚本；
  - 与 todo 系统和缓存文件串联执行进度。

## 阶段总览

本 Skill 按以下阶段编排，阶段详细说明见本 Skill 目录下 `references/stages/`：

1. **阶段0：缓存状态检查**
2. **阶段1：逻辑架构产物校验**（读取 `omni-doc/specs/logic_architecture/architecture.json`，不生成）
3. **阶段2：接口扫描与示例生成**
4. **阶段3：接口清单扫描**
5. **阶段4：详细信息提取与文档生成**

Token 与并发控制遵循原文档中的预算表与“每轮最多 2 个 SubAgent”的统一规则。

## 阶段0：缓存状态检查

- **目标**：检查并初始化接口反构的缓存状态，支持断点续跑。
- **状态文件**：`{REPO_ROOT}/.cache/reverse/interfaces/.cache-status.json`
- 若不存在，则按原文档中的 JSON 模板创建，包含：
  - `few_shot_examples`
  - `interface_list`
  - `document_generation`
- **不再**在接口缓存中维护 `architecture_identification`；架构确认由 `reverse-logic-architecture` 的缓存状态文件管理。
- 在进入阶段1～4 前，根据对应字段的 `confirmed` / `progress` 决定是否跳过阶段（阶段1 为前置校验，见下）。

## 阶段1：逻辑架构产物校验

- **阶段说明来源**：本 Skill 内 [references/stages/01-logic-architecture-prerequisite.md](references/stages/01-logic-architecture-prerequisite.md)
- **目标**：确认共享逻辑架构产物已就绪；**不调用** `architecture-identifier`，**不写入** `architecture.json`。
- **必读路径**：`{REPO_ROOT}/omni-doc/specs/logic_architecture/architecture.json`
- **要点**：
  - 缺失或非法 JSON 时中止接口反构，并提示先执行 `reverse --target logic_architecture`（或全流程编排）；
  - 禁止使用已废弃路径 `.cache/reverse/interfaces/architecture.json`。

## 阶段2：接口扫描与示例生成

- **阶段说明来源**：本 Skill 内 [references/stages/02-interface-scanning-and-few-shot.md](references/stages/02-interface-scanning-and-few-shot.md)
- **目标**：初步扫描潜在接口定义，并生成接口识别 Few-shot 示例。
- **关键输出**：
  - `few-shot-examples.json`
- **要点**：
  - 结合架构信息与代码模式，识别接口候选；
  - 生成少量代表性 Few-shot 示例，供后续扫描阶段使用；
  - 强制生成接口数量预估（按代码行数千分之2基线）并输出类型分布；
  - 在交互模式下展示结果摘要并等待用户确认；
  - 按原文档规则更新缓存状态与 Token 预算。

## 阶段3：接口清单扫描

- **阶段说明来源**：本 Skill 内 [references/stages/03-interface-list-scanning.md](references/stages/03-interface-list-scanning.md)
- **目标**：在全局范围内识别所有接口，生成完整的接口清单。
- **扫描方式选择（按 `.cache/user_input` 预配置优先，其次交互强制选择）**：进入阶段3时按以下优先级确定方式A/方式B：
  - **步骤3.0：优先检查用户预配置文件**：先判断是否存在 `{REPO_ROOT}/.cache/user_input/interface-scan-mode.json`：
    - **若存在**：读取 JSON 中的 `"mode"` 字段（期望为 `"A"` 或 `"B"`），并将其作为阶段3的选择结果（不再要求用户重复选择）
    - **若不存在**：必须在交互中**强制**让用户选择 `"A"` 或 `"B"`（不得默认 A；不得替用户决定）
  - **方式A**：原有接口清单扫描——结合架构信息、Few-shot示例和用户约束规则，由 AI SubAgent 按文件分批识别
  - **方式B**：调用链扫描——通过执行仓库内的 Python 脚本完成语法解析、语义解析与接口识别，从根函数中识别接口；LLM 不可用时自动使用启发式规则。**方式 B 不调用任何子 Agent**（禁止使用 Task 启动 `call-chain-analyzer` 等），仅按阶段文档 3B.1～3B.3 依次执行脚本。
- **方式B 支持语言检查（进入方式B前必须执行）**：
  - **支持范围**：仅支持 **Java / Python / C++ / C** 四类代码库。
  - **判定时机**：
    - **从预配置读到 `"mode": "B"`** 时：在真正进入 3B.1 前，必须先做语言检查；不支持则提示并回退到方式A。
    - **用户交互选择方式B** 时：在真正进入 3B.1 前，必须先做语言检查；不支持则提示并回退到方式A。
  - **判定方法（按可用信息优先级，满足其一即可）**：
    1. **优先**：若阶段1输出的 `architecture.json` 中存在可用的主语言/技术栈字段（例如 `primary_language` / `languages` / `tech_stack` 之类），以其为准；
    2. 否则：按阶段3实际扫描范围（`--path/--files`）统计文件扩展名占比（例如 `.java/.py/.cpp/.c/.h/.hpp`），以占比最高的语言作为代码库主语言；
    3. 若仍无法可靠判定：视为“不支持方式B”，回退到方式A（避免误跑脚本导致无意义输出）。
  - **不支持时的用户提示（必须输出，且必须回退）**：当判定结果不在支持范围内，必须向用户输出等价提示：`【方式B不可用】当前代码库主语言为 <X>（不在 Java/Python/C/C++ 支持范围内），将自动回退使用方式A 继续接口清单扫描。`
- **无预配置时的强制选择提示（必须输出并等待用户回答）**：当 `{REPO_ROOT}/.cache/user_input/interface-scan-mode.json` 不存在时，必须提示用户：`【接口清单扫描】请选择扫描方式：A（默认接口清单扫描，按文件分批 + SubAgent）或 B（reverse 调用链扫描）。请输入 A 或 B（必须选择其一）。`
- **方式B“不可中断执行”强制约束（新增，必须遵守）**：
  - **一旦用户选择方式B并进入 3B.1～3B.3，主 Agent 必须把方式B视为“不可中断的长任务”**：不得在脚本未完成时结束回合/提前交还控制权/跳过等待，更不得因用户发送其他对话内容而中途停止方式B流程。
  - **前台可中断 ≠ 任务可终止**：允许将脚本移入后台以避免前台中断导致进程被杀，但必须将日志与 PID 落盘，并持续轮询直至出现明确“已退出 + 退出码”为止，然后才允许进入下一步。
  - **断点续跑**：若发生会话切换/前台中断/工具超时，必须按阶段文档中的“恢复检查”先判断进程是否仍在运行、输出文件是否已生成且有效，再决定继续等待/重跑/回退到方式A（仅限前置依赖失败或脚本失败且无法恢复时）。
- **方式 B 脚本位置**（执行前必须解析，避免“找不到工具”）：所有脚本均在仓库内，**优先** `{REPO_ROOT}/.claude/skills/reverse-interfaces/references/scripts/`，若不存在则用 `{REPO_ROOT}/claude/skills/reverse-interfaces/references/scripts/`。具体为：① 前置依赖 `reverse_by_call_chain/prepare_reverse_input.py`；② 接口识别 `reverse_by_call_chain/run_reverse_identify.py`（内部调用 `reverse_syntax_parser/main.py --step identify` 生成 `interface_functions_checklist.json` 并做存在性校验）；③ 转换 `reverse_by_call_chain/convert_reverse_interface_checklist.py`。详见 [references/stages/03-interface-list-scanning.md](references/stages/03-interface-list-scanning.md) 中 3B.1～3B.3。
- **操作**：
  - 若存在 `{REPO_ROOT}/.cache/user_input/interface-scan-mode.json`：按其 `"mode"` 执行（进入方式B前仍必须先做“方式B支持语言检查”）。
  - 若不存在：先向用户提问并等待其选择（A 或 B），再根据用户选择的扫描方式执行相应流程（用户选择B时进入方式B前仍必须先做“方式B支持语言检查”）。
- **关键输出**：
  - `interface-list.json`（含接口类型分类）
- **要点**：
  - 支持按文件/接口数量分批处理；
  - 使用接口识别类子 Agent 并发扫描（每轮最多 2 个 SubAgent，轮次间 /compact 压缩上下文）；
  - 结合 Few-shot 示例与约束规则进行过滤；
  - 强制执行“预估数量 vs 实际数量”质量闸门校验，不通过则触发重扫/重筛；
  - 当数量偏低时强制执行扫描文件覆盖度检测；疑似 `file_list` 覆盖不足时，交互模式须由用户确认是否全量扩展并重扫，非交互模式须自动全量扩展并重建批次后重扫；
  - 在交互模式下展示清单统计并等待用户确认。

## 阶段4：详细信息提取与文档生成

- **阶段说明来源**：本 Skill 内 [references/stages/04-detail-extraction-and-document-generation.md](references/stages/04-detail-extraction-and-document-generation.md)
- **目标**：为每个接口提取完整详细信息，并直接生成最终文档。
- **关键输出**：
  - 单接口详情文档：`{REPO_ROOT}/omni-doc/specs/interfaces/{接口ID}_{中文业务简要总结}.md`
  - 汇总清单文档：`{REPO_ROOT}/omni-doc/specs/interfaces/接口清单.md`
- **要点**：
  - 对接口进行分批处理，每轮最多两个接口详情子 Agent，并在轮次之间执行 `/compact`；
  - 严格按照既有模板与字段规范生成文档；
  - 详情文档生成后必须先执行文件名校验与自动修复脚本，确保文件名满足系统规范；
  - 每轮后必须执行“全量文档覆盖校验”，未覆盖全部接口时继续分批处理，禁止以示例文档结束；
  - 完成后更新 `document_generation` 状态，并在交互模式下允许用户查看代表性接口文档摘要。

## 缓存、Todo 与 Token 管理

- **缓存与路径**：沿用原 `reverse-interfaces.md` 中关于 `.cache/reverse/interfaces/` 与 `omni-doc/specs/interfaces` 的约定。
- **Todo 管理**：
  - 依赖 `reverse` 统一初始化的 todo 项（接口主任务 + 阶段0～4 共 5 个阶段子任务）；
  - 本 Skill 在阶段开始/结束时更新对应 todo 的 `in_progress` / `completed` 状态。
- **Token 管理**：
  - 遵循原文档中的整体预算与关键控制点（阶段间清理、分轮执行、强制检查点、极简返回 JSON）。

## 实现文档（本 Skill 内）

阶段 3（接口清单扫描）与阶段 4（详情文档生成）的执行逻辑由以下实现文档定义：

- [references/implementation/interface-recognition.md](references/implementation/interface-recognition.md)（单文件接口识别，阶段 3 子 Agent 按此执行）
- [references/implementation/interface-detail-analysis.md](references/implementation/interface-detail-analysis.md)（单接口详情分析 → 文档，阶段 4 子 Agent 按此执行）

## 参考文档（本 Skill 内）

本 Skill 的详细实现规范位于本目录下 `references/`：

- 阶段 1：[references/stages/01-logic-architecture-prerequisite.md](references/stages/01-logic-architecture-prerequisite.md)
- 阶段 2：[references/stages/02-interface-scanning-and-few-shot.md](references/stages/02-interface-scanning-and-few-shot.md)
- 阶段 3：[references/stages/03-interface-list-scanning.md](references/stages/03-interface-list-scanning.md)
- 阶段 4：[references/stages/04-detail-extraction-and-document-generation.md](references/stages/04-detail-extraction-and-document-generation.md)
- 规则与数据：[references/core-rules.md](references/core-rules.md)、[references/data.md](references/data.md)、[references/token-management.md](references/token-management.md)

AI Agent 在执行本 Skill 时，应读取上述文档并严格按照其中描述的阶段和脚本调用方式执行。

