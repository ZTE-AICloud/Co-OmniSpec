# 架构识别（逻辑架构要素）

<!-- 阶段1：逻辑架构 — 架构识别 -->

## 职责

负责分析代码库的整体架构，识别分层架构模式和关键模块；产出写入 **`omni-doc/specs/logic_architecture/`**，供接口反构等下游读取。

## 执行流程

### 0. [ ] 创建阶段1的子任务的Todo列表

1. **步骤1 清理上一阶段的上下文，保证本阶段的上下文干净**
2. **步骤2 检查缓存状态，确定是否需要执行分析**
3. **步骤3 调用架构识别子Agent执行分析**
4. **步骤4 等待子Agent处理结果**
5. **步骤5 展示结果并向用户确认**
6. **步骤6 处理用户确认，更新缓存状态**

### 1. [x] 清理上一阶段的上下文，保证本阶段的上下文干净

- **阶段开始时主动清空上下文**：执行上下文清理，明确说明「开始阶段1：逻辑架构—架构识别。已清空上一阶段的上下文」
- **处理过程中及时清理**：完成每个分析步骤后，忘掉不必要的中间信息
- **输出精简化**：只输出必要结果，避免冗长的解释性文本

### 2. [ ] 检查缓存状态，确定是否需要执行分析

- 读取状态文件：`{REPO_ROOT}/.cache/reverse/logic_architecture/.cache-status.json`
- 检查 `architecture_identification.confirmed` 字段
- 若 `confirmed == true` 且 `omni-doc/specs/logic_architecture/architecture.json` 存在且非空：可跳过重新分析（除非用户要求 `--clear-cache` 后重跑）
- 若 `confirmed == false` 或主产物缺失：执行本阶段分析

### 3. [ ] 调用架构识别子Agent执行分析

- **启动架构识别子Agent**：
  - 使用 `Task` 工具启动名为 `architecture-identifier` 的子Agent
  - 传递参数：
    - `repo_root`: `{REPO_ROOT}`
    - `target_type`: **`logic_architecture`**（必须，不得再使用 `interfaces`）
    - `path`: 从用户输入获取的扫描路径（如果提供）
  - 等待子Agent完成处理

### 4. [ ] 等待子Agent处理结果

- 监控子Agent的执行状态
- 验证文件是否存在：
  - `{REPO_ROOT}/omni-doc/specs/logic_architecture/architecture.json`
  - `{REPO_ROOT}/.cache/reverse/logic_architecture/.cache-status.json`

### 5. [ ] 展示结果并向用户确认

- 🔴 读取架构识别结果：`{REPO_ROOT}/omni-doc/specs/logic_architecture/architecture.json`
- 总结并展示：架构类型、技术栈、层级信息、关键模块、领域划分、摘要统计等
- **🔴 统一确认机制**：按 `reverse-shared/references/confirmation-template.md` 的「阶段结束确认模板」
  - 阶段名称：逻辑架构—架构识别
  - 询问内容：「架构识别完成，是否确认结果？[Y/n]」
- **全自动模式**（如 `--target all`）：不询问，视为已确认，并直接将 `architecture_identification.confirmed` 更新为 `true`

### 6. [ ] 处理用户确认，更新缓存状态

- 状态文件：`{REPO_ROOT}/.cache/reverse/logic_architecture/.cache-status.json`
- 状态字段：`architecture_identification`
- 用户拒绝（仅交互模式）：允许查看详情、重新生成或手工调整 `architecture.json` 后再次确认

## 输出

- **主产物**：`{REPO_ROOT}/omni-doc/specs/logic_architecture/architecture.json`（JSON，结构见 `claude/agents/architecture-identifier.md` 中示例）
- **状态**：`.cache/reverse/logic_architecture/.cache-status.json`

## 注意事项

- 本阶段产出为 **跨要素共享契约**：`reverse-interfaces` 阶段从上述 `omni-doc` 路径读取，不再写入 `.cache/reverse/interfaces/architecture.json`。
- 跨平台：脚本调用须同时支持 Linux (bash) 与 Windows (PowerShell)。
