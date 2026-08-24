from __future__ import annotations
import argparse
from common import ROOT
from rag_runtime.core.config import settings
from rag_runtime.core.models import Question
from rag_runtime.embeddings.gemini import GeminiEmbeddingProvider
from rag_runtime.vectorstore.factory import create_vector_store
from rag_runtime.questions.similarity import QuestionSimilarityEngine

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("question",nargs="+"); ap.add_argument("--top-k",type=int,default=10); args=ap.parse_args()
    s=settings; s.require_gemini(); emb=GeminiEmbeddingProvider(s.gemini_api_key,s.gemini_embedding_model,s.gemini_embedding_dimension); store=create_vector_store()
    q=Question(question_id="query",text=" ".join(args.question),subject="",grade="",source_id="query",document_id="query",page_start=0,page_end=0); rows=QuestionSimilarityEngine(emb,store).similar(q,args.top_k)
    for r in rows: print(f"{r.score:.4f}\t{r.chunk.document_id}\tpages={r.chunk.page_start}-{r.chunk.page_end}\t{r.chunk.content[:180].replace(chr(10),' ')}")
if __name__=="__main__": main()
