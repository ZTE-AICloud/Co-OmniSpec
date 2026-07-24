"""DocumentRetriever：baseline 模式的文档枚举/定位检索器。

独立于 vector——直接扫描 raw_knowledge_dir 下受支持的文档文件。
仅列举可被 chunk 向量消费的文档类型（当前仅 markdown），
与构建期向量化范围保持一致：列得出 = 搜得到。
"""
from __future__ import annotations
from pathlib import Path
from typing import Any, Optional

# 与构建期 chunk 向量化范围保持一致；扩展时同步 build 的 detect 过滤规则
SUPPORTED_DOC_EXTS = {".md", ".markdown"}


class DocumentRetriever:
    name = "document"

    def __init__(self, raw_dir: Optional[Path]):
        self.raw_dir = raw_dir

    def list_documents(self) -> list[dict[str, Any]]:
        """递归列举 raw_knowledge_dir 下受支持的文档，返回相对路径与文件名。"""
        if not self.raw_dir or not self.raw_dir.exists():
            return []
        docs: list[dict[str, Any]] = []
        for p in sorted(self.raw_dir.rglob("*")):
            if p.is_file() and p.suffix.lower() in SUPPORTED_DOC_EXTS:
                rel = p.relative_to(self.raw_dir).as_posix()
                docs.append({"source_file": rel, "name": p.stem})
        return docs