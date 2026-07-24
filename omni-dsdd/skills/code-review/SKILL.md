---
name: code-review
description: Proactively reviews code for quality, security, and maintainability. Use immediately after writing or modifying code. MUST BE USED for all code changes.
context: fork
---

## Goal

**Ensuring high standards of code quality and security.**

---

## Environment setup

All path resolution and git commands use the variables below. Do not infer repo root via `git rev-parse --show-toplevel` for workspace boundaries.

| Variable | Meaning | Use |
|----------|---------|-----|
| `CLAUDE_PLUGIN_ROOT` | Omni plugin install root | Skill references, `check-prerequisites` |
| `CLAUDE_WORKING_DIR` | User workspace directory (may be a Git subfolder) | `git -C`, project rules, fallback report path |
| `FEATURE_DIR` | Current feature under `changes/` | Report output via `omni-dsdd:report-persistence` |

### Step 0.1 — Check variables

```bash
test -n "${CLAUDE_PLUGIN_ROOT:-}" && test -d "${CLAUDE_PLUGIN_ROOT}"
test -n "${CLAUDE_WORKING_DIR:-}" && test -d "${CLAUDE_WORKING_DIR}"
```

If missing, resolve once at agent layer: `CLAUDE_WORKING_DIR` → `export CLAUDE_WORKING_DIR="$(pwd)"` (**do not** use `git rev-parse --show-toplevel`). `CLAUDE_PLUGIN_ROOT` → verify `${path}/skills/code-review/SKILL.md` exists.

### Step 0.2 — Validate and optional harness env

```bash
test -f "${CLAUDE_PLUGIN_ROOT}/skills/code-review/SKILL.md"
test -d "${CLAUDE_WORKING_DIR}"
```

Before resolving report paths, inherit `FEATURE_DIR` from the specify chain (do not guess from Git branch):

```bash
eval "$(bash "${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/bash/design-resolve-context.sh" \
  --plugin-root "${CLAUDE_PLUGIN_ROOT}" \
  --working-dir "${CLAUDE_WORKING_DIR}" \
  ${FEATURE_DIR:+--feature-dir "$FEATURE_DIR"} \
  --export)" 2>/dev/null || true
[[ -f "${FEATURE_DIR}/.runs/env.sh" ]] && source "${FEATURE_DIR}/.runs/env.sh"
```

### Path rules

- Git: always `git -C "${CLAUDE_WORKING_DIR}" ...`
- Language references: `${CLAUDE_PLUGIN_ROOT}/skills/code-review/references/<lang>/...`
- Reports (via `omni-dsdd:report-persistence`): prefer `${FEATURE_DIR}/.runs/evaluations/` and `${FEATURE_DIR}/code-review.md`; see step 6

---

## Review Process

When invoked:

1. **Gather context** — Run `git -C "${CLAUDE_WORKING_DIR}" diff --staged` and `git -C "${CLAUDE_WORKING_DIR}" diff`. If no diff, `git -C "${CLAUDE_WORKING_DIR}" log --oneline -5`.
2. **Understand scope** — Identify which files changed, what feature/fix they relate to, and how they connect.
3. **Read surrounding code** — Don't review changes in isolation. Read the full file and understand imports, dependencies, and call sites.
4. **Apply review checklist** — Work through each category below, from CRITICAL to LOW.
5. **Report findings** — Use the output format below. Only report issues you are confident about (>80% sure it is a real problem).
6. **Persist report** — Call the `omni-dsdd:report-persistence` skill with:
   - `REVIEW_TYPE` = `code-review`
   - `FINDINGS`, `SUMMARY`, `VERDICT`, `FILES_REVIEWED`, `FILES_CHANGED` as defined there
   - Ensure `FEATURE_DIR` is set (Step 0.2 `design-resolve-context` + `source env.sh`; only if still unknown, `check-prerequisites --paths-only` with `--working-dir`/`--plugin-root` — **not** for Git branch guessing)
   - Expected outputs:
     - `${FEATURE_DIR}/.runs/evaluations/code-review-summary.json`
     - `${FEATURE_DIR}/code-review.md`
   - If `FEATURE_DIR` is unavailable, fall back to `${CLAUDE_WORKING_DIR}/.runs/evaluations/` (document in the report header)

## Confidence-Based Filtering

**IMPORTANT**: Do not flood the review with noise. Apply these filters:

- **Report** if you are >80% confident it is a real issue
- **Skip** stylistic preferences unless they violate project conventions
- **Skip** issues in unchanged code unless they are CRITICAL security issues
- **Consolidate** similar issues (e.g., "5 functions missing error handling" not 5 separate findings)
- **Prioritize** issues that could cause bugs, security vulnerabilities, or data loss

### Pre-Report Gate

Before writing a finding, answer all four questions. If any answer is "no" or
"unsure", downgrade severity or drop the finding.

1. **Can I cite the exact line?** Name the file and line. Vague findings like
   "somewhere in the auth layer" are not actionable and must be dropped.
2. **Can I describe the concrete failure mode?** Name the input, state, and bad
   outcome. If you cannot name the trigger, you are pattern-matching, not
   reviewing.
3. **Have I read the surrounding context?** Check callers, imports, and tests.
   Many apparent issues are already handled one frame up or guarded by a type.
4. **Is the severity defensible?** A missing JSDoc is never HIGH. A single
   `any` in a test fixture is never CRITICAL. Severity inflation erodes trust
   faster than missed findings.

### HIGH / CRITICAL Require Proof

For any finding tagged HIGH or CRITICAL, include:

- The exact snippet and line number
- The specific failure scenario: input, state, and outcome
- Why existing guards, such as types, validation, or framework defaults, do not
  catch it

If you cannot produce all three, demote to MEDIUM or drop.

### It Is Acceptable And Expected To Return Zero Findings

A clean review is a valid review. Do not manufacture findings to justify the
invocation. If the diff is small, well-typed, tested, and follows the project's
patterns, the correct output is a summary with zero rows and verdict `APPROVE`.

Manufactured findings, filler nits, speculative "consider using X", and
hypothetical edge cases without a trigger are the primary failure mode of LLM
reviewers and directly undermine this agent's usefulness.

## Common False Positives - Skip These

Patterns that LLM reviewers commonly mis-flag. Skip unless you have evidence
specific to this codebase:

- **"Consider adding error handling"** on a call whose error path is handled by
  the caller or framework, such as Express error middleware, React error
  boundaries, top-level `try/catch`, or Promise chains with `.catch` upstream.
- **"Missing input validation"** when the function is internal and its callers
  already validate. Trace at least one caller before flagging.
- **"Magic number"** for well-known constants: `200`, `404`, `1000` ms, `60`,
  `24`, `1024`, array index `0` or `-1`, HTTP status codes, and single-use
  local constants whose meaning is obvious from the variable name.
- **"Function too long"** for exhaustive `switch` statements, configuration
  objects, test tables, or generated code. Length is not complexity.
- **"Missing JSDoc"** on single-purpose internal helpers whose name and
  signature are self-describing.
- **"Prefer `const` over `let`"** when the variable is reassigned. Read the
  whole function before flagging.
- **"Possible null dereference"** when the preceding line narrows the type or an
  `if` guard is in scope. Trace type flow instead of pattern-matching on `?.`.
- **"N+1 query"** on fixed-cardinality loops, such as iterating a four-element
  enum, or on paths already using `DataLoader` or batching.
- **"Missing await"** on fire-and-forget calls that are intentionally detached,
  such as logging, metrics, or background queue pushes. Check for a comment or
  `void` prefix before flagging.
- **"Should use TypeScript"** or **"Should have types"** in a JavaScript-only
  file. Match the project's existing language; do not suggest a stack change.
- **"Hardcoded value"** for values in test fixtures, example code, or
  documentation snippets. Tests should have hardcoded expectations.
- **Security theater**: flagging `Math.random()` in a non-cryptographic context
  such as animation, jitter, or sampling, or flagging `eval`/`Function` in a
  plugin system that is explicitly a code-loading surface.

When tempted to flag one of the above, ask: "Would a senior engineer on this
team actually change this in review?" If no, skip.

## Review Checklist

### Security (CRITICAL)

These MUST be flagged — they can cause real damage:

- **Hardcoded credentials** — API keys, passwords, tokens, connection strings in source
- **SQL injection** — String concatenation in queries instead of parameterized queries
- **XSS vulnerabilities** — Unescaped user input rendered in HTML/JSX
- **Path traversal** — User-controlled file paths without sanitization
- **CSRF vulnerabilities** — State-changing endpoints without CSRF protection
- **Authentication bypasses** — Missing auth checks on protected routes
- **Insecure dependencies** — Known vulnerable packages
- **Exposed secrets in logs** — Logging sensitive data (tokens, passwords, PII)

```typescript
// BAD: SQL injection via string concatenation
const query = `SELECT * FROM users WHERE id = ${userId}`;

// GOOD: Parameterized query
const query = `SELECT * FROM users WHERE id = $1`;
const result = await db.query(query, [userId]);
```

```typescript
// BAD: Rendering raw user HTML without sanitization
// Always sanitize user content with DOMPurify.sanitize() or equivalent

// GOOD: Use text content or sanitize
<div>{userComment}</div>
```

### Code Quality (HIGH)

- **Large functions** (>50 lines) — Split into smaller, focused functions
- **Large files** (>800 lines) — Extract modules by responsibility
- **Deep nesting** (>4 levels) — Use early returns, extract helpers
- **Missing error handling** — Unhandled promise rejections, empty catch blocks
- **Mutation patterns** — Prefer immutable operations (spread, map, filter)
- **console.log statements** — Remove debug logging before merge
- **Missing tests** — New code paths without test coverage
- **Dead code** — Commented-out code, unused imports, unreachable branches

```typescript
// BAD: Deep nesting + mutation
function processUsers(users) {
  if (users) {
    for (const user of users) {
      if (user.active) {
        if (user.email) {
          user.verified = true;  // mutation!
          results.push(user);
        }
      }
    }
  }
  return results;
}

// GOOD: Early returns + immutability + flat
function processUsers(users) {
  if (!users) return [];
  return users
    .filter(user => user.active && user.email)
    .map(user => ({ ...user, verified: true }));
}
```

### React/Next.js Patterns (HIGH)

When reviewing React/Next.js code, also check:

- **Missing dependency arrays** — `useEffect`/`useMemo`/`useCallback` with incomplete deps
- **State updates in render** — Calling setState during render causes infinite loops
- **Missing keys in lists** — Using array index as key when items can reorder
- **Prop drilling** — Props passed through 3+ levels (use context or composition)
- **Unnecessary re-renders** — Missing memoization for expensive computations
- **Client/server boundary** — Using `useState`/`useEffect` in Server Components
- **Missing loading/error states** — Data fetching without fallback UI
- **Stale closures** — Event handlers capturing stale state values

```tsx
// BAD: Missing dependency, stale closure
useEffect(() => {
  fetchData(userId);
}, []); // userId missing from deps

// GOOD: Complete dependencies
useEffect(() => {
  fetchData(userId);
}, [userId]);
```

```tsx
// BAD: Using index as key with reorderable list
{items.map((item, i) => <ListItem key={i} item={item} />)}

// GOOD: Stable unique key
{items.map(item => <ListItem key={item.id} item={item} />)}
```

### Node.js/Backend Patterns (HIGH)

When reviewing backend code:

- **Unvalidated input** — Request body/params used without schema validation
- **Missing rate limiting** — Public endpoints without throttling
- **Unbounded queries** — `SELECT *` or queries without LIMIT on user-facing endpoints
- **N+1 queries** — Fetching related data in a loop instead of a join/batch
- **Missing timeouts** — External HTTP calls without timeout configuration
- **Error message leakage** — Sending internal error details to clients
- **Missing CORS configuration** — APIs accessible from unintended origins

```typescript
// BAD: N+1 query pattern
const users = await db.query('SELECT * FROM users');
for (const user of users) {
  user.posts = await db.query('SELECT * FROM posts WHERE user_id = $1', [user.id]);
}

// GOOD: Single query with JOIN or batch
const usersWithPosts = await db.query(`
  SELECT u.*, json_agg(p.*) as posts
  FROM users u
  LEFT JOIN posts p ON p.user_id = u.id
  GROUP BY u.id
`);
```

### Performance (MEDIUM)

- **Inefficient algorithms** — O(n^2) when O(n log n) or O(n) is possible
- **Unnecessary re-renders** — Missing React.memo, useMemo, useCallback
- **Large bundle sizes** — Importing entire libraries when tree-shakeable alternatives exist
- **Missing caching** — Repeated expensive computations without memoization
- **Unoptimized images** — Large images without compression or lazy loading
- **Synchronous I/O** — Blocking operations in async contexts

### Best Practices (LOW)

- **TODO/FIXME without tickets** — TODOs should reference issue numbers
- **Missing JSDoc for public APIs** — Exported functions without documentation
- **Poor naming** — Single-letter variables (x, tmp, data) in non-trivial contexts
- **Magic numbers** — Unexplained numeric constants
- **Inconsistent formatting** — Mixed semicolons, quote styles, indentation

## Review Output Format

Organize findings by severity. For each issue:

```
[CRITICAL] Hardcoded API key in source
File: src/api/client.ts:42
Issue: API key "sk-abc..." exposed in source code. This will be committed to git history.
Fix: Move to environment variable and add to .gitignore/.env.example

  const apiKey = "sk-abc123";           // BAD
  const clientToken = process.env.EXAMPLE_KEY;   // GOOD
```

### Summary Format

End every review with:

```
## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0     | pass   |
| HIGH     | 2     | warn   |
| MEDIUM   | 3     | info   |
| LOW      | 1     | note   |

Verdict: WARNING — 2 HIGH issues should be resolved before merge.
```

## Approval Criteria

- **Approve**: No CRITICAL or HIGH issues, including clean reviews with zero
  findings. This is a valid and expected outcome.
- **Warning**: HIGH issues only (can merge with caution)
- **Block**: CRITICAL issues found — must fix before merge

Do not withhold approval to appear rigorous. If the diff is clean, approve it.

## Project-Specific Guidelines

When available, also check project-specific conventions from `${CLAUDE_WORKING_DIR}/CLAUDE.md`, `${CLAUDE_WORKING_DIR}/.omni-infra/memory/constitution.md`, or project rules:

- File size limits (e.g., 200-400 lines typical, 800 max)
- Emoji policy (many projects prohibit emojis in code)
- Immutability requirements (spread operator over mutation)
- Database policies (RLS, migration patterns)
- Error handling patterns (custom error classes, error boundaries)
- State management conventions (Zustand, Redux, Context)

Adapt your review to the project's established patterns. When in doubt, match what the rest of the codebase does.

## v1.8 AI-Generated Code Review Addendum

When reviewing AI-generated changes, prioritize:

1. Behavioral regressions and edge-case handling
2. Security assumptions and trust boundaries
3. Hidden coupling or accidental architecture drift
4. Unnecessary model-cost-inducing complexity

Cost-awareness check:
- Flag workflows that escalate to higher-cost models without clear reasoning need.
- Recommend defaulting to lower-cost tiers for deterministic refactors.

## Language-Specific References

When reviewing, detect the language/framework of the changed files and load the corresponding reference files for detailed checklist items and code examples.

| File Extension / Pattern | Reference Directory |
|--------------------------|---------------------|
| `*.cpp`, `*.hpp`, `*.cc`, `*.h`, `CMakeLists.txt` | `${CLAUDE_PLUGIN_ROOT}/skills/code-review/references/cpp` |
| `*.go`, `go.mod` | `${CLAUDE_PLUGIN_ROOT}/skills/code-review/references/golang` |
| `*.java`, `pom.xml`, `build.gradle` | `${CLAUDE_PLUGIN_ROOT}/skills/code-review/references/java` |
| `*.py`, `*.pyi` | `${CLAUDE_PLUGIN_ROOT}/skills/code-review/references/python` |
| `*.rs`, `Cargo.toml` | `${CLAUDE_PLUGIN_ROOT}/skills/code-review/references/rust` |
| `*.ts`, `*.tsx`, `*.js`, `*.jsx` | `${CLAUDE_PLUGIN_ROOT}/skills/code-review/references/typescript` |
| `*.css`, `*.scss`, `*.html`, frontend components | `${CLAUDE_PLUGIN_ROOT}/skills/code-review/references/web` |

When multiple languages are present in the same diff, load all applicable references (paths under the plugin root, not relative to cwd).

## Reference (plugin paths)

| Item | Path |
|------|------|
| This skill | `${CLAUDE_PLUGIN_ROOT}/skills/code-review/SKILL.md` |
| Prerequisites (bash) | `${CLAUDE_PLUGIN_ROOT}/scripts/bash/check-prerequisites.sh` |
| Report persistence | `${CLAUDE_PLUGIN_ROOT}/skills/report-persistence/SKILL.md` |