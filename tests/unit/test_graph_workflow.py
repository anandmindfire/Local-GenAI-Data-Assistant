"""Unit tests for LangGraph state machine, routing, and parallel execution."""

import pytest

from app.modules.graph.state import AssistantState
from app.modules.graph.workflow import build_assistant_graph, route_by_intent


def test_route_by_intent():
    """Verify conditional edge router maps intent accurately."""
    assert route_by_intent({"intent": "document"}) == "rag"
    assert route_by_intent({"intent": "sql"}) == "sql"
    assert route_by_intent({"intent": "combined"}) == "combined"
    assert route_by_intent({"intent": "random"}) == "rag"


@pytest.mark.asyncio
async def test_workflow_document_pipeline(mocker):
    """Test full graph execution when routing to Document RAG."""
    mocker.patch(
        "app.modules.graph.workflow.load_context_node",
        new_callable=mocker.AsyncMock,
        return_value={},
    )
    mocker.patch(
        "app.modules.graph.workflow.contextualize_question_node",
        new_callable=mocker.AsyncMock,
        return_value={"contextualized_question": "What is the leave policy?"},
    )
    mocker.patch(
        "app.modules.graph.workflow.intent_router_node",
        new_callable=mocker.AsyncMock,
        return_value={"intent": "document"},
    )
    mocker.patch(
        "app.modules.graph.workflow.rag_node",
        new_callable=mocker.AsyncMock,
        return_value={
            "answer": "Employees receive 24 days leave annually.",
            "sources": [{"filename": "leave.md", "page_number": 1}],
        },
    )
    mocker.patch(
        "app.modules.graph.workflow.persist_conversation_node",
        new_callable=mocker.AsyncMock,
        return_value={},
    )

    graph = build_assistant_graph()
    initial_state: AssistantState = {
        "conversation_id": "test_conv",
        "question": "What is the leave policy?",
        "contextualized_question": "",
        "intent": "unknown",
        "retrieved_documents": [],
        "generated_sql": None,
        "sql_results": None,
        "execution_errors": [],
        "answer": "",
        "sources": [],
        "execution_metadata": {},
    }

    result = await graph.ainvoke(initial_state)
    assert result["intent"] == "document"
    assert "24 days leave" in result["answer"]
    assert len(result["sources"]) == 1


@pytest.mark.asyncio
async def test_workflow_sql_pipeline(mocker):
    """Test full graph execution when routing to SQL Agent."""
    mocker.patch(
        "app.modules.graph.workflow.load_context_node",
        new_callable=mocker.AsyncMock,
        return_value={},
    )
    mocker.patch(
        "app.modules.graph.workflow.contextualize_question_node",
        new_callable=mocker.AsyncMock,
        return_value={"contextualized_question": "Top 5 customers by revenue"},
    )
    mocker.patch(
        "app.modules.graph.workflow.intent_router_node",
        new_callable=mocker.AsyncMock,
        return_value={"intent": "sql"},
    )
    mocker.patch(
        "app.modules.graph.workflow.sql_node",
        new_callable=mocker.AsyncMock,
        return_value={
            "answer": "The top customer is Alice Smith with $4,099.47.",
            "generated_sql": "SELECT * FROM customers LIMIT 5",
            "sql_results": [{"first_name": "Alice"}],
        },
    )
    mocker.patch(
        "app.modules.graph.workflow.persist_conversation_node",
        new_callable=mocker.AsyncMock,
        return_value={},
    )

    graph = build_assistant_graph()
    initial_state: AssistantState = {
        "conversation_id": "test_conv",
        "question": "Who are the top customers?",
        "contextualized_question": "",
        "intent": "unknown",
        "retrieved_documents": [],
        "generated_sql": None,
        "sql_results": None,
        "execution_errors": [],
        "answer": "",
        "sources": [],
        "execution_metadata": {},
    }

    result = await graph.ainvoke(initial_state)
    assert result["intent"] == "sql"
    assert "Alice Smith" in result["answer"]
    assert result["generated_sql"] is not None


@pytest.mark.asyncio
async def test_workflow_combined_pipeline(mocker):
    """Test full graph execution when routing to Combined (parallel fan out + aggregation)."""
    mocker.patch(
        "app.modules.graph.workflow.load_context_node",
        new_callable=mocker.AsyncMock,
        return_value={},
    )
    mocker.patch(
        "app.modules.graph.workflow.contextualize_question_node",
        new_callable=mocker.AsyncMock,
        return_value={"contextualized_question": "What is the return policy and total refunds?"},
    )
    mocker.patch(
        "app.modules.graph.workflow.intent_router_node",
        new_callable=mocker.AsyncMock,
        return_value={"intent": "combined"},
    )

    # Mock parallel execution
    mocker.patch(
        "app.modules.graph.workflow.parallel_combined_node",
        new_callable=mocker.AsyncMock,
        return_value={
            "sources": [{"filename": "refund-policy.md", "page_number": 1}],
            "generated_sql": "SELECT SUM(refund_amount) FROM refunds",
            "sql_results": [{"total": 1349.99}],
            "execution_metadata": {
                "intermediate_rag_answer": "Refund policy permits returns within 30 days.",
                "intermediate_sql_answer": "Total refunds processed last month equal $1,349.99.",
            },
        },
    )
    mocker.patch(
        "app.modules.graph.workflow.result_aggregation_node",
        new_callable=mocker.AsyncMock,
        return_value={
            "answer": (
                "According to company policy, items can be returned within 30 days. "
                "In the past month, $1,349.99 was refunded across processed claims."
            )
        },
    )
    mocker.patch(
        "app.modules.graph.workflow.persist_conversation_node",
        new_callable=mocker.AsyncMock,
        return_value={},
    )

    graph = build_assistant_graph()
    initial_state: AssistantState = {
        "conversation_id": "test_conv",
        "question": "What is the return policy and total refunds?",
        "contextualized_question": "",
        "intent": "unknown",
        "retrieved_documents": [],
        "generated_sql": None,
        "sql_results": None,
        "execution_errors": [],
        "answer": "",
        "sources": [],
        "execution_metadata": {},
    }

    result = await graph.ainvoke(initial_state)
    assert result["intent"] == "combined"
    assert "30 days" in result["answer"]
    assert "1,349.99" in result["answer"]
    assert result["generated_sql"] is not None
