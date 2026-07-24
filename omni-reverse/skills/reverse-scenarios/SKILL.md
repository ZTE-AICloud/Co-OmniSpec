---
name: reverse-scenarios
description: 场景清单与单场景文档反构的编排Skill。识别业务场景、生成场景清单（含超链接）及 SCN 单场景文档。当 reverse 的 --target 为 scenarios 或 all 的场景阶段时触发.
user-invokable: false
---

# 场景反构Skill（场景清单 + 单场景文档）

## 概览（职责与输入输出）

- **职责**：基于既有的接口清单 / 功能清单 / 测试用例等反构产物，完成：
  - 场景模式识别与 few-shot 示例生成
  - 场景清单构建（含统计信息）
  - 单场景 Markdown 文档生成
- **输入前提**：
  - 建议已完成接口 / 功能等前置反构（由其它 reverse-* skills 负责）
  - 用户通过 `reverse --target scenarios ...` 或 `--target all` 触发
  - 参数由 `reverse` 命令解析后通过 `$ARGUMENTS` 传入，支持的参数：
    - `--path <path>`：要扫描的代码路径（必选）
    - `--exclude <pattern>`：排除的文件模式（可选，可多次使用）
    - `--interactive`：交互模式，生成结果后等待用户确认（可选）
    - `--clear-cache`：清理缓存，从头开始（可选）
- **输出产物**：
  - 缓存目录：`{REPO_ROOT}/.cache/reverse/scenarios/`
    - `scenario-patterns.json`
    - `few-shot-examples.json`
    - `scenario-types.json`
    - `constraints.json`
    - `scenario-list.json` 及批次相关 JSON
  - 文档目录：`{REPO_ROOT}/omni-doc/specs/scenarios/`
    - `场景清单.md`（汇总表，含指向各单场景文档的 Markdown 超链接）
    - `SCN-XXX-*.md`（单场景文档）

> **核心要求**：只消费既有产物，不重复做架构识别；严格使用缓存与分批机制；所有交互说明和输出必须为中文。


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

## 行为准则（整个会话期间有效，不因对话长度放松）

1. ❗ **来源引用**：每个发现/修改必须引用来源（文件路径 + 章节/行号）—— 每次输出前自检
2. ❗ **来源约束**：无引用来源的结论 = 不允许输出；来源引用要求同样适用于子代理的输出
3. ❗ **禁止单边修复**：改文档必须同步改实现，改实现必须同步改文档—— 每次修改前自检

> 本 Skill 关键规则（Token 控制、Checkpoint 输出、失败降级）定义在 `references/token-management.md` 和各阶段文档 `references/stages/*.md` 中，执行时须同步引用。

## 与 `reverse` 命令的关系

- 当命令层执行：
  - `reverse --target scenarios ...`，或
  - `reverse --target all ...` 且执行到“场景反构阶段”时，
- `reverse` 负责：
  - 解析 `$ARGUMENTS`（`--path` / `--exclude` / `--interactive` 等）
  - 获取 `REPO_ROOT` 与通用缓存目录
  - 然后**激活本 Skill `omni-reverse:reverse-scenarios`**，将必要上下文（参数、路径、缓存位置）作为前置条件提供。
- 本 Skill 内部按实现文档执行（见本目录 `references/implementation/`）：
  - [references/implementation/scenario-recognition.md](references/implementation/scenario-recognition.md)（单文件场景识别）
  - [references/implementation/scenario-detail-analysis.md](references/implementation/scenario-detail-analysis.md)（单场景详情 → 文档）
  - 以及场景批次相关脚本（见阶段文档）。

## 阶段总览

本 Skill 按以下阶段编排，阶段详细说明见本目录下 `references/stages/`：

1. **阶段0：缓存状态检查**
   - ✅ Checkpoint: 阶段0完成: 状态文件已读取, confirmed字段已确认
   - 验收: `status.confirmed == true` → 跳过；否则执行
   - 失败: 状态文件格式错误 → 报错终止

2. **阶段1：场景模式识别与 few-shot 示例生成**
   - ✅ Checkpoint: 阶段1完成: scenario-patterns.json 已确认, few-shot-examples.json 已确认
   - 验收: `scenario_patterns.confirmed == true AND few_shot_examples.confirmed == true` → 跳过；否则执行
   - 失败: 模式识别超时 → 标记 partial，跳过进入阶段2

3. **阶段2：场景清单构建**
   - ✅ Checkpoint: 阶段2完成: 已处理 N 个批次, scenario-list.json 已生成
   - 验收: `scenario_list.confirmed == true` → 跳过；否则执行
   - 失败: 批次处理失败 → 报错记录，继续下一批次

4. **阶段3：单场景文档生成 + 场景清单**
   - ✅ Checkpoint: 阶段3完成: SCN-XXX-*.md × N 个文档已生成, 场景清单.md 已生成
   - 验收: `document_generation.confirmed == true` → 跳过；否则执行
   - 失败: 文档生成失败 → 标记 failed，继续下一场景

运行时需结合 todo 系统：
- 进入本 Skill 前，`reverse` 会为 `--target scenarios` 创建顶层 todo；
- 本 Skill 在每个阶段开始时将对应 todo 标记为 `in_progress`，完成后标记为 `completed`。

## 阶段0：缓存状态检查

- **目标**：检查并初始化场景反构的缓存状态，支持断点续跑。
- **缓存状态文件**：`{REPO_ROOT}/.cache/reverse/scenarios/.cache-status.json`
- 若状态文件不存在，按原阶段文档约定结构创建（包含 `scenario_patterns`、`few_shot_examples`、`scenario_list`、`document_generation` 等字段）。
- 每个后续阶段开始前读取该文件，根据 `confirmed` / `progress` 决定是否跳过当前阶段。

> 详细字段与初始化规则参见本 Skill 内 `references/` 中的阶段文档。

## 阶段1：场景模式识别与 few-shot 示例生成

- **目标**：识别场景模式特征并生成 few-shot 示例，为场景候选抽取提供支撑。
- **规范来源**：本 Skill 内 [references/stages/01-scenario-pattern-identification-and-few-shot.md](references/stages/01-scenario-pattern-identification-and-few-shot.md)
- **关键输出**：
  - `scenario-patterns.json`
  - `few-shot-examples.json`
  - `scenario-types.json`
  - `constraints.json`
- **主要要点（保持现有实现方式）**：
  - 清理上一阶段上下文，强制 Token 检查与上下文清空；
  - 读取/初始化缓存状态，若 `scenario_patterns` 和 `few_shot_examples` 已确认则可跳过；
  - 支持用户注入配置 `.cache/user_input/scenario-identification-rules.yaml`（简化配置 → 结构化 JSON）；
  - 支持基于模板的场景类型选择与约束规则配置；
  - 分析代码库生成场景模式与 few-shot 示例；
  - 展示结果并在交互模式下等待用户确认，更新缓存状态。

## 阶段2：场景清单构建

- **目标**：基于阶段1 的模式与示例，扫描代码库识别所有业务场景，生成正式的场景清单。
- **规范来源**：本 Skill 内 [references/stages/02-scenario-inventory-construction.md](references/stages/02-scenario-inventory-construction.md)
- **关键输出**：
  - 主清单（缓存）：`scenario-list.json`（及批次 JSON）
  - 批次结果：`scenario-list-batch-{batch_number}.json`
  - 批次映射与状态：`batch-mapping.json`、`scenario_scanning-batch-status.json`
- **主要要点**：
  - 清理上下文、Token 检查；
  - 若 `scenario_list.confirmed == true` 且文件存在则可跳过；
  - 读取阶段1 输出（patterns / few-shot / types / constraints）；
  - 按文件数量选择单批或分批模式：
    - 文件数 > 阈值：使用生成批次脚本 + 多个按 [references/implementation/scenario-recognition.md](references/implementation/scenario-recognition.md) 执行的子 Agent 并发处理；
    - 文件数 ≤ 阈值：创建虚拟批次，串行或小规模并发处理；
  - 使用官方批次脚本管理状态与进度（`generate-scenario-batches.sh`、`get-next-batches.sh`、`update-batches-status.sh`、`verify-batches-completion.sh` 等）；
  - 所有批次完成后调用合并脚本生成 `scenario-list.json`；
  - 在交互模式下展示统计信息并等待用户确认，确认后将 `scenario_list.confirmed` 标记为 true。

## 阶段3：单场景文档生成

- **目标**：根据确认后的场景清单，为每个场景生成独立 Markdown 文档。
- **规范来源**：本 Skill 内 [references/stages/03-scenario-detail-materialization.md](references/stages/03-scenario-detail-materialization.md)
  - **关键输入**：
  - `scenario-list.json`（包含所有场景及 `processing_status` 等状态字段）
  - 场景详情模板：优先使用项目特定模板，否则使用 `.omni-infra/templates/default/reverse-scenario-detail-template.md`
- **关键输出**：
  - `{REPO_ROOT}/omni-doc/specs/scenarios/SCN-XXX-场景名称.md`
  - `{REPO_ROOT}/omni-doc/specs/scenarios/场景清单.md`（各场景条目含指向对应 SCN 文档的相对路径超链接）
  - 更新后的 `scenario-list.json` 中的场景处理状态（`processing_status` 等）
- **主要要点**：
  - 清理上下文、Token 控制；
  - 读取场景总数，决定单批或分批：
    - 分批时调用场景详情批次脚本（如 `create_scenario_detail_batches.sh`、`get_next_scenario_detail_batches.sh` 等）；
  - 使用多个按 [references/implementation/scenario-detail-analysis.md](references/implementation/scenario-detail-analysis.md) 执行的子 Agent 并行处理批次；
  - 每批结束后更新批次状态、进度、耗时，并清理上下文；
  - 所有场景处理完成后，按 `templates/reverse-scenario-inventory-template.md` 生成 `场景清单.md`；
  - 检查输出目录与状态文件一致性；
  - 在交互模式下展示摘要和样例，确认后将 `document_generation.confirmed` 标记为 true。
  - 重录（`--clear-cache`）时，生成前清理 `场景清单.md` 与已有 `SCN-*.md`。

## 依赖链声明

**阶段间数据传递**（禁止重新生成，后步引用前步实际输出）：
- 阶段0 输出 = `.cache-status.json`（confirmed/progress 状态）→ 阶段1/2/3 输入
- 阶段1 输出 = `scenario-patterns.json` + `few-shot-examples.json` + `scenario-types.json` + `constraints.json` → 阶段2 输入
- 阶段2 输出 = `scenario-list.json` + `scenario-list-batch-*.json` → 阶段3 输入
- 阶段3 输出 = `omni-doc/specs/scenarios/SCN-XXX-*.md` + `场景清单.md` → 外部消费（requirements 等下游读取 SCN 文档）

**禁止重新生成**: 后续阶段必须引用前序实际输出文件，不得重新扫描或重新推断。

**交叉验证**: 写入前检查目标文件是否存在；若文件数/计数与预期不符，报告差异但不阻止执行。

## 缓存、Todo 与 Token 管理（继承现有规则）

- **缓存管理**：完全沿用本 Skill 内 `references/stages/*.md` 中对 `.cache-status.json`、批次状态等的定义。
- **Todo 管理**：配合 `reverse` 创建的顶层 todo，本 Skill 内部在各阶段/子步骤中更新对应 todo 状态。
- **Token 管理**：遵循 [references/token-management.md](references/token-management.md) 中的各阶段 Token 预算与控制策略。

## 子代理调用规范

本 Skill 使用 Agent 工具调用 Omni 子代理执行具体任务。详细调用规范如下：

### 调用的子代理

| 子代理类型 | 使用场景 | 规范文档 |
|------------|----------|----------|
| `omni-reverse:scenario-recognizer` | 阶段2单文件场景识别 | [references/implementation/scenario-recognition.md](references/implementation/scenario-recognition.md) |
| `omni-reverse:scenario-detail-generator` | 阶段3单场景详情分析与文档生成 | [references/implementation/scenario-detail-analysis.md](references/implementation/scenario-detail-analysis.md) |

### 调用方式

使用 Agent 工具调用子代理，关键参数：
- `subagent_type`：子代理类型（如 `omni-reverse:scenario-recognizer`）
- `description`：简短描述（3-5个词）
- `prompt`：完整任务描述（包含输入说明、输出要求、约束条件）

### 批次处理规范

**阶段2 场景清单构建**：
- 文件数 > 20 时自动分批
- 每批使用 `omni-reverse:scenario-recognizer` 子代理处理
- 并发数量：每轮最多2个子代理
- 批次完成后合并结果生成 `scenario-list.json`

**阶段3 单场景文档生成**：
- 场景数 > 5 时自动分批
- 每批使用 `omni-reverse:scenario-detail-generator` 子代理处理
- 每批5个场景，并发处理
- 批次完成后更新状态文件

### 返回值处理

1. **直接使用**：子代理返回的结果直接保存到缓存文件（如 `scenario-list-batch-*.json`）
2. **格式验证**：验证返回 JSON 格式完整性
3. **合并结果**：主 Agent 收集各批次结果，合并后保存

### 错误处理

- **重试机制**：调用失败时最多重试2次，间隔递增（10s、30s）
- **降级方案**：重试失败后跳过当前批次，记录错误，继续处理其他批次
- **状态记录**：失败批次的错误信息记录到状态文件

### 超时与并发控制

- **超时设置**：子代理调用超时时间5分钟
- **超时处理**：超时后终止任务，标记为失败，继续下一批次
- **并发策略**：每轮最多2个子代理并发，完成后压缩上下文再处理下一轮

## 幻觉防护

- ❗ **来源引用要求**：所有结论必须引用具体来源（工具名+数据 / 文件路径+行号）—— 每次输出前自检
- ❗ **无来源禁止输出**：无引用来源的结论 = 不允许输出；无来源 = 不输出
- **零结果处理表**：

| 场景 | 正确输出 | 禁止输出 |
|------|---------|---------|
| 阶段跳过 | "阶段N已确认，跳过" | "执行了阶段N"（未实际执行） |
| 零场景 | "未识别到任何场景" | 编造场景填充列表 |
| 批次失败 | "批次N失败，继续下一批次" | 标记为成功或跳过失败记录 |

- **标注分级**：确认结果（无标注）/ 降级分析（⚠️）/ 通用建议（💡）

> 更多细节见各阶段文档 [references/stages/](references/stages/)。

## 参考文档（本 Skill 内）

本 Skill 的详细规范位于本目录下 `references/`：

- 阶段 1：[references/stages/01-scenario-pattern-identification-and-few-shot.md](references/stages/01-scenario-pattern-identification-and-few-shot.md)
- 阶段 2：[references/stages/02-scenario-inventory-construction.md](references/stages/02-scenario-inventory-construction.md)
- 阶段 3：[references/stages/03-scenario-detail-materialization.md](references/stages/03-scenario-detail-materialization.md)
- 数据说明：[references/data.md](references/data.md)
- 场景清单模板：[templates/reverse-scenario-inventory-template.md](templates/reverse-scenario-inventory-template.md)

AI Agent 在执行本 Skill 时，应读取上述文档并严格按照其中的步骤执行。

