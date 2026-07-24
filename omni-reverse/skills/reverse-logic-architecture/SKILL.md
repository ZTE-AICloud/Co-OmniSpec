---
name: reverse-logic-architecture
description: 逻辑架构要素反构编排Skill. 当 reverse 的 --target 为 logic_architecture 或 all 的逻辑架构阶段时触发.
user-invokable: false
allowed-tools: Read, Write, Grep, Glob, Bash, TaskCreate, TaskUpdate, TaskList, TaskGet
when_to_use: 当用户提到 "反向架构"、"分析代码结构"、"识别模块"、"reverse --target logic_architecture"、"逻辑架构" 或需要从代码库提取架构信息时使用.
---

# 逻辑架构反构 Skill（架构识别 → 规格产物）

## 行为准则

以下规则在整个会话期间有效，不因对话长度而放松：

1. ❗ **每个发现/修改必须引用来源**（文件路径 + 章节/行号）— 每次输出前自检
2. ❗ **禁止单边修复** — 改文档必须同步改实现，改实现必须同步改文档 — 每次输出前自检
3. ❗ **禁止未经验证的强结论** — 无来源的结论不允许输出 — 每次输出前自检

## 概览（职责与输入输出）

- **职责**：从代码库反构**逻辑架构**要素，生成结构化架构识别结果，供接口/功能等后续反构阶段作为上下文输入。
- **输入前提**：
  - 用户通过 `reverse --target logic_architecture ...` 触发，或在 `--target all` 时由编排 Skill **最先**调用本 Skill；
  - 已根据 `--path` / `--files` / `--exclude` 等参数确定分析范围（由入口命令解析并传入）。
- **输出产物（契约）**：
  - **主产物（规格目录，供各要素复用）**：`{REPO_ROOT}/omni-doc/specs/logic_architecture/architecture.json`
  - **阶段状态（缓存，断点与确认）**：`{REPO_ROOT}/.cache/reverse/logic_architecture/.cache-status.json`

> 架构识别的**生成**仅在本 Skill 中执行；`reverse-interfaces` 等 Skill **不再写入** `architecture.json`，只**读取**上述 `omni-doc` 路径下的文件。

## 与 `reverse` 命令的关系

- `reverse` 在 `--target logic_architecture` 时激活本 Skill；在 `--target all` 时由 `reverse-orchestration` **排在第一位**调用本 Skill。
- 本 Skill 负责：按阶段驱动架构识别子 Agent、维护本要素缓存状态、将结果写入 `omni-doc/specs/logic_architecture/`。

## 数据依赖链

- **阶段0 → 阶段1**：阶段0创建的状态文件 `.cache-status.json`（初始 confirmed=false）→ 阶段1读取判断是否需要执行
- **阶段1 → 下游阶段**：阶段1生成的 `omni-doc/specs/logic_architecture/architecture.json` → 后续 reverse-interfaces/reverse-functions 等阶段**只读取**此文件，不再重新生成
- **禁止重新生成**：后续阶段不得基于上下文中的架构描述重新生成 architecture.json，必须显式读取上述文件

## 阶段总览

1. **阶段0：缓存与输出目录检查**（初始化 `logic_architecture` 缓存状态、确保 `omni-doc/specs/logic_architecture/` 可写）
   ✅ Checkpoint: 阶段0完成 — 状态文件存在且有效，输出目录可写
2. **阶段1：架构识别**（子 Agent 分析并生成 `architecture.json`，用户确认后更新状态）
   ✅ Checkpoint: 阶段1完成 — architecture.json 已生成且格式有效

详细步骤见 `references/stages/`。

## 阶段0：缓存与输出目录检查

- **状态文件**：`{REPO_ROOT}/.cache/reverse/logic_architecture/.cache-status.json`
- 若不存在，则创建并初始化，至少包含：
  - `architecture_identification`（`confirmed` / `progress` / `timestamp`）
- 确保目录存在：
  - `{REPO_ROOT}/omni-doc/specs/logic_architecture/`
  - `{REPO_ROOT}/.cache/reverse/logic_architecture/`

**失败处理**：
- 目录创建失败 → 报错，禁止跳过，提示用户检查路径权限
- 状态文件写入失败 → 报错，禁止跳过

## 阶段1：架构识别

- **阶段说明来源**：[references/stages/01-architecture-identification.md](references/stages/01-architecture-identification.md)
- **子 Agent**：`architecture-identifier`（`target_type` 必须为 `logic_architecture`）
- **关键输出**：`{REPO_ROOT}/omni-doc/specs/logic_architecture/architecture.json`

**失败处理**：
- 子 Agent 超时（300s）→ 重试 3 次（10s/30s/60s 间隔），仍失败提示用户手动执行
- architecture.json 格式无效 → 报错，不允许跳过

### 架构输出格式（architecture.json Schema）

```json
{
  "architecture_type": "string",      // 架构类型，如"分层架构"、"微服务"、"单体"等
  "tech_stack": ["string"],            // 技术栈列表，如 ["Python", "FastAPI", "React"]
  "layers": [                          // 层级信息
    {
      "name": "string",                // 层级名称
      "description": "string",         // 层级职责描述
      "path_patterns": ["string"]      // 该层文件的路径模式（可选）
    }
  ],
  "modules": [                         // 关键模块列表
    {
      "name": "string",                // 模块名称
      "path": "string",                // 模块路径
      "description": "string",         // 模块职责描述
      "dependencies": ["string"],      // 依赖的其他模块
      "layer": "string"                // 所属层级
    }
  ],
  "domain_boundaries": [               // 领域边界（可选）
    {
      "name": "string",                // 领域名称
      "modules": ["string"],           // 该领域包含的模块
      "description": "string"          // 领域描述
    }
  ],
  "summary": {                         // 摘要统计
    "module_count": "number",          // 模块总数
    "file_count": "number",            // 文件总数
    "layer_count": "number"            // 层级数量
  },
  "metadata": {                        // 元数据
    "generated_at": "string",          // 生成时间（ISO 8601格式）
    "generator": "architecture-identifier",
    "version": "string"                // 架构识别版本
  }
}
```

**字段说明**：

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `architecture_type` | string | 是 | 架构类型，如"分层架构"、"微服务"、"六边形架构"等 |
| `tech_stack` | string[] | 是 | 技术栈列表，至少包含主要语言和框架 |
| `layers` | object[] | 是 | 层级信息，至少包含名称和描述 |
| `modules` | object[] | 是 | 关键模块列表，至少包含名称和路径 |
| `domain_boundaries` | object[] | 否 | 领域划分信息，如有多个领域则提供 |
| `summary` | object | 是 | 摘要统计 |
| `metadata` | object | 是 | 元数据信息 |

**验证规则**：
- JSON 格式必须有效
- `architecture_type` 不能为空
- `modules` 数组不能为空
- 每个 module 必须有 `name` 和 `path`

## 参考文档

- 阶段 1：[references/stages/01-architecture-identification.md](references/stages/01-architecture-identification.md)
- 数据约定：[references/data.md](references/data.md)
- 核心规则：[references/core-rules.md](references/core-rules.md)
- Token 管理：[references/token-management.md](references/token-management.md)

AI Agent 在执行本 Skill 时，应读取上述文档并严格按照其中描述执行。

## 子代理加载说明

### 架构识别子 Agent

本 Skill 使用 `Task` 工具调用 `architecture-identifier` 子 Agent 执行架构识别任务。

#### 加载机制

- **预加载行为**：当使用 `Task` 工具启动子 Agent 时，系统会自动注入完整的子 Agent 配置内容
- **与常规加载的差异**：子 Agent 会获得完整的上下文信息，包括：
  - 子 Agent 的定义和角色说明
  - 当前任务的具体要求
  - 相关的数据结构和输出格式规范

#### 上下文隔离

- 子 Agent 在隔离的环境中执行，不会污染主会话的上下文
- 子 Agent 的输出（架构识别结果）通过文件传递给主会话
- 建议在子 Agent 执行完成后，执行上下文清理（/compact）

#### 参数传递

- 通过 `Task` 工具的 `prompt` 参数传递详细的任务描述
- 必需参数：
  - `name`: `architecture-identifier`
  - `description`: "识别代码库逻辑架构"
  - `prompt`: 包含输入参数、任务要求、输出要求的完整描述

#### 返回值处理

- 子 Agent 完成时，输出文件已写入目标位置
- 主会话通过读取文件获取结果，不依赖上下文中的数据
- 详见 `references/stages/01-architecture-identification.md` 中的返回值处理说明

#### 合并检查清单

- **去重验证**：检查所有模块是否已处理（无遗漏）
- **一致性验证**：检查各模块的层归属、依赖关系是否互相矛盾
- **计数验证**：处理模块数 == modules 数组长度

## 使用示例

### 示例1：单独执行逻辑架构反构

```bash
# 触发逻辑架构识别
reverse --target logic_architecture --path ./src
```

**预期输出**：
1. 检查缓存状态
2. 调用架构识别子 Agent 分析代码结构
3. 生成 `omni-doc/specs/logic_architecture/architecture.json`
4. 展示结果并询问用户确认

### 示例2：执行全量反向（包含逻辑架构）

```bash
# 在全量反向流程中，逻辑架构是第一个被执行的要素
reverse --target all --path ./src
```

**执行顺序**：
1. 逻辑架构识别（本 Skill）
2. 接口反构
3. 功能识别
4. 实体反构
5. ...

### 示例3：清除缓存重新分析

```bash
# 强制重新执行逻辑架构识别
reverse --target logic_architecture --path ./src --clear-cache
```

**效果**：
- 忽略之前的缓存状态
- 重新调用子 Agent 执行完整分析
- 生成新的 `architecture.json`

### 示例4：查看架构识别结果

架构识别完成后，结果存储在：
```bash
cat {REPO_ROOT}/omni-doc/specs/logic_architecture/architecture.json
```

**结果结构示例**：
```json
{
  "architecture_type": "分层架构",
  "tech_stack": ["Python", "FastAPI", "React"],
  "layers": [
    {"name": "presentation", "description": "前端展示层"},
    {"name": "application", "description": "应用层"},
    {"name": "domain", "description": "领域层"},
    {"name": "infrastructure", "description": "基础设施层"}
  ],
  "modules": [...],
  "summary": {
    "module_count": 15,
    "file_count": 120
  }
}
```

### 示例5：手动调整架构结果

如果自动识别结果不准确，可以：

1. 查看结果：`cat omni-doc/specs/logic_architecture/architecture.json`
2. 手动编辑 JSON 文件调整内容
3. 将状态文件的 `confirmed` 设为 `true` 跳过重新分析

```bash
# 更新状态文件
echo '{"architecture_identification": {"confirmed": true, "progress": "completed", "timestamp": "2026-05-19"}}' > .cache/reverse/logic_architecture/.cache-status.json
```
