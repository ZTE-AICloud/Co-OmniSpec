# 场景清单构建

<!-- 阶段2：场景清单构建 -->

## 职责
负责基于阶段1的场景模式识别和few-shot示例，扫描代码库识别所有业务场景，生成正式的场景清单。

## 执行流程

### 0. [ ] 创建阶段2的子任务的Todo列表
为确保阶段执行过程的透明化和可追踪性，创建阶段2的子任务的Todo列表：

1. **步骤1 清理上一阶段的上下文，保证本阶段的上下文干净**
2. **步骤2 检查缓存状态，确定是否需要执行分析**
3. **步骤3 读取阶段1的输出（场景模式特征和few-shot示例）**
4. **步骤4 扫描代码库识别业务场景**
5. **步骤5 生成场景清单并保存**
6. **步骤6 展示结果并向用户确认**
7. **步骤7 处理用户确认，更新缓存状态**

### 1. [x] 清理上一阶段的上下文，保证本阶段的上下文干净
- 🔴 **强制Token检查**：阶段开始前必须检查当前上下文大小，如超过10万tokens则强制清空
- 🔴 **强制要求：必须清空上下文**：执行上下文清理，明确说明"开始阶段2：场景清单构建。已清空上一阶段的上下文"
- 🔴 **清理验证**：清理后验证上下文已清空，只保留当前阶段必需的状态信息（阶段名称、缓存目录路径、状态文件路径）
- **输出结果精简**：只输出清单摘要和统计信息，避免冗余描述

### 2. [ ] 检查缓存状态，确定是否需要执行分析
- 读取状态文件：`{REPO_ROOT}/.cache/reverse/scenarios/.cache-status.json`
- 检查 `scenario_list.confirmed` 字段
- 如果 `confirmed == true` 且 `scenario-list.json`、`scenario-list.md` 都存在：跳过阶段2，使用缓存结果
- 如果 `confirmed == false` 或不存在：执行阶段2

### 3. [ ] 读取阶段1的输出（场景模式特征和few-shot示例）
- 读取 `{REPO_ROOT}/.cache/reverse/scenarios/scenario-patterns.json`：场景模式特征
- 读取 `{REPO_ROOT}/.cache/reverse/scenarios/few-shot-examples.json`：Few-shot示例集合
- 读取 `{REPO_ROOT}/.cache/reverse/scenarios/scenario-types.json`（如果存在）：用户选择的场景类型
- 读取 `{REPO_ROOT}/.cache/reverse/scenarios/constraints.json`（如果存在）：用户配置的约束规则

### 4. [ ] 执行AI分析所有场景（结合场景模式、用户规则和Few-shot）
为确保阶段执行过程的透明化和可追踪性，创建步骤4的子任务的Todo列表：

4.1. [ ] **执行前检查**
4.2. [ ] **读取上下文依赖文件并评估数据规模**
4.3. [ ] **调用批次生成脚本自动分批处理（文件数量 > 20时执行）**
4.4. [ ] **同时启动多个子agent一起并发分别处理多个批次**
4.5. [ ] **收集子agent处理结果**
4.6. [ ] **主agent统一管理批次状态**
4.7. [ ] **收集子agent结果并更新状态**
4.8. [ ] **检查是否还有未处理的批次【必须执行的步骤】**
4.9. [ ] **如果还有待处理批次：继续循环处理**
4.10. [ ] **单批扫描流程**（文件数量 <= 20时执行）
4.11. [ ] **扫描完成后检查**
4.12. [ ] **扫描完成后调用脚本自动合并生成最终场景文件scenario-list.json**

#### 核心执行流程
AI Agent需要按照以下决策树执行分析：

4.1. **执行前检查**：
   - 🔴 强制验证批次规划已完成（验证批次映射文件scenario_scanning-batch-status.json、batch-mapping.json、状态文件和文件列表是否已生成）
   - 阶段开始时明确告知用户当前阶段、扫描范围、预计工作量
   - 🔴 **强制Token检查**：检查当前上下文大小，如超过10万tokens则强制清空
   - 🔴 **强制Token预算评估**：评估当前任务的Token预算，确保不超过15万tokens的安全限制

4.2. **读取上下文依赖文件并评估数据规模**：
   - 读取场景模式特征文件 `{REPO_ROOT}/.cache/reverse/scenarios/scenario-patterns.json`
   - 读取场景类型列表文件 `{REPO_ROOT}/.cache/reverse/scenarios/scenario-types.json`
   - 读取约束规则文件 `{REPO_ROOT}/.cache/reverse/scenarios/constraints.json`
   - 读取Few-shot示例文件 `{REPO_ROOT}/.cache/reverse/scenarios/few-shot-examples.json`
   - 验证所有上下文文件是否存在且可访问
   - **基于用户约束规则、场景模式特征和Few-shot示例特征智能统计需要扫描的文件总数, 并且将识别出的文件写入一个file_list.json文件中：作为自动分批的输入，格式是数组的形式**
   - **判断处理方式**：
     - 文件数量 > 20？执行分批扫描（跳转到步骤4.3）
     - 文件数量 <= 20？执行单批扫描（跳转到步骤4.10）

4.3. **调用批次生成脚本自动分批处理（文件数量 > 20时执行）**：
   - 🔴 **强制要求**：必须调用批次生成脚本自动分批处理，禁止直接创建示例批次文件
   - 🔴 动态批次规划：
     - 基于用户约束规则和特征筛选获取文件列表
     - 调用批次生成脚本自动分批处理：
       - Linux/macOS: `python3 {REPO_ROOT}/scripts/python/generate_scenario_batches.py --repo-root {REPO_ROOT} --file-list {file_list_json}`
       - Windows: `python {REPO_ROOT}\scripts\python\generate_scenario_batches.py --repo-root {REPO_ROOT} --file-list {file_list_json}`
       - 或使用平台原生脚本：
         - Linux/macOS: `{REPO_ROOT}/scripts/bash/generate-scenario-batches.sh --repo-root {REPO_ROOT} --file-list {file_list_json}`
         - Windows: `{REPO_ROOT}\scripts\powershell\generate-scenario-batches.ps1 -RepoRoot {REPO_ROOT} -FileList {file_list_json}`
     - 生成批次映射和详细文件：
       - 脚本自动创建所有batch-details-*.json文件
       - 每个批次详细文件包含该批次的文件列表、预计Token消耗、复杂度评分等信息
       - 批次映射文件只包含批次的基本信息，避免文件过大
       - 🔴 **强制Token限制**：每个批次的预计Token消耗不得超过15万tokens
     - 初始化批次状态

4.4. **分轮启动多个子agent并发处理多个批次（分轮执行策略）**
   - 🔴 **批次处理前强制Token检查**：每个批次开始前必须检查当前上下文大小，如超过10万tokens则强制清空
   - 🔴 **分轮执行策略（核心机制）**：
     - 根据skill-instruction.md规范，每轮最多启动2个SubAgent，避免上下文超限
     - 采用分轮执行模式：轮次1启动Agent1+Agent2 → 等待完成 → /compact，轮次2启动Agent3+Agent4 → 等待完成 → /compact
     - 每轮处理最多2个批次，确保上下文可控
   - 🔴 **并行处理策略**：
     - 采用批量并行处理方式，每次处理最多2个批次（每轮最多2个SubAgent）
     - 使用新的批量获取脚本获取多个待处理批次：
       - Linux/macOS: `{REPO_ROOT}/scripts/bash/get-next-batches.sh --repo-root {REPO_ROOT} --batch-count 2`
       - Windows: `powershell -ExecutionPolicy Bypass -File {REPO_ROOT}\scripts\powershell\get-next-batches.ps1 -RepoRoot {REPO_ROOT} -BatchCount 2`
   - 🔴 **并行启动方式**：
     - 为了提高处理效率，同时启动多个scenario-recognizer子Agent处理不同的批次，一个子agent负责一个批次，多个子agent同时处理。
     - 🔴 **强制要求**：必须使用明确的并行启动指令，确保多个子Agent同时启动
     - 🔴 **并发数限制**：每轮最多同时启动2个子Agent，避免上下文超限
     - 示例：请同时启动2个子Agent scenario-recognizer来分别处理batch-details-1.json和batch-details-2.json批次的场景文件
   - 🔴 **上下文管理**：
     - 主agent负责协调所有子agent的执行
     - 每个子agent独立处理自己的批次数据
     - 主agent不直接参与批次内的具体场景识别工作
     - 🔴 **分轮执行流程**：
       - 轮次1：启动Agent1处理batch-details-1.json + Agent2处理batch-details-2.json → 等待完成 → /compact
       - 轮次2：启动Agent3处理batch-details-3.json + Agent4处理batch-details-4.json → 等待完成 → /compact
       - 依此类推，直到所有批次处理完成
     - 🔴 **等待子agent时的上下文清理**：在等待子agent完成期间，主agent必须清理已处理批次的上下文，只保留必要的状态信息（批次号、状态等）

4.5. **收集子agent处理结果**
   - 🔴 **结果收集机制**：
     - 等待当前轮次所有并行启动的子agent完成处理
     - 收集每个子agent生成的批次场景清单文件：
       - 文件路径：`{REPO_ROOT}/.cache/reverse/scenarios/scenario-list-batch-{batch_number}.json`
     - 验证当前轮次所有子agent是否成功完成处理
     - 如果某个子agent处理失败，记录错误信息并决定是否重试
   - 🔴 **批量状态更新**：
     - 使用新的批量状态更新脚本同时更新所有已完成批次的状态：
       - Linux/macOS: `{REPO_ROOT}/scripts/bash/update-batches-status.sh --repo-root {REPO_ROOT} --batch-updates '{batch_updates_json}'`
       - Windows: `powershell -ExecutionPolicy Bypass -File {REPO_ROOT}\scripts\powershell\update-batches-status.ps1 -RepoRoot {REPO_ROOT} -BatchUpdates "{batch_updates_json}"`
     - 批量更新可以显著减少状态更新时间，提高整体处理效率
   - 🔴 **结果验证**：
     - 检查生成的批次场景清单文件是否存在且格式正确
     - 验证场景数据的完整性
     - 统计处理成功的批次数量
   - 🔴 **强制/compact机制**：
     - 当前轮次所有子agent完成后，必须执行/compact指令压缩上下文
     - 明确声明："当前轮次已完成，执行/compact压缩上下文"
     - 这是防止上下文超限的关键步骤，不能跳过

4.6. **主agent统一管理批次状态**
   - 🔴 **强制要求**：主agent负责所有批次状态的统一管理，子agent不参与状态更新
   - 🔴 **批量启动子agent前更新状态**：在批量启动scenario-recognizer子agent之前，主agent必须调用批量状态更新脚本将所有批次状态标记为"processing"
   - 🔴 调用批量状态更新脚本将批次状态标记为"processing"：
     - Linux/macOS: `{REPO_ROOT}/scripts/bash/update-batches-status.sh --repo-root {REPO_ROOT} --batch-updates '{batch_updates_json}'`
     - Windows: `powershell -ExecutionPolicy Bypass -File {REPO_ROOT}\scripts\powershell\update-batches-status.ps1 -RepoRoot {REPO_ROOT} -BatchUpdates "{batch_updates_json}"`
   - 🔴 **验证要求**：必须验证所有批次状态更新成功，如有更新失败必须报告错误并停止处理
   - 🔴 明确声明："已标记 {batch_count} 个批次为处理中状态"
   - 🔴 记录批次开始处理时间，用于计算处理耗时
   - 🔴 **记录启动的批次列表**：记录本次启动的所有批次编号，用于后续等待验证

4.6.5. **等待子agent完成（强制轮询检查）**
   - 🔴 **强制要求**：必须通过轮询机制等待所有子Agent完成，禁止仅检查文件存在性
   - 🔴 **轮询检查流程**：
     1. 使用批次状态验证脚本验证批次是否真正完成：
        - Linux/macOS: `{REPO_ROOT}/scripts/bash/verify-batches-completion.sh --repo-root {REPO_ROOT} --batch-numbers '{batch_numbers_json}' --stage-type scenarios`
        - Windows: `powershell -ExecutionPolicy Bypass -File {REPO_ROOT}\scripts\powershell\verify-batches-completion.ps1 -RepoRoot {REPO_ROOT} -BatchNumbers "{batch_numbers_json}" -StageType scenarios`
     2. 验证通过条件（必须同时满足）：
        - 批次状态文件中的状态为"completed"
        - 输出文件存在且格式正确（scenario-list-batch-{batch_number}.json）
        - 批次处理时间戳在合理范围内
     3. 如果验证未通过，等待30秒后再次检查（最多等待30分钟）
     4. 如果30分钟内仍有批次未完成，报告超时错误并标记为"failed"
   - 🔴 **禁止行为**：
     - 禁止仅检查文件存在性就认为子Agent完成
     - 禁止在未验证批次状态的情况下继续执行
     - 禁止模拟或创建虚假的结果文件
     - 禁止跳过等待步骤直接进入结果收集
   - 🔴 **等待完成确认**：所有批次验证通过后，明确声明："所有批次已完成验证，可以继续收集结果"

4.7. **收集子agent结果并更新状态**
   - 🔴 **等待子agent处理完成**：主agent等待当前轮次所有并行启动的scenario-recognizer子agent完成场景识别任务
   - 🔴 **批次处理后强制Token检查**：每个批次完成后必须检查当前上下文大小，如超过15万tokens则报错并强制清空
   - 🔴 **收集处理结果**：检查当前轮次所有子agent生成的批次场景清单文件是否存在且格式正确
   - 🔴 **结果收集时的上下文管理**：收集子agent结果时，只读取必要的状态信息，不将完整的批次结果加载到上下文
   - 🔴 **根据结果批量更新状态**：根据当前轮次所有子agent的处理结果，主agent调用批量状态更新脚本更新所有批次状态
   - 🔴 **处理成功**：如果子agent成功完成任务，将对应批次状态标记为"completed"
   - 🔴 **处理失败**：如果子agent处理失败，将对应批次状态标记为"failed"
   - 🔴 批量状态更新脚本调用：
     - Linux/macOS: `{REPO_ROOT}/scripts/bash/update-batches-status.sh --repo-root {REPO_ROOT} --batch-updates '{batch_updates_json}'`
     - Windows: `powershell -ExecutionPolicy Bypass -File {REPO_ROOT}\scripts\powershell\update-batches-status.ps1 -RepoRoot {REPO_ROOT} -BatchUpdates "{batch_updates_json}"`
   - 🔴 **强制要求：批次处理后必须清理上下文**
   - 🔴 清理内容：忘记当前轮次批次的所有处理数据和分析结果
   - 🔴 明确声明："已完成当前轮次 {batch_count} 个批次的处理。已清空当前轮次的上下文"
   - 🔴 **清理验证**：清理后验证上下文已清空，只保留必要的状态信息（批次号、总批次数、处理状态）
   - 🔴 **强制/compact机制**：
     - 当前轮次所有批次处理完成后，必须执行/compact指令压缩上下文
     - 明确声明："当前轮次已完成，执行/compact压缩上下文，释放上下文空间"
     - 这是防止上下文超限的关键步骤，每轮完成后必须执行
   - 🔴 **计算批次处理耗时**：记录批次开始和结束时间，计算处理时长
   - 🔴 **更新批次处理时间**：将处理耗时信息更新到批次状态文件
   - 🔴 **强制要求**：必须调用进度跟踪脚本获取更新后的处理进度
   - 🔴 向用户报告当前进度："已完成 {completed_batches}/{total_batches} 个批次的处理，进度 {progress_percentage}%，剩余 {pending_batches} 个批次待处理"

4.8. **检查是否还有未处理的批次【必须执行的步骤】**
   - 🔴 **强制用户确认机制**：当剩余场景数 > 1时，如果考虑为了节约时间，必须询问用户是否继续处理
   - 🔴 **强制要求**：必须严格按照指导文件要求调用脚本检查是否还有待处理批次
   - 🔴 调用获取批次脚本检查是否还有待处理批次：
       - 使用新的批量获取脚本获取多个待处理批次：
       - Linux/macOS: `{REPO_ROOT}/scripts/bash/get-next-batches.sh --repo-root {REPO_ROOT} --batch-count 5`
       - Windows: `powershell -ExecutionPolicy Bypass -File {REPO_ROOT}\scripts\powershell\get-next-batches.ps1 -RepoRoot {REPO_ROOT} -BatchCount 5`
   - 🔴 **强制要求**：必须调用进度跟踪脚本获取当前处理进度
   - 🔴 调用进度跟踪脚本获取当前处理进度：
     - Linux/macOS: `{REPO_ROOT}/scripts/bash/get-next-batch.sh --repo-root {REPO_ROOT} --action get-summary`
     - Windows: `powershell -ExecutionPolicy Bypass -File {REPO_ROOT}\scripts\powershell\get-next-batch.ps1 -RepoRoot {REPO_ROOT} -Action get-summary`
   - 🔴 **处理要求**：必须严格按照以下规则处理剩余批次
   - 🔴 **处理不同执行场景**：
     - **首次执行场景**：处理所有待处理批次
     - **断点执行场景**：从上次中断处继续处理所有待处理批次

4.9. **如果还有待处理批次：继续循环处理**：
   - 🔴 如果还有待处理批次：继续循环处理
     - 🔴 **强制要求：必须清理上一批次无关的上下文信息**，为了保证token不超限，必须清理无用的上下文数据
     - 🔴 **循环前强制Token检查**：继续处理前必须检查当前上下文大小，如超过10万tokens则强制清空
     - 显示剩余批次数和预估处理时间
     - 🔴 向用户报告当前进度："已完成 {completed_batches}/{total_batches} 个批次的处理，进度 {progress_percentage}%，剩余 {pending_batches} 个批次待处理，预计还需要 {estimated_remaining_time}"
     - 🔴 **强制用户确认机制**：当剩余批次数 > 5时，必须询问用户是否继续处理
       - 询问用户："检测到还有 {remaining_batches} 个批次未处理，预计需要 {estimated_time} 完成，是否继续处理？[Y/n]"
       - 如果用户回复 "n" 或 "no"：记录用户选择并暂停处理，等待进一步指令
       - 如果用户回复 "y"、"yes" 或回车：继续批量处理下一批次（最多5个）
       - 如果用户未回复：继续等待用户确认，不得自动继续
   - 🔴 **严禁跳过**：严禁在任何情况下跳过未处理的批次
   - 🔴 **必须实际处理**：必须实际处理每个批次的数据，不能批量创建空批次文件或跳过任何批次
   - 🔴 如果所有批次已完成：跳出循环
     - 更新整体状态为 "completed"
     - 🔴 **强制要求**：必须调用进度跟踪脚本获取最终处理进度
     - 🔴 调用进度跟踪脚本获取最终处理进度：
       - Linux/macOS: `{REPO_ROOT}/scripts/bash/get-next-batch.sh --repo-root {REPO_ROOT} --action get-summary`
       - Windows: `powershell -ExecutionPolicy Bypass -File {REPO_ROOT}\scripts\powershell\get-next-batch.ps1 -RepoRoot {REPO_ROOT} -Action get-summary`
     - 🔴 最终进度报告："场景清单扫描已完成！总共处理了 {total_batches} 个批次，完成率 100%"

4.10. **单批扫描流程**（文件数量 <= 20时执行）：
   - 🔴 **初始Token检查**：开始处理前检查当前上下文大小，如超过10万tokens则强制清空
   - 🔴 **创建虚拟批次**：对于少量文件，创建一个包含所有文件的虚拟批次，以便复用子agent处理流程
   - 🔴 **主agent更新状态**：在启动子agent前，主agent调用状态更新脚本将虚拟批次状态标记为"processing"
   - 🔴 **启动子agent处理**：使用Task工具启动scenario-recognizer子agent来处理这个虚拟批次
   - 🔴 **收集处理结果**：等待子agent完成处理并收集生成的场景清单文件
   - 🔴 **主agent更新最终状态**：根据子agent处理结果，主agent调用状态更新脚本将批次状态标记为"completed"或"failed"
   - 🔴 **结果验证**：验证子agent处理结果的完整性和正确性
   - 🔴 **Token优化处理**：文件大小检查和分批读取，对超大文件实施严格的内容截断策略
   - 🔴 **处理中Token监控**：处理过程中定期检查上下文大小，如超过15万tokens则报错并停止处理
   - 🔴 **结束Token检查**：完成处理后检查上下文大小，如超过15万tokens则报错
   - ⚪ **注意**：对于少量文件（<=20），仍采用串行处理方式以简化流程

### 子Agent场景识别机制（业务实现文档）

scenario-recognizer 子 Agent 按本 Skill 内业务实现文档执行单文件场景识别：

#### 业务实现文档

- **文档路径**：本 Skill 内 [references/implementation/scenario-recognition.md](../implementation/scenario-recognition.md)
- **职责**：识别单个文件中的场景，将结果写入临时 JSON 文件并返回极简状态（输入/输出与步骤以该文档为准）。
- **SubAgent 职责**：文件读写、批次管理、结果汇总、状态更新
  - 遍历批次文件，对每个文件按上述业务实现文档执行
  - 收集所有输出文件中的场景
  - 生成批次场景清单文件
  - 更新批次状态

4.11. **扫描完成后检查**：
   - 获取仓库根目录路径
   - 确认所有由子agent生成的批次场景清单文件都已保存在缓存目录中
   - 验证批次映射文件 `{REPO_ROOT}/.cache/reverse/scenarios/batch-mapping.json` 的完整性
   - 确认所有子agent均已完成处理且生成了对应的场景清单文件

4.12. **扫描完成后调用脚本自动合并生成最终场景文件scenario-list.json**：
   - 调用自动合并脚本处理所有批次文件：
     - Linux/macOS: `python3 {REPO_ROOT}/scripts/python/merge_scenario_results.py {REPO_ROOT}`
     - Windows: `python {REPO_ROOT}\scripts\python\merge_scenario_results.py {REPO_ROOT}`
   - 脚本将自动按顺序读取所有由子agent生成的批次场景清单文件并合并
   - 使用流式处理避免一次性加载所有批次数据导致内存和Token消耗过大
   - 自动处理重复场景（基于场景名称和源文件去重）
   - 自动生成统计数据（按业务领域、场景类型、优先级等分类统计）
   - 脚本自动生成最终的场景清单文件 `scenario-list.json`
   - 严格按照"场景清单JSON模板定义"生成最终JSON结构
   - 自动添加元数据信息（生成时间、总计数等）
   - 确保所有子agent的处理结果都被正确包含在最终清单中

### 5. [ ] 保存批次结果或最终结果到缓存文件

#### 关键验证步骤
- 如果进行了分批处理，必须首先验证所有子agent均已成功完成处理
- 🔴 AI Agent直接读取批次状态文件，计算未处理批次数
- 如果未处理批次数 > 0：绝对禁止创建最终文件
- 如果未处理批次数 == 0：验证通过，可以继续执行
- 🔴 **保存前Token检查**：检查当前上下文大小，如超过15万tokens则强制清空后再保存

#### 保存过程
- 区分分批处理和单批处理
- 分批处理：每个子agent生成对应批次的场景清单文件，所有子agent完成后通过合并步骤生成最终文件
- 单批处理：创建虚拟批次并由子agent处理，然后生成最终的场景清单文件
- **🔴 严格按照"场景清单JSON模板定义"生成JSON文件结构**
- 🔴 **保存前上下文清理**：保存文件前清空不必要的上下文信息，减少Token消耗
- 使用 `write` 工具直接保存JSON文件到 `{REPO_ROOT}/.cache/reverse/scenarios/scenario-list.json`
- 路径使用完整的绝对路径
- 实施文件写入错误处理机制
- 读取状态文件 `{REPO_ROOT}/.cache/reverse/scenarios/.cache-status.json`
- 更新 `scenario_list` 部分，设置 `confirmed: false` 和当前时间戳
- 使用 `write` 工具保存更新后的状态文件
- **Token优化处理**：生成场景清单时，应按需序列化场景信息，避免一次性加载所有场景数据，使用流式JSON生成技术，减少内存占用和Token消耗
- 🔴 **保存后上下文清理**：文件保存完成后立即清空相关上下文信息

### 6. [ ] 展示结果并向用户确认
- 🔴 强制验证缓存状态：AI Agent直接读取状态文件，验证 `scenario_list.confirmed == false`
- 读取场景清单文件并总结展示：总场景数、按领域/类型的统计摘要、代表性场景条目等
- 询问用户："场景清单已生成，是否确认结果正确？[Y/n]"
- 🔴 状态双重检查：用户响应后AI Agent再次读取状态文件，验证更新成功

### 7. [ ] 处理用户确认，更新缓存状态
#### 用户确认（Y/yes/回车或非交互模式）
- 🔴 **保存前Token检查**：检查当前上下文大小，如超过15万tokens则强制清空后再保存
- 更新状态文件中的 `scenario_list` 部分，设置 `confirmed: true` 和当前时间戳
- 🔴 **强制要求：必须清空上下文**：明确说明阶段2已完成，清空上下文
- 🔴 **清理验证**：清理后验证上下文已清空，只保留必要的状态信息

#### 用户拒绝（n/no）
- 允许查看详情、在本阶段实现简单的编辑机制（删除/合并/改名/改优先级）或回到阶段1重新调整

## 🔴 批次处理要求
请参考接口清单扫描的核心规则文档中的分批处理规则。

## 输出
1. 场景清单（JSON格式），保存到缓存目录 `{REPO_ROOT}/.cache/reverse/scenarios/scenario-list.json`，包含所有识别出的业务场景定义。
2. 批次场景清单文件（JSON格式），保存到缓存目录 `{REPO_ROOT}/.cache/reverse/scenarios/scenario-list-batch-{batch_number}.json`，由scenario-recognizer子agent生成，包含每个批次识别出的场景定义。
3. 批次映射文件（JSON格式），保存到缓存目录 `{REPO_ROOT}/.cache/reverse/scenarios/batch-mapping.json`，由主agent维护，包含批次基本信息和状态。
4. 批次详细文件（JSON格式），保存到缓存目录 `{REPO_ROOT}/.cache/reverse/scenarios/batch-details-{batch_number}.json`，包含每个批次的详细文件列表和处理信息。
5. 批次状态文件（JSON格式），保存到缓存目录 `{REPO_ROOT}/.cache/reverse/scenarios/scenario_scanning-batch-status.json`，由主agent维护，包含批次处理统计信息。

## 场景清单JSON模板定义
为了指导AI Agent正确生成场景清单，以下是场景清单JSON文件的标准结构定义：

### 主场景清单文件结构
```json
{
  "version": "1.0",
  "generated_at": "2026-01-12T10:30:00Z",
  "scan_scope": "/path/to/project",
  "total_scenarios": 45,
  "metadata": {
    "total_scenarios": 45,
    "scan_time": "2026-01-12T10:30:00Z",
    "source": "scenario_scanning_stage",
    "confidence_threshold": 0.8
  },
  "scenarios": [
    {
      "scenario_id": "SCN-001",
      "scenario_name": "用户登录场景",
      "business_name": "用户通过用户名密码登录系统",
      "business_domain": "用户管理",
      "scenario_type": "正向主流程",
      "priority": "high",
      "source_files": ["/path/to/auth.py", "/path/to/user_service.py"],
      "entry_points": ["login", "authenticate"],
      "description": "用户输入用户名和密码，系统验证后允许用户登录",
      "confidence": 0.95,
      "tags": ["authentication", "login"],
      "related_interfaces": ["API-001", "API-002"]
    }
  ],
  "summary": {
    "by_domain": {
      "用户管理": 15,
      "订单处理": 12,
      "支付处理": 8,
      "消息通知": 5,
      "系统管理": 5
    },
    "by_type": {
      "正向主流程": 20,
      "异常场景": 10,
      "边界场景": 8,
      "批处理场景": 4,
      "集成场景": 3
    },
    "by_priority": {
      "high": 25,
      "medium": 15,
      "low": 5
    }
  }
}
```

### 批次映射文件结构
```json
{
  "total_batches": 5,
  "batch_size": 10,
  "batches": [
    {
      "batch_number": 1,
      "batch_file": "batch-details-1.json",
      "status": "pending"
    },
    {
      "batch_number": 2,
      "batch_file": "batch-details-2.json",
      "status": "pending"
    }
  ]
}
```

### 批次详细文件结构
```json
{
  "batch_number": 1,
  "files": [
    "/path/to/file1.py",
    "/path/to/file2.py",
    "/path/to/file3.py"
  ],
  "estimated_tokens": 12000,
  "complexity_score": 7.5,
  "status": "pending"
}
```

### 批次状态文件结构
```json
{
  "version": "1.1",
  "stage": "scenario_scanning",
  "total_items": 45,
  "batch_size": 10,
  "total_batches": 5,
  "processed_batches": 0,
  "current_batch": 0,
  "failed_batches": 0,
  "start_time": "2026-01-11T10:30:00Z",
  "last_update": "2026-01-11T10:30:00Z",
  "status": "initialized",
  "batch_mappings": [
    {
      "batch_number": 1,
      "batch_file": "batch-details-1.json",
      "status": "pending",
      "estimated_tokens": 12000
    }
  ]
}
```

## 🔴 关键注意事项
- **🔴 强制要求**：AI Agent 必须在阶段 2 完成后暂停，等待用户确认后才能继续阶段 3（无论缓存是否存在，只要 `scenario_list.confirmed == false`，就必须展示结果并等待用户确认）
- 场景清单已包含类型分类信息（`scenario_type` 字段），是详细信息提取的输入，必须确认后才能使用
- **用户确认后，AI Agent 应该自动继续执行阶段 3（单场景文档生成），不需要等待额外的用户指令**
- **🔴 用户确认步骤是强制步骤，不能跳过，不能省略**
- **🔴 场景清单生成必须严格按照"场景清单JSON模板定义"中的结构生成，确保与阶段3的输入要求一致**
- **🔴 子agent使用要求：如果有多个批次要处理，为了提升处理效率，必须同时启动多个scenario-recognizer子agent同时分别处理不同批次文件**
- **🔴 状态管理要求**：主agent负责所有批次状态的统一管理，包括状态更新、统计信息维护等
- 扫描优先级：场景模式特征（关键模式） > 用户配置的规则 > Few-shot示例
- 必须读取场景模式特征：优先识别关键场景模式，提高扫描效率和准确性
- 跨平台支持：所有脚本调用必须同时支持Linux(bash)和Windows(PowerShell)
- **🔴 脚本使用违规严重警告**：
  - 严禁手动修改场景状态文件跳过处理步骤
  - 严禁批量创建空场景文件模拟处理完成
  - 严禁跳过用户确认机制自动处理所有剩余场景
  - 违规行为将导致处理状态不一致，影响断点续执行功能


