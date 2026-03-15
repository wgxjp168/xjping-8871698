"""
拼多多开放平台适配器
API 文档：https://open.pinduoduo.com/
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

_API_BASE = "https://gw-api.pinduoduo.com/api/router"


class PinduoduoAdapter(BasePlatformAdapter):
    platform = Platform.PDD

    def _sign(self, params: Dict[str, str]) -> str:
        secret = settings.pdd_client_secret or "MOCK_SECRET"
        body = secret + "".join(f"{k}{v}" for k, v in sorted(params.items())) + secret
        return hashlib.md5(body.encode()).hexdigest().upper()

    def _base_params(self, method: str) -> Dict[str, str]:
        return {
            "type":       method,
            "client_id":  settings.pdd_client_id or "MOCK_ID",
            "timestamp":  str(int(time.time())),
            "data_type":  "JSON",
            "version":    "V1",
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

        params = self._base_params("pdd.ddk.goods.search")
        params.update({
            "keyword":   keyword,
            "page_size": str(min(max_results, 100)),
            "page":      "1",
            "sort_type": "0",
        })
        if filters:
            if filters.price_min is not None:
                params["min_price"] = str(int(filters.price_min * 100))  # PDD uses fen
            if filters.price_max is not None:
                params["max_price"] = str(int(filters.price_max * 100))

        params["sign"] = self._sign(params)
        proxy_url = await proxy_manager.get_proxy()

        try:
            resp = await api_manager.call(
                self.platform, "POST", _API_BASE,
                params=params, proxy=proxy_url,
            )
            data = resp.json()
        except Exception as exc:
            logger.error('"PDD search error keyword=%s: %s"', keyword, exc)
            if proxy_url:
                await proxy_manager.report_failure(proxy_url)
            return self._mock_products(keyword, max_results, session_id, job_id)

        if proxy_url:
            await proxy_manager.report_success(proxy_url)

        items = data.get("goods_search_response", {}).get("goods_list", [])
        return [self._parse(item, session_id, job_id) for item in items[:max_results]]

    async def get_product_detail(self, product_id: str) -> Optional[RawProduct]:
        return None

    def _parse(self, item: Dict[str, Any],
               session_id: Optional[str] = None,
               job_id: Optional[str] = None) -> RawProduct:
        # PDD prices are in fen (1 yuan = 100 fen)
        price_fen = item.get("min_group_price", item.get("min_normal_price", 0))
        orig_fen  = item.get("market_fee", 0)
        p = RawProduct(
            platform       = self.platform,
            product_id     = str(item.get("goods_id", "")),
            title          = item.get("goods_name", ""),
            price          = round(self._safe_float(price_fen) / 100, 2),
            original_price = round(self._safe_float(orig_fen) / 100, 2) or None,
            brand          = item.get("brand_name", ""),
            category       = item.get("category_name", ""),
            images         = [item.get("goods_thumbnail_url", "")],
            specs          = {},
            sales_count    = self._safe_int(item.get("sales_tip", "0")),
            review_count   = self._safe_int(item.get("goods_eval_count", 0)),
            average_rating = self._safe_float(item.get("goods_eval_score", "0")),
            shop_name      = item.get("mall_name", ""),
            in_stock       = True,
            promotion      = bool(item.get("coupon_props")),
            url            = item.get("goods_url_schema", ""),
            raw_data       = item,
        )
        return self._tag(p, session_id, job_id)

    def _mock_products(self, keyword: str, n: int, session_id, job_id) -> List[RawProduct]:
        products = []
        for i in range(min(n, 5)):
            p = RawProduct(
                platform       = self.platform,
                product_id     = f"pdd_mock_{keyword}_{i}",
                title          = f"拼多多-{keyword}-商品{i+1}（模拟数据）",
                price          = round(39.9 + i * 20, 2),
                original_price = round(79.9 + i * 20, 2),
                brand          = f"品牌{i+1}",
                category       = "消费品",
                specs          = {"规格": "默认"},
                sales_count    = 10000 + i * 2000,
                review_count   = 3000 + i * 500,
                average_rating = round(4.7 + i * 0.05, 1),
                shop_name      = f"拼多多旗舰店{i+1}",
                in_stock       = True,
                promotion      = True,
                raw_data       = {"mock": True},
            )
            products.append(self._tag(p, session_id, job_id))
        return products
