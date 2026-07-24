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

### 3.1 子代理调用规范（详细说明）

#### 3.1.1 Agent 工具调用规范

使用 `Task` 工具时，必须包含以下参数：

| 参数 | 说明 | 必需 |
|------|------|------|
| `name` | 子Agent名称，固定为 `architecture-identifier` | 是 |
| `description` | 简短描述任务（3-5个词），如"识别代码库逻辑架构" | 是 |
| `prompt` | 详细的任务描述，包含分析目标和输出要求 | 是 |

#### 3.1.2 prompt 参数内容模板

```
请分析代码库的逻辑架构。

## 输入参数
- 仓库根目录：{REPO_ROOT}
- 目标类型：logic_architecture
- 扫描路径：{path}（如用户提供）

## 任务要求
1. 分析代码库的整体架构结构（分层架构模式、模块划分）
2. 识别关键模块和核心组件
3. 识别领域边界和依赖关系
4. 提取技术栈信息

## 输出要求
- 将结果写入：{REPO_ROOT}/omni-doc/specs/logic_architecture/architecture.json
- JSON格式必须包含以下字段：
  - architecture_type: 架构类型（如分层架构、微服务等）
  - tech_stack: 技术栈列表
  - layers: 层级信息（每层名称和职责）
  - modules: 关键模块列表（名称、路径、职责、依赖）
  - domain_boundaries: 领域划分
  - summary: 摘要统计（模块数、文件数等）

## 约束
- target_type 必须为 logic_architecture，不得使用其他值
- 输出文件必须写入 omni-doc/specs/logic_architecture/ 目录
```

#### 3.1.3 参数验证

- **必须验证** `target_type` 参数值为 `logic_architecture`
- 如果 `target_type` 不正确，架构识别结果将写入错误的路径
- 验证失败时应报错并终止执行

#### 3.1.4 返回值处理

- 子代理完成后，检查输出文件是否存在且非空
- 读取并验证 architecture.json 的 JSON 格式有效性
- 验证必需字段是否存在（architecture_type, modules 等）

#### 3.1.5 错误处理

- **重试机制**：如果子代理执行失败，最多重试3次
  - 第1次重试：间隔10秒
  - 第2次重试：间隔30秒
  - 第3次重试：间隔60秒
- **降级方案**：重试全部失败后，提示用户手动执行架构识别
- **失败记录**：记录失败原因到日志文件

#### 3.1.6 超时设置

- **超时时间**：建议设置5分钟（300秒）
- **超时处理**：
  1. 记录超时日志
  2. 尝试获取已生成的部分结果
  3. 提示用户是否继续等待或使用已有结果

#### 3.1.7 并发控制

- 本阶段子代理建议**串行执行**（一个完成后再执行下一个）
- 不建议并发执行多个架构识别任务，避免资源竞争

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
  - **确认模板说明**：`reverse-shared` 是 `reverse` 编排 Skill 的附属模块，其 `references/confirmation-template.md` 文件位于 `{REPO_ROOT}/.claude/skills/reverse/references/confirmation-template.md`，包含标准的阶段结束确认格式和交互模板
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
