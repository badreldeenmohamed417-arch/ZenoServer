from __future__ import annotations
import math, re
from abc import ABC, abstractmethod
from ..core.models import SearchResult

class Reranker(ABC):
    @abstractmethod
    def rerank(self, query: str, candidates: list[SearchResult], top_k: int) -> list[SearchResult]: ...

class HybridReranker(Reranker):
    """Deterministic reranker: vector score + lexical coverage + authority + exact phrase bonus."""
    def _tokens(self,text): return set(re.findall(r"[\w\u0600-\u06FF]+", text.lower()))
    def rerank(self, query, candidates, top_k):
        qt=self._tokens(query)
        for c in candidates:
            ct=self._tokens(c.chunk.content)
            lexical=len(qt&ct)/max(1,len(qt))
            authority={"official":1.0,"high":0.8,"medium":0.55,"low":0.35,"unknown":0.2}.get(str(c.chunk.authority),0.2)
            exact=1.0 if query.strip().lower() in c.chunk.content.lower() else 0.0
            c.rerank_score=0.65*c.score+0.25*lexical+0.08*authority+0.02*exact
        return sorted(candidates,key=lambda x:x.rerank_score or -math.inf,reverse=True)[:top_k]
