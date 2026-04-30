# 项目入口识别

<!-- 阶段1：项目入口识别 -->

## 职责
负责识别项目的所有入口点，包括RESTful API、CLI命令、消息队列监听器、定时任务、WebSocket等，为后续的场景识别和功能划分提供基础。

## 执行流程

### 0. [ ] 创建阶段1的子任务的Todo列表
为确保阶段执行过程的透明化和可追踪性，创建阶段1的子任务的Todo列表：

1. **步骤1 清理上一阶段的上下文，保证本阶段的上下文干净**
2. **步骤2 检查缓存状态，确定是否需要执行分析**
3. **步骤3 获取仓库根目录和缓存路径**
4. **步骤4 执行AI分析所有入口点（入口点识别）**
5. **步骤5 展示结果并向用户确认**
6. **步骤6 处理用户确认，更新缓存状态**

### 1. [x] 清理上一阶段的上下文，保证本阶段的上下文干净
- **阶段开始时主动清空上下文**：执行上下文清理，明确说明"开始阶段1：项目入口识别。已清空上一阶段的上下文"
- **处理过程中及时清理**：完成每个分析步骤后，忘掉不必要的中间信息
- **输出精简化**：只输出必要结果，避免冗长的解释性文本

### 2. [ ] 检查缓存状态，确定是否需要执行分析
- 读取状态文件：`{REPO_ROOT}/.cache/reverse/functions/.cache-status.json`
- 检查 `project_entry_identification.confirmed` 字段
- 如果 `confirmed == true`：跳过阶段1，使用缓存结果
- 如果 `confirmed == false` 或不存在：执行阶段1

### 3. [ ] 获取仓库根目录和缓存路径
- 跨平台脚本调用获取 REPO_ROOT：
  - AI Agent直接调用check-prerequisites.sh脚本
  - AI Agent直接调用check-prerequisites.ps1脚本
- 定义缓存目录：`{REPO_ROOT}/.cache/reverse/functions/`
- 确保缓存目录存在

### 4. [ ] 执行AI分析所有入口点（入口点识别）
为确保阶段执行过程的透明化和可追踪性，创建步骤4的子任务的Todo列表：

4.1. [ ] **执行前检查**
4.2. [ ] **读取用户输入和评估数据规模**
4.3. [ ] **调用批次生成脚本自动分批处理（入口点数量 > 20时执行）**
4.4. [ ] **同时启动多个子agent一起并发分别处理多个批次**
4.5. [ ] **收集子agent处理结果**
4.6. [ ] **主agent统一管理批次状态**
4.7. [ ] **收集子agent结果并更新状态**
4.8. [ ] **检查是否还有未处理的批次【必须执行的步骤】**
4.9. [ ] **如果还有待处理批次：继续循环处理**
4.10. [ ] **单批扫描流程**（入口点数量 <= 20时执行）
4.11. [ ] **扫描完成后检查**
4.12. [ ] **扫描完成后生成最终入口点文件project-entries.json（批次+索引）**

#### 核心执行流程
AI Agent需要按照以下决策树执行分析：

4.1. **执行前检查**：
   - 阶段开始时明确告知用户当前阶段、扫描范围、预计工作量
   - 🔴 **强制Token预算评估**：评估当前任务的Token预算，确保不超过15万tokens的安全限制

4.2. **读取用户输入和评估数据规模**：
   - 读取用户指定的扫描路径（如果提供）
   - 识别需要扫描的文件（基于入口点特征模式）
   - **智能统计需要扫描的文件总数，并且将识别出的文件写入一个file_list.json文件中：作为自动分批的输入，格式是数组的形式**
   - **判断处理方式**：
     - 文件数量 > 20？执行分批扫描（跳转到步骤4.3）
     - 文件数量 <= 20？执行单批扫描（跳转到步骤4.10）

4.3. **调用批次生成脚本自动分批处理（文件数量 > 20时执行）**：
   - 🔴 **强制要求**：必须调用批次生成脚本自动分批处理，禁止直接创建示例批次文件
   - 🔴 动态批次规划：
     - 基于入口点特征筛选获取文件列表
     - 调用批次生成脚本自动分批处理：
       - Linux/macOS: `python3 {REPO_ROOT}/scripts/python/generate_entry_batches.py --repo-root {REPO_ROOT} --file-list {file_list_json}`
       - Windows: `python {REPO_ROOT}\scripts\python\generate_entry_batches.py --repo-root {REPO_ROOT} --file-list {file_list_json}`
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
     - 使用批量获取脚本获取多个待处理批次：
       - Linux/macOS: `{REPO_ROOT}/scripts/bash/get-next-batches.sh --repo-root {REPO_ROOT} --batch-count 2 --stage-type functions --stage-name entry_identification`
       - Windows: `powershell -ExecutionPolicy Bypass -File {REPO_ROOT}\scripts\powershell\get-next-batches.ps1 -RepoRoot {REPO_ROOT} -BatchCount 2 -StageType functions -StageName entry_identification`
   - 🔴 **并行启动方式**：
     - 为了提高处理效率，同时启动多个entry-identifier子Agent处理不同的批次，一个子agent负责一个批次，多个子agent同时处理。
     - 🔴 **强制要求**：必须使用明确的并行启动指令，确保多个子Agent同时启动
     - 示例：请同时启动2个entry-identifier子Agent来分别处理以下批次文件：
       - `entry-batch-details-1.json`
       - `entry-batch-details-2.json`
   - 🔴 **上下文管理**：
     - 主agent负责协调所有子agent的执行
     - 每轮处理完成后，主agent清理上下文，准备下一轮处理

4.5. **收集子agent处理结果**：
   - 等待所有子Agent完成处理
   - 验证批次结果文件是否存在：
     - `{REPO_ROOT}/.cache/reverse/functions/entry-identification/entry-batch-{batch_number}.json`
   - 验证批次结果文件格式正确性

4.6. **主agent统一管理批次状态**：
   - 读取批次状态文件：`{REPO_ROOT}/.cache/reverse/functions/entry-identification/entry-batch-status.json`
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

4.10. **单批扫描流程**（文件数量 <= 20时执行）：
   - 直接调用entry-identifier子Agent处理所有文件
   - 生成单批结果文件

4.11. **扫描完成后检查**：
   - 验证所有批次都已处理完成
   - 验证结果文件完整性

4.12. **扫描完成后生成最终入口点文件project-entries.json（批次+索引）**：
   - 生成索引文件：`{REPO_ROOT}/.cache/reverse/functions/entry-identification/entry-index.json`
   - 索引文件包含所有批次结果的位置和统计信息
   - 不合并批次结果文件，使用索引文件定位批次结果

### 5. [ ] 展示结果并向用户确认
- 🔴 强制验证缓存状态：AI Agent直接读取状态文件，验证 `project_entry_identification.confirmed == false`
- 读取入口点识别结果索引文件 `{REPO_ROOT}/.cache/reverse/functions/entry-identification/entry-index.json`
- 总结并展示入口点识别结果：
  - 入口点总数
  - 入口点类型分布
  - 入口点文件分布
  - 关键入口点列表
- **🔴 交互模式判断**：
  - **全自动模式（默认）**：不询问用户，直接自动确认，继续执行步骤6
  - **交互模式（`--interactive`）**：询问用户确认："入口点识别完成，是否确认结果？[Y/n]"，等待用户响应
- 🔴 状态双重检查：用户响应后（或自动确认后）AI Agent再次读取状态文件，验证更新成功

### 6. [ ] 处理用户确认，更新缓存状态
#### 用户确认（Y/yes/回车或全自动模式）
- **🔴 全自动模式（默认）**：自动执行确认流程，无需等待用户输入
- **🔴 交互模式（`--interactive`）**：用户输入 Y/yes/回车后执行确认流程
- 读取状态文件 `{REPO_ROOT}/.cache/reverse/functions/.cache-status.json`
- 更新 `project_entry_identification` 部分，设置 `confirmed: true` 和当前时间戳
- 使用 `write` 工具保存更新后的状态文件
- 明确说明阶段1已完成，清空上下文
- 自动继续执行阶段2（场景识别）

#### 用户拒绝（n/no，仅交互模式）
- 仅在交互模式下可能出现
- 允许查看详情
- 或重新生成结果
- 或手动调整结果

## 输出
入口点识别结果（批次+索引格式），保存到缓存目录：
- 批次结果文件：`{REPO_ROOT}/.cache/reverse/functions/entry-identification/entry-batch-{batch_number}.json`
- 索引文件：`{REPO_ROOT}/.cache/reverse/functions/entry-identification/entry-index.json`

每个入口点包含以下信息：
- 入口点ID
- 入口点名称
- 入口点类型（RESTful API、CLI命令、消息队列、定时任务、WebSocket等）
- 入口点路径/命令
- 入口点文件位置
- 入口点函数/方法
- 入口点参数信息
- 入口点描述

## 注意事项
- **🔴 交互模式判断**：
  - **全自动模式（默认）**：阶段1完成后自动确认，不暂停，直接继续阶段2
  - **交互模式（`--interactive`）**：阶段1完成后暂停，等待用户确认后才能继续阶段2
- 入口点识别结果是场景识别的输入，必须确认后才能使用
- 用户确认后（或自动确认后），AI Agent 应该自动继续执行阶段 2（场景识别），不需要等待额外的用户指令
- 跨平台支持：所有脚本调用必须同时支持 Linux (bash) 和 Windows (PowerShell)
- 采用批次处理架构，使用索引文件定位批次结果，避免生成过大的合并文件

