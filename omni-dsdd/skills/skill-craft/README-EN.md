# Skill Craft — Skill Quality Engineering Tool

> Evaluate / Fix / Create / Audit — full lifecycle quality management for Claude Skills.

## Overview

| Mode | Triggers | Purpose |
|------|----------|---------|
| **check** | "evaluate skill", "skill quality", "review skill" | 8-module quality scoring for a single Skill |
| **fix** | "fix skill", "repair skill" | Evaluate + prioritized fixes + regression verification |
| **create** | "create skill", "build a new skill" | Generate a quality-compliant Skill from scratch |
| **audit** | "audit skill system", "route conflict check" | Multi-Skill system-level consistency audit |

## Evaluation Framework

**Four-dimensional scoring** (weighted):
- **8-Module Check** (55%): Trigger conditions, behavioral rules, tool priority, output constraints, process checkpoints, dependency chain, sub-agent delegation, hallucination prevention
- **7 Anti-Pattern Assessment** (20%): Instruction decay, tool drift, output bloat, dependency chain break, parallel isolation, trigger ambiguity, hallucination padding
- **3 Completeness Principles** (15%): Countable acceptance criteria, checkpoint cutoff, failure path definition
- **Decision Gate** (10%): Checks whether signals bypass evidence / counter-evidence and become strong conclusions

> **Hard Cap**: If any of these triggers — trigger-rule conflict / DG Fail ≥ 2 / broken core reference / validate script FAIL / quick check masquerading as deep — the weighted total is clamped to `≤ 6.0/10` and the report is tagged "⚠️ Hard Cap Triggered".

## Directory Structure

```
skill-craft/
├── SKILL.md
├── references/
│   ├── check-guide.md
│   ├── fix-guide.md
│   ├── create-guide.md
│   ├── audit-guide.md
│   ├── quality-standards.md
│   ├── decision-gates.md
│   ├── practical-best-practices.md
│   ├── report-template.md
│   └── skill-scaffold.md
└── scripts/
    ├── validate-metadata.py
    └── validate-structure.py
```

## Quick Start

### Evaluate a Skill
```
evaluate /path/to/my-skill
```
Output: 8-module scores + 7 anti-pattern risks + 3 completeness ratings + action items

### Fix a Skill
```
fix /path/to/my-skill
```
Output: Issue list (P0/P1/P2) -> per-item fix -> regression evaluation (pre vs post scores)

### Create a Skill
```
create a code audit skill
```
Output: Requirements clarification -> scale determination -> file generation -> self-check -> automated validation

### Audit a Multi-Skill System
```
audit /path/to/skills-directory
```
Output: Route conflicts + consistency + reference integrity + P0/P1/P2 system-level issues

## Automated Validation

```bash
# Validate metadata (name + description)
python3 scripts/validate-metadata.py --path /path/to/skill

# Validate structure (directories + 8 modules + reference integrity + empty file detection)
python3 scripts/validate-structure.py --path /path/to/skill
```

## Design Principles

- **Context protection**: SKILL.md remains a lightweight entry point, references load on demand
- **Checkpoint-driven**: Each step must output a checkpoint before proceeding
- **Regression verification**: Fix mode re-runs check after repairs to confirm score improvement
- **Scoring calibration**: 5 modules have concrete 0/1/2 score examples to reduce LLM judgment variance
- **Decision Gate**: Prevents weak signals, keywords, or structural hits from becoming strong conclusions directly
- **Anti-failure**: Defenses designed around 7 systematic LLM failure modes

## Versions

- `skill-craft`: Single-directory version, responds in the user's language
