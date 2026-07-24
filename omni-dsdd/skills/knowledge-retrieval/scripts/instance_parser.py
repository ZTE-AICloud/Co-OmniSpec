import hashlib
import re
from pathlib import Path
from typing import Optional

import yaml

from .models import EntityTypeSpec, InstanceDoc, Schema

FRONTMATTER_RE = re.compile(r"^---\r?\n(.*?)\r?\n---\r?\n?(.*)$", re.DOTALL)


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    fm = yaml.safe_load(m.group(1)) or {}
    if not isinstance(fm, dict):
        fm = {}
    return fm, m.group(2)


def _normalize_heading(h: str, strip_suffixes: list[str]) -> str:
    h = h.strip()
    changed = True
    while changed:
        changed = False
        for s in strip_suffixes:
            if h.endswith(s):
                h = h[: -len(s)].strip()
                changed = True
    return h


def _split_h2_sections(
    body: str,
    allow_h1: bool,
    strip_suffixes: list[str],
) -> tuple[dict[str, str], str]:
    """按 H2 切段。返回 (sections, preamble_text)。
    sections 的键已规范化（去掉"（可选）"等尾缀）。
    preamble_text 是 H1（若有且允许）之后、第一个 H2 之前的文本，作为"孤儿段"返回以便告警。
    """
    lines = body.splitlines()
    i = 0
    # 跳过开头空行
    while i < len(lines) and lines[i].strip() == "":
        i += 1
    # 允许并跳过 H1 标题
    if (
        allow_h1
        and i < len(lines)
        and lines[i].startswith("# ")
        and not lines[i].startswith("## ")
    ):
        i += 1

    sections: dict[str, str] = {}
    preamble: list[str] = []
    current_heading: Optional[str] = None
    current_lines: list[str] = []

    def flush():
        nonlocal current_heading, current_lines
        if current_heading is not None:
            sections[current_heading] = "\n".join(current_lines).rstrip()
        current_heading = None
        current_lines = []

    for line in lines[i:]:
        # 只识别严格 H2（"## "），H3+ 保留在当前段内
        if line.startswith("## ") and not line.startswith("### "):
            if current_heading is None:
                preamble = current_lines.copy()
            else:
                flush()
            raw_heading = line[3:].strip()
            current_heading = _normalize_heading(raw_heading, strip_suffixes)
            current_lines = []
        else:
            current_lines.append(line)

    if current_heading is not None:
        flush()
    else:
        preamble = current_lines.copy()

    return sections, "\n".join(preamble).strip()


def _infer_instance_id(
    spec: EntityTypeSpec, frontmatter: dict, file_path: Path
) -> tuple[str, list[str]]:
    warnings: list[str] = []
    if spec.cardinality == "single":
        return spec.type_id, warnings

    # 直接从 frontmatter["id"] 获取
    inst_id = frontmatter.get("id")
    if not inst_id:
        warnings.append("frontmatter 缺少 id")
        return "", warnings

    inst_id = str(inst_id)
    if spec.id_pattern and not re.match(spec.id_pattern, inst_id):
        warnings.append(f"ID {inst_id} 不匹配 id_pattern={spec.id_pattern}")
    # 文件名与 ID 一致性
    if not file_path.stem.startswith(inst_id):
        warnings.append(f"文件名 {file_path.name} 与 ID {inst_id} 不一致")
    return inst_id, warnings


def parse_instance_file(
    file_path: Path, spec: EntityTypeSpec, schema: Schema
) -> InstanceDoc:
    raw_bytes = file_path.read_bytes()
    content_hash = hashlib.sha256(raw_bytes).hexdigest()
    text = raw_bytes.decode("utf-8")

    frontmatter, body = _parse_frontmatter(text)
    raw_sections, preamble = _split_h2_sections(
        body, True, []  # allow_leading_h1_title=True, strip_suffixes=[]
    )

    inst_id, warnings = _infer_instance_id(spec, frontmatter, file_path)

    # 映射 body 段到声明的属性
    body_attr_names = {a.name for a in spec.attributes}
    frontmatter_attr_keys = {a.key for a in spec.frontmatter_attributes}

    sections: dict[str, str] = {}
    missing: list[str] = []
    for attr in spec.attributes:
        if attr.name in raw_sections:
            sections[attr.name] = raw_sections[attr.name]
        elif attr.required:
            missing.append(attr.name)

    unknown = {k: v for k, v in raw_sections.items() if k not in body_attr_names}

    # frontmatter 属性必填校验（从 frontmatter_attributes 获取）
    for attr in spec.frontmatter_attributes:
        if attr.required and attr.key not in frontmatter:
            missing.append(attr.name)
        # 枚举校验
        if (
            attr.enum
            and attr.key in frontmatter
            and frontmatter[attr.key] not in attr.enum
        ):
            warnings.append(
                f"{attr.name} 取值 {frontmatter[attr.key]!r} 不在枚举 {attr.enum}"
            )

    if preamble:
        warnings.append("存在未归属任意 H2 属性的孤儿段落（preamble），已忽略")

    return InstanceDoc(
        type_id=spec.type_id,
        id=inst_id,
        frontmatter=frontmatter,
        sections=sections,
        source_path=str(file_path),
        content_hash=content_hash,
        unknown_sections=unknown,
        missing_attributes=missing,
        warnings=warnings,
    )


def _find_type_dir(instances_dir: Path, spec: EntityTypeSpec) -> Optional[Path]:
    """递归按目录名定位该类型实例目录（中文 name 优先，回退英文 type_id）。"""
    for target in (spec.name, spec.type_id):  # 中文名优先，英文回退
        if not target:
            continue
        for d in instances_dir.rglob("*"):
            if d.is_dir() and d.name == target:
                return d
    return None


def load_instances(schema: Schema, instances_dir: Path) -> list[InstanceDoc]:
    """根据目录递归加载实例。

    加载规则：
    1. 对每个 entity type，递归在 instances_dir 下按目录名定位（中文 name 优先，回退英文 type_id）
    2. 目录内递归 glob 匹配 file_pattern 的 .md 文件加载为实例
    3. cardinality="single" 类型使用 spec.file_path 直接定位
    4. 检查文件名是否与实例 id/name 一致，不一致报警告
    5. 无可对齐属性的 md 文件不加载并报警告
    """
    results: list[InstanceDoc] = []
    warnings: list[str] = []

    if schema is None:
        return results

    for spec in schema.entity_types.values():
        if spec.cardinality == "single":
            # 单实体直接用 file_path 定位
            fp = instances_dir / spec.file_path
            if fp.exists() and fp.is_file():
                try:
                    doc = parse_instance_file(fp, spec, schema)
                    results.append(doc)
                except Exception as e:
                    warnings.append(f"加载失败 {fp.name}: {e}")
            continue

        # 递归查找该类型对应的实例目录
        type_dir = _find_type_dir(instances_dir, spec)
        if type_dir is None:
            warnings.append(f"未找到类型 {spec.type_id}（{spec.name}）的实例目录")
            continue

        # 目录下递归 glob 匹配 file_pattern 的 .md 文件
        for md_file in sorted(type_dir.rglob(spec.file_pattern)):
            if not md_file.is_file():
                continue
            try:
                doc = parse_instance_file(md_file, spec, schema)

                # 检查文件名是否与实例 id/name 一致
                file_stem = md_file.stem
                name_in_fm = doc.frontmatter.get("name", "")
                if (
                    doc.id
                    and not file_stem.startswith(doc.id)
                    and not (name_in_fm and file_stem.startswith(name_in_fm))
                ):
                    doc.warnings.append(f"文件名 {md_file.name} 与实例 id/name 不一致")

                # 检查是否有任何属性可对齐（frontmatter 或 sections）
                has_frontmatter = bool(doc.frontmatter)
                has_sections = bool(doc.sections)
                if not has_frontmatter and not has_sections:
                    warnings.append(f"跳过无属性实例 {md_file.name}（无 frontmatter 或 sections）")
                    continue

                results.append(doc)
            except Exception as e:
                warnings.append(f"加载失败 {md_file.name}: {e}")

    if warnings:
        print(f"[load_instances] 警告: {', '.join(warnings[:10])}")
    return results