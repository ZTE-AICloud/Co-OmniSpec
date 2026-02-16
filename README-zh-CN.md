# Co-OmniSpec

**用规范驱动开发，更快交付高质量软件。**

Co-OmniSpec是一套面向 [规范驱动开发（Spec-Driven Development）](https://github.com/github/spec-kit) 的开源工具集：让规范可执行，并引导 AI 编程助手完成规格编写、设计、任务拆解与实现。本项目基于 [GitHub Spec Kit](https://github.com/github/spec-kit) 进行本地化与扩展，面向 Cursor 等多种 Agent 环境优化。

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue" alt="License"/></a>
</p>

---

## 目录

- [什么是规范驱动开发？](#-什么是规范驱动开发)
- [快速开始](#-快速开始)
- [功能概览](#-功能概览)
- [开发工作流](#-开发工作流)
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

### 1. 将 Co-OmniSpec安装到你的项目

克隆本仓库后，在 `build/` 目录下执行安装脚本：

**Linux / macOS：**

```bash
./build/install.sh cursor /path/to/your/project
```

**Windows（PowerShell）：**

```powershell
.\build\install.ps1 cursor C:\path\to\your\project
```

脚本会将 Co-OmniSpec 的 `src/agent/` 与 `src/specify/` 复制到目标项目的 `.cursor` 和 `.specify`。

### 2. 在 Cursor 中打开项目（例）

在 [Cursor](https://cursor.sh/) 中打开目标项目，OmniSpec 命令会在 AI 对话中可用。

### 3. 建立项目章程

使用 **`/omni.constitution`** 创建项目原则与开发指南：

```text
/omni.constitution 创建关注代码质量、测试标准、用户体验一致性和性能的原则。
```

### 4. 编写规范

使用 **`/omni.specify`** 描述你要做的功能，侧重「做什么」和「为什么」：

```text
/omni.specify 做一个相册应用：用户可创建相册、上传照片、网格浏览。相册扁平不嵌套，第一版不需登录。
```

### 5. 生成技术计划

使用 **`/omni.design`** 并说明技术栈与架构：

```text
/omni.design 使用 Vite，尽量少用库，用原生 HTML/CSS/JS，元数据存本地 SQLite。
```

### 6. 拆解任务

使用 **`/omni.tasks`** 根据设计生成可执行任务列表：

```text
/omni.tasks
```

### 7. 执行实现

使用 **`/omni.implement`** 按任务顺序执行实现：

```text
/omni.implement
```

详细步骤见 [入门指南](docs/GETTING_STARTED_zh-CN.md) 与 [用户指南](docs/USER_GUIDE_zh-CN.md)。

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
| **Analyze（分析）** | 对 spec、design、tasks 做跨制品一致性分析。 |
| **Checklist（检查清单）** | 为需求生成自定义质量检查清单。 |
| **Reverse（逆向）** | 从现有代码逆向生成规范与上下文。 |

元模型与模板覆盖需求、上下文、场景、逻辑架构、功能、实体、接口与关系，支持绿地与棕地两种场景。

---

## 🔄 开发工作流

```text
/omni.constitution  →  /omni.specify  →  /omni.clarify  →  /omni.design  →  /omni.tasks  →  /omni.analyze  →  /omni.implement
       │                     │                  │                │                │                │
   项目章程              spec.md            澄清并回写         design.md         tasks.md       一致性检查      代码
                       context.md          到规范            research.md                       (可选)
                       checklists/                           data-model.md
                                               可选           contracts/
```

可选命令：`/omni.checklist`（需求检查清单）、`/omni.reverse`（代码逆向为规范）。

---

## 🤖 支持环境

| 环境 | 支持 | 说明 |
|------|------|------|
| [Cursor](https://cursor.sh/) | ✅ | 主要支持；提供斜杠命令与技能。 |
| 其他 AI Agent | 可适配 | 安装时指定目标 agent 目录名即可适配（如 Claude Code）。 |

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
| **迭代增强（棕地）** | 在现有代码上扩展 | 用 `/omni.reverse` 先文档化再演进；或用 specify/design/tasks 增量加功能。 |
| **质量与一致性** | 实施前把关 | 使用 `/omni.clarify`、`/omni.analyze`、`/omni.checklist` 减少返工。 |

---

## 📁 项目结构

安装后，目标项目中会包含：

```text
你的项目/
├── .cursor/
│   ├── commands/          # OmniSpec 斜杠命令
│   └── skills/            # specify、design、tasks、implement 等技能
├── .specify/
│   ├── memory/
│   │   └── constitution.md
│   ├── metamodel/         # 需求、上下文、场景、架构等元模型
│   ├── scripts/          # Bash / PowerShell 脚本
│   └── templates/        # spec、design、tasks、checklist 模板
└── changes/              # 功能目录（由 /omni.specify 创建）
    └── 001-功能名/
        ├── spec.md
        ├── context.md
        ├── design.md
        ├── tasks.md
        └── checklists/
```

---

## 📖 延伸阅读

- **[入门指南（英文）](docs/GETTING_STARTED.md)** — 安装与首次使用。
- **[入门指南（中文）](docs/GETTING_STARTED_zh-CN.md)** — 安装与首次使用。
- **[用户指南（英文）](docs/USER_GUIDE.md)** — 完整工作流与命令说明。
- **[用户指南（中文）](docs/USER_GUIDE_zh-CN.md)** — 完整工作流与命令说明。
- **[构建脚本说明](build/readme.md)** — Co-OmniSpec构建与打包（Linux/Windows）。

<details>
<summary>📋 点击展开详细步骤说明</summary>

安装 Co-OmniSpec并在 Cursor 中打开项目后：

1. **章程** — 运行 `/omni.constitution` 并描述项目原则，生成或更新 `.specify/memory/constitution.md`。
2. **规格** — 运行 `/omni.specify` 并输入功能描述（做什么、为什么），生成分支、`changes/<分支>/spec.md`、`context.md` 与需求检查清单。
3. **澄清**（建议在设计前）— 运行 `/omni.clarify` 消除歧义，答案会写回规范。
4. **设计** — 运行 `/omni.design` 并说明技术栈，生成 `design.md`、`research.md`、`data-model.md`、`quickstart.md` 及可选的 `contracts/`。
5. **任务** — 运行 `/omni.tasks` 生成按依赖排序的 `tasks.md`。
6. **分析**（可选）— 运行 `/omni.analyze` 在实施前检查 spec、design、tasks 的一致性。
7. **实施** — 运行 `/omni.implement` 按顺序执行任务；Agent 可能执行 CLI 命令，请确保所需工具已安装。

更多细节与常见问题见 [入门指南](docs/GETTING_STARTED_zh-CN.md) 与 [用户指南](docs/USER_GUIDE_zh-CN.md)。

</details>

---

## 🔧 前置要求

- **Cursor**（或支持当前命令/技能模式的 AI 编程助手）。
- **Git**（用于特性分支与 `changes/` 工作流）。
- **Bash**（Linux/macOS）或 **PowerShell**（Windows）以运行脚本。

---

## 🔍 常见问题

### Cursor 里看不到命令

确认已把 Co-OmniSpec安装到**当前**项目：检查是否存在 `.cursor/commands/` 与 `.specify/`。重新加载窗口或重启 Cursor 以加载新命令。

### 安装脚本报错

- 目标项目路径请使用**绝对路径**。
- **Windows：** 需允许执行脚本（如 `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`）。
- **Linux/macOS：** 确保脚本可执行：`chmod +x build/install.sh`。

### 未创建分支或功能目录

确认 Git 可用且当前目录为有效仓库。可手动运行创建分支脚本查看报错，详见 [用户指南 — 常见问题](docs/USER_GUIDE_zh-CN.md#常见问题)。

更多问题与解决方案见 [用户指南](docs/USER_GUIDE_zh-CN.md#常见问题)。

---

## 💬 支持与反馈

如有疑问或问题，可在本仓库提交 GitHub Issue。工作流与命令详解见 [用户指南](docs/USER_GUIDE_zh-CN.md) 与 [入门指南](docs/GETTING_STARTED_zh-CN.md)。

---

## 🙏 致谢与许可

Co-OmniSpec受 [GitHub Spec Kit](https://github.com/github/spec-kit) 启发并在此基础上扩展，延续其规范驱动开发理念，并适配 Cursor 等多 Agent 工具链。

许可条款见 [LICENSE](LICENSE)。
