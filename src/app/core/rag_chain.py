import logging

from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
from langchain_core.prompts import ChatPromptTemplate

from app.database import get_vector_store
from app.metrics import (
    track_request_time,
    track_retrieval_time,
    track_llm_time,
    record_retrieved_docs,
    record_retrieval_quality,
    record_success,
    record_error,
)
from config.config import Settings
from config.schemas import RAGResult, RAGChainState

logger = logging.getLogger(__name__)


def _build_enriched_context(docs, scores, settings: Settings) -> tuple[str, float | None, bool]:
    """Собирает контекст из документов и вычисляет best_score, low_confidence."""
    record_retrieved_docs(len(docs))
    best_score: float | None = None
    low_confidence = True
    if scores:
        raw_best = max(scores) if max(scores) <= 1.0 else 1.0 - min(scores)
        best_score = min(1.0, max(0.0, raw_best))
        record_retrieval_quality(best_score, settings.retrieval_score_threshold)
        thr = settings.retrieval_score_threshold
        low_confidence = thr is not None and best_score < thr

    enriched_context = ""
    for i, doc in enumerate(docs):
        source = doc.metadata.get("source", "Неизвестный источник")
        page = doc.metadata.get("page", "?")
        enriched_context += f"\n--- Отрывок {i+1} (Источник: {source}, Стр: {page}) ---\n{doc.page_content}\n"
    return enriched_context, best_score, low_confidence


def answer_question(question: str, state: RAGChainState) -> RAGResult:
    """Отвечает на вопрос по контексту из vector store и LLM."""
    with track_request_time():
        with track_retrieval_time():
            pairs = state.vector_store.similarity_search_with_score(
                question, k=state.settings.retriever_k
            )
        docs = [doc for doc, _ in pairs]
        scores = [s for _, s in pairs]

        enriched_context, best_score, low_confidence = _build_enriched_context(
            docs, scores, state.settings
        )
        logger.info(f"Context: {enriched_context}")

        formatted_prompt = state.prompt_template.format_messages(
            question=question,
            context=enriched_context,
        )
        with track_llm_time():
            response = state.chat_model.invoke(formatted_prompt)

        record_success()
        return RAGResult(
            answer=response.content,
            best_score=best_score,
            low_confidence=low_confidence,
        )


def answer_question_with_metrics(question: str, state: RAGChainState) -> RAGResult:
    """Обёртка над answer_question с записью ошибок в метрики."""
    try:
        return answer_question(question, state)
    except Exception:
        record_error()
        raise


def create_rag_chain(settings: Settings):
    """Создаёт и возвращает функцию ответа на вопрос (с метриками)."""
    llm = HuggingFaceEndpoint(
        repo_id="meta-llama/Llama-3.1-8B-Instruct",
        huggingfacehub_api_token=settings.huggingfacehub_api_token,
        task="text-generation",
        temperature=0.1,
    )
    chat_model = ChatHuggingFace(llm=llm)
    vector_store = get_vector_store(settings)
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", """Ты профессиональный ассистент. Твоя задача — отвечать на вопросы, используя предоставленный контекст.
        Если в контексте нет ответа, постарайся ответить на вопрос сам.
        
        При ответе обязательно указывай источник (название файла и страницу), если они есть в контексте.
        
        Контекст:
        {context}"""),
        ("human", "{question}"),
    ])
    state = RAGChainState(
        chat_model=chat_model,
        vector_store=vector_store,
        prompt_template=prompt_template,
        settings=settings,
    )
    return lambda question: answer_question_with_metrics(question, state)
