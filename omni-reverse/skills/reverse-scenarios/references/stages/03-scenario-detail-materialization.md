# 单场景文档生成

<!-- 阶段3：单场景文档生成 -->

## 职责
负责根据已确认的场景清单，为每个场景生成独立的 Markdown 文档。

**单场景详情分析与文档生成**：子 Agent（scenario-detail-generator）按本 Skill 内 [references/implementation/scenario-detail-analysis.md](../implementation/scenario-detail-analysis.md) 执行，输入/输出与步骤以该文档为准。

## 执行流程

### 0. [ ] 创建阶段3的子任务的Todo列表
为确保阶段执行过程的透明化和可追踪性，创建阶段3的子任务的Todo列表：

1. **步骤1 清理上一阶段的上下文，保证本阶段的上下文干净**
2. **步骤2 获取仓库根目录和缓存路径**
3. **步骤3 检查缓存状态，确定是否需要执行分析**
4. **步骤4 读取场景清单**
5. **步骤5 执行AI分析所有场景并直接生成文档（场景详细信息提取与文档生成）**
6. **步骤6 生成场景清单.md（含各场景超链接）**
7. **步骤7 展示结果并向用户确认**
8. **步骤8 处理用户确认，更新缓存状态**

### 1. [x] 清理上一阶段的上下文，保证本阶段的上下文干净
- 🔴 **强制Token检查**：阶段开始前必须检查当前上下文大小，如超过10万tokens则强制清空
- 🔴 **强制要求：必须清空上下文**：执行上下文清理，明确说明"开始阶段3：单场景文档生成。已清空上一阶段的上下文"
- 🔴 **清理验证**：清理后验证上下文已清空，只保留当前阶段必需的状态信息（阶段名称、缓存目录路径、状态文件路径）
- 🔴 **强制要求：批次处理前必须清理上下文**：处理每个批次前执行无用的批次数据上下文清理
- **输出结果精简**：只输出生成进度和统计信息，避免冗余描述

### 2. [ ] 获取仓库根目录和缓存路径
- 跨平台脚本调用获取 REPO_ROOT：
  - AI Agent直接调用check-prerequisites.sh脚本
  - AI Agent直接调用check-prerequisites.ps1脚本
- 定义缓存目录：`{REPO_ROOT}/.cache/reverse/scenarios/`
- 定义输出目录：`{REPO_ROOT}/omni-doc/specs/scenarios`

### 3. [ ] 检查缓存状态，确定是否需要执行分析
- AI Agent直接读取状态文件 `{REPO_ROOT}/.cache/reverse/scenarios/.cache-status.json`
- 检查 `document_generation.confirmed` 字段
- 如果 `confirmed == true` 且输出目录下已存在全部场景文件：跳过阶段3，使用缓存结果
- 如果 `confirmed == false` 或存在缺失文件：执行阶段3
- 检查场景处理状态：如果有场景处理失败或未完成，从上次中断处继续处理

### 4. [ ] 读取场景清单
- 读取场景清单文件 `{REPO_ROOT}/.cache/reverse/scenarios/scenario-list.json`
- 提取 `scenarios` 数组和 `total_count`
- 根据场景总数决定是否需要批次处理：
  - 如果场景总数 <= 5：执行单批处理模式
  - 如果场景总数 > 5：执行分批处理模式（按每批5个场景划分）

### 5. [ ] 执行AI分析所有场景并直接生成文档（场景详细信息提取与文档生成）
为确保阶段执行过程的透明化和可追踪性，创建步骤4的子任务的Todo列表：

4.1. [ ] **4.1 获取已处理场景信息**
4.2. [ ] **4.2 创建场景批次文件**
4.3. [ ] **4.3 获取下一个要执行的场景批次**
4.4. [ ] **4.4 更新批次状态为processing（启动前）**
4.5. [ ] **4.5 同时启动多个子agent处理多批次（后台同时运行）**
4.6. [ ] **4.6 收集子agent结果并更新状态**
4.7. [ ] **4.7 检查是否还有未处理的批次**
4.8. [ ] **4.8 继续处理剩余的场景**

#### 批处理执行流程概览
批处理模式下，主Agent将按照以下流程执行：
1. **创建场景批次**：调用批次生成脚本将场景按每批5个分组
2. **获取待处理批次**：调用获取批次脚本获取下一个待处理的批次（最多3个）
3. **更新批次状态为processing**：在启动子Agent前，将所有批次状态标记为"processing"并记录开始时间
4. **并行处理批次**：启动多个scenario-detail-generator子Agent并行处理不同批次
5. **收集结果并更新状态**：等待所有子Agent完成，收集结果，根据结果批量更新状态为"completed"或"failed"
6. **循环处理**：重复步骤2-5直到所有批次处理完成

#### 🔴 批处理执行流程

**🔴 批处理步骤**：
4.1. **获取已处理场景信息**
   - 🔴 **强制要求**：必须调用进度跟踪脚本获取当前处理进度
   - 🔴 调用进度跟踪脚本获取当前处理进度：
     - Linux/macOS: `${CLAUDE_PLUGIN_ROOT}/skills/reverse-scenarios/scripts/bash/get_scenario_detail_progress.sh {REPO_ROOT}`
     - Windows: `python "${CLAUDE_PLUGIN_ROOT}/skills/reverse-scenarios/scripts/python/get_scenario_detail_progress.py" {REPO_ROOT}`
   - 🔴 分析场景清单文件，确定当前处理状态：
     - 读取 `{REPO_ROOT}/.cache/reverse/scenarios/scenario-list.json`
     - 统计各状态场景数量（pending, processing, completed, failed）
     - 确定是否为断点执行场景（存在processing状态的场景）
   - 🔴 根据场景总数决定是否需要批次处理：
     - 如果场景总数 <= 5：执行单批处理模式
     - 如果场景总数 > 5：执行分批处理模式（按每批5个场景划分）

4.2. **创建场景批次文件**
   - 🔴 **强制要求**：必须首先检查批次映射文件是否已存在，避免重复创建导致状态丢失
   - 🔴 **前置检查**：在创建批次文件之前，必须先检查批次映射文件是否存在：
     - 检查 `{REPO_ROOT}/.cache/reverse/scenarios/scenario-batch-mapping.json` 文件是否存在
     - 如果文件存在且有效（包含批次信息），**跳过创建步骤**，直接进入步骤4.3获取批次
     - 如果文件不存在或无效，才执行批次创建
   - 🔴 **批次文件创建**：仅在批次映射文件不存在或无效时才调用批次生成脚本：
     - Linux/macOS: `${CLAUDE_PLUGIN_ROOT}/skills/reverse-scenarios/scripts/bash/create_scenario_detail_batches.sh --repo-root {REPO_ROOT}`
     - Windows: `python "${CLAUDE_PLUGIN_ROOT}/skills/reverse-scenarios/scripts/python/create_scenario_detail_batches.py" --repo-root {REPO_ROOT}`
     - 脚本会自动检查现有批次文件，如果存在有效的批次文件，会跳过创建并输出提示信息
     - 如需强制重新生成，可以添加 `--force` 参数（Linux/macOS）或 `-Force` 参数（Windows）
   - 🔴 **验证批次文件**：验证批次文件已正确生成或已存在：
     - 检查 `{REPO_ROOT}/.cache/reverse/scenarios/scenario-batch-mapping.json` 文件存在
     - 检查 `{REPO_ROOT}/.cache/reverse/scenarios/scenario_detail-batch-status.json` 文件存在
     - 检查至少一个 `scenario-batch-details-{n}.json` 文件存在
   - 🔴 明确声明："场景批次文件已就绪，总共 {total_batches} 个批次"（无论是新创建还是已存在）

4.3. **获取下一个要执行的场景批次**
   - 🔴 **强制要求**：必须调用获取批次脚本获取待处理批次
   - 🔴 调用获取批次脚本获取待处理批次（最多3个）：
     - Linux/macOS: `${CLAUDE_PLUGIN_ROOT}/skills/reverse-scenarios/scripts/bash/get_next_scenario_detail_batches.sh --repo-root {REPO_ROOT} --batch-count 3`
     - Windows: `python "${CLAUDE_PLUGIN_ROOT}/skills/reverse-scenarios/scripts/python/get_next_scenario_detail_batches.py" --repo-root {REPO_ROOT} --batch-count 3`
   - 🔴 **处理不同场景**：
     - **首次执行场景**：获取状态为"pending"的批次
     - **断点执行场景**：如果存在"processing"状态的批次，优先处理该批次（可能是上次中断的批次）
   - 🔴 **验证批次信息**：
     - 验证批次编号、批次文件路径等关键信息是否存在
     - 验证批次文件是否存在且可访问
     - 如果批次信息不完整，标记为"failed"并记录错误信息

4.4. **更新批次状态为processing（启动前）**
   - 🔴 **批次处理前强制Token检查**：每个批次开始前必须检查当前上下文大小，如超过10万tokens则强制清空
   - 🔴 **强制要求**：主agent负责所有批次状态的统一管理，子agent不参与状态更新
   - 🔴 **批量更新状态**：在批量启动scenario-detail-generator子agent之前，主agent必须调用批量状态更新脚本将所有批次状态标记为"processing"
   - 🔴 调用批量状态更新脚本将批次状态标记为"processing"：
     - Linux/macOS: `${CLAUDE_PLUGIN_ROOT}/skills/reverse-scenarios/scripts/bash/update_scenario_detail_batches_status.sh --repo-root {REPO_ROOT} --batch-updates '{batch_updates_json}'`
     - Windows: `python "${CLAUDE_PLUGIN_ROOT}/skills/reverse-scenarios/scripts/python/update_scenario_detail_batches_status.py" --repo-root {REPO_ROOT} --batch-updates "{batch_updates_json}"`
   - 🔴 **验证要求**：必须验证所有批次状态更新成功，如有更新失败必须报告错误并停止处理
   - 🔴 明确声明："已标记 {batch_count} 个批次为处理中状态"
   - 🔴 记录批次开始处理时间，用于计算处理耗时
   - 🔴 **记录启动的批次列表**：记录本次启动的所有批次编号，用于后续等待验证
   - 🔴 **等待子agent时的上下文清理**：在等待子agent完成期间，主agent必须清理已处理批次的上下文，只保留必要的状态信息（批次号、状态等）

4.4.5. **等待子agent完成（强制轮询检查）**
   - 🔴 **强制要求**：必须通过轮询机制等待所有子Agent完成，禁止仅检查文件存在性
   - 🔴 **轮询检查流程**：
     1. 使用批次状态验证脚本验证批次是否真正完成：
        - Linux/macOS: `${DSDD}/scripts/bash/verify-batches-completion.sh --repo-root {REPO_ROOT} --batch-numbers '{batch_numbers_json}' --stage-type scenarios`
        - Windows: `powershell -ExecutionPolicy Bypass -File {REPO_ROOT}\scripts\powershell\verify-batches-completion.ps1 -RepoRoot {REPO_ROOT} -BatchNumbers "{batch_numbers_json}" -StageType scenarios`
     2. 验证通过条件（必须同时满足）：
        - 批次状态文件中的状态为"completed"
        - 输出文件存在且格式正确（场景详情文档）
        - 批次处理时间戳在合理范围内
     3. 如果验证未通过，等待30秒后再次检查（最多等待30分钟）
     4. 如果30分钟内仍有批次未完成，报告超时错误并标记为"failed"
   - 🔴 **禁止行为**：
     - 禁止仅检查文件存在性就认为子Agent完成
     - 禁止在未验证批次状态的情况下继续执行
     - 禁止模拟或创建虚假的结果文件
     - 禁止跳过等待步骤直接进入结果收集
   - 🔴 **等待完成确认**：所有批次验证通过后，明确声明："所有批次已完成验证，可以继续收集结果"

4.5. **同时启动多个子agent处理多批次（后台运行）**
   - 🔴 **强制要求**：必须并行启动多个scenario-detail-generator子Agent处理不同批次
   - 🔴 **并行启动方式**：
     - 为了提高处理效率，同时启动多个scenario-detail-generator子Agent处理不同的批次
     - 🔴 **强制要求**：必须使用明确的并行启动指令，确保多个子Agent同时启动
     - 示例：请同时启动多个scenario-detail-generator子Agent来分别处理以下批次文件：
       - `scenario-batch-details-1.json`
       - `scenario-batch-details-2.json`
       - `scenario-batch-details-3.json`
   - 🔴 **上下文管理**：
     - 主agent负责协调所有子agent的执行
     - 每个子agent独立处理自己的批次数据
     - 主agent不直接参与批次内的具体场景详情生成工作

4.6. **收集子agent结果并更新状态**
   - 🔴 **等待子agent处理完成**：主agent等待所有并行启动的scenario-detail-generator子agent完成场景详情生成任务
   - 🔴 **批次处理后强制Token检查**：每个批次完成后必须检查当前上下文大小，如超过15万tokens则报错并强制清空
   - 🔴 **收集处理结果**：
     - 收集每个子agent生成的场景详情文档：
       - 文件路径：`{REPO_ROOT}/omni-doc/specs/scenarios/SCN-XXX-场景名称.md`
   - 🔴 **结果收集时的上下文管理**：收集子agent结果时，只读取必要的状态信息，不将完整的批次结果加载到上下文
   - 🔴 **验证处理结果**：
     - 检查生成的场景详情文档是否存在且格式正确
     - 验证场景数据的完整性
     - 统计处理成功的批次数量
     - 如果某个子agent处理失败，记录错误信息
   - 🔴 **根据结果批量更新状态**：根据所有子agent的处理结果，主agent调用批量状态更新脚本更新所有批次状态
     - **处理成功**：如果子agent成功完成任务，将对应批次状态标记为"completed"
     - **处理失败**：如果子agent处理失败，将对应批次状态标记为"failed"
     - 批量状态更新脚本调用：
       - Linux/macOS: `${CLAUDE_PLUGIN_ROOT}/skills/reverse-scenarios/scripts/bash/update_scenario_detail_batches_status.sh --repo-root {REPO_ROOT} --batch-updates '{batch_updates_json}'`
       - Windows: `python "${CLAUDE_PLUGIN_ROOT}/skills/reverse-scenarios/scripts/python/update_scenario_detail_batches_status.py" --repo-root {REPO_ROOT} --batch-updates "{batch_updates_json}"`
     - 批量更新可以显著减少状态更新时间，提高整体处理效率
   - 🔴 **强制要求：批次处理后必须清理上下文**：
     - 清理内容：忘记当前批次的所有处理数据和分析结果
     - 明确声明："已完成 {batch_count} 个批次的处理。已清空当前批次的上下文"
     - 🔴 **清理验证**：清理后验证上下文已清空，只保留必要的状态信息（批次号、总批次数、处理状态）
   - 🔴 **计算批次处理耗时**：
     - 记录批次开始和结束时间，计算处理时长
     - 更新批次处理时间到批次状态文件
   - 🔴 **强制要求**：必须调用进度跟踪脚本获取更新后的处理进度
   - 🔴 向用户报告当前进度："已完成 {completed_batches}/{total_batches} 个批次的处理，进度 {progress_percentage}%，剩余 {pending_batches} 个批次待处理"

4.7. **检查是否还有未处理的批次**
   - 🔴 **强制用户确认机制**：当剩余场景数 > 1时，如果考虑为了节约时间，必须询问用户是否继续处理
   - 🔴 **强制要求**：必须严格按照指导文件要求调用脚本检查是否还有待处理批次
   - 🔴 调用获取批次脚本检查是否还有待处理批次：
       - 使用新的批量获取脚本获取多个待处理批次：
       - Linux/macOS: `${CLAUDE_PLUGIN_ROOT}/skills/reverse-scenarios/scripts/bash/get_next_scenario_detail_batches.sh --repo-root {REPO_ROOT} --batch-count 3`
       - Windows: `python "${CLAUDE_PLUGIN_ROOT}/skills/reverse-scenarios/scripts/python/get_next_scenario_detail_batches.py" --repo-root {REPO_ROOT} --batch-count 3`
   - 🔴 **强制要求**：必须调用进度跟踪脚本获取当前处理进度
   - 🔴 调用进度跟踪脚本获取当前处理进度：
     - Linux/macOS: `${CLAUDE_PLUGIN_ROOT}/skills/reverse-scenarios/scripts/bash/get_scenario_detail_progress.sh {REPO_ROOT}`
     - Windows: `python "${CLAUDE_PLUGIN_ROOT}/skills/reverse-scenarios/scripts/python/get_scenario_detail_progress.py" {REPO_ROOT}`
   - 🔴 **处理要求**：必须严格按照以下规则处理剩余批次
   - 🔴 **处理不同执行场景**：
     - **首次执行场景**：处理所有待处理批次
     - **断点执行场景**：从上次中断处继续处理所有待处理批次

4.8. **继续处理剩余的场景**
   - 🔴 如果还有待处理批次：继续循环处理
     - 🔴 **强制要求：必须清理上一批次无关的上下文信息**，为了保证token不超限，必须清理无用的上下文数据
     - 🔴 **循环前强制Token检查**：继续处理前必须检查当前上下文大小，如超过10万tokens则强制清空
     - 显示剩余批次数和预估处理时间
     - 🔴 向用户报告当前进度："已完成 {completed_batches}/{total_batches} 个批次的处理，进度 {progress_percentage}%，剩余 {pending_batches} 个批次待处理，预计还需要 {estimated_remaining_time}"
     - 🔴 **强制用户确认机制**：当剩余批次数 > 3时，必须询问用户是否继续处理
       - 询问用户："检测到还有 {remaining_batches} 个批次未处理，预计需要 {estimated_time} 完成，是否继续处理？[Y/n]"
       - 如果用户回复 "n" 或 "no"：记录用户选择并暂停处理，等待进一步指令
       - 如果用户回复 "y"、"yes" 或回车：继续批量处理下一批次（最多3个）
       - 如果用户未回复：继续等待用户确认，不得自动继续
   - 🔴 **严禁跳过**：严禁在任何情况下跳过未处理的批次
   - 🔴 **必须实际处理**：必须实际处理每个批次的数据，不能批量创建空批次文件或跳过任何批次
   - 🔴 如果所有批次已完成：跳出循环
     - 更新整体状态为 "completed"
     - 🔴 **强制要求**：必须调用进度跟踪脚本获取最终处理进度
     - 🔴 调用进度跟踪脚本获取最终处理进度：
       - Linux/macOS: `${CLAUDE_PLUGIN_ROOT}/skills/reverse-scenarios/scripts/bash/get_scenario_detail_progress.sh {REPO_ROOT}`
       - Windows: `python "${CLAUDE_PLUGIN_ROOT}/skills/reverse-scenarios/scripts/python/get_scenario_detail_progress.py" {REPO_ROOT}`
     - 🔴 最终进度报告："场景详细信息提取与文档生成已完成！总共处理了 {total_scenarios} 个场景，完成率 100%"

### 6. [ ] 生成场景清单（含超链接）

- **前置条件**：步骤5 中所有目标 `SCN-XXX-*.md` 已写入 `{REPO_ROOT}/omni-doc/specs/scenarios/`（`processing_status == completed` 或输出目录文件数与 `scenario-list.json` 中 `total_scenarios` 一致）。
- **读取模板**：按 `references/data.md` 优先级查找 `reverse-scenario-inventory-template.md`；若均不存在，使用下列最小结构：

```markdown
# 场景清单

**生成时间**: {ISO8601}
**场景总数**: {N}

## 场景列表

| 场景ID | 场景名称 | 业务领域 | 场景类型 | 优先级 | 来源入口 | 场景文件 |
|--------|----------|----------|----------|--------|----------|----------|
| SCN-001 | ... | ... | ... | high | ... | [SCN-001-xxx](./SCN-001-xxx.md) |
```

- **数据来源**：`scenario-list.json` 的 `scenarios` 数组 + Glob 校验 `SCN-*.md` 实际文件名。
- **超链接**（必须）：`[{link_text}](./{filename}.md)`，`link_text` 优先 `scenario_name` 或文档文件名（无扩展名）。
- **写入路径**：`{REPO_ROOT}/omni-doc/specs/scenarios/场景清单.md`
- **禁止**：将 `场景清单.md` 列入表格；链接指向不存在的文件。
- **重录**：`--clear-cache` 时在阶段3 开始前删除已有 `场景清单.md` 与 `SCN-*.md`。

### 7. [ ] 展示结果并向用户确认
- 获取仓库根目录
- 🔴 强制验证输出目录：检查文档是否已生成到 `{REPO_ROOT}/omni-doc/specs/scenarios/`
- 🔴 强制验证缓存状态：AI Agent直接读取状态文件，验证 `document_generation.confirmed == false`
- 读取生成的文档列表
- 总结并展示：
  - 场景总数
  - 生成的文档列表
  - 按类型分组的统计信息
  - 按领域分组的统计信息
  - 代表性场景示例
  - 元数据：提取时间、来源等
- 询问用户："场景详细信息已提取并生成文档完成，是否确认结果？[Y/n]"
- 🔴 状态双重检查：用户响应后AI Agent再次读取状态文件，验证更新成功

### 8. [ ] 处理用户确认，更新缓存状态
#### 用户确认（Y/yes/回车或非交互模式）
- 🔴 **保存前Token检查**：检查当前上下文大小，如超过15万tokens则强制清空后再保存
- 读取状态文件 `{REPO_ROOT}/.cache/reverse/scenarios/.cache-status.json`
- 更新 `document_generation` 部分，设置 `confirmed: true` 和当前时间戳
- 使用 `write` 工具保存更新后的状态文件
- 🔴 **强制要求：必须清空上下文**：明确说明阶段3已完成，清空上下文
- 🔴 **清理验证**：清理后验证上下文已清空，只保留必要的状态信息
- 自动结束整个流程

#### 用户拒绝（n/no）
- 允许查看详情或重新生成

## AI Agent上下文管理要求
- **阶段开始时主动清空上下文**：请先执行上下文清理，然后明确说明"开始阶段3：场景详细信息提取与文档生成。已清空上一阶段的上下文"
- **执行必要的上下文压缩**：判断当前会话的上下文使用率，这个阶段会很耗token，需要先把当前会话的上下文进行压缩，再执行后续流程

## 🔴 场景处理要求
请参考接口详情提取的核心规则文档中的分批处理规则。

### 场景状态字段说明
在场景清单文件 `{REPO_ROOT}/.cache/reverse/scenarios/scenario-list.json` 中，每个场景对象必须使用以下标准化的状态字段：

#### 必须使用的状态字段
1. **processing_status**（必填）：场景处理状态字段，**必须使用此确切字段名**
   - 可选值：`"pending"`, `"processing"`, `"completed"`, `"failed"`
   - 含义：
     - `"pending"`：场景待处理（初始状态）
     - `"processing"`：场景正在处理中
     - `"completed"`：场景处理完成
     - `"failed"`：场景处理失败

2. **processed_at**（可选）：场景处理完成时间戳
   - 格式：ISO 8601标准格式（例如：`"2026-01-12T10:30:00Z"`）
   - 仅在场景状态为`"completed"`或`"failed"`时添加

3. **processing_time**（可选）：场景处理耗时（秒）
   - 类型：数值型
   - 仅在场景处理完成时添加

#### 状态字段更新规范
- **必须使用标准工具**：更新场景状态时必须使用提供的标准脚本工具（待创建）
- **禁止手动更新**：严禁手动编辑场景清单文件来更新状态，必须使用标准工具
- **字段命名强制要求**：**必须使用`processing_status`作为状态字段名，禁止使用其他名称如`status`、`state`等**

#### 示例格式
```json
{
  "scenario_id": "SCN-001",
  "scenario_name": "用户登录场景",
  "business_name": "用户通过用户名密码登录系统",
  "business_domain": "用户管理",
  "scenario_type": "正向主流程",
  "priority": "high",
  "source_files": ["/path/to/auth.py"],
  // ... 其他原有字段 ...
  "processing_status": "pending"
}
```

处理中的场景示例：
```json
{
  "scenario_id": "SCN-001",
  "scenario_name": "用户登录场景",
  "business_name": "用户通过用户名密码登录系统",
  "business_domain": "用户管理",
  "scenario_type": "正向主流程",
  "priority": "high",
  "source_files": ["/path/to/auth.py"],
  // ... 其他原有字段 ...
  "processing_status": "processing",
  "processed_at": "2026-01-12T10:30:00Z"
}
```

处理完成的场景示例：
```json
{
  "scenario_id": "SCN-001",
  "scenario_name": "用户登录场景",
  "business_name": "用户通过用户名密码登录系统",
  "business_domain": "用户管理",
  "scenario_type": "正向主流程",
  "priority": "high",
  "source_files": ["/path/to/auth.py"],
  // ... 其他原有字段 ...
  "processing_status": "completed",
  "processed_at": "2026-01-12T10:30:15Z",
  "processing_time": 15.5
}
```

## 输出
最终文档输出（omni-doc目录）：
- 场景详情文档：每个场景一个文件，`{REPO_ROOT}/omni-doc/specs/scenarios/SCN-XXX-场景名称.md`
- 场景清单：`{REPO_ROOT}/omni-doc/specs/scenarios/场景清单.md`（表中「场景文件」列为指向各 SCN 文档的超链接）
- 场景状态信息：直接更新到 `{REPO_ROOT}/.cache/reverse/scenarios/scenario-list.json` 文件中，包含每个场景的处理状态信息

## 质量检查（阶段3）

- [ ] 已生成 `场景清单.md`，且「场景文件」列每条均为有效的 `./SCN-*.md` 相对超链接
- [ ] 清单行数与已生成的单场景文档数一致（不含 `场景清单.md`）

## 注意事项
- AI Agent必须在阶段3完成后暂停，等待用户确认后才能结束整个流程
- 文档生成是流程的最终输出，必须确认后才算完成
- 用户确认后，AI Agent应该自动结束整个流程
- **场景处理用户确认**：当场景数量较多时，AI Agent必须在处理过程中适时询问用户是否继续，不得擅自跳过未处理的场景
- 跨平台支持：所有脚本调用必须同时支持Linux(bash)和Windows(PowerShell)
- **🔴 子agent使用要求：如果有多个批次要处理，为了提升处理效率，必须同时启动多个scenario-detail-generator子agent同时分别处理不同批次文件**
- **🔴 脚本使用违规严重警告**：
  - 严禁手动修改场景状态文件跳过处理步骤
  - 严禁批量创建空场景文件模拟处理完成
  - 严禁跳过用户确认机制自动处理所有剩余场景
  - 违规行为将导致处理状态不一致，影响断点续执行功能


