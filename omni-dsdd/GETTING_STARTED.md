# Getting Started with Co-OmniSpec

This guide walks you through installing Co-OmniSpec as two Claude Code plugins (`omni-dsdd` and `omni-reverse`) and running your first Spec-Driven Development workflow.

> **中文说明** — 请参阅 [GETTING_STARTED_zh-CN.md](GETTING_STARTED_zh-CN.md)。

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Verify Installation](#verify-installation)
- [First Run: Constitution](#first-run-constitution)
- [First Run: Specify](#first-run-specify)
- [Next Steps](#next-steps)

---

## Prerequisites

Before you begin, ensure you have:

| Requirement | Notes |
|-------------|-------|
| **Claude Code** | [code.claude.com](https://code.claude.com/) with plugin marketplace support. |
| **Git** | Used for feature branches and the `changes/` directory. |
| **Bash or PowerShell** | Required to execute the shared helpers under `.omni-infra/scripts/`. |

---

## Installation

Co-OmniSpec ships as **two** plugins. Always install them together so the DSDD harness and the reverse-engineering toolkit are both available.

### Option A: Install from marketplace slash commands (recommended)

```text
/plugin marketplace add ZTE-AICloud/Co-OmniSpec
/plugin install omni-dsdd@CoMind-plugins
/plugin install omni-reverse@CoMind-plugins
```

The first command can also be written as `/market add ZTE-AICloud/Co-OmniSpec`.

### Option B: Install from the Claude CLI

If you prefer command-line style (for scripts or non-interactive shells), run the three commands in order:

```bash
claude plugin marketplace add ZTE-AICloud/Co-OmniSpec
claude plugin install omni-dsdd@CoMind-plugins
claude plugin install omni-reverse@CoMind-plugins
```

After all three commands succeed, Claude Code installs commands, skills, hooks, and the shared `.omni-infra/` templates for both plugins.

---

## Verify Installation

1. **Open your target project in Claude Code.**
2. **Open the AI chat** and confirm slash commands such as `/constitution`, `/specify`, `/reverse`, and `/routing` are visible.
3. **Check marketplace and plugin state**:

   - `/plugin marketplace list` (or `/market list`) should list `CoMind-plugins`.
   - `/plugin` (Discover tab) should list both `omni-dsdd` and `omni-reverse` as installed.

If any entry is missing, re-run the corresponding install command from the previous section. After installing a plugin, you may need to re-open the project session for the changes to take effect.

---

## First Run: Constitution

The constitution defines your project's principles and constraints. All later steps (spec, design, tasks, implement) should align with it.

1. In Claude Code, open the AI chat.
2. Run:

   ```text
   /constitution
   ```

3. In the same message (or in a follow-up), describe the principles you want, for example:

   ```text
   Create principles focused on code quality, testing standards, user experience consistency,
   and performance. Include how these principles should guide technical decisions.
   ```

4. The agent creates or updates `.omni-infra/memory/constitution.md`. You can edit this file later to refine principles.

---

## First Run: Specify

Specify turns a short feature description into a full specification (branch, context, spec, and requirements checklist).

1. **Create a feature branch and spec** by running:

   ```text
   /specify
   ```

2. **Provide the feature description** in the same or next message. Focus on *what* and *why*, not on tech stack. Example:

   ```text
   Build a small photo album app. Users can create albums, upload photos, and view them in a grid.
   Albums are flat (no nesting). No login in this first version—single user only.
   ```

3. The agent will:

   - Create a feature branch (e.g. `001-photo-albums`).
   - Create a directory under `changes/` (e.g. `changes/001-photo-albums/`).
   - Generate `spec.md`, `context.md`, and a requirements checklist under `checklists/`.

4. **Review** the generated `changes/<branch>/spec.md` and `checklists/requirements.md`. If something is unclear, run `/clarify` next.

---

## Next Steps

- **Clarify** — Run `/clarify` to resolve ambiguities in the spec (recommended before design).
- **Design** — Run `/design` and describe your tech stack and architecture to generate `design.md`, data model, contracts, etc.
- **Tasks** — Run `/tasks` to generate `tasks.md` from the design.
- **Analyze** — Run `/analyze` to check consistency between spec, design, and tasks.
- **Implement** — Run `/implement` to execute the tasks in order.
- **Archive** — Run `/archive` to archive / merge back completed feature artefacts.
- **Reverse** — Install [`omni-reverse`](../omni-reverse/README.md) and run `/reverse` to document an existing codebase before iterating on it.

For full workflow details and all commands, see the [User Guide](USER_GUIDE.md).
