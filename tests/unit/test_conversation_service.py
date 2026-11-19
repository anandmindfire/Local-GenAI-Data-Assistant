"""Unit tests for conversation service and isolation."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.domain.models.conversation import MessageRole
from app.infrastructure.database.models.base import Base
from app.modules.conversation.context_builder import ContextualizerService
from app.modules.conversation.service import ConversationService


@pytest.fixture
async def conv_test_session():
    """In-memory SQLite session for testing conversation models."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_maker() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_conversation_creation_and_isolation(conv_test_session):
    """Verify conversations remain strictly isolated by conversation_id."""
    service = ConversationService()

    # Create conv 1
    c1 = await service.get_or_create_conversation(
        "conv_user_1", conv_test_session, title="Session 1"
    )
    assert c1.conversation_id == "conv_user_1"

    # Add message to conv 1
    await service.add_message(
        conversation_id="conv_user_1",
        role=MessageRole.USER,
        content="What is the leave policy?",
        session=conv_test_session,
    )

    # Create conv 2
    c2 = await service.get_or_create_conversation(
        "conv_user_2", conv_test_session, title="Session 2"
    )
    assert c2.conversation_id == "conv_user_2"

    # Add message to conv 2
    await service.add_message(
        conversation_id="conv_user_2",
        role=MessageRole.USER,
        content="Who are the top customers?",
        session=conv_test_session,
    )

    # Verify history of conv 1 does not contain conv 2
    h1 = await service.get_conversation_history("conv_user_1", conv_test_session)
    assert len(h1) == 1
    assert h1[0].content == "What is the leave policy?"

    # Verify history of conv 2 does not contain conv 1
    h2 = await service.get_conversation_history("conv_user_2", conv_test_session)
    assert len(h2) == 1
    assert h2[0].content == "Who are the top customers?"


@pytest.mark.asyncio
async def test_contextualizer_rewrites_follow_up(conv_test_session, mocker):
    """Verify follow-up reference rewriting."""
    mock_chat = mocker.AsyncMock()
    mock_chat.ainvoke.return_value = "How many orders were placed by top 5 customer Alice Smith?"

    service = ContextualizerService(chat_service=mock_chat)
    conv_service = ConversationService()

    # Prepare history
    await conv_service.get_or_create_conversation("c1", conv_test_session)
    m1 = await conv_service.add_message(
        "c1", MessageRole.USER, "Who is our top customer?", conv_test_session
    )
    m2 = await conv_service.add_message(
        "c1", MessageRole.ASSISTANT, "Our top customer is Alice Smith.", conv_test_session
    )

    rewritten = await service.contextualize_question("How many orders did they place?", [m1, m2])
    assert "Alice Smith" in rewritten
    mock_chat.ainvoke.assert_called_once()
