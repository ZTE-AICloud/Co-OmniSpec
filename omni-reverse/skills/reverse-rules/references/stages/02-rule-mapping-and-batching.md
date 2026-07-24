# 规则映射与分批

<!-- 阶段2：规则映射与分批 -->

## 职责

作为“规则架构师”，根据阶段1 的**代码库特征检测报告**，智能选择适用的规则，确定生成优先级与依赖关系，并为每个选中的规则生成独立的执行文件（规则生成提示）。

## 执行流程

### 0. [ ] 创建阶段2 子任务 Todo 列表

1. **步骤1** 清理上一阶段上下文
2. **步骤2** 检查缓存状态
3. **步骤3** 读取特征报告 01-features.md
4. **步骤4** 根据特征选择适用规则（P0～P4）并确定分批方案
5. **步骤5** 为每个选中规则生成 03-rule-{规则ID}.md 到缓存目录
6. **步骤6** 保存 rule-mapping.json，展示并等待用户确认
7. **步骤7** 处理用户确认，更新缓存状态

### 1. [x] 清理上一阶段上下文

- 明确说明：“开始阶段2：规则映射与分批。已清空上一阶段的上下文。”

### 2. [ ] 检查缓存状态

- 读取 `{REPO_ROOT}/.cache/reverse/rules/.cache-status.json`
- 若 `rule_mapping.confirmed == true` 且**本次未请求重录**（例如未显式使用 `--clear-cache` 且用户未在对话中要求重新执行）：跳过阶段2，使用已有 rule-mapping 与 prompts
- 若为 `false` 或不存在，或本次明确请求重录：执行阶段2，并覆盖旧的 rule-mapping 与 prompts

### 3. [ ] 读取特征报告

- 读取 `{REPO_ROOT}/.cache/reverse/rules/01-features.md`
- 确认文件存在且内容完整（尤其“主要语言”、技术栈、架构、领域特征）

### 4. [ ] 根据特征选择规则并制定分批方案

#### 规则分类（参考 flow-formal-spec 2.rules-prompt-make）

- **P0 基础规则（必选）**：00-architecture、08-style-patterns
- **P1 核心功能**：03-data-access、05-logging、07-config
- **P2 扩展功能**：01-routing-dispatch、02-state-management、04-communication
- **P3 运维工具**：09-testing、06-monitoring、10-deployment
- **P4 特化规则**：11-dsl-processing、12-protocol-stack、13-real-time、14-security-auth、15-plugin-system 等（仅在有明确代码证据时选择）

#### 选择原则

- 证据驱动：仅选择特征报告中有明确代码证据支撑的规则
- 关键词匹配：根据报告中的技术栈与关键词（如 2.rules-prompt-make 中的关键词匹配规则）选择
- 跳过无证据或与项目无关的规则，并记录跳过原因

#### 分批与依赖

- 阶段1（P0）：00-architecture、08-style-patterns，串行
- 阶段2（P1）：03、05、07，可并行
- 阶段3（P2）：01、02、04，可并行
- 阶段4（P3）：09、06、10，可并行
- 阶段5（P4）：11～15，按需、可并行

### 5. [ ] 生成规则执行文件 03-rule-{规则ID}.md

- 为每个**选中的**规则生成一份执行提示文件
- 保存路径：`{REPO_ROOT}/.cache/reverse/rules/prompts/03-rule-{规则ID}.md`
- **指定模版填充**：若用户传入 `--template <file>` 或存在项目模板 `{REPO_ROOT}/.omni-infra/templates/reverse-rule-execution-template.md`，则优先读取该模板，将占位符（如 `{RULE_ID}`、`{RULE_NAME}`、`{RULE_DESCRIPTION}`、`{GLOBS_PATTERN}`、`{ALWAYS_APPLY}` 等）替换为当前规则信息后，为每条规则生成对应的 03-rule-*.md；否则使用下述内置结构。
- 内容需包含（参考 flow-formal-spec 单规则执行模板或上述自定义模板）：
  - 任务目标：生成该规则的具体规范
  - 输出路径：`{REPO_ROOT}/omni-doc/rules/{规则ID}.mdc`
  - 当前规则信息：规则ID、名称、描述、优先级、前置依赖、关注重点、globs、alwaysApply
  - 语言约束：所有代码示例必须使用特征报告中“主要语言”，配置格式与项目一致
  - 规则结构要求：frontmatter、适用范围、核心原则、具体规范、实现指南、检查要点
  - 执行时可在文档末尾附加 01-features.md 内容供 Agent 参考

### 6. [ ] 保存映射结果并展示

- 将规则选择与分批方案保存到：`{REPO_ROOT}/.cache/reverse/rules/rule-mapping.json`
- 建议结构：适用规则列表、跳过的规则及原因、阶段划分与执行顺序、生成的文件列表
- 更新 `.cache-status.json` 中 `rule_mapping`：`confirmed: false`、`progress: "completed"`、时间戳
- **交互模式**：向用户展示适用规则清单、分批方案、将生成的 03-rule-*.md 列表，询问：“规则映射与分批方案已生成，是否确认？[Y/n]”，根据用户响应决定是否继续；用户响应后再次验证状态更新
- **全自动模式（`--non-interactive` / `--yes`）**：不再询问用户，直接视为已确认，进入下一步骤

### 7. [ ] 处理用户确认，更新缓存状态

#### 用户确认（交互模式下 Y/yes/回车，或全自动模式）

- 更新 `rule_mapping.confirmed: true` 及时间戳，写回 `.cache-status.json`
- 说明阶段2 已完成，自动进入阶段3

#### 用户拒绝（n/no）

- 允许查看详情、调整规则选择或重新执行

## 输出

- `{REPO_ROOT}/.cache/reverse/rules/rule-mapping.json`
- `{REPO_ROOT}/.cache/reverse/rules/prompts/03-rule-{规则ID}.md`（每个选中规则一份）
- `.cache-status.json` 中 `rule_mapping`

## 注意事项

- 只选择有代码证据支撑的规则；禁止捏造或推测
- 阶段2 输出为阶段3 的输入，须用户确认后再执行阶段3
- 跨平台：脚本与路径需同时支持 Linux 与 Windows
