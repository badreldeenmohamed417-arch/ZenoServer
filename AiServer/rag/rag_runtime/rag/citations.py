from __future__ import annotations
import re
from ..core.models import AnswerCitation, SearchResult

CITE_RE=re.compile(r"\[CITE:\s*([^|\]]+)\s*\|\s*pages:\s*(\d+)\s*-\s*(\d+)\s*\]")

def extract_citations(answer: str, results: list[SearchResult]) -> tuple[str,list[AnswerCitation]]:
    by_id = {}
    for r in results:
        by_id[r.chunk.chunk_id] = r
        if hasattr(r, "chunk_id"):
            by_id[r.chunk_id] = r

    citations = []
    seen = set()
    for cid, a, b in CITE_RE.findall(answer):
        cid = cid.strip()
        r = by_id.get(cid)
        if not r or cid in seen:
            continue
        seen.add(cid)
        citations.append(
            AnswerCitation(
                chunk_id=r.chunk.chunk_id,
                document_id=r.chunk.document_id,
                source_id=r.chunk.source_id,
                page_start=r.chunk.page_start,
                page_end=r.chunk.page_end,
                lesson=r.chunk.lesson,
                quote=r.chunk.content[:280]
            )
        )
    cleaned = CITE_RE.sub("", answer).strip()
    return cleaned, citations
