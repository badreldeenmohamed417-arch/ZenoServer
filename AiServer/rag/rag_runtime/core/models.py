from __future__ import annotations
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any
from pydantic import BaseModel, Field, ConfigDict, model_validator
from .enums import AuthorityLevel, ContentType, Difficulty, QuestionType, SourceType, VerificationStatus

UTC = timezone.utc

def now_iso() -> str:
    return datetime.now(UTC).isoformat()

def stable_hash(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()

class DocumentMetadata(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    document_id: str
    title: str
    subject: str
    grade: str
    term: str | None = None
    curriculum_year: str | None = None
    source_type: SourceType
    source_name: str
    source_url: str | None = None
    version: str | None = None
    authority: AuthorityLevel = AuthorityLevel.UNKNOWN
    file_hash: str | None = None
    created_at: str = Field(default_factory=now_iso)
    indexed_at: str | None = None

    @model_validator(mode="after")
    def apply_source_authority(self):
        if self.authority == AuthorityLevel.UNKNOWN:
            mapping = {
                SourceType.OFFICIAL_TEXTBOOK: AuthorityLevel.OFFICIAL,
                SourceType.OFFICIAL_ANSWER_BOOK: AuthorityLevel.OFFICIAL,
                SourceType.PAST_EXAM: AuthorityLevel.HIGH,
                SourceType.SOLVED_WORKSHEET: AuthorityLevel.HIGH,
                SourceType.QUESTION_BANK: AuthorityLevel.MEDIUM,
                SourceType.STUDY_GUIDE: AuthorityLevel.MEDIUM,
                SourceType.TEACHER_MATERIAL: AuthorityLevel.MEDIUM,
                SourceType.OTHER: AuthorityLevel.UNKNOWN,
            }
            self.authority = mapping.get(SourceType(self.source_type), AuthorityLevel.UNKNOWN).value
        return self

class Page(BaseModel):
    document_id: str
    page_number: int
    text: str
    normalized_text: str = ""
    is_empty: bool = False
    suspicious_score: float = 0.0
    needs_ocr: bool = False

class SectionRef(BaseModel):
    name: str
    start_page: int
    end_page: int

class StructureConfig(BaseModel):
    ignore_pages: list[dict[str,int]] = Field(default_factory=list)
    sections: list[SectionRef] = Field(default_factory=list)

    def ignored(self, page: int) -> bool:
        return any(r["start"] <= page <= r["end"] for r in self.ignore_pages)

    def section_for(self, page: int) -> str | None:
        for s in self.sections:
            if s.start_page <= page <= s.end_page:
                return s.name
        return None

class Chunk(BaseModel):
    chunk_id: str
    document_id: str
    source_id: str
    subject: str
    grade: str
    term: str | None = None
    curriculum_year: str | None = None
    authority: AuthorityLevel
    source_type: SourceType
    chapter: str | None = None
    lesson: str | None = None
    section: str | None = None
    page_start: int
    page_end: int
    content_type: ContentType = ContentType.OTHER
    content: str
    answered: bool | None = None
    token_estimate: int = 0
    content_hash: str = ""

    def vector_metadata(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "source_id": self.source_id,
            "subject": self.subject,
            "grade": self.grade,
            "term": self.term,
            "curriculum_year": self.curriculum_year,
            "authority": self.authority.value if hasattr(self.authority, "value") else self.authority,
            "source_type": self.source_type.value if hasattr(self.source_type, "value") else self.source_type,
            "chapter": self.chapter,
            "lesson": self.lesson,
            "section": self.section,
            "page_start": self.page_start,
            "page_end": self.page_end,
            "content_type": self.content_type.value if hasattr(self.content_type, "value") else self.content_type,
            "content": self.content,
            "answered": self.answered,
        }

class Question(BaseModel):
    question_id: str
    text: str
    subject: str
    grade: str
    term: str | None = None
    curriculum_year: str | None = None
    lesson: str | None = None
    topic: str | None = None
    skill: str | None = None
    source_id: str
    document_id: str
    page_start: int
    page_end: int
    question_type: QuestionType = QuestionType.OTHER
    difficulty: Difficulty = Difficulty.UNKNOWN
    cognitive_level: str | None = None
    requires_calculation: bool = False
    requires_diagram: bool = False
    answerability: str = "unknown"
    choices: list[str] = Field(default_factory=list)
    answer: str | None = None
    explanation: str | None = None
    answer_source_id: str | None = None
    answer_page: int | None = None
    marks: int | None = None
    exam_year: str | None = None
    answer_id: str | None = None
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED
    verification_confidence: float = 0.0
    verification_evidence: list[str] = Field(default_factory=list)
    verifier_model: str | None = None
    verification_timestamp: str | None = None

class SearchResult(BaseModel):
    chunk_id: str
    score: float
    chunk: Chunk
    rank: int
    rerank_score: float | None = None

class VerificationResult(BaseModel):
    status: VerificationStatus
    confidence: float
    evidence: list[str] = Field(default_factory=list)
    answer: str | None = None
    explanation: str | None = None
    verifier_model: str | None = None

class AnswerCitation(BaseModel):
    chunk_id: str
    document_id: str
    source_id: str
    page_start: int
    page_end: int
    lesson: str | None = None
    quote: str

class RAGAnswer(BaseModel):
    question: str
    answer: str
    insufficient_evidence: bool = False
    citations: list[AnswerCitation] = Field(default_factory=list)
    retrieved_results: list[SearchResult] = Field(default_factory=list)
