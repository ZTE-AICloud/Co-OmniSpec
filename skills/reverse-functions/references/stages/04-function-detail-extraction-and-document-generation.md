# 功能详细文档生成

<!-- 阶段4：功能详细文档生成 -->

## 职责

基于阶段3的功能划分结果，为每一个功能**按照元模型模板 `.infra/metamodel/5.function-template.md`** 生成功能详细文档文件。  
生成的Markdown文档必须包含完整的YAML Frontmatter（`id`、`name`、`description`、`inputs`、`outputs`）以及模板中规定的所有章节结构和PlantUML流程图，并输出到 `{REPO_ROOT}/omni-doc/specs/functions/` 目录。

## 输出约定（本阶段的“合同”）

- **输出目录**：`{REPO_ROOT}/omni-doc/specs/functions/`
- **单功能文档文件名格式**（必须严格遵守，需与 `.infra/metamodel/5.function-template.md` 保持一致）：
  - `FUNC-XXX-功能名称.md`
  - 示例：`FUNC-001-用户登录.md`
  - 要求：
    - `XXX`：三位数字，从功能清单中的功能序号或功能ID中提取（如 `FUNC-001` → 数字部分 `001`），不足3位左侧补零
    - `功能名称`：来自功能清单中的"功能名称"或"功能业务名称"，推荐使用简短中文短语，例如"用户登录"、"订单创建"
    - 文件名中的数字部分必须与文档Frontmatter中 `id` 字段中的数字部分保持一致（如 `id: FUNC-001` → 文件名 `FUNC-001-用户登录.md`）
    - 只允许使用中文、字母、数字和中划线、下划线，禁止出现空格和特殊符号（必要时将空格替换为中划线）

- **单功能文档内部结构**：**必须完全符合 `.infra/metamodel/5.function-template.md` 中定义的格式**：
  - 顶部为YAML Frontmatter，字段至少包括：
    - `id`: 功能ID，格式为 `FUNC-XXX`
    - `name`: 功能名称，格式为 `[FUNC-XXX-功能名称]`
    - `description`: 功能简要+详细描述
    - `inputs`: 功能输入（列表或简要说明）
    - `outputs`: 功能输出（列表或简要说明）
  - 正文部分章节及顺序必须为：
    1. `## 功能：[FUNC-XXX-功能名称]`
    2. `## 主流程`（内含一个 `plantuml` 活动图代码块，结构与模板保持一致）
    3. `## 异常流程（可选）`（建议生成基础骨架）
    4. `## 关键步骤说明`
    5. `## 输入输出（可选）`
    6. `## 异常场景（可选）`
    7. `## 性能要求（可选）`
    8. `## 约束条件（可选）`

### 单个功能文档结构模板（引用元模型）

- 本阶段在生成文档时，**应将 `.infra/metamodel/5.function-template.md` 视为唯一权威模板**：  
  - 生成内容时，可以直接以该文件为"母版"，用当前功能的信息替换其中的占位符  
  - 如无特殊说明，本阶段文档结构不得自行增删章节标题

> 🔴 **强制要求**：功能文档的Frontmatter字段、章节标题、PlantUML代码块结构必须与 `5.function-template.md` 严格对齐，即使部分内容暂时留空，也要保留完整结构，便于后续人工补全和自动化工具处理。

## 执行流程

### 0. [ ] 创建阶段4的子任务的Todo列表

为确保阶段执行过程的透明化和可追踪性，需要创建阶段4的子任务的Todo列表：

1. **步骤1 清理上一阶段的上下文，保证本阶段的上下文干净**
2. **步骤2 获取仓库根目录和缓存路径**
3. **步骤3 检查缓存状态**
4. **步骤4 读取功能划分结果（功能清单和功能树）**
5. **步骤5 分批执行AI分析所有功能，生成功能详细文档**
6. **步骤6 生成功能清单索引与统计信息**
7. **步骤7 展示结果并向用户确认**
8. **步骤8 处理用户确认，更新缓存状态并结束流程**

### 1. [x] 清理上一阶段的上下文，保证本阶段的上下文干净

- **阶段开始时主动清空上下文**：执行上下文清理，明确说明“开始阶段4：功能详细文档生成。已清空上一阶段的上下文”
- **执行必要的上下文压缩**：判断当前会话的上下文使用率，这个阶段会很耗token，需要先把当前会话的上下文进行压缩，再执行后续流程
- **输出精简化**：只输出关键进度和统计信息，避免冗长解释

### 2. [ ] 获取仓库根目录和缓存路径

- 跨平台脚本调用获取 `REPO_ROOT`：
  - AI Agent直接调用 `check-prerequisites.sh` 脚本
  - AI Agent直接调用 `check-prerequisites.ps1` 脚本
- 定义功能缓存目录：`{REPO_ROOT}/.cache/reverse/functions/`
- 定义输出目录：`{REPO_ROOT}/omni-doc/specs/functions`
- **🔴 强制要求**：AI Agent必须主动创建输出目录（如果不存在）：
  - Linux/macOS：使用 `mkdir -p {REPO_ROOT}/omni-doc/specs/functions` 命令
  - Windows：使用 `New-Item -ItemType Directory -Path {REPO_ROOT}/omni-doc/specs/functions -Force` 命令
  - 或者使用跨平台方式：先检查目录是否存在，不存在则创建
  - **必须在生成任何文档之前确保输出目录存在**

### 3. [ ] 检查缓存状态

- AI Agent直接读取状态文件：`{REPO_ROOT}/.cache/reverse/functions/.cache-status.json`
- 检查 `function_document_generation.confirmed` 字段：
  - 如果 `confirmed == true`：跳过阶段4，使用已有文档结果
  - 如果 `confirmed == false` 或不存在：执行阶段4
- 检查是否已经存在部分功能文档（断点恢复场景）：
  - 扫描 `{REPO_ROOT}/omni-doc/specs/functions` 目录
  - 识别已经生成的 `FUNC-*-*.md` 文件
  - 在功能清单中标记这些功能为"已生成文档"，其余为"待生成文档"

### 4. [ ] 读取功能划分结果（功能清单和功能树）

- 读取功能清单索引文件：`{REPO_ROOT}/.cache/reverse/functions/function-partitioning/function-index.json`
- 根据索引文件按需读取所有批次结果文件，组装完整的功能清单：
  - 每个功能对象至少包含：功能ID、功能简述/业务名称、业务域、分类、关键入口、关联场景ID列表等
- 读取功能树文件：`{REPO_ROOT}/.cache/reverse/functions/function-partitioning/function-tree.json`
- 对功能清单和功能树进行基础校验：
  - 功能ID唯一
  - 功能树中的功能ID能在功能清单中找到

### 5. [ ] 分批执行AI分析所有功能，生成功能详细文档

为确保阶段执行过程的透明化和可追踪性，创建步骤5的子任务的Todo列表：

5.1. [ ] **执行前检查与Token预算评估**  
5.2. [ ] **构建待处理功能列表（跳过已生成文档的功能）**  
5.3. [ ] **调用批次生成脚本自动分批处理（功能数量 > 20时执行）**  
5.4. [ ] **分轮启动多个子Agent并发处理功能批次**  
5.5. [ ] **收集子Agent处理结果并校验文档生成情况**  
5.6. [ ] **更新批次与功能状态，支持断点恢复**  
5.7. [ ] **确认所有功能已处理完成（或记录失败项）**

#### 5.1 执行前检查与Token预算评估

- 明确当前阶段的工作内容、预计功能总数、预计文档数量
- 🔴 **强制Token预算评估**：估算本阶段需要处理的功能总数及每个功能的上下文大小，确保单批次不超过15万 tokens

#### 5.2 构建待处理功能列表

- 从功能清单中选出所有 `尚未生成文档` 的功能：
  - 通过扫描 `{REPO_ROOT}/omni-doc/specs/functions/FUNC-*-*.md` 来判断已存在的功能文档
  - 为每个功能构建待处理条目：
    - `function_id`
    - `short_name`（功能简述，用于文件名与标题）
    - `business_name`（如果有）
    - 关联场景、入口点、模块信息
- 将待处理功能列表写入：`{REPO_ROOT}/.cache/reverse/functions/function-docs/function-doc-list.json`

#### 5.3 批次生成（功能数量 > 20）

- 当待处理功能数量 > 20 时：
  - 调用批次生成脚本按每批 5~10 个功能自动分批：
    - Linux/macOS（示例）：  
      `python3 {REPO_ROOT}/scripts/python/generate_function_doc_batches.py --repo-root {REPO_ROOT} --function-doc-list function-doc-list.json`
  - 生成内容：
    - 批次详情文件：`function-doc-batch-details-{batch_number}.json`
    - 批次状态文件：`function-doc-batch-status.json`
    - 批次索引：`function-doc-batch-index.json`
- 当待处理功能数量 <= 20 时，走单批处理路径（不强制生成批次文件，也可以统一复用同一套批次逻辑）

#### 5.4 分轮并发处理功能批次

- **🔴 重要说明**：如果不存在子Agent，则由主Agent直接处理所有功能批次
- 每轮最多启动 2 个子Agent（例如 `function-detail-writer` 子Agent）并行处理不同批次，或由主Agent直接处理：
  - 输入参数：
    - 功能批次列表文件路径
    - 功能清单、功能树、场景和入口点索引文件路径
    - **输出目录**：`{REPO_ROOT}/omni-doc/specs/functions`（必须使用绝对路径）
  - 处理职责：
    - 对批次中的每个功能：
      - 读取功能及其关联的场景、入口点、模块等上下文信息
      - 先读取模板文件 `specify/metamodel/5.function-template.md` 的完整内容，基于模板原文替换占位符，禁止自行重写章节骨架
      - **生成文档文件**：使用 `write` 工具将文档写入 `{REPO_ROOT}/omni-doc/specs/functions/FUNC-XXX-功能名称.md`，其中 `XXX` 与功能ID中的数字部分保持一致
      - **🔴 强制要求**：生成文档时必须使用完整的绝对路径，确保文件写入到 `{REPO_ROOT}/omni-doc/specs/functions/` 目录下
- 严格按照 `.infra/metamodel/5.function-template.md` 填充Frontmatter字段与各章节内容（包括主流程与异常流程的PlantUML活动图骨架）
- 主Agent职责：
  - 调度批次、更新批次状态、控制并发和Token预算
  - **确保输出目录已创建**（在步骤2中已完成）

#### 5.5 文档生成结果校验

- **🔴 强制要求**：对每个功能，检查文档是否已正确生成到输出目录，且结构符合 `5.function-template.md`：
  - 检查文件路径：`{REPO_ROOT}/omni-doc/specs/functions/FUNC-XXX-功能名称.md`（使用绝对路径）
  - 对应的 `FUNC-XXX-功能名称.md` 文件是否存在
  - 文档顶部是否存在合法的YAML Frontmatter，且至少包含字段：`id`、`name`、`description`、`inputs`、`outputs`
  - `id` 字段格式是否为 `FUNC-XXX`，且 `XXX` 与文件名中的数字部分一致
  - `name` 字段是否包含 `[FUNC-XXX-功能名称]` 形式的内容
  - 正文中是否至少包含以下章节标题，且顺序不乱：
    - `## 功能：[FUNC-XXX-功能名称]`
    - `## 主流程`
    - `## 异常流程（可选）`
    - `## 关键步骤说明`
    - `## 输入输出（可选）`
    - `## 异常场景（可选）`
    - `## 性能要求（可选）`
    - `## 约束条件（可选）`
  - 主流程和异常流程中的PlantUML代码块是否以 ```plantuml 开头并以 `@enduml` 结尾，且基本结构与 `.infra/metamodel/5.function-template.md` 中示例保持一致
- 对缺失或格式错误的文档：
  - 记录到错误列表中，写入 `{REPO_ROOT}/.cache/reverse/functions/function-docs/function-doc-errors.json`
  - **如果文档未在 `{REPO_ROOT}/omni-doc/specs/functions/` 目录下找到，必须记录为错误**

#### 5.6 状态更新与断点恢复

- 在功能清单或单独的状态文件中为每个功能记录文档生成状态：
  - `doc_status`: `"pending" | "processing" | "completed" | "failed"`
  - `doc_path`: 生成的文档相对路径
- 支持断点恢复：
  - 再次进入阶段4时，自动跳过 `doc_status == "completed"` 的功能

### 6. [ ] 生成功能文档清单与统计信息

- 在 `{REPO_ROOT}/omni-doc/specs/functions/` 下生成一个汇总清单，例如：`功能文档清单.md`：
  - 列出所有已生成的功能文档（文件名、功能ID、功能简述）
  - 按业务域、功能分类进行分组统计
- 可选：生成一个 `function-docs-index.json`，方便后续工具或前端消费。

### 7. [ ] 展示结果并向用户确认

- 读取功能文档清单和统计信息：
  - 功能总数 / 已生成文档数 / 失败数
  - 失败功能列表（如果有）
  - 示例文档路径（任选 1~3 个代表性功能）
- 用简要的中文概述本阶段完成情况
- **🔴 交互模式判断**：
  - **全自动模式（默认）**：不询问用户，直接自动确认，继续执行步骤8
  - **交互模式（`--interactive`）**：询问用户："功能详细文档已生成，是否确认结果？[Y/n]"，等待用户响应

### 8. [ ] 处理用户确认，更新缓存状态并结束流程

#### 用户确认（Y/yes/回车或全自动模式）

- **🔴 全自动模式（默认）**：自动执行确认流程，无需等待用户输入
- **🔴 交互模式（`--interactive`）**：用户输入 Y/yes/回车后执行确认流程
- 读取状态文件 `{REPO_ROOT}/.cache/reverse/functions/.cache-status.json`
- 更新 `function_document_generation` 部分：
  - `confirmed: true`
  - `progress: "completed"`
  - `timestamp`: 当前时间戳
- 保存状态文件
- 明确说明"功能详细文档生成阶段已完成"，并清空上下文，结束整个功能反构流程。

#### 用户拒绝（n/no，仅交互模式）

- 仅在交互模式下可能出现
- 允许用户查看错误详情或指定需要重新生成的功能子集
- 支持在保留现有文档的基础上增量重新生成

## 注意事项

- 所有脚本调用必须同时支持 Linux (bash) 和 Windows (PowerShell)
- 文档文件名和内部结构必须严格按照 `.infra/metamodel/5.function-template.md` 执行，这是后续工具和人工评审的**契约**，必须严格遵守
- 当功能数量较多时，必须通过批次+并行子Agent的方式执行，以避免Token超限
- PlantUML 流程图必须遵循 `5.function-template.md` 中的格式要求，可以先生成一个结构化的"骨架"，保证形状正确，再在后续版本中迭代补充更细的业务节点