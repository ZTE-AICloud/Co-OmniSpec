---
name: reverse-external-interfaces
description: 外部依赖接口识别与文档生成的编排Skill. 当 reverse 的 --target 为 external-interfaces 或 all 的外部接口阶段时触发.
user-invokable: false
---

# 外部依赖接口识别Skill（external-interfaces）

## 概览（职责与输入输出）

- **职责**：识别代码库中来自**外部模块**且在本仓库中有调用示例的接口，并生成标准化文档。
- **输入前提**：
  - 用户通过 `reverse --target external-interfaces ...` 或 `--target all` 触发
  - 已根据 `--path` / `--exclude` 等参数确定扫描范围
- **输出产物**：
  - 缓存目录：`{REPO_ROOT}/.cache/reverse/external-interfaces/`
    - `import-list.json`
    - `.cache-status.json` 等
  - 文档目录：`{REPO_ROOT}/omni-doc/specs/external-interfaces/`
    - 单接口文档：`EXTERNAL-API_{NNN}_{简短描述}.md`
    - 汇总文件：`EXTERNAL-API_SUMMARY.json`

> “外部”指：非系统标准库且非当前仓库自身代码的模块；仅当存在调用点时才生成一条外部接口记录。

## 与 `reverse` 命令的关系

- `reverse` 负责解析参数 (`--target external-interfaces`)、设置扫描范围与排除规则、准备缓存目录后，激活本 Skill。
- 本 Skill 负责：
  - 具体执行导入扫描、分类、调用点检索与文档生成；
  - 在交互模式下插入必要的确认点；
  - 与状态/缓存文件和 todo 系统一致地管理进度。

## 阶段总览

本 Skill 由两大阶段组成（对应原 `reverse-external-interfaces.md` 与 `reverse.external-interfaces/stages/*`）：

1. **阶段1：导入模式与扫描**
2. **阶段2：外部调用与文档生成**

支持自动化模式（默认）与对话模式（`--interactive`），并支持 `--clear-cache` 进行重录。

## 阶段1：导入模式与扫描

- **阶段说明来源**：本 Skill 内 [references/stages/01-import-patterns-and-scan.md](references/stages/01-import-patterns-and-scan.md)
- **目标**：
  - 确定仓库主要语言，归纳该语言的导入/引用语法；
  - 扫描全库导入语句并将导入按“系统 / 本库 / 外部”三类进行分类。
- **关键输出**：
  - `import-list.json`：包含符号、来源模块、分类、文件位置等信息。
- **要点**：
  - 按语言识别导入方式（Python `import`/`from`，Java `import`，C++ `#include`，Go `import`，JS/TS `import`/`require` 等）；
  - 使用 `--path` 与 `--exclude` 控制扫描范围，默认排除隐藏目录与 `omni-doc/`；
  - 在交互模式下展示分类统计（系统 / 本库 / 外部），可让用户确认或调整参数后继续；
  - 默认模式下自动视为已确认。

## 阶段2：外部调用与文档生成

- **阶段说明来源**：本 Skill 内 [references/stages/02-external-calls-and-docs.md](references/stages/02-external-calls-and-docs.md)
- **目标**：
  - 对分类为“外部”的符号，在代码库中检索调用点；
  - 仅保留至少有一处调用的外部接口；
  - 为每条外部接口生成单独文档与汇总文件。
- **关键输出**：
  - 单接口文档：`EXTERNAL-API_{NNN}_{简短描述}.md`
  - 汇总文件：`EXTERNAL-API_SUMMARY.json`
- **要点**：
  - 仅针对“外部且有调用点”的条目生成文档；
  - 文档结构遵循原文中的推荐格式（类型、典型文件、接口名称、参数表、波及调用链等）；
  - 在对话模式下有两个关键确认点：
    1. 生成单接口文档前，对候选清单进行增删改查并确认；
    2. 所有单接口文档生成后，确认是否生成/更新汇总文件；
  - 默认/`--non-interactive`/`--yes` 模式下跳过上述对话，自动执行。

## 缓存、重录与路径约定

- **缓存状态文件**：`{REPO_ROOT}/.cache/reverse/external-interfaces/.cache-status.json`  
  结构与原文一致，包含 `import_scan`、`document_generation` 等段落。
- **重录（`--clear-cache`）**：
  - 清理缓存状态并在阶段2开始前删除 `omni-doc/specs/external-interfaces/` 下旧的 `EXTERNAL-API_*.md` 与 `EXTERNAL-API_SUMMARY.json`，再重新扫描与生成。
- **路径与排除规则**：
  - 遵循本 Skill 内 `references/` 中对 `--path` / `--exclude` 与默认排除目录的定义。

## 模式与参数

- **执行模式**：
  - 自动化模式（默认）：不带 `--interactive`；
  - 对话模式：显式带 `--interactive`；
  - 指定 `--non-interactive` 或 `--yes` 时，强制进入全自动模式。
- **关键参数**：
  - `--path`、`--files`：控制扫描范围；
  - `--exclude`：多次传入以排除测试/构建等目录；
  - `--clear-cache`：重录；
  - 其他通用参数与 `reverse` 保持一致。

## 参考文档（本 Skill 内）

本 Skill 的详细规范位于本目录下 `references/`：

- 阶段 1：[references/stages/01-import-patterns-and-scan.md](references/stages/01-import-patterns-and-scan.md)
- 阶段 2：[references/stages/02-external-calls-and-docs.md](references/stages/02-external-calls-and-docs.md)
- 规则与数据：[references/core-rules.md](references/core-rules.md)、[references/data.md](references/data.md)、[references/README.md](references/README.md)

AI Agent 在执行本 Skill 时，应读取上述文档并严格遵循其中的规则与脚本调用方式。

