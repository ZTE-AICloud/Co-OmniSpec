# 规则文档生成

<!-- 阶段3：规则文档生成 -->

## 职责

按阶段2 生成的规则执行文件（03-rule-*.md）和优先级/依赖顺序，逐批执行规则生成，将每条规则还原为 `.mdc` 文档并保存到 `omni-doc/rules/`。

## 执行流程

### 0. [ ] 创建阶段3 子任务 Todo 列表

1. **步骤1** 清理上一阶段上下文
2. **步骤2** 检查缓存状态
3. **步骤3** 读取 rule-mapping 与 prompts 列表
4. **步骤4** 按阶段/批次执行 03-rule-*.md（每批执行前可附加 01-features.md）
5. **步骤5** 将生成的规则保存到 omni-doc/rules/{规则ID}.mdc
6. **步骤6** 展示结果并等待用户确认
7. **步骤7** 处理用户确认，更新缓存状态

### 1. [x] 清理上一阶段上下文

- 明确说明：“开始阶段3：规则文档生成。已清空上一阶段的上下文。”
- 批次间清理：每批开始前清理上一批次的规则内容上下文

### 2. [ ] 检查缓存状态

- 读取 `{REPO_ROOT}/.cache/reverse/rules/.cache-status.json`
- 若 `rule_generation.confirmed == true` 且**本次未请求重录**（例如未显式使用 `--clear-cache` 且用户未在对话中要求重新执行）：跳过阶段3，直接进入用户确认步骤（若文档要求）
- 若为 `false` 或不存在，或本次明确请求重录：执行阶段3；在开始生成前，**需要先删除本次要生成的规则对应的旧结果文档**（通常是 `{REPO_ROOT}/omni-doc/rules/` 下已有的同名 `.mdc` 文件），然后再重新生成，确保重录不会残留旧版本

### 3. [ ] 读取规则映射与执行文件列表

- 读取 `{REPO_ROOT}/.cache/reverse/rules/rule-mapping.json`
- 列出 `{REPO_ROOT}/.cache/reverse/rules/prompts/` 下所有 `03-rule-*.md`，按优先级/依赖排序（P0 → P1 → P2 → P3 → P4）

### 4. [ ] 按批次执行规则生成

#### 执行顺序

- 严格按规则优先级顺序生成：P0 → P1 → P2 → P3 → P4（同优先级组内可并行，跨优先级必须串行）
- 同阶段内可并行时，可一次处理多份 03-rule-*.md（建议每批不超过 5 个以控制 Token）

#### 单规则执行步骤

1. 确定当前规则 ID（如 `00-architecture`、`05-logging`）。
2. **按类型加载模板（推荐）**：优先读取 `{REPO_ROOT}/.omni-infra/templates/default/reverse-rules-templates/{规则ID}.template.md`；若存在，则根据 `01-features.md` 与代码库实际情况填充模板中的占位符（如 `{{MAIN_LANGUAGE}}`、`{{SCOPE}}`、`{{PRINCIPLES}}`、`{{SPECIFICATIONS}}` 等，详见 data.md），直接得到该规则的 .mdc 内容；若不存在，继续下一步。
3. 若无按类型模板：读取该规则的 `03-rule-{规则ID}.md`，可选将 `01-features.md` 附加到提示末尾，由 AI Agent 生成完整规则内容（YAML frontmatter + Markdown 正文）；或使用通用模板 `reverse-rule-output-template.md` 按占位符填充。
4. 保存到：`{REPO_ROOT}/omni-doc/rules/{规则ID}.mdc`；若目录不存在，先创建：`mkdir -p {REPO_ROOT}/omni-doc/rules`。

#### 质量要求与按类型模板填充

- **每个类型一个模板**：每个规则类型对应一个模板文件，位于 `{REPO_ROOT}/.omni-infra/templates/default/reverse-rules-templates/{规则ID}.template.md`，模板内使用占位符（如 `{{RULE_ID}}`、`{{MAIN_LANGUAGE}}`、`{{SCOPE}}`、`{{PRINCIPLES}}`、`{{SPECIFICATIONS}}`、`{{IMPLEMENTATION_GUIDE}}`、`{{CHECKLIST}}` 等），由 Agent 根据代码库实际情况填充后得到最终 .mdc。
- **兜底**：若不存在按类型模板，则使用通用规则输出模板或内置结构（frontmatter + 适用范围、核心原则、具体规范、实现指南、检查要点）。
- 代码示例必须使用特征报告中的“主要语言”；配置文件示例与项目实际格式一致。

#### Token 与上下文

- 单批处理前评估 Token；超过安全限制则缩小批次或分多批
- 每批完成后清理该批规则内容，避免上下文累积

### 5. [ ] 结果汇总

- 统计已生成的 `.mdc` 文件数量与列表
- 可选：简单校验每个文件是否包含 frontmatter 与必要章节

### 6. [ ] 展示结果并等待用户确认

- **交互模式**：展示已生成规则数量、按优先级/类型的分布、代表性规则列表，询问：“规则文档已生成，是否确认？[Y/n]”；仅当用户确认后才更新状态并进入阶段4
- **全自动模式（`--non-interactive` / `--yes`）**：不再询问用户，直接视为已确认，更新状态并进入阶段4

### 7. [ ] 处理用户确认，更新缓存状态

#### 用户确认（交互模式下 Y/yes/回车，或全自动模式）

- 更新 `rule_generation.confirmed: true` 及时间戳，写回 `.cache-status.json`
- 说明阶段3 已完成，自动进入阶段4（用户规则注入）

#### 用户拒绝（n/no）

- 允许查看详情、重新生成部分规则或手动修改 .mdc

## 输出

- `{REPO_ROOT}/omni-doc/rules/{规则ID}.mdc`（每个选中的规则一份）
- `.cache-status.json` 中 `rule_generation`

## 注意事项

- 必须按阶段2 的依赖顺序执行，不得跳过未生成的规则
- 所有代码与配置示例必须与 01-features 中的“主要语言”和项目实际一致
- 跨平台：路径与脚本需支持 Linux 与 Windows
