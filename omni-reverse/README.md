# omni-reverse

**Reverse-engineering toolkit for the Co-OmniSpec Spec-Driven Development flow.**

`omni-reverse` is the companion plugin to [`omni-dsdd`](../omni-dsdd/README.md). It turns an
existing codebase into the same Spec-Driven Development artefacts that `omni-dsdd` produces from a
greenfield description: requirements, scenarios, logic architecture, interfaces, external
interfaces, functions, entities, and rules.

```text
omni-reverse   12 reverse skills, orchestrator, shared resolvers
omni-dsdd      Spec-Driven Development harness, shared scripts, .omni-infra templates
```

Both plugins must be installed from the same `CoMind-plugins` marketplace — see
[Install both plugins](#install-both-plugins).

---

## Table of Contents

- [Install both plugins](#install-both-plugins)
- [Shared infrastructure with `omni-dsdd`](#shared-infrastructure-with-omni-dsdd)
- [Path variables](#path-variables)
- [12 reverse skills](#12-reverse-skills)
- [Quick resolution helpers](#quick-resolution-helpers)
- [Entry point: `reverse`](#entry-point-reverse)
- [Contributing & Security](#contributing--security)
- [License](#license)

---

## Install both plugins

`omni-reverse` depends on `omni-dsdd`; install them together with the standard three-step flow:

```text
/plugin marketplace add ZTE-AICloud/Co-OmniSpec
/plugin install omni-dsdd@CoMind-plugins
/plugin install omni-reverse@CoMind-plugins
```

Equivalent CLI form:

```bash
claude plugin marketplace add ZTE-AICloud/Co-OmniSpec
claude plugin install omni-dsdd@CoMind-plugins
claude plugin install omni-reverse@CoMind-plugins
```

Verify with:

- `/plugin marketplace list` (or `/market list`) — `CoMind-plugins` should appear.
- `/plugin` (Discover) — both `omni-dsdd` and `omni-reverse` should be listed and enabled.

If `omni-reverse` reports "shared plugin `omni-dsdd` not found" at runtime, re-install
`omni-dsdd` from the same marketplace; the shared scripts and templates live there.

---

## Shared infrastructure with `omni-dsdd`

This plugin does **not** ship its own shared scripts or templates. They live in
[`omni-dsdd`](../omni-dsdd/README.md) under `.omni-infra/`, and `omni-reverse` resolves them
through `scripts/resolve-dsdd-root.{sh, py, ps1}` at runtime.

- `omni-dsdd` provides: shared `scripts/`, `templates/`, `metamodel/`, `memory/`.
- `omni-reverse` provides: 12 dedicated `reverse-*` skills, the `reverse-orchestration` skill,
  and 9 AI subagents under `agents/`.

Both plugins must be installed in the same marketplace for the resolver to find the shared assets.

---

## Path variables

| Variable | Source | Meaning |
|----------|--------|---------|
| `${CLAUDE_PLUGIN_ROOT}` | injected at runtime | **This** plugin's install root (`omni-reverse`). Points to plugin-local scripts, e.g. `${CLAUDE_PLUGIN_ROOT}/skills/reverse-interfaces/scripts/`. |
| `${DSDD}` | `scripts/resolve-dsdd-root.sh` resolves | Shared plugin root (`omni-dsdd`). Points at the shared scripts and `.omni-infra/` assets. |
| `${REPO_ROOT}` | project root | The target codebase being reverse-engineered. `.omni-infra/` is initialised here by `init_omni_infra.sh`. |
| `${CLAUDE_WORKING_DIR}` | injected at runtime | Current working area; runtime artefacts from the reverse run are written here. |

---

## 12 reverse skills

`omni-reverse/skills/` ships the following 12 skills (per the public release):

| Skill | Role |
|-------|------|
| `reverse` | Top-level orchestrator entry that schedules the other reverse skills and aggregates their output. |
| `reverse-orchestration` | Coordinates the full reverse pass; selects skills, manages state, and stitches outputs together. |
| `reverse-shared` | Common helpers shared by all reverse skills (path resolution, manifest handling, shared library functions). |
| `reverse-logic-architecture` | Extracts the high-level logic architecture from the target codebase. |
| `reverse-deep-logic-architecture` | Dives deeper than `reverse-logic-architecture` for layered or domain-specific logic decomposition. |
| `reverse-interfaces` | Extracts internal interfaces (function/class signatures, contracts, module boundaries). |
| `reverse-external-interfaces` | Extracts external-facing interfaces (HTTP/RPC APIs, CLI surfaces, public entry points). |
| `reverse-functions` | Extracts function-level artefacts (responsibilities, inputs, outputs, side effects). |
| `reverse-entities` | Extracts domain entities, attributes, and relationships into the SDD entity model. |
| `reverse-scenarios` | Extracts concrete usage scenarios and traces them through the code. |
| `reverse-requirements` | Extracts requirements — both explicit (documents) and implicit (derived from the code). |
| `reverse-rules` | Extracts business rules and invariants expressed by the code. |

> 9 AI subagents under `agents/` work alongside these skills — see the
> [omni-dsdd README](../omni-dsdd/README.md) for shared knowledge-extraction subagents and
> `omni-reverse/agents/` for the reverse-specific ones.

---

## Quick resolution helpers

Get `${DSDD}` from the host shell:

```bash
DSDD="$(bash "${CLAUDE_PLUGIN_ROOT}/scripts/resolve-dsdd-root.sh")" || exit 1
```

Equivalent Python:

```python
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
from resolve_dsdd_root import dsdd_root
DSDD = dsdd_root()
```

PowerShell:

```powershell
$DSDD = & "${env:CLAUDE_PLUGIN_ROOT}\scripts\resolve-dsdd-root.ps1"
if (-not $DSDD) { throw "omni-dsdd not found" }
```

Once `${DSDD}` is set, point to the shared scripts and templates via `${DSDD}/scripts/...`
and `${DSDD}/omni-infra/...`.

---

## Entry point: `reverse`

The `reverse` skill is the top-level entry; it selects modes and dispatches to the orchestrator:

```text
reverse --target all               # Full reverse (8 stages)
reverse --target interfaces        # By element
reverse --target on-demand         # On-demand reverse (per requirement)
```

Common element targets include: `requirements`, `system-contexts`, `scenarios`,
`logic_architecture`, `interfaces`, `external-interfaces`, `entities`, `rules`, `functions`.
Pass the target as `--target <element>`.

---

## Contributing & Security

- [CONTRIBUTING.md](../CONTRIBUTING.md)
- [SECURITY.md](../SECURITY.md)

Examples in documentation must use `PLACEHOLDER_*` values — never commit real credentials,
internal hostnames, or private URLs.

---

## License

MIT — see [LICENSE](../LICENSE). Copyright (c) 2026 ZTE-AICloud / ZTE.
