"""Ground-truth retrieval evaluation primitives.

The evaluator uses :class:`src.retrieval.retriever.Retriever`, so query
normalisation and the embedding-provider contract stay identical to Zeno's
retrieval path.  This module only supplies an in-memory cosine vector store
and persistent, content-addressed embedding caches for offline evaluation.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np

from ..core.models import Chunk, SearchResult
from ..embeddings.base import EmbeddingProvider
from ..vectorstore.base import VectorStore


def file_fingerprint(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_chunks(paths: Iterable[Path]) -> list[Chunk]:
    chunks: list[Chunk] = []
    seen: set[str] = set()
    for path in paths:
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                chunk = Chunk.model_validate_json(line)
            except Exception as exc:
                raise ValueError(f"Malformed chunk in {path}:{line_number}: {exc}") from exc
            if chunk.chunk_id in seen:
                raise ValueError(f"Duplicate chunk_id {chunk.chunk_id!r} in evaluation inputs")
            seen.add(chunk.chunk_id)
            chunks.append(chunk)
    return chunks


def _cache_key(paths: Iterable[Path], model_name: str, kind: str) -> str:
    value = {"kind": kind, "model": model_name, "files": [(str(p.resolve()), file_fingerprint(p)) for p in paths]}
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode("utf-8")).hexdigest()


def load_or_embed_chunks(paths: list[Path], chunks: list[Chunk], provider, cache_dir: Path) -> np.ndarray:
    cache_dir.mkdir(parents=True, exist_ok=True)
    key = _cache_key(paths, provider.model_name, "chunks")
    cache_path = cache_dir / f"chunks-{key}.npz"
    if cache_path.exists():
        data = np.load(cache_path, allow_pickle=False)
        ids = data["chunk_ids"].tolist()
        if ids == [c.chunk_id for c in chunks]:
            print(f"Loading embedding cache: {cache_path}")
            return data["embeddings"].astype(np.float32)
    print("Encoding chunks (cache miss)...")
    embeddings = np.asarray(provider.embed([chunk.content for chunk in chunks]), dtype=np.float32)
    np.savez_compressed(cache_path, embeddings=embeddings, chunk_ids=np.asarray([c.chunk_id for c in chunks]))
    return embeddings


def load_or_embed_questions(question_file: Path, questions: list[dict], provider, cache_dir: Path) -> np.ndarray:
    cache_dir.mkdir(parents=True, exist_ok=True)
    key = _cache_key([question_file], provider.model_name, "questions")
    cache_path = cache_dir / f"questions-{key}.npz"
    ids = [q["id"] for q in questions]
    if cache_path.exists():
        data = np.load(cache_path, allow_pickle=False)
        if data["question_ids"].tolist() == ids:
            print(f"Loading question embedding cache: {cache_path}")
            return data["embeddings"].astype(np.float32)
    print("Encoding questions...")
    embeddings = np.asarray(provider.embed([q["question"] for q in questions]), dtype=np.float32)
    np.savez_compressed(cache_path, embeddings=embeddings, question_ids=np.asarray(ids))
    return embeddings


class InMemoryCosineStore(VectorStore):
    """Read-only cosine store used by evaluation, matching vector-store scoring."""
    def __init__(self, chunks: list[Chunk], embeddings: np.ndarray):
        if len(chunks) != len(embeddings):
            raise ValueError("chunk and embedding counts differ")
        self.chunks = chunks
        self.embeddings = np.asarray(embeddings, dtype=np.float32)
        norms = np.linalg.norm(self.embeddings, axis=1, keepdims=True)
        self.embeddings = self.embeddings / np.maximum(norms, 1e-12)

    def upsert(self, chunks: list[Chunk], embeddings: list[list[float]]) -> str:
        raise RuntimeError("Evaluation store is read-only")

    def query(self, embedding: list[float], top_k: int = 10, filters: dict | None = None) -> list[SearchResult]:
        query = np.asarray(embedding, dtype=np.float32)
        query /= max(float(np.linalg.norm(query)), 1e-12)
        indices = np.arange(len(self.chunks))
        if filters:
            indices = np.asarray([i for i, chunk in enumerate(self.chunks) if all(getattr(chunk, key, None) == value for key, value in filters.items())])
        if not len(indices):
            return []
        scores = self.embeddings[indices] @ query
        ordered = indices[np.argsort(-scores, kind="stable")[:top_k]]
        return [SearchResult(chunk_id=self.chunks[i].chunk_id, score=float(self.embeddings[i] @ query), chunk=self.chunks[i], rank=rank)
                for rank, i in enumerate(ordered, 1)]


class CachedQueryEmbeddingProvider(EmbeddingProvider):
    """Adapter that lets Retriever consume an already-cached query vector."""
    def __init__(self, vector: np.ndarray):
        self.vector = vector.astype(np.float32).tolist()

    def embed(self, texts: list[str]) -> list[list[float]]:
        if len(texts) != 1:
            raise ValueError("Cached query adapter supports one Retriever query at a time")
        return [self.vector]


def page_matches(chunk: Chunk, expected_pages: list[int]) -> bool:
    return any(chunk.page_start <= page <= chunk.page_end for page in expected_pages)


def score_retrieval(question: dict, results: list[SearchResult], cutoffs: tuple[int, ...] = (1, 3, 5, 10)) -> dict:
    expected = set(question["expected_chunk_ids"])
    ranks = [result.rank for result in results if result.chunk_id in expected]
    first_rank = min(ranks) if ranks else None
    return {
        **{f"hit_at_{cutoff}": bool(first_rank and first_rank <= cutoff) for cutoff in cutoffs},
        "reciprocal_rank": 1.0 / first_rank if first_rank else 0.0,
        "expected_chunk_rank": first_rank,
        "page_hit_at_10": any(page_matches(result.chunk, question["expected_pages"]) for result in results[:10]),
    }


def aggregate(results: list[dict]) -> dict:
    total = len(results)
    def avg(values): return sum(values) / total if total else 0.0
    return {
        "questions": total,
        "recall_at_1": avg([r["metrics"]["hit_at_1"] for r in results]),
        "recall_at_3": avg([r["metrics"]["hit_at_3"] for r in results]),
        "recall_at_5": avg([r["metrics"]["hit_at_5"] for r in results]),
        "recall_at_10": avg([r["metrics"]["hit_at_10"] for r in results]),
        "mrr": avg([r["metrics"]["reciprocal_rank"] for r in results]),
        "failed_questions": sum(not r["metrics"]["hit_at_10"] for r in results),
        "average_top_1_similarity": avg([r["retrieved"][0]["score"] if r["retrieved"] else 0.0 for r in results]),
        "average_top_5_similarity": avg([sum(x["score"] for x in r["retrieved"][:5]) / min(5, len(r["retrieved"])) if r["retrieved"] else 0.0 for r in results]),
    }
