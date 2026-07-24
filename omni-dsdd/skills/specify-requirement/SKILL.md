---
name: specify-requirement
description: 从系统视角分析业务意图对既有需求的影响，生成变更需求（INSERT/MODIFY/DELETE/REFER），并追加到 spec.md。仅被 /specify skill 显式调用，不自动触发。使用 EARS 需求表达法进行结构化需求描述。
user-invocable: false
allowed-tools: Read, Write, Edit, Grep, Glob
---
# specify-requirement

## 使用时机

- 仅被 `specify` skill 显式调用

## 阶段总览

本技能按顺序执行以下4个步骤：

1. **明确输入与上下文**：解析业务意图和上下文文件
2. **分析既有需求的变更**：识别 INSERT/MODIFY/DELETE/REFER 动作
3. **生成「需求」章节内容**：按照模板产出需求条目
4. **追加到 spec.md**：将生成的内容追加到规格文档

## 上下文管理

### 阶段间数据传递

| 阶段 | 数据传递方式 | 说明 |
|------|-------------|------|
| 步骤1 → 步骤2 | `$ARGUMENTS` + `context.md` | 业务意图作为主输入 |
| 步骤2 → 步骤3 | 内存中的需求条目列表 | 识别出的变更需求 |
| 步骤3 → 步骤4 | 生成的需求章节文本 | 待追加的 Markdown 内容 |

### 上下文加载策略

- 优先读取 `FEATURE_DIR/context.md` 获取架构分析、可复用模式
- 若 `context_mode = evidence_first`，优先使用 `on_demand.*` 字段
- 需求文档读取路径：`DOC_DIR/specs/requirements/`
- **禁止重新生成**：后续步骤必须引用前序实际输出，不可重新搜索已有结论
- **计数链传递**：每个 Checkpoint 的计数必须传递到下一步
- **写入前交叉验证**：追加到 spec.md 前必须先 Read 验证 ID 不冲突

## 需求定义

- 始终从系统整体视角出发，规范性地描述系统应具备的能力与外部可观测行为（回答“系统在何种条件下应做什么/如何响应”），而非记录具体的用户操作步骤。
- 使用 **EARS 需求表达法** 对需求进行结构化描述:
  - 主句形式: 系统 shall [能力描述]
  - 条件子句:
    - When [触发事件]，系统 shall [系统响应]
    - While [特定状态]，系统 shall [系统响应]
    - If [异常条件]，系统 shall [系统响应]
    - Where [可选特性]，系统 shall [系统响应]

## DoD（完成校验）

| 检查项 | 标准 |
|--------|------|
| 系统视角 | 所有需求均以系统能力与系统对外部事件/状态的响应为中心，不掺入实现细节或分步式的用户操作流程 |
| 结构清晰 | 需求条目采用 EARS 风格或等效「条件–响应」结构，覆盖主要触发条件、关键系统状态及代表性异常路径 |
| 变更完整 | 对应需求文档已按 INSERT/MODIFY/DELETE/REFER 规则完成更新，加粗/删除线标记准确一致 |
| ID连续 | 新增需求的 REQ-XXX 基于当前最大值递增，无冲突；重要需求具备可验证的验收标准或测试思路 |
| 澄清受控 | [NEEDS CLARIFICATION] ≤ 3 个，仅保留高影响事项的待澄清问题 |

## 指令

### 步骤1: 明确输入与上下文

- **业务意图**: 从上层命令传入的 `$ARGUMENTS`, 表达本次要实现或调整的业务目标。
- **上下文文件**: 优先读取 `FEATURE_DIR/context.md`, 参考其中的:
  - 「相关需求文档」章节，作为既有需求的主要参考来源
  - 架构分析、可复用模式、术语对齐、约束和假设
  - 若 `context_mode = evidence_first`，优先使用 `on_demand.scope`、`on_demand.traceability`、`on_demand.contract_deltas`、`on_demand.risks`、`on_demand.evidence_gaps`

### 步骤2: 分析既有需求的变更

基于步骤1输入与上下文，按「需求定义」识别并产出本次变更涉及的全部需求条目（含INSERT/MODIFY/DELETE/REFER），作为后续步骤的范围基线。

动作类型定义:
  - **MODIFY**: 业务意图要求对既有某条需求进行调整或细化。
  - **INSERT**: 理解既有需求后，若业务意图无法合理归属到任何既有需求条目，则需新增所需需求；不存在既有需求时，则需新增所需需求。
  - **DELETE**: 除非删除具有明确业务必要性且风险可控，否则不删除；必须给出充分理由与影响分析（依赖方、兼容策略、回滚策略）。
  - **REFER**: 既有需求已充分覆盖当前业务意图，无需对内容作任何修改，但需记录引用关系以支持后续影响分析。

边界增强规则（仅 evidence_first 模式）：

- 以 `on_demand.scope` 中 in-scope 对象为需求边界基线，避免范围漂移。
- 对 `on_demand.traceability` 命中的已有需求，优先判定为 MODIFY/REFER，减少无依据 INSERT。
- 对 `on_demand.contract_deltas` 提示的接口契约变更，必须落到需求条目（输入变化/输出变化/兼容约束）。
- `on_demand.risks` 与 `on_demand.evidence_gaps` 优先转化为：
  - 显式假设（有合理默认值时）
  - 或 `[NEEDS CLARIFICATION]`（无合理默认值且影响范围/验收）

兼容规则（default 模式）：

- 若 `context_mode = default` 或 `on_demand` 字段缺失，完全沿用原有规则，不阻塞需求生成。

### 步骤3: 按照以下模板生成「需求」章节内容
```
## 需求

### [INSERT/MODIFY/DELETE/REFER] - [需求ID] - [需求名称]

变更原因: [分析业务意图对存量需求的影响]

[需求内容]

[按上述格式继续描述其他需求...]
```

#### MODIFY
1. 从既有需求文档中准确提取对应条目的完整内容，填充到上述模板占位符。
2. 基于 `业务意图` 分析本次变更的动机与影响范围，明确需要调整的具体内容。对**新增或修改**的部分使用 `**加粗**` 标记，对**拟删除**的内容使用 `~~删除线~~` 标记，以便后续评审与追踪。

#### INSERT
1. 生成需求ID:
  - 读取 `DOC_DIR/specs/requirements/0.requirement_list.md`，提取已存在的 `REQ-XXX` 最大ID，取 `最大ID + 1` 作为新需求的ID。
  - 不存在 `0.requirement_list.md` 时，需求ID从 `REQ-001` 开始。
2. 依据 `.omni-infra/metamodel/1.requirement-template.md` 中的规范生成新需求内容:
    - 参考 `DOC_DIR/specs/requirements/` 下既有文档的组织方式与粒度，使新需求在抽象层级上与既有需求保持一致，避免过于宽泛（难以验证）或过于聚焦实现细节。
3. 使用步骤 3 中的模板，将生成的需求内容整理为「需求」章节条目。

#### DELETE
1. 从既有需求文档中提取拟删除条目的完整内容，填充到上述模板占位符。
2. 以审慎态度给出充分且清晰的变更原因，说明删除该需求在业务、合规与技术层面的必要性。

#### REFER
从既有需求文档中提取对应条目的完整内容填入模板，占位符 `[变更原因]` 统一填写为 **无变更**，仅建立引用关系以支持后续波及分析。

### 步骤4: 将生成的「需求」章节内容追加到 `FEATURE_DIR/spec.md` 末尾

## 错误处理

### 文件不存在
- `FEATURE_DIR/context.md` 不存在：跳过上下文读取，仅使用 $ARGUMENTS
- `DOC_DIR/specs/requirements/0.requirement_list.md` 不存在：需求ID从 REQ-001 开始

### 格式错误
- 需求ID冲突：使用当前最大ID+1
- EARS格式错误：参照 .omni-infra/metamodel/1.requirement-template.md 修正

### 特殊情况
- `[NEEDS CLARIFICATION]` 标记超过3个：提示用户优先澄清
- 业务意图无法归属任何既有需求：自动判定为 INSERT

## 使用示例

### 示例1：新增需求
```
业务意图：用户需要支持批量导入功能
```

处理后生成：
```markdown
## 需求

### INSERT - REQ-XXX - 批量导入功能

变更原因: 用户需要支持批量导入功能，无需对存量需求进行调整

系统 shall 支持批量导入 CSV 格式的数据文件。

...
```

### 示例2：修改既有需求
```
业务意图：调整用户登录的超时策略，从30分钟延长至60分钟
```

处理后生成：
```markdown
## 需求

### MODIFY - REQ-005 - 用户会话管理

变更原因: 安全策略调整，延长会话超时时间

If 用户在 **60分钟**（原为30分钟）内无操作，系统 shall 自动终止会话并重定向至登录页面。
```

### 示例3：引用既有需求
```
业务意图：当前业务目标已被现有需求覆盖
```

处理后生成：
```markdown
## 需求

### REFER - REQ-012 - 数据加密存储

变更原因: 无变更

...
```

## 参考文档

- **EARS 需求表达法**：详见 `.omni-infra/metamodel/1.requirement-template.md`
- **需求文档目录**：`DOC_DIR/specs/requirements/`
- **需求清单**：`DOC_DIR/specs/requirements/0.requirement_list.md`
- **上下文文件**：`FEATURE_DIR/context.md`
- **规格文档**：`FEATURE_DIR/spec.md`
- **父技能**：由 `/specify` skill 调用
