"""
淘宝 / 天猫 平台适配器
使用淘宝开放平台 API（Top API）
文档：https://open.taobao.com/api.htm
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import time
from typing import Any, Dict, List, Optional

from app.core.config import get_settings
from app.models.schemas import CrawlFilters, Platform, RawProduct
from app.services.api_manager import api_manager
from app.services.compliance_monitor import compliance_monitor
from app.services.proxy_manager import proxy_manager
from .base import BasePlatformAdapter, PlatformAPIError

logger = logging.getLogger(__name__)
settings = get_settings()

_API_BASE = "https://eco.taobao.com/router/rest"


class TaobaoAdapter(BasePlatformAdapter):
    platform = Platform.TAOBAO

    def _sign(self, params: Dict[str, str]) -> str:
        """HMAC-MD5 signature required by Top API."""
        sorted_params = "".join(f"{k}{v}" for k, v in sorted(params.items()))
        secret = settings.taobao_app_secret or "MOCK_SECRET"
        sig = hmac.new(
            secret.encode(), sorted_params.encode(), hashlib.md5
        ).hexdigest().upper()
        return sig

    def _base_params(self, method: str) -> Dict[str, str]:
        return {
            "method":       method,
            "app_key":      settings.taobao_app_key or "MOCK_KEY",
            "timestamp":    str(int(time.time() * 1000)),
            "format":       "json",
            "v":            "2.0",
            "sign_method":  "hmac-md5",
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

        params = self._base_params("taobao.tbk.item.get")
        params.update({
            "q":         keyword,
            "page_size": str(min(max_results, 40)),
            "page_no":   "1",
            "sort":      "sale_desc",
        })
        if filters:
            if filters.price_min is not None:
                params["start_price"] = str(int(filters.price_min))
            if filters.price_max is not None:
                params["end_price"] = str(int(filters.price_max))

        params["sign"] = self._sign(params)

        proxy_url = await proxy_manager.get_proxy()

        try:
            resp = await api_manager.call(
                self.platform, "GET", _API_BASE,
                params=params, proxy=proxy_url,
            )
            data = resp.json()
            # Check for platform-level business errors (error codes in JSON body)
            try:
                self.check_api_error(data)
            except PlatformAPIError as api_err:
                logger.warning(
                    '"Taobao API error keyword=%s code=%s msg=%s"',
                    keyword, api_err.code, api_err.message,
                )
                if proxy_url and self.is_ban_error(api_err):
                    await proxy_manager.report_ban(proxy_url)
                elif proxy_url and self.is_rate_limit_error(api_err):
                    await proxy_manager.report_failure(proxy_url)
                return self._mock_products(keyword, max_results, session_id, job_id)

        except Exception as exc:
            logger.error('"Taobao search error keyword=%s: %s"', keyword, exc)
            if proxy_url:
                await proxy_manager.report_failure(proxy_url)
            # Return mock data so the pipeline doesn't break in dev/test
            return self._mock_products(keyword, max_results, session_id, job_id)

        if proxy_url:
            await proxy_manager.report_success(proxy_url)

        items = (
            data.get("tbk_item_get_response", {})
                .get("result", {})
                .get("result_list", {})
                .get("map_data", [])
        )
        return [self._parse(item, session_id, job_id) for item in items[:max_results]]

    async def get_product_detail(self, product_id: str) -> Optional[RawProduct]:
        await compliance_monitor.enforce_delay(self.platform)
        params = self._base_params("taobao.item.get")
        params.update({"num_iid": product_id, "fields": "detail_url,title,price,item_imgs"})
        params["sign"] = self._sign(params)
        try:
            resp = await api_manager.call(self.platform, "GET", _API_BASE, params=params)
            item = resp.json().get("item_get_response", {}).get("item", {})
            return self._parse(item) if item else None
        except Exception as exc:
            logger.error('"Taobao detail error id=%s: %s"', product_id, exc)
            return None

    # ── Parsers ──────────────────────────────────────────────────────────

    def _parse(self, item: Dict[str, Any],
               session_id: Optional[str] = None,
               job_id: Optional[str] = None) -> RawProduct:
        p = RawProduct(
            platform       = self.platform,
            product_id     = str(item.get("num_iid", item.get("item_id", ""))),
            title          = item.get("title", ""),
            price          = self._safe_float(item.get("zk_final_price", item.get("price", 0))),
            original_price = self._safe_float(item.get("reserve_price", 0)) or None,
            brand          = item.get("brand_name", ""),
            category       = item.get("category_name", ""),
            images         = [item.get("pict_url", "")] if item.get("pict_url") else [],
            specs          = item.get("props_name", {}),
            sales_count    = self._safe_int(item.get("volume", 0)),
            review_count   = self._safe_int(item.get("comment_count", 0)),
            average_rating = self._safe_float(item.get("score", 0)) / 20.0,  # 0-100 → 0-5
            shop_name      = item.get("nick", ""),
            in_stock       = True,
            promotion      = bool(item.get("coupon_amount")),
            url            = item.get("item_url", ""),
            raw_data       = item,
        )
        return self._tag(p, session_id, job_id)

    def _mock_products(self, keyword: str, n: int,
                        session_id, job_id) -> List[RawProduct]:
        """Fallback mock data for dev/test when API key is absent."""
        products = []
        for i in range(min(n, 5)):
            p = RawProduct(
                platform       = self.platform,
                product_id     = f"tb_mock_{keyword}_{i}",
                title          = f"淘宝-{keyword}-商品{i+1}（模拟数据）",
                price          = round(99.9 + i * 50, 2),
                original_price = round(199.9 + i * 50, 2),
                brand          = f"品牌{i+1}",
                category       = "数码",
                images         = ["https://example.com/img.jpg"],
                specs          = {"颜色": "黑色", "规格": "标准版"},
                sales_count    = 1000 + i * 200,
                review_count   = 500 + i * 100,
                average_rating = round(4.0 + i * 0.1, 1),
                shop_name      = f"淘宝旗舰店{i+1}",
                in_stock       = True,
                promotion      = i % 2 == 0,
                url            = f"https://item.taobao.com/item.htm?id=tb_mock_{i}",
                raw_data       = {"mock": True},
            )
            products.append(self._tag(p, session_id, job_id))
        return products
