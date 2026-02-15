from dataclasses import dataclass
from pydantic import BaseModel


@dataclass
class RAGResult:
    """Результат RAG: ответ и метаданные качества retrieval."""
    answer: str
    best_score: float | None
    low_confidence: bool


class QuestionRequest(BaseModel):
    question: str


class RetrievalQuality(BaseModel):
    """Оценка качества retrieval: нашёл ли RAG релевантные документы."""
    best_score: float | None
    low_confidence: bool


class AnswerResponse(BaseModel):
    answer: str
    retrieval_quality: RetrievalQuality | None = None