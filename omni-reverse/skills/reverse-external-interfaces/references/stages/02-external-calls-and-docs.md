# 阶段2：外部调用与文档生成

<!-- 阶段2：仅保留在代码库有调用示例的外部接口，并生成 EXTERNAL-API_xxx.md -->

> **前置依赖**：本阶段依赖 `.omni-infra/metamodel/9.external-interface-template.md` 作为文档格式模板。如该文件不存在，使用简化格式输出。

## 职责

1. 读取阶段1 输出的 `import-list.json`，筛选 `classification === "external"` 的符号。
2. 对每个外部符号，在代码库中检索**调用点**（使用处）；仅保留**至少有一处调用**的符号。
3. 为每个“有调用的外部接口”生成一份 `EXTERNAL-API_{三位序号}_{简短描述}.md`，并生成 `EXTERNAL-API_SUMMARY.json`。
4. 输出目录：`{REPO_ROOT}/omni-doc/specs/external-interfaces/`。

## 执行流程

### 0. [ ] 创建阶段2 的 Todo 子项

1. 清理阶段1 中与阶段2 无关的上下文
2. 检查缓存：若 `document_generation.confirmed == true` 且输出目录已有完整结果，可跳过
3. 读取 import-list.json，取 external 列表
4. 对每个 external 符号检索调用点
5. 过滤：仅保留有 ≥1 个调用点的符号，得到「待生成接口清单」
5.5 对话模式下：展示待生成清单，支持用户增删改查，用户确认后再生成实际接口文件
6. 为每个保留项分配序号（001, 002, …）并生成 .md 文档
6.5 对话模式下：单接口文档生成后、汇总文件生成前，请用户确认
7. 生成 EXTERNAL-API_SUMMARY.json
8. 展示结果并按运行模式处理确认

**等式验收**：
- 步骤 5 完成后：待生成清单长度 == external 符号数 - 无调用点排除数
- 步骤 6 完成后：生成的 EXTERNAL-API_*.md 文件数 == 待生成清单长度
- 步骤 7 完成后：`EXTERNAL-API_SUMMARY.json` 中 `generated_files` 长度 == 生成的 .md 文件数
- 步骤 7 完成后：`stats.generated + stats.excluded == 阶段1 external 总数`（重录场景下允许 `total` 等于本次参与过滤的数）

### 1. 清理上下文

- 说明：“开始阶段2：外部调用与文档生成。已清空阶段1 的冗余上下文。”
- 只保留 import-list.json 的 external 列表及本阶段输出。

### 2. 检查缓存与重录

- 读取 `{REPO_ROOT}/.cache/reverse/external-interfaces/.cache-status.json`
- 若 `document_generation.confirmed == true` 且**本次未请求重录**（未显式使用 `--clear-cache` 且用户未在对话中要求重新执行）：可跳过阶段2，直接进入展示/确认步骤（若文档要求）。
- 若为 `false` 或不存在，或本次明确请求重录：执行阶段2。
- **重录时**：在开始生成前，**先删除** `{REPO_ROOT}/omni-doc/specs/external-interfaces/` 下已有的 `EXTERNAL-API_*.md` 与 `EXTERNAL-API_SUMMARY.json`，再重新生成，避免残留旧版本。

### 3. 读取 import-list.json，取 external 列表

- 读取 `{REPO_ROOT}/.cache/reverse/external-interfaces/import-list.json`
- 筛选 `imports` 中 `classification === "external"` 的项，得到候选外部符号列表（含 symbol、module_or_header、source_file、language）。

### 4. 对每个 external 符号检索调用点

- **检索范围**：与阶段1 一致，应用 `--exclude` 及默认排除（隐藏目录、`omni-doc/`）；仅在未排除的文件/目录中检索调用点。
- 对每个候选外部符号：
  - 在代码库内（排除后）搜索该符号的**使用处**（调用、引用），例如：
    - 函数/方法调用：通过 grep、codebase_search 查找符号名、方法名、类名等；
    - 若为类/模块，可搜索其实例化、方法调用、静态调用等。
  - 记录找到的调用点：文件路径、行号（可选）、简短上下文（调用链或调用方式）。
- 若某符号在代码库中**未找到任何调用点**，从“待生成文档”列表中排除（不生成 EXTERNAL-API_xxx.md）。

### 5. 过滤：仅保留有 ≥1 个调用点的符号

- 得到「待生成接口清单」：仅包含“在代码库中找到至少一处调用”的外部接口，每条含 symbol、来源模块、调用点摘要、所在文件等。
- 按一定顺序排列（如按 symbol 或 source_file），便于后续序号与展示。

### 5.5 待生成清单的增删改查与确认（仅对话模式）

- **对话模式（`--interactive`）**：在**生成实际接口文件（EXTERNAL-API_xxx.md）之前**，必须先向用户展示上述「待生成接口清单」（序号/符号/来源/典型调用点等），并支持用户对清单进行**增删改查**，用户确认后再继续执行步骤 6。
  - **查**：用户可查看某条或全部条目的详情（符号、模块、调用点列表、所在文件等），或询问某条是否应保留。
  - **删**：用户可指定从清单中移除若干条（如“去掉第 3、5 条”或“去掉某某符号”），更新后的清单不再包含这些项。
  - **改**：用户可要求修改某条的描述、归类或合并/拆分（如修改简短描述、合并两条为一条），按用户意图更新清单内容后再进入确认。
  - **增**：用户可补充遗漏的外部接口（需提供符号或来源模块等信息），将新项加入待生成清单（若需调用点信息，可说明“待生成文档时再根据代码推断”）。
  - 每次增删改后，可再次展示更新后的清单并询问：“是否还有需要增删改查的？确认按当前清单生成接口文件请回复 Y，否则请说明要做的修改。”
  - **确认**：当用户明确表示“确认”“按当前清单生成”“Y”等后，将当前清单固化为步骤 6 的输入，再执行步骤 6 生成 EXTERNAL-API_xxx.md；未确认前不生成任何接口文件。
- **全自动模式（默认或 `--non-interactive` / `--yes`）**：不展示增删改查环节，直接以步骤 5 的清单作为输入执行步骤 6。

### 6. 为每个保留项分配序号并生成 .md 文档

- **序号**：001, 002, 003, …（三位数字，前导零）。
- **文件名**：`EXTERNAL-API_{序号}_{简短描述}.md`
  - 简短描述：中文或英文，概括该外部接口用途（如 “PropertyHelper默认助手接口”、“HttpClient_doGet接口”），文件名中避免特殊字符。
- **目录**：`{REPO_ROOT}/omni-doc/specs/external-interfaces/`
- **单文件内容格式**（推荐做法，模板外置）：
  1. **读取模板**：在生成每个 `EXTERNAL-API_{序号}_{简短描述}.md` 前，从仓库根相对路径读取 **`.omni-infra/metamodel/9.external-interface-template.md`**，作为唯一格式规范来源（不在本阶段文件中内嵌模板内容）。
  2. **解析模板**：解析该文件的 YAML frontmatter（`id`、`name`、`file`、`type`、`description`）与正文结构（`## 接口说明` 下的 `### 接口描述`、`### 接口入口标识`、`### 接口参数`、`### 波及调用链`）。
  3. **填充并输出**：用当前外部接口的实际信息替换模板中的占位符（如将 `EXTERNAL-API-XXX` 换为 `EXTERNAL-API-001`，将接口描述、入口标识、参数表、调用链等替换为根据代码与调用点归纳出的内容），写出到 `{REPO_ROOT}/omni-doc/specs/external-interfaces/EXTERNAL-API_{序号}_{简短描述}.md`。
  4. **内容归纳**：接口描述、接口入口标识、接口参数、波及调用链等字段可根据代码与调用点由大模型归纳填写；若无法推断参数，可标“未知”或省略表格行。
- 可分批生成文档以控制单次 Token（例如每次处理 5～10 个接口）。

### 6.5 生成汇总文件前的确认（仅对话模式）

- **对话模式（`--interactive`）**：单接口文档（EXTERNAL-API_001～N.md）全部生成后，**必须先暂停**，向用户展示已生成的文件数量与文件名列表（或代表性示例），并询问：“单接口文档已全部生成，是否确认并生成汇总文件 EXTERNAL-API_SUMMARY.json？[Y/n]”。仅在用户回复 Y/yes/回车 后，才执行步骤 7 生成 EXTERNAL-API_SUMMARY.json；若用户回复 n/no，则不再生成汇总文件，允许用户查看或调整单接口文档后再决定是否继续。
- **全自动模式（默认或 `--non-interactive` / `--yes`）**：不暂停，直接执行步骤 7 生成 EXTERNAL-API_SUMMARY.json。

### 7. 生成 EXTERNAL-API_SUMMARY.json

- 路径：`{REPO_ROOT}/omni-doc/specs/external-interfaces/EXTERNAL-API_SUMMARY.json`
- 建议结构（与参考项目一致）：

```json
{
  "stats": {
    "total": 54,
    "generated": 54,
    "excluded": 70,
    "errors": 0
  },
  "generated_files": [
    "{REPO_ROOT}/omni-doc/specs/external-interfaces/EXTERNAL-API_001_PropertyHelper默认助手接口.md",
    "..."
  ]
}
```

- `total`：阶段1 中 external 总数（或本阶段参与过滤的总数）；`generated`：实际生成文档数；`excluded`：因无调用点而排除的数量；`errors`：生成失败数（如有）。
- `generated_files`：生成的 .md 的绝对路径或相对路径列表。

### 8. 展示结果并按运行模式处理确认

- 展示：生成文件数量、EXTERNAL-API_SUMMARY.json 中的 stats、部分生成文件名示例。
- **对话模式（`--interactive`）**：询问用户：“外部依赖接口文档已生成，是否确认结果？[Y/n]”，根据用户响应更新状态；用户确认后更新 `document_generation.confirmed: true` 及时间戳，写回 `.cache-status.json`。
- **全自动模式（默认或 `--non-interactive` / `--yes`）**：不再询问，直接视为已确认，更新 `document_generation.confirmed: true` 及时间戳，写回 `.cache-status.json`。
- 用户拒绝（n/no）时：允许查看详情或重新生成。

## 输出

- **单接口文档**：`{REPO_ROOT}/omni-doc/specs/external-interfaces/EXTERNAL-API_{001..N}_{简短描述}.md`
- **汇总**：`{REPO_ROOT}/omni-doc/specs/external-interfaces/EXTERNAL-API_SUMMARY.json`

**等式验收**：
- `EXTERNAL-API_SUMMARY.json` 中 `generated_files` 长度 == 生成的 .md 文件总数
- `stats.generated + stats.excluded == 阶段1 external 总数`（或本次参与过滤的 external 数）

## 注意事项

- 只对“在代码库中找到至少一处调用”的外部符号生成文档。
- **对话模式**下，步骤 6 用于生成文件的清单以步骤 5.5 用户确认后的清单为准（可能经过增删改查）；未确认前不生成任何接口文件。
- 单接口文档的内容格式以 **`.omni-infra/metamodel/9.external-interface-template.md`** 为准，生成时从该模板读取并填充，不在此阶段文件中内嵌模板。
- 所有与用户交互使用中文。
- 若外部接口数量很大，可分批生成并控制每批数量，避免单轮 Token 超限。
