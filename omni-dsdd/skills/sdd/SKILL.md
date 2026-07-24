---
name: sdd
description: OmniSpec 全流程开发入口（SDD 范式）。用户调用 /sdd 或说"部署omnispec"时触发，执行环境初始化后调用 routing skill，由 routing 决定 workflow 模式并启动对应 agent。
allowed-tools: Bash, Read, Task
argument-hint: 功能需求描述（支持 @文件路径 引用） --workflow <express|standard|deep|expert> --e2e [--feature-dir <dir>] [--branch-name <name>] [--knowledge-dir <dir>]
disable-model-invocation: false
---
# sdd

## 依赖说明

本技能依赖以下环境和组件：

### 环境变量

| 变量 | 用途 |
|------|------|
| `CLAUDE_PLUGIN_ROOT` | 插件根目录，定位 `init_omni_infra.sh` 与 `omni-infra/` 种子 |
| `CLAUDE_WORKING_DIR` | 当前工作区目录（可为 Git 仓库子目录），`.omni-infra` 落在此目录下 |
| `FEATURE_DIR` / `OMNISPEC_FEATURE_DIR` | 用户预设特性目录（可选，各阶段预解析；**最终以 create-branch 传参生效**） |
| `BRANCH_NAME` | 用户预设分支名（可选，各阶段预解析；**最终以 create-branch 传参生效**） |
| `KNOWLEDGE_DIR` | 用户预设私域知识库根目录（可选；私域知识检索用，与 DOC_DIR/反构文档库独立；默认 `${CLAUDE_WORKING_DIR}/omni-doc`） |

缺失时由 Agent 在步骤 1 补全（见下文步骤 1.2）。

### 前置条件

- 确保系统已安装 bash 与 git（可选）
- 确保 `init_omni_infra.sh` 具有执行权限
- 确保 `routing` 技能可用
- 确保 `Task(subagent_type="omni-dsdd:constitution")` 可用（`init_omni_infra` 返回 `1` 时**必须**调用）

## 用户输入

用户的功能需求描述，支持：
1. **直接文本**: 如 "添加用户登录功能"
2. **文件引用**: 如 `@doc/需求文档.md`，会自动读取文件内容

```text
$ARGUMENTS
```

> **重要**: 本 skill 负责展开 `@` 文件引用并透传，**不消费、不修改**功能描述内容。
> 如果 `$ARGUMENTS` 为空，在路由转发前询问用户输入功能描述。
>
> 支持可选参数 `--workflow <express|standard|deep|expert>`（或 `--workflow=<...>`），
> 用于显式指定 **workflow 模式**（见下文「workflow 与 agent」）。该参数由 `routing` 解析，本 skill 仅透传。
>
> 支持可选参数 `--feature-dir <dir>`、`--branch-name <name>`（或 `--feature-dir=<...>`、`--branch-name=<...>`），
> 与 shell `export` 的 `FEATURE_DIR`/`OMNISPEC_FEATURE_DIR`/`BRANCH_NAME` **合并解析**（步骤 3）：
> **有传参则以传参为准，无传参则以全局变量为准**；二者皆无则后续走 allocate。
> 解析后 `$ARGUMENTS` 仍原样透传 `routing`；**不在本阶段创建目录/分支**，物理生效由 `specify` → `create-branch` 传参完成。
>
> 支持可选参数 `--knowledge-dir <dir>`（或 `--knowledge-dir=<...>`），指定**私域知识库根目录**（供 constitution / spec-impact-analyze / design 的私域知识检索使用，与 DOC_DIR/反构文档库独立）。
> 与 shell `export` 的 `KNOWLEDGE_DIR` **合并解析**（步骤 3）：**有传参则以传参为准，无传参则以全局变量为准；二者皆无则默认 `${CLAUDE_WORKING_DIR}/omni-doc`**。
> 解析结果：① 步骤 2 透传给 `init_omni_infra.sh --knowledge-dir`（向该目录拷贝 `knowledge.config.yaml` + 写 `.omni-infra/knowledge.path` 标记）；② 步骤 3 `eval` 出会话级 `KNOWLEDGE_DIR`；③ `$ARGUMENTS` 中的 `--knowledge-dir` 原样透传 `routing`，最终由 `specify` 写入 `.runs/env.sh`。

## 流程控制（TaskList）

本 skill 采用 **TaskList 驱动**：进入执行时**必须** `TaskCreate` 建立以下 5 个任务（顺序即依赖关系），每完成一个步骤用 `TaskUpdate` 标记 `completed` 后再进入下一个；任一步骤失败则该任务保持 `in_progress` 并停止推进。

每步的**详细执行逻辑**存放在 `references/` 下，执行该步骤前用 `Read` 加载对应文档（路径基准：`${CLAUDE_PLUGIN_ROOT}/skills/sdd/references/<file>.md`）。按顺序逐项推进，**每完成一项立即勾选 `[x]`**，全部勾选后方可输出「SDD 执行完成」摘要；任一项不满足则保持 `[ ]` 并停止推进。

- [ ] **步骤 1** 环境变量就绪 — Read `references/env-vars.md` — `CLAUDE_PLUGIN_ROOT` / `CLAUDE_WORKING_DIR` 均为有效目录
- [ ] **步骤 2** SDD 环境初始化 — Read `references/infra-init.md` — `init_omni_infra.sh` 退出码为 `0` 或 `1`（`2` 则终止）；退出码 `1` 时已调用并等待 `Skill(constitution)` 返回
- [ ] **步骤 3** 特性上下文合并解析 — Read `references/feature-context.md` — `resolve-feature-context.sh --export` 已执行，会话变量已赋值；**未** `mkdir` / `git checkout` / 写 `.runs/env.sh`
- [ ] **步骤 4** 路由转发 — Read `references/routing-dispatch.md` — `@` 文件引用已展开（仅替换、不重写）；透传日志 `sdd 透传参数: <$ARGUMENTS>` 已打印；`routing` 已通过 Skill 工具调用
- [ ] **步骤 5** 完成性校验 — Read `references/completion-gate.md` — `workflow-gate.sh --check workflow-complete --record` 通过；未通过则**禁止**输出完成摘要

### 收尾检查（全部满足才报完成）

- [ ] 上述 5 项已全部勾选 `[x]`
- [ ] `routing` 已返回且 workflow 末段（implement / review / local-sandbox-fix）均已完成
- [ ] TaskList 中 5 个任务均已 `TaskUpdate` 标记 `completed`

---

## 步骤 1: 环境变量（执行 init 前）

**目的**：确保 `CLAUDE_PLUGIN_ROOT`、`CLAUDE_WORKING_DIR` 两项核心变量就绪。

```txt
Read ${CLAUDE_PLUGIN_ROOT}/skills/sdd/references/env-vars.md
```

执行该文档内步骤 1.1 检查 / 1.2 补全。

✅ 输出: `步骤 1 完成: 环境变量已就绪`, PLUGIN_ROOT=${CLAUDE_PLUGIN_ROOT}, WORKING_DIR=${CLAUDE_WORKING_DIR}

---

## 步骤 2: SDD 环境初始化

**目的**：复制 `omni-infra` 种子为工作区 `.omni-infra`，必要时触发 `constitution`，预提取 `--knowledge-dir`。

```txt
Read ${CLAUDE_PLUGIN_ROOT}/skills/sdd/references/infra-init.md
```

按文档执行 `init_omni_infra.sh` 并处理退出码 `0/1/2`。

✅ 输出: `步骤 2 完成: SDD 环境 {已就绪(0) / 需要 constitution(1) / 失败(2)}`, WORKING_DIR=${CLAUDE_WORKING_DIR}

---

## 步骤 3: 特性上下文合并解析（传参 + 全局变量，不生效）

**目的**：在调用 `routing` 前，一次完成 `FEATURE_DIR` / `BRANCH_NAME` / `KNOWLEDGE_DIR` 的传参与全局变量合并解析（仅会话赋值，不落盘）。

```txt
Read ${CLAUDE_PLUGIN_ROOT}/skills/sdd/references/feature-context.md
```

按文档调用 `resolve-feature-context.sh --export`。

✅ 输出: `步骤 3 完成: 特性上下文已合并解析（未创建目录/分支；preset 时已赋值待传递）`

---

## 步骤 4: 路由转发

**目的**：展开 `@` 文件引用，打印透传日志，调用 `routing`。

```txt
Read ${CLAUDE_PLUGIN_ROOT}/skills/sdd/references/routing-dispatch.md
```

按文档展开 `@` 引用、打印日志，并通过 Skill 工具调用 `routing "$ARGUMENTS"`。

✅ 输出: "步骤 4 完成: routing 已调用, 透传参数 <$ARGUMENTS>"

---

## 步骤 5: routing 返回后的完成性校验（强制）

**目的**：在输出任何「SDD 执行完成」摘要前，强制通过 `workflow-gate` 完成性校验，防止 workflow 半途而废被误报完成。

```txt
Read ${CLAUDE_PLUGIN_ROOT}/skills/sdd/references/completion-gate.md
```

按文档执行 `workflow-gate.sh --check workflow-complete --record`。

✅ 输出: "步骤 5 完成: workflow-complete gate 已通过或已阻断误报完成"

---

## 依赖链

- **数据传递**: 步骤 2 的输入 = 用户原始 `$ARGUMENTS`；步骤 4 在调用 routing 前会先展开 `@` 文件引用
- **文件引用处理**: sdd 读取文件内容并替换 `@引用` 为实际内容后传递给 routing
- **禁止重新生成**: 展开文件引用后，**必须**使用展开后的内容传递给 routing，不可重新生成或修改内容（仅替换文件引用）
- **交叉验证**: 透传前必须打印并写入上下文日志 `sdd 透传参数: <$ARGUMENTS>`

---

## workflow 与编排方式（重要）

- `express`、`standard`、`deep`、`expert` 是 **`flow_mode` 模式标识**，在路由侧用于选择 **对应的 YAML 工作流定义文件**（`workflows/${flow_mode}.yaml`），由 **`workflow-orchestrator` skill** 统一读取并按序编排，**不是** skill 名称，也**不应**当作 agent 去调用。
- 多种模式与 **YAML 定义**的对应关系为：
  - `express` → **`workflows/express.yaml`**（7 阶段，跳过 clarify，含 local-sandbox-fix）
  - `standard` → **`workflows/standard.yaml`**（8 阶段，完整 specify/clarify/design，含 local-sandbox-fix）
  - `deep` → **`workflows/deep.yaml`**（9 阶段，specify 前增加 reverse-on-demand，含 local-sandbox-fix）
  - `expert` → **`workflows/expert.yaml`**（7 阶段，brainstorming 后经 brainstorming-sdd-bridge 转强结构 SDD 接口，跳过 design stage，直接衔接 tasks/implement/review/local-sandbox-fix）
- 进入某一 workflow 后，由 **`workflow-orchestrator` skill**（`Skill("workflow-orchestrator")`）读取 YAML 阶段定义并编排驱动后续步骤；编排器内按需调用各类 **skill**，不要把整条 express/standard/deep/expert 链路误理解为「调用名为 express 的 skill」或「调度对应 agent」。
- 与 **`skills/routing/SKILL.md`**、**`agents/complexity-analyzer.md`** 及 **`skills/workflow-orchestrator/SKILL.md`** 中的「workflow 模式与编排方式」约定一致，避免文档之间表述冲突。

## 关键规则

- **@ 文件引用展开**: 若 `$ARGUMENTS` 包含 `@` 开头的文件引用，必须先读取文件内容并替换引用，再传递给 routing（这是透传的前置步骤，不是修改意图）
- 展开后保持 `$ARGUMENTS` 原样透传到 `routing`（含 `--feature-dir`、`--branch-name`、`--workflow`、`--e2e`；旧输入中的 `--forced` 也会被 routing 兼容移除）
- 若用户携带 `--workflow`，当 `routing` 处于首次执行（无状态文件）或”从头开始”分支时使用该参数选择 **YAML 工作流定义**
- **`--feature-dir` / `--branch-name`** 与 `--workflow` / `--e2e` 一样原样透传；展开 `@` 引用时不得误删特性参数

## 用法说明

### `--workflow` 参数注释

- `--workflow` 可选值支持：`express`、`standard`、`deep`、`expert`（均为 **`flow_mode` 模式标识**，用于选择 YAML 工作流定义）
- 支持两种写法：`--workflow deep` 和 `--workflow=deep`
- 当参数生效时，`routing` 将直接路由到对应的 **YAML 工作流定义**并启动 `workflow-orchestrator` skill 执行，并跳过复杂度判定
- 若参数值非法，`routing` 需立即报错并提示可用取值
- 未传入 `--workflow` 时，保持原有动态判定行为（判定结果同样应映射到某一 **YAML 工作流定义**）
- 使用 `--workflow=expert` 时，routing / workflow-orchestrator 会自动使用内部 forced pending 写入语义；用户不需要额外输入 `--forced` 或 `--force`。

### `--e2e` 参数说明

- `--e2e` 为开关标志，启用后 specify 和 design 阶段会执行 E2E 测试设计
- 由于 sdd 透传所有参数给 routing，该参数会被 routing 正确解析和处理
- 支持两种写法：`--e2e` 和 `--e2e=true`

### 常用命令示例

```bash
/sdd 添加用户登录功能
/sdd 生成订单管理改造方案
/sdd 支持提供VPN服务化方案设计
/sdd 设计并实现多租户权限系统 --workflow deep
/sdd 在 api/user.go 增加 GetProfile 接口 --workflow=express
```

### `--workflow` 使用示例（含说明）

```bash
# 指定 deep：路由到 deep YAML 工作流，适合跨模块、需架构分析的大改动
/sdd 设计并实现多租户权限系统 --workflow deep

# 指定 standard：路由到 standard YAML 工作流（完整流程 specify/clarify/design/tasks/analyze/implement）
/sdd 增加订单导出并补齐异常处理 --workflow standard

# 指定 express：路由到 express YAML 工作流，适合小改动、快速直达
/sdd 在 api/user.go 增加 GetProfile 接口 --workflow=express

# 不指定 workflow：按现有规则自动判定
/sdd 优化用户登录体验并补充必要埋点

# 启用 E2E 测试设计
/sdd 实现用户登录功能 --e2e
/sdd 设计订单管理模块 --workflow standard --e2e
/sdd 复位触发条件修改为仅requested --workflow=expert
/sdd 添加登录 --feature-dir 001-example
/sdd 添加登录 --branch-name 001-example
/sdd 添加登录 --feature-dir changes/001-example --branch-name 001-example --workflow express

# 指定私域知识库目录（私域知识检索用，与反构文档库 DOC_DIR 独立）
/sdd 添加登录 --knowledge-dir ./my-kb
/sdd 添加登录 --knowledge-dir /abs/path/to/knowledge
/sdd 设计多租户权限 --workflow deep --knowledge-dir changes/001-example/kb
```

### `--knowledge-dir` 与 export 全局变量

私域知识库路径合并规则：**`--knowledge-dir` CLI > `KNOWLEDGE_DIR` export > 默认 `${CLAUDE_WORKING_DIR}/omni-doc`**。与 `--feature-dir`/`--branch-name` 不同，KNOWLEDGE_DIR 始终有值（缺省 omni-doc），不存在 allocate。物理落盘由 `specify` 写入 `.runs/env.sh`（`export KNOWLEDGE_DIR`）；constitution 因早于 specify 执行，改读 `.omni-infra/knowledge.path` 标记文件。

```bash
# 方式一：CLI 参数
/sdd 添加登录 --knowledge-dir ./my-kb

# 方式二：export（当前 shell 会话有效，适合续跑）
export KNOWLEDGE_DIR="${PWD}/my-kb"
/sdd 继续完善登录

# 两种方式同时存在：参数覆盖 export
export KNOWLEDGE_DIR="${PWD}/old-kb"
/sdd 添加登录 --knowledge-dir ./new-kb   # → 使用 ./new-kb

# 不传也不 export：默认 ${CLAUDE_WORKING_DIR}/omni-doc
/sdd 添加登录
```

#### 持久化（推荐：免每次 export / 传参）

不想每次 `export` 或带 `--knowledge-dir`，可用 knowledge-retrieval 的 `kb-config` 一次性写入 shell 配置（默认 `~/.bashrc`）：

```bash
PYTHONPATH="${CLAUDE_SKILL_DIR}" python -m scripts.cli kb-config set /abs/path/to/your-kb
PYTHONPATH="${CLAUDE_SKILL_DIR}" python -m scripts.cli kb-config show    # 查看持久化值与当前生效值
PYTHONPATH="${CLAUDE_SKILL_DIR}" python -m scripts.cli kb-config unset   # 删除持久化
```

设置后**新开终端**（或 `source ~/.bashrc`），`KNOWLEDGE_DIR` 全局生效，`/sdd` 自动使用，无需任何参数。优先级链不变：`--knowledge-dir`(本次传参) > `KNOWLEDGE_DIR`(`~/.bashrc`) > 默认 `omni-doc`。zsh 用户加 `--shell-file ~/.zshrc`。

### `--feature-dir` / `--branch-name` 与 export 全局变量

全链路合并规则（**权威定义见步骤 3**）：`有传参 → 传参 > 无传参 → export > 推导 > allocate`。物理生效仅 `specify` → `create-branch`；`routing`/`workflow` 沿用步骤 3 会话赋值，不重复解析。

```bash
# 方式一：CLI 参数
/sdd 添加登录 --feature-dir changes/001-example --branch-name 001-example

# 方式二：export（当前 shell 会话有效，适合续跑）
export FEATURE_DIR="changes/001-example"
export BRANCH_NAME="001-example"
/sdd 继续完善登录

# 只 export 一个变量，另一个由 specify 步骤 1 自动补全
export FEATURE_DIR="001-example"          # → BRANCH_NAME=001-example
/sdd 继续完善

export BRANCH_NAME="001-example"          # → FEATURE_DIR=.../changes/001-example
/specify 补充场景

# 两种方式同时存在：参数覆盖 export
export FEATURE_DIR="changes/002-old"
export BRANCH_NAME="002-old"
/sdd 添加登录 --feature-dir 001-example --branch-name 001-example
# → 使用 001-example，忽略 export 中的 002-old

# 环境变量之间：OMNISPEC_FEATURE_DIR 优先于 FEATURE_DIR（仅在不传 CLI 时）
export OMNISPEC_FEATURE_DIR="/abs/path/changes/001-example"
export BRANCH_NAME="001-example"
/sdd 继续完善

# 清除变量后走自动 allocate
unset FEATURE_DIR OMNISPEC_FEATURE_DIR BRANCH_NAME
/sdd 全新功能：添加用户登录
```
