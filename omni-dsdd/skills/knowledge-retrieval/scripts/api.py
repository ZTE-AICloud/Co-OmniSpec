"""L3 检索原语：9个基础 + 图谱类2个。"""
from typing import Any, Optional
from .knowledge_base import KnowledgeBase
from .models import InstanceDoc
from .graph_context import GraphRetriever  # noqa: F401


def _find_instance_by_id_or_name(
    kb: KnowledgeBase, instance_id_or_name: str
) -> tuple[Optional[InstanceDoc], Optional[str]]:
    """按 id 或 name 查找实例。

    Returns:
        (doc, warning): doc为找到的实例，warning为重复警告（如有）
    """
    # 1. 先按 id 查找
    doc = kb.section._by_id.get(instance_id_or_name)
    if doc is not None:
        return doc, None

    # 2. 按 name 查找（需要遍历，构建 name->docs 映射并检测重复）
    name_to_docs: dict[str, list[InstanceDoc]] = {}
    for d in kb.instances:
        n = d.frontmatter.get("name")
        if n:
            name_to_docs.setdefault(n, []).append(d)

    matched = name_to_docs.get(instance_id_or_name, [])
    if not matched:
        return None, None

    if len(matched) > 1:
        ids = [d.id for d in matched]
        return matched[0], f"存在 {len(matched)} 个同名实例: {instance_id_or_name}，id分别为: {ids}"

    return matched[0], None


def _instance_card(kb: KnowledgeBase, doc: InstanceDoc) -> dict[str, Any]:
    fm = doc.frontmatter
    card = {
        "type": doc.type_id,
        "id": fm.get("id", doc.id),
        "name": fm.get("name", ""),
    }
    brief = fm.get("brief")
    if brief:
        card["brief"] = brief
    return card


# ---------- 1 ----------
def list_entity_types(kb: KnowledgeBase) -> list[dict[str, Any]]:
    counts = kb.metadata.type_counts()
    return [
        {
            "type": t,
            "name": s.name,
            "cardinality": s.cardinality,
            "desc": s.desc,
            "count": counts.get(t, 0),
        }
        for t, s in kb.schema.entity_types.items()
    ]


# ---------- 2 ----------
def describe_entity_type(kb: KnowledgeBase, type_id_or_name: str) -> dict[str, Any]:
    # 支持按 type_id（英文）或 name（中文）查找
    spec = kb.schema.entity_types.get(type_id_or_name)
    if spec is None:
        # 尝试按 name（中文）查找
        for s in kb.schema.entity_types.values():
            if s.name == type_id_or_name:
                spec = s
                break
    if spec is None:
        return {"error": f"unknown entity type: {type_id_or_name}"}

    return {
        "type": spec.type_id,
        "name": spec.name,
        "version": spec.version,
        "cardinality": spec.cardinality,
        "desc": spec.desc,
        "retrieval": {
            "vector": spec.retrieval.vector,
            "keyword": spec.retrieval.keyword,
        },
        "frontmatter_attributes": [
            {"name": a.name, "key": a.key, "content_type": a.content_type,
             "required": a.required, "enum": a.enum, "desc": a.desc}
            for a in spec.frontmatter_attributes
        ],
        "attributes": [
            {"name": a.name, "key": a.key, "content_type": a.content_type,
             "required": a.required, "desc": a.desc}
            for a in spec.attributes
        ],
    }


# ---------- 3 ----------
def list_instances(
    kb: KnowledgeBase,
    type_id: str,
    filter: Optional[dict[str, Any]] = None,
) -> list[dict[str, Any]]:
    if type_id not in kb.schema.entity_types:
        return []
    docs = kb.metadata.filter_by_type(type_id, filter)
    return [_instance_card(kb, d) for d in docs]


# ---------- 4 ----------
def get_instance(
    kb: KnowledgeBase,
    instance_id_or_name: str,
    attributes: Optional[list[str]] = None,
) -> dict[str, Any]:
    # 先按 id 查找，再按 name 查找，支持重复检测
    doc, warning = _find_instance_by_id_or_name(kb, instance_id_or_name)
    if doc is None:
        return {"error": f"instance not found: {instance_id_or_name}"}

    view = kb.section.get_instance_view(doc.id, attributes)
    if view is None:
        return {"error": f"instance not found: {instance_id_or_name}"}

    if warning:
        view["warning"] = warning
    return view


# ---------- 5 ----------
def get_attribute(
    kb: KnowledgeBase,
    instance_id_or_name: str,
    attribute_name: str,
) -> dict[str, Any]:
    # 先按 id 查找，再按 name 查找，支持重复检测
    doc, warning = _find_instance_by_id_or_name(kb, instance_id_or_name)
    if doc is None:
        return {"error": f"instance not found: {instance_id_or_name}"}

    val = kb.section.get_attribute(doc.id, attribute_name)
    result = {
        "id": doc.id,
        "type": doc.type_id,
        "name": doc.frontmatter.get("name", ""),
        "attribute": attribute_name,
        "value": val,
    }
    if val is None:
        result["warning"] = "属性未声明或值为空"
    if warning:
        result["warning"] = (result.get("warning") or "") + f" {warning}" if result.get("warning") else warning
    return result


def _normalize_type_ids(kb: KnowledgeBase, type_ids: Optional[list[str]]) -> Optional[list[str]]:
    """将中文实体名称转换为英文 type_id。"""
    if not type_ids:
        return None
    result = []
    for t in type_ids:
        if t in kb.schema.entity_types:
            result.append(t)
        else:
            # 尝试按 name（中文）查找
            for spec in kb.schema.entity_types.values():
                if spec.name == t:
                    result.append(spec.type_id)
                    break
            else:
                result.append(t)  # 找不到保持原样
    return result


# ---------- 7 ----------
def vector_search(
    kb: KnowledgeBase,
    query: str,
    type_ids: Optional[list[str]] = None,
    attributes: Optional[list[str]] = None,
    top_k: Optional[int] = None,
    min_score: Optional[float] = None,
) -> dict[str, Any]:
    if kb.vector is None:
        return {
            "error": "vector retriever is disabled; 请在 knowledge.config.yaml 中开启 retrievers.vector.enabled"
        }
    # baseline 无 schema，type_ids/attributes 不适用，绕开 normalize 防止访问 kb.schema 崩溃
    norm_type_ids = None if kb.mode == "baseline" else _normalize_type_ids(kb, type_ids)
    hits = kb.vector.search(
        query=query,
        type_ids=norm_type_ids,
        attributes=None if kb.mode == "baseline" else attributes,
        top_k=top_k,
        min_score=min_score,
    )
    return {
        "query": query,
        "mode": kb.vector.config.mode,
        "scope": {"type_ids": type_ids, "attributes": attributes},
        "count": len(hits),
        "hits": hits,
    }


# ---------- 8 ----------
def list_searchable_attributes(kb: KnowledgeBase) -> dict[str, Any]:
    """告诉 Agent：当前 KB 有哪些属性可向量检索（effective=true 的才真正生效）。"""
    if kb.vector is None:
        return {"enabled": False, "items": []}
    return {"enabled": True, "items": kb.vector.list_searchable_attributes()}


# ---------- 9 ----------
def fuzzy_search(
    kb: KnowledgeBase,
    query: str,
    type_ids: Optional[list[str]] = None,
    top_k: int = 10,
) -> dict[str, Any]:
    if not query.strip():
        return {"query": query, "mode": kb.mode, "count": 0, "hits": []}

    if kb.mode == "baseline":
        # 模糊匹配文件名 / 相对路径，数据源来自 DocumentRetriever（与 vector 独立）
        documents = kb.documents.list_documents() if kb.documents else []
        hits = kb.fuzzy.search_files(documents, query, top_k)
        return {"query": query, "mode": "baseline", "count": len(hits), "hits": hits}

    # enhance：模糊匹配实例名（现状逻辑）
    norm_type_ids = _normalize_type_ids(kb, type_ids)
    hits = kb.fuzzy.search(kb, query, norm_type_ids, top_k)
    return {"query": query, "mode": "enhance", "count": len(hits), "hits": hits}

# ---------- 10 ----------
def list_documents(kb: KnowledgeBase) -> dict[str, Any]:
    """baseline：枚举可被检索消费的文档（与 vector 独立，扫描 raw_knowledge_dir）。
    对等 enhance 的 list-instances，用于阶段4兜底遍历与精确定位前的全量浏览。"""
    if kb.mode != "baseline":
        return {
            "error": "unavailable_in_enhance_mode",
            "message": "list-documents 仅在 baseline 模式可用；enhance 模式请用 list-instances。",
        }
    docs = kb.documents.list_documents() if kb.documents else []
    return {"mode": "baseline", "count": len(docs), "documents": docs}