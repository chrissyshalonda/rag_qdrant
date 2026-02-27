import logging

from fastapi import FastAPI
from prometheus_client import make_asgi_app

from app.core.rag_chain import create_rag_chain
from config.config import Settings
from config.schemas import AnswerResponse, QuestionRequest, RetrievalQuality

logger = logging.getLogger(__name__)

_VERSION = "1.0.0"
_TITLE = "Корпоративный ассистент по документам"


def _create_app() -> FastAPI:
    settings = Settings()
    answer_fn = create_rag_chain(settings)

    app = FastAPI(
        title=_TITLE,
        version=_VERSION,
        description="RAG-ассистент для поиска ответов в документах компании.",
    )

    app.mount("/metrics", make_asgi_app())

    @app.get("/")
    async def root():
        return {"name": _TITLE, "version": _VERSION, "status": "running"}

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.post("/ask", response_model=AnswerResponse)
    async def ask(request: QuestionRequest) -> AnswerResponse:
        logger.info("Запрос /ask: %s", request.question[:120])
        result = answer_fn(request.question)
        return AnswerResponse(
            answer=result.answer,
            sources=result.sources,
            retrieval_quality=RetrievalQuality(
                best_score=result.best_score,
                low_confidence=result.low_confidence,
            ),
        )

    return app


app = _create_app()
