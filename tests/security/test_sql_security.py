"""Comprehensive security test suite verifying SQL injection and attack vector rejections."""

import pytest

from app.modules.sql_agent.sql_validator import SQLValidator

validator = SQLValidator()


@pytest.mark.parametrize(
    "attack_sql,expected_category",
    [
        ("DROP TABLE customers CASCADE;", "FORBIDDEN_OPERATION"),
        ("TRUNCATE TABLE orders;", "FORBIDDEN_OPERATION"),
        ("ALTER TABLE products ADD COLUMN leaked_token TEXT;", "FORBIDDEN_OPERATION"),
        ("CREATE TABLE backdoor (id INT);", "FORBIDDEN_OPERATION"),
        ("GRANT ALL ON customers TO public;", "FORBIDDEN_OPERATION"),
        ("REVOKE SELECT ON products FROM genai_readonly;", "FORBIDDEN_OPERATION"),
        ("SELECT * FROM customers; DROP TABLE orders;", "MULTIPLE_STATEMENTS"),
        ("SELECT * FROM customers; DELETE FROM products WHERE 1=1;", "MULTIPLE_STATEMENTS"),
        ("WITH x AS (DELETE FROM customers RETURNING *) SELECT * FROM x;", "FORBIDDEN_OPERATION"),
        (
            "WITH x AS (UPDATE products SET price = 0 RETURNING *) SELECT * FROM x;",
            "FORBIDDEN_OPERATION",
        ),
        (
            "WITH x AS (INSERT INTO orders VALUES (999, 1, NOW(), 'fake', 0) RETURNING *) SELECT * FROM x;",
            "FORBIDDEN_OPERATION",
        ),
        ("SELECT pg_sleep(5);", "FORBIDDEN_FUNCTION"),
        ("SELECT pg_read_file('/etc/passwd');", "FORBIDDEN_FUNCTION"),
        ("SELECT * FROM pg_user;", "UNAUTHORIZED_TABLE"),
        ("SELECT * FROM information_schema.tables;", "UNAUTHORIZED_TABLE"),
        ("SELECT * FROM auth_tokens;", "UNAUTHORIZED_TABLE"),
        ("SELECT * FROM customers -- comment \n; DROP TABLE orders;", "MULTIPLE_STATEMENTS"),
    ],
)
def test_sql_attack_rejection(attack_sql: str, expected_category: str):
    """Verify that every dangerous or unauthorized SQL construct is categorically blocked."""
    result = validator.validate(attack_sql)
    assert result.is_valid is False, f"Expected attack to be rejected: {attack_sql}"
    assert result.error_category is not None
