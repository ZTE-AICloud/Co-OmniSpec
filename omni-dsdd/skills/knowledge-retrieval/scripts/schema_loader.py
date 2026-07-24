from pathlib import Path
import yaml
from .models import Schema, EntityTypeSpec, AttributeSpec, RetrievalConfig


def _load_attribute(raw: dict, in_frontmatter: bool = False) -> AttributeSpec:
    """加载属性定义。in_frontmatter 表示是否为 frontmatter 扩展字段"""
    name = raw["name"]
    return AttributeSpec(
        name=name,
        key=raw.get("key", name),
        content_type=raw.get("content_type", "prose"),
        required=raw.get("required", False),
        desc=raw.get("desc", ""),
        enum=raw.get("enum"),
    )


def _load_entity_type(path: Path) -> EntityTypeSpec:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))

    # 解析 frontmatter 扩展属性
    frontmatter_attrs = [
        _load_attribute(a, in_frontmatter=True)
        for a in raw.get("frontmatter", [])
    ]

    # 解析 body 属性
    body_attrs = [_load_attribute(a) for a in raw.get("attributes", [])]

    # 解析 retrieval 配置
    retrieval_raw = raw.get("retrieval", {})
    retrieval = RetrievalConfig(
        vector=retrieval_raw.get("vector", []),
        keyword=retrieval_raw.get("keyword", []),
        extract_refs=retrieval_raw.get("extract_refs", []),
    )

    spec = EntityTypeSpec(
        type_id=raw["type_id"],
        version=raw.get("version", 1),
        name=raw.get("name", ""),
        cardinality=raw["cardinality"],
        desc=raw.get("desc", ""),
        id_pattern=raw.get("id_pattern"),
        file_pattern=raw.get("file_pattern"),
        instance_format=raw.get("instance_format", "markdown-with-frontmatter"),
        attributes=body_attrs,
        frontmatter_attributes=frontmatter_attrs,
        retrieval=retrieval,
    )
    _validate_entity_type(spec, path)
    return spec


def _validate_entity_type(spec: EntityTypeSpec, path: Path) -> None:
    if spec.cardinality not in ("single", "multi"):
        raise ValueError(f"{path}: cardinality 只能是 single|multi")

    # body 属性 key 不能重名
    body_keys = [a.key for a in spec.attributes]
    if len(body_keys) != len(set(body_keys)):
        raise ValueError(f"{path}: body 属性 key 重复: {body_keys}")


def load_schema(schema_dir: Path) -> Schema:
    """加载实体类型定义。格式规范见 META-SCHEMA.md"""
    entity_types: dict[str, EntityTypeSpec] = {}
    for p in sorted((schema_dir / "entities").glob("*.yaml")):
        spec = _load_entity_type(p)
        if spec.type_id in entity_types:
            raise ValueError(f"重复的 type_id: {spec.type_id} ({p})")
        entity_types[spec.type_id] = spec

    return Schema(
        version=1,
        entity_types=entity_types,
    )