"""Natural language to SQL generator using local LLM."""

import logging
import re

from langchain_core.messages import HumanMessage, SystemMessage

from app.infrastructure.llm.chat_model import LocalChatService, get_chat_service

logger = logging.getLogger(__name__)

SQL_GENERATOR_SYSTEM_PROMPT = """You are a senior PostgreSQL database engineer.
Your task is to write a single, optimal, read-only PostgreSQL SELECT query to answer the user's question based strictly on the provided schema.

DATABASE RULES:
1. Generate ONLY a single SELECT query.
2. NEVER generate INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE, or multi-statement scripts.
3. Only query tables defined in the schema.
4. When filtering by dates, use PostgreSQL standard timestamp expressions (e.g. NOW() - INTERVAL '1 month').
5. Join tables properly using defined foreign keys.
6. When calculating revenue, use SUM(total_amount) from orders or SUM(subtotal) from order_items.
7. For refunds, sum refund_amount from refunds table or link to orders.
8. Output ONLY the raw SQL query. Do not wrap in markdown quotes if possible, or use standard ```sql code blocks. Do not include conversational explanations."""


class SQLGenerator:
    """Generates schema-aware PostgreSQL queries from natural language questions."""

    def __init__(self, chat_service: LocalChatService | None = None) -> None:
        self.chat_service = chat_service or get_chat_service()

    async def generate_sql(
        self,
        question: str,
        schema_text: str,
        previous_error: str | None = None,
    ) -> str:
        """Generate a SQL query from natural language question with optional error feedback."""
        prompt_content = f"DATABASE SCHEMA:\n{schema_text}\n\nUSER QUESTION: {question}"

        if previous_error:
            prompt_content += (
                f"\n\nNOTE: A previous query attempt failed with the following error:\n"
                f"{previous_error}\n"
                f"Please correct the error and generate a valid PostgreSQL SELECT query."
            )

        messages = [
            SystemMessage(content=SQL_GENERATOR_SYSTEM_PROMPT),
            HumanMessage(content=prompt_content),
        ]

        raw_output = await self.chat_service.ainvoke(messages)
        return self._clean_sql_output(raw_output)

    def _clean_sql_output(self, raw_output: str) -> str:
        """Extract clean SQL string from LLM output, removing markdown fences and whitespace."""
        text = raw_output.strip()

        # Extract content from markdown ```sql ... ``` or ``` ... ```
        sql_match = re.search(r"```(?:sql)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
        if sql_match:
            text = sql_match.group(1).strip()

        # Remove trailing semicolon
        return text.rstrip(";")
