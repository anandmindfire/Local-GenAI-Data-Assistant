"""FastAPI application entrypoint with lifecycle management and middleware."""

import logging
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.api.exception_handlers import register_exception_handlers
from app.api.routes import chat, documents, health
from app.core.config import settings
from app.core.logging import configure_logging, correlation_id_ctx
from app.infrastructure.database.connection import close_database, init_tables
from app.infrastructure.vector_store.collections import init_collections
from app.infrastructure.vector_store.qdrant_client import close_qdrant_client

# Configure root logger
configure_logging(level=settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup and shutdown lifecycle manager."""
    logger.info(f"Starting {settings.app_name} in {settings.app_env} mode...")

    # Attempt to initialize database tables
    try:
        await init_tables()
    except Exception as e:
        logger.warning(f"Database table initialization deferred (dependency may be starting): {e}")

    # Attempt to initialize Qdrant collections
    try:
        await init_collections()
    except Exception as e:
        logger.warning(
            f"Qdrant collection initialization deferred (dependency may be starting): {e}"
        )

    yield

    # Shutdown
    logger.info("Initiating graceful shutdown...")
    await close_database()
    await close_qdrant_client()
    logger.info("Shutdown complete.")


app = FastAPI(
    title="Local GenAI Data Assistant API",
    description=(
        "Production-grade local assistant for unstructured documents and relational databases."
    ),
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next) -> Response:
    """Ensure every HTTP request has a correlation ID for end-to-end traceability."""
    correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
    token = correlation_id_ctx.set(correlation_id)
    try:
        response: Response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        return response
    finally:
        correlation_id_ctx.reset(token)


# Register centralized exception handlers
register_exception_handlers(app)

# Include API routers with versioned prefix (/api/v1)
app.include_router(health.router, prefix=settings.api_prefix)
app.include_router(chat.router, prefix=settings.api_prefix)
app.include_router(documents.router, prefix=settings.api_prefix)


@app.get("/", tags=["Root"])
async def root():
    """Root redirect / information endpoint."""
    return {
        "name": settings.app_name,
        "version": "0.1.0",
        "docs": "/docs",
        "health": f"{settings.api_prefix}/health",
    }
