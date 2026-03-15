"""
1688 (阿里巴巴B2B) 平台适配器
API 文档：https://open.1688.com/api/
"""
from __future__ import annotations

import hashlib
import logging
import time
from typing import Any, Dict, List, Optional

from app.core.config import get_settings
from app.models.schemas import CrawlFilters, Platform, RawProduct
from app.services.api_manager import api_manager
from app.services.compliance_monitor import compliance_monitor
from app.services.proxy_manager import proxy_manager
from .base import BasePlatformAdapter

logger = logging.getLogger(__name__)
settings = get_settings()

_API_BASE  = "https://gw.open.1688.com/openapi/http/1/system.gw/alibaba.product.search/1"
_API_PATH  = "/openapi/http/1/system.gw/alibaba.product.search/1"   # used in sign


class Ali1688Adapter(BasePlatformAdapter):
    platform = Platform.ALI1688

    def _sign(self, params: Dict[str, str], path: str = _API_PATH) -> str:
        """1688 open-platform sign: secret + path + sorted(k+v) + secret → MD5 upper."""
        secret = settings.ali1688_app_secret or "MOCK_SECRET"
        sorted_str = "".join(f"{k}{v}" for k, v in sorted(params.items()))
        body = path + sorted_str
        return hashlib.md5((secret + body + secret).encode()).hexdigest().upper()

    async def search(
        self,
        keyword: str,
        max_results: int = 20,
        filters: Optional[CrawlFilters] = None,
        session_id: Optional[str] = None,
        job_id: Optional[str] = None,
    ) -> List[RawProduct]:
        await compliance_monitor.enforce_delay(self.platform)

        params: Dict[str, str] = {
            "app_key":  settings.ali1688_app_key or "MOCK_KEY",
            "timestamp": str(int(time.time() * 1000)),
            "keywords": keyword,
            "beginPage": "1",
            "pageSize":  str(min(max_results, 20)),
        }
        if filters:
            if filters.price_min is not None:
                params["priceStart"] = str(int(filters.price_min))
            if filters.price_max is not None:
                params["priceEnd"] = str(int(filters.price_max))

        # Sign must be computed after all business params are set
        params["sign"] = self._sign(params)

        proxy_url = await proxy_manager.get_proxy()

        try:
            resp = await api_manager.call(
                self.platform, "GET", _API_BASE,
                params=params, proxy=proxy_url,
            )
            data = resp.json()
        except Exception as exc:
            logger.error('"1688 search error keyword=%s: %s"', keyword, exc)
            if proxy_url:
                await proxy_manager.report_failure(proxy_url)
            return self._mock_products(keyword, max_results, session_id, job_id)

        if proxy_url:
            await proxy_manager.report_success(proxy_url)

        items = data.get("result", {}).get("postList", [])
        return [self._parse(item, session_id, job_id) for item in items[:max_results]]

    async def get_product_detail(self, product_id: str) -> Optional[RawProduct]:
        return None  # Requires separate detail API call

    def _parse(self, item: Dict[str, Any],
               session_id: Optional[str] = None,
               job_id: Optional[str] = None) -> RawProduct:
        price_info = item.get("tradePrice", {})
        p = RawProduct(
            platform       = self.platform,
            product_id     = str(item.get("offerId", "")),
            title          = item.get("subject", ""),
            price          = self._safe_float(price_info.get("price", 0)),
            brand          = item.get("companyName", ""),
            category       = item.get("bizType", ""),
            images         = [item.get("image", {}).get("imgUrl", "")],
            specs          = {k: str(v) for k, v in item.get("attributes", {}).items()},
            sales_count    = self._safe_int(item.get("saleCount", 0)),
            review_count   = self._safe_int(item.get("repurchaseRate", 0)),
            average_rating = self._safe_float(item.get("gmvScore", 0)) / 20.0,
            shop_name      = item.get("companyName", ""),
            shop_rating    = self._safe_float(item.get("compositeServiceScore", 0)),
            in_stock       = item.get("tradeType") != "sold_out",
            url            = item.get("detailUrl", ""),
            raw_data       = item,
        )
        return self._tag(p, session_id, job_id)

    def _mock_products(self, keyword: str, n: int, session_id, job_id) -> List[RawProduct]:
        products = []
        for i in range(min(n, 5)):
            p = RawProduct(
                platform       = self.platform,
                product_id     = f"1688_mock_{keyword}_{i}",
                title          = f"1688-{keyword}-批发商品{i+1}（模拟数据）",
                price          = round(29.9 + i * 10, 2),
                brand          = f"供应商{i+1}",
                category       = "工业品",
                specs          = {"最小起订量": "10件", "材质": "铝合金"},
                sales_count    = 5000 + i * 1000,
                review_count   = 100 + i * 20,
                average_rating = round(4.5 + i * 0.05, 1),
                shop_name      = f"1688供应商{i+1}",
                in_stock       = True,
                raw_data       = {"mock": True},
            )
            products.append(self._tag(p, session_id, job_id))
        return products
