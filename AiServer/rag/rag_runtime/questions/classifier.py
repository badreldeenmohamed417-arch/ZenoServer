from __future__ import annotations
import json
from pydantic import BaseModel, Field, ValidationError
from ..core.enums import Difficulty, QuestionType
from ..core.models import Question

class Classification(BaseModel):
    subject: str | None = None
    topic: str | None = None
    lesson: str | None = None
    skill: str | None = None
    question_type: QuestionType = QuestionType.OTHER
    difficulty: Difficulty = Difficulty.UNKNOWN
    cognitive_level: str | None = None
    requires_calculation: bool = False
    requires_diagram: bool = False
    answerability: str = "unknown"

class GeminiQuestionClassifier:
    def __init__(self,api_key:str,model:str="gemini-2.5-flash"):
        from google import genai
        from google.genai import types
        self.client=genai.Client(api_key=api_key); self.model=model; self.types=types
    def classify(self,q:Question,evidence:str="")->Question:
        prompt=f"""Classify this educational question conservatively. Return JSON only. Do not invent a lesson not supported by evidence.\nQuestion: {q.text}\nKnown subject: {q.subject}\nKnown grade: {q.grade}\nKnown lesson: {q.lesson}\nEvidence: {evidence}"""
        schema=Classification.model_json_schema()
        response=self.client.models.generate_content(model=self.model,contents=prompt,config=self.types.GenerateContentConfig(response_mime_type="application/json",response_schema=schema,temperature=0,max_output_tokens=600))
        try: data=json.loads(response.text)
        except Exception: data={}
        try: c=Classification.model_validate(data)
        except ValidationError: c=Classification()
        q.topic=c.topic or q.topic; q.lesson=c.lesson or q.lesson; q.skill=c.skill; q.question_type=c.question_type; q.difficulty=c.difficulty; q.cognitive_level=c.cognitive_level; q.requires_calculation=c.requires_calculation; q.requires_diagram=c.requires_diagram; q.answerability=c.answerability
        q.subject=c.subject or q.subject
        return q
