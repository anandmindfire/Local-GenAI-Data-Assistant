# Implementation Plan: Local GenAI Data Assistant

## 1. Overview and Engineering Objectives

The **Local GenAI Data Assistant** is a production-grade, modular monolith Python application enabling natural-language interaction with:
1. **Unstructured documents** (PDF, DOCX, TXT, Markdown) via a grounded Retrieval-Augmented Generation (RAG) engine.
2. **Structured relational data** in PostgreSQL via a secure, read-only Natural Language to SQL (NL2SQL) agent.
3. **Combined queries** executed through intelligent orchestration via LangGraph (with parallel fan-out, safe aggregation, and source attribution).

Strict architectural, security, and performance constraints:
- **100% Local Execution**: All inference (Ollama `qwen3:8b` / `llama3.1:8b` configurable, `nomic-embed-text`), relational persistence (PostgreSQL), and vector storage (Qdrant) run locally. Zero data leaks to external cloud APIs.
- **Clean Architecture & Separation of Concerns**: Strict separation between API routes, domain contracts, application modules, and infrastructure drivers.
- **Security-First NL2SQL**: SQLGlot AST validation rejecting all write/mutation/DDL operations, multiple statements, and unauthorized schema access; PostgreSQL dedicated read-only role with SELECT-only grants and statement timeouts.
- **Grounded RAG with Traceability**: Retrieved context treated as untrusted data, prompt injection defense, explicit insufficient-evidence handling, and deterministic source attribution (document ID, filename, page number, chunk ID).
- **Asynchronous & High-Performance**: Async FastAPI endpoints, SQLAlchemy 2.0 async engine with connection pooling, batch vector embeddings, and non-blocking I/O throughout.

---

## 2. Module Dependency Map & Architecture Layers

```
                           ┌────────────────────────────┐
                           │   FastAPI Web API Layer    │
                           │  (Routes, Schemas, Errors) │
                           └─────────────┬──────────────┘
                                         │
                                         ▼
                           ┌────────────────────────────┐
                           │    Application Modules     │
                           │  (LangGraph Orchestration) │
                           └──────┬──────────────┬──────┘
                                  │              │
                   ┌──────────────┴──────┐ ┌─────┴──────────────┐
                   │     RAG Engine      │ │     SQL Agent      │
                   │ (Retrieval, Context)│ │(Gen, Validate, Run)│
                   └──────┬──────────────┘ └─────┬──────────────┘
                          │                      │
             ┌────────────┴────────┐      ┌──────┴──────────────┐
             ▼                     ▼      ▼                     ▼
     ┌──────────────┐     ┌──────────────┐ ┌───────────────────────────┐
     │  Ingestion   │     │ Vector Store │ │ PostgreSQL Infrastructure │
     │  & Parsers   │     │   (Qdrant)   │ │  (App DB & Business DB)   │
     └──────────────┘     └──────────────┘ └───────────────────────────┘
             │                     │                     │
             └─────────────────────┼─────────────────────┘
                                   ▼
                   ┌─────────────────────────────┐
                   │    Core / Domain Layer      │
                   │  (Config, Logging, Models)  │
                   └─────────────────────────────┘
```

### Module Boundaries
- `app.core`: Settings (Pydantic Settings v2), structured logging, custom domain exceptions, security utilities, constants.
- `app.domain`: Domain entities (Document, Chunk, Conversation, Message, QueryResult), enums (Intent, Status), and abstract interfaces.
- `app.infrastructure`:
  - `database`: PostgreSQL connection pools (AsyncEngine, sessionmaker), SQLAlchemy ORM models (conversations, messages, business schema), repositories.
  - `vector_store`: Qdrant client wrapper, collection management, payload schemas, vector operations.
  - `llm`: Ollama client abstractions, ChatOllama wrapper with structured outputs, OllamaEmbeddings wrapper with batch support.
  - `document_parsers`: PDF (PyMuPDF), DOCX (python-docx), TXT, and Markdown parsers.
- `app.modules`:
  - `ingestion`: Ingestion service, text chunking, deduplication (SHA-256), metadata enrichment.
  - `retrieval`: Vector search service, similarity thresholds, metadata filters.
  - `rag`: Grounded answer generation, prompt construction, source attribution, confidence scoring.
  - `sql_agent`: Schema discovery, NL2SQL generation, SQLGlot AST validation, read-only parameterized execution, query logging.
  - `conversation`: Conversation history management, context builder, PostgreSQL message persistence.
  - `graph`: LangGraph state machine, question contextualization, intent router, parallel RAG/SQL nodes, aggregation, persistence.
- `app.api`: FastAPI routers (`/chat`, `/documents`, `/health`), Pydantic v2 schemas, dependency injection providers, global exception handlers.

---

## 3. Phased Implementation Roadmap

### Phase 0: Repository Audit and Technical Planning (Current)
- Complete repository state audit.
- Write architectural specifications, technical decisions, and progress tracking files.
- Establish clean directory structure.

### Phase 1: Foundation and Infrastructure
- Setup `pyproject.toml` with pinned, compatible dependencies.
- Configure virtual environment (`.venv`), Ruff, and Pytest.
- Implement `app/core/config.py` (Pydantic Settings reading `.env`).
- Implement `app/core/logging.py` (structured JSON / standard logging with correlation ID).
- Implement `app/core/exceptions.py` (centralized hierarchy: `LLMUnavailableException`, `SQLValidationError`, etc.).
- Implement database connection pool (`app/infrastructure/database/connection.py`).
- Implement Qdrant client setup (`app/infrastructure/vector_store/qdrant_client.py`).
- Implement Dockerfile (multi-stage build) and `docker-compose.yml` (API, PostgreSQL, Qdrant, Ollama).
- Write `docker/postgres/init/01-init-readonly-user.sh` to configure the restricted read-only user.

### Phase 2: Local LLM and Embedding Integration
- Implement `app/infrastructure/llm/ollama_client.py` and `chat_model.py`.
- Implement `app/infrastructure/llm/embeddings.py` using `nomic-embed-text` with batch processing.
- Implement structured output validation with Pydantic schemas.
- Implement resilience: timeouts, bounded exponential backoff retries, and clear domain exceptions.
- Unit and integration tests for Ollama adapters.

### Phase 3: Document Ingestion Pipeline
- Implement format-specific parsers: `pdf_parser.py` (PyMuPDF), `docx_parser.py`, `text_parser.py`, `markdown_parser.py`.
- Implement SHA-256 document and chunk hashing for deduplication.
- Implement `chunker.py` using `RecursiveCharacterTextSplitter` with configurable size/overlap.
- Implement `metadata.py` with stable `document_id`, `chunk_id`, page numbers, content hashes, and timestamps.
- Implement `ingestion/service.py` to coordinate parsing, chunking, deduplication, and batch vectorization.
- Unit tests verifying multi-format extraction, empty doc handling, chunking, and deterministic hashing.

### Phase 4: Qdrant and Semantic Retrieval
- Implement `collections.py`: ensure collection exists with correct vector dimensions (768 for nomic-embed-text), Cosine distance, and payload indexes.
- Implement vector upsert with stable point IDs (UUID v5 derived from chunk ID).
- Implement semantic similarity search with score thresholding and metadata filters (e.g., document_id, filename).
- Implement complete document deletion (cascade deleting all vectors matching `document_id`).
- Implement vector replacement (safe re-ingestion of updated document content).
- Unit and integration tests for Qdrant storage and retrieval.

### Phase 5: Grounded RAG Engine
- Implement query normalization and prompt injection defenses.
- Implement context constructor: formatted context with clear boundaries, treating document content as untrusted evidence.
- Implement `rag/service.py`: prompt construction, LLM generation, answer validation.
- Implement deterministic source attribution and confidence calculation based on retrieval scores and coverage.
- Implement fallback behavior for insufficient context (no hallucination).
- Unit tests for prompt assembly, source mapping, and insufficient evidence handling.

### Phase 6: PostgreSQL SQL Agent
- Define realistic business schema and seed data (`customers`, `products`, `orders`, `order_items`, `refunds`).
- Implement dynamic schema discovery (`schema_inspector.py`) inspecting tables, columns, data types, primary/foreign keys.
- Implement schema-aware SQL generator prompt (`sql_generator.py`).
- Implement rigorous SQL AST validator (`sql_validator.py`) using `sqlglot`:
  - Enforce `SELECT` statements only.
  - Forbid `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `TRUNCATE`, `CREATE`, `GRANT`, `REVOKE`.
  - Forbid multiple statements / query chaining.
  - Forbid data-modifying CTEs (`WITH ... INSERT/UPDATE/DELETE`).
  - Forbid system functions (`pg_sleep`, `pg_read_file`, `current_setting`, etc.).
  - Enforce table whitelist to prevent schema hopping.
  - Enforce query limits (`LIMIT 100` max).
- Implement SQL executor (`sql_executor.py`) using the restricted `readonly_user` credentials with query timeout (e.g. 5 seconds).
- Implement bounded correction loop (up to 2 retries with validation/execution error feedback).
- Implement `query_logger.py` with correlation ID, execution duration, and sanitized query logs.
- Unit and security tests: exhaustive attack suite testing SQL injection, mutation rejection, and schema enforcement.

### Phase 7: LangGraph Orchestration
- Define strongly typed `AssistantState` with `conversation_id`, `question`, `contextualized_question`, `intent`, `retrieved_documents`, `generated_sql`, `sql_results`, `answer`, `sources`, `execution_errors`.
- Implement `IntentRouterNode`: LLM-based structured classifier (Document, SQL, Combined) with fallback.
- Implement workflow nodes:
  - `LoadContextNode`
  - `ContextualizeQuestionNode`
  - `IntentRouterNode`
  - `RAGNode`
  - `SQLNode`
  - `ParallelCombinedNode` (fans out RAG and SQL execution concurrently)
  - `AggregationNode` (merges RAG and SQL results into a unified, coherent response)
  - `PersistConversationNode`
- Unit and integration tests for workflow routing, parallel execution, and state transitions.

### Phase 8: Conversation Memory
- Design PostgreSQL conversation and message persistence tables (`conversations`, `messages`).
- Implement repository and service for session creation, message logging, and windowed history retrieval.
- Implement follow-up question contextualization: resolving anaphoric references (e.g., "they", "those orders") into standalone queries.
- Ensure strict session isolation: user messages and context never leak across conversation IDs.
- Unit and integration tests for conversation lifecycle and multi-turn resolution.

### Phase 9: FastAPI Implementation
- Implement REST API endpoints:
  - `POST /chat`: chat request, correlation ID generation, LangGraph execution, structured response.
  - `POST /documents/ingest`: multipart file upload and directory batch ingestion.
  - `GET /documents`: paginated list of indexed documents.
  - `DELETE /documents/{id}`: document and vector deletion.
  - `GET /health`: detailed health probe for app, PostgreSQL, Qdrant, Ollama, and models.
- Implement centralized exception handling with consistent error response structures and no stack trace leaks.
- Implement OpenAPI documentation with clear examples.
- Comprehensive API tests using HTTPX AsyncClient.

### Phase 10: Docker & Deployment Configuration
- Multi-stage `Dockerfile` optimizing build size and caching.
- `docker-compose.yml` with health checks, dependencies (`service_healthy`), persistent volumes (`postgres_data`, `qdrant_data`, `ollama_data`), and isolated network.
- `scripts/download_models.sh` for one-time initialization of Ollama models.
- `scripts/seed_database.py` and `scripts/ingest_documents.py`.
- Verification of full local startup and teardown.

### Phase 11: Security, Testing & Evaluation
- Pytest suite: Unit, Integration, API, Security, RAG Evaluation, SQL Evaluation.
- Sample realistic documents in `data/documents/` (policies, handbooks, etc.).
- Complete documentation: `README.md`, `docs/architecture.md`, `docs/security.md`, `docs/api.md`, `docs/technical-decisions.md`.
