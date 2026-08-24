from __future__ import annotations
import json
from pydantic import BaseModel
from ..core.enums import VerificationStatus
from ..core.models import Question, VerificationResult

class VerifierPayload(BaseModel):
    answer: str | None = None
    explanation: str | None = None
    confidence: float = 0
    supported: bool = False
    evidence_quotes: list[str] = []

class GeminiQuestionVerifier:
    def __init__(self,api_key:str,model:str="gemini-2.5-flash",second_model:str|None=None):
        from google import genai
        from google.genai import types
        self.client=genai.Client(api_key=api_key); self.model=model; self.second_model=second_model or model; self.types=types
    def _judge(self,model,q,evidence):
        prompt=f"""You are an independent educational verifier. Determine whether a proposed answer is directly supported by TRUSTED evidence. If evidence is insufficient, do not guess. Return JSON.\nQUESTION:\n{q.text}\nPROPOSED ANSWER:\n{q.answer or '(none)'}\nTRUSTED EVIDENCE:\n{evidence}\nFields: answer, explanation, confidence 0..1, supported boolean, evidence_quotes list."""
        r=self.client.models.generate_content(model=model,contents=prompt,config=self.types.GenerateContentConfig(response_mime_type="application/json",response_schema=VerifierPayload.model_json_schema(),temperature=0,max_output_tokens=900))
        try: return VerifierPayload.model_validate(json.loads(r.text))
        except Exception: return VerifierPayload()
    def verify(self,q:Question,evidence:str)->VerificationResult:
        a=self._judge(self.model,q,evidence); b=self._judge(self.second_model,q,evidence)
        confidence=min(a.confidence,b.confidence)
        supported=a.supported and b.supported and confidence>=0.75
        status=VerificationStatus.VERIFIED if supported else VerificationStatus.NEEDS_REVIEW
        if not evidence.strip(): status=VerificationStatus.NEEDS_REVIEW; confidence=0
        answer=a.answer or b.answer
        explanation=a.explanation or b.explanation
        return VerificationResult(status=status,confidence=confidence,evidence=(a.evidence_quotes+b.evidence_quotes)[:8],answer=answer,explanation=explanation,verifier_model=f"{self.model}|{self.second_model}")
