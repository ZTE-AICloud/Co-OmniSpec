---
name: report-persistence
description: Persists review results (security or code review) to structured JSON and Markdown files for traceability. Called as a sub-step after completing any review.
---

## Report Persistence

After completing the review and reporting findings to the conversation, persist the results to files for traceability.

### Input Parameters

The calling skill must provide:

- `REVIEW_TYPE`: e.g. `security-review`, `code-review`
- `FINDINGS`: structured findings
- `SUMMARY`: counts by severity (CRITICAL, HIGH, MEDIUM, LOW)
- `VERDICT`: APPROVE, WARNING, BLOCK
- `FILES_REVIEWED`: number of files reviewed
- `FILES_CHANGED`: list of changed file paths

---

## Environment setup

| Variable | Meaning |
|----------|---------|
| `CLAUDE_PLUGIN_ROOT` | Plugin root (`check-prerequisites` scripts) |
| `CLAUDE_WORKING_DIR` | Workspace directory (git cwd, fallback reports) |
| `FEATURE_DIR` | Feature under `${CLAUDE_WORKING_DIR}/changes/...` |

If `CLAUDE_WORKING_DIR` is missing: `export CLAUDE_WORKING_DIR="$(pwd)"` (**do not** use `git rev-parse --show-toplevel`).

Prefer `source "${FEATURE_DIR}/.runs/env.sh"` when `FEATURE_DIR` is already known.

### 1.1 Resolve report directory

1. If `FEATURE_DIR` is set and the directory exists →  
   - JSON: `${FEATURE_DIR}/.runs/evaluations/`  
   - Markdown: `${FEATURE_DIR}/${REVIEW_TYPE}.md` (feature root, not under `evaluations/`)
2. Else run (under **`CLAUDE_WORKING_DIR`**):
   ```bash
   cd "${CLAUDE_WORKING_DIR}" && bash "${CLAUDE_PLUGIN_ROOT}/scripts/bash/check-prerequisites.sh" --json --paths-only
   ```
   Parse `FEATURE_DIR` from JSON; if valid, use paths as in (1).
3. Else fallback → `${CLAUDE_WORKING_DIR}/.runs/evaluations/` for JSON only; note fallback in report header.

Create target directories if missing (`mkdir -p`).

### 1.2 Write JSON report

Write `${REVIEW_TYPE}-summary.json` under the evaluations directory with this structure:

```json
{
  "timestamp": "<ISO8601>",
  "branch": "<current git branch>",
  "commit": "<current commit hash, short>",
  "files_reviewed": <number>,
  "files_changed": ["<paths>"],
  "findings": [
    {
      "severity": "CRITICAL|HIGH|MEDIUM|LOW",
      "file": "<file path>",
      "line": <line number or null>,
      "category": "<issue category>",
      "issue": "<issue description>",
      "fix": "<suggested fix>",
      "confidence": <0.0-1.0>
    }
  ],
  "summary": {
    "CRITICAL": <count>,
    "HIGH": <count>,
    "MEDIUM": <count>,
    "LOW": <count>
  },
  "verdict": "APPROVE|WARNING|BLOCK"
}
```

Use `git -C "${CLAUDE_WORKING_DIR}"` for branch/commit when recording metadata.

### 1.3 Write Markdown report

Write `${REVIEW_TYPE}.md` to the **feature directory root** (when `FEATURE_DIR` is known), or document workspace fallback. Same content as the conversation output (findings + summary table + verdict), with timestamp, branch, and commit in the header.

### 1.4 Rules

- Purely additive — does not change review logic or conversation output.
- If file writing fails, log a warning and continue; do not block the review.
- Zero findings: still write files (empty `findings` array, verdict `APPROVE`).
