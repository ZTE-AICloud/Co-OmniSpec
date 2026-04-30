# Co-OmniSpec

**Build high-quality software faster with Spec-Driven Development.**

Co-OmniSpec is an open-source toolkit for [Spec-Driven Development](https://github.com/github/spec-kit): specifications become executable and guide your AI coding agent through specification, design, task breakdown, and implementation. This project is a localized and extended adaptation of [GitHub Spec Kit](https://github.com/github/spec-kit), optimized for Claude Code and other agent environments.

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue" alt="License"/></a>
</p>

---

## Table of Contents

- [What is Spec-Driven Development?](#-what-is-spec-driven-development)
- [Get Started](#-get-started)
- [Features](#-features)
- [Development Workflow](#-development-workflow)
- [Routing Paths](#-routing-paths)
- [Supported Environments](#-supported-environments)
- [Core Philosophy](#-core-philosophy)
- [Development Phases](#-development-phases)
- [Project Structure](#-project-structure)
- [Learn More](#-learn-more)
- [Prerequisites](#-prerequisites)
- [Troubleshooting](#-troubleshooting)
- [Support](#-support)
- [Acknowledgments](#-acknowledgments)
- [License](#-license)

> **中文说明** — 请参阅 [README-zh-CN.md](README-zh-CN.md)。

---

## 🤔 What is Spec-Driven Development?

Spec-Driven Development **flips the script** on traditional development: **specifications drive implementation**. Instead of code-first, you define the *what* and *why* first; your AI agent then uses those specs to produce design artifacts, task lists, and code. Co-OmniSpec provides commands and skills so that:

- Specifications are created from natural language and validated with checklists.
- Technical plans and design docs are generated from specs.
- Tasks are ordered by dependency and ready for step-by-step implementation.
- Implementation follows the plan and respects your project constitution.

---

## ⚡ Get Started

### 1. Add the Co-OmniSpec marketplace in Claude Code

In your Claude Code session, add the marketplace:

```text
/plugin marketplace add ZTE-AICloud/Co-OmniSpec
```

You can also use the `market` shortcut:

```text
/market add ZTE-AICloud/Co-OmniSpec
```

### 2. Install the Omni plugin

Install the plugin from marketplace `CoMind-plugins`:

```text
/plugin install omni@CoMind-plugins
```

If you prefer command-line mode, run:

```bash
claude plugin marketplace add ZTE-AICloud/Co-OmniSpec
claude plugin install omni@CoMind-plugins
```

### 3. Establish project principles

Use **`/constitution`** to create your project's governing principles and development guidelines:

```text
/constitution Create principles focused on code quality, testing standards, user experience consistency, and performance requirements.
```

### 4. Create the spec

Use **`/specify`** and describe what you want to build. Focus on the **what** and **why**, not the tech stack:

```text
/specify Build a photo album app. Users can create albums, upload photos, and view them in a grid. Albums are flat (no nesting). No login in this first version.
```

### 5. Create a technical plan

Use **`/design`** with your tech stack and architecture choices:

```text
/design Use Vite with minimal libraries. Vanilla HTML, CSS, and JavaScript. Store metadata in a local SQLite database.
```

### 6. Break down into tasks

Use **`/tasks`** to generate an actionable task list from your design:

```text
/tasks
```

### 7. Execute implementation

Use **`/implement`** to execute all tasks and build the feature:

```text
/implement
```

For detailed step-by-step instructions, see the [Getting Started](GETTING_STARTED.md) guide and the [User Guide](USER_GUIDE.md).

---

## 📋 Features

| Area | Description |
|------|-------------|
| **Constitution** | Project principles and guidelines that steer all later phases. |
| **Specify** | Turn a short feature description into a full spec (branch, context, spec, requirements checklist). |
| **Clarify** | Targeted questions to remove ambiguity before design. |
| **Design** | Generate technical plan, data model, contracts, quickstart from spec. |
| **Tasks** | Break the plan into ordered, dependency-aware tasks in `tasks.md`. |
| **Implement** | Execute tasks from `tasks.md` in sequence. |
| **Archive** | Archive or merge back completed feature artifacts for project continuity. |
| **Analyze** | Cross-artifact consistency checks (spec, design, tasks) before implementation. |
| **Checklist** | Custom checklists to validate requirement quality. |
| **Reverse** | Reverse-engineer existing code into full specification and context. |

Metamodel and templates support requirements, context, scenarios, logic architecture, functions, entities, interfaces, and relations for both greenfield and brownfield workflows.

---

## 🔄 Development Workflow

```text
/constitution  →  /specify  →  /clarify  →  /design  →  /tasks  →  /analyze  →  /implement  →  /archive
       │                     │                  │                │                │                │                 │
   Principles           spec.md           Clarifications    design.md         tasks.md      Consistency        Code          Archive/Mergeback
                       context.md         in spec           research.md                      check
                       checklists                          data-model.md
                                                optional    contracts/
```

Optional commands: `/checklist` (requirement checklists), `/reverse` (code → spec).

`/reverse` supports three modes:

- **Full**: reverse the whole codebase (`/reverse --target all`)
- **On-demand**: reverse for one requirement (`/reverse --target on-demand --requirement "<...>"`)
- **By element**: reverse a specific element type (`/reverse --target requirements|scenarios|interfaces|rules|...`)

---

## 🧭 Routing Paths

The agent supports three routed workflow paths:

- **`express`** → `express-workflow` (fast path, skips clarify)
- **`standard`** → `standard-workflow` (full baseline path)
- **`deep`** → `deep-workflow` (adds on-demand reverse before specify)

You can let `routing` decide automatically by complexity, or force mode with `--workflow <express|standard|deep>`. Add `--e2e` when you want E2E test design in specify/design stages.

---

## 🤖 Supported Environments

| Environment | Support | Notes |
|-------------|---------|-------|
| [Claude Code](https://code.claude.com/) | Yes | Primary target; install and manage through plugin marketplace and `/market` (or `/plugin`) commands. |
| Other AI agents | Adapted | The command/skill pattern and `.infra/` layout can be adapted for other agents. |

---

## 📚 Core Philosophy

Co-OmniSpec's Spec-Driven Development emphasizes:

- **Intent-driven development** — Specifications define the *what* before the *how*.
- **Rich specification creation** — Guardrails, checklists, and constitution guide quality.
- **Multi-step refinement** — Clarify → design → tasks → implement, rather than one-shot code generation.
- **Heavy reliance on AI** — The agent interprets specs, fills templates, and runs tasks under your principles.

---

## 🌟 Development Phases

| Phase | Focus | Key activities |
|-------|--------|-----------------|
| **0-to-1 (Greenfield)** | Generate from scratch | Start with requirements → spec → design → tasks → implementation. |
| **Iterative enhancement (Brownfield)** | Add or modernize | Use `/reverse` to document existing code, then refine and extend with specify/design/tasks. |
| **Quality and consistency** | Before implementation | Use `/clarify`, `/analyze`, and `/checklist` to reduce rework. |

---

## 📁 Project Structure

After installation, your project will contain:

```text
your-project/
├── .claude/
│   ├── commands/          # OmniSpec slash commands
│   └── skills/            # Skills for specify, design, tasks, implement, etc.
├── .infra/
│   ├── memory/
│   │   └── constitution.md
│   ├── metamodel/          # Requirement, context, scenario, architecture, etc.
│   ├── scripts/           # Bash and PowerShell helpers
│   └── templates/         # spec, design, tasks, checklist templates
└── changes/               # Feature directories (created by /specify)
    └── 001-feature-name/
        ├── spec.md
        ├── context.md
        ├── design.md
        ├── tasks.md
        └── checklists/
```

---

## 📖 Learn More

- **[Getting Started](GETTING_STARTED.md)** — Installation and first run (English).
- **[Getting Started (中文)](GETTING_STARTED_zh-CN.md)** — 安装与首次使用（中文）。
- **[User Guide](USER_GUIDE.md)** — Full workflow and command reference (English).
- **[User Guide (中文)](USER_GUIDE_zh-CN.md)** — 完整工作流与命令说明（中文）。

<details>
<summary>📋 Click to expand detailed step-by-step process</summary>

After installing Co-OmniSpec in Claude Code:

1. **Constitution** — Run `/constitution` and describe your project principles. This creates or updates `.infra/memory/constitution.md`.
2. **Specify** — Run `/specify` and provide a feature description (what and why). This creates a branch, `changes/<branch>/spec.md`, `context.md`, and a requirements checklist.
3. **Clarify** (recommended before design) — Run `/clarify` to resolve ambiguities; answers are written back into the spec.
4. **Design** — Run `/design` with your tech stack. This produces `design.md`, `research.md`, `data-model.md`, `quickstart.md`, and optional `contracts/`.
5. **Tasks** — Run `/tasks` to generate `tasks.md` with ordered, dependency-aware tasks.
6. **Analyze** (optional) — Run `/analyze` to check consistency across spec, design, and tasks before implementing.
7. **Implement** — Run `/implement` to execute the tasks in order. The agent may run CLI commands (e.g. `npm`, `dotnet`); ensure required tools are installed.
8. **Archive** (recommended after completion) — Run `/archive` to archive or mergeback completed feature artifacts into the project baseline.

For full details and troubleshooting, see the [Getting Started](GETTING_STARTED.md) and [User Guide](USER_GUIDE.md).

</details>

---

## 🔧 Prerequisites

- **Claude Code** (or another AI coding agent that supports the provided command/skill pattern).
- **Git** (for feature branches and `changes/` workflow).
- **Bash** (Linux/macOS) or **PowerShell** (Windows) for scripts.

---

## 🔍 Troubleshooting

### Commands not visible in Claude Code

Ensure marketplace and plugin are installed correctly:

- Run `/plugin marketplace list` (or `/market list`) and verify `CoMind-plugins`.
- Run `/plugin` (Discover tab) or `/market` to confirm `omni` is available.
- Re-open the project session after installation if commands are still not visible.

### Branch or feature directory not created

Ensure Git is available and the current directory is a valid repository. You can run the create-branch script manually to see errors (see [User Guide — Troubleshooting](USER_GUIDE.md#troubleshooting)).

For more issues and solutions, see the [User Guide](USER_GUIDE.md#troubleshooting).

---

## 💬 Support

For questions or issues, open a GitHub issue in this repository. For detailed workflow and command help, see the [User Guide](USER_GUIDE.md) and [Getting Started](GETTING_STARTED.md).

---

## 🙏 Acknowledgments

Co-OmniSpec is inspired by and extends [GitHub Spec Kit](https://github.com/github/spec-kit), following its Spec-Driven Development philosophy and adapting the workflow for Claude Code and other agent toolchains.

---

## 📄 License

See [LICENSE](LICENSE) for terms.
