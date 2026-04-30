---
name: reverse-logic-architecture
description: 逻辑架构要素反构编排Skill. 当 reverse 的 --target 为 logic_architecture 或 all 的逻辑架构阶段时触发.
user-invokable: false
---

# 逻辑架构反构 Skill（架构识别 → 规格产物）

## 概览（职责与输入输出）

- **职责**：从代码库反构**逻辑架构**要素，生成结构化架构识别结果，供接口/功能等后续反构阶段作为上下文输入。
- **输入前提**：
  - 用户通过 `reverse --target logic_architecture ...` 触发，或在 `--target all` 时由编排 Skill **最先**调用本 Skill；
  - 已根据 `--path` / `--files` / `--exclude` 等参数确定分析范围（由入口命令解析并传入）。
- **输出产物（契约）**：
  - **主产物（规格目录，供各要素复用）**：`{REPO_ROOT}/omni-doc/specs/logic_architecture/architecture.json`
  - **阶段状态（缓存，断点与确认）**：`{REPO_ROOT}/.cache/reverse/logic_architecture/.cache-status.json`

> 架构识别的**生成**仅在本 Skill 中执行；`reverse-interfaces` 等 Skill **不再写入** `architecture.json`，只**读取**上述 `omni-doc` 路径下的文件。

## 与 `reverse` 命令的关系

- `reverse` 在 `--target logic_architecture` 时激活本 Skill；在 `--target all` 时由 `reverse-orchestration` **排在第一位**调用本 Skill。
- 本 Skill 负责：按阶段驱动架构识别子 Agent、维护本要素缓存状态、将结果写入 `omni-doc/specs/logic_architecture/`。

## 阶段总览

1. **阶段0：缓存与输出目录检查**（初始化 `logic_architecture` 缓存状态、确保 `omni-doc/specs/logic_architecture/` 可写）
2. **阶段1：架构识别**（子 Agent 分析并生成 `architecture.json`，用户确认后更新状态）

详细步骤见 `references/stages/`。

## 阶段0：缓存与输出目录检查

- **状态文件**：`{REPO_ROOT}/.cache/reverse/logic_architecture/.cache-status.json`
- 若不存在，则创建并初始化，至少包含：
  - `architecture_identification`（`confirmed` / `progress` / `timestamp`）
- 确保目录存在：
  - `{REPO_ROOT}/omni-doc/specs/logic_architecture/`
  - `{REPO_ROOT}/.cache/reverse/logic_architecture/`

## 阶段1：架构识别

- **阶段说明来源**：[references/stages/01-architecture-identification.md](references/stages/01-architecture-identification.md)
- **子 Agent**：`architecture-identifier`（`target_type` 必须为 `logic_architecture`）
- **关键输出**：`{REPO_ROOT}/omni-doc/specs/logic_architecture/architecture.json`

## 参考文档

- 阶段 1：[references/stages/01-architecture-identification.md](references/stages/01-architecture-identification.md)
- 数据约定：[references/data.md](references/data.md)
- 核心规则：[references/core-rules.md](references/core-rules.md)
- Token 管理：[references/token-management.md](references/token-management.md)

AI Agent 在执行本 Skill 时，应读取上述文档并严格按照其中描述执行。
