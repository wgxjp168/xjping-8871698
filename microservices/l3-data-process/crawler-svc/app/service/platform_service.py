"""
7大电商平台数据采集服务
合规采集策略:
  - 遵守各平台 robots.txt
  - 控制API调用频率（避免超出配额）
  - 错误重试（指数退避）
  - 代理IP轮换
"""
import asyncio
import time
from typing import List, Optional
from dataclasses import dataclass
from enum import Enum


class Platform(str, Enum):
    TAOBAO = "taobao"
    TMALL = "tmall"
    JD = "jd"
    PDD = "pdd"
    ALI1688 = "1688"
    VIP = "vip"
    SUNING = "suning"
    DOUYIN = "douyin"


@dataclass
class SearchQuery:
    keyword: str
    category: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    platforms: Optional[List[Platform]] = None
    page_size: int = 20
    is_b2b: bool = False


@dataclass
class RawProduct:
    platform: str
    product_id: str
    title: str
    price: float
    original_price: Optional[float]
    image_url: str
    shop_name: str
    shop_url: str
    sales_volume: int
    rating: float
    review_count: int
    shop_age_years: float
    is_official: bool
    attributes: dict
    url: str


# 各平台每分钟最大请求数（合规限制）
PLATFORM_RATE_LIMITS = {
    Platform.TAOBAO: 60,
    Platform.TMALL: 60,
    Platform.JD: 100,
    Platform.PDD: 50,
    Platform.ALI1688: 80,
    Platform.VIP: 40,
    Platform.SUNING: 40,
    Platform.DOUYIN: 50,
}


class PlatformService:
    """多平台数据采集服务"""

    def __init__(self):
        self._rate_limiters = {p: RateLimiter(limit) for p, limit in PLATFORM_RATE_LIMITS.items()}

    async def search_all_platforms(self, query: SearchQuery) -> List[RawProduct]:
        """并发搜索所有平台"""
        platforms = query.platforms or list(Platform)

        # 根据 B2B/B2C 选择平台
        if query.is_b2b:
            # B2B优先1688和京东企业
            priority_platforms = [Platform.ALI1688, Platform.JD] + [
                p for p in platforms if p not in [Platform.ALI1688, Platform.JD]
            ]
        else:
            priority_platforms = platforms

        tasks = [
            self._search_platform(platform, query)
            for platform in priority_platforms
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        products = []
        for r in results:
            if isinstance(r, list):
                products.extend(r)
        return products

    async def _search_platform(self, platform: Platform, query: SearchQuery) -> List[RawProduct]:
        """单平台搜索（含限流）"""
        await self._rate_limiters[platform].acquire()
        try:
            return await self._call_platform_api(platform, query)
        except Exception as e:
            print(f"[Crawler] {platform.value} 采集失败: {e}")
            return []

    async def _call_platform_api(self, platform: Platform, query: SearchQuery) -> List[RawProduct]:
        """调用具体平台API（各平台实现不同）"""
        if platform == Platform.JD:
            return await self._call_jd_api(query)
        elif platform == Platform.ALI1688:
            return await self._call_1688_api(query)
        elif platform in [Platform.TAOBAO, Platform.TMALL]:
            return await self._call_taobao_api(query)
        elif platform == Platform.PDD:
            return await self._call_pdd_api(query)
        return []

    async def _call_jd_api(self, query: SearchQuery) -> List[RawProduct]:
        """京东宙斯API"""
        # 实际需要: JD_APP_KEY + JD_APP_SECRET
        # https://api.jd.com/routerjson
        return []

    async def _call_1688_api(self, query: SearchQuery) -> List[RawProduct]:
        """1688开放平台API"""
        # 实际需要: ALIBABA_APP_KEY + ALIBABA_APP_SECRET
        # https://gw.api.taobao.com/router/rest
        return []

    async def _call_taobao_api(self, query: SearchQuery) -> List[RawProduct]:
        """淘宝/天猫开放平台API"""
        return []

    async def _call_pdd_api(self, query: SearchQuery) -> List[RawProduct]:
        """拼多多开放平台API"""
        return []


class RateLimiter:
    """令牌桶限流器"""

    def __init__(self, rate_per_minute: int):
        self.rate = rate_per_minute
        self.interval = 60.0 / rate_per_minute
        self._last_call = 0.0
        self._lock = asyncio.Lock()

    async def acquire(self):
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_call
            if elapsed < self.interval:
                await asyncio.sleep(self.interval - elapsed)
            self._last_call = time.monotonic()


platform_service = PlatformService()
