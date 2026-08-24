from __future__ import annotations
from ..core.models import SearchResult

def build_context(results: list[SearchResult], max_chars: int=10000) -> str:
    blocks=[]; total=0
    for r in results:
        text=r.chunk.content.strip()
        block=f"[SOURCE {r.chunk_id} | {r.chunk.document_id} | pages {r.chunk.page_start}-{r.chunk.page_end} | lesson={r.chunk.lesson or '-'}]\n{text}"
        if total+len(block)>max_chars: break
        blocks.append(block); total+=len(block)+2
    return "\n\n".join(blocks)
