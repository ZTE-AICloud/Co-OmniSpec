from dataclasses import dataclass, field
from typing import Optional, Any


@dataclass
class RetrievalConfig:
    """检索配置，集中在 entity 级别"""
    vector: list[str] = field(default_factory=list)
    keyword: list[str] = field(default_factory=list)
    extract_refs: list[str] = field(default_factory=list)


@dataclass
class AttributeSpec:
    name: str                                   # 中文权威名（Agent/用户优先认）
    key: str                                    # 文档字面键；省略时等于 name
    content_type: str = "prose"
    required: bool = False
    desc: str = ""
    enum: Optional[list[str]] = None


@dataclass
class EntityTypeSpec:
    type_id: str
    cardinality: str                             # "single" | "multi"
    name: str = ""                                 # 中文名称，用于目录查找
    desc: str = ""
    id_pattern: Optional[str] = None            # 保留但不再用于文件匹配
    file_pattern: Optional[str] = None            # 保留但不再用于 glob 匹配
    instance_format: str = "markdown-with-frontmatter"
    attributes: list[AttributeSpec] = field(default_factory=list)
    frontmatter_attributes: list[AttributeSpec] = field(default_factory=list)
    retrieval: RetrievalConfig = field(default_factory=RetrievalConfig)
    version: int = 1

    def attribute_by_name(self, name: str) -> Optional[AttributeSpec]:
        """根据 name 查找属性（优先 body 属性，再 frontmatter 属性）"""
        # 中文名优先 - body 属性
        for a in self.attributes:
            if a.name == name:
                return a
        # 字面键兜底 - body 属性
        for a in self.attributes:
            if a.key == name:
                return a
        # frontmatter 属性
        for a in self.frontmatter_attributes:
            if a.name == name or a.key == name:
                return a
        return None

    def attribute_by_key(self, key: str) -> Optional[AttributeSpec]:
        """根据 key 查找属性（优先 body 属性，再 frontmatter 属性）"""
        for a in self.attributes:
            if a.key == key:
                return a
        for a in self.frontmatter_attributes:
            if a.key == key:
                return a
        return None


@dataclass
class Schema:
    version: int = 1
    entity_types: dict[str, EntityTypeSpec] = field(default_factory=dict)


@dataclass
class InstanceDoc:
    type_id: str
    id: str
    frontmatter: dict[str, Any]
    sections: dict[str, str]                    # 以中文属性名为键
    source_path: str
    content_hash: str
    unknown_sections: dict[str, str] = field(default_factory=dict)
    missing_attributes: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def get_attribute(self, name_or_key: str, spec: EntityTypeSpec) -> Optional[str]:
        """根据属性名或 key 查找属性值（优先 body sections，再 frontmatter）"""
        attr = spec.attribute_by_name(name_or_key)
        if attr is None:
            return None
        # body 属性：从 sections 取（按 name 匹配 H2 标题）
        if attr.name in self.sections:
            return self.sections[attr.name]
        # frontmatter 属性：从 frontmatter 取（按 key 匹配）
        v = self.frontmatter.get(attr.key)
        return None if v is None else str(v)