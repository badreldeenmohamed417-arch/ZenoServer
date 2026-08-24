from __future__ import annotations
import re
from hashlib import sha1
from ..core.models import Chunk, Question, DocumentMetadata
from ..core.enums import QuestionType, VerificationStatus

CHOICE_RE=re.compile(r"(?:^|\n)\s*(?:[A-Dأ-د])[\).:-]\s*(.+)")
NUM_RE=re.compile(r"(?:^|\n)\s*(\d{1,3})[\).:-]\s*(.+)")

class QuestionExtractor:
    def extract_from_chunks(self,chunks:list[Chunk], metadata:DocumentMetadata)->list[Question]:
        out=[]
        for c in chunks:
            text=c.content.strip()
            if c.content_type.value not in {"question","exercise","activity"} and not ("؟" in text or "?" in text):
                continue
            # Preserve a multi-question chunk but split numbered prompts conservatively.
            items=self._split(text)
            for item in items:
                qtext=item.strip()
                if len(qtext)<8: continue
                qid=sha1(f"{c.document_id}|{c.page_start}|{qtext}".encode()).hexdigest()
                choices=CHOICE_RE.findall(qtext)
                answer=None
                out.append(Question(
                    question_id=qid,text=qtext,subject=metadata.subject,grade=metadata.grade,term=metadata.term,
                    curriculum_year=metadata.curriculum_year,lesson=c.lesson,source_id=c.source_id,document_id=c.document_id,
                    page_start=c.page_start,page_end=c.page_end,question_type=self._guess_type(qtext,choices),choices=choices,
                    verification_status=VerificationStatus.UNVERIFIED,
                ))
        return self._dedupe(out)
    def _split(self,text):
        numbered=list(NUM_RE.finditer(text))
        if len(numbered)>=2:
            vals=[]
            for i,m in enumerate(numbered): vals.append(text[m.start(): numbered[i+1].start() if i+1<len(numbered) else len(text)])
            return vals
        return [text]
    def _guess_type(self,text,choices):
        low=text.lower()
        if len(choices)>=2: return QuestionType.MCQ
        if re.search(r"صح|خطأ|true|false",low): return QuestionType.TRUE_FALSE
        if re.search(r"احسب|calculate|ما قيمة|كم|find|احسب قيمة",low): return QuestionType.CALCULATION
        if "____" in text or re.search(r"أكمل|fill",low): return QuestionType.FILL_BLANK
        if re.search(r"زاوج|صل|matching|match",low): return QuestionType.MATCHING
        if len(text)>350: return QuestionType.ESSAY
        return QuestionType.SHORT_ANSWER
    def _dedupe(self,questions):
        seen=set(); out=[]
        for q in questions:
            key=re.sub(r"\W+"," ",q.text.lower()).strip()
            if key in seen: continue
            seen.add(key); out.append(q)
        return out
