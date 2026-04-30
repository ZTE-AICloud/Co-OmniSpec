---
name: constitution
description: 执行项目章程的创建或更新流程：填充 .infra/memory/constitution.md 占位符并同步依赖模板。由 `/constitution` 调用本 skill（与技能名同名）。
argument-hint: "[原则描述或修订说明]"
---

# 项目章程创建与更新

## 用户输入

```text
$ARGUMENTS
```

在继续之前, 你**必须**考虑用户的消息内容(如果不为空).

## 概述

更新位于 `.infra/memory/constitution.md` 的项目章程。该文件为带方括号占位符的模板（如 `[PROJECT_NAME]`、`[PRINCIPLE_1_NAME]`）。任务为：(a) 收集/推导具体值；(b) 精确填充模板；(c) 将修改传播到相关依赖项。

**始终操作现有的 `.infra/memory/constitution.md`，不要创建新文件。**

## 执行流程

### 0. 前置检查：章程是否已存在

读取 `.infra/memory/constitution.md`：
- **如果文件存在且无未填写的 `[ALL_CAPS_IDENTIFIER]` 占位符**：输出 "章程已存在，跳过创建。" 并**立即结束**，不执行后续步骤。
- **如果文件不存在或仍有占位符**：继续执行以下步骤。

### 1. 加载章程模板

- 读取 `.infra/memory/constitution.md`，识别所有 `[ALL_CAPS_IDENTIFIER]` 占位符。
- **原则数量与模板不一致时**：
    - 原则减少：删除对应的 `[PRINCIPLE_N_NAME]` 与 `[PRINCIPLE_N_DESCRIPTION]` 章节。
    - 原则增加：按模板格式新增原则章节。

### 2. 收集/推导占位符值

- 用户输入优先；其次按模板内「填写方式」从参考文档或项目推断。
- **治理日期**：`RATIFICATION_DATE` 为原始采用日（未知则询问或标 TODO）；`LAST_AMENDED_DATE` 若有修改则为今天，否则保留原值。
- **版本 `CONSTITUTION_VERSION`**（语义化版本）：
    - **MAJOR**：原则删除或重新定义等不兼容变更。
    - **MINOR**：新增原则/章节或实质性扩展。
    - **PATCH**：措辞澄清、拼写修正、非语义优化。
- 若版本类型不明确，在定稿前给出理由。

### 3. 起草更新内容

- 用具体文本替换每个占位符；故意保留的槽位需明确说明。
- 保留标题层级；除步骤 5 的同步影响报告注释外，删除其余 HTML 注释。
- 每个原则：简短名称、不可协商规则段落（或列表）、必要时给出理由。
- 治理部分需包含修改程序、版本策略与合规审查期望。

### 4. 一致性传播检查

- 读 `.infra/templates/design-template.md`，确保「章程检查」与更新后原则一致。
- 读 `.infra/templates/tasks-template.md`，确保任务分类反映原则（如可观测性、版本控制、测试纪律）。
- 读 `.infra/templates/spec-template.md`，做范围/需求对齐；章程若增删强制部分或约束则同步更新。
- 读 README、docs、代理指导等，更新对已变更原则的引用。

### 5. 生成同步影响报告

在更新后的章程**文件顶部**以 HTML 注释形式插入：

- 版本变更：旧版本 → 新版本
- 修改的原则列表（若有重命名：旧标题 → 新标题）
- 新增/删除的章节
- 需更新的模板（✅ 已更新 / ⚠ 待处理）及路径
- 若有故意延后的占位符，列出后续 TODO

### 6. 最终验证

- 无未解释的括号占位符。
- 版本行与报告一致。
- 日期为 ISO 格式 YYYY-MM-DD。
- 原则为声明式、可检验，避免模糊用语（用 MUST/SHOULD 及理由替代 "should"）。

### 7. 写回文件

将完成的章程写回 `.infra/memory/constitution.md`（覆盖）。

### 8. 输出摘要

向用户提供：

- 新版本及递增理由。
- 标记为需人工跟进的文件。
- 建议提交信息（如：`docs: amend constitution to vX.Y.Z (principle additions + governance update)`）。

## 格式与样式

- 严格按模板使用 Markdown 标题层级；章节间保留一个空行；避免行尾空格。
- 用户仅提供部分更新（如单条原则修订）时，仍执行完整验证与版本决策。

## 缺失信息处理

若关键信息缺失（如批准日期未知），在正文中插入 `TODO(<FIELD_NAME>): explanation`，并在同步影响报告的「延迟项」中列出。
