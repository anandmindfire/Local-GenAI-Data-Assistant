"""Application configuration module using Pydantic Settings v2."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.constants import (
    DEFAULT_CHAT_MODEL,
    DEFAULT_CHUNK_OVERLAP,
    DEFAULT_CHUNK_SIZE,
    DEFAULT_EMBEDDING_BATCH_SIZE,
    DEFAULT_EMBEDDING_DIMENSION,
    DEFAULT_EMBEDDING_MODEL,
    DEFAULT_MAX_HISTORY_MESSAGES,
    DEFAULT_SIMILARITY_THRESHOLD,
    DEFAULT_TOP_K,
)


class Settings(BaseSettings):
    """Centralized application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    app_name: str = Field(default="local-genai-assistant", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")
    api_prefix: str = Field(default="/api/v1", alias="API_PREFIX")

    # Ollama
    ollama_base_url: str = Field(default="http://localhost:11434", alias="OLLAMA_BASE_URL")
    chat_model: str = Field(default=DEFAULT_CHAT_MODEL, alias="CHAT_MODEL")
    embedding_model: str = Field(default=DEFAULT_EMBEDDING_MODEL, alias="EMBEDDING_MODEL")
    llm_temperature: float = Field(default=0.0, alias="LLM_TEMPERATURE")
    llm_timeout: float = Field(default=120.0, alias="LLM_TIMEOUT")
    llm_max_retries: int = Field(default=2, alias="LLM_MAX_RETRIES")

    # Qdrant
    qdrant_host: str = Field(default="localhost", alias="QDRANT_HOST")
    qdrant_port: int = Field(default=6333, alias="QDRANT_PORT")
    qdrant_grpc_port: int = Field(default=6334, alias="QDRANT_GRPC_PORT")
    qdrant_collection: str = Field(default="documents", alias="QDRANT_COLLECTION")
    qdrant_timeout: float = Field(default=30.0, alias="QDRANT_TIMEOUT")
    embedding_dimension: int = Field(
        default=DEFAULT_EMBEDDING_DIMENSION, alias="EMBEDDING_DIMENSION"
    )

    # PostgreSQL Application Database (Read-Write: conversations, messages, document metadata)
    postgres_host: str = Field(default="localhost", alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")
    postgres_db: str = Field(default="genai_db", alias="POSTGRES_DB")
    postgres_user: str = Field(default="genai_admin", alias="POSTGRES_USER")
    postgres_password: str = Field(default="genai_secret_password", alias="POSTGRES_PASSWORD")
    database_pool_size: int = Field(default=10, alias="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=20, alias="DATABASE_MAX_OVERFLOW")

    # PostgreSQL Read-Only Database (for SQL Agent execution)
    postgres_readonly_user: str = Field(default="genai_readonly", alias="POSTGRES_READONLY_USER")
    postgres_readonly_password: str = Field(
        default="readonly_secret_password", alias="POSTGRES_READONLY_PASSWORD"
    )

    # Ingestion & Chunker
    chunk_size: int = Field(default=DEFAULT_CHUNK_SIZE, alias="CHUNK_SIZE")
    chunk_overlap: int = Field(default=DEFAULT_CHUNK_OVERLAP, alias="CHUNK_OVERLAP")
    embedding_batch_size: int = Field(
        default=DEFAULT_EMBEDDING_BATCH_SIZE, alias="EMBEDDING_BATCH_SIZE"
    )
    documents_directory: Path = Field(default=Path("data/documents"), alias="DOCUMENTS_DIRECTORY")
    max_upload_size_mb: int = Field(default=25, alias="MAX_UPLOAD_SIZE_MB")

    # RAG & Memory
    top_k: int = Field(default=DEFAULT_TOP_K, alias="TOP_K")
    similarity_threshold: float = Field(
        default=DEFAULT_SIMILARITY_THRESHOLD, alias="SIMILARITY_THRESHOLD"
    )
    max_history_messages: int = Field(
        default=DEFAULT_MAX_HISTORY_MESSAGES, alias="MAX_HISTORY_MESSAGES"
    )

    @property
    def async_database_url(self) -> str:
        """Construct SQLAlchemy async database URL for application management."""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def sync_database_url(self) -> str:
        """Construct SQLAlchemy sync database URL for migrations (Alembic)."""
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def readonly_async_database_url(self) -> str:
        """Construct SQLAlchemy async database URL for the restricted read-only SQL agent."""
        return (
            f"postgresql+asyncpg://{self.postgres_readonly_user}:{self.postgres_readonly_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


# Global singleton settings instance
settings = Settings()
