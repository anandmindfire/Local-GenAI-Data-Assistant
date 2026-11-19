"""Chat API endpoint orchestrating multi-pipeline workflows."""

import logging
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_correlation_id, get_db
from app.api.schemas.chat import ChatRequest, ChatResponse
from app.modules.graph.workflow import execute_assistant_workflow

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest,
    correlation_id: str = Depends(get_correlation_id),
    session: AsyncSession = Depends(get_db),
) -> ChatResponse:
    """Natural language chat endpoint supporting documents, SQL, and combined queries."""
    conv_id = request.conversation_id or f"conv_{uuid.uuid4().hex[:16]}"

    logger.info(
        f"Processing chat query for conversation '{conv_id}' [Correlation-ID: {correlation_id}]"
    )

    final_state = await execute_assistant_workflow(
        question=request.message,
        conversation_id=conv_id,
    )

    return ChatResponse(
        conversation_id=conv_id,
        answer=final_state.get("answer", ""),
        intent=final_state.get("intent", "unknown"),
        sources=final_state.get("sources", []),
        sql_results=final_state.get("sql_results"),
        execution_metadata=final_state.get("execution_metadata", {}),
    )
