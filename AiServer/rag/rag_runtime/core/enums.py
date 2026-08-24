from enum import Enum

class SourceType(str, Enum):
    OFFICIAL_TEXTBOOK = "official_textbook"
    OFFICIAL_ANSWER_BOOK = "official_answer_book"
    STUDY_GUIDE = "study_guide"
    SOLVED_WORKSHEET = "solved_worksheet"
    PAST_EXAM = "past_exam"
    QUESTION_BANK = "question_bank"
    TEACHER_MATERIAL = "teacher_material"
    OTHER = "other"

class AuthorityLevel(str, Enum):
    OFFICIAL = "official"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"

class ContentType(str, Enum):
    EXPLANATION = "explanation"
    DEFINITION = "definition"
    EXAMPLE = "example"
    ACTIVITY = "activity"
    EXERCISE = "exercise"
    QUESTION = "question"
    ANSWER = "answer"
    TABLE = "table"
    NOTE = "note"
    SUMMARY = "summary"
    INSTRUCTION = "instruction"
    OTHER = "other"

class QuestionType(str, Enum):
    MCQ = "mcq"
    TRUE_FALSE = "true_false"
    SHORT_ANSWER = "short_answer"
    ESSAY = "essay"
    CALCULATION = "calculation"
    MATCHING = "matching"
    FILL_BLANK = "fill_blank"
    OTHER = "other"

class Difficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    UNKNOWN = "unknown"

class VerificationStatus(str, Enum):
    VERIFIED = "verified"
    NEEDS_REVIEW = "needs_review"
    REJECTED = "rejected"
    UNVERIFIED = "unverified"
