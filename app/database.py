import logging
from qdrant_client import QdrantClient
from qdrant_client.http import models
from langchain_qdrant import QdrantVectorStore
from langchain_community.embeddings.fastembed import FastEmbedEmbeddings
from config.config import Settings

logger = logging.getLogger(__name__)


def _get_embeddings() -> FastEmbedEmbeddings:
    return FastEmbedEmbeddings(model_name="BAAI/bge-small-en-v1.5")


def _get_client(settings: Settings) -> QdrantClient:
    return QdrantClient(url=settings.qdrant_url)


def get_vector_store(settings: Settings) -> QdrantVectorStore:
    try:
        logger.info(f"Подключение к Qdrant по адресу: {settings.qdrant_url}")

        embeddings = _get_embeddings()
        client = _get_client(settings)

        if not client.collection_exists(settings.collection_name):
            logger.info(
                "Коллекция '%s' не найдена. Создаю новую.",
                settings.collection_name,
            )
            client.create_collection(
                collection_name=settings.collection_name,
                vectors_config=models.VectorParams(
                    size=384,
                    distance=models.Distance.COSINE,
                ),
            )
            logger.info("Коллекция '%s' успешно создана.", settings.collection_name)

        vector_store = QdrantVectorStore(
            client=client,
            collection_name=settings.collection_name,
            embedding=embeddings,
        )
        return vector_store
    except Exception as e:
        logger.error(f"Ошибка при инициализации Vector Store: {e}")
        raise