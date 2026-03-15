"""
Product Score Pre-computation
==============================
Computes ProductScore for each cleaned product to avoid repeated calculation
by downstream services (L2 decision-svc scoring models).

Dimensions:
  1. price_score         — how competitive the price is (vs reference)
  2. popularity_score    — log-scaled sales/review volume
  3. rating_score        — weighted average rating × review-count trust
  4. availability_score  — in-stock status + delivery speed
  5. value_for_money_score — specs_count / price ratio

Final total_score is a weighted sum (weights from config).
Grade: A ≥ 85, B ≥ 70, C ≥ 55, D < 55
"""
from __future__ import annotations

import logging
import math
from typing import List

from app.core.config import get_settings
from app.models.schemas import Grade, ProductScore, RawProduct

logger = logging.getLogger(__name__)
settings = get_settings()

# Reference values for normalisation
_REF_PRICE_MID     = 500.0     # "typical" mid-range product price (yuan)
_REF_SALES_HIGH    = 50000     # ≥ this → 100 pts
_REF_REVIEWS_HIGH  = 10000     # ≥ this → 100 pts
_REF_SPECS_PER_YUAN = 0.05     # specs/yuan reference ratio


def _grade(score: float) -> Grade:
    if score >= 85:
        return Grade.A
    if score >= 70:
        return Grade.B
    if score >= 55:
        return Grade.C
    return Grade.D


def _price_score(price: float, original: float | None, promotion: bool) -> float:
    """Score based on discount depth and absolute price level."""
    if price <= 0:
        return 50.0

    # Discount factor
    if original and original > price:
        discount_pct = (original - price) / original
        disc_score = min(100.0, 50.0 + discount_pct * 100.0)
    else:
        disc_score = 50.0

    # Price competitiveness (lower is better, normalised around reference)
    ratio = price / _REF_PRICE_MID
    if ratio <= 0.5:
        comp_score = 100.0
    elif ratio <= 1.5:
        comp_score = 100.0 - (ratio - 0.5) * 50.0
    else:
        comp_score = max(10.0, 50.0 - (ratio - 1.5) * 30.0)

    score = disc_score * 0.4 + comp_score * 0.6
    if promotion:
        score = min(100.0, score + 5.0)
    return round(score, 2)


def _popularity_score(sales_count: int, review_count: int) -> float:
    """Log-scaled popularity from sales + review volume."""
    if sales_count <= 0 and review_count <= 0:
        return 20.0

    sales_score = (
        math.log10(sales_count + 1) / math.log10(_REF_SALES_HIGH + 1) * 100
        if sales_count > 0 else 0.0
    )
    review_score = (
        math.log10(review_count + 1) / math.log10(_REF_REVIEWS_HIGH + 1) * 100
        if review_count > 0 else 0.0
    )

    score = min(100.0, sales_score * 0.6 + review_score * 0.4)
    return round(score, 2)


def _rating_score(avg_rating: float, review_count: int) -> float:
    """Rating weighted by review count trust."""
    if avg_rating <= 0:
        return 40.0

    base = (avg_rating / 5.0) * 100.0

    if review_count >= 1000:
        trust = 1.0
    elif review_count >= 100:
        trust = 0.85 + (review_count - 100) / 900 * 0.15
    elif review_count >= 10:
        trust = 0.65 + (review_count - 10) / 90 * 0.20
    else:
        trust = max(0.5, review_count / 10 * 0.65)

    return round(base * trust, 2)


def _availability_score(in_stock: bool, delivery_days: int | None) -> float:
    """Stock status + estimated delivery speed."""
    if not in_stock:
        return 15.0
    days = delivery_days if delivery_days is not None else 5
    if days <= 1:
        return 100.0
    if days <= 3:
        return 100.0 - (days - 1) / 2 * 15.0
    if days <= 7:
        return 85.0 - (days - 3) / 4 * 25.0
    return max(30.0, 60.0 - (days - 7) * 3.0)


def _value_for_money_score(price: float, spec_count: int, avg_rating: float) -> float:
    """Specs-per-yuan ratio combined with rating efficiency."""
    if price <= 0:
        return 50.0

    ratio = spec_count / price
    if ratio >= _REF_SPECS_PER_YUAN:
        vfm_base = min(100.0, 75.0 + (ratio / _REF_SPECS_PER_YUAN - 1) * 10.0)
    else:
        vfm_base = max(10.0, ratio / _REF_SPECS_PER_YUAN * 75.0)

    # Blend with rating efficiency
    rating_eff = (avg_rating / 5.0) * 100.0 / (price / 100.0 + 1)
    return round(max(0.0, min(100.0, vfm_base * 0.7 + min(100.0, rating_eff * 3) * 0.3)), 2)


def _data_completeness(p: RawProduct) -> float:
    """Fraction of important fields present."""
    checks = [
        bool(p.title),
        p.price > 0,
        bool(p.brand),
        bool(p.category),
        p.review_count > 0,
        p.sales_count > 0,
        p.average_rating > 0,
        bool(p.specs),
        bool(p.images),
        p.delivery_days is not None,
        bool(p.shop_name),
    ]
    return round(sum(checks) / len(checks), 3)


class ProductScorer:
    """Pre-computes ProductScore for a cleaned RawProduct."""

    def score(self, product: RawProduct) -> ProductScore:
        w = settings

        ps  = _price_score(product.price, product.original_price, product.promotion)
        pop = _popularity_score(product.sales_count, product.review_count)
        rs  = _rating_score(product.average_rating, product.review_count)
        avs = _availability_score(product.in_stock, product.delivery_days)
        vfm = _value_for_money_score(
            product.price, len(product.specs), product.average_rating
        )

        total = round(
            ps  * w.weight_price
            + pop * w.weight_popularity
            + rs  * w.weight_rating
            + avs * w.weight_availability
            + vfm * w.weight_value,
            2,
        )
        total = max(0.0, min(100.0, total))
        completeness = _data_completeness(product)

        return ProductScore(
            total_score           = total,
            grade                 = _grade(total),
            price_score           = ps,
            popularity_score      = pop,
            rating_score          = rs,
            availability_score    = avs,
            value_for_money_score = vfm,
            data_completeness     = completeness,
        )

    def score_batch(self, products: List[RawProduct]) -> List[ProductScore]:
        return [self.score(p) for p in products]


# Singleton
product_scorer = ProductScorer()
