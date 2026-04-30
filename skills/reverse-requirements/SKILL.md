---
name: reverse-requirements
description: 基于场景文档的需求分析与拆分编排Skill. 当 reverse 的 --target 为 requirements 或 all 的需求阶段时触发.
user-invokable: false
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

> 单需求文件内容需遵循 `.infra/metamodel/1.requirement-template.md` 模板（YAML frontmatter + EARS 正文）。

## 与 `reverse` 命令的关系

- `reverse` 负责：
  - 解析通用参数与路径/排除规则；
  - 初始化 `requirements` 缓存目录与状态文件；
  - 在需求阶段激活本 Skill。
- 本 Skill 负责：
  - 搜索并验证场景文档存在性；
  - 驱动需求分析与拆分两个阶段；
  - 在对话模式下插入确认点。

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
  - 在交互模式下展示需求摘要并等待用户确认，再进入阶段2。

## 阶段2：需求拆分（功能需求 → 独立需求文件）

- **阶段说明来源**：本 Skill 内 [references/stages/02-requirement-split.md](references/stages/02-requirement-split.md)
- **目标**：将 `需求设计.md` 中的功能需求拆分为多个独立需求文件，便于管理与追踪。
- **输入**：
  - `需求设计.md`（若不存在或不包含功能需求章节，必须中止执行）
- **输出**：
  - `{REPO_ROOT}/omni-doc/specs/requirements/{ID_PREFIX}-XXX-需求简述.md`
- **命名与内容规范**：
  - 文件名：`{ID_PREFIX}-{三位数字}-{需求简述}.md`（如 `REQ-001-计费管理-话单计费.md`、`INTENT-001-模型管理.md`）
  - 内容结构：遵循 `1.requirement-template.md`（frontmatter + EARS 正文）
- **要点**：
  - 在交互模式下可在生成前确认拆分清单、生成后确认汇总结果；
  - 重录（`--clear-cache`）时，生成前要清理旧 `{ID_PREFIX}-*.md` 以避免残留。

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

## 参考文档（本 Skill 内）

本 Skill 的详细规范位于本目录下 `references/`：

- 阶段 1：[references/stages/01-requirement-analysis.md](references/stages/01-requirement-analysis.md)
- 阶段 2：[references/stages/02-requirement-split.md](references/stages/02-requirement-split.md)
- 数据说明：[references/data.md](references/data.md)

执行本 Skill 时，AI Agent 应读取上述文档并严格遵守其中的输入/输出与命名规范。

