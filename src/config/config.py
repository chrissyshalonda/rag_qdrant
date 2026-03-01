from functools import lru_cache

from pydantic import Field
from pydantic_settings import SettingsConfigDict
from common.config import BaseQdrantSettings


class Settings(BaseQdrantSettings):
    huggingfacehub_api_token: str
    api_key: str = Field(default="optional_if_not_used")

    retriever_k: int = 4
    retrieval_score_threshold: float = Field(
        default=0.3,
        description="Минимальный приемлемый similarity score для retrieval",
    )
    # LLM через HuggingFace Inference API
    llm_repo_id: str = Field(
        default="meta-llama/Llama-3.1-8B-Instruct",
        description="HuggingFace repo_id LLM-модели",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache()
def get_settings() -> Settings:
    """Возвращает настройки приложения. Файл .env читается один раз."""
    return Settings()