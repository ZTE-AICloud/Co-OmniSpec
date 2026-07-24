# 阶段3：功能划分

<!-- 阶段3：功能划分 -->

## 职责
基于阶段2的场景识别结果，将相关的场景聚合为功能，建立功能的层次结构，生成功能清单和功能树。

## 执行流程

### 0. [ ] 创建阶段3的子任务的Todo列表
为确保阶段执行过程的透明化和可追踪性，创建阶段3的子任务的Todo列表：

1. **步骤1 清理上一阶段的上下文，保证本阶段的上下文干净**
2. **步骤2 检查缓存状态，确定是否需要执行分析**
3. **步骤3 读取阶段2的输出（场景识别结果）**
4. **步骤4 执行AI分析功能划分（场景聚合为功能）**
5. **步骤5 构建功能树结构**
6. **步骤6 展示结果并向用户确认**
7. **步骤7 处理用户确认，更新缓存状态**

### 1. [x] 清理上一阶段的上下文，保证本阶段的上下文干净
- 🔴 **强制Token检查**：阶段开始前必须检查当前上下文大小，如超过10万tokens则强制清空
- 🔴 **强制要求：必须清空上下文**：执行上下文清理，明确说明"开始阶段3：功能划分。已清空上一阶段的上下文"
- 🔴 **清理验证**：清理后验证上下文已清空，只保留当前阶段必需的状态信息（阶段名称、缓存目录路径、状态文件路径）
- **输出结果精简**：只输出清单摘要和统计信息，避免冗余描述

### 2. [ ] 检查缓存状态，确定是否需要执行分析
- 读取状态文件：`{REPO_ROOT}/.cache/reverse/functions/.cache-status.json`
- 检查 `function_partitioning.confirmed` 字段
- 如果 `confirmed == true`：跳过阶段3，使用缓存结果
- 如果 `confirmed == false` 或不存在：执行阶段3

### 3. [ ] 读取阶段2的输出（场景识别结果）
- 读取场景识别索引文件：`{REPO_ROOT}/.cache/reverse/functions/scenario-identification/scenario-index.json`
- 根据索引文件按需读取批次结果文件，获取所有场景信息
- 验证场景识别结果文件是否存在且格式正确

### 4. [ ] 执行AI分析功能划分（场景聚合为功能）
为确保阶段执行过程的透明化和可追踪性，创建步骤4的子任务的Todo列表：

4.1. [ ] **执行前检查**
4.2. [ ] **读取上下文依赖文件并评估数据规模**
4.3. [ ] **调用批次生成脚本自动分批处理（场景数量 > 20时执行）**
4.4. [ ] **同时启动多个子agent一起并发分别处理多个批次**
4.5. [ ] **收集子agent处理结果**
4.6. [ ] **主agent统一管理批次状态**
4.7. [ ] **收集子agent结果并更新状态**
4.8. [ ] **检查是否还有未处理的批次【必须执行的步骤】**
4.9. [ ] **如果还有待处理批次：继续循环处理**
4.10. [ ] **单批处理流程**（场景数量 <= 20时执行）
4.11. [ ] **处理完成后检查**
4.12. [ ] **处理完成后生成最终功能清单文件function-list.json（批次+索引）**

#### 核心执行流程
AI Agent需要按照以下决策树执行分析：

4.1. **执行前检查**：
   - 🔴 强制验证批次规划已完成（验证批次映射文件、状态文件和文件列表是否已生成）
   - 阶段开始时明确告知用户当前阶段、处理范围、预计工作量
   - 🔴 **强制Token检查**：检查当前上下文大小，如超过10万tokens则强制清空
   - 🔴 **强制Token预算评估**：评估当前任务的Token预算，确保不超过15万tokens的安全限制

4.2. **读取上下文依赖文件并评估数据规模**：
   - 读取场景识别索引文件：`{REPO_ROOT}/.cache/reverse/functions/scenario-identification/scenario-index.json`
   - 根据索引文件按需读取批次结果，获取所有场景信息
   - 读取入口点识别索引文件（如果需要）：`{REPO_ROOT}/.cache/reverse/functions/entry-identification/entry-index.json`
   - **基于场景信息智能统计需要处理的场景总数，并且将识别出的场景写入一个scenario_list.json文件中：作为自动分批的输入，格式是数组的形式**
   - **判断处理方式**：
     - 场景数量 > 20？执行分批处理（跳转到步骤4.3）
     - 场景数量 <= 20？执行单批处理（跳转到步骤4.10）

4.3. **调用批次生成脚本自动分批处理（场景数量 > 20时执行）**：
   - 🔴 **强制要求**：必须调用批次生成脚本自动分批处理，禁止直接创建示例批次文件
   - 🔴 动态批次规划：
     - 基于场景信息获取场景列表
     - 调用批次生成脚本自动分批处理：
       - Linux/macOS: `python3 ${CLAUDE_PLUGIN_ROOT}/skills/reverse-functions/scripts/python/generate_function_batches.py" --repo-root {REPO_ROOT} --scenario-list {scenario_list_json}`
       - Windows: `python "${CLAUDE_PLUGIN_ROOT}/skills/reverse-functions/scripts/python/generate_function_batches.py" --repo-root {REPO_ROOT} --scenario-list {scenario_list_json}`
     - 生成批次映射和详细文件：
       - 脚本自动创建所有batch-details-*.json文件
       - 每个批次详细文件包含该批次的场景列表、预计Token消耗、复杂度评分等信息
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
     - 使用批量获取脚本获取多个待处理批次：
       - Linux/macOS: `${DSDD}/scripts/bash/get-next-batches.sh --repo-root {REPO_ROOT} --batch-count 2 --stage-type functions --stage-name function_partitioning`
       - Windows: `powershell -ExecutionPolicy Bypass -File {REPO_ROOT}\scripts\powershell\get-next-batches.ps1 -RepoRoot {REPO_ROOT} -BatchCount 2 -StageType functions -StageName function_partitioning`
   - 🔴 **并行启动方式**：
     - 为了提高处理效率，同时启动多个function-partitioner子Agent处理不同的批次，一个子agent负责一个批次，多个子agent同时处理。
     - 🔴 **强制要求**：必须使用明确的并行启动指令，确保多个子Agent同时启动
     - 示例：请同时启动2个function-partitioner子Agent来分别处理以下批次文件：
       - `function-batch-details-1.json`
       - `function-batch-details-2.json`
   - 🔴 **上下文管理**：
     - 主agent负责协调所有子agent的执行
     - 每轮处理完成后，主agent清理上下文，准备下一轮处理

4.5. **收集子agent处理结果**：
   - 等待所有子Agent完成处理
   - 验证批次结果文件是否存在：
     - `{REPO_ROOT}/.cache/reverse/functions/function-partitioning/function-batch-{batch_number}.json`
   - 验证批次结果文件格式正确性

4.6. **主agent统一管理批次状态**：
   - 读取批次状态文件：`{REPO_ROOT}/.cache/reverse/functions/function-partitioning/function-batch-status.json`
   - 更新批次状态为"completed"或"failed"
   - 记录处理时间和结果统计

4.7. **收集子agent结果并更新状态**：
   - 收集所有批次的处理结果
   - 更新批次状态文件
   - 统计处理进度

4.8. **检查是否还有未处理的批次【必须执行的步骤】**：
   - 🔴 **强制要求**：必须检查是否还有未处理的批次
   - 读取批次状态文件，检查是否有状态为"pending"的批次
   - 如果有，继续执行步骤4.9

4.9. **如果还有待处理批次：继续循环处理**：
   - 重复执行步骤4.4-4.8，直到所有批次处理完成

4.10. **单批处理流程**（场景数量 <= 20时执行）：
   - 直接调用function-partitioner子Agent处理所有场景
   - 生成单批结果文件

4.11. **处理完成后检查**：
   - 验证所有批次都已处理完成
   - 验证结果文件完整性
   - 进行功能去重和合并检查

4.12. **处理完成后生成最终功能清单文件function-list.json（批次+索引）**：
   - 生成索引文件：`{REPO_ROOT}/.cache/reverse/functions/function-partitioning/function-index.json`
   - 索引文件包含所有批次结果的位置和统计信息
   - 不合并批次结果文件，使用索引文件定位批次结果

### 5. [ ] 构建功能树结构
- 读取功能清单索引文件：`{REPO_ROOT}/.cache/reverse/functions/function-partitioning/function-index.json`
- 根据索引文件按需读取所有批次结果，获取所有功能信息
- 分析功能的层次关系：
  - 按业务域分类
  - 识别功能的父子关系
  - 识别子功能
- 构建功能树结构：
  - 根节点：系统功能
  - 一级节点：业务域分类
  - 二级节点：主要功能
  - 三级节点：子功能
- 生成功能树文件：`{REPO_ROOT}/.cache/reverse/functions/function-partitioning/function-tree.json`
- 生成功能树Markdown文档：`{REPO_ROOT}/.cache/reverse/functions/function-partitioning/功能树.md`

### 6. [ ] 展示结果并向用户确认
- 🔴 强制验证缓存状态：AI Agent直接读取状态文件，验证 `function_partitioning.confirmed == false`
- 读取功能清单索引文件 `{REPO_ROOT}/.cache/reverse/functions/function-partitioning/function-index.json`
- 读取功能树文件 `{REPO_ROOT}/.cache/reverse/functions/function-partitioning/function-tree.json`
- 总结并展示功能划分结果：
  - 功能总数
  - 功能分类分布
  - 功能层次结构概览
  - 功能与场景的关联关系
  - 关键功能列表
- **🔴 交互模式判断**：
  - **全自动模式（默认）**：不询问用户，直接自动确认，继续执行步骤7
  - **交互模式（`--interactive`）**：询问用户确认："功能划分完成，是否确认结果？[Y/n]"，等待用户响应
- 🔴 状态双重检查：用户响应后（或自动确认后）AI Agent再次读取状态文件，验证更新成功

### 7. [ ] 处理用户确认，更新缓存状态
#### 用户确认（Y/yes/回车或全自动模式）
- **🔴 全自动模式（默认）**：自动执行确认流程，无需等待用户输入
- **🔴 交互模式（`--interactive`）**：用户输入 Y/yes/回车后执行确认流程
- 读取状态文件 `{REPO_ROOT}/.cache/reverse/functions/.cache-status.json`
- 更新 `function_partitioning` 部分，设置 `confirmed: true` 和当前时间戳
- 使用 `write` 工具保存更新后的状态文件
- 明确说明阶段3已完成，清空上下文
- 自动继续执行阶段4（功能详细文档生成）

#### 用户拒绝（n/no，仅交互模式）
- 仅在交互模式下可能出现
- 允许查看详情
- 或重新生成结果
- 或手动调整结果

## 输出
功能划分结果，保存到缓存目录：
- 批次结果文件：`{REPO_ROOT}/.cache/reverse/functions/function-partitioning/function-batch-{batch_number}.json`
- 索引文件：`{REPO_ROOT}/.cache/reverse/functions/function-partitioning/function-index.json`
- 功能树文件：`{REPO_ROOT}/.cache/reverse/functions/function-partitioning/function-tree.json`
- 功能树Markdown文档：`{REPO_ROOT}/.cache/reverse/functions/function-partitioning/功能树.md`

每个功能包含以下信息：
- 功能ID
- 功能名称
- 功能业务名称
- 功能业务域
- 功能分类
- 功能描述
- 功能入口信息（主入口点、备用入口点、入口文件列表、入口函数列表）
- 功能关联关系（功能与场景、功能与入口点、功能与模块）
- 功能依赖关系
- 功能详细信息（功能约束、功能行为、功能场景）
- 功能层级信息（父功能、子功能）

## 注意事项
- **🔴 交互模式判断**：
  - **全自动模式（默认）**：阶段3完成后自动确认，不暂停，直接继续阶段4
  - **交互模式（`--interactive`）**：阶段3完成后暂停，等待用户确认后才能继续阶段4
- 功能划分结果是功能详细文档生成的输入，必须确认后才能使用
- 用户确认后（或自动确认后），AI Agent 应该自动继续执行阶段 4（功能详细文档生成），不需要等待额外的用户指令
- 跨平台支持：所有脚本调用必须同时支持 Linux (bash) 和 Windows (PowerShell)
- 采用批次处理架构，使用索引文件定位批次结果，避免生成过大的合并文件
- 功能划分基于场景识别结果，需要确保阶段2已完成并确认
- 功能去重和合并是功能划分的重要环节，需要仔细处理

## 交叉引用

- 上一阶段：[02-scenario-identification.md](02-scenario-identification.md)
- 下一阶段：[04-function-detail-extraction-and-document-generation.md](04-function-detail-extraction-and-document-generation.md)

