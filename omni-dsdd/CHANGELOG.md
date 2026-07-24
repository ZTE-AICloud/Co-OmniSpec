# Changelog

All notable public changes to `omni-dsdd` are documented here. The format follows
[Semantic Versioning](https://semver.org/): MAJOR.MINOR.PATCH.

For internal review commands, historical commit messages, or per-PR screenshots, see
the project's GitHub release notes and commit history on
<https://github.com/ZTE-AICloud/Co-OmniSpec/releases>.

---

## Versioning conventions

- **MAJOR** — incompatible API / workflow changes (for example, the single-plugin → dual-plugin split).
- **MINOR** — new features added in a backward-compatible way.
- **PATCH** — backward-compatible bug fixes.

Before each release:

1. Bump `version` in `.claude-plugin/plugin.json`.
2. Add an entry to this changelog describing the public-facing change.

---

## v3.2.0 — Initial public dual-plugin release

- **Dual-plugin marketplace:** `CoMind-plugins` ships two Claude Code plugins side by side:
  - `omni-dsdd` — Spec-Driven Development harness (constitution, specify, clarify, design, tasks,
    implement, archive, routing, workflow-orchestrator).
  - `omni-reverse` — Reverse-engineering toolkit (see
    [`omni-reverse/README.md`](../omni-reverse/README.md)).
- **Runtime directory:** shared assets (templates, memory, metamodel, scripts) live under
  `.omni-infra/`.
- **Workflow YAML packaging:** the YAML workflow definitions (`workflows/express.yaml`,
  `workflows/standard.yaml`, `workflows/deep.yaml`, `workflows/expert.yaml`) ship with the
  plugin. `express | standard | deep` are the public `flow_mode` values; `expert` is an internal
  review variant and is not advertised as a public flow_mode.
- **Internal integrations removed:** any repository-internal integrations
  (review tooling, batch runners, internal caches) are out of scope for the public release and will be
  re-introduced only if a corresponding public, generic utility is added.
- **Documentation refresh:** dual-language READMEs (`README.md`, `README-zh-CN.md`),
  getting-started guides (`GETTING_STARTED.md`, `GETTING_STARTED_zh-CN.md`), and user guides
  (`USER_GUIDE.md`, `USER_GUIDE_zh-CN.md`) describe the dual-plugin install, the `.omni-infra/`
  directory, and the link to the companion `omni-reverse` plugin.

---

## Acknowledgement

This changelog intentionally omits per-commit messages, branch names, reviewer names, and
internal reference paths. Public release notes and the GitHub release page are the canonical
sources for those details.
