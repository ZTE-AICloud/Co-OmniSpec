---
name: archive
description: 将变更指示文件中的需求/设计/接口变更回流到 DOC_DIR/specs 下的要素文档. 当需要从 feature 变更目录同步更新到 DOC_DIR/specs 下的需求、场景、实体、功能和接口文档及其清单与关联关系时使用
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, Skill
---

# archive

将变更目录中的变更指示文件（spec.md/design.md/contracts/\*.md）解析并应用到 `DOC_DIR/specs/` 下的要素文档，保持规范文档与变更实现的一致性。

## 输入

- **配置脚本输出（必需）**：
    - Windows: `scripts/powershell/check-prerequisites.ps1 --json --paths-only`
    - Linux: `scripts/bash/check-prerequisites.sh --json --paths-only`
    - **期望字段**：`REPO_ROOT`、`BRANCH`、`FEATURE_DIR`、`FEATURE_SPEC`、`IMPL_DESIGN`、`CHANGES_DIR`（即 FEATURE_DIR）、`DOC_DIR`、`DOC_SPECS_DIR` 等
- **变更文件（必需）**（都位于 `CHANGES_DIR` 下）：
    - `spec.md`：需求与场景变更（参考 `spec-template.md`）
    - `design.md`：逻辑实体与功能变更（参考 `design-template.md`）
    - `contracts/*.md`：接口文档变更（参考 `interface-template.md`）
- **模板文件（必需）**（位于 `.omni-infra/metamodel/`）：
    - `1.requirement-template.md`
    - `3.scenario-template.md`
    - `5.function-template.md`
    - `6.entity-template.md`
    - `7.interface-template.md`
- **现有规范文档与清单/关联文件（如存在）**：
    - `DOC_DIR/specs/requirements/*.md`、`DOC_DIR/specs/requirements/requirements.json`
    - `DOC_DIR/specs/scenarios/*.md`、`DOC_DIR/specs/scenarios/0.scenario_list.md`
    - `DOC_DIR/specs/logic_entities/*.md`、`DOC_DIR/specs/logic_entities/0.entity_list.md`
    - `DOC_DIR/specs/functions/*.md`、`DOC_DIR/specs/functions/0.function_list.md`、`DOC_DIR/specs/functions/functions.json`
    - `DOC_DIR/specs/interfaces/*.md`、`DOC_DIR/specs/interfaces/0.interface_list.md`、`DOC_DIR/specs/interfaces/interface.json`

## 输出

- **更新后的要素文档**：
    - 需求：`DOC_DIR/specs/requirements/REQ-XXX-*.md`
    - 场景：`DOC_DIR/specs/scenarios/SCN-XXX-*.md`
    - 逻辑实体：`DOC_DIR/specs/logic_entities/ENTITY-XXX-*.md`
    - 功能：`DOC_DIR/specs/functions/FUNC-XXX-*.md`
    - 接口：`DOC_DIR/specs/interfaces/API-XXX-*.md`
- **更新后的清单与关联关系文件**：
    - `DOC_DIR/specs/scenarios/0.scenario_list.md`
    - `DOC_DIR/specs/logic_entities/0.entity_list.md`
    - `DOC_DIR/specs/functions/0.function_list.md`（如存在）
    - `DOC_DIR/specs/requirements/requirements.json`
    - `DOC_DIR/specs/functions/functions.json`
    - `DOC_DIR/specs/interfaces/interface.json`
- **执行结果摘要**（由 Agent 输出的自然语言报告）：
    - 新增/修改/删除的文档列表
    - 关联关系更新情况
    - 检测到的错误或需要人工确认的冲突

## 指令
### 0. skill执行开始时间打点记录

开始执行步骤之前，需要进行一些打点记录工作，记录本skill的执行时间到 `start_time`字段：
 - 判断当前操作系统，windows还是linux系统;
 - 针对不同操作系统运行脚本获取配置
   windows: `Get-Date -Format "yyyy-MM-dd HH:mm:ss"`
   linux: `date +"%Y-%m-%d %H:%M:%S"`
 - 将获取的时间记录到 `start_time`

### 1. 环境与路径准备

1. 调用对应操作系统的先决条件检查脚本：
    - Windows: `scripts/powershell/check-prerequisites.ps1 --json --paths-only`
    - Linux: `scripts/bash/check-prerequisites.sh --json --paths-only`
2. 解析脚本返回的 JSON，获得至少以下变量：
    - `REPO_ROOT`、`BRANCH`、`FEATURE_DIR`、`CHANGES_DIR`、`DOC_DIR`、`DOC_SPECS_DIR`
3. 使用绝对路径构造后续所有文件路径，禁止使用相对路径进行文件读写。
4. 验证以下路径存在且非空（如适用）：
    - `CHANGES_DIR/spec.md`（如缺失则按错误处理规则处理）
    - `CHANGES_DIR/design.md`
    - `CHANGES_DIR/contracts/` 目录（可为空，但目录本身应存在）
    - `.omni-infra/metamodel/` 下所需模板文件

### 2. 读取与解析变更文件

1. 从 `CHANGES_DIR/spec.md` 中解析**需求**与**场景**变更条目：
    - 需求行格式：`[动作类型，INSERT/MODIFY/DELETE/REFER] - REQ-XXX - [名称]`
    - 场景行格式：`[动作类型，INSERT/MODIFY/DELETE/REFER] - SCN-XXX - [名称](优先级: P1/P2/P3)`
2. 从 `CHANGES_DIR/design.md` 中按章节解析：
    - **逻辑实体**章节：`[动作类型:INSERT/MODIFY/DELETE/REFER] - ENTITY-XXX([名称])`
    - **功能**章节：`[动作类型，INSERT/MODIFY/DELETE/REFER] - FUNC-XXX - [名称](优先级: P1/P2/P3)`
3. 从 `CHANGES_DIR/contracts/*.md` 中解析接口信息：
    - 接口 ID：`API-XXX`
    - 接口名称
    - 文件路径
    - 消息类型标识符等关键元数据
4. 在解析过程中校验：
    - ID 格式是否符合：`REQ-XXX`、`SCN-XXX`、`ENTITY-XXX`、`FUNC-XXX`、`API-XXX`（`XXX` 为三位数字）
    - 动作类型是否在 `{INSERT, MODIFY, DELETE, REFER}` 集合内
    - 必要字段（名称、优先级、关联信息等）是否存在
5. 对于解析失败或格式错误的条目：
    - 记录详细错误信息（所在文件、行号、原始文本）
    - 按错误处理规则决定是跳过该条目还是终止执行。

### 3. 应用需求与场景变更（来自 spec.md）

#### 3.1 需求（REQ-XXX）

1. 针对每条需求变更，根据动作类型执行：
    - **INSERT**：
        - 基于 `.omni-infra/metamodel/1.requirement-template.md` 生成 `DOC_DIR/specs/requirements/REQ-XXX-*.md` 新文档。
        - 在模板中填充至少：ID、名称、来源信息、简要描述。
        - 若目标文件已存在，按“INSERT 冲突”错误处理规则处理（优先报冲突，禁止静默覆盖）。
    - **MODIFY**：
        - 定位已有 `REQ-XXX-*.md` 文档，若不存在则按错误处理规则终止或报告。
        - 依据变更内容更新文档，并使用标记规范：
            - `**加粗**` 表示新增内容
            - `~~删除线~~` 表示删除内容
    - **DELETE**：
        - 确认目标文档存在后删除或标记为废弃，并记录删除原因。
    - **REFER**：
        - 不修改目标文档，仅在关联或变更记录中登记引用关系。
2. 确保需求文档中的元数据（如 ID、名称）与变更指示保持一致。

#### 3.2 场景（SCN-XXX）

1. 针对每条场景变更，根据动作类型执行：
    - **INSERT**：
        - 基于 `.omni-infra/metamodel/3.scenario-template.md` 创建新场景文档。
        - 从变更条目及上下文中提取“归属的需求”，并更新 `DOC_DIR/specs/requirements/requirements.json` 中的场景-需求关联。
    - **MODIFY / DELETE**：
        - 更新或移除对应场景文档，以及 `0.scenario_list.md` 中的清单条目。
2. 更新 `DOC_DIR/specs/scenarios/0.scenario_list.md`：
    - 新增场景按 ID 顺序插入。
    - 保持列表格式与现有文档一致。

### 4. 应用逻辑实体与功能变更（来自 design.md）

#### 4.1 逻辑实体（ENTITY-XXX）

1. 对每条逻辑实体变更按动作类型处理：
    - **INSERT**：
        - 使用 `.omni-infra/metamodel/6.entity-template.md` 创建实体文档。
    - **MODIFY**：
        - 仅更新变更涉及的属性、方法、职责说明等字段。
    - **DELETE / REFER**：
        - 删除或保留文档，并根据需要更新引用信息。
2. 更新实体清单 `DOC_DIR/specs/logic_entities/0.entity_list.md`，确保：
    - 按 ID 排序
    - 无重复或悬空条目

#### 4.2 功能（FUNC-XXX）

1. 对每条功能变更按动作类型处理：
    - **INSERT**：
        - 使用 `.omni-infra/metamodel/5.function-template.md` 创建功能文档。
        - 从变更内容中提取“来源场景”，并更新 `functions.json` 中的功能-场景关联。
    - **MODIFY / DELETE / REFER**：
        - 相应更新或标记功能文档及清单。
2. 若存在 `DOC_DIR/specs/functions/0.function_list.md`：
    - 按 ID 顺序维护列表，插入新增功能，移除删除的功能。

### 5. 应用接口变更（来自 contracts/\*.md）

1. 对 `CHANGES_DIR/contracts/` 下每个接口变更文档：
    - 提取接口 ID（`API-XXX`）、名称、消息类型标识符、文件相对路径等信息。
    - 对于 **INSERT**：
        - 使用 `.omni-infra/metamodel/7.interface-template.md` 创建接口文档。
    - 对于 **MODIFY / DELETE / REFER**：
        - 更新或移除对应接口文档及清单条目。
2. 维护接口清单 `DOC_DIR/specs/interfaces/0.interface_list.md`（如存在）：
    - 按接口 ID 排序
    - 确保名称、路径等信息与实际文档一致。

### 6. 更新关联关系 JSON

根据前述步骤中收集的关联信息，统一更新以下 JSON 文件：

1. `requirements.json`：
    - 维护场景与需求之间的关联。
    - 来源：`spec.md` 中场景条目的“归属的需求”字段。
2. `functions.json`：
    - 维护功能与场景之间的关联。
    - 来源：`design.md` 中功能条目的“来源场景”字段。
3. `interface.json`：
    - 维护接口与功能之间的关联。
    - 来源：接口文档中的功能引用信息或变更条目说明。

在更新上述 JSON 文件时：

- 确保 JSON 结构合法且可解析。
- 避免生成悬空关联（引用不存在的需求/场景/功能/接口）。
- 对于删除的要素，应同步清理其在关联文件中的引用。

### 7. 校验与结果报告

1. **结构与格式校验**：
    - 所有新建或修改的 Markdown 文档：
        - Front matter 存在且字段齐全。
        - Markdown 语法基本正确（标题层级、列表、链接等）。
    - 所有清单与 JSON 文件：
        - 可被对应解析器正常解析。
        - 必要字段存在且类型正确。
2. **一致性检查**：
    - 文档中的 ID 与文件名中的 ID 一致。
    - 清单文件与实际文档集合一致，无多余或缺失条目。
    - 关联 JSON 中的 ID 均可在对应要素文档中找到。
3. **结果输出**：
    - 列出本次执行中：
        - 新增的需求/场景/实体/功能/接口文档
        - 修改的文档（简要说明修改类型）
        - 删除或作废的文档
    - 列出对 `requirements.json`、`functions.json`、`interface.json` 所做的变更摘要。
    - 列出所有阻塞性错误和需人工决策的冲突（例如 INSERT 目标已存在但无法自动合并的情况）。
  
### 8. 记录本skill的运行日志信息

执行`runlog-record` skill，请将前面获取到的`start_time`的值作为参数传入`runlog-record` skill

## 关键规则

- **路径规则**：
    - 全程使用绝对路径访问文件与目录。
    - 所有文档路径均基于脚本返回的 `DOC_DIR` 和 `DOC_SPECS_DIR` 变量计算。
- **ID 与格式规则**：
    - ID 必须符合以下格式（`XXX` 为三位数字）：
        - 需求：`REQ-XXX`
        - 场景：`SCN-XXX`
        - 实体：`ENTITY-XXX`
        - 功能：`FUNC-XXX`
        - 接口：`API-XXX`
    - 变更条目中的动作类型仅允许：`INSERT`、`MODIFY`、`DELETE`、`REFER`。
- **变更标记规则**：
    - 在 MODIFY 场景中，使用：
        - `**加粗**` 表示新增内容
        - `~~删除线~~` 表示被删除内容
- **清单与关联规则**：
    - 清单文件（`0.*_list.md`）中新条目按 ID 排序插入，保持与现有格式完全一致。
    - 任何要素的新增/删除都必须同步更新对应的清单与关联 JSON。
- **错误处理规则**：
    - 变更文件不存在 → 报告错误并终止执行。
    - INSERT 时目标文档已存在 → 报告冲突，不得静默覆盖；若设计允许，可选择人工确认后再执行。
    - MODIFY 时目标文档不存在 → 报告错误并终止该条目处理。
    - ID 格式错误 → 报告错误并跳过该条目。
    - 场景 INSERT 时“归属的需求”缺失 → 报告错误并终止该条目处理。
    - 必要模板文件缺失 → 报告错误并终止执行。
