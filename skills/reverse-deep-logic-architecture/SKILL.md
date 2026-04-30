---
name: reverse-deep-logic-architecture
description: 深度逻辑架构要素反构编排Skill. 当 reverse 的 --target 为 deep_logic_architecture 时触发.
user-invokable: false
---

# 深度逻辑架构反构 Skill（深度架构识别 → logic_architecture.md）

## 概览（职责与输入输出）

- **职责**：从代码库反构深度逻辑架构，生成 `logic_architecture.md`（Markdown），供按需反构和人工分析复用。
- **输入前提**：
  - 用户通过 `reverse --target deep_logic_architecture ...` 触发；
  - 已根据 `--path` / `--files` / `--exclude` 等参数确定分析范围（由入口命令解析并传入）。
- **输出产物（契约）**：
  - **主产物**：`{REPO_ROOT}/omni-doc/on-demand/logic_architecture.md`
  - **状态文件**：`{REPO_ROOT}/omni-doc/on-demand/logic_architecture.cache-status.md`

## 与 `reverse` 命令的关系

- `reverse` 在 `--target deep_logic_architecture` 时激活本 Skill。
- 本 Skill 只负责深度架构产物生成，不参与 `--target all` 的默认全流程。

## 阶段总览

1. **阶段0：缓存与输出目录检查**
2. **阶段1：深度架构识别与文档生成**

## 阶段0：缓存与输出目录检查

- 确保目录存在：
  - `{REPO_ROOT}/omni-doc/on-demand/`
- 检查主产物与状态文件是否可访问：
  - `logic_architecture.md`
  - `logic_architecture.cache-status.md`

## 阶段1：深度架构识别与文档生成

- **阶段说明来源**：[references/stages/01-deep-architecture-identification.md](references/stages/01-deep-architecture-identification.md)
- **子 Agent**：`deep-architecture-identifier`
- **关键输出**：`{REPO_ROOT}/omni-doc/on-demand/logic_architecture.md`

## 参考文档

- 阶段 1：[references/stages/01-deep-architecture-identification.md](references/stages/01-deep-architecture-identification.md)
- 数据约定：[references/data.md](references/data.md)
- 核心规则：[references/core-rules.md](references/core-rules.md)
- Token 管理：[references/token-management.md](references/token-management.md)

AI Agent 在执行本 Skill 时，应读取上述文档并严格按照其中描述执行。
