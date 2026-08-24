from __future__ import annotations
import logging
from ..core.exceptions import LLMError
from ..core.models import RAGAnswer
from ..retrieval.context import build_context
from .prompts import answer_prompt
from .citations import extract_citations

log=logging.getLogger(__name__)

class GeminiAnswerer:
    def __init__(self, api_key: str, model: str="gemini-2.5-flash-light", temperature: float=0.1):
        try:
            from google import genai
            from google.genai import types
        except ImportError as exc: raise LLMError("google-genai is required") from exc
        self.client=genai.Client(api_key=api_key); self.model=model; self.temperature=temperature; self.types=types
    def answer(self, question: str, results: list) -> RAGAnswer:
        if not results:
            return RAGAnswer(question=question, answer="لا توجد أدلة كافية في قاعدة المعرفة للإجابة بثقة.", insufficient_evidence=True)
        context=build_context(results)
        try:
            response=self.client.models.generate_content(model=self.model,contents=answer_prompt(question,context),config=self.types.GenerateContentConfig(temperature=self.temperature,max_output_tokens=1800))
            raw=(response.text or "").strip()
            cleaned,citations=extract_citations(raw,results)
            if not citations:
                log.warning("Model returned no valid citations; failing closed")
                return RAGAnswer(question=question,answer="The available evidence was insufficient to produce a grounded answer.",insufficient_evidence=True,citations=[],retrieved_results=results)
            insufficient = any(x in cleaned.lower() for x in ["insufficient evidence", "not enough evidence", "لا توجد أدلة كافية", "الأدلة غير كافية"])
            return RAGAnswer(question=question,answer=cleaned,insufficient_evidence=insufficient,citations=citations,retrieved_results=results)
        except Exception as exc: raise LLMError(f"Grounded answer generation failed: {exc}") from exc
