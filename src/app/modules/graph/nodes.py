"""LangGraph workflow node implementations."""

import asyncio
import logging
from typing import Any

from langchain_core.messages import HumanMessage
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums.intent import UserIntent
from app.domain.models.conversation import MessageRole
from app.infrastructure.database.connection import db_context
from app.infrastructure.llm.chat_model import get_chat_service
from app.modules.conversation.context_builder import get_contextualizer_service
from app.modules.conversation.service import get_conversation_service
from app.modules.graph.prompts import (
    build_aggregation_system_message,
    build_router_system_message,
)
from app.modules.graph.routing import IntentClassification
from app.modules.graph.state import AssistantState
from app.modules.rag.service import get_rag_service
from app.modules.sql_agent.service import get_sql_agent_service

logger = logging.getLogger(__name__)


async def load_context_node(state: AssistantState) -> dict[str, Any]:
    """Node: Load previous conversation context from PostgreSQL."""
    conversation_id = state.get("conversation_id", "")
    if not conversation_id:
        return {}

    try:
        conv_service = get_conversation_service()
        async with db_context() as session:
            history = await conv_service.get_conversation_history(conversation_id, session=session)
            # Store history in execution_metadata for next node
            return {
                "execution_metadata": {
                    **state.get("execution_metadata", {}),
                    "history": [h.model_dump() for h in history],
                }
            }
    except Exception as e:
        logger.warning(f"Failed to load conversation history for {conversation_id}: {e}")
        return {}


async def contextualize_question_node(state: AssistantState) -> dict[str, Any]:
    """Node: Resolve follow-up references using conversational history."""
    question = state["question"]
    history_raw = state.get("execution_metadata", {}).get("history", [])

    if not history_raw:
        return {"contextualized_question": question}

    try:
        from app.domain.models.conversation import Message

        history = [Message.model_validate(h) for h in history_raw]
        contextualizer = get_contextualizer_service()
        rewritten = await contextualizer.contextualize_question(question, history)
        return {"contextualized_question": rewritten}
    except Exception as e:
        logger.warning(f"Contextualization node error: {e}. Preserving original question.")
        return {"contextualized_question": question}


async def intent_router_node(state: AssistantState) -> dict[str, Any]:
    """Node: Classify question into 'document', 'sql', or 'combined'."""
    question = state.get("contextualized_question") or state["question"]
    chat_service = get_chat_service()

    messages = [
        build_router_system_message(),
        HumanMessage(content=f"Classify the following question:\n{question}"),
    ]

    try:
        classification = await chat_service.generate_structured(
            messages=messages,
            schema=IntentClassification,
        )
        intent_value = classification.intent.value
        logger.info(
            f"Intent classified as '{intent_value}' (confidence={classification.confidence:.2f})"
        )
        return {"intent": intent_value}
    except Exception as e:
        logger.warning(f"LLM intent routing failed ({e}). Defaulting to 'document'.")
        return {"intent": UserIntent.DOCUMENT.value}


async def rag_node(state: AssistantState) -> dict[str, Any]:
    """Node: Execute Document RAG pipeline."""
    question = state.get("contextualized_question") or state["question"]
    rag_service = get_rag_service()

    try:
        response = await rag_service.answer_question(question)
        sources_list = [s.model_dump() for s in response.sources]
        return {
            "answer": response.answer,
            "sources": sources_list,
            "retrieved_documents": sources_list,
            "execution_metadata": {
                **state.get("execution_metadata", {}),
                "rag_confidence": response.confidence,
            },
        }
    except Exception as e:
        logger.error(f"RAG node error: {e}")
        return {
            "answer": "An error occurred while retrieving or processing document information.",
            "execution_errors": state.get("execution_errors", []) + [str(e)],
        }


async def sql_node(state: AssistantState) -> dict[str, Any]:
    """Node: Execute NL2SQL pipeline."""
    question = state.get("contextualized_question") or state["question"]
    sql_service = get_sql_agent_service()

    try:
        response = await sql_service.execute_question(question)
        return {
            "answer": response.answer,
            "generated_sql": response.generated_sql,
            "sql_results": response.query_result.rows,
            "execution_metadata": {
                **state.get("execution_metadata", {}),
                "sql_row_count": response.query_result.row_count,
                "sql_duration_ms": response.query_result.execution_duration_ms,
            },
        }
    except Exception as e:
        logger.error(f"SQL node error: {e}")
        error_msg = getattr(e, "message", str(e))
        return {
            "answer": f"Could not process database query: {error_msg}",
            "execution_errors": state.get("execution_errors", []) + [str(e)],
        }


async def parallel_combined_node(state: AssistantState) -> dict[str, Any]:
    """Node: Concurrently execute both RAG and SQL Agent for combined intent."""
    question = state.get("contextualized_question") or state["question"]
    rag_service = get_rag_service()
    sql_service = get_sql_agent_service()

    logger.info("Executing parallel RAG and SQL execution branches for 'combined' query...")

    # Fan out both tasks concurrently
    rag_task = asyncio.create_task(rag_service.answer_question(question))
    sql_task = asyncio.create_task(sql_service.execute_question(question))

    results = await asyncio.gather(rag_task, sql_task, return_exceptions=True)
    rag_res, sql_res = results[0], results[1]

    state_update: dict[str, Any] = {}
    errors: list[str] = list(state.get("execution_errors", []))

    rag_answer = ""
    sources: list[dict[str, Any]] = []
    if isinstance(rag_res, Exception):
        logger.warning(f"RAG branch in combined node failed: {rag_res}")
        errors.append(f"RAG Branch Error: {rag_res}")
        rag_answer = "Could not retrieve document evidence."
    else:
        rag_answer = rag_res.answer
        sources = [s.model_dump() for s in rag_res.sources]

    sql_answer = ""
    generated_sql = None
    sql_rows = None
    if isinstance(sql_res, Exception):
        logger.warning(f"SQL branch in combined node failed: {sql_res}")
        errors.append(f"SQL Branch Error: {sql_res}")
        sql_answer = "Could not execute database query."
    else:
        sql_answer = sql_res.answer
        generated_sql = sql_res.generated_sql
        sql_rows = sql_res.query_result.rows

    state_update["sources"] = sources
    state_update["retrieved_documents"] = sources
    state_update["generated_sql"] = generated_sql
    state_update["sql_results"] = sql_rows
    state_update["execution_errors"] = errors
    state_update["execution_metadata"] = {
        **state.get("execution_metadata", {}),
        "intermediate_rag_answer": rag_answer,
        "intermediate_sql_answer": sql_answer,
    }

    return state_update


async def result_aggregation_node(state: AssistantState) -> dict[str, Any]:
    """Node: Synthesize outputs from parallel RAG and SQL branches into a single answer."""
    meta = state.get("execution_metadata", {})
    rag_answer = meta.get("intermediate_rag_answer", "")
    sql_answer = meta.get("intermediate_sql_answer", "")
    question = state.get("contextualized_question") or state["question"]

    chat_service = get_chat_service()

    prompt = (
        f"USER QUESTION: {question}\n\n"
        f"DOCUMENT POLICY EVIDENCE:\n{rag_answer}\n\n"
        f"RELATIONAL DATABASE DATA:\n{sql_answer}\n\n"
        f"Please provide a coherent, synthesized final response answering both parts of the question."
    )

    messages = [
        build_aggregation_system_message(),
        HumanMessage(content=prompt),
    ]

    try:
        combined_answer = await chat_service.ainvoke(messages)
        return {"answer": combined_answer}
    except Exception as e:
        logger.warning(
            f"Aggregation node LLM synthesis failed ({e}). Concatenating branch answers."
        )
        concatenated = f"{rag_answer}\n\n---\n\n{sql_answer}"
        return {"answer": concatenated}


async def persist_conversation_node(
    state: AssistantState,
    session: AsyncSession | None = None,
) -> dict[str, Any]:
    """Node: Persist user question and assistant answer in PostgreSQL."""
    conversation_id = state.get("conversation_id", "")
    if not conversation_id:
        return {}

    conv_service = get_conversation_service()

    async def _persist(s: AsyncSession):
        # 1. Ensure conversation exists
        await conv_service.get_or_create_conversation(conversation_id, session=s)

        # 2. Persist user message
        await conv_service.add_message(
            conversation_id=conversation_id,
            role=MessageRole.USER,
            content=state["question"],
            session=s,
        )

        # 3. Persist assistant message
        await conv_service.add_message(
            conversation_id=conversation_id,
            role=MessageRole.ASSISTANT,
            content=state.get("answer", ""),
            intent=state.get("intent"),
            sources=state.get("sources", []),
            sql_query=state.get("generated_sql"),
            sql_results=state.get("sql_results"),
            execution_metadata=state.get("execution_metadata", {}),
            session=s,
        )

    try:
        if session is not None:
            await _persist(session)
        else:
            async with db_context() as s:
                await _persist(s)
    except Exception as e:
        logger.warning(f"Failed to persist conversation {conversation_id}: {e}")

    return {}
