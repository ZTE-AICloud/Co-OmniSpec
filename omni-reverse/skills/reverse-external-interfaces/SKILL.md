---
name: reverse-external-interfaces
description: 识别代码库中的外部依赖接口并生成标准化文档。扫描导入语句，将外部符号按系统/本库/外部分类，仅对有调用点的外部接口生成 EXTERNAL-API_xxx.md 和汇总文件。当用户执行 reverse --target external-interfaces 或 --target all 的外部接口阶段时触发。
user-invokable: false
when_to_use: 当用户执行 reverse --target external-interfaces 或 --target all 的外部接口阶段时触发本技能
argument-hint: [--target external-interfaces] [--path 路径] [--exclude 模式] [--interactive] [--non-interactive] [--yes] [--clear-cache]
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
  - 文档目录：`{REPO_ROOT}/omni-doc/specs/external-interfaces/`（输出目录与文件命名规范见 [references/data.md](references/data.md)）

> “外部”指：非系统标准库且非当前仓库自身代码的模块；仅当存在调用点时才生成一条外部接口记录。

## 行为准则（整个会话期间有效，不因对话长度放松）

1. ❗ **每个发现/修改必须引用来源** — 所有结论必须引用具体文件路径+行号；无引用来源 = 不允许输出
2. ❗ **仅对有调用点的外部接口生成文档** — 无调用点不生成，阶段1 分类为 external 的项仍需在阶段2 验证调用点存在后才生成文档
3. ❗ **禁止输出冗余内容** — 每次输出前自检：
   - 禁止开场白（”让我来分析...” / “首先我们需要...”）
   - 禁止工具调用描述（”我将使用 X 工具” / “正在读取...”）
   - 禁止已知信息复述（用户已提供的路径、参数等）

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
- **Checkpoint**：阶段完成后必须输出 `✅ Checkpoint: 阶段1 完成: X 个导入已分类（系统 Y / 本库 Z / 外部 W）`

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
- **Checkpoint**：阶段完成后必须输出 `✅ Checkpoint: 阶段2 完成: N 个外部接口文档已生成，X 个已排除（无调用点）`

## 缓存、重录与路径约定

- **缓存状态文件**：`{REPO_ROOT}/.cache/reverse/external-interfaces/.cache-status.json`  
  结构与原文一致，包含 `import_scan`、`document_generation` 等段落。
- **重录（`--clear-cache`）**：
  - 清理缓存状态并在阶段2开始前删除 `omni-doc/specs/external-interfaces/` 下旧的 `EXTERNAL-API_*.md` 与 `EXTERNAL-API_SUMMARY.json`，再重新扫描与生成。
- **路径与排除规则**：
  - 遵循本 Skill 内 `references/` 中对 `--path` / `--exclude` 与默认排除目录的定义。

## 使用示例

- **自动化执行（推荐）**：自动执行导入扫描与文档生成
  ```
  reverse --target external-interfaces
  reverse --target external-interfaces --path ./src
  ```

- **对话模式**：在关键节点暂停确认，适合需要审核结果的场景
  ```
  reverse --target external-interfaces --interactive
  ```

- **排除特定目录**：排除测试或构建目录后再扫描
  ```
  reverse --target external-interfaces --path ./src --exclude test --exclude build
  ```

- **强制重录**：清除缓存后重新执行全部阶段
  ```
  reverse --target external-interfaces --clear-cache
  ```

## 模式与参数

- **执行模式**：
  - 自动化模式（默认）：不带 `--interactive`；
  - 对话模式：显式带 `--interactive`；
  - 指定 `--non-interactive` 或 `--yes` 时，强制进入全自动模式。
- **关键参数**：
  - `--target external-interfaces`：指定触发本 Skill（必选）；
  - `--target all`：触发包括 external-interfaces 在内的所有阶段；
  - `--path`、`--files`：控制扫描范围；
  - `--exclude`：多次传入以排除测试/构建等目录；
  - `--interactive`：进入对话模式，阶段完成后暂停确认；
  - `--non-interactive`、`--yes`：强制自动化模式；
  - `--clear-cache`：重录，清除缓存后重新执行；
  - 其他通用参数与 `reverse` 保持一致。

## 参考文档（本 Skill 内）

本 Skill 的详细规范位于本目录下 `references/`：

- 阶段 1：[references/stages/01-import-patterns-and-scan.md](references/stages/01-import-patterns-and-scan.md)
- 阶段 2：[references/stages/02-external-calls-and-docs.md](references/stages/02-external-calls-and-docs.md)
- 规则与数据：[references/core-rules.md](references/core-rules.md)、[references/data.md](references/data.md)、[references/README.md](references/README.md)

AI Agent 在执行本 Skill 时，应读取上述文档并严格遵循其中的规则与脚本调用方式。

## 性能与 Token 管理

- **大型仓库处理**：如仓库规模很大（数千个源文件），阶段1 的导入扫描可能产生大量条目。AI Agent 可分批处理：
  - 按语言或目录分批扫描，控制每次上下文大小；
  - 阶段2 的文档生成也可分批进行（如每次生成 5～10 个接口文档），避免单轮 Token 超限。
- **Token 控制策略**：
  - 缓存已确认阶段的结果（`import-list.json`），避免重复扫描；
  - 使用 `--exclude` 排除不必要的目录（如 vendor/、node_modules/），减少扫描量；
  - 对话模式下可先确认阶段1 结果再继续，避免无效的大规模处理。
- **上下文压缩**：两阶段之间可清理上一阶段的冗余上下文，只保留关键输出文件路径和本阶段的执行目标。

