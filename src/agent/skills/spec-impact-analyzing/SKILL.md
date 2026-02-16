name: spec-impact-analyzing
description: 需求波及分析:从需求出发，分析与整理从 DOC_DIR/specs 中获取已有规格与代码知识，判断可复用范围与波及影响，产出结构化上下文供 `FEATURE_DIR/context.md` 使用，不直接写文件。
---

# 我的技能

围绕单个功能/需求或变更描述，自动完成**需求波及分析**，输出一份可直接用于填充 `context.md` 的结构化内容。

**核心目标**：
- 从用户描述中提取功能目标、用户类型、业务价值和关键概念
- 基于 REQ/SCN/FUNC/API/ENTITY 及 `relations/*.json` 找到相关/受影响的规格
- 复用 `spec-impact-analyzing` 的分析结果，补充架构视角、术语映射、约束与假设
- 产出一份结构化的「上下文中间态」，供上层命令按模板写入 `FEATURE_DIR/context.md`

**不做的事情**：
- 不创建分支、不运行任何脚本
- 不直接写入 `FEATURE_DIR/context.md` 或其他文件，只返回结构化内容
- 不直接修改现有 REQ/SCN/FUNC/API/ENTITY 文档

# 使用时机

在以下场景使用本技能：

- 需要在生成功能规范之前，先基于现有反构文档**收集和整理上下文**
- 希望将「上下文收集」与具体命令（如 `/omni.specify`）解耦，由上层命令统一调用本技能
- 需要一份可直接用于 `context.md` 的结构化上下文，而不是散乱的文档列表

# 指令

## 1. 输入

调用本技能时，应提供：

- **功能/需求或变更描述文本**（等价于 `/omni.specify` 中的 `$ARGUMENTS`）
- （可选）**DOC_DIR** 根目录；若未提供，则内部通过与 `.specify/scripts/*/check-prerequisites.*` 相同的方式检测，默认 `DOC_DIR = omni-doc`

## 2. 获取文档目录

- 如果调用方未显式提供 `DOC_DIR`，本技能内部需：
  - 判断操作系统（Windows / Linux）
  - 运行：
    - Windows: `.specify/scripts/powershell/check-prerequisites.ps1 --json --paths-only`
    - Linux: `.specify/scripts/bash/check-prerequisites.sh --json --paths-only`
  - 从 JSON 输出中解析 `DOC_DIR`，并派生以下路径：
    - `DOC_DIR/specs/requirements/` → `REQ-*.md`
    - `DOC_DIR/specs/scenarios/` → `SCN-*.md`
    - `DOC_DIR/specs/functions/` → `FUNC-*.md`
    - `DOC_DIR/specs/interfaces/` → `API-*.md`
    - `DOC_DIR/specs/logic_entities/` → `ENTITY-*.md`
    - `DOC_DIR/specs/relations/requirements.json`
    - `DOC_DIR/specs/relations/scenarios.json`
    - `DOC_DIR/specs/relations/functions.json`
    - `DOC_DIR/specs/relations/interface.json`

## 3. 解析功能/变更描述

从输入描述中提取：

- **功能目标**：系统要达成的能力或效果
- **用户类型 / 角色**：如 GSU、PFU、运维人员等
- **业务价值**：为什么要做这件事
- **关键概念与数据对象**：例如「会话删除」「UPSeid」「ACK」「LDB 同步」等
- **关键词列表**：用于后续检索和匹配（不必原样写入 `context.md`）

## 4. 检索反构文档与基础关联

- 使用 `glob_file_search` / `list_dir` 获取以下目录下的所有文档：
  - `requirements/`（REQ-*.md）
  - `scenarios/`（SCN-*.md）
  - `functions/`（FUNC-*.md）
  - `interfaces/`（API-*.md）
  - `logic_entities/`（ENTITY-*.md）
- 对每个文档：
  - 读取 front matter 元数据：`id`, `name`, `type`, `file`, `identifier` 等
  - 读取前若干内容用于关键词匹配
  - 按照名称、ID、内容命中情况和类型权重，计算与输入描述的**基础关联度**，要求如下：
    - **名称命中**：文档 `name` 与从输入描述提取的关键词做子串/包含匹配（不区分大小写）；每命中一个关键词贡献 **0.3**，同一文档名称项累计上限 **0.3**。
    - **ID 命中**：文档 `id` 与关键词做子串/包含匹配；每命中一个关键词贡献 **0.2**，同一文档 ID 项累计上限 **0.2**。
    - **内容命中**：在文档内容前 N 字符内统计关键词出现次数；得分 = (命中关键词数 / 关键词总数) × **0.4**，上限 **0.4**。
    - **类型权重**：按文档类型在基础分上叠加固定权重，只加一次：`Functional`(REQ) **0.1**，`Scenario`(SCN) **0.08**，`Function`(FUNC) **0.08**，`Interface`(API) **0.06**，`Entity`(ENTITY) **0.05**；若元数据无 `type` 则按目录/文件名推断类型。
    - **基础关联度** = 名称项 + ID 项 + 内容项 + 类型权重，结果截断到 **[0, 1]**。**相关性阈值**：仅当基础关联度 **大于 0.6** 的文档视为相关文档，用于排序与筛选。

## 5. 构建用于 `context.md` 的结构化结果

1. **功能描述**：
   - 原始输入描述
   - 提炼后的功能目标
   - 用户类型 / 角色
   - 业务价值与动机

2. **相关反构文档**：
   - **反构文档层级关系概览**：REQL → SCN → FUNC → API / ENTITY 的主干链路总结（而非纯文件列表）
   - **需求文档（REQ）**：
     - 相关 REQ-XXX 文件名列表（不含目录）
     - 每个 REQ 与本功能/变更的关系说明与建议变更类型
   - **场景文档（SCN）**：
     - 相关 SCN-XXX 文件名列表
     - 每个场景在本次功能中的角色（扩展/复用/新增）
   - **功能文档（FUNC）**：
     - 相关 FUNC-XXX 文件名列表
     - 每个功能与接口/实体的关键关系与变更建议
   - **接口文档（API）**：
     - 相关 API-XXX 文件名列表
     - 每个接口的消息类型标识符、代码文件路径、与本功能/变更的关系、变更建议
   - **逻辑实体文档（ENTITY）**：
     - 相关 ENTITY-XXX 文件名列表
     - 每个实体在本功能中的作用（请求/响应/内部消息等）与变更建议
   - **代码映射简表**：
     - 代码文件 ↔ API / FUNC / ENTITY 的主要映射关系（用于后续实现阶段参考）

3. **架构分析与设计参考**：
   - 可复用的需求模式（引用现有 REQ 编号 + 简述模式）
   - 可扩展的场景模式（引用现有 SCN 编号 + 简述扩展点）
   - 针对本次功能/变更**需要新增**的需求/场景/功能/接口/实体建议（概要级，不写详细规范）

4. **术语对齐**：
   - 用户术语 → 系统术语映射表（例如：「GSU 会话删除请求」 → `ENTITY-054`，ACK → `ENTITY-055`）
   - 重要的术语差异点说明（同一概念多种叫法时的统一规则）

5. **约束与假设**：
   - 技术约束：性能、时延、可靠性等（引用现有文档或架构约束）
   - 业务规则：从相关 REQ/SCN/FUNC 中抽取的关键业务逻辑约束
   - 显式假设：在缺乏信息时做出的合理假设，供上层命令在规范中引用

> 输出应以「总结与归纳」为主，而不是简单复制文档原文或罗列文件名。

## 7. 输出约定

调用本技能时，应返回一个**结构化对象**（或等价的 Markdown 结构），其字段尽量与 `context-template.md` 对齐，方便上层命令直接：

上层命令（如 `/omni.specify`）只负责：

- 调用本技能获取上下文结构
- 按模板写入 `FEATURE_DIR/context.md`

