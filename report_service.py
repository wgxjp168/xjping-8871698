"""
report_service.py  —  业务逻辑层: 报告服务 (Part 8)
报告管理 · 生成(HTML/PDF/Excel/JSON/CSV) · 交付 · 模板管理
Production-grade: SQLite-compat ORM, Pydantic v2, conditional imports
"""
# ── stdlib ────────────────────────────────────────────────────────────────────
import asyncio
import base64
import concurrent.futures
import csv
import hashlib
import io
import json
import logging
import os
import re
import secrets
import time
import uuid
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ── SQLAlchemy ────────────────────────────────────────────────────────────────
from sqlalchemy import (
    Boolean, Column, DateTime, Index, Integer, JSON,
    Numeric, String, Text, UniqueConstraint,
    and_, asc, desc, func, or_, select,
    update as sa_update,
)
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# ── FastAPI + Pydantic ────────────────────────────────────────────────────────
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, StreamingResponse
from pydantic import BaseModel, Field, field_validator, model_validator
import aiohttp

# ── Optional: Redis ───────────────────────────────────────────────────────────
try:
    import redis.asyncio as _aioredis; _HAS_REDIS = True
except ImportError:
    _HAS_REDIS = False

# ── Optional: jinja2 ─────────────────────────────────────────────────────────
try:
    import jinja2; _HAS_JINJA2 = True
except ImportError:
    _HAS_JINJA2 = False

# ── Optional: openpyxl ───────────────────────────────────────────────────────
try:
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, PatternFill
    from openpyxl.utils import get_column_letter
    _HAS_OPENPYXL = True
except ImportError:
    _HAS_OPENPYXL = False

# ── Optional: reportlab (PDF) ─────────────────────────────────────────────────
try:
    from reportlab.lib import colors as rl_colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    _HAS_REPORTLAB = True
except ImportError:
    _HAS_REPORTLAB = False

# ── Optional: weasyprint ──────────────────────────────────────────────────────
try:
    from weasyprint import HTML as WeasyHTML; _HAS_WEASYPRINT = True
except ImportError:
    _HAS_WEASYPRINT = False

# ── Optional: pandas ─────────────────────────────────────────────────────────
try:
    import pandas as _pd; _HAS_PANDAS = True
except ImportError:
    _HAS_PANDAS = False

# ── Optional: Prometheus ──────────────────────────────────────────────────────
try:
    from prometheus_client import (
        CollectorRegistry, Counter, Gauge, Histogram, generate_latest
    )
    _HAS_PROMETHEUS = True
    _RS_REGISTRY = CollectorRegistry()
except ImportError:
    _HAS_PROMETHEUS = False; _RS_REGISTRY = None

_THREAD_POOL = concurrent.futures.ThreadPoolExecutor(max_workers=4)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("report_service")


# ══════════════════════════════════════════════════════════════════════════════
# 枚举
# ══════════════════════════════════════════════════════════════════════════════
class ReportType(str, Enum):
    PRODUCT_ANALYSIS       = "product_analysis"
    COMPARISON             = "comparison"
    RECOMMENDATION         = "recommendation"
    TREND                  = "trend"
    B2B_ANALYSIS           = "b2b_analysis"
    B2C_BRAND_SPECIFIED    = "b2c_brand_specified"
    B2C_BRAND_UNSPECIFIED  = "b2c_brand_unspecified"
    CUSTOM                 = "custom"


class ReportFormat(str, Enum):
    HTML     = "html"
    PDF      = "pdf"
    EXCEL    = "excel"
    JSON     = "json"
    CSV      = "csv"
    MARKDOWN = "markdown"


class ReportStatus(str, Enum):
    PENDING    = "pending"
    PROCESSING = "processing"
    COMPLETED  = "completed"
    FAILED     = "failed"
    EXPIRED    = "expired"


class DeliveryChannel(str, Enum):
    WEB_PORTAL = "web_portal"
    EMAIL      = "email"
    WECHAT     = "wechat"
    SMS        = "sms"
    API        = "api"
    DOWNLOAD   = "download"


class DeliveryStatus(str, Enum):
    PENDING   = "pending"
    SENDING   = "sending"
    DELIVERED = "delivered"
    FAILED    = "failed"


class ReportLanguage(str, Enum):
    ZH_CN = "zh_CN"
    EN_US = "en_US"


# ══════════════════════════════════════════════════════════════════════════════
# 配置
# ══════════════════════════════════════════════════════════════════════════════
@dataclass
class ServiceConfig:
    database_url:            str = os.getenv("DATABASE_URL",       "sqlite+aiosqlite:///./report_service.db")
    redis_url:               str = os.getenv("REDIS_URL",           "redis://localhost:6379/3")
    host:                    str = os.getenv("REPORT_HOST",         "0.0.0.0")
    port:                    int = int(os.getenv("REPORT_PORT",     "8024"))
    secret_key:              str = os.getenv("REPORT_SECRET",       secrets.token_hex(32))
    output_dir:              str = os.getenv("REPORT_OUTPUT_DIR",   "/tmp/report_service_output")
    default_expire_days:     int = int(os.getenv("REPORT_EXPIRE_DAYS", "30"))
    max_concurrent:          int = int(os.getenv("REPORT_MAX_CONCURRENT", "5"))
    notify_url:              str = os.getenv("NOTIFY_SERVICE_URL",  "http://localhost:8040")
    debug:                   bool = os.getenv("DEBUG", "false").lower() == "true"


# ══════════════════════════════════════════════════════════════════════════════
# ORM 模型  (SQLite-compat: Integer PK, JSON, no relationship, extra_metadata)
# ══════════════════════════════════════════════════════════════════════════════
Base = declarative_base()


class Report(Base):
    __tablename__ = "reports"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    report_id      = Column(String(64),  unique=True, nullable=False, index=True)
    report_number  = Column(String(32),  unique=True, nullable=False, index=True)
    user_id        = Column(String(64),  nullable=False, index=True)
    user_role      = Column(String(20),  nullable=False, default="unknown")
    session_id     = Column(String(64),  nullable=True,  index=True)
    report_type    = Column(String(50),  nullable=False, index=True)
    language       = Column(String(10),  nullable=False, default="zh_CN")
    title          = Column(String(200), nullable=False)
    description    = Column(Text, nullable=True)
    status         = Column(String(20),  nullable=False, default="pending", index=True)
    error_message  = Column(Text, nullable=True)
    retry_count    = Column(Integer, default=0)
    raw_data       = Column(JSON, nullable=False)
    data_summary   = Column(JSON, nullable=True)
    extra_metadata = Column("report_metadata", JSON, default=dict)
    template_id    = Column(String(64),  nullable=True)
    files          = Column(JSON, default=dict)      # {format: {path,url,size,content_type}}
    available_formats  = Column(JSON, default=list)
    generated_formats  = Column(JSON, default=list)
    access_count   = Column(Integer, default=0)
    download_count = Column(Integer, default=0)
    generation_ms  = Column(Integer, nullable=True)
    expires_at     = Column(DateTime, nullable=True,  index=True)
    generated_at   = Column(DateTime, nullable=True)
    created_at     = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at     = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("idx_report_user_status",  "user_id", "status", "created_at"),
        Index("idx_report_type_status",  "report_type", "status"),
        Index("idx_report_expiry",       "expires_at", "status"),
    )


class ReportDelivery(Base):
    __tablename__ = "report_deliveries"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    delivery_id = Column(String(64), unique=True, nullable=False, index=True)
    report_id   = Column(String(64), nullable=False, index=True)
    channel     = Column(String(20), nullable=False, index=True)
    recipient   = Column(String(500), nullable=False)
    fmt         = Column(String(20), nullable=False)
    message     = Column(Text, nullable=True)
    status      = Column(String(20), nullable=False, default="pending", index=True)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    opened_count = Column(Integer, default=0)
    extra_metadata = Column("delivery_metadata", JSON, default=dict)
    scheduled_at = Column(DateTime, nullable=True)
    sent_at      = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    opened_at    = Column(DateTime, nullable=True)
    created_at   = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at   = Column(DateTime, default=datetime.utcnow, nullable=False)


class ReportActivity(Base):
    __tablename__ = "report_activities"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    activity_id    = Column(String(64), unique=True, nullable=False, index=True)
    report_id      = Column(String(64), nullable=False, index=True)
    activity_type  = Column(String(50), nullable=False)
    action         = Column(String(100), nullable=False)
    result         = Column(String(20), nullable=False, default="success")
    message        = Column(String(500), nullable=True)
    performed_by   = Column(String(64), nullable=True)
    performed_by_type = Column(String(20), nullable=True, default="system")
    before_state   = Column(JSON, nullable=True)
    after_state    = Column(JSON, nullable=True)
    ip_address     = Column(String(50), nullable=True)
    performed_at   = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    created_at     = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("idx_rpt_act_order_time", "report_id", "performed_at"),
    )


class ReportTemplate(Base):
    __tablename__ = "report_templates"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    template_id = Column(String(64), unique=True, nullable=False, index=True)
    name        = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=True)
    report_type = Column(String(50), nullable=False, index=True)
    language    = Column(String(10), nullable=False, default="zh_CN")
    fmt         = Column(String(20), nullable=False)
    version     = Column(String(20), nullable=False, default="1.0")
    content     = Column(JSON, nullable=False)
    styles      = Column(JSON, default=dict)
    variables   = Column(JSON, default=list)
    is_active   = Column(Boolean, default=True, nullable=False)
    is_system   = Column(Boolean, default=False, nullable=False)
    usage_count = Column(Integer, default=0)
    created_by  = Column(String(64), nullable=False, default="system")
    updated_by  = Column(String(64), nullable=False, default="system")
    created_at  = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at  = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("idx_tmpl_active_type", "is_active", "report_type", "fmt"),
    )


# ══════════════════════════════════════════════════════════════════════════════
# Pydantic v2 模型
# ══════════════════════════════════════════════════════════════════════════════
class GenerateReportRequest(BaseModel):
    report_type:       ReportType    = Field(...)
    data:              Dict[str, Any] = Field(...)
    formats:           List[str]     = Field(default_factory=lambda: ["html", "json"])
    language:          str           = Field(default="zh_CN")
    delivery_channels: List[str]     = Field(default_factory=lambda: ["web_portal"])
    recipients:        List[str]     = Field(default_factory=list)
    title:             Optional[str] = None
    description:       Optional[str] = None
    expire_days:       int           = Field(default=30, ge=1, le=365)
    template_id:       Optional[str] = None
    callback_url:      Optional[str] = None
    user_id:           Optional[str] = None
    session_id:        Optional[str] = None
    extra_metadata:    Dict[str, Any] = Field(default_factory=dict)

    @field_validator("title", mode="before")
    @classmethod
    def default_title(cls, v: Optional[str], info: Any) -> str:
        if v:
            return v
        data = info.data if hasattr(info, "data") else {}
        rt = data.get("report_type", "")
        rt_val = rt.value if hasattr(rt, "value") else str(rt)
        titles = {
            "product_analysis":      "商品分析报告",
            "comparison":            "商品比较报告",
            "recommendation":        "商品推荐报告",
            "trend":                 "市场趋势报告",
            "b2b_analysis":          "B2B商品分析报告",
            "b2c_brand_specified":   "B2C已定品牌分析报告",
            "b2c_brand_unspecified": "B2C未定品牌分析报告",
            "custom":                "自定义报告",
        }
        return titles.get(rt_val, "分析报告")

    @field_validator("recipients")
    @classmethod
    def check_recipients(cls, v: List[str], info: Any) -> List[str]:
        data = info.data if hasattr(info, "data") else {}
        channels = data.get("delivery_channels", [])
        if "email" in channels and not v:
            raise ValueError("邮件交付必须指定收件人")
        return v


class DeliverReportRequest(BaseModel):
    report_id:         str       = Field(..., min_length=1)
    delivery_channels: List[str] = Field(..., min_length=1)
    recipients:        List[str] = Field(..., min_length=1)
    fmt:               Optional[str] = None
    message:           Optional[str] = None


class CreateTemplateRequest(BaseModel):
    template_id: str           = Field(..., min_length=1)
    name:        str           = Field(..., min_length=1)
    report_type: str           = Field(..., min_length=1)
    language:    str           = Field(default="zh_CN")
    fmt:         str           = Field(..., min_length=1)
    content:     Dict[str, Any]= Field(...)
    styles:      Dict[str, Any]= Field(default_factory=dict)
    variables:   List[str]     = Field(default_factory=list)
    description: Optional[str] = None
    version:     str           = Field(default="1.0")

    @field_validator("template_id")
    @classmethod
    def check_id(cls, v: str) -> str:
        if not re.match(r"^[a-zA-Z0-9_\-]+$", v):
            raise ValueError("template_id 只能含字母、数字、下划线、连字符")
        return v


class ReportQuery(BaseModel):
    user_id:     Optional[str]      = None
    report_type: Optional[str]      = None
    status:      Optional[str]      = None
    page:        int                = Field(default=1, ge=1)
    page_size:   int                = Field(default=20, ge=1, le=100)
    sort_by:     str                = Field(default="created_at")
    sort_order:  str                = Field(default="desc")


# ══════════════════════════════════════════════════════════════════════════════
# RedisManager  (in-memory fallback)
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
                logger.warning(f"Redis unavailable, using in-memory: {exc}")
                self._client = None

    async def get(self, key: str) -> Optional[str]:
        if self._client:
            try: return await self._client.get(key)
            except Exception: pass
        e = self._mock.get(key)
        if e and e[1] > time.time(): return e[0]
        self._mock.pop(key, None)
        return None

    async def set(self, key: str, value: str, ex: int = 3600) -> None:
        if self._client:
            try: await self._client.set(key, value, ex=ex); return
            except Exception: pass
        self._mock[key] = (value, time.time() + ex)

    async def delete(self, key: str) -> None:
        if self._client:
            try: await self._client.delete(key); return
            except Exception: pass
        self._mock.pop(key, None)


# ══════════════════════════════════════════════════════════════════════════════
# 报告格式生成器
# ══════════════════════════════════════════════════════════════════════════════
class ReportFormatter:
    """Base formatter with fallback implementations."""

    # ── HTML ─────────────────────────────────────────────────────────────────
    def to_html(self, title: str, report_type: str, data: Dict[str, Any],
                language: str, generated_at: str) -> bytes:
        products = data.get("products", [])
        analysis = data.get("analysis", {})
        summary  = data.get("summary", data.get("nlp_explanation", {}).get("summary", ""))

        # Build product rows
        rows_html = ""
        for p in products[:50]:
            price  = p.get("current_price", p.get("price", "N/A"))
            rating = p.get("average_score", p.get("rating", "N/A"))
            title_p= p.get("title", "未知商品")[:60]
            platform = p.get("platform_name", p.get("platform", ""))
            rows_html += f"""<tr>
              <td>{title_p}</td>
              <td>¥{price}</td>
              <td>{rating}</td>
              <td>{platform}</td>
            </tr>\n"""

        # Analysis metrics
        metrics_html = ""
        if analysis:
            for k, v in list(analysis.items())[:8]:
                metrics_html += f'<div class="metric"><span class="mv">{v}</span><span class="ml">{k}</span></div>'

        if _HAS_JINJA2:
            tpl = jinja2.Template("""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>{{title}}</title>
<style>
 body{font-family:'Microsoft YaHei',Arial,sans-serif;margin:0;background:#f7f8fa}
 .hdr{background:linear-gradient(135deg,#1a73e8,#0d47a1);color:#fff;padding:30px 40px}
 .hdr h1{margin:0;font-size:26px} .hdr p{margin:6px 0 0;opacity:.8;font-size:13px}
 .body{padding:30px 40px}
 .card{background:#fff;border-radius:8px;padding:20px;margin-bottom:20px;box-shadow:0 1px 4px rgba(0,0,0,.1)}
 .metrics{display:flex;flex-wrap:wrap;gap:12px;margin-bottom:8px}
 .metric{background:#e8f0fe;border-radius:6px;padding:12px 18px;min-width:110px;text-align:center}
 .mv{display:block;font-size:22px;font-weight:700;color:#1a73e8}
 .ml{font-size:12px;color:#555}
 table{width:100%;border-collapse:collapse;font-size:13px}
 th{background:#1a73e8;color:#fff;padding:10px;text-align:left}
 td{padding:9px 10px;border-bottom:1px solid #eee}
 tr:hover td{background:#f1f8ff}
 .footer{text-align:center;color:#999;font-size:12px;padding:20px}
</style></head><body>
<div class="hdr"><h1>{{title}}</h1><p>生成时间: {{generated_at}} · 数据条数: {{count}}</p></div>
<div class="body">
{% if summary %}<div class="card"><h3 style="margin-top:0">摘要</h3><p>{{summary}}</p></div>{% endif %}
{% if metrics_html %}<div class="card"><h3 style="margin-top:0">关键指标</h3>
<div class="metrics">{{metrics_html|safe}}</div></div>{% endif %}
{% if rows_html %}<div class="card"><h3 style="margin-top:0">商品列表 (共{{count}}条)</h3>
<table><tr><th>商品名称</th><th>价格</th><th>评分</th><th>平台</th></tr>
{{rows_html|safe}}</table></div>{% endif %}
</div>
<div class="footer">由多模态商品识别系统生成 · {{generated_at}}</div>
</body></html>""")
            html = tpl.render(
                title=title, generated_at=generated_at, summary=summary,
                metrics_html=metrics_html, rows_html=rows_html, count=len(products),
            )
        else:
            html = f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><title>{title}</title></head>
<body><h1>{title}</h1><p>生成时间: {generated_at}</p>
<p>{summary}</p>
<table border="1"><tr><th>商品</th><th>价格</th><th>评分</th><th>平台</th></tr>
{rows_html}</table></body></html>"""
        return html.encode("utf-8")

    # ── PDF ──────────────────────────────────────────────────────────────────
    def to_pdf(self, title: str, data: Dict[str, Any], generated_at: str) -> bytes:
        if _HAS_REPORTLAB:
            buf = io.BytesIO()
            doc = SimpleDocTemplate(buf, pagesize=A4,
                                    leftMargin=2*cm, rightMargin=2*cm,
                                    topMargin=2*cm, bottomMargin=2*cm)
            styles = getSampleStyleSheet()
            story  = []

            story.append(Paragraph(title, styles["Title"]))
            story.append(Spacer(1, 0.5*cm))
            story.append(Paragraph(f"生成时间: {generated_at}", styles["Normal"]))
            story.append(Spacer(1, 0.5*cm))

            summary = data.get("summary", "")
            if summary:
                story.append(Paragraph("摘要", styles["Heading2"]))
                story.append(Paragraph(str(summary), styles["Normal"]))
                story.append(Spacer(1, 0.3*cm))

            products = data.get("products", [])[:30]
            if products:
                story.append(Paragraph("商品列表", styles["Heading2"]))
                table_data = [["商品名称", "价格", "评分", "平台"]]
                for p in products:
                    table_data.append([
                        str(p.get("title", ""))[:40],
                        str(p.get("current_price", p.get("price", ""))),
                        str(p.get("average_score", p.get("rating", ""))),
                        str(p.get("platform_name", p.get("platform", ""))),
                    ])
                t = Table(table_data, colWidths=[10*cm, 3*cm, 3*cm, 3*cm])
                t.setStyle(TableStyle([
                    ("BACKGROUND", (0,0), (-1,0), rl_colors.HexColor("#1a73e8")),
                    ("TEXTCOLOR",  (0,0), (-1,0), rl_colors.white),
                    ("FONTSIZE",   (0,0), (-1,0), 10),
                    ("FONTSIZE",   (0,1), (-1,-1), 9),
                    ("ROWBACKGROUNDS", (0,1), (-1,-1), [rl_colors.white, rl_colors.HexColor("#f1f8ff")]),
                    ("GRID",       (0,0), (-1,-1), 0.5, rl_colors.grey),
                    ("VALIGN",     (0,0), (-1,-1), "MIDDLE"),
                ]))
                story.append(t)

            doc.build(story)
            return buf.getvalue()

        # fallback: return HTML as PDF placeholder
        logger.warning("reportlab not available; returning HTML as PDF placeholder")
        return self.to_html(title, "", data, "zh_CN", generated_at)

    # ── Excel ────────────────────────────────────────────────────────────────
    def to_excel(self, title: str, data: Dict[str, Any]) -> bytes:
        if _HAS_OPENPYXL:
            wb = Workbook()
            ws = wb.active
            ws.title = "商品数据"

            hdr_fill = PatternFill("solid", fgColor="1A73E8")
            hdr_font = Font(color="FFFFFF", bold=True)

            headers = ["商品名称", "平台", "价格", "原价", "评分", "销量", "库存", "品牌"]
            fields  = ["title","platform_name","current_price","original_price",
                       "average_score","monthly_sales","stock_quantity","brand_name"]
            for col, h in enumerate(headers, 1):
                cell = ws.cell(row=1, column=col, value=h)
                cell.fill = hdr_fill; cell.font = hdr_font
                cell.alignment = Alignment(horizontal="center")
                ws.column_dimensions[get_column_letter(col)].width = 18

            products = data.get("products", [])
            for row_i, p in enumerate(products[:500], 2):
                brand_name = ""
                brand = p.get("brand", {})
                if isinstance(brand, dict):
                    brand_name = brand.get("name", "")
                elif isinstance(brand, str):
                    brand_name = brand
                values = [
                    str(p.get("title",""))[:80],
                    p.get("platform_name", p.get("platform","")),
                    p.get("current_price", p.get("price", 0)),
                    p.get("original_price", 0),
                    p.get("average_score", p.get("rating", 0)),
                    p.get("monthly_sales", 0),
                    p.get("stock_quantity", 0),
                    brand_name,
                ]
                for col, v in enumerate(values, 1):
                    ws.cell(row=row_i, column=col, value=v)

            # Summary sheet
            ws2 = wb.create_sheet("分析摘要")
            analysis = data.get("analysis", {})
            ws2.cell(row=1, column=1, value="指标").font = Font(bold=True)
            ws2.cell(row=1, column=2, value="数值").font  = Font(bold=True)
            for i, (k, v) in enumerate(analysis.items(), 2):
                ws2.cell(row=i, column=1, value=str(k))
                ws2.cell(row=i, column=2, value=str(v))

            buf = io.BytesIO()
            wb.save(buf)
            return buf.getvalue()

        # fallback: CSV
        return self.to_csv(data)

    # ── CSV ──────────────────────────────────────────────────────────────────
    def to_csv(self, data: Dict[str, Any]) -> bytes:
        products = data.get("products", [])
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["商品名称","平台","价格","评分","销量","品牌"])
        for p in products[:1000]:
            brand = p.get("brand", {})
            brand_name = brand.get("name","") if isinstance(brand,dict) else str(brand)
            writer.writerow([
                p.get("title","")[:80],
                p.get("platform_name", p.get("platform","")),
                p.get("current_price", p.get("price",0)),
                p.get("average_score", p.get("rating",0)),
                p.get("monthly_sales",0),
                brand_name,
            ])
        return buf.getvalue().encode("utf-8-sig")

    # ── JSON ─────────────────────────────────────────────────────────────────
    def to_json(self, title: str, report_type: str,
                data: Dict[str, Any], generated_at: str) -> bytes:
        output = {
            "title":        title,
            "report_type":  report_type,
            "generated_at": generated_at,
            "item_count":   len(data.get("products", [])),
            "data":         data,
        }
        return json.dumps(output, ensure_ascii=False, indent=2,
                          default=str).encode("utf-8")

    # ── Markdown ─────────────────────────────────────────────────────────────
    def to_markdown(self, title: str, data: Dict[str, Any],
                    generated_at: str) -> bytes:
        products = data.get("products", [])
        analysis = data.get("analysis", {})
        summary  = data.get("summary", "")

        lines = [f"# {title}", f"\n> 生成时间: {generated_at}\n"]
        if summary:
            lines += ["\n## 摘要\n", summary, ""]
        if analysis:
            lines += ["\n## 关键指标\n"]
            for k, v in list(analysis.items())[:10]:
                lines.append(f"- **{k}**: {v}")
        if products:
            lines += ["\n## 商品列表\n",
                      "| 商品名称 | 平台 | 价格 | 评分 |",
                      "| --- | --- | --- | --- |"]
            for p in products[:30]:
                name = str(p.get("title",""))[:40].replace("|","｜")
                lines.append(
                    f"| {name} | {p.get('platform_name',p.get('platform',''))} "
                    f"| ¥{p.get('current_price',p.get('price',''))} "
                    f"| {p.get('average_score',p.get('rating',''))} |"
                )
        return "\n".join(lines).encode("utf-8")

    # ── dispatcher ───────────────────────────────────────────────────────────
    def format(self, fmt: str, title: str, report_type: str,
               data: Dict[str, Any], language: str) -> Dict[str, Any]:
        ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        if fmt == "html":
            raw = self.to_html(title, report_type, data, language, ts)
            return {"data": raw, "content_type": "text/html; charset=utf-8", "ext": "html"}
        elif fmt == "pdf":
            raw = self.to_pdf(title, data, ts)
            ct = "application/pdf" if _HAS_REPORTLAB else "text/html; charset=utf-8"
            return {"data": raw, "content_type": ct, "ext": "pdf"}
        elif fmt == "excel":
            raw = self.to_excel(title, data)
            ct = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" if _HAS_OPENPYXL else "text/csv"
            ext = "xlsx" if _HAS_OPENPYXL else "csv"
            return {"data": raw, "content_type": ct, "ext": ext}
        elif fmt == "csv":
            raw = self.to_csv(data)
            return {"data": raw, "content_type": "text/csv; charset=utf-8-sig", "ext": "csv"}
        elif fmt == "json":
            raw = self.to_json(title, report_type, data, ts)
            return {"data": raw, "content_type": "application/json", "ext": "json"}
        elif fmt == "markdown":
            raw = self.to_markdown(title, data, ts)
            return {"data": raw, "content_type": "text/markdown; charset=utf-8", "ext": "md"}
        else:
            raise ValueError(f"Unsupported format: {fmt}")



# ══════════════════════════════════════════════════════════════════════════════
# ReportService
# ══════════════════════════════════════════════════════════════════════════════
class ReportService:
    def __init__(self, config: ServiceConfig) -> None:
        self.config    = config
        self.engine    = create_async_engine(
            config.database_url,
            echo=config.debug,
            connect_args={"check_same_thread": False} if "sqlite" in config.database_url else {},
        )
        self.async_session = sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)
        self.redis     = RedisManager()
        self.formatter = ReportFormatter()
        self._http: Optional[aiohttp.ClientSession] = None
        self._active: int = 0
        Path(config.output_dir).mkdir(parents=True, exist_ok=True)

        # Prometheus metrics (reuse if already registered in same process)
        if _HAS_PROMETHEUS:
            def _counter(name, desc, labels):
                try: return Counter(name, desc, labels, registry=_RS_REGISTRY)
                except ValueError: return Counter(name, desc, labels, registry=CollectorRegistry())
            def _histogram(name, desc, labels):
                try: return Histogram(name, desc, labels, registry=_RS_REGISTRY)
                except ValueError: return Histogram(name, desc, labels, registry=CollectorRegistry())
            def _gauge(name, desc):
                try: return Gauge(name, desc, registry=_RS_REGISTRY)
                except ValueError: return Gauge(name, desc, registry=CollectorRegistry())
            self.ctr_generated  = _counter("rs_reports_generated_total",  "Reports generated", ["type","fmt","st"])
            self.ctr_delivered  = _counter("rs_reports_delivered_total",  "Delivered",          ["channel","st"])
            self.hist_gen_time  = _histogram("rs_generation_seconds",     "Gen time",           ["type"])
            self.gauge_active   = _gauge("rs_active_generations",         "Active")
        else:
            class _N:
                def labels(self, **_): return self
                def inc(self, *a, **k): pass
                def observe(self, *a, **k): pass
                def set(self, *a, **k): pass
            n = _N()
            self.ctr_generated = n; self.ctr_delivered = n
            self.hist_gen_time = n; self.gauge_active   = n

    # ── lifecycle ─────────────────────────────────────────────────────────────
    async def startup(self) -> None:
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        await self.redis.connect(self.config.redis_url)
        self._http = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=8))
        asyncio.create_task(self._expire_reports_task())
        logger.info(f"ReportService ready on {self.config.host}:{self.config.port}")

    async def shutdown(self) -> None:
        if self._http: await self._http.close()
        await self.engine.dispose()

    # ── helpers ───────────────────────────────────────────────────────────────
    def _now(self) -> datetime: return datetime.utcnow()

    def _gen_report_id(self) -> str: return f"rpt_{uuid.uuid4().hex[:16]}"

    def _gen_report_number(self, rt: str) -> str:
        codes = {
            "product_analysis":"PA","comparison":"CP","recommendation":"RC",
            "trend":"TR","b2b_analysis":"BA","b2c_brand_specified":"BS",
            "b2c_brand_unspecified":"BU","custom":"CU",
        }
        return f"{codes.get(rt,'RP')}{self._now().strftime('%Y%m%d%H%M%S')}"

    def _data_summary(self, data: Dict[str, Any]) -> Dict[str, Any]:
        products = data.get("products", [])
        summary: Dict[str, Any] = {
            "item_count":  len(products),
            "data_types":  list(data.keys()),
            "generated_at":self._now().isoformat(),
        }
        if products:
            prices = [float(p.get("current_price", p.get("price", 0)) or 0) for p in products]
            valid  = [x for x in prices if x > 0]
            if valid:
                summary["price_min"]  = min(valid)
                summary["price_max"]  = max(valid)
                summary["price_avg"]  = round(sum(valid)/len(valid), 2)
        return summary

    async def _record_activity(
        self, sess: AsyncSession, report_id: str,
        act_type: str, action: str, result: str = "success",
        performed_by: str = "system", by_type: str = "system",
        before: Optional[Dict] = None, after: Optional[Dict] = None,
        message: str = "", ip: Optional[str] = None,
    ) -> None:
        sess.add(ReportActivity(
            activity_id   = f"act_{uuid.uuid4().hex[:16]}",
            report_id     = report_id,
            activity_type = act_type,
            action        = action,
            result        = result,
            message       = message,
            performed_by  = performed_by,
            performed_by_type = by_type,
            before_state  = before,
            after_state   = after,
            ip_address    = ip,
            performed_at  = self._now(),
            created_at    = self._now(),
        ))

    async def _notify(self, report_id: str, user_id: str, event: str, data: Dict) -> None:
        if not self._http: return
        try:
            await self._http.post(
                f"{self.config.notify_url}/internal/notify",
                json={"report_id": report_id, "user_id": user_id, "event": event, "data": data},
            )
        except Exception as exc:
            logger.debug(f"Notify failed (non-fatal): {exc}")

    def _fmt_report(self, r: Report) -> Dict[str, Any]:
        return {
            "report_id":        r.report_id,
            "report_number":    r.report_number,
            "user_id":          r.user_id,
            "user_role":        r.user_role,
            "report_type":      r.report_type,
            "title":            r.title,
            "description":      r.description,
            "status":           r.status,
            "data_summary":     r.data_summary,
            "extra_metadata":   r.extra_metadata or {},
            "formats":          r.generated_formats or [],
            "files":            r.files or {},
            "access_count":     r.access_count,
            "download_count":   r.download_count,
            "generation_ms":    r.generation_ms,
            "expires_at":       r.expires_at.isoformat() if r.expires_at else None,
            "generated_at":     r.generated_at.isoformat() if r.generated_at else None,
            "created_at":       r.created_at.isoformat() if r.created_at else None,
            "updated_at":       r.updated_at.isoformat() if r.updated_at else None,
        }

    # ── core: generate_report ─────────────────────────────────────────────────
    async def generate_report(self, req: GenerateReportRequest) -> Dict[str, Any]:
        report_id  = self._gen_report_id()
        report_num = self._gen_report_number(req.report_type.value)
        now        = self._now()
        expires    = now + timedelta(days=req.expire_days)
        rt_val     = req.report_type.value
        title      = req.title or "分析报告"

        async with self.async_session() as sess:
            report = Report(
                report_id         = report_id,
                report_number     = report_num,
                user_id           = req.user_id or "anonymous",
                user_role         = "unknown",
                session_id        = req.session_id,
                report_type       = rt_val,
                language          = req.language,
                title             = title,
                description       = req.description,
                status            = ReportStatus.PENDING.value,
                raw_data          = {"data": req.data, "metadata": req.extra_metadata},
                data_summary      = self._data_summary(req.data),
                extra_metadata    = req.extra_metadata,
                template_id       = req.template_id,
                available_formats = req.formats,
                generated_formats = [],
                files             = {},
                expires_at        = expires,
                created_at        = now,
                updated_at        = now,
            )
            sess.add(report)
            await sess.flush()
            await self._record_activity(
                sess, report_id, "report", "create", "success",
                req.user_id or "anonymous", "user",
                after={"status": "pending", "title": title},
            )
            await sess.commit()

        # Kick off async generation
        asyncio.create_task(self._generate_async(report_id, req))
        return {
            "success":       True,
            "report_id":     report_id,
            "report_number": report_num,
            "status":        ReportStatus.PENDING.value,
            "message":       "报告生成任务已提交，请稍候查询结果",
            "check_url":     f"/api/v1/reports/{report_id}",
            "expires_at":    expires.isoformat(),
        }

    async def _generate_async(self, report_id: str, req: GenerateReportRequest) -> None:
        if self._active >= self.config.max_concurrent:
            await asyncio.sleep(2)
        self._active += 1
        self.gauge_active.set(self._active)
        t0 = time.perf_counter()
        try:
            await self._set_status(report_id, ReportStatus.PROCESSING.value)

            data    = req.data
            title   = req.title or "分析报告"
            rt_val  = req.report_type.value
            lang    = req.language

            # build a light analysis dict if not provided
            if "analysis" not in data:
                products = data.get("products", [])
                prices   = [float(p.get("current_price", p.get("price",0)) or 0) for p in products]
                valid    = [x for x in prices if x > 0]
                data["analysis"] = {
                    "商品总数":   len(products),
                    "价格最低":  f"¥{min(valid):.2f}" if valid else "N/A",
                    "价格最高":  f"¥{max(valid):.2f}" if valid else "N/A",
                    "均价":      f"¥{sum(valid)/len(valid):.2f}" if valid else "N/A",
                    "平均评分":  round(sum(float(p.get("average_score",p.get("rating",0)) or 0) for p in products)/max(len(products),1), 2),
                }

            files: Dict[str, Any] = {}
            gen_fmts: List[str]   = []
            out_dir = Path(self.config.output_dir) / report_id
            out_dir.mkdir(parents=True, exist_ok=True)

            for fmt in req.formats:
                try:
                    result = self.formatter.format(fmt, title, rt_val, data, lang)
                    raw  = result["data"]
                    ext  = result["ext"]
                    ct   = result["content_type"]
                    fname = f"{report_id}_{rt_val}.{ext}"
                    fpath = out_dir / fname
                    if isinstance(raw, bytes):
                        fpath.write_bytes(raw)
                    else:
                        fpath.write_text(str(raw), encoding="utf-8")
                    size = fpath.stat().st_size
                    files[fmt] = {
                        "filename":     fname,
                        "path":         str(fpath),
                        "url":          f"/api/v1/reports/{report_id}/download/{fmt}",
                        "size":         size,
                        "content_type": ct,
                    }
                    gen_fmts.append(fmt)
                    self.ctr_generated.labels(type=rt_val, fmt=fmt, st="success").inc()
                except Exception as exc:
                    logger.error(f"Format {fmt} failed for {report_id}: {exc}")
                    self.ctr_generated.labels(type=rt_val, fmt=fmt, st="failed").inc()

            gen_ms = int((time.perf_counter() - t0) * 1000)

            if gen_fmts:
                async with self.async_session() as sess:
                    await sess.execute(
                        sa_update(Report).where(Report.report_id == report_id)
                        .values(
                            status            = ReportStatus.COMPLETED.value,
                            generated_at      = self._now(),
                            generated_formats = gen_fmts,
                            files             = files,
                            generation_ms     = gen_ms,
                            updated_at        = self._now(),
                        )
                    )
                    await self._record_activity(
                        sess, report_id, "report", "generation_complete", "success",
                        "system", "system",
                        after={"formats": gen_fmts, "generation_ms": gen_ms},
                        message=f"已生成格式: {', '.join(gen_fmts)}, 耗时 {gen_ms}ms",
                    )
                    await sess.commit()
                self.hist_gen_time.labels(type=rt_val).observe(gen_ms / 1000)
                logger.info(f"Report {report_id} completed in {gen_ms}ms, formats={gen_fmts}")

                # Auto-deliver
                if req.delivery_channels:
                    asyncio.create_task(
                        self._deliver_report(report_id, req, gen_fmts)
                    )
            else:
                await self._set_status(report_id, ReportStatus.FAILED.value, "所有格式转换失败")

        except Exception as exc:
            logger.error(f"_generate_async error {report_id}: {exc}", exc_info=True)
            await self._set_status(report_id, ReportStatus.FAILED.value, str(exc)[:500])
        finally:
            self._active = max(0, self._active - 1)
            self.gauge_active.set(self._active)

    async def _set_status(self, report_id: str, st: str, error: str = "") -> None:
        async with self.async_session() as sess:
            vals: Dict[str, Any] = {"status": st, "updated_at": self._now()}
            if error:
                vals["error_message"] = error
            await sess.execute(sa_update(Report).where(Report.report_id == report_id).values(**vals))
            await sess.commit()

    # ── deliver ───────────────────────────────────────────────────────────────
    async def _deliver_report(self, report_id: str, req: GenerateReportRequest,
                              gen_fmts: List[str]) -> None:
        chosen_fmt = next((f for f in req.formats if f in gen_fmts), gen_fmts[0] if gen_fmts else None)
        if not chosen_fmt:
            return
        for channel in req.delivery_channels:
            recipients = req.recipients if req.recipients else [req.user_id or "web_portal"]
            for recipient in recipients:
                del_id = f"del_{uuid.uuid4().hex[:16]}"
                now    = self._now()
                async with self.async_session() as sess:
                    sess.add(ReportDelivery(
                        delivery_id = del_id,
                        report_id   = report_id,
                        channel     = channel,
                        recipient   = recipient,
                        fmt         = chosen_fmt,
                        message     = req.description,
                        status      = DeliveryStatus.SENDING.value,
                        created_at  = now,
                        updated_at  = now,
                    ))
                    await sess.commit()

                # Simulate delivery (stub for email/wechat/sms)
                success = True
                err_msg = ""
                try:
                    if channel == "email" and self._http:
                        await self._http.post(
                            f"{self.config.notify_url}/internal/email",
                            json={"to": recipient, "subject": req.title, "report_id": report_id},
                        )
                    # Other channels (wechat, sms, api) would use their SDKs here
                except Exception as exc:
                    success = False; err_msg = str(exc)

                async with self.async_session() as sess:
                    await sess.execute(
                        sa_update(ReportDelivery).where(ReportDelivery.delivery_id == del_id)
                        .values(
                            status      = DeliveryStatus.DELIVERED.value if success else DeliveryStatus.FAILED.value,
                            sent_at     = self._now() if success else None,
                            delivered_at= self._now() if success else None,
                            error_message = err_msg or None,
                            updated_at  = self._now(),
                        )
                    )
                    await sess.commit()
                self.ctr_delivered.labels(
                    channel=channel, st="success" if success else "failed"
                ).inc()

    # ── CRUD: get / list ──────────────────────────────────────────────────────
    async def get_report(self, report_id: str,
                         user_id: Optional[str] = None,
                         increment_view: bool = True) -> Dict[str, Any]:
        async with self.async_session() as sess:
            stmt = select(Report).where(Report.report_id == report_id)
            if user_id:
                stmt = stmt.where(Report.user_id == user_id)
            report = await sess.scalar(stmt)
            if not report:
                raise HTTPException(404, "报告不存在")
            if increment_view:
                await sess.execute(
                    sa_update(Report).where(Report.report_id == report_id)
                    .values(access_count=Report.access_count + 1, updated_at=self._now())
                )
                await self._record_activity(
                    sess, report_id, "report", "view", "success",
                    user_id or "anonymous", "user",
                )
                await sess.commit()
                await sess.refresh(report)

            # fetch deliveries
            dels = (await sess.scalars(
                select(ReportDelivery).where(ReportDelivery.report_id == report_id).limit(20)
            )).all()

        delivery_list = [
            {"delivery_id": d.delivery_id, "channel": d.channel,
             "recipient": d.recipient, "fmt": d.fmt,
             "status": d.status, "sent_at": d.sent_at.isoformat() if d.sent_at else None}
            for d in dels
        ]
        return {
            "success":    True,
            "report":     self._fmt_report(report),
            "deliveries": delivery_list,
        }

    async def list_reports(
        self, user_id: str,
        report_type: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 1, page_size: int = 20,
        sort_by: str = "created_at", sort_order: str = "desc",
    ) -> Dict[str, Any]:
        async with self.async_session() as sess:
            conds = [Report.user_id == user_id]
            if report_type: conds.append(Report.report_type == report_type)
            if status:       conds.append(Report.status == status)
            total = await sess.scalar(select(func.count(Report.id)).where(and_(*conds))) or 0
            sort_col  = getattr(Report, sort_by, Report.created_at)
            direction = asc if sort_order == "asc" else desc
            rows = (await sess.scalars(
                select(Report).where(and_(*conds))
                .order_by(direction(sort_col))
                .offset((page-1)*page_size).limit(page_size)
            )).all()
        return {"success":True,"total":total,"page":page,"page_size":page_size,
                "reports":[self._fmt_report(r) for r in rows]}

    async def delete_report(self, report_id: str, user_id: str) -> Dict[str, Any]:
        async with self.async_session() as sess:
            report = await sess.scalar(
                select(Report).where(Report.report_id == report_id, Report.user_id == user_id)
            )
            if not report:
                raise HTTPException(404, "报告不存在")
            # soft-delete: mark expired
            await sess.execute(
                sa_update(Report).where(Report.report_id == report_id)
                .values(status=ReportStatus.EXPIRED.value, updated_at=self._now())
            )
            await self._record_activity(
                sess, report_id, "report", "delete", "success", user_id, "user"
            )
            await sess.commit()
        return {"success": True, "report_id": report_id, "status": ReportStatus.EXPIRED.value}

    # ── download ──────────────────────────────────────────────────────────────
    async def get_download_stream(self, report_id: str, fmt: str,
                                  user_id: Optional[str] = None):
        async with self.async_session() as sess:
            stmt = select(Report).where(Report.report_id == report_id)
            if user_id:
                stmt = stmt.where(Report.user_id == user_id)
            report = await sess.scalar(stmt)
            if not report:
                raise HTTPException(404, "报告不存在")
            if report.status != ReportStatus.COMPLETED.value:
                raise HTTPException(400, f"报告状态为 {report.status}，不可下载")

            file_info = (report.files or {}).get(fmt)
            if not file_info:
                raise HTTPException(404, f"格式 {fmt} 不存在")

            fpath = Path(file_info["path"])
            if not fpath.exists():
                raise HTTPException(404, "报告文件已删除")

            await sess.execute(
                sa_update(Report).where(Report.report_id == report_id)
                .values(download_count=Report.download_count + 1, updated_at=self._now())
            )
            await sess.commit()

        content = fpath.read_bytes()
        ct      = file_info.get("content_type", "application/octet-stream")
        fname   = file_info.get("filename", f"report.{fmt}")
        return content, ct, fname

    # ── template CRUD ─────────────────────────────────────────────────────────
    async def create_template(self, req: CreateTemplateRequest, created_by: str) -> Dict[str, Any]:
        async with self.async_session() as sess:
            existing = await sess.scalar(
                select(ReportTemplate).where(ReportTemplate.template_id == req.template_id)
            )
            if existing:
                raise HTTPException(409, "模板ID已存在")
            now = self._now()
            tmpl = ReportTemplate(
                template_id = req.template_id,
                name        = req.name,
                description = req.description,
                report_type = req.report_type,
                language    = req.language,
                fmt         = req.fmt,
                version     = req.version,
                content     = req.content,
                styles      = req.styles,
                variables   = req.variables,
                is_active   = True,
                is_system   = False,
                created_by  = created_by,
                updated_by  = created_by,
                created_at  = now,
                updated_at  = now,
            )
            sess.add(tmpl)
            await sess.commit()
        return {"success": True, "template_id": req.template_id, "name": req.name}

    async def list_templates(self, report_type: Optional[str] = None,
                             fmt: Optional[str] = None) -> Dict[str, Any]:
        async with self.async_session() as sess:
            conds = [ReportTemplate.is_active == True]
            if report_type: conds.append(ReportTemplate.report_type == report_type)
            if fmt:         conds.append(ReportTemplate.fmt == fmt)
            rows = (await sess.scalars(
                select(ReportTemplate).where(and_(*conds)).order_by(desc(ReportTemplate.created_at))
            )).all()
        return {
            "success": True,
            "total":   len(rows),
            "templates": [
                {"template_id": t.template_id, "name": t.name, "report_type": t.report_type,
                 "fmt": t.fmt, "language": t.language, "version": t.version,
                 "usage_count": t.usage_count, "is_system": t.is_system,
                 "created_at": t.created_at.isoformat() if t.created_at else None}
                for t in rows
            ],
        }

    # ── activities ────────────────────────────────────────────────────────────
    async def get_activities(self, report_id: str) -> Dict[str, Any]:
        async with self.async_session() as sess:
            rows = (await sess.scalars(
                select(ReportActivity).where(ReportActivity.report_id == report_id)
                .order_by(desc(ReportActivity.performed_at)).limit(50)
            )).all()
        return {
            "success":    True,
            "report_id":  report_id,
            "activities": [
                {"activity_id": a.activity_id, "activity_type": a.activity_type,
                 "action": a.action, "result": a.result, "message": a.message,
                 "performed_by": a.performed_by, "performed_by_type": a.performed_by_type,
                 "performed_at": a.performed_at.isoformat() if a.performed_at else None}
                for a in rows
            ],
        }

    # ── stats ─────────────────────────────────────────────────────────────────
    async def get_stats(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        async with self.async_session() as sess:
            conds = [Report.user_id == user_id] if user_id else []
            total     = await sess.scalar(select(func.count(Report.id)).where(*conds)) or 0
            completed = await sess.scalar(select(func.count(Report.id)).where(*conds, Report.status == "completed")) or 0
            failed    = await sess.scalar(select(func.count(Report.id)).where(*conds, Report.status == "failed")) or 0
            downloads = await sess.scalar(select(func.sum(Report.download_count)).where(*conds)) or 0
            views     = await sess.scalar(select(func.sum(Report.access_count)).where(*conds)) or 0
        return {
            "success":         True,
            "total_reports":   total,
            "completed":       completed,
            "failed":          failed,
            "pending":         total - completed - failed,
            "total_downloads": int(downloads),
            "total_views":     int(views),
        }

    # ── background tasks ──────────────────────────────────────────────────────
    async def _expire_reports_task(self) -> None:
        while True:
            await asyncio.sleep(3600)
            try:
                now = self._now()
                async with self.async_session() as sess:
                    await sess.execute(
                        sa_update(Report)
                        .where(Report.expires_at <= now,
                               Report.status == ReportStatus.COMPLETED.value)
                        .values(status=ReportStatus.EXPIRED.value, updated_at=now)
                    )
                    await sess.commit()
            except Exception as exc:
                logger.error(f"expire_reports_task: {exc}")


# ══════════════════════════════════════════════════════════════════════════════
# FastAPI app + routes
# ══════════════════════════════════════════════════════════════════════════════
def _get_svc(request: Request) -> ReportService:
    return request.app.state.service


def create_app(config: Optional[ServiceConfig] = None) -> FastAPI:
    cfg = config or ServiceConfig()
    svc = ReportService(cfg)

    app = FastAPI(
        title="Report Service",
        description="业务逻辑层 – 报告服务 (Part 8)",
        version="1.0.0",
    )
    app.add_middleware(CORSMiddleware, allow_origins=["*"],
                       allow_methods=["*"], allow_headers=["*"])
    app.state.service = svc

    @app.on_event("startup")
    async def _up() -> None:
        await svc.startup()
        await _seed_demo_reports(svc)

    @app.on_event("shutdown")
    async def _down() -> None:
        await svc.shutdown()

    # ── info / health ─────────────────────────────────────────────────────────
    @app.get("/")
    async def root():
        return {
            "service": "report_service",
            "version": "1.0.0",
            "formatters": {
                "html":     "jinja2" if _HAS_JINJA2 else "builtin",
                "pdf":      "reportlab" if _HAS_REPORTLAB else ("weasyprint" if _HAS_WEASYPRINT else "html-fallback"),
                "excel":    "openpyxl" if _HAS_OPENPYXL else "csv-fallback",
                "csv":      "builtin",
                "json":     "builtin",
                "markdown": "builtin",
            },
        }

    @app.get("/health")
    async def health():
        return {"status": "UP", "service": "report_service", "active_generations": svc._active}

    @app.get("/metrics", response_class=PlainTextResponse)
    async def metrics():
        if _HAS_PROMETHEUS:
            return generate_latest(_RS_REGISTRY).decode()
        return "# prometheus_client not available\n"

    # ── reports ───────────────────────────────────────────────────────────────
    @app.post("/api/v1/reports", status_code=status.HTTP_201_CREATED)
    async def generate_report(req: GenerateReportRequest,
                              svc: ReportService = Depends(_get_svc)):
        return await svc.generate_report(req)

    @app.get("/api/v1/reports")
    async def list_reports(
        user_id:     str           = Query(...),
        report_type: Optional[str] = Query(None),
        rpt_status:  Optional[str] = Query(None, alias="status"),
        page:        int           = Query(1, ge=1),
        page_size:   int           = Query(20, ge=1, le=100),
        sort_by:     str           = Query("created_at"),
        sort_order:  str           = Query("desc"),
        svc: ReportService = Depends(_get_svc),
    ):
        return await svc.list_reports(user_id, report_type, rpt_status,
                                      page, page_size, sort_by, sort_order)

    @app.get("/api/v1/reports/{report_id}")
    async def get_report(
        report_id: str,
        user_id:   Optional[str] = Query(None),
        svc: ReportService = Depends(_get_svc),
    ):
        return await svc.get_report(report_id, user_id)

    @app.delete("/api/v1/reports/{report_id}")
    async def delete_report(
        report_id: str,
        user_id:   str = Query(...),
        svc: ReportService = Depends(_get_svc),
    ):
        return await svc.delete_report(report_id, user_id)

    @app.get("/api/v1/reports/{report_id}/activities")
    async def get_activities(report_id: str, svc: ReportService = Depends(_get_svc)):
        return await svc.get_activities(report_id)

    # ── download ──────────────────────────────────────────────────────────────
    @app.get("/api/v1/reports/{report_id}/download/{fmt}")
    async def download_report(
        report_id: str, fmt: str,
        user_id:   Optional[str] = Query(None),
        svc: ReportService = Depends(_get_svc),
    ):
        content, ct, fname = await svc.get_download_stream(report_id, fmt, user_id)
        return StreamingResponse(
            io.BytesIO(content),
            media_type=ct,
            headers={"Content-Disposition": f'attachment; filename="{fname}"'},
        )

    # ── deliver ───────────────────────────────────────────────────────────────
    @app.post("/api/v1/reports/{report_id}/deliver")
    async def deliver_report(
        report_id: str, req: DeliverReportRequest,
        svc: ReportService = Depends(_get_svc),
    ):
        req_gen = GenerateReportRequest(
            report_type        = ReportType.CUSTOM,
            data               = {},
            delivery_channels  = req.delivery_channels,
            recipients         = req.recipients,
        )
        asyncio.create_task(svc._deliver_report(
            report_id, req_gen,
            [req.fmt] if req.fmt else ["html", "json"]
        ))
        return {"success": True, "report_id": report_id, "message": "交付任务已提交"}

    # ── templates ─────────────────────────────────────────────────────────────
    @app.post("/api/v1/report-templates", status_code=status.HTTP_201_CREATED)
    async def create_template(
        req: CreateTemplateRequest,
        created_by: str = Query(default="user"),
        svc: ReportService = Depends(_get_svc),
    ):
        return await svc.create_template(req, created_by)

    @app.get("/api/v1/report-templates")
    async def list_templates(
        report_type: Optional[str] = Query(None),
        fmt:         Optional[str] = Query(None),
        svc: ReportService = Depends(_get_svc),
    ):
        return await svc.list_templates(report_type, fmt)

    # ── stats ─────────────────────────────────────────────────────────────────
    @app.get("/api/v1/stats/reports")
    async def stats(
        user_id: Optional[str] = Query(None),
        svc: ReportService = Depends(_get_svc),
    ):
        return await svc.get_stats(user_id)

    return app


# ══════════════════════════════════════════════════════════════════════════════
# Seed data
# ══════════════════════════════════════════════════════════════════════════════
async def _seed_demo_reports(svc: ReportService) -> None:
    async with svc.async_session() as sess:
        if await sess.scalar(select(func.count(Report.id))):
            return  # already seeded

    demo_products = [
        {"title": "联想ThinkPad E14 Gen5", "platform_name": "天猫",
         "current_price": 5299, "original_price": 5999, "average_score": 4.8,
         "monthly_sales": 12500, "stock_quantity": 485,
         "brand": {"name": "联想"}, "platform": "tmall"},
        {"title": "Apple MacBook Pro 14寸", "platform_name": "京东",
         "current_price": 14999, "original_price": 16999, "average_score": 4.9,
         "monthly_sales": 3200, "stock_quantity": 120,
         "brand": {"name": "苹果"}, "platform": "jd"},
        {"title": "华为MateBook 16s", "platform_name": "华为商城",
         "current_price": 8999, "original_price": 9999, "average_score": 4.7,
         "monthly_sales": 6800, "stock_quantity": 350,
         "brand": {"name": "华为"}, "platform": "huawei"},
    ]
    demo_data = {
        "products": demo_products,
        "summary":  "电脑办公类商品比较分析，涵盖联想、苹果、华为三大品牌旗舰产品",
        "analysis": {"商品总数":"3","价格范围":"¥5299~¥14999","均价":"¥9765.67","平均评分":"4.80"},
    }

    req = GenerateReportRequest(
        report_type = ReportType.PRODUCT_ANALYSIS,
        data        = demo_data,
        formats     = ["html", "json", "csv"],
        user_id     = "user_demo_001",
        title       = "电脑商品分析报告 (演示)",
        description = "包含联想/苹果/华为三款热门笔记本电脑的横向比较",
    )
    result = await svc.generate_report(req)
    logger.info(f"Demo report seeded: {result['report_id']}")


# ══════════════════════════════════════════════════════════════════════════════
# Entry point
# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import uvicorn
    cfg = ServiceConfig()
    app = create_app(cfg)
    uvicorn.run(app, host=cfg.host, port=cfg.port, log_level="info")
