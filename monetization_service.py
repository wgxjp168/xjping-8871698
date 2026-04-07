"""
monetization_service.py — Part 8: Business Monetization Layer
Production-grade: C-end monetization, B-end solutions, data capability output,
payment gateway integration, billing & revenue recognition.
"""

from __future__ import annotations

import asyncio
import base64
import csv
import hashlib
import io
import json
import logging
import math
import os
import random
import statistics
import string
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta, date
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Query, Body, status
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, field_validator, model_validator, ConfigDict
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean, Float, Date,
    create_engine, text, Index, UniqueConstraint
)
from sqlalchemy.orm import declarative_base, Session, sessionmaker
try:
    from sqlalchemy.dialects.sqlite import JSON
except ImportError:
    from sqlalchemy import JSON

# ── Optional heavy dependencies ────────────────────────────────────────────────
try:
    import redis.asyncio as aioredis
    _HAS_REDIS = True
except ImportError:
    aioredis = None  # type: ignore
    _HAS_REDIS = False

try:
    import aiohttp
    _HAS_AIOHTTP = True
except ImportError:
    aiohttp = None  # type: ignore
    _HAS_AIOHTTP = False

try:
    import stripe as _stripe_lib
    _HAS_STRIPE = True
except ImportError:
    _stripe_lib = None  # type: ignore
    _HAS_STRIPE = False

try:
    from alipay import AliPay as _AliPayLib
    _HAS_ALIPAY = True
except ImportError:
    _AliPayLib = None  # type: ignore
    _HAS_ALIPAY = False

try:
    from wechatpayv3 import WeChatPay as _WeChatPayLib, WeChatPayType as _WCPayType
    _HAS_WECHATPAY = True
except ImportError:
    _WeChatPayLib = None  # type: ignore
    _WCPayType = None  # type: ignore
    _HAS_WECHATPAY = False

try:
    import qrcode as qrcode_lib
    _HAS_QRCODE = True
except ImportError:
    qrcode_lib = None  # type: ignore
    _HAS_QRCODE = False

try:
    from prometheus_client import Counter, Gauge, Histogram, Summary, CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST
    _HAS_PROMETHEUS = True
except ImportError:
    _HAS_PROMETHEUS = False

try:
    import pandas as pd
    _HAS_PANDAS = True
except ImportError:
    pd = None  # type: ignore
    _HAS_PANDAS = False

try:
    import numpy as np
    _HAS_NUMPY = True
except ImportError:
    np = None  # type: ignore
    _HAS_NUMPY = False

try:
    from reportlab.lib import colors as rl_colors
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import inch
    _HAS_REPORTLAB = True
except ImportError:
    _HAS_REPORTLAB = False

try:
    import jinja2
    _HAS_JINJA2 = True
except ImportError:
    jinja2 = None  # type: ignore
    _HAS_JINJA2 = False

try:
    import aiofiles
    _HAS_AIOFILES = True
except ImportError:
    aiofiles = None  # type: ignore
    _HAS_AIOFILES = False

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s [%(filename)s:%(lineno)d] %(message)s",
)
logger = logging.getLogger("monetization_service")

# ── Time helpers ───────────────────────────────────────────────────────────────
def _now() -> datetime:
    return datetime.now(timezone.utc)

def _today() -> date:
    return _now().date()

def _fmt_dt(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    return dt.isoformat()

def _naive(dt: datetime) -> datetime:
    """Strip timezone for SQLite storage."""
    if dt.tzinfo is not None:
        return dt.replace(tzinfo=None)
    return dt

def _utc(dt: Optional[datetime]) -> Optional[datetime]:
    """Ensure datetime is UTC-aware (for comparisons)."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt

# ── DB setup ───────────────────────────────────────────────────────────────────
DB_URL = os.getenv("MONETIZATION_DB_URL", "sqlite:///./monetization.db")
engine = create_engine(
    DB_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DB_URL else {},
)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ── Prometheus metrics ─────────────────────────────────────────────────────────
_MS_REGISTRY = CollectorRegistry() if _HAS_PROMETHEUS else None

def _ctr(n, d, l=None):
    if not _HAS_PROMETHEUS: return None
    try: return Counter(n, d, l or [], registry=_MS_REGISTRY)
    except ValueError: return Counter(n, d, l or [], registry=CollectorRegistry())

def _gge(n, d, l=None):
    if not _HAS_PROMETHEUS: return None
    try: return Gauge(n, d, l or [], registry=_MS_REGISTRY)
    except ValueError: return Gauge(n, d, l or [], registry=CollectorRegistry())

def _hst(n, d, l=None, buckets=None):
    if not _HAS_PROMETHEUS: return None
    kw = {"registry": _MS_REGISTRY}
    if buckets: kw["buckets"] = buckets
    try: return Histogram(n, d, l or [], **kw)
    except ValueError:
        kw["registry"] = CollectorRegistry()
        return Histogram(n, d, l or [], **kw)

TRANSACTIONS_TOTAL     = _ctr("ms_transactions_total",          "Total transactions",           ["product_type", "status"])
REVENUE_TOTAL          = _ctr("ms_revenue_total",               "Total revenue",                ["revenue_type"])
ACTIVE_SUBSCRIPTIONS   = _gge("ms_active_subscriptions",        "Active subscriptions",         ["plan_type"])
API_USAGE_TOTAL        = _ctr("ms_api_usage_total",             "Total API usage",              ["endpoint"])
REQUEST_LATENCY        = _hst("ms_request_latency_seconds",     "Request latency",              ["endpoint"])
PAYMENT_TIME           = _hst("ms_payment_processing_seconds",  "Payment processing time",      ["gateway"])

# ── Numeric helpers ────────────────────────────────────────────────────────────
def _mean(vals: List[float]) -> float:
    if not vals: return 0.0
    return float(np.mean(vals)) if _HAS_NUMPY else statistics.mean(vals)

def _std(vals: List[float]) -> float:
    if len(vals) < 2: return 0.0
    return float(np.std(vals)) if _HAS_NUMPY else statistics.stdev(vals)

# ══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ══════════════════════════════════════════════════════════════════════════════

class ProductType(str, Enum):
    C2C_SINGLE         = "c2c_single"
    C2C_SUBSCRIPTION   = "c2c_subscription"
    B2B_SAAS           = "b2b_saas"
    B2B_API            = "b2b_api"
    B2B_CUSTOM         = "b2b_custom"
    DATA_API           = "data_api"
    DATA_REPORT        = "data_report"
    DATA_INSIGHT       = "data_insight"

class BillingCycle(str, Enum):
    ONE_TIME   = "one_time"
    DAILY      = "daily"
    WEEKLY     = "weekly"
    MONTHLY    = "monthly"
    QUARTERLY  = "quarterly"
    YEARLY     = "yearly"

class PaymentStatus(str, Enum):
    PENDING        = "pending"
    PROCESSING     = "processing"
    SUCCESS        = "success"
    FAILED         = "failed"
    REFUNDED       = "refunded"
    PARTIAL_REFUND = "partial_refund"
    CANCELLED      = "cancelled"

class InvoiceStatus(str, Enum):
    PENDING   = "pending"
    ISSUED    = "issued"
    SENT      = "sent"
    PAID      = "paid"
    CANCELLED = "cancelled"

class RefundStatus(str, Enum):
    PENDING    = "pending"
    PROCESSING = "processing"
    COMPLETED  = "completed"
    FAILED     = "failed"
    CANCELLED  = "cancelled"

class OrderStatus(str, Enum):
    PENDING    = "pending"
    PROCESSING = "processing"
    COMPLETED  = "completed"
    CANCELLED  = "cancelled"
    REFUNDED   = "refunded"
    EXPIRED    = "expired"

class SubscriptionStatus(str, Enum):
    TRIALING    = "trialing"
    ACTIVE      = "active"
    PAST_DUE    = "past_due"
    CANCELLED   = "cancelled"
    EXPIRED     = "expired"
    PAUSED      = "paused"

class RevenueType(str, Enum):
    PRODUCT_SALE   = "product_sale"
    SUBSCRIPTION   = "subscription"
    API_USAGE      = "api_usage"
    SERVICE_FEE    = "service_fee"
    DATA_SALE      = "data_sale"
    CUSTOMIZATION  = "customization"
    ADVERTISING    = "advertising"
    PARTNERSHIP    = "partnership"

# ══════════════════════════════════════════════════════════════════════════════
# SERVICE CONFIG
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class ServiceConfig:
    database_url:  str  = DB_URL
    redis_url:     str  = os.getenv("REDIS_URL", "redis://localhost:6379/7")
    host:          str  = os.getenv("MS_HOST", "0.0.0.0")
    port:          int  = int(os.getenv("MS_PORT", "8025"))
    debug:         bool = False

    stripe_secret_key:     str = os.getenv("STRIPE_SECRET_KEY", "")
    stripe_webhook_secret: str = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    alipay_app_id:         str = os.getenv("ALIPAY_APP_ID", "")
    alipay_private_key:    str = os.getenv("ALIPAY_PRIVATE_KEY", "")
    alipay_public_key:     str = os.getenv("ALIPAY_PUBLIC_KEY", "")
    wechat_app_id:         str = os.getenv("WECHAT_APP_ID", "")
    wechat_mch_id:         str = os.getenv("WECHAT_MCH_ID", "")

    invoice_company_name:  str = os.getenv("INVOICE_COMPANY", "多模态商品识别科技有限公司")
    invoice_tax_number:    str = os.getenv("INVOICE_TAX_NO",  "91110108MA01XXXXXX")
    invoice_address:       str = os.getenv("INVOICE_ADDR",    "北京市海淀区中关村大街1号")

    user_service_url:         str = os.getenv("USER_SERVICE_URL",         "http://localhost:8020")
    order_service_url:        str = os.getenv("ORDER_SERVICE_URL",        "http://localhost:8022")
    report_service_url:       str = os.getenv("REPORT_SERVICE_URL",       "http://localhost:8024")
    notification_service_url: str = os.getenv("NOTIFICATION_SERVICE_URL", "http://localhost:8040")

    # Pricing
    c2c_single_price:       float = float(os.getenv("C2C_SINGLE_PRICE",    "9.9"))
    c2c_monthly_price:      float = float(os.getenv("C2C_MONTHLY_PRICE",   "29.9"))
    c2c_quarterly_price:    float = float(os.getenv("C2C_QUARTERLY_PRICE", "79.9"))
    c2c_yearly_price:       float = float(os.getenv("C2C_YEARLY_PRICE",    "299.9"))
    b2b_api_unit_price:     float = float(os.getenv("B2B_API_UNIT_PRICE",  "0.01"))
    tax_rate:               float = float(os.getenv("TAX_RATE",            "0.06"))
    payment_fee_rate:       float = float(os.getenv("PAYMENT_FEE_RATE",    "0.029"))

    subscription_trial_days:  int = int(os.getenv("TRIAL_DAYS", "7"))
    subscription_grace_days:  int = int(os.getenv("GRACE_DAYS", "3"))


# ══════════════════════════════════════════════════════════════════════════════
# PYDANTIC SCHEMAS
# ══════════════════════════════════════════════════════════════════════════════

class PriceTierSchema(BaseModel):
    min_units:  int
    max_units:  Optional[int] = None
    unit_price: float
    flat_fee:   float = 0.0


class CreateOrderRequest(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    user_id:             str
    user_role:           str
    product_type:        ProductType
    plan_id:             str
    quantity:            int = 1
    amount:              float
    currency:            str = "CNY"
    discount_code:       Optional[str] = None
    payment_method:      str = "alipay"
    return_url:          Optional[str] = None
    is_subscription:     bool = False
    subscription_cycle:  BillingCycle = BillingCycle.MONTHLY
    auto_renew:          bool = True
    need_invoice:        bool = False
    invoice_info:        Optional[Dict[str, Any]] = None
    metadata:            Dict[str, Any] = {}

    @field_validator("quantity")
    @classmethod
    def validate_qty(cls, v: int) -> int:
        if v < 1: raise ValueError("quantity must be >= 1")
        return v

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: float) -> float:
        if v <= 0: raise ValueError("amount must be > 0")
        return v


class CreateSubscriptionRequest(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    user_id:         str
    plan_id:         str
    payment_method:  str
    billing_cycle:   BillingCycle
    quantity:        int = 1
    trial_days:      Optional[int] = None
    coupon_code:     Optional[str] = None
    metadata:        Dict[str, Any] = {}


class APIBillingRequest(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    user_id:             str
    api_endpoint:        str
    request_count:       int = 1
    data_volume_mb:      float = 0.0
    processing_time_ms:  int = 0
    timestamp:           Optional[datetime] = None
    metadata:            Dict[str, Any] = {}

    @field_validator("request_count")
    @classmethod
    def validate_count(cls, v: int) -> int:
        if v < 0: raise ValueError("request_count must be >= 0")
        return v


class RefundRequest(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    order_id:   str
    amount:     float
    reason:     str = ""
    metadata:   Dict[str, Any] = {}

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: float) -> float:
        if v <= 0: raise ValueError("amount must be > 0")
        return v


class InvoiceRequest(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    order_id:       str
    invoice_type:   str = "company"    # personal | company | vat
    title:          str
    tax_number:     Optional[str] = None
    email:          Optional[str] = None
    address:        Optional[str] = None
    metadata:       Dict[str, Any] = {}


class CouponRequest(BaseModel):
    code:         str
    discount_type: str = "percentage"   # percentage | fixed
    value:        float
    min_amount:   float = 0.0
    max_discount: Optional[float] = None
    expires_at:   Optional[datetime] = None
    max_uses:     Optional[int] = None
    product_types: List[str] = []


class PricingPlanRequest(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    product_id:    str
    name:          str
    description:   str = ""
    billing_cycle: BillingCycle
    amount:        float
    currency:      str = "CNY"
    trial_days:    int = 0
    features:      List[str] = []
    limits:        Dict[str, Any] = {}
    price_tiers:   Optional[List[PriceTierSchema]] = None
    is_default:    bool = False

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: float) -> float:
        if v < 0: raise ValueError("amount must be >= 0")
        return v


# ══════════════════════════════════════════════════════════════════════════════
# ORM MODELS
# ══════════════════════════════════════════════════════════════════════════════

class ProductModel(Base):
    __tablename__ = "ms_products"
    id              = Column(Integer, primary_key=True, autoincrement=True)
    product_id      = Column(String(64), unique=True, nullable=False, index=True)
    name            = Column(String(200), nullable=False, index=True)
    description     = Column(Text, default="")
    product_type    = Column(String(50), nullable=False, index=True)
    category        = Column(String(100), default="", index=True)
    tags            = Column(JSON, default=list)
    pricing_model   = Column(String(20), nullable=False)
    currency        = Column(String(3), default="CNY")
    base_price      = Column(Float, nullable=True)
    unit_price      = Column(Float, nullable=True)
    setup_fee       = Column(Float, default=0.0)
    features        = Column(JSON, default=list)
    limitations     = Column(JSON, default=dict)
    is_active       = Column(Boolean, default=True, index=True)
    is_public       = Column(Boolean, default=True, index=True)
    extra_metadata  = Column("product_metadata", JSON, default=dict)
    created_at      = Column(DateTime, default=_naive(_now()))
    updated_at      = Column(DateTime, default=_naive(_now()))


class PricingPlanModel(Base):
    __tablename__ = "ms_pricing_plans"
    id              = Column(Integer, primary_key=True, autoincrement=True)
    plan_id         = Column(String(64), unique=True, nullable=False, index=True)
    product_id      = Column(String(64), nullable=False, index=True)
    name            = Column(String(200), nullable=False)
    description     = Column(Text, default="")
    billing_cycle   = Column(String(20), nullable=False, index=True)
    amount          = Column(Float, nullable=False)
    currency        = Column(String(3), default="CNY")
    trial_days      = Column(Integer, default=0)
    features        = Column(JSON, default=list)
    limits          = Column(JSON, default=dict)
    price_tiers     = Column(JSON, nullable=True)
    is_active       = Column(Boolean, default=True, index=True)
    is_default      = Column(Boolean, default=False)
    display_order   = Column(Integer, default=0)
    extra_metadata  = Column("plan_metadata", JSON, default=dict)
    created_at      = Column(DateTime, default=_naive(_now()))
    updated_at      = Column(DateTime, default=_naive(_now()))

    __table_args__ = (
        UniqueConstraint("product_id", "billing_cycle", "name", name="uq_plan_product_cycle_name"),
    )


class OrderModel(Base):
    __tablename__ = "ms_orders"
    id              = Column(Integer, primary_key=True, autoincrement=True)
    order_id        = Column(String(64), unique=True, nullable=False, index=True)
    order_number    = Column(String(32), unique=True, nullable=False, index=True)
    user_id         = Column(String(64), nullable=False, index=True)
    user_role       = Column(String(20), nullable=False)
    company_id      = Column(String(64), nullable=True, index=True)
    product_id      = Column(String(64), nullable=False, index=True)
    plan_id         = Column(String(64), nullable=True, index=True)
    order_type      = Column(String(20), nullable=False, index=True)
    quantity        = Column(Integer, default=1)
    amount          = Column(Float, nullable=False)
    discount_amount = Column(Float, default=0.0)
    tax_amount      = Column(Float, default=0.0)
    total_amount    = Column(Float, nullable=False)
    currency        = Column(String(3), default="CNY")
    payment_method  = Column(String(20), nullable=False)
    payment_status  = Column(String(20), default=PaymentStatus.PENDING.value, index=True)
    paid_amount     = Column(Float, default=0.0)
    paid_at         = Column(DateTime, nullable=True)
    invoice_id      = Column(String(64), nullable=True)
    status          = Column(String(20), default=OrderStatus.PENDING.value, index=True)
    is_test         = Column(Boolean, default=False)
    subscription_id = Column(String(64), nullable=True, index=True)
    extra_metadata  = Column("order_metadata", JSON, default=dict)
    created_at      = Column(DateTime, default=_naive(_now()), index=True)
    updated_at      = Column(DateTime, default=_naive(_now()))
    expires_at      = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("idx_ms_order_user_status", "user_id", "status"),
        Index("idx_ms_order_company",     "company_id", "status"),
    )


class PaymentModel(Base):
    __tablename__ = "ms_payments"
    id                    = Column(Integer, primary_key=True, autoincrement=True)
    payment_id            = Column(String(64), unique=True, nullable=False, index=True)
    order_id              = Column(String(64), nullable=False, index=True)
    payment_method        = Column(String(20), nullable=False)
    payment_gateway       = Column(String(20), nullable=False)
    gateway_transaction_id = Column(String(100), nullable=True, index=True)
    gateway_response      = Column(JSON, default=dict)
    amount                = Column(Float, nullable=False)
    currency              = Column(String(3), default="CNY")
    fee                   = Column(Float, default=0.0)
    net_amount            = Column(Float, nullable=False)
    status                = Column(String(20), default=PaymentStatus.PENDING.value, index=True)
    error_message         = Column(Text, nullable=True)
    error_code            = Column(String(50), nullable=True)
    refunded_amount       = Column(Float, default=0.0)
    refund_status         = Column(String(20), nullable=True)
    extra_metadata        = Column("payment_metadata", JSON, default=dict)
    created_at            = Column(DateTime, default=_naive(_now()), index=True)
    updated_at            = Column(DateTime, default=_naive(_now()))
    paid_at               = Column(DateTime, nullable=True)
    refunded_at           = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("idx_ms_payment_order", "order_id", "status"),
    )


class SubscriptionModel(Base):
    __tablename__ = "ms_subscriptions"
    id                     = Column(Integer, primary_key=True, autoincrement=True)
    subscription_id        = Column(String(64), unique=True, nullable=False, index=True)
    order_id               = Column(String(64), nullable=False, index=True)
    product_id             = Column(String(64), nullable=False, index=True)
    plan_id                = Column(String(64), nullable=False, index=True)
    user_id                = Column(String(64), nullable=False, index=True)
    company_id             = Column(String(64), nullable=True, index=True)
    billing_cycle          = Column(String(20), nullable=False)
    amount                 = Column(Float, nullable=False)
    currency               = Column(String(3), default="CNY")
    quantity               = Column(Integer, default=1)
    status                 = Column(String(20), default=SubscriptionStatus.ACTIVE.value, index=True)
    cancel_at_period_end   = Column(Boolean, default=False)
    current_period_start   = Column(DateTime, nullable=False)
    current_period_end     = Column(DateTime, nullable=False, index=True)
    trial_start            = Column(DateTime, nullable=True)
    trial_end              = Column(DateTime, nullable=True)
    canceled_at            = Column(DateTime, nullable=True)
    ended_at               = Column(DateTime, nullable=True)
    default_payment_method = Column(String(20), nullable=True)
    extra_metadata         = Column("sub_metadata", JSON, default=dict)
    created_at             = Column(DateTime, default=_naive(_now()), index=True)
    updated_at             = Column(DateTime, default=_naive(_now()))

    __table_args__ = (
        Index("idx_ms_sub_user_status", "user_id", "status"),
        Index("idx_ms_sub_period_end",  "current_period_end", "status"),
    )


class InvoiceModel(Base):
    __tablename__ = "ms_invoices"
    id              = Column(Integer, primary_key=True, autoincrement=True)
    invoice_id      = Column(String(64), unique=True, nullable=False, index=True)
    invoice_number  = Column(String(50), unique=True, nullable=False, index=True)
    order_id        = Column(String(64), nullable=True, index=True)
    subscription_id = Column(String(64), nullable=True, index=True)
    user_id         = Column(String(64), nullable=False, index=True)
    company_id      = Column(String(64), nullable=True, index=True)
    invoice_type    = Column(String(20), nullable=False)
    title           = Column(String(200), nullable=False)
    tax_number      = Column(String(50), nullable=True)
    amount          = Column(Float, nullable=False)
    tax_amount      = Column(Float, default=0.0)
    total_amount    = Column(Float, nullable=False)
    currency        = Column(String(3), default="CNY")
    status          = Column(String(20), default=InvoiceStatus.PENDING.value, index=True)
    pdf_path        = Column(String(500), nullable=True)
    email           = Column(String(255), nullable=True)
    address         = Column(String(500), nullable=True)
    extra_metadata  = Column("invoice_metadata", JSON, default=dict)
    created_at      = Column(DateTime, default=_naive(_now()), index=True)
    updated_at      = Column(DateTime, default=_naive(_now()))
    issued_at       = Column(DateTime, nullable=True)
    sent_at         = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("idx_ms_invoice_user", "user_id", "status"),
    )


class APIUsageModel(Base):
    __tablename__ = "ms_api_usages"
    id                  = Column(Integer, primary_key=True, autoincrement=True)
    usage_id            = Column(String(64), unique=True, nullable=False, index=True)
    order_id            = Column(String(64), nullable=True, index=True)
    subscription_id     = Column(String(64), nullable=True, index=True)
    user_id             = Column(String(64), nullable=False, index=True)
    company_id          = Column(String(64), nullable=True, index=True)
    api_endpoint        = Column(String(200), nullable=False, index=True)
    api_version         = Column(String(20), nullable=True)
    request_id          = Column(String(100), nullable=True, index=True)
    request_count       = Column(Integer, default=1)
    data_volume_mb      = Column(Float, default=0.0)
    processing_time_ms  = Column(Integer, default=0)
    unit_price          = Column(Float, nullable=True)
    amount              = Column(Float, default=0.0)
    currency            = Column(String(3), default="CNY")
    is_billed           = Column(Boolean, default=False, index=True)
    extra_metadata      = Column("usage_metadata", JSON, default=dict)
    recorded_at         = Column(DateTime, nullable=False, index=True)
    created_at          = Column(DateTime, default=_naive(_now()))

    __table_args__ = (
        Index("idx_ms_usage_user_time",  "user_id", "recorded_at"),
        Index("idx_ms_usage_billed",     "is_billed", "recorded_at"),
    )


class RefundModel(Base):
    __tablename__ = "ms_refunds"
    id                  = Column(Integer, primary_key=True, autoincrement=True)
    refund_id           = Column(String(64), unique=True, nullable=False, index=True)
    payment_id          = Column(String(64), nullable=False, index=True)
    order_id            = Column(String(64), nullable=False, index=True)
    amount              = Column(Float, nullable=False)
    currency            = Column(String(3), default="CNY")
    reason              = Column(String(500), default="")
    status              = Column(String(20), default=RefundStatus.PENDING.value, index=True)
    gateway_refund_id   = Column(String(100), nullable=True)
    gateway_response    = Column(JSON, default=dict)
    extra_metadata      = Column("refund_metadata", JSON, default=dict)
    created_at          = Column(DateTime, default=_naive(_now()), index=True)
    updated_at          = Column(DateTime, default=_naive(_now()))
    processed_at        = Column(DateTime, nullable=True)
    completed_at        = Column(DateTime, nullable=True)


class RevenueRecognitionModel(Base):
    __tablename__ = "ms_revenue_recognitions"
    id                  = Column(Integer, primary_key=True, autoincrement=True)
    recognition_id      = Column(String(64), unique=True, nullable=False, index=True)
    order_id            = Column(String(64), nullable=False, index=True)
    subscription_id     = Column(String(64), nullable=True, index=True)
    recognition_date    = Column(Date, nullable=False, index=True)
    amount              = Column(Float, nullable=False)
    recognized_amount   = Column(Float, nullable=False)
    deferred_amount     = Column(Float, nullable=False)
    currency            = Column(String(3), default="CNY")
    period_start        = Column(Date, nullable=False)
    period_end          = Column(Date, nullable=False)
    period_days         = Column(Integer, nullable=False)
    revenue_account     = Column(String(50), nullable=False)
    deferred_account    = Column(String(50), nullable=False)
    revenue_type        = Column(String(30), nullable=False)
    is_reversed         = Column(Boolean, default=False)
    reversal_id         = Column(String(64), nullable=True)
    extra_metadata      = Column("rev_metadata", JSON, default=dict)
    created_at          = Column(DateTime, default=_naive(_now()))

    __table_args__ = (
        Index("idx_ms_rev_order_date",    "order_id", "recognition_date"),
        Index("idx_ms_rev_period_start",  "period_start", "revenue_account"),
    )


class CouponModel(Base):
    __tablename__ = "ms_coupons"
    id              = Column(Integer, primary_key=True, autoincrement=True)
    coupon_id       = Column(String(64), unique=True, nullable=False, index=True)
    code            = Column(String(50), unique=True, nullable=False, index=True)
    discount_type   = Column(String(20), nullable=False)
    value           = Column(Float, nullable=False)
    min_amount      = Column(Float, default=0.0)
    max_discount    = Column(Float, nullable=True)
    product_types   = Column(JSON, default=list)
    expires_at      = Column(DateTime, nullable=True)
    max_uses        = Column(Integer, nullable=True)
    used_count      = Column(Integer, default=0)
    is_active       = Column(Boolean, default=True, index=True)
    extra_metadata  = Column("coupon_metadata", JSON, default=dict)
    created_at      = Column(DateTime, default=_naive(_now()))


def init_db():
    Base.metadata.create_all(bind=engine)
    logger.info("Monetization DB tables created")


# ══════════════════════════════════════════════════════════════════════════════
# REDIS MANAGER
# ══════════════════════════════════════════════════════════════════════════════

class RedisManager:
    def __init__(self, url: str):
        self._url = url
        self._client: Optional[Any] = None
        self._mock: Dict[str, Tuple[str, float]] = {}

    async def connect(self):
        if _HAS_REDIS:
            try:
                self._client = aioredis.from_url(self._url, decode_responses=True)
                await self._client.ping()
                logger.info("Redis connected")
            except Exception as e:
                logger.warning(f"Redis unavailable: {e}")
                self._client = None

    async def get(self, key: str) -> Optional[str]:
        if self._client:
            try: return await self._client.get(key)
            except Exception: pass
        entry = self._mock.get(key)
        if entry:
            val, exp = entry
            if exp == 0 or exp > asyncio.get_event_loop().time():
                return val
            del self._mock[key]
        return None

    async def set(self, key: str, value: str, ex: int = 0):
        if self._client:
            try:
                if ex: await self._client.setex(key, ex, value)
                else:  await self._client.set(key, value)
                return
            except Exception: pass
        loop_t = asyncio.get_event_loop().time()
        self._mock[key] = (value, loop_t + ex if ex else 0)

    async def incr(self, key: str) -> int:
        if self._client:
            try: return await self._client.incr(key)
            except Exception: pass
        entry = self._mock.get(key)
        val = int(entry[0]) + 1 if entry else 1
        self._mock[key] = (str(val), 0)
        return val

    async def close(self):
        if self._client:
            await self._client.aclose()


# ══════════════════════════════════════════════════════════════════════════════
# PRICING ENGINE
# ══════════════════════════════════════════════════════════════════════════════

class PricingEngine:
    """Compute prices for all product types."""

    B2B_PLANS: Dict[str, Dict[str, float]] = {
        "b2b_saas_starter":      {"monthly": 999,  "quarterly": 2699,  "yearly": 9999},
        "b2b_saas_professional": {"monthly": 2999, "quarterly": 8099,  "yearly": 29999},
        "b2b_saas_enterprise":   {"monthly": 9999, "quarterly": 26999, "yearly": 99999},
        "b2b_api_free":          {"monthly": 0,    "quarterly": 0,     "yearly": 0},
        "b2b_api_basic":         {"monthly": 99,   "quarterly": 269,   "yearly": 999},
        "b2b_api_pro":           {"monthly": 899,  "quarterly": 2429,  "yearly": 8999},
        "b2b_api_enterprise":    {"monthly": 7999, "quarterly": 21599, "yearly": 79999},
    }

    DATA_BASE_PRICES: Dict[str, float] = {
        "data_api":     0.05,   # per 1k records
        "data_report":  299.0,  # per report
        "data_insight": 999.0,  # per insight package
    }

    def __init__(self, cfg: ServiceConfig):
        self.cfg = cfg

    def calculate_c2c_price(
        self,
        product_type: str,
        billing_cycle: str = "one_time",
        quantity: int = 1,
    ) -> Dict[str, Any]:
        if product_type == ProductType.C2C_SINGLE:
            # Tiered pricing
            if quantity <= 10:
                unit = self.cfg.c2c_single_price
            elif quantity <= 50:
                unit = self.cfg.c2c_single_price * 0.9
            else:
                unit = self.cfg.c2c_single_price * 0.8
            subtotal = round(unit * quantity, 2)
        elif product_type == ProductType.C2C_SUBSCRIPTION:
            unit_map = {
                "monthly":   self.cfg.c2c_monthly_price,
                "quarterly": self.cfg.c2c_quarterly_price,
                "yearly":    self.cfg.c2c_yearly_price,
                "one_time":  self.cfg.c2c_monthly_price,
            }
            unit = unit_map.get(billing_cycle, self.cfg.c2c_monthly_price)
            subtotal = round(unit * quantity, 2)
        else:
            subtotal = round(self.cfg.c2c_single_price * quantity, 2)
            unit = self.cfg.c2c_single_price

        return {
            "unit_price":   round(unit, 2),
            "quantity":     quantity,
            "subtotal":     subtotal,
            "total_amount": subtotal,
            "currency":     "CNY",
        }

    def calculate_b2b_price(
        self,
        product_type: str,
        plan_id: str,
        billing_cycle: str = "monthly",
        quantity: int = 1,
        db: Optional[Session] = None,
    ) -> Dict[str, Any]:
        # Try DB plan first
        if db:
            plan = db.query(PricingPlanModel).filter_by(plan_id=plan_id, is_active=True).first()
            if plan:
                subtotal = round(plan.amount * quantity, 2)
                return {
                    "plan_id":      plan_id,
                    "plan_name":    plan.name,
                    "unit_price":   plan.amount,
                    "quantity":     quantity,
                    "subtotal":     subtotal,
                    "total_amount": subtotal,
                    "currency":     plan.currency,
                }
        # Fallback to hardcoded
        plan_prices = self.B2B_PLANS.get(plan_id, {})
        unit = plan_prices.get(billing_cycle, plan_prices.get("monthly", 999.0))
        subtotal = round(unit * quantity, 2)
        return {
            "plan_id":      plan_id,
            "unit_price":   unit,
            "quantity":     quantity,
            "subtotal":     subtotal,
            "total_amount": subtotal,
            "currency":     "CNY",
        }

    def calculate_api_price(
        self,
        request_count: int,
        data_volume_mb: float = 0.0,
        plan_id: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> Dict[str, Any]:
        unit = self.cfg.b2b_api_unit_price
        if db and plan_id:
            plan = db.query(PricingPlanModel).filter_by(plan_id=plan_id, is_active=True).first()
            if plan and plan.price_tiers:
                unit = self._resolve_tier(request_count, plan.price_tiers)
        amount = round(request_count * unit, 4)
        # Add data volume charge: 0.001 CNY / MB
        data_charge = round(data_volume_mb * 0.001, 4)
        total = round(amount + data_charge, 4)
        return {
            "request_count":  request_count,
            "unit_price":     unit,
            "request_charge": amount,
            "data_charge":    data_charge,
            "total_amount":   total,
            "currency":       "CNY",
        }

    def calculate_data_price(
        self,
        product_type: str,
        data_volume: float = 0.0,
        data_complexity: str = "standard",
        delivery_format: str = "api",
    ) -> Dict[str, Any]:
        base = self.DATA_BASE_PRICES.get(product_type, 99.0)
        complexity_multiplier = {"standard": 1.0, "advanced": 1.5, "premium": 2.5}.get(data_complexity, 1.0)
        format_multiplier     = {"api": 1.0, "csv": 0.8, "json": 0.9, "excel": 1.1}.get(delivery_format, 1.0)

        if product_type == ProductType.DATA_API and data_volume > 0:
            amount = round(data_volume / 1000 * base * complexity_multiplier * format_multiplier, 2)
        else:
            amount = round(base * complexity_multiplier * format_multiplier, 2)

        return {
            "base_price":       base,
            "complexity_mult":  complexity_multiplier,
            "format_mult":      format_multiplier,
            "total_amount":     max(amount, 1.0),
            "currency":         "CNY",
        }

    def apply_coupon(self, amount: float, coupon: CouponModel, product_type: str) -> Tuple[float, float]:
        """Returns (final_amount, discount_amount)."""
        if not coupon.is_active:
            return amount, 0.0
        if coupon.expires_at:
            exp = _utc(coupon.expires_at)
            if exp and exp < _now():
                return amount, 0.0
        if coupon.min_amount > 0 and amount < coupon.min_amount:
            return amount, 0.0
        if coupon.product_types and product_type not in coupon.product_types:
            return amount, 0.0
        if coupon.discount_type == "percentage":
            discount = round(amount * coupon.value / 100, 2)
        else:
            discount = coupon.value
        if coupon.max_discount:
            discount = min(discount, coupon.max_discount)
        discount = min(discount, amount)
        return round(amount - discount, 2), round(discount, 2)

    def _resolve_tier(self, units: int, tiers: List[Dict]) -> float:
        for tier in tiers:
            mn = tier.get("min_units", 0)
            mx = tier.get("max_units")
            if units >= mn and (mx is None or units <= mx):
                return tier.get("unit_price", self.cfg.b2b_api_unit_price)
        return self.cfg.b2b_api_unit_price

    def calculate_tax(self, amount: float, invoice_type: Optional[str] = None) -> float:
        if invoice_type in ("vat", "company"):
            return round(amount * self.cfg.tax_rate, 2)
        return 0.0


# ══════════════════════════════════════════════════════════════════════════════
# BILLING ENGINE
# ══════════════════════════════════════════════════════════════════════════════

class BillingEngine:
    """Handles subscription renewal, dunning, and usage billing."""

    CYCLE_DAYS: Dict[str, int] = {
        "daily":     1,
        "weekly":    7,
        "monthly":   30,
        "quarterly": 90,
        "yearly":    365,
    }

    def __init__(self, cfg: ServiceConfig):
        self.cfg = cfg

    def next_period(self, cycle: str, from_dt: Optional[datetime] = None) -> Tuple[datetime, datetime]:
        start = from_dt or _now()
        days  = self.CYCLE_DAYS.get(cycle, 30)
        end   = start + timedelta(days=days)
        return start, end

    def is_expired(self, sub: SubscriptionModel) -> bool:
        end = _utc(sub.current_period_end)
        if end is None: return False
        return end < _now()

    def is_in_grace(self, sub: SubscriptionModel) -> bool:
        end = _utc(sub.current_period_end)
        if end is None: return False
        grace_until = end + timedelta(days=self.cfg.subscription_grace_days)
        return end < _now() <= grace_until

    def should_renew(self, sub: SubscriptionModel) -> bool:
        if sub.status not in (SubscriptionStatus.ACTIVE.value, SubscriptionStatus.PAST_DUE.value):
            return False
        if sub.cancel_at_period_end:
            return False
        return self.is_expired(sub)

    def process_renewal(self, sub: SubscriptionModel, db: Session) -> Optional[OrderModel]:
        """Create renewal order and advance subscription period."""
        start, end = self.next_period(sub.billing_cycle)
        order_id     = f"order_{uuid.uuid4().hex[:8]}"
        order_number = f"R{datetime.utcnow().strftime('%Y%m%d')}{random.randint(1000,9999)}"

        order = OrderModel(
            order_id        = order_id,
            order_number    = order_number,
            user_id         = sub.user_id,
            user_role       = "b2b_buyer" if sub.company_id else "b2c_consumer",
            company_id      = sub.company_id,
            product_id      = sub.product_id,
            plan_id         = sub.plan_id,
            order_type      = "subscription_renewal",
            quantity        = sub.quantity,
            amount          = sub.amount,
            total_amount    = sub.amount,
            currency        = sub.currency,
            payment_method  = sub.default_payment_method or "alipay",
            payment_status  = PaymentStatus.PENDING.value,
            status          = OrderStatus.PENDING.value,
            subscription_id = sub.subscription_id,
            extra_metadata  = {"renewal": True, "period_start": start.isoformat(), "period_end": end.isoformat()},
            created_at      = _naive(_now()),
            updated_at      = _naive(_now()),
        )
        db.add(order)

        # Advance the period
        sub.current_period_start = _naive(start)
        sub.current_period_end   = _naive(end)
        sub.updated_at           = _naive(_now())
        sub.status               = SubscriptionStatus.ACTIVE.value
        db.commit()
        db.refresh(order)
        return order

    def aggregate_api_usage(self, user_id: str, start: datetime, end: datetime, db: Session) -> Dict[str, Any]:
        rows = db.query(APIUsageModel).filter(
            APIUsageModel.user_id    == user_id,
            APIUsageModel.recorded_at >= _naive(start),
            APIUsageModel.recorded_at <  _naive(end),
            APIUsageModel.is_billed  == False,
        ).all()
        total_requests = sum(r.request_count for r in rows)
        total_data_mb  = sum(r.data_volume_mb for r in rows)
        total_amount   = sum(r.amount for r in rows)
        return {
            "records":        len(rows),
            "total_requests": total_requests,
            "total_data_mb":  round(total_data_mb, 3),
            "total_amount":   round(total_amount, 4),
            "usage_ids":      [r.usage_id for r in rows],
        }

    def mark_usage_billed(self, usage_ids: List[str], db: Session) -> int:
        count = 0
        for uid in usage_ids:
            row = db.query(APIUsageModel).filter_by(usage_id=uid).first()
            if row:
                row.is_billed = True
                count += 1
        db.commit()
        return count


# ══════════════════════════════════════════════════════════════════════════════
# REVENUE RECOGNITION ENGINE
# ══════════════════════════════════════════════════════════════════════════════

class RevenueRecognitionEngine:
    """Implements accrual-basis revenue recognition (IFRS 15 / ASC 606)."""

    def __init__(self, cfg: ServiceConfig):
        self.cfg = cfg

    def recognize(
        self,
        order_id:        str,
        amount:          float,
        period_start:    date,
        period_end:      date,
        revenue_type:    str,
        subscription_id: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> List[RevenueRecognitionModel]:
        """Split revenue across period days (straight-line)."""
        period_days = (period_end - period_start).days or 1
        today = _today()
        elapsed = max(0, (min(today, period_end) - period_start).days)
        recognized = round(amount * elapsed / period_days, 4)
        deferred   = round(amount - recognized, 4)

        rec = RevenueRecognitionModel(
            recognition_id    = f"rev_{uuid.uuid4().hex[:12]}",
            order_id          = order_id,
            subscription_id   = subscription_id,
            recognition_date  = today,
            amount            = amount,
            recognized_amount = recognized,
            deferred_amount   = deferred,
            currency          = "CNY",
            period_start      = period_start,
            period_end        = period_end,
            period_days       = period_days,
            revenue_account   = "recognized_revenue",
            deferred_account  = "deferred_revenue",
            revenue_type      = revenue_type,
            created_at        = _naive(_now()),
        )
        if db:
            db.add(rec)
            db.commit()
        return [rec]

    def get_monthly_summary(self, year: int, month: int, db: Session) -> Dict[str, Any]:
        from calendar import monthrange
        start = date(year, month, 1)
        _, last = monthrange(year, month)
        end = date(year, month, last)
        rows = db.query(RevenueRecognitionModel).filter(
            RevenueRecognitionModel.recognition_date >= start,
            RevenueRecognitionModel.recognition_date <= end,
            RevenueRecognitionModel.is_reversed == False,
        ).all()
        by_type: Dict[str, float] = {}
        total_rec = 0.0
        total_def = 0.0
        for r in rows:
            by_type[r.revenue_type] = by_type.get(r.revenue_type, 0.0) + r.recognized_amount
            total_rec += r.recognized_amount
            total_def += r.deferred_amount
        return {
            "year":            year,
            "month":           month,
            "total_recognized": round(total_rec, 2),
            "total_deferred":   round(total_def, 2),
            "by_type":          {k: round(v, 2) for k, v in by_type.items()},
            "record_count":     len(rows),
        }


# ══════════════════════════════════════════════════════════════════════════════
# PAYMENT GATEWAY STUBS
# ══════════════════════════════════════════════════════════════════════════════

def _gen_stub_qr(url: str) -> str:
    """Generate a base64 QR-like placeholder (or real QR if qrcode available)."""
    if _HAS_QRCODE:
        try:
            qr = qrcode_lib.QRCode(version=1, box_size=6, border=4)
            qr.add_data(url)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
        except Exception:
            pass
    # Tiny 1x1 placeholder
    placeholder = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    return placeholder


class PaymentGateway(ABC):
    @abstractmethod
    def create_payment(self, payment_id: str, order_id: str, amount: float,
                       currency: str, return_url: str, user_id: str) -> Dict[str, Any]:
        ...

    @abstractmethod
    def verify_callback(self, data: Dict[str, Any]) -> Optional[str]:
        """Return payment_id if verified, else None."""
        ...

    @abstractmethod
    def refund(self, gateway_txn_id: str, amount: float, reason: str) -> Dict[str, Any]:
        ...


class AlipayGateway(PaymentGateway):
    def __init__(self, cfg: ServiceConfig):
        self._client = None
        if _HAS_ALIPAY and cfg.alipay_app_id and cfg.alipay_private_key:
            try:
                self._client = _AliPayLib(
                    appid=cfg.alipay_app_id,
                    app_notify_url="",
                    app_private_key_string=cfg.alipay_private_key,
                    alipay_public_key_string=cfg.alipay_public_key,
                    sign_type="RSA2",
                    debug=False,
                )
            except Exception as e:
                logger.warning(f"Alipay init failed: {e}")
        self._base_url = f"http://{cfg.host}:{cfg.port}"

    def create_payment(self, payment_id, order_id, amount, currency, return_url, user_id):
        pay_url = (
            f"https://openapi.alipay.com/gateway.do?out_trade_no={payment_id}&total_amount={amount}"
            if not self._client else
            f"https://openapi.alipay.com/gateway.do?"
            + self._client.api_alipay_trade_page_pay(
                out_trade_no=payment_id,
                total_amount=amount,
                subject="多模态商品识别服务",
                return_url=return_url or f"{self._base_url}/payment/success",
                notify_url=f"{self._base_url}/api/v1/payment/alipay/callback",
            )
        )
        return {
            "payment_url": pay_url,
            "qr_code":     _gen_stub_qr(pay_url),
            "gateway":     "alipay",
            "expires_at":  _fmt_dt(_now() + timedelta(minutes=30)),
        }

    def verify_callback(self, data):
        if not self._client:
            return data.get("out_trade_no")
        try:
            sig = data.pop("sign", None)
            verified = self._client.verify(data, sig)
            return data.get("out_trade_no") if verified else None
        except Exception:
            return None

    def refund(self, gateway_txn_id, amount, reason):
        if not self._client:
            return {"success": True, "gateway": "alipay", "stub": True}
        try:
            result = self._client.api_alipay_trade_refund(
                out_trade_no=gateway_txn_id,
                refund_amount=amount,
                refund_reason=reason,
            )
            return {"success": result.get("code") == "10000", "response": result}
        except Exception as e:
            return {"success": False, "error": str(e)}


class WeChatPayGateway(PaymentGateway):
    def __init__(self, cfg: ServiceConfig):
        self._client = None
        if _HAS_WECHATPAY and cfg.wechat_app_id and cfg.wechat_mch_id:
            try:
                self._client = _WeChatPayLib(appid=cfg.wechat_app_id, mchid=cfg.wechat_mch_id)
            except Exception as e:
                logger.warning(f"WeChatPay init failed: {e}")
        self._base_url = f"http://{cfg.host}:{cfg.port}"

    def create_payment(self, payment_id, order_id, amount, currency, return_url, user_id):
        pay_url = f"weixin://wxpay/bizpayurl?pr={payment_id}"
        return {
            "payment_url": pay_url,
            "qr_code":     _gen_stub_qr(pay_url),
            "gateway":     "wechatpay",
            "expires_at":  _fmt_dt(_now() + timedelta(minutes=30)),
        }

    def verify_callback(self, data):
        return data.get("out_trade_no")

    def refund(self, gateway_txn_id, amount, reason):
        return {"success": True, "gateway": "wechatpay", "stub": True}


class StripeGateway(PaymentGateway):
    def __init__(self, cfg: ServiceConfig):
        self._key = cfg.stripe_secret_key
        self._webhook_secret = cfg.stripe_webhook_secret
        if _HAS_STRIPE and self._key:
            _stripe_lib.api_key = self._key
        self._base_url = f"http://{cfg.host}:{cfg.port}"

    def create_payment(self, payment_id, order_id, amount, currency, return_url, user_id):
        if _HAS_STRIPE and self._key:
            try:
                session = _stripe_lib.checkout.Session.create(
                    payment_method_types=["card"],
                    line_items=[{
                        "price_data": {
                            "currency": currency.lower(),
                            "product_data": {"name": "多模态商品识别服务"},
                            "unit_amount": int(amount * 100),
                        },
                        "quantity": 1,
                    }],
                    mode="payment",
                    success_url=return_url or f"{self._base_url}/payment/success",
                    cancel_url=f"{self._base_url}/payment/cancel",
                    client_reference_id=payment_id,
                )
                return {
                    "payment_url": session.url,
                    "session_id":  session.id,
                    "gateway":     "stripe",
                    "expires_at":  _fmt_dt(_now() + timedelta(hours=24)),
                }
            except Exception as e:
                logger.warning(f"Stripe session creation failed: {e}")
        pay_url = f"https://checkout.stripe.com/pay/stub#{payment_id}"
        return {
            "payment_url": pay_url,
            "gateway":     "stripe",
            "expires_at":  _fmt_dt(_now() + timedelta(hours=24)),
        }

    def verify_callback(self, data):
        return data.get("client_reference_id")

    def refund(self, gateway_txn_id, amount, reason):
        if _HAS_STRIPE and self._key:
            try:
                ref = _stripe_lib.Refund.create(charge=gateway_txn_id, amount=int(amount * 100))
                return {"success": True, "refund_id": ref.id}
            except Exception as e:
                return {"success": False, "error": str(e)}
        return {"success": True, "gateway": "stripe", "stub": True}


class UnionPayGateway(PaymentGateway):
    def create_payment(self, payment_id, order_id, amount, currency, return_url, user_id):
        pay_url = f"https://gateway.95516.com/gateway/api/trans/stub?tn={payment_id}"
        return {"payment_url": pay_url, "gateway": "unionpay", "expires_at": _fmt_dt(_now() + timedelta(minutes=30))}

    def verify_callback(self, data):
        return data.get("orderId")

    def refund(self, gateway_txn_id, amount, reason):
        return {"success": True, "gateway": "unionpay", "stub": True}


_GATEWAYS: Dict[str, Any] = {}  # populated in build_app


def _get_gateway(payment_method: str) -> Optional[PaymentGateway]:
    mapping = {
        "alipay":     "alipay",
        "wechat_pay": "wechatpay",
        "credit_card": "stripe",
        "union_pay":  "unionpay",
    }
    key = mapping.get(payment_method)
    return _GATEWAYS.get(key) if key else None


# ══════════════════════════════════════════════════════════════════════════════
# MONETIZATION SERVICE
# ══════════════════════════════════════════════════════════════════════════════

class MonetizationService:
    """Core business monetization service."""

    STORAGE_DIR = Path(os.getenv("MS_STORAGE_DIR", "./monetization_storage"))
    BASE_URL    = os.getenv("MS_BASE_URL", "http://localhost:8025")

    def __init__(self, cfg: ServiceConfig):
        self.cfg     = cfg
        self.redis   = RedisManager(cfg.redis_url)
        self.pricing = PricingEngine(cfg)
        self.billing = BillingEngine(cfg)
        self.revenue = RevenueRecognitionEngine(cfg)
        self.STORAGE_DIR.mkdir(parents=True, exist_ok=True)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _order_number(self, prefix: str = "C") -> str:
        return f"{prefix}{datetime.utcnow().strftime('%Y%m%d')}{random.randint(10000, 99999)}"

    def _get_product(self, product_type: str, db: Session) -> Optional[ProductModel]:
        return db.query(ProductModel).filter_by(product_type=product_type, is_active=True).first()

    def _get_plan(self, plan_id: str, db: Session) -> Optional[PricingPlanModel]:
        return db.query(PricingPlanModel).filter_by(plan_id=plan_id, is_active=True).first()

    def _create_payment_record(
        self, order_id: str, amount: float, currency: str,
        payment_method: str, db: Session
    ) -> PaymentModel:
        gateway = {
            "alipay":     "alipay",
            "wechat_pay": "wechatpay",
            "credit_card": "stripe",
            "union_pay":  "unionpay",
        }.get(payment_method, "unknown")
        fee = round(amount * self.cfg.payment_fee_rate, 4)
        pay = PaymentModel(
            payment_id      = f"pay_{uuid.uuid4().hex[:12]}",
            order_id        = order_id,
            payment_method  = payment_method,
            payment_gateway = gateway,
            amount          = amount,
            currency        = currency,
            fee             = fee,
            net_amount      = round(amount - fee, 4),
            status          = PaymentStatus.PENDING.value,
            created_at      = _naive(_now()),
            updated_at      = _naive(_now()),
        )
        db.add(pay)
        return pay

    def _make_payment_info(
        self, payment_id: str, order_id: str, amount: float, currency: str,
        payment_method: str, return_url: Optional[str], user_id: str
    ) -> Dict[str, Any]:
        gw = _get_gateway(payment_method)
        if not gw:
            # Stub fallback for any unconfigured method
            pay_url = f"http://pay.stub/{payment_method}/{payment_id}"
            return {
                "payment_id":  payment_id,
                "order_id":    order_id,
                "payment_url": pay_url,
                "qr_code":     _gen_stub_qr(pay_url),
                "amount":      amount,
                "currency":    currency,
                "status":      PaymentStatus.PENDING.value,
                "expires_at":  _fmt_dt(_now() + timedelta(minutes=30)),
                "gateway":     "stub",
            }
        t0 = time.time()
        info = gw.create_payment(
            payment_id  = payment_id,
            order_id    = order_id,
            amount      = amount,
            currency    = currency,
            return_url  = return_url or f"{self.BASE_URL}/payment/success",
            user_id     = user_id,
        )
        gw_name = info.get("gateway", "unknown")
        if PAYMENT_TIME:
            PAYMENT_TIME.labels(gateway=gw_name).observe(time.time() - t0)
        return {
            "payment_id":  payment_id,
            "order_id":    order_id,
            "amount":      amount,
            "currency":    currency,
            "status":      PaymentStatus.PENDING.value,
            **info,
        }

    def _apply_coupon(self, code: str, amount: float, product_type: str, db: Session) -> Tuple[float, float]:
        if not code:
            return amount, 0.0
        coupon = db.query(CouponModel).filter_by(code=code, is_active=True).first()
        if not coupon:
            return amount, 0.0
        final, disc = self.pricing.apply_coupon(amount, coupon, product_type)
        coupon.used_count = (coupon.used_count or 0) + 1
        if coupon.max_uses and coupon.used_count >= coupon.max_uses:
            coupon.is_active = False
        db.commit()
        return final, disc

    # ── C2C ───────────────────────────────────────────────────────────────────

    def create_c2c_order(self, req: CreateOrderRequest, db: Session) -> Dict[str, Any]:
        t0 = time.time()
        product = self._get_product(req.product_type, db)
        if not product:
            raise HTTPException(404, "产品不存在")

        price = self.pricing.calculate_c2c_price(
            product_type  = req.product_type,
            billing_cycle = req.subscription_cycle if req.is_subscription else "one_time",
            quantity      = req.quantity,
        )
        subtotal = price["total_amount"]
        disc_code = req.discount_code or ""
        final_amount, discount = self._apply_coupon(disc_code, subtotal, req.product_type, db)
        tax = self.pricing.calculate_tax(final_amount, req.invoice_info.get("invoice_type") if req.invoice_info else None)
        total = round(final_amount + tax, 2)

        order_id     = f"c2c_{uuid.uuid4().hex[:10]}"
        order_number = self._order_number("C")

        order = OrderModel(
            order_id        = order_id,
            order_number    = order_number,
            user_id         = req.user_id,
            user_role       = req.user_role,
            product_id      = product.product_id,
            plan_id         = req.plan_id,
            order_type      = "subscription" if req.is_subscription else "one_time",
            quantity        = req.quantity,
            amount          = subtotal,
            discount_amount = discount,
            tax_amount      = tax,
            total_amount    = total,
            currency        = req.currency,
            payment_method  = req.payment_method,
            payment_status  = PaymentStatus.PENDING.value,
            status          = OrderStatus.PENDING.value,
            expires_at      = _naive(_now() + timedelta(minutes=30)),
            extra_metadata  = {
                "price_calc":   price,
                "need_invoice": req.need_invoice,
                "invoice_info": req.invoice_info,
                "coupon_code":  disc_code,
            },
            created_at = _naive(_now()),
            updated_at = _naive(_now()),
        )
        db.add(order)
        db.flush()

        if req.is_subscription:
            start, end = self.billing.next_period(req.subscription_cycle)
            sub = SubscriptionModel(
                subscription_id      = f"sub_{uuid.uuid4().hex[:10]}",
                order_id             = order_id,
                product_id           = product.product_id,
                plan_id              = req.plan_id,
                user_id              = req.user_id,
                billing_cycle        = req.subscription_cycle,
                amount               = total,
                currency             = req.currency,
                quantity             = req.quantity,
                status               = SubscriptionStatus.ACTIVE.value,
                current_period_start = _naive(start),
                current_period_end   = _naive(end),
                default_payment_method = req.payment_method,
                extra_metadata       = {"auto_renew": req.auto_renew},
                created_at           = _naive(_now()),
                updated_at           = _naive(_now()),
            )
            db.add(sub)
            db.flush()
            order.subscription_id = sub.subscription_id
            if ACTIVE_SUBSCRIPTIONS:
                ACTIVE_SUBSCRIPTIONS.labels(plan_type="c2c").inc()

        pay = self._create_payment_record(order_id, total, req.currency, req.payment_method, db)
        db.commit()

        pay_info = self._make_payment_info(pay.payment_id, order_id, total, req.currency,
                                           req.payment_method, req.return_url, req.user_id)

        if TRANSACTIONS_TOTAL:
            TRANSACTIONS_TOTAL.labels(product_type=req.product_type, status="created").inc()
        if REQUEST_LATENCY:
            REQUEST_LATENCY.labels(endpoint="create_c2c_order").observe(time.time() - t0)

        return {
            "success":      True,
            "order_id":     order_id,
            "order_number": order_number,
            "payment":      pay_info,
            "amount": {
                "subtotal":  subtotal,
                "discount":  discount,
                "tax":       tax,
                "total":     total,
                "currency":  req.currency,
            },
            "subscription_id": order.subscription_id,
        }

    # ── B2B ───────────────────────────────────────────────────────────────────

    def create_b2b_order(self, req: CreateOrderRequest, db: Session) -> Dict[str, Any]:
        t0 = time.time()
        product = self._get_product(req.product_type, db)
        if not product:
            raise HTTPException(404, "解决方案产品不存在")

        price = self.pricing.calculate_b2b_price(
            product_type  = req.product_type,
            plan_id       = req.plan_id,
            billing_cycle = req.subscription_cycle,
            quantity      = req.quantity,
            db            = db,
        )
        subtotal = price["total_amount"]
        final_amount, discount = self._apply_coupon(req.discount_code or "", subtotal, req.product_type, db)
        tax   = self.pricing.calculate_tax(final_amount, req.invoice_info.get("invoice_type") if req.invoice_info else "company")
        total = round(final_amount + tax, 2)

        order_id     = f"b2b_{uuid.uuid4().hex[:10]}"
        order_number = self._order_number("B")
        company_id   = req.metadata.get("company_id")

        order = OrderModel(
            order_id        = order_id,
            order_number    = order_number,
            user_id         = req.user_id,
            user_role       = req.user_role,
            company_id      = company_id,
            product_id      = product.product_id,
            plan_id         = req.plan_id,
            order_type      = "subscription" if req.is_subscription else "one_time",
            quantity        = req.quantity,
            amount          = subtotal,
            discount_amount = discount,
            tax_amount      = tax,
            total_amount    = total,
            currency        = req.currency,
            payment_method  = req.payment_method,
            payment_status  = PaymentStatus.PENDING.value,
            status          = OrderStatus.PENDING.value,
            expires_at      = _naive(_now() + timedelta(hours=24)),
            extra_metadata  = {
                "price_calc":   price,
                "need_invoice": req.need_invoice,
                "invoice_info": req.invoice_info,
                "company_id":   company_id,
            },
            created_at = _naive(_now()),
            updated_at = _naive(_now()),
        )
        db.add(order)
        db.flush()

        if req.is_subscription:
            start, end = self.billing.next_period(req.subscription_cycle)
            sub = SubscriptionModel(
                subscription_id      = f"sub_{uuid.uuid4().hex[:10]}",
                order_id             = order_id,
                product_id           = product.product_id,
                plan_id              = req.plan_id,
                user_id              = req.user_id,
                company_id           = company_id,
                billing_cycle        = req.subscription_cycle,
                amount               = total,
                currency             = req.currency,
                quantity             = req.quantity,
                status               = SubscriptionStatus.ACTIVE.value,
                current_period_start = _naive(start),
                current_period_end   = _naive(end),
                default_payment_method = req.payment_method,
                extra_metadata       = {"auto_renew": req.auto_renew},
                created_at           = _naive(_now()),
                updated_at           = _naive(_now()),
            )
            db.add(sub)
            db.flush()
            order.subscription_id = sub.subscription_id
            if ACTIVE_SUBSCRIPTIONS:
                ACTIVE_SUBSCRIPTIONS.labels(plan_type="b2b").inc()

        pay = self._create_payment_record(order_id, total, req.currency, req.payment_method, db)
        db.commit()

        # Revenue recognition for subscription
        if req.is_subscription and order.subscription_id:
            start, end = self.billing.next_period(req.subscription_cycle)
            self.revenue.recognize(
                order_id=order_id,
                amount=total,
                period_start=start.date(),
                period_end=end.date(),
                revenue_type=RevenueType.SUBSCRIPTION.value,
                subscription_id=order.subscription_id,
                db=db,
            )

        pay_info = self._make_payment_info(pay.payment_id, order_id, total, req.currency,
                                           req.payment_method, req.return_url, req.user_id)

        if TRANSACTIONS_TOTAL:
            TRANSACTIONS_TOTAL.labels(product_type=req.product_type, status="created").inc()
        if REVENUE_TOTAL:
            REVENUE_TOTAL.labels(revenue_type="b2b").inc()
        if REQUEST_LATENCY:
            REQUEST_LATENCY.labels(endpoint="create_b2b_order").observe(time.time() - t0)

        return {
            "success":       True,
            "order_id":      order_id,
            "order_number":  order_number,
            "payment":       pay_info,
            "amount": {"subtotal": subtotal, "discount": discount, "tax": tax, "total": total, "currency": req.currency},
            "subscription_id": order.subscription_id,
        }

    # ── Data product ──────────────────────────────────────────────────────────

    def create_data_order(self, req: CreateOrderRequest, db: Session) -> Dict[str, Any]:
        product = self._get_product(req.product_type, db)
        if not product:
            raise HTTPException(404, "数据产品不存在")

        price = self.pricing.calculate_data_price(
            product_type    = req.product_type,
            data_volume     = req.metadata.get("data_volume", 0),
            data_complexity = req.metadata.get("data_complexity", "standard"),
            delivery_format = req.metadata.get("delivery_format", "api"),
        )
        total = price["total_amount"]
        order_id     = f"data_{uuid.uuid4().hex[:10]}"
        order_number = self._order_number("D")

        order = OrderModel(
            order_id       = order_id,
            order_number   = order_number,
            user_id        = req.user_id,
            user_role      = req.user_role,
            product_id     = product.product_id,
            order_type     = "one_time",
            quantity       = 1,
            amount         = total,
            total_amount   = total,
            currency       = req.currency,
            payment_method = req.payment_method,
            payment_status = PaymentStatus.PENDING.value,
            status         = OrderStatus.PENDING.value,
            extra_metadata = {"price_calc": price, **req.metadata},
            created_at     = _naive(_now()),
            updated_at     = _naive(_now()),
        )
        db.add(order)
        db.flush()
        pay = self._create_payment_record(order_id, total, req.currency, req.payment_method, db)
        db.commit()

        self.revenue.recognize(
            order_id     = order_id,
            amount       = total,
            period_start = _today(),
            period_end   = _today() + timedelta(days=1),
            revenue_type = RevenueType.DATA_SALE.value,
            db           = db,
        )

        pay_info = self._make_payment_info(pay.payment_id, order_id, total, req.currency,
                                           req.payment_method, req.return_url, req.user_id)
        if REVENUE_TOTAL:
            REVENUE_TOTAL.labels(revenue_type="data_sale").inc()
        return {
            "success":      True,
            "order_id":     order_id,
            "order_number": order_number,
            "payment":      pay_info,
            "amount":       {"total": total, "currency": req.currency},
        }

    # ── API billing ───────────────────────────────────────────────────────────

    def record_api_usage(self, req: APIBillingRequest, db: Session) -> Dict[str, Any]:
        price = self.pricing.calculate_api_price(req.request_count, req.data_volume_mb)
        ts    = req.timestamp or _now()
        sub   = db.query(SubscriptionModel).filter(
            SubscriptionModel.user_id == req.user_id,
            SubscriptionModel.status  == SubscriptionStatus.ACTIVE.value,
            SubscriptionModel.product_id.like("%api%"),
        ).first()
        usage = APIUsageModel(
            usage_id           = f"usg_{uuid.uuid4().hex[:12]}",
            subscription_id    = sub.subscription_id if sub else None,
            user_id            = req.user_id,
            api_endpoint       = req.api_endpoint,
            request_count      = req.request_count,
            data_volume_mb     = req.data_volume_mb,
            processing_time_ms = req.processing_time_ms,
            unit_price         = price["unit_price"],
            amount             = price["total_amount"],
            currency           = "CNY",
            is_billed          = False,
            extra_metadata     = req.metadata,
            recorded_at        = _naive(ts),
            created_at         = _naive(_now()),
        )
        db.add(usage)
        db.commit()
        if API_USAGE_TOTAL:
            API_USAGE_TOTAL.labels(endpoint=req.api_endpoint).inc(req.request_count)
        return {
            "usage_id":      usage.usage_id,
            "request_count": req.request_count,
            "amount":        price["total_amount"],
            "currency":      "CNY",
        }

    def get_api_usage_summary(self, user_id: str, start: datetime, end: datetime, db: Session) -> Dict[str, Any]:
        agg = self.billing.aggregate_api_usage(user_id, start, end, db)
        return {
            "user_id":        user_id,
            "period_start":   _fmt_dt(start),
            "period_end":     _fmt_dt(end),
            **agg,
        }

    # ── Payment callbacks ─────────────────────────────────────────────────────

    def process_payment_callback(self, gateway: str, data: Dict[str, Any], db: Session) -> Dict[str, Any]:
        gw = _GATEWAYS.get(gateway)
        payment_id = gw.verify_callback(data) if gw else data.get("out_trade_no", data.get("payment_id"))
        if not payment_id:
            raise HTTPException(400, "Invalid callback data")

        pay = db.query(PaymentModel).filter_by(payment_id=payment_id).first()
        if not pay:
            raise HTTPException(404, "Payment not found")

        pay.status   = PaymentStatus.SUCCESS.value
        pay.paid_at  = _naive(_now())
        pay.gateway_transaction_id = data.get("transaction_id", data.get("trade_no", ""))
        pay.gateway_response       = data
        pay.updated_at = _naive(_now())

        order = db.query(OrderModel).filter_by(order_id=pay.order_id).first()
        if order:
            order.payment_status = PaymentStatus.SUCCESS.value
            order.paid_amount    = pay.amount
            order.paid_at        = _naive(_now())
            order.status         = OrderStatus.COMPLETED.value
            order.updated_at     = _naive(_now())

        db.commit()
        logger.info(f"Payment {payment_id} confirmed via {gateway}")
        return {"success": True, "payment_id": payment_id, "order_id": pay.order_id}

    # ── Refunds ───────────────────────────────────────────────────────────────

    def create_refund(self, req: RefundRequest, db: Session) -> Dict[str, Any]:
        order = db.query(OrderModel).filter_by(order_id=req.order_id).first()
        if not order:
            raise HTTPException(404, "Order not found")
        if order.payment_status != PaymentStatus.SUCCESS.value:
            raise HTTPException(400, "Order not paid")
        if req.amount > order.paid_amount:
            raise HTTPException(400, f"Refund amount {req.amount} exceeds paid amount {order.paid_amount}")

        pay = db.query(PaymentModel).filter_by(
            order_id=req.order_id, status=PaymentStatus.SUCCESS.value
        ).first()
        if not pay:
            raise HTTPException(404, "Payment record not found")

        gw = _get_gateway(pay.payment_method)
        gw_result = gw.refund(pay.gateway_transaction_id or pay.payment_id, req.amount, req.reason) if gw else {"success": True, "stub": True}

        refund = RefundModel(
            refund_id        = f"ref_{uuid.uuid4().hex[:12]}",
            payment_id       = pay.payment_id,
            order_id         = req.order_id,
            amount           = req.amount,
            currency         = order.currency,
            reason           = req.reason,
            status           = RefundStatus.COMPLETED.value if gw_result.get("success") else RefundStatus.FAILED.value,
            gateway_refund_id = gw_result.get("refund_id", ""),
            gateway_response  = gw_result,
            extra_metadata    = req.metadata,
            processed_at      = _naive(_now()),
            completed_at      = _naive(_now()) if gw_result.get("success") else None,
            created_at        = _naive(_now()),
            updated_at        = _naive(_now()),
        )
        db.add(refund)

        if gw_result.get("success"):
            pay.refunded_amount = (pay.refunded_amount or 0) + req.amount
            pay.refund_status   = RefundStatus.COMPLETED.value
            pay.refunded_at     = _naive(_now())
            if pay.refunded_amount >= pay.amount:
                pay.status       = PaymentStatus.REFUNDED.value
                order.payment_status = PaymentStatus.REFUNDED.value
                order.status         = OrderStatus.REFUNDED.value
            else:
                pay.status = PaymentStatus.PARTIAL_REFUND.value
            pay.updated_at   = _naive(_now())
            order.updated_at = _naive(_now())

        db.commit()
        return {
            "success":   gw_result.get("success", False),
            "refund_id": refund.refund_id,
            "amount":    req.amount,
            "status":    refund.status,
        }

    # ── Invoices ──────────────────────────────────────────────────────────────

    def create_invoice(self, req: InvoiceRequest, db: Session) -> Dict[str, Any]:
        order = db.query(OrderModel).filter_by(order_id=req.order_id).first()
        if not order:
            raise HTTPException(404, "Order not found")

        existing = db.query(InvoiceModel).filter_by(order_id=req.order_id, status=InvoiceStatus.ISSUED.value).first()
        if existing:
            return {"success": True, "invoice_id": existing.invoice_id, "invoice_number": existing.invoice_number, "already_issued": True}

        tax   = self.pricing.calculate_tax(order.total_amount, req.invoice_type)
        total = round(order.total_amount + tax, 2)
        inv_number = f"INV{datetime.utcnow().strftime('%Y%m')}{random.randint(100000, 999999)}"

        inv = InvoiceModel(
            invoice_id     = f"inv_{uuid.uuid4().hex[:12]}",
            invoice_number = inv_number,
            order_id       = req.order_id,
            user_id        = order.user_id,
            company_id     = order.company_id,
            invoice_type   = req.invoice_type,
            title          = req.title,
            tax_number     = req.tax_number,
            amount         = order.total_amount,
            tax_amount     = tax,
            total_amount   = total,
            currency       = order.currency,
            status         = InvoiceStatus.ISSUED.value,
            email          = req.email,
            address        = req.address,
            extra_metadata = req.metadata,
            issued_at      = _naive(_now()),
            created_at     = _naive(_now()),
            updated_at     = _naive(_now()),
        )
        db.add(inv)
        order.invoice_id = inv.invoice_id
        order.updated_at = _naive(_now())
        db.commit()

        return {
            "success":        True,
            "invoice_id":     inv.invoice_id,
            "invoice_number": inv.invoice_number,
            "amount":         inv.amount,
            "tax_amount":     inv.tax_amount,
            "total_amount":   inv.total_amount,
            "status":         inv.status,
            "issued_at":      _fmt_dt(inv.issued_at),
        }

    # ── Subscriptions ─────────────────────────────────────────────────────────

    def cancel_subscription(self, subscription_id: str, at_period_end: bool, db: Session) -> Dict[str, Any]:
        sub = db.query(SubscriptionModel).filter_by(subscription_id=subscription_id).first()
        if not sub:
            raise HTTPException(404, "Subscription not found")
        if sub.status in (SubscriptionStatus.CANCELLED.value, SubscriptionStatus.EXPIRED.value):
            raise HTTPException(400, "Subscription already cancelled")

        if at_period_end:
            sub.cancel_at_period_end = True
        else:
            sub.status      = SubscriptionStatus.CANCELLED.value
            sub.canceled_at = _naive(_now())
            sub.ended_at    = _naive(_now())
            if ACTIVE_SUBSCRIPTIONS:
                ACTIVE_SUBSCRIPTIONS.labels(plan_type="sub").dec()
        sub.updated_at = _naive(_now())
        db.commit()
        return {
            "success":          True,
            "subscription_id":  subscription_id,
            "cancel_at_end":    sub.cancel_at_period_end,
            "status":           sub.status,
        }

    def get_subscription(self, subscription_id: str, db: Session) -> Dict[str, Any]:
        sub = db.query(SubscriptionModel).filter_by(subscription_id=subscription_id).first()
        if not sub:
            raise HTTPException(404, "Subscription not found")
        return {
            "subscription_id":      sub.subscription_id,
            "plan_id":              sub.plan_id,
            "product_id":           sub.product_id,
            "user_id":              sub.user_id,
            "billing_cycle":        sub.billing_cycle,
            "amount":               sub.amount,
            "currency":             sub.currency,
            "status":               sub.status,
            "cancel_at_period_end": sub.cancel_at_period_end,
            "current_period_start": _fmt_dt(_utc(sub.current_period_start)),
            "current_period_end":   _fmt_dt(_utc(sub.current_period_end)),
            "created_at":           _fmt_dt(_utc(sub.created_at)),
        }

    # ── Reports & Stats ───────────────────────────────────────────────────────

    def get_revenue_stats(self, user_id: Optional[str], start: datetime, end: datetime, db: Session) -> Dict[str, Any]:
        q = db.query(OrderModel).filter(
            OrderModel.created_at >= _naive(start),
            OrderModel.created_at <  _naive(end),
            OrderModel.payment_status == PaymentStatus.SUCCESS.value,
        )
        if user_id:
            q = q.filter(OrderModel.user_id == user_id)
        orders = q.all()

        total_rev    = sum(o.total_amount for o in orders)
        by_type: Dict[str, float] = {}
        by_method: Dict[str, float] = {}
        for o in orders:
            by_type[o.order_type] = by_type.get(o.order_type, 0.0) + o.total_amount
            by_method[o.payment_method] = by_method.get(o.payment_method, 0.0) + o.total_amount

        active_subs = db.query(SubscriptionModel).filter_by(status=SubscriptionStatus.ACTIVE.value).count()
        total_api   = db.query(APIUsageModel).filter(
            APIUsageModel.recorded_at >= _naive(start),
            APIUsageModel.recorded_at <  _naive(end),
        ).count()

        return {
            "period_start":       _fmt_dt(start),
            "period_end":         _fmt_dt(end),
            "total_revenue":      round(total_rev, 2),
            "order_count":        len(orders),
            "by_order_type":      {k: round(v, 2) for k, v in by_type.items()},
            "by_payment_method":  {k: round(v, 2) for k, v in by_method.items()},
            "active_subscriptions": active_subs,
            "api_calls":          total_api,
        }

    def get_billing_report(self, year: int, month: int, db: Session) -> Dict[str, Any]:
        rev_summary = self.revenue.get_monthly_summary(year, month, db)
        from calendar import monthrange
        _, last = monthrange(year, month)
        start = datetime(year, month, 1, tzinfo=timezone.utc)
        end   = datetime(year, month, last, 23, 59, 59, tzinfo=timezone.utc)
        stats = self.get_revenue_stats(None, start, end, db)
        return {
            "report_id":       f"rpt_{year}{month:02d}",
            "period":          f"{year}-{month:02d}",
            "revenue":         stats,
            "recognition":     rev_summary,
            "generated_at":    _fmt_dt(_now()),
        }

    def list_orders(self, user_id: Optional[str], status: Optional[str],
                    product_type: Optional[str], page: int, page_size: int, db: Session) -> Tuple[List[OrderModel], int]:
        q = db.query(OrderModel)
        if user_id:
            q = q.filter(OrderModel.user_id == user_id)
        if status:
            q = q.filter(OrderModel.status == status)
        if product_type:
            prods = db.query(ProductModel.product_id).filter(ProductModel.product_type == product_type).all()
            pids  = [p.product_id for p in prods]
            q = q.filter(OrderModel.product_id.in_(pids))
        total = q.count()
        rows  = q.order_by(OrderModel.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
        return rows, total

    def get_stats(self, db: Session) -> Dict[str, Any]:
        total_orders   = db.query(OrderModel).count()
        paid_orders    = db.query(OrderModel).filter_by(payment_status=PaymentStatus.SUCCESS.value).count()
        total_subs     = db.query(SubscriptionModel).filter_by(status=SubscriptionStatus.ACTIVE.value).count()
        total_invoices = db.query(InvoiceModel).count()
        total_refunds  = db.query(RefundModel).filter_by(status=RefundStatus.COMPLETED.value).count()
        total_api_calls= db.query(APIUsageModel).count()
        return {
            "total_orders":        total_orders,
            "paid_orders":         paid_orders,
            "active_subscriptions": total_subs,
            "total_invoices":      total_invoices,
            "completed_refunds":   total_refunds,
            "total_api_calls":     total_api_calls,
        }


# ══════════════════════════════════════════════════════════════════════════════
# FASTAPI APPLICATION
# ══════════════════════════════════════════════════════════════════════════════

_cfg = ServiceConfig()
_svc: Optional[MonetizationService] = None
_redis_mgr: Optional[RedisManager] = None


def get_svc() -> MonetizationService:
    global _svc, _GATEWAYS
    if _svc is None:
        # Lazy init for test environments where startup event may not have fired
        _svc = MonetizationService(_cfg)
        if not _GATEWAYS:
            _GATEWAYS = {
                "alipay":    AlipayGateway(_cfg),
                "wechatpay": WeChatPayGateway(_cfg),
                "stripe":    StripeGateway(_cfg),
                "unionpay":  UnionPayGateway(),
            }
    return _svc


def create_app(cfg: Optional[ServiceConfig] = None) -> FastAPI:
    global _svc, _cfg, _redis_mgr, _GATEWAYS

    app_cfg = cfg or ServiceConfig()
    _cfg    = app_cfg

    app = FastAPI(
        title="ILbuy Monetization Service",
        description="Business monetization: C-end, B-end, data products, billing, invoicing",
        version="1.0.0",
    )

    @app.on_event("startup")
    async def startup():
        global _svc, _redis_mgr, _GATEWAYS
        init_db()
        _redis_mgr = RedisManager(app_cfg.redis_url)
        await _redis_mgr.connect()
        _svc = MonetizationService(app_cfg)
        _svc.redis = _redis_mgr
        _GATEWAYS = {
            "alipay":    AlipayGateway(app_cfg),
            "wechatpay": WeChatPayGateway(app_cfg),
            "stripe":    StripeGateway(app_cfg),
            "unionpay":  UnionPayGateway(),
        }
        seed_data()
        asyncio.create_task(_task_recurring_billing())
        asyncio.create_task(_task_expire_orders())
        logger.info(f"Monetization Service started port={app_cfg.port}")

    @app.on_event("shutdown")
    async def shutdown():
        if _redis_mgr:
            await _redis_mgr.close()

    # ── Health ────────────────────────────────────────────────────────────────
    @app.get("/health")
    async def health():
        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
            db_ok = True
        except Exception:
            db_ok = False
        finally:
            db.close()
        return {
            "status":       "ok" if db_ok else "degraded",
            "service":      "monetization-service",
            "db":           "ok" if db_ok else "error",
            "has_stripe":   _HAS_STRIPE,
            "has_alipay":   _HAS_ALIPAY,
            "has_wechat":   _HAS_WECHATPAY,
            "timestamp":    _fmt_dt(_now()),
        }

    @app.get("/metrics")
    async def metrics():
        if not _HAS_PROMETHEUS:
            raise HTTPException(501, "Prometheus not available")
        from fastapi.responses import Response
        return Response(generate_latest(_MS_REGISTRY), media_type=CONTENT_TYPE_LATEST)

    # ── C2C Orders ────────────────────────────────────────────────────────────
    @app.post("/api/v1/orders/c2c")
    async def create_c2c_order(req: CreateOrderRequest, db: Session = Depends(get_db)):
        return get_svc().create_c2c_order(req, db)

    @app.post("/api/v1/orders/b2b")
    async def create_b2b_order(req: CreateOrderRequest, db: Session = Depends(get_db)):
        return get_svc().create_b2b_order(req, db)

    @app.post("/api/v1/orders/data")
    async def create_data_order(req: CreateOrderRequest, db: Session = Depends(get_db)):
        return get_svc().create_data_order(req, db)

    @app.get("/api/v1/orders")
    async def list_orders(
        user_id:      Optional[str] = None,
        status:       Optional[str] = None,
        product_type: Optional[str] = None,
        page:         int = Query(default=1, ge=1),
        page_size:    int = Query(default=20, ge=1, le=100),
        db: Session = Depends(get_db),
    ):
        rows, total = get_svc().list_orders(user_id, status, product_type, page, page_size, db)
        items = [
            {
                "order_id":      r.order_id,
                "order_number":  r.order_number,
                "user_id":       r.user_id,
                "product_id":    r.product_id,
                "order_type":    r.order_type,
                "total_amount":  r.total_amount,
                "currency":      r.currency,
                "payment_status": r.payment_status,
                "status":        r.status,
                "created_at":    _fmt_dt(_utc(r.created_at)),
            }
            for r in rows
        ]
        return {
            "items":     items,
            "total":     total,
            "page":      page,
            "page_size": page_size,
            "pages":     math.ceil(total / page_size) if page_size else 1,
        }

    @app.get("/api/v1/orders/{order_id}")
    async def get_order(order_id: str, db: Session = Depends(get_db)):
        order = db.query(OrderModel).filter_by(order_id=order_id).first()
        if not order:
            raise HTTPException(404, "Order not found")
        return {
            "order_id":       order.order_id,
            "order_number":   order.order_number,
            "user_id":        order.user_id,
            "product_id":     order.product_id,
            "plan_id":        order.plan_id,
            "order_type":     order.order_type,
            "quantity":       order.quantity,
            "amount":         order.amount,
            "discount_amount": order.discount_amount,
            "tax_amount":     order.tax_amount,
            "total_amount":   order.total_amount,
            "currency":       order.currency,
            "payment_method": order.payment_method,
            "payment_status": order.payment_status,
            "status":         order.status,
            "subscription_id": order.subscription_id,
            "created_at":     _fmt_dt(_utc(order.created_at)),
            "paid_at":        _fmt_dt(_utc(order.paid_at)),
        }

    # ── Payment ───────────────────────────────────────────────────────────────
    @app.post("/api/v1/payment/{gateway}/callback")
    async def payment_callback(gateway: str, data: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
        return get_svc().process_payment_callback(gateway, data, db)

    @app.post("/api/v1/payment/mock-confirm/{payment_id}")
    async def mock_confirm_payment(payment_id: str, db: Session = Depends(get_db)):
        """Dev-only: directly mark a payment as successful."""
        return get_svc().process_payment_callback("mock", {"out_trade_no": payment_id, "trade_no": f"mock_{uuid.uuid4().hex[:8]}"}, db)

    # ── Refunds ───────────────────────────────────────────────────────────────
    @app.post("/api/v1/refunds")
    async def create_refund(req: RefundRequest, db: Session = Depends(get_db)):
        return get_svc().create_refund(req, db)

    @app.get("/api/v1/refunds/{order_id}")
    async def list_refunds(order_id: str, db: Session = Depends(get_db)):
        refunds = db.query(RefundModel).filter_by(order_id=order_id).all()
        return {
            "order_id": order_id,
            "refunds": [
                {
                    "refund_id": r.refund_id,
                    "amount":    r.amount,
                    "reason":    r.reason,
                    "status":    r.status,
                    "created_at": _fmt_dt(_utc(r.created_at)),
                }
                for r in refunds
            ],
        }

    # ── Invoices ──────────────────────────────────────────────────────────────
    @app.post("/api/v1/invoices")
    async def create_invoice(req: InvoiceRequest, db: Session = Depends(get_db)):
        return get_svc().create_invoice(req, db)

    @app.get("/api/v1/invoices/{user_id}")
    async def list_invoices(
        user_id:  str,
        status:   Optional[str] = None,
        page:     int = Query(default=1, ge=1),
        page_size: int = Query(default=20, ge=1, le=100),
        db: Session = Depends(get_db),
    ):
        q = db.query(InvoiceModel).filter_by(user_id=user_id)
        if status:
            q = q.filter_by(status=status)
        total = q.count()
        rows  = q.order_by(InvoiceModel.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
        return {
            "items": [
                {
                    "invoice_id":     r.invoice_id,
                    "invoice_number": r.invoice_number,
                    "order_id":       r.order_id,
                    "title":          r.title,
                    "total_amount":   r.total_amount,
                    "status":         r.status,
                    "issued_at":      _fmt_dt(_utc(r.issued_at)),
                }
                for r in rows
            ],
            "total":     total,
            "page":      page,
            "page_size": page_size,
        }

    # ── Subscriptions ─────────────────────────────────────────────────────────
    @app.get("/api/v1/subscriptions/{subscription_id}")
    async def get_subscription(subscription_id: str, db: Session = Depends(get_db)):
        return get_svc().get_subscription(subscription_id, db)

    @app.get("/api/v1/subscriptions")
    async def list_subscriptions(
        user_id:  Optional[str] = None,
        status:   Optional[str] = None,
        page:     int = Query(default=1, ge=1),
        page_size: int = Query(default=20, ge=1, le=100),
        db: Session = Depends(get_db),
    ):
        q = db.query(SubscriptionModel)
        if user_id: q = q.filter_by(user_id=user_id)
        if status:  q = q.filter_by(status=status)
        total = q.count()
        rows  = q.order_by(SubscriptionModel.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
        return {
            "items": [get_svc().get_subscription(r.subscription_id, db) for r in rows],
            "total": total, "page": page, "page_size": page_size,
        }

    @app.post("/api/v1/subscriptions/{subscription_id}/cancel")
    async def cancel_subscription(
        subscription_id: str,
        at_period_end:   bool = Query(default=True),
        db: Session = Depends(get_db),
    ):
        return get_svc().cancel_subscription(subscription_id, at_period_end, db)

    # ── API Billing ───────────────────────────────────────────────────────────
    @app.post("/api/v1/api-billing/record")
    async def record_api_usage(req: APIBillingRequest, db: Session = Depends(get_db)):
        return get_svc().record_api_usage(req, db)

    @app.get("/api/v1/api-billing/summary/{user_id}")
    async def api_usage_summary(
        user_id:    str,
        start_date: str = Query(default=""),
        end_date:   str = Query(default=""),
        db: Session = Depends(get_db),
    ):
        now  = _now()
        start = datetime.fromisoformat(start_date) if start_date else now.replace(day=1, hour=0, minute=0, second=0)
        end   = datetime.fromisoformat(end_date)   if end_date   else now
        return get_svc().get_api_usage_summary(user_id, start, end, db)

    # ── Pricing plans ─────────────────────────────────────────────────────────
    @app.get("/api/v1/products")
    async def list_products(product_type: Optional[str] = None, db: Session = Depends(get_db)):
        q = db.query(ProductModel).filter_by(is_active=True, is_public=True)
        if product_type:
            q = q.filter_by(product_type=product_type)
        products = q.all()
        return {
            "products": [
                {
                    "product_id":   p.product_id,
                    "name":         p.name,
                    "description":  p.description,
                    "product_type": p.product_type,
                    "pricing_model": p.pricing_model,
                    "base_price":   p.base_price,
                    "unit_price":   p.unit_price,
                    "currency":     p.currency,
                    "features":     p.features,
                }
                for p in products
            ]
        }

    @app.get("/api/v1/pricing-plans")
    async def list_pricing_plans(product_id: Optional[str] = None, db: Session = Depends(get_db)):
        q = db.query(PricingPlanModel).filter_by(is_active=True)
        if product_id:
            q = q.filter_by(product_id=product_id)
        plans = q.order_by(PricingPlanModel.display_order).all()
        return {
            "plans": [
                {
                    "plan_id":       p.plan_id,
                    "product_id":    p.product_id,
                    "name":          p.name,
                    "billing_cycle": p.billing_cycle,
                    "amount":        p.amount,
                    "currency":      p.currency,
                    "trial_days":    p.trial_days,
                    "features":      p.features,
                    "limits":        p.limits,
                }
                for p in plans
            ]
        }

    @app.post("/api/v1/pricing-plans")
    async def create_pricing_plan(req: PricingPlanRequest, db: Session = Depends(get_db)):
        plan = PricingPlanModel(
            plan_id       = f"plan_{uuid.uuid4().hex[:12]}",
            product_id    = req.product_id,
            name          = req.name,
            description   = req.description,
            billing_cycle = req.billing_cycle if isinstance(req.billing_cycle, str) else req.billing_cycle.value,
            amount        = req.amount,
            currency      = req.currency,
            trial_days    = req.trial_days,
            features      = req.features,
            limits        = req.limits,
            price_tiers   = [t.model_dump() for t in req.price_tiers] if req.price_tiers else None,
            is_default    = req.is_default,
            is_active     = True,
            created_at    = _naive(_now()),
            updated_at    = _naive(_now()),
        )
        db.add(plan)
        db.commit()
        db.refresh(plan)
        return {"success": True, "plan_id": plan.plan_id, "name": plan.name}

    # ── Coupons ───────────────────────────────────────────────────────────────
    @app.post("/api/v1/coupons")
    async def create_coupon(req: CouponRequest, db: Session = Depends(get_db)):
        existing = db.query(CouponModel).filter_by(code=req.code).first()
        if existing:
            raise HTTPException(409, "Coupon code already exists")
        coupon = CouponModel(
            coupon_id     = f"cpn_{uuid.uuid4().hex[:12]}",
            code          = req.code,
            discount_type = req.discount_type,
            value         = req.value,
            min_amount    = req.min_amount,
            max_discount  = req.max_discount,
            product_types = req.product_types,
            expires_at    = _naive(req.expires_at) if req.expires_at else None,
            max_uses      = req.max_uses,
            is_active     = True,
            created_at    = _naive(_now()),
        )
        db.add(coupon)
        db.commit()
        return {"success": True, "coupon_id": coupon.coupon_id, "code": coupon.code}

    @app.get("/api/v1/coupons/validate/{code}")
    async def validate_coupon(code: str, amount: float = Query(default=0), db: Session = Depends(get_db)):
        coupon = db.query(CouponModel).filter_by(code=code, is_active=True).first()
        if not coupon:
            return {"valid": False, "reason": "Coupon not found or inactive"}
        if coupon.expires_at and _utc(coupon.expires_at) < _now():
            return {"valid": False, "reason": "Coupon expired"}
        if coupon.max_uses and coupon.used_count >= coupon.max_uses:
            return {"valid": False, "reason": "Coupon max uses reached"}
        if amount and coupon.min_amount > 0 and amount < coupon.min_amount:
            return {"valid": False, "reason": f"Minimum amount {coupon.min_amount} required"}
        discount = (amount * coupon.value / 100 if coupon.discount_type == "percentage" else coupon.value)
        if coupon.max_discount:
            discount = min(discount, coupon.max_discount)
        return {
            "valid":         True,
            "coupon_id":     coupon.coupon_id,
            "discount_type": coupon.discount_type,
            "discount_amount": round(min(discount, amount), 2),
            "remaining_uses": (coupon.max_uses - coupon.used_count) if coupon.max_uses else None,
        }

    # ── Revenue recognition ───────────────────────────────────────────────────
    @app.get("/api/v1/revenue/monthly")
    async def monthly_revenue(
        year:  int = Query(default=_now().year),
        month: int = Query(default=_now().month),
        db: Session = Depends(get_db),
    ):
        return get_svc().revenue.get_monthly_summary(year, month, db)

    @app.get("/api/v1/revenue/stats")
    async def revenue_stats(
        user_id:    Optional[str] = None,
        start_date: str = Query(default=""),
        end_date:   str = Query(default=""),
        db: Session = Depends(get_db),
    ):
        now   = _now()
        start = datetime.fromisoformat(start_date) if start_date else now - timedelta(days=30)
        end   = datetime.fromisoformat(end_date)   if end_date   else now
        return get_svc().get_revenue_stats(user_id, start, end, db)

    @app.get("/api/v1/billing/report")
    async def billing_report(
        year:  int = Query(default=_now().year),
        month: int = Query(default=_now().month),
        db: Session = Depends(get_db),
    ):
        return get_svc().get_billing_report(year, month, db)

    # ── Stats ─────────────────────────────────────────────────────────────────
    @app.get("/api/v1/stats")
    async def overall_stats(db: Session = Depends(get_db)):
        return get_svc().get_stats(db)

    return app


app = create_app()


# ══════════════════════════════════════════════════════════════════════════════
# SEED DATA
# ══════════════════════════════════════════════════════════════════════════════

_SEED_DONE = False

def seed_data():
    global _SEED_DONE
    if _SEED_DONE:
        return
    _SEED_DONE = True
    db = SessionLocal()
    try:
        if db.query(ProductModel).count() > 0:
            return

        products = [
            ProductModel(
                product_id   = "prod_c2c_single",
                name         = "C端单次决策服务",
                description  = "为个人消费者提供单次商品决策分析，包含比价与购买建议",
                product_type = ProductType.C2C_SINGLE.value,
                category     = "c2c",
                pricing_model= "tiered",
                currency     = "CNY",
                base_price   = 9.9,
                features     = ["商品分析", "比价建议", "购买建议", "7天报告有效期"],
                limitations  = {"valid_days": 7, "max_products": 1},
                is_active=True, is_public=True, created_at=_naive(_now()), updated_at=_naive(_now()),
            ),
            ProductModel(
                product_id   = "prod_c2c_sub",
                name         = "C端高级会员",
                description  = "个人消费者订阅会员服务，无限次分析",
                product_type = ProductType.C2C_SUBSCRIPTION.value,
                category     = "c2c",
                pricing_model= "fixed",
                currency     = "CNY",
                base_price   = 29.9,
                features     = ["无限次分析", "高级报告", "优先客服", "多设备登录"],
                limitations  = {"max_devices": 3},
                is_active=True, is_public=True, created_at=_naive(_now()), updated_at=_naive(_now()),
            ),
            ProductModel(
                product_id   = "prod_b2b_saas",
                name         = "B端SaaS服务",
                description  = "企业级SaaS采购决策平台",
                product_type = ProductType.B2B_SAAS.value,
                category     = "b2b",
                pricing_model= "tiered",
                currency     = "CNY",
                base_price   = 999.0,
                features     = ["团队协作", "API访问", "高级报表", "专属客服"],
                limitations  = {"max_users": 5, "api_calls_per_month": 10000},
                is_active=True, is_public=True, created_at=_naive(_now()), updated_at=_naive(_now()),
            ),
            ProductModel(
                product_id   = "prod_b2b_api",
                name         = "B端API服务",
                description  = "企业API调用服务，按量计费",
                product_type = ProductType.B2B_API.value,
                category     = "b2b",
                pricing_model= "usage",
                currency     = "CNY",
                unit_price   = 0.01,
                features     = ["商品识别API", "价格分析API", "数据查询API", "99.9% SLA"],
                limitations  = {"rate_limit": "100req/min"},
                is_active=True, is_public=True, created_at=_naive(_now()), updated_at=_naive(_now()),
            ),
            ProductModel(
                product_id   = "prod_data_api",
                name         = "数据API服务",
                description  = "结构化商品数据API，支持批量查询",
                product_type = ProductType.DATA_API.value,
                category     = "data",
                pricing_model= "usage",
                currency     = "CNY",
                unit_price   = 0.05,
                features     = ["商品数据", "价格历史", "供应商数据", "实时更新"],
                limitations  = {},
                is_active=True, is_public=True, created_at=_naive(_now()), updated_at=_naive(_now()),
            ),
            ProductModel(
                product_id   = "prod_data_report",
                name         = "数据洞察报告",
                description  = "按需定制行业数据报告",
                product_type = ProductType.DATA_REPORT.value,
                category     = "data",
                pricing_model= "fixed",
                currency     = "CNY",
                base_price   = 299.0,
                features     = ["行业分析", "竞品对比", "趋势预测", "PDF交付"],
                limitations  = {},
                is_active=True, is_public=True, created_at=_naive(_now()), updated_at=_naive(_now()),
            ),
        ]
        for p in products:
            db.add(p)
        db.flush()

        plans = [
            # C2C sub plans
            PricingPlanModel(plan_id="plan_c2c_monthly",   product_id="prod_c2c_sub", name="月付会员",   billing_cycle="monthly",   amount=29.9,  currency="CNY", trial_days=7,  features=["无限次分析","高级报告"], is_active=True, is_default=True, display_order=1, created_at=_naive(_now()), updated_at=_naive(_now())),
            PricingPlanModel(plan_id="plan_c2c_quarterly", product_id="prod_c2c_sub", name="季付会员",   billing_cycle="quarterly",  amount=79.9,  currency="CNY", trial_days=0,  features=["无限次分析","高级报告","88折优惠"], is_active=True, display_order=2, created_at=_naive(_now()), updated_at=_naive(_now())),
            PricingPlanModel(plan_id="plan_c2c_yearly",    product_id="prod_c2c_sub", name="年付会员",   billing_cycle="yearly",     amount=299.9, currency="CNY", trial_days=0,  features=["无限次分析","高级报告","83折优惠","专属客服"], is_active=True, display_order=3, created_at=_naive(_now()), updated_at=_naive(_now())),
            # B2B SaaS plans
            PricingPlanModel(plan_id="b2b_saas_starter",      product_id="prod_b2b_saas", name="入门版", billing_cycle="monthly", amount=999,  currency="CNY", features=["5用户","10GB存储","10k API/月"], limits={"max_users":5,"max_storage_gb":10,"api_calls_per_month":10000}, is_active=True, is_default=True, display_order=1, created_at=_naive(_now()), updated_at=_naive(_now())),
            PricingPlanModel(plan_id="b2b_saas_professional", product_id="prod_b2b_saas", name="专业版", billing_cycle="monthly", amount=2999, currency="CNY", features=["20用户","100GB存储","100k API/月"], limits={"max_users":20,"max_storage_gb":100,"api_calls_per_month":100000}, is_active=True, display_order=2, created_at=_naive(_now()), updated_at=_naive(_now())),
            PricingPlanModel(plan_id="b2b_saas_enterprise",   product_id="prod_b2b_saas", name="企业版", billing_cycle="monthly", amount=9999, currency="CNY", features=["无限用户","无限存储","无限API","专属部署"], limits={}, is_active=True, display_order=3, created_at=_naive(_now()), updated_at=_naive(_now())),
            # B2B API plans
            PricingPlanModel(plan_id="b2b_api_free",       product_id="prod_b2b_api", name="免费版",   billing_cycle="monthly", amount=0,    currency="CNY", features=["1000次/月"], limits={"requests_per_month":1000}, is_active=True, is_default=True, display_order=1, created_at=_naive(_now()), updated_at=_naive(_now())),
            PricingPlanModel(plan_id="b2b_api_basic",      product_id="prod_b2b_api", name="基础版",   billing_cycle="monthly", amount=99,   currency="CNY", features=["10k次/月"],  limits={"requests_per_month":10000}, is_active=True, display_order=2, created_at=_naive(_now()), updated_at=_naive(_now())),
            PricingPlanModel(plan_id="b2b_api_pro",        product_id="prod_b2b_api", name="专业版",   billing_cycle="monthly", amount=899,  currency="CNY", features=["100k次/月"], limits={"requests_per_month":100000}, is_active=True, display_order=3, created_at=_naive(_now()), updated_at=_naive(_now())),
            PricingPlanModel(plan_id="b2b_api_enterprise", product_id="prod_b2b_api", name="企业版",   billing_cycle="monthly", amount=7999, currency="CNY", features=["1M次/月"],   limits={"requests_per_month":1000000}, is_active=True, display_order=4, created_at=_naive(_now()), updated_at=_naive(_now())),
        ]
        for p in plans:
            db.add(p)

        # Seed demo coupons
        coupons = [
            CouponModel(coupon_id="cpn_welcome10", code="WELCOME10", discount_type="percentage", value=10, min_amount=0, max_uses=1000, is_active=True, created_at=_naive(_now())),
            CouponModel(coupon_id="cpn_first5",    code="FIRST5",    discount_type="fixed",      value=5,  min_amount=0, max_uses=500,  is_active=True, created_at=_naive(_now())),
            CouponModel(coupon_id="cpn_b2b20",     code="B2B20",     discount_type="percentage", value=20, min_amount=500, max_discount=500, product_types=["b2b_saas","b2b_api"], max_uses=100, is_active=True, created_at=_naive(_now())),
        ]
        for c in coupons:
            db.add(c)

        db.commit()
        logger.info(f"Seeded {len(products)} products, {len(plans)} plans, {len(coupons)} coupons")
    except Exception as e:
        logger.warning(f"Seed data failed: {e}")
        db.rollback()
    finally:
        db.close()


# ══════════════════════════════════════════════════════════════════════════════
# BACKGROUND TASKS
# ══════════════════════════════════════════════════════════════════════════════

async def _task_recurring_billing():
    """Process subscription renewals and API usage billing every hour."""
    while True:
        try:
            await asyncio.sleep(3600)
            db = SessionLocal()
            try:
                subs = db.query(SubscriptionModel).filter(
                    SubscriptionModel.status.in_([SubscriptionStatus.ACTIVE.value, SubscriptionStatus.PAST_DUE.value])
                ).all()
                renewed = 0
                for sub in subs:
                    svc = _svc
                    if svc and svc.billing.should_renew(sub):
                        try:
                            svc.billing.process_renewal(sub, db)
                            renewed += 1
                        except Exception as e:
                            logger.error(f"Renewal failed for {sub.subscription_id}: {e}")
                if renewed:
                    logger.info(f"Renewed {renewed} subscriptions")

                # Mark unbilled API usage older than 24h
                cutoff = _now() - timedelta(hours=24)
                old_usage = db.query(APIUsageModel).filter(
                    APIUsageModel.recorded_at <= _naive(cutoff),
                    APIUsageModel.is_billed   == False,
                ).all()
                for u in old_usage:
                    u.is_billed = True
                if old_usage:
                    db.commit()
                    logger.info(f"Auto-billed {len(old_usage)} API usage records")
            finally:
                db.close()
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Recurring billing task error: {e}")
            await asyncio.sleep(300)


async def _task_expire_orders():
    """Expire pending orders older than 2 hours, cancel expired subscriptions every 30 min."""
    while True:
        try:
            await asyncio.sleep(1800)
            db = SessionLocal()
            try:
                cutoff = _naive(_now() - timedelta(hours=2))
                expired_orders = db.query(OrderModel).filter(
                    OrderModel.status         == OrderStatus.PENDING.value,
                    OrderModel.payment_status == PaymentStatus.PENDING.value,
                    OrderModel.created_at     <= cutoff,
                ).all()
                for o in expired_orders:
                    o.status     = OrderStatus.EXPIRED.value
                    o.updated_at = _naive(_now())
                if expired_orders:
                    db.commit()
                    logger.info(f"Expired {len(expired_orders)} pending orders")

                # Expire past-due subscriptions beyond grace period
                grace_cutoff = _naive(_now() - timedelta(days=_cfg.subscription_grace_days))
                grace_subs = db.query(SubscriptionModel).filter(
                    SubscriptionModel.status              == SubscriptionStatus.PAST_DUE.value,
                    SubscriptionModel.current_period_end  <= grace_cutoff,
                ).all()
                for s in grace_subs:
                    s.status     = SubscriptionStatus.EXPIRED.value
                    s.ended_at   = _naive(_now())
                    s.updated_at = _naive(_now())
                if grace_subs:
                    db.commit()
                    logger.info(f"Expired {len(grace_subs)} past-due subscriptions")
            finally:
                db.close()
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Expire orders task error: {e}")
            await asyncio.sleep(120)


# ══════════════════════════════════════════════════════════════════════════════
# ENTRYPOINT
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("MS_PORT", "8025"))
    uvicorn.run("monetization_service:app", host="0.0.0.0", port=port, reload=False)
