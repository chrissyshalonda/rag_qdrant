import logging
import os
import sys

from langchain_community.embeddings.fastembed import FastEmbedEmbeddings
from langchain_qdrant import QdrantVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client import QdrantClient
from qdrant_client.http import models
from langchain_docling import DoclingLoader


_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)
from scripts.ingest_config import IngestSettings

logger = logging.getLogger(__name__)


def _get_client(settings: IngestSettings) -> QdrantClient:
    return QdrantClient(url=settings.qdrant_url)


def _ensure_collection(settings: IngestSettings) -> None:
    client = _get_client(settings)
    if not client.collection_exists(settings.collection_name):
        logger.info("Коллекция '%s' не найдена. Создаю новую.", settings.collection_name)
        client.create_collection(
            collection_name=settings.collection_name,
            vectors_config=models.VectorParams(
                size=settings.vector_size,
                distance=models.Distance.COSINE,
            ),
        )
        logger.info("Коллекция '%s' успешно создана.", settings.collection_name)


def ingest_docs(settings: IngestSettings) -> None:
    logger.info("Запуск процесса индексации документов (конфиг: .env_database)")

    if not os.path.exists(settings.data_path):
        logger.warning("Путь %s не найден. Создаю папку.", settings.data_path)
        os.makedirs(settings.data_path)
        return

    file_paths = []
    for root, _, files in os.walk(settings.data_path):
        for file in files:
            if file.lower().endswith((".pdf", ".docx", ".pptx", ".xlsx", ".html")):
                file_paths.append(os.path.join(root, file))
    
    if not file_paths:
        logger.info("Файлы для обработки не найдены.")
        return
    
    loader = DoclingLoader(file_path=file_paths)
    docs = loader.load()

    if not docs:
        logger.info("Новых PDF документов для загрузки не найдено.")
        return

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        separators=["\n# ", "\n## ", "\n### ", "\n\n", "\n", " ", ""]
    )
    chunks = text_splitter.split_documents(docs)

    _ensure_collection(settings)
    embeddings = FastEmbedEmbeddings(model_name=settings.embedding_model)
    client = _get_client(settings)
    vector_store = QdrantVectorStore(
        client=client,
        collection_name=settings.collection_name,
        embedding=embeddings,
    )
    vector_store.add_documents(chunks)

    logger.info("Готово! Загружено %s чанков из %s файлов.", len(chunks), len(file_paths))


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    settings = IngestSettings()
    ingest_docs(settings)
