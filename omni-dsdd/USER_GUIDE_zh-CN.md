# Co-OmniSpec 用户指南

本文说明完整的规范驱动开发工作流与所有 Co-OmniSpec 命令。`omni-dsdd` 负责规划链路；逆向工程能力由同市场的 [`omni-reverse`](../omni-reverse/README.md) 提供。

> **English** — See [USER_GUIDE.md](USER_GUIDE.md) for the English version.

---

## 目录

- [工作流概览](#工作流概览)
- [三种工作流与 Routing 用法](#三种工作流与-routing-用法)
- [核心命令](#核心命令)
- [可选命令](#可选命令)
- [功能目录结构](#功能目录结构)
- [环境与配置](#环境与配置)
- [常见问题](#常见问题)

---

## 工作流概览

推荐顺序：

```text
1. /constitution        → 设定项目原则
2. /specify             → 从功能描述生成规范
3. /clarify             → （可选）消除规范歧义
4. /design              → 生成技术计划与设计制品
5. /tasks               → 根据设计生成 tasks.md
6. /analyze             → （可选）跨制品一致性检查
7. /implement           → 按顺序执行任务
```

随时可用的可选命令：

- **`/checklist`** — 生成自定义需求检查清单。
- **`/reverse`** — 从代码逆向生成规范与上下文（需先安装 [`omni-reverse`](../omni-reverse/README.md)）。
- **`/knowledge-retrieval [--build]`** — 构建或更新 `specify` 等环节所需的知识索引。

---

## 三种工作流与 Routing 用法

`omni-dsdd` 提供三种工作流模式，由 `routing` 路由并交给 `workflow-orchestrator` skill 执行（读取对应的 YAML 工作流定义）：

| flow_mode | YAML 定义 | 适用场景 | 关键差异 |
|-----------|-----------|----------|----------|
| `express` | `workflows/express.yaml` | 改动小、需求清晰 | 跳过 `clarify`，减少迭代轮次。 |
| `standard` | `workflows/standard.yaml` | 中等复杂度功能 | 完整执行 `specify → clarify → design`。 |
| `deep` | `workflows/deep.yaml` | 大规模或架构型改动 | 在 `specify` 前增加 `reverse-on-demand`。 |

Routing 行为说明：

- **默认路径**：`routing` 调用 `complexity-analyzer` 自动判定 `express` / `standard` / `deep`。
- **强制路径**：通过 `--workflow <express|standard|deep>` 指定工作流，跳过复杂度判定。
- **E2E 开关**：通过 `--e2e` 启用 `specify` 与 `design` 阶段的 E2E 测试设计。

Routing 参数示例：

```text
/routing 做一个小型的内部指标看板。
/routing --workflow standard 做一个带鉴权与限流的对客 API。
/routing --workflow deep --e2e 重构订单编排，并对齐跨服务契约。
```

关键约定：

- `express | standard | deep` 仅是 `flow_mode` 取值，不是可直接调用的 skill。
- `routing` 与 `workflow-orchestrator` 是 skill；`express | standard | deep` 用于选择对应的 YAML 定义。
- 在 `deep` 模式中，同一份 `$ARGUMENTS` 会同时用于 `reverse-on-demand` 的 requirement 输入，以及后续 `specify` 的功能描述输入。
- `expert` 是定义在 `workflows/expert.yaml` 的内部评审变体，**不作为公开 flow_mode**。

---

## 核心命令

### `/constitution`

**作用：** 创建或更新项目的治理原则与开发指南。

**输入（可选）：** 用自然语言描述你希望的原则（如代码质量、测试、用户体验、性能）。

**产出：**

- 创建或更新 `.omni-infra/memory/constitution.md`；
- 依赖模板保持同步。

**使用时机：** 项目开始时执行一次，或当项目级规则变更时。

### `/specify`

**作用：** 将简短的功能描述转化为完整规范。

**输入：** 一段（或多段）描述你要做的「什么」与「为什么」，此阶段不必写技术栈。

**产出：**

- 新建特性分支（如 `001-feature-name`）。
- `changes/<分支名>/spec.md` — 主规范。
- `changes/<分支名>/context.md` — 来自既有文档的波及/上下文（若有）。
- `changes/<分支名>/checklists/requirements.md` — 需求检查清单（迭代更新）。

**过程概览：** 技能创建分支、执行波及分析（若存在 `DOC_DIR`/specs）、用模板和上下文填充 spec，再由质量检查技能生成并验证需求检查清单。

**下一步：** 若规范中有不清楚的地方，可运行 `/clarify`；否则运行 `/design` 生成技术计划。

### `/clarify`

**作用：** 通过少量针对性问题消除当前规范中的模糊，并将答案写回规范。

**输入（可选）：** 补充说明或希望重点澄清的方面。

**使用时机：** 在 `/specify` 之后、`/design` 之前；尤其当规范中存在 `[NEEDS CLARIFICATION]` 或表述含糊时。

### `/design`

**作用：** 根据规范生成技术实施计划与设计制品。

**输入：** 技术栈与架构选择（如运行时、框架、数据库、测试、目标平台）。

**产出（在同一功能目录下）：**

- `design.md` — 实施计划；
- `research.md` — 研究笔记（如版本、选型）；
- `data-model.md` — 数据模型；
- `quickstart.md` — 功能快速上手；
- `contracts/` — 按需的 API/契约说明。

**使用时机：** 规范（及可选的澄清）完成后。设计需符合 `.omni-infra/memory/constitution.md`。

### `/tasks`

**作用：** 将设计拆解为按依赖排序的任务并写入 `tasks.md`。

**输入：** 通常无需输入；技能会读取当前功能的 design 与 spec。

**产出：**

- `changes/<分支名>/tasks.md` — 按依赖排序的任务列表，可含并行标记。

**使用时机：** 在 `/design` 之后；可接着运行 `/analyze` 做一致性检查再实施。

### `/implement`

**作用：** 按 `tasks.md` 中的定义依次执行任务。

**输入（可选）：** 约束或说明（如「只做任务 1–3」「跳过测试」）。

**过程：** 技能读取 `tasks.md`，解析顺序与依赖，逐条执行任务（如创建文件、执行命令），可能调用 CLI（如 `npm`、`dotnet`）。

**使用时机：** 在 `tasks.md` 就绪且（可选）已运行 `/analyze` 之后。请确保所需开发环境已安装。

---

## 可选命令

### `/analyze`

**作用：** 对 `spec.md`、`design.md`、`tasks.md` 做非破坏性的一致性与质量分析。

**使用时机：** 在 `/tasks` 之后、`/implement` 之前。用于发现遗漏、矛盾或引用不清。

### `/checklist`

**作用：** 生成自定义检查清单，用于验证需求完整性、清晰度与一致性（「对英文规范的单元测试」）。

**输入（可选）：** 希望检查清单重点覆盖的方面。

**使用时机：** 需要为当前功能增加一层需求质量把关时。

### `/reverse`

**作用：** 从现有代码库逆向出完整规范与上下文（需求、场景、实体、接口等）。

**模式：** `/reverse` 支持三种模式：

| 模式 | 说明 | 典型命令 |
|------|------|----------|
| **全量** | 对整个代码库做完整逆向，生成端到端制品。 | `/reverse --target all` |
| **按需** | 针对单个需求或变更诉求做按需逆向。 | `/reverse --target on-demand --requirement "<需求描述或文件>"` |
| **按要素** | 仅逆向某一类要素（需求/场景/接口/规则等）。 | `/reverse --target <element>` |

常见要素目标：`requirements`、`system-contexts`、`scenarios`、`logic_architecture`、`interfaces`、`external-interfaces`、`entities`、`rules`、`functions`。

**输入（可选）：** 范围、目标模式与侧重点（如需求文本/文件、子目录或模块）。

**产出：** 生成或填充规范与上下文制品，便于后续用 `/design` 或 `/specify` 继续演进。

**使用时机：** 棕地项目或需要先文档化现有行为再修改时。

> 真正的反构技能（`reverse`、`reverse-orchestration`、`reverse-shared`、`reverse-logic-architecture`、`reverse-deep-logic-architecture`、`reverse-interfaces`、`reverse-external-interfaces`、`reverse-functions`、`reverse-entities`、`reverse-scenarios`、`reverse-requirements`、`reverse-rules`）归属于同市场的 [`omni-reverse`](../omni-reverse/README.md) 插件，请一并安装。

### `/knowledge-retrieval [--build]`

**作用：** 对存量文档、代码进行知识抽取与索引构建，可提升 `specify` 等环节的存量知识获取能力。

**使用时机：** 棕地项目期望把存量文档与代码用于知识消费。

**使用说明：**

1. 执行 `/knowledge-retrieval --build [raw_knowledge_dir]` 进行抽取与构建；不指定目录时默认为当前目录 `.` 下所有内容（**推荐不指定目录，将代码与文档统一放在项目根下**）。
2. 构建完成后，`knowledge-retrieval` SKILL 已默认嵌入 `specify` 等需要文档检索的活动，无需额外配置；调用时将查询诉求传入即可。
3. 文档/代码产生变更时，执行 `/knowledge-retrieval --build --update` 进行增量构建。
4. 需要强制重建时，执行 `/knowledge-retrieval --build --force`（会先删除已有索引）。

---

## 功能目录结构

完成 `specify → design → tasks` 后，典型功能目录如下：

```text
changes/001-feature-name/
├── spec.md              # 来自 /specify
├── context.md           # 来自 /specify（波及分析）
├── design.md            # 来自 /design
├── research.md          # 来自 /design
├── data-model.md        # 来自 /design
├── quickstart.md        # 来自 /design
├── tasks.md             # 来自 /tasks
├── contracts/           # 来自 /design（按需）
│   ├── api-spec.json
│   └── ...
└── checklists/
    └── requirements.md  # 来自 /specify + spec-quality-check
```

路径均相对于仓库根目录。分支名通常与目录名一致（如 `001-feature-name`）。

---

## 环境与配置

| 项 | 说明 |
|----|------|
| **DOC_DIR** | 既有规格/文档根目录，用于波及分析与逆向。默认常为 `omni-doc`。可通过 `.omni-infra/config` 或环境变量设置。 |
| **SPECIFY_FEATURE** | 在不使用 Git 分支时覆盖功能检测。设为功能目录名（如 `001-photo-albums`），以便 `/design` 及后续命令确定当前功能。 |
| **`.omni-infra/config`** | 可选配置文件，用于路径与默认值。 |
| **`.omni-infra/memory/constitution.md`** | 项目章程；可手动编辑或通过 `/constitution` 更新。 |

脚本位于 `.omni-infra/scripts/bash/` 与 `.omni-infra/scripts/powershell/`，由技能调用；也可手动执行以便排查问题。

`omni-reverse` 通过 `scripts/resolve-dsdd-root.{sh, py, ps1}` 解析共享的 `.omni-infra/` 根目录——因此两个插件必须安装在同一 `CoMind-plugins` 市场下。

---

## 常见问题

### Claude Code 里看不到命令

- 确认当前环境已安装市场与两个插件：`/plugin marketplace list`（或 `/market list`）应能列出 `CoMind-plugins`；`/plugin` 应同时出现 `omni-dsdd` 与 `omni-reverse`。
- 若仍不可见，重新打开项目会话后再检查。

### 没有创建分支或功能目录

- 确认 Git 可用且当前目录是有效仓库。
- 可手动运行创建分支脚本查看错误：`create-branch` skill 下的 `scripts/.../create-new-feature.sh`（或 PowerShell 等价）传入 `--json --short-name "my-feature"` 即可查看详细输出。

### 设计或任务针对错误的功能

- 若不在特性分支上，设置 `SPECIFY_FEATURE` 为功能目录名（如 `001-photo-albums`）。
- 确保 Agent 在仓库根目录执行，以便正确解析 `FEATURE_DIR` 与路径。

### 插件安装失败

- 运行 `/plugin marketplace list`（或 `/market list`）确认 `CoMind-plugins` 是否存在。
- 如缺失，重新添加市场：`/plugin marketplace add ZTE-AICloud/Co-OmniSpec`。
- 重新安装插件：
  - `/plugin install omni-dsdd@CoMind-plugins`
  - `/plugin install omni-reverse@CoMind-plugins`
- CLI 模式：
  - `claude plugin marketplace add ZTE-AICloud/Co-OmniSpec`
  - `claude plugin install omni-dsdd@CoMind-plugins`
  - `claude plugin install omni-reverse@CoMind-plugins`

### `/reverse` 报「未找到 omni-dsdd」

- `omni-reverse` 依赖 `omni-dsdd` 提供的共享脚本与 `.omni-infra/` 资产。请在同一 `CoMind-plugins` 市场下安装 `omni-dsdd`，再重新执行 `/reverse`。

### 实施阶段执行了错误命令或失败

- 检查 `tasks.md` 是否存在且格式正确。
- 确认所需工具（如 `npm`、`dotnet`、`python`）已安装且在 `PATH` 中。
- 可单独执行某一任务以查看具体命令与报错。
