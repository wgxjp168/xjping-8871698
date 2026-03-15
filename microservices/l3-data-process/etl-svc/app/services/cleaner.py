"""
Data Cleaner
============
Rules applied to each raw product:
  1. Drop records with missing/invalid title, price, or product_id
  2. Strip HTML tags, excessive whitespace, and emoji from title
  3. Clamp price to [min_price, max_price]
  4. Normalise rating to [0, 5]
  5. Clamp review/sales counts to ≥ 0
  6. Sanitise image URLs (must start with http/https)
  7. Remove spec entries with empty keys or values
  8. Compute discount_pct from original_price/price
"""
from __future__ import annotations

import logging
import re
from typing import List, Optional, Tuple

from app.core.config import get_settings
from app.models.schemas import RawProduct

logger = logging.getLogger(__name__)
settings = get_settings()

_HTML_TAG_RE   = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")
# Emoji removal — covers most Unicode emoji ranges
_EMOJI_RE = re.compile(
    "[\U00010000-\U0010ffff"
    "\U0001F600-\U0001F64F"
    "\U0001F300-\U0001F5FF"
    "\U0001F680-\U0001F6FF"
    "\U0001F1E0-\U0001F1FF"
    "\u2600-\u26FF\u2700-\u27BF]+",
    flags=re.UNICODE,
)


def _clean_text(text: str) -> str:
    text = _HTML_TAG_RE.sub(" ", text)
    text = _EMOJI_RE.sub("", text)
    text = _WHITESPACE_RE.sub(" ", text).strip()
    return text


def _is_valid_url(url: Optional[str]) -> bool:
    return bool(url and (url.startswith("http://") or url.startswith("https://")))


class DataCleaner:
    """Validates and cleans raw product records."""

    def clean_batch(self, products: List[RawProduct]) -> Tuple[List[RawProduct], int]:
        """
        Returns (cleaned_products, invalid_count).
        Invalid records are logged and dropped.
        """
        cleaned: List[RawProduct] = []
        invalid = 0
        for p in products:
            result, reason = self._clean_one(p)
            if result is None:
                logger.debug(
                    '"Dropped product platform=%s id=%s reason=%s"',
                    p.platform, p.product_id, reason,
                )
                invalid += 1
            else:
                cleaned.append(result)
        return cleaned, invalid

    def _clean_one(self, p: RawProduct) -> Tuple[Optional[RawProduct], Optional[str]]:
        # ── Mandatory field checks ────────────────────────────────────────
        if not p.product_id or not p.product_id.strip():
            return None, "empty product_id"

        title_raw = (p.title or "").strip()
        if not title_raw:
            return None, "empty title"

        title_cleaned = _clean_text(title_raw)
        if len(title_cleaned) < settings.min_title_len:
            return None, f"title too short ({len(title_cleaned)} chars)"

        if p.price < settings.min_price:
            return None, f"price too low ({p.price})"

        # ── Mutations (create modified copy via model_copy) ───────────────
        updates = {
            "title": title_cleaned,
        }

        # Price clamping
        updates["price"] = max(settings.min_price, min(settings.max_price, p.price))

        # Original price sanity
        if p.original_price is not None:
            if p.original_price <= 0 or p.original_price < p.price:
                updates["original_price"] = None
            else:
                updates["original_price"] = min(settings.max_price, p.original_price)

        # Promotion price
        if p.promotion_price is not None:
            if p.promotion_price <= 0 or p.promotion_price > p.price:
                updates["promotion_price"] = None

        # Rating clamp [0, 5]
        updates["average_rating"] = max(0.0, min(5.0, p.average_rating))
        updates["shop_rating"]    = max(0.0, min(5.0, p.shop_rating))

        # Counts clamp ≥ 0
        updates["sales_count"]  = max(0, p.sales_count)
        updates["review_count"] = max(0, p.review_count)

        # Image URL sanitisation
        updates["images"] = [u for u in p.images if _is_valid_url(u)]

        # Spec cleanup
        updates["specs"] = {
            str(k).strip(): str(v).strip()
            for k, v in (p.specs or {}).items()
            if k and v and str(k).strip() and str(v).strip()
        }

        # Delivery days clamp
        if p.delivery_days is not None and p.delivery_days < 0:
            updates["delivery_days"] = None

        return p.model_copy(update=updates), None


# Singleton
data_cleaner = DataCleaner()
