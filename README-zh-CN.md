# Co-OmniSpec

**用规范驱动开发，更快交付高质量软件。**

Co-OmniSpec是一套面向 [规范驱动开发（Spec-Driven Development）](https://github.com/github/spec-kit) 的开源工具集：让规范可执行，并引导 AI 编程助手完成规格编写、设计、任务拆解与实现。本项目基于 [GitHub Spec Kit](https://github.com/github/spec-kit) 进行本地化与扩展，面向 Claude Code 等多种 Agent 环境优化。

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue" alt="License"/></a>
</p>

---

## 目录

- [什么是规范驱动开发？](#-什么是规范驱动开发)
- [快速开始](#-快速开始)
- [功能概览](#-功能概览)
- [开发工作流](#-开发工作流)
- [Routing 路径](#-routing-路径)
- [支持环境](#-支持环境)
- [核心理念](#-核心理念)
- [开发阶段](#-开发阶段)
- [项目结构](#-项目结构)
- [延伸阅读](#-延伸阅读)
- [前置要求](#-前置要求)
- [常见问题](#-常见问题)
- [支持与反馈](#-支持与反馈)
- [致谢与许可](#-致谢与许可)

> **English** — See [README.md](README.md) for the English readme.

---

## 🤔 什么是规范驱动开发？

规范驱动开发**扭转**传统“先写代码再补文档”的方式：**用规范驱动实现**。先明确“做什么”和“为什么”，再由 AI 根据规范生成设计制品、任务列表与代码。Co-OmniSpec 通过命令与技能实现：

- 用自然语言生成规格，并用检查清单做质量验证。
- 根据规范与技术选型生成技术计划与设计文档。
- 将计划拆解为按依赖排序的可执行任务。
- 按任务顺序实施，并遵循项目章程中的原则。

---

## ⚡ 快速开始

### 1. 在 Claude Code 中添加 Co-OmniSpec 市场

在 Claude Code 会话中执行：

```text
/plugin marketplace add ZTE-AICloud/Co-OmniSpec
```

也可使用 `market` 简写：

```text
/market add ZTE-AICloud/Co-OmniSpec
```

### 2. 安装 Omni 插件

从 `CoMind-plugins` 市场安装插件：

```text
/plugin install omni@CoMind-plugins
```

如果你更偏好命令行方式，也可以执行：

```bash
claude plugin marketplace add ZTE-AICloud/Co-OmniSpec
claude plugin install omni@CoMind-plugins
```

### 3. 建立项目章程

使用 **`/constitution`** 创建项目原则与开发指南：

```text
/constitution 创建关注代码质量、测试标准、用户体验一致性和性能的原则。
```

### 4. 编写规范

使用 **`/specify`** 描述你要做的功能，侧重「做什么」和「为什么」：

```text
/specify 做一个相册应用：用户可创建相册、上传照片、网格浏览。相册扁平不嵌套，第一版不需登录。
```

### 5. 生成技术计划

使用 **`/design`** 并说明技术栈与架构：

```text
/design 使用 Vite，尽量少用库，用原生 HTML/CSS/JS，元数据存本地 SQLite。
```

### 6. 拆解任务

使用 **`/tasks`** 根据设计生成可执行任务列表：

```text
/tasks
```

### 7. 执行实现

使用 **`/implement`** 按任务顺序执行实现：

```text
/implement
```

详细步骤见 [入门指南](GETTING_STARTED_zh-CN.md) 与 [用户指南](USER_GUIDE_zh-CN.md)。

---

## 📋 功能概览

| 能力 | 说明 |
|------|------|
| **Constitution（章程）** | 项目原则与约束，指导后续所有阶段。 |
| **Specify（规格编写）** | 从简短功能描述生成完整规范（分支、上下文、spec、需求检查清单）。 |
| **Clarify（澄清）** | 在设计前通过针对性问题消除规范模糊点。 |
| **Design（设计）** | 从规范生成技术计划、数据模型、契约与快速上手文档。 |
| **Tasks（任务）** | 将计划拆解为带依赖顺序的 `tasks.md`。 |
| **Implement（实施）** | 按 `tasks.md` 顺序执行任务。 |
| **Archive（归档）** | 将已完成特性进行归档/回流，沉淀到项目基线。 |
| **Analyze（分析）** | 对 spec、design、tasks 做跨制品一致性分析。 |
| **Checklist（检查清单）** | 为需求生成自定义质量检查清单。 |
| **Reverse（逆向）** | 从现有代码逆向生成规范与上下文。 |

元模型与模板覆盖需求、上下文、场景、逻辑架构、功能、实体、接口与关系，支持绿地与棕地两种场景。

---

## 🔄 开发工作流

```text
/constitution  →  /specify  →  /clarify  →  /design  →  /tasks  →  /analyze  →  /implement  →  /archive
       │                     │                  │                │                │                │                 │
   项目章程              spec.md            澄清并回写         design.md         tasks.md       一致性检查          代码         归档/回流
                       context.md          到规范            research.md                       (可选)
                       checklists/                           data-model.md
                                               可选           contracts/
```

可选命令：`/checklist`（需求检查清单）、`/reverse`（代码逆向为规范）。

`/reverse` 支持三种模式：

- **全量**：对整个代码库逆向（`/reverse --target all`）
- **on-demand**：针对单个需求按需逆向（`/reverse --target on-demand --requirement "<...>"`）
- **按要素**：按要素类型逆向（`/reverse --target requirements|scenarios|interfaces|rules|...`）

---

## 🧭 Routing 路径

当前 agent 支持三种可路由工作流路径：

- **`express`** → `express-workflow`（快速路径，跳过 clarify）
- **`standard`** → `standard-workflow`（标准完整路径）
- **`deep`** → `deep-workflow`（在 specify 前增加按需反构）

你可以让 `routing` 按复杂度自动判定，也可以通过 `--workflow <express|standard|deep>` 强制指定。若希望在 specify/design 阶段启用 E2E 测试设计，可附加 `--e2e`。

---

## 🤖 支持环境

| 环境 | 支持 | 说明 |
|------|------|------|
| [Claude Code](https://code.claude.com/) | ✅ | 主要支持；通过插件市场与 `/market`（或 `/plugin`）命令管理。 |
| 其他 AI Agent | 可适配 | 命令/技能模式与 `.specify/` 目录结构可按需迁移适配。 |

---

## 📚 核心理念

Co-OmniSpec的规范驱动开发强调：

- **意图驱动** — 先定义「做什么」，再谈「怎么做」。
- **规范先行** — 用章程、检查清单与模板保证规范质量。
- **分步精化** — 澄清 → 设计 → 任务 → 实施，而非一次性生成代码。
- **善用 AI** — 由 Agent 解读规范、填充模板、执行任务，并遵循项目原则。

---

## 🌟 开发阶段

| 阶段 | 重点 | 主要活动 |
|------|------|----------|
| **从零到一（绿地）** | 从无到有 | 需求 → 规范 → 设计 → 任务 → 实现。 |
| **迭代增强（棕地）** | 在现有代码上扩展 | 用 `/reverse` 先文档化再演进；或用 specify/design/tasks 增量加功能。 |
| **质量与一致性** | 实施前把关 | 使用 `/clarify`、`/analyze`、`/checklist` 减少返工。 |

---

## 📁 项目结构

安装后，目标项目中会包含：

```text
你的项目/
├── .claude/
│   ├── commands/          # OmniSpec 斜杠命令
│   └── skills/            # specify、design、tasks、implement 等技能
├── .specify/
│   ├── memory/
│   │   └── constitution.md
│   ├── metamodel/         # 需求、上下文、场景、架构等元模型
│   ├── scripts/          # Bash / PowerShell 脚本
│   └── templates/        # spec、design、tasks、checklist 模板
└── changes/              # 功能目录（由 /specify 创建）
    └── 001-功能名/
        ├── spec.md
        ├── context.md
        ├── design.md
        ├── tasks.md
        └── checklists/
```

---

## 📖 延伸阅读

- **[入门指南（英文）](GETTING_STARTED.md)** — 安装与首次使用。
- **[入门指南（中文）](GETTING_STARTED_zh-CN.md)** — 安装与首次使用。
- **[用户指南（英文）](USER_GUIDE.md)** — 完整工作流与命令说明。
- **[用户指南（中文）](USER_GUIDE_zh-CN.md)** — 完整工作流与命令说明。

<details>
<summary>📋 点击展开详细步骤说明</summary>

在 Claude Code 中安装 Co-OmniSpec 后：

1. **章程** — 运行 `/constitution` 并描述项目原则，生成或更新 `.specify/memory/constitution.md`。
2. **规格** — 运行 `/specify` 并输入功能描述（做什么、为什么），生成分支、`changes/<分支>/spec.md`、`context.md` 与需求检查清单。
3. **澄清**（建议在设计前）— 运行 `/clarify` 消除歧义，答案会写回规范。
4. **设计** — 运行 `/design` 并说明技术栈，生成 `design.md`、`research.md`、`data-model.md`、`quickstart.md` 及可选的 `contracts/`。
5. **任务** — 运行 `/tasks` 生成按依赖排序的 `tasks.md`。
6. **分析**（可选）— 运行 `/analyze` 在实施前检查 spec、design、tasks 的一致性。
7. **实施** — 运行 `/implement` 按顺序执行任务；Agent 可能执行 CLI 命令，请确保所需工具已安装。
8. **归档**（建议完成功能后执行）— 运行 `/archive` 将已完成特性归档/回流到项目基线。

更多细节与常见问题见 [入门指南](GETTING_STARTED_zh-CN.md) 与 [用户指南](USER_GUIDE_zh-CN.md)。

</details>

---

## 🔧 前置要求

- **Claude Code**（或支持当前命令/技能模式的 AI 编程助手）。
- **Git**（用于特性分支与 `changes/` 工作流）。
- **Bash**（Linux/macOS）或 **PowerShell**（Windows）以运行脚本。

---

## 🔍 常见问题

### Claude Code 里看不到命令

确认市场与插件均已安装：

- 运行 `/plugin marketplace list`（或 `/market list`）并确认存在 `CoMind-plugins`。
- 运行 `/plugin`（Discover）或 `/market`，确认可看到 `omni`。
- 若仍不可见，重新打开项目会话后再检查。

### 未创建分支或功能目录

确认 Git 可用且当前目录为有效仓库。可手动运行创建分支脚本查看报错，详见 [用户指南 — 常见问题](USER_GUIDE_zh-CN.md#常见问题)。

更多问题与解决方案见 [用户指南](USER_GUIDE_zh-CN.md#常见问题)。

---

## 💬 支持与反馈

如有疑问或问题，可在本仓库提交 GitHub Issue。工作流与命令详解见 [用户指南](USER_GUIDE_zh-CN.md) 与 [入门指南](GETTING_STARTED_zh-CN.md)。

---

## 🙏 致谢与许可

Co-OmniSpec受 [GitHub Spec Kit](https://github.com/github/spec-kit) 启发并在此基础上扩展，延续其规范驱动开发理念，并适配 Claude Code 等多 Agent 工具链。

许可条款见 [LICENSE](LICENSE)。
