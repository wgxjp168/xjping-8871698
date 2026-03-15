"""
Brand Detector Service for ILbuy Intent Service.

Classifies the user's brand knowledge into three states:
- KNOWN:   User explicitly named a brand (and ideally a model).
- PARTIAL: User mentioned a brand but not a specific model.
- UNKNOWN: User shows no brand preference or actively seeks a recommendation.

Classification uses a signal-scoring approach rather than a single hard rule,
allowing graceful degradation when signals conflict.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Optional

from app.models.schemas import BrandDetectResponse, BrandStatusEnum
from app.services.entity_extractor import BRAND_LIST_SORTED

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Signal dictionaries
# ---------------------------------------------------------------------------

# Phrases that strongly indicate the user has NO brand preference
UNKNOWN_SIGNAL_PHRASES: list[str] = [
    "推荐", "不知道", "随便", "哪个好", "帮我选", "哪款好",
    "没想好", "不确定", "任何牌子", "随意", "帮我推荐",
    "选什么", "买什么", "什么品牌好", "哪个牌子好",
    "求推荐", "有什么好的", "最好的是什么",
]

UNKNOWN_SIGNAL_REGEX: list[re.Pattern] = [
    re.compile(r"(帮\s*[我]?\s*)?(推荐|建议|介绍)\s*[一几]?\s*[下款个台部]?", re.UNICODE),
    re.compile(r"哪\s*[款个台]\s*[比较]*\s*好", re.UNICODE),
    re.compile(r"不\s*知\s*道\s*(选|买|要)", re.UNICODE),
    re.compile(r"随\s*便", re.UNICODE),
]

# Phrases that indicate model-level specificity (boosts KNOWN confidence)
MODEL_SPECIFICITY_PATTERNS: list[re.Pattern] = [
    # e.g. Mate60 Pro, iPhone 15, 小米13
    re.compile(r"[A-Z]\w+\s*\d+", re.IGNORECASE | re.UNICODE),
    re.compile(r"\d+\s*(Pro|Max|Ultra|Plus|Lite|SE|Air|Mini)", re.IGNORECASE),
    re.compile(r"(?<=[\u4e00-\u9fff])\d{1,2}(?:\s*Pro)?", re.UNICODE),
    # model from entity dict
]


class BrandDetector:
    """
    Multi-signal brand preference classifier.
    """

    def __init__(self) -> None:
        self._initialized = False

    def initialize(self) -> None:
        logger.info("BrandDetector initialised.")
        self._initialized = True

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def detect(
        self,
        text: str,
        entities: dict[str, Any],
    ) -> BrandDetectResponse:
        """
        Detect the user's brand preference status.

        Parameters
        ----------
        text:     Raw user utterance.
        entities: Pre-extracted entity dict (output of EntityExtractor).

        Returns
        -------
        BrandDetectResponse with status, brand_name, confidence, reasoning.
        """
        brand_from_entities: Optional[str] = entities.get("brand")
        model_from_entities: Optional[str] = entities.get("model")

        unknown_score = self._compute_unknown_score(text)
        known_score, detected_brand = self._compute_known_score(
            text, brand_from_entities, model_from_entities
        )

        reasoning_parts: list[str] = []
        brand_status: BrandStatusEnum
        confidence: float
        brand_name: Optional[str] = detected_brand or brand_from_entities

        # Decision logic ---------------------------------------------------
        if unknown_score >= 0.5 and known_score < 0.3:
            # Clear UNKNOWN signal dominates
            brand_status = BrandStatusEnum.UNKNOWN
            brand_name = None
            confidence = min(0.90, 0.50 + unknown_score * 0.5)
            reasoning_parts.append(
                f"Detected {unknown_score:.2f} UNKNOWN signal strength "
                f"(recommendation/no-preference phrases found). "
                f"Known signal was low ({known_score:.2f})."
            )

        elif known_score >= 0.5 and model_from_entities:
            # Brand + model both present → KNOWN
            brand_status = BrandStatusEnum.KNOWN
            confidence = min(0.97, 0.60 + known_score * 0.4)
            reasoning_parts.append(
                f"Brand '{brand_name}' identified with model '{model_from_entities}'. "
                f"Combined known signal: {known_score:.2f}."
            )

        elif known_score >= 0.4 and brand_name and not model_from_entities:
            # Brand present but no model → PARTIAL
            brand_status = BrandStatusEnum.PARTIAL
            confidence = min(0.85, 0.45 + known_score * 0.45)
            reasoning_parts.append(
                f"Brand '{brand_name}' detected but no specific model number found. "
                f"Known signal: {known_score:.2f}."
            )

        elif known_score >= 0.4 and brand_name and model_from_entities:
            # Brand + model from text (regex) even if entity extractor missed
            brand_status = BrandStatusEnum.KNOWN
            confidence = min(0.90, 0.55 + known_score * 0.4)
            reasoning_parts.append(
                f"Brand '{brand_name}' and model '{model_from_entities}' detected via text analysis."
            )

        elif unknown_score > 0 and known_score == 0:
            # Weak UNKNOWN signal, no brand found
            brand_status = BrandStatusEnum.UNKNOWN
            brand_name = None
            confidence = min(0.75, 0.40 + unknown_score * 0.35)
            reasoning_parts.append(
                f"Weak UNKNOWN signal ({unknown_score:.2f}) and no brand mentions found in text."
            )

        elif brand_name and not model_from_entities:
            # Only brand name in text
            brand_status = BrandStatusEnum.PARTIAL
            confidence = 0.65
            reasoning_parts.append(
                f"Brand '{brand_name}' detected from text but no model specified. "
                "Classified as PARTIAL."
            )

        elif brand_name and model_from_entities:
            brand_status = BrandStatusEnum.KNOWN
            confidence = 0.80
            reasoning_parts.append(
                f"Brand '{brand_name}' and model '{model_from_entities}' detected."
            )

        else:
            # No signals at all — default UNKNOWN with low confidence
            brand_status = BrandStatusEnum.UNKNOWN
            brand_name = None
            confidence = 0.45
            reasoning_parts.append(
                "No brand signals detected. Defaulting to UNKNOWN with low confidence."
            )

        return BrandDetectResponse(
            brand_status=brand_status,
            brand_name=brand_name,
            confidence=round(confidence, 4),
            reasoning=" ".join(reasoning_parts),
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _compute_unknown_score(self, text: str) -> float:
        """
        Score how strongly the text indicates no brand preference.
        Returns a value in [0, 1].
        """
        hits = 0

        for phrase in UNKNOWN_SIGNAL_PHRASES:
            if phrase in text:
                hits += 1

        for pattern in UNKNOWN_SIGNAL_REGEX:
            if pattern.search(text):
                hits += 2  # Regex hits are more specific, weight heavier

        # Normalise: cap at total possible signals
        max_possible = len(UNKNOWN_SIGNAL_PHRASES) + len(UNKNOWN_SIGNAL_REGEX) * 2
        return min(1.0, hits / max(max_possible * 0.15, 1))

    def _compute_known_score(
        self,
        text: str,
        brand_from_entities: Optional[str],
        model_from_entities: Optional[str],
    ) -> tuple[float, Optional[str]]:
        """
        Score how strongly the text indicates a known brand preference.
        Returns (score, detected_brand_name).
        """
        score = 0.0
        detected_brand: Optional[str] = brand_from_entities

        # Brand from entity extractor
        if brand_from_entities:
            score += 0.45
        else:
            # Try direct text scan for brand name
            for brand in BRAND_LIST_SORTED:
                if brand in text:
                    detected_brand = brand
                    score += 0.40
                    break

        # Model from entity extractor
        if model_from_entities:
            score += 0.35

        # Model-like pattern in text (even if entity extractor missed)
        if not model_from_entities:
            for pattern in MODEL_SPECIFICITY_PATTERNS:
                if pattern.search(text):
                    score += 0.20
                    break

        return min(1.0, score), detected_brand
