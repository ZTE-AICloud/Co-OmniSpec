---
name: design
description: 执行实施规划工作流, 使用计划模板生成设计制品，在代码之前建立可执行的技术决策体系。仅通过 /design 命令调用，不自动触发。
context: fork
---
# design

## 输入

- **用户参数**：`$ARGUMENTS`（可为空）

## 输出

- `IMPL_DESIGN`：设计主文档（路径由步骤 1 脚本提供）
- `research.md`：关键技术决策与取舍（位于 FEATURE_DIR 或脚本指定位置）
- `FEATURE_DIR/data-model.md`：数据模型（若适用）
- `FEATURE_DIR/contracts/*`：接口契约（若适用）
- `FEATURE_DIR/quickstart.md`：最小可验证集成与测试路径（若适用）
- Agent 特定上下文文件：由更新脚本生成/更新

## 指令

### 0. skill执行开始时间打点记录

开始执行步骤之前，需要进行一些打点记录工作，记录本skill的执行时间到 `start_time`字段：
 - 判断当前操作系统，windows还是linux系统;
 - 针对不同操作系统运行脚本获取配置
   windows: `Get-Date -Format "yyyy-MM-dd HH:mm:ss"`
   linux: `date +"%Y-%m-%d %H:%M:%S"`
 - 将获取的时间记录到 `start_time`

### 1. 设置阶段

- 判断当前操作系统，windows还是linux系统;
- 针对不同操作系统从仓库根目录运行脚本
  windows:`scripts/powershell/setup-design.ps1 --json`
  linux:`scripts/bash/setup-design.sh --json`
- 解析 JSON 获取 FEATURE_SPEC、IMPL_DESIGN、CHANGES_DIR、BRANCH. 对于参数中的单引号如 "I'm Groot", 使用转义语法: 例如 'I'\''m Groot'(或尽可能使用双引号: "I'm Groot").
- **获取文档目录配置**：运行脚本获取 DOC_DIR 配置
  windows:`scripts/powershell/check-prerequisites.ps1 --json --paths-only`
  linux:`scripts/bash/check-prerequisites.sh --json --paths-only`
- 从 JSON 输出中解析 **DOC_DIR** 变量（如果未设置则默认为 "omni-doc"）
- **重要**: DOC_DIR 将用于后续所有文档路径引用，支持通过环境变量 `SPECIFY_DOC_DIR` 或 `config` 文件配置

### 2. 加载上下文

- 读取 `.infra/memory/constitution.md` 以及 IMPL_DESIGN 模板(已复制)。
- **优先加载 context.md**:
  - **必须检查** `FEATURE_DIR/context.md` 是否存在
  - **如果存在**, 直接读取 `context.md` 作为主要上下文源，提取以下信息:
    - 功能描述和目标
    - 提取的关键词（用于后续检索）
    - 检索到的设计文档列表（可直接参考，减少重复检索）
    - 可复用的需求和场景模式
    - 术语对齐信息
    - 约束和假设
    - **相关代码文件**（新增）：代码文件路径、函数接口、数据结构、实现模式
    - **需要新增的代码**（新增）：消息类型、消息结构、处理函数等
  - **如果不存在**, 继续执行后续检索步骤（但应提示用户先执行 `/spec-impact-analyze` 生成上下文）
- **补充检索**（仅在 context.md 信息不足时执行）:
  1. **如文档无法解答疑问**：允许深入代码仓库执行 `search`（可用 `grep`、`read_file` 逐文件阅读），直到澄清概念或接口约束，避免凭空猜测。**优先参考 context.md 中的代码文件**: 如果 context.md 中已列出相关代码文件，优先阅读这些文件，了解现有实现模式 2.**查找文件时禁止使用限制命令**：使用 `read_file`、`grep`、`glob_file_search` 等工具时，**严禁使用 `head`、`tail`、`limit` 等命令限制输出**，必须读取完整内容以准确理解项目结构
- **逻辑架构文档（与 `design-entity` / `design-interface` 一致）**:
  - **解析顺序**（均相对于仓库根目录，与 `DOC_DIR` 拼接；**不阻塞**：任一不存在则尝试下一项，两项均不存在则跳过）：
    1. `${DOC_DIR}/on-demand/logic_architecture.md`（按需反构快照，**优先**）
    2. `${DOC_DIR}/specs/logic_architecture.md`（规格库）
  - **生效规则**：按顺序选用**第一个存在的文件**作为本次设计的**有效架构约束**；若两项均不存在，**不报错**，在 IMPL_DESIGN 技术上下文中简要注明「未找到架构文档，分层假设见下文」，后续子技能按同一规则处理。
- **按需反构逐功能文档（可选）**:
  - **路径**：`${DOC_DIR}/on-demand/functions/`（目录，内含 `*.md`；与按需反构阶段约定一致）
  - **若目录存在且含至少一个 `.md`**：列出并读取与本次变更相关的功能文档（优先按 `FEATURE_SPEC`、`context.md` 中的功能名/关键词/`function_key` 匹配；无法判定时可读取目录内全部 `.md` 作为候选），将**现状行为、入口、波及点、证据链**等纳入技术上下文，并在调用 `design-function`、`design-entity`、`design-interface` 时作为**存量实现参考**。
  - **若不存在**：跳过，不阻塞。
- **上下文模式与兼容回退（强制）**:
  - 读取 `FEATURE_DIR/context.md` 中的 `context_mode` 与 `on_demand` 结构（若存在）。
  - 若 `context_mode = evidence_first`：启用 on-demand 证据优先设计模式。
  - 若 `context_mode = default` 或字段缺失：回退原流程，不阻塞设计。
  - 在任一模式下都必须继续生成设计产物，不得因 on-demand 缺失而中断。

### 2.1 设计边界锁定（仅 evidence_first 模式）

- 以 `on_demand.scope` 作为设计范围基线：
  - in-scope: `direct_functions`、`indirect_functions`、`interfaces`
  - out-of-scope: 不在基线且无证据链(`on_demand.traceability`)支持的项
- 将以下内容写入 IMPL_DESIGN 的技术上下文或波及分析部分：
  - in-scope 清单
  - out-of-scope 清单
  - 依赖前置条件（来自 `on_demand.risks` / `on_demand.evidence_gaps`）
- 对 `on_demand.contract_deltas` 中出现的契约变化，必须在：
  - 功能设计（行为变化）
  - 接口契约（输入/输出变化）
  - 测试实现分析（覆盖这些变化）
  三处形成一致映射。

### 3. 执行计划工作流

1. 按照 IMPL_DESIGN 模板中的结构填充内容
   - 填充技术上下文(将未知项标记为 `NEEDS CLARIFICATION`)
   - 从章程文档填充章程检查部分
   - 评估关卡（如果违规无正当理由则报错）

2. 阶段 0: 大纲与研究
   - **从技术上下文中提取未知项**:
     - 每个 `NEEDS CLARIFICATION` → 研究任务
     - 每个依赖项 → 最佳实践任务
     - 每个集成 → 模式任务

   - **生成和分发研究任务**:
     ```text
     For each unknown in Technical Context:
     Task: "Research {unknown} for {feature context}"
     For each technology choice:
     Task: "Find best practices for {tech} in {domain}"
     ```

   - **在 `research.md` 中整合发现**，使用格式:
     - Decision: [选择了什么]
     - Rationale: [为什么选择]
     - Alternatives considered: [还评估了什么]
   - **输出**: `research.md`，所有 `NEEDS CLARIFICATION` 已解决
   - **evidence_first 额外要求**:
     - 优先从 `on_demand.risks` 与 `on_demand.evidence_gaps` 生成研究任务
     - 若存在合理默认值则写入假设，不强制新增澄清

3. 阶段 1: 技术设计建模
   - **前提条件**: `research.md` 完成
   - 调用 `design-function` skill，获取功能变更内容，并追加到 IMPL_DESIGN 末尾
   - 调用 `design-entity` skill，获取逻辑实体变更内容，并追加到 IMPL_DESIGN 末尾，以及生成 `data-model.md` 文件
   - 调用 `design-interface` skill，获取接口变更内容，并写入 `contracts/api-contract.md` 文件
   - **输出**: `data-model.md`、`/contracts/*`、`quickstart.md`

4. 阶段 2: Agent上下文更新
   - 判断当前操作系统，windows还是linux系统;
   - 针对不同操作系统从仓库根目录运行脚本
     windows: `scripts/powershell/update-agent-context.ps1`
     linux: `scripts/bash/update-agent-context.sh`
   - 这些脚本检测正在使用哪个 AI Agent
   - 更新相应的Agent特定上下文文件
   - 仅添加当前计划中的新技术
   - 保留标记之间的手动添加内容
   - **输出**: Agent特定文件

5. 阶段 3: 设计后重新评估
   - 重新评估章程检查，确保设计符合项目规范

6. 阶段 4: 测试实现分析（仅当 `$ENABLE_E2E=true` 时执行）

  - **判断条件**：检查传入的 `$ENABLE_E2E` 参数
    - 若 `$ENABLE_E2E=false` 或未设置：跳过阶段 4 和阶段 5，直接进入步骤8（设计验证与质量评估）
    - 若 `$ENABLE_E2E=true` 但 `e2e-test.md` 不存在：记录警告"E2E已启用但 e2e-test.md 不存在，跳过测试实现分析"，跳过阶段 4 和阶段 5，直接进入步骤8
    - 若 `$ENABLE_E2E=true` 且 `e2e-test.md` 存在：执行本步骤

  - **前提条件**：`design.md` 已完成，`e2e-test.md` 已存在

  - **目标**：生成测试实现分析报告，包含入口函数分析、外部依赖分析、测试数据设计、验证点定义

  - **强制要求**：当执行时，测试实现分析必须严格按照 `e2e-design` 技能文件中定义的流程执行，不得跳过或修改任何步骤。

  - 调用 `e2e-design` skill，该技能将：
    1. 验证前置文件（spec.md、design.md、e2e-test.md）
    2. 加载上下文文档（baseline、存量测试代码）
    3. 启动 `test-impl-design` subagent
    4. 生成测试实现分析报告
    5. 验证生成文档内容完整性

  - 执行完本步骤后，将生成以下文档：
  - `e2e-impl-design.md`：测试实现分析报告（包含用例实现映射表、入口函数详细分析、外部依赖详细分析、测试数据清单、验证点详细清单、存量测试复用分析）

  **注意**: 如果步骤6（测试实现分析）验证失败且无法继续（如 agent 执行失败、文档未生成），应记录错误信息并报告失败。

7. 阶段 5: 测试设计完整性检查与完善（仅当 `$ENABLE_E2E=true` 且阶段 4 已执行时执行）

  - **前提条件**：`e2e-design` 已完成，`e2e-impl-design.md` 已存在

  - **目标**：生成测试实现分析报告，包含入口函数分析、外部依赖分析、测试数据设计、验证点定义

  - **强制要求**：当执行时，测试实现分析必须严格按照 `e2e-varify` 技能文件中定义的流程执行，不得跳过或修改任何步骤。

  - 调用 `e2e-varify` skill，该技能将：
    - 执行变更点覆盖分析
    - 执行深度用例设计

  **注意**: 如果步骤7（测试设计完整性检查与完善）验证失败且无法继续（如 agent 执行失败、文档未生成），应记录错误信息并报告失败。

8. 设计验证与质量评估
   * **需求一致性检查**:
     * 加载 `requirement-consistency-check` skill 的检查准则，对 IMPL_DESIGN 执行
     * **Scope Creep 检测**: 变更点是否有 FEATURE_SPEC 中的需求依据
     * **需求覆盖检测**: FEATURE_SPEC 的所有 FR-xxx 是否都有设计条目
     * **语义一致性检测**: 业务场景描述是否与 FEATURE_SPEC 一致
     * 输入: FEATURE_SPEC（参照）+ IMPL_DESIGN（目标）
     * 通过标准: 无 blocking 问题
   * **方案质量评测**:
     * 加载 `solution-evaluation` skill 的五维量规，对 IMPL_DESIGN 评测
     * 结构完整性、语义准确性、业务规则准确性、规则合规性、文档质量（满分 100）
     * 输出: `FEATURE_DIR/.runs/evaluations/design-evaluation-summary.json` + `FEATURE_DIR/design-evaluation-report.md`
     * 通过标准: overall_score >= 95
   * **验证结果处理**:
     * **通过**（无 blocking 且 score >= 95）: 继续完成报告
     * **不通过**: 针对 blocking 问题和低分维度修复 IMPL_DESIGN，重新执行本步骤验证（最多 3 轮）
     * 3 轮后仍不通过: 在报告中标记问题，警告用户，附上 `validation_status: "warning"`

9. 修改点严格检查（强制门禁）
   - 在完成设计产物后、进入完成报告前，必须逐条检查每个修改点：
     1. **是否已经支持**：
        - 依据 context.md、按需反构文档（`${DOC_DIR}/on-demand/functions/*.md`、`${DOC_DIR}/on-demand/interfaces/*.md`）和现有代码证据，判定是“已支持/部分支持/不支持”。
        - 对“已支持/部分支持”项，必须在设计中标注复用入口（模块、接口、函数、配置）。
     2. **是否遵循利旧原则（原有架构与实现）**：
        - 检查设计是否复用现有架构分层、模块边界、既有接口契约和已有实现模式。
        - 若选择新增实现而非复用，必须在 design 中给出“不可复用原因”和“替代方案比较”。
     3. **代码修改是否遵循最小化原则**：
        - 对每个修改点输出最小变更面：目标文件、目标函数/接口、预估新增/改动范围、避免改动项。
        - 禁止无需求依据的跨模块扩散修改（Scope Creep）。
   - **检查输出要求**：
     - 在 `IMPL_DESIGN` 增加“修改点严格检查”小节，至少包含字段：`修改点`、`支持状态`、`利旧结论`、`最小化结论`、`证据`、`风险/备注`。
   - **evidence_first 额外门禁**：
     - 若设计条目不在 `on_demand.scope` 且无 `on_demand.traceability` 证据链支撑，判定为 scope creep，必须回退修正。
     - `on_demand.contract_deltas` 中的所有条目必须在 `contracts/api-contract.md` 可定位；缺失则判定不通过。
   - **门禁规则**：
     - 任一修改点缺少证据或未满足利旧/最小化原则且无合理说明时，本次设计判定为不通过，必须回到设计阶段修正后再报告完成。

### 4. 完成报告

- 所有阶段及验证完成后，报告分支、IMPL_DESIGN 路径、生成的制品，以及验证结果（score、blocking 数量、validation_status）
- 完成报告中必须附“修改点严格检查汇总”：总修改点数、已支持数量、复用数量、最小变更通过数量、未通过项（如有）
- 如果阶段 4/5 已执行：报告 e2e-impl-design.md 路径
- 如果阶段 4/5 已跳过（未启用 `--e2e`）：报告"E2E测试实现分析已跳过（未启用 --e2e）"
- 完成报告中必须附上下文模式：
  - `context_mode=evidence_first`: 已按 on-demand 边界与证据链执行
  - `context_mode=default`: 未命中 on-demand 或信息不足，已回退原流程（附 `fallback_reason`）

### 5. 记录本skill的运行日志信息

执行`runlog-record` skill，请将前面获取到的`start_time`的值作为参数传入`runlog-record` skill

## 关键规则

- 关卡失败或未解决的澄清事项时报错
