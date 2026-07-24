---
name: design
description: 执行实施规划工作流, 使用计划模板生成设计制品，在代码之前建立可执行的技术决策体系。
context: fork
allowed-tools: Read, Write, Edit, Grep, Glob, Bash, Skill, TodoWrite, Task, Agent(knowledge-retrieval-agent)
---
# design

## 行为准则

1. ❗ 每个步骤必须按顺序执行，不得跳过或截断
2. ❗ 步骤 1 **继承** specify 已落盘的 `FEATURE_DIR`/`BRANCH_NAME`（`paths.json`/`env.sh`）；init **仅扩展** design 字段，不得新建特性目录或改分支名；步骤 1.2 之后以 `IMPL_DESIGN` 等为路径基准
3. ❗ **产物落盘优先于对话输出** — 必须用 **Write/Edit** 写入约定路径；**禁止**仅在回复中展示却未落盘
4. ❗ **Harness 门禁优先于完成报告** — 每步须 `design-gate` 且 `gate_exit=0`；全量 `verify-design-artifacts.sh` 通过后方可报告完成
5. ❗ **私域知识检索强约束** — 当 Step 2.2 判定知识源**就绪**（`ready`/`self_healed`，含自愈后）时，**必须**真实派发 `knowledge-retrieval-agent`，并以其返回如实填写 `${FEATURE_DIR}/.runs/internal/knowledge-retrieval.json` 的 `knowledge_retrieval` 字段（`executed:true` + `hits` + `config_hit/vector_built/graph_built/mode`）。**禁止**在知识源就绪时跳过派发或填 `executed:false`。派发后须运行 `design-gate --step kr --record`，`gate_exit=0` 方可进入步骤 3；`gate_exit=1` 按 `errors` 补齐后重跑（最多 2 次）。仅知识源缺失/为空（`skip`）是合法跳过路径。

---

## 环境初始化

本技能**所有**路径拼接与脚本调用，均依赖以下两个变量。

| 变量 | 含义 | 用途 |
|------|------|------|
| `CLAUDE_PLUGIN_ROOT` | Omni 插件安装根目录 | 定位本技能脚本、`design-resolve-context`、`check-prerequisites` |
| `CLAUDE_WORKING_DIR` | 用户当前工作区目录（可为 Git 仓库子目录） | 定位 `.omni-infra/`、`changes/`、Harness 落盘 |
| `FEATURE_DIR` / `BRANCH_NAME` | 特性目录与分支名（绝对路径 / 名称） | **继承 specify**；`design-resolve-context.sh` 或 `source env.sh` |
| `KNOWLEDGE_DIR` | 私域知识库根目录（私域知识检索用，与反构文档库 `DOC_DIR` 独立） | **继承 specify**（`source env.sh` 后已导出）；缺失回退 `${CLAUDE_WORKING_DIR}/omni-doc` |

### Step 0.1 检查变量

```bash
test -n "${CLAUDE_PLUGIN_ROOT:-}" && test -d "${CLAUDE_PLUGIN_ROOT}"
test -n "${CLAUDE_WORKING_DIR:-}" && test -d "${CLAUDE_WORKING_DIR}"
```

任一项失败 → Step 0.2 补全（仅 Agent 层一次）：
- `CLAUDE_WORKING_DIR` 缺失时用 `export CLAUDE_WORKING_DIR="$(pwd)"`（**不用** `git rev-parse --show-toplevel`）。
- `KNOWLEDGE_DIR`（处理方式对标 `CLAUDE_WORKING_DIR`：已注入则沿用）：本技能在 specify 之后执行，`${FEATURE_DIR}/.runs/env.sh` 已含 `export KNOWLEDGE_DIR`，**步骤 1 `source env.sh` 后即自动获取**；若 source 后仍为空（独立调用 / env.sh 缺失），回退默认：

  ```bash
  # 步骤 1 source env.sh 之后追加（已注入则不覆盖）
  export KNOWLEDGE_DIR="${KNOWLEDGE_DIR:-${CLAUDE_WORKING_DIR}/omni-doc}"
  ```

  `KNOWLEDGE_DIR` 是可选知识源，不强制目录存在；目录缺失/为空时 Step 2.2 私域检索合法跳过（`skip`），目录存在时由 Step 2.2 机器闸门判定（`ready`/`self_healed` 必须派发，详见行为准则 5）。

### Step 0.3 校验

```bash
test -f "${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/python/design_harness.py"
test -f "${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/bash/design-resolve-context.sh"
test -f "${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/bash/design-init-harness.sh"
test -f "${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/powershell/design-init-harness.ps1"
test -d "${CLAUDE_WORKING_DIR}"
```

### 路径拼接约定

- `scripts/bash/`、`scripts/powershell/` — 平台封装；`scripts/python/` — Harness 核心
- 工作区模板：`${CLAUDE_WORKING_DIR}/.omni-infra/templates/...`
- resolve/init **必须**传 `--plugin-root`、`--working-dir`；`--feature-dir`/`--branch-name` 可省略（从 specify 上游解析）
- **禁止**用 `setup-design.sh` 的 Git 当前分支猜特性目录（与 `tasks` 一致）
- **禁止**脚本内用 `__file__.parents`、`pwd`、`git rev-parse` 推断根路径

| 平台 | init | gate / verify / finalize |
|------|------|---------------------------|
| Linux / bash | `scripts/bash/design-init-harness.sh` | `scripts/bash/design-gate.sh` 等 |
| Windows / pwsh | `scripts/powershell/design-init-harness.ps1` | `scripts/powershell/design-gate.ps1` 等 |

---

## Harness 执行契约（不含 E2E 时亦适用）

**编排 / 落盘 / 校验分离**：LLM 产出内容 → **Write** 文件 → **脚本 gate** 判定 → 更新 `design-run.json`。

**模板契约（强制）**：`skills/design/references/template-contract.json` 由 `design_template_gate.py` 在 gate 步骤 `0/3/1a/1b/1c/1d/9/4` 校验；未按 `omni-infra/templates/*.md` 与 metamodel 结构落盘时 `gate_exit=1`。初始化可用：

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/python/design_harness.py" render-design \
  --feature-dir "$FEATURE_DIR" --branch-name "$BRANCH"
```

### 机器可读状态

| 文件 | 用途 |
|------|------|
| `{FEATURE_DIR}/.runs/paths.json` | 路径真值源 |
| `{FEATURE_DIR}/.runs/env.sh` | `source` 后导出 `FEATURE_DIR`、`IMPL_DESIGN`、`KNOWLEDGE_DIR`（私域知识库根目录）、`DOC_DIR`（反构文档库）等 |
| `{FEATURE_DIR}/.runs/design-run.json` | 分步门禁、断点续跑 |
| `{FEATURE_DIR}/.runs/.omnispec-state.json` | SDD 阶段状态 |

### 硬性交付物（非 E2E，缺一则不得完成）

| 文件 | 步骤 |
|------|------|
| `design.md` | 1→3→1a→1b→1c→1d→9 |
| `research.md` | 0 |
| `data-model.md` | 1b |
| `contracts/api-contract.md` | 1c |
| `quickstart.md` | 1d |
| `.runs/evaluations/eval-design-summary.json` | 8 |
| `.runs/evaluations/eval-design-report.md` | 8 |
| `.runs/metrics/omni-metrics-log.json` | 5（runlog） |

### 分步门禁

| 步骤 | gate `--step` | 时机 |
|------|---------------|------|
| 1.2 | `1` | `design-init-harness.sh` 之后 |
| 私域知识检索 | `kr` | 步骤 2.2 派发/留痕后，进入步骤 3 之前（知识源就绪则必跑） |
| 阶段 0 | `0` | Write `research.md` 之后 |
| 填充设计骨架 | `3` | 填充 `design.md` 技术背景/章程检查后 |
| design-function 后 | `1a` | `## 功能` + `FUNC-xxx` |
| design-entity 后 | `1b` | `data-model.md` + `## 逻辑实体` |
| design-interface 后 | `1c` | `contracts/api-contract.md` |
| quickstart 落盘 | `1d` | Write `quickstart.md`（可执行验证路径） |
| 修改点检查 | `9` | `## 修改点严格检查` 表格完成后 |
| 方案评测 | `8` | 评测 json + report 落盘后 |
| runlog | `11` | `omni-dsdd:runlog-record` 之后 |
| 全量 | `all` | 完成报告前（步骤 4.5） |

### 统一命令

**Linux / bash：**

```bash
bash "${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/bash/design-resolve-context.sh" \
  --plugin-root "${CLAUDE_PLUGIN_ROOT}" \
  --working-dir "${CLAUDE_WORKING_DIR}" \
  ${FEATURE_DIR:+--feature-dir "$FEATURE_DIR"} \
  ${BRANCH_NAME:+--branch-name "$BRANCH_NAME"} \
  --export

bash "${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/bash/design-init-harness.sh" \
  --plugin-root "${CLAUDE_PLUGIN_ROOT}" \
  --working-dir "${CLAUDE_WORKING_DIR}" \
  ${FEATURE_DIR:+--feature-dir "$FEATURE_DIR"} \
  ${ENABLE_E2E:+--enable-e2e} \
  --start-time "$start_time"

source "$FEATURE_DIR/.runs/env.sh"
# KNOWLEDGE_DIR 回退默认（对标 CLAUDE_WORKING_DIR：source 后仍为空才回退，已注入则不覆盖）
export KNOWLEDGE_DIR="${KNOWLEDGE_DIR:-${CLAUDE_WORKING_DIR}/omni-doc}"

bash "${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/bash/design-gate.sh" \
  --feature-dir "$FEATURE_DIR" --step STEP --record

bash "${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/bash/verify-design-artifacts.sh" \
  --feature-dir "$FEATURE_DIR"

python3 "${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/python/design_harness.py" resume \
  --feature-dir "$FEATURE_DIR"

bash "${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/bash/design-finalize.sh" \
  --feature-dir "$FEATURE_DIR" --next-stage tasks
```

**Windows / pwsh：** 将 `bash .../scripts/bash/*.sh` 换为 `pwsh .../scripts/powershell/*.ps1`（参数相同）。

- `gate_exit=0`：允许进入下一步
- `gate_exit=1`：根据 JSON `errors` 回退重做（每步最多 2 次）

## 输入

- **用户参数**：`$ARGUMENTS`（可为空）
- **`$ENABLE_E2E`**：可选，`true` 时额外要求 `e2e-impl-design.md`（全量门禁加 `--enable-e2e`）
- **上游特性上下文**（workflow 调用时由 prompt 注入）：`FEATURE_DIR`、`BRANCH_NAME` — 须与 specify 落盘一致；**禁止** design 自行 allocate 或猜目录

## 输出

- `IMPL_DESIGN`（`design.md`）：设计主文档
- `research.md`：**必需**
- `data-model.md`：**必需**
- `contracts/api-contract.md`：**必需**
- `quickstart.md`：**必需**（最小可验证集成路径）
- `.runs/evaluations/eval-design-summary.json`、`.runs/evaluations/eval-design-report.md`：**必需**
- Agent 特定上下文文件：由 `update-agent-context` 更新

## 技能依赖

本技能会调用以下技能：
- `/omni-dsdd:design-function`：获取功能变更内容，追加到 IMPL_DESIGN
- `/omni-dsdd:design-entity`：获取逻辑实体变更内容，生成 `data-model.md`
- `/omni-dsdd:design-interface`：获取接口变更内容，写入 `contracts/api-contract.md`
- `/omni-dsdd:e2e-design`：执行测试实现分析，生成 `e2e-impl-design.md`
- `/omni-dsdd:e2e-varify`：执行测试设计完整性检查与完善
- `/omni-dsdd:eval-design`：执行方案质量评测
- `/omni-dsdd:tdd-workflow`：获取 TDD 测试策略规则（覆盖率要求、测试分层标准、测试模式模板），用于指导 TDD 测试策略章节的生成
- `/omni-dsdd:runlog-record`：记录本 skill 的运行日志信息

## 指令

### 0. skill执行开始时间打点记录

开始执行步骤之前，需要进行一些打点记录工作，记录本skill的执行时间到 `start_time`字段：
 - 判断当前操作系统，windows还是linux系统;
 - 针对不同操作系统运行脚本获取配置
   windows: `Get-Date -Format "yyyy-MM-dd HH:mm:ss"`
   linux: `date +"%Y-%m-%d %H:%M:%S"`
 - 将获取的时间记录到 `start_time`

### 1. 继承上游特性上下文（specify 已记录，禁止 Git 猜目录）

与 **`tasks`** 一致，**禁止**用当前 Git 分支推断 `FEATURE_DIR`。

**解析顺序**：

1. workflow prompt 注入的 `FEATURE_DIR` / `BRANCH_NAME`（若有）
2. 运行 `design-resolve-context`（读 specify 的 `paths.json` / `.active-feature` / `env.sh`）：

```bash
eval "$(bash "${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/bash/design-resolve-context.sh" \
  --plugin-root "${CLAUDE_PLUGIN_ROOT}" \
  --working-dir "${CLAUDE_WORKING_DIR}" \
  ${FEATURE_DIR:+--feature-dir "$FEATURE_DIR"} \
  ${BRANCH_NAME:+--branch-name "$BRANCH_NAME"} \
  --export)"
source "${FEATURE_DIR}/.runs/env.sh"
```

3. **仅直连 `/design` 且无上游**时，可降级 `check-prerequisites --json --paths-only`（须已有 `spec.md`）；**SDD 链路禁止**使用 `setup-design.sh`

**强制校验**：

- `FEATURE_DIR` 位于 `${CLAUDE_WORKING_DIR}/changes/` 下
- `${FEATURE_DIR}/spec.md` 或 `.runs/paths.json` 已存在（说明 specify 已跑过）
- `BRANCH_NAME` 来自上游 `paths.json`/`env.sh`，**不是** `git branch` 当前分支

日志：`design 继承上游: FEATURE_DIR=..., BRANCH_NAME=..., source=specify`

### 1.2 初始化 Harness（紧接步骤 1，扩展不重建）

- 执行 `design-init-harness`（**必须**含 `--plugin-root`、`--working-dir`；`--feature-dir` 可省略，由 harness 继承上游）
- init **合并** specify 的 `paths.json`/`env.sh`，只补 `design_file`、`IMPL_DESIGN`、`enable_e2e` 等字段
- 执行 `design-gate.sh --feature-dir "$FEATURE_DIR" --step 1 --record`
- **`gate_exit=0` 后方可进入步骤 2**
- init 会预建 `contracts/`、`.runs/` 并写入 `research.md`、`data-model.md`、`contracts/api-contract.md`、`quickstart.md` 占位文件（后续步骤必须 **替换** 占位内容，不得仅保留占位）

### 2. 加载上下文

- 读取 `${CLAUDE_WORKING_DIR}/.omni-infra/memory/constitution.md` 以及 IMPL_DESIGN 模板（init 已从 `${CLAUDE_WORKING_DIR}/.omni-infra/templates/` 种子化）。
- **优先加载 context.md**:
  - **必须检查** `FEATURE_DIR/context.md` 是否存在
  - **如果存在**, 直接读取 `context.md` 作为主要上下文源，提取以下信息:
    - 功能描述和目标
    - 提取的关键词（用于后续检索）
    - 检索到的设计文档列表（可直接参考，减少重复检索）
    - 可复用的需求和场景模式
    - 术语对齐信息
    - 约束和假设
    - **相关代码文件**（新增）：代码文件路径、函数接口、数据结构、实现模式
    - **需要新增的代码**（新增）：消息类型、消息结构、处理函数等
  - **如果不存在**, 继续执行后续检索步骤（但应提示用户先执行 `/omni-dsdd:spec-impact-analyze` 生成上下文）
- **补充检索**（仅在 context.md 信息不足时执行）:
  1. **如文档无法解答疑问**：允许深入代码仓库执行 `search`（可用 `grep`、`read_file` 逐文件阅读），直到澄清概念或接口约束，避免凭空猜测。**优先参考 context.md 中的代码文件**: 如果 context.md 中已列出相关代码文件，优先阅读这些文件，了解现有实现模式 2.**查找文件时禁止使用限制命令**：使用 `read_file`、`grep`、`glob_file_search` 等工具时，**严禁使用 `head`、`tail`、`limit` 等命令限制输出**，必须读取完整内容以准确理解项目结构
- **逻辑架构文档（与 `omni-dsdd:design-entity` / `omni-dsdd:design-interface` 一致）**:
  - **解析顺序**（步骤 1.2 init 并 `source "$FEATURE_DIR/.runs/env.sh"` 后，`DOC_DIR` 为绝对路径；直接 `${DOC_DIR}/...` 拼接；**不阻塞**：任一不存在则尝试下一项，两项均不存在则跳过）：
    1. `${DOC_DIR}/on-demand/logic_architecture.md`（按需反构快照，**优先**）
    2. `${DOC_DIR}/specs/logic_architecture.md`（规格库）
  - **生效规则**：按顺序选用**第一个存在的文件**作为本次设计的**有效架构约束**；若两项均不存在，**不报错**，在 IMPL_DESIGN 技术上下文中简要注明「未找到架构文档，分层假设见下文」，后续子技能按同一规则处理。
- **按需反构逐功能文档（可选）**:
  - **路径**：`${DOC_DIR}/on-demand/functions/`（目录，内含 `*.md`；与按需反构阶段约定一致）
  - **若目录存在且含至少一个 `.md`**：列出并读取与本次变更相关的功能文档（优先按 `FEATURE_SPEC`、`context.md` 中的功能名/关键词/`function_key` 匹配；无法判定时可读取目录内全部 `.md` 作为候选），将**现状行为、入口、波及点、证据链**等纳入技术上下文，并在调用 `omni-dsdd:design-function`、`omni-dsdd:design-entity`、`omni-dsdd:design-interface` 时作为**存量实现参考**。
  - **若不存在**：跳过，不阻塞。

### 2.2 私域知识检索（知识源就绪时必须执行）

> ⚠️ 强约束：本步是否执行由**机器闸门**（下方三态判定）决定，**不再**以"推断 context.md 是否信息充足"等主观理由跳过。仅知识源 `skip`（目录缺失/为空）才是合法跳过路径；`ready`/`self_healed` 必须无条件派发 `knowledge-retrieval-agent`（见行为准则 5）。

**机器闸门三态判定**（与 `design-gate --step kr` 的 `_gate_step_kr` 语义一致）：

- **就绪 (`ready`)**：`${KNOWLEDGE_DIR}`（已由 Step 0.2 + 步骤 1 `source env.sh` 解析；与反构文档库 `${DOC_DIR}` 独立）目录存在且非空 **且** 其下 `knowledge.config.yaml` 存在 → 必须派发检索。
- **config 缺失 → 就地自愈 (`self_healed`)**：目录存在但 `knowledge.config.yaml` 缺失 → **不自降级 fallback**，从插件模板拷贝补齐（与 `init_omni_infra.sh` 的 `_knowledge_config` 同源）：
  ```bash
  cp "${CLAUDE_PLUGIN_ROOT}/skills/knowledge-retrieval/knowledge.config.yaml" "${KNOWLEDGE_DIR}/knowledge.config.yaml"
  sed -i 's|^raw_knowledge_dir:.*|raw_knowledge_dir: .|' "${KNOWLEDGE_DIR}/knowledge.config.yaml"
  ```
  自愈后视为就绪 → 必须派发检索。
- **合法跳过 (`skip`)**：`${KNOWLEDGE_DIR}` 目录不存在或为空 → 唯一允许跳过的路径；跳过时仍须写 `executed:false` + 非空 `skip_reason` 到留痕 json。

**知识检索**（`ready`/`self_healed` 时执行）：
  - 委托 `knowledge-retrieval-agent` sub-agent 执行检索（隔离其厚重上下文），在 prompt 中**显式传入**（subagent 上下文从空白开始，不继承本会话历史）：
    - **检索意图文本** = 来自 context.md 或功能描述的设计关注点
    - **已提取要素** = 功能目标 / 关键概念 / 关键词列表
    - **`@knowledge` 检索路径** = **`${KNOWLEDGE_DIR}`**
    - **检索配置** = **`${KNOWLEDGE_DIR}/knowledge.config.yaml`**（sub-agent 在该目录下运行，CLI 自动级联查找配置）
    - **额外要求**：要求 sub-agent 在返回里**如实标注** `config_hit`（config 是否命中）、`vector_built`（向量索引是否已构建）、`graph_built`（图谱是否已构建）、`mode`（`enhance`/`baseline`，来源 `config-info`），用于区分「真零结果」与「产物未构建导致的中途降级」。
  - sub-agent 返回带来源的结构化结果后：
    - 直接用于补充设计上下文（阶段 0 research.md），引用其命中文档列表与关联度判断
    - 满足来源引用准则：所有结论沿用 sub-agent 返回的 `source_file/location`
    - 命中数为 0 → 按**真零结果**处理（`executed:true, hits:0`），**不得**当作跳过。

**❗ 强制留痕**：派发完成后（含真零结果 / 合法跳过），必须 **Write** 到 `${FEATURE_DIR}/.runs/internal/knowledge-retrieval.json`，完整 schema：
  - `executed`: `bool`（就绪时必须 `true`；仅 `skip` 可 `false`）
  - `hits`: `int`（真零结果记 `0`）
  - `config_hit` / `vector_built` / `graph_built`: `bool`
  - `mode`: `"enhance"` | `"baseline"`
  - `skip_reason`: `string|null`（`executed:false` 时必须非空）

**门禁**（派发并留痕后，进入步骤 3 之前**必须**执行）：
  ```bash
  design-gate.sh --feature-dir "$FEATURE_DIR" --step kr --record   # Windows: design-gate.ps1
  ```
  `gate_exit=0` 方可进入步骤 3；`gate_exit=1` 读 JSON `errors` 补齐 json 或补派 sub-agent 后重跑（最多 2 次）。门禁自动完成 config 缺失自愈。

**Fallback**（仅知识源 `skip`，或派发后仍需澄清概念时补充）：允许深入代码仓库执行 `search`（可用 `grep`、`read_file` 逐文件阅读），**优先参考 context.md 中的代码文件**；**查找文件时禁止使用限制命令**（`head`/`tail`/`limit`），必须读取完整内容以准确理解项目结构。

- **多语言覆盖与配置文件分析（on-demand 快照优先）**:
  - **目的**：复用 `reverse-on-demand` 已产出的 polyglot 覆盖与配置分析结论，识别主语言（Java/Go/Python/...）之外的附属语言（Lua/Shell/SQL/Proto/Thrift...）及配置文件波及面，避免附属语言逻辑与配置项成为隐性修改点。与 `reverse-on-demand` 的 `polyglot_coverage`、`config_parse` 约束语义一致。
  - **不阻塞**：下列产物任一不存在则跳过该条，并在步骤 3 阶段 0 补扫（见下文）；全部缺失时不得中断设计。
  - **多语言覆盖（polyglot）**——按顺序读取，取第一个命中：
    1. `${DOC_DIR}/on-demand/logic_architecture.md` 的「1.3 语言构成与附属语言影响面」「1.4 文件类型组成」章节（主语言/附属语言、role、分析方式 lsp/grep/read、文件数/占比、入口与被调用关系）
    2. `${FEATURE_DIR}/.runs/stage2-search-coverage.json`（若上游反构落盘在此）的 `languages` / `file_type_stats` 子结构
    - 提取要点：全部识别到的语言清单、各语言 `analysis_method`、**命中本需求范围的附属语言**（`impact_status=hit`）
  - **配置文件分析（config_parse）**——按顺序读取：
    1. `${DOC_DIR}/on-demand/logic_architecture.md` 的「1.5 配置文件影响分析」章节
    2. `${FEATURE_DIR}/.runs/stage2-static-asset-scan.json` 的 `config_files` 子结构（每条含 `file_path`/`extracted_keys`/`consumer_refs`/`structure_summary`）
    3. `${FEATURE_DIR}/.runs/stage2-interface-config-scan.json` 的 `interface_config_analysis`（接口侧配置依赖，`consumed_config_keys`/`config_impact`）
    - 提取要点：命中的配置文件、关键 key、读取/消费方（consumer_refs）、与本需求关键词的匹配项
  - 读取结果作为**存量约束**纳入技术上下文，供步骤 3 阶段 0 研究与步骤 9 修改点检查引用；缺失部分由阶段 0 补扫。
- **上下文模式与兼容回退（强制）**:
  - 读取 `FEATURE_DIR/context.md` 中的 `context_mode` 与 `on_demand` 结构（若存在）。
  - 若 `context_mode = evidence_first`：启用 on-demand 证据优先设计模式。
  - 若 `context_mode = default` 或字段缺失：回退原流程，不阻塞设计。
  - 在任一模式下都必须继续生成设计产物，不得因 on-demand 缺失而中断。

### 2.1 设计边界锁定（仅 evidence_first 模式）

- 以 `on_demand.scope` 作为设计范围基线：
  - in-scope: `direct_functions`、`indirect_functions`、`interfaces`
  - out-of-scope: 不在基线且无证据链(`on_demand.traceability`)支持的项
- 将以下内容写入 IMPL_DESIGN 的技术上下文或波及分析部分：
  - in-scope 清单
  - out-of-scope 清单
  - 依赖前置条件（来自 `on_demand.risks` / `on_demand.evidence_gaps`）
- 对 `on_demand.contract_deltas` 中出现的契约变化，必须在：
  - 功能设计（行为变化）
  - 接口契约（输入/输出变化）
  - 测试实现分析（覆盖这些变化）
  三处形成一致映射。

### 3. 执行计划工作流

1. 按照 IMPL_DESIGN 模板中的结构填充内容
   - 填充技术上下文(将未知项标记为 `NEEDS CLARIFICATION`)
   - 从章程文档填充章程检查部分
   - 评估关卡（如果违规无正当理由则报错）
   - **强制落盘**：Write/Edit `IMPL_DESIGN`
   - **门禁**：`design-gate.sh --step 3 --record`（须含 `## 技术背景`、`## 章程检查`）

2. 阶段 0: 大纲与研究
   - **从技术上下文中提取未知项**:
     - 每个 `NEEDS CLARIFICATION` → graphify 查询任务
     - 每个依赖项 → graphify 模式查询任务
     - 每个集成 → graphify 关系路径任务
     - **多语言覆盖（polyglot）补扫任务**：当步骤 2 未能从 on-demand 快照取得完整 `languages` 清单或附属语言覆盖不全时触发，确保附属语言（Lua/Shell/SQL/Proto/Thrift 等）不被遗漏。补扫方式（与 `reverse-on-demand` 同款）：
       - 文件发现：`rg --files --no-ignore-vcs -g '!**/.git/**'`，按扩展名统计主语言（`.java/.go/.py/.ts/.js/.kt/.rs/.cpp/.cs` 等）与附属语言（`.lua/.sh/.bash/.sql/.proto/.thrift/.groovy/.ps1` 等）
       - 附属语言定位（grep 模式）：Lua `function|local`、Shell `function |[a-zA-Z_][a-zA-Z0-9_]*\(\)`、SQL `CREATE (PROCEDURE|FUNCTION)`、Proto `service|rpc`
       - 命中判定：承载业务逻辑的附属语言文件是否落入本需求修改范围（`impact_status` hit/no_hit）
       - `graphify_available=true` 时优先 `graphify query/explain "<语言/模块>"`，否则用 Grep/Glob/Read + bash `find`/`rg`
     - **配置文件分析（config_parse）补扫任务**：当步骤 2 未能从 on-demand 快照取得配置分析结论时触发。补扫方式（与 `reverse-on-demand` 同款）：
       - 文件发现（枚举重点目录下**所有文件类型**，禁止只搜单一后缀）：`config/ configs/ scripts/ deploy/ deployment/ charts/ helm/ manifests/ k8s/ resources/ settings/ properties/`
       - 内容扫描：用需求关键词全文检索 `rg -n "<关键词1>|<关键词2>" config/ deploy/ resources/ ...`
       - 结构解析（按类型提取 key）：YAML `(?m)^[[:blank:]]*[^#].*:\s*`、JSON `"[^"]+"\s*:`、properties/ini `^[^#=]+=`、XML `(?m)<[^/!?][^>]*>`
       - 消费者追溯：从代码侧反查 key 被谁读取 `rg -n "<config_key>" src/ pkg/ internal/`

   - **生成和分发研究任务**:
    - **检查 graph.json 是否存在**:
      - 在项目根目录下查找 `graphify-out/graph.json` 文件
      - 如果 `graphify-out/graph.json` 存在, 记录 `graphify_available = true`
      - 如果 `graphify-out/graph.json` 不存在, 记录 `graphify_available = false`
    - 调用 @"Explore(agent)" 探索代码库相关实现:
      - **当 `graphify_available = true` 时, 在 subagent 中优先使用 graphify 工具**:
        ```bash
        # 通用问题探索
        graphify query "<question>"

        # 查找组件/模块之间的调用路径
        graphify path "<A>" "<B>"

        # 深入理解特定概念
        graphify explain "<concept>"
        ```
      - **当 `graphify_available = false` 时, 使用代码库原生搜索工具**:
        - 使用 Grep/Glob 搜索关键代码符号、函数名、文件名
        - 使用 Read 阅读关键源文件理解实现逻辑
        - 使用 bash find/rg 等命令辅助定位代码
        - 禁止调用 graphify 工具(因为没有 graph.json 数据支撑, 调用会失败)

   - **在 `research.md` 中整合发现**，使用格式:
     ```markdown
     ## [探索主题]
     - Details: [graphify 查询/路径/解释的具体内容]
     - Rationale: [发现的关键信息、模式或关系]
     - Reference: [引用的 graphify 输出或文件位置]
     ```
   - **多语言覆盖与配置文件分析必须落 research.md**：阶段 0 结束前，`research.md` 须至少各含一条 `## 多语言覆盖` 与 `## 配置文件分析` 小节（遵循上述 Details/Rationale/Reference 格式）。若步骤 2 已从 on-demand 快照取得结论，则写一条「引用快照」的简短小节（Reference 指向快照文件路径与章节）；若为补扫结论，则 Details 记录 grep/glob 命中、Rationale 记录命中本需求的附属语言/配置项及消费方、Reference 记录具体文件:行号。

   - **强制落盘**：必须用 **Write** 写入 `FEATURE_DIR/research.md`（替换 init 占位）
   - **门禁**：`design-gate.sh --step 0 --record`（须含 `Details:`、`Rationale:`、`Reference:`，且非 Harness 占位；标签可加粗或使用全角冒号）
   - **evidence_first 额外要求**:
     - 优先从 `on_demand.risks` 与 `on_demand.evidence_gaps` 生成研究任务
     - 若存在合理默认值则写入假设，不强制新增澄清

3. 阶段 1: 技术设计建模
   - **前提条件**: `research.md` 门禁通过
   - 加载 skill `omni-dsdd:design-function` → **Write/Edit** 追加 `## 功能` 到 `IMPL_DESIGN` → `design-gate.sh --step 1a --record`
   - 加载 skill `omni-dsdd:design-entity` → **Write** `data-model.md` + 追加 `## 逻辑实体` 到 `IMPL_DESIGN` → `design-gate.sh --step 1b --record`
   - 加载 skill `omni-dsdd:design-interface` → **Write** `contracts/api-contract.md` → `design-gate.sh --step 1c --record`
   - **生成 quickstart（必需）**：
     - 依据 `spec.md` 验收场景、`design.md` 功能/接口、`contracts/api-contract.md`，编写最小可执行验证路径
     - 参考模板：`${CLAUDE_WORKING_DIR}/.omni-infra/templates/quickstart-template.md`（须含 `## 前置条件`、`## 验证步骤`（至少 2 条编号步骤）、`## 期望结果`）
     - **强制落盘**：必须用 **Write** 写入 `FEATURE_DIR/quickstart.md`（替换 init 占位）
     - **门禁**：`design-gate.sh --step 1d --record`
   - 加载 skill `omni-dsdd:tdd-workflow`，获取其定义的 覆盖率阈值、测试分层要求（单元 / 集成 / E2E）、测试模式模板
     - 基于 design.md 中的功能变更点、接口契约、数据模型，识别需要测试的关键入口
     - 为每个场景（P1/P2/P3...）规划：
       - 单元测试范围（函数、工具方法、纯逻辑）
       - 集成测试范围（API 端点、数据库操作、服务交互）
       - E2E 测试范围（关键用户流程）— 仅当 `$ENABLE_E2E=true`
     - 将上述规划写入 `FEATURE_DIR/quickstart.md` 的  `##TDD 测试策略## `

4. 阶段 2: Agent上下文更新
   - 判断当前操作系统，windows还是linux系统;
   - 针对不同操作系统从仓库根目录运行脚本
     windows: `pwsh "${CLAUDE_PLUGIN_ROOT}/scripts/powershell/update-agent-context.ps1"`
     linux: `bash "${CLAUDE_PLUGIN_ROOT}/scripts/bash/update-agent-context.sh"`
   - 这些脚本检测正在使用哪个 AI Agent
   - 更新相应的Agent特定上下文文件
   - 仅添加当前计划中的新技术
   - 保留标记之间的手动添加内容
   - **输出**: Agent特定文件

5. 阶段 3: 设计后重新评估
   - 重新评估章程检查，确保设计符合项目规范

6. 阶段 4: 测试实现分析（仅当 `$ENABLE_E2E=true` 时执行）

  - **判断条件**：检查传入的 `$ENABLE_E2E` 参数
    - 若 `$ENABLE_E2E=false` 或未设置：跳过阶段 4 和阶段 5，直接进入步骤8（设计验证与质量评估）
    - 若 `$ENABLE_E2E=true` 但 `e2e-test.md` 不存在：记录警告"E2E已启用但 e2e-test.md 不存在，跳过测试实现分析"，跳过阶段 4 和阶段 5，直接进入步骤8
    - 若 `$ENABLE_E2E=true` 且 `e2e-test.md` 存在：执行本步骤

  - **前提条件**：`design.md` 已完成，`e2e-test.md` 已存在

  - **目标**：生成测试实现分析报告，包含入口函数分析、外部依赖分析、测试数据设计、验证点定义

  - **强制要求**：当执行时，测试实现分析必须严格按照 `omni-dsdd:e2e-design` 技能文件中定义的流程执行，不得跳过或修改任何步骤。

  - 加载 skill `omni-dsdd:e2e-design`，该技能将：
    1. 验证前置文件（spec.md、design.md、e2e-test.md）
    2. 加载上下文文档（baseline、存量测试代码）
    3. 启动 `test-impl-design` subagent
    4. 生成测试实现分析报告
    5. 验证生成文档内容完整性

  - 执行完本步骤后，将生成以下文档：
  - `e2e-impl-design.md`：测试实现分析报告（包含用例实现映射表、入口函数详细分析、外部依赖详细分析、测试数据清单、验证点详细清单、存量测试复用分析）
  - **门禁**：`design-gate.sh --step 4 --record`；全量校验使用 `verify-design-artifacts.sh --enable-e2e`

  **注意**: 如果步骤6（测试实现分析）验证失败且无法继续（如 agent 执行失败、文档未生成），应记录错误信息并报告失败。

7. 阶段 5: 测试设计完整性检查与完善（仅当 `$ENABLE_E2E=true` 且阶段 4 已执行时执行）

  - **前提条件**：`e2e-design` 已完成，`e2e-impl-design.md` 已存在

  - **目标**：生成测试实现分析报告，包含入口函数分析、外部依赖分析、测试数据设计、验证点定义

  - **强制要求**：当执行时，测试实现分析必须严格按照 `omni-dsdd:e2e-varify` 技能文件中定义的流程执行，不得跳过或修改任何步骤。

  - 加载 skill `omni-dsdd:e2e-varify`，该技能将：
    - 执行变更点覆盖分析
    - 执行深度用例设计

  **注意**: 如果步骤7（测试设计完整性检查与完善）验证失败且无法继续（如 agent 执行失败、文档未生成），应记录错误信息并报告失败。

8. 设计验证与质量评估
  - 加载 skill `omni-dsdd:eval-design`, 对 design.md 进行多维度质量评测
   * **验证结果处理**:
     * **通过**（无 blocking 且 score >= 95）: 完成质量评估，进入下一步骤
     * **不通过**: 针对 blocking 问题和低分维度修复 IMPL_DESIGN，重新执行本步骤验证（最多 3 轮）
     * 3 轮后仍不通过: 在报告中标记问题，警告用户，附上 `validation_status: "warning"`
  - **门禁**：`design-gate.sh --step 8 --record`

9. 修改点严格检查（强制门禁）
   - 在完成设计产物后、进入完成报告前，必须逐条检查每个修改点：
     1. **是否已经支持**：
        - 依据 context.md、按需反构文档（`${DOC_DIR}/on-demand/functions/*.md`、`${DOC_DIR}/on-demand/interfaces/*.md`）、**多语言覆盖与配置文件分析结论**（步骤 2 on-demand 快照 + 步骤 3 阶段 0 research.md，含命中本需求的附属语言、命中的配置文件/key/消费方）和现有代码证据，判定是“已支持/部分支持/不支持”。
        - 对“已支持/部分支持”项，必须在设计中标注复用入口（模块、接口、函数、配置）。
     2. **是否遵循利旧原则（原有架构与实现）**：
        - 检查设计是否复用现有架构分层、模块边界、既有接口契约和已有实现模式。
        - 若选择新增实现而非复用，必须在 design 中给出“不可复用原因”和“替代方案比较”。
     3. **代码修改是否遵循最小化原则**：
        - 对每个修改点输出最小变更面：目标文件、目标函数/接口、预估新增/改动范围、避免改动项。
        - **附属语言与配置文件波及面**：若修改点涉及附属语言文件（Lua/Shell/SQL/Proto 等）或配置文件（yaml/properties/json/env 等），最小变更面须明确列出「目标附属语言文件 + 目标函数/规则」「目标配置文件 + 具体 key」，避免附属语言逻辑与配置项被无需求依据地扩散修改（这是 polyglot 与 config 分析的核心价值——防止附属语言和配置成为隐性波及面）。
        - 禁止无需求依据的跨模块扩散修改（Scope Creep）。
   - **检查输出要求**：
     - 在 `IMPL_DESIGN` 增加“修改点严格检查”小节，至少包含字段：`修改点`、`支持状态`、`利旧结论`、`最小化结论`、`证据`、`风险/备注`。
   - **evidence_first 额外门禁**：
     - 若设计条目不在 `on_demand.scope` 且无 `on_demand.traceability` 证据链支撑，判定为 scope creep，必须回退修正。
     - `on_demand.contract_deltas` 中的所有条目必须在 `contracts/api-contract.md` 可定位；缺失则判定不通过。
   - **门禁**：`design-gate.sh --step 9 --record`
   - **门禁规则**：
     - 任一修改点缺少证据或未满足利旧/最小化原则且无合理说明时，本次设计判定为不通过，必须回到设计阶段修正后再报告完成。

### 4.5 产物完整性校验（完成报告的前置门控）

- 执行：`verify-design-artifacts.sh --feature-dir "$FEATURE_DIR"`（E2E 时加 `--enable-e2e`）
- 可选：`python3 "${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/python/design_harness.py" resume --feature-dir "$FEATURE_DIR"`
- **`gate_exit=0` 后方可进入步骤 4 完成报告**；失败则按 `errors` 回退（每类最多 2 次）

### 4. 完成报告

- **前置条件**：步骤 4.5 `verify-design-artifacts.sh` 的 `gate_exit=0`（报告中写明 `evidence: verify-design-artifacts.sh exit 0`）
- 所有阶段及验证完成后，报告分支、IMPL_DESIGN 路径、生成的制品，以及验证结果（score、blocking 数量、validation_status）
- 完成报告中必须附“修改点严格检查汇总”：总修改点数、已支持数量、复用数量、最小变更通过数量、未通过项（如有）
- 如果阶段 4/5 已执行：报告 e2e-impl-design.md 路径
- 如果阶段 4/5 已跳过（未启用 `--e2e`）：报告"E2E测试实现分析已跳过（未启用 --e2e）"
- 完成报告中必须附上下文模式：
  - `context_mode=evidence_first`: 已按 on-demand 边界与证据链执行
  - `context_mode=default`: 未命中 on-demand 或信息不足，已回退原流程（附 `fallback_reason`）

### 5. 记录本skill的运行日志信息

- 执行前：`source "$FEATURE_DIR/.runs/env.sh"`
- 执行 `omni-dsdd:runlog-record` skill，传入 `start_time`
- **强制落盘**：追加 `omni-metrics-log.json` 后执行 `design-gate.sh --step 11 --record`

### 5.5 同步 SDD 状态

- 执行 `design-finalize.sh --feature-dir "$FEATURE_DIR" --next-stage tasks`
- 确认 `.runs/.omnispec-state.json` 的 `completed_stages` 包含 `"design"`

## 错误处理

| 场景 | 处理 |
|------|------|
| 分步 gate 失败 | 按 `errors` 回退该步重做，不得输出完成报告 |
| 全量 gate 失败 | 执行 `resume` 补跑缺失步骤 |
| 子技能仅返回文本未写文件 | 由 design 主流程 Write 落盘后再 gate |
| runlog 失败 | Write 追加 JSON 条目后重跑 `gate --step 11` |

## 关键规则

- 关卡失败或未解决的澄清事项时报错
- **禁止**在 `verify-design-artifacts.sh` 未通过时声明 design 完成
