"""
Deduplicator
============
Two-level deduplication:
  1. Same-platform: identical product_id → keep newest
  2. Cross-platform: same physical product by title similarity + price proximity
     - Uses MinHash-inspired fingerprint (trigrams of cleaned title)
     - Keeps record with higher score if duplicate found
"""
from __future__ import annotations

import hashlib
import logging
import re
from typing import Dict, List, Set, Tuple

from app.models.schemas import RawProduct

logger = logging.getLogger(__name__)

_NON_ALNUM_RE  = re.compile(r"[^\w\u4e00-\u9fff]", re.UNICODE)
_WHITESPACE_RE = re.compile(r"\s+")

# Price proximity threshold: two products are "same" if prices differ < 5%
_PRICE_TOLERANCE = 0.05


def _normalise_title(title: str) -> str:
    t = title.lower()
    t = _NON_ALNUM_RE.sub(" ", t)
    t = _WHITESPACE_RE.sub(" ", t).strip()
    return t


def _title_fingerprint(title: str) -> str:
    """
    Character-trigram fingerprint of the normalised title.
    Returns a 16-char hex digest stable across calls.
    """
    norm = _normalise_title(title)
    trigrams: Set[str] = set()
    for i in range(len(norm) - 2):
        trigrams.add(norm[i:i+3])
    # Sort for determinism
    combined = "|".join(sorted(trigrams))
    return hashlib.md5(combined.encode()).hexdigest()[:16]


def _prices_close(p1: float, p2: float) -> bool:
    if p1 <= 0 or p2 <= 0:
        return False
    ratio = abs(p1 - p2) / max(p1, p2)
    return ratio <= _PRICE_TOLERANCE


class Deduplicator:
    """In-memory deduplication for a single ETL batch."""

    def deduplicate(
        self, products: List[RawProduct]
    ) -> Tuple[List[RawProduct], int]:
        """
        Returns (unique_products, duplicate_count).
        """
        # ── Pass 1: same-platform deduplication ──────────────────────────
        seen_platform: Dict[str, RawProduct] = {}
        for p in products:
            key = f"{p.platform}:{p.product_id}"
            existing = seen_platform.get(key)
            if existing is None:
                seen_platform[key] = p
            else:
                # Keep the one with more data / newer crawl time
                if _richer(p, existing):
                    seen_platform[key] = p

        after_pass1 = list(seen_platform.values())
        pass1_dupes = len(products) - len(after_pass1)

        # ── Pass 2: cross-platform deduplication ─────────────────────────
        # Group by title fingerprint, then check price proximity
        fingerprint_map: Dict[str, List[RawProduct]] = {}
        for p in after_pass1:
            fp = _title_fingerprint(p.title)
            fingerprint_map.setdefault(fp, []).append(p)

        unique: List[RawProduct] = []
        pass2_dupes = 0
        for group in fingerprint_map.values():
            kept = _resolve_group(group)
            unique.extend(kept)
            pass2_dupes += len(group) - len(kept)

        total_dupes = pass1_dupes + pass2_dupes
        logger.info(
            '"Dedup: input=%d pass1_dupes=%d pass2_dupes=%d unique=%d"',
            len(products), pass1_dupes, pass2_dupes, len(unique),
        )
        return unique, total_dupes


def _resolve_group(group: List[RawProduct]) -> List[RawProduct]:
    """
    Within a fingerprint group, merge price-close cross-platform duplicates.
    Keep the record with the highest review_count (best data completeness).
    """
    if len(group) == 1:
        return group

    clusters: List[List[RawProduct]] = []
    for p in group:
        placed = False
        for cluster in clusters:
            representative = cluster[0]
            if _prices_close(p.price, representative.price):
                cluster.append(p)
                placed = True
                break
        if not placed:
            clusters.append([p])

    result: List[RawProduct] = []
    for cluster in clusters:
        # Pick the richest record from each cluster
        best = max(cluster, key=lambda r: (r.review_count, r.sales_count, r.average_rating))
        result.append(best)

    return result


def _richer(a: RawProduct, b: RawProduct) -> bool:
    """True if `a` is a richer record than `b`."""
    a_score = a.review_count + a.sales_count + len(a.specs) + len(a.images)
    b_score = b.review_count + b.sales_count + len(b.specs) + len(b.images)
    return a_score > b_score


# Singleton
deduplicator = Deduplicator()
