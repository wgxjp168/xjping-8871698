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
        description="Whether to stream the response",
    )
    enable_thinking: bool = Field(
        default=False,
        description="Enable adaptive thinking (Anthropic claude-opus-4-6 / sonnet-4-6 only)",
    )
    context_type: Literal[
        "product_analysis",
        "decision_support",
        "report_generation",
        "scoring_insight",
        "intent_disambiguation",
        "general",
    ] = Field(
        default="general",
        description="Semantic context hint used to route prompts and parsing",
    )


class LLMChatResponse(BaseModel):
    content: str = Field(description="Generated text content")
    thinking: Optional[str] = Field(
        default=None,
        description="Thinking/reasoning trace from adaptive thinking (Anthropic only)",
    )
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


# ---------------------------------------------------------------------------
# Scoring insight  (NEW)
# LLM evaluates qualitative dimension signals that rule-based models miss.
# ---------------------------------------------------------------------------


class DimensionInsight(BaseModel):
    dimension: str = Field(description="Scoring dimension name")
    signal: Literal["positive", "negative", "neutral"] = Field(
        description="Overall signal direction for this dimension"
    )
    adjustment: float = Field(
        ge=-20.0,
        le=20.0,
        description="Suggested score adjustment (-20 to +20 points)",
    )
    rationale: str = Field(description="Chinese-language rationale for the adjustment")
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="LLM confidence in this assessment",
    )


class ScoringInsightRequest(BaseModel):
    scoring_context: Literal["B2B", "B2C_KNOWN", "B2C_UNKNOWN"] = Field(
        description="Scoring model context"
    )
    intent: str = Field(description="User purchase intent")
    entities: Dict[str, Any] = Field(description="Extracted entities")
    dimension_scores: Dict[str, float] = Field(
        description="Current rule-based dimension scores (0-100)"
    )
    enriched_context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Enriched product/market context from L3 services",
    )
    provider: Optional[LLMProvider] = Field(default=None)


class ScoringInsightResponse(BaseModel):
    dimension_insights: List[DimensionInsight] = Field(
        description="Per-dimension LLM assessment and adjustment suggestions"
    )
    risk_signals: List[str] = Field(
        description="Key risk factors identified by LLM (Chinese)"
    )
    opportunity_signals: List[str] = Field(
        description="Key opportunity factors identified by LLM (Chinese)"
    )
    overall_assessment: str = Field(
        description="LLM overall purchase assessment narrative (Chinese)"
    )
    adjusted_total: float = Field(
        ge=0.0,
        le=100.0,
        description="Suggested total score after applying LLM adjustments",
    )
    provider: str = Field(description="Provider used")
    model: str = Field(description="Model used")
    latency_ms: float = Field(description="Generation latency in milliseconds")


# ---------------------------------------------------------------------------
# Intent disambiguation  (NEW)
# LLM resolves low-confidence intent classification ambiguity.
# ---------------------------------------------------------------------------


class IntentCandidate(BaseModel):
    intent: str = Field(description="Intent enum value")
    confidence: float = Field(ge=0.0, le=1.0, description="Rule-based confidence score")


class IntentDisambiguationRequest(BaseModel):
    text: str = Field(description="Original user utterance")
    candidates: List[IntentCandidate] = Field(
        description="Top-N rule-based intent candidates with confidence scores"
    )
    context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Conversation context (previous intent, entities, session history)",
    )
    provider: Optional[LLMProvider] = Field(default=None)


class IntentDisambiguationResponse(BaseModel):
    intent: str = Field(description="Disambiguated intent enum value")
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="LLM-calibrated confidence after disambiguation",
    )
    rationale: str = Field(
        description="Chinese-language explanation of the disambiguation decision"
    )
    sub_intents: List[IntentCandidate] = Field(
        default_factory=list,
        description="Secondary intent signals from LLM analysis",
    )
    provider: str = Field(description="Provider used")
    latency_ms: float = Field(description="Latency in milliseconds")
