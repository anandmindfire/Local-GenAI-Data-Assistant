# Technical Decisions & Architectural Rationale

This document captures the key architectural and technical decisions made for the **Local GenAI Data Assistant**, detailing the rationale, trade-offs, and alternatives considered.

---

## 1. Modular Monolith vs. Microservices

### Decision
Implement the entire application as a **Modular Monolith** in Python 3.12, organized with clear domain boundaries, dependency injection, and clean architecture layers.

### Rationale
- **Zero Network Overhead**: Calling between RAG, SQL Agent, Ingestion, and Orchestration occurs in-process with Python async functions, avoiding serialization, RPC latency, and network failure modes.
- **Unified Local Deployment**: A single container for the backend API minimizes memory footprint on local developer workstations, allowing remaining RAM/VRAM to be dedicated to the LLM and vector store.
- **Operational Simplicity**: Avoids distributed tracing complexity, service meshes, and multi-repo synchronization while maintaining strict logical decoupling between modules.

### Alternatives Considered
- *Microservices (Separate RAG service, SQL service, Router service)*: Rejected due to unnecessary operational complexity, distributed transaction difficulties, and redundant memory overhead for local execution.

---

## 2. LLM Runtime: Ollama with Qwen 2.5 / 3 and Nomic Embed Text

### Decision
Use **Ollama** as the local inference runtime, pairing a general-purpose chat model (`qwen2.5:7b` / `qwen3:8b` / `llama3.1:8b`) with `nomic-embed-text` (768-dimensional embeddings).

### Rationale
- **Standard Local API**: Ollama provides a reliable, high-performance C++ backend (llama.cpp) with GPU acceleration (Metal on macOS, CUDA on Linux/Windows) and native OpenAI/LangChain-compatible REST APIs.
- **Local Privacy**: Ensures zero data leakage to external cloud APIs, complying with enterprise data residency and privacy mandates.
- **Configurable Models**: Model names are strictly externalized in environment variables (`CHAT_MODEL`, `EMBEDDING_MODEL`), permitting drop-in replacement with any compatible GGUF model in Ollama without code changes.

### Alternatives Considered
- *vLLM / TGI*: High resource requirements, complex setup on macOS/Metal, overkill for single-user local deployment.
- *Local HuggingFace Transformers in Python*: High RAM footprint, GIL constraints in Python process, slower than C++ inference backends like llama.cpp/Ollama.

---

## 3. Vector Database: Qdrant

### Decision
Use **Qdrant** as the vector search engine, running as an independent Docker container with persistent disk storage.

### Rationale
- **High-Performance Rust Core**: Fast vector indexing (HNSW) and filtering with low resource consumption.
- **Rich Payload Filtering**: Allows arbitrary JSON metadata payloads with indexed fields, enabling efficient document-level filtering, chunk deduplication, and cascading deletions by `document_id`.
- **First-Class Python SDK**: Robust `qdrant-client` with both synchronous and asynchronous support.
- **Persistence**: Vectors and payloads persist reliably across container restarts without complex backup procedures.

### Alternatives Considered
- *Chroma*: Less mature server/client architecture, historical SQLite locking issues in concurrent async setups.
- *pgvector*: Strong option, but separating vector search into Qdrant keeps relational transaction pools dedicated to business and conversation queries without competing for database buffers.

---

## 4. SQL Validation: SQLGlot AST vs. Regex / LLM Self-Validation

### Decision
Enforce security in the SQL Agent via **SQLGlot AST Parsing & Recursive Analysis**, augmented with a restricted PostgreSQL `readonly_user` database role.

### Rationale
- **Semantic AST Verification**: Regex or string-matching (`contains('DROP')`) is trivial to bypass using comments (`--`), string encodings, or nested CTEs. SQLGlot parses the exact Abstract Syntax Tree (AST), ensuring:
  1. Root node is strictly `exp.Select`.
  2. No descendant nodes of type `exp.Insert`, `exp.Update`, `exp.Delete`, `exp.Drop`, `exp.Alter`, `exp.Create`, `exp.Truncate`.
  3. No dangerous functions (`pg_sleep`, `pg_read_file`, `copy`).
  4. Only whitelisted business tables are queried.
- **Defense in Depth**: Even if a zero-day bypass existed in AST parsing, the PostgreSQL database user executing the query only has `SELECT` grants on specific business tables and a strict `statement_timeout`.

### Alternatives Considered
- *Regex matching*: Fundamentally insecure against SQL injection and obfuscated queries.
- *LLM self-validation (asking LLM "Is this query safe?")*: Hallucination-prone, easily manipulated via prompt injection.

---

## 5. Workflow Orchestration: LangGraph

### Decision
Use **LangGraph** to construct a deterministic state machine for multi-turn query handling, intent routing, and branch coordination.

### Rationale
- **Stateful Control Flow**: LangGraph provides explicit, strongly typed graph state (`AssistantState`), cyclic graph capabilities (bounded retry loops for SQL correction), and conditional branch routing.
- **True Fan-Out / Fan-In**: Seamlessly supports the "Combined" query intent, running RAG retrieval and SQL generation concurrently via `asyncio.gather` and synthesizing both result streams in an aggregation node.
- **Inspectability**: Every transition, node input, and output is traceable, simplifying debugging and evaluation.

### Alternatives Considered
- *Linear LangChain Chains / LCEL*: Lack fine-grained state loops, conditional retries, and parallel branch merging.
- *Autogen / CrewAI*: Too non-deterministic and heavy for a structured enterprise data assistant requiring strict control over tool execution.

---

## 6. Conversation Persistence: PostgreSQL

### Decision
Persist conversations and messages in PostgreSQL relational tables (`conversations`, `messages`).

### Rationale
- **ACID Transactions & Relational Integrity**: Guarantees durability, cascading cleanup on conversation deletion, and straightforward indexing by `conversation_id` and `created_at`.
- **Zero Extra Infrastructure**: PostgreSQL is already part of the infrastructure stack for the business database, avoiding the operational overhead of adding Redis or MongoDB.
- **Auditability**: Enables SQL-based reporting on conversation history, query latency, and assistant performance.

---

## 7. Document Parsers: PyMuPDF & python-docx

### Decision
Use **PyMuPDF (`fitz`)** for PDF extraction, **`python-docx`** for Word files, and native Python for Text/Markdown.

### Rationale
- **Speed & Accuracy**: PyMuPDF is orders of magnitude faster than PyPDF2/pypdf and accurately preserves page numbers, which are critical for precise RAG source attribution.
- **No Heavy OCR Overhead**: Extracts native text streams cleanly while remaining lightweight.
