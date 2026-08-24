from __future__ import annotations

import argparse
import json
from pathlib import Path

from common import ROOT
from rag_runtime.core.config import settings
from rag_runtime.core.logging import configure_logging
from rag_runtime.core.models import Chunk
from rag_runtime.embeddings.gemini import GeminiEmbeddingProvider
from rag_runtime.vectorstore.factory import create_vector_store


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chunks", required=True)
    ap.add_argument("--backend", choices=["sqlite"], default="sqlite")
    ap.add_argument("--batch-size", type=int, default=32)
    args = ap.parse_args()

    configure_logging(settings.log_level)
    backend = args.backend or settings.vector_backend
    settings.vector_backend = backend

    settings.require_gemini()

    chunks = [
        Chunk.model_validate_json(x)
        for x in Path(args.chunks).read_text(encoding="utf-8").splitlines()
        if x.strip()
    ]
    emb = GeminiEmbeddingProvider(
        settings.gemini_api_key,
        settings.gemini_embedding_model,
        settings.gemini_embedding_dimension,
    )
    store = create_vector_store()

    total = 0
    for i in range(0, len(chunks), args.batch_size):
        batch = chunks[i : i + args.batch_size]
        vectors = emb.embed([c.content for c in batch])
        mutation = store.upsert(batch, vectors)
        total += len(batch)
        print(f"indexed={total}/{len(chunks)} mutation={mutation}")

    print(json.dumps({"backend": backend, "indexed": total}, indent=2))


if __name__ == "__main__":
    main()
