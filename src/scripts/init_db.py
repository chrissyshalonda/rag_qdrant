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
            if file.lower().endswith(('.pdf', '.docx', '.doc', '.xlsx', '.xls', '.txt')):
                file_paths.append(os.path.join(root, file))
    
    if not file_paths:
        logger.info("Файлы для обработки не найдены.")
        return
    
    _ensure_collection(settings)
    embeddings = FastEmbedEmbeddings(model_name=settings.embedding_model)
    client = _get_client(settings)
    vector_store = QdrantVectorStore(
        client=client,
        collection_name=settings.collection_name,
        embedding=embeddings,
    )
    
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        separators=["\n# ", "\n## ", "\n### ", "\n\n", "\n", " ", ""]
    )

    loader = DoclingLoader(file_path=file_paths)
    doc_iter = loader.lazy_load()
    
    total_chunks = 0
    processed_docs = 0
    batch_chunks = []
    batch_size = 32 
    
    for doc in doc_iter:
        doc_chunks = text_splitter.split_documents([doc])
        batch_chunks.extend(doc_chunks)
        total_chunks += len(doc_chunks)
        
        if len(batch_chunks) >= batch_size:
            vector_store.add_documents(batch_chunks)
            logger.debug("Добавлено %s чанков в векторную БД (всего обработано: %s)", 
                       len(batch_chunks), total_chunks)
            batch_chunks = []
        
        processed_docs += 1
        if processed_docs % 10 == 0:
            logger.info("Обработано документов: %s, чанков: %s", processed_docs, total_chunks)

    if batch_chunks:
        vector_store.add_documents(batch_chunks)
        logger.debug("Добавлено последних %s чанков в векторную БД", len(batch_chunks))
    
    if total_chunks == 0:
        logger.info("Новых документов для загрузки не найдено.")
        return

    logger.info("Готово! Загружено %s чанков из %s документов (%s файлов).", 
                total_chunks, processed_docs, len(file_paths))


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    settings = IngestSettings()
    ingest_docs(settings)
