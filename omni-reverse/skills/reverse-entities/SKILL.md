---
name: reverse-entities
description: 实体清单与实体关系反构的编排Skill. 当 reverse 的 --target 为 entities 或 all 的实体阶段时触发.
user-invokable: false
---

# 实体反构Skill（实体清单 + 文档 + 关系）

## 行为准则（整个会话期间有效，不因对话长度放松）

1. ❗ 阶段间上下文必须清空 — 每次输出前自检
2. ❗ 禁止跳过未确认阶段 — 每次输出前自检
3. ❗ 禁止手动修改缓存文件模拟完成 — 每次输出前自检

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

- **详细说明**：本 Skill 内 references/ 中的缓存与依赖约定（无对应独立 stage 文档）
- **目标**：
  - 初始化 `{REPO_ROOT}/.cache/reverse/entities/.cache-status.json`
  - 验证接口反构已完成（`{REPO_ROOT}/.cache/reverse/interfaces/.cache-status.json` 中 `document_generation.confirmed == true`）
- **状态文件结构**：沿用 JSON 模板（entity_extraction / entity_consolidation / entity_document_generation / entity_relationship_building）
- ✅ Checkpoint: "阶段0完成: 缓存目录已初始化, 接口反构依赖已验证"
- **失败路径**: 依赖检查失败 → 用中文输出错误并终止, 不得进入阶段1; 缓存目录创建失败 → 输出错误并终止

## 阶段1：从接口抽取实体

- **详细说明**：[references/stages/01-entity-extraction-from-interfaces.md](references/stages/01-entity-extraction-from-interfaces.md)
- **关键产物**：`entity-extraction/ENTITIES-*.md` + `entities-index.json` + `lineage/*.json`
- **量化验收**：已处理批次 == 计划批次; 已抽取实体数 == extraction_stats.json.total_entities
- ✅ Checkpoint: "阶段1完成: X/Y 批次已处理, Z 个实体已抽取, X 个溯源文件已记录"
- **失败路径**: 缓存 confirmed==true → 跳过; 聚合文件目录不存在 → 输出错误并终止; 批次处理中断 → 从断点恢复

## 阶段2：实体融合和去重

- **详细说明**：[references/stages/02-entity-consolidation.md](references/stages/02-entity-consolidation.md)
- **关键产物**：`consolidated-entities.json` + `entities_lineage.json` + `consolidation_stats.json`
- **量化验收**：规则去重后数量 == consolidated-entities.json.total_entities（原始-去重-融合后逐级递减）
- ✅ Checkpoint: "阶段2完成: 规则去重 X→Y, 融合 X 轮, 价值评估后保留 Z 个实体"
- **失败路径**: 缓存 confirmed==true → 跳过; 阶段1未完成 → 输出错误并终止; 融合中断 → 从断点恢复

## 阶段3：实体文档生成

- **详细说明**：[references/stages/03-entity-document-generation.md](references/stages/03-entity-document-generation.md)
- **关键产物**：`omni-doc/specs/entities/ENTITY-*.md` + `实体清单.md`
- **量化验收**：已生成文档数 == consolidated-entities.json.total_entities
- ✅ Checkpoint: "阶段3完成: X/Y 个实体文档已生成, 实体清单已生成"
- **失败路径**: 缓存 confirmed==true → 跳过; 阶段2未完成 → 输出错误并终止; 模板文件不存在 → 输出错误并终止

## 阶段4：实体关系建立

- **详细说明**：[references/stages/04-entity-relationship-building.md](references/stages/04-entity-relationship-building.md)
- **关键产物**：`relations/interface-entity.json` + `relations/entity-interface.json` + `relations/function-entity.json`（可选）
- **量化验收**：interface-entity.json 条目数 == 接口聚合文件总数; 每条关系 targets 非空
- ✅ Checkpoint: "阶段4完成: 接口→实体 X 条关系, 实体→接口 Y 条关系, 功能→实体 Z 条关系(可选)"
- **失败路径**: 缓存 confirmed==true → 跳过; 阶段3未完成 → 输出错误并终止; 溯源映射文件不存在 → 输出错误并终止

## 依赖链声明

- **数据传递**：阶段2输入 = 阶段1完整产出（entities-index.json + 溯源文件列表）；阶段3输入 = 阶段2完整产出（consolidated-entities.json）；阶段4输入 = 阶段3产出（实体文档）+ 阶段2产出（entities_lineage.json）
- **禁止重新生成**：阶段2起不得重新搜索接口聚合文件，必须引用阶段1实际产出
- **写入前验证**：写 .cache-status.json 前必须先 Read 确认当前状态，跨阶段操作前验证前置阶段 confirmed==true

## 缓存、Todo 与 Token 管理

- **缓存与路径**：完全沿用原 `reverse-entities.md` 与各阶段文档中的路径与字段约定。
- **Todo 管理**：
  - 利用 `reverse` 为 `entities` 初始化的 todo（主任务 + 0～4 阶段）；
  - 本 Skill 各阶段开始/结束时更新对应 todo 状态。
- **Token 管理**：
  - 大文件仅读取相关部分；
  - 阶段间清空上下文；
  - 按阶段文档中的强制检查点控制 Token 上限。

## Decision Gate

强结论的 claim_type 与 required evidence：
- **behavioral**（实体融合/价值评估）: evidence = consolidated-entities.json 实际数据 + 融合统计; counter-evidence = 原始实体数量、价值评分分布
- **structural**（输出路径/格式）: evidence = 模板文件存在 + 文件实际写入; counter-evidence = 路径冲突、文件已存在
- **relational**（接口-实体关系）: evidence = entities_lineage.json + 接口聚合文件; counter-evidence = 功能反构未完成（功能→实体关系时）

规则：
- 无 evidence 的 signal 只能输出 `unresolved`，不得输出强结论
- 未检查 counter-evidence 的强结论最高只能 `tentative`
- 未找到接口聚合文件/模板文件时 → `unresolved` + 原因

## 参考文档（本 Skill 内）

本 Skill 的详细规范位于本目录下 `references/`：

- 阶段 1：[references/stages/01-entity-extraction-from-interfaces.md](references/stages/01-entity-extraction-from-interfaces.md)
- 阶段 2：[references/stages/02-entity-consolidation.md](references/stages/02-entity-consolidation.md)
- 阶段 3：[references/stages/03-entity-document-generation.md](references/stages/03-entity-document-generation.md)
- 阶段 4：[references/stages/04-entity-relationship-building.md](references/stages/04-entity-relationship-building.md)
- 规则与数据：[references/core-rules.md](references/core-rules.md)、[references/data.md](references/data.md)

执行本 Skill 时，AI Agent 应读取上述文档并严格按照其中描述的阶段与脚本调用方式执行。

