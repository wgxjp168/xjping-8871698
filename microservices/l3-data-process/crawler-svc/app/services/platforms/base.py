"""
Abstract base class for all platform adapters.
"""
from __future__ import annotations

import abc
import logging
from typing import List, Optional

from app.models.schemas import CrawlFilters, Platform, RawProduct

logger = logging.getLogger(__name__)


class BasePlatformAdapter(abc.ABC):
    """
    Each platform subclass implements search() which returns a list of
    RawProduct.  The adapter is responsible for:
      - Signing requests (app_key / HMAC / OAuth2)
      - Parsing platform-specific response formats
      - Normalising fields to the canonical RawProduct schema
    """

    platform: Platform   # Must be set by subclass

    @abc.abstractmethod
    async def search(
        self,
        keyword: str,
        max_results: int = 20,
        filters: Optional[CrawlFilters] = None,
        session_id: Optional[str] = None,
        job_id: Optional[str] = None,
    ) -> List[RawProduct]:
        """Search platform for `keyword` and return raw product records."""

    @abc.abstractmethod
    async def get_product_detail(self, product_id: str) -> Optional[RawProduct]:
        """Fetch detailed info for a single product by platform ID."""

    def _tag(self, product: RawProduct, session_id: Optional[str],
             job_id: Optional[str]) -> RawProduct:
        """Helper: attach session / job metadata."""
        product.session_id = session_id
        product.job_id     = job_id
        return product

    def _safe_float(self, value, default: float = 0.0) -> float:
        try:
            return float(str(value).replace("¥", "").replace(",", "").strip())
        except (ValueError, TypeError):
            return default

    def _safe_int(self, value, default: int = 0) -> int:
        try:
            v = str(value).replace(",", "").strip()
            # Handle "1.2万" style
            if "万" in v:
                return int(float(v.replace("万", "")) * 10000)
            return int(float(v))
        except (ValueError, TypeError):
            return default
