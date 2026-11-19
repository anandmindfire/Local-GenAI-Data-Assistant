"""SQL Agent orchestrator with bounded correction loop and result synthesis."""

import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.core.exceptions import SQLExecutionFailureException, SQLValidationFailureException
from app.domain.models.sql import SQLQueryResult
from app.infrastructure.llm.chat_model import LocalChatService, get_chat_service
from app.modules.sql_agent.query_logger import log_sql_execution
from app.modules.sql_agent.schema_inspector import DatabaseSchemaInspector
from app.modules.sql_agent.sql_executor import SQLExecutor
from app.modules.sql_agent.sql_generator import SQLGenerator
from app.modules.sql_agent.sql_validator import SQLValidator

logger = logging.getLogger(__name__)


class SQLAgentResponse(BaseModel):
    """Response returned by the SQL Agent containing SQL, results, and natural language answer."""

    question: str
    generated_sql: str
    query_result: SQLQueryResult
    answer: str
    execution_metadata: dict[str, Any] = Field(default_factory=dict)


class SQLAgentService:
    """Coordinates schema introspection, generation, AST validation, execution, and synthesis."""

    def __init__(
        self,
        generator: SQLGenerator | None = None,
        validator: SQLValidator | None = None,
        executor: SQLExecutor | None = None,
        inspector: DatabaseSchemaInspector | None = None,
        chat_service: LocalChatService | None = None,
        max_retries: int = 2,
    ) -> None:
        self.generator = generator or SQLGenerator()
        self.validator = validator or SQLValidator()
        self.executor = executor or SQLExecutor()
        self.inspector = inspector or DatabaseSchemaInspector()
        self.chat_service = chat_service or get_chat_service()
        self.max_retries = max_retries

    async def execute_question(
        self,
        question: str,
        session: Any | None = None,
    ) -> SQLAgentResponse:
        """Process a natural language question through the SQL generation and validation loop."""
        schema_text = await self.inspector.get_schema_representation()
        last_error: str | None = None
        candidate_sql = ""
        sanitized_sql = ""
        query_result: SQLQueryResult | None = None

        # Bounded generation and validation correction loop
        for attempt in range(self.max_retries + 1):
            try:
                candidate_sql = await self.generator.generate_sql(
                    question=question,
                    schema_text=schema_text,
                    previous_error=last_error,
                )

                validation_res = self.validator.validate(candidate_sql)
                if not validation_res.is_valid:
                    error_msg = validation_res.error_message or "Validation failed."
                    log_sql_execution(
                        sql=candidate_sql,
                        duration_ms=0.0,
                        status="VALIDATION_FAILED",
                        error_message=error_msg,
                        error_category=validation_res.error_category,
                    )
                    last_error = f"SQL Validation Error: {error_msg}"
                    if attempt < self.max_retries:
                        logger.warning(
                            f"SQL attempt {attempt + 1} failed validation: {error_msg}. Retrying..."
                        )
                        continue
                    raise SQLValidationFailureException(
                        f"Generated query failed security validation: {error_msg}",
                        details={"sql": candidate_sql, "error": error_msg},
                    )

                sanitized_sql = validation_res.sanitized_sql or candidate_sql

                # Execute sanitized query
                query_result = await self.executor.execute(sanitized_sql, session=session)
                break  # Successful execution

            except SQLExecutionFailureException as e:
                last_error = f"Database Execution Error: {e.message}"
                if attempt < self.max_retries:
                    logger.warning(
                        f"SQL execution attempt {attempt + 1} failed: {e.message}. Retrying..."
                    )
                    continue
                raise

        if query_result is None:
            raise SQLExecutionFailureException("Failed to obtain SQL results.")

        # Synthesize natural language answer from query results
        answer = await self._synthesize_answer(question, sanitized_sql, query_result)

        return SQLAgentResponse(
            question=question,
            generated_sql=sanitized_sql,
            query_result=query_result,
            answer=answer,
            execution_metadata={
                "row_count": query_result.row_count,
                "duration_ms": query_result.execution_duration_ms,
            },
        )

    async def _synthesize_answer(
        self,
        question: str,
        sql: str,
        result: SQLQueryResult,
    ) -> str:
        """Synthesize natural language explanation of SQL query results."""
        if result.row_count == 0:
            return "No matching records were found in the database for your query."

        # Limit result preview sent to LLM for synthesis
        rows_preview = result.rows[:20]
        prompt = (
            f"USER QUESTION: {question}\n\n"
            f"EXECUTED SQL: {sql}\n\n"
            f"DATABASE RESULTS (Total {result.row_count} rows):\n"
            f"{rows_preview}\n\n"
            f"Provide a concise, direct natural language answer answering the user's question "
            f"based strictly on the database results above. Mention key numbers, customer names, or products directly."
        )

        messages = [
            SystemMessage(
                content="You are a helpful data analyst explaining relational database results accurately and concisely."
            ),
            HumanMessage(content=prompt),
        ]

        return await self.chat_service.ainvoke(messages)


_sql_agent_service: SQLAgentService | None = None


def get_sql_agent_service() -> SQLAgentService:
    """Get or instantiate singleton SQLAgentService."""
    global _sql_agent_service
    if _sql_agent_service is None:
        _sql_agent_service = SQLAgentService()
    return _sql_agent_service
