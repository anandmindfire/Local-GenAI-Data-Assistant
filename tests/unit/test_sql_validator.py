"""Unit tests for SQLGlot AST validation."""

from app.modules.sql_agent.sql_validator import SQLValidator


def test_validator_valid_select():
    """Verify standard SELECT queries pass validation."""
    validator = SQLValidator()
    sql = "SELECT customer_id, first_name, email FROM customers WHERE city = 'New York'"
    res = validator.validate(sql)
    assert res.is_valid is True
    assert res.sanitized_sql is not None
    assert "LIMIT 100" in res.sanitized_sql
    assert "customers" in res.tables_referenced


def test_validator_joins_and_aggregations():
    """Verify joins, group by, and order by work properly."""
    validator = SQLValidator()
    sql = """
    SELECT c.first_name, c.last_name, SUM(o.total_amount) AS total_revenue
    FROM customers c
    JOIN orders o ON c.customer_id = o.customer_id
    GROUP BY c.customer_id, c.first_name, c.last_name
    ORDER BY total_revenue DESC
    LIMIT 5
    """
    res = validator.validate(sql)
    assert res.is_valid is True
    assert set(res.tables_referenced) == {"customers", "orders"}
    assert "LIMIT 5" in res.sanitized_sql


def test_validator_reject_insert():
    """Verify INSERT statements are rejected."""
    validator = SQLValidator()
    sql = "INSERT INTO customers (customer_id, first_name) VALUES (99, 'Hacker')"
    res = validator.validate(sql)
    assert res.is_valid is False
    assert res.error_category in ["NON_SELECT_ROOT", "FORBIDDEN_OPERATION"]


def test_validator_reject_update():
    """Verify UPDATE statements are rejected."""
    validator = SQLValidator()
    sql = "UPDATE products SET price = 0.0 WHERE product_id = 1"
    res = validator.validate(sql)
    assert res.is_valid is False
    assert res.error_category in ["NON_SELECT_ROOT", "FORBIDDEN_OPERATION"]


def test_validator_reject_delete():
    """Verify DELETE statements are rejected."""
    validator = SQLValidator()
    sql = "DELETE FROM orders WHERE order_id = 1"
    res = validator.validate(sql)
    assert res.is_valid is False
    assert res.error_category in ["NON_SELECT_ROOT", "FORBIDDEN_OPERATION"]


def test_validator_reject_drop():
    """Verify DROP TABLE statements are rejected."""
    validator = SQLValidator()
    sql = "DROP TABLE customers"
    res = validator.validate(sql)
    assert res.is_valid is False
    assert res.error_category in ["NON_SELECT_ROOT", "FORBIDDEN_OPERATION"]


def test_validator_reject_multiple_statements():
    """Verify semicolon statement chaining is rejected."""
    validator = SQLValidator()
    sql = "SELECT * FROM customers; DROP TABLE orders;"
    res = validator.validate(sql)
    assert res.is_valid is False
    assert res.error_category == "MULTIPLE_STATEMENTS"


def test_validator_reject_data_modifying_cte():
    """Verify data-modifying CTEs are rejected."""
    validator = SQLValidator()
    sql = "WITH deleted_orders AS (DELETE FROM orders RETURNING *) SELECT * FROM deleted_orders"
    res = validator.validate(sql)
    assert res.is_valid is False
    assert res.error_category in ["FORBIDDEN_OPERATION", "DATA_MODIFYING_CTE"]


def test_validator_reject_dangerous_function():
    """Verify dangerous system functions like pg_sleep are rejected."""
    validator = SQLValidator()
    sql = "SELECT pg_sleep(10)"
    res = validator.validate(sql)
    assert res.is_valid is False
    assert res.error_category == "FORBIDDEN_FUNCTION"


def test_validator_reject_unauthorized_table():
    """Verify querying non-whitelisted tables or schemas is rejected."""
    validator = SQLValidator()
    sql = "SELECT * FROM pg_shadow"
    res = validator.validate(sql)
    assert res.is_valid is False
    assert res.error_category == "UNAUTHORIZED_TABLE"


def test_validator_enforce_max_limit():
    """Verify queries requesting more than max_limit are capped."""
    validator = SQLValidator(max_row_limit=50)
    sql = "SELECT * FROM products LIMIT 500"
    res = validator.validate(sql)
    assert res.is_valid is True
    assert "LIMIT 50" in res.sanitized_sql
