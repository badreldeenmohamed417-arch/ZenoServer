from __future__ import annotations
import argparse,json
from pathlib import Path
from common import ROOT, storage_path
from rag_runtime.core.models import Question
from rag_runtime.questions.bank import QuestionBank

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--questions",required=True); ap.add_argument("--verified-only",action="store_true"); ap.add_argument("--db",default=str(storage_path("zeno.db"))); args=ap.parse_args()
    bank=QuestionBank(args.db); count=0
    for line in Path(args.questions).read_text(encoding="utf-8").splitlines():
        if not line.strip(): continue
        q=Question.model_validate_json(line)
        if args.verified_only and q.verification_status.value!="verified": continue
        bank.upsert(q); count+=1
    print(json.dumps({"stored":count,"db":args.db,"verified_only":args.verified_only},ensure_ascii=False,indent=2))
if __name__=="__main__": main()
