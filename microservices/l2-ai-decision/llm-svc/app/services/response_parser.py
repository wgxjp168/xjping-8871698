"""
ResponseParser – converts raw LLM text output into typed Pydantic models.

All LLM responses are requested in JSON format via the prompt. This module
provides robust parsing with graceful degradation: if structured JSON cannot
be found, it falls back to heuristic text extraction so the API never returns
a 500 due to a model going off-format.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

from app.models.schemas import DecisionSupportResponse, ProductAnalysisResponse

logger = logging.getLogger(__name__)


class ResponseParser:
    """Parse raw LLM text into structured Pydantic response models."""

    # ------------------------------------------------------------------
    # Product analysis
    # ------------------------------------------------------------------

    @staticmethod
    def parse_product_analysis(raw_text: str) -> ProductAnalysisResponse:
        """
        Parse LLM output into a ProductAnalysisResponse.

        Expected LLM JSON shape::

            {
              "analysis": "...",
              "key_features": ["..."],
              "pros": ["..."],
              "cons": ["..."],
              "match_score": 0.85,
              "recommendation": "..."
            }
        """
        data = ResponseParser.extract_structured_data(raw_text, "product_analysis")

        analysis = data.get("analysis") or ResponseParser.clean_response(raw_text)[:800]
        key_features = ResponseParser._ensure_list(data.get("key_features"))
        pros = ResponseParser._ensure_list(data.get("pros"))
        cons = ResponseParser._ensure_list(data.get("cons"))
        recommendation = (
            data.get("recommendation")
            or data.get("建议")
            or "请参阅上方综合分析。"
        )

        raw_score = data.get("match_score") or data.get("匹配度")
        match_score = ResponseParser._safe_float(raw_score, default=0.5)
        match_score = max(0.0, min(1.0, match_score))

        return ProductAnalysisResponse(
            analysis=analysis,
            key_features=key_features,
            pros=pros,
            cons=cons,
            match_score=match_score,
            recommendation=recommendation,
        )

    # ------------------------------------------------------------------
    # Decision support
    # ------------------------------------------------------------------

    @staticmethod
    def parse_decision_support(raw_text: str) -> DecisionSupportResponse:
        """
        Parse LLM output into a DecisionSupportResponse.

        Expected LLM JSON shape::

            {
              "decision_context": "...",
              "suggested_questions": ["..."],
              "confidence_factors": ["..."],
              "preliminary_recommendation": "..."
            }
        """
        data = ResponseParser.extract_structured_data(raw_text, "decision_support")

        decision_context = (
            data.get("decision_context")
            or data.get("决策背景")
            or ResponseParser.clean_response(raw_text)[:600]
        )
        suggested_questions = ResponseParser._ensure_list(
            data.get("suggested_questions") or data.get("建议问题")
        )
        confidence_factors = ResponseParser._ensure_list(
            data.get("confidence_factors") or data.get("置信度因素")
        )
        preliminary_recommendation = (
            data.get("preliminary_recommendation")
            or data.get("初步建议")
            or "需要更多信息以提供具体建议。"
        )

        return DecisionSupportResponse(
            decision_context=decision_context,
            suggested_questions=suggested_questions,
            confidence_factors=confidence_factors,
            preliminary_recommendation=preliminary_recommendation,
        )

    # ------------------------------------------------------------------
    # Generic structured data extractor
    # ------------------------------------------------------------------

    @staticmethod
    def extract_structured_data(
        raw_text: str, schema_hint: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract a JSON object from raw LLM text.

        Strategy:
        1. Parse the whole text as JSON directly.
        2. Find the first ```json … ``` or ``` … ``` code block.
        3. Find the first ``{…}`` balanced brace pair.
        4. Return an empty dict (graceful degradation).
        """
        cleaned = ResponseParser.clean_response(raw_text)

        # Strategy 1 – whole body is JSON
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        # Strategy 2 – fenced code block
        fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, re.DOTALL)
        if fenced:
            try:
                return json.loads(fenced.group(1))
            except json.JSONDecodeError:
                pass

        # Strategy 3 – first balanced brace pair
        brace_start = cleaned.find("{")
        if brace_start != -1:
            depth = 0
            for i, ch in enumerate(cleaned[brace_start:], start=brace_start):
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        candidate = cleaned[brace_start : i + 1]
                        try:
                            return json.loads(candidate)
                        except json.JSONDecodeError:
                            break

        logger.warning(
            "ResponseParser: could not extract JSON from LLM response "
            "(schema_hint=%s, first 120 chars: %r)",
            schema_hint,
            raw_text[:120],
        )
        return {}

    # ------------------------------------------------------------------
    # Text cleaner
    # ------------------------------------------------------------------

    @staticmethod
    def clean_response(text: str) -> str:
        """
        Normalise LLM output for downstream processing.

        - Strip leading/trailing whitespace.
        - Remove markdown bold/italic markers (**, __, *, _).
        - Collapse multiple blank lines into a single one.
        - Remove HTML-like tags.
        """
        if not text:
            return ""

        # Remove HTML tags
        text = re.sub(r"<[^>]+>", "", text)
        # Remove markdown bold/italic asterisk markers (e.g. **bold**, *italic*)
        # Use word-boundary-aware pattern so JSON keys with underscores are preserved.
        text = re.sub(r"\*{1,3}", "", text)
        # Remove markdown underscore markers only when NOT inside identifiers:
        # matches _word_ or __word__ at non-word boundaries to avoid stripping
        # underscores in JSON keys like match_score → matchscore.
        text = re.sub(r"(?<!\w)_{1,3}(?!\w)", "", text)
        # Collapse horizontal rules
        text = re.sub(r"^[-*]{3,}\s*$", "", text, flags=re.MULTILINE)
        # Collapse multiple blank lines
        text = re.sub(r"\n{3,}", "\n\n", text)

        return text.strip()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _ensure_list(value: Any) -> List[str]:
        """Coerce a value to a non-empty list of strings."""
        if isinstance(value, list):
            return [str(item) for item in value if item]
        if isinstance(value, str) and value.strip():
            # Try to split by newlines or semicolons
            parts = re.split(r"[\n;]", value)
            return [p.strip(" -•·") for p in parts if p.strip()]
        return []

    @staticmethod
    def _safe_float(value: Any, *, default: float = 0.0) -> float:
        """Convert *value* to float, returning *default* on failure."""
        try:
            return float(value)
        except (TypeError, ValueError):
            return default
