---
name: reverse-deep-logic-architecture
description: 从代码库自动识别并生成深度逻辑架构文档，提取核心业务逻辑层、数据流模式、模块依赖关系和决策逻辑集中点，输出 logic_architecture.md。适用于代码架构分析、遗留系统改造、技术尽职调查等场景。当 reverse 的 --target 为 deep_logic_architecture 时触发。
user-invokable: false
allowed-tools: Read, Write, Agent
disable-model-invocation: true
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
- **子 Agent**：`deep-architecture-identifier`（通过 `Task` 工具调用，详见阶段文档中的"子 Agent 调用规范"章节）
- **关键输出**：`{REPO_ROOT}/omni-doc/on-demand/logic_architecture.md`
- **规范速查**：失败重试 3 次；结果需验证文件存在且非空

## 参考文档

- 阶段文档：
  - 阶段1：[references/stages/01-deep-architecture-identification.md](references/stages/01-deep-architecture-identification.md)（子 Agent 调用规范、超时、错误处理）
- 数据约定：[references/data.md](references/data.md)（路径契约、模板约定）
- 核心规则：[references/core-rules.md](references/core-rules.md)（输出规则、执行规则）
- Token 管理：[references/token-management.md](references/token-management.md)（上下文策略、输出策略）

AI Agent 在执行本 Skill 时，应读取上述文档并严格按照其中描述执行。

## 工具权限

本 Skill 需要以下工具权限：

| 工具 | 用途 |
|------|------|
| `Read` | 读取代码库文件，分析代码结构 |
| `Write` | 写入 `logic_architecture.md` 和 `logic_architecture.cache-status.md` |
| `Agent` | 通过 `Task` 工具调用 `deep-architecture-identifier` 子 Agent |

## 上下文管理

### 阶段间数据传递

本 Skill 分为两个阶段，阶段间通过文件状态传递数据：

| 数据 | 传递方式 | 格式 |
|------|----------|------|
| 缓存命中状态 | 文件可读性检查 | `logic_architecture.md` 是否存在且非空 |
| 识别结果 | 写入主产物文件 | `logic_architecture.md`（Markdown） |
| 执行状态 | 写入状态文件 | `logic_architecture.cache-status.md`（可选） |

**依赖链约束**：
- 阶段0 产出的文件路径必须在阶段1 中被引用，**禁止重新搜索**
- 写入 `logic_architecture.md` 前验证文件非空（`size > 0`）
- 阶段1 子 Agent 结果由主 Agent 合并，不得跳过验证直接使用

### 缓存策略

- 阶段0检查产物是否已存在，命中时跳过阶段1，直接复用已有结果
- 缓存有效性由文件时间戳和 `cache-status.md` 中的状态字段共同判定
- 强制重新识别时，由入口命令（reverse）负责清理缓存

### Token 预算

- 详见 [references/token-management.md](references/token-management.md)
- 核心原则：单次分析输入控制在 15 万 tokens 内，详细结果写入文件而非对话
