"""
order_service.py  —  业务逻辑层: 订单服务 (Part 7)
订单创建 · 支付处理 · 履约追踪 · 退款处理
Production-grade: SQLite-compat ORM, Pydantic v2, conditional imports, no raw SQL
"""
# ── stdlib ────────────────────────────────────────────────────────────────────
import asyncio
import base64
import concurrent.futures
import hashlib
import hmac
import json
import logging
import os
import random
import re
import secrets
import string
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

# ── SQLAlchemy (always available) ─────────────────────────────────────────────
from sqlalchemy import (
    Boolean, Column, DateTime, Index, Integer, JSON,
    Numeric, String, Text, UniqueConstraint,
    and_, asc, desc, func, or_, select,
    update as sa_update,
)
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# ── FastAPI + Pydantic (always available) ─────────────────────────────────────
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field, field_validator, model_validator
import aiohttp

# ── Optional: Redis ───────────────────────────────────────────────────────────
try:
    import redis.asyncio as _aioredis
    _HAS_REDIS = True
except ImportError:
    _HAS_REDIS = False

# ── Optional: qrcode ─────────────────────────────────────────────────────────
try:
    import qrcode
    from io import BytesIO
    _HAS_QRCODE = True
except ImportError:
    _HAS_QRCODE = False

# ── Optional: Prometheus ──────────────────────────────────────────────────────
try:
    from prometheus_client import (
        CollectorRegistry, Counter, Gauge, Histogram, generate_latest
    )
    _HAS_PROMETHEUS = True
    _OS_REGISTRY = CollectorRegistry()
except ImportError:
    _HAS_PROMETHEUS = False
    _OS_REGISTRY = None

# ── Thread pool for sync helpers ──────────────────────────────────────────────
_THREAD_POOL = concurrent.futures.ThreadPoolExecutor(max_workers=4)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("order_service")


# ══════════════════════════════════════════════════════════════════════════════
# 枚举
# ══════════════════════════════════════════════════════════════════════════════
class OrderStatus(str, Enum):
    PENDING    = "pending"
    PAID       = "paid"
    CONFIRMED  = "confirmed"
    PROCESSING = "processing"
    SHIPPED    = "shipped"
    DELIVERED  = "delivered"
    COMPLETED  = "completed"
    CANCELLED  = "cancelled"
    REFUNDING  = "refunding"
    REFUNDED   = "refunded"
    FAILED     = "failed"


class PaymentStatus(str, Enum):
    PENDING    = "pending"
    PROCESSING = "processing"
    SUCCESS    = "success"
    FAILED     = "failed"
    REFUNDED   = "refunded"
    CLOSED     = "closed"


class PaymentMethod(str, Enum):
    ALIPAY       = "alipay"
    WECHAT_PAY   = "wechat_pay"
    UNION_PAY    = "union_pay"
    BANK_TRANSFER = "bank_transfer"
    WALLET       = "wallet"


class ShippingMethod(str, Enum):
    EXPRESS    = "express"
    SF_EXPRESS = "sf_express"
    YTO        = "yto"
    ZTO        = "zto"
    SELF_PICKUP = "self_pickup"


class OrderSource(str, Enum):
    WEB    = "web"
    MOBILE = "mobile"
    APP    = "app"
    WECHAT = "wechat"
    API    = "api"


# ══════════════════════════════════════════════════════════════════════════════
# 配置
# ══════════════════════════════════════════════════════════════════════════════
@dataclass
class ServiceConfig:
    database_url: str      = os.getenv("DATABASE_URL",      "sqlite+aiosqlite:///./order_service.db")
    redis_url:    str      = os.getenv("REDIS_URL",          "redis://localhost:6379/2")
    host:         str      = os.getenv("ORDER_HOST",         "0.0.0.0")
    port:         int      = int(os.getenv("ORDER_PORT",     "8022"))
    secret_key:   str      = os.getenv("ORDER_SECRET",      secrets.token_hex(32))
    order_timeout_min: int = int(os.getenv("ORDER_TIMEOUT", "30"))
    auto_confirm_days: int = int(os.getenv("AUTO_CONFIRM",  "7"))
    notify_url:   str      = os.getenv("NOTIFY_SERVICE_URL", "http://localhost:8040")
    product_url:  str      = os.getenv("PRODUCT_SERVICE_URL","http://localhost:8006")
    debug:        bool     = os.getenv("DEBUG", "false").lower() == "true"


# ══════════════════════════════════════════════════════════════════════════════
# ORM 模型  (SQLite-compat: Integer PK, JSON not JSONB, no relationship)
# ══════════════════════════════════════════════════════════════════════════════
Base = declarative_base()


class Order(Base):
    __tablename__ = "orders"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    order_id       = Column(String(64),  unique=True, nullable=False, index=True)
    order_number   = Column(String(32),  unique=True, nullable=False, index=True)
    user_id        = Column(String(64),  nullable=False, index=True)
    user_role      = Column(String(20),  nullable=False, default="buyer")
    order_status   = Column(String(20),  nullable=False, default="pending", index=True)
    payment_status = Column(String(20),  nullable=False, default="pending")
    total_amount   = Column(Numeric(12, 2), nullable=False)
    discount_amount= Column(Numeric(12, 2), default=0)
    shipping_fee   = Column(Numeric(12, 2), default=0)
    tax_amount     = Column(Numeric(12, 2), default=0)
    final_amount   = Column(Numeric(12, 2), nullable=False)
    paid_amount    = Column(Numeric(12, 2), default=0)
    refund_amount  = Column(Numeric(12, 2), default=0)
    items          = Column(JSON, nullable=False)
    shipping_address = Column(JSON, nullable=False)
    billing_address  = Column(JSON, nullable=True)
    shipping_method  = Column(String(50), nullable=False, default="express")
    tracking_number  = Column(String(100), nullable=True, index=True)
    logistics_company= Column(String(100), nullable=True)
    payment_method   = Column(String(20), nullable=False, default="alipay")
    payment_channel  = Column(String(50), nullable=True)
    payment_tx_id    = Column(String(100), nullable=True)
    invoice_info     = Column(JSON, nullable=True)
    coupon_code      = Column(String(50), nullable=True)
    coupon_discount  = Column(Numeric(10, 2), default=0)
    promotion_ids    = Column(JSON, nullable=True)
    promotion_discount = Column(Numeric(10, 2), default=0)
    points_used      = Column(Integer, default=0)
    source           = Column(String(20), nullable=False, default="web")
    ip_address       = Column(String(50), nullable=True)
    notes            = Column(Text, nullable=True)
    extra_metadata   = Column("order_metadata", JSON, default=dict)
    expires_at       = Column(DateTime, nullable=True)
    paid_at          = Column(DateTime, nullable=True)
    shipped_at       = Column(DateTime, nullable=True)
    delivered_at     = Column(DateTime, nullable=True)
    completed_at     = Column(DateTime, nullable=True)
    cancelled_at     = Column(DateTime, nullable=True)
    refunded_at      = Column(DateTime, nullable=True)
    created_at       = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at       = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("idx_order_user_status", "user_id", "order_status", "created_at"),
        Index("idx_order_payment",     "payment_status", "created_at"),
    )


class Payment(Base):
    __tablename__ = "payments"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    payment_id     = Column(String(64), unique=True, nullable=False, index=True)
    order_id       = Column(String(64), nullable=False, index=True)
    payment_method = Column(String(20), nullable=False)
    payment_status = Column(String(20), nullable=False, default="pending", index=True)
    amount         = Column(Numeric(12, 2), nullable=False)
    currency       = Column(String(3), default="CNY")
    out_trade_no   = Column(String(100), nullable=True, index=True)
    transaction_id = Column(String(100), nullable=True, index=True)
    payment_url    = Column(String(1000), nullable=True)
    qr_code        = Column(Text, nullable=True)
    payment_data   = Column(JSON, default=dict)
    callback_data  = Column(JSON, default=dict)
    error_code     = Column(String(50), nullable=True)
    error_message  = Column(String(500), nullable=True)
    retry_count    = Column(Integer, default=0)
    expires_at     = Column(DateTime, nullable=True)
    paid_at        = Column(DateTime, nullable=True)
    created_at     = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at     = Column(DateTime, default=datetime.utcnow, nullable=False)


class Refund(Base):
    __tablename__ = "refunds"

    id                  = Column(Integer, primary_key=True, autoincrement=True)
    refund_id           = Column(String(64), unique=True, nullable=False, index=True)
    order_id            = Column(String(64), nullable=False, index=True)
    refund_status       = Column(String(20), nullable=False, default="pending", index=True)
    refund_amount       = Column(Numeric(12, 2), nullable=False)
    refund_reason       = Column(String(500), nullable=False)
    refund_type         = Column(String(20), default="full")
    transaction_id      = Column(String(100), nullable=True)
    refund_tx_id        = Column(String(100), nullable=True)
    refund_items        = Column(JSON, nullable=True)
    processor_id        = Column(String(64), nullable=True)
    processor_notes     = Column(Text, nullable=True)
    extra_metadata      = Column("refund_metadata", JSON, default=dict)
    requested_at        = Column(DateTime, nullable=False, default=datetime.utcnow)
    processed_at        = Column(DateTime, nullable=True)
    completed_at        = Column(DateTime, nullable=True)
    created_at          = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at          = Column(DateTime, default=datetime.utcnow, nullable=False)


class Shipment(Base):
    __tablename__ = "shipments"

    id                = Column(Integer, primary_key=True, autoincrement=True)
    shipment_id       = Column(String(64), unique=True, nullable=False, index=True)
    order_id          = Column(String(64), nullable=False, index=True)
    tracking_number   = Column(String(100), nullable=False, index=True)
    logistics_company = Column(String(100), nullable=False)
    logistics_code    = Column(String(50), nullable=True)
    weight            = Column(Numeric(10, 3), nullable=True)
    shipped_items     = Column(JSON, nullable=True)
    logistics_info    = Column(JSON, nullable=True)
    current_status    = Column(String(50), nullable=True)
    estimated_delivery= Column(DateTime, nullable=True)
    delivered_at      = Column(DateTime, nullable=True)
    shipped_at        = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_at        = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at        = Column(DateTime, default=datetime.utcnow, nullable=False)


class OrderActivity(Base):
    __tablename__ = "order_activities"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    activity_id    = Column(String(64), unique=True, nullable=False, index=True)
    order_id       = Column(String(64), nullable=False, index=True)
    activity_type  = Column(String(50), nullable=False)
    activity_action= Column(String(100), nullable=False)
    activity_result= Column(String(20), nullable=False, default="success")
    message        = Column(String(500), nullable=True)
    performed_by   = Column(String(64), nullable=True)
    performed_by_type = Column(String(20), nullable=True, default="user")
    before_state   = Column(JSON, nullable=True)
    after_state    = Column(JSON, nullable=True)
    ip_address     = Column(String(50), nullable=True)
    performed_at   = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    created_at     = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("idx_activity_order_time", "order_id", "performed_at"),
    )



# ══════════════════════════════════════════════════════════════════════════════
# Pydantic v2 请求/响应模型
# ══════════════════════════════════════════════════════════════════════════════
class OrderItemIn(BaseModel):
    product_id:   str   = Field(..., min_length=1)
    platform:     str   = Field(..., min_length=1)
    sku_id:       Optional[str] = None
    product_name: str   = Field(..., min_length=1)
    product_image:Optional[str] = None
    quantity:     int   = Field(..., gt=0)
    unit_price:   float = Field(..., gt=0)
    total_price:  float = Field(..., gt=0)
    specifications: Dict[str, Any] = Field(default_factory=dict)
    weight:       float = Field(0.0, ge=0)
    tax_rate:     float = Field(0.0, ge=0, le=1)
    discount_amount: float = Field(0.0, ge=0)
    notes:        Optional[str] = None

    @field_validator("total_price")
    @classmethod
    def check_total(cls, v: float, info: Any) -> float:
        data = info.data if hasattr(info, "data") else {}
        qty, up = data.get("quantity"), data.get("unit_price")
        if qty and up:
            expected = round(qty * up, 2)
            if abs(v - expected) > 0.05:
                raise ValueError(f"total_price {v} ≠ qty×unit_price {expected}")
        return v


class ShippingAddressIn(BaseModel):
    receiver_name:  str = Field(..., min_length=1)
    receiver_phone: str = Field(..., min_length=1)
    province:       str = Field(..., min_length=1)
    city:           str = Field(..., min_length=1)
    district:       str = Field(default="")
    street:         str = Field(..., min_length=1)
    postal_code:    Optional[str] = None
    country:        str = Field(default="中国")

    @field_validator("receiver_phone")
    @classmethod
    def check_phone(cls, v: str) -> str:
        if not re.match(r"^[1-9]\d{6,14}$", v.replace("-", "").replace(" ", "")):
            raise ValueError("电话号码格式不正确")
        return v


class CreateOrderRequest(BaseModel):
    user_id:       str = Field(..., min_length=1)
    user_role:     str = Field(default="buyer")
    items:         List[OrderItemIn] = Field(..., min_length=1)
    shipping_address: ShippingAddressIn
    billing_address:  Optional[Dict[str, Any]] = None
    shipping_method:  str = Field(default="express")
    payment_method:   str = Field(default="alipay")
    payment_channel:  Optional[str] = None
    coupon_code:      Optional[str] = None
    promotion_ids:    List[str] = Field(default_factory=list)
    points_used:      int = Field(default=0, ge=0)
    source:           str = Field(default="web")
    notes:            Optional[str] = None
    ip_address:       Optional[str] = None
    extra_metadata:   Dict[str, Any] = Field(default_factory=dict)


class PaymentRequest(BaseModel):
    order_id:       str = Field(..., min_length=1)
    payment_method: str = Field(..., min_length=1)
    payment_channel:Optional[str] = None
    return_url:     Optional[str] = None
    client_ip:      Optional[str] = None


class RefundRequest(BaseModel):
    order_id:      str   = Field(..., min_length=1)
    refund_amount: float = Field(..., gt=0)
    refund_reason: str   = Field(..., min_length=2)
    refund_items:  Optional[List[Dict[str, Any]]] = None
    notes:         Optional[str] = None


class ShipOrderRequest(BaseModel):
    order_id:          str = Field(..., min_length=1)
    tracking_number:   str = Field(..., min_length=1)
    logistics_company: str = Field(..., min_length=1)
    logistics_code:    Optional[str] = None
    weight:            Optional[float] = None
    shipped_at:        Optional[datetime] = None
    notes:             Optional[str] = None


class ProcessRefundRequest(BaseModel):
    approve:    bool
    notes:      Optional[str] = None
    processor_id: Optional[str] = None


# ══════════════════════════════════════════════════════════════════════════════
# RedisManager  (in-memory fallback if Redis unavailable)
# ══════════════════════════════════════════════════════════════════════════════
class RedisManager:
    def __init__(self) -> None:
        self._client: Any = None
        self._mock: Dict[str, Tuple[str, float]] = {}

    async def connect(self, url: str) -> None:
        if _HAS_REDIS:
            try:
                self._client = _aioredis.from_url(url, decode_responses=True)
                await self._client.ping()
                logger.info("Redis connected")
            except Exception as exc:
                logger.warning(f"Redis unavailable, using in-memory fallback: {exc}")
                self._client = None

    async def get(self, key: str) -> Optional[str]:
        if self._client:
            try:
                return await self._client.get(key)
            except Exception:
                pass
        entry = self._mock.get(key)
        if entry and entry[1] > time.time():
            return entry[0]
        self._mock.pop(key, None)
        return None

    async def set(self, key: str, value: str, ex: int = 3600) -> None:
        if self._client:
            try:
                await self._client.set(key, value, ex=ex)
                return
            except Exception:
                pass
        self._mock[key] = (value, time.time() + ex)

    async def delete(self, key: str) -> None:
        if self._client:
            try:
                await self._client.delete(key)
                return
            except Exception:
                pass
        self._mock.pop(key, None)

    async def exists(self, key: str) -> bool:
        return await self.get(key) is not None


# ══════════════════════════════════════════════════════════════════════════════
# PaymentManager  (stubs — replace with real SDK in production)
# ══════════════════════════════════════════════════════════════════════════════
class PaymentManager:
    """Stub payment manager. Replace inner methods with wechatpayv3/alipay SDK."""

    def _make_qr(self, data: str) -> str:
        if _HAS_QRCODE:
            img = qrcode.make(data)
            buf = BytesIO()
            img.save(buf, format="PNG")
            return base64.b64encode(buf.getvalue()).decode()
        return base64.b64encode(data.encode()).decode()

    async def create_alipay(self, out_trade_no: str, amount: float,
                            subject: str, return_url: str) -> Dict[str, Any]:
        pay_url = (
            f"https://openapi.alipay.com/gateway.do"
            f"?app_id=STUB&out_trade_no={out_trade_no}"
            f"&total_amount={amount:.2f}&subject={subject}"
        )
        return {"payment_url": pay_url, "out_trade_no": out_trade_no, "method": "alipay"}

    async def create_wechat(self, out_trade_no: str, amount: float,
                            description: str, client_ip: str) -> Dict[str, Any]:
        qr_data = f"weixin://wxpay/bizpayurl?order={out_trade_no}&amount={amount:.2f}"
        return {
            "qr_code": self._make_qr(qr_data),
            "out_trade_no": out_trade_no,
            "method": "wechat_pay",
        }

    async def create_bank_transfer(self, out_trade_no: str, amount: float) -> Dict[str, Any]:
        return {
            "bank_name": "中国工商银行",
            "bank_account": "6222 0202 0012 3456 789",
            "account_name": "ILbuy商城",
            "amount": amount,
            "reference": out_trade_no,
            "method": "bank_transfer",
        }

    async def verify_alipay_callback(self, params: Dict[str, str]) -> bool:
        return params.get("trade_status") in ("TRADE_SUCCESS", "TRADE_FINISHED")

    async def verify_wechat_callback(self, body: str) -> Dict[str, Any]:
        try:
            import xml.etree.ElementTree as ET
            root = ET.fromstring(body)
            return {child.tag: child.text for child in root}
        except Exception:
            return {}

    async def refund(self, method: str, transaction_id: str,
                     amount: float, reason: str) -> Dict[str, Any]:
        return {
            "refund_id": f"RF_{uuid.uuid4().hex[:12].upper()}",
            "status": "success",
            "amount": amount,
            "method": method,
        }



# ══════════════════════════════════════════════════════════════════════════════
# OrderService
# ══════════════════════════════════════════════════════════════════════════════
class OrderService:
    def __init__(self, config: ServiceConfig) -> None:
        self.config  = config
        self.engine  = create_async_engine(
            config.database_url,
            echo=config.debug,
            connect_args={"check_same_thread": False} if "sqlite" in config.database_url else {},
        )
        self.async_session = sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)
        self.redis   = RedisManager()
        self.payment = PaymentManager()
        self._secret = config.secret_key.encode()
        self._http: Optional[aiohttp.ClientSession] = None

        # Prometheus metrics (no-op if unavailable)
        if _HAS_PROMETHEUS:
            self.ctr_created   = Counter("os_orders_created_total",   "Orders created",   ["source"],     registry=_OS_REGISTRY)
            self.ctr_payments  = Counter("os_payments_total",         "Payments",         ["method","st"],registry=_OS_REGISTRY)
            self.ctr_refunds   = Counter("os_refunds_total",          "Refunds",          ["status"],     registry=_OS_REGISTRY)
            self.hist_latency  = Histogram("os_request_seconds",      "Request latency",  ["op"],         registry=_OS_REGISTRY)
        else:
            class _Noop:
                def labels(self, **_): return self
                def inc(self, *a, **k): pass
                def observe(self, *a, **k): pass
            _n = _Noop()
            self.ctr_created  = _n
            self.ctr_payments = _n
            self.ctr_refunds  = _n
            self.hist_latency = _n

    # ── lifecycle ─────────────────────────────────────────────────────────────
    async def startup(self) -> None:
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        await self.redis.connect(self.config.redis_url)
        self._http = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5))
        asyncio.create_task(self._expire_orders_task())
        asyncio.create_task(self._auto_confirm_task())
        logger.info(f"OrderService ready on {self.config.host}:{self.config.port}")

    async def shutdown(self) -> None:
        if self._http:
            await self._http.close()
        await self.engine.dispose()

    # ── helpers ───────────────────────────────────────────────────────────────
    def _gen_order_id(self) -> str:
        return f"ord_{uuid.uuid4().hex[:16]}"

    def _gen_order_number(self, source: str) -> str:
        prefix = {"web":"W","mobile":"M","app":"A","wechat":"X","api":"P"}.get(source, "O")
        ts  = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        rnd = f"{random.randint(1000,9999)}"
        return f"{prefix}{ts}{rnd}"

    def _gen_payment_id(self) -> str:
        return f"pay_{uuid.uuid4().hex[:16]}"

    def _gen_refund_id(self) -> str:
        return f"ref_{uuid.uuid4().hex[:16]}"

    def _gen_shipment_id(self) -> str:
        return f"shp_{uuid.uuid4().hex[:16]}"

    def _now(self) -> datetime:
        return datetime.utcnow()

    def _fmt_amount(self, v: Any) -> float:
        return float(v) if v is not None else 0.0

    def _fmt_order(self, o: Order) -> Dict[str, Any]:
        return {
            "order_id":         o.order_id,
            "order_number":     o.order_number,
            "user_id":          o.user_id,
            "user_role":        o.user_role,
            "order_status":     o.order_status,
            "payment_status":   o.payment_status,
            "total_amount":     self._fmt_amount(o.total_amount),
            "discount_amount":  self._fmt_amount(o.discount_amount),
            "shipping_fee":     self._fmt_amount(o.shipping_fee),
            "tax_amount":       self._fmt_amount(o.tax_amount),
            "final_amount":     self._fmt_amount(o.final_amount),
            "paid_amount":      self._fmt_amount(o.paid_amount),
            "refund_amount":    self._fmt_amount(o.refund_amount),
            "items":            o.items or [],
            "shipping_address": o.shipping_address or {},
            "billing_address":  o.billing_address,
            "shipping_method":  o.shipping_method,
            "tracking_number":  o.tracking_number,
            "logistics_company":o.logistics_company,
            "payment_method":   o.payment_method,
            "payment_tx_id":    o.payment_tx_id,
            "coupon_code":      o.coupon_code,
            "coupon_discount":  self._fmt_amount(o.coupon_discount),
            "points_used":      o.points_used or 0,
            "source":           o.source,
            "notes":            o.notes,
            "extra_metadata":   o.extra_metadata or {},
            "expires_at":       o.expires_at.isoformat() if o.expires_at else None,
            "paid_at":          o.paid_at.isoformat() if o.paid_at else None,
            "shipped_at":       o.shipped_at.isoformat() if o.shipped_at else None,
            "delivered_at":     o.delivered_at.isoformat() if o.delivered_at else None,
            "completed_at":     o.completed_at.isoformat() if o.completed_at else None,
            "cancelled_at":     o.cancelled_at.isoformat() if o.cancelled_at else None,
            "refunded_at":      o.refunded_at.isoformat() if o.refunded_at else None,
            "created_at":       o.created_at.isoformat() if o.created_at else None,
            "updated_at":       o.updated_at.isoformat() if o.updated_at else None,
        }

    async def _record_activity(
        self, sess: AsyncSession, order_id: str,
        act_type: str, action: str, result: str,
        performed_by: str = "system", by_type: str = "system",
        before: Optional[Dict] = None, after: Optional[Dict] = None,
        message: str = "", ip: Optional[str] = None,
    ) -> None:
        activity = OrderActivity(
            activity_id    = f"act_{uuid.uuid4().hex[:16]}",
            order_id       = order_id,
            activity_type  = act_type,
            activity_action= action,
            activity_result= result,
            message        = message,
            performed_by   = performed_by,
            performed_by_type = by_type,
            before_state   = before,
            after_state    = after,
            ip_address     = ip,
            performed_at   = self._now(),
            created_at     = self._now(),
        )
        sess.add(activity)

    async def _notify(self, order_id: str, user_id: str,
                      event: str, data: Dict[str, Any]) -> None:
        if not self._http:
            return
        try:
            await self._http.post(
                f"{self.config.notify_url}/internal/notify",
                json={"order_id": order_id, "user_id": user_id, "event": event, "data": data},
            )
        except Exception as exc:
            logger.debug(f"Notify failed (non-fatal): {exc}")

    def _calc_prices(
        self, items: List[Dict], shipping_addr: Dict,
        coupon_code: Optional[str], points_used: int, user_role: str,
    ) -> Dict[str, float]:
        total     = sum(float(i["total_price"]) for i in items)
        items_disc= sum(float(i.get("discount_amount", 0)) for i in items)

        # shipping fee
        total_kg = sum(float(i.get("weight", 0)) * int(i["quantity"]) for i in items)
        sfee = 8.0 + max(0.0, total_kg - 1) * 2.0
        remote = {"新疆","西藏","青海","内蒙古","黑龙江"}
        if shipping_addr.get("province", "") in remote:
            sfee += 15.0

        # tax (B2B 13 %)
        tax = total * 0.13 if user_role in ("b2b_buyer", "B2B_BUYER") else 0.0

        # coupon discount
        coup_disc = 0.0
        if coupon_code:
            if coupon_code.upper().startswith("DISCOUNT10"):
                coup_disc = min(total * 0.10, 50.0)
            elif coupon_code.upper().startswith("DISCOUNT20"):
                coup_disc = min(total * 0.20, 100.0)
            elif coupon_code.upper().startswith("FIXED"):
                try:
                    coup_disc = float(coupon_code.upper().replace("FIXED",""))
                except ValueError:
                    coup_disc = 0.0

        # points  (100 pts = 1 CNY)
        pts_disc  = points_used / 100.0

        discount  = items_disc + coup_disc + pts_disc
        final     = max(0.0, total - discount + sfee + tax)
        return {
            "total_amount":    round(total, 2),
            "discount_amount": round(discount, 2),
            "shipping_fee":    round(sfee, 2),
            "tax_amount":      round(tax, 2),
            "final_amount":    round(final, 2),
            "coupon_discount": round(coup_disc, 2),
            "pts_discount":    round(pts_disc, 2),
        }

    # ── order CRUD ────────────────────────────────────────────────────────────
    async def create_order(self, req: CreateOrderRequest) -> Dict[str, Any]:
        t0 = time.perf_counter()
        items_raw = [i.model_dump() for i in req.items]
        addr_raw  = req.shipping_address.model_dump()
        prices    = self._calc_prices(
            items_raw, addr_raw, req.coupon_code, req.points_used, req.user_role
        )
        order_id  = self._gen_order_id()
        order_num = self._gen_order_number(req.source)
        now       = self._now()
        expires   = now + timedelta(minutes=self.config.order_timeout_min)

        async with self.async_session() as sess:
            order = Order(
                order_id        = order_id,
                order_number    = order_num,
                user_id         = req.user_id,
                user_role       = req.user_role,
                order_status    = OrderStatus.PENDING.value,
                payment_status  = PaymentStatus.PENDING.value,
                total_amount    = prices["total_amount"],
                discount_amount = prices["discount_amount"],
                shipping_fee    = prices["shipping_fee"],
                tax_amount      = prices["tax_amount"],
                final_amount    = prices["final_amount"],
                items           = items_raw,
                shipping_address= addr_raw,
                billing_address = req.billing_address,
                shipping_method = req.shipping_method,
                payment_method  = req.payment_method,
                payment_channel = req.payment_channel,
                coupon_code     = req.coupon_code,
                coupon_discount = prices["coupon_discount"],
                promotion_ids   = req.promotion_ids or [],
                points_used     = req.points_used,
                source          = req.source,
                ip_address      = req.ip_address,
                notes           = req.notes,
                extra_metadata  = req.extra_metadata,
                expires_at      = expires,
                created_at      = now,
                updated_at      = now,
            )
            sess.add(order)
            await sess.flush()
            await self._record_activity(
                sess, order_id, "order", "create", "success",
                req.user_id, "user",
                before={},
                after={"order_status": order.order_status, "final_amount": prices["final_amount"]},
                ip=req.ip_address,
            )
            await sess.commit()

        asyncio.create_task(self._notify(order_id, req.user_id, "order_created", {
            "order_number": order_num,
            "final_amount": prices["final_amount"],
        }))
        self.ctr_created.labels(source=req.source).inc()
        self.hist_latency.labels(op="create_order").observe(time.perf_counter() - t0)
        return {
            "success":      True,
            "order_id":     order_id,
            "order_number": order_num,
            "total_amount": prices["total_amount"],
            "final_amount": prices["final_amount"],
            "expires_at":   expires.isoformat(),
            "next_step":    "payment",
        }

    async def get_order(self, order_id: str,
                        user_id: Optional[str] = None) -> Dict[str, Any]:
        async with self.async_session() as sess:
            stmt = select(Order).where(Order.order_id == order_id)
            if user_id:
                stmt = stmt.where(Order.user_id == user_id)
            order = await sess.scalar(stmt)
            if not order:
                raise HTTPException(status_code=404, detail="订单不存在")
            return {"success": True, "order": self._fmt_order(order)}

    async def list_orders(
        self, user_id: str,
        order_status: Optional[str] = None,
        payment_status: Optional[str] = None,
        page: int = 1, page_size: int = 20,
        sort_by: str = "created_at", sort_order: str = "desc",
    ) -> Dict[str, Any]:
        async with self.async_session() as sess:
            conds = [Order.user_id == user_id]
            if order_status:
                conds.append(Order.order_status == order_status)
            if payment_status:
                conds.append(Order.payment_status == payment_status)

            total_stmt = select(func.count(Order.id)).where(and_(*conds))
            total = await sess.scalar(total_stmt) or 0

            sort_col = getattr(Order, sort_by, Order.created_at)
            direction = asc if sort_order == "asc" else desc
            stmt = (
                select(Order)
                .where(and_(*conds))
                .order_by(direction(sort_col))
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
            rows = (await sess.scalars(stmt)).all()
            return {
                "success":   True,
                "total":     total,
                "page":      page,
                "page_size": page_size,
                "orders":    [self._fmt_order(o) for o in rows],
            }

    async def cancel_order(self, order_id: str, user_id: str, reason: str) -> Dict[str, Any]:
        async with self.async_session() as sess:
            order = await sess.scalar(
                select(Order).where(Order.order_id == order_id, Order.user_id == user_id)
            )
            if not order:
                raise HTTPException(404, "订单不存在")
            if order.order_status not in (OrderStatus.PENDING.value, OrderStatus.CONFIRMED.value):
                raise HTTPException(400, f"当前状态 {order.order_status} 不可取消")

            now = self._now()
            before = {"order_status": order.order_status}
            await sess.execute(
                sa_update(Order)
                .where(Order.order_id == order_id)
                .values(
                    order_status  = OrderStatus.CANCELLED.value,
                    cancelled_at  = now,
                    updated_at    = now,
                    notes         = reason,
                )
            )
            await self._record_activity(
                sess, order_id, "order", "cancel", "success",
                user_id, "user",
                before=before, after={"order_status": OrderStatus.CANCELLED.value},
                message=reason,
            )
            await sess.commit()
        return {"success": True, "order_id": order_id, "order_status": OrderStatus.CANCELLED.value}

    # ── payment ───────────────────────────────────────────────────────────────
    async def initiate_payment(self, req: PaymentRequest) -> Dict[str, Any]:
        async with self.async_session() as sess:
            order = await sess.scalar(select(Order).where(Order.order_id == req.order_id))
            if not order:
                raise HTTPException(404, "订单不存在")
            if order.payment_status == PaymentStatus.SUCCESS.value:
                raise HTTPException(400, "订单已支付")
            if order.order_status == OrderStatus.CANCELLED.value:
                raise HTTPException(400, "订单已取消")

            amount      = self._fmt_amount(order.final_amount)
            out_trade_no= f"{order.order_number}_{int(time.time())}"
            pay_id      = self._gen_payment_id()
            now         = self._now()
            expires     = now + timedelta(minutes=self.config.order_timeout_min)
            method      = req.payment_method

            if method == PaymentMethod.ALIPAY.value:
                pay_data = await self.payment.create_alipay(
                    out_trade_no, amount, f"订单 {order.order_number}",
                    req.return_url or ""
                )
            elif method == PaymentMethod.WECHAT_PAY.value:
                pay_data = await self.payment.create_wechat(
                    out_trade_no, amount, f"订单 {order.order_number}",
                    req.client_ip or "127.0.0.1"
                )
            elif method == PaymentMethod.BANK_TRANSFER.value:
                pay_data = await self.payment.create_bank_transfer(out_trade_no, amount)
            else:
                pay_data = {"method": method, "out_trade_no": out_trade_no}

            payment = Payment(
                payment_id     = pay_id,
                order_id       = req.order_id,
                payment_method = method,
                payment_status = PaymentStatus.PENDING.value,
                amount         = amount,
                out_trade_no   = out_trade_no,
                payment_url    = pay_data.get("payment_url"),
                qr_code        = pay_data.get("qr_code"),
                payment_data   = pay_data,
                expires_at     = expires,
                created_at     = now,
                updated_at     = now,
            )
            sess.add(payment)
            await sess.execute(
                sa_update(Order).where(Order.order_id == req.order_id)
                .values(payment_method=method, updated_at=now)
            )
            await self._record_activity(
                sess, req.order_id, "payment", "initiate", "success",
                order.user_id, "user",
                after={"payment_id": pay_id, "method": method, "amount": amount},
            )
            await sess.commit()

        self.ctr_payments.labels(method=method, st="initiated").inc()
        return {
            "success":       True,
            "payment_id":    pay_id,
            "order_id":      req.order_id,
            "payment_method":method,
            "payment_status":PaymentStatus.PENDING.value,
            "amount":        amount,
            "expires_at":    expires.isoformat(),
            **{k: v for k, v in pay_data.items() if k not in ("method",)},
        }

    async def handle_payment_callback(
        self, method: str, params: Dict[str, Any], raw_body: str = ""
    ) -> Dict[str, Any]:
        verified = False
        tx_id    = ""

        if method == "alipay":
            verified = await self.payment.verify_alipay_callback(params)
            tx_id    = params.get("trade_no", "")
            out_no   = params.get("out_trade_no", "")
        elif method == "wechat":
            data     = await self.payment.verify_wechat_callback(raw_body)
            verified = data.get("result_code") == "SUCCESS"
            tx_id    = data.get("transaction_id", "")
            out_no   = data.get("out_trade_no", "")
        else:
            return {"success": False, "message": "unsupported method"}

        if not verified:
            return {"success": False, "message": "验签失败"}

        # Extract order_number from out_trade_no (format: ORDER_NUMBER_TIMESTAMP)
        order_number = out_no.rsplit("_", 1)[0] if "_" in out_no else out_no
        now = self._now()

        async with self.async_session() as sess:
            order = await sess.scalar(
                select(Order).where(Order.order_number == order_number)
            )
            if not order:
                return {"success": False, "message": "订单不存在"}
            if order.payment_status == PaymentStatus.SUCCESS.value:
                return {"success": True, "message": "already paid"}

            await sess.execute(
                sa_update(Order)
                .where(Order.order_id == order.order_id)
                .values(
                    order_status   = OrderStatus.PAID.value,
                    payment_status = PaymentStatus.SUCCESS.value,
                    payment_tx_id  = tx_id,
                    paid_amount    = order.final_amount,
                    paid_at        = now,
                    updated_at     = now,
                )
            )
            await sess.execute(
                sa_update(Payment)
                .where(Payment.out_trade_no == out_no)
                .values(
                    payment_status = PaymentStatus.SUCCESS.value,
                    transaction_id = tx_id,
                    paid_at        = now,
                    callback_data  = params,
                    updated_at     = now,
                )
            )
            await self._record_activity(
                sess, order.order_id, "payment", "callback_success", "success",
                "system", "system",
                after={"tx_id": tx_id, "method": method},
            )
            await sess.commit()
            asyncio.create_task(self._notify(order.order_id, order.user_id, "payment_success", {
                "order_number": order.order_number,
                "amount": self._fmt_amount(order.final_amount),
            }))

        self.ctr_payments.labels(method=method, st="success").inc()
        return {"success": True, "message": "ok", "order_id": order.order_id}

    # ── refund ────────────────────────────────────────────────────────────────
    async def request_refund(self, req: RefundRequest, user_id: str) -> Dict[str, Any]:
        async with self.async_session() as sess:
            order = await sess.scalar(
                select(Order).where(Order.order_id == req.order_id, Order.user_id == user_id)
            )
            if not order:
                raise HTTPException(404, "订单不存在")
            if order.order_status not in (
                OrderStatus.PAID.value, OrderStatus.COMPLETED.value,
                OrderStatus.DELIVERED.value, OrderStatus.CONFIRMED.value,
            ):
                raise HTTPException(400, f"状态 {order.order_status} 不可申请退款")

            max_refund = self._fmt_amount(order.paid_amount) - self._fmt_amount(order.refund_amount)
            if req.refund_amount > max_refund + 0.01:
                raise HTTPException(400, f"退款金额 {req.refund_amount} 超过可退 {max_refund:.2f}")

            refund_id = self._gen_refund_id()
            now       = self._now()
            refund    = Refund(
                refund_id      = refund_id,
                order_id       = req.order_id,
                refund_status  = "pending",
                refund_amount  = req.refund_amount,
                refund_reason  = req.refund_reason,
                refund_type    = "partial" if req.refund_amount < max_refund else "full",
                transaction_id = order.payment_tx_id,
                refund_items   = req.refund_items,
                requested_at   = now,
                created_at     = now,
                updated_at     = now,
            )
            sess.add(refund)
            await sess.execute(
                sa_update(Order).where(Order.order_id == req.order_id)
                .values(order_status=OrderStatus.REFUNDING.value, updated_at=now)
            )
            await self._record_activity(
                sess, req.order_id, "refund", "request", "success",
                user_id, "user",
                after={"refund_id": refund_id, "amount": req.refund_amount},
            )
            await sess.commit()

        self.ctr_refunds.labels(status="requested").inc()
        return {
            "success":       True,
            "refund_id":     refund_id,
            "order_id":      req.order_id,
            "refund_amount": req.refund_amount,
            "refund_status": "pending",
        }

    async def process_refund(self, refund_id: str, req: ProcessRefundRequest) -> Dict[str, Any]:
        async with self.async_session() as sess:
            refund = await sess.scalar(select(Refund).where(Refund.refund_id == refund_id))
            if not refund:
                raise HTTPException(404, "退款单不存在")
            if refund.refund_status != "pending":
                raise HTTPException(400, f"退款状态 {refund.refund_status} 不可处理")

            order = await sess.scalar(select(Order).where(Order.order_id == refund.order_id))
            now   = self._now()

            if req.approve:
                # call payment gateway
                result = await self.payment.refund(
                    order.payment_method if order else "alipay",
                    refund.transaction_id or "",
                    float(refund.refund_amount),
                    refund.refund_reason,
                )
                new_ref_status = "completed" if result["status"] == "success" else "failed"
                new_ord_status = OrderStatus.REFUNDED.value
                new_ord_refund = self._fmt_amount(order.refund_amount if order else 0) + float(refund.refund_amount) if order else float(refund.refund_amount)
                await sess.execute(
                    sa_update(Refund).where(Refund.refund_id == refund_id)
                    .values(
                        refund_status = new_ref_status,
                        refund_tx_id  = result.get("refund_id"),
                        processor_id  = req.processor_id,
                        processor_notes = req.notes,
                        processed_at  = now,
                        completed_at  = now,
                        updated_at    = now,
                    )
                )
                if order:
                    await sess.execute(
                        sa_update(Order).where(Order.order_id == order.order_id)
                        .values(
                            order_status  = new_ord_status,
                            payment_status= PaymentStatus.REFUNDED.value,
                            refund_amount = new_ord_refund,
                            refunded_at   = now,
                            updated_at    = now,
                        )
                    )
            else:
                await sess.execute(
                    sa_update(Refund).where(Refund.refund_id == refund_id)
                    .values(
                        refund_status   = "rejected",
                        processor_id    = req.processor_id,
                        processor_notes = req.notes,
                        processed_at    = now,
                        updated_at      = now,
                    )
                )
                if order:
                    await sess.execute(
                        sa_update(Order).where(Order.order_id == order.order_id)
                        .values(order_status=OrderStatus.COMPLETED.value, updated_at=now)
                    )

            if order:
                await self._record_activity(
                    sess, order.order_id, "refund",
                    "approve" if req.approve else "reject",
                    "success", req.processor_id or "admin", "admin",
                    after={"refund_id": refund_id, "approve": req.approve},
                )
            await sess.commit()

        status_str = "completed" if req.approve else "rejected"
        self.ctr_refunds.labels(status=status_str).inc()
        return {"success": True, "refund_id": refund_id, "refund_status": status_str}

    # ── shipment ──────────────────────────────────────────────────────────────
    async def ship_order(self, req: ShipOrderRequest) -> Dict[str, Any]:
        async with self.async_session() as sess:
            order = await sess.scalar(select(Order).where(Order.order_id == req.order_id))
            if not order:
                raise HTTPException(404, "订单不存在")
            if order.order_status not in (OrderStatus.PAID.value, OrderStatus.CONFIRMED.value, OrderStatus.PROCESSING.value):
                raise HTTPException(400, f"状态 {order.order_status} 不可发货")

            shp_id  = self._gen_shipment_id()
            now     = self._now()
            shipped = req.shipped_at or now
            est_del = shipped + timedelta(days={"express":3,"sf_express":2,"yto":5,"zto":5,"self_pickup":0}.get(order.shipping_method, 4))
            shipment = Shipment(
                shipment_id       = shp_id,
                order_id          = req.order_id,
                tracking_number   = req.tracking_number,
                logistics_company = req.logistics_company,
                logistics_code    = req.logistics_code,
                weight            = req.weight,
                shipped_items     = order.items,
                current_status    = "shipped",
                estimated_delivery= est_del,
                shipped_at        = shipped,
                created_at        = now,
                updated_at        = now,
            )
            sess.add(shipment)
            await sess.execute(
                sa_update(Order).where(Order.order_id == req.order_id)
                .values(
                    order_status      = OrderStatus.SHIPPED.value,
                    tracking_number   = req.tracking_number,
                    logistics_company = req.logistics_company,
                    shipped_at        = shipped,
                    updated_at        = now,
                )
            )
            await self._record_activity(
                sess, req.order_id, "shipment", "ship", "success",
                "operator", "admin",
                after={"tracking": req.tracking_number, "company": req.logistics_company},
            )
            await sess.commit()

        asyncio.create_task(self._notify(req.order_id, order.user_id, "order_shipped", {
            "tracking_number":   req.tracking_number,
            "logistics_company": req.logistics_company,
            "estimated_delivery": est_del.isoformat(),
        }))
        return {
            "success":          True,
            "shipment_id":      shp_id,
            "order_id":         req.order_id,
            "tracking_number":  req.tracking_number,
            "logistics_company":req.logistics_company,
            "estimated_delivery": est_del.isoformat(),
        }

    async def confirm_delivery(self, order_id: str, user_id: str) -> Dict[str, Any]:
        async with self.async_session() as sess:
            order = await sess.scalar(
                select(Order).where(Order.order_id == order_id, Order.user_id == user_id)
            )
            if not order:
                raise HTTPException(404, "订单不存在")
            if order.order_status not in (OrderStatus.SHIPPED.value, OrderStatus.DELIVERED.value):
                raise HTTPException(400, f"状态 {order.order_status} 不可确认收货")

            now = self._now()
            await sess.execute(
                sa_update(Order).where(Order.order_id == order_id)
                .values(
                    order_status = OrderStatus.COMPLETED.value,
                    delivered_at = now,
                    completed_at = now,
                    updated_at   = now,
                )
            )
            await sess.execute(
                sa_update(Shipment).where(Shipment.order_id == order_id)
                .values(current_status="delivered", delivered_at=now, updated_at=now)
            )
            await self._record_activity(
                sess, order_id, "delivery", "confirm", "success", user_id, "user",
                after={"order_status": OrderStatus.COMPLETED.value},
            )
            await sess.commit()

        return {"success": True, "order_id": order_id, "order_status": OrderStatus.COMPLETED.value}

    async def get_activities(self, order_id: str) -> Dict[str, Any]:
        async with self.async_session() as sess:
            rows = (await sess.scalars(
                select(OrderActivity)
                .where(OrderActivity.order_id == order_id)
                .order_by(desc(OrderActivity.performed_at))
                .limit(50)
            )).all()
        return {
            "success":    True,
            "order_id":   order_id,
            "activities": [
                {
                    "activity_id":    a.activity_id,
                    "activity_type":  a.activity_type,
                    "action":         a.activity_action,
                    "result":         a.activity_result,
                    "message":        a.message,
                    "performed_by":   a.performed_by,
                    "performed_by_type": a.performed_by_type,
                    "before_state":   a.before_state,
                    "after_state":    a.after_state,
                    "performed_at":   a.performed_at.isoformat() if a.performed_at else None,
                }
                for a in rows
            ],
        }

    async def get_shipments(self, order_id: str) -> Dict[str, Any]:
        async with self.async_session() as sess:
            rows = (await sess.scalars(
                select(Shipment)
                .where(Shipment.order_id == order_id)
                .order_by(desc(Shipment.shipped_at))
            )).all()
        return {
            "success":   True,
            "order_id":  order_id,
            "shipments": [
                {
                    "shipment_id":       s.shipment_id,
                    "tracking_number":   s.tracking_number,
                    "logistics_company": s.logistics_company,
                    "current_status":    s.current_status,
                    "estimated_delivery":s.estimated_delivery.isoformat() if s.estimated_delivery else None,
                    "delivered_at":      s.delivered_at.isoformat() if s.delivered_at else None,
                    "shipped_at":        s.shipped_at.isoformat() if s.shipped_at else None,
                    "logistics_info":    s.logistics_info,
                }
                for s in rows
            ],
        }

    async def get_refund(self, refund_id: str) -> Dict[str, Any]:
        async with self.async_session() as sess:
            refund = await sess.scalar(select(Refund).where(Refund.refund_id == refund_id))
            if not refund:
                raise HTTPException(404, "退款单不存在")
        return {
            "success":       True,
            "refund_id":     refund.refund_id,
            "order_id":      refund.order_id,
            "refund_status": refund.refund_status,
            "refund_amount": float(refund.refund_amount),
            "refund_reason": refund.refund_reason,
            "refund_type":   refund.refund_type,
            "transaction_id":refund.transaction_id,
            "refund_tx_id":  refund.refund_tx_id,
            "requested_at":  refund.requested_at.isoformat() if refund.requested_at else None,
            "processed_at":  refund.processed_at.isoformat() if refund.processed_at else None,
            "completed_at":  refund.completed_at.isoformat() if refund.completed_at else None,
        }

    async def get_stats(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        async with self.async_session() as sess:
            conds = [Order.user_id == user_id] if user_id else []
            total      = await sess.scalar(select(func.count(Order.id)).where(*conds)) or 0
            paid_cnt   = await sess.scalar(select(func.count(Order.id)).where(*conds, Order.order_status == "paid")) or 0
            done_cnt   = await sess.scalar(select(func.count(Order.id)).where(*conds, Order.order_status == "completed")) or 0
            gmv        = await sess.scalar(select(func.sum(Order.final_amount)).where(*conds, Order.payment_status == "success")) or 0
            refund_amt = await sess.scalar(select(func.sum(Order.refund_amount)).where(*conds)) or 0
        return {
            "success":       True,
            "total_orders":  total,
            "paid_orders":   paid_cnt,
            "completed_orders": done_cnt,
            "gmv":           float(gmv),
            "total_refunded":float(refund_amt),
        }

    # ── background tasks ──────────────────────────────────────────────────────
    async def _expire_orders_task(self) -> None:
        while True:
            await asyncio.sleep(60)
            try:
                now = self._now()
                async with self.async_session() as sess:
                    await sess.execute(
                        sa_update(Order)
                        .where(
                            Order.order_status  == OrderStatus.PENDING.value,
                            Order.payment_status == PaymentStatus.PENDING.value,
                            Order.expires_at    <= now,
                        )
                        .values(
                            order_status    = OrderStatus.CANCELLED.value,
                            payment_status  = PaymentStatus.CLOSED.value,
                            cancelled_at    = now,
                            updated_at      = now,
                        )
                    )
                    await sess.commit()
            except Exception as exc:
                logger.error(f"expire_orders_task error: {exc}")

    async def _auto_confirm_task(self) -> None:
        while True:
            await asyncio.sleep(3600)
            try:
                cutoff = self._now() - timedelta(days=self.config.auto_confirm_days)
                now    = self._now()
                async with self.async_session() as sess:
                    await sess.execute(
                        sa_update(Order)
                        .where(
                            Order.order_status == OrderStatus.SHIPPED.value,
                            Order.shipped_at   <= cutoff,
                        )
                        .values(
                            order_status = OrderStatus.COMPLETED.value,
                            delivered_at = now,
                            completed_at = now,
                            updated_at   = now,
                        )
                    )
                    await sess.commit()
            except Exception as exc:
                logger.error(f"auto_confirm_task error: {exc}")



# ══════════════════════════════════════════════════════════════════════════════
# FastAPI  app factory + routes
# ══════════════════════════════════════════════════════════════════════════════
_bearer = HTTPBearer(auto_error=False)


def _get_service(request: Request) -> OrderService:
    return request.app.state.service


def create_app(config: Optional[ServiceConfig] = None) -> FastAPI:
    cfg = config or ServiceConfig()
    svc = OrderService(cfg)

    app = FastAPI(
        title="Order Service",
        description="业务逻辑层 – 订单服务 (Part 7)",
        version="1.0.0",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
    )
    app.state.service = svc

    @app.on_event("startup")
    async def _startup() -> None:
        await svc.startup()
        await _seed_demo_orders(svc)

    @app.on_event("shutdown")
    async def _shutdown() -> None:
        await svc.shutdown()

    # ── health / info ─────────────────────────────────────────────────────────
    @app.get("/")
    async def root():
        return {
            "service": "order_service",
            "version": "1.0.0",
            "status":  "running",
            "endpoints": [
                "POST   /api/v1/orders",
                "GET    /api/v1/orders",
                "GET    /api/v1/orders/{order_id}",
                "PUT    /api/v1/orders/{order_id}/cancel",
                "POST   /api/v1/orders/{order_id}/payment",
                "POST   /api/v1/payment/callback/{method}",
                "POST   /api/v1/orders/{order_id}/refund",
                "PUT    /api/v1/refunds/{refund_id}/process",
                "GET    /api/v1/refunds/{refund_id}",
                "POST   /api/v1/orders/{order_id}/ship",
                "PUT    /api/v1/orders/{order_id}/confirm",
                "GET    /api/v1/orders/{order_id}/activities",
                "GET    /api/v1/orders/{order_id}/shipments",
                "GET    /api/v1/stats/orders",
                "GET    /metrics",
                "GET    /health",
            ],
        }

    @app.get("/health")
    async def health():
        return {"status": "UP", "service": "order_service"}

    @app.get("/metrics", response_class=PlainTextResponse)
    async def metrics():
        if _HAS_PROMETHEUS:
            return generate_latest(_OS_REGISTRY).decode()
        return "# prometheus_client not available\n"

    # ── orders ────────────────────────────────────────────────────────────────
    @app.post("/api/v1/orders", status_code=status.HTTP_201_CREATED)
    async def create_order(req: CreateOrderRequest, svc: OrderService = Depends(_get_service)):
        return await svc.create_order(req)

    @app.get("/api/v1/orders")
    async def list_orders(
        user_id:        str            = Query(...),
        order_status:   Optional[str]  = Query(None),
        payment_status: Optional[str]  = Query(None),
        page:           int            = Query(1, ge=1),
        page_size:      int            = Query(20, ge=1, le=100),
        sort_by:        str            = Query("created_at"),
        sort_order:     str            = Query("desc"),
        svc: OrderService = Depends(_get_service),
    ):
        return await svc.list_orders(
            user_id, order_status, payment_status,
            page, page_size, sort_by, sort_order,
        )

    @app.get("/api/v1/orders/{order_id}")
    async def get_order(
        order_id: str,
        user_id:  Optional[str] = Query(None),
        svc: OrderService = Depends(_get_service),
    ):
        return await svc.get_order(order_id, user_id)

    @app.put("/api/v1/orders/{order_id}/cancel")
    async def cancel_order(
        order_id: str,
        user_id:  str  = Query(...),
        reason:   str  = Query("用户取消"),
        svc: OrderService = Depends(_get_service),
    ):
        return await svc.cancel_order(order_id, user_id, reason)

    # ── payment ───────────────────────────────────────────────────────────────
    @app.post("/api/v1/orders/{order_id}/payment")
    async def initiate_payment(
        order_id: str, req: PaymentRequest,
        svc: OrderService = Depends(_get_service),
    ):
        req.order_id = order_id
        return await svc.initiate_payment(req)

    @app.post("/api/v1/payment/callback/{method}")
    async def payment_callback(
        method: str, request: Request,
        svc: OrderService = Depends(_get_service),
    ):
        try:
            params   = dict(await request.form()) or await request.json()
        except Exception:
            params = {}
        body = (await request.body()).decode(errors="replace")
        return await svc.handle_payment_callback(method, dict(params), body)

    # ── refund ────────────────────────────────────────────────────────────────
    @app.post("/api/v1/orders/{order_id}/refund", status_code=status.HTTP_201_CREATED)
    async def request_refund(
        order_id: str, req: RefundRequest,
        user_id:  str = Query(...),
        svc: OrderService = Depends(_get_service),
    ):
        req.order_id = order_id
        return await svc.request_refund(req, user_id)

    @app.put("/api/v1/refunds/{refund_id}/process")
    async def process_refund(
        refund_id: str, req: ProcessRefundRequest,
        svc: OrderService = Depends(_get_service),
    ):
        return await svc.process_refund(refund_id, req)

    @app.get("/api/v1/refunds/{refund_id}")
    async def get_refund(refund_id: str, svc: OrderService = Depends(_get_service)):
        return await svc.get_refund(refund_id)

    # ── shipment ──────────────────────────────────────────────────────────────
    @app.post("/api/v1/orders/{order_id}/ship", status_code=status.HTTP_201_CREATED)
    async def ship_order(
        order_id: str, req: ShipOrderRequest,
        svc: OrderService = Depends(_get_service),
    ):
        req.order_id = order_id
        return await svc.ship_order(req)

    @app.put("/api/v1/orders/{order_id}/confirm")
    async def confirm_delivery(
        order_id: str,
        user_id:  str = Query(...),
        svc: OrderService = Depends(_get_service),
    ):
        return await svc.confirm_delivery(order_id, user_id)

    @app.get("/api/v1/orders/{order_id}/shipments")
    async def get_shipments(order_id: str, svc: OrderService = Depends(_get_service)):
        return await svc.get_shipments(order_id)

    # ── activities / stats ────────────────────────────────────────────────────
    @app.get("/api/v1/orders/{order_id}/activities")
    async def get_activities(order_id: str, svc: OrderService = Depends(_get_service)):
        return await svc.get_activities(order_id)

    @app.get("/api/v1/stats/orders")
    async def order_stats(
        user_id: Optional[str] = Query(None),
        svc: OrderService = Depends(_get_service),
    ):
        return await svc.get_stats(user_id)

    return app


# ══════════════════════════════════════════════════════════════════════════════
# Demo seed data
# ══════════════════════════════════════════════════════════════════════════════
async def _seed_demo_orders(svc: OrderService) -> None:
    """Insert demo orders so the service starts non-empty."""
    async with svc.async_session() as sess:
        existing = await sess.scalar(select(func.count(Order.id)))
        if existing and existing > 0:
            return  # already seeded

    demo = [
        {
            "user_id": "user_demo_001", "user_role": "b2c_consumer",
            "order_status": "completed", "payment_status": "success",
            "total": 5299.0, "discount": 300.0, "sfee": 0.0, "tax": 0.0, "final": 4999.0,
            "paid": 4999.0, "refund": 0.0,
            "items": [{"product_id":"TB_V2_001","platform":"tmall","product_name":"联想ThinkPad E14","quantity":1,"unit_price":5299.0,"total_price":5299.0,"discount_amount":300.0}],
            "addr": {"receiver_name":"张三","receiver_phone":"13800138001","province":"北京","city":"北京市","district":"朝阳区","street":"建国路1号","country":"中国"},
            "method": "alipay", "source": "web",
        },
        {
            "user_id": "user_demo_002", "user_role": "b2b_buyer",
            "order_status": "shipped", "payment_status": "success",
            "total": 180000.0, "discount": 0.0, "sfee": 50.0, "tax": 23400.0, "final": 203450.0,
            "paid": 203450.0, "refund": 0.0,
            "items": [{"product_id":"JD_V2_001","platform":"jd","product_name":"Dell PowerEdge服务器","quantity":5,"unit_price":36000.0,"total_price":180000.0,"discount_amount":0.0}],
            "addr": {"receiver_name":"李四","receiver_phone":"13900139002","province":"上海","city":"上海市","district":"浦东新区","street":"张江高科技园区","country":"中国"},
            "method": "bank_transfer", "source": "api",
        },
        {
            "user_id": "user_demo_001", "user_role": "b2c_consumer",
            "order_status": "pending", "payment_status": "pending",
            "total": 2999.0, "discount": 0.0, "sfee": 10.0, "tax": 0.0, "final": 3009.0,
            "paid": 0.0, "refund": 0.0,
            "items": [{"product_id":"PDD_V2_001","platform":"pinduoduo","product_name":"苹果iPhone 15","quantity":1,"unit_price":2999.0,"total_price":2999.0,"discount_amount":0.0}],
            "addr": {"receiver_name":"张三","receiver_phone":"13800138001","province":"北京","city":"北京市","district":"朝阳区","street":"建国路1号","country":"中国"},
            "method": "wechat_pay", "source": "mobile",
        },
    ]

    now  = datetime.utcnow()
    async with svc.async_session() as sess:
        for i, d in enumerate(demo):
            oid = f"ord_demo_{i+1:04d}{uuid.uuid4().hex[:8]}"
            onum = f"DEMO{now.strftime('%Y%m%d')}{i+1:03d}"
            order = Order(
                order_id        = oid,
                order_number    = onum,
                user_id         = d["user_id"],
                user_role       = d["user_role"],
                order_status    = d["order_status"],
                payment_status  = d["payment_status"],
                total_amount    = d["total"],
                discount_amount = d["discount"],
                shipping_fee    = d["sfee"],
                tax_amount      = d["tax"],
                final_amount    = d["final"],
                paid_amount     = d["paid"],
                refund_amount   = d["refund"],
                items           = d["items"],
                shipping_address= d["addr"],
                payment_method  = d["method"],
                source          = d["source"],
                extra_metadata  = {},
                created_at      = now - timedelta(days=(3 - i)),
                updated_at      = now,
                paid_at         = (now - timedelta(days=(3 - i) - 0.1)) if d["paid"] > 0 else None,
                shipped_at      = (now - timedelta(days=1)) if d["order_status"] in ("shipped","completed") else None,
                completed_at    = now if d["order_status"] == "completed" else None,
                expires_at      = now + timedelta(minutes=30) if d["order_status"] == "pending" else None,
            )
            sess.add(order)
        await sess.commit()
    logger.info("Demo orders seeded")


# ══════════════════════════════════════════════════════════════════════════════
# Entry point
# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import uvicorn
    cfg = ServiceConfig()
    app = create_app(cfg)
    uvicorn.run(app, host=cfg.host, port=cfg.port, log_level="info")
