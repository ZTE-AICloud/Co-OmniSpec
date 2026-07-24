# omni-dsdd

**Spec-Driven Development core plugin for Claude Code.**

`omni-dsdd` is the harness and workflow engine that powers the Spec-Driven Development flow inside Co-OmniSpec. It defines the `constitution → specify → clarify → design → tasks → implement → archive` pipeline, supplies shared scripts under `.omni-infra/`, and ships the slash commands and skills that an AI coding agent uses to turn intent into structured artefacts.

`omni-dsdd` is intentionally paired with [`omni-reverse`](../omni-reverse/README.md), which performs the reverse-engineering half of the workflow. Both plugins must be installed side-by-side from the `CoMind-plugins` marketplace.

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue" alt="License"/></a>
</p>

---

## Table of Contents

- [Why Spec-Driven Development?](#why-spec-driven-development)
- [Install both `omni-dsdd` and `omni-reverse`](#install-both-omni-dsdd-and-omni-reverse)
- [Reverse Engineering](#reverse-engineering)
- [Prerequisites](#prerequisites)
- [First Run](#first-run)
- [Core Workflow](#core-workflow)
- [Workflow Modes](#workflow-modes)
- [Reverse Capabilities](#reverse-capabilities)
- [Plugin Layout](#plugin-layout)
- [Troubleshooting](#troubleshooting)
- [Contributing & Security](#contributing--security)
- [Acknowledgments & License](#acknowledgments--license)

> **中文说明** — 请参阅 [README-zh-CN.md](README-zh-CN.md)。

---

## Why Spec-Driven Development?

Spec-Driven Development flips the traditional code-first workflow: **specifications drive implementation**. You write the *what* and *why* in natural language; your AI agent translates them into structured specifications, design artefacts, dependency-aware task lists, and ultimately code. `omni-dsdd` provides the commands, skills, and shared scripts that make this pipeline repeatable.

The plugin focuses on:

- Producing executable specifications validated against checklists and a project constitution.
- Generating technical plans, data models, contracts, and quickstart notes from a spec.
- Breaking plans into ordered tasks that an agent can execute step by step.
- Enforcing the project constitution throughout the implementation.

For the philosophical background, see the [Co-OmniSpec release design](https://github.com/ZTE-AICloud/Co-OmniSpec/discussions).

---

## Install both `omni-dsdd` and `omni-reverse`

Add the Co-OmniSpec marketplace and install **both** plugins side-by-side. The installation flow expects the three commands below in order:

```text
/plugin marketplace add ZTE-AICloud/Co-OmniSpec
/plugin install omni-dsdd@CoMind-plugins
/plugin install omni-reverse@CoMind-plugins
```

If you prefer the short `market` form, the first command can be `/market add ZTE-AICloud/Co-OmniSpec`.

The corresponding CLI form (for scripts or non-interactive shells) is:

```bash
claude plugin marketplace add ZTE-AICloud/Co-OmniSpec
claude plugin install omni-dsdd@CoMind-plugins
claude plugin install omni-reverse@CoMind-plugins
```

Verify the installation:

1. `/plugin marketplace list` (or `/market list`) — confirm `CoMind-plugins` is registered.
2. `/plugin` (Discover) — confirm both `omni-dsdd` and `omni-reverse` are listed and enabled.
3. In your project workspace, open the AI chat and confirm slash commands such as `/constitution`, `/specify`, `/reverse`, and `/routing` are available.

If a plugin is missing, re-run the corresponding `install` command.

---

## Reverse Engineering

`omni-dsdd` ships the planning half of the workflow; the reverse-engineering half lives in [`omni-reverse`](../omni-reverse/README.md). Install `omni-reverse` from the same `CoMind-plugins` marketplace — both plugins must be present for either side to work.

- `omni-dsdd` owns the shared helpers (`.omni-infra/`, command/skill assets) that `omni-reverse` resolves through `scripts/resolve-dsdd-root.{sh,py,ps1}`.
- `omni-reverse` owns the dedicated `reverse-*` skills that produce specs and context out of existing code.

For reverse-specific instructions, see the [omni-reverse README](../omni-reverse/README.md).

---

## Prerequisites

| Requirement | Notes |
|-------------|-------|
| **Claude Code** | [code.claude.com](https://code.claude.com/) with plugin marketplace support. |
| **Git** | Used for feature branches and the `changes/` directory. |
| **Bash or PowerShell** | Required to run shared scripts under `.omni-infra/scripts/`. |

For local validation of the plugin's own skills, you can also run `pnpm validate` from the `omni-dsdd/` directory (see `CONTRIBUTING.md`).

---

## First Run

1. **Establish project principles** — run `/constitution` and describe the principles you want (code quality, testing standards, UX consistency, performance). The agent writes or updates `.omni-infra/memory/constitution.md`.
2. **Create the spec** — run `/specify` and describe a feature (the *what* and *why*). This creates a branch (e.g. `001-photo-albums`) and `changes/001-photo-albums/{spec.md, context.md, checklists/requirements.md}`.
3. **Clarify** (recommended) — run `/clarify` to resolve open questions and write the answers back into the spec.
4. **Design** — run `/design` with your stack to generate `design.md`, `research.md`, `data-model.md`, `quickstart.md`, and (when relevant) `contracts/`.
5. **Break down tasks** — run `/tasks` to produce `tasks.md` with ordered, dependency-aware tasks.
6. **Implement** — run `/implement` to execute the tasks in order.

Detailed walkthroughs live in [GETTING_STARTED.md](GETTING_STARTED.md); the full command reference lives in [USER_GUIDE.md](USER_GUIDE.md).

---

## Core Workflow

```text
/constitution  →  /specify  →  /clarify  →  /design  →  /tasks  →  /analyze  →  /implement  →  /archive
       │                     │                  │                │                │                │                 │
   Principles           spec.md           Clarifications    design.md         tasks.md      Consistency        Code          Archive/Mergeback
                       context.md         in spec           research.md                      check
                       checklists                          data-model.md
                                                optional    contracts/
```

Optional commands available at any time: `/checklist` (custom requirement checklists), `/reverse` (code → spec, see below), `/knowledge-retrieval [--build]` (build or update a knowledge index used by `specify` and other steps).

---

## Workflow Modes

The `routing` skill selects one of three YAML-defined workflows, executed by `workflow-orchestrator`:

| flow_mode | YAML definition | Typical use case | Key difference |
|-----------|-----------------|------------------|----------------|
| `express` | `workflows/express.yaml` | Small, clear change | Skips `clarify` to reduce iterations. |
| `standard` | `workflows/standard.yaml` | Medium-complexity feature | Full `specify → clarify → design` path. |
| `deep` | `workflows/deep.yaml` | Large or architecture-heavy change | Adds `reverse-on-demand` before `specify`. |

Let `routing` decide automatically by complexity, or force a mode with `--workflow <express|standard|deep>`. Add `--e2e` when you want E2E test design in the `specify` and `design` stages. (`expert` is an internal review variant and is not advertised as a public flow mode.)

Examples:

```text
/routing Build a simple dashboard for internal metrics.
/routing --workflow standard Build a partner API with auth and rate limiting.
/routing --workflow deep --e2e Refactor order orchestration and align cross-service contracts.
```

---

## Reverse Capabilities

`omni-dsdd` ships the `/reverse` (on-demand) interface and the `reverse-on-demand` skill; the bulk of reverse engineering lives in `omni-reverse` (see [omni-reverse/README.md](../omni-reverse/README.md) for the 12 reverse skills).

Three modes are available:

- **Full** — `/reverse --target all`
- **On-demand** — `/reverse --target on-demand --requirement "<...>"`
- **By element** — `/reverse --target requirements|scenarios|interfaces|rules|...`

For the dedicated reverse skills and the orchestrator that schedules them, install `omni-reverse` and consult its README.

---

## Plugin Layout

`omni-dsdd/` after a clean checkout contains:

```text
omni-dsdd/
├── .claude-plugin/
│   └── plugin.json          # Plugin manifest
├── agents/                  # AI subagents (constitution, knowledge extractors, ...)
├── hooks/                   # Lifecycle hooks for runtime instrumentation
├── omni-infra/              # Shared templates, scripts, memory, metamodel
│   ├── config/
│   ├── memory/
│   ├── metamodel/
│   ├── scripts/
│   └── templates/
├── scripts/                 # Node-based skill validation helpers
├── skills/                  # Slash-command and workflow skills
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

Inside the user's project, the runtime artefacts are written under `.omni-infra/` (configuration, memory, metamodel, scripts, templates) and `changes/<branch>/` (per-feature artefacts).

---

## Troubleshooting

### Slash commands are not visible

- Confirm the marketplace and both plugins are registered: `/plugin marketplace list` (or `/market list`) — `CoMind-plugins` should appear; `/plugin` — both `omni-dsdd` and `omni-reverse` should be listed.
- Re-open the project session after installing a plugin.

### Plugin installation fails

- `/plugin marketplace list` and verify `CoMind-plugins`. Re-add if missing: `/plugin marketplace add ZTE-AICloud/Co-OmniSpec`.
- Re-install each plugin: `/plugin install omni-dsdd@CoMind-plugins`, `/plugin install omni-reverse@CoMind-plugins`.
- For CLI mode: `claude plugin marketplace add ZTE-AICloud/Co-OmniSpec`, `claude plugin install omni-dsdd@CoMind-plugins`, `claude plugin install omni-reverse@CoMind-plugins`.

### Branch or feature directory not created

- Make sure Git is available and the working directory is a valid repo. Run the create-branch helper manually to inspect errors (see [USER_GUIDE.md — Troubleshooting](USER_GUIDE.md#troubleshooting)).

---

## Contributing & Security

Contributions, issue triage, and security disclosure policies live at the repository root:

- [CONTRIBUTING.md](../CONTRIBUTING.md)
- [SECURITY.md](../SECURITY.md)

Please **do not** open issues or pull requests containing real credentials, tokens, internal hostnames, or private URLs. Use `PLACEHOLDER_*` values in examples.

---

## Acknowledgments & License

`omni-dsdd` is inspired by and extends [GitHub Spec Kit](https://github.com/github/spec-kit), following its Spec-Driven Development philosophy and adapting the workflow for Claude Code and other agent toolchains.

License: MIT — see [LICENSE](LICENSE). Copyright (c) 2026 ZTE-AICloud / ZTE.

> **English** — See [README.md](README.md). **中文** — 参见 [README-zh-CN.md](README-zh-CN.md)。
