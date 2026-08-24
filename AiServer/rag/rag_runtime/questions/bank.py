from __future__ import annotations
import sqlite3, json
from pathlib import Path
from ..core.models import Question
from ..core.enums import VerificationStatus
from ..core.paths import storage_path

class QuestionBank:
    def __init__(self,path:str|Path|None=None):
        path = path or storage_path("zeno.db")
        self.path=Path(path); self.path.parent.mkdir(parents=True,exist_ok=True); self._init()
    def _conn(self):
        c=sqlite3.connect(self.path); c.row_factory=sqlite3.Row; return c
    def _init(self):
        with self._conn() as c:
            c.execute("""CREATE TABLE IF NOT EXISTS questions (question_id TEXT PRIMARY KEY, payload TEXT NOT NULL, verification_status TEXT NOT NULL, subject TEXT, grade TEXT, term TEXT, curriculum_year TEXT, lesson TEXT, topic TEXT, difficulty TEXT, question_type TEXT, cognitive_level TEXT, source_id TEXT, document_id TEXT, page_start INTEGER, page_end INTEGER)""")
            c.execute("CREATE INDEX IF NOT EXISTS idx_q_filters ON questions(subject,grade,term,curriculum_year,lesson,difficulty,question_type,verification_status)")
    def upsert(self,q:Question):
        p=q.model_dump(mode="json")
        with self._conn() as c:
            c.execute("""INSERT INTO questions VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(question_id) DO UPDATE SET payload=excluded.payload, verification_status=excluded.verification_status, topic=excluded.topic, difficulty=excluded.difficulty, question_type=excluded.question_type, cognitive_level=excluded.cognitive_level""",(q.question_id,json.dumps(p,ensure_ascii=False),q.verification_status.value,q.subject,q.grade,q.term,q.curriculum_year,q.lesson,q.topic,q.difficulty.value,q.question_type.value,q.cognitive_level,q.source_id,q.document_id,q.page_start,q.page_end))
    def list(self, *, subject=None, grade=None, lesson=None, verified=None, difficulty=None, question_type=None, limit=100):
        clauses=[]; params=[]
        for col,val in [("subject",subject),("grade",grade),("lesson",lesson),("difficulty",difficulty),("question_type",question_type)]:
            if val: clauses.append(f"{col}=?"); params.append(val.value if hasattr(val,'value') else val)
        if verified is True: clauses.append("verification_status=?"); params.append(VerificationStatus.VERIFIED.value)
        where=(" WHERE "+" AND ".join(clauses)) if clauses else ""
        with self._conn() as c: rows=c.execute(f"SELECT payload FROM questions{where} ORDER BY rowid DESC LIMIT ?",(*params,limit)).fetchall()
        return [Question.model_validate(json.loads(r[0])) for r in rows]
