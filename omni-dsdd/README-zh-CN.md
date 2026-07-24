# omni-dsdd

**面向 Claude Code 的规范驱动开发（DSDD）核心插件。**

`omni-dsdd` 是 Co-OmniSpec 中规范驱动开发工作流的承载者：它定义 `constitution → specify → clarify → design → tasks → implement → archive` 的全链路，提供共享脚本 `.omni-infra/`，并交付 AI 编程助手所需的斜杠命令与技能。

`omni-dsdd` 必须与同一市场中的 [`omni-reverse`](../omni-reverse/README.md) 配合使用，逆向工程由后者承担。

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue" alt="License"/></a>
</p>

---

## 目录

- [为什么要用规范驱动开发？](#为什么要用规范驱动开发)
- [同时安装 `omni-dsdd` 与 `omni-reverse`](#同时安装-omni-dsdd-与-omni-reverse)
- [逆向工程](#逆向工程)
- [前置要求](#前置要求)
- [首次使用](#首次使用)
- [核心工作流](#核心工作流)
- [工作流模式](#工作流模式)
- [逆向能力](#逆向能力)
- [插件目录结构](#插件目录结构)
- [故障排查](#故障排查)
- [贡献与安全](#贡献与安全)
- [致谢与许可](#致谢与许可)

> **English** — See [README.md](README.md) for the English readme.

---

## 为什么要用规范驱动开发？

规范驱动开发**颠覆**「先写代码再补文档」的传统方式：**用规范驱动实现**。先用自然语言描述「做什么」与「为什么」，再由 AI 编程助手将规范转化为结构化的规格、设计制品、依赖关系清晰的任务列表，并最终产出代码。`omni-dsdd` 提供让这套流程可重复执行的命令、技能与共享脚本。

本插件聚焦于：

- 生成可执行的规范，并通过检查清单与项目章程进行质量验证。
- 根据规范生成技术计划、数据模型、契约与快速上手文档。
- 将计划拆解为按依赖排序、可被 Agent 顺序执行的任务。
- 在实施全过程中贯彻项目章程。

设计背景请参考 [Co-OmniSpec 开源整理设计](https://github.com/ZTE-AICloud/Co-OmniSpec/discussions)。

---

## 同时安装 `omni-dsdd` 与 `omni-reverse`

请先添加 Co-OmniSpec 市场，再**并列**安装两个插件。按以下三步顺序执行：

```text
/plugin marketplace add ZTE-AICloud/Co-OmniSpec
/plugin install omni-dsdd@CoMind-plugins
/plugin install omni-reverse@CoMind-plugins
```

若习惯使用简写，第一条命令也可以写成 `/market add ZTE-AICloud/Co-OmniSpec`。

如使用 CLI（非交互式脚本场景）：

```bash
claude plugin marketplace add ZTE-AICloud/Co-OmniSpec
claude plugin install omni-dsdd@CoMind-plugins
claude plugin install omni-reverse@CoMind-plugins
```

安装完成后请验证：

1. 运行 `/plugin marketplace list`（或 `/market list`），确认 `CoMind-plugins` 已注册。
2. 运行 `/plugin`（Discover），确认同时列出 `omni-dsdd` 与 `omni-reverse`。
3. 打开 AI 对话，确认可触发 `/constitution`、`/specify`、`/reverse`、`/routing` 等斜杠命令。

如缺失任意插件，重新执行对应安装命令即可。

---

## 逆向工程

`omni-dsdd` 负责规划链路；逆向工程部分由 [`omni-reverse`](../omni-reverse/README.md) 提供。请务必在同一 `CoMind-plugins` 市场中并列安装 `omni-reverse`，否则两条链路都无法独立工作。

- `omni-dsdd` 提供共享层（`.omni-infra/`、命令/技能资产），`omni-reverse` 通过 `scripts/resolve-dsdd-root.{sh,py,ps1}` 解析定位。
- `omni-reverse` 提供专门负责反构的 `reverse-*` 系列技能，从代码生成规范与上下文。

关于反构部分的具体说明，请参考 [omni-reverse/README.md](../omni-reverse/README.md)。

---

## 前置要求

| 要求 | 说明 |
|------|------|
| **Claude Code** | [code.claude.com](https://code.claude.com/)，需支持插件市场。 |
| **Git** | 用于特性分支与 `changes/` 工作流。 |
| **Bash 或 PowerShell** | 用于运行 `.omni-infra/scripts/` 中的共享脚本。 |

如需对插件自身的 skill 进行本地校验，可在 `omni-dsdd/` 目录下执行 `pnpm validate`（参见根目录 [CONTRIBUTING.md](../CONTRIBUTING.md)）。

---

## 首次使用

1. **建立项目章程** —— 运行 `/constitution`，描述你希望的原则（代码质量、测试标准、用户体验一致性、性能等）。Agent 会创建或更新 `.omni-infra/memory/constitution.md`。
2. **编写规格** —— 运行 `/specify` 并输入功能描述（侧重「做什么」和「为什么」），Agent 会创建分支（如 `001-photo-albums`）并生成 `changes/001-photo-albums/{spec.md, context.md, checklists/requirements.md}`。
3. **澄清**（建议执行）—— 运行 `/clarify` 消除规范中的歧义，并将答案写回规范。
4. **设计** —— 运行 `/design` 并输入技术栈，生成 `design.md`、`research.md`、`data-model.md`、`quickstart.md` 以及（按需的）`contracts/`。
5. **拆解任务** —— 运行 `/tasks` 生成 `tasks.md`，任务按依赖排序。
6. **实施** —— 运行 `/implement` 按顺序执行任务。

详细教程见 [GETTING_STARTED_zh-CN.md](GETTING_STARTED_zh-CN.md)；完整命令参考见 [USER_GUIDE_zh-CN.md](USER_GUIDE_zh-CN.md)。

---

## 核心工作流

```text
/constitution  →  /specify  →  /clarify  →  /design  →  /tasks  →  /analyze  →  /implement  →  /archive
       │                     │                  │                │                │                │                 │
   项目章程              spec.md           澄清写回规范     design.md         tasks.md       一致性检查          代码         归档/回流
                       context.md                          research.md
                       checklists                          data-model.md
                                                可选       contracts/
```

随时可用的可选命令：`/checklist`（生成自定义需求检查清单）、`/reverse`（代码 → 规范，见下文）、`/knowledge-retrieval [--build]`（构建或更新 `specify` 等环节所需的知识索引）。

---

## 工作流模式

`routing` skill 按复杂度选择三种 YAML 工作流之一，由 `workflow-orchestrator` 执行：

| flow_mode | YAML 定义 | 适用场景 | 关键差异 |
|-----------|-----------|----------|----------|
| `express` | `workflows/express.yaml` | 改动小、需求清晰 | 跳过 `clarify`，减少迭代轮次。 |
| `standard` | `workflows/standard.yaml` | 中等复杂度功能 | 完整执行 `specify → clarify → design`。 |
| `deep` | `workflows/deep.yaml` | 大规模或架构型改动 | 在 `specify` 前增加 `reverse-on-demand`。 |

可让 `routing` 按复杂度自动判定，也可通过 `--workflow <express|standard|deep>` 强制指定。若需在 `specify` / `design` 阶段启用 E2E 测试设计，附加 `--e2e`。（`expert` 为内部评审变体，不作为公开 flow_mode 公开。）

示例：

```text
/routing 做一个小型的内部指标看板。
/routing --workflow standard 做一个带鉴权与限流的对客 API。
/routing --workflow deep --e2e 重构订单编排，并对齐跨服务契约。
```

---

## 逆向能力

`omni-dsdd` 提供 `/reverse`（按需反构）与 `reverse-on-demand` 入口；系统的反构能力集中在 `omni-reverse` 中（详见 [omni-reverse/README.md](../omni-reverse/README.md)）。

支持三种模式：

- **全量** —— `/reverse --target all`
- **按需** —— `/reverse --target on-demand --requirement "<...>"`
- **按要素** —— `/reverse --target requirements|scenarios|interfaces|rules|...`

具体的 12 个反构技能以及调度它们的 `reverse-orchestration`，请安装 `omni-reverse` 后查阅其 README。

---

## 插件目录结构

`omni-dsdd/` 仓库的初始结构如下：

```text
omni-dsdd/
├── .claude-plugin/
│   └── plugin.json          # 插件清单
├── agents/                  # AI 子代理（constitution、知识抽取等）
├── hooks/                   # 运行时生命周期钩子
├── omni-infra/              # 共享模板、脚本、记忆、元模型
│   ├── config/
│   ├── memory/
│   ├── metamodel/
│   ├── scripts/
│   └── templates/
├── scripts/                 # 基于 Node 的技能校验辅助
├── skills/                  # 斜杠命令与工作流技能
├── workflows/               # express.yaml / standard.yaml / deep.yaml / expert.yaml
├── GETTING_STARTED.md
├── GETTING_STARTED_zh-CN.md
├── USER_GUIDE.md
├── USER_GUIDE_zh-CN.md
├── CHANGELOG.md
├── LICENSE
├── package.json
└── pnpm-workspace.yaml
```

用户项目内，运行时产物写入 `.omni-infra/`（配置、记忆、元模型、脚本、模板）以及 `changes/<分支名>/`（按特性组织的制品）。`.omni-infra/` 路径替代了上一版本单插件时代的 `.infra/`。

---

## 故障排查

### 看不到斜杠命令

- 确认市场与两个插件都已安装：运行 `/plugin marketplace list`（或 `/market list`）应出现 `CoMind-plugins`；运行 `/plugin`，应同时看到 `omni-dsdd` 与 `omni-reverse`。
- 在安装完毕后重新打开项目会话。

### 插件安装失败

- 运行 `/plugin marketplace list` 确认 `CoMind-plugins`。缺失则重新添加：`/plugin marketplace add ZTE-AICloud/Co-OmniSpec`。
- 重新安装：`/plugin install omni-dsdd@CoMind-plugins`、`/plugin install omni-reverse@CoMind-plugins`。
- 命令行模式下：`claude plugin marketplace add ZTE-AICloud/Co-OmniSpec`、`claude plugin install omni-dsdd@CoMind-plugins`、`claude plugin install omni-reverse@CoMind-plugins`。

### 没有创建分支或功能目录

- 确认 Git 可用且当前目录为有效仓库。可手动运行创建分支脚本查看错误，详见 [USER_GUIDE_zh-CN.md — 常见问题](USER_GUIDE_zh-CN.md#常见问题)。

---

## 贡献与安全

贡献流程、Issue 提交与安全披露约定见仓库根目录：

- [CONTRIBUTING.md](../CONTRIBUTING.md)
- [SECURITY.md](../SECURITY.md)

请勿在 Issue / PR 中提交真实凭据、token、内网主机名或私有 URL；示例请使用 `PLACEHOLDER_*`。

---

## 致谢与许可

`omni-dsdd` 受 [GitHub Spec Kit](https://github.com/github/spec-kit) 启发并在此基础上扩展，延续其规范驱动开发理念，并适配 Claude Code 等多 Agent 工具链。

许可：MIT — 详见 [LICENSE](LICENSE)。Copyright (c) 2026 ZTE-AICloud / ZTE。

> **English** — See [README.md](README.md). **中文** — 参见 [README-zh-CN.md](README-zh-CN.md)。
