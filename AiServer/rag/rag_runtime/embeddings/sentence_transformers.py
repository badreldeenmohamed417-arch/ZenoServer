"""Local SentenceTransformers embedding provider.

This provider is intentionally independent from the Gemini provider used by the
application.  Retrieval evaluation must be reproducible and must not call an
LLM or an external judgement service.
"""
from __future__ import annotations

from .base import EmbeddingProvider
from ..core.exceptions import EmbeddingError


class SentenceTransformerEmbeddingProvider(EmbeddingProvider):
    def __init__(self, model_name: str, batch_size: int = 32):
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:  # pragma: no cover - depends on optional runtime dependency
            raise EmbeddingError(
                "sentence-transformers is required for local retrieval evaluation; "
                "run pip install -r requirements.txt"
            ) from exc
        self.model_name = model_name
        self.batch_size = batch_size
        self.model = SentenceTransformer(model_name)
        dimension_method = getattr(self.model, "get_embedding_dimension", self.model.get_sentence_embedding_dimension)
        self.dimension = dimension_method()

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        vectors = self.model.encode(
            texts, batch_size=self.batch_size, show_progress_bar=False,
            normalize_embeddings=True,
        )
        return vectors.tolist()
