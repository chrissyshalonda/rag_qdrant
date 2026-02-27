import logging
from dataclasses import dataclass
from typing import List, Tuple

from langchain_core.prompts import ChatPromptTemplate
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
from rank_bm25 import BM25Okapi

from app.core.prompts import COMPANY_ASSISTANT_PROMPT
from app.database import get_vector_store
from app.metrics import (
    record_error,
    record_retrieved_docs,
    record_retrieval_quality,
    record_success,
    track_llm_time,
    track_request_time,
    track_retrieval_time,
)
from config.config import Settings
from config.schemas import RAGResult

logger = logging.getLogger(__name__)

_RRF_K = 60


@dataclass
class RAGChainState:
    """Состояние RAG-цепи: модель, хранилище, промпт и настройки."""
    chat_model: ChatHuggingFace
    vector_store: object
    prompt_template: ChatPromptTemplate
    settings: Settings


def _tokenize(text: str) -> List[str]:
    return text.lower().split()


def _hybrid_retrieve(question: str, state: RAGChainState) -> Tuple[list, list]:
    """
    Hybrid retrieval: vector search + BM25, объединённые через RRF.

    1. Берём candidate_k кандидатов от векторного поиска (уже ранжированы по косинусному сходству).
    2. Вычисляем BM25-скоры по тем же кандидатам и получаем BM25-ранги.
    3. RRF объединяет оба ранга: score = 1/(k + rank_vec) + 1/(k + rank_bm25).
       Ни один сигнал не теряется — документ, хороший в обоих ранжированиях, поднимается выше.
    4. Возвращаем топ-k по RRF, сохраняя векторный score для метрик.
    """
    candidate_k = state.settings.retriever_k * 3
    pairs = state.vector_store.similarity_search_with_score(question, k=candidate_k)
    if not pairs:
        return [], []

    docs = [doc for doc, _ in pairs]
    vector_scores = [s for _, s in pairs]

    bm25 = BM25Okapi([_tokenize(d.page_content) for d in docs])
    bm25_raw = bm25.get_scores(_tokenize(question))
    bm25_rank = [0] * len(docs)
    
    for rank, idx in enumerate(sorted(range(len(docs)), key=lambda i: bm25_raw[i], reverse=True)):
        bm25_rank[idx] = rank

    rrf_scores = [
        1.0 / (_RRF_K + i) + 1.0 / (_RRF_K + bm25_rank[i])
        for i in range(len(docs))
    ]

    top_indices = sorted(range(len(docs)), key=lambda i: rrf_scores[i], reverse=True)
    top_indices = top_indices[:state.settings.retriever_k]

    return [docs[i] for i in top_indices], [vector_scores[i] for i in top_indices]


def _to_similarity(raw: float) -> float:
    s = 1.0 - raw if raw > 1.0 else raw
    return round(min(1.0, max(0.0, s)), 3)


def _build_context(
    docs: list,
    vector_scores: list,
    settings: Settings,
) -> Tuple[str, float | None, bool, list[str]]:
    """
    Собирает контекст для промпта из найденных документов.

    Каждый отрывок помечается источником и векторным score,
    чтобы модель могла ориентироваться в релевантности.
    """
    record_retrieved_docs(len(docs))

    similarities = [_to_similarity(s) for s in vector_scores]
    best_score = max(similarities) if similarities else None

    if best_score is not None:
        record_retrieval_quality(best_score, settings.retrieval_score_threshold)

    low_confidence = (
        best_score is None
        or (
            settings.retrieval_score_threshold is not None
            and best_score < settings.retrieval_score_threshold
        )
    )

    parts: list[str] = []
    sources: list[str] = []

    for doc, sim in zip(docs, similarities):
        source = doc.metadata.get("source", "unknown source")
        page = doc.metadata.get("page", doc.metadata.get("sheet", "?"))

        parts.append(f"[{source}, page {page}, score {sim}]\n{doc.page_content}")
        label = f"{source} (page {page})"
        if label not in sources:
            sources.append(label)

    return "\n\n".join(parts), best_score, low_confidence, sources


def answer_question(question: str, state: RAGChainState) -> RAGResult:
    with track_request_time():
        with track_retrieval_time():
            docs, vector_scores = _hybrid_retrieve(question, state)

        context, best_score, low_confidence, sources = _build_context(
            docs, vector_scores, state.settings
        )
        logger.debug("Retrieval: %d docs, best_score=%.3f", len(docs), best_score or 0)

        formatted = state.prompt_template.format_messages(
            question=question,
            context=context,
        )
        with track_llm_time():
            response = state.chat_model.invoke(formatted)

    record_success()
    return RAGResult(
        answer=response.content,
        best_score=best_score,
        low_confidence=low_confidence,
        sources=sources,
    )


def create_rag_chain(settings: Settings):
    llm = HuggingFaceEndpoint(
        repo_id=settings.llm_repo_id,
        huggingfacehub_api_token=settings.huggingfacehub_api_token,
        task="text-generation",
        temperature=0.1,
    )
    state = RAGChainState(
        chat_model=ChatHuggingFace(llm=llm),
        vector_store=get_vector_store(settings),
        prompt_template=COMPANY_ASSISTANT_PROMPT,
        settings=settings,
    )

    def _answer(question: str) -> RAGResult:
        try:
            return answer_question(question, state)
        except Exception:
            record_error()
            raise

    return _answer
