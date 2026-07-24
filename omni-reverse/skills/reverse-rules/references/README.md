## `reverse.rules` 规则反构说明（配合 `reverse --target rules` 使用）

本目录下文件定义了 **rules（规则/约束）反构** 的全部行为，包括阶段拆分、缓存管理、分批规则以及模板使用方式。

### 1. 入口命令关系

- 主入口：命令 `reverse`（`claude/commands/reverse.md`），`--target rules` 时调用 Skill `omni-reverse:reverse-rules`
- rules 编排与阶段说明：本 Skill 的 `SKILL.md` 及 `references/` 下文档
- 规则反构实现目录：`本 Skill（reverse-rules）的 references/`
  - `core-rules.md`：分批/Token/阶段定位等核心规则
  - `data.md`：缓存与数据交换约定
  - `stages/01-04-*.md`：四个阶段的详细执行指引

建议：在 `reverse.md` 里只看总体入口和参数；**rules 的详细说明以本目录下文件为准**。

### 2. 四个阶段概览

1. **阶段1：特征检测**（`stages/01-features-scan.md`）  
   - 扫描代码库结构、语言、技术栈、工程化水平等，输出 `01-features.md`。
2. **阶段2：规则映射与分批**（`stages/02-rule-mapping-and-batching.md`）  
   - 根据 `01-features.md` 智能选择适用规则类型（P0～P4），输出 `rule-mapping.json` 与 `03-rule-{规则ID}.md`。
3. **阶段3：规则文档生成**（`stages/03-rule-document-generation.md`）  
   - 结合规则执行提示与模板，生成最终规则文档 `omni-doc/rules/{规则ID}.mdc`；支持按规则类型模板填充。
4. **阶段4：用户规则注入**（`stages/04-user-rules-injection.md`，可选）  
   - 注入用户自定义规则，并可选做智能融合。

### 3. 支持的规则类型

详见本 Skill 的 `SKILL.md` 及 `references/core-rules.md` 中「支持的规则类型」一节，这里只列出 ID：

- **P0 基础规则**：`00-architecture`、`08-style-patterns`
- **P1 核心功能**：`03-data-access`、`05-logging`、`07-config`
- **P2 扩展功能**：`01-routing-dispatch`、`02-state-management`、`04-communication`
- **P3 运维工具**：`09-testing`、`06-monitoring`、`10-deployment`
- **P4 特化规则**：`11-dsl-processing`、`12-protocol-stack`、`13-real-time`、`14-security-auth`、`15-plugin-system`

### 4. 模板体系（rules 特有）

#### 4.1 规则执行模板（生成 03-rule-*.md）

- 作用：控制每条规则的「大模型执行 Prompt」，即 `03-rule-{规则ID}.md` 的结构。
- 配置方式：
  - 命令参数：`--template <file>`
  - 未指定时，按本 Skill 的 `references/` 中描述的默认结构生成。

#### 4.2 按规则类型的输出模板（生成最终 .mdc）

- 模板目录（在用户项目中）：  
  ` {REPO_ROOT}/.omni-infra/metamodel/10.rules-templates/{规则ID}.template.md`
- 每个规则类型**一个模板文件**（如 `00-architecture.template.md`、`05-logging.template.md`），用于阶段3 生成最终 `.mdc`：
  1. 阶段3 读取对应规则 ID 的模板；
  2. 结合 `01-features.md` 和代码分析结果，填充模板中的占位符（如 `{{MAIN_LANGUAGE}}`、`{{SCOPE}}`、`{{PRINCIPLES}}` 等）；
  3. 输出到 `omni-doc/rules/{规则ID}.mdc`。
- 若某规则类型无单独模板，则回退到通用模板或内置默认结构（frontmatter + 适用范围、核心原则、具体规范、实现指南、检查要点）。

模板占位符的详细列表，见：  
`本 Skill（reverse-rules）的 references/data.md` 与  
`omni-infra/metamodel/10.rules-templates/README.md`。

### 5. 默认行为与注意事项（rules）

- **默认模式**：全自动（不传 `--interactive` 时）；所有阶段的「是否确认？」按已确认处理，自动顺序跑完 1～4 阶段。
- **默认执行目标**：在 `reverse` 中，不传 `--target` 时默认按 `all` 执行，其中已实现的部分包含 `interfaces` → `rules`。
- **重录/多次执行**：  
  - 使用 `--clear-cache` 或在对话中明确要求重跑时，已确认阶段也会重新执行；  
  - 阶段3 在重录时会先删除对应规则的旧 `.mdc` 文档，再重新生成。
- **默认排除路径**：  
  - 所有 target：默认排除隐藏目录（如 `.git/`、`.idea/`、`.vscode/` 等）；  
  - `rules`：额外默认排除仓库根目录下的 `omni-doc/`，避免把已生成文档当成源码再次扫描。

更多细节（如分批策略、Token 管理）请参考本目录下的 `core-rules.md`、`token-management.md` 与各阶段文件。

