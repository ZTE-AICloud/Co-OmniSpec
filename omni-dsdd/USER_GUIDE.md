# Co-OmniSpec User Guide

This guide describes the full Spec-Driven Development workflow and all Co-OmniSpec commands. `omni-dsdd` covers the planning half of the pipeline; reverse engineering lives in the companion [`omni-reverse`](../omni-reverse/README.md) plugin.

> **中文说明** — 请参阅 [USER_GUIDE_zh-CN.md](USER_GUIDE_zh-CN.md)。

---

## Table of Contents

- [Workflow Overview](#workflow-overview)
- [Workflow Modes and Routing](#workflow-modes-and-routing)
- [Core Commands](#core-commands)
- [Optional Commands](#optional-commands)
- [Feature Directory Layout](#feature-directory-layout)
- [Environment and Configuration](#environment-and-configuration)
- [Troubleshooting](#troubleshooting)

---

## Workflow Overview

Recommended order:

```text
1. /constitution        → Set project principles
2. /specify             → Create spec from feature description
3. /clarify             → (Optional) Resolve ambiguities in spec
4. /design              → Generate technical plan and design artefacts
5. /tasks               → Generate tasks.md from design
6. /analyze             → (Optional) Cross-artefact consistency check
7. /implement           → Execute tasks in order
```

Optional at any time:

- **`/checklist`** — Generate custom requirement checklists.
- **`/reverse`** — Reverse-engineer code into spec and context (requires [`omni-reverse`](../omni-reverse/README.md) to be installed).
- **`/knowledge-retrieval [--build]`** — Build or update a knowledge index that `specify` and other commands can query.

---

## Workflow Modes and Routing

`omni-dsdd` provides three workflow modes. They are routed by `routing` and executed by `workflow-orchestrator` (which reads YAML workflow definitions):

| flow_mode | YAML definition | Typical use case | Key difference |
|-----------|-----------------|------------------|----------------|
| `express` | `workflows/express.yaml` | Small, clear change | Skips `clarify` to reduce iterations. |
| `standard` | `workflows/standard.yaml` | Medium-complexity feature | Full `specify → clarify → design` path. |
| `deep` | `workflows/deep.yaml` | Large or architecture-heavy change | Adds `reverse-on-demand` before `specify`. |

Routing behaviour:

- **Default path** — `routing` calls `complexity-analyzer` and selects `express` / `standard` / `deep` automatically.
- **Forced path** — pass `--workflow <express|standard|deep>` to override complexity analysis.
- **E2E toggle** — pass `--e2e` to enable E2E test design in `specify` and `design`.

Routing parameter examples:

```text
/routing Build a simple dashboard for internal metrics.
/routing --workflow standard Build a partner API with auth and rate limiting.
/routing --workflow deep --e2e Refactor order orchestration and align cross-service contracts.
```

Important routing conventions:

- `express | standard | deep` are `flow_mode` values only, not callable skills.
- `routing` and `workflow-orchestrator` are skills. `express | standard | deep` select the corresponding YAML definition.
- In `deep` mode, the same `$ARGUMENTS` is used for both the on-demand reverse requirement input and the later feature specification input.
- `expert` is an internal review variant defined in `workflows/expert.yaml` and is not advertised as a public `flow_mode`.

---

## Core Commands

### `/constitution`

**Purpose:** Create or update the project's governing principles and development guidelines.

**Input (optional):** Natural language description of the principles you want (e.g. code quality, testing, UX, performance).

**Output:**

- `.omni-infra/memory/constitution.md` created or updated.
- Dependent templates kept in sync.

**When to use:** Once at project start, or when you change project-wide rules.

### `/specify`

**Purpose:** Turn a short feature description into a full specification.

**Input:** A single paragraph (or more) describing *what* you want to build and *why*. Do not focus on tech stack here.

**Output:**

- A new feature branch (e.g. `001-feature-name`).
- `changes/<branch>/spec.md` — main specification.
- `changes/<branch>/context.md` — impact / context from existing docs (if any).
- `changes/<branch>/checklists/requirements.md` — requirements checklist (iteratively updated).

**Process (high level):** The skill creates the branch, runs impact analysis (when `DOC_DIR`/specs exist), fills the spec from the template using your description and context, then runs a quality-check skill to produce and validate the requirements checklist.

**Next step:** Run `/clarify` if the spec has unclear points, or `/design` to generate the technical plan.

### `/clarify`

**Purpose:** Ask up to a few targeted questions to remove ambiguity in the current spec and encode answers back into the spec.

**Input (optional):** Extra instructions or areas to focus on.

**When to use:** After `/specify` and before `/design`, especially when the spec has `[NEEDS CLARIFICATION]` or vague areas.

### `/design`

**Purpose:** Generate the technical implementation plan and design artefacts from the spec.

**Input:** Your tech stack and architecture choices (e.g. runtime, framework, database, testing, target platform).

**Output (under the same feature directory):**

- `design.md` — implementation plan.
- `research.md` — research notes (e.g. versions, options).
- `data-model.md` — data model.
- `quickstart.md` — quick start for the feature.
- `contracts/` — API / contract specs as needed.

**When to use:** After the spec (and optionally clarify) is done. The design should align with `.omni-infra/memory/constitution.md`.

### `/tasks`

**Purpose:** Break the design into ordered, dependency-aware tasks and write them to `tasks.md`.

**Input:** Usually none; the skill reads the current feature's design and spec.

**Output:**

- `changes/<branch>/tasks.md` — ordered list of tasks, with dependencies and optional parallel markers.

**When to use:** After `/design`. You can run `/analyze` next to check consistency before implementation.

### `/implement`

**Purpose:** Execute the tasks defined in `tasks.md` in order.

**Input (optional):** Instructions or constraints (e.g. "only task 1–3", "skip tests").

**Process:** The skill reads `tasks.md`, resolves order and dependencies, and runs each task (e.g. create files, run commands). It may run CLI tools (e.g. `npm`, `dotnet`) as needed.

**When to use:** After `tasks.md` is ready and (optionally) `/analyze` has been run. Ensure required dev tools are installed.

---

## Optional Commands

### `/analyze`

**Purpose:** Non-destructive consistency and quality analysis across `spec.md`, `design.md`, and `tasks.md`.

**When to use:** After `/tasks`, before `/implement`. Helps find gaps, contradictions, or unclear references.

### `/checklist`

**Purpose:** Generate a custom checklist to validate requirement completeness, clarity, and consistency (like "unit tests for the spec").

**Input (optional):** What the checklist should focus on.

**When to use:** Whenever you want an extra quality gate on the current feature's requirements.

### `/reverse`

**Purpose:** Reverse-engineer the existing codebase into full specification and context (requirements, scenarios, entities, interfaces, etc.).

**Modes:** `/reverse` supports three modes:

| Mode | Description | Typical command form |
|------|-------------|----------------------|
| **Full** | Reverse the full codebase and generate end-to-end artefacts. | `/reverse --target all` |
| **On-demand** | Reverse only what is needed for one requirement or change request. | `/reverse --target on-demand --requirement "<requirement-or-file>"` |
| **By element** | Reverse one specific element type (requirements / scenarios / interfaces / rules, etc.). | `/reverse --target <element>` |

Common element targets include: `requirements`, `system-contexts`, `scenarios`, `logic_architecture`, `interfaces`, `external-interfaces`, `entities`, `rules`, `functions`.

**Input (optional):** Scope, target mode, and focus (e.g. requirement text/file, subfolder, or module).

**Output:** Fills or creates spec and context artefacts that can then be refined and used with `/design` or `/specify`.

**When to use:** For brownfield projects or when you need to document existing behaviour before changing it.

> The deep reverse skills (`reverse-logic-architecture`, `reverse-interfaces`, `reverse-entities`, `reverse-scenarios`, `reverse-requirements`, `reverse-rules`, `reverse-functions`, `reverse-external-interfaces`, `reverse-deep-logic-architecture`, `reverse`, `reverse-orchestration`, `reverse-shared`) live in the companion [`omni-reverse`](../omni-reverse/README.md) plugin. Install it from the same `CoMind-plugins` marketplace to use them.

### `/knowledge-retrieval [--build]`

**Purpose:** Extract knowledge from user-provided documents and code, then build an index. The index is consumed by `specify` and other steps to surface relevant knowledge context.

**When to use:** Brownfield projects that want to make existing documentation and source code available for knowledge consumption.

**Usage:**

1. Run `/knowledge-retrieval --build [raw_knowledge_dir]` to extract knowledge and build the index. When `raw_knowledge_dir` is omitted, the tool defaults to the current project directory `.` and indexes everything under it (recommended: keep all documents and code under the project root and omit the argument).
2. After the build finishes, the `knowledge-retrieval` SKILL is embedded in any activity that needs document retrieval; pass your query to the SKILL and it returns the relevant knowledge context. Activities such as `specify` already embed `/knowledge-retrieval`, so no extra configuration is required.
3. When documents or code change, run `/knowledge-retrieval --build --update` to perform an incremental build.
4. To rebuild from scratch, run `/knowledge-retrieval --build --force` (the existing index is deleted first).

---

## Feature Directory Layout

After a full run of `specify → design → tasks`, a feature directory typically looks like:

```text
changes/001-feature-name/
├── spec.md              # From /specify
├── context.md           # From /specify (impact analysis)
├── design.md            # From /design
├── research.md          # From /design
├── data-model.md        # From /design
├── quickstart.md        # From /design
├── tasks.md             # From /tasks
├── contracts/           # From /design (if applicable)
│   ├── api-spec.json
│   └── ...
└── checklists/
    └── requirements.md  # From /specify + spec-quality-check
```

All paths are relative to the repository root. The branch name usually matches the directory name (e.g. `001-feature-name`).

---

## Environment and Configuration

| Item | Description |
|------|-------------|
| **DOC_DIR** | Root for existing specs / docs used by impact analysis and reverse. Default often `omni-doc`. Can be set via `.omni-infra/config` or an environment variable. |
| **SPECIFY_FEATURE** | Override feature detection when not using Git branches. Set to the feature directory name (e.g. `001-photo-albums`) so that `/design` and later commands know which feature to use. |
| **`.omni-infra/config`** | Optional config file for paths and defaults. |
| **`.omni-infra/memory/constitution.md`** | Project principles; editable by hand or via `/constitution`. |

Scripts (prerequisite checks, branch creation, etc.) live under `.omni-infra/scripts/bash/` and `.omni-infra/scripts/powershell/`. They are invoked by the skills; you can run them manually for debugging.

`omni-reverse` resolves the shared `.omni-infra/` root via `scripts/resolve-dsdd-root.{sh, py, ps1}` — both plugins must be installed in the same `CoMind-plugins` marketplace for the resolver to succeed.

---

## Troubleshooting

### Slash commands are not visible

- Confirm marketplace and both plugins are installed: `/plugin marketplace list` (or `/market list`) — `CoMind-plugins` should appear; `/plugin` — both `omni-dsdd` and `omni-reverse` should be listed.
- Reopen the project session if commands still do not appear.

### Branch or feature directory not created

- Check that Git is available and the repo is valid.
- Run the create-branch helper manually to inspect errors. The helper ships under the `create-branch` skill; invoke the underlying script with `bash scripts/.../create-new-feature.sh --json --short-name "my-feature"` (or the PowerShell equivalent) from the plugin checkout to see detailed output.

### Design or tasks use the wrong feature

- If you are not on a feature branch, set `SPECIFY_FEATURE` to the feature directory name (e.g. `001-photo-albums`).
- Ensure the agent is running in the repo root so that `FEATURE_DIR` and paths resolve correctly.

### Plugin installation fails

- Run `/plugin marketplace list` (or `/market list`) and check whether `CoMind-plugins` is present.
- If missing, re-add marketplace: `/plugin marketplace add ZTE-AICloud/Co-OmniSpec`.
- Re-install plugins:
  - `/plugin install omni-dsdd@CoMind-plugins`
  - `/plugin install omni-reverse@CoMind-plugins`
- For CLI mode, use:
  - `claude plugin marketplace add ZTE-AICloud/Co-OmniSpec`
  - `claude plugin install omni-dsdd@CoMind-plugins`
  - `claude plugin install omni-reverse@CoMind-plugins`

### `/reverse` reports `omni-dsdd not found`

- `omni-reverse` depends on the shared scripts and `.omni-infra/` assets shipped by `omni-dsdd`. Install `omni-dsdd` from the same `CoMind-plugins` marketplace, then re-run `/reverse`.

### Implement runs wrong commands or fails

- Check that `tasks.md` exists and is well-formed.
- Ensure required tools (e.g. `npm`, `dotnet`, `python`) are installed and on `PATH`.
- Run a single task manually to see the exact command and error.
