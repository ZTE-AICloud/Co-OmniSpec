---
name: reverse-orchestration
description: 全流程反构编排 Skill。当用户执行 reverse --target all 时，自动编排执行逻辑架构、接口、功能、实体、场景、需求、外部接口、规则共 8 个阶段，生成完整的代码库逆向工程文档。适用于：代码库分析、知识提取、架构文档生成、存量代码逆向等场景。
user-invokable: false
allowed-tools: TodoWrite, Read, Glob, Grep
when_to_use: 当用户执行 reverse --target all、提到"全流程反构"、"8阶段编排"、reverse all、全面逆向工程，或需要一次性生成完整代码库文档时触发。
---

## 行为准则

以下规则在整个会话期间有效，不因对话长度而放松：

1. ❗ **禁止进入对话模式** — 全流程执行时不得询问"是否继续""是否确认"，每次输出前自检
2. ❗ **阶段失败必须中止** — 任一阶段执行失败时，立即中止后续阶段并输出原因，每次输出前自检
3. ❗ **复用产物不重推断** — 下游阶段必须复用上游已产出的文档，禁止重新推断或覆盖，每次输出前自检

## 输出约束

禁止输出:
- 对话模式确认（"是否继续""是否确认"等询问）
- 阶段间的技术细节解释（应由子 Skill 输出，编排层仅传递状态）
- 冗余状态复述（已完成阶段的产物路径只需引用，不重新描述内容）
- 未经验证的阶段执行假设

# 全流程反构编排 Skill（--target all）

## 概览

- **职责**：当用户执行 `reverse --target all`（或未显式指定 `--target`，默认视为 `all`）时，统一编排以下 **8** 个阶段：
  1. 逻辑架构反构（logic_architecture）— **必须最先执行**，产物供后续要素只读使用
  2. 接口反构（interfaces）
  3. 功能反构（functions）
  4. 实体反构（entities）
  5. 场景反构（scenarios）
  6. 需求反构（requirements）
  7. 外部接口识别（external-interfaces）
  8. 规则/约束反构（rules）
- **模式**：全程**全自动、不中断**，不进入对话模式，不询问「是否继续/是否确认」。
- **行为原则**：
  - 各阶段的**输出路径与格式（契约）固定**，仅输入参数与上游产物是否存在可以变化；
  - 具体单 target 的阶段细节，仍由各自 `reverse-*` Skill 的 `SKILL.md` 与 `references/` 定义。

## 输入与输出

### 输入（来自 `reverse` 命令）

- `--target all`（或未显式指定 `--target` 且默认视为 `all`）
- 公共参数（在入口已解析，传入本 Skill）：
  - `--path` / `--files`：主扫描范围（至少一个，按 `reverse.md` 入口规则要求）
  - `--exclude`：排除模式（零个或多个）
  - `--output-dir`、`--template`、`--incremental`、`--git-diff`、`--since`、`--merge`、`--validate` 等通用参数
  - 交互相关参数：`--interactive` / `--non-interactive` / `--yes`（在 `all` 模式下只作为「显式全自动」确认，不改变**非交互**模式）
- 环境变量：
  - `REPO_ROOT`：通过 `check-prerequisites` 获取
  - 通用缓存根目录：`{REPO_ROOT}/.cache/reverse/`

### 输出（整体视角）

- 按各 target 约定的固定路径和格式输出：
  - logic_architecture：`omni-doc/specs/logic_architecture/architecture.json` 与 `.cache/reverse/logic_architecture/.cache-status.json`
  - interfaces：`.cache/reverse/interfaces/` 与 `omni-doc/specs/interfaces/`（**不再**在接口缓存中生成 `architecture.json`）
  - functions：以 `reverse-functions.md` / `reverse-functions` 约定为准
  - entities：`.cache/reverse/entities/` 与 `omni-doc/specs/entities/`
  - scenarios：`.cache/reverse/scenarios/` 与 `omni-doc/specs/scenarios/`
  - requirements：需求设计 + 独立需求文件，路径以 `reverse-requirements` 约定为准
  - external-interfaces：外部接口清单与文档，以 `reverse-external-interfaces` 约定为准
  - rules：规则/约束文档（如 `.mdc`），以 `reverse-rules` 约定为准
- 全流程 Todo 列表：通过 `todo_write` 工具创建并维护，覆盖 8 个阶段及一个主任务。

> **注意**：本 Skill **不改变** 各 target 的输出契约，仅负责顺序、参数复用、依赖校验与 Todo 串接。

## 阶段顺序与输入/输出契约

本节抽象自 `claude/commands/reverse.md` 中「全流程调用串接（--target all）」的规则，用于指导 AI 在本 Skill 中如何串接各 `reverse-*` Skill。

### 阶段1：逻辑架构反构（logic_architecture）

- **调用**：`reverse-logic-architecture`
- **参考文档**：`claude/skills/reverse-logic-architecture/SKILL.md` 及 `references/stages/`
- **输入（可变）**：
  - 扫描范围：`--path` / `--files`（至少一个），`--exclude`（可选）；交互参数在 `all` 模式下被忽略
- **输出（不可变，契约）**：
  - `{REPO_ROOT}/omni-doc/specs/logic_architecture/architecture.json`
  - `{REPO_ROOT}/.cache/reverse/logic_architecture/.cache-status.json`
- **下游依赖**：
  - **阶段2（interfaces）强制读取**上述 `architecture.json`；其他阶段可按各自 Skill 约定作为可选上下文。

### 阶段2：接口反构（interfaces）

- **调用**：`reverse-interfaces`
- **参考文档**：`reverse-interfaces.md`（若存在）或 `claude/skills/reverse-interfaces/SKILL.md`
- **输入（可变）**：
  - 扫描范围：`--path` / `--files`（至少一个），`--exclude`（可选）
  - **硬依赖**：阶段1 已产出 `{REPO_ROOT}/omni-doc/specs/logic_architecture/architecture.json`
  - 其它：`--interface-types`（可选），交互参数在 `all` 模式下被忽略
- **输出（不可变，契约）**：
  - 缓存目录：`{REPO_ROOT}/.cache/reverse/interfaces/`
    - 如 `few-shot-examples.json`、`interface-list.json`、`.cache-status.json`（**不含** `architecture.json`）
  - 文档目录：`{REPO_ROOT}/omni-doc/specs/interfaces/`
    - 单接口详情：`{接口ID}_{英文业务名称}.md`
    - 接口清单：`接口清单.md`
- **下游依赖**：
  - 为 entities / scenarios / external-interfaces 等阶段提供可选输入。

### 阶段3：功能反构（functions）

- **调用**：`reverse-functions`
- **参考文档**：`reverse-functions.md`
- **输入（可变）**：
  - 扫描范围：`--path` / `--files`，`--exclude`（可选）
  - 可选依赖：阶段2 产出的接口清单/入口信息（若存在则复用；否则按 functions 自身策略从代码推断）；可选读取 `omni-doc/specs/logic_architecture/architecture.json` 作为上下文
- **输出（不可变，契约）**：
  - 功能清单与功能文档，以 `reverse-functions.md` / `reverse-functions` Skill 约定为准。

### 阶段4：实体反构（entities）

- **调用**：`reverse-entities`
- **参考文档**：`reverse-entities.md`
- **输入（可变）**：
  - 扫描范围：`--path` / `--files`，`--exclude`（可选）
  - 可选依赖：阶段2/3 的产物（interfaces / functions），存在则优先消费，不存在则按 entities 自身策略降级处理；可选读取逻辑架构 JSON。
- **输出（不可变，契约）**：
  - 缓存目录：`{REPO_ROOT}/.cache/reverse/entities/`
  - 文档目录：`{REPO_ROOT}/omni-doc/specs/entities/`（实体清单 + 单实体文档，具体命名以 entities 阶段文档为准）。

### 阶段5：场景反构（scenarios）

- **调用**：`reverse-scenarios`
- **参考文档**：`reverse-scenarios.md`
- **输入（可变）**：
  - 扫描范围：`--path` / `--files`，`--exclude`（可选）
  - 可选依赖：接口清单、功能清单、测试用例等（存在则消费，不存在则按 scenarios 自身策略降级）。
- **输出（不可变，契约）**：
  - 缓存目录：`{REPO_ROOT}/.cache/reverse/scenarios/`
    - 如 `scenario-list.json`、`.cache-status.json` 等
  - 文档目录：`{REPO_ROOT}/omni-doc/specs/scenarios/`
    - 场景清单：`场景清单.md`（含各场景超链接）
    - 单场景：`SCN-XXX-*.md`
- **下游依赖**：
  - 为 requirements 阶段提供场景文档输入。

### 阶段6：需求反构（requirements）

- **调用**：`reverse-requirements`
- **参考文档**：`reverse-requirements.md`
- **输入（可变）**：
  - 场景文档来源：工程内 `SCN-XXX-*.md`
    - 默认：使用阶段5 输出目录；
    - 也允许用户提前准备/放置。
  - 过滤范围：`--path` / `--exclude`（可选，用于限定搜索范围）。
- **输出（不可变，契约）**：
  - `需求设计.md`
  - 独立需求文件：`{ID_PREFIX}-XXX-*.md`
  - 需求清单：`omni-doc/specs/requirements/需求清单.md`（含各需求超链接）
  - 具体输出目录以 `reverse-requirements` Skill 约定为准。

### 阶段7：外部接口识别（external-interfaces）

- **调用**：`reverse-external-interfaces`
- **参考文档**：`reverse-external-interfaces.md`
- **输入（可变）**：
  - 扫描范围：`--path` / `--files`，`--exclude`（可选）
  - 可选依赖：接口清单（若阶段2 已产出则复用；否则按 external-interfaces 自身策略从代码识别外部依赖）。
- **输出（不可变，契约）**：
  - 外部接口清单与文档，以 `reverse-external-interfaces` Skill 约定为准。

### 阶段8：规则/约束反构（rules）

- **调用**：`reverse-rules`
- **参考文档**：`reverse-rules.md`
- **输入（可变）**：
  - 扫描范围：`--path` / `--files`，`--exclude`（可选）
  - 可选依赖：前序阶段产物（接口/功能/场景/需求等文档若存在可作为辅助上下文）。
- **输出（不可变，契约）**：
  - 规则/约束文档（如 `.mdc`），以 `reverse-rules` Skill 约定为准。

## 执行步骤（编排逻辑）

1. **统一参数解析与环境准备**
   - 使用 `reverse.md` 中的入口规则解析 `$ARGUMENTS`，获取公共参数与 `REPO_ROOT`。
   - 忽略 `--interactive`：即使用户传入也**不得进入对话模式**。
   - 如存在 `--non-interactive` 或 `--yes`，仅视为「显式确认全自动模式」，与默认行为一致。
   - 初始化通用缓存目录：`{REPO_ROOT}/.cache/reverse/`。
   ✅ Checkpoint: "Step 1 完成: 参数已解析, REPO_ROOT={值}, 缓存目录已初始化"

2. **创建总 Todo 列表**
   - 主任务："执行 reverse --target all 进行全流程反构"。
   - 子任务：
     - "阶段1: 逻辑架构反构（logic_architecture）"
     - "阶段2: 接口反构（interfaces）"
     - "阶段3: 功能反构（functions）"
     - "阶段4: 实体反构（entities）"
     - "阶段5: 场景反构（scenarios）"
     - "阶段6: 需求反构（requirements）"
     - "阶段7: 外部接口识别（external-interfaces）"
     - "阶段8: 规则/约束反构（rules）"
   - 使用 `todo_write` 工具创建，初始状态为 `pending`。
   ✅ Checkpoint: "Step 2 完成: 已创建 9 个 Todo（1 主任务 + 8 阶段子任务，pending 状态）"
   失败降级: TodoWrite 失败 → 记录主任务状态为 pending，继续执行

3. **按顺序串行执行 8 个阶段**
   - 对每个阶段：
     - 将对应 todo 标记为 `in_progress`；
     - 调用相应 `reverse-*` Skill，并按本文件「阶段顺序与输入/输出契约」传递参数与依赖产物路径；
     - 完成且无致命错误时，将 todo 标记为 `completed`；
     - 如阶段失败或关键依赖缺失（例如缺少 `SCN-XXX-*.md`），立即：
       - 用中文输出错误原因与建议；
       - 中止后续阶段执行；
       - 保持主任务与当前阶段 todo 为未完成状态。
   ✅ Checkpoint: "Step 3 完成: 已执行 {已执行数}/8 阶段, 已完成数 == 应完成数"
   失败降级: 阶段失败 → 中止后续阶段，记录失败原因

4. **模式要求：全自动、不停顿**
   - 全流程执行时：
     - **不进入对话模式**：禁止在阶段间或阶段内询问「是否继续」「是否确认」等问题；
     - 将子 target 文档中的「交互确认」步骤一律视为**已确认**，按其全自动分支执行。
   ✅ Checkpoint: "Step 4 完成: 全自动模式已确认，不进入对话"

5. **参数与缓存复用策略**
   - `--path` / `--files`：作为**主扫描范围**，在各阶段中保持一致；若某阶段有更细粒度参数需求，由该阶段 Skill 的文档补充说明。
   - `--exclude`：在所有「扫描/搜索代码或文档」的子阶段中统一应用，避免重复配置。
  - `--clear-cache`：在 `--target all` 下表示**清理所有相关 target 的缓存**（logic_architecture/interfaces/functions/entities/scenarios/requirements/external-interfaces/rules），从头执行各阶段；其中逻辑架构含 `.cache/reverse/logic_architecture/` 及按需清理 `omni-doc/specs/logic_architecture/architecture.json`（若策略要求完全重录）。
   - 增量/差异参数（如 `--incremental`、`--git-diff`、`--since`）：在支持这些模式的阶段中启用相应分支，其余阶段按正常全量模式执行。
   ✅ Checkpoint: "Step 5 完成: 主扫描范围={path}, 排除模式={exclude_count}项, 增量参数={状态}"

## 依赖链声明

- **阶段 N 的输出 = 阶段 N+1 的输入**：后续阶段必须读取前序阶段已写入约定路径的产物，不可重新推断
- **禁止重新生成**：阶段产物一旦写入约定路径，后续阶段直接复用，不重新搜索或覆盖
- **交叉验证**：写入阶段产物前，验证路径目录是否存在，文件是否可写

## 子技能依赖

本编排 Skill 串接以下 8 个子 Skill，按阶段顺序执行：

| 阶段 | Skill 名称 | 依赖关系 |
|------|------------|----------|
| 1 | reverse-logic-architecture | 无上游依赖（最先执行） |
| 2 | reverse-interfaces | 强制依赖阶段1的 architecture.json |
| 3 | reverse-functions | 可选依赖阶段2的接口清单 |
| 4 | reverse-entities | 可选依赖阶段2/3的产物 |
| 5 | reverse-scenarios | 可选依赖接口/功能/测试用例 |
| 6 | reverse-requirements | 依赖阶段5的场景文档（SCN-XXX-*.md） |
| 7 | reverse-external-interfaces | 可选依赖阶段2的接口清单 |
| 8 | reverse-rules | 可选依赖前序阶段产物 |

**调用方式**：通过 Claude 的 Skill 触发机制自动调用各子 Skill，AI 根据阶段描述中的参数传递产物路径。

**注意事项**：
- 阶段间通过 Todo 列表维护进度状态
- 阶段产物通过约定的输出路径传递
- 阶段失败时中止后续阶段执行

## 错误处理

### 阶段失败处理策略

**自动回滚**：
- 各阶段执行失败时，当前阶段 Todo 保持 `in_progress` 状态，不标记完成
- 已完成阶段产物保留在缓存目录，供问题排查使用
- 主任务 Todo 保持 `pending` 状态

**常见失败场景及处理**：

| 阶段 | 常见失败原因 | 处理策略 |
|------|-------------|----------|
| 阶段1（逻辑架构） | 扫描范围无代码文件、路径无效 | 提示用户检查 --path 参数 |
| 阶段2（接口） | 缺少 architecture.json（阶段1未完成） | 中止并提示先完成阶段1 |
| 阶段3（功能） | 扫描超时、文件过大 | 缩小扫描范围或排除大文件 |
| 阶段4（实体） | 依赖产物格式解析失败 | 降级使用自身推断策略 |
| 阶段5（场景） | 缺少 SCN-XXX-*.md 场景文档 | 提示场景文档来源或跳过该阶段 |
| 阶段6（需求） | 场景文档数量不足 | 提示需要至少 N 个场景文档 |
| 阶段7（外部接口） | 网络访问受限、依赖识别失败 | 降级为本地代码分析 |
| 阶段8（规则） | 前序产物缺失 | 降级使用基础规则生成 |

### 恢复策略

**重新执行**：
- 使用 `--clear-cache` 清理缓存后重新执行失败的阶段
- 重新执行会保留已完成阶段（除非显式清理）

**部分重跑**：
- 可单独调用失败的子 Skill 进行重试
- 子 Skill 会自动读取已有的上游产物（若仍有效）

## 使用示例

### 基本用法

**执行全流程反构**：
```
reverse --target all --path ./src
```

**指定输出目录**：
```
reverse --target all --path ./src --output-dir ./omni-doc
```

### 进阶用法

**增量更新（仅处理变更文件）**：
```
reverse --target all --path ./src --incremental
```

**基于 Git 差异分析**：
```
reverse --target all --since "2024-01-01"
```

**排除特定目录**：
```
reverse --target all --path ./src --exclude "**/test/**" --exclude "**/__pycache__/**"
```

### 常见场景

| 场景 | 命令 | 说明 |
|------|------|------|
| 首次全量分析 | `reverse --target all --path ./src` | 扫描全部代码生成文档 |
| 增量更新 | `reverse --target all --path ./src --incremental` | 仅分析变更文件 |
| 指定输出位置 | `reverse --target all --path ./src --output-dir ./docs` | 自定义输出目录 |
| 排除测试代码 | `reverse --target all --path ./src --exclude "**/test/**"` | 不分析测试代码 |

## 上下文管理

### Todo 状态管理

**状态传递机制**：
- 通过 TodoList 工具创建 9 个任务（1 个主任务 + 8 个阶段任务）
- 阶段间状态通过 Todo 描述字段传递中间产物路径
- 每个阶段完成后标记为 `completed`，失败保持 `in_progress`

**状态示例**：
```markdown
主任务: "执行 reverse --target all 进行全流程反构"
  子任务: "阶段1: 逻辑架构反构" → completed
  子任务: "阶段2: 接口反构" → in_progress
  ...
```

### 阶段间数据传递

**传递方式**：
- 文件路径传递：产物写入约定路径，下游阶段按需读取
- 缓存目录：`{REPO_ROOT}/.cache/reverse/{target}/`
- 文档目录：`{REPO_ROOT}/omni-doc/specs/{target}/`

**关键产物依赖**：
```
architecture.json → interfaces → functions/entities/scenarios
                                         ↓
                              requirements ← scenarios
```

### Token 预算参考

全流程 8 阶段预估 Token 消耗（实际因代码规模而异）：

| 阶段 | 预估 Token | 主要消耗 |
|------|-----------|----------|
| 阶段1 逻辑架构 | 20K | 代码库结构分析 |
| 阶段2 接口 | 30K | 接口扫描与文档生成 |
| 阶段3 功能 | 40K | 函数识别与分析 |
| 阶段4 实体 | 20K | 实体建模 |
| 阶段5 场景 | 30K | 场景文档生成 |
| 阶段6 需求 | 25K | 需求提取与设计 |
| 阶段7 外部接口 | 15K | 外部依赖识别 |
| 阶段8 规则 | 10K | 规则提取 |
| **总计** | **~190K** | - |

