---
name: reverse-interfaces
description: 接口清单与接口详情反构编排 Skill。当 reverse 的 --target 为 interfaces 或 all 的接口阶段时触发；依赖 logic_architecture/architecture.json。产出 interface-list.json、接口详情 Markdown、接口清单.md。关键词：reverse interfaces、接口反构、interface-list、API 反构。
user-invokable: false
allowed-tools: Read, Write, Edit, Glob, Grep, Agent, Task, TaskCreate, TaskUpdate, TaskList, TaskGet, Bash(python3 *)
when_to_use: 当 reverse 编排执行 --target interfaces 或 all 的接口阶段，或需要从代码库反构接口清单与接口详情文档时使用。
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

> 编排与约束已标准化；阶段执行细节见 `references/stages/`，子 Agent 见 `agents/`。


## 路径变量约定（执行前必读）

本 Skill 阶段文档中引用了以下路径变量，执行阶段命令前须先解析：

- `${CLAUDE_PLUGIN_ROOT}`：omni-reverse 插件安装根（运行期注入；指向本 skill 内专属脚本，如 `${CLAUDE_PLUGIN_ROOT}/skills/reverse-<X>/scripts/`）。
- `${DSDD}`：共享插件 omni-dsdd 安装根（含共享 `scripts/` 与 `omni-infra/`）。**首次使用前必须解析**：
  ```bash
  DSDD="$(bash "${CLAUDE_PLUGIN_ROOT}/scripts/resolve-dsdd-root.sh")" || { echo "缺少 omni-dsdd，中止"; exit 1; }
  ```
  解析器优先用 `${CLAUDE_PLUGIN_ROOT}/../omni-dsdd`，回退到脚本相对位置推算；失败则提示需与 omni-reverse 同 marketplace 安装 omni-dsdd。
- `{REPO_ROOT}` / `${CLAUDE_WORKING_DIR}`：被反构的代码工程根（运行期产物，与插件位置无关）。
- `${CLAUDE_SKILL_DIR}`：本 skill 自身目录（指向本 skill 内 `references/scripts/` 等自包含资源）。

> 说明：`${DSDD}` 不是运行期自动注入的变量，必须经 `resolve-dsdd-root.sh` 取值后方可使用。

## 路径解析

执行前统一解析路径（各阶段文档引用本节约定的变量）：

| 变量 | 解析顺序 |
|------|----------|
| 本 Skill 目录 | 优先 `{REPO_ROOT}/.claude/skills/reverse-interfaces/`，否则 `{REPO_ROOT}/claude/skills/reverse-interfaces/` |
| 捆绑 Python 脚本 | `{本 Skill 目录}/references/scripts/` |
| 项目 Python 脚本 | `${DSDD}/scripts/python/`（如 `merge_interface_results.py`） |
| 子 Agent 定义 | `{REPO_ROOT}/agents/interface-recognizer.md`、`interface-analyzer.md`（或插件 agents 目录） |

## 行为准则

以下规则在整个会话期间有效，不因对话长度而放松：

1. ❗ **阶段按序执行，禁止跳过**：所有阶段（0→1→2→3→4）必须按顺序执行；每个阶段开始前必须读取缓存状态文件（`.cache-status.json`）判断是否需要执行，已确认的阶段不得重新执行。跳过阶段必须显式记录原因。
2. ❗ **每步发现必须引用来源**：所有发现、结论、产物描述必须引用来源（文件路径 + 行号或章节）。无来源的结论 = 不允许输出。阶段间依赖的数据必须通过缓存文件传递，不得在上下文中假设。
3. ❗ **禁止伪造或跳过批次**：禁止创建空批次文件模拟完成，禁止跳过用户确认，禁止跳过全量校验脚本（`ensure_all_interface_docs_generated.py`）的通过条件。

## 禁止输出

- 开场白（"让我来分析..." / "首先我们需要..."）
- 工具调用描述（"我将使用 Read 工具..." / "正在调用脚本..."）
- 已知信息的复述（用户刚说的参数、路径、文件刚读的内容）
- 以"示例文档"代替全量文档（阶段 3/4 的产物必须是全量，禁止只生成几条作为样例）
- 在未通过全量校验（`ensure_all_interface_docs_generated.py` 退出码 ≠ 0）时输出"已完成"

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

1. **阶段0：缓存状态检查** ✅ Checkpoint: `阶段0完成: .cache-status.json 已就绪`
2. **阶段1：逻辑架构产物校验** ✅ Checkpoint: `阶段1完成: architecture.json 校验通过 / 中止接口反构`
3. **阶段2：接口扫描与示例生成** ✅ Checkpoint: `阶段2完成: few-shot-examples.json + interface-estimation.json 已生成，用户已确认`
4. **阶段3：接口清单扫描** ✅ Checkpoint: `阶段3完成: interface-list.json 全量生成，质量闸门已通过，用户已确认`
5. **阶段4：详细信息提取与文档生成** ✅ Checkpoint: `阶段4完成: 全量接口详情文档已生成，接口清单.md 已生成，ensure_all 通过`

### 依赖链

- 阶段1 → 阶段2：`architecture.json`（只读）作为阶段2的模式识别输入
- 阶段2 → 阶段3：`few-shot-examples.json` + `interface-types.json` + `constraints.json` + `interface-estimation.json` 作为阶段3的扫描输入
- 阶段3 → 阶段4：`interface-list.json` 作为阶段4的输入
- **禁止重新生成**：阶段间依赖的数据必须从缓存文件读取，不得在后续阶段中重新搜索或重新生成已由前序阶段输出的数据
- **交叉验证**：写入最终产物前，必须验证缓存文件中的状态计数与实际产物数量一致（由 `ensure_all_interface_docs_generated.py` 等脚本执行）

Token 与并发控制遵循原文档中的预算表与「每轮最多 2 个 SubAgent」的统一规则。

## 子 Agent 依赖

| 子 Agent | 阶段 | 实现依据 | 启动方式 |
|----------|------|----------|----------|
| `omni-reverse:interface-recognizer` | 3（方式 A） | `agents/interface-recognizer.md` + [interface-recognition.md](references/implementation/interface-recognition.md) | Task，`subagent_type: omni-reverse:interface-recognizer` |
| `omni-reverse:interface-analyzer` | 4 | `agents/interface-analyzer.md` + [interface-detail-analysis.md](references/implementation/interface-detail-analysis.md) | Task，`subagent_type: omni-reverse:interface-analyzer` |

**禁止**：方式 B 使用 Task 启动 `call-chain-analyzer` 或其他子 Agent（仅按阶段文档执行脚本）。

## 子 Agent 委派规则

本 Skill 在阶段 3（方式 A）和阶段 4 使用上表子 Agent 并发处理批次，必须遵循以下合并协议：

- **分工边界**：每个子 Agent 只处理自己负责的批次（由 `batch-mapping.json` 分配），不得处理其他批次的文件或接口。
- **结果归并**：主 Agent 收集所有批次结果后，由专用合并脚本（`${DSDD}/scripts/python/merge_interface_results.py`、`ensure_all_interface_docs_generated.py`）统一归并。脚本不存在或退出码非 0 时不得手工拼 `interface-list.json`。禁止手工拼接。
- **合并检查清单**：
  1. **去重**：检查不同批次的输出是否重复（同一接口 ID 只出现一次），重复时由合并脚本统一去重。
  2. **一致性**：检查所有批次的输出字段是否一致（`interface_id`、`interface_type`、`processing_status` 等字段格式统一），不一致时按统一 schema 修复。
  3. **计数验证**：验证批次接口总数 = 所有批次结果去重后总数 = `interface-list.json` / `interface-estimation.json` 中的预期数量，三者不一致时必须排查原因，禁止忽略差异。

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
    - **若存在**：读取 JSON 中的 `"mode"` 字段（期望为 `"A"` 或 `"B"`）和 `"allow_mode_downgrade"` 字段（可选，默认 `true`）
      - `"allow_mode_downgrade": true`：当方式 B 不支持或执行失败时，允许自动切换到方式 A
      - `"allow_mode_downgrade": false`：当方式 B 不支持或执行失败时，必须报错并退出当前阶段（禁止自动回退到方式 A）
      - 若缺失 `"allow_mode_downgrade"`：按 `true` 处理（向后兼容）
    - **若存在**：将 `"mode"` 作为阶段3的选择结果（不再要求用户重复选择）
    - **若不存在**：必须在交互中**强制**让用户选择 `"A"` 或 `"B"`（不得默认 A；不得替用户决定）
  - **方式A**：原有接口清单扫描——结合架构信息、Few-shot示例和用户约束规则，由 AI SubAgent 按文件分批识别
  - **方式B**：调用链扫描——通过执行仓库内的 Python 脚本完成语法解析、语义解析与接口识别，从根函数中识别接口；LLM 不可用时自动使用启发式规则。**方式 B 不调用任何子 Agent**（禁止使用 Task 启动 `call-chain-analyzer` 等），仅按阶段文档 3B.1～3B.3 依次执行脚本。
- **方式B 支持语言检查（进入方式B前必须执行）**：
  - **支持范围**：仅支持 **Java / Python / C++ / C** 四类代码库。
  - **判定时机**：
    - **从预配置读到 `"mode": "B"`** 时：在真正进入 3B.1 前，必须先做语言检查；
      - `allow_mode_downgrade=true` 时，不支持则提示并回退到方式A
      - `allow_mode_downgrade=false` 时，不支持则报错并退出当前阶段
    - **用户交互选择方式B** 时：在真正进入 3B.1 前，必须先做语言检查；
      - 未显式配置时按 `allow_mode_downgrade=true` 处理
  - **判定方法（按可用信息优先级，满足其一即可）**：
    1. **优先**：读取阶段1已校验的 `{REPO_ROOT}/omni-doc/specs/logic_architecture/architecture.json`（由 `reverse-logic-architecture` 生成）中的主语言/技术栈字段（如 `primary_language` / `languages` / `tech_stack`），以其为准；
    2. 否则：按阶段3实际扫描范围（`--path/--files`）统计文件扩展名占比（例如 `.java/.py/.cpp/.c/.h/.hpp`），以占比最高的语言作为代码库主语言；
    3. 若仍无法可靠判定：视为“不支持方式B”；
      - `allow_mode_downgrade=true` 时回退到方式A
      - `allow_mode_downgrade=false` 时报错退出当前阶段（避免误跑脚本导致无意义输出）。
  - **不支持时的用户提示**：
    - `allow_mode_downgrade=true`：`【方式B不可用】当前代码库主语言为 <X>（不在 Java/Python/C/C++ 支持范围内），将自动回退使用方式A继续接口清单扫描。`
    - `allow_mode_downgrade=false`：`【方式B不可用】当前代码库主语言为 <X>（不在 Java/Python/C/C++ 支持范围内），且已配置禁止降级切换（allow_mode_downgrade=false），接口清单扫描阶段将报错退出。`
- **无预配置时的强制选择提示（必须输出并等待用户回答）**：当 `{REPO_ROOT}/.cache/user_input/interface-scan-mode.json` 不存在时，必须提示用户：`【接口清单扫描】请选择扫描方式：A（默认接口清单扫描，按文件分批 + SubAgent）或 B（reverse 调用链扫描）。请输入 A 或 B（必须选择其一）。`
- **方式B“不可中断执行”强制约束（新增，必须遵守）**：
  - **一旦用户选择方式B并进入 3B.1～3B.3，主 Agent 必须把方式B视为“不可中断的长任务”**：不得在脚本未完成时结束回合/提前交还控制权/跳过等待，更不得因用户发送其他对话内容而中途停止方式B流程。
  - **前台可中断 ≠ 任务可终止**：允许将脚本移入后台以避免前台中断导致进程被杀，但必须将日志与 PID 落盘，并持续轮询直至出现明确“已退出 + 退出码”为止，然后才允许进入下一步。
  - **断点续跑**：若发生会话切换/前台中断/工具超时，必须按阶段文档中的“恢复检查”先判断进程是否仍在运行、输出文件是否已生成且有效，再决定继续等待/重跑/回退到方式A（仅限前置依赖失败或脚本失败且无法恢复时）。
- **方式 B 脚本位置**（执行前必须解析，避免“找不到工具”）：所有脚本均在仓库内，**优先** `{REPO_ROOT}/.claude/skills/reverse-interfaces/references/scripts/`，若不存在则用 `{REPO_ROOT}/claude/skills/reverse-interfaces/references/scripts/`。具体为：① 前置依赖 `reverse_by_call_chain/prepare_reverse_input.py`；② 接口识别 `reverse_by_call_chain/run_reverse_identify.py`（内部调用 `reverse_syntax_parser/main.py --step identify` 生成 `interface_functions_checklist.json` 并做存在性校验）；③ 转换 `reverse_by_call_chain/convert_reverse_interface_checklist.py`。详见 [references/stages/03-interface-list-scanning.md](references/stages/03-interface-list-scanning.md) 中 3B.1～3B.3。
- **操作**：
  - 若存在 `{REPO_ROOT}/.cache/user_input/interface-scan-mode.json`：按其 `"mode"` 执行，并应用 `"allow_mode_downgrade"`（缺省 `true`）。
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

## 错误处理

### 阶段级错误处理

各阶段的错误处理策略如下：

- **阶段1（架构校验）**：缺失 `architecture.json` 时中止接口反构，提示先执行 `reverse --target logic_architecture`
- **阶段2（示例生成）**：模式识别失败时使用默认模式继续
- **阶段3（清单扫描）**：
  - 方式A：批次处理失败时标记状态并重试
  - 方式B：脚本执行失败或前置依赖不满足时
    - `allow_mode_downgrade=true`：自动回退到方式A
    - `allow_mode_downgrade=false`：直接报错退出当前阶段
- **阶段4（详情生成）**：文档生成失败时保持批次为 `pending` 并重试

### 断点续跑机制

所有阶段支持断点续跑：
- 通过 `.cache/reverse/interfaces/.cache-status.json` 记录进度
- 通过批次状态文件记录每个批次的处理状态
- 重新运行时自动从上次中断处继续

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

## 技能与脚本依赖

### 前置技能

- `reverse-logic-architecture`：生成 `omni-doc/specs/logic_architecture/architecture.json`
- `reverse-shared`：确认模板 `references/confirmation-template.md`

### 本 Skill 捆绑脚本（`references/scripts/`）

- `estimate_interface_counts.py`、`validate_interface_quality_gate.py`、`detect_interface_scan_coverage.py`
- `ensure_all_interface_docs_generated.py`、`ensure_interface_batch_docs_generated.py`、`validate_and_fix_interface_doc_filenames.py`
- `reverse_by_call_chain/*`（阶段 3 方式 B）

### 项目脚本（`${DSDD}/scripts/python/`）

- `merge_interface_results.py`（阶段 3 方式 A 合并 `interface-list.json`，**必需**；缺失则中止，禁止手工合并）

## 外部依赖说明

本 Skill 的阶段文档中引用了以下项目外部文件，这些文件由 OmniSpec 框架或 reverse 全局编排提供：

- **`{REPO_ROOT}/.claude/skills/reverse-shared/references/confirmation-template.md`**：OmniSpec 公共技能库（`reverse-shared`）中的统一确认模板，用于阶段间的交互确认机制。此文件由 `reverse-shared` 技能提供，本 Skill 仅引用其路径，不在本 Skill 目录内维护。
- **`.omni-infra/templates/` 下的模板文件**（如 `interface-type-selection-template.md`、`constraint-configuration-template.md`、`final-confirmation-template.md`）：OmniSpec 项目内的交互式模板，用于用户配置和确认。来源：`{REPO_ROOT}/.omni-infra/templates/`
- **`${DSDD}/scripts/bash/reverse/interfaces/utils/`** 和 **`${DSDD}/scripts/powershell/reverse/interfaces/utils/`**：OmniSpec 项目内的 bash/PowerShell 工具脚本，用于批次管理、进度跟踪等。**注意**：本 Skill 自带的 Python 脚本位于 `${CLAUDE_SKILL_DIR}/references/scripts/`，而 OmniSpec 项目内的脚本位于 `${DSDD}/scripts/` 下，执行时请注意路径来源

如需完整执行本 Skill，请确保 OmniSpec 项目已正确安装上述外部依赖文件。

## 事实性约束

- **来源引用要求**：所有结论、发现和产物描述必须引用具体来源（文件路径 + 行号/章节，或脚本退出码）。无来源引用 = 不允许输出。
- **零结果处理表**：

| 场景 | 正确输出 | 禁止输出 |
|------|---------|---------|
| 阶段1: `architecture.json` 不存在 | 中止接口反构，提示先执行 `reverse --target logic_architecture` | 假设架构已就绪继续执行 |
| 阶段2: 模式识别无结果 | 输出现有模式（空列表）+ 提示调整接口类型配置 | 推测"代码库无接口"作为结论 |
| 阶段3: 接口数量远低于预估 | 触发覆盖度检测，提示全量扩展 | 假设预估有误直接输出低数量清单 |
| 阶段3: 方式B脚本执行失败 | 退回方式A，向用户说明原因 | 假设方式B已成功继续流程 |
| 阶段4: 接口详情文档校验失败 | 保持批次为 `pending`，重试同批次 | 跳过缺失文档继续下一批次 |
| `ensure_all_interface_docs_generated.py` 退出码 ≠ 0 | 继续分批生成，直至全部通过 | 输出"已完成"并结束阶段 |

- **标注分级**：
  - 无标注 = 确认结果（工具确认的产物）
  - ⚠️ 降级 = 降级分析（工具不可用时的人工推断，须说明降级原因）
  - 💡 建议 = 通用建议（不改变核心决策）

本 Skill 输出的判断性结论必须满足以下证据要求：

| Claim Type | 适用场景 | Required Evidence | Counter-Evidence 检查 |
|------------|---------|-------------------|----------------------|
| `structural` | `interface-list.json` / 接口详情文档生成完成 | 脚本退出码为 0 + 文件存在且非空 + 字段完整（`interface_id`、`interface_type` 等必填字段非空） | 检查是否仅生成了示例而非全量（`full_list_generated == true`） |
| `behavioral` | 接口数量质量闸门通过/不通过 | `validate_interface_quality_gate.py` 退出码 + 报告字段 `mandatory_flags.quality_gate_passed == true` | 检查是否因覆盖不足（`file_list.json` 规模）导致数量偏低，而非识别规则失效 |
| `empirical` | 接口数量预估 | `estimate_interface_counts.py` 输出 + 基线值（`ceil(total_code_lines * 0.002)`） | 检查是否低于基线（若是则标记 `under_estimated=true` 并触发扩范围） |
| `structural` | 阶段跳过判断 | `.cache-status.json` 中对应字段 `confirmed == true` | 检查状态文件更新时间是否在合理范围内 |

**通用规则**：
- Signal 只能启动调查，不能直接输出强结论
- 无 script 退出码 + 文件存在 → `unresolved`
- 有退出码但 scope 不清 → `tentative`
- 未检查 counter-evidence → 最高 `tentative`
- `ensure_all_interface_docs_generated.py` 未通过（退出码 ≠ 0）→ 不得输出"已完成"，不得结束阶段

