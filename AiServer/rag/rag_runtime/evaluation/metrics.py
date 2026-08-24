from __future__ import annotations
from dataclasses import dataclass

@dataclass
class EvaluationMetrics:
    total: int = 0
    retrieval_hits: int = 0
    answer_correct: int = 0
    citation_correct: int = 0
    similar_question_hits: int = 0
    verification_correct: int = 0
    hallucinated: int = 0
    @property
    def retrieval_accuracy(self): return self.retrieval_hits/max(1,self.total)
    @property
    def answer_accuracy(self): return self.answer_correct/max(1,self.total)
    @property
    def citation_accuracy(self): return self.citation_correct/max(1,self.total)
    @property
    def similar_question_accuracy(self): return self.similar_question_hits/max(1,self.total)
    @property
    def verification_accuracy(self): return self.verification_correct/max(1,self.total)
    @property
    def hallucination_rate(self): return self.hallucinated/max(1,self.total)
    def as_dict(self):
        return {"total":self.total,"retrieval_accuracy":self.retrieval_accuracy,"answer_accuracy":self.answer_accuracy,"citation_accuracy":self.citation_accuracy,"similar_question_accuracy":self.similar_question_accuracy,"verification_accuracy":self.verification_accuracy,"hallucination_rate":self.hallucination_rate}
