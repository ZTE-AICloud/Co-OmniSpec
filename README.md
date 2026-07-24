# Co-OmniSpec

**Build high-quality software faster with [Spec-Driven Development](https://github.com/github/spec-kit).**

Co-OmniSpec is an open-source toolkit that turns intent into structured specifications, design
artefacts, and dependency-aware tasks, and then drives an AI coding agent through implementation.
It is a localized and extended adaptation of [GitHub Spec Kit](https://github.com/github/spec-kit),
optimised for Claude Code and other agent environments.

Co-OmniSpec ships as two plugins from the `CoMind-plugins` marketplace: **`omni-dsdd`** for the
Spec-Driven Development pipeline and **`omni-reverse`** for the reverse-engineering side. Both
must be installed together.

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue" alt="License"/></a>
</p>

---

## Table of Contents

1. [Project Overview & Spec-Driven Development](#1-project-overview--spec-driven-development)
2. [Plugin Responsibilities](#2-plugin-responsibilities)
3. [Prerequisites](#3-prerequisites)
4. [Install Commands](#4-install-commands)
5. [First Use](#5-first-use)
6. [Workflow Map (express / standard / deep / expert)](#6-workflow-map)
7. [Using Reverse Engineering](#7-using-reverse-engineering)
8. [Repository Layout](#8-repository-layout)
9. [Troubleshooting](#9-troubleshooting)
10. [Contributing & Security](#10-contributing--security)
11. [Acknowledgements & License](#11-acknowledgements--license)

> **中文说明** — 请参阅 [README-zh-CN.md](README-zh-CN.md)。

---

## 1. Project Overview & Spec-Driven Development

Spec-Driven Development flips the traditional code-first workflow: **specifications drive
implementation**. You write the *what* and *why* in natural language; your AI agent translates
them into structured specifications, design notes, dependency-aware tasks, and finally code.

Co-OmniSpec provides:

- A **constitution** that anchors every step in project-level principles.
- A repeatable pipeline: `constitution → specify → clarify → design → tasks → implement → archive`.
- Built-in support for **brownfield** work through reverse engineering of existing code.
- **Quality gates** at each stage (clarify, analyze, checklist, review).

---

## 2. Plugin Responsibilities

Co-OmniSpec is **two plugins** in one marketplace. They share runtime assets but each focuses on
half of the workflow:

| Plugin | Marketplace name | Focus | Plugin-local skills (highlights) | Shared assets |
|--------|------------------|-------|---------------------------------|---------------|
| **`omni-dsdd`** | `CoMind-plugins` | The Spec-Driven Development pipeline: harness, slash commands, shared templates, scripts, workflow YAML. | `specify`, `clarify`, `design`, `tasks`, `implement`, `archive`, `analyze`, `checklist`, `constitution`, `routing`, `workflow-orchestrator`, `knowledge-retrieval`, `create-branch`, `sdd`, and the on-demand `reverse-on-demand`. | Owns `.omni-infra/` (config, memory, metamodel, scripts, templates). |
| **`omni-reverse`** | `CoMind-plugins` | Reverse engineering of existing code into SDD artefacts. | `reverse`, `reverse-orchestration`, `reverse-shared`, `reverse-logic-architecture`, `reverse-deep-logic-architecture`, `reverse-interfaces`, `reverse-external-interfaces`, `reverse-functions`, `reverse-entities`, `reverse-scenarios`, `reverse-requirements`, `reverse-rules`. | Depends on `omni-dsdd`; resolves `${DSDD}` through `scripts/resolve-dsdd-root.{sh, py, ps1}`. |

Both plugins must be installed side by side. `omni-reverse` cannot run without `omni-dsdd`; the
DSDD pipeline benefits from `omni-reverse` whenever the project has existing code to document.

---

## 3. Prerequisites

| Requirement | Notes |
|-------------|-------|
| **Claude Code** | [code.claude.com](https://code.claude.com/) with plugin marketplace support. |
| **Git** | Used for feature branches and the `changes/` directory. |
| **Bash or PowerShell** | Required to execute the shared scripts under `.omni-infra/scripts/`. |
| **Node + pnpm (optional)** | Needed only when validating the plugin's own skills locally (`pnpm validate` inside `omni-dsdd/`); see [CONTRIBUTING.md](CONTRIBUTING.md). |

---

## 4. Install Commands

Add the marketplace and install both plugins:

```text
/plugin marketplace add ZTE-AICloud/Co-OmniSpec
/plugin install omni-dsdd@CoMind-plugins
/plugin install omni-reverse@CoMind-plugins
```

The first command is also accepted as `/market add ZTE-AICloud/Co-OmniSpec`.

Equivalent CLI form (for non-interactive shells or CI):

```bash
claude plugin marketplace add ZTE-AICloud/Co-OmniSpec
claude plugin install omni-dsdd@CoMind-plugins
claude plugin install omni-reverse@CoMind-plugins
```

Verify:

1. `/plugin marketplace list` (or `/market list`) — `CoMind-plugins` is registered.
2. `/plugin` (Discover) — both `omni-dsdd` and `omni-reverse` are listed and enabled.
3. In your project workspace, open AI chat and check that `/constitution`, `/specify`, `/reverse`,
   `/routing` are visible.

If a plugin is missing, re-run its `install` command. The plugin guides cover the same commands
in more detail ([omni-dsdd/README.md](omni-dsdd/README.md),
[omni-reverse/README.md](omni-reverse/README.md)).

---

## 5. First Use

A minimal first run uses only `omni-dsdd`:

1. **Constitution** — run `/constitution` and describe the principles you want (code quality,
   testing standards, UX, performance). The agent creates or updates
   `.omni-infra/memory/constitution.md`.
2. **Specify** — run `/specify` with a feature description (the *what* and *why*). The agent
   creates a feature branch and `changes/<branch>/{spec.md, context.md, checklists/requirements.md}`.
3. **Clarify** (recommended) — run `/clarify` to resolve ambiguities and write answers back into
   the spec.
4. **Design** — run `/design` with your stack. Generates `design.md`, `research.md`,
   `data-model.md`, `quickstart.md`, and (when relevant) `contracts/`.
5. **Tasks** — run `/tasks` to break the design into ordered, dependency-aware tasks
   (`tasks.md`).
6. **Implement** — run `/implement` to execute tasks in order.
7. **Archive** (recommended after completion) — run `/archive` to archive/merge back completed
   feature artefacts.

For brownfield projects, install `omni-reverse` first and start with step 0: `/reverse` to
document existing behaviour before changing it (see [Section 7](#7-using-reverse-engineering)).

Detailed walkthroughs live in [omni-dsdd/GETTING_STARTED.md](omni-dsdd/GETTING_STARTED.md) and the
full command reference in [omni-dsdd/USER_GUIDE.md](omni-dsdd/USER_GUIDE.md).

---

## 6. Workflow Map

The `routing` skill selects one of three YAML-defined workflows, executed by
`workflow-orchestrator`:

| flow_mode | YAML definition | Typical use case | Key difference |
|-----------|-----------------|------------------|----------------|
| `express` | `omni-dsdd/workflows/express.yaml` | Small, clear change | Skips `clarify` to reduce iterations. |
| `standard` | `omni-dsdd/workflows/standard.yaml` | Medium-complexity feature | Full `specify → clarify → design` path. |
| `deep` | `omni-dsdd/workflows/deep.yaml` | Large or architecture-heavy change | Adds `reverse-on-demand` before `specify`. |
| `expert` | `omni-dsdd/workflows/expert.yaml` | Internal review variant | Not advertised as a public `flow_mode`; not user-selectable. |

Let `routing` decide by complexity, or force a mode with `--workflow <express|standard|deep>`.
Add `--e2e` to enable E2E test design in `specify` and `design`. Examples:

```text
/routing Build a small dashboard for internal metrics.
/routing --workflow standard Build a partner API with auth and rate limiting.
/routing --workflow deep --e2e Refactor order orchestration and align cross-service contracts.
```

The trailing `express|standard|deep` are `flow_mode` values, not skill names; the workflow YAML
files live under `omni-dsdd/workflows/`.

---

## 7. Using Reverse Engineering

Reverse engineering lives in the **omni-reverse** plugin. Use it for brownfield work or when you
need to document an existing codebase before refactoring it.

Entry points (driven by the `reverse` skill in `omni-reverse`):

- **Full** — `/reverse --target all`
- **On-demand** — `/reverse --target on-demand --requirement "<requirement-or-file>"`
- **By element** — `/reverse --target requirements|scenarios|interfaces|rules|...`

`omni-reverse` provides 12 dedicated skills (`reverse`, `reverse-orchestration`, `reverse-shared`,
`reverse-logic-architecture`, `reverse-deep-logic-architecture`, `reverse-interfaces`,
`reverse-external-interfaces`, `reverse-functions`, `reverse-entities`, `reverse-scenarios`,
`reverse-requirements`, `reverse-rules`) that produce the corresponding SDD artefacts. The shared
infrastructure — paths, templates, scripts — comes from `omni-dsdd`'s `.omni-infra/`.

See [omni-reverse/README.md](omni-reverse/README.md) for the full reverse-side reference.

---

## 8. Repository Layout

```text
Co-OmniSpec/
├── .claude-plugin/
│   └── marketplace.json          # Registers both plugins under CoMind-plugins
├── omni-dsdd/
│   ├── .claude-plugin/plugin.json
│   ├── agents/                   # AI subagents (constitution, knowledge extractors, ...)
│   ├── hooks/                    # Lifecycle hooks
│   ├── omni-infra/               # Shared .omni-infra/ assets
│   │   ├── config/
│   │   ├── memory/
│   │   ├── metamodel/
│   │   ├── scripts/
│   │   └── templates/
│   ├── scripts/                  # Node-based validation helpers
│   ├── skills/                   # Slash-command and workflow skills
│   ├── workflows/                # express.yaml / standard.yaml / deep.yaml / expert.yaml
│   ├── README.md / README-zh-CN.md
│   ├── GETTING_STARTED.md / GETTING_STARTED_zh-CN.md
│   ├── USER_GUIDE.md / USER_GUIDE_zh-CN.md
│   ├── CHANGELOG.md
│   ├── LICENSE                   # Same bytes as root LICENSE
│   ├── package.json
│   └── pnpm-workspace.yaml
├── omni-reverse/
│   ├── .claude-plugin/plugin.json
│   ├── agents/                   # Reverse-specific subagents
│   ├── scripts/                  # resolve-dsdd-root.{sh,py,ps1}
│   ├── skills/                   # 12 reverse skills (see omni-reverse/README.md)
│   ├── README.md
│   └── require.txt
├── README.md / README-zh-CN.md   # This document (English / 中文)
├── CONTRIBUTING.md
├── SECURITY.md
├── THIRD_PARTY_NOTICES.md
└── LICENSE                       # MIT, Copyright (c) 2026 ZTE-AICloud / ZTE
```

After installation, the **target** project (the codebase the AI agent works on) gains:

```text
your-project/
├── .claude/
│   ├── commands/                 # OmniSpec slash commands (from omni-dsdd)
│   └── skills/                   # Skills (from omni-dsdd and omni-reverse)
├── .omni-infra/                  # Shared templates, scripts, memory, metamodel
│   ├── memory/constitution.md
│   ├── metamodel/
│   ├── scripts/                  # Bash and PowerShell helpers
│   └── templates/                # spec, design, tasks, checklist templates
└── changes/                      # Feature directories (created by /specify)
    └── 001-feature-name/
        ├── spec.md
        ├── context.md
        ├── design.md
        ├── tasks.md
        └── checklists/
```

The path `.omni-infra/` is the shared runtime directory used by both plugins inside the
target project.

---

## 9. Troubleshooting

### Slash commands are not visible

- Confirm the marketplace is registered: `/plugin marketplace list` (or `/market list`) — `CoMind-plugins` should appear.
- Confirm both plugins are installed: `/plugin` (Discover) — `omni-dsdd` and `omni-reverse` should both be listed.
- Re-open the project session after installing a plugin.

### Plugin installation fails

- Run `/plugin marketplace list`. If `CoMind-plugins` is missing, re-add it:
  `/plugin marketplace add ZTE-AICloud/Co-OmniSpec`.
- Re-run the install commands:
  `/plugin install omni-dsdd@CoMind-plugins`, `/plugin install omni-reverse@CoMind-plugins`.
- CLI mode equivalents:
  `claude plugin marketplace add ZTE-AICloud/Co-OmniSpec`,
  `claude plugin install omni-dsdd@CoMind-plugins`,
  `claude plugin install omni-reverse@CoMind-plugins`.

### `/reverse` reports "omni-dsdd not found"

- `omni-reverse` resolves the shared `.omni-infra/` assets through `omni-dsdd`'s install root.
  Install `omni-dsdd` from the same `CoMind-plugins` marketplace and re-run `/reverse`.

### Branch or feature directory not created

- Confirm Git is available and the working directory is a valid repo.
- Run the create-branch helper manually to inspect errors. The helper ships in the
  `create-branch` skill under `omni-dsdd/skills/create-branch/scripts/`.

### Implement runs wrong commands or fails

- Confirm `tasks.md` exists and is well-formed under your `changes/<branch>/` directory.
- Confirm required tools (`npm`, `dotnet`, `python`, …) are installed and on `PATH`.
- Run a single task manually to surface the exact error before retrying `/implement`.

---

## 10. Contributing & Security

- **[CONTRIBUTING.md](CONTRIBUTING.md)** — issue / pull-request workflow, local validation
  (`pnpm validate`, language self-tests), documentation conventions, credential policy.
- **[SECURITY.md](SECURITY.md)** — how to report vulnerabilities through GitHub Security
  Advisories, and what to do if you accidentally expose a credential in an issue or commit.

**Never** commit real credentials, tokens, internal hostnames, or private URLs. Use
`PLACEHOLDER_*` values in examples.

---

## 11. Acknowledgements & License

Co-OmniSpec is inspired by and extends [GitHub Spec Kit](https://github.com/github/spec-kit),
following its Spec-Driven Development philosophy and adapting the workflow for Claude Code and
other agent toolchains. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for the relevant
acknowledgement and license notice.

License: **MIT** — see [LICENSE](LICENSE). Copyright (c) 2026 ZTE-AICloud / ZTE.

> **English** — See [README.md](README.md). **中文** — 参见 [README-zh-CN.md](README-zh-CN.md)。
