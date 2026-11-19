VENV ?= .venv
BIN = $(VENV)/bin

# Auto-detect virtualenv binaries if present, otherwise fall back to system PATH
PYTHON := $(if $(wildcard $(BIN)/python),$(BIN)/python,python3)
PIP := $(if $(wildcard $(BIN)/pip),$(BIN)/pip,pip)
UVICORN := $(if $(wildcard $(BIN)/uvicorn),$(BIN)/uvicorn,uvicorn)
STREAMLIT := $(if $(wildcard $(BIN)/streamlit),$(BIN)/streamlit,streamlit)
PYTEST := $(if $(wildcard $(BIN)/pytest),$(BIN)/pytest,pytest)
RUFF := $(if $(wildcard $(BIN)/ruff),$(BIN)/ruff,ruff)
ALEMBIC := $(if $(wildcard $(BIN)/alembic),$(BIN)/alembic,alembic)

.PHONY: help install run ui test lint format migrate seed ingest docker-build docker-up docker-down

help:
	@echo "Local GenAI Assistant: Developer Commands"
	@echo "  make install       Install project dependencies into virtual environment"
	@echo "  make run           Run local FastAPI development server"
	@echo "  make ui            Run Streamlit chat UI"
	@echo "  make test          Run full Pytest test suite"
	@echo "  make lint          Run Ruff linter"
	@echo "  make format        Format code with Ruff"
	@echo "  make migrate       Apply database migrations via Alembic"
	@echo "  make seed          Seed local database with realistic business data"
	@echo "  make ingest        Batch ingest all documents from data/documents/"
	@echo "  make docker-build  Build Docker Compose services"
	@echo "  make docker-up     Start all Docker Compose services"
	@echo "  make docker-down   Stop and remove Docker Compose containers"

install:
	$(PIP) install -e ".[dev]"

run:
	$(UVICORN) app.main:app --host 0.0.0.0 --port 8000 --reload

ui:
	$(STREAMLIT) run frontend/app.py --server.port 8501

test:
	$(PYTEST) --cov=app --cov-report=term-missing

lint:
	$(RUFF) check .

format:
	$(RUFF) format . && $(RUFF) check --fix .

migrate:
	$(ALEMBIC) upgrade head

seed:
	$(PYTHON) scripts/seed_database.py

ingest:
	$(PYTHON) scripts/ingest_documents.py

docker-build:
	docker compose build

docker-up:
	docker compose up -d

docker-down:
	docker compose down
