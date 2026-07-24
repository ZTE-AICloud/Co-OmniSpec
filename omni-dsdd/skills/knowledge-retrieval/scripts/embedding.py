"""嵌入模型的极简封装：懒加载、批量 encode、L2 归一化。
MVP 只依赖 sentence-transformers；后续想换成 OpenAI/Ollama 只需实现同样的 encode 接口。
"""
from __future__ import annotations
from typing import Optional
import numpy as np
import sys, json, time
from pathlib import Path


class Embedder:
    def __init__(self, model_name: str, device: str = "cpu", batch_size: int = 32):
        self.model_name = model_name
        self.device = device
        self.batch_size = batch_size
        self._model = None  # 懒加载

    def _ensure_loaded(self):
        if self._model is not None:
            return
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as e:
            raise RuntimeError(
                "vector retriever 需要 sentence-transformers，请先 `pip install sentence-transformers`"
            ) from e
        self._model = SentenceTransformer(self.model_name, device=self.device)

    @property
    def dim(self) -> int:
        self._ensure_loaded()
        return int(self._model.get_sentence_embedding_dimension())

    @property
    def tokenizer(self):
        """暴露底层 HF tokenizer，供 baseline 按真实 token 切分使用。"""
        self._ensure_loaded()
        return self._model.tokenizer

    def encode(self, texts, progress_path: str | None = None):
        if not texts:
            self._ensure_loaded()
            return np.zeros((0, self.dim), dtype=np.float32)
        self._ensure_loaded()

        n = len(texts)
        out = []
        for i in range(0, n, self.batch_size):
            batch = texts[i:i + self.batch_size]
            vecs = self._model.encode(
                batch, batch_size=self.batch_size,
                convert_to_numpy=True, normalize_embeddings=True,
                show_progress_bar=False,
            ).astype(np.float32)
            out.append(vecs)
            done = min(i + self.batch_size, n)
            print(f"[vector] encoded {done}/{n}", file=sys.stderr, flush=True)
            if progress_path:
                Path(progress_path).write_text(json.dumps(
                    {"done": done, "total": n, "ts": time.time()}), encoding="utf-8")
        return np.vstack(out)