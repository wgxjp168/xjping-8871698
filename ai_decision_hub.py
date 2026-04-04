"""
ai_decision_hub.py
AI决策中枢 - 核心智能层
包含：意图识别、决策引擎、大模型服务、报告生成
"""

import asyncio
import enum
import json
import os
import time
import uuid
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
import logging
import re
import base64
import random
from decimal import Decimal
from collections import defaultdict, Counter as PyCounter
from functools import lru_cache

# ── 可选重型依赖 ────────────────────────────────────────────────
try:
    import numpy as np
    _HAS_NUMPY = True
except ImportError:
    _HAS_NUMPY = False

try:
    import aiohttp as _aiohttp
    _HAS_AIOHTTP = True
except ImportError:
    _HAS_AIOHTTP = False

try:
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.orm import declarative_base, sessionmaker
    from sqlalchemy import Column, String, Integer, Float, Boolean, JSON, DateTime, Text
    _HAS_SQLALCHEMY = True
    Base = declarative_base()
except ImportError:
    _HAS_SQLALCHEMY = False
    Base = object  # type: ignore

try:
    import redis.asyncio as _redis
    _HAS_REDIS = True
except ImportError:
    _HAS_REDIS = False

try:
    from prometheus_client import (Counter as _PCounter, Histogram as _PHisto,
                                   Gauge as _PGauge, generate_latest,
                                   CONTENT_TYPE_LATEST, CollectorRegistry)
    _HUB_REGISTRY = CollectorRegistry()
    _HAS_PROMETHEUS = True
except ImportError:
    _HAS_PROMETHEUS = False
    _HUB_REGISTRY = None  # type: ignore

from pydantic import BaseModel, Field, validator
_PydanticBase = BaseModel
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
import uvicorn

# ==================== 配置和日志 ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
)
logger = logging.getLogger(__name__)


def _make_counter(name, doc, labels=None):
    if not _HAS_PROMETHEUS:
        return None
    try:
        if labels:
            return _PCounter(name, doc, labels, registry=_HUB_REGISTRY)
        return _PCounter(name, doc, registry=_HUB_REGISTRY)
    except Exception:
        return None

def _make_histo(name, doc, labels=None):
    if not _HAS_PROMETHEUS:
        return None
    try:
        if labels:
            return _PHisto(name, doc, labels, registry=_HUB_REGISTRY)
        return _PHisto(name, doc, registry=_HUB_REGISTRY)
    except Exception:
        return None

def _make_gauge(name, doc):
    if not _HAS_PROMETHEUS:
        return None
    try:
        return _PGauge(name, doc, registry=_HUB_REGISTRY)
    except Exception:
        return None


# ==================== 枚举 ====================
class UserType(Enum):
    B2B_BUYER    = "b2b_buyer"
    B2C_CONSUMER = "b2c_consumer"


class IntentType(Enum):
    PURCHASE  = "purchase"
    COMPARE   = "compare"
    INQUIRE   = "inquire"
    SEARCH    = "search"
    RECOMMEND = "recommend"
    CUSTOMIZE = "customize"


class BrandPreference(Enum):
    SPECIFIED   = "specified"
    UNSPECIFIED = "unspecified"
    ANY         = "any"


class ProductCategory(Enum):
    ELECTRONICS    = "electronics"
    CLOTHING       = "clothing"
    HOME_APPLIANCES = "home_appliances"
    BEAUTY         = "beauty"
    FOOD           = "food"
    FURNITURE      = "furniture"
    SPORTS         = "sports"
    BOOKS          = "books"
    MOTHER_BABY    = "mother_baby"
    AUTOMOTIVE     = "automotive"


# ==================== 数据模型 ====================
@dataclass
class DialogState:
    session_id: str
    user_id:    str
    user_type:  UserType
    intent:       Optional[IntentType]   = None
    current_step: str                    = "initial"
    context:      Dict[str, Any]         = field(default_factory=dict)
    history:      List[Dict[str, Any]]   = field(default_factory=list)
    missing_info: List[str]              = field(default_factory=list)
    created_at:   datetime               = field(default_factory=datetime.now)
    updated_at:   datetime               = field(default_factory=datetime.now)
    turns:        int                    = 0

    def add_message(self, role: str, content: str, metadata: Optional[Dict] = None):
        self.history.append({
            "role":      role,
            "content":   content,
            "timestamp": datetime.now().isoformat(),
            "metadata":  metadata or {},
        })
        self.turns   += 1
        self.updated_at = datetime.now()
        if len(self.history) > 100:
            self.history = self.history[-100:]

    def get_context_summary(self) -> str:
        parts = []
        if self.intent:
            parts.append(f"意图: {self.intent.value}")
        for key in ("brand_preference", "budget", "requirements"):
            if self.context.get(key):
                parts.append(f"{key}: {self.context[key]}")
        return "; ".join(parts)


@dataclass
class IntentResult:
    intent:                 IntentType
    confidence:             float
    entities:               Dict[str, Any]
    slots:                  Dict[str, Any]
    user_type:              UserType
    needs_clarification:    bool              = False
    clarification_questions: List[str]        = field(default_factory=list)

    # ── Compatibility properties used by DecisionEngineService ──────────────

    @property
    def intent_type(self) -> str:
        return self.intent.value

    @property
    def purchase_type(self) -> str:
        """Map UserType to purchase_type string (b2b / b2c)."""
        return "b2b" if self.user_type == UserType.B2B_BUYER else "b2c"

    @property
    def parameters(self) -> "ParameterSet":
        """Build a ParameterSet from the extracted slots (only known ParameterSet fields)."""
        s = self.slots
        pr = s.get("price_range") or self.entities.get("price_range")
        brand_raw = s.get("brand") or self.entities.get("brand")
        brand = (brand_raw[0] if isinstance(brand_raw, list) else brand_raw) or None
        cat_raw = s.get("category") or self.entities.get("category")
        category = (cat_raw[0] if isinstance(cat_raw, list) else cat_raw) or None
        return ParameterSet(
            brand=brand,
            category=category,
            quantity=int(s.get("quantity", 1)),
            price_range=tuple(pr[:2]) if pr and len(pr) >= 2 else None,
            features=s.get("features", []),
            material=s.get("material"),
            color=s.get("color"),
            moq=s.get("moq"),
            delivery_time=s.get("delivery_time"),
            warranty=s.get("warranty"),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "intent":                  self.intent.value,
            "confidence":              self.confidence,
            "entities":                self.entities,
            "slots":                   self.slots,
            "user_type":               self.user_type.value,
            "needs_clarification":     self.needs_clarification,
            "clarification_questions": self.clarification_questions,
        }


@dataclass
class ParameterSet:
    brand:         Optional[str]                = None
    category:      Optional[str]                = None
    price_range:   Optional[Tuple[float, float]] = None
    quantity:      Optional[int]                = None
    dimensions:    Optional[Dict[str, float]]   = None
    weight:        Optional[float]              = None
    material:      Optional[str]                = None
    color:         Optional[str]                = None
    capacity:      Optional[float]              = None
    power:         Optional[float]              = None
    resolution:    Optional[str]                = None
    processor:     Optional[str]                = None
    features:      List[str]                    = field(default_factory=list)
    certifications: List[str]                   = field(default_factory=list)
    moq:           Optional[int]                = None
    delivery_time: Optional[int]                = None
    warranty:      Optional[int]                = None

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ParameterSet":
        """安全地从字典构造（忽略未知键）"""
        known = {f for f in cls.__dataclass_fields__}
        kwargs = {k: v for k, v in d.items() if k in known}
        # price_range may arrive as list → convert to tuple
        if "price_range" in kwargs and isinstance(kwargs["price_range"], list):
            kwargs["price_range"] = tuple(kwargs["price_range"][:2])
        return cls(**kwargs)

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        for k, v in self.__dict__.items():
            if v is not None and v != [] and v != {}:
                result[k] = list(v) if isinstance(v, tuple) else v
        return result

    def is_complete(self) -> bool:
        return bool(self.category and self.price_range)


@dataclass
class ProcurementStandard:
    standard_id:      str
    user_id:          str
    user_type:        UserType
    intent:           IntentType
    parameters:       ParameterSet
    priority_weights: Dict[str, float]
    constraints:      Dict[str, Any]
    created_at:       datetime = field(default_factory=datetime.now)

    def to_query(self) -> Dict[str, Any]:
        q: Dict[str, Any] = {"category": self.parameters.category}
        if self.parameters.price_range:
            q["price_min"] = self.parameters.price_range[0]
            q["price_max"] = self.parameters.price_range[1]
        if self.parameters.brand:
            q["brand"] = self.parameters.brand
        if self.parameters.quantity:
            q["min_quantity"] = self.parameters.quantity
        if self.user_type == UserType.B2B_BUYER:
            q["is_wholesale"] = True
            if self.parameters.moq:
                q["moq"] = self.parameters.moq
        return {k: v for k, v in q.items() if v is not None}

    def calculate_priority_score(self, product_features: Dict[str, Any]) -> float:
        score = total = 0.0
        for param, weight in self.priority_weights.items():
            if product_features.get(param) is not None:
                score += weight * 0.8
                total += weight
        return round(score / total, 4) if total else 0.0


@dataclass
class ProductCandidate:
    product_id:    str
    platform:      str
    title:         str
    price:         float
    score:         float             = 0.0
    scores:        Dict[str, float]  = field(default_factory=dict)
    features:      Dict[str, Any]    = field(default_factory=dict)
    match_reasons: List[str]         = field(default_factory=list)
    risks:         List[str]         = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "product_id":    self.product_id,
            "platform":      self.platform,
            "title":         self.title,
            "price":         self.price,
            "score":         round(self.score, 2),
            "scores":        {k: round(v, 2) for k, v in self.scores.items()},
            "features":      self.features,
            "match_reasons": self.match_reasons,
            "risks":         self.risks,
        }


@dataclass
class RecommendationResult:
    session_id:           str
    user_id:              str
    recommendation_id:    str
    quality_products:     List[ProductCandidate]
    value_products:       List[ProductCandidate]
    procurement_standard: ProcurementStandard
    analysis_report:      Dict[str, Any]
    generated_at:         datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id":        self.session_id,
            "user_id":           self.user_id,
            "recommendation_id": self.recommendation_id,
            "quality_products":  [p.to_dict() for p in self.quality_products],
            "value_products":    [p.to_dict() for p in self.value_products],
            "procurement_standard": {
                "standard_id":      self.procurement_standard.standard_id,
                "parameters":       self.procurement_standard.parameters.to_dict(),
                "priority_weights": self.procurement_standard.priority_weights,
            },
            "analysis_report": self.analysis_report,
            "generated_at":    self.generated_at.isoformat(),
        }


# ==================== 数据库模型 ====================
if _HAS_SQLALCHEMY:
    class DialogSession(Base):  # type: ignore
        __tablename__ = "dialog_sessions"
        session_id      = Column(String(64), primary_key=True)
        user_id         = Column(String(64), index=True)
        user_type       = Column(String(32))
        current_intent  = Column(String(32), nullable=True)
        current_step    = Column(String(64))
        context         = Column(JSON)
        history         = Column(JSON)
        missing_info    = Column(JSON)
        turns           = Column(Integer, default=0)
        created_at      = Column(DateTime, default=datetime.now)
        updated_at      = Column(DateTime, default=datetime.now)
        expired_at      = Column(DateTime, nullable=True)

    class IntentHistory(Base):  # type: ignore
        __tablename__ = "intent_history"
        id          = Column(Integer, primary_key=True, autoincrement=True)
        session_id  = Column(String(64), index=True)
        user_id     = Column(String(64), index=True)
        intent_type = Column(String(32))
        confidence  = Column(Float)
        entities    = Column(JSON)
        slots       = Column(JSON)
        input_text  = Column(Text)
        created_at  = Column(DateTime, default=datetime.now)

    class ProcurementHistory(Base):  # type: ignore
        __tablename__ = "procurement_history"
        id               = Column(Integer, primary_key=True, autoincrement=True)
        standard_id      = Column(String(64), unique=True, index=True)
        user_id          = Column(String(64), index=True)
        user_type        = Column(String(32))
        parameters       = Column(JSON)
        priority_weights = Column(JSON)
        constraints      = Column(JSON)
        created_at       = Column(DateTime, default=datetime.now)


# ==================== 意图识别服务 ====================
class BrandDetector:
    _BRANDS: Dict[str, List[str]] = {
        "electronics":     ["苹果", "华为", "小米", "OPPO", "vivo", "三星", "戴尔", "联想", "华硕"],
        "clothing":        ["耐克", "阿迪", "李宁", "安踏", "优衣库", "ZARA", "H&M"],
        "home_appliances": ["海尔", "美的", "格力", "松下", "西门子"],
        "beauty":          ["兰蔻", "雅诗兰黛", "欧莱雅", "资生堂", "SK-II", "完美日记"],
    }

    def detect(self, text: str, entities: Dict[str, Any]) -> BrandPreference:
        for brands in self._BRANDS.values():
            if any(b in text for b in brands):
                return BrandPreference.SPECIFIED
        if entities.get("brand"):
            return BrandPreference.SPECIFIED
        return BrandPreference.UNSPECIFIED


class ParameterExtractor:
    _RULES: Dict[str, Dict] = {
        "material":   {"patterns": [r"(?:材质|材料).*?(棉|麻|丝|毛|皮革|塑料|金属|玻璃)"]},
        "capacity":   {"patterns": [r"(\d+)(?:GB|TB|升|L|毫升|ml)"]},
        "power":      {"patterns": [r"(\d+)(?:瓦|W|千瓦|KW)"]},
        "resolution": {"patterns": [r"(\d+)[×xX](\d+)(?:像素)?"]},
        "processor":  {"patterns": [r"(i[3579]|锐龙|骁龙|麒麟|天玑)"]},
        "size":       {"patterns": [r"([\d\.]+)(?:寸|英寸)", r"(XS|S|M|L|XL|XXL)"]},
        "quantity":   {"patterns": [r"(\d+)(?:个|件|台|部|套)"]},
    }

    def extract(self, text: str, entities: Dict[str, Any]) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        for param, cfg in self._RULES.items():
            for pat in cfg["patterns"]:
                m = re.search(pat, text)
                if m:
                    val = m.group(1) if m.lastindex == 1 else m.group(0)
                    try:
                        out[param] = float(val) if val.replace(".", "").isdigit() else val
                    except Exception:
                        out[param] = val
                    break
        return out


class IntentRecognitionService:
    """规则优先 + 模拟模型兜底的意图识别服务"""

    _INTENT_RULES: Dict[IntentType, List[str]] = {
        IntentType.PURCHASE:  ["买", "购买", "想买", "要买", "下单", "订购", "采购"],
        IntentType.COMPARE:   ["对比", "比较", "哪个好", "有什么区别", "怎么选"],
        IntentType.INQUIRE:   ["多少钱", "价格", "价位", "报价", "多钱", "贵不贵"],
        IntentType.SEARCH:    ["找", "搜索", "查找", "看看", "浏览"],
        IntentType.RECOMMEND: ["推荐", "建议", "有什么好"],
        IntentType.CUSTOMIZE: ["定制", "定做", "个性化", "特殊要求"],
    }

    _ENTITY_PATTERNS: Dict[str, List[str]] = {
        "brand":    [r"(苹果|华为|小米|OPPO|vivo|三星|耐克|阿迪|戴尔|联想|海尔|美的|格力)"],
        "price":    [r"(\d{3,5})(?:到|-)?(\d{3,5})?(?:元|块)?"],
        "category": [r"(手机|电脑|笔记本|电视|冰箱|洗衣机|衣服|鞋子|化妆品|食品|家具)"],
        "color":    [r"(红色|蓝色|绿色|白色|黑色|灰色|黄色|紫色|粉色)"],
        "quantity": [r"(\d+)(?:个|件|台|部|套)"],
    }

    def __init__(self):
        self.brand_detector    = BrandDetector()
        self.param_extractor   = ParameterExtractor()
        self._req_count        = _make_counter("hub_intent_requests_total", "Intent requests")
        self._accuracy_gauge   = _make_gauge("hub_intent_accuracy", "Intent confidence")

    async def recognize_intent(self, user_id: str, user_type: str,
                                text: str,
                                context: Optional[Dict[str, Any]] = None) -> IntentResult:
        if self._req_count:
            self._req_count.inc()
        context = context or {}
        cleaned = re.sub(r"\s+", " ", text).strip()

        intent, confidence = self._classify_intent(cleaned, context)
        entities            = self._extract_entities(cleaned)
        bp                  = self.brand_detector.detect(cleaned, entities)
        entities["brand_preference"] = bp.value
        entities.update(self.param_extractor.extract(cleaned, entities))
        slots = self._fill_slots(entities, intent, UserType(user_type))
        needs_clarification, questions = self._check_clarification(slots, intent, UserType(user_type))

        if self._accuracy_gauge:
            self._accuracy_gauge.set(confidence)

        return IntentResult(
            intent=intent, confidence=confidence,
            entities=entities, slots=slots,
            user_type=UserType(user_type),
            needs_clarification=needs_clarification,
            clarification_questions=questions,
        )

    async def recognize(self, text: str, context: Optional[Dict] = None) -> "IntentResult":
        """Convenience wrapper used by DecisionEngineService and DialogManagerService."""
        ctx = context or {}
        user_type = ctx.get("user_type", UserType.B2C_CONSUMER.value)
        user_id   = ctx.get("user_id", "anon")
        return await self.recognize_intent(user_id=user_id, user_type=user_type,
                                           text=text, context=ctx)

    def _classify_intent(self, text: str, context: Dict) -> Tuple[IntentType, float]:
        for intent, keywords in self._INTENT_RULES.items():
            if any(kw in text for kw in keywords):
                return intent, round(0.80 + random.random() * 0.15, 3)
        return IntentType.SEARCH, 0.50

    def _extract_entities(self, text: str) -> Dict[str, Any]:
        entities: Dict[str, Any] = {}
        for etype, patterns in self._ENTITY_PATTERNS.items():
            for pat in patterns:
                matches = re.findall(pat, text)
                if matches:
                    flat = []
                    for m in matches:
                        if isinstance(m, tuple):
                            flat.extend(x for x in m if x)
                        elif m:
                            flat.append(m)
                    entities[etype] = list(dict.fromkeys(flat))  # dedup preserve order
                    break
        # price_range from first two price matches
        if "price" in entities and len(entities["price"]) >= 2:
            try:
                lo, hi = float(entities["price"][0]), float(entities["price"][1])
                entities["price_range"] = [min(lo, hi), max(lo, hi)]
            except ValueError:
                pass
        return entities

    def _fill_slots(self, entities: Dict, intent: IntentType, ut: UserType) -> Dict[str, Any]:
        slots: Dict[str, Any] = {"intent": intent.value, "user_type": ut.value}
        brand_list = entities.get("brand", [])
        cat_list   = entities.get("category", [])
        if brand_list:
            slots["brand"]    = brand_list[0]
        if cat_list:
            slots["category"] = cat_list[0]
        if "price_range" in entities:
            slots["budget"] = entities["price_range"]
        if intent == IntentType.COMPARE and len(brand_list) >= 2:
            slots["compare_items"] = brand_list[:2]
        return slots

    def _check_clarification(self, slots: Dict, intent: IntentType,
                              ut: UserType) -> Tuple[bool, List[str]]:
        q: List[str] = []
        if intent == IntentType.PURCHASE:
            if not slots.get("category"):
                q.append("您想购买什么类型的商品？")
            if not slots.get("budget"):
                q.append("您的预算大概是多少？")
        elif intent == IntentType.COMPARE:
            if len(slots.get("compare_items", [])) < 2:
                q.append("您想比较哪些品牌或型号？（请列举两个）")
        elif intent == IntentType.CUSTOMIZE:
            q.append("请描述定制要求（数量、规格、交期等）")
        return bool(q), q


# ==================== 大模型服务 ====================
class LLMService:
    """大模型服务 — 支持 openai / claude / wenxin / local（均为 mock 实现）"""

    _MOCK: Dict[str, str] = {
        "optimize_parameters": json.dumps({
            "optimized_parameters": {
                "brand": None, "category": "手机",
                "price_range": [3000, 5000], "quantity": 1,
                "must_have": ["5G", "128GB以上存储", "官方正品"],
                "nice_to_have": ["快充", "高刷新率屏幕"],
                "exclude": ["二手", "翻新"],
            },
            "explanation": "根据需求生成采购参数"
        }),
        "generate_query": json.dumps({
            "search_query": {
                "keywords": ["手机", "5G"],
                "filters": {"price_min": 3000, "price_max": 5000},
                "sort_by": "sales", "sort_order": "desc",
                "special_requirements": [],
            },
            "explanation": "生成搜索查询"
        }),
        "explain_recommendation": json.dumps({
            "explanation": {
                "reasoning":   "根据您的预算和需求综合推荐",
                "comparison":  "品质款性能更强，性价比款价格更实惠",
                "risks":       "请确认正品和售后政策",
                "suggestions": "建议选择官方旗舰店，注意用户评价",
            }
        }),
    }

    def __init__(self, model: str = "mock"):
        self.current_model = model
        self._req_count = _make_counter("hub_llm_requests_total", "LLM requests")
        self._tok_count = _make_counter("hub_llm_tokens_total", "LLM tokens")

    async def _call_llm(self, prompt: str, template_key: str) -> str:
        await asyncio.sleep(0.02)  # simulate latency
        if self._req_count:
            self._req_count.inc()
        if self._tok_count:
            self._tok_count.inc(len(prompt) // 4)
        return self._MOCK.get(template_key, self._MOCK["optimize_parameters"])

    async def optimize_parameters(self, intent: str, user_type: str,
                                   parameters: Dict, context: Optional[Dict] = None) -> Dict:
        raw = await self._call_llm("", "optimize_parameters")
        try:
            return json.loads(raw)
        except Exception:
            return {"optimized_parameters": parameters, "explanation": "优化失败"}

    async def generate_search_query(self, standard: Dict,
                                     platform: str, user_type: str) -> Dict:
        raw = await self._call_llm("", "generate_query")
        try:
            return json.loads(raw)
        except Exception:
            return {"search_query": {"keywords": [], "filters": {}}, "explanation": ""}

    async def explain_recommendation(self, products: List[Dict],
                                      standard: Dict, user_type: str) -> Dict:
        raw = await self._call_llm("", "explain_recommendation")
        try:
            return json.loads(raw)
        except Exception:
            return {"explanation": {
                "reasoning":   "综合推荐",
                "comparison":  "见商品详情",
                "risks":       "注意正品和售后",
                "suggestions": "建议官方旗舰店购买",
            }}


# ==================== 评分模型 ====================
class BaseScoringModel(ABC):
    """评分模型基类"""

    @abstractmethod
    def score(self, product: Dict[str, Any],
              standard: Dict[str, Any]) -> Tuple[float, Dict[str, float]]:
        """返回 (overall_score, dimension_scores)"""

    @staticmethod
    def _clamp(v: float) -> float:
        return max(0.0, min(1.0, v))

    @staticmethod
    def _price_score(price: float, price_range: Optional[List]) -> float:
        if not price_range or not price:
            return 0.5
        lo, hi = float(price_range[0]), float(price_range[1])
        if lo == hi:
            return 1.0 if price == lo else 0.3
        if lo <= price <= hi:
            # closer to lo (cheaper end) → higher score within range
            return round(1.0 - 0.4 * (price - lo) / (hi - lo), 3)
        if price < lo:
            return 0.6  # cheap but below stated budget (possible quality concern)
        return max(0.0, round(1.0 - (price - hi) / hi, 3))  # over budget

    @staticmethod
    def _rating_score(rating: float) -> float:
        # rating 0-5 → 0-1
        return round(min(1.0, max(0.0, (rating - 3.0) / 2.0)), 3) if rating else 0.5

    @staticmethod
    def _review_count_score(reviews: int) -> float:
        if not reviews:
            return 0.3
        # log scale: 0→0.3, 100→0.6, 10000→1.0
        import math
        return round(min(1.0, 0.3 + 0.7 * math.log10(max(1, reviews)) / 4), 3)


class B2BScoringModel(BaseScoringModel):
    """B2B采购评分 — 供应商资质、信用、交付能力、价格、质量"""
    _WEIGHTS = {
        "supplier_qualification": 0.30,
        "credit_rating":          0.25,
        "delivery_capability":    0.20,
        "price":                  0.15,
        "quality":                0.10,
    }

    def score(self, product: Dict, standard: Dict) -> Tuple[float, Dict[str, float]]:
        feats = product.get("features", {})
        params = standard.get("parameters", {})

        sq = self._clamp(feats.get("shop_rating", 4.0) / 5.0)
        cr = self._clamp(feats.get("credit_score", 0.8))
        # delivery: if delivery_time ≤ standard, score = 1
        std_delivery = params.get("delivery_time") or 30
        actual_delivery = feats.get("delivery_days", 14)
        dc = self._clamp(1.0 - max(0, actual_delivery - std_delivery) / std_delivery)
        pr = self._price_score(product.get("price", 0), params.get("price_range"))
        qu = self._rating_score(feats.get("rating", 4.0))

        dims = {
            "supplier_qualification": sq,
            "credit_rating":          cr,
            "delivery_capability":    dc,
            "price":                  pr,
            "quality":                qu,
        }
        overall = sum(dims[k] * self._WEIGHTS[k] for k in dims)
        return round(overall, 4), dims


class B2CBrandScoringModel(BaseScoringModel):
    """B2C已定品牌评分 — 正品保障、质量、服务、价格、评价"""
    _WEIGHTS = {
        "authenticity": 0.30,
        "quality":      0.25,
        "service":      0.20,
        "price":        0.15,
        "reviews":      0.10,
    }

    def score(self, product: Dict, standard: Dict) -> Tuple[float, Dict[str, float]]:
        feats  = product.get("features", {})
        params = standard.get("parameters", {})

        au = 1.0 if feats.get("is_official") else 0.5
        qu = self._rating_score(feats.get("rating", 4.0))
        sv = self._clamp(feats.get("service_score", 4.5) / 5.0)
        pr = self._price_score(product.get("price", 0), params.get("price_range"))
        rv = self._review_count_score(feats.get("review_count", 0))

        dims = {"authenticity": au, "quality": qu,
                "service": sv, "price": pr, "reviews": rv}
        overall = sum(dims[k] * self._WEIGHTS[k] for k in dims)
        return round(overall, 4), dims


class B2CNoBrandScoringModel(BaseScoringModel):
    """B2C未定品牌评分 — 规格匹配、质量、价格性价比、评价、服务、店龄"""
    _WEIGHTS = {
        "specifications": 0.25,
        "quality":        0.20,
        "price":          0.20,
        "reviews":        0.15,
        "service":        0.10,
        "shop_age":       0.10,
    }

    def score(self, product: Dict, standard: Dict) -> Tuple[float, Dict[str, float]]:
        feats  = product.get("features", {})
        params = standard.get("parameters", {})

        # spec match: how many required features are present
        req_features = params.get("features", [])
        prod_features = feats.get("features", [])
        sp = (sum(1 for f in req_features if f in prod_features) / len(req_features)
              if req_features else 0.7)
        qu = self._rating_score(feats.get("rating", 4.0))
        pr = self._price_score(product.get("price", 0), params.get("price_range"))
        rv = self._review_count_score(feats.get("review_count", 0))
        sv = self._clamp(feats.get("service_score", 4.0) / 5.0)
        sa = self._clamp(min(feats.get("shop_years", 3), 10) / 10.0)

        dims = {"specifications": sp, "quality": qu, "price": pr,
                "reviews": rv, "service": sv, "shop_age": sa}
        overall = sum(dims[k] * self._WEIGHTS[k] for k in dims)
        return round(overall, 4), dims


# ---------------------------------------------------------------------------
# Section s5 — RuleEngine
# ---------------------------------------------------------------------------

class RuleEngine:
    """业务规则引擎：对候选商品列表进行过滤和评分调整"""

    def __init__(self):
        self._rules: List[Dict[str, Any]] = self._default_rules()

    # ---- public ----

    def apply(
        self,
        products: List[Dict],
        standard: Dict,
        context: Dict,
    ) -> List[Dict]:
        """Apply all rules; return sorted, filtered product list."""
        results = []
        for product in products:
            passed, adjustments = self._evaluate(product, standard, context)
            if passed:
                adj_score = adjustments.get("score_delta", 0.0)
                p = dict(product)
                p["_rule_score_delta"] = adj_score
                p["_rule_tags"] = adjustments.get("tags", [])
                results.append(p)
        results.sort(key=lambda x: x.get("score", 0) + x.get("_rule_score_delta", 0),
                     reverse=True)
        return results

    # ---- private ----

    def _evaluate(
        self,
        product: Dict,
        standard: Dict,
        context: Dict,
    ) -> Tuple[bool, Dict]:
        adjustments: Dict[str, Any] = {"score_delta": 0.0, "tags": []}
        for rule in self._rules:
            ok, delta, tags = rule["fn"](product, standard, context)
            if not ok:
                return False, {}
            adjustments["score_delta"] += delta
            adjustments["tags"].extend(tags)
        return True, adjustments

    @staticmethod
    def _default_rules() -> List[Dict]:
        def _blacklist_filter(product, standard, context):
            blacklist = context.get("blacklist_suppliers", [])
            supplier_id = product.get("supplier_id", "")
            if supplier_id in blacklist:
                return False, 0.0, []
            return True, 0.0, []

        def _budget_hard_cap(product, standard, context):
            budget = context.get("budget_cap")
            price = product.get("price", 0)
            if budget is not None and price > budget:
                return False, 0.0, []
            return True, 0.0, []

        def _verified_supplier_boost(product, standard, context):
            if product.get("features", {}).get("is_verified_supplier"):
                return True, 0.05, ["verified_supplier"]
            return True, 0.0, []

        def _low_stock_penalty(product, standard, context):
            stock = product.get("features", {}).get("stock", 9999)
            qty   = standard.get("parameters", {}).get("quantity", 1)
            if stock < qty:
                return False, 0.0, []
            if stock < qty * 1.5:
                return True, -0.03, ["low_stock"]
            return True, 0.0, []

        def _fast_delivery_boost(product, standard, context):
            days = product.get("features", {}).get("delivery_days", 30)
            if days <= 3:
                return True, 0.04, ["fast_delivery"]
            if days <= 7:
                return True, 0.02, ["standard_delivery"]
            return True, 0.0, []

        def _new_product_penalty(product, standard, context):
            review_count = product.get("features", {}).get("review_count", 0)
            if review_count < 10:
                return True, -0.05, ["new_product_low_reviews"]
            return True, 0.0, []

        return [
            {"name": "blacklist_filter",     "fn": _blacklist_filter},
            {"name": "budget_hard_cap",      "fn": _budget_hard_cap},
            {"name": "verified_boost",       "fn": _verified_supplier_boost},
            {"name": "low_stock_penalty",    "fn": _low_stock_penalty},
            {"name": "fast_delivery_boost",  "fn": _fast_delivery_boost},
            {"name": "new_product_penalty",  "fn": _new_product_penalty},
        ]


# ---------------------------------------------------------------------------
# Section s6 — DataCollector
# ---------------------------------------------------------------------------

class DataCollector:
    """多平台商品数据采集（生产环境替换为真实API调用）"""

    PLATFORMS = ["platform_a", "platform_b", "platform_c"]

    def __init__(self, http_session: Optional[Any] = None):
        self._session = http_session
        self._own_session = http_session is None

    async def __aenter__(self):
        if self._own_session and _HAS_AIOHTTP:
            import aiohttp as _ahttp
            self._session = _ahttp.ClientSession(
                timeout=_ahttp.ClientTimeout(total=15)
            )
        return self

    async def __aexit__(self, *_):
        if self._own_session and self._session:
            await self._session.close()

    # ---- public ----

    async def collect(
        self,
        query: str,
        standard: Dict,
        platforms: Optional[List[str]] = None,
        max_per_platform: int = 20,
    ) -> List[Dict]:
        """并发采集所有平台数据，合并去重后返回。"""
        targets = platforms or self.PLATFORMS
        tasks = [
            self._collect_platform(p, query, standard, max_per_platform)
            for p in targets
        ]
        results_nested = await asyncio.gather(*tasks, return_exceptions=True)
        merged: List[Dict] = []
        seen_ids: set = set()
        for i, res in enumerate(results_nested):
            if isinstance(res, Exception):
                logger.warning("DataCollector platform %s error: %s", targets[i], res)
                continue
            for item in res:
                uid = item.get("product_id", "")
                if uid and uid not in seen_ids:
                    seen_ids.add(uid)
                    merged.append(item)
        return merged

    # ---- private ----

    async def _collect_platform(
        self,
        platform: str,
        query: str,
        standard: Dict,
        max_items: int,
    ) -> List[Dict]:
        """Mock implementation — 生产中替换为真实爬虫/API。"""
        await asyncio.sleep(0.05)   # simulate network latency
        params = standard.get("parameters", {})
        price_range = params.get("price_range", (0, 99999))
        min_p, max_p = (price_range[0], price_range[1]) if len(price_range) >= 2 else (0, 99999)

        items = []
        import random, hashlib as _hs
        rng = random.Random(f"{platform}{query}")
        for i in range(min(max_items, 15)):
            pid = _hs.md5(f"{platform}:{query}:{i}".encode()).hexdigest()[:12]
            price = round(rng.uniform(max(min_p * 0.8, 1), min(max_p * 1.2, max_p * 2 + 1)), 2)
            rating = round(rng.uniform(3.5, 5.0), 1)
            items.append({
                "product_id":  f"{platform}_{pid}",
                "platform":    platform,
                "name":        f"{query} 商品{i+1}",
                "price":       price,
                "supplier_id": f"sup_{platform}_{rng.randint(1, 50)}",
                "score":       0.0,
                "features": {
                    "rating":               rating,
                    "review_count":         rng.randint(0, 5000),
                    "is_verified_supplier": rng.random() > 0.4,
                    "is_official":          rng.random() > 0.6,
                    "delivery_days":        rng.randint(1, 15),
                    "stock":                rng.randint(0, 1000),
                    "service_score":        round(rng.uniform(3.5, 5.0), 1),
                    "shop_years":           rng.randint(1, 10),
                    "features":             params.get("features", []),
                    "supplier_qualification": round(rng.uniform(0.5, 1.0), 2),
                    "credit_rating":          round(rng.uniform(0.4, 1.0), 2),
                    "delivery_capability":    round(rng.uniform(0.4, 1.0), 2),
                },
            })
        return items


# ---------------------------------------------------------------------------
# Section s7 — ReportGenerator
# ---------------------------------------------------------------------------

class ReportGenerator:
    """生成推荐报告、市场分析、价格对比"""

    def generate_recommendation_report(
        self,
        recommendations: List[Dict],
        standard: Dict,
        intent: IntentResult,
    ) -> Dict[str, Any]:
        if not recommendations:
            return {"error": "no_recommendations", "items": []}

        prices = [r.get("price", 0) for r in recommendations]
        scores = [r.get("score", 0) for r in recommendations]

        return {
            "summary": {
                "total_candidates": len(recommendations),
                "intent_type":      intent.intent_type,
                "purchase_type":    intent.purchase_type,
                "generated_at":     datetime.utcnow().isoformat() + "Z",
            },
            "price_analysis": self._price_analysis(prices, standard),
            "score_analysis":  self._score_analysis(scores),
            "top_picks":       self._top_picks(recommendations, n=5),
            "market_insights": self._market_insights(recommendations, standard),
        }

    def generate_market_analysis(
        self,
        products: List[Dict],
        standard: Dict,
    ) -> Dict[str, Any]:
        if not products:
            return {"error": "no_products"}
        prices  = [p.get("price", 0) for p in products]
        ratings = [p.get("features", {}).get("rating", 0) for p in products]
        platforms: Dict[str, int] = {}
        for p in products:
            pl = p.get("platform", "unknown")
            platforms[pl] = platforms.get(pl, 0) + 1

        return {
            "total_products": len(products),
            "price_distribution": self._price_analysis(prices, standard),
            "quality_distribution": {
                "avg_rating":  round(sum(ratings) / len(ratings), 2) if ratings else 0,
                "high_rating": sum(1 for r in ratings if r >= 4.5),
                "low_rating":  sum(1 for r in ratings if r < 3.5),
            },
            "platform_distribution": platforms,
        }

    # ---- private helpers ----

    @staticmethod
    def _price_analysis(prices: List[float], standard: Dict) -> Dict:
        if not prices:
            return {}
        sorted_p = sorted(prices)
        n = len(sorted_p)
        avg = sum(sorted_p) / n
        params = standard.get("parameters", {})
        price_range = params.get("price_range", (0, 99999))
        budget = price_range[1] if len(price_range) >= 2 else 99999
        return {
            "min":    sorted_p[0],
            "max":    sorted_p[-1],
            "avg":    round(avg, 2),
            "median": sorted_p[n // 2],
            "budget": budget,
            "within_budget_pct": round(
                sum(1 for p in prices if p <= budget) / n * 100, 1
            ),
        }

    @staticmethod
    def _score_analysis(scores: List[float]) -> Dict:
        if not scores:
            return {}
        n = len(scores)
        avg = sum(scores) / n
        return {
            "avg":       round(avg, 4),
            "max":       max(scores),
            "min":       min(scores),
            "excellent": sum(1 for s in scores if s >= 0.8),
            "good":      sum(1 for s in scores if 0.6 <= s < 0.8),
            "fair":      sum(1 for s in scores if s < 0.6),
        }

    @staticmethod
    def _top_picks(recommendations: List[Dict], n: int = 5) -> List[Dict]:
        sorted_recs = sorted(recommendations, key=lambda x: x.get("score", 0), reverse=True)
        picks = []
        for r in sorted_recs[:n]:
            picks.append({
                "product_id":    r.get("product_id"),
                "name":          r.get("name"),
                "price":         r.get("price"),
                "score":         r.get("score"),
                "platform":      r.get("platform"),
                "match_reasons": r.get("match_reasons", []),
                "rule_tags":     r.get("_rule_tags", []),
            })
        return picks

    @staticmethod
    def _market_insights(products: List[Dict], standard: Dict) -> List[str]:
        insights: List[str] = []
        prices = [p.get("price", 0) for p in products]
        if prices:
            spread = max(prices) - min(prices)
            avg    = sum(prices) / len(prices)
            if spread > avg * 0.5:
                insights.append("价格区间较大，建议重点关注中间价位段商品")
            verified = sum(1 for p in products if p.get("features", {}).get("is_verified_supplier"))
            if verified / len(products) > 0.5:
                insights.append("市场上认证供应商占比较高，供应链较稳定")
            fast = sum(1 for p in products if p.get("features", {}).get("delivery_days", 30) <= 3)
            if fast / len(products) > 0.3:
                insights.append("快速发货商品占比较高，可优先考虑时效性")
        return insights


# ---------------------------------------------------------------------------
# Section s8 — DecisionEngineService (remaining methods + constructor)
# ---------------------------------------------------------------------------

class DecisionEngineService:
    """AI决策引擎：整合评分、规则、报告，生成采购推荐"""

    def __init__(
        self,
        llm_service: LLMService,
        intent_service: IntentRecognitionService,
        db_pool: Optional[Any] = None,
        redis_client: Optional[Any] = None,
    ):
        self._llm     = llm_service
        self._intent  = intent_service
        self._db      = db_pool
        self._redis   = redis_client
        self._rule_engine     = RuleEngine()
        self._report_gen      = ReportGenerator()
        self._scoring_models: Dict[str, BaseScoringModel] = {
            "b2b":         B2BScoringModel(),
            "b2c_brand":   B2CBrandScoringModel(),
            "b2c_nobrand": B2CNoBrandScoringModel(),
        }

    # ---- public entry point ----

    async def get_recommendation(
        self,
        session_id: str,
        user_input: str,
        context: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        ctx = context or {}
        try:
            intent = await self._intent.recognize(user_input, ctx)
            standard = self._build_standard(intent, ctx)
            llm_result = await self._llm.generate_search_query(
                standard=standard,
                platform="all",
                user_type=intent.purchase_type,
            )
            sq = llm_result.get("search_query", {})
            kws = sq.get("keywords", [intent.parameters.category or "商品"])
            search_query = " ".join(kws) if isinstance(kws, list) else str(kws)

            async with DataCollector() as collector:
                raw_products = await collector.collect(search_query, standard)

            scored = self._score_products(raw_products, standard, intent)
            filtered = self._rule_engine.apply(scored, standard, ctx)
            dual_recs = self._generate_dual_recommendations(filtered, standard, intent)
            report = self._report_gen.generate_recommendation_report(
                dual_recs["primary"], standard, intent
            )
            quality = self._calculate_recommendation_quality(dual_recs["primary"], standard)

            result = {
                "session_id":      session_id,
                "intent":          intent.__dict__,
                "recommendations": dual_recs,
                "report":          report,
                "quality_score":   quality,
                "search_query":    search_query,
            }

            if _HAS_PROMETHEUS and "decision_requests" in _HUB_METRICS:
                _HUB_METRICS["decision_requests"].labels(
                    intent_type=intent.intent_type,
                    purchase_type=intent.purchase_type,
                ).inc()

            await self._persist_recommendation(session_id, result)
            return result

        except Exception as exc:
            logger.exception("DecisionEngineService.get_recommendation error: %s", exc)
            if _HAS_PROMETHEUS and "decision_errors" in _HUB_METRICS:
                _HUB_METRICS["decision_errors"].inc()
            raise

    # ---- scoring ----

    def _select_scoring_model(self, intent: IntentResult) -> BaseScoringModel:
        pt = intent.purchase_type
        if pt == "b2b":
            return self._scoring_models["b2b"]
        brand = intent.parameters.brand
        if brand:
            return self._scoring_models["b2c_brand"]
        return self._scoring_models["b2c_nobrand"]

    def _score_products(
        self,
        products: List[Dict],
        standard: Dict,
        intent: IntentResult,
    ) -> List[Dict]:
        model = self._select_scoring_model(intent)
        scored = []
        for p in products:
            try:
                score, dims = model.score(p, standard)
                sp = dict(p)
                sp["score"] = score
                sp["score_dimensions"] = dims
                sp["match_reasons"] = self._generate_match_reasons(sp, dims, intent)
                sp["risks"] = self._identify_risks(sp, standard)
                scored.append(sp)
            except Exception as e:
                logger.debug("Scoring error for %s: %s", p.get("product_id"), e)
        return scored

    # ---- match reasons ----

    def _generate_match_reasons(
        self,
        product: Dict,
        dims: Dict[str, float],
        intent: IntentResult,
    ) -> List[str]:
        reasons: List[str] = []
        sorted_dims = sorted(dims.items(), key=lambda x: x[1], reverse=True)
        labels = {
            "supplier_qualification": "供应商资质优",
            "credit_rating":          "信用评级高",
            "delivery_capability":    "配送能力强",
            "price":                  "价格具有竞争力",
            "quality":                "商品质量好",
            "authenticity":           "品牌正品",
            "service":                "售后服务好",
            "reviews":                "买家口碑好",
            "specifications":         "规格完全匹配",
            "shop_age":               "店铺经营时间长",
        }
        for dim, val in sorted_dims[:3]:
            if val >= 0.75 and dim in labels:
                reasons.append(labels[dim])
        feats = product.get("features", {})
        if feats.get("is_verified_supplier"):
            reasons.append("平台认证供应商")
        if feats.get("delivery_days", 99) <= 3:
            reasons.append("支持次日达")
        if feats.get("review_count", 0) >= 1000:
            reasons.append(f"累计好评 {feats['review_count']} 条")
        params = intent.parameters
        if params.price_range:
            lo, hi = params.price_range
            price = product.get("price", 0)
            if lo <= price <= hi:
                reasons.append("价格在预算范围内")
        return reasons[:5]

    # ---- risk identification ----

    def _identify_risks(self, product: Dict, standard: Dict) -> List[str]:
        risks: List[str] = []
        feats  = product.get("features", {})
        params = standard.get("parameters", {})

        if feats.get("review_count", 0) < 10:
            risks.append("商品评价数量不足，质量存在不确定性")
        if feats.get("rating", 5.0) < 3.5:
            risks.append("商品评分偏低，需谨慎")
        stock = feats.get("stock", 9999)
        qty   = params.get("quantity", 1)
        if 0 < stock < qty * 1.2:
            risks.append(f"库存紧张（现货 {stock}，需求 {qty}）")
        if feats.get("delivery_days", 0) > 14:
            risks.append("配送时间较长，可能影响到货时效")
        if not feats.get("is_verified_supplier") and standard.get("purchase_type") == "b2b":
            risks.append("供应商未经平台认证，B2B采购建议优先选择认证商家")
        return risks

    # ---- dual recommendations ----

    def _generate_dual_recommendations(
        self,
        filtered: List[Dict],
        standard: Dict,
        intent: IntentResult,
    ) -> Dict[str, List[Dict]]:
        """主推 + 备选双列表。主推 top-3，备选 4-8。"""
        primary   = filtered[:3]
        secondary = filtered[3:8]
        # 备选加"替代原因"注释
        for item in secondary:
            reasons = item.get("match_reasons", [])
            item["alt_reason"] = reasons[0] if reasons else "性价比备选"
        return {"primary": primary, "secondary": secondary}

    # ---- quality score ----

    def _calculate_recommendation_quality(
        self,
        recommendations: List[Dict],
        standard: Dict,
    ) -> float:
        if not recommendations:
            return 0.0
        scores = [r.get("score", 0) for r in recommendations]
        avg_score = sum(scores) / len(scores)

        # diversity bonus: more platforms → higher quality
        platforms = {r.get("platform") for r in recommendations}
        diversity = min(len(platforms) / 3, 1.0) * 0.1

        # coverage: fraction with risks < 1
        safe = sum(1 for r in recommendations if len(r.get("risks", [])) == 0)
        safety_ratio = safe / len(recommendations) * 0.1

        quality = min(avg_score + diversity + safety_ratio, 1.0)
        return round(quality, 4)

    # ---- helpers ----

    @staticmethod
    def _build_standard(intent: IntentResult, context: Dict) -> Dict:
        params = intent.parameters
        return {
            "purchase_type": intent.purchase_type,
            "parameters": {
                "quantity":    params.quantity,
                "price_range": list(params.price_range) if params.price_range else [0, 99999],
                "features":    params.features,
                "brand":       params.brand,
                "category":    params.category,
            },
            "context": context,
        }

    async def _persist_recommendation(self, session_id: str, result: Dict) -> None:
        if self._redis:
            try:
                key = f"rec:{session_id}"
                await self._redis.setex(key, 3600, json.dumps(result, default=str))
            except Exception as e:
                logger.debug("Redis persist error: %s", e)


# ---------------------------------------------------------------------------
# Section s9 — DialogStateMachine
# ---------------------------------------------------------------------------

class DialogState(str, enum.Enum):
    INITIAL           = "initial"
    INTENT_IDENTIFIED = "intent_identified"
    COLLECTING_INFO   = "collecting_info"
    PROCESSING        = "processing"
    RECOMMENDING      = "recommending"
    COMPLETED         = "completed"
    ERROR             = "error"


class DialogStateMachine:
    """对话状态机：控制状态转换合法性"""

    _TRANSITIONS: Dict[str, List[str]] = {
        DialogState.INITIAL:           [DialogState.INTENT_IDENTIFIED, DialogState.ERROR],
        DialogState.INTENT_IDENTIFIED: [DialogState.COLLECTING_INFO, DialogState.PROCESSING, DialogState.ERROR],
        DialogState.COLLECTING_INFO:   [DialogState.PROCESSING, DialogState.COLLECTING_INFO, DialogState.ERROR],
        DialogState.PROCESSING:        [DialogState.RECOMMENDING, DialogState.ERROR],
        DialogState.RECOMMENDING:      [DialogState.COMPLETED, DialogState.COLLECTING_INFO, DialogState.PROCESSING, DialogState.ERROR],
        DialogState.COMPLETED:         [DialogState.INITIAL],
        DialogState.ERROR:             [DialogState.INITIAL],
    }

    def __init__(self, initial: str = DialogState.INITIAL):
        # Normalize plain string to DialogState enum so _TRANSITIONS lookup works
        try:
            self._state: str = DialogState(initial)
        except ValueError:
            self._state = DialogState.INITIAL

    @property
    def state(self) -> str:
        return self._state

    def can_transition(self, target: str) -> bool:
        try:
            t = DialogState(target)
        except ValueError:
            return False
        return t in self._TRANSITIONS.get(self._state, [])

    def transition(self, target: str) -> bool:
        if self.can_transition(target):
            try:
                self._state = DialogState(target)
            except ValueError:
                self._state = target
            return True
        logger.warning("Invalid state transition: %s → %s", self._state, target)
        return False

    def force_error(self) -> None:
        self._state = DialogState.ERROR


# ---------------------------------------------------------------------------
# Section s10 — DialogManagerService
# ---------------------------------------------------------------------------

_MISSING_FIELD_QUESTIONS: Dict[str, str] = {
    "quantity":    "请问您需要采购多少数量？",
    "price_range": "请问您的预算范围是多少（例如：100-500元）？",
    "category":    "请问商品的具体类别是什么？",
    "brand":       "请问是否有品牌偏好？",
    "features":    "请问对商品有哪些具体功能要求？",
}


class DialogManagerService:
    """对话管理服务：维护会话状态、驱动多轮对话"""

    def __init__(
        self,
        decision_engine: DecisionEngineService,
        db_pool: Optional[Any] = None,
        redis_client: Optional[Any] = None,
    ):
        self._engine  = decision_engine
        self._db      = db_pool
        self._redis   = redis_client
        self._sessions: Dict[str, Dict] = {}   # fallback in-memory store
        self._lock = asyncio.Lock()

    # ---- public ----

    async def process_message(
        self,
        session_id: str,
        user_message: str,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """处理用户消息，驱动对话状态机，返回系统回复。"""
        session = await self._load_session(session_id, user_id)
        machine = DialogStateMachine(session.get("state", DialogState.INITIAL))

        try:
            response = await self._handle_turn(session, machine, user_message)
            session["state"] = machine.state
            session["updated_at"] = datetime.utcnow().isoformat()
            await self._save_session(session_id, session)
            return response
        except Exception as exc:
            logger.exception("DialogManager error session=%s: %s", session_id, exc)
            machine.force_error()
            session["state"] = DialogState.ERROR
            await self._save_session(session_id, session)
            return {
                "session_id": session_id,
                "state":      DialogState.ERROR,
                "message":    "抱歉，处理您的请求时遇到问题，请稍后重试。",
                "error":      str(exc),
            }

    async def get_session(self, session_id: str) -> Optional[Dict]:
        return await self._load_session(session_id)

    async def reset_session(self, session_id: str) -> None:
        empty = self._new_session(session_id)
        await self._save_session(session_id, empty)

    # ---- private conversation logic ----

    async def _handle_turn(
        self,
        session: Dict,
        machine: DialogStateMachine,
        user_message: str,
    ) -> Dict[str, Any]:
        state = machine.state
        session_id = session["session_id"]

        # Append user turn to history
        session.setdefault("history", []).append({
            "role": "user",
            "content": user_message,
            "ts": datetime.utcnow().isoformat(),
        })

        # --- INITIAL: first message, recognize intent ---
        if state == DialogState.INITIAL:
            intent_service: IntentRecognitionService = self._engine._intent
            intent = await intent_service.recognize(user_message, session.get("context", {}))
            session["intent"] = intent.__dict__
            session["parameters"] = intent.parameters.__dict__

            if intent.confidence < 0.5:
                machine.transition(DialogState.COLLECTING_INFO)
                reply = "您好！我理解您想采购商品，但我需要了解更多信息。" + self._next_question(session)
            else:
                machine.transition(DialogState.INTENT_IDENTIFIED)
                missing = self._find_missing_params(session)
                if missing:
                    machine.transition(DialogState.COLLECTING_INFO)
                    reply = f"好的，我已了解您需要采购「{intent.parameters.category or '商品'}」。" + self._next_question(session)
                else:
                    machine.transition(DialogState.PROCESSING)
                    reply = await self._run_recommendation(session_id, session, machine)
                    return self._build_response(session, machine, reply)

        # --- COLLECTING_INFO: gather missing params ---
        elif state == DialogState.COLLECTING_INFO:
            self._extract_and_update_params(session, user_message)
            missing = self._find_missing_params(session)
            if missing:
                reply = "谢谢！" + self._next_question(session)
            else:
                machine.transition(DialogState.PROCESSING)
                reply = await self._run_recommendation(session_id, session, machine)
                return self._build_response(session, machine, reply)

        # --- RECOMMENDING: user wants refinement ---
        elif state == DialogState.RECOMMENDING:
            lower = user_message.lower()
            if any(w in lower for w in ["更便宜", "价格低", "预算少"]):
                params = session.get("parameters", {})
                pr = params.get("price_range", [0, 99999])
                params["price_range"] = [pr[0], int(pr[1] * 0.8)]
                session["parameters"] = params
                machine.transition(DialogState.PROCESSING)
                reply = await self._run_recommendation(session_id, session, machine)
            elif any(w in lower for w in ["确认", "好的", "就这个", "下单"]):
                machine.transition(DialogState.COMPLETED)
                reply = "好的！我已为您锁定推荐商品，正在为您生成采购单，请稍候..."
            else:
                # treat as new requirement
                intent_service = self._engine._intent
                intent = await intent_service.recognize(user_message, session.get("context", {}))
                session["parameters"].update({
                    k: v for k, v in intent.parameters.__dict__.items()
                    if v not in (None, [], ())
                })
                machine.transition(DialogState.PROCESSING)
                reply = await self._run_recommendation(session_id, session, machine)

        # --- COMPLETED ---
        elif state == DialogState.COMPLETED:
            machine.transition(DialogState.INITIAL)
            reply = "您的采购已完成！如需继续采购，请直接告诉我需求。"

        # --- ERROR: restart ---
        else:
            machine.transition(DialogState.INITIAL)
            reply = "会话已重置，请重新描述您的采购需求。"

        session["history"].append({"role": "assistant", "content": reply,
                                   "ts": datetime.utcnow().isoformat()})
        return self._build_response(session, machine, reply)

    async def _run_recommendation(
        self,
        session_id: str,
        session: Dict,
        machine: DialogStateMachine,
    ) -> str:
        """调用决策引擎，生成推荐；转换状态到 RECOMMENDING。"""
        params = session.get("parameters", {})
        intent_data = session.get("intent", {})
        user_input = session.get("history", [{}])[-1].get("content", "")

        # Reconstruct a natural language query from stored intent
        category = params.get("category") or intent_data.get("category", "商品") or "商品"
        brand    = params.get("brand") or ""
        qty      = params.get("quantity") or 1
        pr_raw   = params.get("price_range")
        pr       = pr_raw if (pr_raw and len(pr_raw) >= 2) else [0, 99999]
        query_str = f"采购{qty}件{brand}{category}，预算{pr[0]}-{pr[1]}元"

        context = session.get("context", {})
        result = await self._engine.get_recommendation(session_id, query_str, context)
        session["last_result"] = result

        recs = result.get("recommendations", {}).get("primary", [])
        machine.transition(DialogState.RECOMMENDING)

        if not recs:
            return "抱歉，暂时没有找到符合您条件的商品，建议放宽价格或规格要求。"

        lines = [f"为您找到 {len(recs)} 款推荐商品："]
        for i, r in enumerate(recs, 1):
            name  = r.get("name", "商品")
            price = r.get("price", 0)
            score = r.get("score", 0)
            reasons = "、".join(r.get("match_reasons", [])[:2])
            lines.append(f"{i}. {name} — ¥{price:.2f}（匹配度 {score:.0%}）{reasons}")
        lines.append("\n如需调整需求或确认采购，请告诉我。")
        return "\n".join(lines)

    # ---- param utilities ----

    @staticmethod
    def _find_missing_params(session: Dict) -> List[str]:
        params = session.get("parameters", {})
        missing = []
        if not params.get("category"):
            missing.append("category")
        if not params.get("quantity"):
            missing.append("quantity")
        return missing

    @staticmethod
    def _next_question(session: Dict) -> str:
        params   = session.get("parameters", {})
        asked    = session.get("asked_fields", [])
        priority = ["category", "quantity", "price_range", "brand", "features"]
        for field in priority:
            value = params.get(field)
            is_empty = not value or value in ([], (), [0, 99999])
            if is_empty and field not in asked:
                session.setdefault("asked_fields", []).append(field)
                return _MISSING_FIELD_QUESTIONS.get(field, f"请提供{field}信息。")
        return "请确认以上信息是否正确，或告诉我其他要求。"

    @staticmethod
    def _extract_and_update_params(session: Dict, text: str) -> None:
        """Simple regex extraction for quantity and price_range from free text."""
        params = session.setdefault("parameters", {})
        import re as _re
        # quantity
        m = _re.search(r"(\d+)\s*(?:件|个|台|箱|套|条|双|副)", text)
        if m:
            params["quantity"] = int(m.group(1))
        # price_range: "100到500" or "100-500" or "预算500"
        m2 = _re.search(r"(\d+)[到\-~～~](\d+)", text)
        if m2:
            params["price_range"] = [int(m2.group(1)), int(m2.group(2))]
        else:
            m3 = _re.search(r"预算[约]?(\d+)", text)
            if m3:
                budget = int(m3.group(1))
                params["price_range"] = [0, budget]
        # brand keywords (very basic)
        for brand in ["Apple", "苹果", "华为", "小米", "三星", "联想", "戴尔"]:
            if brand in text:
                params["brand"] = brand
                break

    @staticmethod
    def _build_response(session: Dict, machine: DialogStateMachine, message: str) -> Dict:
        return {
            "session_id": session["session_id"],
            "state":      machine.state,
            "message":    message,
            "intent":     session.get("intent"),
            "parameters": session.get("parameters"),
        }

    # ---- session persistence ----

    async def _load_session(
        self,
        session_id: str,
        user_id: Optional[str] = None,
    ) -> Dict:
        # 1. Redis
        if self._redis:
            try:
                raw = await self._redis.get(f"dialog:{session_id}")
                if raw:
                    return json.loads(raw)
            except Exception:
                pass
        # 2. in-memory
        async with self._lock:
            if session_id in self._sessions:
                return dict(self._sessions[session_id])
        return self._new_session(session_id, user_id)

    async def _save_session(self, session_id: str, session: Dict) -> None:
        if self._redis:
            try:
                await self._redis.setex(
                    f"dialog:{session_id}", 86400, json.dumps(session, default=str)
                )
                return
            except Exception:
                pass
        async with self._lock:
            self._sessions[session_id] = dict(session)

    @staticmethod
    def _new_session(session_id: str, user_id: Optional[str] = None) -> Dict:
        return {
            "session_id":   session_id,
            "user_id":      user_id,
            "state":        DialogState.INITIAL,
            "intent":       None,
            "parameters":   {},
            "asked_fields": [],
            "context":      {},
            "history":      [],
            "last_result":  None,
            "created_at":   datetime.utcnow().isoformat(),
            "updated_at":   datetime.utcnow().isoformat(),
        }


# ---------------------------------------------------------------------------
# Section s11 — Prometheus metric helpers
# ---------------------------------------------------------------------------

_HUB_METRICS: Dict[str, Any] = {}

def _init_hub_metrics() -> None:
    global _HUB_METRICS
    if not _HAS_PROMETHEUS:
        return
    from prometheus_client import Counter as _C, Histogram as _H, Gauge as _G
    _HUB_METRICS["decision_requests"] = _C(
        "hub_decision_requests_total",
        "Total decision requests",
        ["intent_type", "purchase_type"],
        registry=_HUB_REGISTRY,
    )
    _HUB_METRICS["decision_errors"] = _C(
        "hub_decision_errors_total",
        "Total decision errors",
        registry=_HUB_REGISTRY,
    )
    _HUB_METRICS["dialog_turns"] = _C(
        "hub_dialog_turns_total",
        "Total dialog turns",
        ["state"],
        registry=_HUB_REGISTRY,
    )
    _HUB_METRICS["recommendation_latency"] = _H(
        "hub_recommendation_latency_seconds",
        "Recommendation latency",
        registry=_HUB_REGISTRY,
    )
    _HUB_METRICS["active_sessions"] = _G(
        "hub_active_sessions",
        "Currently active dialog sessions",
        registry=_HUB_REGISTRY,
    )


# ---------------------------------------------------------------------------
# Section s12 — FastAPI application factory + routes
# ---------------------------------------------------------------------------

# ---- Pydantic request/response models ----

class ChatRequest(BaseModel):
    session_id: str
    message:    str
    user_id:    Optional[str] = None
    context:    Optional[Dict[str, Any]] = None

    @validator("session_id", "message")
    def not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("field must not be empty")
        return v.strip()


class RecommendRequest(BaseModel):
    query:      str
    session_id: Optional[str] = None
    context:    Optional[Dict[str, Any]] = None

    @validator("query")
    def not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("query must not be empty")
        return v.strip()


class SessionResetRequest(BaseModel):
    session_id: str


class HealthResponse(BaseModel):
    status:  str
    service: str
    version: str
    ts:      str


# ---- app factory ----

def create_hub_app(
    db_url: str = "sqlite+aiosqlite:///./hub.db",
    redis_url: Optional[str] = None,
) -> FastAPI:
    app = FastAPI(
        title="AI决策中枢",
        description="ILbuy AI决策引擎 — 意图识别、评分推荐、多轮对话",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # ---- shared state ----
    _state: Dict[str, Any] = {}

    # ---- lifecycle ----

    @app.on_event("startup")
    async def _startup():
        _init_hub_metrics()

        # DB
        try:
            engine = create_async_engine(db_url, echo=False)
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            session_factory = AsyncSessionLocal
            # Monkey-patch factory to use our engine
            session_factory.kw["bind"] = engine
            _state["db"] = session_factory
            logger.info("DB ready: %s", db_url)
        except Exception as e:
            logger.warning("DB init error (non-fatal): %s", e)
            _state["db"] = None

        # Redis
        _state["redis"] = None
        if redis_url:
            try:
                import aioredis
                _state["redis"] = await aioredis.from_url(redis_url, decode_responses=True)
                logger.info("Redis ready: %s", redis_url)
            except Exception as e:
                logger.warning("Redis unavailable (non-fatal): %s", e)

        # Services
        llm     = LLMService()
        intent  = IntentRecognitionService(llm)
        engine_svc = DecisionEngineService(llm, intent, _state["db"], _state["redis"])
        _state["dialog_manager"] = DialogManagerService(engine_svc, _state["db"], _state["redis"])
        _state["decision_engine"] = engine_svc
        logger.info("AI决策中枢 startup complete")

    @app.on_event("shutdown")
    async def _shutdown():
        if _state.get("redis"):
            await _state["redis"].close()
        logger.info("AI决策中枢 shutdown complete")

    # ---- dependency ----

    def _get_dialog_manager() -> DialogManagerService:
        dm = _state.get("dialog_manager")
        if dm is None:
            raise HTTPException(status_code=503, detail="Service initializing")
        return dm

    def _get_decision_engine() -> DecisionEngineService:
        de = _state.get("decision_engine")
        if de is None:
            raise HTTPException(status_code=503, detail="Service initializing")
        return de

    # ---- routes ----

    @app.get("/health", response_model=HealthResponse, tags=["system"])
    async def health():
        return HealthResponse(
            status="ok",
            service="ai-decision-hub",
            version="1.0.0",
            ts=datetime.utcnow().isoformat() + "Z",
        )

    @app.get("/metrics", tags=["system"])
    async def metrics():
        if not _HAS_PROMETHEUS:
            raise HTTPException(status_code=501, detail="Prometheus not available")
        from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
        from fastapi.responses import Response as _Resp
        return _Resp(
            content=generate_latest(_HUB_REGISTRY),
            media_type=CONTENT_TYPE_LATEST,
        )

    @app.post("/api/v1/chat", tags=["dialog"])
    async def chat(
        req: ChatRequest,
        dm: DialogManagerService = Depends(_get_dialog_manager),
    ):
        """多轮对话接口"""
        t0 = time.time()
        result = await dm.process_message(req.session_id, req.message, req.user_id)
        if _HAS_PROMETHEUS and "dialog_turns" in _HUB_METRICS:
            _HUB_METRICS["dialog_turns"].labels(state=result.get("state", "unknown")).inc()
        result["latency_ms"] = round((time.time() - t0) * 1000, 1)
        return result

    @app.post("/api/v1/recommend", tags=["recommendation"])
    async def recommend(
        req: RecommendRequest,
        de: DecisionEngineService = Depends(_get_decision_engine),
    ):
        """直接推荐接口（无需多轮对话）"""
        import uuid
        session_id = req.session_id or str(uuid.uuid4())
        t0 = time.time()
        result = await de.get_recommendation(session_id, req.query, req.context or {})
        if _HAS_PROMETHEUS and "recommendation_latency" in _HUB_METRICS:
            _HUB_METRICS["recommendation_latency"].observe(time.time() - t0)
        result["latency_ms"] = round((time.time() - t0) * 1000, 1)
        return result

    @app.get("/api/v1/sessions/{session_id}", tags=["dialog"])
    async def get_session(
        session_id: str,
        dm: DialogManagerService = Depends(_get_dialog_manager),
    ):
        """获取会话详情"""
        session = await dm.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        return session

    @app.delete("/api/v1/sessions/{session_id}", tags=["dialog"])
    async def reset_session(
        session_id: str,
        dm: DialogManagerService = Depends(_get_dialog_manager),
    ):
        """重置会话"""
        await dm.reset_session(session_id)
        return {"session_id": session_id, "status": "reset"}

    @app.post("/api/v1/intent", tags=["nlp"])
    async def recognize_intent(
        body: Dict[str, Any],
        de: DecisionEngineService = Depends(_get_decision_engine),
    ):
        """纯意图识别接口"""
        text = body.get("text", "").strip()
        if not text:
            raise HTTPException(status_code=422, detail="text is required")
        context = body.get("context", {})
        intent = await de._intent.recognize(text, context)
        return {
            "intent_type":   intent.intent_type,
            "purchase_type": intent.purchase_type,
            "confidence":    intent.confidence,
            "parameters":    intent.parameters.__dict__,
            "entities":      intent.entities,
        }

    @app.get("/api/v1/market-analysis", tags=["analysis"])
    async def market_analysis(
        query: str,
        de: DecisionEngineService = Depends(_get_decision_engine),
    ):
        """市场分析接口"""
        if not query.strip():
            raise HTTPException(status_code=422, detail="query is required")
        standard = {"parameters": {"price_range": [0, 99999], "features": []}}
        async with DataCollector() as collector:
            products = await collector.collect(query, standard)
        rg = ReportGenerator()
        return rg.generate_market_analysis(products, standard)

    return app


# ---------------------------------------------------------------------------
# Section s13 — Async session factory
# ---------------------------------------------------------------------------
# SQLAlchemy Base + models already defined above (inside _HAS_SQLALCHEMY block)

if _HAS_SQLALCHEMY:
    AsyncSessionLocal = sessionmaker(class_=AsyncSession, expire_on_commit=False)
else:
    AsyncSessionLocal = None  # type: ignore


# ---------------------------------------------------------------------------
# Section s14 — Main entrypoint
# ---------------------------------------------------------------------------

app = create_hub_app(
    db_url=os.getenv("HUB_DB_URL", "sqlite+aiosqlite:///./hub.db"),
    redis_url=os.getenv("HUB_REDIS_URL"),
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "ai_decision_hub:app",
        host=os.getenv("HUB_HOST", "0.0.0.0"),
        port=int(os.getenv("HUB_PORT", "8003")),
        reload=os.getenv("HUB_RELOAD", "false").lower() == "true",
        log_level=os.getenv("HUB_LOG_LEVEL", "info"),
        workers=int(os.getenv("HUB_WORKERS", "1")),
    )
