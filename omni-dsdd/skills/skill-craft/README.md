# Skill Craft

> Claude Skill quality engineering tool — Evaluate / Fix / Create / Audit

A quality framework for Claude Code Skills, covering the full lifecycle with 8-module evaluation, 7 anti-pattern detection, and 3 completeness principles.

## Documentation

- [README-CN.md](README-CN.md) - Chinese documentation
- [README-EN.md](README-EN.md) - English documentation

## Quick Start

Copy `SKILL.md`, `references/`, and `scripts/` to `~/.claude/skills/skill-craft/`, then:

```
# Evaluate a Skill
evaluate /path/to/my-skill

# Fix a Skill
fix /path/to/my-skill

# Create a new Skill
create a code audit skill

# Audit a multi-Skill system
audit /path/to/skills-directory
```

## Evaluation Framework

| Dimension | Weight | Content |
|-----------|--------|---------|
| 8-Module Check | 60% | Trigger conditions, behavioral rules, tool priority, output constraints, process checkpoints, dependency chain, sub-agent delegation, hallucination prevention |
| 7 Anti-Pattern Assessment | 25% | Instruction decay, tool drift, output bloat, dependency chain break, parallel isolation, trigger ambiguity, hallucination padding |
| 3 Completeness Principles | 15% | Countable acceptance criteria, checkpoint cutoff, failure path definition |

## Structure

```
skill-craft/
├── SKILL.md                              # Main skill definition
├── references/                           # On-demand reference docs
│   ├── check-guide.md                    # Check flow + quality framework
│   ├── fix-guide.md                      # Fix flow + repair constraints
│   ├── create-guide.md                   # Create flow + generation guide
│   ├── audit-guide.md                    # Audit flow + audit standards
│   ├── quality-standards.md              # 7 anti-patterns + 3 completeness
│   ├── practical-best-practices.md       # Real-world best practices
│   ├── report-template.md                # Report template
│   └── skill-scaffold.md                 # New Skill scaffold
└── scripts/                              # Automated validators
    ├── validate-metadata.py              # Name + description validation
    └── validate-structure.py             # Structure + module + reference check
```

## License

MIT
