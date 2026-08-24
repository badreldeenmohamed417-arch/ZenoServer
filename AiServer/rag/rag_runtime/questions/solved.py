from __future__ import annotations
import re
from hashlib import sha1
from ..core.models import Chunk, Question

class SolvedMaterialMatcher:
    """Conservative question/answer association using explicit numbering first, then lexical overlap."""
    def _number(self,text):
        m=re.match(r"\s*(\d{1,3})[\).:-]",text)
        return m.group(1) if m else None
    def match(self, questions:list[Question], answer_chunks:list[Chunk]):
        links=[]
        for q in questions:
            qnum=self._number(q.text); candidates=[]
            for a in answer_chunks:
                if a.content_type.value != "answer": continue
                anum=self._number(a.content)
                if qnum and anum and qnum==anum: candidates.append((2.0,a))
                else:
                    qt=set(re.findall(r"[\w\u0600-\u06FF]+",q.text.lower())); at=set(re.findall(r"[\w\u0600-\u06FF]+",a.content.lower()));
                    overlap=len(qt&at)/max(1,len(qt));
                    if overlap >= 0.35: candidates.append((overlap,a))
            if not candidates: continue
            candidates.sort(key=lambda x:x[0],reverse=True); score,a=candidates[0]
            q.answer_source_id=a.source_id; q.answer_page=a.page_start; q.answer_id=sha1(f"{a.chunk_id}|{q.question_id}".encode()).hexdigest(); q.answerability="known"
            links.append({"question_id":q.question_id,"answer_id":q.answer_id,"answer_chunk_id":a.chunk_id,"source_id":a.source_id,"page":a.page_start,"score":score})
        return links
