"""Database connection management and session factories using SQLAlchemy 2.0."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings
from app.core.exceptions import DatabaseUnavailableException
from app.infrastructure.database.models.base import Base

logger = logging.getLogger(__name__)

# Application async engine (Read/Write)
_async_engine: AsyncEngine | None = None
_async_session_factory: async_sessionmaker[AsyncSession] | None = None

# Restricted SQL Agent async engine (Read-Only)
_readonly_async_engine: AsyncEngine | None = None
_readonly_async_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Get or create the primary application async database engine."""
    global _async_engine
    if _async_engine is None:
        _async_engine = create_async_engine(
            settings.async_database_url,
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
            pool_pre_ping=True,
            echo=False,
        )
    return _async_engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Get or create the session factory for the primary application database."""
    global _async_session_factory
    if _async_session_factory is None:
        _async_session_factory = async_sessionmaker(
            bind=get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
    return _async_session_factory


def get_readonly_engine() -> AsyncEngine:
    """Get or create the restricted read-only async database engine for SQL Agent."""
    global _readonly_async_engine
    if _readonly_async_engine is None:
        _readonly_async_engine = create_async_engine(
            settings.readonly_async_database_url,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
            echo=False,
        )
    return _readonly_async_engine


def get_readonly_session_factory() -> async_sessionmaker[AsyncSession]:
    """Get or create the session factory for the read-only SQL agent."""
    global _readonly_async_session_factory
    if _readonly_async_session_factory is None:
        _readonly_async_session_factory = async_sessionmaker(
            bind=get_readonly_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
    return _readonly_async_session_factory


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for obtaining an application database session."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def db_context() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for obtaining an application database session outside API routes."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def readonly_db_context() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for obtaining a read-only session for the SQL agent."""
    session_factory = get_readonly_session_factory()
    async with session_factory() as session:
        try:
            yield session
        finally:
            await session.rollback()


async def check_database_health() -> bool:
    """Verify PostgreSQL connectivity via a lightweight ping."""
    from sqlalchemy import text

    try:
        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.warning(f"Database health check failed: {e}")
        return False


async def init_tables() -> None:
    """Create all registered tables if they do not exist (useful for testing and init)."""
    try:
        engine = get_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database tables: {e}")
        raise DatabaseUnavailableException(
            f"Could not initialize database tables: {e}",
            details={"error": str(e)},
        ) from e


async def close_database() -> None:
    """Dispose of engine connection pools on shutdown."""
    global _async_engine, _readonly_async_engine
    if _async_engine:
        await _async_engine.dispose()
        _async_engine = None
    if _readonly_async_engine:
        await _readonly_async_engine.dispose()
        _readonly_async_engine = None
    logger.info("Database connection pools closed")
