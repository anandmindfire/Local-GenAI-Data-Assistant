"""Intent router classification schema and service."""

import re

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


SQL_QUANT_PATTERNS = [
    r"\bhow\s+many\b",
    r"\btotal\s+(revenue|sales|amount|number|refunds|orders|customers|spent?)\b",
    r"\bhow\s+much\s+(was|were|is|are)?\s*(refunded|spent|sold|earned)\b",
    r"\b(top|bottom)\s+\d+\b",
    r"\b(highest|lowest|most|least)\b",
    r"\baverage\b",
    r"\bstock\s+(below|above|under|over|<|>|=)\b",
    r"\bwhich\s+(customers|products|orders)\b",
    r"\blist\s+(all\s+)?(customers|orders|products|refunds)\b",
    r"\bplaced\s+(an\s+)?order\b",
    r"\border(s)?\s+placed\b",
    r"\bby\s+revenue\b",
]

SQL_ENTITY_PATTERNS = [
    r"\b(customer|customers)\b",
    r"\b(order|orders)\b",
    r"\b(product|products)\b",
    r"\b(revenue|sales)\b",
    r"\b(inventory|stock)\b",
    r"\bdatabase\b",
]

DOC_PATTERNS = [
    r"\b(policy|policies)\b",
    r"\b(handbook|guideline|guidelines|manual|procedure|procedures)\b",
    r"\b(leave|leaves|vacation|holiday|sick\s+leave|casual\s+leave|maternity|paternity)\b",
    r"\b(onboarding|probation|notice\s+period|dress\s+code|conduct|harassment|compliance|nda)\b",
    r"\b(remote(ly)?|work\s+from\s+home|wfh|working\s+hours)\b",
    r"\b(benefits|health\s+insurance)\b",
]


def classify_intent_heuristic(question: str) -> IntentClassification | None:
    """Fast-path heuristic intent classifier.

    Resolves obvious document, SQL, or combined queries in <1ms without LLM latency.
    Returns None when the query is ambiguous, prompting LLM structured classification.
    """
    q_lower = question.lower()
    has_doc = any(re.search(p, q_lower) for p in DOC_PATTERNS)
    has_sql_quant = any(re.search(p, q_lower) for p in SQL_QUANT_PATTERNS)
    has_sql_entity = any(re.search(p, q_lower) for p in SQL_ENTITY_PATTERNS)

    has_sql = has_sql_quant or (has_sql_entity and not has_doc)

    if has_doc and (
        has_sql_quant
        or ("order" in q_lower and "placed" in q_lower)
        or ("how much" in q_lower and "refund" in q_lower)
    ):
        return IntentClassification(
            intent=UserIntent.COMBINED,
            confidence=0.98,
            reasoning="Fast-path match: query combines document policy and quantitative database indicators.",
        )
    if has_doc and not has_sql_quant:
        return IntentClassification(
            intent=UserIntent.DOCUMENT,
            confidence=0.95,
            reasoning="Fast-path match: query targets unstructured policy or document guidance.",
        )
    if has_sql:
        return IntentClassification(
            intent=UserIntent.SQL,
            confidence=0.95,
            reasoning="Fast-path match: query targets structured relational database records or metrics.",
        )

    return None
