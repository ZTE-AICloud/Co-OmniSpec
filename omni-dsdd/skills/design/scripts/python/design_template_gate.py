#!/usr/bin/env python3
"""design 产物模板契约校验（从 template-contract.json 驱动）。"""

import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

_SCRIPT_DIR = Path(__file__).resolve().parent
_CONTRACT_PATH = _SCRIPT_DIR.parent.parent / "references" / "template-contract.json"

_SPECIFY_PYTHON = _SCRIPT_DIR.parent.parent.parent / "specify" / "scripts" / "python"
if str(_SPECIFY_PYTHON) not in sys.path:
    sys.path.insert(0, str(_SPECIFY_PYTHON))

from specify_template_gate import (  # noqa: E402
    has_heading,
    section_body,
    validate_patterns,
    working_infra_root,
)

DESIGN_PLACEHOLDER_MARKERS = (
    "[FEATURE]",
    "[###-feature-name]",
    "[DATE]",
    "[link]",
    "[例如:",
    "[从功能规范中提取",
    "[记录所选结构",
    "[可观测的成功标准 1]",
    "[第一步：",
    "[功能名称]",
)


# Markdown 强调标记：匹配前剥离，使 `**Decision:**`/`Decision：` 等写法
# 与裸 `Decision:` 等价，避免门禁因加粗或全角标点误判 token 缺失。
_EMPHASIS_RE = re.compile(r"[*_`~]+")


def normalize_for_token(text: str) -> str:
    """规范化文本以做 token 子串匹配。

    - 剥离 Markdown 强调标记（``**`` ``*`` ``__`` ``_`` `` ` `` ``~``），故
      ``**Decision:**`` 与 ``Decision:`` 视作相同；
    - 全角标点归一为半角（``：`` → ``:``），兼容中文输入法误打。
    """
    stripped = _EMPHASIS_RE.sub("", text)
    return stripped.translate(str.maketrans({"：": ":", "（": "(", "）": ")", "，": ",", "；": ";"}))


def load_contract(path: Optional[Path] = None) -> Dict[str, Any]:
    contract_path = path or _CONTRACT_PATH
    return json.loads(contract_path.read_text(encoding="utf-8"))


def _merge_step_rules(base: Dict[str, Any], gate_step: Optional[str]) -> Dict[str, Any]:
    if not gate_step:
        return base
    steps = base.get("gate_steps", {})
    step_rules = steps.get(gate_step)
    if not step_rules:
        return base
    merged = {k: v for k, v in base.items() if k != "gate_steps"}
    for key, value in step_rules.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = {**merged[key], **value}
        else:
            merged[key] = value
    return merged


def validate_artifact(
    rel_path: str,
    text: str,
    contract: Optional[Dict[str, Any]] = None,
    gate_step: Optional[str] = None,
) -> List[str]:
    contract = contract or load_contract()
    base_rules = contract.get("artifacts", {}).get(rel_path)
    if not base_rules:
        return [f"unknown artifact in contract: {rel_path}"]

    rules = _merge_step_rules(base_rules, gate_step)
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
                    f"{rel_path}: section ## {title} too short "
                    f"({len(body)} < {threshold} chars); follow template"
                )

    min_chars = rules.get("min_chars")
    if min_chars is not None and len(text.strip()) < int(min_chars):
        errors.append(f"{rel_path}: too short ({len(text.strip())} < {min_chars} chars)")

    # token 匹配对加粗/全角等 Markdown 等价写法宽容：先规范化再判断子串。
    normalized = normalize_for_token(text)
    for token in rules.get("required_tokens", []):
        if token not in normalized:
            errors.append(f"{rel_path}: missing token {token!r}")

    errors.extend(validate_patterns(text, rules.get("patterns", [])))

    forbidden = list(rules.get("forbidden_tokens", []))
    max_hits = rules.get("max_forbidden_token_hits")
    if forbidden:
        # 与 required_tokens 一致，对加粗/全角宽容，避免漏判未替换占位。
        hits = sum(1 for token in forbidden if token in normalized)
        limit = int(max_hits) if max_hits is not None else 0
        if hits > limit:
            errors.append(
                f"{rel_path}: {hits} unreplaced template placeholder(s) "
                f"(max {limit}); copy from .omni-infra/templates and fill"
            )

    placeholder_hits = sum(1 for m in DESIGN_PLACEHOLDER_MARKERS if m in text)
    max_placeholder = rules.get("max_template_placeholders")
    if max_placeholder is not None and placeholder_hits > int(max_placeholder):
        errors.append(
            f"{rel_path}: too many template placeholders ({placeholder_hits}); "
            "use render-design or replace placeholders per design-template.md"
        )

    max_tbd = rules.get("max_tbd_count")
    if max_tbd is not None and text.count("TBD") > int(max_tbd):
        errors.append(f"{rel_path}: too many TBD ({text.count('TBD')} > {max_tbd})")

    min_checks = rules.get("min_checkbox_items")
    if min_checks is not None:
        checks = len(re.findall(r"^- \[[ xX]\]", text, re.MULTILINE))
        if checks < int(min_checks):
            errors.append(f"{rel_path}: checkbox items {checks} < {min_checks}")

    return errors


def validate_gate_step(
    gate_step: str,
    feature_dir: Path,
    contract: Optional[Dict[str, Any]] = None,
) -> List[str]:
    contract = contract or load_contract()
    mapping = contract.get("gate_step_artifacts", {})
    rel_paths = mapping.get(gate_step, [])
    errors: List[str] = []
    for rel in rel_paths:
        path = feature_dir / rel
        if not path.is_file():
            errors.append(f"{rel}: missing")
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        step_for_artifact = gate_step if rel == "design.md" else None
        for msg in validate_artifact(rel, text, contract, gate_step=step_for_artifact):
            errors.append(msg)
    return errors


def render_design_skeleton(
    *,
    feature_name: str,
    branch_name: str,
    spec_link: str = "../spec.md",
    working_dir: Path,
    template_path: Optional[Path] = None,
) -> str:
    infra = working_infra_root(working_dir)
    tpl_path = template_path or (infra / "templates" / "design-template.md")
    if not tpl_path.is_file():
        raise FileNotFoundError(f"design template not found: {tpl_path}")

    text = tpl_path.read_text(encoding="utf-8")
    replacements = {
        "[FEATURE]": feature_name or "未命名功能",
        "[###-feature-name]": branch_name or "000-feature",
        "[DATE]": date.today().isoformat(),
        "[link]": spec_link,
    }
    for key, value in replacements.items():
        text = text.replace(key, value)
    return text


def render_from_infra_template(
    template_name: str,
    *,
    working_dir: Path,
    replacements: Optional[Dict[str, str]] = None,
) -> str:
    infra = working_infra_root(working_dir)
    tpl_path = infra / "templates" / template_name
    if not tpl_path.is_file():
        raise FileNotFoundError(f"template not found: {tpl_path}")
    text = tpl_path.read_text(encoding="utf-8")
    for key, value in (replacements or {}).items():
        text = text.replace(key, value)
    return text


def render_api_contract_skeleton() -> str:
    return """# 接口契约

## 对外接口

### 动作类型:INSERT - API-001 - [接口名称]

**变更原因**: [接口的变更描述]

**所属逻辑实体**: [ENTITY-001] - [逻辑实体名称]

**调用方**: [谁调用/何时调用]

[接口具体内容 — 参见 omni-infra/metamodel/7.interface-template.md]

## 内部接口

### [内部接口名称]

**变更原因**: [接口的变更描述]

**调用方**: [协作方]

[接口具体内容]
"""
