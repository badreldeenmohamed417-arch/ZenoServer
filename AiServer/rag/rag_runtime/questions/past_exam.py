from __future__ import annotations
import re
from ..core.models import Question, DocumentMetadata
from ..core.enums import QuestionType
from .extractor import QuestionExtractor

class PastExamParser:
    def parse(self,chunks,metadata:DocumentMetadata,exam_year:str|None=None)->list[Question]:
        base=QuestionExtractor().extract_from_chunks(chunks,metadata)
        for q in base:
            q.document_id=metadata.document_id
            if exam_year:
                q.curriculum_year=exam_year
                q.exam_year=exam_year
            marks=re.search(r"(?:\(|\[)?\s*(\d+)\s*(?:marks?|درجات?|درجة)\s*(?:\)|\])?",q.text,re.I)
            if marks: q.marks=int(marks.group(1))
            q.answerability="known" if q.answer else "unknown"
        return base
