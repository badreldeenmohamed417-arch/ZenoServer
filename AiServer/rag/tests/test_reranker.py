from rag_runtime.core.enums import AuthorityLevel, ContentType, SourceType
from rag_runtime.core.models import Chunk, SearchResult
from rag_runtime.retrieval.reranker import HybridReranker

def test_hybrid_reranker_prioritizes_exact_terms_and_authority():
    c1 = Chunk(chunk_id="c1", document_id="d1", source_id="d1", subject="s", grade="g", term="t", curriculum_year="2024", authority=AuthorityLevel.OFFICIAL, source_type=SourceType.OFFICIAL_TEXTBOOK, lesson="l", page_start=1, page_end=1, content_type=ContentType.EXPLANATION, content="photosynthesis and light reactions")
    c2 = Chunk(chunk_id="c2", document_id="d2", source_id="d2", subject="s", grade="g", term="t", curriculum_year="2024", authority=AuthorityLevel.MEDIUM, source_type=SourceType.STUDY_GUIDE, lesson="l", page_start=1, page_end=1, content_type=ContentType.EXPLANATION, content="general plant biology discussion")

    ranked = HybridReranker().rerank("photosynthesis", [SearchResult(chunk_id=c2.chunk_id, chunk=c2, score=0.9, rank=1), SearchResult(chunk_id=c1.chunk_id, chunk=c1, score=0.85, rank=2)], top_k=2)
    assert ranked[0].chunk.chunk_id == "c1"
