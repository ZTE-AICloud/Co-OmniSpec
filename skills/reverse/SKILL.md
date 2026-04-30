---
description: 从代码库中反构各种类型的要素（接口、功能、场景、约束等），生成标准化的要素文档。第一阶段支持接口清单（interfaces）反构，新增支持按需反构（on-demand）。
---

## ⚠️ 重要提示：命令执行方式

**`reverse` 不是可执行命令，必须按照文档步骤执行！**

- ✅ **正确方式**：读取本文档，并根据 `--target` 调用对应的 reverse-* Skill（如 `reverse-logic-architecture`、`reverse-interfaces`），按照 Skill 中的阶段说明执行


**🔴 语言要求（必须严格遵守）**：**AI Agent 在执行所有步骤时，必须使用中文进行说明和输出。所有与用户的交互、步骤说明、进度提示都必须使用中文，禁止使用英文。**

**执行流程**：
1. 解析用户参数（从 `$ARGUMENTS`）
2. 根据 `--target` 参数读取对应的详细指导文档（如 `reverse-interfaces.md`，相对路径，与本文档同目录）
3. 按照详细指导文档中的步骤执行（**所有步骤说明和用户交互必须使用中文**）
4. 需要时调用脚本处理结果

## 用户输入

```text
$ARGUMENTS
```

在继续之前, 你**必须**考虑用户输入(如果不为空).

**🔴 重要：语言要求（必须严格遵守）**
- **AI Agent 在执行所有步骤时，必须使用中文进行说明和输出**
- **所有与用户的交互、步骤说明、进度提示都必须使用中文**
- **禁止使用英文**：所有向用户展示的信息、询问、确认提示等都必须使用中文
- **包括但不限于**：步骤说明、错误提示、进度信息、用户确认问题、结果展示等

## 概述

`reverse` 命令支持反构多种要素类型，通过 `--target` 参数指定要反构的要素类型：
- `logic_architecture`：逻辑架构要素（架构识别 JSON，写入 `omni-doc/specs/logic_architecture/`，供接口等下游只读使用）
- `deep_logic_architecture`：深度逻辑架构要素（生成 `omni-doc/on-demand/logic_architecture.md`，用于深度架构分析与按需反构）
- `interfaces`：接口清单（依赖逻辑架构产物；不再在接口阶段生成 `architecture.json`）
- `external-interfaces`：外部依赖接口识别（识别代码库外模块提供的、且在库内有调用示例的接口）
- `rules`：规则/约束反构（从代码库反构规则并生成 .mdc）
- `functions`：功能规范（基于入口与场景的功能清单与功能文档）
- `scenarios`：场景描述（基于接口/功能等既有产物的场景清单与单场景文档）
- `requirements`：需求分析（场景→功能需求→独立需求文件）
- `constraints`：约束规则（规划中）
- `entities`：逻辑实体（第一阶段实现）
- `on-demand`：按需反构（新增支持）
- `all`：按固定顺序依次执行**逻辑架构**→接口→功能→实体→场景→需求→外部接口→规则的全流程反构（默认全自动模式，不进入对话模式）

此外，`reverse` 支持通过 `--source` 切换反构数据源：
- `--source code`（默认）：从代码库反构（本文档主流程）
- `--source icenter`：从 iCenter 拉取页面并提取知识（通过 `reverse --source icenter` 入口触发 `reverse-icenter` Skill）

## 通用执行步骤

**第一步：解析参数并选择对应 Skill**

1. **解析用户输入参数**：
   - 从 `$ARGUMENTS` 中解析 `--source` 参数
     - 如果 `--source` 未指定，**默认使用 `code`**
     - 如果 `--source icenter`：必须按 `reverse-icenter` 的参数约束处理 `--page-root`（必填），同时调用 Skill `reverse-icenter`
   - 从 `$ARGUMENTS` 中解析 `--target` 参数
   - 如果 `--target` 未指定，**默认使用 `all`，执行完整流水线（logic_architecture → interfaces → functions → entities → scenarios → requirements → external-interfaces → rules）**
   - 解析其他参数（`--path`、`--files`、`--interactive`、`--non-interactive`、`--yes` 等）
   - **🔴 交互模式设置（重要，当 `--target functions` 时）**：
     - **默认行为**：全自动模式（非交互），所有"是否确认？"自动当作 Y，不再停顿询问
     - **交互模式**：只有明确指定 `--interactive` 参数时，才会切换到对话模式，每个阶段完成后会暂停等待用户确认
     - **非交互模式**：如果用户指定了 `--non-interactive` 或 `--yes`，强制使用全自动模式（与默认行为一致）
     - **判断逻辑**：如果参数中包含 `--interactive`，则启用交互模式；否则使用全自动模式
   - **🔴 全流程模式交互设置（当 `--target all` 时）**：
     - **始终使用全自动模式**：无论用户是否传入 `--interactive`，都必须按全自动模式执行，不进入对话/确认式交互
     - **忽略对话参数**：当 `--target all` 时，`--interactive` 参数应被忽略；如传入 `--non-interactive` 或 `--yes`，与默认行为一致，保持全自动
     - **参数复用**：`--path`、`--files`、`--exclude`、`--output-dir` 等通用参数，在全流程各子阶段（interfaces/functions/entities/scenarios/requirements/external-interfaces/rules）中按统一规则复用

2. **根据 `--target` 调用对应的反构 Skill**：
   - **🔴 重要：每一种要素类型都有一个对应的 reverse-* Skill，由 `claude/skills/reverse-*/SKILL.md` 定义详细阶段与调用方式**
   - 如果 `--source icenter`，必须立即调用 Skill `reverse-icenter`，按照 `claude/skills/reverse-icenter/SKILL.md` 中的阶段说明执行（此时 `--target` 取值遵循 iCenter 约定：`all|requirements|system-contexts|scenarios|logical-architectures`，未指定默认 `all`），不要继续解析本文其他部分
   - 如果 `--target logic_architecture`，**必须立即调用** Skill `reverse-logic-architecture`，按该 Skill 的 `SKILL.md` 执行逻辑架构识别并写入 `omni-doc/specs/logic_architecture/architecture.json`
   - 如果 `--target deep_logic_architecture`，**必须立即调用** Skill `reverse-deep-logic-architecture`，按该 Skill 的 `SKILL.md` 生成 `omni-doc/on-demand/logic_architecture.md`
   - 如果 `--target interfaces`，**必须立即调用** Skill `reverse-interfaces`，按照该 Skill 的 `SKILL.md` 中的阶段说明执行接口清单反构（须读取已存在的逻辑架构产物；单独执行 `interfaces` 前应先完成 `logic_architecture` 或确保 `architecture.json` 已存在）
   - 如果 `--target entities`，**必须立即调用** Skill `reverse-entities`，按照该 Skill 的 `SKILL.md` 中的阶段说明执行实体清单反构
   - 如果 `--target on-demand`，**必须立即调用** Skill `reverse-on-demand`，按照该 Skill 的 `SKILL.md` 中的阶段说明执行按需反构
   - 如果 `--target external-interfaces`，**必须立即调用** Skill `reverse-external-interfaces`，按照该 Skill 的 `SKILL.md` 中的阶段说明执行外部依赖接口识别
   - 如果 `--target rules`，**必须立即调用** Skill `reverse-rules`，按照该 Skill 的 `SKILL.md` 中的阶段说明执行规则/约束反构
   - 如果 `--target requirements`，**必须立即调用** Skill `reverse-requirements`，按照该 Skill 的 `SKILL.md` 中的阶段说明执行需求反构
   - 如果 `--target functions`，在 Skill `reverse-functions` 存在时，应优先调用该 Skill 按其阶段说明执行功能反构
   - Skill 位置示例：`{REPO_ROOT}/claude/skills/reverse-interfaces/SKILL.md`、`{REPO_ROOT}/claude/skills/reverse-scenarios/SKILL.md` 等
   - 按照对应 Skill 的 `SKILL.md` 中的步骤执行，不要尝试直接将本命令当作可执行脚本

3. **获取环境信息**：
   - 判断当前操作系统（Windows/Linux）
   - **跨平台脚本调用**：
     - Linux: `bash .specify/scripts/bash/check-prerequisites.sh --paths-only --json`
     - Windows: `pwsh .specify/scripts/powershell/check-prerequisites.ps1 --paths-only --json`
   - 从输出中提取 `REPO_ROOT`（JSON格式）
   - **🔴 路径说明**：脚本路径为 `.specify/scripts/bash/check-prerequisites.sh`（Linux）或 `.specify/scripts/powershell/check-prerequisites.ps1`（Windows）
   - 注意：使用 `--paths-only` 模式可以跳过分支检查，允许在任何分支（包括 main/master）上执行 reverse 命令
   - 验证参数有效性

**第二步：创建初始 Todo 列表**

3. **创建初始 Todo 列表**（重要）：
   - **AI Agent 必须在开始执行前创建初始 todo 列表**，包含所有阶段的任务项
   - 对于 `--target logic_architecture`，应包含以下 todo 项：
     - "执行 reverse 命令进行逻辑架构反构"（主任务）
     - "阶段0: 缓存与输出目录检查"
     - "阶段1: 架构识别（写入 omni-doc/specs/logic_architecture/architecture.json）"
   - 对于 `--target deep_logic_architecture`，应包含以下 todo 项：
     - "执行 reverse 命令进行深度逻辑架构反构"（主任务）
     - "阶段0: 缓存与输出目录检查"
     - "阶段1: 深度架构识别与文档生成（写入 omni-doc/on-demand/logic_architecture.md）"
   - 对于 `--target interfaces`，应包含以下 todo 项：
     - "执行 reverse 命令进行接口反构"（主任务）
     - "阶段0: 缓存状态检查"
     - "阶段1: 逻辑架构产物校验（读取 omni-doc/specs/logic_architecture/architecture.json）"
     - "阶段2: 初步扫描与Few-shot 示例生成"
     - "阶段3: 接口清单扫描"
     - "阶段4: 详细信息提取与文档生成"
   - 对于 `--target entities`，应包含以下 todo 项：
     - "执行 reverse 命令进行实体清单反构"（主任务）
     - "阶段0: 缓存状态检查"
     - "阶段1: 从接口抽取实体"
     - "阶段2: 实体融合和去重"
     - "阶段3: 实体文档生成"
     - "阶段4: 实体关系建立"
   - 对于 `--target on-demand`，应包含以下 todo 项：
     - "执行 reverse 命令进行按需反构"（主任务）
     - "阶段1: 分支和特性准备"
     - "阶段2: 深度架构识别"
     - "阶段3: 按需反构执行"
   - 对于 `--target external-interfaces`，应包含以下 todo 项：
     - "执行 reverse 命令进行外部依赖接口识别"（主任务）
     - "阶段1: 导入模式与扫描"
     - "阶段2: 外部调用与文档生成"
   - 对于 `--target rules`，应包含以下 todo 项：
     - "执行 reverse 命令进行规则反构"（主任务）
     - "阶段1: 特征检测"
     - "阶段2: 规则映射与分批"
     - "阶段3: 规则文档生成"
     - "阶段4: 用户规则注入（可选）"
   - 对于 `--target requirements`，应包含以下 todo 项：
     - "执行 reverse 命令进行需求反构"（主任务）
     - "阶段0: 缓存与路径检查"
     - "阶段1: 需求分析（场景→功能需求）"
     - "阶段2: 需求拆分（→独立需求文件）"
   - 使用 `todo_write` 工具创建初始 todo 列表，所有项初始状态为 `pending`
   - **重要**：用户需要能够直观地看到每个阶段的完成状态，因此 todo 状态更新是必须的

**第三步：按照对应 Skill 的阶段说明执行**

4. **按照对应 reverse-* Skill 中的阶段说明执行**：
   - **🔴 语言要求**：所有步骤说明、用户交互、确认提示都必须使用中文，禁止使用英文
   - 根据 `--target` 参数，完全按照对应的详细指导文档（如 `reverse-interfaces.md` 或 `reverse-on-demand.md`，相对路径）中的步骤执行
   - **🔴 重要：必须首先执行详细指导文档中的"执行前检查清单"**：
     - 提取用户命令参数（`--path` 或 `--files` 或其他相关参数）
     - 获取仓库根目录（`REPO_ROOT`）
     - **创建缓存目录和初始化状态文件**（必须执行，不能跳过）
     - 读取接口类型列表（如果适用）
     - 检查缓存状态
   - 每个步骤都有明确的说明，按照说明执行即可（**使用中文说明**）
   - **在每个阶段开始时将对应 todo 项标记为 `in_progress`**
   - **在每个阶段完成后立即将对应 todo 项标记为 `completed`**
   - **🔴 用户确认机制**：
     - **全自动模式（默认，当 `--target functions` 时）**：所有阶段完成后自动确认，不询问用户，直接继续下一阶段
     - **交互模式（`--interactive`，当 `--target functions` 时）**：每个阶段完成后，AI Agent **必须暂停执行，使用中文询问用户确认**，只有在用户确认后才能继续下一阶段
     - **判断方式**：当 `--target functions` 时，检查参数中是否包含 `--interactive`，如果没有则使用全自动模式
     - **其他 target**：按照各自详细指导文档的要求处理


**注意**：不要尝试直接执行 `reverse` 命令，它不是一个可执行命令。必须按照文档中的步骤，由 AI Agent 执行分析任务，然后调用脚本处理结果。

## 要素类型与对应 Skills 映射

根据 `--source` 参数，调用对应的要素类型 Skill：
- **`--source icenter`**：调用 Skill `reverse-icenter`（已实现，`claude/skills/reverse-icenter/SKILL.md`）

根据 `--target` 参数，调用对应的要素类型 Skill：

- **`--target logic_architecture`**：调用 Skill `reverse-logic-architecture`（`claude/skills/reverse-logic-architecture/SKILL.md`）
- **`--target deep_logic_architecture`**：调用 Skill `reverse-deep-logic-architecture`（`claude/skills/reverse-deep-logic-architecture/SKILL.md`）
- **`--target interfaces`**：调用 Skill `reverse-interfaces`（已实现，`claude/skills/reverse-interfaces/SKILL.md`）
- **`--target external-interfaces`**：调用 Skill `reverse-external-interfaces`（已实现，`claude/skills/reverse-external-interfaces/SKILL.md`）
- **`--target rules`**：调用 Skill `reverse-rules`（已实现，`claude/skills/reverse-rules/SKILL.md`）
- **`--target on-demand`**：调用 Skill `reverse-on-demand`（已实现，`claude/skills/reverse-on-demand/SKILL.md`）
- **`--target functions`**：调用 Skill `reverse-functions`（规划中，`claude/skills/reverse-functions/SKILL.md`）
- **`--target scenarios`**：调用 Skill `reverse-scenarios`（已实现，`claude/skills/reverse-scenarios/SKILL.md`）
- **`--target requirements`**：调用 Skill `reverse-requirements`（已实现，`claude/skills/reverse-requirements/SKILL.md`）
- **`--target constraints`**：预留未来的 Skill `reverse-constraints`
- **`--target entities`**：调用 Skill `reverse-entities`（已实现，`claude/skills/reverse-entities/SKILL.md`）
- **`--target all`**：调用 Skill `reverse-orchestration`，按其编排说明依次处理 `logic_architecture` → `interfaces` → `functions` → `entities` → `scenarios` → `requirements` → `external-interfaces` → `rules`（默认全自动模式）

## 全流程调用串接（--target all）

当用户指定 `--target all` 时，AI Agent **不得直接在命令层手写 8 个阶段的编排逻辑**，而是应：

1. 按本命令文件前文的规则解析参数、获取 `REPO_ROOT` 与通用缓存根目录；
2. 将解析后的参数（尤其是 `--path` / `--files` / `--exclude` / `--clear-cache` 等）作为输入，**激活 Skill `reverse-orchestration`**；
3. 严格按照该 Skill 的 `SKILL.md` 中的说明执行完整流水线反构：
   - 固定调用顺序：logic_architecture → interfaces → functions → entities → scenarios → requirements → external-interfaces → rules；
   - 每个阶段的**输入（可变）/输出（不可变，契约）**；
   - 全自动、不停顿的模式要求；
   - 全流程 Todo 的创建与阶段状态更新；
   - 参数与缓存的复用策略。

> 简而言之：`reverse --target all` 只是**入口命令**，真正的全流程编排规范统一收敛到 Skill `reverse-orchestration` 中，由该 Skill 负责调用各 `reverse-*` Skill 并衔接 **8** 个阶段（逻辑架构必须最先执行，生成的内容供后续要素使用）。`deep_logic_architecture` 为单独 target，不纳入 `all`。

## 按需反构（on-demand）特殊说明

按需反构是一种新的反构模式，它基于需求意图（SDD文档或自然语言）来检索和反构波及的功能。与传统的全量反构不同，按需反构只反构被新需求波及的存量要素，提供更精准和高效的反构体验。

按需反构支持两种复杂度模式：
- **简单需求**（默认）：自动确认波及功能清单，直接执行反构
- **复杂需求**：用户确认波及功能清单后，逐功能深入分析

按需反构的主要特点：
1. **需求驱动**：基于需求意图识别需要反构的要素类型
2. **语义检索**：基于需求意图进行语义匹配，检索波及的功能
3. **波及分析**：智能识别哪些存量要素被新需求波及
4. **精准反构**：只反构被波及的存量要素，避免全量反构
5. **全面反构**：对波及的功能进行全面的反构，包括实现、层级、架构、约束、场景、接口、测试用例等

## 扩展性说明

当添加新的要素类型时：
1. 在要素类型注册表中注册新类型
2. 实现对应的扫描和分析函数
3. 创建对应的模板文件
4. **创建对应的要素类型指导文件**（`reverse-<element-type>.md`，与现有各 `reverse-*` 子技能文档命名一致）
5. 在主命令文件中添加引用（可选，脚本会自动识别）

## 命令参数

### 基本参数

```bash
reverse \
  [--source <code|icenter>] \
  --target <target-type> \
  [--path <path1,path2,...>] \
  [--files <file1,file2,...>] \
  [--interface-types <type1,type2,...>] \
  [--output-dir <dir>] \
  [--template <template-file>] \
  [--page-root <icenter_root_url1,icenter_root_url2,...>] \
  [--interactive] \
  [--non-interactive] \
  [--yes] \
  [--preview] \
  [--incremental] \
  [--git-diff <commit>] \
  [--since <date>] \
  [--merge] \
  [--validate] \
  [--exclude <pattern>] \
  [--clear-cache] \
  [--verbose] \
  [--json] \
  [--help]
```

### 参数说明

- `--target` (必需)：目标要素类型，支持 `all`、`logic_architecture`、`deep_logic_architecture`、`interfaces`、`functions`、`entities`、`scenarios`、`requirements`、`external-interfaces`、`rules`、`on-demand`、`constraints`（预留）等；未指定时默认 `all`
- `--source` (可选)：反构数据源，支持 `code`（默认，从代码库反构）与 `icenter`
- `--path` (可选*)：反构的目录路径（逗号分隔）
- `--files` (可选*)：反构的文件路径（逗号分隔）
- `--interface-types` (可选)：指定要反构的接口类型（仅当 `--target interfaces` 时使用）
- `--output-dir` (可选)：输出目录，默认根据分支类型决定
- `--template` (可选)：模板文件路径，默认使用内置模板
- `--page-root` (当 `--source icenter` 时必须)：iCenter 根页面 URL，支持多个 URL 以英文逗号分隔
- `--interactive` (可选)：启用交互式确认
- `--non-interactive` (可选)：强制非交互模式
- `--yes` (可选)：非交互模式，自动接受所有默认选项
- `--preview` (可选)：预览模式，不写入文件
- `--incremental` (可选)：增量反构模式
- `--git-diff` (可选)：基于 Git 提交差异反构（需配合 `--incremental`）
- `--since` (可选)：基于时间戳反构（需配合 `--incremental`）
- `--merge` (可选)：合并到现有清单文件（需配合 `--incremental`）
- `--validate` (可选)：启用结果校验
- `--exclude` (可选)：排除文件模式（可多次使用）
- `--clear-cache` (可选)：清理缓存
- `--verbose` (可选)：详细输出模式
- `--json` (可选)：JSON 格式输出
- `--help` (可选)：显示帮助信息

**注意**：
- 当 `--source code`或没有该参数时：`--path` 和 `--files` 至少需要指定一个（对于按需反构，参数要求可能不同，请参考 `reverse-on-demand.md`）。
- 当 `--source icenter` 时：必须提供 `--page-root`；。

## 使用示例

```bash
# 无参数：按固定顺序执行完整流水线（默认行为）
# 等价于：reverse --target all --path .
reverse --path .

# 仅反构逻辑架构（生成 omni-doc/specs/logic_architecture/architecture.json）
reverse --target logic_architecture --path .

# 仅反构深度逻辑架构（生成 omni-doc/on-demand/logic_architecture.md）
reverse --target deep_logic_architecture --path .

# 仅反构整个代码库的接口（须已有逻辑架构产物，或先执行上一行）
reverse --target interfaces --path .

# 反构指定目录的接口
reverse --target interfaces --path src/api/,src/services/

# 仅反构 RESTful 和消息类接口
reverse --target interfaces --path src/ --interface-types restful,message

# 反构指定文件的接口
reverse --target interfaces --files src/api/user.py

# 基于已完成的接口反构结果，执行实体清单反构
reverse --target entities --path .

# 外部依赖接口识别（识别代码库外模块提供的、且在库内有调用示例的接口）
reverse --target external-interfaces --path .

# 外部依赖接口识别（排除测试与构建目录；对话模式每阶段确认）
reverse --target external-interfaces --path . --exclude "**/test/**" --exclude "**/build/**" --interactive

# 外部依赖接口识别（重录：清除缓存后重新执行）
reverse --target external-interfaces --path . --clear-cache

# 规则反构（从代码库反构规则并生成 .mdc）
reverse --target rules --path .

# 规则反构（对话模式，每阶段确认）
reverse --target rules --path . --interactive

# 需求反构（场景→功能需求→独立需求文件；依赖场景反构产物）
reverse --target requirements
reverse --target requirements --interactive
reverse --target requirements --clear-cache
reverse --target requirements --exclude "**/test/**" --exclude "**/build/**"

# 按需反构（基于SDD需求文档）
reverse --target on-demand --requirement spec.md

# 按需反构（基于需求意图表达）
reverse --target on-demand --intent "实现用户登录功能，支持多因素认证"

# 按需反构（复杂需求模式）
reverse --target on-demand --requirement spec.md --demand-complexity complex

# 交互式反构（仅对单一 target 生效；--target all 时将被忽略，始终全自动）
reverse --target interfaces --path src/ --interactive
reverse --target entities --path src/ --interactive

# 预览模式
reverse --target interfaces --path src/ --preview

# JSON 输出
reverse --target interfaces --path src/ --json

# iCenter 反构：从 iCenter 拉取页面并一次性提取全部知识
reverse --source icenter --target all --page-root "https://i.zte.com.cn/.../wiki/page/xxx/view,https://i.zte.com.cn/.../wiki/page/yyy/view"

# iCenter 反构：仅提取场景（target=scenarios）
reverse --source icenter --target scenarios --page-root "https://i.zte.com.cn/.../wiki/page/xxx/view"
```