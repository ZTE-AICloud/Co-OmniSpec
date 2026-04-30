# Co-OmniSpec 用户指南

本文说明完整的规范驱动开发工作流及所有 Co-OmniSpec 命令。

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
- **`/reverse`** — 从代码逆向生成规范与上下文（如棕地项目）。

---

## 三种工作流与 Routing 用法

Co-OmniSpec 提供三种工作流模式，由 `routing` 路由并交给对应 workflow **agent** 执行（不是同名 skill）：

| flow_mode | workflow agent | 适用场景 | 关键差异 |
|----------|----------------|----------|----------|
| `express` | `express-workflow` | 改动小、需求清晰 | 跳过 `clarify`，减少迭代轮次 |
| `standard` | `standard-workflow` | 中等复杂度功能 | 完整执行 `specify -> clarify -> design` |
| `deep` | `deep-workflow` | 大规模或架构型改动 | 在 `specify` 前增加 `reverse-on-demand` |

Routing 行为说明：

- **默认路径**：`routing` 调用 `complexity-analyzer` 自动判定 `express`/`standard`/`deep`。
- **强制路径**：通过 `--workflow <express|standard|deep>` 指定工作流，跳过复杂度判定。
- **E2E 开关**：通过 `--e2e` 启用 `specify` 与 `design` 阶段的 E2E 测试设计。

Routing 参数示例：

```text
/routing Build a simple dashboard for internal metrics.
/routing --workflow standard Build a partner API with auth and rate limiting.
/routing --workflow deep --e2e Refactor order orchestration and align cross-service contracts.
```

关键约定：

- `express|standard|deep` 仅是 `flow_mode` 取值，不是可直接调用的 skill 名。
- `routing` 是 skill；`express-workflow` / `standard-workflow` / `deep-workflow` 是 agent。
- 在 `deep` 模式中，同一份 `$ARGUMENTS` 会同时用于按需反构（`reverse-on-demand`）的 requirement 输入，以及后续 `specify` 的功能描述输入。

---

## 核心命令

### `/constitution`

**作用：** 创建或更新项目的 governing 原则与开发指南。

**输入（可选）：** 用自然语言描述你希望的原则（如代码质量、测试、用户体验、性能）。

**产出：**

- 创建或更新 `.specify/memory/constitution.md`。
- 依赖模板保持同步。

**使用时机：** 项目开始时执行一次，或当项目级规则变更时。

---

### `/specify`

**作用：** 将简短的功能描述转化为完整规范。

**输入：** 一段（或多段）描述你要做的“什么”和“为什么”，此阶段不必写技术栈。

**产出：**

- 新建特性分支（如 `001-feature-name`）。
- `changes/<分支名>/spec.md` — 主规范。
- `changes/<分支名>/context.md` — 来自既有文档的波及/上下文（若有）。
- `changes/<分支名>/checklists/requirements.md` — 需求检查清单（会迭代更新）。

**过程概览：** 技能会创建分支、执行波及分析（若存在 DOC_DIR/specs）、用模板和上下文填写 spec，再调用质量检查技能生成并验证需求检查清单。

**下一步：** 若规范有不清楚处可运行 `/clarify`，否则可直接运行 `/design` 生成技术计划。

---

### `/clarify`

**作用：** 通过少量针对性问题消除当前规范中的模糊，并将答案写回规范。

**输入（可选）：** 补充说明或希望重点澄清的方面。

**使用时机：** 在 `/specify` 之后、`/design` 之前，尤其当规范中存在 `[NEEDS CLARIFICATION]` 或表述含糊时。

---

### `/design`

**作用：** 根据规范生成技术实施计划与设计制品。

**输入：** 技术栈与架构选择（如运行时、框架、数据库、测试、目标平台）。

**产出（在同一功能目录下）：**

- `design.md` — 实施计划。
- `research.md` — 研究笔记（如版本、选型）。
- `data-model.md` — 数据模型。
- `quickstart.md` — 功能快速上手。
- `contracts/` — 按需的 API/契约说明。

**使用时机：** 规范（及可选的澄清）完成后。设计需符合 `.specify/memory/constitution.md`。

---

### `/tasks`

**作用：** 将设计拆解为带依赖顺序的任务并写入 `tasks.md`。

**输入：** 通常无需输入；技能会读取当前功能的 design 与 spec。

**产出：**

- `changes/<分支名>/tasks.md` — 按依赖排序的任务列表，可含并行标记。

**使用时机：** 在 `/design` 之后。可接着运行 `/analyze` 做一致性检查再实施。

---

### `/implement`

**作用：** 按 `tasks.md` 中的定义依次执行任务。

**输入（可选）：** 约束或说明（如“只做任务 1–3”“跳过测试”）。

**过程：** 技能读取 `tasks.md`，解析顺序与依赖，逐条执行任务（如创建文件、执行命令），可能调用 CLI（如 `npm`、`dotnet`）。

**使用时机：** 在 `tasks.md` 就绪且（可选）已运行 `/analyze` 之后。请确保所需开发环境已安装。

---

## 可选命令

### `/analyze`

**作用：** 对 `spec.md`、`design.md`、`tasks.md` 做非破坏性的一致性与质量分析。

**使用时机：** 在 `/tasks` 之后、`/implement` 之前，用于发现遗漏、矛盾或引用不清。

---

### `/checklist`

**作用：** 生成自定义检查清单，用于验证需求完整性、清晰度与一致性（类似“对英文规范的单元测试”）。

**输入（可选）：** 希望检查清单重点覆盖的方面。

**使用时机：** 需要为当前功能增加一层需求质量把关时。

---

### `/reverse`

**作用：** 从现有代码库逆向出完整规范与上下文（需求、场景、实体、接口等）。

**模式：** `reverse` 支持三种模式：

| 模式 | 说明 | 典型命令形态 |
|------|------|--------------|
| **全量** | 对整个代码库做完整逆向，生成端到端制品。 | `/reverse --target all` |
| **on-demand** | 针对单个需求或变更诉求做按需逆向。 | `/reverse --target on-demand --requirement "<需求描述或文件>"` |
| **按要素** | 仅逆向某一类要素（需求/场景/接口/规则等）。 | `/reverse --target <element>` |

常见要素目标包括：`requirements`、`system-contexts`、`scenarios`、`logic_architecture`、`interfaces`、`external-interfaces`、`entities`、`rules`、`functions`。

**输入（可选）：** 范围、目标模式与侧重点（如需求文本/文件、子目录或模块）。

**产出：** 生成或填充规范与上下文制品，便于后续用 `/design` 或 `/specify` 继续演进。

**使用时机：** 棕地项目或需要先文档化现有行为再修改时。

---

## 功能目录结构

完成 specify → design → tasks 后，典型功能目录如下：

```text
changes/001-feature-name/
├── spec.md              # 来自 /specify
├── context.md           # 来自 /specify（波及分析）
├── design.md            # 来自 /design
├── research.md           # 来自 /design
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
| **DOC_DIR** | 既有规格/文档根目录，用于波及分析与逆向。默认常为 `omni-doc`。可通过 `.specify/config` 或环境变量设置。 |
| **SPECIFY_FEATURE** | 在不使用 Git 分支时覆盖功能检测。设为功能目录名（如 `001-photo-albums`），以便 `/design` 及后续命令确定当前功能。 |
| **`.specify/config`** | 可选配置文件，用于路径与默认值。 |
| **`.specify/memory/constitution.md`** | 项目章程；可手动编辑或通过 `/constitution` 更新。 |

脚本位于 `.specify/scripts/bash/` 与 `.specify/scripts/powershell/`，由技能调用；也可手动执行以便排查问题。

---

## 常见问题

### Claude Code 里看不到命令

- 确认当前环境已安装对应市场与插件。
- 运行 `/plugin marketplace list`（或 `/market list`）并确认存在 `CoMind-plugins`。
- 若仍不可见，重新打开项目会话后再检查。

### 没有创建分支或功能目录

- 确认 Git 可用且当前目录是有效仓库。
- 可手动执行创建分支脚本查看报错：
  - Bash: `bash .claude/skills/omni-create-branch/scripts/bash/create-new-feature.sh --json --short-name "my-feature"`
  - PowerShell: `pwsh -File .claude/skills/omni-create-branch/scripts/powershell/create-new-feature.ps1 --json --short-name "my-feature"`

### 设计或任务针对错误的功能

- 若未在特性分支上，设置 `SPECIFY_FEATURE` 为功能目录名（如 `001-photo-albums`）。
- 确保 Agent 在仓库根目录执行，以便正确解析 `FEATURE_DIR` 与路径。

### 插件安装失败

- 运行 `/plugin marketplace list`（或 `/market list`）确认是否存在 `CoMind-plugins`。
- 如不存在，重新添加市场：`/plugin marketplace add ZTE-AICloud/Co-OmniSpec`。
- 重新安装插件：`/plugin install omni@CoMind-plugins`。
- 命令行模式可执行：
  - `claude plugin marketplace add ZTE-AICloud/Co-OmniSpec`
  - `claude plugin install omni@CoMind-plugins`

### 实施阶段执行了错误命令或失败

- 检查 `tasks.md` 是否存在且格式正确。
- 确认所需工具（如 `npm`、`dotnet`、`python`）已安装且在 `PATH` 中。
- 可单独执行某一任务以查看具体命令与报错。


