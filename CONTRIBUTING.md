# Contributing to Local GenAI Data Assistant

Thank you for your interest in contributing to the **Local GenAI Data Assistant**! We welcome bug reports, documentation enhancements, security improvements, and feature contributions.

This project is built with a strict **local-first, privacy-by-design architecture**. All contributions must uphold the principle that enterprise data never leaks to external cloud APIs.

---

## Table of Contents
- [Code of Conduct & Philosophy](#code-of-conduct--philosophy)
- [Prerequisites](#prerequisites)
- [Development Setup](#development-setup)
- [Developer Workflow & Makefile](#developer-workflow--makefile)
- [Commit Message Guidelines (Conventional Commits)](#commit-message-guidelines-conventional-commits)
- [Code Style & Quality Standards](#code-style--quality-standards)
- [Testing & Security Requirements](#testing--security-requirements)
- [Pull Request Process](#pull-request-process)

---

## Code of Conduct & Philosophy

1. **100% Local Execution**: All models (chat, embeddings) and datastores (PostgreSQL, Qdrant) must execute locally within Docker or on the host machine. Never introduce external API calls (e.g. OpenAI, Anthropic, Google Cloud AI) to the application runtime.
2. **Defensive by Default**: All database interactions must use AST-validated read-only queries with strict timeouts and limits. All user uploads must be sanitized.
3. **Respect & Collaboration**: Treat all contributors and reviewers with professionalism and constructive feedback.

---

## Prerequisites

Ensure you have the following installed on your development machine:
- **Python**: `>= 3.12`
- **Docker & Docker Compose**: Docker Desktop with Compose v2
- **Git**: `>= 2.30`
- **Make**: Standard GNU Make

---

## Development Setup

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/<your-username>/local-llm-rag.git
   cd local-llm-rag
   ```

2. **Create and Activate Virtual Environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install Dependencies (including development tooling)**:
   ```bash
   make install
   ```

4. **Install Python-Native Git Hooks**:
   ```bash
   make hooks-install
   ```
   *This activates both `pre-commit` (linting, formatting, security) and `commit-msg` (conventional commits validation).*

5. **Start Infrastructure Services**:
   ```bash
   make docker-up
   ```
   *Starts PostgreSQL (`genai-postgres`), Qdrant (`genai-qdrant`), and Ollama (`genai-ollama`).*

6. **Pull Local Models into Ollama**:
   ```bash
   bash scripts/download_models.sh
   ```
   *Downloads `qwen3:1.7b` (chat/reasoning) and `nomic-embed-text` (embeddings).*

7. **Migrate and Seed Relational Database**:
   ```bash
   make migrate
   make seed
   ```

8. **Batch Ingest Sample Enterprise Documents**:
   ```bash
   make ingest
   ```

---

## Developer Workflow & Makefile

We provide convenient `make` commands to streamline local development:

| Command | Action |
| :--- | :--- |
| `make run` | Starts FastAPI backend server with hot reloading on `http://localhost:8000` |
| `make ui` | Starts Streamlit conversational frontend on `http://localhost:8501` |
| `make test` | Runs the full Pytest test suite with line-by-line coverage metrics |
| `make lint` | Checks code formatting and syntax with Ruff (ESLint alternative) |
| `make format` | Automatically formats Python files with Ruff (Prettier alternative) |
| `make security` | Runs Bandit AST security scanner and pip-audit for CVE vulnerabilities |
| `make hooks-run` | Executes all pre-commit hooks manually against all files in the repository |
| `make docker-build` | Rebuilds Docker images for API and frontend services |
| `make docker-up` | Starts all Docker Compose services in the background |
| `make docker-down` | Gracefully stops and removes all Docker Compose containers |

---

## Commit Message Guidelines (Conventional Commits)

This repository enforces the **[Conventional Commits specification](https://www.conventionalcommits.org/)** via the `conventional-pre-commit` hook. Commits that do not match this specification will be blocked automatically.

### Structure
```text
<type>(<optional scope>): <short description in lowercase or imperative>

[optional body explaining motivation and technical approach]

[optional footer, e.g. Closes #123]
```

### Allowed Types
- **`feat`**: A new user-facing feature or capability.
- **`fix`**: A bug fix.
- **`docs`**: Documentation changes only (e.g., README, architecture docs).
- **`style`**: Formatting, white-space, missing semi-colons (no production code change).
- **`refactor`**: Code restructuring without bug fixes or new features.
- **`perf`**: Performance and latency improvements.
- **`test`**: Adding or correcting unit, integration, or evaluation tests.
- **`build`**: Changes affecting build system or external dependencies.
- **`ci`**: Changes to CI/CD workflows and scripts (`.github/workflows/`).
- **`chore`**: Maintenance tasks, tooling updates, or repository hygiene.
- **`revert`**: Reverting a previous commit.

### Examples
- :white_check_mark: `feat(rag): add multi-format document parser for docx and pdf`
- :white_check_mark: `fix(sql): prevent ambiguous column naming in customer revenue join`
- :white_check_mark: `perf(graph): fast-path intent classifier for sub-millisecond routing`
- :white_check_mark: `docs: update setup instructions for streamilt frontend`
- :x: `added stuff` *(missing type and structure)*
- :x: `Fix: bug in parser` *(type must be lowercase `fix:`)*

---

## Code Style & Quality Standards

1. **Ruff as Linter and Formatter**:
   - We use [Ruff](https://astral.sh/ruff) exclusively. Do not run Flake8, Black, or isort directly.
   - Run `make format` before committing to auto-format code.
   - Line length is configured to **100 characters**.
2. **Type Annotations**:
   - All function signatures, parameters, and return types must include standard Python 3.12 type hints (`int | str`, `list[dict[str, Any]]`).
3. **Pydantic Validation**:
   - All external request and response structures must use Pydantic models for validation.

---

## Testing & Security Requirements

Before opening a pull request, ensure that:
1. **All Tests Pass**:
   ```bash
   make test
   ```
2. **Pre-commit Hooks Pass Cleanly**:
   ```bash
   make hooks-run
   ```
3. **Security Scans Pass with Zero Findings**:
   ```bash
   make security
   ```
   - No high/medium severity findings in Bandit.
   - No known CVEs in `pip-audit`.
4. **Coverage**:
   - Do not decrease overall test coverage. Add unit or integration tests for new features and bug fixes.

---

## Pull Request Process

1. **Create a Topic Branch**:
   ```bash
   git checkout -b feat/your-feature-name
   ```
2. **Make Focused, Atomic Commits**:
   - Keep commits small, logical, and adhering to Conventional Commits.
3. **Verify Locally**:
   - Run `make hooks-run` and `make test`.
4. **Push and Open a Pull Request**:
   - Push your branch to GitHub and open a Pull Request targeting `master`.
   - Complete all sections of the **Pull Request Template**.
5. **Continuous Integration**:
   - Ensure all CI workflow checks pass:
     - `lint-and-format`
     - `test`
     - `security-scan`
     - `docker-build`
6. **Code Review**:
   - Address any reviewer feedback promptly. Once approved, your PR will be squash-merged into `master`.
