"""FuzzyRetriever：基于名称的模糊字符串匹配检索。
权重：
  - 0.5  substring match    (查询词完整包含在名称中)
  - 0.3  token Jaccard     (分词后交集/并集)
  - 0.2  sequence ratio    (difflib.SequenceMatcher 全局相似度)
"""
from __future__ import annotations
import difflib
import re
from typing import TYPE_CHECKING, Any, Optional

from .base import Retriever

if TYPE_CHECKING:
    from ..knowledge_base import KnowledgeBase


def _tokenize(text: str) -> set[str]:
    """中英文混合分词：英文按单词切分，中文按连续字符组切分后过滤单字。"""
    tokens: set[str] = set()
    # 英文 token
    for w in re.findall(r"[a-zA-Z0-9_]+", text.lower()):
        if len(w) >= 2:
            tokens.add(w)
    # 中文 token（每两个连续汉字为一词，避免单字噪音）
    for chunk in re.findall(r"[\u4e00-\u9fff]+", text):
        for i in range(0, len(chunk) - 1, 2):
            tokens.add(chunk[i : i + 2])
    return tokens


def _score(query: str, name: str) -> float:
    if not query.strip():
        return 0.0
    q_lower = query.lower()
    n_lower = name.lower()

    # 1. substring（含去除空格后的匹配，覆盖 "IPSec VPN配置" 包含 "VPN" 的情况）
    raw_substring = 1.0 if q_lower in n_lower else 0.0
    no_space_substring = 1.0 if q_lower.replace(" ", "") in n_lower.replace(" ", "") else 0.0
    substring = max(raw_substring, no_space_substring)

    # 2. token Jaccard
    q_tokens = _tokenize(query)
    n_tokens = _tokenize(name)
    if q_tokens and n_tokens:
        jaccard = len(q_tokens & n_tokens) / len(q_tokens | n_tokens)
    else:
        jaccard = 0.0

    # 3. sequence ratio
    seq = difflib.SequenceMatcher(None, q_lower, n_lower).ratio()

    return 0.5 * substring + 0.3 * jaccard + 0.2 * seq


class FuzzyRetriever(Retriever):
    name = "fuzzy"

    def capabilities(self) -> dict[str, Any]:
        return {"search": ["fuzzy"], "scope": ["type_ids"]}

    def search(
        self,
        kb: "KnowledgeBase",
        query: str,
        type_ids: Optional[list[str]] = None,
        top_k: int = 10,
    ) -> list[dict[str, Any]]:
        results: list[tuple[float, dict[str, Any]]] = []

        for doc in kb.instances:
            if type_ids and doc.type_id not in type_ids:
                continue

            # 直接从 frontmatter 获取 id 和 name
            inst_id = doc.frontmatter.get("id", "")
            name = doc.frontmatter.get("name", "")

            if not name and not inst_id:
                continue

            # 合并 id 和 name 进行匹配
            match_text = f"{inst_id} {name}".strip()

            score = _score(query, match_text)
            if score == 0.0:
                continue

            results.append(
                (
                    score,
                    {
                        "id": doc.id,
                        "type": doc.type_id,
                        "name": name or inst_id,  # 优先用 name
                        "score": round(score, 4),
                    },
                )
            )

        # 降序
        results.sort(key=lambda x: x[0], reverse=True)
        return [r[1] for r in results[:top_k]]
    
    def search_files(
        self,
        documents: list[dict[str, Any]],
        query: str,
        top_k: int = 10,
    ) -> list[dict[str, Any]]:
        """baseline：对文档（文件名 + 相对路径）做模糊匹配，复用 _score 内核。"""
        results: list[tuple[float, dict[str, Any]]] = []
        for d in documents:
            match_text = f'{d["source_file"]} {d["name"]}'.strip()
            score = _score(query, match_text)
            if score == 0.0:
                continue
            results.append(
                (
                    score,
                    {
                        "source_file": d["source_file"],
                        "name": d["name"],
                        "score": round(score, 4),
                    },
                )
            )
        results.sort(key=lambda x: x[0], reverse=True)
        return [r[1] for r in results[:top_k]]