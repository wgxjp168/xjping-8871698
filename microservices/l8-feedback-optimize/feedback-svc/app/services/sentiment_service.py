import logging
from typing import Tuple, Optional

# Try to import snownlp; fall back gracefully if not available (e.g. Python 3.11+
# where snownlp's legacy setup.py build fails with modern pip/setuptools).
try:
    from snownlp import SnowNLP as _SnowNLP  # type: ignore
    _SNOWNLP_AVAILABLE = True
except ImportError:
    _SnowNLP = None
    _SNOWNLP_AVAILABLE = False

logger = logging.getLogger(__name__)

# Thresholds for label classification
POSITIVE_THRESHOLD = 0.65
NEGATIVE_THRESHOLD = 0.35

# Rule-based keyword boosters for domain-specific words
POSITIVE_KEYWORDS = ["推荐", "准确", "有用", "满意", "好", "棒", "优秀", "专业", "详细", "值得"]
NEGATIVE_KEYWORDS = ["不准确", "错误", "差", "失望", "无用", "不好", "糟糕", "浪费", "坑", "垃圾"]


def analyze_sentiment(text: str) -> Tuple[float, str]:
    """
    Analyze sentiment of Chinese text.
    Uses snownlp when available; otherwise falls back to keyword-rule scoring.
    Returns (score 0.0-1.0, label POSITIVE/NEUTRAL/NEGATIVE)
    """
    if not text or not text.strip():
        return 0.5, "NEUTRAL"

    if not _SNOWNLP_AVAILABLE:
        return _rule_based_fallback(text)

    try:
        score = _SnowNLP(text).sentiments

        # Keyword boosting for domain-specific context
        score = _apply_keyword_boost(text, score)

        # Clamp to [0, 1]
        score = max(0.0, min(1.0, score))

        label = _score_to_label(score)
        return round(score, 4), label

    except Exception as e:
        logger.warning(f"Sentiment analysis failed: {e}, falling back to rule-based")
        return _rule_based_fallback(text)


def analyze_sentiment_from_rating(rating: int, comment: Optional[str]) -> Tuple[float, str]:
    """
    Combined sentiment: weight rating (60%) + NLP (40%) when comment available.
    """
    # Convert 1-5 rating to 0-1 score
    rating_score = (rating - 1) / 4.0

    if comment and len(comment.strip()) > 3:
        nlp_score, _ = analyze_sentiment(comment)
        combined = 0.6 * rating_score + 0.4 * nlp_score
    else:
        combined = rating_score

    combined = max(0.0, min(1.0, combined))
    return round(combined, 4), _score_to_label(combined)


def _apply_keyword_boost(text: str, score: float) -> float:
    boost = 0.0
    for kw in POSITIVE_KEYWORDS:
        if kw in text:
            boost += 0.05
    for kw in NEGATIVE_KEYWORDS:
        if kw in text:
            boost -= 0.05
    return score + boost


def _score_to_label(score: float) -> str:
    if score >= POSITIVE_THRESHOLD:
        return "POSITIVE"
    elif score <= NEGATIVE_THRESHOLD:
        return "NEGATIVE"
    return "NEUTRAL"


def _rule_based_fallback(text: str) -> Tuple[float, str]:
    pos_count = sum(1 for kw in POSITIVE_KEYWORDS if kw in text)
    neg_count = sum(1 for kw in NEGATIVE_KEYWORDS if kw in text)
    if pos_count > neg_count:
        return 0.75, "POSITIVE"
    elif neg_count > pos_count:
        return 0.25, "NEGATIVE"
    return 0.5, "NEUTRAL"
