# 深度架构识别阶段

<!-- 阶段2：执行架构识别（可选，带缓存） -->

## 职责
负责执行深度架构分析，为后续反构提供稳定的架构上下文。支持缓存机制，避免重复识别。

## 执行流程

### 0. [ ] 创建阶段2的子任务的Todo列表
为确保阶段执行过程的透明化和可追踪性，创建阶段2的子任务的Todo列表：

1. **步骤1 清理上一阶段的上下文，保证本阶段的上下文干净**
2. **步骤2 确认前置条件（阶段1已完成）**
3. **步骤3 判断架构识别缓存是否存在**
4. **步骤4 若缓存不存在：执行架构识别**
5. **步骤5 验证架构识别结果并设置变量**

### 1. [x] 清理上一阶段的上下文，保证本阶段的上下文干净
- **阶段开始时主动清空上下文**：执行上下文清理，明确说明"开始阶段2：深度架构识别。已清空上一阶段的上下文"
- **处理过程中及时清理**：完成每个步骤后，忘掉不必要的中间信息
- **输出精简化**：只输出必要结果，避免冗长的解释性文本

### 2. [ ] 确认前置条件（阶段1已完成）
- **前置条件检查**：
  - 确认阶段1已执行完成，并已获取以下变量：
    - `REPO_ROOT`：仓库根目录（绝对路径）
    - `FEATURE_DIR`：特性目录路径（绝对路径）
    - `BRANCH_NAME`：特性分支名称
  - 若阶段1未执行完成或变量未设置：
    - 输出错误信息：`❌ 错误：阶段1（分支和特性准备）未完成，无法继续执行架构识别`
    - 输出提示：`请确保阶段1已成功执行完成，并获取了必要的环境变量`
    - **立即终止流程**，不继续执行后续步骤
    - 返回错误状态

### 3. [ ] 判断架构识别缓存是否存在
- 检查 `{REPO_ROOT}/omni-doc/on-demand/logic_architecture.md` 是否已存在（`REPO_ROOT` 为阶段1中获取的值）
- 若存在：
  - 输出提示：`⏭️ deep-architecture cache hit, skip deep-architecture-identifier`
  - 设置 `deep_architecture_result = {REPO_ROOT}/omni-doc/on-demand/logic_architecture.md`（绝对路径）
  - **跳过步骤4，直接进入步骤5**
- 若不存在：继续执行步骤4

### 4. [ ] 若缓存不存在：执行架构识别
- **⚠️ 执行顺序约束**：本步骤必须在阶段3之前执行完成，阶段3依赖本步骤的执行结果
- **实现**：按本 Skill 内 [references/implementation/deep-architecture-identification.md](../implementation/deep-architecture-identification.md) 执行深度架构识别（输入/输出及步骤以该文档为准）。
- 输入：
  - `repo_root`: 阶段1中获取的 `REPO_ROOT`（必须为绝对路径）
- 期望输出（必须成功）：
  - `{REPO_ROOT}/omni-doc/on-demand/logic_architecture.md`（`REPO_ROOT` 为阶段1中获取的值，必需）
  - `{REPO_ROOT}/omni-doc/on-demand/logic_architecture.cache-status.md`（可选）
- 失败策略：**必须成功**（失败则终止流程，不继续执行阶段3）

### 5. [ ] 验证架构识别结果并设置变量
- 检查 `{REPO_ROOT}/omni-doc/on-demand/logic_architecture.md` 是否存在（`REPO_ROOT` 为阶段1中获取的值）
- 若存在：设置 `deep_architecture_result = {REPO_ROOT}/omni-doc/on-demand/logic_architecture.md`（绝对路径）
- 若不存在：
  - 输出错误信息：`❌ 错误：架构识别结果不存在，无法继续执行反构流程`
  - 输出提示：`请确保步骤4（架构识别）已成功执行，生成文件：{REPO_ROOT}/omni-doc/on-demand/logic_architecture.md`
  - **立即终止流程**，不继续执行后续步骤
  - 返回错误状态
- **阶段2完成**：标记阶段2已完成，可以继续执行阶段3

## 输出
- `deep_architecture_result`：架构识别结果文件路径（绝对路径，格式：`{REPO_ROOT}/omni-doc/on-demand/logic_architecture.md`）

## 注意事项
- **⚠️ 执行顺序约束**：本阶段必须在阶段3之前执行完成，阶段3依赖本阶段的执行结果（无论成功或失败）
- **🔴 重要**：AI Agent 在执行所有步骤时，必须使用中文进行说明和输出
- 缓存策略：若架构识别结果已存在，则跳过执行，直接使用缓存结果
- 阶段2完成后，必须将 `deep_architecture_result` 变量传递给后续阶段

