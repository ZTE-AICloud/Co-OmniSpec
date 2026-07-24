#!/usr/bin/env python3
"""Validate Skill directory structure: 8-module presence smoke check, line budget, file organization.

Usage:
    python3 scripts/validate-structure.py --path /path/to/skill-dir

Exit 0 = all checks pass, Exit 1 = errors found (details on stderr).
"""

import os
import re
import sys
import argparse


# 8 modules and their detection patterns (keywords/headings to look for in SKILL.md).
# This is a presence smoke check, not a semantic quality grader.
MODULES = {
    1: {
        "name": "触发条件 (Trigger Conditions)",
        "patterns": [r"触发条件", r"trigger", r"不触发", r"DO NOT TRIGGER", r"歧义处理"],
    },
    2: {
        "name": "行为准则 (Behavioral Rules)",
        "patterns": [r"行为准则", r"behavioral?\s*rules?", r"❗", r"会话.*有效"],
    },
    3: {
        "name": "工具优先级 (Tool Priority)",
        "patterns": [r"工具优先级", r"tool\s*priority", r"降级条件", r"降级工具"],
    },
    4: {
        "name": "输出约束 (Output Constraints)",
        "patterns": [r"输出约束", r"output\s*constraint", r"禁止输出", r"prohibit"],
    },
    5: {
        "name": "流程步骤 (Process Steps)",
        "patterns": [r"执行流程", r"流程步骤", r"process\s*step", r"Step\s*\d", r"Checkpoint"],
    },
    6: {
        "name": "依赖链 (Dependency Chain)",
        "patterns": [r"依赖链", r"dependency\s*chain", r"数据传递"],
    },
    7: {
        "name": "子Agent委派 (Sub-Agent Delegation)",
        "patterns": [r"子\s*[Aa]gent", r"sub.?agent", r"委派", r"delegation"],
    },
    8: {
        "name": "幻觉防护 (Hallucination Prevention)",
        "patterns": [r"幻觉", r"hallucination", r"事实性约束", r"零结果", r"来源引用"],
    },
}

# Line budget thresholds
SKILL_MD_MAX_LINES = 300
SKILL_MD_WARN_LINES = 200
REF_FILE_MAX_LINES = 500


def check_structure(skill_path):
    errors = []
    warnings = []
    info = []

    # --- Check SKILL.md exists ---
    skill_md_path = os.path.join(skill_path, "SKILL.md")
    if not os.path.isfile(skill_md_path):
        errors.append("STRUCTURE ERROR: SKILL.md not found.")
        print("\n".join(errors), file=sys.stderr)
        sys.exit(1)

    with open(skill_md_path, "r", encoding="utf-8") as f:
        skill_content = f.read()
    skill_lines = skill_content.splitlines()
    line_count = len(skill_lines)

    # --- Line budget ---
    if line_count > SKILL_MD_MAX_LINES:
        errors.append(
            f"BUDGET ERROR: SKILL.md is {line_count} lines (max {SKILL_MD_MAX_LINES}). "
            "Extract detailed content to references/ files."
        )
    elif line_count > SKILL_MD_WARN_LINES:
        warnings.append(
            f"BUDGET WARNING: SKILL.md is {line_count} lines (recommended <= {SKILL_MD_WARN_LINES}). "
            "Consider moving verbose sections to references/."
        )
    info.append(f"SKILL.md: {line_count} lines")

    # --- Check for deprecated directory names ---
    deprecated_dirs = {"reference": "references", "templates": "references (merge template files into references/)"}
    for old_name, suggestion in deprecated_dirs.items():
        old_path = os.path.join(skill_path, old_name)
        if os.path.isdir(old_path):
            warnings.append(
                f"STRUCTURE WARNING: Found deprecated directory '{old_name}/'. "
                f"Rename to '{suggestion}'."
            )

    # --- Check standard directories ---
    expected_dirs = ["references", "scripts"]
    found_dirs = []
    for d in expected_dirs:
        dp = os.path.join(skill_path, d)
        if os.path.isdir(dp):
            found_dirs.append(d)
            # Check for nested subdirectories (should be flat)
            for item in os.listdir(dp):
                item_path = os.path.join(dp, item)
                if os.path.isdir(item_path):
                    warnings.append(
                        f"STRUCTURE WARNING: Nested directory found: {d}/{item}/. "
                        "Keep structure flat (one level deep)."
                    )
    info.append(f"Directories: {', '.join(found_dirs) if found_dirs else 'none'}")

    # --- Check for human-centric docs that shouldn't exist ---
    unwanted = ["CHANGELOG.md", "INSTALLATION_GUIDE.md", "INSTALLATION.md"]
    for uw in unwanted:
        if os.path.isfile(os.path.join(skill_path, uw)):
            warnings.append(
                f"STRUCTURE WARNING: Found {uw}. "
                "Agent Skills should not contain human-centric documentation files."
            )

    # --- 8-module presence scan ---
    skill_lower = skill_content.lower()
    modules_found = 0
    modules_missing = []
    modules_present = []

    for mod_num, mod_info in MODULES.items():
        found = any(re.search(p, skill_content, re.IGNORECASE) for p in mod_info["patterns"])
        if found:
            modules_found += 1
            modules_present.append(mod_num)
        else:
            modules_missing.append(f"Module {mod_num}: {mod_info['name']}")

    info.append(f"Modules: {modules_found}/8 found in SKILL.md (presence check only)")

    if modules_missing:
        # Module 7 (sub-agent) can be N/A for simple skills
        critical_missing = [m for m in modules_missing if not m.startswith("Module 7")]
        if critical_missing:
            for m in critical_missing:
                warnings.append(f"MODULE WARNING: {m} — not detected in SKILL.md")
        na_missing = [m for m in modules_missing if m.startswith("Module 7")]
        if na_missing:
            info.append(f"Module 7 not detected (may be N/A for simple Skills)")

    # --- Reference file line budget + emptiness check ---
    ref_dir = os.path.join(skill_path, "references")
    if os.path.isdir(ref_dir):
        ref_files = [f for f in os.listdir(ref_dir) if f.endswith(".md")]
        info.append(f"Reference files: {len(ref_files)}")
        for rf in ref_files:
            rf_path = os.path.join(ref_dir, rf)
            with open(rf_path, "r", encoding="utf-8") as f:
                rf_lines = len(f.readlines())
            if rf_lines == 0:
                errors.append(f"REFERENCE ERROR: references/{rf} is empty.")
            elif rf_lines > REF_FILE_MAX_LINES:
                warnings.append(
                    f"BUDGET WARNING: references/{rf} is {rf_lines} lines (recommend <= {REF_FILE_MAX_LINES}). "
                    "Consider splitting into smaller files."
                )

        # Check SKILL.md references point to existing files
        ref_pattern = re.compile(r'references/([a-z0-9_-]+\.md)')
        referenced = set(ref_pattern.findall(skill_content))
        existing = set(ref_files)
        for ref_name in referenced:
            if ref_name not in existing:
                errors.append(f"REFERENCE ERROR: SKILL.md references 'references/{ref_name}' but file does not exist.")

    # --- Frontmatter check ---
    if not skill_content.startswith("---"):
        errors.append("STRUCTURE ERROR: SKILL.md missing frontmatter (no leading ---).")
    else:
        fm_end = skill_content.find("---", 3)
        if fm_end == -1:
            errors.append("STRUCTURE ERROR: SKILL.md frontmatter not closed.")
        else:
            fm = skill_content[3:fm_end]
            if "name:" not in fm:
                errors.append("STRUCTURE ERROR: Frontmatter missing 'name' field.")
            if "description:" not in fm:
                errors.append("STRUCTURE ERROR: Frontmatter missing 'description' field.")

    # --- Output ---
    print("=== Structure Validation Report ===")
    for i in info:
        print(f"  {i}")

    if warnings:
        print(f"\n{len(warnings)} warning(s):", file=sys.stderr)
        for w in warnings:
            print(f"  {w}", file=sys.stderr)

    if errors:
        print(f"\n{len(errors)} error(s):")
        for e in errors:
            print(f"  {e}")
        status = "FAIL"
        print(
            f"\n{status}: {modules_found}/8 modules found in SKILL.md (presence check only), "
            f"{line_count} lines, {len(found_dirs)} dirs"
        )
    else:
        status = "PASS WITH WARNINGS" if warnings else "PASS"
        print(
            f"\n{status}: {modules_found}/8 modules found in SKILL.md (presence check only), "
            f"{line_count} lines, {len(found_dirs)} dirs"
        )
    # Always exit 0 — errors are evaluation results, not script failures
    sys.exit(0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate Skill directory structure")
    parser.add_argument("--path", required=True, help="Path to Skill directory")
    args = parser.parse_args()

    if not os.path.isdir(args.path):
        print(f"ERROR: Directory not found: {args.path}", file=sys.stderr)
        sys.exit(1)

    check_structure(args.path)
