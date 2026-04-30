---
name: reverse-scenarios
description: 场景清单与单场景文档反构的编排Skill. 当 reverse 的 --target 为 scenarios 或 all 的场景阶段时触发.
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
- **输出产物**：
  - 缓存目录：`{REPO_ROOT}/.cache/reverse/scenarios/`
    - `scenario-patterns.json`
    - `few-shot-examples.json`
    - `scenario-types.json`
    - `constraints.json`
    - `scenario-list.json` 及批次相关 JSON
  - 文档目录：`{REPO_ROOT}/omni-doc/specs/scenarios/SCN-XXX-*.md`

> **核心要求**：只消费既有产物，不重复做架构识别；严格使用缓存与分批机制；所有交互说明和输出必须为中文。

## 与 `reverse` 命令的关系

- 当命令层执行：
  - `reverse --target scenarios ...`，或
  - `reverse --target all ...` 且执行到“场景反构阶段”时，
- `reverse` 负责：
  - 解析 `$ARGUMENTS`（`--path` / `--exclude` / `--interactive` 等）
  - 获取 `REPO_ROOT` 与通用缓存目录
  - 然后**激活本 Skill `reverse-scenarios`**，将必要上下文（参数、路径、缓存位置）作为前置条件提供。
- 本 Skill 内部按实现文档执行（见本目录 `references/implementation/`）：
  - [references/implementation/scenario-recognition.md](references/implementation/scenario-recognition.md)（单文件场景识别）
  - [references/implementation/scenario-detail-analysis.md](references/implementation/scenario-detail-analysis.md)（单场景详情 → 文档）
  - 以及场景批次相关脚本（见阶段文档）。

## 阶段总览

本 Skill 按以下阶段编排，阶段详细说明见本目录下 `references/stages/`：

1. **阶段0：缓存状态检查**
2. **阶段1：场景模式识别与 few-shot 示例生成**
3. **阶段2：场景清单构建**
4. **阶段3：单场景文档生成**

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
  - 主清单：`scenario-list.json`、`scenario-list.md`
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
  - 场景详情模板：优先使用项目特定模板，否则使用 `.infra/templates/default/reverse-scenario-detail-template.md`
- **关键输出**：
  - `{REPO_ROOT}/omni-doc/specs/scenarios/SCN-XXX-场景名称.md`
  - 更新后的 `scenario-list.json` 中的场景处理状态（`processing_status` 等）
- **主要要点**：
  - 清理上下文、Token 控制；
  - 读取场景总数，决定单批或分批：
    - 分批时调用场景详情批次脚本（如 `create_scenario_detail_batches.sh`、`get_next_scenario_detail_batches.sh` 等）；
  - 使用多个按 [references/implementation/scenario-detail-analysis.md](references/implementation/scenario-detail-analysis.md) 执行的子 Agent 并行处理批次；
  - 每批结束后更新批次状态、进度、耗时，并清理上下文；
  - 所有场景处理完成后，检查输出目录与状态文件一致性；
  - 在交互模式下展示摘要和样例，确认后将 `document_generation.confirmed` 标记为 true。

## 缓存、Todo 与 Token 管理（继承现有规则）

- **缓存管理**：完全沿用本 Skill 内 `references/stages/*.md` 中对 `.cache-status.json`、批次状态等的定义。
- **Todo 管理**：配合 `reverse` 创建的顶层 todo，本 Skill 内部在各阶段/子步骤中更新对应 todo 状态。
- **Token 管理**：遵循阶段文档中的强制检查点与 `/compact` 机制，优先复用结构化 JSON，避免加载完整代码。

## 参考文档（本 Skill 内）

本 Skill 的详细规范位于本目录下 `references/`：

- 阶段 1：[references/stages/01-scenario-pattern-identification-and-few-shot.md](references/stages/01-scenario-pattern-identification-and-few-shot.md)
- 阶段 2：[references/stages/02-scenario-inventory-construction.md](references/stages/02-scenario-inventory-construction.md)
- 阶段 3：[references/stages/03-scenario-detail-materialization.md](references/stages/03-scenario-detail-materialization.md)
- 数据说明：[references/data.md](references/data.md)

AI Agent 在执行本 Skill 时，应读取上述文档并严格按照其中的步骤执行。

