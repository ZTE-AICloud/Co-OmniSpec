---
name: reverse-rules
description: 基于 reverse 命令编排规则与约束的反构流程。当 reverse --target 为 rules 或 all 时自动触发，扫描代码库特征、映射规则类型、生成分层结构的 .mdc 规则文档.
user-invocable: false
argument-hint: [--target rules|all] [--path path] [--exclude patterns] [--interactive]
---

# reverse-rules

## 行为准则（会话全程有效，不因对话长度放松）

以下规则在整个会话期间有效，不因对话长度而放松：

1. ❗ **阶段顺序不可跳过** — 特征检测 → 规则映射与分批 → 规则文档生成 → 用户规则注入，顺序执行。不得跳到阶段 3 再回头补阶段 2。每次输出前自检此条。
2. ❗ **缓存状态必须检查** — 每个阶段开始前必须读取 `.cache-status.json`，已确认的阶段不重复执行（除非 `--clear-cache`）。每次输出前自检此条。
3. ❗ **证据驱动，不推测** — 特征检测中所有结论必须有代码证据，不确定处标注"需进一步确认"；规则选择必须有特征报告中的代码证据。每次输出前自检此条。

**禁止行为**:
- 跳过未完成的阶段继续往下执行
- 在特征检测完成前进行规则映射
- 在规则映射完成前生成规则文档
- 忽略缓存状态文件中的 `confirmed` 字段

## 概览（职责与输入输出）

- **职责**：从代码库与既有文档中反构各类规则与约束，生成可被 AI/IDE 使用的 `.mdc` 规则文档。
- **输入前提**：
  - 用户通过 `reverse --target rules ...` 或 `--target all` 触发
  - 已根据 `--path` / `--exclude` 等参数确定扫描范围
- **输出产物**：
  - **work artifacts**（AI 执行中间产物，机器可读，不直接面向用户）：
    - 缓存目录：`{REPO_ROOT}/.cache/reverse/rules/`
      - `01-features.md`（特征报告）
      - `rule-mapping.json`（规则选择与分批方案，machine-readable JSON）
      - `prompts/03-rule-{规则ID}.md`（规则执行提示）
      - `.cache-status.json`（阶段完成状态）
  - **human-readable**（直接面向用户的最终产物）：
    - 文档目录：`{REPO_ROOT}/omni-doc/rules/`
      - 每条规则对应一份 `{规则ID}.mdc`（规则文档，供 AI/IDE 使用）

> 规则类型按优先级 P0～P4 管理，支持通用模板与规则类型专用模板。

## 与 `reverse` 命令的关系

- `reverse` 负责：
  - 解析参数（包含 `--path`、`--exclude`、`--interactive`、`--template`、`--clear-cache` 等）；
  - 初始化缓存与输出目录；
  - 在规则阶段激活本 Skill。
- 本 Skill 负责：
  - 执行特征检测、规则映射与分批、文档生成与用户规则注入；
  - 在对话模式下插入合适的确认点。

## 技能依赖

- **调用方式**：被 `reverse` 主命令通过 Agent 工具编排调用
- **调用其他 Skill**：本 Skill 作为编排器，通过读取 `references/stages/` 中的阶段文档，引导 AI Agent 分阶段执行规则反构任务，**不直接调用其他 Skill**
- **工具使用**：依赖 Claude Code 内置工具（Read、Glob、Grep 等）完成代码扫描与文档生成

## 子 Agent 委派规则（模块 7）

> 编排型 Skill 不直接执行，由 AI Agent 按阶段文档分步执行。以下约束确保各阶段 Agent 产出不重复、不矛盾。

**委派 prompt 复制原则**（不转述）:
- 每个阶段 Agent 的 prompt 必须包含本 Skill 的核心约束原文（触发条件、行为准则、输出约束），不得简化或意译

**分工边界**（"你只负责 X，不要涉及 Y"）:
- 阶段 1 Agent：只负责特征检测，输出 `01-features.md`，不涉及规则映射
- 阶段 2 Agent：只负责规则映射与分批，输出 `rule-mapping.json` 和 `prompts/03-rule-*.md`，不涉及规则生成
- 阶段 3 Agent：只负责规则文档生成，输出 `omni-doc/rules/*.mdc`，不涉及用户规则注入
- 阶段 4 Agent：只负责用户规则注入（可选），不涉及已生成规则的重新生成

**完成性约束**（"输入集共 N 项，必须全部处理"）:
- 4 个工作流阶段必须全部处理（特征检测 → 规则映射与分批 → 规则文档生成 → 用户规则注入），顺序不可跳过；规则优先级按 P0→P1→P2→P3→P4 串行生成
- 每阶段产出数量由输入决定：阶段 2 生成的 `03-rule-*.md` 数量 = 阶段 3 需要生成 .mdc 的数量

**并行约束**:
- 工作流阶段 2（规则映射与分批）内，规则优先级 P1 组（03-data-access、05-logging、07-config）、P2 组（01-routing-dispatch、02-state-management、04-communication）、P3 组（09-testing、06-monitoring、10-deployment）各自可并行，但跨 P 组必须串行
- 并行 Agent 各自只处理分配给它的规则 ID，不得触及其他 Agent 负责的规则

**合并检查清单**:
- 主 Agent 汇总阶段 3 产出时：去重（同一规则 ID 不出现两次） + 一致性（各 .mdc 均有 frontmatter 和必要章节） + Checkpoint 计数之和 == 阶段 2 选中的规则总数

## 阶段总览

对应原 `reverse-rules.md` 与 `reverse.rules/stages/*`，本 Skill 包含 4 个阶段：

1. **阶段1：特征检测**
2. **阶段2：规则映射与分批**
3. **阶段3：规则文档生成**
4. **阶段4：用户规则注入（可选）**

### 阶段间数据传递

| 传递方向 | 传递方式 | 传递内容 |
|---------|---------|---------|
| 阶段1 → 阶段2 | 缓存文件 `.cache/reverse/rules/01-features.md` | 特征报告（语言、技术栈、工程化水平等） |
| 阶段2 → 阶段3 | 缓存文件 `.cache/reverse/rules/rule-mapping.json` | 规则映射、分批方案、各规则提示文档 |
| 阶段3 → 阶段4 | 缓存文件 + 输出文件 | 已生成的 `.mdc` 规则文档列表 |
| 跨阶段持久化 | `.cache/reverse/rules/.cache-status.json` | 各阶段完成状态，支持断点续执 |

**顶层 Checkpoint 与等式验收**:

- 阶段 1 完成: `01-features.md` 文件存在且非空，`.cache-status.json` 中 `features_scan.confirmed == true`
- 阶段 2 完成: `rule-mapping.json` 存在且 `03-rule-*.md` 数量 == `rule-mapping.json` 中的规则总数，`.cache-status.json` 中 `rule_mapping.confirmed == true`
- 阶段 3 完成: `omni-doc/rules/*.mdc` 文件数 == `rule-mapping.json` 中选中的规则数，`.cache-status.json` 中 `rule_generation.confirmed == true`
- 阶段 4 完成: 缓存状态已更新，`.cache-status.json` 中 `user_rules_injection` 为 `confirmed` 或 `skipped`

**失败降级路径**:
- 缓存文件缺失 → 返回错误，不继续后续阶段
- `.cache-status.json` 损坏 → 使用 `--clear-cache` 重录
- 无用户规则文件 → 阶段 4 标记为 `skipped`，不阻塞流程

✅ Checkpoint: `reverse-rules 完成: 4 阶段全部处理, 产出 N 条 .mdc 规则`

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
  - 使用规则类型模板：`{REPO_ROOT}/.omni-infra/metamodel/10.rules-templates/{规则ID}.template.md`（若存在）；
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

## 上下文管理

### 执行模式
- **自动化模式（默认）**：不带 `--interactive`
- **对话模式**：显式指定 `--interactive`，在关键节点插入用户确认
- **强制全自动模式**：`--non-interactive` / `--yes`

### 缓存管理
- **缓存状态文件**：`{REPO_ROOT}/.cache/reverse/rules/.cache-status.json`  
  结构包含 `features_scan`、`rule_mapping`、`rule_generation`、`user_rules_injection` 段落
- **缓存策略**：每个阶段完成后更新 cache-status，标记阶段完成状态
- **重录（`--clear-cache`）**：根据缓存状态重新执行已确认阶段，重录规则生成时先清理对应旧 `.mdc` 文件

### Token 预算
详细 Token 分配与阶段间数据传递策略参见 [references/token-management.md](references/token-management.md)，以下是概要：

| 阶段 | 预估 Token | 说明 |
|------|-----------|------|
| 阶段1：特征检测 | ~15K | 扫描仓库结构，生成特征报告 |
| 阶段2：规则映射与分批 | ~10K | 规则匹配、分批规划 |
| 阶段3：规则文档生成 | ~50K | 分批生成 .mdc 文档（主消耗） |
| 阶段4：用户规则注入 | ~10K | 冲突检测与融合 |
| **合计** | **~85K** | - |

> 如接近预算上限，优先保证阶段1和阶段3的输出质量，降低阶段2和阶段4的详细程度。

## 使用示例

### 基本用法（自动化模式）
```
reverse --target rules --path ./src
```
扫描 `./src` 目录，生成全量规则 .mdc 文档。

### 对话模式（交互确认）
```
reverse --target rules --path ./src --interactive
```
在规则映射完成后暂停，向用户确认规则集合与执行范围。

### 部分规则生成
```
reverse --target rules --path ./src --interactive
# 选择 P0～P1 规则后确认，跳过 P2～P4
```

### 增量更新
```
# 不带 --clear-cache 时，已完成的阶段会被跳过
reverse --target rules --path ./src
```
只执行缓存中未完成的阶段。

## 参考文档

本 Skill 的详细规范位于 `references/` 目录下：

### 阶段实现文档
- 阶段1（特征检测）：[references/stages/01-features-scan.md](references/stages/01-features-scan.md)
- 阶段2（规则映射与分批）：[references/stages/02-rule-mapping-and-batching.md](references/stages/02-rule-mapping-and-batching.md)
- 阶段3（规则文档生成）：[references/stages/03-rule-document-generation.md](references/stages/03-rule-document-generation.md)
- 阶段4（用户规则注入）：[references/stages/04-user-rules-injection.md](references/stages/04-user-rules-injection.md)

### 核心规则与数据规范
- 规则类型定义：[references/core-rules.md](references/core-rules.md)
- Token 管理策略：[references/token-management.md](references/token-management.md)
- 数据格式规范：[references/data.md](references/data.md)
- 总体说明：[references/README.md](references/README.md)

> 执行本 Skill 时，AI Agent 应读取上述文档并按照其中描述的阶段、规则类型与模板体系执行。

