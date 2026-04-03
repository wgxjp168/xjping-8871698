"""
local_simulation.py
ILbuy 本地多模态商品助手 - 无需外部 API 密钥的生产级测试系统

支持四种输入模式：
  - text  : 文字查询
  - voice : 语音输入（本地模拟 ASR）
  - image : 图片输入（本地模拟图像识别）
  - link  : 商品链接解析

运行方式：
  python local_simulation.py        # 快速演示
  python local_simulation.py test   # 综合测试
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import random
import re
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse, unquote

try:
    import requests as _req
    _HAS_REQUESTS = True
except ImportError:
    _HAS_REQUESTS = False

GATEWAY_URL = "http://localhost:8080"
BUYER_USERNAME = "buyer01"
BUYER_PASSWORD = "Test@123456"


# ── Fallback local product data (used when ILbuy gateway is unreachable) ─────
LOCAL_PRODUCTS: list[dict] = [
    {"id": "TB001", "title": "联想ThinkPad E14笔记本电脑 i5 16G 512G", "price": 5299.0, "originalPrice": 5999.0, "stock": 85, "sales": 3200, "category": "IT设备", "brand": "联想", "shopName": "联想官方旗舰店", "platform": "taobao", "platformName": "淘宝"},
    {"id": "TM001", "title": "苹果MacBook Pro 14寸 M3芯片", "price": 14999.0, "originalPrice": 15999.0, "stock": 45, "sales": 1800, "category": "IT设备", "brand": "苹果", "shopName": "Apple官方旗舰店", "platform": "tmall", "platformName": "天猫"},
    {"id": "JD001", "title": "Dell PowerEdge R750服务器 64G内存", "price": 28800.0, "originalPrice": 32000.0, "stock": 15, "sales": 320, "category": "IT设备", "brand": "戴尔", "shopName": "戴尔企业官方店", "platform": "jd", "platformName": "京东"},
    {"id": "JD004", "title": "思科Catalyst 2960-X 48口千兆交换机", "price": 4800.0, "originalPrice": 5600.0, "stock": 35, "sales": 680, "category": "IT设备", "brand": "思科", "shopName": "思科网络官方店", "platform": "jd", "platformName": "京东"},
    {"id": "TB004", "title": "A4复印纸70g 500张整箱8包装", "price": 158.0, "originalPrice": 188.0, "stock": 2000, "sales": 12000, "category": "办公用品", "brand": "得力", "shopName": "得力文具旗舰店", "platform": "taobao", "platformName": "淘宝"},
    {"id": "TM004", "title": "宜家IKEA MARKUS马库斯人体工学转椅", "price": 1499.0, "originalPrice": 1699.0, "stock": 120, "sales": 3800, "category": "办公用品", "brand": "宜家", "shopName": "宜家官方旗舰店", "platform": "tmall", "platformName": "天猫"},
    {"id": "TM007", "title": "英威腾变频器三相380V 7.5KW工业级", "price": 1280.0, "originalPrice": 1580.0, "stock": 65, "sales": 890, "category": "工业设备", "brand": "英威腾", "shopName": "英威腾官方旗舰店", "platform": "tmall", "platformName": "天猫"},
    {"id": "ALI001", "title": "不锈钢板材304 2mm冷轧钢板零切加工定制", "price": 28.5, "originalPrice": 0.0, "stock": 50000, "sales": 2300, "category": "原材料", "brand": "宝钢", "shopName": "宝钢钢材专营店", "platform": "1688", "platformName": "阿里巴巴1688"},
    {"id": "ALI005", "title": "工业级继电器8脚14脚24V220V小型电磁继电器", "price": 8.5, "originalPrice": 0.0, "stock": 50000, "sales": 68000, "category": "电子元件", "brand": "欧姆龙", "shopName": "欧姆龙配件专营店", "platform": "1688", "platformName": "阿里巴巴1688"},
    {"id": "ALI007", "title": "ARM STM32F103C8T6单片机最小系统板开发板", "price": 15.9, "originalPrice": 0.0, "stock": 20000, "sales": 35000, "category": "电子元件", "brand": "意法半导体", "shopName": "单片机专营店", "platform": "1688", "platformName": "阿里巴巴1688"},
]

LOCAL_MARKET_PRICES: list[dict] = [
    {"id": 1, "category": "IT设备", "productName": "商务笔记本电脑（i7/16G/512G）", "avgPrice": 6800.0, "minPrice": 4500.0, "maxPrice": 9800.0, "unit": "台"},
    {"id": 3, "category": "IT设备", "productName": "企业级服务器（Dell PowerEdge）", "avgPrice": 38000.0, "minPrice": 28000.0, "maxPrice": 65000.0, "unit": "台"},
    {"id": 7, "category": "办公用品", "productName": "A4复印纸（500张/包）", "avgPrice": 38.0, "minPrice": 25.0, "maxPrice": 55.0, "unit": "包"},
    {"id": 11, "category": "工业设备", "productName": "数控机床（三轴CNC）", "avgPrice": 85000.0, "minPrice": 60000.0, "maxPrice": 130000.0, "unit": "台"},
    {"id": 14, "category": "原材料", "productName": "不锈钢板（304# 2mm）", "avgPrice": 35.0, "minPrice": 22.0, "maxPrice": 52.0, "unit": "kg"},
    {"id": 16, "category": "电子元件", "productName": "工业级继电器模块", "avgPrice": 18.0, "minPrice": 8.0, "maxPrice": 32.0, "unit": "个"},
]


# ── ILbuy API client ──────────────────────────────────────────────────────────

class ILbuyClient:
    """HTTP client for the ILbuy API gateway. Falls back to local data on failure."""

    def __init__(self, base_url: str = GATEWAY_URL):
        self.base_url = base_url
        self._token: str | None = None
        self._available: bool | None = None  # None = not checked yet

    def _is_available(self) -> bool:
        if self._available is not None:
            return self._available
        if not _HAS_REQUESTS:
            self._available = False
            return False
        try:
            r = _req.get(f"{self.base_url}/actuator/health", timeout=2)
            self._available = r.status_code == 200
        except Exception:
            self._available = False
        return self._available

    def _login(self) -> str | None:
        if not _HAS_REQUESTS:
            return None
        try:
            r = _req.post(
                f"{self.base_url}/api/v1/auth/login",
                json={"username": BUYER_USERNAME, "password": BUYER_PASSWORD},
                timeout=5,
            )
            data = r.json()
            if data.get("code") == 0:
                return data["data"]["accessToken"]
        except Exception:
            pass
        return None

    def _headers(self) -> dict[str, str]:
        if self._token is None:
            self._token = self._login()
        return {"Authorization": f"Bearer {self._token}"} if self._token else {}

    def search_products(self, keyword: str = "", platform: str = "", category: str = "", page: int = 1, size: int = 10) -> list[dict]:
        if not self._is_available():
            return self._local_search_products(keyword, platform, category)
        try:
            params: dict[str, Any] = {"page": page, "size": size}
            if keyword:
                params["keyword"] = keyword
            if platform:
                params["platform"] = platform
            if category:
                params["category"] = category
            r = _req.get(f"{self.base_url}/api/v1/data/products", params=params, headers=self._headers(), timeout=5)
            data = r.json()
            if data.get("code") == 0:
                return data["data"].get("items", data["data"].get("content", []))
        except Exception:
            pass
        return self._local_search_products(keyword, platform, category)

    def get_market_prices(self, keyword: str = "", category: str = "") -> list[dict]:
        if not self._is_available():
            return self._local_market_prices(keyword, category)
        try:
            params: dict[str, Any] = {}
            if keyword:
                params["keyword"] = keyword
            if category:
                params["category"] = category
            r = _req.get(f"{self.base_url}/api/v1/data/market-prices", params=params, headers=self._headers(), timeout=5)
            data = r.json()
            if data.get("code") == 0:
                return data["data"].get("items", [])
        except Exception:
            pass
        return self._local_market_prices(keyword, category)

    # ── local fallbacks ───────────────────────────────────────────────────────

    @staticmethod
    def _local_search_products(keyword: str, platform: str, category: str) -> list[dict]:
        raw_tokens = re.split(r"[\uff0c,\u3002!?\s]+", keyword.lower().strip())
        tokens = [t for t in raw_tokens if len(t) >= 2]
        if not tokens and keyword:
            tokens = [keyword.lower()]
        results = []
        for p in LOCAL_PRODUCTS:
            if platform and p["platform"] != platform:
                continue
            if category and category not in p["category"]:
                continue
            score = 0
            title = p["title"].lower()
            brand = p["brand"].lower()
            cat = p["category"].lower()
            shop = p["shopName"].lower()
            for tok in tokens:
                if tok in title:
                    score += 3
                if tok in brand:
                    score += 2
                if tok in cat:
                    score += 2
                if tok in shop:
                    score += 1
            if tokens and score == 0:
                continue
            results.append((score, p))
        results.sort(key=lambda x: (-x[0], -x[1]["sales"]))
        return [p for _, p in results]

    @staticmethod
    def _local_market_prices(keyword: str, category: str) -> list[dict]:
        kw = keyword.lower()
        cat = category.lower()
        return [
            mp for mp in LOCAL_MARKET_PRICES
            if (not kw or kw in mp["productName"].lower())
            and (not cat or cat in mp["category"].lower())
        ]


# ── Intent recognition ────────────────────────────────────────────────────────

class Intent:
    SEARCH = "SEARCH"
    PRICE_QUERY = "PRICE_QUERY"
    PURCHASE = "PURCHASE"
    COMPARE = "COMPARE"
    STOCK_CHECK = "STOCK_CHECK"
    UNKNOWN = "UNKNOWN"

_INTENT_RULES: list[tuple[str, list[str]]] = [
    (Intent.PURCHASE,    ["买", "购买", "想买", "采购", "下单", "订购", "要买"]),
    (Intent.PRICE_QUERY, ["多少钱", "价格", "价位", "报价", "行情", "多钱", "贵不贵", "市场价"]),
    (Intent.COMPARE,     ["对比", "比较", "哪个好", "有什么区别", "区别", "怎么选"]),
    (Intent.STOCK_CHECK, ["有货", "有货吗", "有没有", "库存", "有吗", "现货", "缺货"]),
    (Intent.SEARCH,      ["找", "搜索", "查找", "看看", "浏览", "推荐", "介绍", "帮我找"]),
]

_CATEGORY_HINTS: dict[str, list[str]] = {
    "IT设备":  ["电脑", "笔记本", "服务器", "打印机", "交换机", "路由器", "显示器", "显卡", "内存"],
    "办公用品": ["复印纸", "椅", "椅子", "办公椅", "桌子", "文件柜", "白板", "笔", "文具", "耗材", "办公"],
    "工业设备": ["机床", "电机", "液压", "变频器", "传感器", "气缸", "泵站", "工业", "设备"],
    "原材料":  ["钢板", "铝材", "铜材", "不锈钢", "铝合金", "钢材", "型材"],
    "电子元件": ["继电器", "芯片", "单片机", "传感器", "电阻", "电容", "模块", "mcu"],
}

def _extract_intent(text: str) -> str:
    t = text.lower()
    for intent, patterns in _INTENT_RULES:
        if any(p in t for p in patterns):
            return intent
    return Intent.UNKNOWN

def _extract_keywords(text: str) -> list[str]:
    """Simple keyword extraction: split on common delimiters and filter short tokens."""
    tokens = re.split(r"[，,。！？\s]+", text.strip())
    return [tok for tok in tokens if len(tok) >= 2]

def _infer_category(text: str) -> str:
    t = text.lower()
    for category, hints in _CATEGORY_HINTS.items():
        if any(h in t for h in hints):
            return category
    return ""


def _extract_search_term(text: str) -> str:
    """
    Extract the most searchable product keyword from a natural language query.
    Prefers shorter, general terms over longer compound words to improve DB match recall.
    Falls back to the last 2 CJK tokens.
    """
    t_lower = text.lower()
    candidates: list[str] = []
    for hints in _CATEGORY_HINTS.values():
        for hint in hints:
            if hint in t_lower and len(hint) >= 1:
                candidates.append(hint)
    if candidates:
        # Prefer longer hints (more specific) unless they are compound terms
        # that are unlikely to appear verbatim in product titles (len > 3)
        short = [c for c in candidates if len(c) <= 3]
        long  = [c for c in candidates if len(c) > 3]
        # Use the longest of the short ones (most specific yet likely to match)
        if short:
            return max(short, key=len)
        return max(long, key=len)
    # Fallback: last 2 non-trivial tokens
    tokens = [tok for tok in re.split(r"[\uff0c,\u3002!?\s]+", text.strip()) if len(tok) >= 2]
    return " ".join(tokens[-2:]) if tokens else text[:20]


# ── Text processor ────────────────────────────────────────────────────────────

class TextProcessor:
    def __init__(self, client: ILbuyClient):
        self.client = client

    async def process(self, text: str, session: dict) -> dict:
        await asyncio.sleep(0)  # yield to event loop
        intent = _extract_intent(text)
        keywords = _extract_keywords(text)
        category = _infer_category(text)

        # combine with session context for follow-up queries
        if intent == Intent.UNKNOWN and session.get("last_intent") not in (None, Intent.UNKNOWN):
            intent = session["last_intent"]
        search_term = _extract_search_term(text)

        if intent == Intent.PRICE_QUERY:
            prices = self.client.get_market_prices(keyword=search_term, category=category)
            products = self.client.search_products(keyword=search_term, category=category, size=5)
            return {
                "intent": intent, "keywords": keywords, "category": category,
                "matched_products": products[:3], "market_prices": prices[:3],
                "response": _format_price_response(search_term, prices, products),
            }
        else:
            products = self.client.search_products(keyword=search_term, category=category, size=6)
            return {
                "intent": intent, "keywords": keywords, "category": category,
                "matched_products": products[:3], "market_prices": [],
                "response": _format_product_response(intent, search_term, products),
            }


def _format_product_response(intent: str, query: str, products: list[dict]) -> str:
    if not products:
        return f"抱歉，没有找到与「{query}」相关的商品，请尝试其他关键词。"
    p = products[0]
    if intent == Intent.PURCHASE:
        return (f"为您找到适合采购的商品：【{p['title']}】，"
                f"{p['brand']}品牌，¥{p['price']:.2f}/件，"
                f"来自{p['platformName']} · {p['shopName']}，"
                f"库存{p['stock']}件，已售{p['sales']}件。")
    if intent == Intent.COMPARE and len(products) >= 2:
        p2 = products[1]
        return (f"为您找到{len(products)}款相关商品可供对比：\n"
                f"① {p['title']} ({p['brand']}) ¥{p['price']:.2f}\n"
                f"② {p2['title']} ({p2['brand']}) ¥{p2['price']:.2f}")
    if intent == Intent.STOCK_CHECK:
        status = "有货" if p["stock"] > 0 else "暂时缺货"
        return (f"【{p['title']}】{status}，"
                f"当前库存{p['stock']}件，来自{p['platformName']}。")
    return (f"找到{len(products)}款相关商品，推荐：【{p['title']}】，"
            f"{p['brand']}，¥{p['price']:.2f}，{p['platformName']}。")


def _format_price_response(query: str, prices: list[dict], products: list[dict]) -> str:
    if prices:
        mp = prices[0]
        return (f"「{mp['productName']}」市场参考价："
                f"均价¥{mp['avgPrice']:.2f}/{mp['unit']}，"
                f"价格区间¥{mp['minPrice']:.2f}–¥{mp['maxPrice']:.2f}。")
    if products:
        p = products[0]
        return f"【{p['title']}】在{p['platformName']}售价¥{p['price']:.2f}，供参考。"
    return f"暂未找到「{query}」的市场价格数据，建议直接联系供应商询价。"


# ── Voice processor (mock ASR) ────────────────────────────────────────────────

_MOCK_UTTERANCES: list[tuple[str, float]] = [
    ("我想采购一批联想笔记本电脑，大概100台", 0.94),
    ("不锈钢板材304号两毫米的价格是多少", 0.91),
    ("帮我查一下办公椅的库存情况", 0.89),
    ("戴尔服务器和华为服务器哪个性价比高", 0.87),
    ("我们需要采购A4复印纸500箱，请报价", 0.93),
    ("工业级继电器模块现在有没有货", 0.88),
    ("推荐几款企业级交换机，48口千兆的", 0.90),
    ("ARM单片机STM32开发板的价格和库存", 0.86),
    ("请问变频器7.5千瓦三相380伏的市场价", 0.92),
    ("查询阿里巴巴1688上不锈钢螺丝的报价", 0.85),
]


class VoiceProcessor:
    """Simulates ASR by deterministically mapping audio bytes to Chinese utterances."""

    def __init__(self, text_processor: TextProcessor):
        self.text_processor = text_processor

    async def process(self, audio_data: bytes, session: dict) -> dict:
        await asyncio.sleep(random.uniform(0.05, 0.15))  # simulate processing time
        idx = int(hashlib.md5(audio_data[:512]).hexdigest(), 16) % len(_MOCK_UTTERANCES)
        text, confidence = _MOCK_UTTERANCES[idx]

        result = await self.text_processor.process(text, session)
        return {
            **result,
            "transcribed_text": text,
            "asr_confidence": confidence,
        }


# ── Image processor (mock CV) ─────────────────────────────────────────────────

@dataclass
class ImageRecognitionResult:
    labels: list[dict]      # [{"name": str, "confidence": float}]
    brands: list[str]
    objects: list[str]
    ocr_text: str
    search_keyword: str     # derived keyword for product search

_MOCK_IMAGE_RESULTS: list[ImageRecognitionResult] = [
    ImageRecognitionResult(
        labels=[{"name": "笔记本电脑", "confidence": 0.96}, {"name": "IT设备", "confidence": 0.91}],
        brands=["联想", "ThinkPad"],
        objects=["笔记本", "键盘", "屏幕"],
        ocr_text="ThinkPad E14 Gen 5\ni5-1340P 16GB 512GB\n¥5299",
        search_keyword="联想笔记本电脑",
    ),
    ImageRecognitionResult(
        labels=[{"name": "服务器", "confidence": 0.94}, {"name": "机架式设备", "confidence": 0.88}],
        brands=["戴尔", "Dell"],
        objects=["服务器", "机架", "指示灯"],
        ocr_text="Dell PowerEdge R750\nDual Xeon Gold 6348\n2x 32GB DDR4",
        search_keyword="戴尔服务器",
    ),
    ImageRecognitionResult(
        labels=[{"name": "工业设备", "confidence": 0.89}, {"name": "变频器", "confidence": 0.85}],
        brands=["英威腾", "Inovance"],
        objects=["变频器", "控制面板", "接线端子"],
        ocr_text="INVT MD500T7R5G3\n三相380V 7.5kW\nIP20防护等级",
        search_keyword="变频器7.5KW",
    ),
    ImageRecognitionResult(
        labels=[{"name": "不锈钢板材", "confidence": 0.91}, {"name": "原材料", "confidence": 0.87}],
        brands=["宝钢", "BAOSTEEL"],
        objects=["钢板", "金属板材", "切割板"],
        ocr_text="304不锈钢冷轧板\n2.0mm*1220mm*2440mm\n≥28.5元/kg",
        search_keyword="不锈钢板材304",
    ),
    ImageRecognitionResult(
        labels=[{"name": "办公椅", "confidence": 0.93}, {"name": "家具", "confidence": 0.88}],
        brands=["西昊", "SIHOO"],
        objects=["椅子", "扶手", "滚轮底座"],
        ocr_text="SIHOO S300\n人体工学电脑椅\n¥2399 原价¥2899",
        search_keyword="人体工学办公椅",
    ),
]


class ImageProcessor:
    """Simulates computer vision by mapping image bytes to mock recognition results."""

    def __init__(self, client: ILbuyClient):
        self.client = client

    async def process(self, image_data: bytes, session: dict) -> dict:
        await asyncio.sleep(random.uniform(0.1, 0.3))  # simulate CV latency
        idx = int(hashlib.md5(image_data[:512]).hexdigest(), 16) % len(_MOCK_IMAGE_RESULTS)
        rec = _MOCK_IMAGE_RESULTS[idx]

        category = _infer_category(rec.search_keyword)
        products = self.client.search_products(keyword=rec.search_keyword, category=category, size=5)

        brand_str = "、".join(rec.brands) if rec.brands else "未识别"
        response = (
            f"图像识别到{rec.labels[0]['name']}（置信度{rec.labels[0]['confidence']:.0%}），"
            f"品牌：{brand_str}。"
            f"OCR识别文字：「{rec.ocr_text.split(chr(10))[0]}」。"
        )
        if products:
            p = products[0]
            response += f" 推荐商品：【{p['title']}】¥{p['price']:.2f}，{p['platformName']}。"

        return {
            "intent": Intent.SEARCH,
            "keywords": rec.objects,
            "category": category,
            "matched_products": products[:3],
            "market_prices": [],
            "image_labels": rec.labels,
            "image_brands": rec.brands,
            "ocr_text": rec.ocr_text,
            "response": response,
        }


# ── Link processor ────────────────────────────────────────────────────────────

_PLATFORM_DOMAINS: dict[str, str] = {
    "taobao.com": "taobao",
    "tmall.com": "tmall",
    "jd.com": "jd",
    "pinduoduo.com": "pinduoduo",
    "douyin.com": "douyin",
    "vip.com": "weipinhui",
    "1688.com": "1688",
}

_PLATFORM_NAMES: dict[str, str] = {
    "taobao": "淘宝", "tmall": "天猫", "jd": "京东",
    "pinduoduo": "拼多多", "douyin": "抖音",
    "weipinhui": "唯品会", "1688": "阿里巴巴1688",
}

_PATH_KEYWORDS: list[tuple[str, str]] = [
    ("laptop", "笔记本电脑"), ("notebook", "笔记本电脑"), ("server", "服务器"),
    ("printer", "打印机"), ("switch", "交换机"), ("chair", "办公椅"),
    ("paper", "复印纸"), ("steel", "钢板"), ("inverter", "变频器"),
    ("relay", "继电器"), ("mcu", "单片机"), ("sensor", "传感器"),
]


class LinkProcessor:
    def __init__(self, client: ILbuyClient):
        self.client = client

    async def process(self, url: str, session: dict) -> dict:
        await asyncio.sleep(0.05)
        parsed = urlparse(url)
        domain = parsed.netloc.lower().lstrip("www.")

        # detect platform
        platform = ""
        platform_name = "未知平台"
        for d, plat in _PLATFORM_DOMAINS.items():
            if d in domain:
                platform = plat
                platform_name = _PLATFORM_NAMES.get(plat, plat)
                break

        # extract keyword from path
        path = unquote(parsed.path + " " + (parsed.query or "")).lower()
        keyword = ""
        for path_token, kw in _PATH_KEYWORDS:
            if path_token in path:
                keyword = kw
                break
        # also try to grab meaningful Chinese-looking or product-name segments
        if not keyword:
            # take last non-empty path segment (often item name / item id)
            segments = [s for s in parsed.path.split("/") if s]
            if segments:
                raw = unquote(segments[-1]).replace("-", " ").replace("_", " ")
                keyword = raw[:40]

        category = _infer_category(keyword)
        products = self.client.search_products(keyword=keyword, platform=platform, category=category, size=5)

        response = f"解析到{platform_name}商品链接，"
        if keyword:
            response += f"关键词「{keyword}」，"
        if products:
            p = products[0]
            response += f"推荐：【{p['title']}】¥{p['price']:.2f}，库存{p['stock']}件。"
        else:
            response += "暂未找到精确匹配商品，请尝试更具体的搜索关键词。"

        return {
            "intent": Intent.SEARCH,
            "keywords": [keyword] if keyword else [],
            "category": category,
            "platform": platform,
            "platform_name": platform_name,
            "matched_products": products[:3],
            "market_prices": [],
            "response": response,
        }


# ── Session management ────────────────────────────────────────────────────────

@dataclass
class Session:
    session_id: str
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_activity: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    interaction_count: int = 0
    last_intent: str = Intent.UNKNOWN
    last_keywords: list[str] = field(default_factory=list)
    history: deque = field(default_factory=lambda: deque(maxlen=5))  # last 5 exchanges

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "created_at": self.created_at,
            "last_activity": self.last_activity,
            "interaction_count": self.interaction_count,
            "last_intent": self.last_intent,
            "last_keywords": self.last_keywords,
            "history_len": len(self.history),
        }

    def record(self, input_type: str, user_input: str, response: str, intent: str, keywords: list[str]) -> None:
        self.interaction_count += 1
        self.last_activity = datetime.now(timezone.utc).isoformat()
        self.last_intent = intent
        self.last_keywords = keywords
        self.history.append({
            "turn": self.interaction_count,
            "input_type": input_type,
            "user": user_input[:80],
            "assistant": response[:120],
        })


# ── Multimodal assistant ──────────────────────────────────────────────────────

class MultimodalAssistant:
    """
    Orchestrates all input processors.
    Maintains per-session context for multi-round conversations.
    """

    def __init__(self, gateway_url: str = GATEWAY_URL):
        self._client = ILbuyClient(base_url=gateway_url)
        self._text = TextProcessor(self._client)
        self._voice = VoiceProcessor(self._text)
        self._image = ImageProcessor(self._client)
        self._link = LinkProcessor(self._client)
        self._sessions: dict[str, Session] = {}

    def _get_session(self, session_id: str) -> Session:
        if session_id not in self._sessions:
            self._sessions[session_id] = Session(session_id=session_id)
        return self._sessions[session_id]

    async def process(
        self,
        session_id: str,
        input_type: str,
        content: str | bytes,
    ) -> dict:
        """
        Route input to the correct processor and return a unified response dict.

        Parameters
        ----------
        session_id : str
            Conversation session identifier.
        input_type : str
            One of: "text", "voice", "image", "link".
        content : str | bytes
            The user's input (text/link as str; voice/image as bytes).

        Returns
        -------
        dict with keys:
            session_id, input_type, intent, keywords, category,
            matched_products, market_prices, response, timestamp, session_info
        """
        session = self._get_session(session_id)
        session_dict = session.to_dict()

        if input_type == "text":
            assert isinstance(content, str)
            result = await self._text.process(content, session_dict)
            display_input = content
        elif input_type == "voice":
            assert isinstance(content, bytes)
            result = await self._voice.process(content, session_dict)
            display_input = result.get("transcribed_text", "<audio>")
        elif input_type == "image":
            assert isinstance(content, bytes)
            result = await self._image.process(content, session_dict)
            display_input = "<image>"
        elif input_type == "link":
            assert isinstance(content, str)
            result = await self._link.process(content, session_dict)
            display_input = content
        else:
            return {
                "session_id": session_id,
                "input_type": input_type,
                "error": f"Unsupported input_type: {input_type!r}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        # update session state
        session.record(
            input_type=input_type,
            user_input=display_input,
            response=result.get("response", ""),
            intent=result.get("intent", Intent.UNKNOWN),
            keywords=result.get("keywords", []),
        )

        return {
            "session_id": session_id,
            "input_type": input_type,
            **result,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session_info": session.to_dict(),
        }

    def get_session_history(self, session_id: str) -> list[dict]:
        s = self._sessions.get(session_id)
        return list(s.history) if s else []


# ── Test client ───────────────────────────────────────────────────────────────

class TestClient:
    """Comprehensive test runner for all four input modes."""

    def __init__(self, gateway_url: str = GATEWAY_URL):
        self.assistant = MultimodalAssistant(gateway_url=gateway_url)

    async def run_comprehensive_test(self) -> None:
        sep = "=" * 65
        print(sep)
        print("  ILbuy 本地多模态商品助手 — 综合测试")
        print(sep)

        session_id = f"test_{int(time.time())}"

        # ── 1. Text input ──────────────────────────────────────────────────
        print("\n【1/4】文字输入测试")
        text_cases = [
            "我想采购100台联想笔记本电脑",
            "不锈钢板材304号的市场价格",
            "办公椅有库存吗",
        ]
        for text in text_cases:
            r = await self.assistant.process(session_id, "text", text)
            print(f"  用户: {text}")
            print(f"  意图: {r['intent']}  |  匹配商品数: {len(r['matched_products'])}")
            print(f"  回复: {r['response']}")
            print()

        # ── 2. Voice input ─────────────────────────────────────────────────
        print("\n【2/4】语音输入测试")
        voice_session = f"voice_{int(time.time())}"
        for audio_seed in [b"audio_laptop", b"audio_steel", b"audio_relay"]:
            r = await self.assistant.process(voice_session, "voice", audio_seed)
            print(f"  ASR识别: {r.get('transcribed_text', '')} (置信度: {r.get('asr_confidence', 0):.0%})")
            print(f"  意图: {r['intent']}  |  匹配商品数: {len(r['matched_products'])}")
            print(f"  回复: {r['response']}")
            print()

        # ── 3. Image input ─────────────────────────────────────────────────
        print("\n【3/4】图片输入测试")
        image_session = f"img_{int(time.time())}"
        image_cases = [
            (b"img_thinkpad_e14", "笔记本电脑图片"),
            (b"img_dell_server",  "服务器图片"),
            (b"img_steel_plate",  "钢板材料图片"),
        ]
        for img_bytes, desc in image_cases:
            r = await self.assistant.process(image_session, "image", img_bytes)
            labels = [lb["name"] for lb in r.get("image_labels", [])[:2]]
            print(f"  图片: {desc}")
            print(f"  识别标签: {labels}  品牌: {r.get('image_brands', [])}")
            print(f"  回复: {r['response']}")
            print()

        # ── 4. Link input ──────────────────────────────────────────────────
        print("\n【4/4】链接输入测试")
        link_session = f"link_{int(time.time())}"
        links = [
            "https://item.taobao.com/item.htm?id=12345&title=laptop-thinkpad",
            "https://detail.tmall.com/item.htm?server-poweredge-dell",
            "https://item.jd.com/10043656.html#steel-plate-304",
            "https://detail.1688.com/offer/relay-industrial-88.html",
        ]
        for url in links:
            r = await self.assistant.process(link_session, "link", url)
            print(f"  链接: {url[:60]}...")
            print(f"  平台: {r.get('platform_name', '未知')}  关键词: {r.get('keywords', [])}")
            print(f"  回复: {r['response']}")
            print()

        # ── 5. Multi-round conversation ────────────────────────────────────
        print("\n【5/5】多轮对话测试")
        multi_session = f"multi_{int(time.time())}"
        turns = [
            ("text", "推荐一些工业设备"),
            ("text", "价格怎么样"),
            ("voice", b"audio_inverter_query"),
        ]
        for input_type, content in turns:
            r = await self.assistant.process(multi_session, input_type, content)
            if input_type == "voice":
                user_str = f"[语音] {r.get('transcribed_text', '')}"
            else:
                user_str = content
            print(f"  用户({input_type}): {user_str}")
            print(f"  回复: {r['response']}")

        history = self.assistant.get_session_history(multi_session)
        print(f"\n  对话历史 ({len(history)} 轮):")
        for turn in history:
            print(f"    Turn {turn['turn']}: [{turn['input_type']}] {turn['user'][:40]} → {turn['assistant'][:50]}...")

        print(f"\n{sep}")
        print("  测试完成！")
        print(sep)


# ── Quick start demo ──────────────────────────────────────────────────────────

async def quick_start() -> None:
    print("ILbuy 多模态商品助手 — 快速演示\n")
    assistant = MultimodalAssistant()

    # Text
    r = await assistant.process("demo", "text", "我想采购一批服务器")
    print(f"[文字] 我想采购一批服务器")
    print(f"  → {r['response']}\n")

    # Voice
    r = await assistant.process("demo", "voice", b"voice_check")
    print(f"[语音] ASR识别: {r.get('transcribed_text')}")
    print(f"  → {r['response']}\n")

    # Image
    r = await assistant.process("demo", "image", b"image_demo_office_chair")
    print(f"[图片] 识别: {[lb['name'] for lb in r.get('image_labels', [])[:2]]}")
    print(f"  → {r['response']}\n")

    # Link
    r = await assistant.process("demo", "link", "https://detail.1688.com/offer/relay-88.html")
    print(f"[链接] https://detail.1688.com/offer/relay-88.html")
    print(f"  → {r['response']}\n")

    session_info = r["session_info"]
    print(f"会话信息: {session_info['interaction_count']} 次交互 | 最后意图: {session_info['last_intent']}")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        client = TestClient()
        asyncio.run(client.run_comprehensive_test())
    else:
        asyncio.run(quick_start())
