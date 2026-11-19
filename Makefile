.PHONY: help install run test lint format migrate seed ingest docker-build docker-up docker-down

help:
	@echo "Local GenAI Assistant: Developer Commands"
	@echo "  make install       Install project dependencies into virtual environment"
	@echo "  make run           Run local FastAPI development server"
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
	pip install -e ".[dev]"

run:
	uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

test:
	pytest --cov=app --cov-report=term-missing

lint:
	ruff check .

format:
	ruff format . && ruff check --fix .

migrate:
	alembic upgrade head

seed:
	python scripts/seed_database.py

ingest:
	python scripts/ingest_documents.py

docker-build:
	docker compose build

docker-up:
	docker compose up -d

docker-down:
	docker compose down
