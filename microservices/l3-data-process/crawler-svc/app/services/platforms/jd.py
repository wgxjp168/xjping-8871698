"""
京东开放平台适配器
API 文档：https://jos.jd.com/api/index
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
from .base import BasePlatformAdapter, PlatformAPIError

logger = logging.getLogger(__name__)
settings = get_settings()

_API_BASE = "https://api.jd.com/routerjson"


class JDAdapter(BasePlatformAdapter):
    platform = Platform.JD

    def _sign(self, params: Dict[str, str]) -> str:
        secret = settings.jd_app_secret or "MOCK_SECRET"
        body = secret + "".join(f"{k}{v}" for k, v in sorted(params.items())) + secret
        return hashlib.md5(body.encode()).hexdigest().upper()

    def _base_params(self, method: str) -> Dict[str, str]:
        return {
            "method":     method,
            "app_key":    settings.jd_app_key or "MOCK_KEY",
            "timestamp":  str(int(time.time() * 1000)),
            "format":     "json",
            "v":          "1.0",
            "sign_method": "md5",
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

        params = self._base_params("jd.union.open.goods.query")
        params.update({
            "goodsReqDTO": f'{{"keyword":"{keyword}","pageIndex":1,"pageSize":{min(max_results, 30)}}}',
        })
        params["sign"] = self._sign(params)

        proxy_url = await proxy_manager.get_proxy()

        try:
            resp = await api_manager.call(
                self.platform, "POST", _API_BASE,
                params=params, proxy=proxy_url,
            )
            data = resp.json()
            try:
                self.check_api_error(data)
            except PlatformAPIError as api_err:
                logger.warning(
                    '"JD API error keyword=%s code=%s msg=%s"',
                    keyword, api_err.code, api_err.message,
                )
                if proxy_url and self.is_ban_error(api_err):
                    await proxy_manager.report_ban(proxy_url)
                elif proxy_url and self.is_rate_limit_error(api_err):
                    await proxy_manager.report_failure(proxy_url)
                return self._mock_products(keyword, max_results, session_id, job_id)

        except Exception as exc:
            logger.error('"JD search error keyword=%s: %s"', keyword, exc)
            if proxy_url:
                await proxy_manager.report_failure(proxy_url)
            return self._mock_products(keyword, max_results, session_id, job_id)

        if proxy_url:
            await proxy_manager.report_success(proxy_url)

        items = (
            data.get("queryResult", {})
                .get("data", {})
                .get("result", [])
        )
        return [self._parse(item, session_id, job_id) for item in items[:max_results]]

    async def get_product_detail(self, product_id: str) -> Optional[RawProduct]:
        await compliance_monitor.enforce_delay(self.platform)
        params = self._base_params("jd.union.open.goods.promotiongoodsinfo.query")
        params.update({"skuIds": product_id})
        params["sign"] = self._sign(params)
        try:
            resp = await api_manager.call(self.platform, "POST", _API_BASE, params=params)
            goods = resp.json().get("queryPromotionGoodsInfoResult", {}).get("data", [])
            return self._parse(goods[0]) if goods else None
        except Exception as exc:
            logger.error('"JD detail error id=%s: %s"', product_id, exc)
            return None

    def _parse(self, item: Dict[str, Any],
               session_id: Optional[str] = None,
               job_id: Optional[str] = None) -> RawProduct:
        goods = item.get("goodsInfo", item)
        price_info = item.get("priceInfo", {})
        p = RawProduct(
            platform       = self.platform,
            product_id     = str(goods.get("skuId", "")),
            title          = goods.get("skuName", ""),
            price          = self._safe_float(price_info.get("price", goods.get("lowestCouponPrice", 0))),
            original_price = self._safe_float(price_info.get("originalPrice", 0)) or None,
            brand          = goods.get("brandName", ""),
            category       = goods.get("cid3Name", ""),
            images         = [goods.get("imageInfo", {}).get("imageList", [{}])[0].get("url", "")],
            specs          = {},
            sales_count    = self._safe_int(goods.get("comments", 0)),
            review_count   = self._safe_int(goods.get("comments", 0)),
            average_rating = self._safe_float(goods.get("goodComments", "0").replace("%", "")) / 20.0,
            shop_name      = goods.get("shopInfo", {}).get("shopName", ""),
            in_stock       = True,
            promotion      = bool(item.get("couponInfo", {}).get("couponList")),
            url            = f"https://item.jd.com/{goods.get('skuId', '')}.html",
            raw_data       = item,
        )
        return self._tag(p, session_id, job_id)

    def _mock_products(self, keyword: str, n: int, session_id, job_id) -> List[RawProduct]:
        products = []
        for i in range(min(n, 5)):
            p = RawProduct(
                platform       = self.platform,
                product_id     = f"jd_mock_{keyword}_{i}",
                title          = f"京东-{keyword}-商品{i+1}（模拟数据）",
                price          = round(89.9 + i * 60, 2),
                original_price = round(189.9 + i * 60, 2),
                brand          = f"品牌{i+1}",
                category       = "数码",
                images         = ["https://example.com/img.jpg"],
                specs          = {"颜色": "白色", "版本": "国行"},
                sales_count    = 2000 + i * 300,
                review_count   = 800 + i * 150,
                average_rating = round(4.2 + i * 0.1, 1),
                shop_name      = f"京东自营{i+1}",
                in_stock       = True,
                promotion      = i % 3 == 0,
                url            = f"https://item.jd.com/jd_mock_{i}.html",
                raw_data       = {"mock": True},
            )
            products.append(self._tag(p, session_id, job_id))
        return products
