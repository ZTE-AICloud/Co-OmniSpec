from typing import Any, Iterable, Optional
from ..models import InstanceDoc, Schema
from .base import Retriever


class MetadataRetriever(Retriever):
    """基于 frontmatter 的精确过滤与查找。"""

    name = "metadata"

    def __init__(self, schema: Schema, instances: list[InstanceDoc]):
        self.schema = schema
        self._by_type: dict[str, list[InstanceDoc]] = {}
        self._by_id: dict[str, InstanceDoc] = {}
        for inst in instances:
            self._by_type.setdefault(inst.type_id, []).append(inst)
            if inst.id:
                self._by_id[inst.id] = inst

    def capabilities(self) -> dict[str, Any]:
        return {"filters": ["eq", "in"], "scope": ["type", "id"]}

    # --- 查询方法 ---

    def get_by_id(self, instance_id: str) -> Optional[InstanceDoc]:
        return self._by_id.get(instance_id)

    def list_by_type(self, type_id: str) -> list[InstanceDoc]:
        return list(self._by_type.get(type_id, []))

    def filter_by_type(
        self,
        type_id: str,
        filters: Optional[dict[str, Any]] = None,
    ) -> list[InstanceDoc]:
        """filters 的 key 支持中文属性名或字面 key；value 支持标量或列表（list=IN 语义）。"""
        items = self.list_by_type(type_id)
        if not filters:
            return items
        spec = self.schema.entity_types.get(type_id)
        if not spec:
            return []

        # 把 filters 的 key 归一化到字面 key（frontmatter 的实际键）
        # frontmatter 属性在 spec.frontmatter_attributes 列表中
        frontmatter_keys = {a.key for a in spec.frontmatter_attributes}
        normalized: dict[str, Any] = {}
        for k, v in filters.items():
            attr = spec.attribute_by_name(k)
            if attr is None or attr.key not in frontmatter_keys:
                # 未知字段：直接尝试字面 key 匹配 frontmatter
                normalized[k] = v
            else:
                normalized[attr.key] = v

        def match(doc: InstanceDoc) -> bool:
            for k, v in normalized.items():
                actual = doc.frontmatter.get(k)
                if isinstance(v, (list, tuple, set)):
                    if actual not in v:
                        return False
                else:
                    if actual != v:
                        return False
            return True

        return [d for d in items if match(d)]

    def all_ids(self) -> Iterable[str]:
        return self._by_id.keys()

    def type_counts(self) -> dict[str, int]:
        return {t: len(v) for t, v in self._by_type.items()}