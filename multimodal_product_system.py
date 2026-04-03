"""
multimodal_product_system.py
多模态商品识别系统 - 生产级完整实现
基于架构图实现的多层系统架构
"""

import asyncio
import json
import time
import uuid
import hashlib
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
import re
import base64
import random
from collections import defaultdict
import logging
from contextlib import asynccontextmanager

# ==================== 配置和日志 ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ==================== 数据模型 ====================
class InputType(Enum):
    TEXT = "text"
    IMAGE = "image"
    VOICE = "voice"
    LINK = "link"


class UserType(Enum):
    B2C_CONSUMER = "b2c_consumer"
    B2B_BUYER = "b2b_buyer"


class PlatformType(Enum):
    TAOBAO = "taobao"
    TMALL = "tmall"
    JD = "jd"
    PINDUODUO = "pinduoduo"
    DOUYIN = "douyin"
    VIP = "vip"
    ALIBABA = "alibaba"


@dataclass
class UserProfile:
    user_id: str
    user_type: UserType
    username: Optional[str] = None
    preferences: Dict[str, Any] = field(default_factory=dict)
    budget_range: Optional[Tuple[float, float]] = None
    purchase_history: List[Dict] = field(default_factory=list)
    interaction_history: List[Dict] = field(default_factory=list)
    session_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def update_preferences(self, new_preferences: Dict[str, Any]):
        self.preferences.update(new_preferences)
        self.updated_at = datetime.now()

    def add_interaction(self, interaction: Dict):
        # BUG FIX: was {interaction, "timestamp":...} (set literal) → must be dict spread
        self.interaction_history.append({
            **interaction,
            "timestamp": datetime.now().isoformat()
        })
        if len(self.interaction_history) > 1000:
            self.interaction_history = self.interaction_history[-1000:]
        self.session_count += 1
        self.updated_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "user_type": self.user_type.value,
            "username": self.username,
            "preferences": self.preferences,
            "budget_range": list(self.budget_range) if self.budget_range else None,
            "session_count": self.session_count,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class UserInput:
    session_id: str
    user_id: str
    input_type: InputType
    content: Any
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "input_type": self.input_type.value,
            "content": str(self.content)[:200] if isinstance(self.content, (str, bytes)) else str(self.content),
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class ProductInfo:
    product_id: str
    platform: PlatformType
    title: str
    price: float
    currency: str = "CNY"
    category: Optional[str] = None
    brand: Optional[str] = None
    image_urls: List[str] = field(default_factory=list)
    description: Optional[str] = None
    specifications: Dict[str, Any] = field(default_factory=dict)
    platform_specific: Dict[str, Any] = field(default_factory=dict)
    score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        desc = self.description
        if desc and len(desc) > 100:
            desc = desc[:100] + "..."
        return {
            "product_id": self.product_id,
            "platform": self.platform.value,
            "title": self.title,
            "price": self.price,
            "currency": self.currency,
            "category": self.category,
            "brand": self.brand,
            "image_urls": self.image_urls[:3],
            "description": desc,
            "specifications": self.specifications,
            "score": round(self.score, 2)
        }


@dataclass
class SystemResponse:
    session_id: str
    user_id: str
    response_type: str
    message: str
    products: List[ProductInfo] = field(default_factory=list)
    confidence: float = 0.0
    need_clarification: bool = False
    clarification_questions: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "response_type": self.response_type,
            "message": self.message,
            "products": [p.to_dict() for p in self.products[:5]],
            "confidence": round(self.confidence, 2),
            "need_clarification": self.need_clarification,
            "clarification_questions": self.clarification_questions,
            "suggestions": self.suggestions,
            "timestamp": self.timestamp.isoformat()
        }


# ==================== 第一部分：输入层处理器 ====================
class BaseInputProcessor(ABC):
    @abstractmethod
    async def process(self, user_input: UserInput) -> Dict[str, Any]:
        pass

    @abstractmethod
    def validate(self, content: Any) -> bool:
        pass


class TextInputProcessor(BaseInputProcessor):
    def __init__(self):
        self.intent_patterns = {
            "purchase": ["买", "购买", "想买", "要买", "下单", "订购"],
            "inquire":  ["多少钱", "价格", "价位", "报价", "多钱", "贵不贵"],
            "compare":  ["对比", "比较", "哪个好", "有什么区别", "对比一下"],
            "search":   ["找", "搜索", "查找", "看看", "浏览", "推荐"],
            "stock":    ["有货", "有货吗", "有没有", "库存", "有吗"],
            "specs":    ["配置", "参数", "规格", "尺寸", "颜色", "型号"],
        }
        # BUG FIX: skeleton had broken newlines inside regex strings
        self.keyword_patterns = {
            "brand":    r"(苹果|华为|小米|OPPO|vivo|三星|耐克|阿迪|戴尔|联想|海尔)",
            "price":    r"(\d+)(?:到|-)?(\d+)?(?:元|块|钱)?",
            "category": r"(手机|电脑|笔记本|电视|冰箱|洗衣机|衣服|鞋子|化妆品)",
        }

    @staticmethod
    def _sanitize_text(text: str) -> str:
        """去除控制字符并截断到1000字符"""
        cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
        return cleaned[:1000]

    def validate(self, content: Any) -> bool:
        if not isinstance(content, str):
            return False
        text = content.strip()
        if not text:
            return False
        if len(content) > 1000:
            return False
        return True

    async def process(self, user_input: UserInput) -> Dict[str, Any]:
        if not self.validate(user_input.content):
            raise ValueError("无效的文本输入：内容为空或超过1000字符")
        text = self._sanitize_text(str(user_input.content))
        intent   = self._detect_intent(text)
        keywords = self._extract_keywords(text)
        entities = self._extract_entities(text)
        return {
            "input_type":     "text",
            "processed_text": text,
            "intent":         intent,
            "keywords":       keywords,
            "entities":       entities,
            "confidence":     0.9,
        }

    def _detect_intent(self, text: str) -> Dict[str, Any]:
        for intent_type, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if pattern in text:
                    return {"intent": intent_type, "confidence": round(0.80 + random.random() * 0.15, 3)}
        return {"intent": "unknown", "confidence": 0.3}

    def _extract_keywords(self, text: str) -> List[str]:
        common = ["最新", "新款", "旗舰", "高端", "性价比", "优惠", "打折"]
        return [kw for kw in common if kw in text]

    def _extract_entities(self, text: str) -> Dict[str, Any]:
        entities: Dict[str, Any] = {"brands": [], "categories": [], "price_range": None}
        for token in re.findall(self.keyword_patterns["brand"], text):
            entities["brands"].append(token)
        for token in re.findall(self.keyword_patterns["category"], text):
            entities["categories"].append(token)
        m = re.search(self.keyword_patterns["price"], text)
        if m:
            lo = float(m.group(1))
            hi = float(m.group(2)) if m.group(2) else lo
            entities["price_range"] = (lo, hi)
        return entities


class ImageInputProcessor(BaseInputProcessor):
    # JPEG: FF D8 FF  PNG: 89 50 4E 47
    _MAGIC = {b'\xff\xd8\xff': "jpeg", b'\x89PNG': "png",
              b'GIF8': "gif", b'RIFF': "webp"}

    def validate(self, content: Any) -> bool:
        if not isinstance(content, bytes):
            return False
        # BUG FIX: was `10  1024  1024` → `10 * 1024 * 1024`
        if len(content) < 100 or len(content) > 10 * 1024 * 1024:
            return False
        # check magic bytes (lenient: at least one known header)
        for magic in self._MAGIC:
            if content[:len(magic)] == magic:
                return True
        # unknown format but within size — accept for mock
        return True

    async def process(self, user_input: UserInput) -> Dict[str, Any]:
        if not self.validate(user_input.content):
            raise ValueError("无效的图片输入：格式不支持或超过10MB")
        image_data = user_input.content
        recognition = await self._recognize_image(image_data)
        ocr_text    = await self._extract_text(image_data)
        return {
            "input_type":         "image",
            "image_size":         len(image_data),
            "recognition_result": recognition,
            "ocr_text":           ocr_text,
            "features":           self._extract_features(recognition, ocr_text),
            "confidence":         recognition.get("confidence", 0.7),
        }

    async def _recognize_image(self, image_data: bytes) -> Dict[str, Any]:
        await asyncio.sleep(0.1)
        h = int(hashlib.md5(image_data[:1000]).hexdigest()[:8], 16) % 2
        mock = [
            {"labels": [{"name": "手机", "confidence": 0.95},
                        {"name": "电子产品", "confidence": 0.88},
                        {"name": "苹果", "confidence": 0.82}],
             "brands": ["苹果", "Apple"], "colors": ["黑色", "银色"], "confidence": 0.85},
            {"labels": [{"name": "运动鞋", "confidence": 0.92},
                        {"name": "鞋子", "confidence": 0.85},
                        {"name": "耐克", "confidence": 0.78}],
             "brands": ["耐克", "Nike"], "colors": ["黑色", "白色", "红色"], "confidence": 0.82},
        ]
        return mock[h]

    async def _extract_text(self, image_data: bytes) -> str:
        await asyncio.sleep(0.05)
        h = int(hashlib.md5(image_data[:1000]).hexdigest()[:8], 16) % 2
        return [
            "iPhone 15 Pro Max 256GB\nA17 Pro芯片\n¥8999",
            "NIKE AIR ZOOM PEGASUS 40\n跑步运动鞋\n¥899",
        ][h]

    def _extract_features(self, recognition: Dict, ocr_text: str) -> Dict[str, Any]:
        return {
            "categories": [l["name"] for l in recognition.get("labels", [])[:3]],
            "brands":     recognition.get("brands", []),
            "colors":     recognition.get("colors", []),
            "keywords":   ocr_text.split()[:10],
        }


class VoiceInputProcessor(BaseInputProcessor):
    def validate(self, content: Any) -> bool:
        if not isinstance(content, bytes):
            return False
        # BUG FIX: was `5  1024  1024`
        if len(content) < 1000 or len(content) > 5 * 1024 * 1024:
            return False
        return True

    async def process(self, user_input: UserInput) -> Dict[str, Any]:
        if not self.validate(user_input.content):
            raise ValueError("无效的语音输入：长度不足1KB或超过5MB")
        audio_data = user_input.content
        transcribed_text = await self._speech_to_text(audio_data)
        text_processor = TextInputProcessor()
        text_input = UserInput(
            session_id=user_input.session_id,
            user_id=user_input.user_id,
            input_type=InputType.TEXT,
            content=transcribed_text,
            metadata=user_input.metadata,
        )
        text_result = await text_processor.process(text_input)
        # BUG FIX: was `{text_result, "input_type": ...}` (set literal) → dict spread
        return {
            **text_result,
            "input_type":       "voice",
            "audio_duration":   round(len(audio_data) / 16000, 2),
            "transcribed_text": transcribed_text,
            "speech_confidence": 0.85,
        }

    async def _speech_to_text(self, audio_data: bytes) -> str:
        await asyncio.sleep(0.2)
        h = int(hashlib.md5(audio_data[:1000]).hexdigest()[:8], 16) % 4
        return [
            "我想买一双耐克运动鞋",
            "苹果手机最新款多少钱",
            "看看华为笔记本电脑",
            "这个红色的连衣裙有货吗",
        ][h]


class LinkInputProcessor(BaseInputProcessor):
    _PLATFORM_RE = {
        "taobao":   re.compile(r"taobao\.com|tmall\.com"),
        "jd":       re.compile(r"jd\.com|360buy\.com"),
        "pinduoduo":re.compile(r"pinduoduo\.com|yangkeduo\.com"),
        "douyin":   re.compile(r"douyin\.com|iesdouyin\.com"),
        "vip":      re.compile(r"vip\.com"),
        "alibaba":  re.compile(r"1688\.com|alibaba\.com"),
    }

    @staticmethod
    def _normalize_url(url: str) -> str:
        """小写 scheme+host，去除尾部斜杠"""
        m = re.match(r"(https?://)([^/]+)(.*)", url, re.IGNORECASE)
        if not m:
            return url.rstrip("/")
        return m.group(1).lower() + m.group(2).lower() + m.group(3).rstrip("/")

    def validate(self, content: Any) -> bool:
        if not isinstance(content, str):
            return False
        url = content.strip()
        if not url.startswith(("http://", "https://")):
            return False
        if len(url) > 2048:
            return False
        return True

    async def process(self, user_input: UserInput) -> Dict[str, Any]:
        if not self.validate(user_input.content):
            raise ValueError("无效的链接输入：需要以 http(s):// 开头且不超过2048字符")
        url         = self._normalize_url(str(user_input.content))
        parsed_info = await self._parse_url(url)
        product_info = await self._extract_product_info(url)
        return {
            "input_type":   "link",
            "url":          url,
            "parsed_info":  parsed_info,
            "product_info": product_info,
            "platform":     parsed_info.get("platform"),
            "confidence":   0.8,
        }

    async def _parse_url(self, url: str) -> Dict[str, Any]:
        platform = "unknown"
        for plat, pattern in self._PLATFORM_RE.items():
            if pattern.search(url):
                platform = plat
                break
        host = url.split("//")[-1].split("/")[0]
        return {"domain": host, "platform": platform, "is_valid": True}

    async def _extract_product_info(self, url: str) -> Dict[str, Any]:
        await asyncio.sleep(0.1)
        h = int(hashlib.md5(url.encode()).hexdigest()[:8], 16) % 3
        return [
            {"title": "iPhone 15 Pro Max 256GB",  "price": 8999.0, "brand": "苹果", "category": "手机"},
            {"title": "NIKE AIR ZOOM 跑步鞋",       "price":  899.0, "brand": "耐克", "category": "运动鞋"},
            {"title": "戴尔XPS 13 笔记本电脑",        "price": 9999.0, "brand": "戴尔", "category": "笔记本电脑"},
        ][h]


# ==================== 第二部分：AI处理层 ====================
class IntentUnderstandingEngine:
    """意图理解引擎"""

    async def understand_intent(self,
                                processed_input: Dict[str, Any],
                                user_profile: UserProfile) -> Dict[str, Any]:
        input_type = processed_input.get("input_type")

        if input_type in ("text", "voice"):
            raw_intent = processed_input.get("intent", {})
            entities   = processed_input.get("entities", {})
            keywords   = processed_input.get("keywords", [])
            text       = processed_input.get("processed_text", processed_input.get("transcribed_text", ""))

            # B2B 批量采购信号提权
            if user_profile.user_type == UserType.B2B_BUYER:
                if any(kw in text for kw in ["批量", "批发", "采购", "定制", "供货"]):
                    raw_intent = {"intent": "bulk_purchase", "confidence": min(raw_intent.get("confidence", 0.5) + 0.2, 1.0)}

            return {
                "primary_intent":   raw_intent,
                "secondary_intents": [],
                "entities":          entities,
                "keywords":          keywords,
                "context_aware":     True,
            }

        elif input_type == "image":
            features = processed_input.get("features", {})
            return {
                "primary_intent":   {"intent": "visual_search",   "confidence": 0.80},
                "secondary_intents": [
                    {"intent": "identify_product", "confidence": 0.70},
                    {"intent": "find_similar",     "confidence": 0.60},
                ],
                "entities": {
                    "categories": features.get("categories", []),
                    "brands":     features.get("brands", []),
                    "colors":     features.get("colors", []),
                },
                "keywords":      features.get("keywords", []),
                "context_aware": True,
            }

        elif input_type == "link":
            product_info = processed_input.get("product_info", {})
            return {
                "primary_intent":   {"intent": "link_analysis",     "confidence": 0.85},
                "secondary_intents": [
                    {"intent": "price_check",       "confidence": 0.70},
                    {"intent": "platform_compare",  "confidence": 0.60},
                ],
                "entities": {
                    "brands":     [product_info["brand"]]    if product_info.get("brand")    else [],
                    "categories": [product_info["category"]] if product_info.get("category") else [],
                    "price":       product_info.get("price"),
                },
                "keywords":      [product_info["title"]] if product_info.get("title") else [],
                "context_aware": True,
            }

        return {
            "primary_intent":   {"intent": "unknown", "confidence": 0.3},
            "secondary_intents": [],
            "entities":          {},
            "keywords":          [],
            "context_aware":     False,
        }


class ProductRecognitionEngine:
    """商品识别引擎"""

    def __init__(self, product_database):
        self.product_db = product_database

    async def recognize_product(self,
                                processed_input: Dict[str, Any],
                                user_intent: Dict[str, Any]) -> List[ProductInfo]:
        input_type = processed_input.get("input_type")
        entities   = user_intent.get("entities", {})
        keywords   = user_intent.get("keywords", [])

        if input_type in ("text", "voice"):
            products = await self._recognize_from_text(processed_input, entities, keywords)
        elif input_type == "image":
            products = await self._recognize_from_image(processed_input, entities)
        elif input_type == "link":
            products = await self._recognize_from_link(processed_input)
        else:
            products = []

        products = self._filter_by_intent(products, user_intent)
        return products[:10]

    async def _recognize_from_text(self, processed_input, entities, keywords):
        text = processed_input.get("processed_text", processed_input.get("transcribed_text", ""))
        conditions: Dict[str, Any] = {}
        if entities.get("brands"):
            conditions["brand"] = entities["brands"][0]
        if entities.get("categories"):
            conditions["category"] = entities["categories"][0]
        if entities.get("price_range"):
            conditions["price_range"] = entities["price_range"]
        return self.product_db.search_products(text=text, conditions=conditions, keywords=keywords)

    async def _recognize_from_image(self, processed_input, entities):
        features  = processed_input.get("features", {})
        ocr_text  = processed_input.get("ocr_text", "")
        visual    = self.product_db.search_by_features(
            categories=features.get("categories", []),
            brands=features.get("brands", []),
            colors=features.get("colors", []),
        )
        by_text   = self.product_db.search_products(text=ocr_text)
        seen: set = set()
        result = []
        for p in visual + by_text:
            if p.product_id not in seen:
                seen.add(p.product_id)
                result.append(p)
        return result

    async def _recognize_from_link(self, processed_input):
        product_info = processed_input.get("product_info", {})
        if not product_info:
            return []
        return self.product_db.search_similar_products(
            title=product_info.get("title", ""),
            brand=product_info.get("brand", ""),
            category=product_info.get("category", ""),
            price=product_info.get("price", 0),
        )

    def _filter_by_intent(self, products, user_intent):
        intent = user_intent.get("primary_intent", {}).get("intent", "")
        if intent in ("purchase", "bulk_purchase"):
            products = [p for p in products if p.price > 0]
            products.sort(key=lambda x: x.price)
        elif intent == "compare":
            by_brand: Dict[str, List] = defaultdict(list)
            for p in products:
                by_brand[p.brand or ""].append(p)
            flat = []
            for bp in by_brand.values():
                flat.extend(bp[:2])
            products = flat
        elif intent == "visual_search":
            products.sort(key=lambda x: x.score, reverse=True)
        return products


# ==================== 第三部分：业务逻辑层 ====================
class UserProfileManager:
    def __init__(self):
        self.profiles: Dict[str, UserProfile] = {}
        self._load_sample_profiles()

    def _load_sample_profiles(self):
        b2c = UserProfile(
            user_id="b2c_user_001", user_type=UserType.B2C_CONSUMER,
            username="消费者张三",
            preferences={"preferred_brands": ["苹果", "华为", "小米"],
                         "preferred_categories": ["手机", "电脑", "智能家居"],
                         "max_budget": 10000.0,
                         "preferred_platforms": ["tmall", "jd"]},
            budget_range=(1000.0, 10000.0),
        )
        b2b = UserProfile(
            user_id="b2b_user_001", user_type=UserType.B2B_BUYER,
            username="企业采购李经理",
            preferences={"company_name": "XX科技有限公司",
                         "purchase_scale": "bulk", "min_order_quantity": 10,
                         "need_invoice": True, "need_customization": False,
                         "preferred_platforms": ["alibaba", "1688"]},
            budget_range=(10000.0, 1_000_000.0),
        )
        self.profiles[b2c.user_id] = b2c
        self.profiles[b2b.user_id] = b2b

    def get_profile(self, user_id: str) -> UserProfile:
        if user_id not in self.profiles:
            self.profiles[user_id] = UserProfile(
                user_id=user_id, user_type=UserType.B2C_CONSUMER,
                preferences={"preferred_brands": [], "preferred_categories": [], "max_budget": 5000.0},
                budget_range=(100.0, 5000.0),
            )
        return self.profiles[user_id]

    def update_profile_from_interaction(self, user_id: str, interaction: Dict[str, Any]):
        profile = self.get_profile(user_id)
        for product in interaction.get("products", [])[:5]:
            if isinstance(product, dict):
                cat = product.get("category")
                brand = product.get("brand")
            elif isinstance(product, ProductInfo):
                cat = product.category
                brand = product.brand
            else:
                continue
            if cat:
                profile.preferences.setdefault("recent_categories", []).append(cat)
            if brand:
                profile.preferences.setdefault("recent_brands", []).append(brand)
        profile.add_interaction(interaction)


class ProductRecommendationEngine:
    def __init__(self, product_database, user_profile_manager: UserProfileManager):
        self.product_db = product_database
        self.user_profile_mgr = user_profile_manager

    async def recommend_products(self, user_id: str,
                                 recognized: List[ProductInfo],
                                 user_intent: Dict[str, Any]) -> List[ProductInfo]:
        profile = self.user_profile_mgr.get_profile(user_id)
        if not recognized:
            return await self._exploratory_recommendation(profile, user_intent)

        ranked = self._personalize_ranking(recognized, profile, user_intent)
        extra  = await self._get_supplementary_recommendations(ranked[:3], profile)

        seen: set = set()
        final = []
        for p in ranked + extra:
            if p.product_id not in seen:
                seen.add(p.product_id)
                final.append(p)
        return final[:10]

    async def _exploratory_recommendation(self, profile: UserProfile,
                                           user_intent: Dict[str, Any]) -> List[ProductInfo]:
        prefs = profile.preferences
        if profile.user_type == UserType.B2C_CONSUMER:
            return self.product_db.get_hot_products(
                categories=prefs.get("preferred_categories", []), limit=10)
        return self.product_db.get_wholesale_products(
            min_order_quantity=prefs.get("min_order_quantity", 1), limit=10)

    def _personalize_ranking(self, products: List[ProductInfo],
                              profile: UserProfile,
                              user_intent: Dict[str, Any]) -> List[ProductInfo]:
        preferred_brands = set(profile.preferences.get("preferred_brands", []))
        preferred_cats   = set(profile.preferences.get("preferred_categories", []))
        for p in products:
            s = 0.0
            if p.brand     and p.brand     in preferred_brands: s += 0.3
            if p.category  and p.category  in preferred_cats:   s += 0.2
            if profile.budget_range:
                lo, hi = profile.budget_range
                if lo <= p.price <= hi:     s += 0.2
                elif p.price < lo:          s += 0.1
                else:                       s -= 0.1
            if profile.user_type == UserType.B2B_BUYER:
                if any(kw in p.title for kw in ["批发", "大量", "定制", "供货"]):
                    s += 0.3
            p.score = max(0.0, min(1.0, s))
        products.sort(key=lambda x: x.score, reverse=True)
        return products

    async def _get_supplementary_recommendations(self, base: List[ProductInfo],
                                                   profile: UserProfile) -> List[ProductInfo]:
        result = []
        for p in base[:2]:
            result.extend(self.product_db.get_similar_products(p.product_id, limit=3))
            result.extend(self.product_db.get_complementary_products(p.product_id, limit=2))
        return result


class ConversationManager:
    def __init__(self):
        self.conversations: Dict[str, List[Dict]] = defaultdict(list)
        self.user_states:   Dict[str, Dict]       = defaultdict(dict)

    def get_conversation_history(self, session_id: str) -> List[Dict]:
        return list(self.conversations.get(session_id, []))

    def add_to_conversation(self, session_id: str,
                            user_input: UserInput,
                            system_response: SystemResponse):
        self.conversations[session_id].append({
            "user_input":      user_input.to_dict(),
            "system_response": system_response.to_dict(),
            "timestamp":       datetime.now().isoformat(),
        })
        if len(self.conversations[session_id]) > 50:
            self.conversations[session_id] = self.conversations[session_id][-50:]

    def get_user_state(self, session_id: str) -> Dict[str, Any]:
        return dict(self.user_states.get(session_id, {}))

    def update_user_state(self, session_id: str, state_updates: Dict[str, Any]):
        self.user_states[session_id].update(state_updates)

    def clear_conversation(self, session_id: str):
        self.conversations.pop(session_id, None)
        self.user_states.pop(session_id, None)


class ResponseGenerator:
    def __init__(self, conversation_manager: ConversationManager):
        self.conv_mgr = conversation_manager

    async def generate_response(self, session_id: str, user_id: str,
                                products: List[ProductInfo],
                                user_intent: Dict[str, Any],
                                need_clarification: bool = False) -> SystemResponse:
        history    = self.conv_mgr.get_conversation_history(session_id)
        user_state = self.conv_mgr.get_user_state(session_id)
        rtype      = self._determine_response_type(products, user_intent, need_clarification, len(history))
        message    = self._generate_message(rtype, products, user_intent)
        cqs        = self._generate_clarification_questions(user_intent, user_state) if need_clarification else []
        suggs      = self._generate_suggestions(products, user_intent)
        conf       = self._calculate_confidence(products, user_intent)
        return SystemResponse(
            session_id=session_id, user_id=user_id,
            response_type=rtype, message=message,
            products=products, confidence=conf,
            need_clarification=need_clarification,
            clarification_questions=cqs, suggestions=suggs,
        )

    def _determine_response_type(self, products, user_intent, need_clarification, history_len):
        if need_clarification:
            return "clarification_needed"
        if not products:
            return "no_results"
        intent = user_intent.get("primary_intent", {}).get("intent", "")
        return {
            "purchase":       "purchase_recommendation",
            "bulk_purchase":  "purchase_recommendation",
            "compare":        "comparison_result",
            "visual_search":  "visual_search_result",
            "link_analysis":  "link_analysis_result",
        }.get(intent, "general_recommendation")

    def _generate_message(self, rtype, products, user_intent):
        if rtype == "clarification_needed":
            return "为了给您更准确的推荐，请提供更多信息："
        if not products:
            return "抱歉，没有找到符合您要求的商品。请尝试更具体的描述，或者上传图片看看。"
        p = products[0]
        desc = p.description or "这款商品很受欢迎。"
        if rtype == "purchase_recommendation":
            return f"为您推荐：{p.title}，价格 {p.price}{p.currency}。{desc}"
        if rtype == "comparison_result":
            if len(products) >= 2:
                return f"为您找到 {len(products)} 个相关商品，建议对比：{products[0].title} 和 {products[1].title}"
            return f"找到相关商品：{p.title}"
        if rtype == "visual_search_result":
            return f"根据图片识别，为您找到 {len(products)} 个相似商品。"
        if rtype == "link_analysis_result":
            return f"已分析链接中的商品信息，并为您找到 {len(products)} 个相关商品。"
        return f"为您找到 {len(products)} 个相关商品。"

    def _generate_clarification_questions(self, user_intent, user_state):
        intent   = user_intent.get("primary_intent", {}).get("intent", "")
        entities = user_intent.get("entities", {})
        questions = []
        if intent in ("purchase", "bulk_purchase"):
            if not entities.get("price_range"):
                questions.append("您的预算是多少？")
            if not entities.get("categories"):
                questions.append("您想购买什么类型的商品？")
        elif intent == "compare":
            if len(entities.get("brands", [])) < 2:
                questions.append("您想比较哪些品牌或型号？")
        elif intent == "visual_search":
            questions.append("您能描述一下图片中商品的具体特征吗？")
        if not questions:
            questions = ["您可以提供更详细的需求描述吗？",
                         "您有特定的品牌或型号偏好吗？",
                         "您的预算是多少？"]
        return questions[:3]

    def _generate_suggestions(self, products, user_intent):
        suggestions = []
        if len(products) >= 3:
            suggestions.append("您可以通过筛选条件来缩小范围")
            suggestions.append("点击商品图片可以查看详细信息")
        if user_intent.get("primary_intent", {}).get("intent") == "compare":
            suggestions.append("可以使用对比功能详细比较商品参数")
        if len(products) > 10:
            suggestions.append("当前结果较多，建议添加更多筛选条件")
        return suggestions

    def _calculate_confidence(self, products, user_intent):
        if not products:
            return 0.3
        pc = user_intent.get("primary_intent", {}).get("confidence", 0.5)
        pf = min(len(products) / 10, 1.0)
        sf = sum(p.score for p in products[:5]) / min(len(products), 5) if products else 0.0
        return round(min(max(pc * 0.6 + pf * 0.2 + sf * 0.2, 0.0), 1.0), 3)


# ==================== 第四部分：数据层 ====================
class MockProductDatabase:
    def __init__(self):
        self.products: Dict[str, ProductInfo] = {}
        self._init_sample_products()

    def _init_sample_products(self):
        samples = [
            ProductInfo("p001", PlatformType.TMALL,     "苹果iPhone 15 Pro Max 256GB 钛金属原色 5G手机",       8999.0, category="手机",   brand="苹果",  image_urls=["https://img.example.com/iphone15-1.jpg"],   description="苹果最新旗舰手机，A17 Pro芯片，钛金属设计，5倍光学变焦"),
            ProductInfo("p002", PlatformType.JD,        "华为Mate 60 Pro 12GB+512GB 雅川青 卫星通话手机",       6999.0, category="手机",   brand="华为",  image_urls=["https://img.example.com/mate60-1.jpg"],     description="华为旗舰手机，卫星通话，昆仑玻璃，麒麟芯片"),
            ProductInfo("p003", PlatformType.PINDUODUO, "耐克跑步鞋 Air Zoom Pegasus 40 男女运动鞋",             699.0, category="运动鞋", brand="耐克",  image_urls=["https://img.example.com/nike-1.jpg"],       description="专业跑步鞋，Zoom Air气垫，轻便透气"),
            ProductInfo("p004", PlatformType.DOUYIN,    "珍珠项链 女 2023新款 气质百搭 淡水珍珠",               299.0, category="珠宝",   brand="周大福", image_urls=["https://img.example.com/pearl-1.jpg"],      description="淡水珍珠项链，气质百搭，精美礼盒包装"),
            ProductInfo("p005", PlatformType.VIP,       "NIKE AIR FORCE 1 空军一号 男女运动鞋",                  599.0, category="运动鞋", brand="耐克",  image_urls=["https://img.example.com/airforce-1.jpg"],   description="经典空军一号，皮质鞋面，舒适缓震"),
            ProductInfo("p006", PlatformType.ALIBABA,   "夏季新款T恤 男女同款 纯棉短袖 可定制logo",              35.0, category="服装",   brand="无印良品", image_urls=["https://img.example.com/tshirt-1.jpg"],    description="100%纯棉T恤，舒适透气，支持logo定制",    platform_specific={"wholesale": True, "moq": 100}),
            ProductInfo("p007", PlatformType.TMALL,     "戴尔XPS 13 笔记本电脑 13.4英寸 4K触控屏",             9999.0, category="笔记本电脑", brand="戴尔", image_urls=["https://img.example.com/xps13-1.jpg"],    description="轻薄本，4K触控屏，英特尔酷睿i7"),
            ProductInfo("p008", PlatformType.JD,        "海尔冰箱 对开门 变频 智能 520L",                       3999.0, category="冰箱",   brand="海尔",  image_urls=["https://img.example.com/fridge-1.jpg"],     description="对开门冰箱，变频节能，智能控制"),
            ProductInfo("p009", PlatformType.PINDUODUO, "儿童玩具 乐高兼容积木 城市系列 1000颗粒",                89.0, category="玩具",   brand="乐高",  image_urls=["https://img.example.com/lego-1.jpg"],       description="兼容乐高积木，1000颗粒，城市系列"),
            ProductInfo("p010", PlatformType.DOUYIN,    "美妆蛋 6个装 不吃粉 化妆工具",                          29.9, category="美妆",   brand="尔木萄", image_urls=["https://img.example.com/beauty-1.jpg"],     description="不吃粉美妆蛋，6个装，柔软亲肤"),
        ]
        for p in samples:
            self.products[p.product_id] = p

    def search_products(self, text: str = "",
                        conditions: Optional[Dict[str, Any]] = None,
                        keywords: Optional[List[str]] = None) -> List[ProductInfo]:
        conditions = conditions or {}
        keywords   = keywords or []
        tl = text.lower()
        matched = []
        for p in self.products.values():
            s = 0.0
            if tl:
                if tl in p.title.lower():      s += 3.0
                if p.description and tl in p.description.lower(): s += 1.0
            if conditions.get("brand")    and p.brand    == conditions["brand"]:    s += 2.0
            if conditions.get("category") and p.category == conditions["category"]: s += 2.0
            if conditions.get("price_range"):
                lo, hi = conditions["price_range"]
                if lo <= p.price <= hi:            s += 1.5
                elif p.price < lo * 0.5 or p.price > hi * 2: s -= 1.0
            for kw in keywords:
                if kw in p.title.lower(): s += 0.5
            if s > 0:
                p.score = min(s / 10.0, 1.0)
                matched.append(p)
        matched.sort(key=lambda x: x.score, reverse=True)
        return matched

    def search_by_features(self, categories: Optional[List[str]] = None,
                           brands: Optional[List[str]] = None,
                           colors: Optional[List[str]] = None) -> List[ProductInfo]:
        categories = categories or []
        brands     = brands or []
        matched = []
        for p in self.products.values():
            s = 0.0
            for c in categories:
                if p.category and c in p.category: s += 2.0
            for b in brands:
                if p.brand and b in p.brand:       s += 1.5
            if s > 0:
                p.score = min(s / 10.0, 1.0)
                matched.append(p)
        matched.sort(key=lambda x: x.score, reverse=True)
        return matched

    def search_similar_products(self, title="", brand="", category="", price=0.0) -> List[ProductInfo]:
        matched = []
        for p in self.products.values():
            s = 0.0
            if category and p.category == category: s += 2.0
            if brand    and p.brand    == brand:    s += 1.5
            if price    and 0.5 * price <= p.price <= 2.0 * price: s += 1.0
            if s > 0:
                p.score = min(s / 10.0, 1.0)
                matched.append(p)
        matched.sort(key=lambda x: x.score, reverse=True)
        return matched

    def get_hot_products(self, categories: Optional[List[str]] = None, limit: int = 10) -> List[ProductInfo]:
        products = list(self.products.values())
        if categories:
            products = [p for p in products if p.category in categories]
        for p in products:
            p.score = round(random.uniform(0.6, 1.0), 3)
        products.sort(key=lambda x: x.score, reverse=True)
        return products[:limit]

    def get_wholesale_products(self, min_order_quantity: int = 1, limit: int = 10) -> List[ProductInfo]:
        result = []
        for p in self.products.values():
            if p.price < 1000 or any(kw in p.title for kw in ["批发", "定制", "供货"]):
                p.score = 0.9 if any(kw in p.title for kw in ["批发", "定制"]) else 0.8
                result.append(p)
        result.sort(key=lambda x: x.score, reverse=True)
        return result[:limit]

    def get_similar_products(self, product_id: str, limit: int = 3) -> List[ProductInfo]:
        if product_id not in self.products:
            return []
        base = self.products[product_id]
        similar = [p for p in self.products.values()
                   if p.product_id != product_id and p.category == base.category]
        for p in similar:
            p.score = round(random.uniform(0.6, 0.9), 3)
        similar.sort(key=lambda x: x.score, reverse=True)
        return similar[:limit]

    def get_complementary_products(self, product_id: str, limit: int = 2) -> List[ProductInfo]:
        if product_id not in self.products:
            return []
        base = self.products[product_id]
        compl_keywords = {
            "手机":    ["手机壳", "充电器"],
            "运动鞋":  ["袜子", "运动服"],
            "笔记本电脑": ["鼠标", "键盘", "支架"],
        }
        target_kws = compl_keywords.get(base.category or "", [])
        result = [p for p in self.products.values()
                  if p.product_id != product_id
                  and any(kw in p.title for kw in target_kws)]
        for p in result:
            p.score = 0.7
        return result[:limit]


# ==================== 第五部分：基础设施层 ====================
class MessageQueue:
    """消息队列（内存实现，asyncio.Lock 线程安全）"""

    def __init__(self, maxsize: int = 1000):
        self._queues: Dict[str, list] = defaultdict(list)
        self._maxsize = maxsize
        self._lock = asyncio.Lock()

    async def publish(self, queue_name: str, message: Dict[str, Any]):
        async with self._lock:
            q = self._queues[queue_name]
            q.append({"message": message, "timestamp": datetime.now().isoformat()})
            if len(q) > self._maxsize:
                self._queues[queue_name] = q[-self._maxsize:]
        logger.debug(f"MQ publish → {queue_name}: {message.get('type', '-')}")

    async def consume(self, queue_name: str) -> Optional[Dict[str, Any]]:
        await asyncio.sleep(0)  # yield to event loop
        async with self._lock:
            if self._queues.get(queue_name):
                return self._queues[queue_name].pop(0)["message"]
        return None

    async def queue_length(self, queue_name: str) -> int:
        async with self._lock:
            return len(self._queues.get(queue_name, []))


class Cache:
    """TTL 缓存（asyncio.Lock 线程安全）"""

    def __init__(self):
        self._data: Dict[str, Any]   = {}
        self._ttl:  Dict[str, float] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        async with self._lock:
            if key not in self._data:
                return None
            if key in self._ttl and self._ttl[key] < time.monotonic():
                del self._data[key]
                del self._ttl[key]
                return None
            return self._data[key]

    async def set(self, key: str, value: Any, ttl: int = 300):
        async with self._lock:
            self._data[key] = value
            if ttl > 0:
                self._ttl[key] = time.monotonic() + ttl

    async def delete(self, key: str):
        async with self._lock:
            self._data.pop(key, None)
            self._ttl.pop(key, None)

    async def clear_expired(self):
        now = time.monotonic()
        async with self._lock:
            expired = [k for k, exp in self._ttl.items() if exp < now]
            for k in expired:
                del self._data[k]
                del self._ttl[k]


class Storage:
    """KV 存储（内存实现）"""

    def __init__(self):
        self._store: Dict[str, Dict] = {}
        self._lock = asyncio.Lock()

    async def save(self, key: str, data: Any):
        now = datetime.now().isoformat()
        async with self._lock:
            if key in self._store:
                self._store[key] = {**self._store[key], "data": data, "updated_at": now}
            else:
                self._store[key] = {"data": data, "created_at": now, "updated_at": now}

    async def load(self, key: str) -> Optional[Any]:
        async with self._lock:
            entry = self._store.get(key)
            return entry["data"] if entry else None

    async def delete(self, key: str):
        async with self._lock:
            self._store.pop(key, None)


# ==================== 第六部分：核心服务 ====================
class MultimodalProductService:
    """多模态商品服务 - 核心服务类"""

    def __init__(self):
        self._start_time: float = time.monotonic()

        # 基础设施
        self.message_queue = MessageQueue()
        self.cache         = Cache()
        self.storage       = Storage()

        # 数据层
        self.product_db        = MockProductDatabase()
        self.user_profile_mgr  = UserProfileManager()

        # 业务层
        self.conv_mgr          = ConversationManager()
        self.response_generator = ResponseGenerator(self.conv_mgr)
        self.product_recommender = ProductRecommendationEngine(self.product_db, self.user_profile_mgr)

        # AI层
        self.intent_engine      = IntentUnderstandingEngine()
        self.product_recognizer = ProductRecognitionEngine(self.product_db)

        # 输入处理器
        self.input_processors: Dict[InputType, BaseInputProcessor] = {
            InputType.TEXT:  TextInputProcessor(),
            InputType.IMAGE: ImageInputProcessor(),
            InputType.VOICE: VoiceInputProcessor(),
            InputType.LINK:  LinkInputProcessor(),
        }

        # 监控指标
        self.metrics: Dict[str, Any] = {
            "total_requests":    0,
            "successful_requests": 0,
            "failed_requests":   0,
            "avg_response_time": 0.0,
            "requests_by_type":  defaultdict(int),
        }

    async def process_request(self,
                              session_id: str,
                              user_id: str,
                              input_type: str,
                              content: Any,
                              metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """处理用户请求 — 主入口（12步流水线）"""
        start   = time.monotonic()
        metadata = metadata or {}
        self.metrics["total_requests"] += 1
        self.metrics["requests_by_type"][input_type] += 1

        try:
            logger.info(f"Request start  session={session_id} user={user_id} type={input_type}")

            # 1. 验证 input_type
            try:
                itype = InputType(input_type)
            except ValueError:
                raise ValueError(f"不支持的输入类型: {input_type!r}，可选: text/image/voice/link")

            # 2. 构建 UserInput 对象
            user_input = UserInput(
                session_id=session_id, user_id=user_id,
                input_type=itype, content=content, metadata=metadata,
            )

            # 3. 输入处理（含验证）
            processed = await self._process_input(user_input)

            # 4. 获取用户画像
            profile = self.user_profile_mgr.get_profile(user_id)

            # 5. 意图理解
            user_intent = await self.intent_engine.understand_intent(processed, profile)

            # 6. 商品识别
            recognized = await self.product_recognizer.recognize_product(processed, user_intent)

            # 7. 个性化推荐
            recommended = await self.product_recommender.recommend_products(
                user_id, recognized, user_intent)

            # 8. 是否需要澄清
            need_clarification = self._need_clarification(processed, user_intent, recommended)

            # 9. 生成响应
            response = await self.response_generator.generate_response(
                session_id, user_id, recommended, user_intent, need_clarification)

            # 10. 记录对话
            self.conv_mgr.add_to_conversation(session_id, user_input, response)

            # 11. 更新用户画像
            self.user_profile_mgr.update_profile_from_interaction(user_id, {
                "input_type":    input_type,
                "intent":        user_intent,
                "products":      [p.to_dict() for p in recommended[:3]],
                "response_type": response.response_type,
            })

            # 12. 异步发布事件 & 缓存
            await self.message_queue.publish("processed_requests", {
                "type": "request_processed",
                "session_id": session_id, "user_id": user_id,
                "response": response.to_dict(),
                "timestamp": datetime.now().isoformat(),
            })
            cache_key = f"resp:{session_id}:{hashlib.md5(str(content).encode()).hexdigest()[:8]}"
            await self.cache.set(cache_key, response.to_dict(), ttl=60)

            elapsed = time.monotonic() - start
            self._update_avg_response_time(elapsed)
            self.metrics["successful_requests"] += 1
            logger.info(f"Request done   session={session_id} t={elapsed:.3f}s products={len(recommended)}")

            return {
                "success": True,
                "response": response.to_dict(),
                "metrics": {
                    "response_time": round(elapsed, 3),
                    "products_found": len(recommended),
                    "confidence": response.confidence,
                },
            }

        except Exception as exc:
            self.metrics["failed_requests"] += 1
            logger.error(f"Request failed session={session_id} error={exc}", exc_info=True)
            error_resp = SystemResponse(
                session_id=session_id, user_id=user_id,
                response_type="error",
                message="抱歉，处理您的请求时出现了问题，请稍后重试。",
                confidence=0.0,
            )
            return {"success": False, "error": str(exc), "response": error_resp.to_dict()}

    async def _process_input(self, user_input: UserInput) -> Dict[str, Any]:
        processor = self.input_processors.get(user_input.input_type)
        if not processor:
            raise ValueError(f"未找到处理器: {user_input.input_type}")
        return await processor.process(user_input)

    def _need_clarification(self, processed, user_intent, products) -> bool:
        if not products:
            return True
        primary_conf = user_intent.get("primary_intent", {}).get("confidence", 0)
        if primary_conf < 0.4:
            return True
        if len(products) > 20:
            return True
        # 文本输入且实体完全缺失时
        if processed.get("input_type") == "text":
            entities = user_intent.get("entities", {})
            if not entities.get("categories") and not entities.get("brands"):
                return True
        return False

    def _update_avg_response_time(self, new_time: float):
        alpha = 0.1
        cur   = self.metrics["avg_response_time"]
        self.metrics["avg_response_time"] = round(
            new_time if self.metrics["total_requests"] == 1
            else alpha * new_time + (1 - alpha) * cur, 4)

    async def get_conversation_history(self, session_id: str) -> List[Dict]:
        return self.conv_mgr.get_conversation_history(session_id)

    async def clear_conversation(self, session_id: str):
        self.conv_mgr.clear_conversation(session_id)

    async def get_user_profile(self, user_id: str) -> Optional[UserProfile]:
        return self.user_profile_mgr.get_profile(user_id)

    async def get_metrics(self) -> Dict[str, Any]:
        return {
            **{k: (dict(v) if isinstance(v, defaultdict) else v)
               for k, v in self.metrics.items()},
            "uptime_seconds":  round(time.monotonic() - self._start_time, 1),
            "active_sessions": len(self.conv_mgr.conversations),
            "total_users":     len(self.user_profile_mgr.profiles),
        }


# ==================== 第七部分：API接口 ====================
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional as Opt
import uvicorn


class APIRequest(BaseModel):
    session_id: Opt[str] = Field(default_factory=lambda: f"session_{uuid.uuid4().hex[:8]}")
    user_id:    str      = Field(default="default_user")
    input_type: str      = Field(...,  description="输入类型: text | image | voice | link")
    content:    str      = Field(...,  description="输入内容（文本或 base64 编码）")
    metadata:   Opt[Dict[str, Any]] = Field(default_factory=dict)


class APIResponse(BaseModel):
    success: bool
    data:    Opt[Dict[str, Any]] = None
    error:   Opt[str]            = None
    metrics: Opt[Dict[str, Any]] = None


class FastAPIApp:
    """FastAPI 应用封装"""

    def __init__(self, product_service: MultimodalProductService):
        self.service = product_service
        self.app = FastAPI(
            title="多模态商品识别系统 API",
            description="支持文本、图片、语音、链接的多模态商品识别系统",
            version="1.0.0",
        )
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"], allow_credentials=True,
            allow_methods=["*"], allow_headers=["*"],
        )
        self._setup_routes()
        self._setup_lifecycle()

    def _setup_lifecycle(self):
        @self.app.on_event("startup")
        async def _startup():
            self.service._start_time = time.monotonic()
            logger.info("多模态商品识别系统已启动")

        @self.app.on_event("shutdown")
        async def _shutdown():
            logger.info("多模态商品识别系统已关闭")

    def _setup_routes(self):
        svc = self.service

        # ── 根路由 ─────────────────────────────────────────────
        @self.app.get("/", summary="服务信息")
        async def root():
            return {
                "service": "多模态商品识别系统", "version": "1.0.0", "status": "running",
                "endpoints": {
                    "POST /process":                   "处理多模态输入",
                    "GET  /health":                    "健康检查",
                    "GET  /history/{session_id}":      "获取对话历史",
                    "GET  /profile/{user_id}":         "获取用户画像",
                    "GET  /metrics":                   "获取系统指标",
                    "DELETE /conversation/{session_id}": "清空对话",
                    "GET  /products/search":           "商品搜索",
                },
            }

        # ── 健康检查 ────────────────────────────────────────────
        @self.app.get("/health", summary="健康检查")
        async def health():
            return {"status": "ok", "timestamp": datetime.now().isoformat()}

        # ── 处理多模态输入 ──────────────────────────────────────
        @self.app.post("/process", response_model=APIResponse, summary="处理多模态输入")
        async def process_request(request: APIRequest):
            """
            处理多模态输入请求。

            - **text**: content 直接为文本字符串
            - **image / voice**: content 为 base64 编码的二进制数据
            - **link**: content 为商品链接 URL
            """
            content: Any = request.content
            if request.input_type in ("image", "voice"):
                try:
                    content = base64.b64decode(request.content)
                except Exception:
                    raise HTTPException(status_code=400, detail="无效的 base64 编码")

            result = await svc.process_request(
                session_id=request.session_id,
                user_id=request.user_id,
                input_type=request.input_type,
                content=content,
                metadata=request.metadata or {},
            )
            if result["success"]:
                return APIResponse(success=True, data=result["response"], metrics=result.get("metrics"))
            return APIResponse(success=False, error=result.get("error"), data=result.get("response"))

        # ── 对话历史 ────────────────────────────────────────────
        @self.app.get("/history/{session_id}", summary="获取对话历史")
        async def get_history(session_id: str):
            history = await svc.get_conversation_history(session_id)
            return {"session_id": session_id, "count": len(history), "history": history}

        # ── 用户画像 ────────────────────────────────────────────
        @self.app.get("/profile/{user_id}", summary="获取用户画像")
        async def get_profile(user_id: str):
            profile = await svc.get_user_profile(user_id)
            if not profile:
                raise HTTPException(status_code=404, detail=f"用户 {user_id!r} 不存在")
            return {"user_id": user_id, "profile": profile.to_dict()}

        # ── 系统指标 ────────────────────────────────────────────
        @self.app.get("/metrics", summary="获取系统指标")
        async def get_metrics():
            return await svc.get_metrics()

        # ── 清空对话 ────────────────────────────────────────────
        @self.app.delete("/conversation/{session_id}", summary="清空对话")
        async def clear_conversation(session_id: str):
            await svc.clear_conversation(session_id)
            return {"session_id": session_id, "cleared": True}

        # ── 商品搜索 ────────────────────────────────────────────
        @self.app.get("/products/search", summary="商品搜索")
        async def search_products(
            q:        str          = Query(default="", description="搜索关键词"),
            platform: Opt[str]     = Query(default=None, description="平台过滤"),
            category: Opt[str]     = Query(default=None, description="类别过滤"),
            limit:    int          = Query(default=10, ge=1, le=50, description="返回数量"),
        ):
            conditions: Dict[str, Any] = {}
            if category:
                conditions["category"] = category

            products = svc.product_db.search_products(
                text=q, conditions=conditions, keywords=[q] if q else [])

            if platform:
                try:
                    pt = PlatformType(platform)
                    products = [p for p in products if p.platform == pt]
                except ValueError:
                    raise HTTPException(status_code=400, detail=f"未知平台: {platform!r}")

            return {
                "query":    q,
                "total":    len(products),
                "limit":    limit,
                "products": [p.to_dict() for p in products[:limit]],
            }

        # ── 全局异常处理 ────────────────────────────────────────
        @self.app.exception_handler(ValueError)
        async def value_error_handler(request, exc):
            return JSONResponse(status_code=400, content={"success": False, "error": str(exc)})

        @self.app.exception_handler(Exception)
        async def generic_error_handler(request, exc):
            logger.error(f"Unhandled error: {exc}", exc_info=True)
            return JSONResponse(status_code=500, content={"success": False, "error": "服务内部错误"})


# ==================== 工厂函数 & 主入口 ====================
def create_app() -> FastAPI:
    """创建并返回 FastAPI 应用实例（供 ASGI 服务器挂载）"""
    service = MultimodalProductService()
    api     = FastAPIApp(service)
    return api.app


if __name__ == "__main__":
    uvicorn.run(
        create_app(),
        host="0.0.0.0",
        port=8010,
        log_level="info",
        access_log=True,
    )
