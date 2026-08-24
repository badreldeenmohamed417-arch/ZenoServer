from __future__ import annotations
import argparse,json
from pathlib import Path
from common import ROOT, storage_path
from rag_runtime.core.config import settings
from rag_runtime.core.models import Question
from rag_runtime.core.models import StructureConfig
from rag_runtime.embeddings.gemini import GeminiEmbeddingProvider
from rag_runtime.vectorstore.factory import create_vector_store
from rag_runtime.retrieval.retriever import Retriever
from rag_runtime.retrieval.reranker import HybridReranker
from rag_runtime.retrieval.context import build_context
from rag_runtime.questions.verifier import GeminiQuestionVerifier

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--questions",required=True); ap.add_argument("--evidence",help="optional evidence file; otherwise retrieve from vectorstore"); ap.add_argument("--out",default=str(storage_path("questions_verified.jsonl"))); ap.add_argument("--top-k",type=int,default=8); args=ap.parse_args()
    s=settings; s.require_gemini(); verifier=GeminiQuestionVerifier(s.gemini_api_key,s.gemini_generation_model,s.gemini_verifier_model)
    retriever=None
    if not args.evidence:
        emb=GeminiEmbeddingProvider(s.gemini_api_key,s.gemini_embedding_model,s.gemini_embedding_dimension); retriever=Retriever(emb,create_vector_store())
    static_evidence=Path(args.evidence).read_text(encoding="utf-8") if args.evidence else None
    out=[]
    for line in Path(args.questions).read_text(encoding="utf-8").splitlines():
        if not line.strip(): continue
        q=Question.model_validate_json(line)
        evidence=static_evidence if static_evidence is not None else build_context(HybridReranker().rerank(q.text,retriever.search(q.text,args.top_k),min(6,args.top_k)))
        r=verifier.verify(q,evidence)
        q.answer=r.answer; q.explanation=r.explanation; q.verification_status=r.status; q.verification_confidence=r.confidence; q.verification_evidence=r.evidence; q.verifier_model=r.verifier_model; q.verification_timestamp=__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat()
        out.append(q.model_dump_json())
    Path(args.out).parent.mkdir(parents=True,exist_ok=True); Path(args.out).write_text("\n".join(out),encoding="utf-8"); print(json.dumps({"questions":len(out),"out":args.out},indent=2))
if __name__=="__main__": main()
