"""SQLGlot AST-based SQL Validator enforcing strict read-only execution and table whitelisting."""

import logging

import sqlglot
from sqlglot import exp

from app.core.constants import ALLOWED_BUSINESS_TABLES
from app.domain.models.sql import SQLValidationResult

logger = logging.getLogger(__name__)

# Dangerous PostgreSQL functions that could be leveraged for DoS or exfiltration
DANGEROUS_FUNCTIONS = frozenset(
    {
        "pg_sleep",
        "pg_read_file",
        "pg_read_binary_file",
        "pg_ls_dir",
        "pg_stat_file",
        "copy",
        "current_setting",
        "set_config",
        "inet_client_addr",
        "inet_server_addr",
        "lo_import",
        "lo_export",
        "query_to_xml",
        "dblink",
    }
)


class SQLValidator:
    """Validates SQL query strings against AST rules ensuring strict read-only safety."""

    def __init__(
        self,
        allowed_tables: frozenset[str] = ALLOWED_BUSINESS_TABLES,
        max_row_limit: int = 100,
    ) -> None:
        self.allowed_tables = {t.lower() for t in allowed_tables}
        self.max_row_limit = max_row_limit

    def validate(self, sql_query: str) -> SQLValidationResult:
        """Parse and recursively validate the SQL AST."""
        if not sql_query or not sql_query.strip():
            return SQLValidationResult(
                is_valid=False,
                error_message="SQL query is empty.",
                error_category="EMPTY_QUERY",
            )

        raw_sql = sql_query.strip().rstrip(";")

        # 1. Parse using SQLGlot (Postgres dialect)
        try:
            parsed_expressions = sqlglot.parse(raw_sql, read="postgres")
        except Exception as e:
            return SQLValidationResult(
                is_valid=False,
                error_message=f"SQL syntax error: {e}",
                error_category="SYNTAX_ERROR",
            )

        if not parsed_expressions:
            return SQLValidationResult(
                is_valid=False,
                error_message="Failed to parse any valid SQL statement.",
                error_category="PARSE_ERROR",
            )

        # 2. Reject multi-statement queries
        if len(parsed_expressions) > 1:
            return SQLValidationResult(
                is_valid=False,
                error_message="Multiple statements are strictly forbidden. Submit a single SELECT query.",
                error_category="MULTIPLE_STATEMENTS",
            )

        statement = parsed_expressions[0]

        # 3. Enforce that root statement is strictly a SELECT
        if not isinstance(statement, exp.Select):
            return SQLValidationResult(
                is_valid=False,
                error_message=f"Only SELECT queries are permitted. Got statement type: {type(statement).__name__}",
                error_category="NON_SELECT_ROOT",
            )

        # 4. Recursively check AST for forbidden mutations or DDL
        forbidden_nodes = (
            exp.Insert,
            exp.Update,
            exp.Delete,
            exp.Drop,
            exp.Alter,
            exp.Create,
            exp.Command,
            exp.Transaction,
            exp.Commit,
            exp.Rollback,
        )

        for node in statement.walk():
            if isinstance(node, forbidden_nodes):
                return SQLValidationResult(
                    is_valid=False,
                    error_message=f"Disallowed operation detected: {type(node).__name__}. Database is read-only.",
                    error_category="FORBIDDEN_OPERATION",
                )

            # Check for data-modifying CTEs
            if isinstance(node, exp.CTE):
                if not isinstance(node.this, exp.Select):
                    return SQLValidationResult(
                        is_valid=False,
                        error_message="Data-modifying Common Table Expressions (CTEs) are forbidden.",
                        error_category="DATA_MODIFYING_CTE",
                    )

            # Check for dangerous functions
            if isinstance(node, exp.Anonymous):
                func_name = node.name.lower()
                if func_name in DANGEROUS_FUNCTIONS:
                    return SQLValidationResult(
                        is_valid=False,
                        error_message=f"Dangerous function '{func_name}' is forbidden.",
                        error_category="FORBIDDEN_FUNCTION",
                    )

        # 5. Validate table references
        tables_referenced = set()
        for table in statement.find_all(exp.Table):
            table_name = table.name.lower()
            if table_name:
                tables_referenced.add(table_name)
                if table_name not in self.allowed_tables:
                    return SQLValidationResult(
                        is_valid=False,
                        error_message=f"Table '{table_name}' is not in the authorized business schema.",
                        error_category="UNAUTHORIZED_TABLE",
                    )

        if not tables_referenced:
            # Query might be selecting standalone literals (e.g. SELECT 1)
            pass

        # 6. Enforce LIMIT clause
        current_limit = statement.args.get("limit")
        if current_limit is None:
            statement = statement.limit(self.max_row_limit)
        else:
            try:
                limit_val = int(current_limit.expression.name)
                if limit_val > self.max_row_limit:
                    statement.set("limit", None)
                    statement = statement.limit(self.max_row_limit)
            except Exception:
                statement.set("limit", None)
                statement = statement.limit(self.max_row_limit)

        sanitized_sql = statement.sql(dialect="postgres")

        return SQLValidationResult(
            is_valid=True,
            sanitized_sql=sanitized_sql,
            tables_referenced=sorted(tables_referenced),
        )
