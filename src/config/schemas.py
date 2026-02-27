from dataclasses import dataclass, field
from pydantic import BaseModel


@dataclass
class RAGResult:
    """Результат одного RAG-запроса."""
    answer: str
    best_score: float | None
    low_confidence: bool
    sources: list[str] = field(default_factory=list)


class QuestionRequest(BaseModel):
    """Запрос к ассистенту."""
    question: str
    session_id: str | None = None


class RetrievalQuality(BaseModel):
    """Метаданные качества retrieval."""
    best_score: float | None
    low_confidence: bool


class AnswerResponse(BaseModel):
    """Ответ ассистента."""
    answer: str
    sources: list[str] = []
    retrieval_quality: RetrievalQuality | None = None