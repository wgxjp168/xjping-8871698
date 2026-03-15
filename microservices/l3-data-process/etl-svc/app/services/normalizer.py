"""
Normalizer
==========
Transforms a cleaned RawProduct into a CleanProduct with:
  - canonical_id and dedupe_key
  - brand normalisation (alias map)
  - category path parsing
  - spec value normalisation (units, boolean strings)
  - discount_pct computation
  - title_cleaned (for ML / search indexing)
"""
from __future__ import annotations

import hashlib
import logging
import re
from typing import Dict, List, Optional

from app.models.schemas import CleanProduct, Platform, ProductScore, RawProduct

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Brand alias map — maps common variants to canonical name
# ---------------------------------------------------------------------------
_BRAND_ALIASES: Dict[str, str] = {
    "苹果": "Apple",
    "apple": "Apple",
    "华为": "Huawei",
    "huawei": "Huawei",
    "小米": "Xiaomi",
    "mi": "Xiaomi",
    "三星": "Samsung",
    "samsung": "Samsung",
    "oppo": "OPPO",
    "vivo": "vivo",
    "荣耀": "Honor",
    "honor": "Honor",
    "联想": "Lenovo",
    "lenovo": "Lenovo",
    "戴尔": "Dell",
    "dell": "Dell",
    "惠普": "HP",
    "hp": "HP",
    "索尼": "Sony",
    "sony": "Sony",
    "耐克": "Nike",
    "nike": "Nike",
    "阿迪达斯": "Adidas",
    "adidas": "Adidas",
}

# Category separators (used in path parsing)
_CAT_SEP_RE = re.compile(r"[>/\\>、,，|｜]")

# Spec value normalisation patterns
_BOOL_TRUE  = {"是", "yes", "true", "有", "支持", "✓"}
_BOOL_FALSE = {"否", "no", "false", "无", "不支持", "✗"}

# Title cleaning — keep CJK, alphanumeric, spaces
_TITLE_CLEAN_RE = re.compile(r"[^\w\u4e00-\u9fff\s]", re.UNICODE)
_WS_RE          = re.compile(r"\s+")


def _normalise_brand(brand: Optional[str]) -> Optional[str]:
    if not brand:
        return None
    b = brand.strip().lower()
    return _BRAND_ALIASES.get(b, brand.strip())


def _parse_category_path(category: Optional[str]) -> List[str]:
    if not category:
        return []
    parts = _CAT_SEP_RE.split(category)
    return [p.strip() for p in parts if p.strip()]


def _normalise_spec_value(value: str) -> str:
    v = value.strip().lower()
    if v in _BOOL_TRUE:
        return "是"
    if v in _BOOL_FALSE:
        return "否"
    return value.strip()


def _clean_title(title: str) -> str:
    t = title.lower()
    t = _TITLE_CLEAN_RE.sub(" ", t)
    t = _WS_RE.sub(" ", t).strip()
    return t


def _compute_discount(price: float, original: Optional[float]) -> Optional[float]:
    if original and original > price and price > 0:
        return round((original - price) / original * 100, 1)
    return None


def _dedupe_key(platform: Platform, product_id: str, title: str, price: float) -> str:
    """Stable cross-platform deduplication key."""
    norm_title = _clean_title(title)[:50]
    price_bucket = int(price / 10) * 10   # round to nearest 10 yuan
    raw = f"{norm_title}|{price_bucket}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]


class Normalizer:
    """Converts a cleaned RawProduct → CleanProduct."""

    def normalise(self, raw: RawProduct, score: ProductScore) -> CleanProduct:
        canonical_id = f"{raw.platform.value}:{raw.product_id}"
        brand_norm   = _normalise_brand(raw.brand)
        cat_path     = _parse_category_path(raw.category)
        discount     = _compute_discount(raw.price, raw.original_price)
        title_cl     = _clean_title(raw.title)
        specs_norm   = {
            k: _normalise_spec_value(v)
            for k, v in (raw.specs or {}).items()
        }

        return CleanProduct(
            platform         = raw.platform,
            product_id       = raw.product_id,
            canonical_id     = canonical_id,
            dedupe_key       = _dedupe_key(raw.platform, raw.product_id, raw.title, raw.price),
            title            = raw.title,
            title_cleaned    = title_cl,
            price            = raw.price,
            original_price   = raw.original_price,
            discount_pct     = discount,
            brand            = raw.brand,
            brand_normalised = brand_norm,
            category         = raw.category,
            category_path    = cat_path,
            specs            = specs_norm,
            images           = raw.images,
            sales_count      = raw.sales_count,
            review_count     = raw.review_count,
            average_rating   = raw.average_rating,
            shop_name        = raw.shop_name,
            shop_rating      = raw.shop_rating,
            in_stock         = raw.in_stock,
            delivery_days    = raw.delivery_days,
            promotion        = raw.promotion,
            promotion_price  = raw.promotion_price,
            url              = raw.url,
            score            = score,
            crawled_at       = raw.crawled_at,
            session_id       = raw.session_id,
            job_id           = raw.job_id,
            is_mock          = bool(raw.raw_data.get("mock")),
        )

    def normalise_batch(
        self, products: List[RawProduct], scores: List[ProductScore]
    ) -> List[CleanProduct]:
        return [
            self.normalise(p, s)
            for p, s in zip(products, scores)
        ]


# Singleton
normalizer = Normalizer()
