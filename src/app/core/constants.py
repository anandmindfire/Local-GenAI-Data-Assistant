"""Application constants and default configurations."""

# Model Defaults
DEFAULT_CHAT_MODEL = "qwen3:1.7b"
DEFAULT_EMBEDDING_MODEL = "nomic-embed-text"
DEFAULT_EMBEDDING_DIMENSION = 768

# Ingestion Defaults
DEFAULT_CHUNK_SIZE = 1000
DEFAULT_CHUNK_OVERLAP = 200
DEFAULT_EMBEDDING_BATCH_SIZE = 32
SUPPORTED_FILE_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}

# Retrieval Defaults
DEFAULT_TOP_K = 4
DEFAULT_SIMILARITY_THRESHOLD = 0.5

# Database Defaults
DEFAULT_QUERY_TIMEOUT_SECONDS = 5.0
DEFAULT_SQL_ROW_LIMIT = 100

# Conversation Defaults
DEFAULT_MAX_HISTORY_MESSAGES = 10

# Allowed Business Tables for SQL Agent (Defense in Depth)
ALLOWED_BUSINESS_TABLES = frozenset({"customers", "products", "orders", "order_items", "refunds"})

# Forbidden SQL statements / AST expressions
FORBIDDEN_SQL_STATEMENTS = frozenset(
    {
        "insert",
        "update",
        "delete",
        "drop",
        "alter",
        "truncate",
        "create",
        "grant",
        "revoke",
        "comment",
        "vacuum",
        "reindex",
        "cluster",
        "refresh",
    }
)
