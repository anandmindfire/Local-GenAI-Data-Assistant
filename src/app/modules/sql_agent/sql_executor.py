"""Safe read-only SQL query executor with timeouts and audit logging."""

import asyncio
import logging
import time
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import SQLExecutionFailureException
from app.domain.models.sql import SQLQueryResult
from app.infrastructure.database.connection import readonly_db_context
from app.modules.sql_agent.query_logger import log_sql_execution

logger = logging.getLogger(__name__)


def serialize_db_value(val: Any) -> Any:
    """Convert non-JSON serializable database values (Decimals, datetimes) to primitives."""
    if isinstance(val, datetime | date):
        return val.isoformat()
    elif isinstance(val, Decimal):
        return float(val)
    return val


class SQLExecutor:
    """Executes validated SELECT queries against the read-only database connection with strict timeouts."""

    def __init__(self, timeout_seconds: float = 5.0) -> None:
        self.timeout_seconds = timeout_seconds

    async def execute(
        self,
        sanitized_sql: str,
        session: AsyncSession | None = None,
    ) -> SQLQueryResult:
        """Execute a sanitized query and return structured SQLQueryResult."""
        start_time = time.perf_counter()

        if session is not None:
            return await self._run_query(sanitized_sql, session, start_time)

        # Use the restricted read-only context
        async with readonly_db_context() as ro_session:
            return await self._run_query(sanitized_sql, ro_session, start_time)

    async def _run_query(
        self,
        sanitized_sql: str,
        session: AsyncSession,
        start_time: float,
    ) -> SQLQueryResult:
        try:
            # Wrap execution with asyncio.wait_for to enforce strict client-side timeout
            result = await asyncio.wait_for(
                session.execute(text(sanitized_sql)),
                timeout=self.timeout_seconds,
            )

            columns = list(result.keys())
            rows_raw = result.fetchall()
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Serialize row data
            rows: list[dict[str, Any]] = []
            for r in rows_raw:
                row_dict = {
                    col: serialize_db_value(val) for col, val in zip(columns, r, strict=False)
                }
                rows.append(row_dict)

            # Audit log
            log_sql_execution(
                sql=sanitized_sql,
                duration_ms=duration_ms,
                status="SUCCESS",
                row_count=len(rows),
            )

            return SQLQueryResult(
                columns=columns,
                rows=rows,
                row_count=len(rows),
                execution_duration_ms=round(duration_ms, 2),
                truncated=len(rows) >= settings.database_pool_size,
            )

        except TimeoutError as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            log_sql_execution(
                sql=sanitized_sql,
                duration_ms=duration_ms,
                status="TIMEOUT",
                error_message="Query exceeded execution timeout limit.",
                error_category="QUERY_TIMEOUT",
            )
            raise SQLExecutionFailureException(
                f"SQL query exceeded statement timeout of {self.timeout_seconds}s.",
                details={"sql": sanitized_sql, "timeout": self.timeout_seconds},
            ) from e

        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            error_str = str(e)
            log_sql_execution(
                sql=sanitized_sql,
                duration_ms=duration_ms,
                status="EXECUTION_FAILED",
                error_message=error_str,
                error_category="DATABASE_EXECUTION_ERROR",
            )
            raise SQLExecutionFailureException(
                f"Database query execution failed: {error_str}",
                details={"sql": sanitized_sql, "error": error_str},
            ) from e
