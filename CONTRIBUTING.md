# Contributing to Co-OmniSpec

Thank you for your interest in Co-OmniSpec. This document covers how to file
issues, send pull requests, and validate changes locally before opening them.

> **中文说明** — If a Chinese version becomes available, it will live alongside
> this file. Until then, please file issues in English when possible.

---

## Table of contents

- [Code of conduct](#code-of-conduct)
- [Filing issues](#filing-issues)
- [Pull requests](#pull-requests)
- [Local development setup](#local-development-setup)
- [Local validation](#local-validation)
- [Documentation conventions](#documentation-conventions)
- [Credentials and secrets](#credentials-and-secrets)
- [Release process (maintainers)](#release-process-maintainers)

---

## Code of conduct

By participating, you agree to abide by the project's open-source norms: be
respectful, focus on the technical merits of each contribution, and avoid
disclosing private or sensitive information.

## Filing issues

Before opening a new issue:

1. **Search existing issues** to avoid duplicates.
2. **Reproduce** the problem against the latest release when possible.
3. **Pick the right scope**:
   - Bugs / unexpected behaviour / CLI errors → "Bug report".
   - Propose a new skill, command, or workflow change → "Feature request".
   - Documentation typos or unclear wording → "Documentation".

Each issue should include:

- A minimal reproduction (commands run, expected vs. actual behaviour).
- The plugin versions (`omni-dsdd`, `omni-reverse`) and the marketplace name.
- Output of `/plugin` (Discover) and the relevant marketplace state.
- Platform (Linux / macOS / WSL) and the hosting environment (Claude Code
  version where relevant).

**Do not** include real credentials, internal hostnames, private URLs, or
session tokens in the issue. Use `PLACEHOLDER_*` values.

## Pull requests

Open a pull request from a feature branch off `main`. A good PR:

- Targets **one** change at a time. Bundle unrelated cleanups separately.
- Has a clear title and description: motivation, approach, alternatives
  considered, and any follow-up work.
- Updates or adds tests / scripts when behaviour changes.
- Updates the relevant documentation (`README*`, `GETTING_STARTED*`, `USER_GUIDE*`,
  `CHANGELOG.md`, and any design notes shipped with the change).
- Keeps file-level edits focused; do not reformat untouched code.

Before requesting review, make sure:

- `pnpm validate` (from `omni-dsdd/`) passes.
- All relevant language self-tests pass (see [Local validation](#local-validation)).
- `git status` is clean apart from your change.
- You can describe **what** changed and **why** without referring to private
  sources or unshipped work.

## Local development setup

To work on `omni-dsdd`:

```bash
cd omni-dsdd
corepack enable   # if pnpm is not yet available
pnpm install
```

To work on `omni-reverse`, no build step is needed — the plugin's skills are
markdown prompts and the resolver helpers under `omni-reverse/scripts/` are
self-contained bash / Python / PowerShell scripts. Test them by invoking them
with a known `${CLAUDE_PLUGIN_ROOT}` value:

```bash
cd omni-reverse
CLAUDE_PLUGIN_ROOT="$(pwd)" bash scripts/resolve-dsdd-root.sh
# should print the absolute path of the sibling omni-dsdd checkout
```

## Local validation

Run the relevant validation from `omni-dsdd/`:

| Check | Command | Purpose |
|-------|---------|---------|
| Skill manifest validation | `pnpm validate` | Validate skill definitions in `omni-dsdd/skills/`. |
| Skill discovery | `pnpm list` | Enumerate registered skills. |

Language-specific self-tests live alongside each language skill in
`omni-dsdd/skills/<language>-{patterns,testing,coding-standards,security,...}`.
Follow the `SKILL.md` of the relevant skill to run its bundled Bash / Python
self-tests. Aim to keep those tests green before requesting review.

For reverse-related changes, exercise the resolution helpers from
`omni-reverse/scripts/resolve-dsdd-root.{sh, py, ps1}` against a fixture:

```bash
mkdir -p /tmp/fake-marketplace
mkdir -p /tmp/fake-marketplace/omni-dsdd/scripts
mkdir -p /tmp/fake-marketplace/omni-dsdd/omni-infra
ln -s "$(pwd)/omni-dsdd" /tmp/fake-marketplace/omni-dsdd      # symbolic is fine
ln -s "$(pwd)/omni-reverse" /tmp/fake-marketplace/omni-reverse
CLAUDE_PLUGIN_ROOT="/tmp/fake-marketplace/omni-reverse" bash \
  /tmp/fake-marketplace/omni-reverse/scripts/resolve-dsdd-root.sh
# expected: prints /tmp/fake-marketplace/omni-dsdd (or the symlink target)
```

## Documentation conventions

- Bilingual documents (`README*`, `GETTING_STARTED*`, `USER_GUIDE*`) **must**
  keep the same section order, command examples, and file paths. The Chinese
  version is not a literal translation; prefer natural technical Chinese.
- Anchor names in Markdown should match across languages for the same section.
- Public identity:
  - Repository: `ZTE-AICloud/Co-OmniSpec`
  - Marketplace: `CoMind-plugins`
  - Author: `ZTE-AICloud`
  - Copyright: `Copyright (c) 2026 ZTE-AICloud / ZTE`
- `.claude-plugin/marketplace.json` is the single source of truth for the
  plugins shipped from this repository. Update both `marketplace.json` and the
  plugin manifests in lock-step.
- Installation commands **must** be the three-step form:
  ```text
  /plugin marketplace add ZTE-AICloud/Co-OmniSpec
  /plugin install omni-dsdd@CoMind-plugins
  /plugin install omni-reverse@CoMind-plugins
  ```

## Credentials and secrets

This repository is public. Treat every change as if it will be visible to the
world on the next release. In particular:

- **Do not** commit real tokens, passwords, API keys, SSH keys, or internal
  certificates — neither in source code, in tests, in documentation, nor in
  examples.
- **Do not** commit internal hostnames, intranet URLs, VPN endpoints, or
  staging URLs. Use `PLACEHOLDER_HOST`, `PLACEHOLDER_TOKEN`, etc.
- **Do not** paste captured network traffic or stack traces that embed
  credentials. Sanitize them first.
- Reviewers and CI will reject PRs that contain any of the above.

If you ever accidentally commit a credential, follow the steps in
[SECURITY.md](SECURITY.md) immediately.

## Release process (maintainers)

1. Bump the version in `.claude-plugin/plugin.json` for the affected plugin(s)
   (SemVer, see [omni-dsdd/CHANGELOG.md](omni-dsdd/CHANGELOG.md)).
2. Update the matching `CHANGELOG.md` entry to describe the public-facing
   change.
3. Verify the marketplace manifest: `.claude-plugin/marketplace.json`.
4. Tag the release: `git tag omni-dsdd-vX.Y.Z` / `git tag omni-reverse-vX.Y.Z`.
5. Push the tag; the release notes should reference any design notes
   included with the change.
