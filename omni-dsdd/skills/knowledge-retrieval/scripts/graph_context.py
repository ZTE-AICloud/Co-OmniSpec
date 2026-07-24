"""graphify 图上下文召回适配器。

将 graphify 预构建的 graph.json 接入本检索 Skill，作为"图上下文召回"原语。
仅负责召回关联子图上下文，不负责生成答案，不修改任何数据。
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Optional


class GraphRetriever:
    def __init__(self, graph_path: str | Path):
        self.graph_path = Path(graph_path).resolve()
        self._G = None
        self._vocab: Optional[list[str]] = None

    def _load_graph(self):
        if self._G is not None:
            return self._G
        if not self.graph_path.exists():
            raise FileNotFoundError(
                f"graph.json 未找到: {self.graph_path}；"
                f"请先用 graphify 构建（/graphify <docs_dir>）并在 config 中配置 graph_path"
            )
        from networkx.readwrite import json_graph

        raw = json.loads(self.graph_path.read_text(encoding="utf-8"))
        # graphify 导出的是 {nodes, edges}; networkx 期望 links
        if "links" not in raw and "edges" in raw:
            raw = dict(raw, links=raw["edges"])
        try:
            G = json_graph.node_link_graph(raw, edges="links")
        except TypeError:  # 兼容旧版 networkx 签名
            G = json_graph.node_link_graph(raw)
        self._G = G
        return G

    def context(
        self,
        query: str,
        *,
        mode: str = "bfs",
        depth: int = 2,
        token_budget: int = 2000,
        context_filters: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        G = self._load_graph()
        # 与 graphify 官方 CLI 同款入口，稳定性等同 `graphify query`
        from graphify.serve import _query_graph_text

        text = _query_graph_text(
            G,
            query,
            mode=mode,
            depth=depth,
            token_budget=token_budget,
            context_filters=context_filters or None,
        )

        return {
            "query": query,
            "mode": mode,
            "depth": depth,
            "budget": token_budget,
            "context_filters": context_filters or [],
            "seeds": self._extract_seeds(G, query),
            "context": text,
        }

    def _extract_seeds(self, G, query: str) -> list[dict[str, Any]]:
        """尽力而为地抽出种子节点，附带 source_file/label，便于回连到本 KB 实例。

        依赖 graphify 内部函数；若其内部结构变化则静默降级为空列表，
        不影响 context 文本的返回（MVP 容错策略）。
        """
        try:
            from graphify.serve import _query_terms, _score_nodes, _pick_seeds

            terms = _query_terms(query)
            scored = _score_nodes(G, terms)
            seed_ids = _pick_seeds(scored)
            seeds = []
            for nid in seed_ids:
                d = G.nodes[nid]
                seeds.append(
                    {
                        "node_id": nid,
                        "label": d.get("label", nid),
                        "source_file": d.get("source_file", ""),
                    }
                )
            return seeds
        except Exception:
            return []

    def vocab(self) -> list[str]:
        """导出图节点 label 的 token 词表，供 Claude 做受约束的查询扩展。

        中英文混合处理：含中文的 label 用 graphify 的 jieba 分词（与 query
        端切词同一套，保证词空间一致）；英文用正则 + 驼峰拆分。
        """
        if self._vocab is not None:
            return self._vocab
        G = self._load_graph()
        try:
            from graphify.serve import _has_chinese, _segment_chinese
        except Exception:  # graphify 内部结构变化时降级
            _segment_chinese = None

            def _has_chinese(s: str) -> bool:
                return any("\u4e00" <= c <= "\u9fff" for c in s)

        vocab: set[str] = set()
        for _, d in G.nodes(data=True):
            label = d.get("label", "") or ""
            if _has_chinese(label) and _segment_chinese is not None:
                for seg in _segment_chinese(label.lower().strip()):
                    seg = seg.strip()
                    if 2 <= len(seg) <= 30:  # 中文：>=2 字，滤掉单字噪声
                        vocab.add(seg)
            else:
                for c in re.findall(r"[^\W\d_]+", label, re.UNICODE):
                    parts = (
                        re.findall(
                            r"[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+", c
                        )
                        or [c]
                    )
                    for p in parts:
                        t = p.lower()
                        if 3 <= len(t) <= 30:  # 英文：3-30 字
                            vocab.add(t)
        self._vocab = sorted(vocab)
        return self._vocab