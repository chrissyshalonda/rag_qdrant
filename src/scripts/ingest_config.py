from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class IngestSettings(BaseSettings):
    """Настройки для standalone-скрипта индексации векторной БД."""

    qdrant_url: str = Field(default="http://localhost:6333", description="URL Qdrant")
    collection_name: str = Field(..., description="Имя коллекции")

    data_path: str = Field(default="./data", description="Папка с PDF для индексации")
    chunk_size: int = Field(default=1000, description="Размер чанка")
    chunk_overlap: int = Field(default=100, description="Перекрытие чанков")

    embedding_model: str = Field(
        default="BAAI/bge-small-en-v1.5",
        description="Модель эмбеддингов (должна совпадать с RAG-сервисом)",
    )
    vector_size: int = Field(default=384, description="Размерность вектора")

    model_config = SettingsConfigDict(
        env_file=".env.database",
        env_file_encoding="utf-8",
        extra="ignore",
    )
