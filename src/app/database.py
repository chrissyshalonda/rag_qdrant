import logging

from langchain_community.embeddings.fastembed import FastEmbedEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient

from config.config import Settings

logger = logging.getLogger(__name__)


class CollectionNotFoundError(Exception):
    def __init__(self, collection_name: str, message: str | None = None):
        self.collection_name = collection_name
        super().__init__(
            message
            or f"Коллекция '{collection_name}' не найдена. "
               f"Запустите init_db для создания и заполнения коллекции."
        )


def get_vector_store(settings: Settings) -> QdrantVectorStore:
    logger.info("Подключение к Qdrant: %s", settings.qdrant_url)

    embeddings = FastEmbedEmbeddings(model_name=settings.embedding_model)
    client = QdrantClient(url=settings.qdrant_url)

    if not client.collection_exists(settings.collection_name):
        logger.error("Коллекция '%s' не найдена!", settings.collection_name)
        raise CollectionNotFoundError(settings.collection_name)

    return QdrantVectorStore(
        client=client,
        collection_name=settings.collection_name,
        embedding=embeddings,
    )