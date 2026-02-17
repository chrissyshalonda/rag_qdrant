import logging

from fastapi import FastAPI
from prometheus_client import make_asgi_app

from config.config import Settings
from main import create_rag_chain
from config.schemas import AnswerResponse, QuestionRequest, RetrievalQuality

logger = logging.getLogger(__name__)



def _create_app() -> FastAPI:
    """
    Создаём экземпляр FastAPI-приложения и инициализируем RAG-цепочку.
    Это выполняется один раз при старте процесса, как в проде.
    """
    settings = Settings()
    answer_fn = create_rag_chain(settings)

    app = FastAPI(title="RAG Assistant API")

    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)

    @app.post("/ask", response_model=AnswerResponse)
    async def ask(request: QuestionRequest) -> AnswerResponse:
        """
        Эндпоинт для вопросов к RAG. В ответе — текст и оценка качества retrieval
        (best_score, low_confidence: нашёл ли релевантные документы).
        """
        logger.info("Получен запрос к /ask")
        result = answer_fn(request.question)
        return AnswerResponse(
            answer=result.answer,
            retrieval_quality=RetrievalQuality(
                best_score=result.best_score,
                low_confidence=result.low_confidence,
            ),
        )

    return app


app = _create_app()

