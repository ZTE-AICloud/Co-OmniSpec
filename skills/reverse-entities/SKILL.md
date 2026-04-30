---
name: reverse-entities
description: 实体清单与实体关系反构的编排Skill. 当 reverse 的 --target 为 entities 或 all 的实体阶段时触发.
user-invokable: false
---

# 实体反构Skill（实体清单 + 文档 + 关系）

## 概览（职责与输入输出）

- **职责**：基于接口与功能等既有反构产物，抽取逻辑实体，完成：
  - 实体抽取
  - 实体融合与去重
  - 实体文档生成
  - 实体与接口/功能的关系建立
- **输入前提**：
  - 接口反构已完成详情阶段（`document_generation.confirmed == true`）
  - 用户通过 `reverse --target entities ...` 或 `--target all` 触发
- **输出产物**：
  - 缓存目录：`{REPO_ROOT}/.cache/reverse/entities/`
    - 实体抽取中间文档、索引与溯源元数据
    - 融合后的实体列表与统计
    - 状态文件：`.cache-status.json`
  - 文档目录：
    - 实体详情：`{REPO_ROOT}/omni-doc/specs/entities/ENTITY-*.md`
    - 实体清单：`{REPO_ROOT}/omni-doc/specs/entities/实体清单.md`
    - 关系文件：`omni-doc/specs/entities/relations/*.json`

> 本 Skill 继承原有阶段设计，仅改变为 Skill 形式；所有约束、依赖与 Token 管理保持不变。

## 与 `reverse` 命令的关系

- `reverse` 负责：
  - 统一解析参数与准备缓存目录；
  - 在执行到实体阶段时激活本 Skill；
  - 按两种模式管理交互（默认全自动 / 显式 `--interactive`）。
- 本 Skill 负责：
  - 验证接口反构依赖；
  - 驱动各实体阶段并更新 todo 与缓存状态。

## 阶段总览

本 Skill 按以下阶段执行，阶段详细说明见本目录下 `references/stages/`：

1. **阶段0：缓存状态与依赖检查**
2. **阶段1：从接口抽取实体**
3. **阶段2：实体融合和去重**
4. **阶段3：实体文档生成**
5. **阶段4：实体关系建立**

## 阶段0：缓存状态与依赖检查

- **阶段说明来源**：本 Skill 内 references/ 中的缓存与依赖约定
- **目标**：
  - 初始化 `{REPO_ROOT}/.cache/reverse/entities/.cache-status.json`
  - 验证接口反构已完成（`{REPO_ROOT}/.cache/reverse/interfaces/.cache-status.json` 中 `document_generation.confirmed == true`）
- **状态文件结构**：沿用原 JSON 模板（`entity_extraction`、`entity_consolidation`、`entity_document_generation`、`entity_relationship_building`）。
- 若依赖检查失败，必须用中文输出错误并终止实体反构流程。

## 阶段1：从接口抽取实体

- **阶段说明来源**：`本 Skill 内 references/stages/01-entity-extraction-from-interfaces.md`
- **目标**：从接口聚合文件中识别和提取逻辑实体，并保留溯源信息。
- **关键输出**：
  - 中间实体文档：`{REPO_ROOT}/.cache/reverse/entities/entity-extraction/ENTITIES-{原接口文件名}.md`
  - 实体索引与统计：`entities-index.json`、`extraction_stats.json`
  - 溯源元数据：`lineage/*.json`
- **交互模式**：
  - 默认/非交互/`--yes`：自动视为已确认抽取结果；
  - `--interactive`：展示抽取统计与代表性实体，请用户确认后进入下一阶段。

## 阶段2：实体融合和去重

- **阶段说明来源**：`本 Skill 内 references/stages/02-entity-consolidation.md`
- **目标**：融合重复或相似实体，生成统一的实体列表。
- **关键输出**：
  - 融合后的实体列表：`{REPO_ROOT}/.cache/reverse/entities/entity-consolidation/consolidated-entities.json`
  - 溯源映射：`entities_lineage.json`
  - 统计信息：`consolidation_stats.json`
- **要点**：
  - 支持多轮融合迭代与价值评估；
  - 在交互模式下展示融合前后数量对比和典型合并案例，等待确认；
  - 默认自动接受。

## 阶段3：实体文档生成

- **阶段说明来源**：`本 Skill 内 references/stages/03-entity-document-generation.md`
- **目标**：为每个实体生成标准化实体文档。
- **关键输出**：
  - `omni-doc/specs/entities/ENTITY-*.md`
  - `omni-doc/specs/entities/实体清单.md`
- **要点**：
  - 结合实体模板与融合结果生成功能；
  - 在交互模式下可让用户抽查示例文档并决定是否继续；
  - 按既有路径与命名规范生成文件。

## 阶段4：实体关系建立

- **阶段说明来源**：`本 Skill 内 references/stages/04-entity-relationship-building.md`
- **目标**：建立实体与接口/功能之间的关系。
- **关键输出**：
  - 接口 → 实体：`omni-doc/specs/entities/relations/interface-entity.json`
  - 实体 → 接口：`omni-doc/specs/entities/relations/entity-interface.json`
  - 功能 → 实体：`omni-doc/specs/entities/relations/function-entity.json`（在功能反构已完成时）
- **要点**：
  - 在交互模式下展示关系统计和示例关系；
  - 默认模式下自动确认保存。

## 缓存、Todo 与 Token 管理

- **缓存与路径**：完全沿用原 `reverse-entities.md` 与各阶段文档中的路径与字段约定。
- **Todo 管理**：
  - 利用 `reverse` 为 `entities` 初始化的 todo（主任务 + 0～4 阶段）；
  - 本 Skill 各阶段开始/结束时更新对应 todo 状态。
- **Token 管理**：
  - 大文件仅读取相关部分；
  - 阶段间清空上下文；
  - 按阶段文档中的强制检查点控制 Token 上限。

## 参考文档（本 Skill 内）

本 Skill 的详细规范位于本目录下 `references/`：

- 阶段 1：[references/stages/01-entity-extraction-from-interfaces.md](references/stages/01-entity-extraction-from-interfaces.md)
- 阶段 2：[references/stages/02-entity-consolidation.md](references/stages/02-entity-consolidation.md)
- 阶段 3：[references/stages/03-entity-document-generation.md](references/stages/03-entity-document-generation.md)
- 阶段 4：[references/stages/04-entity-relationship-building.md](references/stages/04-entity-relationship-building.md)
- 规则与数据：[references/core-rules.md](references/core-rules.md)、[references/data.md](references/data.md)

执行本 Skill 时，AI Agent 应读取上述文档并严格按照其中描述的阶段与脚本调用方式执行。

