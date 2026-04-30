# 阶段2：需求拆分（功能需求 → 独立需求文件）

<!-- 阶段2：将需求设计文档中的功能需求拆分为 omni-doc/specs/requirements 下的独立文件 -->

## 职责

1. 读取需求设计文档中的「功能需求」章节。
2. 识别每条主需求及其子需求（EARS 子句）。
3. 为每条主需求分配编号并生成需求简述。
4. 按项目约定命名与内容格式，在 `omni-doc/specs/requirements/` 下生成独立需求文件。

## 输入

- **需求设计文档**：`{REPO_ROOT}/.cache/reverse/requirements/internal/需求设计.md`
- 若不存在则回退：同目录下 `设计文档.md`（仅使用其中功能需求章节）

## 输出

- **输出目录**：`{REPO_ROOT}/omni-doc/specs/requirements/`
- **文件命名格式**：`{ID_PREFIX}-XXX-需求简述.md`
  - `ID_PREFIX`：与项目现有 `omni-doc/specs/requirements` 下文件一致（如 `REQ` 或 `INTENT`）
  - `XXX`：三位数字，从 001 起连续
  - `需求简述`：简短描述，建议不超过 20 字，中文，无标点

## 文件内容格式

**不在此处写死模板**。生成每个需求文件时：

1. **读取模板**：从 **`.infra/metamodel/1.requirement-template.md`** 读取格式定义（frontmatter 字段与正文结构）。
2. **按模板填充**：将当前需求的 id、name、type、description 及 EARS 主需求/子需求填入模板对应位置后写出。

若运行环境为安装后的目标项目，模板路径为 **`.infra/metamodel/1.requirement-template.md`**（安装时 OmniSpec 的 `infra/` 等资源落在目标仓库的 `.infra/` 下）。

## 需求识别规则

### 主需求识别

- 带功能域：`- [功能域名称] 系统 shall 提供XX功能` 或 `- [功能域] 系统 shall ...`
- 不带功能域：`- 系统 shall 提供XX功能`
- 编号列表：`1. 系统 shall ...`

### 子需求归属

- 子需求通常有缩进，归属到紧邻其上的主需求
- EARS 子句：`When ...`、`While ...`、`If ...`、`Where ...` 均保留在主需求下

## 需求简述生成规则

1. **优先使用功能域**：主需求有 `[功能域]` 时，简述以功能域开头
2. **提取核心动作**：从 `shall` 后提取主要动作或功能
3. **简洁**：总长度建议不超过 20 字
4. **去标点**：文件名中去除句号、逗号等
5. **中文**：与项目 omni-doc/specs/requirements 命名风格一致

**示例**：

| 需求内容 | 简述示例 |
|---------|----------|
| `[计费管理] 系统 shall 提供话单计费功能` | `计费管理-话单计费` |
| `[会话管理] 系统 shall 提供会话生命周期管理功能` | `会话管理-生命周期管理` |
| `系统 shall 支持并发处理` | `并发处理` |

## 执行流程

### 0. [ ] 创建阶段2 的 Todo 子项

1. 检查缓存：若 `requirement_split.confirmed == true` 且**未使用 --clear-cache**，可跳过阶段2
2. 获取 REPO_ROOT、REQUIREMENTS_OUTPUT_DIR、ID_PREFIX（见 data.md 或项目配置）
3. 读取需求设计文档，定位「功能需求」章节
4. 识别主需求与子需求，分配编号（001 起）
5. 为每条生成需求简述
6. **交互模式**（可选）：展示待生成清单，支持用户增删改查，确认后再生成文件
7. 确保输出目录存在；若重录则先删除已有 `{ID_PREFIX}-*.md` 再生成
8. 逐条写入 `{ID_PREFIX}-XXX-需求简述.md`
9. 创建 `{REPO_ROOT}/.cache/reverse/requirements/internal/requirement_split_success.flag`（可选）
10. 更新缓存状态；交互模式下可再次确认后结束

### 1. 解析参数与检查缓存

- 从 `$ARGUMENTS` 解析：`--clear-cache`、`--interactive`。若带 `--clear-cache` 或用户要求重录，则忽略 `requirement_split.confirmed`，执行本阶段；且在生成文件前先删除输出目录下已有 `{ID_PREFIX}-*.md`（及可选 SUMMARY），再重新生成。

### 2. 确定 ID_PREFIX 与输出目录

- 若项目 `omni-doc/specs/requirements/` 下已有文件，沿用其前缀（如 `INTENT`、`REQ`）
- 否则默认使用 `REQ`
- 输出目录：`{REPO_ROOT}/omni-doc/specs/requirements/`（独立需求文件）；需求设计文档与 success 标记在 `{REPO_ROOT}/.cache/reverse/requirements/internal/`，执行前 `mkdir -p`

### 3. 读取并定位功能需求（依赖缺失则中止，不继续生成）

- 读取 `{REPO_ROOT}/.cache/reverse/requirements/internal/需求设计.md`（若不存在则尝试同目录下 `设计文档.md`）。
- 若文件不存在：**中止阶段2**，不生成任何 `{ID_PREFIX}-XXX-*.md`；用中文提示：「缺少需求设计文档，无法拆分需求。请先执行阶段1 生成功能需求章节后再执行阶段2。」
- 定位 `## 功能需求` 或 `# 功能需求`，提取该章节下全部内容。
- 若该章节不存在或内容为空：**中止阶段2**，不生成任何需求文件；用中文提示：「需求设计文档中未找到功能需求章节或内容为空，请先完成阶段1 或补充功能需求后再执行阶段2。」

### 4. 拆分与编号

- 按主需求识别规则切分，每条主需求及其子需求为一个单元
- 编号从 001 起连续递增

### 5. 生成文件

- 对每条需求：按 `.infra/metamodel/1.requirement-template.md` 格式写入 `{REPO_ROOT}/omni-doc/specs/requirements/{ID_PREFIX}-XXX-需求简述.md`（先写 YAML frontmatter，再写 EARS 正文）
- 重录时：先删除该目录下已有 `{ID_PREFIX}-*.md`（及可选 SUMMARY 文件），再生成

### 6. 成功标记与状态

- 全部完成后创建 `{REPO_ROOT}/.cache/reverse/requirements/internal/requirement_split_success.flag`
- 将 `requirement_split.progress` 置为 `completed`，`requirement_split.confirmed` 置为 `true`

## 质量检查

- [ ] 所有主需求已拆分为独立文件
- [ ] 文件命名符合 `{ID_PREFIX}-XXX-需求简述.md`
- [ ] 文件内容遵循 1.requirement-template.md：含 YAML frontmatter（id、name、type、description）及 EARS 正文
- [ ] 编号连续无遗漏
- [ ] 需求简述简洁准确，子需求归属正确
- [ ] 已创建成功标记文件（若约定需要）
