#!/usr/bin/env python3
"""specify 产物模板契约校验（从 template-contract.json 驱动）。"""

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

_CONTRACT_PATH = (
    Path(__file__).resolve().parent.parent.parent / "references" / "template-contract.json"
)

PLACEHOLDER_MARKERS = (
    "（未识别到相关内容）",
    "[FEATURE NAME]",
    "[DATE]",
    "[###-feature-name]",
    "$ARGUMENTS",
    "[可衡量的指标",
    "[实体 1]",
)

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)


def working_infra_root(working_dir: Path) -> Path:
    """工作区 omni-infra 根：优先 .omni-infra，禁止用 __file__ 推断仓库根。"""
    base = working_dir.resolve()
    for name in (".omni-infra", "omni-infra"):
        candidate = base / name
        if candidate.is_dir():
            return candidate
    raise FileNotFoundError(
        f"工作区 omni-infra 不存在: 期望 {base}/.omni-infra 或 {base}/omni-infra；"
        "请先执行 init_omni_infra.sh 或 Task(subagent_type=\"omni-dsdd:constitution\")"
    )


def load_contract(path: Optional[Path] = None) -> Dict[str, Any]:
    contract_path = path or _CONTRACT_PATH
    return json.loads(contract_path.read_text(encoding="utf-8"))


def extract_headings(text: str, level: int = 2) -> List[str]:
    prefix = "#" * level + " "
    titles: List[str] = []
    for match in HEADING_RE.finditer(text):
        marks, title = match.group(1), match.group(2).strip()
        if len(marks) == level:
            titles.append(title)
    return titles


def has_heading(text: str, title: str, level: int = 2) -> bool:
    titles = extract_headings(text, level)
    base = title.strip()
    return any(t == base or t.startswith(base) or base in t for t in titles)


def section_body(text: str, heading_title: str, level: int = 2) -> str:
    pattern = rf"^{'#' * level}\s+{re.escape(heading_title)}[^\n]*\n"
    match = re.search(pattern, text, re.MULTILINE)
    if not match:
        for t in extract_headings(text, level):
            if t.startswith(heading_title) or heading_title in t:
                pattern = rf"^{'#' * level}\s+{re.escape(t)}[^\n]*\n"
                match = re.search(pattern, text, re.MULTILINE)
                if match:
                    break
    if not match:
        return ""
    start = match.end()
    next_match = re.search(rf"^{'#' * level}\s+", text[start:], re.MULTILINE)
    end = start + next_match.start() if next_match else len(text)
    return text[start:end].strip()


def count_placeholder_sections(text: str, required_titles: List[str], level: int = 2) -> int:
    count = 0
    for title in required_titles:
        body = section_body(text, title, level)
        if not body:
            continue
        if "（未识别到相关内容）" in body and len(body) < 120:
            count += 1
            continue
        if any(marker in body for marker in PLACEHOLDER_MARKERS) and len(body) < 80:
            count += 1
    return count


def validate_patterns(text: str, patterns: List[Dict[str, Any]]) -> List[str]:
    errors: List[str] = []
    for item in patterns:
        regex = item["regex"]
        min_count = int(item.get("min_count", 1))
        found = len(re.findall(regex, text, re.MULTILINE | re.IGNORECASE))
        if found < min_count:
            hint = item.get("hint", regex)
            errors.append(f"missing pattern {item.get('id', regex)}: need>={min_count}, got={found} ({hint})")
    return errors


def validate_artifact(rel_path: str, text: str, contract: Optional[Dict[str, Any]] = None) -> List[str]:
    contract = contract or load_contract()
    rules = contract.get("artifacts", {}).get(rel_path)
    if not rules:
        return [f"unknown artifact in contract: {rel_path}"]

    errors: List[str] = []

    for title in rules.get("required_headings", []):
        if not has_heading(text, title, level=2):
            errors.append(f"{rel_path}: missing section ## {title}")

    min_section = int(rules.get("min_section_chars", 0))
    per_heading = rules.get("min_section_chars_by_heading", {})
    if min_section > 0 or per_heading:
        for title in rules.get("required_headings", []):
            body = section_body(text, title, level=2)
            if not body:
                continue
            threshold = int(per_heading.get(title, min_section))
            if threshold > 0 and len(body) < threshold:
                errors.append(
                    f"{rel_path}: section ## {title} too short ({len(body)} < {threshold} chars)"
                )

    max_placeholder = rules.get("max_placeholder_sections")
    if max_placeholder is not None:
        placeholders = count_placeholder_sections(text, rules.get("required_headings", []))
        if placeholders > int(max_placeholder):
            errors.append(
                f"{rel_path}: too many placeholder sections ({placeholders} > {max_placeholder}); "
                "rerun spec-impact-analyze or fill context.payload.json"
            )

    for line in rules.get("required_metadata_lines", []):
        if line not in text:
            errors.append(f"{rel_path}: missing metadata line {line}")

    errors.extend(validate_patterns(text, rules.get("patterns", [])))

    min_checks = rules.get("min_checkbox_items")
    if min_checks is not None:
        checks = len(re.findall(r"^- \[[ xX]\]", text, re.MULTILINE))
        if checks < int(min_checks):
            errors.append(
                f"{rel_path}: checkbox items {checks} < {min_checks} "
                "(copy from .omni-infra/templates/requirements-template.md)"
            )

    for token in rules.get("required_tokens", []):
        if token not in text:
            errors.append(f"{rel_path}: missing token {token}")

    return errors


def render_spec_skeleton(
    *,
    feature_name: str,
    branch_name: str,
    user_input: str,
    working_dir: Path,
    template_path: Optional[Path] = None,
) -> str:
    infra = working_infra_root(working_dir)
    tpl_path = template_path or (infra / "templates" / "spec-template.md")
    if not tpl_path.is_file():
        raise FileNotFoundError(f"spec template not found: {tpl_path}")

    from datetime import date

    text = tpl_path.read_text(encoding="utf-8")
    replacements = {
        "[FEATURE NAME]": feature_name or "未命名功能",
        "[###-feature-name]": branch_name or "000-feature",
        "[DATE]": date.today().isoformat(),
        "$ARGUMENTS": user_input or "",
    }
    for key, value in replacements.items():
        text = text.replace(key, value)
    return text


def render_requirements_checklist_skeleton(
    *,
    feature_name: str,
    spec_rel_link: str = "../spec.md",
    working_dir: Path,
    template_path: Optional[Path] = None,
) -> str:
    infra = working_infra_root(working_dir)
    tpl_path = template_path or (infra / "templates" / "requirements-template.md")
    if not tpl_path.is_file():
        raise FileNotFoundError(f"requirements template not found: {tpl_path}")

    from datetime import date

    text = tpl_path.read_text(encoding="utf-8")
    replacements = {
        "[功能名称]": feature_name or "未命名功能",
        "[日期]": date.today().isoformat(),
        "[指向 spec.md 的链接]": spec_rel_link,
    }
    for key, value in replacements.items():
        text = text.replace(key, value)
    return text
