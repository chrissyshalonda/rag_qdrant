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

from common.database import get_vector_store
from common.utils import sha256_file, load_email_meta
from scripts.ingest_config import IngestSettings
from scripts.parsers import parse_files

logger = logging.getLogger(__name__)


def _make_id(file_hash: str, index: int) -> str:
    """Deterministic UUID for a chunk based on file hash and index."""
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{file_hash}_{index}"))


def _create_splitters(settings: IngestSettings):
    """Creates a pair of splitters: by MD headers and by length."""
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
    """Loads and chunks a document depending on the file type."""
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
    """Sends a batch of chunks to Qdrant. Returns True on success."""
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
        logger.error("Error upsert in Qdrant: %s", exc)
        return False


def _process_file(
    file_path: str,
    file_hash: str,
    vector_store: QdrantVectorStore,
    embeddings: FastEmbedEmbeddings,
    settings: IngestSettings,
    splitters: tuple,
) -> Tuple[int, bool]:
    """Processes one file: parses, chunks, and uploads to Qdrant."""
    email_meta = load_email_meta(file_path)
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
        logger.error("Error processing %s: %s", file_path, exc)
        return 0, False


def ingest_docs(settings: IngestSettings) -> None:
    """Indexes all documents from data_path into Qdrant."""
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

    vector_store = get_vector_store(settings)
    splitters = _create_splitters(settings)

    files_count = 0
    for root, _, filenames in os.walk(settings.data_path):
        for fname in filenames:
            if not fname.lower().endswith((".pdf", ".docx", ".xlsx", ".txt")):
                continue
            
            path = os.path.join(root, fname)
            f_hash = sha256_file(path)
            
            added, success = _process_file(path, f_hash, vector_store, embeddings, settings, splitters)
            files_count += 1

            if success:
                logger.info("%s (+%d chunks)", fname, added)
            else:
                logger.error("%s - Error uploading to Qdrant", fname)

    logger.info("Processed %d files.", files_count)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    ingest_docs(IngestSettings())
