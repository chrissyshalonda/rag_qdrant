import logging
from qdrant_client import QdrantClient
from langchain_qdrant import QdrantVectorStore
from langchain_community.embeddings.fastembed import FastEmbedEmbeddings
from config.config import Settings

logger = logging.getLogger(__name__)


class CollectionNotFoundError(Exception):
    """Коллекция не найдена в Qdrant. Запустите ingest для создания и заполнения коллекции."""

    def __init__(self, collection_name: str, message: str | None = None):
        self.collection_name = collection_name
        super().__init__(
            message or f"Коллекция '{collection_name}' не найдена. Запустите ingest для создания и заполнения коллекции."
        )


def _get_embeddings() -> FastEmbedEmbeddings:
    return FastEmbedEmbeddings(model_name="intfloat/multilingual-e5-large")


def _get_client(settings: Settings) -> QdrantClient:
    return QdrantClient(url=settings.qdrant_url)


def get_vector_store(settings: Settings) -> QdrantVectorStore:
    """
    Возвращает Vector Store для существующей коллекции.
    Если коллекции нет — выбрасывает CollectionNotFoundError.
    """
    try:
        logger.info(f"Подключение к Qdrant по адресу: {settings.qdrant_url}")

        embeddings = _get_embeddings()
        client = _get_client(settings)

        if not client.collection_exists(settings.collection_name):
            raise CollectionNotFoundError(settings.collection_name)

        vector_store = QdrantVectorStore(
            client=client,
            collection_name=settings.collection_name,
            embedding=embeddings,
        )
        return vector_store
    except CollectionNotFoundError:
        raise
    except Exception as e:
        logger.error(f"Ошибка при инициализации Vector Store: {e}")
        raise