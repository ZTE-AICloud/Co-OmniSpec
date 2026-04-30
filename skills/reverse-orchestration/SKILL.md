---
name: reverse-orchestration
description: 全流程反构编排. 当 reverse 的 --target 为 all 时触发.
user-invokable: false
---

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

3. **按顺序串行执行 8 个阶段**
   - 对每个阶段：
     - 将对应 todo 标记为 `in_progress`；
     - 调用相应 `reverse-*` Skill，并按本文件「阶段顺序与输入/输出契约」传递参数与依赖产物路径；
     - 完成且无致命错误时，将 todo 标记为 `completed`；
     - 如阶段失败或关键依赖缺失（例如缺少 `SCN-XXX-*.md`），立即：
       - 用中文输出错误原因与建议；
       - 中止后续阶段执行；
       - 保持主任务与当前阶段 todo 为未完成状态。

4. **模式要求：全自动、不停顿**
   - 全流程执行时：
     - **不进入对话模式**：禁止在阶段间或阶段内询问「是否继续」「是否确认」等问题；
     - 将子 target 文档中的「交互确认」步骤一律视为**已确认**，按其全自动分支执行。

5. **参数与缓存复用策略**
   - `--path` / `--files`：作为**主扫描范围**，在各阶段中保持一致；若某阶段有更细粒度参数需求，由该阶段 Skill 的文档补充说明。
   - `--exclude`：在所有「扫描/搜索代码或文档」的子阶段中统一应用，避免重复配置。
  - `--clear-cache`：在 `--target all` 下表示**清理所有相关 target 的缓存**（logic_architecture/interfaces/functions/entities/scenarios/requirements/external-interfaces/rules），从头执行各阶段；其中逻辑架构含 `.cache/reverse/logic_architecture/` 及按需清理 `omni-doc/specs/logic_architecture/architecture.json`（若策略要求完全重录）。
   - 增量/差异参数（如 `--incremental`、`--git-diff`、`--since`）：在支持这些模式的阶段中启用相应分支，其余阶段按正常全量模式执行。

