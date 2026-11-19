"""LangGraph workflow definition and compilation."""

import logging

from langgraph.graph import END, START, StateGraph

from app.modules.graph.nodes import (
    contextualize_question_node,
    intent_router_node,
    load_context_node,
    parallel_combined_node,
    persist_conversation_node,
    rag_node,
    result_aggregation_node,
    sql_node,
)
from app.modules.graph.state import AssistantState

logger = logging.getLogger(__name__)


def route_by_intent(state: AssistantState) -> str:
    """Conditional edge router directing execution based on classified intent."""
    intent = state.get("intent", "").lower()
    match intent:
        case "document":
            return "rag"
        case "sql":
            return "sql"
        case "combined":
            return "combined"
        case _:
            logger.info(f"Unknown intent '{intent}'. Routing to 'rag' fallback.")
            return "rag"


def build_assistant_graph():
    """Construct and compile the LangGraph StateGraph workflow."""
    builder = StateGraph(AssistantState)

    # 1. Register workflow nodes
    builder.add_node("load_context", load_context_node)
    builder.add_node("contextualize", contextualize_question_node)
    builder.add_node("router", intent_router_node)
    builder.add_node("rag", rag_node)
    builder.add_node("sql", sql_node)
    builder.add_node("combined", parallel_combined_node)
    builder.add_node("aggregate", result_aggregation_node)
    builder.add_node("persist", persist_conversation_node)

    # 2. Add sequential edges
    builder.add_edge(START, "load_context")
    builder.add_edge("load_context", "contextualize")
    builder.add_edge("contextualize", "router")

    # 3. Add conditional routing edges
    builder.add_conditional_edges(
        "router",
        route_by_intent,
        {
            "rag": "rag",
            "sql": "sql",
            "combined": "combined",
        },
    )

    # 4. Connect branch completions
    builder.add_edge("rag", "persist")
    builder.add_edge("sql", "persist")
    builder.add_edge("combined", "aggregate")
    builder.add_edge("aggregate", "persist")
    builder.add_edge("persist", END)

    return builder.compile()


# Global compiled workflow instance
assistant_graph = build_assistant_graph()


async def execute_assistant_workflow(
    question: str,
    conversation_id: str,
) -> AssistantState:
    """Execute the end-to-end assistant graph workflow for a user message."""
    initial_state: AssistantState = {
        "conversation_id": conversation_id,
        "question": question,
        "contextualized_question": question,
        "intent": "unknown",
        "retrieved_documents": [],
        "generated_sql": None,
        "sql_results": None,
        "execution_errors": [],
        "answer": "",
        "sources": [],
        "execution_metadata": {},
    }

    final_state = await assistant_graph.ainvoke(initial_state)
    return final_state
