from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseQdrantSettings(BaseSettings):
    qdrant_url: str = Field(default="http://localhost:6333", description="URL Qdrant")
    collection_name: str = Field(..., description="Имя коллекции")
    embedding_model: str = Field(..., description="Модель эмбеддингов")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
