"""Unit tests for SQLAgentService execution and bounded correction loop."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.exceptions import SQLValidationFailureException
from app.infrastructure.database.models.base import Base
from app.modules.sql_agent.service import SQLAgentService
from app.modules.sql_agent.sql_executor import SQLExecutor
from app.modules.sql_agent.sql_generator import SQLGenerator
from app.modules.sql_agent.sql_validator import SQLValidator
from scripts.seed_database import seed_data


@pytest.fixture
async def sqlite_business_db():
    """Create in-memory SQLite business database with seed data."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_maker() as session:
        await seed_data(session)
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_sql_agent_successful_query(sqlite_business_db, mocker):
    """Test SQL agent execution with valid question and seed data."""
    mock_chat = mocker.AsyncMock()
    # First call: SQL generation; Second call: natural language synthesis
    mock_chat.ainvoke.side_effect = [
        "SELECT first_name, last_name, email FROM customers ORDER BY customer_id LIMIT 3",
        "The first 3 customers are Alice Smith, Bob Jones, and Charlie Brown.",
    ]

    generator = SQLGenerator(chat_service=mock_chat)
    executor = SQLExecutor()
    validator = SQLValidator()

    service = SQLAgentService(
        generator=generator,
        validator=validator,
        executor=executor,
        chat_service=mock_chat,
    )

    resp = await service.execute_question("List 3 customers", session=sqlite_business_db)
    assert resp.generated_sql is not None
    assert "LIMIT 3" in resp.generated_sql
    assert resp.query_result.row_count == 3
    assert len(resp.query_result.rows) == 3
    assert resp.query_result.rows[0]["first_name"] == "Alice"
    assert "Alice Smith" in resp.answer


@pytest.mark.asyncio
async def test_sql_agent_correction_loop_recovers(sqlite_business_db, mocker):
    """Test that correction loop retries on initial validation failure and succeeds."""
    mock_chat = mocker.AsyncMock()
    # 1st attempt: returns illegal DROP; 2nd attempt: returns valid SELECT; 3rd: answer synthesis
    mock_chat.ainvoke.side_effect = [
        "DROP TABLE customers;",
        "SELECT COUNT(*) AS total_customers FROM customers",
        "There are 7 customers in the database.",
    ]

    generator = SQLGenerator(chat_service=mock_chat)
    executor = SQLExecutor()
    validator = SQLValidator()

    service = SQLAgentService(
        generator=generator,
        validator=validator,
        executor=executor,
        chat_service=mock_chat,
        max_retries=2,
    )

    resp = await service.execute_question("How many customers?", session=sqlite_business_db)
    assert "SELECT COUNT(*)" in resp.generated_sql
    assert resp.query_result.row_count == 1
    assert resp.query_result.rows[0]["total_customers"] == 7


@pytest.mark.asyncio
async def test_sql_agent_exceeds_max_retries_raises(mocker):
    """Test that persisting validation errors raises SQLValidationFailureException."""
    mock_chat = mocker.AsyncMock()
    mock_chat.ainvoke.return_value = "DELETE FROM orders;"

    generator = SQLGenerator(chat_service=mock_chat)
    executor = SQLExecutor()
    validator = SQLValidator()

    service = SQLAgentService(
        generator=generator,
        validator=validator,
        executor=executor,
        chat_service=mock_chat,
        max_retries=1,
    )

    with pytest.raises(SQLValidationFailureException) as exc_info:
        await service.execute_question("Clear orders")
    assert "failed security validation" in str(exc_info.value)
