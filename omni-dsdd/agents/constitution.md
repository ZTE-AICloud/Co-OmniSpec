---
name: constitution
description: 执行项目章程的创建或更新流程：填充 .omni-infra/memory/constitution.md 占位符并同步依赖模板。
argument-hint: "[原则描述或修订说明]"
allowed-tools: Read, Write, Edit, Bash(test, mkdir), Task, Agent(knowledge-retrieval-agent)
---

# 项目章程创建与更新

## 用户输入

```text
$ARGUMENTS
```

在继续之前, 你**必须**考虑用户的消息内容(如果不为空).

---

## 环境初始化

本技能**所有**读写路径均基于以下变量。后续步骤不得用裸相对路径 `.omni-infra/...` 绕过它们。

| 变量 | 含义 | 用途 |
|------|------|------|
| `CLAUDE_PLUGIN_ROOT` | Omni 插件安装根目录 | 定位插件内 `omni-infra/` 种子、`init_omni_infra.sh` 等 |
| `CLAUDE_WORKING_DIR` | 用户当前工作区目录（可为 Git 仓库子目录） | 定位工作区 `.omni-infra/` 下章程与模板 |
| `KNOWLEDGE_DIR` | 私域知识库根目录（私域知识检索用，与反构文档库独立） | 定位知识源目录与 `knowledge.config.yaml`；由 Step 0.2 解析（读 `.omni-infra/knowledge.path`，缺失回退 `omni-doc`） |

### 工作区路径约定（全文统一使用）

| 符号 | 展开路径 |
|------|----------|
| 章程文件 | `${CLAUDE_WORKING_DIR}/.omni-infra/memory/constitution.md` |
| 设计模板 | `${CLAUDE_WORKING_DIR}/.omni-infra/templates/design-template.md` |
| 任务模板 | `${CLAUDE_WORKING_DIR}/.omni-infra/templates/tasks-template.md` |
| 规范模板 | `${CLAUDE_WORKING_DIR}/.omni-infra/templates/spec-template.md` |
| 知识库路径标记 | `${CLAUDE_WORKING_DIR}/.omni-infra/knowledge.path`（init 脚本写入的生效 `KNOWLEDGE_DIR` 绝对路径，constitution 读取） |
| 知识源检查路径 | `${KNOWLEDGE_DIR}`（读 `knowledge.path`；缺失回退 `${CLAUDE_WORKING_DIR}/omni-doc`） |
| 知识检索配置 | `${KNOWLEDGE_DIR}/knowledge.config.yaml`（由 sdd 初始化脚本 `init_omni_infra.sh` 生成，非本技能职责） |
| 插件 omni-infra 种子 | `${CLAUDE_PLUGIN_ROOT}/omni-infra/`（仅 `.omni-infra` 尚未存在时参考） |
| 插件 knowledge 配置模板 | `${CLAUDE_PLUGIN_ROOT}/skills/knowledge-retrieval/knowledge.config.yaml`（`init_omni_infra.sh` 拷贝源） |

### Step 0.1 检查变量是否已存在

```bash
test -n "${CLAUDE_PLUGIN_ROOT:-}" && test -d "${CLAUDE_PLUGIN_ROOT}"
test -n "${CLAUDE_WORKING_DIR:-}" && test -d "${CLAUDE_WORKING_DIR}"
test -n "${KNOWLEDGE_DIR:-}"   # 仅判非空；不要求目录必须存在（私域知识库为可选）
```

`CLAUDE_PLUGIN_ROOT` / `CLAUDE_WORKING_DIR` 两项均通过 → 进入 Step 0.3。  
任一项失败 → 执行 Step 0.2。  
`KNOWLEDGE_DIR` 仅为空时参与 Step 0.2 补全（已非空则沿用，不强制目录存在）。

### Step 0.2 补全缺失变量（仅 Agent 层执行一次）

**`CLAUDE_PLUGIN_ROOT`**

1. 若 Claude Code 已注入且目录存在：沿用。
2. 若仍缺失，按顺序降级（须验证 `${路径}/skills/constitution/SKILL.md` 存在）：
   - Skill 加载上下文中的插件安装根；
   - 在 `${CLAUDE_WORKING_DIR}` 或其上级查找含 `.claude-plugin/plugin.json` 的目录；
3. `export CLAUDE_PLUGIN_ROOT="<绝对路径>"`
4. 失败 → 终止并提示配置插件。

**`CLAUDE_WORKING_DIR`**

1. 若已注入且目录存在：沿用。
2. 若缺失：`export CLAUDE_WORKING_DIR="$(pwd)"`（**不用** `git rev-parse --show-toplevel`，避免子目录工作区被抬到仓库根）
3. 失败 → 终止。

**`KNOWLEDGE_DIR`**（处理方式对标 `CLAUDE_WORKING_DIR`：已注入则沿用，缺失才降级解析）

1. 若已注入且非空：**沿用**（不做覆盖，与会话变量一致）。
2. 若缺失：降级解析——读 init 脚本写入的标记文件 `knowledge.path`；标记缺失则回退默认 `omni-doc`。constitution 在 sdd Step 1（`.omni-infra` 首建）触发，**早于 specify 写 `.runs/env.sh`**，故降级源是标记文件而非会话变量：

   ```bash
   if [[ -z "${KNOWLEDGE_DIR:-}" ]]; then
     # 读 init 脚本写入的 knowledge.path（sdd Step 1 已写好）；标记缺失则回退默认 omni-doc
     export KNOWLEDGE_DIR="$(cat "${CLAUDE_WORKING_DIR}/.omni-infra/knowledge.path" 2>/dev/null || true)"
     export KNOWLEDGE_DIR="${KNOWLEDGE_DIR:-${CLAUDE_WORKING_DIR}/omni-doc}"
   fi
   ```
3. 失败 → 终止（此步骤无失败路径：标记缺失已回退默认，故不终止）。

> 与 `CLAUDE_WORKING_DIR` 的差异：KNOWLEDGE_DIR 是**可选**知识源，不强制目录必须存在（Step 0.3 不对它做 `test -d`），目录缺失时由步骤 3 的 Fallback 处理。

### Step 0.3 校验工作区 `.omni-infra`（必须通过）

```bash
test -f "${CLAUDE_PLUGIN_ROOT}/omni-infra/memory/constitution.md"
test -d "${CLAUDE_WORKING_DIR}"
```

**若 `${CLAUDE_WORKING_DIR}/.omni-infra` 不存在**：执行初始化（显式传入工作区，**不要**依赖脚本内 `pwd`，**不要**仅 `export` 后无参调用；透传 Step 0.2 已解析的 `KNOWLEDGE_DIR`，使 init 脚本向正确目录拷贝 `knowledge.config.yaml` + 写 `knowledge.path` 标记）：

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/bash/init_omni_infra.sh" \
  --plugin-root "${CLAUDE_PLUGIN_ROOT}" \
  --working-dir "${CLAUDE_WORKING_DIR}" \
  --knowledge-dir "${KNOWLEDGE_DIR}"
```

说明：`init_omni_infra.sh` 将 `${CLAUDE_PLUGIN_ROOT}/omni-infra` 复制为 `${CLAUDE_WORKING_DIR}/.omni-infra`。
- 透传 `--knowledge-dir` 时，脚本向该目录拷贝 `knowledge.config.yaml`（缺失才拷，不覆盖），并把生效的绝对路径写入 `${CLAUDE_WORKING_DIR}/.omni-infra/knowledge.path` 标记文件（供本技能步骤 3 私域检索读取）；`KNOWLEDGE_DIR` 缺省为 `${CLAUDE_WORKING_DIR}/omni-doc`。
- 执行过程中会**自动**（幂等）向工作区根目录 `${CLAUDE_WORKING_DIR}/.gitignore` 追加 SDD 运行时产物目录：`changes/` 与知识库目录（默认 `omni-doc/`；若 `KNOWLEDGE_DIR` 为其它目录则一并追加，已存在则跳过），避免过程文件被误提交。
- 返回码（与 sdd Step 1 一致）：
  - `0`：`.omni-infra` 已存在 → 继续后续步骤（本技能由 sdd 在返回 `1` 时触发，故正常路径下此时 `.omni-infra`刚建好、`knowledge.path` 已写入，校验已通过）
  - `1`：工作区**原本无** `.omni-infra`、脚本已首次创建 → 继续本技能（constitution 本就是该返回码的后续动作）
  - `2`：失败 → 终止流程

**若仅缺章程文件、但 `.omni-infra` 已存在**：从 `${CLAUDE_PLUGIN_ROOT}/omni-infra/memory/constitution.md` 复制到 `${CLAUDE_WORKING_DIR}/.omni-infra/memory/constitution.md`（勿在工作区外创建新文件）。

✅ Checkpoint: `CLAUDE_PLUGIN_ROOT=...`, `CLAUDE_WORKING_DIR=...`, `KNOWLEDGE_DIR=...`, 章程路径=`${CLAUDE_WORKING_DIR}/.omni-infra/memory/constitution.md`

### 路径拼接约定

- 工作区读写：`${CLAUDE_WORKING_DIR}/.omni-infra/...`
- 插件种子/初始化脚本：`${CLAUDE_PLUGIN_ROOT}/omni-infra/...`、`${CLAUDE_PLUGIN_ROOT}/scripts/bash/init_omni_infra.sh`
- **禁止**用 `git rev-parse --show-toplevel` 替代 `CLAUDE_WORKING_DIR` 定位章程与模板

---

## 概述

更新位于 **`${CLAUDE_WORKING_DIR}/.omni-infra/memory/constitution.md`** 的项目章程。该文件为带方括号占位符的模板（如 `[PROJECT_NAME]`、`[PRINCIPLE_1_NAME]`）。任务为：(a) 收集/推导具体值；(b) 精确填充模板；(c) 将修改传播到相关依赖项。

**始终操作工作区内已有的 `${CLAUDE_WORKING_DIR}/.omni-infra/memory/constitution.md`，不要在工作区外或插件目录内直接改写。**

---

## 执行流程

> 以下步骤均在完成「环境初始化」之后执行。所有 Read/Write/Edit 目标路径须使用上表绝对路径（基于 `CLAUDE_WORKING_DIR`）。

### 1. 前置检查：章程是否已存在

读取 **`${CLAUDE_WORKING_DIR}/.omni-infra/memory/constitution.md`**：

- **如果文件存在且无未填写的 `[ALL_CAPS_IDENTIFIER]` 占位符**：输出 "章程已存在，跳过创建。" 并**立即结束**，不执行后续步骤。
- **如果文件不存在或仍有占位符**：继续执行以下步骤。

### 2. 加载章程模板

- 读取 **`${CLAUDE_WORKING_DIR}/.omni-infra/memory/constitution.md`**，识别所有 `[ALL_CAPS_IDENTIFIER]` 占位符。
- **原则数量与模板不一致时**：
  - 原则减少：删除对应的 `[PRINCIPLE_N_NAME]` 与 `[PRINCIPLE_N_DESCRIPTION]` 章节。
  - 原则增加：按模板格式新增原则章节。

### 3. 收集/推导占位符值

依次执行 3.1 → 3.2 → 3.3，**三者是相互补充的过程，每一步都必须执行，不得跳过任何一步**。三步各自产出的候选值在步骤 4「起草更新内容」时**合并/交叉校验**后填入占位符，而非由某一步单独覆盖。

#### 3.1 用户输入

- 采集 `$ARGUMENTS` 用户消息中明确给出的内容（项目名、原则名称与描述、采纳日期等）。
- 用户输入未覆盖的占位符，由 3.2、3.3 补充。

#### 3.2 私域知识检索

- **无条件执行一次检索**——不再以「推断是否充足」作为前置门槛。只要下方「就绪检查」通过即检索；通过与否**都必须在 Step 9 摘要里留痕**（已执行+命中数 / 已跳过+具体原因）。
- **就绪检查**（机器闸门，非主观判断；`KNOWLEDGE_DIR` 已由 Step 0.2 解析：读 `knowledge.path`，缺失回退 `omni-doc`）：
  - `${KNOWLEDGE_DIR}` 目录存在 **且** 其下 `knowledge.config.yaml` 存在 → 就绪，执行检索。
  - **目录存在但 `knowledge.config.yaml` 缺失**：**就地自愈**——从 `${CLAUDE_PLUGIN_ROOT}/skills/knowledge-retrieval/knowledge.config.yaml` 拷贝到 `${KNOWLEDGE_DIR}/knowledge.config.yaml`（已存在则保留不覆盖），并将其中 `raw_knowledge_dir:` 改为 `.`（相对该 config 解析为知识库目录自身），随后视为就绪并执行检索。
  - **`${KNOWLEDGE_DIR}` 目录不存在或为空**：不就绪，跳过检索并进入 3.3。
- **执行检索**（就绪时）：委托 `knowledge-retrieval-agent` sub-agent（隔离其厚重上下文），在 prompt 中**显式传入**（subagent 上下文从空白开始，不继承本会话历史）：
  - **意图文本** = 章程模板中尚未被 3.1 覆盖的占位符及其上下文
  - **已提取要素** = 占位符类型（名称/原则描述/项目名称等）/ 关键概念
  - **`@knowledge` 检索路径** = **`${KNOWLEDGE_DIR}`**
  - **检索配置** = **`${KNOWLEDGE_DIR}/knowledge.config.yaml`**（sub-agent 须在该目录下运行——prompt 中要求其先 `cd "${KNOWLEDGE_DIR}"` 再加载 skill，使 CLI 自动级联查找配置）
- **使用结果**：sub-agent 返回的带来源结构化结果作为占位符候选值之一，与 3.1、3.3 合并；要求其在返回里**明确标注 config 是否命中、vector/graph 产物是否已构建**，以便区分「真零结果」与「中途降级」。本步命中为零或降级时，相应占位符依赖 3.1、3.3 补充。

#### 3.3 按模板「填写方式」从参考文档或项目推断

- 对每个占位符，按模板内「填写方式」从参考文档或项目结构推断，产出候选值之一。
- 与 3.1、3.2 的候选值合并/交叉校验，不得跳过本步。
- **治理日期**：`RATIFICATION_DATE` 为原始采用日（未知则询问或标 TODO）；`LAST_AMENDED_DATE` 若有修改则为今天，否则保留原值。
- **版本 `CONSTITUTION_VERSION`**（语义化版本）：
  - **MAJOR**：原则删除或重新定义等不兼容变更。
  - **MINOR**：新增原则/章节或实质性扩展。
  - **PATCH**：措辞澄清、拼写修正、非语义优化。
- 若版本类型不明确，在定稿前给出理由。

### 4. 起草更新内容

- 用具体文本替换每个占位符；故意保留的槽位需明确说明。
- 保留标题层级；除步骤 7 的同步影响报告注释外，删除其余 HTML 注释。
- 每个原则：简短名称、不可协商规则段落（或列表）、必要时给出理由。
- 治理部分需包含修改程序、版本策略与合规审查期望。

### 5. 一致性传播检查

读 **`${CLAUDE_WORKING_DIR}/.omni-infra/templates/`** 下依赖模板，确保与更新后原则一致：

- **`design-template.md`**：「章程检查」与更新后原则一致。
- **`tasks-template.md`**：任务分类反映原则（如可观测性、版本控制、测试纪律）。
- **`spec-template.md`**：范围/需求对齐；章程若增删强制部分或约束则同步更新。
- 工作区内 README、docs、代理指导等，更新对已变更原则的引用。

### 6. 生成同步影响报告

在更新后的章程**文件顶部**以 HTML 注释形式插入：

- 版本变更：旧版本 → 新版本
- 修改的原则列表（若有重命名：旧标题 → 新标题）
- 新增/删除的章节
- 需更新的模板（✅ 已更新 / ⚠ 待处理）及路径（使用 `${CLAUDE_WORKING_DIR}/.omni-infra/...` 绝对路径）
- 若有故意延后的占位符，列出后续 TODO

### 7. 最终验证

- 无未解释的括号占位符。
- 版本行与报告一致。
- 日期为 ISO 格式 YYYY-MM-DD。
- 原则为声明式、可检验，避免模糊用语（用 MUST/SHOULD 及理由替代 "should"）。

### 8. 写回文件

将完成的章程写回 **`${CLAUDE_WORKING_DIR}/.omni-infra/memory/constitution.md`**（覆盖）。

### 9. 输出摘要

向用户提供：

- 新版本及递增理由。
- 标记为需人工跟进的文件（完整路径）。
- 建议提交信息（如：`docs: amend constitution to vX.Y.Z (principle additions + governance update)`）。

---

## 格式与样式

- 严格按模板使用 Markdown 标题层级；章节间保留一个空行；避免行尾空格。
- 用户仅提供部分更新（如单条原则修订）时，仍执行完整验证与版本决策。

## 缺失信息处理

若关键信息缺失（如批准日期未知），在正文中插入 `TODO(<FIELD_NAME>): explanation`，并在同步影响报告的「延迟项」中列出。
