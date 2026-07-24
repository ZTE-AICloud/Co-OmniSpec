---
name: brainstorming-sdd-bridge
description: Expert workflow adapter that converts an approved brainstorming *-design.md into the standard SDD document interface consumed by tasks/implement/review/local-sandbox-fix. Use only after expert brainstorming and before tasks.
context: fork
agent: general-purpose
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
---

# brainstorming-sdd-bridge

Convert expert-mode brainstorming output into the standard document interface consumed by downstream SDD stages. This is an adapter, not a new design phase.

## Contract

Input:

- `FEATURE_DIR` from workflow context.
- An approved brainstorming document in `FEATURE_DIR/*-design.md`.

Output:

- `FEATURE_DIR/spec.md`
- `FEATURE_DIR/design.md`
- `FEATURE_DIR/context.md`
- `FEATURE_DIR/research.md`
- `FEATURE_DIR/data-model.md`
- `FEATURE_DIR/contracts/api-contract.md`
- `FEATURE_DIR/quickstart.md`
- `FEATURE_DIR/checklists/requirements.md`
- `FEATURE_DIR/.runs/evaluations/eval-specify-report.yaml`
- `FEATURE_DIR/.runs/metrics/omni-metrics-log.json`
- `FEATURE_DIR/.runs/paths.json`
- `FEATURE_DIR/.runs/env.sh`
- `.runs/.omnispec-state.json` updated with `brainstorming-sdd-bridge` completed and `current_stage=tasks`.

## Procedure

1. Resolve `CLAUDE_PLUGIN_ROOT`, `CLAUDE_WORKING_DIR`, `FEATURE_DIR`, and `BRANCH_NAME`.
2. Run:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/brainstorming-sdd-bridge/scripts/python/brainstorming_sdd_bridge.py" \
  --plugin-root "${CLAUDE_PLUGIN_ROOT}" \
  --working-dir "${CLAUDE_WORKING_DIR}" \
  --feature-dir "${FEATURE_DIR}" \
  ${BRANCH_NAME:+--branch-name "${BRANCH_NAME}"}
```

3. If the script fails, stop and report the exact error. Do not continue to `tasks`.
4. On success, report the generated `spec.md`, `design.md`, `context.md`, and source brainstorming document paths.

## Rules

- This skill is expert-only. Do not call it from `express`, `standard`, or `deep`.
- Do not overwrite the original brainstorming `*-design.md` file.
- Do not ask new design questions and do not redo design decisions.
- Do not hand-write `.omnispec-state.json`; the script uses `workflow-update-state.sh`.
- `design.md` is retained as a downstream interface file even though the `design` workflow stage is skipped.
