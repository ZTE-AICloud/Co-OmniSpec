from abc import ABC, abstractmethod
from typing import Any


class Retriever(ABC):
    """所有检索器的统一接口。MVP 只需 init/capabilities/query_* 的语义，
    refresh 暂时以重建形式实现（在 KnowledgeBase 层重新构造即可）。"""

    name: str = "base"

    @abstractmethod
    def capabilities(self) -> dict[str, Any]: ...

    # 预留；MVP 先不实现增量刷新
    def refresh(self, *_args, **_kwargs) -> None:
        return None