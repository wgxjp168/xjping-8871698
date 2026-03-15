"""
Abstract base class for all platform adapters.
"""
from __future__ import annotations

import abc
import logging
from typing import Any, Dict, List, Optional, Tuple

from app.models.schemas import CrawlFilters, Platform, RawProduct

logger = logging.getLogger(__name__)


class PlatformAPIError(Exception):
    """Raised when the platform returns a business-level error code (not a network error)."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


# ── Per-platform error-code extraction rules ─────────────────────────────────
# Each entry: (error_code_path, error_msg_path)  —  dot-separated JSON paths.
# e.g. "error_response.code" → data["error_response"]["code"]

_ERROR_PATH_MAP: Dict[Platform, Tuple[str, str]] = {
    Platform.TAOBAO:  ("error_response.code",  "error_response.zh_desc"),
    Platform.JD:      ("error_response.code",  "error_response.zh_desc"),
    Platform.ALI1688: ("result.errorCode",     "result.errorMsg"),
    Platform.PDD:     ("error_response.error_code", "error_response.error_msg"),
    Platform.VIPSHOP: ("returnCode",           "returnMsg"),
    Platform.SUNING:  ("returnValue.errorCode", "returnValue.errorMsg"),
    Platform.DOUYIN:  ("code",                 "msg"),
}

# Error codes that mean "quota exhausted / rate limited" → should back-off
_RATE_LIMIT_CODES = {"27",  "88",  "50",  "limitSellBuy", "10070",
                     "1071", "rate_limit_exceeded"}

# Error codes that mean "access forbidden / IP banned" → flag proxy ban
_BAN_CODES = {"50",  "403",  "27",  "ISP_PERMISSION_DENY",
              "invalid-sessionkey", "10010", "forbidden"}


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

    # ── Error-code parsing ────────────────────────────────────────────────

    def check_api_error(self, data: Dict[str, Any]) -> None:
        """
        Parse the JSON response body for platform-level business error codes.
        Raises PlatformAPIError if an error is detected.
        This must be called before extracting product items from `data`.
        """
        code_path, msg_path = _ERROR_PATH_MAP.get(
            self.platform, ("error_response.code", "error_response.zh_desc")
        )
        code = self._get_nested(data, code_path)
        if code is None:
            return   # no error field → success
        msg = self._get_nested(data, msg_path) or ""
        raise PlatformAPIError(str(code), str(msg))

    def is_rate_limit_error(self, exc: PlatformAPIError) -> bool:
        return exc.code in _RATE_LIMIT_CODES

    def is_ban_error(self, exc: PlatformAPIError) -> bool:
        return exc.code in _BAN_CODES

    # ── Metadata tagging ─────────────────────────────────────────────────

    def _tag(self, product: RawProduct, session_id: Optional[str],
             job_id: Optional[str]) -> RawProduct:
        """Helper: attach session / job metadata."""
        product.session_id = session_id
        product.job_id     = job_id
        return product

    # ── Type coercion helpers ─────────────────────────────────────────────

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

    # ── Internal helpers ──────────────────────────────────────────────────

    @staticmethod
    def _get_nested(data: Dict[str, Any], dot_path: str) -> Optional[Any]:
        """Traverse a dot-separated key path in a nested dict."""
        node: Any = data
        for key in dot_path.split("."):
            if not isinstance(node, dict):
                return None
            node = node.get(key)
            if node is None:
                return None
        return node
