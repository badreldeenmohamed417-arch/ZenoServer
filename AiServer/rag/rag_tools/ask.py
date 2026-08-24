from __future__ import annotations

import argparse

from common import ROOT
from rag_runtime.core.config import settings as settings_var
from rag_runtime.embeddings.gemini import GeminiEmbeddingProvider
from rag_runtime.rag.answerer import GeminiAnswerer
from rag_runtime.rag.service import RAGService
from rag_runtime.retrieval.reranker import HybridReranker
from rag_runtime.retrieval.retriever import Retriever
from rag_runtime.vectorstore.factory import create_vector_store


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("question", nargs="+")
    ap.add_argument("--backend", choices=["sqlite"], default="sqlite")
    args = ap.parse_args()
    q = " ".join(args.question)

    settings = settings_var.from_env()
    backend = args.backend or settings.vector_backend
    settings.vector_backend = backend
    settings.require_gemini()

    emb = GeminiEmbeddingProvider(
        settings.gemini_api_key,
        settings.gemini_embedding_model,
        settings.gemini_embedding_dimension,
    )
    store = create_vector_store()
    service = RAGService(
        Retriever(emb, store),
        HybridReranker(),
        GeminiAnswerer(settings.gemini_api_key, settings.gemini_generation_model),
    )
    ans = service.ask(q)
    print(ans.answer)
    print("\nCitations:")
    for c in ans.citations:
        print(f"- {c.document_id}, pages {c.page_start}-{c.page_end}, chunk={c.chunk_id}")


if __name__ == "__main__":
    main()
