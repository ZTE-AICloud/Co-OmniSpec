---
name: reverse-functions
description: 功能清单与功能详情文档反构编排Skill。当用户提到"功能反构"、"reverse functions"、或执行 `reverse --target functions` 时自动触发。编排5个阶段：阶段0缓存检查、阶段1项目入口识别、阶段2场景识别、阶段3功能划分、阶段4功能文档生成。支持批量并发处理和缓存复用。
user-invokable: false
allowed-tools: Agent, Read, Write, Edit, Bash(python3 *, bash *, powershell *)
---

# 功能反构Skill（functions）

## 概览（职责与输入输出）

- **职责**：基于项目入口与场景信息，完成：
  - 项目入口识别
  - 场景识别
  - 功能划分与功能树构建
  - 功能详细文档生成
- **输入前提**：
  - 用户通过 `reverse --target functions ...` 或 `--target all` 触发
  - 已根据 `--path` / `--files` 等参数确定扫描范围
- **输出产物**：
  - 缓存目录：`{REPO_ROOT}/.cache/reverse/functions/`
    - `project-entries.json`
    - `scenarios.json`
    - `function-list.json`、`function-tree.json`
    - `.cache-status.json`
  - 文档目录：`{REPO_ROOT}/omni-doc/specs/functions/`
    - `FUNC-XXX-功能名称.md`

> 本 Skill 对应原 `reverse-functions` 的“快捷命令 + 详细步骤”，现在以 Skill 形式承载该编排逻辑。


## 路径变量约定（执行前必读）

本 Skill 阶段文档中引用了以下路径变量，执行阶段命令前须先解析：

- `${CLAUDE_PLUGIN_ROOT}`：omni-reverse 插件安装根（运行期注入；指向本 skill 内专属脚本，如 `${CLAUDE_PLUGIN_ROOT}/skills/reverse-<X>/scripts/`）。
- `${DSDD}`：共享插件 omni-dsdd 安装根（含共享 `scripts/` 与 `omni-infra/`）。**首次使用前必须解析**：
  ```bash
  DSDD="$(bash "${CLAUDE_PLUGIN_ROOT}/scripts/resolve-dsdd-root.sh")" || { echo "缺少 omni-dsdd，中止"; exit 1; }
  ```
  解析器优先用 `${CLAUDE_PLUGIN_ROOT}/../omni-dsdd`，回退到脚本相对位置推算；失败则提示需与 omni-reverse 同 marketplace 安装 omni-dsdd。
- `{REPO_ROOT}` / `${CLAUDE_WORKING_DIR}`：被反构的代码工程根（运行期产物，与插件位置无关）。
- `${CLAUDE_SKILL_DIR}`：本 skill 自身目录（指向本 skill 内 `references/scripts/` 等自包含资源）。

> 说明：`${DSDD}` 不是运行期自动注入的变量，必须经 `resolve-dsdd-root.sh` 取值后方可使用。

## 与 `reverse` 命令的关系

- `reverse` 负责：
  - 将 `--target` 固定为 `functions`（或在 all 流水线中进入功能阶段）；
  - 解析交互模式（默认全自动 / `--interactive` / `--non-interactive` / `--yes`）；
  - 初始化 todo 与缓存后，激活本 Skill。
- 本 Skill 负责：
  - 驱动 4 个阶段的执行；
  - 遵守功能反构的交互与缓存规则。

## 阶段总览

本 Skill 按以下阶段执行，阶段详细说明见本目录下 `references/stages/`：

1. **阶段0：缓存状态检查**
2. **阶段1：项目入口识别**
3. **阶段2：场景识别**
4. **阶段3：功能划分**
5. **阶段4：功能详细文档生成**

## 行为准则（整个会话期间有效）

1. ❗ **缓存状态优先**：每步执行前必须读取 `.cache-status.json`，confirmed==true 时跳过该阶段
2. ❗ **Token 预算强制**：上下文超 10 万 tokens 必须清空；单批次预估超 15 万 tokens 必须分批
3. ❗ **来源引用**：所有推断结论必须标注来源（文件路径+行号），无来源 = 禁止输出

## 阶段0：缓存状态检查

- **阶段说明来源**：本 Skill 内 references/ 中的缓存约定
- **目标**：
  - 初始化 `{REPO_ROOT}/.cache/reverse/functions/.cache-status.json`
  - 建立 `project_entry_identification`、`scenario_identification`、`function_partitioning`、`function_document_generation` 四个段落
- **要点**：
  - 若某阶段已 `confirmed == true` 且对应输出存在，可在后续执行中跳过该阶段。

## 阶段1：项目入口识别

- **阶段说明来源**：本 Skill 内 [references/stages/01-project-entry-identification.md](references/stages/01-project-entry-identification.md)
- **目标**：识别项目的所有入口点（REST API、CLI、消息监听、定时任务、WebSocket 等）。
- **关键输出**：
  - `project-entries.json`（支持批次与索引）
- **要点**：
  - 按路径范围扫描并识别各种入口形式；
  - 提取路径、方法、参数、文件位置等信息及基本调用关系；
  - 默认模式下自动确认；在 `--interactive` 模式下可让用户确认入口识别结果。

## 阶段2：场景识别

- **阶段说明来源**：本 Skill 内 [references/stages/02-scenario-identification.md](references/stages/02-scenario-identification.md)
- **目标**：基于项目入口识别对应的业务场景。
- **关键输出**：
  - `scenarios.json`（支持批次与索引）
- **要点**：
  - 从入口结果中推断场景类型（正向主流程 / 异常 / 边界 / 批处理等）；
  - 提取场景名称、业务描述、前置条件、执行步骤等；
  - 建立场景与入口点的关联；
  - 交互模式下允许用户对场景识别进行确认与调整。

## 阶段3：功能划分

- **阶段说明来源**：本 Skill 内 [references/stages/03-function-partitioning.md](references/stages/03-function-partitioning.md)
- **目标**：基于场景识别结果划分功能，构建功能树。
- **关键输出**：
  - `function-list.json`（批次+索引）
  - `function-tree.json`
- **要点**：
  - 将相关场景聚合为功能，区分功能与子功能；
  - 提取功能名称、描述、分类、入口等；
  - 建立功能与场景、入口之间的关联关系；
  - 执行功能去重与合并逻辑；
  - 在 `--interactive` 模式下展示功能划分结果并等待确认。

## 阶段4：功能详细文档生成

- **阶段说明来源**：本 Skill 内 [references/stages/04-function-detail-extraction-and-document-generation.md](references/stages/04-function-detail-extraction-and-document-generation.md)
- **目标**：提取功能的完整详细信息并按模板生成文档。
- **关键输出**：
  - `{REPO_ROOT}/omni-doc/specs/functions/FUNC-XXX-功能名称.md`
- **要点**：
  - 以 `function-list.json` 为输入，分批处理功能；
  - 严格按照 `.omni-infra/metamodel/5.function-template.md` 的结构和字段生成文档（frontmatter、章节、PlantUML 部分等必须保持一致）；
  - 在默认模式下自动生成；如 Skill 需要，可在交互模式加入最终确认。

## 模式、缓存与 Todo 管理

- **执行模式**：
  - 默认：全自动模式（所有”是否确认？”视为 Y）；
  - 显式 `--interactive`：在每个阶段结束后暂停，使用中文询问用户是否继续；
  - `--non-interactive` / `--yes`：强制全自动。
- **缓存状态文件**：`{REPO_ROOT}/.cache/reverse/functions/.cache-status.json`  
  结构与原文档保持一致。
- **Todo 管理**：
  - `reverse` 为功能反构创建主任务与 4 个阶段 todo；
  - 本 Skill 在阶段开始/结束时更新 todo 状态。
- **验收条件**：
  - 阶段1：入口点已识别数 == 扫描文件总数（无遗漏）
  - 阶段2：场景已识别数 == 入口点数（每个入口点 ≥1 个场景）
  - 阶段3：功能已划分数 == 场景数（每场景 ≥1 个功能）
  - 阶段4：文档已生成数 == 功能总数

## 错误处理

- **阶段级失败**：某阶段失败时，记录错误到缓存状态文件，跳过后续阶段
- **子 Agent 失败**：重试最多3次，每次间隔递增；失败后标记批次状态为 failed，继续处理其他批次
- **缓存恢复**：阶段完成后可从断点恢复，已确认（confirmed）的阶段自动跳过
- **交互模式错误**：错误时展示具体原因和恢复建议，等待用户决策
- **脚本执行失败**：检查退出码，记录错误日志，终止当前阶段

## 上下文管理

- **缓存目录**：`{REPO_ROOT}/.cache/reverse/functions/`
- **状态文件**：`.cache-status.json`，记录各阶段 confirmed 状态
- **批次文件**：各阶段 `{stage}/batch-details-{N}.json` 和 `{stage}-batch-status.json`
- **索引文件**：各阶段 `{stage}-index.json`，避免生成过大的合并文件
- **详细说明**：见 [references/token-management.md](references/token-management.md)（Token 预算分配和上下文清理策略）

## 阶段间数据传递

| 传递方向 | 传递方式 | 传递内容 |
|----------|----------|----------|
| 阶段1 → 阶段2 | `entry-index.json` | 入口点批次索引和统计 |
| 阶段2 → 阶段3 | `scenario-index.json` | 场景批次索引和统计 |
| 阶段3 → 阶段4 | `function-index.json` + `function-tree.json` | 功能清单索引和功能树结构 |

## 子 Agent 调用

本 Skill 编排 4 个阶段，各阶段通过 Agent 工具调用子 Agent 执行并发分析。

**子 Agent 命名空间**：子 Agent 使用归属插件的命名空间前缀，由 Agent 工具的 `subagent_type` 参数指定——本插件（omni-reverse）本地提供的 agent 用 `omni-reverse:` 前缀，omni-dsdd 共享的 agent 用 `omni-dsdd:` 前缀。

| 阶段 | 子 Agent | 职责 | 并发策略 |
|------|----------|------|----------|
| 阶段1 | omni-dsdd:entry-identifier | 识别项目入口点 | 每轮最多2个 |
| 阶段2 | omni-reverse:scenario-recognizer | 识别业务场景 | 每轮最多2个 |
| 阶段3 | omni-dsdd:function-partitioner | 划分功能构建功能树 | 每轮最多2个 |
| 阶段4 | omni-dsdd:function-detail-writer | 生成功能详细文档 | 每轮最多2个 |

**并发控制**：采用分轮执行策略，每轮启动不超过2个子 Agent，避免上下文超限。每轮完成后执行 /compact 压缩上下文。

**参数传递**：通过 `{REPO_ROOT}/.cache/reverse/functions/{stage}/batch-details-{N}.json` 文件传递批次信息。

**返回值处理**：子 Agent 将结果写入对应批次文件，主 Agent 收集后更新索引文件。

**合并检查**：每轮处理完成后，主 Agent 必须验证：
- 计数之和 == 总任务量（入口点总数/场景总数/功能总数）
- 去重后无重复 ID
- 各批次结果格式一致

## 参考文档（本 Skill 内）

本 Skill 的详细规范位于本目录下 `references/`：

- Token 管理：[references/token-management.md](references/token-management.md)
- 阶段 1：[references/stages/01-project-entry-identification.md](references/stages/01-project-entry-identification.md)
- 阶段 2：[references/stages/02-scenario-identification.md](references/stages/02-scenario-identification.md)
- 阶段 3：[references/stages/03-function-partitioning.md](references/stages/03-function-partitioning.md)
- 阶段 4：[references/stages/04-function-detail-extraction-and-document-generation.md](references/stages/04-function-detail-extraction-and-document-generation.md)

执行本 Skill 时，AI Agent 应读取上述文档并严格按照其中描述的步骤和数据结构进行操作。

## 使用示例

### 基础用法
执行功能反构，自动识别入口点、场景、功能并生成文档：
```
reverse --target functions --path ./src
```

### 交互模式
在每个阶段完成后暂停确认：
```
reverse --target functions --interactive --path ./src
```

### 增量恢复
从断点恢复，跳过已确认的阶段：
```
reverse --target functions --path ./src
# 阶段1已确认（confirmed=true），自动跳过
```

## 幻觉防护

- 所有推断性结论必须引用具体来源（文件路径+行号或工具返回内容）
- 无来源的结论 = 禁止输出（可标注 "UNABLE TO ASSESS: [原因]"）
- 零结果场景处理：

| 场景 | 正确输出 | 禁止输出 |
|------|---------|---------|
| 无入口点 | "未找到任何入口点，请检查扫描路径" | 基于猜测列出虚假入口 |
| 阶段产出缺失 | 报错并退出当前阶段 | 跳过或自行生成 |

