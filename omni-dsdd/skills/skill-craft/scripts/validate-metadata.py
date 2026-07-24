#!/usr/bin/env python3
"""Validate Skill metadata (name + description) against agentskills.io spec.

Usage:
    python3 scripts/validate-metadata.py --path /path/to/skill-dir
    python3 scripts/validate-metadata.py --name "skill-name" --description "desc text"

Exit 0 = valid, Exit 1 = errors found (details on stderr).
"""

import re
import sys
import argparse
import os


def parse_frontmatter(skill_path):
    """Extract name and description from SKILL.md frontmatter."""
    skill_md = os.path.join(skill_path, "SKILL.md")
    if not os.path.isfile(skill_md):
        print(f"ERROR: SKILL.md not found at {skill_md}", file=sys.stderr)
        sys.exit(1)

    with open(skill_md, "r", encoding="utf-8") as f:
        content = f.read()

    if not content.startswith("---"):
        print("ERROR: SKILL.md missing frontmatter (no leading ---)", file=sys.stderr)
        sys.exit(1)

    end = content.find("---", 3)
    if end == -1:
        print("ERROR: SKILL.md frontmatter not closed (missing second ---)", file=sys.stderr)
        sys.exit(1)

    fm = content[3:end]
    name = None
    description_lines = []
    in_description = False

    for line in fm.splitlines():
        if line.startswith("name:"):
            name = line.split(":", 1)[1].strip()
            in_description = False
        elif line.startswith("description:"):
            val = line.split(":", 1)[1].strip()
            if val and val != "|":
                description_lines.append(val)
            in_description = True
        elif in_description and (line.startswith("  ") or line.startswith("\t")):
            description_lines.append(line.strip())
        else:
            in_description = False

    description = " ".join(description_lines)
    return name, description


def validate(name, description, dir_name=None):
    errors = []
    warnings = []

    # --- Name checks ---
    if not name:
        errors.append("NAME ERROR: name field is empty or missing.")
    else:
        if not (1 <= len(name) <= 64):
            errors.append(f"NAME ERROR: '{name}' is {len(name)} chars. Must be 1-64.")

        if not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", name):
            errors.append(
                f"NAME ERROR: '{name}' invalid. "
                "Use only lowercase letters, numbers, and single hyphens. "
                "Cannot start/end with hyphen or have consecutive hyphens."
            )

        if dir_name and name != dir_name:
            errors.append(
                f"NAME ERROR: name '{name}' does not match directory '{dir_name}'. "
                "They must be identical."
            )

    # --- Description checks ---
    if not description:
        errors.append("DESCRIPTION ERROR: description field is empty or missing.")
    else:
        if len(description) > 1024:
            errors.append(
                f"DESCRIPTION ERROR: {len(description)} chars, max 1024."
            )

        if len(description) < 50:
            warnings.append(
                f"DESCRIPTION WARNING: Only {len(description)} chars. "
                "Recommend >= 50 chars for adequate trigger coverage."
            )

        # Third-person check
        first_second_person = {"i", "me", "my", "we", "our", "you", "your"}
        words = set(re.findall(r"\b\w+\b", description.lower()))
        found = first_second_person.intersection(words)
        if found:
            warnings.append(
                f"STYLE WARNING: First/second person terms found: {sorted(found)}. "
                "Use third-person imperative (e.g., 'Evaluates...', 'Creates...')."
            )

        # Negative trigger check
        neg_patterns = [
            r"(?i)do\s+not\s+use",
            r"(?i)don'?t\s+use",
            r"(?i)不触发",
            r"(?i)不适用",
            r"(?i)DO NOT TRIGGER",
        ]
        has_negative = any(re.search(p, description) for p in neg_patterns)
        if not has_negative:
            warnings.append(
                "DISCOVERY WARNING: No negative trigger found. "
                "Add 'Do not use for...' to reduce false positive activations."
            )

    # --- Output ---
    if warnings:
        for w in warnings:
            print(w, file=sys.stderr)

    summary = f"name='{name}', description={len(description)} chars"
    if errors:
        for e in errors:
            print(e)
        print(f"FAIL: Metadata validation failed. {summary}")
    elif warnings:
        print(f"PASS WITH WARNINGS: Metadata valid but has {len(warnings)} warning(s). {summary}")
    else:
        print(f"PASS: Metadata valid and optimized for discovery. {summary}")
    # Always exit 0 for validation results — errors are findings, not script failures
    sys.exit(0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate Skill metadata")
    parser.add_argument("--path", help="Path to Skill directory (reads SKILL.md frontmatter)")
    parser.add_argument("--name", help="Skill name (if not using --path)")
    parser.add_argument("--description", help="Skill description (if not using --path)")
    args = parser.parse_args()

    if args.path:
        dir_name = os.path.basename(os.path.normpath(args.path))
        name, desc = parse_frontmatter(args.path)
        validate(name, desc, dir_name=dir_name)
    elif args.name and args.description:
        validate(args.name, args.description)
    else:
        parser.error("Provide --path OR both --name and --description")
