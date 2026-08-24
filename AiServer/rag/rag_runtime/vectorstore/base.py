from __future__ import annotations
from abc import ABC, abstractmethod
from ..core.models import Chunk, SearchResult

class VectorStore(ABC):
    @abstractmethod
    def upsert(self, chunks: list[Chunk], embeddings: list[list[float]]) -> str: ...
    @abstractmethod
    def query(self, embedding: list[float], top_k: int = 10, filters: dict | None = None) -> list[SearchResult]: ...
