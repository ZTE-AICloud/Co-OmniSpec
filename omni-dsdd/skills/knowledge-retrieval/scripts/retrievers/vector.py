"""VectorRetriever — 支持 'enhance' 和 'baseline' 两种模式。

enhance：基于 schema 的属性级向量检索。
baseline：对 raw_knowledge_dir 下 Markdown 按 heading/token 窗口切分后建向量索引，无需 schema。

两模式共用同一套 embedding + 缓存 + 余弦检索机制，差异仅在「收集哪些条目」和「返回哪些字段」。
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional
import sys
import numpy as np

from ..embedding import Embedder
from ..models import InstanceDoc, Schema
from .base import Retriever
from ..chunk_splitter import split_markdown, TokenCounter


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

@dataclass
class VectorConfig:
    enabled: bool = True
    model: str = "BAAI/bge-base-zh-v1.5"
    device: str = "cpu"
    batch_size: int = 32
    exclude_content_types: list[str] = field(
        default_factory=lambda: ["code", "enum", "scalar"]
    )
    top_k_default: int = 8
    min_score: float = 0.30
    min_text_length: int = 4
    # baseline 专用（均按 token 计）
    chunk_size: int = 512
    chunk_overlap: int = 64
    min_chunk_len: int = 40
    mode: str = "baseline"  # "enhance" | "baseline"

    @classmethod
    def from_dict(cls, raw: dict, mode: str = "baseline") -> "VectorConfig":
        """解析 retrievers.vector 配置。mode 由上层依据 knowledge_model.enabled 传入。

        约定结构（与 config 设计一致，flat 字段作为回退）：
          retrievers.vector:
            model/device/batch_size/top_k_default/min_score: 通用
            enhance:  {exclude_content_types, min_text_length}
            baseline: {chunk_size, chunk_overlap, min_chunk_len}
        """
        raw = raw or {}
        cfg = cls()
        cfg.mode = mode

        for f in ("enabled", "model", "device", "batch_size",
                  "top_k_default", "min_score"):
            if f in raw:
                setattr(cfg, f, raw[f])

        enh = raw.get("enhance", {}) or {}
        if "exclude_content_types" in enh:
            cfg.exclude_content_types = enh["exclude_content_types"]
        elif "exclude_content_types" in raw:
            cfg.exclude_content_types = raw["exclude_content_types"]
        if "min_text_length" in enh:
            cfg.min_text_length = enh["min_text_length"]
        elif "min_text_length" in raw:
            cfg.min_text_length = raw["min_text_length"]

        base = raw.get("baseline", {}) or {}
        for key in ("chunk_size", "chunk_overlap", "min_chunk_len"):
            if key in base:
                setattr(cfg, key, base[key])
            elif key in raw:
                setattr(cfg, key, raw[key])

        return cfg


# ---------------------------------------------------------------------------
# Index entries（两类条目都带 text/hash/row，供共用 embedding 路径使用）
# ---------------------------------------------------------------------------

@dataclass
class _IndexEntry:
    """enhance：属性级索引单元。"""
    id: str
    type: str
    attribute: str
    content_type: str
    text: str
    hash: str
    row: int
    name: str = ""


@dataclass
class _ChunkEntry:
    """baseline：chunk 窗口索引单元。"""
    source_file: str
    location: str
    breadcrumb: str
    text: str
    hash: str
    row: int


def _text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Retriever
# ---------------------------------------------------------------------------

class VectorRetriever(Retriever):
    name = "vector"

    def __init__(
        self,
        schema: Optional[Schema],
        instances: Optional[list[InstanceDoc]],
        config: VectorConfig,
        cache_dir: Path,
        raw_dir: Optional[Path] = None,
    ):
        self.schema = schema
        self.instances = instances or []
        self.config = config
        self.cache_dir = cache_dir / "vectors"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.raw_dir = Path(raw_dir) if raw_dir else None

        self._matrix_path = self.cache_dir / "matrix.npy"
        self._manifest_path = self.cache_dir / "manifest.json"

        self._embedder: Optional[Embedder] = None
        self._cached_vectors: Optional[np.ndarray] = None
        self._hash_to_row: dict[str, int] = {}
        self._entries: list[Any] = []
        self._built: bool = False
        self._skip_reasons: dict[str, int] = {}
        # 不在 __init__ 构建；首次 search 懒构建，或由 build-vector-index 显式构建。

    # ------------------------------------------------------------------
    def capabilities(self) -> dict[str, Any]:
        base = {
            "search": ["vector"],
            "model": self.config.model,
            "enabled": self.config.enabled,
            "mode": self.config.mode,
        }
        if self.config.mode == "enhance":
            base["scope"] = ["type_ids", "attributes"]
        return base

    def _ensure_embedder(self) -> None:
        if self._embedder is None:
            self._embedder = Embedder(
                self.config.model,
                device=self.config.device,
                batch_size=self.config.batch_size,
            )

    # ------------------------------------------------------------------
    # 收集条目（按模式分叉）
    # ------------------------------------------------------------------
    def _collect_entries(self) -> list[Any]:
        if self.config.mode == "baseline":
            return self._collect_chunk_entries()
        return self._collect_attribute_entries()

    def _collect_attribute_entries(self) -> list[_IndexEntry]:
        entries: list[_IndexEntry] = []
        skip: dict[str, int] = {}
        for doc in self.instances:
            if not self.schema:
                continue
            spec = self.schema.entity_types.get(doc.type_id)
            if not spec:
                continue
            vector_keys = set(spec.retrieval.vector)
            for attr in spec.attributes:
                if attr.key not in vector_keys:
                    continue
                if attr.content_type in self.config.exclude_content_types:
                    skip["excluded_content_type"] = skip.get("excluded_content_type", 0) + 1
                    continue
                val = doc.get_attribute(attr.key, spec)
                if not val:
                    skip["empty"] = skip.get("empty", 0) + 1
                    continue
                text = val.strip()
                if len(text) < self.config.min_text_length:
                    skip["too_short"] = skip.get("too_short", 0) + 1
                    continue
                entries.append(_IndexEntry(
                    id=doc.id,
                    type=doc.type_id,
                    name=doc.frontmatter.get("name", ""),
                    attribute=attr.name,
                    content_type=attr.content_type,
                    text=text,
                    hash=_text_hash(text),
                    row=-1,
                ))
        self._skip_reasons = skip
        return entries

    def _collect_chunk_entries(self) -> list[_ChunkEntry]:
        entries: list[_ChunkEntry] = []
        skip: dict[str, int] = {}
        if not self.raw_dir or not self.raw_dir.is_dir():
            self._skip_reasons = {"no_raw_dir": 1}
            return entries

        # 仅消费 md：代码及其它类型交给 graphify，不做向量
        self._ensure_embedder()
        tokenizer = TokenCounter(self._embedder.tokenizer)

        md_files = [
            p for p in self.raw_dir.rglob("*")
            if p.is_file() and p.suffix.lower() in (".md", ".markdown")
        ]
        for md_path in sorted(md_files):
            try:
                md_text = md_path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                skip["unreadable"] = skip.get("unreadable", 0) + 1
                continue
            rel = str(md_path.relative_to(self.raw_dir))
            for ch in split_markdown(
                md_text,
                source_file=rel,
                chunk_size=self.config.chunk_size,
                chunk_overlap=self.config.chunk_overlap,
                min_chunk_len=self.config.min_chunk_len,
                tokenizer=tokenizer,
            ):
                entries.append(_ChunkEntry(
                    source_file=ch.source_file,
                    location=ch.location,
                    breadcrumb=ch.breadcrumb,
                    text=ch.text,
                    hash=_text_hash(ch.text),
                    row=-1,
                ))
        self._skip_reasons = skip
        return entries

    # ------------------------------------------------------------------
    # 缓存（两模式共用；manifest 记 model+mode，任一不一致即作废）
    # ------------------------------------------------------------------
    def _load_cache(self) -> None:
        if not (self._matrix_path.exists() and self._manifest_path.exists()):
            self._cached_vectors = None
            self._hash_to_row = {}
            return
        manifest = json.loads(self._manifest_path.read_text(encoding="utf-8"))
        if manifest.get("model") != self.config.model or manifest.get("mode") != self.config.mode:
            self._cached_vectors = None
            self._hash_to_row = {}
            return
        try:
            self._cached_vectors = np.load(self._matrix_path)
            self._hash_to_row = {h: i for i, h in enumerate(manifest["hashes"])}
        except Exception:
            self._cached_vectors = None
            self._hash_to_row = {}

    def _save_cache(self) -> None:
        if self._cached_vectors is None or self._cached_vectors.size == 0:
            return
        hashes: list[Optional[str]] = [None] * self._cached_vectors.shape[0]
        for h, r in self._hash_to_row.items():
            hashes[r] = h
        manifest = {
            "model": self.config.model,
            "mode": self.config.mode,
            "dim": int(self._cached_vectors.shape[1]),
            "size": int(self._cached_vectors.shape[0]),
            "hashes": hashes,
        }
        np.save(self._matrix_path, self._cached_vectors)
        self._manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False), encoding="utf-8"
        )

    # ------------------------------------------------------------------
    # 建索引（两模式共用 embedding 路径）
    # ------------------------------------------------------------------
    def build_index(self, force: bool = False) -> dict[str, Any]:
        if force:
            if self._matrix_path.exists():
                self._matrix_path.unlink()
            if self._manifest_path.exists():
                self._manifest_path.unlink()

        self._load_cache()
        entries = self._collect_entries()

        need_hashes: list[str] = []
        seen = set()
        for e in entries:
            if e.hash not in self._hash_to_row and e.hash not in seen:
                need_hashes.append(e.hash)
                seen.add(e.hash)

        encoded_new = 0
        if need_hashes:
            self._ensure_embedder()
            hash_to_text = {e.hash: e.text for e in entries}
            texts = [hash_to_text[h] for h in need_hashes]
            print(f"[vector] need_encode={len(need_hashes)} total_entries={len(entries)}",
                file=sys.stderr, flush=True)
            new_vecs = self._embedder.encode(
                texts, progress_path=str(self.cache_dir / "progress.json"))
            encoded_new = len(need_hashes)
            if self._cached_vectors is None or self._cached_vectors.size == 0:
                self._cached_vectors = new_vecs
                self._hash_to_row = {h: i for i, h in enumerate(need_hashes)}
            else:
                base = self._cached_vectors.shape[0]
                self._cached_vectors = np.vstack([self._cached_vectors, new_vecs])
                for i, h in enumerate(need_hashes):
                    self._hash_to_row[h] = base + i

        for e in entries:
            e.row = self._hash_to_row[e.hash]
        self._entries = entries
        self._built = True
        self._save_cache()

        stats: dict[str, Any] = {
            "mode": self.config.mode,
            "total_entries": len(entries),
            "encoded_new": encoded_new,
            "reused_from_cache": len(entries) - encoded_new,
            "skipped": self._skip_reasons,
            "model": self.config.model,
            "dim": int(self._cached_vectors.shape[1])
                   if self._cached_vectors is not None and self._cached_vectors.size else 0,
        }
        if self.config.mode == "baseline":
            stats["raw_knowledge_dir"] = str(self.raw_dir)
        return stats

    # ------------------------------------------------------------------
    # 查询（两模式共用向量打分，仅 scope 过滤与结果格式化分叉）
    # ------------------------------------------------------------------
    def search(
        self,
        query: str,
        type_ids: Optional[list[str]] = None,
        attributes: Optional[list[str]] = None,
        top_k: Optional[int] = None,
        min_score: Optional[float] = None,
        scope: Optional[str] = None,  # 兼容旧签名，baseline 下无意义
    ) -> list[dict[str, Any]]:
        if not self._built:
            self.build_index(force=False)
        if not self._entries or self._cached_vectors is None:
            return []

        query = query.strip()
        if not query:
            return []

        self._ensure_embedder()
        q_vec = self._embedder.encode([query])[0]

        # scope 过滤：仅 enhance 支持按 type/attribute 收窄；baseline 全量
        if self.config.mode == "enhance" and (type_ids or attributes):
            scope_idx = [
                i for i, e in enumerate(self._entries)
                if (not type_ids or e.type in type_ids)
                and (not attributes or e.attribute in attributes)
            ]
        else:
            scope_idx = list(range(len(self._entries)))

        if not scope_idx:
            return []

        rows = np.array([self._entries[i].row for i in scope_idx], dtype=np.int64)
        sub_matrix = self._cached_vectors[rows]
        scores = sub_matrix @ q_vec  # 已归一化，点积=余弦

        k = top_k if top_k is not None else self.config.top_k_default
        thresh = min_score if min_score is not None else self.config.min_score

        if k >= len(scope_idx):
            order = np.argsort(-scores)
        else:
            part = np.argpartition(-scores, k)[:k]
            order = part[np.argsort(-scores[part])]

        results: list[dict[str, Any]] = []
        for oi in order:
            score = float(scores[oi])
            if score < thresh:
                continue
            entry = self._entries[scope_idx[oi]]
            if self.config.mode == "baseline":
                results.append({
                    "source_file": entry.source_file,
                    "location": entry.location,
                    "breadcrumb": entry.breadcrumb,
                    "score": round(score, 4),
                    "snippet": entry.text[:200] + ("…" if len(entry.text) > 200 else ""),
                })
            else:
                results.append({
                    "id": entry.id,
                    "type": entry.type,
                    "name": entry.name,
                    "attribute": entry.attribute,
                    "score": round(score, 4),
                    "snippet": entry.text[:160] + ("…" if len(entry.text) > 160 else ""),
                })
            if len(results) >= k:
                break
        return results

    # ------------------------------------------------------------------
    def list_searchable_attributes(self) -> list[Any]:
        if self.config.mode == "baseline":
            return []
        if not self.schema:
            return []
        out: list[dict[str, Any]] = []
        for type_id, spec in self.schema.entity_types.items():
            vector_keys = set(spec.retrieval.vector)
            for attr in spec.attributes:
                if attr.key not in vector_keys:
                    continue
                excluded = attr.content_type in self.config.exclude_content_types
                out.append({
                    "type": type_id,
                    "attribute": attr.name,
                    "content_type": attr.content_type,
                    "effective": not excluded,
                    "note": (
                        f"excluded by content_type={attr.content_type}"
                        if excluded else attr.desc
                    ),
                })
        return out