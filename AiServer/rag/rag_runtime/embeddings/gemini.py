from __future__ import annotations
import logging
import time
from ..core.exceptions import EmbeddingError
from .base import EmbeddingProvider

log = logging.getLogger(__name__)

class GeminiEmbeddingProvider(EmbeddingProvider):
    def __init__(self, api_key: str, model: str = "gemini-embedding-001", dimension: int = 768, max_retries: int = 4):
        try:
            from google import genai
        except ImportError as exc:
            raise EmbeddingError("google-genai is not installed; run pip install -r requirements.txt") from exc
        self.client = genai.Client(api_key=api_key)
        self.model = model; self.dimension = dimension; self.max_retries = max_retries

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts: return []
        last_exc=None
        for attempt in range(1,self.max_retries+1):
            try:
                response = self.client.models.embed_content(
                    model=self.model,
                    contents=texts,
                    config={"output_dimensionality": self.dimension},
                )
                embeddings = getattr(response, "embeddings", None) or []
                vectors=[]
                for e in embeddings:
                    values = list(getattr(e, "values", []) or [])
                    if len(values) != self.dimension:
                        raise EmbeddingError(f"Gemini returned dimension {len(values)}, expected {self.dimension}")
                    vectors.append([float(x) for x in values])
                if len(vectors) != len(texts):
                    raise EmbeddingError(f"Gemini returned {len(vectors)} embeddings for {len(texts)} texts")
                return vectors
            except EmbeddingError as exc:
                last_exc=exc
            except Exception as exc:
                last_exc=EmbeddingError(f"Gemini embedding failed: {exc}")
            if attempt < self.max_retries:
                is_rate_limit = "429" in str(last_exc) or "RESOURCE_EXHAUSTED" in str(last_exc)
                delay = (10 * attempt) if is_rate_limit else min(2**(attempt-1), 12)
                log.warning("Embedding retry %d/%d after error (delay=%ds): %s", attempt, self.max_retries, delay, last_exc)
                time.sleep(delay)
        raise last_exc or EmbeddingError("Gemini embedding failed")
