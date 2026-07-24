# 按规则类型的输出模板（reverse-rules）

本目录为**每个规则类型一个模板文件**，阶段3 根据代码库实际情况填充占位符后生成 `omni-doc/rules/{规则ID}.mdc`。

## 路径

- **OmniSpec 仓库内**：`omni-infra/metamodel/10.rules-templates/`
- **用户项目中**（`.omni-infra` 已安装或链接）：`{REPO_ROOT}/.omni-infra/metamodel/10.rules-templates/`

## 文件命名

- 文件名：`{规则ID}.template.md`，例如 `00-architecture.template.md`、`05-logging.template.md`

## 占位符

| 占位符 | 说明 |
|--------|------|
| `{{RULE_ID}}` | 规则 ID |
| `{{RULE_NAME}}` | 规则名称 |
| `{{DESCRIPTION}}` | 规则简短描述（frontmatter） |
| `{{GLOBS}}` | 文件匹配模式（alwaysApply 为 false 时使用） |
| `{{ALWAYS_APPLY}}` | true / false |
| `{{MAIN_LANGUAGE}}` | 项目主要语言 |
| `{{SCOPE}}` | 适用范围正文 |
| `{{PRINCIPLES}}` | 核心原则正文 |
| `{{SPECIFICATIONS}}` | 具体规范与示例正文 |
| `{{IMPLEMENTATION_GUIDE}}` | 实现指南正文 |
| `{{CHECKLIST}}` | 检查要点正文 |

P0 规则（00-architecture、08-style-patterns）通常 `alwaysApply: true`，模板中可不含 `globs`；其余规则模板含 `globs`，由 Agent 按项目填充或省略。
