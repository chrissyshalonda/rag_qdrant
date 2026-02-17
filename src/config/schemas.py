from dataclasses import dataclass
from pydantic import BaseModel
from langchain_huggingface import ChatHuggingFace
from langchain_core.prompts import ChatPromptTemplate
from config.config import Settings


@dataclass
class RAGChainState:
    """Состояние RAG-цепи: модель, хранилище, промпт и настройки."""
    chat_model: ChatHuggingFace
    vector_store: any
    prompt_template: ChatPromptTemplate
    settings: Settings


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