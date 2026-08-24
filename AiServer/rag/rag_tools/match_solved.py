from __future__ import annotations
import argparse,json
from pathlib import Path
from common import ROOT, storage_path
from rag_runtime.core.models import Chunk, Question
from rag_runtime.questions.solved import SolvedMaterialMatcher

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--questions",required=True); ap.add_argument("--answers",required=True); ap.add_argument("--out",default=str(storage_path("solved_links.json"))); args=ap.parse_args()
    qs=[Question.model_validate_json(x) for x in Path(args.questions).read_text(encoding='utf-8').splitlines() if x.strip()]
    ans=[Chunk.model_validate_json(x) for x in Path(args.answers).read_text(encoding='utf-8').splitlines() if x.strip()]
    links=SolvedMaterialMatcher().match(qs,ans)
    Path(args.out).parent.mkdir(parents=True,exist_ok=True); Path(args.out).write_text(json.dumps(links,ensure_ascii=False,indent=2),encoding='utf-8')
    Path(args.questions).write_text("\n".join(q.model_dump_json() for q in qs),encoding='utf-8')
    print(json.dumps({"links":len(links),"out":args.out},ensure_ascii=False,indent=2))
if __name__=="__main__": main()
