from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import yaml

from .models import Schema, InstanceDoc
from .schema_loader import load_schema
from .instance_parser import load_instances
from .retrievers.metadata import MetadataRetriever
from .retrievers.section import SectionRetriever
from .retrievers.vector import VectorRetriever, VectorConfig
from .retrievers.fuzzy import FuzzyRetriever
from .retrievers.document import DocumentRetriever


@dataclass
class KBConfig:
    """知识库配置，同时支持 enhance 和 baseline 两种模式。"""
    cache_dir: Path
    retrievers: dict
    # 兼容旧配置的字段（enhance 模式必须）
    schema_dir: Optional[Path] = None
    instances_dir: Optional[Path] = None
    # baseline 专用
    raw_knowledge_dir: Optional[Path] = None
    # 模式标识
    mode: str = "enhance"  # "enhance" | "baseline"


def load_config(config_path: Path) -> KBConfig:
    """
    从 YAML 文件加载配置。

    优先读取 knowledge_model（enhance 语义），
    若不存在则回退到顶层 schema_dir/instances_dir（兼容旧配置）。
    """
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    base = config_path.parent

    km = raw.get("knowledge_model", {})
    cache_dir = (base / raw.get("cache_dir", ".knowledge-cache")).resolve()

    if isinstance(km, dict) and km.get("enabled", True):
        # enhance 模式
        schema_dir = (base / km["schema_dir"]).resolve() if km.get("schema_dir") else None
        instances_dir = (base / km["instances_dir"]).resolve() if km.get("instances_dir") else None
        raw_knowledge_dir = None
        mode = "enhance"
    else:
        # baseline 模式（enabled=False）或旧格式
        mode = "baseline" if isinstance(km, dict) else "enhance"
        schema_dir = (base / raw["schema_dir"]).resolve() if raw.get("schema_dir") else None
        instances_dir = (base / raw["instances_dir"]).resolve() if raw.get("instances_dir") else None
        # baseline: raw_knowledge_dir 在顶层（不在 knowledge_model 里）
        raw_knowledge_dir = (
            (base / raw["raw_knowledge_dir"]).resolve()
            if raw.get("raw_knowledge_dir")
            else None
        )

    return KBConfig(
        schema_dir=schema_dir,
        instances_dir=instances_dir,
        raw_knowledge_dir=raw_knowledge_dir,
        cache_dir=cache_dir,
        retrievers=raw.get("retrievers", {}),
        mode=mode,
    )


class KnowledgeBase:
    """
    知识库主类，支持 enhance / baseline 两种运行模式。

    enhance 模式：需要 schema + instances，正常加载全量检索组件。
    baseline 模式：无需 schema/instances，仅加载 vector（基于 chunk）
                  和可选的 graph。
    """

    def __init__(self, config: KBConfig):
        self.config = config
        self.mode = config.mode

        if config.mode == "baseline":
            # baseline: 不加载 schema/instances
            self.schema: Optional[Schema] = None
            self.instances: list[InstanceDoc] = []
            self.metadata = None
            self.section = None
            self.fuzzy = FuzzyRetriever()
            self.documents = DocumentRetriever(config.raw_knowledge_dir)
        else:
            # enhance: 正常加载全量组件
            self.schema = load_schema(config.schema_dir)
            self.instances = load_instances(self.schema, config.instances_dir)
            self.metadata = MetadataRetriever(self.schema, self.instances)
            self.section = SectionRetriever(self.schema, self.instances)
            self.fuzzy = FuzzyRetriever()
            self.documents = None

        # vector: enhance 传 schema/instances，baseline 传 raw_dir
        self.vector: Optional[VectorRetriever] = None
        v_raw = (config.retrievers or {}).get("vector") or {}
        if v_raw.get("enabled", False):
            vconf = VectorConfig.from_dict(v_raw, mode=config.mode)
            self.vector = VectorRetriever(
                schema=self.schema if config.mode == "enhance" else None,
                instances=self.instances if config.mode == "enhance" else None,
                config=vconf,
                cache_dir=config.cache_dir,
                raw_dir=config.raw_knowledge_dir if config.mode == "baseline" else None,
            )

        # graph: 两种模式均可使用（由 graph 配置决定）
        self.graph = None
        g_raw = (config.retrievers or {}).get("graph") or {}
        if g_raw.get("enabled", False) and g_raw.get("graph_path"):
            gp = Path(g_raw["graph_path"])
            if not gp.is_absolute():
                base_dir = config.schema_dir.parent if config.schema_dir else config.cache_dir.parent
                gp = base_dir / gp
            # from .graph_context import GraphRetriever
            # self.graph = GraphRetriever(gp)
            pass  # graph_context 未启用，暂不实例化

    @classmethod
    def from_config_file(cls, config_path: str | Path) -> "KnowledgeBase":
        return cls(load_config(Path(config_path)))
