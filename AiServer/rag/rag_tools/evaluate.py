from __future__ import annotations
import argparse,json
from pathlib import Path
from common import ROOT
from rag_runtime.core.config import settings
from rag_runtime.core.models import Question
from rag_runtime.evaluation.regression import load_dataset
from rag_runtime.evaluation.metrics import EvaluationMetrics

def run_static(dataset):
    return {"regression_cases":len(dataset),"types":sorted({x["type"] for x in dataset})}

def run_live(questions_path, limit):
    from rag_runtime.embeddings.gemini import GeminiEmbeddingProvider
    from rag_runtime.vectorstore.factory import create_vector_store
    from rag_runtime.retrieval.retriever import Retriever
    from rag_runtime.retrieval.reranker import HybridReranker
    from rag_runtime.rag.answerer import GeminiAnswerer
    from rag_runtime.rag.service import RAGService
    from rag_runtime.questions.similarity import QuestionSimilarityEngine
    s=settings; s.require_gemini()
    emb=GeminiEmbeddingProvider(s.gemini_api_key,s.gemini_embedding_model,s.gemini_embedding_dimension); store=create_vector_store()
    service=RAGService(Retriever(emb,store),HybridReranker(),GeminiAnswerer(s.gemini_api_key,s.gemini_generation_model)); similarity=QuestionSimilarityEngine(emb,store)
    qs=[Question.model_validate_json(x) for x in Path(questions_path).read_text(encoding='utf-8').splitlines() if x.strip()][:limit]
    m=EvaluationMetrics(total=len(qs)); details=[]
    for q in qs:
        rag=service.ask(q.text,top_k=12,context_k=6)
        expected_docs={q.document_id}; retrieval_hit=any(r.chunk.document_id in expected_docs and r.chunk.page_start<=q.page_start<=r.chunk.page_end for r in rag.retrieved_results)
        citation_ok=bool(rag.citations) and all(c.chunk_id in {r.chunk_id for r in rag.retrieved_results} for c in rag.citations)
        similar=similarity.similar(q,top_k=5); similar_hit=any(r.chunk.document_id==q.document_id for r in similar)
        answer_match=bool(q.answer and q.answer.strip() and q.answer.strip()[:120].lower() in rag.answer.lower())
        hallucinated=(not rag.insufficient_evidence) and not rag.citations
        m.retrieval_hits+=int(retrieval_hit); m.citation_correct+=int(citation_ok); m.similar_question_hits+=int(similar_hit); m.answer_correct+=int(answer_match); m.hallucinated+=int(hallucinated)
        details.append({"question_id":q.question_id,"retrieval_hit":retrieval_hit,"citation_ok":citation_ok,"similar_hit":similar_hit,"answer_match":answer_match,"hallucinated":hallucinated})
    return {"metrics":m.as_dict(),"details":details}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--questions"); ap.add_argument("--dataset",default="tests/evaluation_dataset.json"); ap.add_argument("--live",action="store_true"); ap.add_argument("--limit",type=int,default=50); ap.add_argument("--out",default="storage/reports/evaluation.json"); args=ap.parse_args()
    data=load_dataset(args.dataset); result=run_static(data)
    if args.live:
        if not args.questions: raise SystemExit("--questions is required with --live")
        result["live"]=run_live(args.questions,args.limit)
    Path(args.out).parent.mkdir(parents=True,exist_ok=True); Path(args.out).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8'); print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=="__main__": main()
