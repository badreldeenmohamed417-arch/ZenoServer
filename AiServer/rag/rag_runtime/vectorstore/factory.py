from __future__ import annotations

from ..core.config import settings
from .base import VectorStore
from .sqlite import SQLiteVectorStore


def create_vector_store() -> VectorStore:
    return SQLiteVectorStore(
        path=settings.sqlite_path,
        dimension=settings.gemini_embedding_dimension,
    )
