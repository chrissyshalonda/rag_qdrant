import json
import logging
import os
import uuid
from typing import Iterable, List, Tuple

from langchain_community.embeddings.fastembed import FastEmbedEmbeddings
from langchain_core.documents import Document
from langchain_docling import DoclingLoader
from langchain_qdrant import QdrantVectorStore
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models

# Note: adjusted imports for db_manager structure
from scripts.ingest_config import IngestSettings
from scripts.ingest_state import IngestStateDB
from scripts.parsers import parse_files, sha256_file

logger = logging.getLogger(__name__)


def _make_id(file_hash: str, index: int) -> str:
    """Детерминированный UUID для чанка на основе хеша файла и индекса."""
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{file_hash}_{index}"))


def _create_splitters(settings: IngestSettings):
    """Создаёт пару сплиттеров: по заголовкам MD и по длине."""
    header_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=[("#", "h1"), ("##", "h2"), ("###", "h3")]
    )
    length_splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )
    return header_splitter, length_splitter


def _extract_documents(
    file_path: str,
    is_xlsx: bool,
    header_splitter: MarkdownHeaderTextSplitter,
    length_splitter: RecursiveCharacterTextSplitter,
) -> Iterable[Document]:
    """Загружает и чанкует документ в зависимости от типа файла."""
    if is_xlsx:
        for parsed in parse_files([file_path]):
            yield parsed.document
    else:
        loader = DoclingLoader(file_path=[file_path])
        for doc in loader.lazy_load():
            for header_chunk in header_splitter.split_text(doc.page_content):
                temp = Document(
                    page_content=header_chunk.page_content,
                    metadata={**doc.metadata, **header_chunk.metadata},
                )
                yield from length_splitter.split_documents([temp])


def _load_email_meta(file_path: str) -> dict:
    meta_path = file_path + ".meta.json"
    if not os.path.exists(meta_path):
        return {}
    with open(meta_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _upsert_batch(
    vector_store: QdrantVectorStore,
    chunks: List[Document],
    ids: List[str],
    embeddings_model: FastEmbedEmbeddings,
) -> bool:
    """Отправляет батч чанков в Qdrant. Возвращает True при успехе."""
    if not chunks:
        return True
    try:
        vectors = embeddings_model.embed_documents([c.page_content for c in chunks])
        points = [
            qdrant_models.PointStruct(
                id=idx,
                vector=vec,
                payload={"page_content": chunk.page_content, **chunk.metadata},
            )
            for chunk, vec, idx in zip(chunks, vectors, ids)
        ]
        vector_store.client.upsert(
            collection_name=vector_store.collection_name,
            points=points,
        )
        return True
    except Exception as exc:
        logger.error("Ошибка upsert в Qdrant: %s", exc)
        return False


def _process_file(
    file_path: str,
    file_hash: str,
    vector_store: QdrantVectorStore,
    embeddings: FastEmbedEmbeddings,
    settings: IngestSettings,
    splitters: tuple,
) -> Tuple[int, bool]:
    """Обрабатывает один файл: парсит, чанкует, загружает в Qdrant."""
    email_meta = _load_email_meta(file_path)
    is_xlsx = file_path.lower().endswith(".xlsx")
    header_splitter, length_splitter = splitters

    batch_chunks: List[Document] = []
    batch_ids: List[str] = []
    total_added = 0

    try:
        for idx, chunk in enumerate(
            _extract_documents(file_path, is_xlsx, header_splitter, length_splitter)
        ):
            chunk.metadata.update(email_meta)
            batch_chunks.append(chunk)
            batch_ids.append(_make_id(file_hash, idx))

            if len(batch_chunks) >= 32:
                if not _upsert_batch(vector_store, batch_chunks, batch_ids, embeddings):
                    return total_added, False
                total_added += len(batch_chunks)
                batch_chunks, batch_ids = [], []

        if batch_chunks:
            if not _upsert_batch(vector_store, batch_chunks, batch_ids, embeddings):
                return total_added, False
            total_added += len(batch_chunks)

        return total_added, True

    except Exception as exc:
        logger.error("Ошибка обработки %s: %s", file_path, exc)
        return 0, False


def ingest_docs(settings: IngestSettings) -> None:
    """Индексирует все новые и изменённые документы из data_path в Qdrant."""
    state_db = IngestStateDB(os.path.join(os.path.dirname(__file__), "ingest_state.db"))
    embeddings = FastEmbedEmbeddings(model_name=settings.embedding_model)
    client = QdrantClient(url=settings.qdrant_url)

    if not client.collection_exists(settings.collection_name):
        client.create_collection(
            collection_name=settings.collection_name,
            vectors_config=qdrant_models.VectorParams(
                size=settings.vector_size,
                distance=qdrant_models.Distance.COSINE,
            ),
        )

    vector_store = QdrantVectorStore(
        client=client,
        collection_name=settings.collection_name,
        embedding=embeddings,
    )
    splitters = _create_splitters(settings)

    # Собираем файлы, которые нужно обработать
    files_to_process: List[Tuple[str, str]] = []
    for root, _, filenames in os.walk(settings.data_path):
        for fname in filenames:
            if not fname.lower().endswith((".pdf", ".docx", ".xlsx", ".txt")):
                continue
            path = os.path.join(root, fname)
            f_hash = sha256_file(path)
            if not state_db.should_skip_file(path, f_hash):
                files_to_process.append((path, f_hash))

    logger.info("Новых/изменённых файлов для индексации: %d", len(files_to_process))

    for path, f_hash in files_to_process:
        state_db.mark_in_progress(path, f_hash)
        added, success = _process_file(path, f_hash, vector_store, embeddings, settings, splitters)

        if success:
            state_db.mark_done(path, f_hash)
            logger.info("%s (+%d чанков)", os.path.basename(path), added)
        else:
            state_db.mark_failed(path, f_hash, "Ошибка загрузки в Qdrant")
            logger.error("%s", os.path.basename(path))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    ingest_docs(IngestSettings())
