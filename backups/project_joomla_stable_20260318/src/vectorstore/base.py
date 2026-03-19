from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol


@dataclass(frozen=True)
class SearchResult:
    text: str
    score: float
    metadata: Dict[str, Any]


class VectorStore(Protocol):
    """
    VectorStore interface (adapter) so we can swap Chroma/Qdrant/pgvector later.
    """

    def upsert(
        self,
        ids: List[str],
        texts: List[str],
        metadatas: List[Dict[str, Any]],
    ) -> None:
        ...

    def query(
        self,
        query_text: str,
        top_k: int = 3,
        where: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        ...

    def delete(self, ids: List[str]) -> None:
        ...
    
    def delete_by_url(self, url: str) -> None:
        ...


    def persist(self) -> None:
        ...

    def health_check(self) -> bool:
        ...
