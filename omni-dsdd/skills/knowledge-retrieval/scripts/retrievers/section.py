from typing import Any, Optional
from ..models import InstanceDoc, Schema
from .base import Retriever


class SectionRetriever(Retriever):
    """按 Schema 声明的属性定位实例内容；支持 meta/body 统一访问。"""

    name = "section"

    def __init__(self, schema: Schema, instances: list[InstanceDoc]):
        self.schema = schema
        self._by_id: dict[str, InstanceDoc] = {d.id: d for d in instances if d.id}

    def capabilities(self) -> dict[str, Any]:
        return {"select": ["by_instance_and_attribute", "by_instance_all_attributes"]}

    def get_attribute(self, instance_id: str, attribute_name: str) -> Optional[str]:
        doc = self._by_id.get(instance_id)
        if doc is None:
            return None
        spec = self.schema.entity_types[doc.type_id]
        return doc.get_attribute(attribute_name, spec)

    def get_instance_view(
        self,
        instance_id: str,
        attributes: Optional[list[str]] = None,
    ) -> Optional[dict[str, Any]]:
        doc = self._by_id.get(instance_id)
        if doc is None:
            return None
        spec = self.schema.entity_types[doc.type_id]
        selected = attributes or [a.name for a in spec.attributes]
        out: dict[str, Any] = {
            "type": doc.type_id,
            "id": doc.id,
            "source_path": doc.source_path,
            "attributes": {},
        }
        for name in selected:
            attr = spec.attribute_by_name(name)
            if attr is None:
                out["attributes"][name] = None
                continue
            out["attributes"][attr.name] = doc.get_attribute(attr.name, spec)
        return out

    def keyword_search(
        self,
        keyword: str,
        type_ids: Optional[list[str]] = None,
        attributes: Optional[list[str]] = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """朴素子串匹配（MVP，不做分词/BM25）。"""
        kw = keyword.strip()
        if not kw:
            return []
        hits: list[dict[str, Any]] = []
        for doc in self._by_id.values():
            if type_ids and doc.type_id not in type_ids:
                continue
            spec = self.schema.entity_types[doc.type_id]
            attr_names = attributes or [a.name for a in spec.attributes if a.indexable]
            for name in attr_names:
                content = doc.get_attribute(name, spec)
                if content and kw in content:
                    hits.append(
                        {
                            "id": doc.id,
                            "type": doc.type_id,
                            "attribute": name,
                            "snippet": _snippet(content, kw),
                        }
                    )
                    if len(hits) >= limit:
                        return hits
        return hits


def _snippet(text: str, kw: str, radius: int = 40) -> str:
    idx = text.find(kw)
    if idx < 0:
        return text[: radius * 2]
    start = max(0, idx - radius)
    end = min(len(text), idx + len(kw) + radius)
    prefix = "…" if start > 0 else ""
    suffix = "…" if end < len(text) else ""
    return f"{prefix}{text[start:end]}{suffix}"