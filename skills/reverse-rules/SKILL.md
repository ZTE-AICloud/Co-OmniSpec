---
name: reverse-rules
description: 规则与约束反构的编排Skill. 当 reverse 的 --target 为 rules 或 all 的规则阶段时触发.
user-invokable: false
---

# 规则/约束反构Skill（rules）

## 概览（职责与输入输出）

- **职责**：从代码库与既有文档中反构各类规则与约束，生成可被 AI/IDE 使用的 `.mdc` 规则文档。
- **输入前提**：
  - 用户通过 `reverse --target rules ...` 或 `--target all` 触发
  - 已根据 `--path` / `--exclude` 等参数确定扫描范围
- **输出产物**：
  - 缓存目录：`{REPO_ROOT}/.cache/reverse/rules/`
    - `01-features.md`（特征报告）
    - `rule-mapping.json` 等中间数据
    - `.cache-status.json`
  - 文档目录：`{REPO_ROOT}/omni-doc/rules/`
    - 每条规则对应一份 `{规则ID}.mdc`

> 规则类型按优先级 P0～P4 管理，支持通用模板与规则类型专用模板。

## 与 `reverse` 命令的关系

- `reverse` 负责：
  - 解析参数（包含 `--path`、`--exclude`、`--interactive`、`--template`、`--clear-cache` 等）；
  - 初始化缓存与输出目录；
  - 在规则阶段激活本 Skill。
- 本 Skill 负责：
  - 执行特征检测、规则映射与分批、文档生成与用户规则注入；
  - 在对话模式下插入合适的确认点。

## 阶段总览

对应原 `reverse-rules.md` 与 `reverse.rules/stages/*`，本 Skill 包含 4 个阶段：

1. **阶段1：特征检测**
2. **阶段2：规则映射与分批**
3. **阶段3：规则文档生成**
4. **阶段4：用户规则注入（可选）**

## 阶段1：特征检测

- **阶段说明来源**：本 Skill 内 [references/stages/01-features-scan.md](references/stages/01-features-scan.md)
- **目标**：扫描代码库结构、语言、技术栈、工程化水平等，生成特征报告。
- **关键输出**：
  - `{REPO_ROOT}/.cache/reverse/rules/01-features.md`
- **要点**：
  - 按路径/排除规则扫描仓库；
  - 抽取有助于规则选择的语言与架构特征；
  - 更新缓存状态中 `features_scan` 段落。

## 阶段2：规则映射与分批

- **阶段说明来源**：本 Skill 内 [references/stages/02-rule-mapping-and-batching.md](references/stages/02-rule-mapping-and-batching.md)
- **目标**：根据特征报告选择适用规则类型（P0～P4），生成规则执行提示与分批方案。
- **关键输出**：
  - `rule-mapping.json`
  - 各规则提示文档：`prompts/03-rule-{规则ID}.md`
- **要点**：
  - 根据仓库特征选择/关闭部分规则；
  - 按规则 ID 规划生成顺序与分批信息；
  - 在对话模式下可让用户确认规则集合与执行范围。

## 阶段3：规则文档生成

- **阶段说明来源**：本 Skill 内 [references/stages/03-rule-document-generation.md](references/stages/03-rule-document-generation.md)
- **目标**：结合规则提示与模板，为每条规则生成 `.mdc` 文档。
- **关键输出**：
  - `{REPO_ROOT}/omni-doc/rules/{规则ID}.mdc`
- **要点**：
  - 使用规则类型模板：`{REPO_ROOT}/.infra/metamodel/10.rules-templates/{规则ID}.template.md`（若存在）；
  - 按模板定义填充占位符（如 `{{MAIN_LANGUAGE}}`、`{{SCOPE}}`、`{{PRINCIPLES}}` 等）；
  - 若指定 `--template`，可覆盖默认模板；
  - 支持分批生成与 Token 控制。

## 阶段4：用户规则注入（可选）

- **阶段说明来源**：本 Skill 内 [references/stages/04-user-rules-injection.md](references/stages/04-user-rules-injection.md)
- **目标**：将用户自定义规则注入到规则体系中，可选进行智能融合。
- **输出**：视实现而定（通常为追加/更新 `omni-doc/rules` 或 `.cursor/rules` 中的规则）。
- **要点**：
  - 在对话模式下引导用户提供或确认自定义规则；
  - 与已生成规则做冲突检测与合并（如有定义）。

## 模式、缓存与重录

- **执行模式**：
  - 自动化模式（默认）：不带 `--interactive`；
  - 对话模式：显式指定 `--interactive`；
  - `--non-interactive` / `--yes`：强制全自动模式。
- **缓存状态文件**：`{REPO_ROOT}/.cache/reverse/rules/.cache-status.json`  
  结构包含 `features_scan`、`rule_mapping`、`rule_generation`、`user_rules_injection` 段落。
- **重录（`--clear-cache`）**：
  - 根据原文档约定，重新执行已确认阶段；
  - 在重录规则生成时，应先清理对应旧 `.mdc` 文件，避免残留。

## 参考文档（本 Skill 内）

本 Skill 的详细规范位于本目录下 `references/`：

- 阶段 1：[references/stages/01-features-scan.md](references/stages/01-features-scan.md)
- 阶段 2：[references/stages/02-rule-mapping-and-batching.md](references/stages/02-rule-mapping-and-batching.md)
- 阶段 3：[references/stages/03-rule-document-generation.md](references/stages/03-rule-document-generation.md)
- 阶段 4：[references/stages/04-user-rules-injection.md](references/stages/04-user-rules-injection.md)
- 规则类型与 Token 管理：[references/core-rules.md](references/core-rules.md)、[references/token-management.md](references/token-management.md)、[references/data.md](references/data.md)、[references/README.md](references/README.md)

执行本 Skill 时，AI Agent 应读取上述文档并按照其中描述的阶段、规则类型与模板体系执行。

