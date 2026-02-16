# Getting Started with Co-OmniSpec

This guide walks you through installing Co-OmniSpec and running your first Spec-Driven Development workflow in Cursor.

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
| **Cursor** | [cursor.sh](https://cursor.sh/) or compatible IDE with slash commands. |
| **Git** | Used for feature branches and the `changes/` directory. |
| **Bash** (Linux/macOS) or **PowerShell** (Windows) | For running install and project scripts. |

---

## Installation

### Option A: Install from a cloned repository

1. **Clone Co-OmniSpec** (or download and extract the repo):

   ```bash
   git clone <your-omnispec2-repo-url> omnispec2
   cd omnispec2
   ```

2. **Run the install script** from the `build/` directory.

   **Linux / macOS:**

   ```bash
   ./build/install.sh cursor /path/to/your/target/project
   ```

   **Windows (PowerShell):**

   ```powershell
   .\build\install.ps1 cursor C:\path\to\your\target\project
   ```

   Replace `/path/to/your/target/project` with the **absolute path** of the project where you want Co-OmniSpec (the project you will develop with Cursor).

3. **Result:** The installer copies:

   - `src/agent/` (commands and skills) from Co-OmniSpec into your target project’s `.cursor/`.
   - `src/specify/` from Co-OmniSpec into your target project’s `.specify/`.

   Your target project will now have the OmniSpec commands available when opened in Cursor.

### Option B: Install from a release package

If you have a pre-built zip (e.g. from CI or a release):

1. Extract the zip to a folder (e.g. `omnispec2-build`).
2. In that folder, run the same install command as above, pointing to your target project:

   ```bash
   ./install.sh cursor /path/to/your/project
   ```

   (Use `install.ps1` on Windows with the same arguments.)

---

## Verify Installation

1. **Open your target project in Cursor** (the one you passed to `install.sh` / `install.ps1`).
2. **Open the AI chat** and check that you can trigger OmniSpec commands, for example:
   - `/omni.constitution`
   - `/omni.specify`
3. **Check that these paths exist** in your project:
   - `.cursor/commands/` — contains `omni.*.md` command files.
   - `.specify/` — contains `memory/`, `metamodel/`, `scripts/`, `templates/`.

If any of these are missing, re-run the install script and ensure the target path is correct.

---

## First Run: Constitution

The constitution defines your project’s principles and constraints. All later steps (spec, design, tasks, implement) should align with it.

1. In Cursor, open the AI chat.
2. Run:

   ```
   /omni.constitution
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
   /omni.specify
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

4. **Review** the generated `changes/<branch>/spec.md` and `checklists/requirements.md`. If something is unclear, you can run `/omni.clarify` next.

---

## Next Steps

- **Clarify** — Run `/omni.clarify` to resolve ambiguities in the spec (recommended before design).
- **Design** — Run `/omni.design` and describe your tech stack and architecture to generate `design.md`, data model, contracts, etc.
- **Tasks** — Run `/omni.tasks` to generate `tasks.md` from the design.
- **Analyze** — Run `/omni.analyze` to check consistency between spec, design, and tasks.
- **Implement** — Run `/omni.implement` to execute the tasks in order.

For full workflow details and all commands, see the [User Guide](USER_GUIDE.md).

For build and release scripts (building zip packages, versioning), see the [Build readme](../build/readme.md).
