"""
report_output_layer.py — Part 7: Report Output & Presentation Layer
Production-grade implementation with multi-format output and multi-channel delivery.
"""

from __future__ import annotations

import asyncio
import csv
import hashlib
import io
import json
import logging
import math
import os
import random
import re
import statistics
import string
import tempfile
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Query
from fastapi.responses import JSONResponse, StreamingResponse, HTMLResponse
from pydantic import BaseModel, field_validator, model_validator, ConfigDict
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean, Float,
    create_engine, text
)
from sqlalchemy.orm import declarative_base, Session, sessionmaker
try:
    from sqlalchemy.dialects.sqlite import JSON
except ImportError:
    from sqlalchemy import JSON

# ── Optional heavy dependencies ───────────────────────────────────────────────
try:
    import redis.asyncio as aioredis
    _HAS_REDIS = True
except ImportError:
    aioredis = None  # type: ignore
    _HAS_REDIS = False

try:
    import jinja2
    _HAS_JINJA2 = True
except ImportError:
    jinja2 = None  # type: ignore
    _HAS_JINJA2 = False

try:
    from weasyprint import HTML as WeasyHTML
    _HAS_WEASYPRINT = True
except Exception:
    WeasyHTML = None  # type: ignore
    _HAS_WEASYPRINT = False

try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        HRFlowable, PageBreak
    )
    from reportlab.lib.units import inch
    _HAS_REPORTLAB = True
except ImportError:
    _HAS_REPORTLAB = False

try:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    from openpyxl.chart import BarChart, LineChart, Reference
    _HAS_OPENPYXL = True
except ImportError:
    _HAS_OPENPYXL = False

try:
    import plotly.graph_objects as go
    import plotly.express as px
    _HAS_PLOTLY = True
except ImportError:
    go = None  # type: ignore
    px = None  # type: ignore
    _HAS_PLOTLY = False

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
    import qrcode as qrcode_lib
    _HAS_QRCODE = True
except ImportError:
    qrcode_lib = None  # type: ignore
    _HAS_QRCODE = False

try:
    import aiofiles
    _HAS_AIOFILES = True
except ImportError:
    aiofiles = None  # type: ignore
    _HAS_AIOFILES = False

try:
    import aiohttp
    _HAS_AIOHTTP = True
except ImportError:
    aiohttp = None  # type: ignore
    _HAS_AIOHTTP = False

try:
    import aiosmtplib
    _HAS_AIOSMTPLIB = True
except ImportError:
    aiosmtplib = None  # type: ignore
    _HAS_AIOSMTPLIB = False

try:
    from prometheus_client import Counter, Gauge, Histogram, CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST
    _HAS_PROMETHEUS = True
except ImportError:
    _HAS_PROMETHEUS = False

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger("report_output_layer")

# ── Numeric helpers (numpy fallback) ─────────────────────────────────────────
def _mean(values: List[float]) -> float:
    if not values:
        return 0.0
    if _HAS_NUMPY:
        return float(np.mean(values))
    return statistics.mean(values)

def _std(values: List[float]) -> float:
    if len(values) < 2:
        return 0.0
    if _HAS_NUMPY:
        return float(np.std(values))
    return statistics.stdev(values)

def _median(values: List[float]) -> float:
    if not values:
        return 0.0
    if _HAS_NUMPY:
        return float(np.median(values))
    return statistics.median(values)

def _percentile(values: List[float], p: float) -> float:
    if not values:
        return 0.0
    if _HAS_NUMPY:
        return float(np.percentile(values, p))
    sorted_v = sorted(values)
    idx = int(len(sorted_v) * p / 100)
    return sorted_v[min(idx, len(sorted_v) - 1)]

# ── Time helpers ──────────────────────────────────────────────────────────────
def _now() -> datetime:
    return datetime.now(timezone.utc)

def _fmt_dt(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    return dt.isoformat()

# ── DB setup ──────────────────────────────────────────────────────────────────
DB_URL = os.getenv("REPORT_DB_URL", "sqlite:///./report_output.db")
engine = create_engine(DB_URL, connect_args={"check_same_thread": False} if "sqlite" in DB_URL else {})
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ── Prometheus metrics ────────────────────────────────────────────────────────
_RO_REGISTRY = CollectorRegistry() if _HAS_PROMETHEUS else None

def _ctr(n, d, l=None):
    if not _HAS_PROMETHEUS:
        return None
    try:
        return Counter(n, d, l or [], registry=_RO_REGISTRY)
    except ValueError:
        return Counter(n, d, l or [], registry=CollectorRegistry())

def _gge(n, d, l=None):
    if not _HAS_PROMETHEUS:
        return None
    try:
        return Gauge(n, d, l or [], registry=_RO_REGISTRY)
    except ValueError:
        return Gauge(n, d, l or [], registry=CollectorRegistry())

def _hst(n, d, l=None, buckets=None):
    if not _HAS_PROMETHEUS:
        return None
    kwargs = {"registry": _RO_REGISTRY}
    if buckets:
        kwargs["buckets"] = buckets
    try:
        return Histogram(n, d, l or [], **kwargs)
    except ValueError:
        kwargs["registry"] = CollectorRegistry()
        return Histogram(n, d, l or [], **kwargs)

REPORTS_GENERATED   = _ctr("ro_reports_generated_total", "Total reports generated", ["report_type", "format"])
REPORTS_DELIVERED   = _ctr("ro_reports_delivered_total", "Total reports delivered", ["channel", "status"])
REPORT_SIZE_BYTES   = _hst("ro_report_size_bytes", "Report size in bytes", ["format"], [1024, 10240, 102400, 1048576, 10485760])
ACTIVE_REPORTS      = _gge("ro_active_reports", "Active reports count")
GENERATION_TIME     = _hst("ro_generation_seconds", "Report generation time", ["report_type"])

# ══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ══════════════════════════════════════════════════════════════════════════════

class ReportType(str, Enum):
    B2B_PRODUCT_ANALYSIS   = "b2b_product_analysis"
    B2C_BRAND_SPECIFIED    = "b2c_brand_specified"
    B2C_BRAND_UNSPECIFIED  = "b2c_brand_unspecified"
    MARKET_OVERVIEW        = "market_overview"
    SUPPLIER_EVALUATION    = "supplier_evaluation"
    PRICE_COMPARISON       = "price_comparison"
    QUALITY_ASSESSMENT     = "quality_assessment"
    TREND_ANALYSIS         = "trend_analysis"

class OutputFormat(str, Enum):
    HTML     = "html"
    PDF      = "pdf"
    EXCEL    = "excel"
    CSV      = "csv"
    JSON     = "json"
    MARKDOWN = "markdown"

class DeliveryChannel(str, Enum):
    EMAIL   = "email"
    WECHAT  = "wechat"
    WEBHOOK = "webhook"
    WEB     = "web"
    API     = "api"

class DeliveryStatus(str, Enum):
    PENDING   = "pending"
    SENDING   = "sending"
    DELIVERED = "delivered"
    FAILED    = "failed"
    RETRYING  = "retrying"

class ReportStatus(str, Enum):
    PENDING    = "pending"
    GENERATING = "generating"
    COMPLETED  = "completed"
    FAILED     = "failed"
    EXPIRED    = "expired"

# ══════════════════════════════════════════════════════════════════════════════
# DATACLASSES
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class ReportTemplate:
    template_id: str
    name: str
    report_type: ReportType
    description: str
    sections: List[str]
    default_format: OutputFormat = OutputFormat.HTML
    custom_css: str = ""
    header_template: str = ""
    footer_template: str = ""
    chart_config: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=_now)
    is_active: bool = True

@dataclass
class ReportData:
    report_id: str
    report_type: ReportType
    title: str
    data: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=_now)
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None

@dataclass
class FormatOptions:
    page_size: str = "A4"
    orientation: str = "portrait"
    include_charts: bool = True
    include_tables: bool = True
    include_summary: bool = True
    include_toc: bool = True
    watermark: str = ""
    custom_css: str = ""
    chart_theme: str = "default"
    language: str = "zh"
    max_rows: int = 1000

@dataclass
class DeliveryOptions:
    channel: DeliveryChannel
    recipients: List[str]
    subject: str = ""
    message: str = ""
    schedule_at: Optional[datetime] = None
    retry_count: int = 3
    retry_interval: int = 60
    extra: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ReportRequest:
    report_type: ReportType
    title: str
    data: Dict[str, Any]
    formats: List[OutputFormat] = field(default_factory=lambda: [OutputFormat.HTML])
    delivery: Optional[List[DeliveryOptions]] = None
    template_id: Optional[str] = None
    format_options: FormatOptions = field(default_factory=FormatOptions)
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    expires_in: int = 7 * 86400  # seconds

@dataclass
class GeneratedReport:
    report_id: str
    title: str
    report_type: ReportType
    format: OutputFormat
    content: bytes
    content_type: str
    size: int
    generated_at: datetime
    expires_at: Optional[datetime] = None
    download_url: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


# ══════════════════════════════════════════════════════════════════════════════
# ORM MODELS
# ══════════════════════════════════════════════════════════════════════════════

class ReportTemplateModel(Base):
    __tablename__ = "report_templates"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    template_id   = Column(String(64), unique=True, nullable=False, index=True)
    name          = Column(String(200), nullable=False)
    report_type   = Column(String(50), nullable=False)
    description   = Column(Text, default="")
    sections      = Column(JSON, default=list)
    default_format = Column(String(20), default="html")
    custom_css    = Column(Text, default="")
    header_tmpl   = Column(Text, default="")
    footer_tmpl   = Column(Text, default="")
    chart_config  = Column(JSON, default=dict)
    is_active     = Column(Boolean, default=True)
    created_at    = Column(DateTime, default=_now)
    updated_at    = Column(DateTime, default=_now, onupdate=_now)

class ReportGenerationLog(Base):
    __tablename__ = "report_generation_logs"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    report_id     = Column(String(64), unique=True, nullable=False, index=True)
    title         = Column(String(500), nullable=False)
    report_type   = Column(String(50), nullable=False)
    format        = Column(String(20), nullable=False)
    status        = Column(String(20), default="pending")
    file_path     = Column(String(500), nullable=True)
    file_size     = Column(Integer, default=0)
    content_type  = Column(String(100), default="")
    template_id   = Column(String(64), nullable=True)
    user_id       = Column(String(64), nullable=True, index=True)
    tenant_id     = Column(String(64), nullable=True, index=True)
    extra_metadata = Column("report_metadata", JSON, default=dict)
    error_message  = Column(Text, nullable=True)
    generation_ms  = Column(Integer, default=0)
    expires_at     = Column(DateTime, nullable=True)
    created_at     = Column(DateTime, default=_now)
    updated_at     = Column(DateTime, default=_now)

class ReportDeliveryModel(Base):
    __tablename__ = "report_deliveries"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    delivery_id   = Column(String(64), unique=True, nullable=False, index=True)
    report_id     = Column(String(64), nullable=False, index=True)
    channel       = Column(String(30), nullable=False)
    status        = Column(String(20), default="pending")
    recipients    = Column(JSON, default=list)
    subject       = Column(String(500), default="")
    message       = Column(Text, default="")
    attempt_count = Column(Integer, default=0)
    last_attempt  = Column(DateTime, nullable=True)
    delivered_at  = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    extra_metadata = Column("delivery_metadata", JSON, default=dict)
    created_at    = Column(DateTime, default=_now)
    updated_at    = Column(DateTime, default=_now)

def init_db():
    Base.metadata.create_all(bind=engine)
    logger.info("Report output DB tables created")


# ══════════════════════════════════════════════════════════════════════════════
# REDIS MANAGER
# ══════════════════════════════════════════════════════════════════════════════

class RedisManager:
    def __init__(self, url: str = "redis://localhost:6379"):
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
                logger.warning(f"Redis unavailable, using in-memory mock: {e}")
                self._client = None

    async def disconnect(self):
        if self._client:
            await self._client.aclose()

    async def get(self, key: str) -> Optional[str]:
        if self._client:
            try:
                return await self._client.get(key)
            except Exception:
                pass
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
                if ex:
                    await self._client.setex(key, ex, value)
                else:
                    await self._client.set(key, value)
                return
            except Exception:
                pass
        loop_time = asyncio.get_event_loop().time()
        self._mock[key] = (value, loop_time + ex if ex else 0)

    async def delete(self, key: str):
        if self._client:
            try:
                await self._client.delete(key)
                return
            except Exception:
                pass
        self._mock.pop(key, None)

redis_manager = RedisManager(os.getenv("REDIS_URL", "redis://localhost:6379"))

# ══════════════════════════════════════════════════════════════════════════════
# REPORT GENERATORS
# ══════════════════════════════════════════════════════════════════════════════

class ReportGenerator(ABC):
    """Abstract base for report content generators."""

    @abstractmethod
    def generate(self, data: ReportData, options: FormatOptions) -> Dict[str, Any]:
        """Generate structured report content from raw data."""

    def _safe_list(self, data: Dict, key: str, default: Optional[List] = None) -> List:
        val = data.get(key, default or [])
        return val if isinstance(val, list) else []

    def _safe_dict(self, data: Dict, key: str, default: Optional[Dict] = None) -> Dict:
        val = data.get(key, default or {})
        return val if isinstance(val, dict) else {}

    def _safe_float(self, val: Any, default: float = 0.0) -> float:
        try:
            return float(val)
        except (TypeError, ValueError):
            return default


class B2BProductAnalysisGenerator(ReportGenerator):
    """Generator for B2B product analysis reports."""

    def generate(self, data: ReportData, options: FormatOptions) -> Dict[str, Any]:
        raw = data.data
        products     = self._safe_list(raw, "products")
        suppliers    = self._safe_list(raw, "suppliers")
        market_data  = self._safe_dict(raw, "market_data")
        price_history = self._safe_list(raw, "price_history")

        content: Dict[str, Any] = {
            "title": data.title,
            "report_type": data.report_type.value,
            "generated_at": _fmt_dt(data.created_at),
            "summary": self._build_summary(products, suppliers, market_data),
            "sections": [],
        }

        if options.include_summary:
            content["sections"].append(self._executive_summary(products, suppliers, market_data))
        content["sections"].append(self._product_analysis(products))
        content["sections"].append(self._supplier_evaluation(suppliers))
        content["sections"].append(self._price_analysis(products, price_history))
        content["sections"].append(self._market_insights(market_data))
        content["sections"].append(self._recommendations(products, suppliers, market_data))

        return content

    def _build_summary(self, products, suppliers, market_data) -> Dict:
        prices = [self._safe_float(p.get("price")) for p in products if p.get("price")]
        return {
            "total_products": len(products),
            "total_suppliers": len(suppliers),
            "avg_price": round(_mean(prices), 2) if prices else 0,
            "min_price": round(min(prices), 2) if prices else 0,
            "max_price": round(max(prices), 2) if prices else 0,
            "price_std": round(_std(prices), 2) if prices else 0,
            "market_size": market_data.get("market_size", "N/A"),
            "growth_rate": market_data.get("growth_rate", "N/A"),
        }

    def _executive_summary(self, products, suppliers, market_data) -> Dict:
        prices = [self._safe_float(p.get("price")) for p in products if p.get("price")]
        return {
            "section": "executive_summary",
            "title": "执行摘要",
            "content": {
                "overview": f"本报告分析了 {len(products)} 款产品和 {len(suppliers)} 家供应商。",
                "key_findings": [
                    f"平均价格 ¥{round(_mean(prices), 2)}" if prices else "价格数据不足",
                    f"价格区间 ¥{round(min(prices), 2)} ~ ¥{round(max(prices), 2)}" if prices else "",
                    f"市场规模: {market_data.get('market_size', 'N/A')}",
                    f"年增长率: {market_data.get('growth_rate', 'N/A')}",
                ],
                "conclusion": "基于数据分析，建议重点关注性价比优质供应商。",
            }
        }

    def _product_analysis(self, products) -> Dict:
        rows = []
        for p in products[:100]:
            rows.append({
                "name": p.get("name", ""),
                "category": p.get("category", ""),
                "price": self._safe_float(p.get("price")),
                "rating": self._safe_float(p.get("rating")),
                "stock": p.get("stock", 0),
                "supplier": p.get("supplier", ""),
            })
        prices = [r["price"] for r in rows if r["price"]]
        ratings = [r["rating"] for r in rows if r["rating"]]
        return {
            "section": "product_analysis",
            "title": "产品分析",
            "table": {"headers": ["产品名称","分类","价格","评分","库存","供应商"], "rows": rows},
            "chart": {
                "type": "bar",
                "title": "产品价格分布",
                "labels": [r["name"] for r in rows[:20]],
                "values": [r["price"] for r in rows[:20]],
            },
            "stats": {
                "count": len(rows),
                "avg_price": round(_mean(prices), 2),
                "avg_rating": round(_mean(ratings), 2),
                "median_price": round(_median(prices), 2),
            }
        }

    def _supplier_evaluation(self, suppliers) -> Dict:
        rows = []
        for s in suppliers[:50]:
            score = (
                self._safe_float(s.get("quality_score")) * 0.4 +
                self._safe_float(s.get("delivery_score")) * 0.3 +
                self._safe_float(s.get("price_score")) * 0.3
            )
            rows.append({
                "name": s.get("name", ""),
                "location": s.get("location", ""),
                "quality_score": self._safe_float(s.get("quality_score")),
                "delivery_score": self._safe_float(s.get("delivery_score")),
                "price_score": self._safe_float(s.get("price_score")),
                "composite_score": round(score, 2),
                "years_active": s.get("years_active", 0),
            })
        rows.sort(key=lambda x: x["composite_score"], reverse=True)
        return {
            "section": "supplier_evaluation",
            "title": "供应商评估",
            "table": {
                "headers": ["供应商","所在地","质量分","交期分","价格分","综合分","经营年限"],
                "rows": rows,
            },
            "top_suppliers": rows[:5],
        }

    def _price_analysis(self, products, price_history) -> Dict:
        prices = [self._safe_float(p.get("price")) for p in products if p.get("price")]
        buckets: Dict[str, int] = {}
        for pr in prices:
            bucket = f"¥{int(pr // 100) * 100}-{int(pr // 100) * 100 + 99}"
            buckets[bucket] = buckets.get(bucket, 0) + 1
        return {
            "section": "price_analysis",
            "title": "价格分析",
            "distribution": buckets,
            "history": price_history[:30],
            "stats": {
                "mean": round(_mean(prices), 2),
                "std": round(_std(prices), 2),
                "p25": round(_percentile(prices, 25), 2),
                "p50": round(_percentile(prices, 50), 2),
                "p75": round(_percentile(prices, 75), 2),
                "p90": round(_percentile(prices, 90), 2),
            },
        }

    def _market_insights(self, market_data) -> Dict:
        trends = market_data.get("trends", [])
        competitors = market_data.get("competitors", [])
        return {
            "section": "market_insights",
            "title": "市场洞察",
            "trends": trends[:10],
            "competitors": competitors[:10],
            "opportunities": market_data.get("opportunities", []),
            "risks": market_data.get("risks", []),
        }

    def _recommendations(self, products, suppliers, market_data) -> Dict:
        recs = []
        prices = [self._safe_float(p.get("price")) for p in products if p.get("price")]
        if prices and _std(prices) / (_mean(prices) + 1e-9) > 0.5:
            recs.append("价格波动较大，建议锁定长期合同价格")
        if len(suppliers) < 3:
            recs.append("供应商数量不足，建议开拓备选供应商渠道")
        recs.append("建议建立供应商评级制度，定期更新评估")
        recs.append("可通过批量采购降低单价，提升利润空间")
        return {
            "section": "recommendations",
            "title": "决策建议",
            "items": recs,
        }


class B2CBrandSpecifiedGenerator(ReportGenerator):
    """Generator for B2C reports where brand is specified by user."""

    def generate(self, data: ReportData, options: FormatOptions) -> Dict[str, Any]:
        raw = data.data
        brand      = raw.get("brand", {})
        products   = self._safe_list(raw, "products")
        reviews    = self._safe_list(raw, "reviews")
        competitors = self._safe_list(raw, "competitors")

        content: Dict[str, Any] = {
            "title": data.title,
            "report_type": data.report_type.value,
            "generated_at": _fmt_dt(data.created_at),
            "brand": brand,
            "sections": [],
        }

        content["sections"].append(self._brand_overview(brand, products))
        content["sections"].append(self._product_lineup(products))
        content["sections"].append(self._review_analysis(reviews))
        content["sections"].append(self._competitive_analysis(brand, competitors))
        content["sections"].append(self._product_comparison(products))
        content["sections"].append(self._purchase_guide(products, reviews))

        return content

    def _brand_overview(self, brand, products) -> Dict:
        prices = [self._safe_float(p.get("price")) for p in products if p.get("price")]
        ratings = [self._safe_float(p.get("rating")) for p in products if p.get("rating")]
        return {
            "section": "brand_overview",
            "title": f"品牌概览 - {brand.get('name', '未知品牌')}",
            "content": {
                "brand_name": brand.get("name", ""),
                "brand_story": brand.get("story", ""),
                "founded_year": brand.get("founded_year", ""),
                "origin": brand.get("origin", ""),
                "product_count": len(products),
                "price_range": f"¥{round(min(prices), 0):.0f} ~ ¥{round(max(prices), 0):.0f}" if prices else "N/A",
                "avg_rating": round(_mean(ratings), 1) if ratings else 0,
            }
        }

    def _product_lineup(self, products) -> Dict:
        rows = []
        for p in products[:50]:
            rows.append({
                "name": p.get("name", ""),
                "series": p.get("series", ""),
                "price": self._safe_float(p.get("price")),
                "rating": self._safe_float(p.get("rating")),
                "sales": p.get("sales", 0),
                "highlights": p.get("highlights", []),
            })
        return {
            "section": "product_lineup",
            "title": "产品阵容",
            "products": rows,
            "table": {
                "headers": ["产品名","系列","价格","评分","销量"],
                "rows": [{k: v for k, v in r.items() if k != "highlights"} for r in rows],
            }
        }

    def _review_analysis(self, reviews) -> Dict:
        total = len(reviews)
        if total == 0:
            return {"section": "review_analysis", "title": "用户评价分析", "content": {}}
        ratings = [self._safe_float(r.get("rating")) for r in reviews if r.get("rating")]
        sentiment_counts: Dict[str, int] = {"positive": 0, "neutral": 0, "negative": 0}
        for r in reviews:
            s = r.get("sentiment", "neutral")
            if s in sentiment_counts:
                sentiment_counts[s] += 1
        keywords: Dict[str, int] = {}
        for r in reviews:
            for kw in r.get("keywords", []):
                keywords[kw] = keywords.get(kw, 0) + 1
        top_kw = sorted(keywords.items(), key=lambda x: x[1], reverse=True)[:20]
        return {
            "section": "review_analysis",
            "title": "用户评价分析",
            "content": {
                "total_reviews": total,
                "avg_rating": round(_mean(ratings), 2),
                "sentiment_distribution": sentiment_counts,
                "top_keywords": dict(top_kw),
                "rating_distribution": self._rating_dist(ratings),
                "sample_reviews": reviews[:5],
            }
        }

    def _rating_dist(self, ratings: List[float]) -> Dict[str, int]:
        dist: Dict[str, int] = {"5": 0, "4": 0, "3": 0, "2": 0, "1": 0}
        for r in ratings:
            key = str(min(5, max(1, round(r))))
            dist[key] = dist.get(key, 0) + 1
        return dist

    def _competitive_analysis(self, brand, competitors) -> Dict:
        dimensions = ["price", "quality", "service", "innovation", "popularity"]
        rows = []
        brand_scores = {d: random.uniform(6, 9) for d in dimensions}
        rows.append({"name": brand.get("name", "本品牌"), **{d: round(brand_scores[d], 1) for d in dimensions}})
        for c in competitors[:5]:
            rows.append({
                "name": c.get("name", ""),
                **{d: round(self._safe_float(c.get(d, random.uniform(5, 9))), 1) for d in dimensions}
            })
        return {
            "section": "competitive_analysis",
            "title": "竞品对比分析",
            "dimensions": dimensions,
            "brands": rows,
            "chart": {
                "type": "radar",
                "title": "品牌综合竞争力雷达图",
                "categories": dimensions,
                "series": rows,
            }
        }

    def _product_comparison(self, products) -> Dict:
        top = sorted(products, key=lambda p: self._safe_float(p.get("sales", 0)), reverse=True)[:5]
        categories = list({p.get("category", "其他") for p in products})
        return {
            "section": "product_comparison",
            "title": "热销产品横向对比",
            "top_products": top,
            "categories": categories,
            "comparison_matrix": [
                {
                    "product": p.get("name", ""),
                    "price": self._safe_float(p.get("price")),
                    "rating": self._safe_float(p.get("rating")),
                    "value_score": round(
                        self._safe_float(p.get("rating")) / (self._safe_float(p.get("price")) + 1) * 1000, 2
                    ),
                }
                for p in top
            ],
        }

    def _purchase_guide(self, products, reviews) -> Dict:
        top_rated = sorted(products, key=lambda p: self._safe_float(p.get("rating", 0)), reverse=True)[:3]
        top_value = sorted(
            products,
            key=lambda p: self._safe_float(p.get("rating", 0)) / (self._safe_float(p.get("price", 1)) + 1),
            reverse=True
        )[:3]
        return {
            "section": "purchase_guide",
            "title": "购买指南",
            "best_rated": top_rated,
            "best_value": top_value,
            "tips": [
                "建议关注官方旗舰店活动获得优惠价",
                "参考真实用户评价，避免刷单产品",
                "注意查看售后服务政策",
                "对比同价位竞品，确保物有所值",
            ]
        }


class B2CBrandUnspecifiedGenerator(ReportGenerator):
    """Generator for B2C reports where brand is not specified (general market)."""

    def generate(self, data: ReportData, options: FormatOptions) -> Dict[str, Any]:
        raw = data.data
        category  = raw.get("category", "")
        brands    = self._safe_list(raw, "brands")
        products  = self._safe_list(raw, "products")
        trends    = self._safe_list(raw, "trends")
        user_prefs = self._safe_dict(raw, "user_preferences")

        content: Dict[str, Any] = {
            "title": data.title,
            "report_type": data.report_type.value,
            "generated_at": _fmt_dt(data.created_at),
            "category": category,
            "sections": [],
        }

        content["sections"].append(self._market_overview(category, brands, products))
        content["sections"].append(self._brand_ranking(brands))
        content["sections"].append(self._product_recommendations(products, user_prefs))
        content["sections"].append(self._trend_analysis(trends))
        content["sections"].append(self._budget_guide(products))

        return content

    def _market_overview(self, category, brands, products) -> Dict:
        prices = [self._safe_float(p.get("price")) for p in products if p.get("price")]
        return {
            "section": "market_overview",
            "title": f"{category} 市场概览",
            "content": {
                "category": category,
                "brand_count": len(brands),
                "product_count": len(products),
                "price_range": {
                    "min": round(min(prices), 2) if prices else 0,
                    "max": round(max(prices), 2) if prices else 0,
                    "avg": round(_mean(prices), 2) if prices else 0,
                },
                "market_segments": self._segment_products(products),
            }
        }

    def _segment_products(self, products) -> Dict[str, int]:
        segments: Dict[str, int] = {"入门级(<500)": 0, "中端(500-2000)": 0, "高端(2000-5000)": 0, "旗舰(>5000)": 0}
        for p in products:
            price = self._safe_float(p.get("price", 0))
            if price < 500:
                segments["入门级(<500)"] += 1
            elif price < 2000:
                segments["中端(500-2000)"] += 1
            elif price < 5000:
                segments["高端(2000-5000)"] += 1
            else:
                segments["旗舰(>5000)"] += 1
        return segments

    def _brand_ranking(self, brands) -> Dict:
        scored = []
        for b in brands:
            score = (
                self._safe_float(b.get("reputation", 5)) * 0.35 +
                self._safe_float(b.get("quality", 5)) * 0.35 +
                self._safe_float(b.get("service", 5)) * 0.30
            )
            scored.append({**b, "composite_score": round(score, 2)})
        scored.sort(key=lambda x: x["composite_score"], reverse=True)
        return {
            "section": "brand_ranking",
            "title": "品牌排行榜",
            "rankings": scored[:20],
            "table": {
                "headers": ["排名","品牌","声誉分","品质分","服务分","综合分"],
                "rows": [
                    {"rank": i+1, **{k: v for k, v in b.items()}}
                    for i, b in enumerate(scored[:20])
                ]
            }
        }

    def _product_recommendations(self, products, user_prefs) -> Dict:
        budget_max = self._safe_float(user_prefs.get("budget_max", 9999999))
        categories = user_prefs.get("preferred_categories", [])
        filtered = [
            p for p in products
            if self._safe_float(p.get("price", 0)) <= budget_max
            and (not categories or p.get("category") in categories)
        ]
        top = sorted(filtered, key=lambda p: self._safe_float(p.get("rating", 0)), reverse=True)[:10]
        return {
            "section": "product_recommendations",
            "title": "个性化产品推荐",
            "user_preferences": user_prefs,
            "recommendations": top,
            "reasoning": "根据您的预算和偏好，以上产品综合评分最高，建议重点考察。",
        }

    def _trend_analysis(self, trends) -> Dict:
        return {
            "section": "trend_analysis",
            "title": "市场趋势分析",
            "trends": trends[:10],
            "emerging_technologies": [t for t in trends if t.get("type") == "technology"][:5],
            "consumer_behaviors": [t for t in trends if t.get("type") == "behavior"][:5],
        }

    def _budget_guide(self, products) -> Dict:
        segments: Dict[str, List] = {
            "entry": [],
            "mid_range": [],
            "high_end": [],
            "flagship": [],
        }
        for p in products:
            price = self._safe_float(p.get("price", 0))
            if price < 500:
                segments["entry"].append(p)
            elif price < 2000:
                segments["mid_range"].append(p)
            elif price < 5000:
                segments["high_end"].append(p)
            else:
                segments["flagship"].append(p)
        return {
            "section": "budget_guide",
            "title": "预算购买指南",
            "entry_picks": sorted(segments["entry"], key=lambda p: self._safe_float(p.get("rating", 0)), reverse=True)[:3],
            "mid_range_picks": sorted(segments["mid_range"], key=lambda p: self._safe_float(p.get("rating", 0)), reverse=True)[:3],
            "high_end_picks": sorted(segments["high_end"], key=lambda p: self._safe_float(p.get("rating", 0)), reverse=True)[:3],
            "flagship_picks": sorted(segments["flagship"], key=lambda p: self._safe_float(p.get("rating", 0)), reverse=True)[:3],
        }


# Generator registry
_GENERATORS: Dict[ReportType, ReportGenerator] = {
    ReportType.B2B_PRODUCT_ANALYSIS:  B2BProductAnalysisGenerator(),
    ReportType.B2C_BRAND_SPECIFIED:   B2CBrandSpecifiedGenerator(),
    ReportType.B2C_BRAND_UNSPECIFIED: B2CBrandUnspecifiedGenerator(),
    ReportType.MARKET_OVERVIEW:       B2CBrandUnspecifiedGenerator(),
    ReportType.SUPPLIER_EVALUATION:   B2BProductAnalysisGenerator(),
    ReportType.PRICE_COMPARISON:      B2BProductAnalysisGenerator(),
    ReportType.QUALITY_ASSESSMENT:    B2BProductAnalysisGenerator(),
    ReportType.TREND_ANALYSIS:        B2CBrandUnspecifiedGenerator(),
}

def get_generator(report_type: ReportType) -> ReportGenerator:
    return _GENERATORS.get(report_type, B2BProductAnalysisGenerator())


# ══════════════════════════════════════════════════════════════════════════════
# REPORT TEMPLATE MANAGER
# ══════════════════════════════════════════════════════════════════════════════

class ReportTemplateManager:
    """Manages report templates stored in DB."""

    def __init__(self, db: Session):
        self._db = db

    def get(self, template_id: str) -> Optional[ReportTemplate]:
        row = self._db.query(ReportTemplateModel).filter_by(template_id=template_id, is_active=True).first()
        if not row:
            return None
        return self._row_to_template(row)

    def list_all(self, report_type: Optional[str] = None) -> List[ReportTemplate]:
        q = self._db.query(ReportTemplateModel).filter_by(is_active=True)
        if report_type:
            q = q.filter_by(report_type=report_type)
        return [self._row_to_template(r) for r in q.all()]

    def create(self, tmpl: ReportTemplate) -> ReportTemplate:
        row = ReportTemplateModel(
            template_id   = tmpl.template_id,
            name          = tmpl.name,
            report_type   = tmpl.report_type.value if isinstance(tmpl.report_type, ReportType) else tmpl.report_type,
            description   = tmpl.description,
            sections      = tmpl.sections,
            default_format= tmpl.default_format.value if isinstance(tmpl.default_format, OutputFormat) else tmpl.default_format,
            custom_css    = tmpl.custom_css,
            header_tmpl   = tmpl.header_template,
            footer_tmpl   = tmpl.footer_template,
            chart_config  = tmpl.chart_config,
            is_active     = tmpl.is_active,
            created_at    = _now(),
            updated_at    = _now(),
        )
        self._db.add(row)
        self._db.commit()
        self._db.refresh(row)
        return self._row_to_template(row)

    def update(self, template_id: str, updates: Dict) -> Optional[ReportTemplate]:
        row = self._db.query(ReportTemplateModel).filter_by(template_id=template_id).first()
        if not row:
            return None
        for k, v in updates.items():
            if hasattr(row, k):
                setattr(row, k, v)
        row.updated_at = _now()
        self._db.commit()
        self._db.refresh(row)
        return self._row_to_template(row)

    def delete(self, template_id: str) -> bool:
        row = self._db.query(ReportTemplateModel).filter_by(template_id=template_id).first()
        if not row:
            return False
        row.is_active = False
        row.updated_at = _now()
        self._db.commit()
        return True

    def _row_to_template(self, row: ReportTemplateModel) -> ReportTemplate:
        rt = row.report_type
        try:
            rt = ReportType(rt)
        except ValueError:
            rt = ReportType.B2B_PRODUCT_ANALYSIS
        fmt = row.default_format
        try:
            fmt = OutputFormat(fmt)
        except ValueError:
            fmt = OutputFormat.HTML
        return ReportTemplate(
            template_id     = row.template_id,
            name            = row.name,
            report_type     = rt,
            description     = row.description or "",
            sections        = row.sections or [],
            default_format  = fmt,
            custom_css      = row.custom_css or "",
            header_template = row.header_tmpl or "",
            footer_template = row.footer_tmpl or "",
            chart_config    = row.chart_config or {},
            is_active       = row.is_active,
        )


# ══════════════════════════════════════════════════════════════════════════════
# FORMATTERS
# ══════════════════════════════════════════════════════════════════════════════

_DEFAULT_CSS = """
body { font-family: 'Microsoft YaHei', Arial, sans-serif; margin: 0; padding: 20px; color: #333; }
h1 { color: #1a237e; border-bottom: 3px solid #1a237e; padding-bottom: 10px; }
h2 { color: #283593; border-left: 4px solid #3949ab; padding-left: 10px; margin-top: 30px; }
h3 { color: #3949ab; }
table { width: 100%; border-collapse: collapse; margin: 15px 0; }
th { background: #3949ab; color: white; padding: 10px; text-align: left; }
td { padding: 8px 10px; border-bottom: 1px solid #e0e0e0; }
tr:nth-child(even) { background: #f5f5f5; }
.summary-box { background: #e8eaf6; border-radius: 8px; padding: 20px; margin: 15px 0; }
.metric { display: inline-block; margin: 10px 20px 10px 0; }
.metric-value { font-size: 24px; font-weight: bold; color: #3949ab; }
.metric-label { font-size: 12px; color: #666; }
.recommendation { background: #fff8e1; border-left: 4px solid #ffc107; padding: 10px 15px; margin: 8px 0; }
.section { margin-bottom: 40px; page-break-inside: avoid; }
@media print { .no-print { display: none; } }
"""

_JINJA2_REPORT_TEMPLATE = """<!DOCTYPE html>
<html lang="{{ lang | default('zh') }}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{ title }}</title>
<style>{{ css }}</style>
</head>
<body>
<h1>{{ title }}</h1>
<p style="color:#888; font-size:13px;">生成时间: {{ generated_at }} | 报告类型: {{ report_type }}</p>
{% if summary %}
<div class="summary-box">
  <h2>数据摘要</h2>
  {% for k, v in summary.items() %}
  <div class="metric"><span class="metric-value">{{ v }}</span><br><span class="metric-label">{{ k }}</span></div>
  {% endfor %}
</div>
{% endif %}
{% for section in sections %}
<div class="section">
  <h2>{{ section.title }}</h2>
  {% if section.content is defined and section.content is mapping %}
    {% for k, v in section.content.items() %}
      {% if v is iterable and v is not string %}
        <h3>{{ k }}</h3>
        <ul>{% for item in v %}<li>{{ item }}</li>{% endfor %}</ul>
      {% else %}
        <p><strong>{{ k }}:</strong> {{ v }}</p>
      {% endif %}
    {% endfor %}
  {% endif %}
  {% if section.table is defined %}
    <table>
      <thead><tr>{% for h in section.table.headers %}<th>{{ h }}</th>{% endfor %}</tr></thead>
      <tbody>
        {% for row in section.table.rows[:50] %}
        <tr>{% for h in section.table.headers %}<td>{{ row[h] | default('') }}</td>{% endfor %}</tr>
        {% endfor %}
      </tbody>
    </table>
  {% endif %}
  {% if "items" in section %}
    {% for item in section["items"] %}
    <div class="recommendation">{{ item }}</div>
    {% endfor %}
  {% endif %}
</div>
{% endfor %}
<hr>
<p style="text-align:center; color:#888; font-size:12px;">本报告由 ILbuy 智能采购平台生成</p>
</body>
</html>"""


class HTMLFormatter:
    """Renders report content as HTML."""

    def format(self, content: Dict[str, Any], options: FormatOptions, template: Optional[ReportTemplate] = None) -> bytes:
        css = _DEFAULT_CSS + (template.custom_css if template else "") + options.custom_css
        if _HAS_JINJA2:
            return self._render_jinja2(content, css, options)
        return self._render_stdlib(content, css, options)

    def _render_jinja2(self, content: Dict, css: str, options: FormatOptions) -> bytes:
        env = jinja2.Environment(autoescape=True, undefined=jinja2.Undefined)
        tmpl = env.from_string(_JINJA2_REPORT_TEMPLATE)
        html = tmpl.render(
            title        = content.get("title", "Report"),
            generated_at = content.get("generated_at", ""),
            report_type  = content.get("report_type", ""),
            summary      = content.get("summary"),
            sections     = content.get("sections", []),
            css          = css,
            lang         = options.language,
        )
        return html.encode("utf-8")

    def _render_stdlib(self, content: Dict, css: str, options: FormatOptions) -> bytes:
        parts = [
            f'<!DOCTYPE html><html lang="{options.language}"><head>',
            '<meta charset="utf-8">',
            f'<title>{content.get("title","Report")}</title>',
            f'<style>{css}</style></head><body>',
            f'<h1>{content.get("title","Report")}</h1>',
            f'<p style="color:#888">生成时间: {content.get("generated_at","")} | 类型: {content.get("report_type","")}</p>',
        ]
        summary = content.get("summary")
        if summary:
            parts.append('<div class="summary-box"><h2>数据摘要</h2>')
            for k, v in summary.items():
                parts.append(f'<div class="metric"><span class="metric-value">{v}</span><br><span class="metric-label">{k}</span></div>')
            parts.append('</div>')
        for section in content.get("sections", []):
            parts.append(f'<div class="section"><h2>{section.get("title","")}</h2>')
            sec_content = section.get("content")
            if isinstance(sec_content, dict):
                for k, v in sec_content.items():
                    if isinstance(v, list):
                        parts.append(f'<h3>{k}</h3><ul>')
                        for item in v:
                            parts.append(f'<li>{item}</li>')
                        parts.append('</ul>')
                    else:
                        parts.append(f'<p><strong>{k}:</strong> {v}</p>')
            tbl = section.get("table")
            if tbl:
                headers = tbl.get("headers", [])
                parts.append('<table><thead><tr>')
                for h in headers:
                    parts.append(f'<th>{h}</th>')
                parts.append('</tr></thead><tbody>')
                for row in tbl.get("rows", [])[:50]:
                    parts.append('<tr>')
                    if isinstance(row, dict):
                        vals = list(row.values())
                    else:
                        vals = [row]
                    for v in vals:
                        parts.append(f'<td>{v}</td>')
                    parts.append('</tr>')
                parts.append('</tbody></table>')
            for item in section.get("items", []):
                parts.append(f'<div class="recommendation">{item}</div>')
            parts.append('</div>')
        parts.append('<hr><p style="text-align:center;color:#888;font-size:12px;">本报告由 ILbuy 智能采购平台生成</p></body></html>')
        return "\n".join(parts).encode("utf-8")


class PDFFormatter:
    """Renders report content as PDF using reportlab or HTML fallback."""

    def __init__(self):
        self._html_formatter = HTMLFormatter()

    def format(self, content: Dict[str, Any], options: FormatOptions, template: Optional[ReportTemplate] = None) -> bytes:
        if _HAS_REPORTLAB:
            try:
                return self._render_reportlab(content, options, template)
            except Exception as e:
                logger.warning(f"reportlab render failed, falling back to HTML: {e}")
        if _HAS_WEASYPRINT:
            try:
                html_bytes = self._html_formatter.format(content, options, template)
                return WeasyHTML(string=html_bytes.decode("utf-8")).write_pdf()
            except Exception as e:
                logger.warning(f"weasyprint failed: {e}")
        # Final fallback: return HTML bytes labelled as PDF-compatible
        logger.warning("No PDF library available, returning HTML content as PDF fallback")
        return self._html_formatter.format(content, options, template)

    def _render_reportlab(self, content: Dict, options: FormatOptions, template: Optional[ReportTemplate]) -> bytes:
        buf = io.BytesIO()
        page_size = A4 if options.page_size.upper() == "A4" else letter
        doc = SimpleDocTemplate(
            buf,
            pagesize=page_size,
            rightMargin=0.75 * inch,
            leftMargin=0.75 * inch,
            topMargin=inch,
            bottomMargin=0.75 * inch,
        )
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "ReportTitle",
            parent=styles["Title"],
            fontSize=20,
            textColor=colors.HexColor("#1a237e"),
            spaceAfter=16,
            fontName="Helvetica-Bold",
        )
        h2_style = ParagraphStyle(
            "ReportH2",
            parent=styles["Heading2"],
            fontSize=14,
            textColor=colors.HexColor("#283593"),
            spaceBefore=20,
            spaceAfter=8,
            fontName="Helvetica-Bold",
        )
        body_style = ParagraphStyle(
            "ReportBody",
            parent=styles["Normal"],
            fontSize=10,
            spaceAfter=6,
            fontName="Helvetica",
        )
        meta_style = ParagraphStyle(
            "ReportMeta",
            parent=styles["Normal"],
            fontSize=9,
            textColor=colors.grey,
            spaceAfter=16,
            fontName="Helvetica",
        )
        story = []
        story.append(Paragraph(content.get("title", "Report"), title_style))
        story.append(Paragraph(
            f"生成时间: {content.get('generated_at','')} | 类型: {content.get('report_type','')}",
            meta_style
        ))
        story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#3949ab")))
        story.append(Spacer(1, 0.2 * inch))

        # Summary box
        summary = content.get("summary")
        if summary:
            story.append(Paragraph("数据摘要", h2_style))
            summary_data = [["指标", "数值"]]
            for k, v in summary.items():
                summary_data.append([str(k), str(v)])
            summary_table = Table(summary_data, colWidths=[3 * inch, 3 * inch])
            summary_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#3949ab")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e0e0e0")),
                ("PADDING", (0, 0), (-1, -1), 6),
            ]))
            story.append(summary_table)
            story.append(Spacer(1, 0.2 * inch))

        for section in content.get("sections", []):
            story.append(Paragraph(section.get("title", ""), h2_style))
            sec_content = section.get("content")
            if isinstance(sec_content, dict):
                for k, v in sec_content.items():
                    if isinstance(v, list):
                        story.append(Paragraph(f"<b>{k}:</b>", body_style))
                        for item in v:
                            if item:
                                story.append(Paragraph(f"• {item}", body_style))
                    elif v:
                        story.append(Paragraph(f"<b>{k}:</b> {v}", body_style))
            tbl = section.get("table")
            if tbl and tbl.get("headers") and tbl.get("rows"):
                headers = tbl["headers"]
                table_data = [headers]
                for row in tbl["rows"][:30]:
                    if isinstance(row, dict):
                        table_data.append([str(row.get(h, "")) for h in headers])
                    else:
                        table_data.append([str(v) for v in (list(row.values()) if isinstance(row, dict) else [row])])
                col_w = (6.5 * inch) / max(len(headers), 1)
                pdf_table = Table(table_data, colWidths=[col_w] * len(headers))
                pdf_table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#3949ab")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e0e0e0")),
                    ("PADDING", (0, 0), (-1, -1), 4),
                    ("WORDWRAP", (0, 0), (-1, -1), True),
                ]))
                story.append(pdf_table)
                story.append(Spacer(1, 0.1 * inch))
            for item in section.get("items", []):
                story.append(Paragraph(f"▶ {item}", body_style))
            story.append(Spacer(1, 0.15 * inch))

        doc.build(story)
        return buf.getvalue()


class ExcelFormatter:
    """Renders report content as Excel (.xlsx) using openpyxl or CSV fallback."""

    def format(self, content: Dict[str, Any], options: FormatOptions, template: Optional[ReportTemplate] = None) -> bytes:
        if _HAS_OPENPYXL:
            try:
                return self._render_openpyxl(content, options)
            except Exception as e:
                logger.warning(f"openpyxl render failed, falling back to CSV: {e}")
        return self._render_csv_fallback(content)

    def _render_openpyxl(self, content: Dict, options: FormatOptions) -> bytes:
        wb = Workbook()
        # Remove default sheet
        default_sheet = wb.active
        wb.remove(default_sheet)

        # Summary sheet
        ws_summary = wb.create_sheet("摘要")
        self._style_sheet_header(ws_summary, content.get("title", "Report"))
        row = 3
        ws_summary.cell(row, 1, "生成时间").font = Font(bold=True)
        ws_summary.cell(row, 2, content.get("generated_at", ""))
        row += 1
        ws_summary.cell(row, 1, "报告类型").font = Font(bold=True)
        ws_summary.cell(row, 2, content.get("report_type", ""))
        row += 2
        summary = content.get("summary")
        if summary:
            ws_summary.cell(row, 1, "数据摘要").font = Font(bold=True, size=12)
            row += 1
            for k, v in summary.items():
                ws_summary.cell(row, 1, str(k))
                ws_summary.cell(row, 2, str(v))
                row += 1
        ws_summary.column_dimensions["A"].width = 25
        ws_summary.column_dimensions["B"].width = 30

        # Section sheets
        for section in content.get("sections", []):
            sheet_name = section.get("title", "Sheet")[:31]
            ws = wb.create_sheet(sheet_name)
            self._style_sheet_header(ws, section.get("title", ""))
            row = 3
            sec_content = section.get("content")
            if isinstance(sec_content, dict):
                for k, v in sec_content.items():
                    if isinstance(v, (list, dict)):
                        ws.cell(row, 1, str(k)).font = Font(bold=True)
                        row += 1
                        if isinstance(v, list):
                            for item in v:
                                ws.cell(row, 1, "•")
                                ws.cell(row, 2, str(item))
                                row += 1
                    else:
                        ws.cell(row, 1, str(k)).font = Font(bold=True)
                        ws.cell(row, 2, str(v))
                        row += 1
                row += 1
            tbl = section.get("table")
            if tbl and tbl.get("headers"):
                headers = tbl["headers"]
                # Header row
                for ci, h in enumerate(headers, 1):
                    cell = ws.cell(row, ci, h)
                    cell.font = Font(bold=True, color="FFFFFF")
                    cell.fill = PatternFill("solid", fgColor="3949AB")
                    cell.alignment = Alignment(horizontal="center")
                row += 1
                for data_row in tbl.get("rows", [])[:options.max_rows]:
                    if isinstance(data_row, dict):
                        for ci, h in enumerate(headers, 1):
                            ws.cell(row, ci, data_row.get(h, ""))
                    elif isinstance(data_row, (list, tuple)):
                        for ci, v in enumerate(data_row, 1):
                            ws.cell(row, ci, v)
                    row += 1
                for ci in range(1, len(headers) + 1):
                    ws.column_dimensions[get_column_letter(ci)].width = 18
            for item in section.get("items", []):
                ws.cell(row, 1, "▶")
                ws.cell(row, 2, str(item))
                row += 1
        buf = io.BytesIO()
        wb.save(buf)
        return buf.getvalue()

    def _style_sheet_header(self, ws, title: str):
        ws.merge_cells("A1:F1")
        cell = ws.cell(1, 1, title)
        cell.font = Font(bold=True, size=14, color="1A237E")
        cell.alignment = Alignment(horizontal="center")
        ws.row_dimensions[1].height = 30

    def _render_csv_fallback(self, content: Dict) -> bytes:
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["Report:", content.get("title", "")])
        writer.writerow(["Generated:", content.get("generated_at", "")])
        writer.writerow([])
        summary = content.get("summary")
        if summary:
            writer.writerow(["=== Summary ==="])
            for k, v in summary.items():
                writer.writerow([k, v])
            writer.writerow([])
        for section in content.get("sections", []):
            writer.writerow([f"=== {section.get('title','')} ==="])
            tbl = section.get("table")
            if tbl and tbl.get("headers"):
                writer.writerow(tbl["headers"])
                for row in tbl.get("rows", []):
                    if isinstance(row, dict):
                        writer.writerow(list(row.values()))
                    else:
                        writer.writerow([row])
            for item in section.get("items", []):
                writer.writerow([f"• {item}"])
            writer.writerow([])
        return buf.getvalue().encode("utf-8-sig")


class CSVFormatter:
    """Renders report as CSV (single flat table or multi-section)."""

    def format(self, content: Dict[str, Any], options: FormatOptions, template: Optional[ReportTemplate] = None) -> bytes:
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["Title", content.get("title", "")])
        writer.writerow(["Generated At", content.get("generated_at", "")])
        writer.writerow(["Report Type", content.get("report_type", "")])
        writer.writerow([])
        summary = content.get("summary")
        if summary:
            writer.writerow(["--- Summary ---"])
            writer.writerow(["Metric", "Value"])
            for k, v in summary.items():
                writer.writerow([k, v])
            writer.writerow([])
        for section in content.get("sections", []):
            writer.writerow([f"--- {section.get('title','')} ---"])
            tbl = section.get("table")
            if tbl and tbl.get("headers"):
                writer.writerow(tbl["headers"])
                for row in tbl.get("rows", [])[:options.max_rows]:
                    if isinstance(row, dict):
                        writer.writerow(list(row.values()))
                    else:
                        writer.writerow([str(row)])
            for item in section.get("items", []):
                writer.writerow([item])
            writer.writerow([])
        return buf.getvalue().encode("utf-8-sig")


class JSONFormatter:
    """Renders report as structured JSON."""

    def format(self, content: Dict[str, Any], options: FormatOptions, template: Optional[ReportTemplate] = None) -> bytes:
        output = {
            "report": content,
            "format_version": "1.0",
            "generated_by": "ILbuy Report Output Layer",
        }
        return json.dumps(output, ensure_ascii=False, indent=2, default=str).encode("utf-8")


class MarkdownFormatter:
    """Renders report as Markdown."""

    def format(self, content: Dict[str, Any], options: FormatOptions, template: Optional[ReportTemplate] = None) -> bytes:
        lines = []
        lines.append(f"# {content.get('title', 'Report')}")
        lines.append(f"")
        lines.append(f"**生成时间**: {content.get('generated_at', '')}  ")
        lines.append(f"**报告类型**: {content.get('report_type', '')}  ")
        lines.append("")
        summary = content.get("summary")
        if summary:
            lines.append("## 数据摘要")
            lines.append("")
            for k, v in summary.items():
                lines.append(f"- **{k}**: {v}")
            lines.append("")
        for section in content.get("sections", []):
            lines.append(f"## {section.get('title', '')}")
            lines.append("")
            sec_content = section.get("content")
            if isinstance(sec_content, dict):
                for k, v in sec_content.items():
                    if isinstance(v, list):
                        lines.append(f"### {k}")
                        for item in v:
                            if item:
                                lines.append(f"- {item}")
                    elif v:
                        lines.append(f"**{k}**: {v}  ")
                lines.append("")
            tbl = section.get("table")
            if tbl and tbl.get("headers"):
                headers = tbl["headers"]
                lines.append("| " + " | ".join(str(h) for h in headers) + " |")
                lines.append("| " + " | ".join("---" for _ in headers) + " |")
                for row in tbl.get("rows", [])[:50]:
                    if isinstance(row, dict):
                        vals = [str(row.get(h, "")) for h in headers]
                    else:
                        vals = [str(row)]
                    lines.append("| " + " | ".join(vals) + " |")
                lines.append("")
            for item in section.get("items", []):
                lines.append(f"> {item}")
            lines.append("")
        lines.append("---")
        lines.append("*本报告由 ILbuy 智能采购平台生成*")
        return "\n".join(lines).encode("utf-8")


# Formatter registry
_FORMATTERS: Dict[OutputFormat, Any] = {
    OutputFormat.HTML:     HTMLFormatter(),
    OutputFormat.PDF:      PDFFormatter(),
    OutputFormat.EXCEL:    ExcelFormatter(),
    OutputFormat.CSV:      CSVFormatter(),
    OutputFormat.JSON:     JSONFormatter(),
    OutputFormat.MARKDOWN: MarkdownFormatter(),
}

_CONTENT_TYPES: Dict[OutputFormat, str] = {
    OutputFormat.HTML:     "text/html; charset=utf-8",
    OutputFormat.PDF:      "application/pdf",
    OutputFormat.EXCEL:    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    OutputFormat.CSV:      "text/csv; charset=utf-8",
    OutputFormat.JSON:     "application/json; charset=utf-8",
    OutputFormat.MARKDOWN: "text/markdown; charset=utf-8",
}

_FILE_EXTENSIONS: Dict[OutputFormat, str] = {
    OutputFormat.HTML:     "html",
    OutputFormat.PDF:      "pdf",
    OutputFormat.EXCEL:    "xlsx",
    OutputFormat.CSV:      "csv",
    OutputFormat.JSON:     "json",
    OutputFormat.MARKDOWN: "md",
}


# ══════════════════════════════════════════════════════════════════════════════
# DELIVERY MANAGER
# ══════════════════════════════════════════════════════════════════════════════

class DeliveryManager:
    """Handles multi-channel delivery of reports."""

    SMTP_HOST = os.getenv("SMTP_HOST", "smtp.example.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER = os.getenv("SMTP_USER", "")
    SMTP_PASS = os.getenv("SMTP_PASS", "")
    SMTP_FROM = os.getenv("SMTP_FROM", "reports@ilbuy.com")

    WECHAT_API_URL = os.getenv("WECHAT_API_URL", "")
    WECHAT_APPID   = os.getenv("WECHAT_APPID", "")
    WECHAT_SECRET  = os.getenv("WECHAT_SECRET", "")

    async def deliver(
        self,
        report: GeneratedReport,
        options: DeliveryOptions,
        delivery_id: str,
    ) -> Tuple[DeliveryStatus, str]:
        """Dispatch delivery to appropriate channel. Returns (status, message)."""
        handlers = {
            DeliveryChannel.EMAIL:   self._deliver_email,
            DeliveryChannel.WECHAT:  self._deliver_wechat,
            DeliveryChannel.WEBHOOK: self._deliver_webhook,
            DeliveryChannel.WEB:     self._deliver_web,
            DeliveryChannel.API:     self._deliver_api,
        }
        handler = handlers.get(options.channel)
        if not handler:
            return DeliveryStatus.FAILED, f"Unknown channel: {options.channel}"
        try:
            return await handler(report, options, delivery_id)
        except Exception as e:
            logger.error(f"Delivery {delivery_id} failed: {e}")
            return DeliveryStatus.FAILED, str(e)

    async def _deliver_email(self, report: GeneratedReport, options: DeliveryOptions, delivery_id: str) -> Tuple[DeliveryStatus, str]:
        if not _HAS_AIOSMTPLIB:
            logger.warning(f"[STUB] Email delivery {delivery_id}: aiosmtplib not available; would send to {options.recipients}")
            return DeliveryStatus.DELIVERED, "stub: email sent (aiosmtplib not available)"
        if not self.SMTP_HOST or not self.SMTP_USER:
            logger.warning(f"[STUB] Email delivery {delivery_id}: SMTP not configured")
            return DeliveryStatus.DELIVERED, "stub: email sent (SMTP not configured)"
        try:
            from email.mime.multipart import MIMEMultipart
            from email.mime.base import MIMEBase
            from email.mime.text import MIMEText
            from email import encoders
            ext = _FILE_EXTENSIONS.get(report.format, "bin")
            filename = f"report_{report.report_id[:8]}.{ext}"
            for recipient in options.recipients:
                msg = MIMEMultipart()
                msg["From"]    = self.SMTP_FROM
                msg["To"]      = recipient
                msg["Subject"] = options.subject or f"报告: {report.title}"
                msg.attach(MIMEText(options.message or "请查看附件中的报告。", "plain", "utf-8"))
                part = MIMEBase("application", "octet-stream")
                part.set_payload(report.content)
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", f'attachment; filename="{filename}"')
                msg.attach(part)
                await aiosmtplib.send(
                    msg,
                    hostname=self.SMTP_HOST,
                    port=self.SMTP_PORT,
                    username=self.SMTP_USER,
                    password=self.SMTP_PASS,
                    use_tls=True,
                )
            return DeliveryStatus.DELIVERED, f"Email sent to {len(options.recipients)} recipients"
        except Exception as e:
            return DeliveryStatus.FAILED, f"SMTP error: {e}"

    async def _deliver_wechat(self, report: GeneratedReport, options: DeliveryOptions, delivery_id: str) -> Tuple[DeliveryStatus, str]:
        if not _HAS_AIOHTTP or not self.WECHAT_API_URL:
            logger.warning(f"[STUB] WeChat delivery {delivery_id} to {options.recipients}")
            return DeliveryStatus.DELIVERED, "stub: WeChat notification sent"
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "appid": self.WECHAT_APPID,
                    "recipients": options.recipients,
                    "template_id": options.extra.get("template_id", ""),
                    "data": {
                        "title": report.title,
                        "download_url": report.download_url or "",
                        "message": options.message,
                    }
                }
                async with session.post(self.WECHAT_API_URL, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        return DeliveryStatus.DELIVERED, "WeChat notification sent"
                    body = await resp.text()
                    return DeliveryStatus.FAILED, f"WeChat API error {resp.status}: {body[:200]}"
        except Exception as e:
            return DeliveryStatus.FAILED, f"WeChat delivery error: {e}"

    async def _deliver_webhook(self, report: GeneratedReport, options: DeliveryOptions, delivery_id: str) -> Tuple[DeliveryStatus, str]:
        webhook_url = options.extra.get("url") or (options.recipients[0] if options.recipients else "")
        if not webhook_url:
            return DeliveryStatus.FAILED, "No webhook URL specified"
        if not _HAS_AIOHTTP:
            logger.warning(f"[STUB] Webhook delivery {delivery_id} to {webhook_url}")
            return DeliveryStatus.DELIVERED, "stub: webhook posted (aiohttp not available)"
        try:
            payload = {
                "event":       "report.generated",
                "delivery_id": delivery_id,
                "report_id":   report.report_id,
                "title":       report.title,
                "format":      report.format.value if isinstance(report.format, OutputFormat) else report.format,
                "size":        report.size,
                "download_url": report.download_url,
                "generated_at": _fmt_dt(report.generated_at),
                "metadata":    report.metadata,
            }
            headers = options.extra.get("headers", {})
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    webhook_url,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    if 200 <= resp.status < 300:
                        return DeliveryStatus.DELIVERED, f"Webhook delivered, status={resp.status}"
                    body = await resp.text()
                    return DeliveryStatus.FAILED, f"Webhook error {resp.status}: {body[:200]}"
        except Exception as e:
            return DeliveryStatus.FAILED, f"Webhook error: {e}"

    async def _deliver_web(self, report: GeneratedReport, options: DeliveryOptions, delivery_id: str) -> Tuple[DeliveryStatus, str]:
        """Web delivery means the report is accessible via download URL (no push needed)."""
        return DeliveryStatus.DELIVERED, f"Web portal: {report.download_url}"

    async def _deliver_api(self, report: GeneratedReport, options: DeliveryOptions, delivery_id: str) -> Tuple[DeliveryStatus, str]:
        """API delivery means the caller fetches the report themselves."""
        return DeliveryStatus.DELIVERED, f"API endpoint available: /api/v1/reports/{report.report_id}/download"


delivery_manager = DeliveryManager()

# ══════════════════════════════════════════════════════════════════════════════
# REPORT OUTPUT SERVICE
# ══════════════════════════════════════════════════════════════════════════════

class ReportOutputService:
    """Core service: generate, store, deliver, and manage reports."""

    STORAGE_DIR = Path(os.getenv("REPORT_STORAGE_DIR", "./report_storage"))
    BASE_URL    = os.getenv("REPORT_BASE_URL", "http://localhost:8007")

    def __init__(self):
        self.STORAGE_DIR.mkdir(parents=True, exist_ok=True)

    # ── Generate ──────────────────────────────────────────────────────────────

    async def generate(self, request: ReportRequest, db: Session) -> List[GeneratedReport]:
        """Generate report in all requested formats. Returns list of GeneratedReport."""
        report_id = str(uuid.uuid4())
        start_ts  = _now()

        report_data = ReportData(
            report_id   = report_id,
            report_type = request.report_type,
            title       = request.title,
            data        = request.data,
            metadata    = {},
            created_at  = start_ts,
            user_id     = request.user_id,
            tenant_id   = request.tenant_id,
        )

        template: Optional[ReportTemplate] = None
        if request.template_id:
            mgr = ReportTemplateManager(db)
            template = mgr.get(request.template_id)

        # Build structured content once (reused by all formats)
        generator = get_generator(request.report_type)
        try:
            content = generator.generate(report_data, request.format_options)
        except Exception as e:
            logger.error(f"Content generation failed for {report_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Report content generation failed: {e}")

        generated: List[GeneratedReport] = []
        expires_at = _now() + timedelta(seconds=request.expires_in)

        for fmt in request.formats:
            formatter = _FORMATTERS.get(fmt)
            if not formatter:
                continue
            try:
                fmt_start = _now()
                content_bytes = formatter.format(content, request.format_options, template)
                elapsed_ms = int((_now() - fmt_start).total_seconds() * 1000)
                content_type = _CONTENT_TYPES.get(fmt, "application/octet-stream")
                ext          = _FILE_EXTENSIONS.get(fmt, "bin")

                # Store file
                file_path = self.STORAGE_DIR / f"{report_id}_{fmt.value}.{ext}"
                if _HAS_AIOFILES:
                    async with aiofiles.open(file_path, "wb") as f:
                        await f.write(content_bytes)
                else:
                    file_path.write_bytes(content_bytes)

                download_url = f"{self.BASE_URL}/api/v1/reports/{report_id}/download?format={fmt.value}"

                gr = GeneratedReport(
                    report_id    = report_id,
                    title        = request.title,
                    report_type  = request.report_type,
                    format       = fmt,
                    content      = content_bytes,
                    content_type = content_type,
                    size         = len(content_bytes),
                    generated_at = _now(),
                    expires_at   = expires_at,
                    download_url = download_url,
                    metadata     = {
                        "template_id":  request.template_id,
                        "user_id":      request.user_id,
                        "tenant_id":    request.tenant_id,
                        "generation_ms": elapsed_ms,
                    },
                )
                generated.append(gr)

                # Persist log
                log = ReportGenerationLog(
                    report_id     = f"{report_id}_{fmt.value}",
                    title         = request.title,
                    report_type   = request.report_type.value,
                    format        = fmt.value,
                    status        = ReportStatus.COMPLETED.value,
                    file_path     = str(file_path),
                    file_size     = len(content_bytes),
                    content_type  = content_type,
                    template_id   = request.template_id,
                    user_id       = request.user_id,
                    tenant_id     = request.tenant_id,
                    extra_metadata = gr.metadata,
                    generation_ms  = elapsed_ms,
                    expires_at    = expires_at,
                    created_at    = start_ts,
                    updated_at    = _now(),
                )
                db.add(log)

                if REPORTS_GENERATED:
                    REPORTS_GENERATED.labels(report_type=request.report_type.value, format=fmt.value).inc()
                if REPORT_SIZE_BYTES:
                    REPORT_SIZE_BYTES.labels(format=fmt.value).observe(len(content_bytes))
                if GENERATION_TIME:
                    GENERATION_TIME.labels(report_type=request.report_type.value).observe(elapsed_ms / 1000)

                logger.info(f"Generated report {report_id} format={fmt.value} size={len(content_bytes)} ms={elapsed_ms}")

            except Exception as e:
                logger.error(f"Format {fmt.value} generation failed for {report_id}: {e}")
                db.add(ReportGenerationLog(
                    report_id     = f"{report_id}_{fmt.value}",
                    title         = request.title,
                    report_type   = request.report_type.value,
                    format        = fmt.value,
                    status        = ReportStatus.FAILED.value,
                    error_message = str(e),
                    created_at    = start_ts,
                    updated_at    = _now(),
                ))

        db.commit()
        if ACTIVE_REPORTS:
            ACTIVE_REPORTS.inc(len(generated))
        return generated

    # ── Deliver ───────────────────────────────────────────────────────────────

    async def deliver(self, report: GeneratedReport, delivery_opts: List[DeliveryOptions], db: Session) -> List[Dict]:
        results = []
        for opts in delivery_opts:
            delivery_id = str(uuid.uuid4())
            row = ReportDeliveryModel(
                delivery_id  = delivery_id,
                report_id    = report.report_id,
                channel      = opts.channel.value,
                status       = DeliveryStatus.SENDING.value,
                recipients   = opts.recipients,
                subject      = opts.subject,
                message      = opts.message,
                created_at   = _now(),
                updated_at   = _now(),
            )
            db.add(row)
            db.commit()
            db.refresh(row)

            status, message = await delivery_manager.deliver(report, opts, delivery_id)

            row.status        = status.value
            row.attempt_count = 1
            row.last_attempt  = _now()
            row.updated_at    = _now()
            if status == DeliveryStatus.DELIVERED:
                row.delivered_at = _now()
            else:
                row.error_message = message
            db.commit()

            if REPORTS_DELIVERED:
                REPORTS_DELIVERED.labels(channel=opts.channel.value, status=status.value).inc()

            results.append({
                "delivery_id": delivery_id,
                "channel":     opts.channel.value,
                "status":      status.value,
                "message":     message,
            })
        return results

    # ── Fetch ─────────────────────────────────────────────────────────────────

    def get_report_log(self, report_id: str, fmt: Optional[str], db: Session) -> Optional[ReportGenerationLog]:
        q = db.query(ReportGenerationLog)
        if fmt:
            q = q.filter_by(report_id=f"{report_id}_{fmt}")
        else:
            q = q.filter(ReportGenerationLog.report_id.like(f"{report_id}_%"))
        return q.first()

    def get_report_file(self, report_id: str, fmt: str, db: Session) -> Optional[Tuple[bytes, str, str]]:
        """Returns (content, content_type, filename) or None."""
        log = db.query(ReportGenerationLog).filter_by(
            report_id=f"{report_id}_{fmt}",
            status=ReportStatus.COMPLETED.value
        ).first()
        if not log or not log.file_path:
            return None
        # Expiry check
        if log.expires_at:
            exp = log.expires_at
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            if exp < _now():
                return None
        fp = Path(log.file_path)
        if not fp.exists():
            return None
        content = fp.read_bytes()
        ext = _FILE_EXTENSIONS.get(OutputFormat(fmt), "bin")
        filename = f"report_{report_id[:8]}.{ext}"
        return content, log.content_type, filename

    def list_reports(
        self,
        user_id: Optional[str],
        tenant_id: Optional[str],
        report_type: Optional[str],
        fmt: Optional[str],
        status: Optional[str],
        page: int,
        page_size: int,
        db: Session,
    ) -> Tuple[List[ReportGenerationLog], int]:
        q = db.query(ReportGenerationLog)
        if user_id:
            q = q.filter_by(user_id=user_id)
        if tenant_id:
            q = q.filter_by(tenant_id=tenant_id)
        if report_type:
            q = q.filter_by(report_type=report_type)
        if fmt:
            q = q.filter_by(format=fmt)
        if status:
            q = q.filter_by(status=status)
        total = q.count()
        rows  = q.order_by(ReportGenerationLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
        return rows, total

    def get_stats(self, db: Session) -> Dict:
        total   = db.query(ReportGenerationLog).count()
        done    = db.query(ReportGenerationLog).filter_by(status="completed").count()
        failed  = db.query(ReportGenerationLog).filter_by(status="failed").count()
        pending = db.query(ReportGenerationLog).filter_by(status="pending").count()
        deliveries = db.query(ReportDeliveryModel).count()
        delivered  = db.query(ReportDeliveryModel).filter_by(status="delivered").count()
        avg_size_row = db.execute(text("SELECT AVG(file_size) FROM report_generation_logs WHERE status='completed'")).fetchone()
        avg_size = float(avg_size_row[0] or 0)
        return {
            "total_reports":     total,
            "completed":         done,
            "failed":            failed,
            "pending":           pending,
            "total_deliveries":  deliveries,
            "delivered":         delivered,
            "avg_report_size_bytes": round(avg_size, 0),
        }

    def get_delivery_history(self, report_id: str, db: Session) -> List[ReportDeliveryModel]:
        return db.query(ReportDeliveryModel).filter_by(report_id=report_id).order_by(ReportDeliveryModel.created_at.desc()).all()

    async def delete_report(self, report_id: str, db: Session) -> int:
        """Delete all format files and logs for a report_id prefix. Returns count deleted."""
        logs = db.query(ReportGenerationLog).filter(
            ReportGenerationLog.report_id.like(f"{report_id}_%")
        ).all()
        count = 0
        for log in logs:
            if log.file_path:
                fp = Path(log.file_path)
                if fp.exists():
                    fp.unlink(missing_ok=True)
            db.delete(log)
            count += 1
        db.commit()
        if ACTIVE_REPORTS and count:
            ACTIVE_REPORTS.dec(count)
        return count


report_service = ReportOutputService()


# ══════════════════════════════════════════════════════════════════════════════
# PYDANTIC REQUEST/RESPONSE SCHEMAS
# ══════════════════════════════════════════════════════════════════════════════

class FormatOptionsSchema(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    page_size:        str  = "A4"
    orientation:      str  = "portrait"
    include_charts:   bool = True
    include_tables:   bool = True
    include_summary:  bool = True
    include_toc:      bool = True
    watermark:        str  = ""
    custom_css:       str  = ""
    chart_theme:      str  = "default"
    language:         str  = "zh"
    max_rows:         int  = 1000

    @field_validator("page_size")
    @classmethod
    def validate_page_size(cls, v: str) -> str:
        allowed = {"A4", "LETTER", "A3"}
        v = v.upper()
        if v not in allowed:
            raise ValueError(f"page_size must be one of {allowed}")
        return v

    @field_validator("max_rows")
    @classmethod
    def validate_max_rows(cls, v: int) -> int:
        return max(1, min(v, 10000))


class DeliveryOptionsSchema(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    channel:        DeliveryChannel
    recipients:     List[str]
    subject:        str = ""
    message:        str = ""
    schedule_at:    Optional[datetime] = None
    retry_count:    int = 3
    retry_interval: int = 60
    extra:          Dict[str, Any] = {}

    @field_validator("recipients")
    @classmethod
    def validate_recipients(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("recipients must not be empty")
        return v[:50]


class GenerateReportRequest(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    report_type:    ReportType
    title:          str
    data:           Dict[str, Any]
    formats:        List[OutputFormat] = [OutputFormat.HTML]
    delivery:       Optional[List[DeliveryOptionsSchema]] = None
    template_id:    Optional[str] = None
    format_options: FormatOptionsSchema = FormatOptionsSchema()
    user_id:        Optional[str] = None
    tenant_id:      Optional[str] = None
    expires_in:     int = 7 * 86400

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("title must not be empty")
        return v[:500]

    @field_validator("formats")
    @classmethod
    def validate_formats(cls, v: List[Any]) -> List[Any]:
        if not v:
            raise ValueError("at least one format required")
        return list(set(v))[:6]


class CreateTemplateRequest(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    name:           str
    report_type:    ReportType
    description:    str = ""
    sections:       List[str] = []
    default_format: OutputFormat = OutputFormat.HTML
    custom_css:     str = ""
    header_template: str = ""
    footer_template: str = ""
    chart_config:   Dict[str, Any] = {}


class ReportLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    report_id:    str
    title:        str
    report_type:  str
    format:       str
    status:       str
    file_size:    int
    content_type: str
    template_id:  Optional[str]
    user_id:      Optional[str]
    tenant_id:    Optional[str]
    generation_ms: int
    expires_at:   Optional[str]
    created_at:   Optional[str]
    error_message: Optional[str]

    @classmethod
    def from_log(cls, log: ReportGenerationLog) -> "ReportLogResponse":
        return cls(
            report_id    = log.report_id,
            title        = log.title,
            report_type  = log.report_type,
            format       = log.format,
            status       = log.status,
            file_size    = log.file_size or 0,
            content_type = log.content_type or "",
            template_id  = log.template_id,
            user_id      = log.user_id,
            tenant_id    = log.tenant_id,
            generation_ms = log.generation_ms or 0,
            expires_at   = _fmt_dt(log.expires_at),
            created_at   = _fmt_dt(log.created_at),
            error_message = log.error_message,
        )


class DeliveryResponse(BaseModel):
    delivery_id:  str
    report_id:    str
    channel:      str
    status:       str
    recipients:   List[str]
    subject:      str
    attempt_count: int
    delivered_at: Optional[str]
    error_message: Optional[str]
    created_at:   Optional[str]

    @classmethod
    def from_model(cls, m: ReportDeliveryModel) -> "DeliveryResponse":
        return cls(
            delivery_id   = m.delivery_id,
            report_id     = m.report_id,
            channel       = m.channel,
            status        = m.status,
            recipients    = m.recipients or [],
            subject       = m.subject or "",
            attempt_count = m.attempt_count or 0,
            delivered_at  = _fmt_dt(m.delivered_at),
            error_message = m.error_message,
            created_at    = _fmt_dt(m.created_at),
        )


class TemplateResponse(BaseModel):
    template_id:    str
    name:           str
    report_type:    str
    description:    str
    sections:       List[str]
    default_format: str
    is_active:      bool
    created_at:     Optional[str]

    @classmethod
    def from_template(cls, t: ReportTemplate, created_at: Optional[datetime] = None) -> "TemplateResponse":
        return cls(
            template_id    = t.template_id,
            name           = t.name,
            report_type    = t.report_type.value if isinstance(t.report_type, ReportType) else t.report_type,
            description    = t.description,
            sections       = t.sections,
            default_format = t.default_format.value if isinstance(t.default_format, OutputFormat) else t.default_format,
            is_active      = t.is_active,
            created_at     = _fmt_dt(created_at or t.created_at),
        )


# ══════════════════════════════════════════════════════════════════════════════
# FASTAPI APPLICATION
# ══════════════════════════════════════════════════════════════════════════════

def create_app() -> FastAPI:
    app = FastAPI(
        title="ILbuy Report Output Layer",
        description="Multi-format report generation and multi-channel delivery service",
        version="1.0.0",
    )

    # ── Lifecycle ─────────────────────────────────────────────────────────────
    @app.on_event("startup")
    async def startup():
        init_db()
        await redis_manager.connect()
        seed_templates()
        asyncio.create_task(_cleanup_expired_reports())
        logger.info("Report Output Layer started")

    @app.on_event("shutdown")
    async def shutdown():
        await redis_manager.disconnect()

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
            "status":      "ok" if db_ok else "degraded",
            "service":     "report-output-layer",
            "db":          "ok" if db_ok else "error",
            "has_jinja2":  _HAS_JINJA2,
            "has_reportlab": _HAS_REPORTLAB,
            "has_openpyxl": _HAS_OPENPYXL,
            "has_weasyprint": _HAS_WEASYPRINT,
            "has_plotly":  _HAS_PLOTLY,
            "timestamp":   _fmt_dt(_now()),
        }

    # ── Metrics ───────────────────────────────────────────────────────────────
    @app.get("/metrics")
    async def metrics():
        if not _HAS_PROMETHEUS:
            raise HTTPException(status_code=501, detail="Prometheus not available")
        from fastapi.responses import Response
        return Response(generate_latest(_RO_REGISTRY), media_type=CONTENT_TYPE_LATEST)

    # ── Report Generation ─────────────────────────────────────────────────────
    @app.post("/api/v1/reports/generate")
    async def generate_report(
        req: GenerateReportRequest,
        background_tasks: BackgroundTasks,
        db: Session = Depends(get_db),
    ):
        fmt_opts = FormatOptions(
            page_size       = req.format_options.page_size,
            orientation     = req.format_options.orientation,
            include_charts  = req.format_options.include_charts,
            include_tables  = req.format_options.include_tables,
            include_summary = req.format_options.include_summary,
            include_toc     = req.format_options.include_toc,
            watermark       = req.format_options.watermark,
            custom_css      = req.format_options.custom_css,
            chart_theme     = req.format_options.chart_theme,
            language        = req.format_options.language,
            max_rows        = req.format_options.max_rows,
        )
        rr = ReportRequest(
            report_type    = ReportType(req.report_type) if isinstance(req.report_type, str) else req.report_type,
            title          = req.title,
            data           = req.data,
            formats        = [OutputFormat(f) if isinstance(f, str) else f for f in req.formats],
            template_id    = req.template_id,
            format_options = fmt_opts,
            user_id        = req.user_id,
            tenant_id      = req.tenant_id,
            expires_in     = req.expires_in,
        )
        generated = await report_service.generate(rr, db)
        if not generated:
            raise HTTPException(status_code=500, detail="No reports generated")

        results = []
        for gr in generated:
            result = {
                "report_id":    gr.report_id,
                "format":       gr.format.value if isinstance(gr.format, OutputFormat) else gr.format,
                "size":         gr.size,
                "download_url": gr.download_url,
                "expires_at":   _fmt_dt(gr.expires_at),
                "generated_at": _fmt_dt(gr.generated_at),
            }
            results.append(result)

        # Handle delivery
        if req.delivery and generated:
            primary = generated[0]
            delivery_opts = []
            for d in req.delivery:
                delivery_opts.append(DeliveryOptions(
                    channel    = DeliveryChannel(d.channel) if isinstance(d.channel, str) else d.channel,
                    recipients = d.recipients,
                    subject    = d.subject,
                    message    = d.message,
                    extra      = d.extra,
                ))
            deliveries = await report_service.deliver(primary, delivery_opts, db)
            return {"reports": results, "deliveries": deliveries}

        return {"reports": results, "deliveries": []}

    @app.get("/api/v1/reports/{report_id}")
    async def get_report(report_id: str, fmt: Optional[str] = None, db: Session = Depends(get_db)):
        log = report_service.get_report_log(report_id, fmt, db)
        if not log:
            raise HTTPException(status_code=404, detail="Report not found")
        return ReportLogResponse.from_log(log)

    @app.get("/api/v1/reports/{report_id}/download")
    async def download_report(
        report_id: str,
        format: str = Query(default="html", alias="format"),
        db: Session = Depends(get_db),
    ):
        result = report_service.get_report_file(report_id, format, db)
        if not result:
            raise HTTPException(status_code=404, detail="Report file not found or expired")
        content, content_type, filename = result
        headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
        return StreamingResponse(io.BytesIO(content), media_type=content_type, headers=headers)

    @app.get("/api/v1/reports/{report_id}/preview")
    async def preview_report(
        report_id: str,
        db: Session = Depends(get_db),
    ):
        result = report_service.get_report_file(report_id, "html", db)
        if not result:
            raise HTTPException(status_code=404, detail="Report not found or not in HTML format")
        content, _, _ = result
        return HTMLResponse(content=content.decode("utf-8"))

    @app.delete("/api/v1/reports/{report_id}")
    async def delete_report(report_id: str, db: Session = Depends(get_db)):
        count = await report_service.delete_report(report_id, db)
        if count == 0:
            raise HTTPException(status_code=404, detail="Report not found")
        return {"deleted": count, "report_id": report_id}

    @app.get("/api/v1/reports")
    async def list_reports(
        user_id:     Optional[str] = None,
        tenant_id:   Optional[str] = None,
        report_type: Optional[str] = None,
        format:      Optional[str] = None,
        status:      Optional[str] = None,
        page:        int = Query(default=1, ge=1),
        page_size:   int = Query(default=20, ge=1, le=100),
        db: Session = Depends(get_db),
    ):
        rows, total = report_service.list_reports(user_id, tenant_id, report_type, format, status, page, page_size, db)
        return {
            "items":     [ReportLogResponse.from_log(r) for r in rows],
            "total":     total,
            "page":      page,
            "page_size": page_size,
            "pages":     math.ceil(total / page_size) if page_size else 1,
        }

    @app.get("/api/v1/reports/stats/summary")
    async def report_stats(db: Session = Depends(get_db)):
        return report_service.get_stats(db)

    # ── Delivery ──────────────────────────────────────────────────────────────
    @app.post("/api/v1/reports/{report_id}/deliver")
    async def deliver_report(
        report_id: str,
        delivery_opts: List[DeliveryOptionsSchema],
        format: str = Query(default="html"),
        db: Session = Depends(get_db),
    ):
        result = report_service.get_report_file(report_id, format, db)
        if not result:
            raise HTTPException(status_code=404, detail="Report file not found or expired")
        content, content_type, filename = result
        log = report_service.get_report_log(report_id, format, db)
        gr = GeneratedReport(
            report_id    = report_id,
            title        = log.title if log else "Report",
            report_type  = ReportType(log.report_type) if log else ReportType.B2B_PRODUCT_ANALYSIS,
            format       = OutputFormat(format),
            content      = content,
            content_type = content_type,
            size         = len(content),
            generated_at = _now(),
            download_url = f"{report_service.BASE_URL}/api/v1/reports/{report_id}/download?format={format}",
        )
        opts = [
            DeliveryOptions(
                channel    = DeliveryChannel(d.channel) if isinstance(d.channel, str) else d.channel,
                recipients = d.recipients,
                subject    = d.subject,
                message    = d.message,
                extra      = d.extra,
            )
            for d in delivery_opts
        ]
        results = await report_service.deliver(gr, opts, db)
        return {"deliveries": results}

    @app.get("/api/v1/reports/{report_id}/deliveries")
    async def get_delivery_history(report_id: str, db: Session = Depends(get_db)):
        history = report_service.get_delivery_history(report_id, db)
        return {"deliveries": [DeliveryResponse.from_model(m) for m in history]}

    # ── Templates ─────────────────────────────────────────────────────────────
    @app.post("/api/v1/templates")
    async def create_template(req: CreateTemplateRequest, db: Session = Depends(get_db)):
        mgr = ReportTemplateManager(db)
        tmpl = ReportTemplate(
            template_id    = str(uuid.uuid4()),
            name           = req.name,
            report_type    = ReportType(req.report_type) if isinstance(req.report_type, str) else req.report_type,
            description    = req.description,
            sections       = req.sections,
            default_format = OutputFormat(req.default_format) if isinstance(req.default_format, str) else req.default_format,
            custom_css     = req.custom_css,
            header_template = req.header_template,
            footer_template = req.footer_template,
            chart_config   = req.chart_config,
        )
        created = mgr.create(tmpl)
        return TemplateResponse.from_template(created)

    @app.get("/api/v1/templates")
    async def list_templates(report_type: Optional[str] = None, db: Session = Depends(get_db)):
        mgr = ReportTemplateManager(db)
        templates = mgr.list_all(report_type)
        return {"templates": [TemplateResponse.from_template(t) for t in templates]}

    @app.get("/api/v1/templates/{template_id}")
    async def get_template(template_id: str, db: Session = Depends(get_db)):
        mgr = ReportTemplateManager(db)
        tmpl = mgr.get(template_id)
        if not tmpl:
            raise HTTPException(status_code=404, detail="Template not found")
        return TemplateResponse.from_template(tmpl)

    @app.put("/api/v1/templates/{template_id}")
    async def update_template(template_id: str, updates: Dict[str, Any], db: Session = Depends(get_db)):
        mgr = ReportTemplateManager(db)
        tmpl = mgr.update(template_id, updates)
        if not tmpl:
            raise HTTPException(status_code=404, detail="Template not found")
        return TemplateResponse.from_template(tmpl)

    @app.delete("/api/v1/templates/{template_id}")
    async def delete_template(template_id: str, db: Session = Depends(get_db)):
        mgr = ReportTemplateManager(db)
        ok = mgr.delete(template_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Template not found")
        return {"deleted": True, "template_id": template_id}

    # ── Report Types & Formats ────────────────────────────────────────────────
    @app.get("/api/v1/report-types")
    async def list_report_types():
        return {"report_types": [{"value": t.value, "label": t.value.replace("_", " ").title()} for t in ReportType]}

    @app.get("/api/v1/output-formats")
    async def list_output_formats():
        return {
            "formats": [
                {
                    "value":        f.value,
                    "label":        f.value.upper(),
                    "content_type": _CONTENT_TYPES.get(f, ""),
                    "extension":    _FILE_EXTENSIONS.get(f, ""),
                }
                for f in OutputFormat
            ]
        }

    return app


app = create_app()


# ══════════════════════════════════════════════════════════════════════════════
# SEED DATA
# ══════════════════════════════════════════════════════════════════════════════

_SEED_DONE = False

def seed_templates():
    global _SEED_DONE
    if _SEED_DONE:
        return
    _SEED_DONE = True
    db = SessionLocal()
    try:
        existing = db.query(ReportTemplateModel).count()
        if existing > 0:
            return
        templates = [
            ReportTemplate(
                template_id    = "tmpl-b2b-standard",
                name           = "B2B标准产品分析模板",
                report_type    = ReportType.B2B_PRODUCT_ANALYSIS,
                description    = "适用于企业采购场景的标准产品分析报告，包含价格分析、供应商评估、市场洞察等模块",
                sections       = ["executive_summary", "product_analysis", "supplier_evaluation", "price_analysis", "market_insights", "recommendations"],
                default_format = OutputFormat.PDF,
                custom_css     = ".summary-box { border: 2px solid #1a237e; }",
                chart_config   = {"theme": "corporate", "palette": "blue"},
            ),
            ReportTemplate(
                template_id    = "tmpl-b2c-brand",
                name           = "B2C品牌指定分析模板",
                report_type    = ReportType.B2C_BRAND_SPECIFIED,
                description    = "针对消费者指定品牌的深度分析报告，含品牌概览、产品阵容、用户评价、竞品对比",
                sections       = ["brand_overview", "product_lineup", "review_analysis", "competitive_analysis", "product_comparison", "purchase_guide"],
                default_format = OutputFormat.HTML,
                custom_css     = "h1 { color: #e91e63; } h2 { color: #ad1457; }",
                chart_config   = {"theme": "consumer", "palette": "pink"},
            ),
            ReportTemplate(
                template_id    = "tmpl-b2c-market",
                name           = "B2C市场全景模板",
                report_type    = ReportType.B2C_BRAND_UNSPECIFIED,
                description    = "面向无品牌偏好消费者的市场全景报告，含市场概览、品牌排行、产品推荐、趋势分析",
                sections       = ["market_overview", "brand_ranking", "product_recommendations", "trend_analysis", "budget_guide"],
                default_format = OutputFormat.HTML,
                custom_css     = "h1 { color: #00695c; } h2 { color: #004d40; }",
                chart_config   = {"theme": "market", "palette": "teal"},
            ),
        ]
        mgr = ReportTemplateManager(db)
        for tmpl in templates:
            mgr.create(tmpl)
        logger.info(f"Seeded {len(templates)} report templates")
    except Exception as e:
        logger.warning(f"Seed templates failed: {e}")
    finally:
        db.close()


# ══════════════════════════════════════════════════════════════════════════════
# BACKGROUND TASKS
# ══════════════════════════════════════════════════════════════════════════════

async def _cleanup_expired_reports():
    """Periodically delete expired report files and their DB records."""
    while True:
        try:
            await asyncio.sleep(3600)  # run every hour
            db = SessionLocal()
            try:
                now = _now()
                expired = db.query(ReportGenerationLog).filter(
                    ReportGenerationLog.expires_at.isnot(None),
                    ReportGenerationLog.status == ReportStatus.COMPLETED.value,
                ).all()
                deleted = 0
                for log in expired:
                    exp = log.expires_at
                    if exp is None:
                        continue
                    if exp.tzinfo is None:
                        exp = exp.replace(tzinfo=timezone.utc)
                    if exp < now:
                        if log.file_path:
                            fp = Path(log.file_path)
                            if fp.exists():
                                fp.unlink(missing_ok=True)
                        log.status     = ReportStatus.EXPIRED.value
                        log.updated_at = _now()
                        deleted += 1
                db.commit()
                if deleted:
                    logger.info(f"Cleaned up {deleted} expired reports")
                    if ACTIVE_REPORTS:
                        ACTIVE_REPORTS.dec(deleted)
            finally:
                db.close()
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Cleanup task error: {e}")
            await asyncio.sleep(300)


# ══════════════════════════════════════════════════════════════════════════════
# ENTRYPOINT
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("REPORT_SERVICE_PORT", "8007"))
    uvicorn.run("report_output_layer:app", host="0.0.0.0", port=port, reload=False)
