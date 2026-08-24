from __future__ import annotations
import argparse,json
from pathlib import Path
from common import ROOT, storage_path
from rag_runtime.core.config import settings
from rag_runtime.core.models import Chunk, DocumentMetadata
from rag_runtime.core.registry import DocumentRegistry
from rag_runtime.questions.extractor import QuestionExtractor
from rag_runtime.questions.classifier import GeminiQuestionClassifier

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--file",required=True,help="chunk JSONL file from ingestion"); ap.add_argument("--document-id",required=True); ap.add_argument("--classify",action="store_true"); ap.add_argument("--out",default=str(storage_path("questions.jsonl"))); args=ap.parse_args()
    chunks=[Chunk.model_validate_json(x) for x in Path(args.file).read_text(encoding="utf-8").splitlines() if x.strip()]; meta=DocumentRegistry().get(args.document_id)
    if not meta: raise SystemExit(f"Unknown document_id: {args.document_id}")
    questions=QuestionExtractor().extract_from_chunks(chunks,meta)
    if args.classify:
        s=settings; s.require_gemini(); clf=GeminiQuestionClassifier(s.gemini_api_key,s.gemini_generation_model); questions=[clf.classify(q) for q in questions]
    Path(args.out).parent.mkdir(parents=True,exist_ok=True); Path(args.out).write_text("\n".join(q.model_dump_json() for q in questions),encoding="utf-8")
    print(json.dumps({"questions":len(questions),"out":args.out},ensure_ascii=False,indent=2))
if __name__=="__main__": main()
