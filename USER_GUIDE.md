# Co-OmniSpec User Guide

This guide describes the full Spec-Driven Development workflow and all Co-OmniSpec commands.

---

## Table of Contents

- [Workflow Overview](#workflow-overview)
- [Core Commands](#core-commands)
- [Optional Commands](#optional-commands)
- [Feature Directory Layout](#feature-directory-layout)
- [Environment and Configuration](#environment-and-configuration)
- [Troubleshooting](#troubleshooting)

---

## Workflow Overview

Recommended order:

```text
1. /omni.constitution   → Set project principles
2. /omni.specify        → Create spec from feature description
3. /omni.clarify        → (Optional) Resolve ambiguities in spec
4. /omni.design         → Generate technical plan and design artifacts
5. /omni.tasks          → Generate tasks.md from design
6. /omni.analyze        → (Optional) Cross-artifact consistency check
7. /omni.implement      → Execute tasks in order
```

Optional at any time:

- **`/omni.checklist`** — Generate custom requirement checklists.
- **`/omni.reverse`** — Reverse-engineer code into spec and context (e.g. for brownfield).

---

## Core Commands

### `/omni.constitution`

**Purpose:** Create or update the project’s governing principles and development guidelines.

**Input (optional):** Natural language description of the principles you want (e.g. code quality, testing, UX, performance).

**Output:**

- `.specify/memory/constitution.md` created or updated.
- Dependent templates kept in sync.

**When to use:** Once at project start, or when you change project-wide rules.

---

### `/omni.specify`

**Purpose:** Turn a short feature description into a full specification.

**Input:** A single paragraph (or more) describing *what* you want to build and *why*. Do not focus on tech stack here.

**Output:**

- A new feature branch (e.g. `001-feature-name`).
- `changes/<branch>/spec.md` — main specification.
- `changes/<branch>/context.md` — impact/context from existing docs (if any).
- `changes/<branch>/checklists/requirements.md` — requirements checklist (iteratively updated).

**Process (high level):** The skill creates the branch, runs impact analysis (if `DOC_DIR`/specs exist), fills the spec from the template using your description and context, then runs a quality-check skill to produce and validate the requirements checklist.

**Next step:** Run `/omni.clarify` if the spec has unclear points, or `/omni.design` to generate the technical plan.

---

### `/omni.clarify`

**Purpose:** Ask up to a few targeted questions to remove ambiguity in the current spec and encode answers back into the spec.

**Input (optional):** Extra instructions or areas to focus on.

**When to use:** After `/omni.specify` and before `/omni.design`, especially when the spec has `[NEEDS CLARIFICATION]` or vague areas.

---

### `/omni.design`

**Purpose:** Generate the technical implementation plan and design artifacts from the spec.

**Input:** Your tech stack and architecture choices (e.g. runtime, framework, database, testing, target platform).

**Output (under the same feature directory):**

- `design.md` — implementation plan.
- `research.md` — research notes (e.g. versions, options).
- `data-model.md` — data model.
- `quickstart.md` — quick start for the feature.
- `contracts/` — API/contract specs as needed.

**When to use:** After the spec (and optionally clarify) is done. The design should align with `.specify/memory/constitution.md`.

---

### `/omni.tasks`

**Purpose:** Break the design into ordered, dependency-aware tasks and write them to `tasks.md`.

**Input:** Usually none; the skill reads the current feature’s design and spec.

**Output:**

- `changes/<branch>/tasks.md` — ordered list of tasks, with dependencies and optional parallel markers.

**When to use:** After `/omni.design`. You can run `/omni.analyze` next to check consistency before implementation.

---

### `/omni.implement`

**Purpose:** Execute the tasks defined in `tasks.md` in order.

**Input (optional):** Instructions or constraints (e.g. “only task 1–3”, “skip tests”).

**Process:** The skill reads `tasks.md`, resolves order and dependencies, and runs each task (e.g. create files, run commands). It may run CLI tools (e.g. `npm`, `dotnet`) as needed.

**When to use:** After `tasks.md` is ready and (optionally) `/omni.analyze` has been run. Ensure required dev tools are installed.

---

## Optional Commands

### `/omni.analyze`

**Purpose:** Non-destructive consistency and quality analysis across `spec.md`, `design.md`, and `tasks.md`.

**When to use:** After `/omni.tasks`, before `/omni.implement`. Helps find gaps, contradictions, or unclear references.

---

### `/omni.checklist`

**Purpose:** Generate a custom checklist to validate requirement completeness, clarity, and consistency (like “unit tests for the spec”).

**Input (optional):** What the checklist should focus on.

**When to use:** Whenever you want an extra quality gate on the current feature’s requirements.

---

### `/omni.reverse`

**Purpose:** Reverse-engineer the existing codebase into full specification and context (requirements, scenarios, entities, interfaces, etc.).

**Input (optional):** Scope or focus (e.g. a subfolder or module).

**Output:** Fills or creates spec and context artifacts that can then be refined and used with `/omni.design` or `/omni.specify`.

**When to use:** For brownfield projects or when you need to document existing behavior before changing it.

---

## Feature Directory Layout

After a full run of specify → design → tasks, a feature directory typically looks like:

```text
changes/001-feature-name/
├── spec.md              # From /omni.specify
├── context.md           # From /omni.specify (impact analysis)
├── design.md            # From /omni.design
├── research.md          # From /omni.design
├── data-model.md        # From /omni.design
├── quickstart.md        # From /omni.design
├── tasks.md             # From /omni.tasks
├── contracts/          # From /omni.design (if applicable)
│   ├── api-spec.json
│   └── ...
└── checklists/
    └── requirements.md  # From /omni.specify + spec-quality-check
```

All paths are relative to the repository root. The branch name usually matches the directory name (e.g. `001-feature-name`).

---

## Environment and Configuration

| Item | Description |
|------|-------------|
| **DOC_DIR** | Root for existing specs/docs used by impact analysis and reverse. Default often `omni-doc`. Can be set via `.specify/config` or environment. |
| **SPECIFY_FEATURE** | Override feature detection when not using Git branches. Set to the feature directory name (e.g. `001-photo-albums`) so that `/omni.design` and later commands know which feature to use. |
| **`.specify/config`** | Optional config file for paths and defaults. |
| **`.specify/memory/constitution.md`** | Project principles; editable by hand or via `/omni.constitution`. |

Scripts (e.g. prerequisite checks, branch creation) live under `.specify/scripts/bash/` and `.specify/scripts/powershell/`. They are invoked by the skills; you can run them manually for debugging.

---

## Troubleshooting

### Commands not visible in Cursor

- Ensure Co-OmniSpec is installed in **this** project (`{AGENT_DIR}/commands/` and `.specify/` present, where `{AGENT_DIR}` is `.cursor/`, `.claude/`, etc.).
- Reload the window or restart Cursor so it picks up the new commands.

### Branch or feature directory not created

- Check that Git is available and the repo is valid.
- Run the create-branch script manually to see errors:
  - Bash: `bash {AGENT_DIR}/skills/omni-create-branch/scripts/bash/create-new-feature.sh --json --short-name "my-feature"`
  - PowerShell: `pwsh -File {AGENT_DIR}/skills/omni-create-branch/scripts/powershell/create-new-feature.ps1 --json --short-name "my-feature"`

### Design or tasks use the wrong feature

- If you are not on a feature branch, set `SPECIFY_FEATURE` to the feature directory name (e.g. `001-photo-albums`).
- Ensure the agent is running in the repo root so that `FEATURE_DIR` and paths resolve correctly.

### Install script fails

- Use absolute paths for the target project.
- On Windows, run PowerShell with execution policy that allows scripts (e.g. `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`).
- On Linux/macOS, ensure the script is executable: `chmod +x build/install.sh`.

### Implement runs wrong commands or fails

- Check that `tasks.md` exists and is well-formed.
- Ensure required tools (e.g. `npm`, `dotnet`, `python`) are installed and on `PATH`.
- Run a single task manually to see the exact command and error.

For build and packaging issues, see [Build readme](../build/readme.md) and the platform-specific docs in `build/`.
