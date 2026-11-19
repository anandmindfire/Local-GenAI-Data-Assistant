"""Unit tests for configuration and settings."""

from app.core.config import Settings


def test_settings_default_values():
    """Verify default configuration values."""
    s = Settings()
    assert s.app_name == "local-genai-assistant"
    assert s.port == 8000
    assert s.chat_model == "qwen3:1.7b"
    assert s.embedding_model == "nomic-embed-text"
    assert s.embedding_dimension == 768
    assert s.chunk_size == 1000
    assert s.chunk_overlap == 200


def test_database_urls():
    """Verify generated database connection strings."""
    s = Settings(
        postgres_host="localhost",
        postgres_port=5432,
        postgres_db="test_db",
        postgres_user="admin",
        postgres_password="password",
        postgres_readonly_user="readonly",
        postgres_readonly_password="ropassword",
    )
    assert s.async_database_url == "postgresql+asyncpg://admin:password@localhost:5432/test_db"
    assert s.sync_database_url == "postgresql+psycopg2://admin:password@localhost:5432/test_db"
    assert (
        s.readonly_async_database_url
        == "postgresql+asyncpg://readonly:ropassword@localhost:5432/test_db"
    )
