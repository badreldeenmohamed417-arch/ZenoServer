from __future__ import annotations
import random
from ..core.models import Question

class SyntheticUserEvaluator:
    def __init__(self,rag_service,similarity_engine,seed=42):
        self.rag=rag_service; self.similarity=similarity_engine; self.random=random.Random(seed)
    def run(self,questions:list[Question],limit:int=50):
        selected=questions[:]; self.random.shuffle(selected); selected=selected[:limit]
        metrics=[]; details=[]
        from .metrics import EvaluationMetrics
        m=EvaluationMetrics(total=len(selected))
        for q in selected:
            rag=self.rag.ask(q.text,top_k=12,context_k=6)
            hit=any(r.chunk.document_id==q.document_id and r.chunk.page_start<=q.page_start<=r.chunk.page_end for r in rag.retrieved_results)
            cites_ok=all(c.chunk_id in {r.chunk_id for r in rag.retrieved_results} for c in rag.citations)
            similar=self.similarity.similar(q,top_k=5)
            similar_hit=any(r.chunk.document_id==q.document_id for r in similar)
            answer_ok=bool(q.answer and q.answer.strip() and q.answer.strip() in rag.answer)
            m.retrieval_hits+=int(hit); m.citation_correct+=int(cites_ok); m.similar_question_hits+=int(similar_hit); m.answer_correct+=int(answer_ok)
            details.append({"question_id":q.question_id,"retrieval_hit":hit,"citation_ok":cites_ok,"similar_hit":similar_hit,"answer_match":answer_ok,"insufficient_evidence":rag.insufficient_evidence})
        return m,details
