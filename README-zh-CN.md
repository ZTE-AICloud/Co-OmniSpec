# Co-OmniSpec

**借助[规范驱动开发](https://github.com/github/spec-kit)，更快交付高质量软件。**

Co-OmniSpec 是一套开源工具集，把开发意图转化为结构化的规范、设计制品与按依赖排序的任务，并引导 AI 编程助手完成实施。它基于 [GitHub Spec Kit](https://github.com/github/spec-kit) 进行本地化与扩展，并面向 Claude Code 等 Agent 环境进行优化。

Co-OmniSpec 在 `CoMind-plugins` 市场下以两个插件同时发布：**`omni-dsdd`** 负责规范驱动开发流水线；**`omni-reverse`** 负责反向工程能力。两者必须并列安装。

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue" alt="License"/></a>
</p>

---

## 目录

1. [项目简介与规范驱动开发](#1-项目简介与规范驱动开发)
2. [双插件职责对照](#2-双插件职责对照)
3. [前置依赖](#3-前置依赖)
4. [安装命令](#4-安装命令)
5. [首次使用流程](#5-首次使用流程)
6. [工作流地图（express / standard / deep / expert）](#6-工作流地图)
7. [逆向能力使用](#7-逆向能力使用)
8. [仓库目录结构](#8-仓库目录结构)
9. [故障排查](#9-故障排查)
10. [贡献与安全](#10-贡献与安全)
11. [致谢与许可证](#11-致谢与许可证)

> **English** — See [README.md](README.md) for the English readme.

---

## 1. 项目简介与规范驱动开发

规范驱动开发**颠覆**「先写代码再补文档」的传统方式：**用规范驱动实现**。先用自然语言描述「做什么」与「为什么」，再由 AI 把它们转译为结构化的规范、设计说明、按依赖排序的任务，最终产出代码。

Co-OmniSpec 提供的能力：

- 项目级**章程（constitution）** 将每一步锚定在统一的原则上。
- 可重复执行的流水线：`constitution → specify → clarify → design → tasks → implement → archive`。
- 通过**逆向**为已有代码生成规范，天然支持**棕地**项目。
- 在每个阶段都有**质量门**（clarify、analyze、checklist、review）。

完整背景与设计说明请参阅：

---

## 2. 双插件职责对照

Co-OmniSpec 是**两个插件**共用一个市场。它们共享运行时资产，但分别承担工作流的两端：

| 插件 | 市场名 | 定位 | 插件内的核心 skill | 共享资产 |
|------|--------|------|-------------------|----------|
| **`omni-dsdd`** | `CoMind-plugins` | 规范驱动开发流水线：脚手架、斜杠命令、共享模板与脚本、工作流 YAML。 | `specify`、`clarify`、`design`、`tasks`、`implement`、`archive`、`analyze`、`checklist`、`constitution`、`routing`、`workflow-orchestrator`、`knowledge-retrieval`、`create-branch`、`sdd`，以及按需逆向入口 `reverse-on-demand`。 | 持有 `.omni-infra/`（config、memory、metamodel、scripts、templates）。 |
| **`omni-reverse`** | `CoMind-plugins` | 把已有代码逆向为 SDD 制品。 | `reverse`、`reverse-orchestration`、`reverse-shared`、`reverse-logic-architecture`、`reverse-deep-logic-architecture`、`reverse-interfaces`、`reverse-external-interfaces`、`reverse-functions`、`reverse-entities`、`reverse-scenarios`、`reverse-requirements`、`reverse-rules` 共 12 个 skill。 | 依赖 `omni-dsdd`；通过 `scripts/resolve-dsdd-root.{sh, py, ps1}` 解析 `${DSDD}`。 |

两个插件必须并列安装：`omni-reverse` 缺了 `omni-dsdd` 就无法运行；当目标工程已有代码时，DSDD 流水线也会受益于 `omni-reverse`。

---

## 3. 前置依赖

| 要求 | 说明 |
|------|------|
| **Claude Code** | [code.claude.com](https://code.claude.com/)，需支持插件市场。 |
| **Git** | 用于特性分支与 `changes/` 目录。 |
| **Bash 或 PowerShell** | 用于执行 `.omni-infra/scripts/` 中的共享脚本。 |
| **Node + pnpm（可选）** | 仅在本地对插件自身 skill 进行校验时使用（在 `omni-dsdd/` 目录下执行 `pnpm validate`）；详见 [CONTRIBUTING.md](CONTRIBUTING.md)。 |

---

## 4. 安装命令

添加市场并安装两个插件：

```text
/plugin marketplace add ZTE-AICloud/Co-OmniSpec
/plugin install omni-dsdd@CoMind-plugins
/plugin install omni-reverse@CoMind-plugins
```

第一条命令也可用简写 `/market add ZTE-AICloud/Co-OmniSpec`。

CLI 形式（适合非交互式或 CI 场景）：

```bash
claude plugin marketplace add ZTE-AICloud/Co-OmniSpec
claude plugin install omni-dsdd@CoMind-plugins
claude plugin install omni-reverse@CoMind-plugins
```

安装后请验证：

1. `/plugin marketplace list`（或 `/market list`）—— `CoMind-plugins` 已注册。
2. `/plugin`（Discover）—— `omni-dsdd` 与 `omni-reverse` 都已列出并启用。
3. 在项目 AI 对话中确认能看到 `/constitution`、`/specify`、`/reverse`、`/routing`。

如缺失其中任一项，重新执行对应的 `install` 命令。两个插件的子文档（[omni-dsdd/README.md](omni-dsdd/README.md)、
[omni-reverse/README.md](omni-reverse/README.md)）对相同命令有更详细说明。

---

## 5. 首次使用流程

仅使用 `omni-dsdd` 的最小首次流程：

1. **章程** —— 运行 `/constitution`，描述你希望的原则（代码质量、测试标准、用户体验、性能等）。Agent 创建或更新 `.omni-infra/memory/constitution.md`。
2. **规格** —— 运行 `/specify`，输入功能描述（「做什么」与「为什么」）。Agent 创建特性分支并生成 `changes/<分支名>/{spec.md, context.md, checklists/requirements.md}`。
3. **澄清**（建议）—— 运行 `/clarify` 消除歧义，并把答案写回规范。
4. **设计** —— 运行 `/design` 并输入技术栈，生成 `design.md`、`research.md`、`data-model.md`、`quickstart.md` 及按需的 `contracts/`。
5. **任务** —— 运行 `/tasks`，按依赖顺序生成 `tasks.md`。
6. **实施** —— 运行 `/implement` 按顺序执行任务。
7. **归档**（完成后建议执行）—— 运行 `/archive` 归档/回流已完成特性。

若目标工程已有代码，请先安装 `omni-reverse`，从步骤 0 开始：`/reverse` 先文档化现有行为，再进入步骤 1（详见 [第 7 节](#7-逆向能力使用)）。

详细教程见 [omni-dsdd/GETTING_STARTED_zh-CN.md](omni-dsdd/GETTING_STARTED_zh-CN.md)；完整命令参考见 [omni-dsdd/USER_GUIDE_zh-CN.md](omni-dsdd/USER_GUIDE_zh-CN.md)。

---

## 6. 工作流地图

`routing` skill 按复杂度选择三种 YAML 之一，由 `workflow-orchestrator` 执行：

| flow_mode | YAML 定义 | 适用场景 | 关键差异 |
|-----------|-----------|----------|----------|
| `express` | `omni-dsdd/workflows/express.yaml` | 改动小、需求清晰 | 跳过 `clarify`，减少迭代轮次。 |
| `standard` | `omni-dsdd/workflows/standard.yaml` | 中等复杂度功能 | 完整执行 `specify → clarify → design`。 |
| `deep` | `omni-dsdd/workflows/deep.yaml` | 大规模或架构型改动 | 在 `specify` 前增加 `reverse-on-demand`。 |
| `expert` | `omni-dsdd/workflows/expert.yaml` | 内部评审变体 | **不作为公开 `flow_mode`**，不对外暴露。 |

可让 `routing` 按复杂度自动判定，也可通过 `--workflow <express|standard|deep>` 强制指定。若需在 `specify` / `design` 阶段启用 E2E 测试设计，附加 `--e2e`。示例：

```text
/routing 做一个小型的内部指标看板。
/routing --workflow standard 做一个带鉴权与限流的对客 API。
/routing --workflow deep --e2e 重构订单编排，并对齐跨服务契约。
```

末尾的 `express|standard|deep` 是 `flow_mode` 取值，不是 skill 名；YAML 文件位于 `omni-dsdd/workflows/`。

---

## 7. 逆向能力使用

逆向工程集中在 **`omni-reverse`** 插件。适用于棕地项目，或想在改动前先建立既有代码规范的场景。

入口（由 `omni-reverse` 中的 `reverse` skill 调度）：

- **全量** —— `/reverse --target all`
- **按需** —— `/reverse --target on-demand --requirement "<需求描述或文件>"`
- **按要素** —— `/reverse --target requirements|scenarios|interfaces|rules|...`

`omni-reverse` 提供 12 个专用 skill：`reverse`、`reverse-orchestration`、`reverse-shared`、`reverse-logic-architecture`、`reverse-deep-logic-architecture`、`reverse-interfaces`、`reverse-external-interfaces`、`reverse-functions`、`reverse-entities`、`reverse-scenarios`、`reverse-requirements`、`reverse-rules`，分别产出对应的 SDD 制品。共享基础设施（路径、模板、脚本）由 `omni-dsdd` 的 `.omni-infra/` 提供。

完整参考见 [omni-reverse/README.md](omni-reverse/README.md)。

---

## 8. 仓库目录结构

```text
Co-OmniSpec/
├── .claude-plugin/
│   └── marketplace.json          # 在 CoMind-plugins 下注册两个插件
├── omni-dsdd/
│   ├── .claude-plugin/plugin.json
│   ├── agents/                   # AI 子代理（constitution、知识抽取等）
│   ├── hooks/                    # 生命周期钩子
│   ├── omni-infra/               # 共享 .omni-infra/ 资产
│   │   ├── config/
│   │   ├── memory/
│   │   ├── metamodel/
│   │   ├── scripts/
│   │   └── templates/
│   ├── scripts/                  # 基于 Node 的校验辅助
│   ├── skills/                   # 斜杠命令与工作流 skill
│   ├── workflows/                # express.yaml / standard.yaml / deep.yaml / expert.yaml
│   ├── README.md / README-zh-CN.md
│   ├── GETTING_STARTED.md / GETTING_STARTED_zh-CN.md
│   ├── USER_GUIDE.md / USER_GUIDE_zh-CN.md
│   ├── CHANGELOG.md
│   ├── LICENSE                   # 与根 LICENSE 字节相同
│   ├── package.json
│   └── pnpm-workspace.yaml
├── omni-reverse/
│   ├── .claude-plugin/plugin.json
│   ├── agents/                   # 逆向专属子代理
│   ├── scripts/                  # resolve-dsdd-root.{sh,py,ps1}
│   ├── skills/                   # 12 个反构 skill（见 omni-reverse/README.md）
│   ├── README.md
│   └── require.txt
├── README.md / README-zh-CN.md   # 本文档（中英文双版）
├── CONTRIBUTING.md
├── SECURITY.md
├── THIRD_PARTY_NOTICES.md
└── LICENSE                       # MIT，Copyright (c) 2026 ZTE-AICloud / ZTE
```

安装后，**目标工程**（AI 助手真正处理的代码项目）中会出现：

```text
你的项目/
├── .claude/
│   ├── commands/                 # OmniSpec 斜杠命令（来自 omni-dsdd）
│   └── skills/                   # skill（来自 omni-dsdd 与 omni-reverse）
├── .omni-infra/                  # 共享模板、脚本、记忆、元模型
│   ├── memory/constitution.md
│   ├── metamodel/
│   ├── scripts/                  # Bash / PowerShell 辅助脚本
│   └── templates/                # spec、design、tasks、checklist 模板
└── changes/                      # 功能目录（由 /specify 创建）
    └── 001-功能名/
        ├── spec.md
        ├── context.md
        ├── design.md
        ├── tasks.md
        └── checklists/
```

目标工程的 `.omni-infra/` 是两个插件共享的运行时目录。

---

## 9. 故障排查

### 看不到斜杠命令

- 确认市场已注册：`/plugin marketplace list`（或 `/market list`），应有 `CoMind-plugins`。
- 确认两个插件都已安装：`/plugin`（Discover），应同时出现 `omni-dsdd` 与 `omni-reverse`。
- 安装插件后重新打开项目会话。

### 插件安装失败

- 运行 `/plugin marketplace list`，如缺失 `CoMind-plugins`，重新添加：
  `/plugin marketplace add ZTE-AICloud/Co-OmniSpec`。
- 重新执行安装命令：
  `/plugin install omni-dsdd@CoMind-plugins`、`/plugin install omni-reverse@CoMind-plugins`。
- 对应 CLI 形式：
  `claude plugin marketplace add ZTE-AICloud/Co-OmniSpec`、
  `claude plugin install omni-dsdd@CoMind-plugins`、
  `claude plugin install omni-reverse@CoMind-plugins`。

### `/reverse` 报「未找到 omni-dsdd」

- `omni-reverse` 通过 `omni-dsdd` 安装根解析共享的 `.omni-infra/` 资产。请在同一 `CoMind-plugins` 市场下安装 `omni-dsdd`，再重新运行 `/reverse`。

### 没有创建分支或功能目录

- 确认 Git 可用且当前目录是有效仓库。
- 可手动运行 `omni-dsdd/skills/create-branch/scripts/` 下的分支创建脚本查看错误。

### 实施阶段执行了错误命令或失败

- 确认 `tasks.md` 存在于 `changes/<分支名>/` 下且格式正确。
- 确认所需工具（如 `npm`、`dotnet`、`python`）已安装且在 `PATH` 中。
- 可手动执行单个任务以查看具体报错，再决定是否重跑 `/implement`。

---

## 11. 贡献与安全

- **[CONTRIBUTING.md](CONTRIBUTING.md)** —— Issue / PR 流程、本地校验（`pnpm validate`、各语言自测脚本）、文档约定、凭据策略。
- **[SECURITY.md](SECURITY.md)** —— 通过 GitHub Security Advisories 公开报告漏洞的方式，以及意外暴露凭据时的处置建议。

**严禁**在 Issue / PR / 提交中包含真实凭据、token、内网主机名或私有 URL；示例请使用 `PLACEHOLDER_*`。

---

## 12. 致谢与许可证

Co-OmniSpec 受 [GitHub Spec Kit](https://github.com/github/spec-kit) 启发并在其基础上扩展，延续其规范驱动开发理念，并适配 Claude Code 等多 Agent 工具链。第三方归属与许可详见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。

许可证：**MIT** — 详见 [LICENSE](LICENSE)。Copyright (c) 2026 ZTE-AICloud / ZTE。

> **English** — See [README.md](README.md). **中文** — 参见 [README-zh-CN.md](README-zh-CN.md)。
