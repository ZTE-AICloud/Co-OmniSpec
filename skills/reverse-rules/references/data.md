---
description: 规则反构的数据交换与缓存规范
parent: reverse-rules
target: rules
---

### 缓存目录与路径

**缓存根目录**：`{REPO_ROOT}/.cache/reverse/rules/`

**主要文件**：

- `.cache-status.json`：各阶段确认状态与时间戳
- `01-features.md`：代码库特征检测报告（阶段1 输出）
- `rule-mapping.json`：规则选择与分批方案（阶段2 输出）
- `prompts/03-rule-{规则ID}.md`：单规则执行提示（阶段2 生成，阶段3 使用）

**输出目录**：`{REPO_ROOT}/omni-doc/rules/`

- 规则文档：`{REPO_ROOT}/omni-doc/rules/{规则ID}.mdc`

### 状态文件格式

```json
{
  "features_scan": {
    "confirmed": true,
    "progress": "completed",
    "timestamp": "2024-01-01T00:00:00Z"
  },
  "rule_mapping": {
    "confirmed": true,
    "progress": "completed",
    "timestamp": "2024-01-01T00:00:00Z"
  },
  "rule_generation": {
    "confirmed": true,
    "progress": "completed",
    "timestamp": "2024-01-01T00:00:00Z"
  },
  "user_rules_injection": {
    "confirmed": true,
    "progress": "completed",
    "timestamp": "2024-01-01T00:00:00Z"
  }
}
```

### AI Agent 与脚本/文件交互

- **读取**：Agent 使用 `read_file` 读取 `01-features.md`、`rule-mapping.json`、各 `03-rule-*.md`
- **写入**：Agent 使用 `write` 将特征报告、规则映射、规则执行提示写入缓存目录；将生成的规则写入 `omni-doc/rules/*.mdc`
- **展示**：Agent 基于上述文件内容做摘要与统计，用中文向用户展示并等待确认

### 规则文档结构要求

- 每个 `.mdc` 包含 YAML frontmatter（`description`、`globs` 或 `alwaysApply`）与 Markdown 规则正文
- 正文需包含：适用范围、核心原则、具体规范、实现指南、检查要点
- 代码示例必须使用项目主要语言（依据 01-features 中的“主要语言”）

### 指定模版填充（模板路径约定）

- **规则执行模板**（阶段2 生成 03-rule-*.md 时使用）  
  - 用户通过参数指定：`--template <file>`，Agent 读取该文件作为“单规则执行模板”，用占位符（如 `{RULE_ID}`、`{RULE_NAME}`、`{RULE_DESCRIPTION}`、`{GLOBS_PATTERN}`、`{ALWAYS_APPLY}` 等）填充后写出各 `03-rule-{规则ID}.md`。  
  - 项目默认路径（未传 `--template` 时优先查找）：`{REPO_ROOT}/.infra/templates/reverse-rule-execution-template.md`  
  - 若两者均不存在：使用阶段2 文档中描述的内置模板结构。

- **按规则类型的输出模板**（阶段3 生成每条 .mdc，推荐）  
  - 每个规则类型一个模板文件，**位置**：`{REPO_ROOT}/.infra/templates/default/reverse-rules-templates/{规则ID}.template.md`（例如 `00-architecture.template.md`、`05-logging.template.md`）。  
  - 阶段3 生成某条规则时：先加载该规则 ID 对应的模板；再根据 `01-features.md` 与代码库实际情况填充占位符或章节，得到最终 .mdc。  
  - 若某规则类型无单独模板，则使用通用规则输出模板或内置结构。

- **通用规则输出模板**（兜底）  
  - 项目模板路径：`{REPO_ROOT}/.infra/templates/reverse-rule-output-template.md`  
  - 若存在：Agent 按该模板的章节与占位符填充生成 .mdc；若不存在，按“规则文档结构要求”中的默认结构生成。

**按类型模板可用占位符**（由 Agent 根据 01-features 与代码分析填充）：

| 占位符 | 说明 | 来源 |
|--------|------|------|
| `{{RULE_ID}}` | 规则 ID | 如 00-architecture |
| `{{RULE_NAME}}` | 规则名称 | 如“项目结构分析” |
| `{{DESCRIPTION}}` | 规则简短描述 | frontmatter description |
| `{{GLOBS}}` | 文件匹配模式 | 当 alwaysApply 为 false 时 |
| `{{ALWAYS_APPLY}}` | 是否始终应用 | true/false |
| `{{MAIN_LANGUAGE}}` | 项目主要语言 | 01-features 项目概况 |
| `{{PROJECT_STRUCTURE}}` | 项目/目录结构摘要 | 01-features + 代码库 |
| `{{DETECTED_FRAMEWORKS}}` | 检测到的框架与库 | 01-features 技术栈 |
| `{{SCOPE}}` | 适用范围 | 根据代码库与规则类型生成 |
| `{{PRINCIPLES}}` | 核心原则 | 根据代码库与规则类型生成 |
| `{{SPECIFICATIONS}}` | 具体规范与示例 | 根据代码库与规则类型生成 |
| `{{IMPLEMENTATION_GUIDE}}` | 实现指南 | 根据代码库与规则类型生成 |
| `{{CHECKLIST}}` | 检查要点 | 根据代码库与规则类型生成 |
