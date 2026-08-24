from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from common import ROOT

from rag_runtime.core.enums import AuthorityLevel, ContentType, SourceType
from rag_runtime.core.models import Chunk
from rag_runtime.embeddings.deterministic import DeterministicEmbeddingProvider
from rag_runtime.vectorstore.sqlite import SQLiteVectorStore


def _make_chunk(idx: int, dim_content: str) -> Chunk:
    return Chunk(
        chunk_id=f"c{idx}",
        document_id="integrated_science_g1_t1",
        source_id="integrated_science_g1_t1",
        subject="science",
        grade="g1",
        term="t1",
        curriculum_year="2024",
        authority=AuthorityLevel.MEDIUM,
        source_type=SourceType.STUDY_GUIDE,
        lesson=f"lesson-{idx % 20}",
        page_start=max(1, idx // 8),
        page_end=max(1, idx // 8),
        content_type=ContentType.EXPLANATION,
        content=f"{dim_content} chunk {idx}: water, heat, photosynthesis, density, and energy transfer",
    )


def main() -> None:
    ap = argparse.ArgumentParser(description="Benchmark sqlite-vec vector search at textbook scale.")
    ap.add_argument("--chunks", type=int, default=800, help="Number of chunks (~100 pages at 8 chunks/page)")
    ap.add_argument("--dimension", type=int, default=768, help="Embedding dimension")
    ap.add_argument("--top-k", type=int, default=12)
    ap.add_argument("--db", default="storage/benchmark_vectors.db")
    ap.add_argument("--report", default="storage/reports/vectorstore_benchmark.json")
    args = ap.parse_args()

    db_path = Path(args.db)
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    emb = DeterministicEmbeddingProvider(args.dimension)
    store = SQLiteVectorStore(db_path, dimension=args.dimension)

    chunks = [_make_chunk(i, "science") for i in range(args.chunks)]
    upsert_start = time.perf_counter()
    vectors = emb.embed([c.content for c in chunks])
    store.upsert(chunks, vectors)
    upsert_ms = (time.perf_counter() - upsert_start) * 1000

    query = "Explain how temperature affects water density and energy transfer"
    query_vec = emb.embed_one(query)

    timings: list[float] = []
    for _ in range(5):
        start = time.perf_counter()
        results = store.query(
            query_vec,
            top_k=args.top_k,
            filters={
                "subject": "science",
                "grade": "g1",
                "document_id": "integrated_science_g1_t1",
            },
        )
        timings.append((time.perf_counter() - start) * 1000)

    report = {
        "backend": "sqlite-vec",
        "description": "Local production vector backend benchmark (~100-page textbook scale)",
        "chunks": args.chunks,
        "dimension": args.dimension,
        "top_k": args.top_k,
        "upsert_ms": round(upsert_ms, 2),
        "query_ms": {
            "min": round(min(timings), 2),
            "median": round(sorted(timings)[len(timings) // 2], 2),
            "max": round(max(timings), 2),
            "samples": [round(t, 2) for t in timings],
        },
        "returned": len(results),
        "top_score": round(results[0].score, 4) if results else None,
        "db_path": str(db_path),
    }
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
