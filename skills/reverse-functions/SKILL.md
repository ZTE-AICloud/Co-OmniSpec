---
name: reverse-functions
description: 功能清单与功能详情文档反构的编排Skill. 当 reverse 的 --target 为 functions 或 all 的功能阶段时触发.
user-invokable: false
---

# 功能反构Skill（functions）

## 概览（职责与输入输出）

- **职责**：基于项目入口与场景信息，完成：
  - 项目入口识别
  - 场景识别
  - 功能划分与功能树构建
  - 功能详细文档生成
- **输入前提**：
  - 用户通过 `reverse --target functions ...` 或 `--target all` 触发
  - 已根据 `--path` / `--files` 等参数确定扫描范围
- **输出产物**：
  - 缓存目录：`{REPO_ROOT}/.cache/reverse/functions/`
    - `project-entries.json`
    - `scenarios.json`
    - `function-list.json`、`function-tree.json`
    - `.cache-status.json`
  - 文档目录：`{REPO_ROOT}/omni-doc/specs/functions/`
    - `FUNC-XXX-功能名称.md`

> 本 Skill 对应原 `reverse-functions` 的“快捷命令 + 详细步骤”，现在以 Skill 形式承载该编排逻辑。

## 与 `reverse` 命令的关系

- `reverse` 负责：
  - 将 `--target` 固定为 `functions`（或在 all 流水线中进入功能阶段）；
  - 解析交互模式（默认全自动 / `--interactive` / `--non-interactive` / `--yes`）；
  - 初始化 todo 与缓存后，激活本 Skill。
- 本 Skill 负责：
  - 驱动 4 个阶段的执行；
  - 遵守功能反构的交互与缓存规则。

## 阶段总览

本 Skill 按以下阶段执行，阶段详细说明见本目录下 `references/stages/`：

1. **阶段0：缓存状态检查**
2. **阶段1：项目入口识别**
3. **阶段2：场景识别**
4. **阶段3：功能划分**
5. **阶段4：功能详细文档生成**

## 阶段0：缓存状态检查

- **阶段说明来源**：本 Skill 内 references/ 中的缓存约定
- **目标**：
  - 初始化 `{REPO_ROOT}/.cache/reverse/functions/.cache-status.json`
  - 建立 `project_entry_identification`、`scenario_identification`、`function_partitioning`、`function_document_generation` 四个段落
- **要点**：
  - 若某阶段已 `confirmed == true` 且对应输出存在，可在后续执行中跳过该阶段。

## 阶段1：项目入口识别

- **阶段说明来源**：本 Skill 内 [references/stages/01-project-entry-identification.md](references/stages/01-project-entry-identification.md)
- **目标**：识别项目的所有入口点（REST API、CLI、消息监听、定时任务、WebSocket 等）。
- **关键输出**：
  - `project-entries.json`（支持批次与索引）
- **要点**：
  - 按路径范围扫描并识别各种入口形式；
  - 提取路径、方法、参数、文件位置等信息及基本调用关系；
  - 默认模式下自动确认；在 `--interactive` 模式下可让用户确认入口识别结果。

## 阶段2：场景识别

- **阶段说明来源**：本 Skill 内 [references/stages/02-scenario-identification.md](references/stages/02-scenario-identification.md)
- **目标**：基于项目入口识别对应的业务场景。
- **关键输出**：
  - `scenarios.json`（支持批次与索引）
- **要点**：
  - 从入口结果中推断场景类型（正向主流程 / 异常 / 边界 / 批处理等）；
  - 提取场景名称、业务描述、前置条件、执行步骤等；
  - 建立场景与入口点的关联；
  - 交互模式下允许用户对场景识别进行确认与调整。

## 阶段3：功能划分

- **阶段说明来源**：本 Skill 内 [references/stages/03-function-partitioning.md](references/stages/03-function-partitioning.md)
- **目标**：基于场景识别结果划分功能，构建功能树。
- **关键输出**：
  - `function-list.json`（批次+索引）
  - `function-tree.json`
- **要点**：
  - 将相关场景聚合为功能，区分功能与子功能；
  - 提取功能名称、描述、分类、入口等；
  - 建立功能与场景、入口之间的关联关系；
  - 执行功能去重与合并逻辑；
  - 在 `--interactive` 模式下展示功能划分结果并等待确认。

## 阶段4：功能详细文档生成

- **阶段说明来源**：本 Skill 内 [references/stages/04-function-detail-extraction-and-document-generation.md](references/stages/04-function-detail-extraction-and-document-generation.md)
- **目标**：提取功能的完整详细信息并按模板生成文档。
- **关键输出**：
  - `{REPO_ROOT}/omni-doc/specs/functions/FUNC-XXX-功能名称.md`
- **要点**：
  - 以 `function-list.json` 为输入，分批处理功能；
  - 严格按照 `.infra/metamodel/5.function-template.md` 的结构和字段生成文档（frontmatter、章节、PlantUML 部分等必须保持一致）；
  - 在默认模式下自动生成；如 Skill 需要，可在交互模式加入最终确认。

## 模式、缓存与 Todo 管理

- **执行模式**：
  - 默认：全自动模式（所有“是否确认？”视为 Y）；
  - 显式 `--interactive`：在每个阶段结束后暂停，使用中文询问用户是否继续；
  - `--non-interactive` / `--yes`：强制全自动。
- **缓存状态文件**：`{REPO_ROOT}/.cache/reverse/functions/.cache-status.json`  
  结构与原文档保持一致。
- **Todo 管理**：
  - `reverse` 为功能反构创建主任务与 4 个阶段 todo；
  - 本 Skill 在阶段开始/结束时更新 todo 状态。

## 参考文档（本 Skill 内）

本 Skill 的详细规范位于本目录下 `references/`：

- 阶段 1：[references/stages/01-project-entry-identification.md](references/stages/01-project-entry-identification.md)
- 阶段 2：[references/stages/02-scenario-identification.md](references/stages/02-scenario-identification.md)
- 阶段 3：[references/stages/03-function-partitioning.md](references/stages/03-function-partitioning.md)
- 阶段 4：[references/stages/04-function-detail-extraction-and-document-generation.md](references/stages/04-function-detail-extraction-and-document-generation.md)

执行本 Skill 时，AI Agent 应读取上述文档并严格按照其中描述的步骤和数据结构进行操作。

