from __future__ import annotations
from ..embeddings.base import EmbeddingProvider
from ..vectorstore.base import VectorStore
from ..core.models import Question

class QuestionSimilarityEngine:
    def __init__(self,embedding_provider:EmbeddingProvider,store:VectorStore): self.embeddings=embedding_provider; self.store=store
    def similar(self,question:Question,top_k:int=10,filters:dict|None=None):
        # Prefix improves vector-space consistency without changing the stored question text.
        vec=self.embeddings.embed_one("QUESTION: "+question.text)
        return self.store.query(vec,top_k=top_k,filters=filters)
