---
name: reverse
description: 执行 reverse 命令从代码库反构接口、架构、实体、场景、需求等要素，生成标准化文档。
when_to_use: 用户提到"反构"、"reverse"、"接口清单"、"架构识别"、"需求分析"、"实体识别"、"场景描述"等关键词时
argument-hint: --target <all|logic_architecture|deep_logic_architecture|interfaces|functions|entities|scenarios|requirements|external-interfaces|rules> [--source <code>] [--path <path1,path2,...>] [--files <file1,file2,...>]
allowed-tools: Bash, TodoCreate, TodoUpdate, TodoList, Read, Write, Glob
disable-model-invocation: true
user-invocable: true
---

## ⚠️ 重要提示：命令执行方式

**`reverse` 不是可执行命令，必须按照文档步骤执行！**

- ✅ **正确方式**：读取本文档，并根据 `--target` 调用对应的 reverse-* Skill（如 `reverse-logic-architecture`、`reverse-interfaces`），按照 Skill 中的阶段说明执行

## 行为准则

以下规则在整个 reverse 执行会话期间始终有效，不因对话长度放松：

1. ❗ **非可执行命令**：reverse 是 Skill 入口而非可执行命令，必须通过 `Skill` 工具调用子 reverse-* Skill。每次输出前自检此条。
2. ❗ **全中文输出**：AI Agent 在执行所有步骤时，必须使用中文进行说明和输出。所有与用户的交互、步骤说明、进度提示都必须使用中文，禁止使用英文。每次输出前自检此条。
3. ❗ **引用子 Skill 规范**：阶段执行逻辑由对应子 reverse-* Skill 定义，reverse 主 Skill 只负责任务分发。每次输出前自检此条。

**执行流程（统一三级编号）**：
- **第一步**：解析参数并选择对应 Skill（见下方详细说明）
- **第二步**：创建初始 Todo 列表（见下方详细说明）
- **第三步**：调用子 Skill 并收集结果（见下方详细说明）

每个阶段完成后必须输出 Checkpoint，每个阶段必须定义失败处理路径。

## 用户输入

```text
$ARGUMENTS
```

在继续之前, 你**必须**考虑用户输入(如果不为空).


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
- `all`：按固定顺序依次执行**逻辑架构**→接口→功能→实体→场景→需求→外部接口→规则的全流程反构（默认全自动模式，不进入对话模式）

此外，`reverse` 支持通过 `--source` 切换反构数据源：
- `--source code`（默认）：从代码库反构（本文档主流程）

## 通用执行步骤

**第一步：解析参数并选择对应 Skill**

1. **获取环境信息与 SDD 环境初始化**：
   - **🔴 首先获取 REPO_ROOT**（必须先执行此步骤）：
     - **优先使用 `CLAUDE_WORKING_DIR` 环境变量**：
       - 如果 `CLAUDE_WORKING_DIR` 存在且为有效目录：`REPO_ROOT="$CLAUDE_WORKING_DIR"`
       - 否则使用当前工作目录：`REPO_ROOT="$(pwd)"`（Linux/macOS）或 `$REPO_ROOT = (Get-Location).Path`（Windows）
     - **不要使用 `git rev-parse --show-toplevel`**（已废弃，可能导致子目录工作区问题）
   - **🔴 解析共享插件根 DSDD**（omni-infra 与共享脚本均在 omni-dsdd 中，必须先解析）：
     - `DSDD="$(bash "${CLAUDE_PLUGIN_ROOT}/scripts/resolve-dsdd-root.sh")" || exit 1`
     - 解析器优先取 `${CLAUDE_PLUGIN_ROOT}/../omni-dsdd`，失败则终止并提示需同 marketplace 安装 omni-dsdd。
   - **🔴 SDD 环境初始化（init_omni_infra，必须在 check-prerequisites 之前执行）**：
     - 将 `${DSDD}/omni-infra` 拷贝为 `${REPO_ROOT}/.omni-infra`；显式传 `--plugin-root`/`--working-dir`，**不要**依赖脚本内 `pwd`，**不要**仅 `export` 后无参调用：
       ```bash
       bash "${DSDD}/scripts/bash/init_omni_infra.sh" \
         --plugin-root "${DSDD}" \
         --working-dir "${REPO_ROOT}"
       ```
     - **返回码约定**：`1` = 首次创建成功（按需执行 `constitution` 后继续）；`0` = 已存在；`2` = 失败（须终止）。
   - **跨平台脚本调用**（omni-infra 初始化完成后执行；`check-prerequisites` 位于共享插件 `scripts/`，经 `${DSDD}` 访问）：
     - Linux: `bash ${DSDD}/scripts/bash/check-prerequisites.sh --paths-only --json`
     - Windows: `pwsh ${DSDD}/scripts/powershell/check-prerequisites.ps1 --paths-only --json`
   - 从输出中提取 `REPO_ROOT`（JSON格式）
   - 使用 `--paths-only` 模式可以跳过分支检查
   - **失败路径**：如果 `CLAUDE_WORKING_DIR` 和 `pwd` 都无效 → 输出 `unresolved: 无法确定工程目录` + 建议使用 `--path` 指定代码目录；如果 `init_omni_infra.sh` 返回 `2` → 输出 `unresolved: SDD 环境初始化失败` 并终止

**✅ Checkpoint: "1.1 完成: REPO_ROOT={值}, DSDD={值}, .omni-infra已就绪, 操作系统={值}"**

2. **解析用户输入参数**：
   - 从 `$ARGUMENTS` 中解析 `--source` 参数
     - 如果 `--source` 未指定，**默认使用 `code`**
   - 从 `$ARGUMENTS` 中解析 `--target` 参数
   - 如果 `--target` 未指定，**默认使用 `all`**
   - 解析其他参数（`--path`、`--files`、`--interactive`、`--non-interactive`、`--yes` 等）
   - **交互模式设置**：如果参数中包含 `--interactive`，则启用交互模式；否则使用全自动模式（所有确认自动接受 Y）。**当 `--target all` 时始终使用全自动模式，`--interactive` 参数被忽略**
   - **失败路径**：参数格式错误 → 输出 `unresolved` + 参数约束提示，不执行后续阶段

**✅ Checkpoint: "1.2 完成: source={值}, target={值}, 交互模式={值}, 有效参数 N 个"**

3. **根据 `--target` 调用对应的反构 Skill**：
   - **🔴 调用方式**：使用 `Skill` 工具调用子技能，例如：`Skill(omni-reverse:reverse-interfaces)`
   - **重要**：子技能由 reverse 编排调用，AI Agent 不应直接在 reverse 执行阶段逻辑
   - 如果 `--target logic_architecture`，**必须立即调用** Skill `omni-reverse:reverse-logic-architecture`
   - 如果 `--target deep_logic_architecture`，**必须立即调用** Skill `omni-reverse:reverse-deep-logic-architecture`
   - 如果 `--target interfaces`，**必须立即调用** Skill `omni-reverse:reverse-interfaces`
   - 如果 `--target entities`，**必须立即调用** Skill `omni-reverse:reverse-entities`
   - 如果 `--target external-interfaces`，**必须立即调用** Skill `omni-reverse:reverse-external-interfaces`
   - 如果 `--target rules`，**必须立即调用** Skill `omni-reverse:reverse-rules`
   - 如果 `--target requirements`，**必须立即调用** Skill `omni-reverse:reverse-requirements`
   - 如果 `--target functions`，应优先调用 Skill `omni-reverse:reverse-functions`（如果存在）；如果该 Skill 不存在，输出 `unresolved: reverse-functions 功能规划中，请使用具体 target（如 interfaces/entities/scenarios）代替`
   - 如果 `--target constraints`，输出 `unresolved: constraints 反构功能规划中，暂不可用`
   - Skill 位置示例：`{REPO_ROOT}/claude/skills/reverse-interfaces/SKILL.md`
   - **失败路径**：目标子 Skill 不存在或规划中 → 输出 `unresolved` + 失败原因，不尝试替代执行

**✅ Checkpoint: "第一步完成: source={值}, target={值}, REPO_ROOT={值}, 子Skill={Skill名称}, 有效参数 N 个"

**第二步：创建初始 Todo 列表**

1. **创建初始 Todo 列表**：
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
   - 使用 `TodoCreate` 工具创建初始 todo 列表，所有项初始状态为 `pending`
   - **失败路径**：TodoCreate 调用失败 → 重试一次；仍失败则记录原因并继续执行（Todo 是辅助工具，不阻塞主流程）

**✅ Checkpoint: "第二步完成: Todo 列表已创建，N 个任务项，状态均为 pending"**

**第三步：调用子 Skill 并收集结果**

1. **激活子 Skill 并获取产物**：
   - 使用 `Skill` 工具激活第一步中确定的子 Skill（如 `Skill(omni-reverse:reverse-interfaces)`）
   - 子 Skill 负责执行实际的反构逻辑（读取代码库、生成产物）
   - **🔴 必须在子 Skill 开始时将对应 Todo 项标记为 `in_progress`**（使用 `TodoUpdate`）
   - **🔴 子 Skill 完成后必须立即将对应 Todo 项标记为 `completed`**
   - 失败路径：子 Skill 执行失败 → 将 Todo 项标记为 `pending`，输出 `unresolved` + 失败原因，**不得生成不完整的产物文件**

2. **产物路径契约**：
   - 各 target 的产物路径已在第一步第 3 步中明确
   - 产物文件命名遵循子 Skill 的 schema 规范
   - **写入产物前**：必须确认 REPO_ROOT 路径正确、目标目录存在；如目录不存在则先创建

3. **全流程模式（`--target all`）**：
   - 当 `--target all` 时，必须按固定顺序依次调用子 Skill：
     `reverse-logic-architecture` → `reverse-interfaces` → `reverse-entities` → `reverse-scenarios` → `reverse-requirements` → `reverse-external-interfaces` → `reverse-rules`
   - 每个子 Skill 完成后输出 Checkpoint 并更新 Todo 状态
   - 中间某个子 Skill 失败时：
     - 如果失败原因是输入产物不存在（依赖未满足）→ 输出 `unresolved` + 依赖说明，**停止后续阶段**
     - 如果失败原因是技术错误（工具不可用等）→ 记录原因，继续下一子 Skill（允许部分成功）
   - **⚠️ 全流程模式不使用对话确认，始终全自动执行**（`--interactive` 参数被忽略）

**✅ Checkpoint: "第三步完成: target={值}, 产物已写入 {文件路径}, 产物文件数 N 个"**


根据 `--target` 参数，调用对应的要素类型 Skill：

- **`--target logic_architecture`**：调用 Skill `omni-reverse:reverse-logic-architecture`（`claude/skills/reverse-logic-architecture/SKILL.md`）
- **`--target deep_logic_architecture`**：调用 Skill `omni-reverse:reverse-deep-logic-architecture`（`claude/skills/reverse-deep-logic-architecture/SKILL.md`）
- **`--target interfaces`**：调用 Skill `omni-reverse:reverse-interfaces`（已实现，`claude/skills/reverse-interfaces/SKILL.md`）
- **`--target external-interfaces`**：调用 Skill `omni-reverse:reverse-external-interfaces`（已实现，`claude/skills/reverse-external-interfaces/SKILL.md`）
- **`--target rules`**：调用 Skill `omni-reverse:reverse-rules`（已实现，`claude/skills/reverse-rules/SKILL.md`）
- **`--target functions`**：调用 Skill `omni-reverse:reverse-functions`（规划中，`claude/skills/reverse-functions/SKILL.md`）
- **`--target scenarios`**：调用 Skill `omni-reverse:reverse-scenarios`（已实现，`claude/skills/reverse-scenarios/SKILL.md`）
- **`--target requirements`**：调用 Skill `omni-reverse:reverse-requirements`（已实现，`claude/skills/reverse-requirements/SKILL.md`）
- **`--target constraints`**：预留未来的 Skill `omni-reverse:reverse-constraints`
- **`--target entities`**：调用 Skill `omni-reverse:reverse-entities`（已实现，`claude/skills/reverse-entities/SKILL.md`）
- **`--target all`**：调用 Skill `omni-reverse:reverse-orchestration`，按其编排说明依次处理 `logic_architecture` → `interfaces` → `functions` → `entities` → `scenarios` → `requirements` → `external-interfaces` → `rules`（默认全自动模式）

## 全流程调用串接（--target all）

当用户指定 `--target all` 时，AI Agent **不得直接在命令层手写 8 个阶段的编排逻辑**，而是应：

1. 按本命令文件前文的规则解析参数、获取 `REPO_ROOT` 与通用缓存根目录；
2. 将解析后的参数（尤其是 `--path` / `--files` / `--exclude` / `--clear-cache` 等）作为输入，**激活 Skill `omni-reverse:reverse-orchestration`**；
3. 严格按照该 Skill 的 `SKILL.md` 中的说明执行完整流水线反构：
   - 固定调用顺序：logic_architecture → interfaces → functions → entities → scenarios → requirements → external-interfaces → rules；
   - 每个阶段的**输入（可变）/输出（不可变，契约）**；
   - 全自动、不停顿的模式要求；
   - 全流程 Todo 的创建与阶段状态更新；
   - 参数与缓存的复用策略。

> 简而言之：`reverse --target all` 只是**入口命令**，真正的全流程编排规范统一收敛到 Skill `omni-reverse:reverse-orchestration` 中，由该 Skill 负责调用各 `reverse-*` Skill 并衔接 **8** 个阶段（逻辑架构必须最先执行，生成的内容供后续要素使用）。`deep_logic_architecture` 为单独 target，不纳入 `all`。

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
  [--source <code>] \
  --target <target-type> \
  [--path <path1,path2,...>] \
  [--files <file1,file2,...>] \
  [--interface-types <type1,type2,...>] \
  [--output-dir <dir>] \
  [--template <template-file>] \
  [--interactive] \
  [--non-interactive] \
  [--yes] \
  [--preview] \
  [--incremental] \
  [--git-diff <commit>] \
  [--since <date>] \
  [--merge] \
  [--validate] \
  [--exclude <pattern1,pattern2,...>] \
  [--clear-cache] \
  [--verbose] \
  [--json] \
  [--help]
```

### 参数说明

- `--target` (必需)：目标要素类型，支持 `all`、`logic_architecture`、`deep_logic_architecture`、`interfaces`、`functions`、`entities`、`scenarios`、`requirements`、`external-interfaces`、`rules`、`constraints`（预留）等；未指定时默认 `all`
- `--source` (可选)：反构数据源，支持 `code`（默认，从代码库反构）
- `--path` (可选*)：反构的目录路径（逗号分隔多个目录，使用单个参数传入）
- `--files` (可选*)：反构的文件路径（逗号分隔）
- `--interface-types` (可选)：指定要反构的接口类型（仅当 `--target interfaces` 时使用）
- `--output-dir` (可选)：输出目录，默认根据分支类型决定
- `--template` (可选)：模板文件路径，默认使用内置模板
- `--interactive` (可选)：启用交互式确认
- `--non-interactive` (可选)：强制非交互模式
- `--yes` (可选)：非交互模式，自动接受所有默认选项
- `--preview` (可选)：预览模式，不写入文件
- `--incremental` (可选)：增量反构模式
- `--git-diff` (可选)：基于 Git 提交差异反构（需配合 `--incremental`）
- `--since` (可选)：基于时间戳反构（需配合 `--incremental`）
- `--merge` (可选)：合并到现有清单文件（需配合 `--incremental`）
- `--validate` (可选)：启用结果校验
- `--exclude` (可选)：排除文件模式（逗号分隔多个 pattern，使用单个参数传入）
- `--clear-cache` (可选)：清理缓存
- `--verbose` (可选)：详细输出模式
- `--json` (可选)：JSON 格式输出
- `--help` (可选)：显示帮助信息

**注意**：
- 当 `--source code`或没有该参数时：`--path` 和 `--files` 至少需要指定一个。

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
reverse --target external-interfaces --path . --exclude "**/test/**,**/build/**" --interactive

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
reverse --target requirements --exclude "**/test/**,**/build/**"

# 交互式反构（仅对单一 target 生效；--target all 时将被忽略，始终全自动）
reverse --target interfaces --path src/ --interactive
reverse --target entities --path src/ --interactive

# 预览模式
reverse --target interfaces --path src/ --preview

# JSON 输出
reverse --target interfaces --path src/ --json

```

## 上下文管理

### 缓存策略

- 缓存目录：`reverse-cache/`
- 缓存内容：中间产物、扫描结果、解析结果
- 使用 `--clear-cache` 参数清除缓存后重新执行

### Todo 集成

- 每个阶段对应一个 Todo 任务项
- 阶段开始时标记为 `in_progress`
- 阶段完成后标记为 `completed`
- 使用 TodoList 查看整体进度

### Token 预算

详细预算分配见 `references/token-management.md`

### 阶段间数据传递

- 通过文件系统：产物文件（architecture.json、interface-list.json 等）
- 通过 Todo 状态：进度、阶段完成状态
- 通过缓存文件：中间处理结果
