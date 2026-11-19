"""Intent router classification schema and service."""

from pydantic import BaseModel, Field

from app.domain.enums.intent import UserIntent


class IntentClassification(BaseModel):
    """Structured output schema for intent routing classification."""

    intent: UserIntent = Field(
        ...,
        description=(
            "The classified target pipeline: "
            "'document' for unstructured policy/handbook/guide questions, "
            "'sql' for database queries on customers, products, revenue, stock, orders, refunds, "
            "'combined' if the query asks for both document policy AND quantitative relational database data."
        ),
    )
    confidence: float = Field(
        default=0.9,
        ge=0.0,
        le=1.0,
        description="Confidence score between 0.0 and 1.0",
    )
    reasoning: str = Field(
        default="",
        description="Brief explanation of the routing classification decision",
    )
