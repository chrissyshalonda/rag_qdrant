import time
from contextlib import contextmanager
from typing import Generator

from prometheus_client import Counter, Histogram

# Количество запросов к RAG (успех / ошибка)
rag_requests_total = Counter(
    "rag_requests_total",
    "Total RAG requests",
    ["status"],  # success | error
)

# Время ответа RAG по этапам (в секундах)
rag_retrieval_duration_seconds = Histogram(
    "rag_retrieval_duration_seconds",
    "Time spent retrieving documents from vector store",
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)
rag_llm_duration_seconds = Histogram(
    "rag_llm_duration_seconds",
    "Time spent in LLM generation",
    buckets=(0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 60.0),
)
rag_request_duration_seconds = Histogram(
    "rag_request_duration_seconds",
    "Total RAG request duration (retrieval + LLM)",
    buckets=(0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 60.0),
)

# Количество документов, возвращённых retriever'ом по запросу
rag_documents_retrieved = Histogram(
    "rag_documents_retrieved",
    "Number of documents retrieved per request",
    buckets=(0, 1, 2, 3, 4, 5, 8, 10, 15, 20),
)

# Качество retrieval: лучший score по запросу (чем выше — тем релевантнее найденные документы)
rag_retrieval_best_score = Histogram(
    "rag_retrieval_best_score",
    "Best similarity score among retrieved documents per request",
    buckets=(0.0, 0.2, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 1.0),
)

# Запросы, где лучший score ниже порога — «ничего релевантного не нашли»
rag_retrieval_low_confidence_total = Counter(
    "rag_retrieval_low_confidence_total",
    "Number of requests where best retrieval score was below threshold",
)


@contextmanager
def track_retrieval_time() -> Generator[None, None, None]:
    """Контекстный менеджер для замера времени retrieval."""
    start = time.perf_counter()
    try:
        yield
    finally:
        rag_retrieval_duration_seconds.observe(time.perf_counter() - start)


@contextmanager
def track_llm_time() -> Generator[None, None, None]:
    """Контекстный менеджер для замера времени работы LLM."""
    start = time.perf_counter()
    try:
        yield
    finally:
        rag_llm_duration_seconds.observe(time.perf_counter() - start)


@contextmanager
def track_request_time() -> Generator[None, None, None]:
    """Контекстный менеджер для замера полного времени запроса."""
    start = time.perf_counter()
    try:
        yield
    finally:
        rag_request_duration_seconds.observe(time.perf_counter() - start)


def record_retrieved_docs(count: int) -> None:
    rag_documents_retrieved.observe(count)


def record_success() -> None:
    rag_requests_total.labels(status="success").inc()


def record_error() -> None:
    rag_requests_total.labels(status="error").inc()


def record_retrieval_quality(best_score: float, score_threshold: float | None) -> None:
    """
    Записывает качество retrieval: лучший score по запросу и флаг низкой уверенности.
    best_score: лучший similarity score среди найденных документов (0..1, выше = релевантнее).
    score_threshold: если задан и best_score < порога — инкрементируется счётчик low_confidence.
    """
    rag_retrieval_best_score.observe(best_score)
    if score_threshold is not None and best_score < score_threshold:
        rag_retrieval_low_confidence_total.inc()
