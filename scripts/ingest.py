import logging
import os
from langchain_community.document_loaders import DirectoryLoader, PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from config import Settings
from database import get_vector_store

logger = logging.getLogger(__name__)


def ingest_docs(settings: Settings):
    logger.info("Запуск процесса индексации документов")

    if not os.path.exists(settings.data_path):
        logger.warning(f"Путь {settings.data_path} не найден. Создаю папку.")
        os.makedirs(settings.data_path)
        return

    loader = DirectoryLoader(settings.data_path, glob="**/*.pdf", loader_cls=PyPDFLoader)
    docs = loader.load()

    if not docs:
        logger.info("Новых PDF документов для загрузки не найдено.")
        return

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )
    chunks = text_splitter.split_documents(docs)

    # используем тот же vector_store, что и в основном приложении
    vector_store = get_vector_store(settings)
    vector_store.add_documents(chunks)

    logger.info(f"Успешно проиндексировано {len(chunks)} чанков в коллекции {settings.collection_name}")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    settings = Settings()
    ingest_docs(settings)