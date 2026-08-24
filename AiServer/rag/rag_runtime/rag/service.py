from __future__ import annotations
from ..retrieval.retriever import Retriever
from ..retrieval.reranker import Reranker
from .answerer import GeminiAnswerer

class RAGService:
    def __init__(self,retriever:Retriever,reranker:Reranker,answerer:GeminiAnswerer):
        self.retriever=retriever; self.reranker=reranker; self.answerer=answerer
    def ask(self, question: str, top_k=12, context_k=6, filters=None):
        candidates=self.retriever.search(question,top_k=top_k,filters=filters)
        ranked=self.reranker.rerank(question,candidates,top_k=context_k)
        return self.answerer.answer(question,ranked)
