from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from functools import lru_cache

class Settings(BaseSettings):
    huggingfacehub_api_token: str
    api_key: str = Field(default="optional_if_not_used")

    qdrant_url: str = Field(default="http://localhost:6333")
    collection_name: str
    retriever_k: int = 4
    retrieval_score_threshold: float = Field(default=0.3, description="Минимальный приемлемый best score, напр. 0.5")

    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8",
        extra="ignore"
    )

@lru_cache()
def get_settings():
    """
    Функция для получения настроек. 
    lru_cache гарантирует, что файл прочитается только один раз.
    """
    return Settings()