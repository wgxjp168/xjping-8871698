"""
唯品会开放平台适配器
API 文档：https://open.vip.com/
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

_API_BASE = "https://gw.vipapis.com/gateway"


class VipshopAdapter(BasePlatformAdapter):
    platform = Platform.VIPSHOP

    def _sign(self, params: Dict[str, str]) -> str:
        secret = settings.vipshop_app_key or "MOCK_SECRET"
        body = "".join(f"{k}={v}" for k, v in sorted(params.items()))
        return hashlib.md5((secret + body).encode()).hexdigest()

    def _base_params(self, method: str) -> Dict[str, str]:
        return {
            "method":    method,
            "appKey":    settings.vipshop_app_key or "MOCK_KEY",
            "timestamp": str(int(time.time() * 1000)),
            "format":    "json",
            "v":         "1.0",
        }

    async def search(
        self,
        keyword: str,
        max_results: int = 20,
        filters: Optional[CrawlFilters] = None,
        session_id: Optional[str] = None,
        job_id: Optional[str] = None,
    ) -> List[RawProduct]:
        await compliance_monitor.enforce_delay(self.platform)

        params = self._base_params("vip.union.item.search")
        params.update({
            "keyword":  keyword,
            "pageNum":  "1",
            "pageSize": str(min(max_results, 20)),
        })
        params["sign"] = self._sign(params)
        proxy_url = await proxy_manager.get_proxy()

        try:
            resp = await api_manager.call(
                self.platform, "GET", _API_BASE,
                params=params, proxy=proxy_url,
            )
            data = resp.json()
        except Exception as exc:
            logger.error('"VipShop search error keyword=%s: %s"', keyword, exc)
            if proxy_url:
                await proxy_manager.report_failure(proxy_url)
            return self._mock_products(keyword, max_results, session_id, job_id)

        if proxy_url:
            await proxy_manager.report_success(proxy_url)

        items = data.get("data", {}).get("result", [])
        return [self._parse(item, session_id, job_id) for item in items[:max_results]]

    async def get_product_detail(self, product_id: str) -> Optional[RawProduct]:
        return None

    def _parse(self, item: Dict[str, Any],
               session_id: Optional[str] = None,
               job_id: Optional[str] = None) -> RawProduct:
        p = RawProduct(
            platform       = self.platform,
            product_id     = str(item.get("goodsId", "")),
            title          = item.get("goodsName", ""),
            price          = self._safe_float(item.get("vipPrice", 0)),
            original_price = self._safe_float(item.get("marketPrice", 0)) or None,
            brand          = item.get("brandName", ""),
            category       = item.get("catName", ""),
            images         = [item.get("goodsThumbUrl", "")],
            specs          = {},
            sales_count    = self._safe_int(item.get("saleNum", 0)),
            review_count   = self._safe_int(item.get("commentNum", 0)),
            average_rating = self._safe_float(item.get("score", 0)) / 20.0,
            shop_name      = item.get("brandName", ""),
            in_stock       = item.get("stockStatus") != 0,
            promotion      = bool(item.get("couponInfo")),
            url            = item.get("goodsUrl", ""),
            raw_data       = item,
        )
        return self._tag(p, session_id, job_id)

    def _mock_products(self, keyword: str, n: int, session_id, job_id) -> List[RawProduct]:
        products = []
        for i in range(min(n, 5)):
            p = RawProduct(
                platform       = self.platform,
                product_id     = f"vip_mock_{keyword}_{i}",
                title          = f"唯品会-{keyword}-特卖{i+1}（模拟数据）",
                price          = round(59.9 + i * 30, 2),
                original_price = round(199.9 + i * 60, 2),
                brand          = f"品牌{i+1}",
                category       = "服装",
                specs          = {"尺码": "M", "颜色": "蓝色"},
                sales_count    = 800 + i * 100,
                review_count   = 200 + i * 50,
                average_rating = round(4.3 + i * 0.1, 1),
                shop_name      = f"唯品会官方",
                in_stock       = True,
                promotion      = True,
                raw_data       = {"mock": True},
            )
            products.append(self._tag(p, session_id, job_id))
        return products
