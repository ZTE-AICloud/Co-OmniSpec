# 任务: 生成单个需求规范

## 输入内容
{{requirement_info}}

## 步骤

### 第一步：理解需求上下文
- 根据**输入内容**中的需求描述和关联场景，理解需求的业务背景
- 阅读关联场景的详细文档（`omni-doc/specs/scenarios/SCN-XXX-*.md`），深入理解场景的业务流程

### 第二步：完善需求描述
基于场景文档分析，完善需求的描述：
- 明确需求的目的和范围
- 确认需求类型（Functional / Non-Functional）

### 第三步：细化 EARS 描述
在输入内容已有 EARS 描述的基础上，补充和细化：
- 主需求使用 Ubiquitous 模式，确保描述清晰完整
- 子需求选择合适的模式（Event-driven / State-based / Unwanted / Optional）
- 每条子需求描述具体明确，避免模糊表述
- 覆盖正常流程和关键异常流程

### 第四步：整理并输出
按照**输出格式**要求，将结果保存到 `omni-doc/specs/requirements/REQ-XXX-需求名称.md`

- 文件名中的 `XXX` 与需求ID一致
- 文件名中的需求名称与需求名称一致
- 确保 YAML frontmatter 中所有字段填写完整
- 确保输出格式符合Markdown规范

## 输出格式

读取模板文件 `specify/metamodel/1.requirement-template.md`，严格按照模板结构生成输出文件。

### 输出要求
- **输出路径**：`omni-doc/specs/requirements/REQ-XXX-需求名称.md`
- **模板遵循**：文件结构、frontmatter 字段、章节层级均以模板文件为准
- **填充规则**：
  - frontmatter 中所有字段必须填写完整（id, name, type, description）
  - 正文使用 EARS 语法格式
  - 主需求 + 子需求层次结构清晰

**注意事项**：
- **分析必须基于场景文档的实际内容**，不能主观推测
- EARS 描述要具体明确，避免使用占位符
- frontmatter 中的 `description` 简要说明需求的目的和范围
- type 字段仅可为 `Functional` 或 `Non-Functional`
