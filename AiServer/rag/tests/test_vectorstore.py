from __future__ import annotations

import json
import time
from pathlib import Path

from rag_runtime.core.enums import AuthorityLevel, ContentType, SourceType
from rag_runtime.core.models import Chunk
from rag_runtime.embeddings.deterministic import DeterministicEmbeddingProvider
from rag_runtime.vectorstore.sqlite import SQLiteVectorStore


def _make_chunk(
    idx: int,
    *,
    subject: str = "science",
    grade: str = "g1",
    term: str = "t1",
    curriculum_year: str = "2024",
    source_type: SourceType = SourceType.STUDY_GUIDE,
    document_id: str = "doc1",
    lesson: str = "water",
    content_type: ContentType = ContentType.EXPLANATION,
    content: str | None = None,
) -> Chunk:
    text = content or f"lesson chunk {idx} about water density and heat transfer"
    return Chunk(
        chunk_id=f"c{idx}",
        document_id=document_id,
        source_id=document_id,
        subject=subject,
        grade=grade,
        term=term,
        curriculum_year=curriculum_year,
        authority=AuthorityLevel.MEDIUM,
        source_type=source_type,
        lesson=lesson,
        page_start=idx,
        page_end=idx,
        content_type=content_type,
        content=text,
    )


def test_local_vector_query_and_metadata_filter(tmp_path):
    dim = 16
    emb = DeterministicEmbeddingProvider(dim)
    store = SQLiteVectorStore(tmp_path / "v.db", dimension=dim)
    chunk = _make_chunk(1, content="water density")
    store.upsert([chunk], emb.embed([chunk.content]))
    results = store.query(emb.embed_one("water"), filters={"subject": "science"})
    assert results and results[0].chunk.chunk_id == "c1"


def test_metadata_filter_operators(tmp_path):
    dim = 16
    emb = DeterministicEmbeddingProvider(dim)
    store = SQLiteVectorStore(tmp_path / "v.db", dimension=dim)

    chunks = [
        _make_chunk(1, subject="science", grade="g1", lesson="water", content="water cycle"),
        _make_chunk(2, subject="math", grade="g1", lesson="algebra", content="linear equations"),
        _make_chunk(3, subject="science", grade="g2", lesson="cells", content="plant cells"),
    ]
    store.upsert(chunks, emb.embed([c.content for c in chunks]))

    eq_hits = store.query(emb.embed_one("water"), filters={"subject": {"$eq": "science"}})
    assert {r.chunk.chunk_id for r in eq_hits} == {"c1", "c3"}

    in_hits = store.query(
        emb.embed_one("equations"),
        filters={"subject": {"$in": ["science", "math"]}, "grade": "g1"},
    )
    assert {r.chunk.chunk_id for r in in_hits} == {"c1", "c2"}
