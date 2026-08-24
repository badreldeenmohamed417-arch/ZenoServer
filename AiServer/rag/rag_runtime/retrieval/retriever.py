from __future__ import annotations
from ..core.models import SearchResult
from ..embeddings.base import EmbeddingProvider
from ..vectorstore.base import VectorStore

class Retriever:
    def __init__(self, embeddings: EmbeddingProvider, store: VectorStore):
        self.embeddings=embeddings; self.store=store
    def search(self, query: str, top_k: int=12, filters: dict|None=None) -> list[SearchResult]:
        q=query.strip()
        if not q: return []
        normalized=" ".join(q.split())
        vector=self.embeddings.embed_one(normalized)
        return self.store.query(vector,top_k=top_k,filters=filters)
