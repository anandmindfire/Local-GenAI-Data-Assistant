## 📋 Summary of Changes

<!-- Provide a concise description of the motivation and high-level technical changes in this PR. -->

---

## 🏷️ Type of Change

- [ ] 🚀 **New Feature** (`feat`) - Adds new capability or user-facing feature
- [ ] 🐛 **Bug Fix** (`fix`) - Fixes an issue or defect
- [ ] ⚡ **Performance Improvement** (`perf`) - Reduces latency or memory consumption
- [ ] ♻️ **Refactoring** (`refactor`) - Code improvement without behavior changes
- [ ] 🔒 **Security Enhancement** (`security`) - Hardens access control, sanitization, or validation
- [ ] 📝 **Documentation** (`docs`) - Updates documentation, guides, or specifications
- [ ] 🧪 **Testing** (`test`) - Adds or fixes automated test suites
- [ ] 🔧 **Chore / Build** (`chore` / `build` / `ci`) - Tooling, CI/CD, or dependency updates

---

## 🎯 Target Domain(s) Affected

- [ ] **Unstructured Documents (RAG)** - Parsing, embedding (`nomic-embed-text`), Qdrant vector retrieval, citation generation
- [ ] **Structured Relational (NL2SQL)** - Schema introspection, SQL generation, AST validation (`sqlglot`), execution, result synthesis
- [ ] **Multi-Source Orchestration** - LangGraph state machine, intent router, parallel fan-out, answer aggregation
- [ ] **Conversational Memory** - Session tracking, question contextualization, PostgreSQL persistence
- [ ] **FastAPI Backend** - REST routes (`/api/v1/chat`, `/api/v1/documents`, `/api/v1/health`), exception handling, middleware
- [ ] **Streamlit Presentation** - Chat UI, dataframe rendering, document upload interface, session controls
- [ ] **Infrastructure & Tooling** - Docker Compose, local Ollama models, pre-commit hooks, CI/CD

---

## 🔒 Privacy & Security Checklist

- [ ] **100% Local**: Confirmed no external cloud API dependencies (OpenAI, Anthropic, Google Cloud) or outbound network leaks were introduced.
- [ ] **SQL Injection Defense**: Confirmed all new database operations are strictly read-only and validated via AST parsing where applicable.
- [ ] **Input Sanitization**: Confirmed all file inputs and user messages are sanitized against path traversal or malicious injection.
- [ ] **Credential Safety**: Confirmed no secrets, tokens, or environment keys are committed in code.

---

## ✅ Quality & Verification Checklist

- [ ] Code formatted with Ruff (`make format`)
- [ ] Code linted with Ruff with zero errors (`make lint`)
- [ ] All automated tests pass (`make test`)
- [ ] Security scans pass with zero findings (`make security`)
- [ ] Pre-commit hooks pass on all staged files (`make hooks-run`)
- [ ] Commit messages follow the [Conventional Commits specification](https://www.conventionalcommits.org/)

---

## 📸 Screenshots / Output Logs (Optional)

<!-- Attach terminal outputs, Swagger UI snapshots, or Streamlit interface screenshots if applicable -->
