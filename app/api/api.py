import logging

from fastapi import FastAPI
from pydantic import BaseModel

from config.config import Settings
from main import create_rag_chain


logger = logging.getLogger(__name__)


class QuestionRequest(BaseModel):
    question: str


class AnswerResponse(BaseModel):
    answer: str


def _create_app() -> FastAPI:
    """
    Создаём экземпляр FastAPI-приложения и инициализируем RAG-цепочку.
    Это выполняется один раз при старте процесса, как в проде.
    """
    settings = Settings()
    answer_fn = create_rag_chain(settings)

    app = FastAPI(title="RAG Assistant API")

    @app.post("/ask", response_model=AnswerResponse)
    async def ask(request: QuestionRequest) -> AnswerResponse:
        """
        Простой эндпоинт для задавания вопросов RAG-ассистенту.
        """
        logger.info("Получен запрос к /ask")
        answer = answer_fn(request.question)
        return AnswerResponse(answer=answer)

    return app


app = _create_app()

