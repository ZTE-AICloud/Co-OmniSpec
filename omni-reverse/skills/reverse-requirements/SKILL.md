---
name: reverse-requirements
description: 基于场景文档（SCN-XXX-*.md）进行需求分析与拆分，生成 EARS 语法功能需求、独立需求文件及带超链接的需求清单。由 reverse --target requirements 或 --target all 触发，适用于代码反构流程中的需求分析阶段。适用于：需要从场景生成需求文档、将功能需求拆分为独立文件、生成需求清单、EARS 规范需求编写等场景。
when_to_use: 当用户执行 reverse --target requirements、reverse --target all，或在反构流程中需要将场景文档（SCN-XXX-*.md）转化为功能需求（EARS 语法）并拆分为独立需求文件时触发。
argument-hint: "[--path <范围>] [--exclude <排除模式>] [--interactive] [--clear-cache] [--yes]"
user-invokable: false
allowed-tools: Read, Write, Edit, Glob, Grep
---

# 需求反构Skill（requirements）

## 概览（职责与输入输出）

- **职责**：基于已有场景文档（`SCN-XXX-*.md`），完成：
  - 场景 → 功能需求的分析（EARS 格式）
  - 功能需求拆分为独立的需求文件
- **输入前提**：
  - 工程根目录（或 `--path` 指定范围）中已有命名形如 `SCN-XXX-场景名称.md` 的场景文档
  - 用户通过 `reverse --target requirements ...` 或 `--target all` 触发
- **输出产物**：
  - internal 目录：`{REPO_ROOT}/.cache/reverse/requirements/internal/`
    - `需求设计.md`（或等价文件）
  - 需求文档目录：`{REPO_ROOT}/omni-doc/specs/requirements/`
    - `{ID_PREFIX}-XXX-需求简述.md`
    - `需求清单.md`（汇总表，含指向各独立需求文件的 Markdown 超链接）

> 单需求文件内容需遵循 `.omni-infra/metamodel/1.requirement-template.md` 模板（YAML frontmatter + EARS 正文）。

## 行为准则

以下规则在整个会话期间有效，不因对话长度而放松：

1. ❗ **每个 EARS 句式必须有来源场景 ID 标注** — 无来源的场景不得凭空生成需求，每次输出前自检
2. ❗ **阶段间数据不得重新生成** — 阶段2 必须引用阶段1 的需求设计文档产出，禁止重新搜索场景文档，每次输出前自检
3. ❗ **completeness ceiling 未满足不得输出强结论** — 覆盖不足时只能输出 `unresolved` 或 `tentative`，每次输出前自检

## 与 `reverse` 命令的关系

### 调用关系

- `reverse` 主命令负责：
  - 解析通用参数（`--path`、`--exclude`、`--interactive`、`--clear-cache`、`--yes`）与路径/排除规则
  - 初始化 `requirements` 缓存目录 `{REPO_ROOT}/.cache/reverse/requirements/` 与状态文件 `.cache-status.json`
  - 在需求阶段（`--target requirements` 或 `--target all`）激活本 Skill
  - 将解析后的参数传递给本 Skill

### 参数传递

本 Skill 通过 `$ARGUMENTS` 接收以下参数：

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--path` | 搜索范围（工程根目录或指定路径） | `.`（工程根目录） |
| `--exclude` | 排除的文件/目录模式（可多次使用） | 隐藏目录、`omni-doc/` |
| `--interactive` | 启用对话模式，阶段间插入确认步骤 | 全自动模式 |
| `--clear-cache` | 清除缓存并重新执行全部阶段 | 跳过已完成阶段 |
| `--yes` / `--non-interactive` | 强制全自动模式 | - |

### 阶段激活顺序

```
reverse --target requirements [--path ...] [--exclude ...] [--interactive]
    │
    ├── 阶段0：初始化缓存 + 搜索场景文档
    │       └── 若未找到 SCN-XXX-*.md → 中止
    │
    ├── 阶段1：需求分析（场景 → 功能需求）
    │       └── 输出：需求设计.md
    │       └── 交互模式：展示需求摘要 → 等待确认
    │
    └── 阶段2：需求拆分（功能需求 → 独立需求文件 + 需求清单）
            └── 输出：omni-doc/specs/requirements/{ID_PREFIX}-*.md、需求清单.md
            └── 交互模式：确认拆分清单 → 确认汇总结果
```

### 依赖前提

本 Skill 依赖以下外部资源：
- **场景文档**：`SCN-XXX-场景名称.md` 格式的 PlantUML 场景文档
- **需求模板**：`.omni-infra/metamodel/1.requirement-template.md`（阶段2 生成单需求文件时使用）

## 阶段总览

对应原 `reverse-requirements.md` 与 `reverse.requirements/stages/*`，本 Skill 包含：

1. **阶段0：缓存与路径检查**
2. **阶段1：需求分析（场景 → 功能需求）**
3. **阶段2：需求拆分（功能需求 → 独立需求文件）**

## 阶段0：缓存与路径检查

- **阶段说明来源**：本 Skill 内 references/ 中的缓存与依赖约定
- **目标**：
  - 获取 `REPO_ROOT` 并创建/读取 `{REPO_ROOT}/.cache/reverse/requirements/` 与 `.cache-status.json`
  - 在 `REPO_ROOT`（或 `--path`）下搜索 `SCN-XXX-*.md` 场景文档
- **关键规则**：
  - 若未找到任何 `SCN-XXX-*.md`：
    - 必须立即中止流程，不进入阶段1/2；
    - 用中文提示用户在工程中放置或生成场景文档后重试。

## 阶段1：需求分析（场景 → 功能需求）

- **阶段说明来源**：本 Skill 内 [references/stages/01-requirement-analysis.md](references/stages/01-requirement-analysis.md)
- **目标**：将场景分析结果转化为结构化的功能需求（EARS）。
- **输入**：
  - 在工程根目录或 `--path` 范围下搜索到的 `SCN-XXX-*.md` 场景文档
- **输出**：
  - `需求设计.md`（包含「功能需求」章节），位于 `{REPO_ROOT}/.cache/reverse/requirements/internal/`
- **要点**：
  - 对场景进行归类与抽象提升；
  - 为每个场景生成对应的功能需求条目（EARS 语法）；
  - **Decision Gate**：EARS 需求必须通过覆盖充分性验证（见 `01-requirement-analysis.md` 的 Decision Gate 小节）后才能写入需求设计文档；
  - 在交互模式下展示需求摘要并等待用户确认，再进入阶段2。

## 阶段2：需求拆分（功能需求 → 独立需求文件）

- **阶段说明来源**：本 Skill 内 [references/stages/02-requirement-split.md](references/stages/02-requirement-split.md)
- **目标**：将 `需求设计.md` 中的功能需求拆分为多个独立需求文件，便于管理与追踪。
- **输入**：
  - `需求设计.md`（若不存在或不包含功能需求章节，必须中止执行）
- **输出**：
  - `{REPO_ROOT}/omni-doc/specs/requirements/{ID_PREFIX}-XXX-需求简述.md`
  - `{REPO_ROOT}/omni-doc/specs/requirements/需求清单.md`（各需求条目含指向对应文件的相对路径超链接）
- **命名与内容规范**：
  - 文件名：`{ID_PREFIX}-{三位数字}-{需求简述}.md`（如 `REQ-001-计费管理-话单计费.md`、`INTENT-001-模型管理.md`）
  - 内容结构：遵循 `1.requirement-template.md`（frontmatter + EARS 正文）
- **要点**：
  - 在交互模式下可在生成前确认拆分清单、生成后确认汇总结果；
  - 全部独立需求文件生成后，按 `templates/reverse-requirement-inventory-template.md` 生成 `需求清单.md`；
  - 重录（`--clear-cache`）时，生成前要清理旧 `{ID_PREFIX}-*.md` 与 `需求清单.md` 以避免残留。

## 模式、缓存与路径规则

- **执行模式**：
  - 全自动模式（默认）：不带 `--interactive`，阶段间不插入人工确认；
  - 对话模式：显式 `--interactive`，在阶段1/2 中加入确认步骤；
  - `--non-interactive` / `--yes`：显式强制全自动。
- **缓存状态文件**：`{REPO_ROOT}/.cache/reverse/requirements/.cache-status.json`
  结构包含阶段状态与 `confirmed` 字段，沿用原文档定义。
- **路径与排除**：
  - 搜索场景文档时：排除隐藏目录与 `omni-doc/`，**不排除** `.cache/` 以便识别 `.cache/reverse/scenarios/` 下的场景详情；
  - 搜索/读写需求文件时遵循本 Skill 内 `references/data.md` 中的路径约定。

## 上下文管理

### 缓存策略

- **缓存根目录**：`{REPO_ROOT}/.cache/reverse/requirements/`
- **内部产物**：`{REPO_ROOT}/.cache/reverse/requirements/internal/`（需求设计文档等）
- **状态文件**：`{REPO_ROOT}/.cache/reverse/requirements/.cache-status.json`

### 缓存状态结构

```jsonc
{
  "requirement_analysis": {
    "confirmed": false,    // 用户已确认或自动化模式下为 true
    "progress": "pending", // pending | progressing | completed
    "timestamp": null
  },
  "requirement_split": {
    "confirmed": false,
    "progress": "pending",
    "timestamp": null
  }
}
```

### 缓存清理

- **手动清理**：使用 `--clear-cache` 参数清除缓存并重新执行
- **自动清理**：重录时（`--clear-cache`），阶段2 会删除输出目录 `{ID_PREFIX}-*.md` 与 `需求清单.md` 再重新生成

### 阶段间数据传递

- **阶段0 → 阶段1**：通过 Glob 搜索获得 `SCN-XXX-*.md` 文件列表
- **阶段1 → 阶段2**：通过 `{REPO_ROOT}/.cache/reverse/requirements/internal/需求设计.md` 中的「功能需求」章节传递
- **阶段2 → 外部**：生成 `{REPO_ROOT}/omni-doc/specs/requirements/{ID_PREFIX}-XXX-需求简述.md` 及 `需求清单.md`
- **禁止重新生成**：阶段2 必须直接读取阶段1 的需求设计文档，不得重新搜索场景文档或重新执行归类分析

### Token 预算说明

本技能以 AI Agent 操作为主，Token 消耗主要来自：
- 场景文档读取（约 5-20K tokens/文件）
- EARS 需求生成（约 3-5K tokens/需求）
- 建议根据场景文档数量和需求复杂度合理评估 Token 预算

### 回退机制

- **阶段1 失败**：
  - 清除当前阶段状态（`progress` 置为 `pending`）
  - 中止流程，不进入阶段2
  - 保留已读取的场景文档列表，用户修复后可直接重试
- **阶段2 失败**：
  - 保留阶段1 已生成的 `需求设计.md`
  - 可跳过阶段1 直接重试阶段2（若缓存中 `requirement_analysis.confirmed == true`）
- **文件回退**：
  - 重录时（`--clear-cache`），阶段2 会先删除 `{ID_PREFIX}-*.md` 与 `需求清单.md` 再重新生成
  - 如需手动回滚，可删除 `.cache/reverse/requirements/` 下对应文件
- **状态重置**：任何阶段失败后，可通过删除 `.cache-status.json` 中的 `confirmed` 字段重置状态

## 参考文档（本 Skill 内）

本 Skill 的详细规范位于本目录下 `references/`：

- 阶段 1：[references/stages/01-requirement-analysis.md](references/stages/01-requirement-analysis.md)
- 阶段 2：[references/stages/02-requirement-split.md](references/stages/02-requirement-split.md)
- 数据说明：[references/data.md](references/data.md)
- 需求清单模板：[templates/reverse-requirement-inventory-template.md](templates/reverse-requirement-inventory-template.md)
- Token 管理：[references/token-management.md](references/token-management.md)

执行本 Skill 时，AI Agent 应读取上述文档并严格遵守其中的输入/输出与命名规范。

