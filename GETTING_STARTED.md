# Getting Started with Co-OmniSpec

This guide walks you through installing Co-OmniSpec as a Claude Code plugin and running your first Spec-Driven Development workflow.

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

---

## Installation

### Option A: Install from marketplace command (recommended)

1. In a Claude Code session, add the marketplace:

   ```text
   /plugin marketplace add ZTE-AICloud/Co-OmniSpec
   ```

   Shortcut form:

   ```text
   /market add ZTE-AICloud/Co-OmniSpec
   ```

2. Install the plugin:

   ```text
   /plugin install omni@CoMind-plugins
   ```

3. **Result:** Claude Code will install OmniSpec commands, skills, and hooks for your workflow.

### Option B: Install from Claude CLI command

If you prefer command-line style (non-slash command):

```bash
claude plugin marketplace add ZTE-AICloud/Co-OmniSpec
claude plugin install omni@CoMind-plugins
```

---

## Verify Installation

1. **Open your target project in Claude Code**.
2. **Open the AI chat** and check that you can trigger OmniSpec commands, for example:
   - `/constitution`
   - `/specify`
3. **Check marketplace/plugin state**:
   - Run `/plugin marketplace list` (or `/market list`) and verify `CoMind-plugins`.
   - Run `/plugin` (Discover) or `/market` and verify `omni` is installed.

If missing, re-run the marketplace add and install commands.

---

## First Run: Constitution

The constitution defines your project’s principles and constraints. All later steps (spec, design, tasks, implement) should align with it.

1. In Claude Code, open the AI chat.
2. Run:

   ```
   /constitution
   ```

3. In the same message (or in a follow-up), describe the principles you want, for example:

   ```
   Create principles focused on code quality, testing standards, user experience consistency,
   and performance. Include how these principles should guide technical decisions.
   ```

4. The agent will create or update `.specify/memory/constitution.md`. You can edit this file later to refine principles.

---

## First Run: Specify

Specify turns a short feature description into a full specification (branch, context, spec, and requirements checklist).

1. **Create a feature branch and spec** by running:

   ```
   /specify
   ```

2. **Provide the feature description** in the same or next message. Focus on *what* and *why*, not the tech stack. Example:

   ```
   Build a small photo album app. Users can create albums, upload photos, and view them in a grid.
   Albums are flat (no nesting). No login in this first version—single user only.
   ```

3. The agent will:

   - Create a feature branch (e.g. `001-photo-albums`).
   - Create a directory under `changes/` (e.g. `changes/001-photo-albums/`).
   - Generate `spec.md`, `context.md`, and a requirements checklist under `checklists/`.

4. **Review** the generated `changes/<branch>/spec.md` and `checklists/requirements.md`. If something is unclear, you can run `/clarify` next.

---

## Next Steps

- **Clarify** — Run `/clarify` to resolve ambiguities in the spec (recommended before design).
- **Design** — Run `/design` and describe your tech stack and architecture to generate `design.md`, data model, contracts, etc.
- **Tasks** — Run `/tasks` to generate `tasks.md` from the design.
- **Analyze** — Run `/analyze` to check consistency between spec, design, and tasks.
- **Implement** — Run `/implement` to execute the tasks in order.
- **Archive** — Run `/archive` to archive/mergeback completed feature artifacts.

For full workflow details and all commands, see the [User Guide](USER_GUIDE.md).

