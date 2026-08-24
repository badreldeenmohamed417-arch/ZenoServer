from abc import ABC, abstractmethod


class RAGProvider(ABC):
    @abstractmethod
    async def retrieve(
        self,
        query: str,
        *,
        subject: str | None = None,
        grade: str | None = None,
        lesson: str | None = None
    ) -> list[dict]: ...


class PlaceholderRAGProvider(RAGProvider):
    async def retrieve(
        self,
        query: str,
        *,
        subject: str | None = None,
        grade: str | None = None,
        lesson: str | None = None
    ) -> list[dict]:
        return []  # The external Zeno RAG service will replace this adapter.


class RAGService:
    def __init__(self, provider: RAGProvider | None = None):
        self.provider = provider or PlaceholderRAGProvider()

    async def retrieve(
        self,
        query: str,
        *,
        subject: str | None = None,
        grade: str | None = None,
        lesson: str | None = None
    ) -> list[dict]:
        return await self.provider.retrieve(
            query, subject=subject, grade=grade, lesson=lesson
        )
