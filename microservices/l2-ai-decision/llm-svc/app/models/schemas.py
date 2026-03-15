"""
Pydantic schemas for the LLM service API.
"""

from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class LLMProvider(str, Enum):
    openai = "openai"
    anthropic = "anthropic"
    wenxin = "wenxin"


# ---------------------------------------------------------------------------
# Chat primitives
# ---------------------------------------------------------------------------


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"] = Field(
        description="Message role in the conversation"
    )
    content: str = Field(description="Text content of the message")


# ---------------------------------------------------------------------------
# General chat
# ---------------------------------------------------------------------------


class LLMChatRequest(BaseModel):
    messages: List[ChatMessage] = Field(
        description="Conversation history including the new user turn"
    )
    provider: Optional[LLMProvider] = Field(
        default=None,
        description="Override the default LLM provider for this request",
    )
    max_tokens: int = Field(
        default=2048,
        ge=1,
        le=32768,
        description="Maximum tokens in the completion",
    )
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Sampling temperature",
    )
    stream: bool = Field(
        default=False,
        description="Whether to stream the response (reserved for future use)",
    )
    context_type: Literal[
        "product_analysis",
        "decision_support",
        "report_generation",
        "general",
    ] = Field(
        default="general",
        description="Semantic context hint used to route prompts and parsing",
    )


class LLMChatResponse(BaseModel):
    content: str = Field(description="Generated text content")
    provider: str = Field(description="Provider that served the request")
    model: str = Field(description="Model identifier used")
    usage: Dict[str, Any] = Field(
        default_factory=dict,
        description="Token usage statistics returned by the provider",
    )
    latency_ms: float = Field(description="End-to-end request latency in milliseconds")


# ---------------------------------------------------------------------------
# Product analysis
# ---------------------------------------------------------------------------


class ProductAnalysisRequest(BaseModel):
    product_description: str = Field(
        description="Free-text description or specifications of the product"
    )
    user_requirements: Dict[str, Any] = Field(
        description="Structured requirements from the buyer (e.g. quantity, cert, delivery)"
    )
    budget_range: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional budget constraints, e.g. {'min': 100, 'max': 500, 'currency': 'USD'}",
    )


class ProductAnalysisResponse(BaseModel):
    analysis: str = Field(description="Comprehensive analysis narrative in Chinese")
    key_features: List[str] = Field(description="Extracted key product features")
    pros: List[str] = Field(description="Advantages / strengths of the product")
    cons: List[str] = Field(description="Disadvantages / weaknesses of the product")
    match_score: float = Field(
        ge=0.0,
        le=1.0,
        description="0-1 score indicating how well the product matches requirements",
    )
    recommendation: str = Field(
        description="Final concise purchasing recommendation in Chinese"
    )


# ---------------------------------------------------------------------------
# Decision support
# ---------------------------------------------------------------------------


class DecisionSupportRequest(BaseModel):
    intent: str = Field(
        description="Parsed user purchase intent (e.g. 'compare', 'buy', 'consult')"
    )
    entities: Dict[str, Any] = Field(
        description="Named entities extracted from the user query (product, brand, spec…)"
    )
    brand_status: str = Field(
        description="Brand availability / compliance status from upstream service"
    )
    user_context: Dict[str, Any] = Field(
        description="User session context: history, preferences, membership tier, etc."
    )


class DecisionSupportResponse(BaseModel):
    decision_context: str = Field(
        description="Synthesised decision context narrative in Chinese"
    )
    suggested_questions: List[str] = Field(
        description="Follow-up clarifying questions to present to the user"
    )
    confidence_factors: List[str] = Field(
        description="Key factors driving confidence in the preliminary recommendation"
    )
    preliminary_recommendation: str = Field(
        description="Early recommendation before full analysis, in Chinese"
    )


# ---------------------------------------------------------------------------
# Report generation (internal use – passed through routes)
# ---------------------------------------------------------------------------


class ReportGenerationRequest(BaseModel):
    decision_data: Dict[str, Any] = Field(
        description="Aggregated decision data (intent, entities, analysis results…)"
    )
    scoring_result: Dict[str, Any] = Field(
        description="Scoring / ranking results from the scoring service"
    )
    report_format: Literal["summary", "detailed", "executive"] = Field(
        default="summary",
        description="Level of detail for the generated report",
    )


class ReportGenerationResponse(BaseModel):
    report: str = Field(description="Generated report content in Chinese")
    provider: str = Field(description="Provider used")
    model: str = Field(description="Model used")
    latency_ms: float = Field(description="Generation latency in milliseconds")
