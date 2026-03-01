from pydantic import Field
from pydantic_settings import SettingsConfigDict
from common.config import BaseQdrantSettings


class IngestSettings(BaseQdrantSettings):
    data_path: str = Field(default="./data", description="Folder with PDF for indexing")
    chunk_size: int = Field(default=1000, description="Chunk size")
    chunk_overlap: int = Field(default=100, description="Chunk overlap")

    vector_size: int = Field(default=384, description="Vector size")

    model_config = SettingsConfigDict(
        env_file=".env.database",
        env_file_encoding="utf-8",
        extra="ignore",
    )
