# Multi-stage Dockerfile for Local GenAI Data Assistant
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install virtualenv and build dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY pyproject.toml README.md ./
COPY src/ ./src/

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

# Final runtime image
FROM python:3.12-slim AS runner

WORKDIR /app

# Install runtime dependencies for psycopg2 and tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy virtualenv from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONPATH="/app/src:$PYTHONPATH"
ENV PYTHONUNBUFFERED=1

# Copy source code and application assets
COPY src/ /app/src/
COPY data/ /app/data/
COPY scripts/ /app/scripts/
COPY alembic.ini /app/alembic.ini
COPY alembic/ /app/alembic/

# Create non-root application user
RUN groupadd -r genai && useradd -r -g genai -d /app -s /sbin/nologin genai && \
    chown -R genai:genai /app

USER genai

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
