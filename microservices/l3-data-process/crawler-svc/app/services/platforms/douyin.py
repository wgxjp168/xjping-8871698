"""
抖音小店 / 抖音电商开放平台适配器
API 文档：https://op.jinritemai.com/
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

_API_BASE = "https://openapi-fxg.jinritemai.com/api"


class DouyinAdapter(BasePlatformAdapter):
    platform = Platform.DOUYIN

    def _sign(self, method: str, params: Dict[str, str], timestamp: str) -> str:
        secret = settings.douyin_app_secret or "MOCK_SECRET"
        app_key = settings.douyin_app_key or "MOCK_KEY"
        param_str = "".join(f"{k}={v}" for k, v in sorted(params.items()))
        body = f"app_key{app_key}method{method}param_json{param_str}timestamp{timestamp}v2"
        return hashlib.md5((secret + body + secret).encode()).hexdigest()

    async def search(
        self,
        keyword: str,
        max_results: int = 20,
        filters: Optional[CrawlFilters] = None,
        session_id: Optional[str] = None,
        job_id: Optional[str] = None,
    ) -> List[RawProduct]:
        await compliance_monitor.enforce_delay(self.platform)

        timestamp = str(int(time.time()))
        inner_params: Dict[str, str] = {
            "keyword":   keyword,
            "page":      "0",
            "page_size": str(min(max_results, 50)),
        }
        if filters and filters.price_min is not None:
            inner_params["price_min"] = str(int(filters.price_min * 100))
        if filters and filters.price_max is not None:
            inner_params["price_max"] = str(int(filters.price_max * 100))

        method = "product.search"
        params = {
            "method":     method,
            "app_key":    settings.douyin_app_key or "MOCK_KEY",
            "timestamp":  timestamp,
            "v":          "2",
            "param_json": str(inner_params),
            "sign":       self._sign(method, inner_params, timestamp),
        }

        proxy_url = await proxy_manager.get_proxy()

        try:
            resp = await api_manager.call(
                self.platform, "POST", _API_BASE,
                params=params, proxy=proxy_url,
            )
            data = resp.json()
        except Exception as exc:
            logger.error('"Douyin search error keyword=%s: %s"', keyword, exc)
            if proxy_url:
                await proxy_manager.report_failure(proxy_url)
            return self._mock_products(keyword, max_results, session_id, job_id)

        if proxy_url:
            await proxy_manager.report_success(proxy_url)

        items = data.get("data", {}).get("product_list", [])
        return [self._parse(item, session_id, job_id) for item in items[:max_results]]

    async def get_product_detail(self, product_id: str) -> Optional[RawProduct]:
        return None

    def _parse(self, item: Dict[str, Any],
               session_id: Optional[str] = None,
               job_id: Optional[str] = None) -> RawProduct:
        price = self._safe_float(item.get("price", 0)) / 100.0
        orig  = self._safe_float(item.get("market_price", 0)) / 100.0
        p = RawProduct(
            platform       = self.platform,
            product_id     = str(item.get("product_id", "")),
            title          = item.get("name", ""),
            price          = round(price, 2),
            original_price = round(orig, 2) if orig > price else None,
            brand          = item.get("brand_name", ""),
            category       = item.get("first_cid_name", ""),
            images         = [item.get("img", "")],
            specs          = {sp["name"]: sp["value"]
                              for sp in item.get("specs", [])
                              if "name" in sp and "value" in sp},
            sales_count    = self._safe_int(item.get("sales", 0)),
            review_count   = self._safe_int(item.get("comment_count", 0)),
            average_rating = self._safe_float(item.get("score", 0)) / 20.0,
            shop_name      = item.get("shop_name", ""),
            in_stock       = item.get("stock", 0) > 0,
            promotion      = bool(item.get("coupon")),
            url            = f"https://haohuo.jinritemai.com/views/product/item?id={item.get('product_id','')}",
            raw_data       = item,
        )
        return self._tag(p, session_id, job_id)

    def _mock_products(self, keyword: str, n: int, session_id, job_id) -> List[RawProduct]:
        products = []
        for i in range(min(n, 5)):
            p = RawProduct(
                platform       = self.platform,
                product_id     = f"dy_mock_{keyword}_{i}",
                title          = f"抖音-{keyword}-爆款{i+1}（模拟数据）",
                price          = round(49.9 + i * 25, 2),
                original_price = round(129.9 + i * 40, 2),
                brand          = f"品牌{i+1}",
                category       = "生活用品",
                specs          = {"款式": "A款", "材质": "棉"},
                sales_count    = 5000 + i * 1500,
                review_count   = 1200 + i * 300,
                average_rating = round(4.6 + i * 0.04, 1),
                shop_name      = f"抖音小店{i+1}",
                in_stock       = True,
                promotion      = True,
                raw_data       = {"mock": True},
            )
            products.append(self._tag(p, session_id, job_id))
        return products
