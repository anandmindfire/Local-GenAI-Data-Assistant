"""SQL Agent Evaluation benchmark testing natural language questions against database outcomes."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.infrastructure.database.models.base import Base
from app.modules.sql_agent.service import SQLAgentService
from app.modules.sql_agent.sql_executor import SQLExecutor
from app.modules.sql_agent.sql_generator import SQLGenerator
from app.modules.sql_agent.sql_validator import SQLValidator
from scripts.seed_database import seed_data


@pytest.fixture
async def evaluation_database():
    """Create in-memory SQLite database populated with seed benchmark data."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_maker() as session:
        await seed_data(session)
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_eval_top_customers_by_revenue(evaluation_database, mocker):
    """Benchmark: Top customers by revenue."""
    mock_chat = mocker.AsyncMock()
    mock_chat.ainvoke.side_effect = [
        """
        SELECT c.first_name, c.last_name, SUM(o.total_amount) AS revenue
        FROM customers c
        JOIN orders o ON c.customer_id = o.customer_id
        WHERE o.status = 'completed'
        GROUP BY c.customer_id, c.first_name, c.last_name
        ORDER BY revenue DESC
        LIMIT 5
        """,
        "The top customer by revenue is Alice Smith followed by Bob Jones.",
    ]

    service = SQLAgentService(
        generator=SQLGenerator(chat_service=mock_chat),
        validator=SQLValidator(),
        executor=SQLExecutor(),
        chat_service=mock_chat,
    )

    resp = await service.execute_question(
        "Who are the top 5 customers by revenue?", session=evaluation_database
    )
    assert resp.query_result.row_count > 0
    top_customer = resp.query_result.rows[0]
    assert top_customer["first_name"] == "Alice"
    assert top_customer["revenue"] > 3000


@pytest.mark.asyncio
async def test_eval_low_stock_products(evaluation_database, mocker):
    """Benchmark: Products with stock below 10."""
    mock_chat = mocker.AsyncMock()
    mock_chat.ainvoke.side_effect = [
        "SELECT product_id, name, stock_quantity FROM products WHERE stock_quantity < 10 ORDER BY stock_quantity ASC",
        "There are 3 products with stock below 10: Ergonomic Precision Mouse, 4K Monitor, and Smartphone.",
    ]

    service = SQLAgentService(
        generator=SQLGenerator(chat_service=mock_chat),
        validator=SQLValidator(),
        executor=SQLExecutor(),
        chat_service=mock_chat,
    )

    resp = await service.execute_question(
        "Which products have stock below 10?", session=evaluation_database
    )
    assert resp.query_result.row_count == 3
    # Check that lowest stock is Ergonomic Precision Mouse (stock 4)
    assert resp.query_result.rows[0]["name"] == "Ergonomic Precision Mouse"
    assert resp.query_result.rows[0]["stock_quantity"] == 4


@pytest.mark.asyncio
async def test_eval_total_refunds_processed(evaluation_database, mocker):
    """Benchmark: Total refund amounts processed."""
    mock_chat = mocker.AsyncMock()
    mock_chat.ainvoke.side_effect = [
        "SELECT SUM(refund_amount) AS total_refunds FROM refunds WHERE status = 'processed'",
        "Total processed refunds equal $1,349.99.",
    ]

    service = SQLAgentService(
        generator=SQLGenerator(chat_service=mock_chat),
        validator=SQLValidator(),
        executor=SQLExecutor(),
        chat_service=mock_chat,
    )

    resp = await service.execute_question(
        "How much was refunded in total?", session=evaluation_database
    )
    assert resp.query_result.row_count == 1
    total = resp.query_result.rows[0]["total_refunds"]
    assert total == 1349.99
