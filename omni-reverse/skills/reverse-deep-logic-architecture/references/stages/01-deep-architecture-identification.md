# 深度架构识别（深度逻辑架构要素）

## 职责

执行深度架构识别，生成 Markdown 报告 `logic_architecture.md`。

## 执行流程

1. **检查缓存命中**：
   - 若 `{REPO_ROOT}/omni-doc/on-demand/logic_architecture.md` 已存在且可读，允许直接复用。
2. **缓存未命中时，调用子 Agent**：
   - 使用 `Task` 工具启动 `deep-architecture-identifier`
   - 传入 `repo_root`（绝对路径）
3. **结果校验**：
   - 验证 `logic_architecture.md` 已生成且非空
   - 验证 `logic_architecture.cache-status.md` 可读（若存在）
4. **展示摘要并确认**（交互模式）/ 自动确认（非交互模式）

## 子 Agent 调用规范

本阶段通过 `Task` 工具调用 `deep-architecture-identifier` 子 Agent。

### 必需参数

- **name**（子 Agent 名称）：`deep-architecture-identifier`
- **description**（简短描述，3-5个词）：`深度架构识别子代理`
- **prompt**（任务描述，3-5句话）：
  ```
  分析代码库的深度逻辑架构，识别以下要素：
  1. 核心业务逻辑层及其职责边界
  2. 数据流和状态管理模式
  3. 模块间的依赖关系和调用链
  4. 业务规则和决策逻辑的集中点

  输入：repo_root = {REPO_ROOT}
  输出：生成 {REPO_ROOT}/omni-doc/on-demand/logic_architecture.md

  要求：
  - 使用 LSP 和结构化信号分析，优先按模块逐步归纳
  - 单次分析输入控制在 15 万 tokens 内
  - 输出必须为 Markdown，格式符合 logic-architecture-template.md
  - 详细结果写入文件，避免在对话中展开大段内容
  ```
- **subagent_type**：根据实际需求选择（建议 `general-purpose` 或 `Explore`）

### 超时设置

- **建议超时**：5 分钟（300 秒）
- **超时处理**：超时后记录错误日志，标记任务失败，通知用户

### 错误处理

- **重试机制**：子 Agent 调用失败时重试最多 3 次，间隔 10s、30s、60s
- **降级方案**：重试全部失败后，使用备用方法（人工审核或跳过）
- **失败记录**：记录失败原因到日志文件，格式：`[时间戳] 子Agent调用失败：{原因}`
- **用户通知**：交互模式下提示用户失败原因和可用的备选方案

### 返回值处理

1. **验证返回结果**：
   - 检查 `logic_architecture.md` 文件是否存在
   - 验证文件大小 > 0（非空）
   - 验证 Markdown 格式有效
2. **完整性检查**：
   - 检查是否包含核心章节（架构概述、模块划分、依赖关系等）
   - 检查 Token 消耗是否在预算范围内
3. **后处理**：
   - 更新 `logic_architecture.cache-status.md`（记录生成时间、状态等）
   - 在交互模式下展示摘要供用户确认

### 并发控制

- 本阶段为单 Agent 串行执行（无并发需求）
- 如后续扩展为多 Agent 并发，需注意资源冲突处理（使用唯一输出文件名）

## 输出

- **主产物**：`{REPO_ROOT}/omni-doc/on-demand/logic_architecture.md`
- **状态文件**：`{REPO_ROOT}/omni-doc/on-demand/logic_architecture.cache-status.md`（可选）