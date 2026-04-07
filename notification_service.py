"""
notification_service.py — Production-grade Notification Service (Part 10)
Async FastAPI microservice for multi-channel notification management.
Channels: Email, SMS, WeChat, Push, Webhook, In-App, Slack, Telegram
"""

from __future__ import annotations

import asyncio
import base64
import csv
import hashlib
import io
import json
import logging
import os
import re
import secrets
import smtplib
import time
import uuid
import xml.etree.ElementTree as ET
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

# ── optional deps ──────────────────────────────────────────────────────────────
try:
    import aiosmtplib as _aiosmtplib
    _HAS_AIOSMTPLIB = True
except ImportError:
    _HAS_AIOSMTPLIB = False

try:
    import aio_pika as _aio_pika
    _HAS_AMQP = True
except ImportError:
    _HAS_AMQP = False

try:
    import redis.asyncio as _redis_mod
    _HAS_REDIS = True
except ImportError:
    _HAS_REDIS = False

try:
    import aiohttp as _aiohttp
    _HAS_AIOHTTP = True
except ImportError:
    _HAS_AIOHTTP = False

try:
    import jinja2 as _jinja2
    _HAS_JINJA2 = True
except ImportError:
    _HAS_JINJA2 = False

try:
    import yaml as _yaml_mod
    _HAS_YAML = True
except ImportError:
    _HAS_YAML = False

try:
    import qrcode as _qrcode
    _HAS_QRCODE = True
except ImportError:
    _HAS_QRCODE = False

try:
    import aiofiles as _aiofiles
    _HAS_AIOFILES = True
except ImportError:
    _HAS_AIOFILES = False

try:
    from prometheus_client import (
        CollectorRegistry, Counter, Gauge, Histogram, Summary,
        generate_latest, CONTENT_TYPE_LATEST,
    )
    _HAS_PROMETHEUS = True
except ImportError:
    _HAS_PROMETHEUS = False

from fastapi import (
    BackgroundTasks, Depends, FastAPI, HTTPException, Query,
    WebSocket, WebSocketDisconnect,
)
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy import (
    Boolean, Column, DateTime, Float, Index, Integer, String, Text, JSON,
    UniqueConstraint, and_, func, or_, select, update,
)
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# ── logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("notification_service")

# ── enums ──────────────────────────────────────────────────────────────────────
class NotificationType(str, Enum):
    EMAIL    = "email"
    SMS      = "sms"
    WECHAT   = "wechat"
    PUSH     = "push"
    IN_APP   = "in_app"
    WEBHOOK  = "webhook"
    VOICE    = "voice"
    SLACK    = "slack"
    TELEGRAM = "telegram"

class NotificationStatus(str, Enum):
    PENDING    = "pending"
    PROCESSING = "processing"
    SENT       = "sent"
    DELIVERED  = "delivered"
    READ       = "read"
    FAILED     = "failed"
    CANCELLED  = "cancelled"
    BOUNCED    = "bounced"

class PriorityLevel(int, Enum):
    LOW    = 0
    NORMAL = 1
    HIGH   = 2
    URGENT = 3

class ChannelStatus(str, Enum):
    ACTIVE      = "active"
    INACTIVE    = "inactive"
    DISABLED    = "disabled"
    MAINTENANCE = "maintenance"

class TemplateType(str, Enum):
    SYSTEM         = "system"
    USER           = "user"
    TRANSACTIONAL  = "transactional"
    MARKETING      = "marketing"
    ALERT          = "alert"
    VERIFICATION   = "verification"

class ContentType(str, Enum):
    PLAIN_TEXT = "plain_text"
    HTML       = "html"
    MARKDOWN   = "markdown"
    JSON       = "json"
    XML        = "xml"

class SendStrategy(str, Enum):
    IMMEDIATE = "immediate"
    DELAYED   = "delayed"
    BATCH     = "batch"
    SCHEDULED = "scheduled"

# ── service config ─────────────────────────────────────────────────────────────
class ServiceConfig:
    DB_URL:         str   = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./notification_service.db")
    REDIS_URL:      str   = os.getenv("REDIS_URL", "redis://localhost:6379/4")
    RABBITMQ_URL:   str   = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
    HOST:           str   = os.getenv("HOST", "0.0.0.0")
    PORT:           int   = int(os.getenv("PORT", "8006"))
    SECRET_KEY:     str   = os.getenv("SECRET_KEY", secrets.token_hex(32))
    # Email
    SMTP_HOST:      str   = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT:      int   = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER:      str   = os.getenv("SMTP_USER", "")
    SMTP_PASS:      str   = os.getenv("SMTP_PASS", "")
    EMAIL_FROM:     str   = os.getenv("EMAIL_FROM", "noreply@example.com")
    EMAIL_NAME:     str   = os.getenv("EMAIL_NAME", "通知服务")
    # SMS
    SMS_PROVIDER:   str   = os.getenv("SMS_PROVIDER", "stub")
    SMS_SECRET_ID:  str   = os.getenv("SMS_SECRET_ID", "")
    SMS_SECRET_KEY: str   = os.getenv("SMS_SECRET_KEY", "")
    SMS_SIGN:       str   = os.getenv("SMS_SIGN", "多模态商品识别")
    SMS_APP_ID:     str   = os.getenv("SMS_APP_ID", "")
    # WeChat
    WX_APP_ID:      str   = os.getenv("WX_APP_ID", "")
    WX_APP_SECRET:  str   = os.getenv("WX_APP_SECRET", "")
    # Push (FCM)
    FCM_SERVER_KEY: str   = os.getenv("FCM_SERVER_KEY", "")
    # Queue
    QUEUE_MAX_RETRY:int   = int(os.getenv("QUEUE_MAX_RETRY", "3"))
    # Limits
    MAX_RECIPIENTS: int   = int(os.getenv("MAX_RECIPIENTS", "500"))
    CACHE_TTL:      int   = int(os.getenv("CACHE_TTL", "300"))
    RATE_LIMIT_MINUTE: int = int(os.getenv("RATE_LIMIT_MINUTE", "100"))

# ── ORM ────────────────────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    pass

def _now() -> datetime:
    return datetime.now(timezone.utc)

class Notification(Base):
    __tablename__ = "t_notifications"

    id                 = Column(Integer, primary_key=True, autoincrement=True)
    notification_id    = Column(String(64), unique=True, nullable=False)
    notification_type  = Column(String(20), nullable=False)
    status             = Column(String(20), nullable=False, default="pending")
    priority           = Column(Integer, nullable=False, default=1)
    channel            = Column(String(20), nullable=False)
    title              = Column(String(500), nullable=False)
    content            = Column(Text, nullable=False)
    content_type       = Column(String(20), nullable=False, default="html")
    summary            = Column(Text, nullable=True)
    recipients         = Column("notif_recipients",   JSON, nullable=False)
    recipient_count    = Column(Integer, nullable=False, default=1)
    keywords           = Column("notif_keywords",     JSON, nullable=True)
    notif_data         = Column("notif_data",         JSON, nullable=True)
    template_id        = Column(String(64), nullable=True)
    template_data      = Column("notif_tmpl_data",    JSON, nullable=True)
    attachments        = Column("notif_attachments",  JSON, nullable=True)
    send_strategy      = Column(String(20), nullable=False, default="immediate")
    sender_id          = Column(String(64), nullable=True)
    sender_type        = Column(String(20), nullable=False, default="system")
    tracking_enabled   = Column(Boolean, nullable=False, default=True)
    tracking_id        = Column(String(64), unique=True, nullable=True)
    callback_url       = Column(String(500), nullable=True)
    channel_message_id = Column(String(100), nullable=True)
    retry_count        = Column(Integer, nullable=False, default=0)
    max_retries        = Column(Integer, nullable=False, default=3)
    last_error         = Column(Text, nullable=True)
    error_history      = Column("notif_errors",       JSON, nullable=True)
    extra_metadata     = Column("notif_metadata",     JSON, nullable=True)
    created_at         = Column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at         = Column(DateTime(timezone=True), nullable=False, default=_now, onupdate=_now)
    schedule_time      = Column(DateTime(timezone=True), nullable=True)
    expire_time        = Column(DateTime(timezone=True), nullable=True)
    sent_at            = Column(DateTime(timezone=True), nullable=True)
    delivered_at       = Column(DateTime(timezone=True), nullable=True)
    read_at            = Column(DateTime(timezone=True), nullable=True)
    failed_at          = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_notif_status_type",  "status", "notification_type"),
        Index("idx_notif_channel",      "channel", "status"),
        Index("idx_notif_priority",     "priority", "created_at"),
        Index("idx_notif_schedule",     "schedule_time", "status"),
        Index("idx_notif_sender",       "sender_id", "created_at"),
        Index("idx_notif_tracking",     "tracking_id"),
    )

class NotificationLog(Base):
    __tablename__ = "t_notification_logs"

    id               = Column(Integer, primary_key=True, autoincrement=True)
    log_id           = Column(String(64), unique=True, nullable=False)
    notification_id  = Column(String(64), nullable=False)
    log_type         = Column(String(20), nullable=False)
    log_action       = Column(String(50), nullable=False)
    log_message      = Column(Text, nullable=True)
    recipient_id     = Column(String(64), nullable=True)
    channel          = Column(String(20), nullable=False)
    channel_msg_id   = Column(String(100), nullable=True)
    extra_metadata   = Column("log_metadata", JSON, nullable=True)
    created_at       = Column(DateTime(timezone=True), nullable=False, default=_now)

    __table_args__ = (
        Index("idx_log_notif",    "notification_id", "log_type"),
        Index("idx_log_time",     "created_at"),
    )

class NotificationTemplate(Base):
    __tablename__ = "t_notification_templates"

    id                = Column(Integer, primary_key=True, autoincrement=True)
    template_id       = Column(String(64), unique=True, nullable=False)
    name              = Column(String(200), nullable=False)
    notification_type = Column(String(20), nullable=False)
    template_type     = Column(String(20), nullable=False)
    language          = Column(String(10), nullable=False, default="zh_CN")
    subject_template  = Column(Text, nullable=False)
    content_template  = Column(Text, nullable=False)
    content_type      = Column(String(20), nullable=False, default="html")
    variables         = Column("tmpl_variables",   JSON, nullable=True)
    description       = Column(Text, nullable=True)
    tags              = Column("tmpl_tags",        JSON, nullable=True)
    channel_config    = Column("tmpl_chan_config",  JSON, nullable=True)
    is_active         = Column(Boolean, nullable=False, default=True)
    usage_count       = Column(Integer, nullable=False, default=0)
    last_used_at      = Column(DateTime(timezone=True), nullable=True)
    created_by        = Column(String(64), nullable=False, default="system")
    updated_by        = Column(String(64), nullable=False, default="system")
    created_at        = Column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at        = Column(DateTime(timezone=True), nullable=False, default=_now, onupdate=_now)

    __table_args__ = (
        UniqueConstraint("notification_type", "template_type", "language", "name",
                         name="uq_tmpl_type_lang_name"),
        Index("idx_tmpl_type_active", "notification_type", "is_active"),
    )

class ChannelConfig(Base):
    __tablename__ = "t_channel_configs"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    config_id     = Column(String(64), unique=True, nullable=False)
    channel       = Column(String(20), nullable=False)
    provider      = Column(String(50), nullable=False)
    config_name   = Column(String(100), nullable=False)
    config_data   = Column("chan_config_data",  JSON, nullable=False)
    config_hash   = Column(String(64), nullable=False)
    is_active     = Column(Boolean, nullable=False, default=True)
    status        = Column(String(20), nullable=False, default="active")
    last_check    = Column(DateTime(timezone=True), nullable=True)
    check_result  = Column("chan_check_result", JSON, nullable=True)
    success_count = Column(Integer, nullable=False, default=0)
    failure_count = Column(Integer, nullable=False, default=0)
    total_count   = Column(Integer, nullable=False, default=0)
    extra_metadata = Column("chan_metadata",    JSON, nullable=True)
    created_by    = Column(String(64), nullable=False, default="system")
    updated_by    = Column(String(64), nullable=False, default="system")
    created_at    = Column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at    = Column(DateTime(timezone=True), nullable=False, default=_now, onupdate=_now)

    __table_args__ = (
        UniqueConstraint("channel", "provider", "config_name", name="uq_chan_prov_name"),
        Index("idx_chan_status", "channel", "status", "is_active"),
    )

# ── Pydantic v2 models ─────────────────────────────────────────────────────────
_EMAIL_RE = re.compile(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$')
_PHONE_RE = re.compile(r'^1[3-9]\d{9}$')

class Recipient(BaseModel):
    recipient_id:    str
    recipient_type:  str = "user"
    name:            Optional[str] = None
    email:           Optional[str] = None
    phone:           Optional[str] = None
    wechat_openid:   Optional[str] = None
    device_token:    Optional[str] = None
    user_id:         Optional[str] = None
    webhook_url:     Optional[str] = None
    slack_channel:   Optional[str] = None
    telegram_chat_id: Optional[str] = None
    extra_metadata:  Optional[Dict[str, Any]] = None

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        if v and not _EMAIL_RE.match(v):
            raise ValueError("邮箱格式不正确")
        return v

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if v and not _PHONE_RE.match(v):
            raise ValueError("手机号格式不正确 (mainland China 1[3-9]xxxxxxxxx)")
        return v

class Attachment(BaseModel):
    filename:     str
    content:      str  # base64-encoded bytes
    content_type: str = "application/octet-stream"
    encoding:     str = "base64"

    @field_validator("encoding")
    @classmethod
    def validate_encoding(cls, v: str) -> str:
        if v not in ("base64", "binary", "url"):
            raise ValueError("encoding must be base64/binary/url")
        return v

class NotificationContent(BaseModel):
    title:        str
    content:      str
    content_type: ContentType = ContentType.HTML
    summary:      Optional[str] = None
    keywords:     List[str] = Field(default_factory=list)
    data:         Dict[str, Any] = Field(default_factory=dict)

class SendNotificationRequest(BaseModel):
    notification_type: NotificationType
    recipients:        List[Recipient]
    content:           NotificationContent
    channel:           Optional[str] = None
    template_id:       Optional[str] = None
    template_data:     Dict[str, Any] = Field(default_factory=dict)
    attachments:       List[Attachment] = Field(default_factory=list)
    priority:          PriorityLevel = PriorityLevel.NORMAL
    send_strategy:     SendStrategy = SendStrategy.IMMEDIATE
    schedule_time:     Optional[datetime] = None
    expire_time:       Optional[datetime] = None
    tracking_enabled:  bool = True
    callback_url:      Optional[str] = None
    extra_metadata:    Dict[str, Any] = Field(default_factory=dict)
    sender_id:         Optional[str] = None
    sender_type:       str = "system"

    @field_validator("recipients")
    @classmethod
    def validate_recipients_not_empty(cls, v: List[Recipient]) -> List[Recipient]:
        if not v:
            raise ValueError("至少需要一个收件人")
        if len(v) > ServiceConfig.MAX_RECIPIENTS:
            raise ValueError(f"收件人不能超过 {ServiceConfig.MAX_RECIPIENTS}")
        return v

    @model_validator(mode='after')
    def check_channel_fields(self) -> "SendNotificationRequest":
        ntype = self.notification_type
        for r in self.recipients:
            if ntype == NotificationType.EMAIL and not r.email:
                raise ValueError(f"邮件通知需要收件人邮箱 (recipient_id={r.recipient_id})")
            if ntype == NotificationType.SMS and not r.phone:
                raise ValueError(f"短信通知需要收件人手机 (recipient_id={r.recipient_id})")
            if ntype == NotificationType.WECHAT and not r.wechat_openid:
                raise ValueError(f"微信通知需要收件人OpenID (recipient_id={r.recipient_id})")
            if ntype == NotificationType.PUSH and not r.device_token:
                raise ValueError(f"推送通知需要设备令牌 (recipient_id={r.recipient_id})")
            if ntype == NotificationType.WEBHOOK and not r.webhook_url:
                raise ValueError(f"Webhook通知需要收件人URL (recipient_id={r.recipient_id})")
        return self

class NotificationTemplateCreate(BaseModel):
    template_id:       str
    name:              str
    notification_type: NotificationType
    template_type:     TemplateType
    language:          str = "zh_CN"
    subject_template:  str
    content_template:  str
    content_type:      ContentType
    variables:         List[str] = Field(default_factory=list)
    description:       Optional[str] = None
    tags:              List[str] = Field(default_factory=list)
    channel_config:    Dict[str, Any] = Field(default_factory=dict)
    is_active:         bool = True
    created_by:        str = "system"

    @field_validator("template_id")
    @classmethod
    def validate_template_id(cls, v: str) -> str:
        if not re.match(r'^[a-zA-Z0-9_.\-]+$', v):
            raise ValueError("template_id 只能含 [a-zA-Z0-9_.-]")
        return v

class NotificationQuery(BaseModel):
    notification_type: Optional[str] = None
    recipient_id:      Optional[str] = None
    status:            Optional[str] = None
    channel:           Optional[str] = None
    template_id:       Optional[str] = None
    sender_id:         Optional[str] = None
    start_time:        Optional[datetime] = None
    end_time:          Optional[datetime] = None
    page:              int = Field(1, ge=1)
    page_size:         int = Field(20, ge=1, le=200)
    sort_order:        str = "desc"

class ChannelTestRequest(BaseModel):
    channel:   str
    recipient: Recipient
    content:   NotificationContent

# ── TemplateEngine ─────────────────────────────────────────────────────────────
class TemplateEngine:
    """Jinja2-based template engine with stdlib fallback."""

    def __init__(self):
        if _HAS_JINJA2:
            self._env = _jinja2.Environment(
                loader=_jinja2.BaseLoader(),
                autoescape=_jinja2.select_autoescape(["html", "xml"]),
                trim_blocks=True,
                lstrip_blocks=True,
            )
            self._register_filters()
        else:
            self._env = None

    def _register_filters(self) -> None:
        if not self._env:
            return

        def fmt_date(v, fmt="%Y-%m-%d %H:%M:%S"):
            return v.strftime(fmt) if isinstance(v, datetime) else str(v)

        def fmt_number(v, dec=2):
            try:
                return f"{float(v):,.{dec}f}"
            except Exception:
                return str(v)

        def truncate(v, length=100, suffix="..."):
            v = str(v or "")
            return v if len(v) <= length else v[:length] + suffix

        self._env.filters["fmt_date"]   = fmt_date
        self._env.filters["fmt_number"] = fmt_number
        self._env.filters["truncate"]   = truncate

    def render(self, template_str: str, data: Dict[str, Any]) -> str:
        if self._env:
            try:
                return self._env.from_string(template_str).render(**data)
            except Exception as e:
                raise ValueError(f"Jinja2渲染失败: {e}")
        # fallback: simple {{key}} substitution
        result = template_str
        for k, v in data.items():
            result = result.replace("{{" + k + "}}", str(v))
            result = result.replace("{{ " + k + " }}", str(v))
        return result

# ── Handler ABC ────────────────────────────────────────────────────────────────
class NotificationHandler(ABC):
    channel: str = ""

    @abstractmethod
    async def send(self, notification: Dict[str, Any]) -> Dict[str, Any]:
        ...

    @abstractmethod
    async def check_status(self, message_id: str) -> Dict[str, Any]:
        ...

    async def validate_recipient(self, recipient: Dict[str, Any]) -> bool:
        return True

    def metrics(self) -> Dict[str, Any]:
        return {"channel": self.channel, "status": "active"}

# ── Email handler ──────────────────────────────────────────────────────────────
class EmailNotificationHandler(NotificationHandler):
    channel = "email"

    def __init__(self):
        self.smtp_host = ServiceConfig.SMTP_HOST
        self.smtp_port = ServiceConfig.SMTP_PORT
        self.smtp_user = ServiceConfig.SMTP_USER
        self.smtp_pass = ServiceConfig.SMTP_PASS
        self.from_addr = ServiceConfig.EMAIL_FROM
        self.from_name = ServiceConfig.EMAIL_NAME

    async def send(self, notification: Dict[str, Any]) -> Dict[str, Any]:
        recipient = notification.get("recipient", {})
        email     = recipient.get("email", "")
        title     = notification.get("content", {}).get("title", "")
        body      = notification.get("content", {}).get("content", "")
        ctype     = notification.get("content", {}).get("content_type", "html")

        if not email:
            return {"success": False, "error": "no email address", "error_code": "NO_EMAIL"}

        msg = MIMEMultipart("alternative")
        msg["From"]    = f"{self.from_name} <{self.from_addr}>"
        msg["To"]      = email
        msg["Subject"] = title
        msg_id = f"<{notification.get('notification_id', uuid.uuid4().hex)}@ns>"
        msg["Message-ID"] = msg_id

        if ctype == "html":
            msg.attach(MIMEText(body, "html", "utf-8"))
            msg.attach(MIMEText(re.sub(r'<[^>]+>', ' ', body), "plain", "utf-8"))
        else:
            msg.attach(MIMEText(body, "plain", "utf-8"))

        for att in notification.get("attachments", []):
            raw = base64.b64decode(att["content"]) if att.get("encoding") == "base64" else att["content"].encode()
            part = MIMEApplication(raw)
            part.add_header("Content-Disposition", "attachment", filename=att["filename"])
            msg.attach(part)

        # Try aiosmtplib → sync smtplib → stub
        if _HAS_AIOSMTPLIB and self.smtp_user:
            try:
                async with _aiosmtplib.SMTP(
                    hostname=self.smtp_host, port=self.smtp_port,
                    use_tls=(self.smtp_port == 465),
                    timeout=30,
                ) as smtp:
                    if self.smtp_port == 587:
                        await smtp.ehlo()
                        await smtp.starttls()
                    if self.smtp_user:
                        await smtp.login(self.smtp_user, self.smtp_pass)
                    await smtp.send_message(msg)
                logger.info("[email] sent to %s", email)
                return {"success": True, "message_id": msg_id, "recipient": email, "provider": "smtp"}
            except Exception as e:
                logger.error("[email] aiosmtplib failed: %s", e)
                return {"success": False, "error": str(e), "error_code": "SMTP_ERROR"}

        # stub mode — log only
        logger.info("[email][stub] would send to=%s subject=%s", email, title)
        return {"success": True, "message_id": msg_id, "recipient": email, "provider": "stub"}

    async def check_status(self, message_id: str) -> Dict[str, Any]:
        return {"status": "delivered", "message_id": message_id}

    async def validate_recipient(self, recipient: Dict[str, Any]) -> bool:
        return bool(recipient.get("email") and _EMAIL_RE.match(recipient["email"]))

# ── SMS handler ────────────────────────────────────────────────────────────────
class SMSNotificationHandler(NotificationHandler):
    channel = "sms"

    async def send(self, notification: Dict[str, Any]) -> Dict[str, Any]:
        phone    = notification.get("recipient", {}).get("phone", "")
        content  = notification.get("content", {}).get("content", "")
        provider = ServiceConfig.SMS_PROVIDER

        if not phone:
            return {"success": False, "error": "no phone number", "error_code": "NO_PHONE"}

        if provider == "tencent" and ServiceConfig.SMS_SECRET_ID:
            return await self._send_tencent(phone, notification)
        if provider == "aliyun" and ServiceConfig.SMS_SECRET_ID:
            return await self._send_aliyun(phone, notification)

        # stub
        msg_id = f"sms_{uuid.uuid4().hex[:10]}"
        logger.info("[sms][stub] to=%s content=%.50s", phone, content)
        return {"success": True, "message_id": msg_id, "recipient": phone, "provider": "stub"}

    async def _send_tencent(self, phone: str, notification: Dict[str, Any]) -> Dict[str, Any]:
        """Tencent SMS via REST API (no SDK required)."""
        import hashlib, hmac, json as _j
        action     = "SendSms"
        secret_id  = ServiceConfig.SMS_SECRET_ID
        secret_key = ServiceConfig.SMS_SECRET_KEY
        timestamp  = int(time.time())
        date_str   = datetime.utcfromtimestamp(timestamp).strftime("%Y-%m-%d")
        service    = "sms"
        payload = {
            "SmsSdkAppId":    ServiceConfig.SMS_APP_ID,
            "SignName":       ServiceConfig.SMS_SIGN,
            "TemplateId":     notification.get("template_id", ""),
            "TemplateParamSet": [str(v) for v in notification.get("template_data", {}).values()],
            "PhoneNumberSet": [f"+86{phone}"],
        }
        body = _j.dumps(payload)
        ct   = "application/json; charset=utf-8"
        headers_to_sign = f"content-type:{ct}\nhost:sms.tencentcloudapi.com\n"
        hashed_payload  = hashlib.sha256(body.encode()).hexdigest()
        string_to_sign  = f"TC3-HMAC-SHA256\n{timestamp}\n{date_str}/{service}/tc3_request\n{hashlib.sha256((headers_to_sign + hashed_payload).encode()).hexdigest()}"
        signing_key = hmac.new(
            hmac.new(hmac.new(
                f"TC3{secret_key}".encode(), date_str.encode(), hashlib.sha256
            ).digest(), service.encode(), hashlib.sha256).digest(),
            b"tc3_request", hashlib.sha256
        ).digest()
        signature = hmac.new(signing_key, string_to_sign.encode(), hashlib.sha256).hexdigest()
        auth = (f"TC3-HMAC-SHA256 Credential={secret_id}/{date_str}/{service}/tc3_request, "
                f"SignedHeaders=content-type;host, Signature={signature}")
        if _HAS_AIOHTTP:
            async with _aiohttp.ClientSession() as sess:
                async with sess.post(
                    "https://sms.tencentcloudapi.com",
                    headers={"Content-Type": ct, "Authorization": auth, "X-TC-Action": action,
                             "X-TC-Version": "2021-01-11", "X-TC-Timestamp": str(timestamp)},
                    data=body, timeout=_aiohttp.ClientTimeout(total=30)
                ) as r:
                    resp = await r.json()
            send_set = resp.get("Response", {}).get("SendStatusSet", [{}])
            if send_set and send_set[0].get("Code") == "Ok":
                return {"success": True, "message_id": send_set[0].get("SerialNo", ""), "recipient": phone, "provider": "tencent"}
            return {"success": False, "error": str(send_set), "error_code": "TENCENT_SMS_FAILED"}
        return {"success": True, "message_id": f"tc_{uuid.uuid4().hex[:8]}", "recipient": phone, "provider": "tencent_stub"}

    async def _send_aliyun(self, phone: str, notification: Dict[str, Any]) -> Dict[str, Any]:
        """Aliyun SMS via REST API."""
        msg_id = f"ali_{uuid.uuid4().hex[:8]}"
        logger.info("[sms][aliyun][stub] to=%s", phone)
        return {"success": True, "message_id": msg_id, "recipient": phone, "provider": "aliyun_stub"}

    async def check_status(self, message_id: str) -> Dict[str, Any]:
        return {"status": "delivered", "message_id": message_id}

    async def validate_recipient(self, recipient: Dict[str, Any]) -> bool:
        return bool(recipient.get("phone") and _PHONE_RE.match(recipient["phone"]))

# ── WeChat handler ─────────────────────────────────────────────────────────────
class WeChatNotificationHandler(NotificationHandler):
    channel = "wechat"

    async def _get_access_token(self) -> Optional[str]:
        if not (ServiceConfig.WX_APP_ID and ServiceConfig.WX_APP_SECRET):
            return None
        url = (f"https://api.weixin.qq.com/cgi-bin/token"
               f"?grant_type=client_credential&appid={ServiceConfig.WX_APP_ID}"
               f"&secret={ServiceConfig.WX_APP_SECRET}")
        if _HAS_AIOHTTP:
            async with _aiohttp.ClientSession() as sess:
                async with sess.get(url, timeout=_aiohttp.ClientTimeout(total=10)) as r:
                    data = await r.json()
            return data.get("access_token")
        return None

    async def send(self, notification: Dict[str, Any]) -> Dict[str, Any]:
        openid  = notification.get("recipient", {}).get("wechat_openid", "")
        if not openid:
            return {"success": False, "error": "no wechat_openid", "error_code": "NO_OPENID"}
        token = await self._get_access_token()
        if not token:
            msg_id = f"wx_{uuid.uuid4().hex[:10]}"
            logger.info("[wechat][stub] to=%s template=%s", openid, notification.get("template_id"))
            return {"success": True, "message_id": msg_id, "recipient": openid, "provider": "stub"}
        # Send template message via WeChat API
        template_id = notification.get("template_id", "")
        data = notification.get("template_data", {})
        payload = {
            "touser": openid, "template_id": template_id,
            "data": {k: {"value": str(v)} for k, v in data.items()},
        }
        if _HAS_AIOHTTP:
            async with _aiohttp.ClientSession() as sess:
                async with sess.post(
                    f"https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={token}",
                    json=payload, timeout=_aiohttp.ClientTimeout(total=15)
                ) as r:
                    resp = await r.json()
            if resp.get("errcode") == 0:
                return {"success": True, "message_id": str(resp.get("msgid", "")), "recipient": openid, "provider": "wechat"}
            return {"success": False, "error": resp.get("errmsg", ""), "error_code": "WX_API_ERROR"}
        return {"success": True, "message_id": f"wx_{uuid.uuid4().hex[:8]}", "recipient": openid, "provider": "wechat_stub"}

    async def check_status(self, message_id: str) -> Dict[str, Any]:
        return {"status": "sent", "message_id": message_id, "note": "WeChat无状态查询"}

# ── Push (FCM) handler ─────────────────────────────────────────────────────────
class PushNotificationHandler(NotificationHandler):
    channel = "push"

    async def send(self, notification: Dict[str, Any]) -> Dict[str, Any]:
        token   = notification.get("recipient", {}).get("device_token", "")
        title   = notification.get("content", {}).get("title", "")
        body    = notification.get("content", {}).get("content", "")
        if not token:
            return {"success": False, "error": "no device_token", "error_code": "NO_TOKEN"}
        if not ServiceConfig.FCM_SERVER_KEY:
            msg_id = f"push_{uuid.uuid4().hex[:10]}"
            logger.info("[push][stub] token=...%s title=%s", token[-6:], title)
            return {"success": True, "message_id": msg_id, "recipient": token[:8] + "...", "provider": "stub"}
        payload = {"to": token, "notification": {"title": title, "body": body[:200]}}
        if _HAS_AIOHTTP:
            async with _aiohttp.ClientSession() as sess:
                async with sess.post(
                    "https://fcm.googleapis.com/fcm/send",
                    json=payload,
                    headers={"Authorization": f"key={ServiceConfig.FCM_SERVER_KEY}"},
                    timeout=_aiohttp.ClientTimeout(total=15)
                ) as r:
                    resp = await r.json()
            if resp.get("success", 0) == 1:
                return {"success": True, "message_id": str(resp.get("results", [{}])[0].get("message_id", "")), "recipient": token[:8] + "...", "provider": "fcm"}
            return {"success": False, "error": str(resp), "error_code": "FCM_ERROR"}
        return {"success": True, "message_id": f"fcm_{uuid.uuid4().hex[:8]}", "recipient": token[:8] + "...", "provider": "stub"}

    async def check_status(self, message_id: str) -> Dict[str, Any]:
        return {"status": "delivered", "message_id": message_id}

# ── Webhook handler ────────────────────────────────────────────────────────────
class WebhookNotificationHandler(NotificationHandler):
    channel = "webhook"

    async def send(self, notification: Dict[str, Any]) -> Dict[str, Any]:
        url = notification.get("recipient", {}).get("webhook_url", "")
        if not url:
            return {"success": False, "error": "no webhook_url", "error_code": "NO_URL"}
        payload = {
            "notification_id": notification.get("notification_id"),
            "title":           notification.get("content", {}).get("title"),
            "content":         notification.get("content", {}).get("content"),
            "timestamp":       _now().isoformat(),
        }
        if _HAS_AIOHTTP:
            try:
                async with _aiohttp.ClientSession() as sess:
                    async with sess.post(url, json=payload, timeout=_aiohttp.ClientTimeout(total=15)) as r:
                        status_code = r.status
                if status_code < 300:
                    return {"success": True, "message_id": f"wh_{uuid.uuid4().hex[:8]}", "recipient": url, "provider": "webhook"}
                return {"success": False, "error": f"HTTP {status_code}", "error_code": "WEBHOOK_HTTP_ERROR"}
            except Exception as e:
                return {"success": False, "error": str(e), "error_code": "WEBHOOK_ERROR"}
        logger.info("[webhook][stub] url=%s", url)
        return {"success": True, "message_id": f"wh_{uuid.uuid4().hex[:8]}", "recipient": url, "provider": "stub"}

    async def check_status(self, message_id: str) -> Dict[str, Any]:
        return {"status": "delivered", "message_id": message_id}

# ── In-App handler ─────────────────────────────────────────────────────────────
class InAppNotificationHandler(NotificationHandler):
    channel = "in_app"

    async def send(self, notification: Dict[str, Any]) -> Dict[str, Any]:
        uid = notification.get("recipient", {}).get("user_id") or notification.get("recipient", {}).get("recipient_id", "")
        msg_id = f"inapp_{uuid.uuid4().hex[:10]}"
        logger.info("[in_app] user_id=%s title=%s", uid, notification.get("content", {}).get("title"))
        return {"success": True, "message_id": msg_id, "recipient": uid, "provider": "in_app"}

    async def check_status(self, message_id: str) -> Dict[str, Any]:
        return {"status": "delivered", "message_id": message_id}

# ── InMemoryQueue (aio_pika fallback) ──────────────────────────────────────────
class InMemoryQueue:
    """asyncio.Queue-backed queue used when aio_pika is unavailable."""

    def __init__(self):
        self._queues: Dict[str, asyncio.Queue] = {}

    def _q(self, key: str) -> asyncio.Queue:
        if key not in self._queues:
            self._queues[key] = asyncio.Queue()
        return self._queues[key]

    async def publish(self, routing_key: str, message: Dict[str, Any], priority: int = 0) -> None:
        await self._q(routing_key).put(message)

    async def consume(self, routing_key: str, callback: Callable, prefetch_count: int = 10) -> None:
        q = self._q(routing_key)
        while True:
            message = await q.get()
            try:
                await callback(message)
            except Exception as e:
                logger.error("[queue] consumer error on %s: %s", routing_key, e)
            finally:
                q.task_done()

    async def qsize(self, routing_key: str) -> int:
        return self._q(routing_key).qsize()

# ── NotificationQueue (wraps aio_pika or InMemoryQueue) ───────────────────────
class NotificationQueue:
    def __init__(self):
        self._amqp_conn = None
        self._amqp_channel = None
        self._mem: InMemoryQueue = InMemoryQueue()

    async def connect(self) -> None:
        if _HAS_AMQP:
            try:
                self._amqp_conn    = await _aio_pika.connect_robust(ServiceConfig.RABBITMQ_URL)
                self._amqp_channel = await self._amqp_conn.channel()
                logger.info("RabbitMQ connected")
                return
            except Exception as e:
                logger.warning("RabbitMQ unavailable (%s), using in-memory queue", e)
        self._amqp_conn = None

    async def disconnect(self) -> None:
        if self._amqp_conn:
            await self._amqp_conn.close()

    async def publish(self, routing_key: str, message: Dict[str, Any], priority: int = 0) -> None:
        if self._amqp_channel:
            body = json.dumps(message, default=str).encode()
            await self._amqp_channel.default_exchange.publish(
                _aio_pika.Message(body=body, content_type="application/json", priority=priority),
                routing_key=routing_key,
            )
        else:
            await self._mem.publish(routing_key, message)

    async def consume(self, routing_key: str, callback: Callable, prefetch_count: int = 10) -> None:
        if self._amqp_channel:
            queue = await self._amqp_channel.declare_queue(routing_key, durable=True)
            await self._amqp_channel.set_qos(prefetch_count=prefetch_count)
            async with queue.iterator() as it:
                async for msg in it:
                    async with msg.process():
                        data = json.loads(msg.body.decode())
                        await callback(data)
        else:
            await self._mem.consume(routing_key, callback, prefetch_count)

    async def qsize(self, routing_key: str) -> int:
        if self._amqp_channel:
            return 0  # cannot easily query AMQP queue size here
        return await self._mem.qsize(routing_key)

# ── RedisManager ───────────────────────────────────────────────────────────────
class RedisManager:
    def __init__(self, url: str):
        self._url = url
        self._client: Any = None
        self._mock: Dict[str, Tuple[str, float]] = {}

    async def connect(self) -> None:
        if _HAS_REDIS:
            try:
                self._client = _redis_mod.from_url(self._url, decode_responses=True)
                await self._client.ping()
                logger.info("Redis connected")
                return
            except Exception as e:
                logger.warning("Redis unavailable (%s), using mock", e)
        self._client = None

    async def get(self, key: str) -> Optional[str]:
        if self._client:
            return await self._client.get(key)
        entry = self._mock.get(key)
        if entry and (entry[1] == 0 or entry[1] > time.time()):
            return entry[0]
        self._mock.pop(key, None)
        return None

    async def set(self, key: str, value: str, ex: int = 0) -> None:
        if self._client:
            if ex: await self._client.set(key, value, ex=ex)
            else:  await self._client.set(key, value)
            return
        self._mock[key] = (value, time.time() + ex if ex else 0)

    async def delete(self, key: str) -> None:
        if self._client: await self._client.delete(key)
        else: self._mock.pop(key, None)

    async def close(self) -> None:
        if self._client: await self._client.close()

# ── Prometheus (duplicate-safe) ────────────────────────────────────────────────
if _HAS_PROMETHEUS:
    _NS_REGISTRY = CollectorRegistry()

    def _ctr(n, d, l):
        try: return Counter(n, d, l, registry=_NS_REGISTRY)
        except ValueError: return Counter(n, d, l, registry=CollectorRegistry())

    def _gau(n, d, l=[]):
        try: return Gauge(n, d, l, registry=_NS_REGISTRY)
        except ValueError: return Gauge(n, d, l, registry=CollectorRegistry())

    def _hist(n, d, l):
        try: return Histogram(n, d, l, registry=_NS_REGISTRY)
        except ValueError: return Histogram(n, d, l, registry=CollectorRegistry())

    _m_sent       = _ctr("ns_notifications_sent_total",    "Total sent",      ["channel", "status"])
    _m_failed     = _ctr("ns_notifications_failed_total",  "Total failed",    ["channel", "code"])
    _m_queue      = _gau("ns_queue_size",                  "Queue size",      ["queue"])
    _m_ws_conn    = _gau("ns_ws_connections",              "WS connections",  [])
    _m_latency    = _hist("ns_send_latency_s",             "Send latency",    ["channel"])

# ── WebSocketManager ───────────────────────────────────────────────────────────
class WSManager:
    def __init__(self):
        self._conns: Dict[str, Tuple[WebSocket, Optional[str]]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket, cid: str, user_id: Optional[str] = None) -> None:
        await ws.accept()
        async with self._lock:
            self._conns[cid] = (ws, user_id)

    async def disconnect(self, cid: str) -> None:
        async with self._lock:
            self._conns.pop(cid, None)

    async def send_to_user(self, user_id: str, event: Dict[str, Any]) -> None:
        msg = json.dumps(event, default=str)
        dead = []
        async with self._lock:
            targets = [(cid, ws) for cid, (ws, uid) in self._conns.items() if uid == user_id]
        for cid, ws in targets:
            try:
                await ws.send_text(msg)
            except Exception:
                dead.append(cid)
        for cid in dead:
            await self.disconnect(cid)

    async def broadcast(self, event: Dict[str, Any]) -> None:
        msg = json.dumps(event, default=str)
        dead = []
        async with self._lock:
            targets = list(self._conns.items())
        for cid, (ws, _) in targets:
            try:
                await ws.send_text(msg)
            except Exception:
                dead.append(cid)
        for cid in dead:
            await self.disconnect(cid)

    @property
    def count(self) -> int:
        return len(self._conns)

# ── DB engine ──────────────────────────────────────────────────────────────────
_engine = create_async_engine(
    ServiceConfig.DB_URL, echo=False, pool_pre_ping=True,
    connect_args={"check_same_thread": False} if "sqlite" in ServiceConfig.DB_URL else {},
)
_SessionFactory = sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)

async def get_db() -> AsyncSession:
    async with _SessionFactory() as s:
        yield s

# ── singletons ─────────────────────────────────────────────────────────────────
_redis_mgr  = RedisManager(ServiceConfig.REDIS_URL)
_queue      = NotificationQueue()
_ws_mgr     = WSManager()
_tmpl_eng   = TemplateEngine()

_handlers: Dict[str, NotificationHandler] = {
    "email":   EmailNotificationHandler(),
    "sms":     SMSNotificationHandler(),
    "wechat":  WeChatNotificationHandler(),
    "push":    PushNotificationHandler(),
    "webhook": WebhookNotificationHandler(),
    "in_app":  InAppNotificationHandler(),
}

# ── NotificationService ────────────────────────────────────────────────────────
class NotificationService:

    async def send_notification(
        self,
        session: AsyncSession,
        req: SendNotificationRequest,
        user_id: str = "system",
    ) -> Dict[str, Any]:
        channel = req.channel or req.notification_type.value
        if channel not in _handlers:
            raise HTTPException(400, f"不支持的通道: {channel}")

        notif_id   = f"n_{uuid.uuid4().hex[:12]}"
        tracking_id = f"t_{uuid.uuid4().hex[:12]}" if req.tracking_enabled else None

        # render content
        content = req.content.model_dump()
        if req.template_id:
            tmpl = await self._get_template_obj(session, req.template_id)
            if tmpl:
                try:
                    content["title"]   = _tmpl_eng.render(tmpl.subject_template, req.template_data)
                    content["content"] = _tmpl_eng.render(tmpl.content_template, req.template_data)
                except ValueError as e:
                    raise HTTPException(422, str(e))

        # persist
        notif = Notification(
            notification_id   = notif_id,
            notification_type = req.notification_type.value,
            status            = NotificationStatus.PENDING.value,
            priority          = req.priority.value,
            channel           = channel,
            title             = content["title"],
            content           = content["content"],
            content_type      = content.get("content_type", "html"),
            summary           = content.get("summary"),
            keywords          = content.get("keywords"),
            notif_data        = content.get("data"),
            recipients        = [r.model_dump() for r in req.recipients],
            recipient_count   = len(req.recipients),
            sender_id         = user_id,
            sender_type       = req.sender_type,
            template_id       = req.template_id,
            template_data     = req.template_data,
            attachments       = [a.model_dump() for a in req.attachments],
            send_strategy     = req.send_strategy.value,
            schedule_time     = req.schedule_time,
            expire_time       = req.expire_time,
            tracking_enabled  = req.tracking_enabled,
            tracking_id       = tracking_id,
            callback_url      = req.callback_url,
            max_retries       = ServiceConfig.QUEUE_MAX_RETRY,
            extra_metadata    = req.extra_metadata,
        )
        session.add(notif)
        await session.commit()
        await session.refresh(notif)

        # dispatch
        notif_data = {
            "notification_id": notif_id,
            "channel":         channel,
            "recipients":      [r.model_dump() for r in req.recipients],
            "content":         content,
            "template_id":     req.template_id,
            "template_data":   req.template_data,
            "attachments":     [a.model_dump() for a in req.attachments],
            "tracking_enabled": req.tracking_enabled,
            "tracking_id":     tracking_id,
            "callback_url":    req.callback_url,
            "priority":        req.priority.value,
        }
        if req.send_strategy == SendStrategy.IMMEDIATE:
            asyncio.create_task(self._dispatch(notif_id, channel, notif_data))
        else:
            await _queue.publish(f"notification.{req.send_strategy.value}", notif_data, priority=req.priority.value)

        return {"notification_id": notif_id, "status": "pending", "channel": channel,
                "recipient_count": len(req.recipients), "tracking_id": tracking_id}

    async def _dispatch(
        self, notif_id: str, channel: str, notif_data: Dict[str, Any]
    ) -> None:
        handler   = _handlers.get(channel)
        recipients = notif_data.get("recipients", [])
        t0 = time.monotonic()

        async with _SessionFactory() as session:
            notif = (await session.execute(
                select(Notification).where(Notification.notification_id == notif_id)
            )).scalars().first()
            if not notif:
                return
            notif.status     = NotificationStatus.PROCESSING.value
            notif.updated_at = _now()
            await session.commit()

        success_count = 0
        last_error: Optional[str] = None

        for recipient in recipients:
            msg_payload = dict(notif_data)
            msg_payload["recipient"] = recipient
            try:
                result = await handler.send(msg_payload)
                ok = result.get("success", False)
                if ok:
                    success_count += 1
                    msg_id = result.get("message_id", "")
                    await self._log(notif_id, channel, "send", "sent", recipient.get("recipient_id"), msg_id)
                else:
                    last_error = result.get("error", "unknown")
                    await self._log(notif_id, channel, "error", last_error, recipient.get("recipient_id"), None)
                if _HAS_PROMETHEUS:
                    _m_sent.labels(channel=channel, status="sent" if ok else "failed").inc()
            except Exception as e:
                last_error = str(e)
                logger.error("[dispatch] channel=%s error=%s", channel, e)
                if _HAS_PROMETHEUS:
                    _m_failed.labels(channel=channel, code="DISPATCH_ERROR").inc()

        elapsed = time.monotonic() - t0
        if _HAS_PROMETHEUS:
            _m_latency.labels(channel=channel).observe(elapsed)

        final_status = (
            NotificationStatus.SENT.value if success_count == len(recipients)
            else (NotificationStatus.FAILED.value if success_count == 0
                  else NotificationStatus.SENT.value)
        )
        async with _SessionFactory() as session:
            notif = (await session.execute(
                select(Notification).where(Notification.notification_id == notif_id)
            )).scalars().first()
            if notif:
                notif.status     = final_status
                notif.updated_at = _now()
                notif.sent_at    = _now()
                if last_error:
                    notif.last_error = last_error
                if final_status == NotificationStatus.FAILED.value:
                    notif.failed_at = _now()
                await session.commit()

        await _ws_mgr.broadcast({
            "event":           "notification_status",
            "notification_id": notif_id,
            "status":          final_status,
            "channel":         channel,
            "timestamp":       _now().isoformat(),
        })

    async def _log(
        self, notif_id: str, channel: str, log_type: str,
        action: str, recipient_id: Optional[str], msg_id: Optional[str]
    ) -> None:
        async with _SessionFactory() as session:
            log = NotificationLog(
                log_id          = f"log_{uuid.uuid4().hex[:12]}",
                notification_id = notif_id,
                log_type        = log_type,
                log_action      = action,
                recipient_id    = recipient_id,
                channel         = channel,
                channel_msg_id  = msg_id,
            )
            session.add(log)
            await session.commit()

    async def get_notification(self, session: AsyncSession, notif_id: str) -> Notification:
        n = (await session.execute(
            select(Notification).where(Notification.notification_id == notif_id)
        )).scalars().first()
        if not n:
            raise HTTPException(404, f"Notification {notif_id} not found")
        return n

    async def list_notifications(
        self, session: AsyncSession, query: NotificationQuery
    ) -> Dict[str, Any]:
        conds = []
        if query.notification_type: conds.append(Notification.notification_type == query.notification_type)
        if query.status:            conds.append(Notification.status == query.status)
        if query.channel:           conds.append(Notification.channel == query.channel)
        if query.sender_id:         conds.append(Notification.sender_id == query.sender_id)
        if query.template_id:       conds.append(Notification.template_id == query.template_id)
        if query.start_time:        conds.append(Notification.created_at >= query.start_time)
        if query.end_time:          conds.append(Notification.created_at <= query.end_time)

        stmt  = select(Notification)
        if conds: stmt = stmt.where(and_(*conds))
        total = (await session.execute(
            select(func.count()).select_from(Notification).where(and_(*conds) if conds else True)
        )).scalar_one()
        order = Notification.created_at.desc() if query.sort_order == "desc" else Notification.created_at.asc()
        rows  = (await session.execute(
            stmt.order_by(order).offset((query.page - 1) * query.page_size).limit(query.page_size)
        )).scalars().all()
        return {"items": rows, "total": total, "page": query.page, "page_size": query.page_size,
                "total_pages": (total + query.page_size - 1) // query.page_size}

    async def cancel_notification(
        self, session: AsyncSession, notif_id: str
    ) -> Dict[str, Any]:
        n = await self.get_notification(session, notif_id)
        if n.status not in (NotificationStatus.PENDING.value,):
            raise HTTPException(409, f"Cannot cancel notification in status={n.status}")
        n.status     = NotificationStatus.CANCELLED.value
        n.updated_at = _now()
        await session.commit()
        return {"notification_id": notif_id, "status": "cancelled"}

    async def retry_notification(
        self, session: AsyncSession, notif_id: str
    ) -> Dict[str, Any]:
        n = await self.get_notification(session, notif_id)
        if n.status not in (NotificationStatus.FAILED.value,):
            raise HTTPException(409, f"Only failed notifications can be retried, current status={n.status}")
        if n.retry_count >= n.max_retries:
            raise HTTPException(409, f"Max retries ({n.max_retries}) reached")
        n.status      = NotificationStatus.PENDING.value
        n.retry_count += 1
        n.updated_at  = _now()
        await session.commit()

        recipients = n.recipients or []
        notif_data = {
            "notification_id": notif_id,
            "channel":         n.channel,
            "recipients":      recipients,
            "content":         {"title": n.title, "content": n.content, "content_type": n.content_type},
            "template_id":     n.template_id,
            "template_data":   n.template_data or {},
            "attachments":     n.attachments or [],
            "tracking_enabled": n.tracking_enabled,
            "tracking_id":     n.tracking_id,
        }
        asyncio.create_task(self._dispatch(notif_id, n.channel, notif_data))
        return {"notification_id": notif_id, "status": "pending", "retry_count": n.retry_count}

    async def get_logs(
        self, session: AsyncSession, notif_id: str,
        page: int = 1, page_size: int = 20
    ) -> Dict[str, Any]:
        total = (await session.execute(
            select(func.count()).select_from(NotificationLog).where(
                NotificationLog.notification_id == notif_id)
        )).scalar_one()
        rows  = (await session.execute(
            select(NotificationLog).where(NotificationLog.notification_id == notif_id)
            .order_by(NotificationLog.created_at.desc())
            .offset((page - 1) * page_size).limit(page_size)
        )).scalars().all()
        return {"items": rows, "total": total, "page": page}

    # ── Templates ──────────────────────────────────────────────────────────────
    async def create_template(
        self, session: AsyncSession, req: NotificationTemplateCreate
    ) -> NotificationTemplate:
        existing = (await session.execute(
            select(NotificationTemplate).where(NotificationTemplate.template_id == req.template_id)
        )).scalars().first()
        if existing:
            raise HTTPException(409, f"Template '{req.template_id}' already exists")
        tmpl = NotificationTemplate(
            template_id       = req.template_id,
            name              = req.name,
            notification_type = req.notification_type.value,
            template_type     = req.template_type.value,
            language          = req.language,
            subject_template  = req.subject_template,
            content_template  = req.content_template,
            content_type      = req.content_type.value,
            variables         = req.variables,
            description       = req.description,
            tags              = req.tags,
            channel_config    = req.channel_config,
            is_active         = req.is_active,
            created_by        = req.created_by,
            updated_by        = req.created_by,
        )
        session.add(tmpl)
        await session.commit()
        await session.refresh(tmpl)
        return tmpl

    async def get_template(self, session: AsyncSession, template_id: str) -> NotificationTemplate:
        return await self._get_template_obj(session, template_id) or (
            (_ for _ in ()).throw(HTTPException(404, f"Template '{template_id}' not found"))
        )

    async def _get_template_obj(
        self, session: AsyncSession, template_id: str
    ) -> Optional[NotificationTemplate]:
        return (await session.execute(
            select(NotificationTemplate).where(NotificationTemplate.template_id == template_id)
        )).scalars().first()

    async def list_templates(
        self, session: AsyncSession,
        notification_type: Optional[str] = None,
        template_type: Optional[str] = None,
        is_active: Optional[bool] = None,
        page: int = 1, page_size: int = 20,
    ) -> Dict[str, Any]:
        conds = []
        if notification_type: conds.append(NotificationTemplate.notification_type == notification_type)
        if template_type:     conds.append(NotificationTemplate.template_type == template_type)
        if is_active is not None: conds.append(NotificationTemplate.is_active == is_active)
        stmt  = select(NotificationTemplate)
        if conds: stmt = stmt.where(and_(*conds))
        total = (await session.execute(
            select(func.count()).select_from(NotificationTemplate).where(and_(*conds) if conds else True)
        )).scalar_one()
        rows  = (await session.execute(
            stmt.order_by(NotificationTemplate.created_at.desc())
            .offset((page - 1) * page_size).limit(page_size)
        )).scalars().all()
        return {"items": rows, "total": total, "page": page, "page_size": page_size}

    async def update_template(
        self, session: AsyncSession, template_id: str, updates: Dict[str, Any]
    ) -> NotificationTemplate:
        tmpl = await self._get_template_obj(session, template_id)
        if not tmpl:
            raise HTTPException(404, f"Template '{template_id}' not found")
        allowed = {"name", "subject_template", "content_template", "description",
                   "variables", "tags", "channel_config", "is_active", "updated_by"}
        for k, v in updates.items():
            if k in allowed and v is not None:
                setattr(tmpl, k, v)
        tmpl.updated_at = _now()
        await session.commit()
        await session.refresh(tmpl)
        return tmpl

    async def delete_template(self, session: AsyncSession, template_id: str) -> Dict[str, Any]:
        tmpl = await self._get_template_obj(session, template_id)
        if not tmpl:
            raise HTTPException(404, f"Template '{template_id}' not found")
        tmpl.is_active  = False
        tmpl.updated_at = _now()
        await session.commit()
        return {"message": f"Template '{template_id}' deactivated"}

    async def render_preview(
        self, session: AsyncSession, template_id: str, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        tmpl = await self._get_template_obj(session, template_id)
        if not tmpl:
            raise HTTPException(404, f"Template '{template_id}' not found")
        subject = _tmpl_eng.render(tmpl.subject_template, data)
        content = _tmpl_eng.render(tmpl.content_template, data)
        return {"template_id": template_id, "subject": subject, "content": content}

    # ── Channel status ─────────────────────────────────────────────────────────
    async def get_channel_status(self, channel: str) -> Dict[str, Any]:
        h = _handlers.get(channel)
        if not h:
            raise HTTPException(404, f"Channel '{channel}' not found")
        return {
            "channel": channel, "status": "active", "enabled": True,
            "handler": h.__class__.__name__, "metrics": h.metrics(),
            "last_check": _now().isoformat(),
        }

    async def test_channel(self, session: AsyncSession, req: ChannelTestRequest) -> Dict[str, Any]:
        h = _handlers.get(req.channel)
        if not h:
            raise HTTPException(404, f"Channel '{req.channel}' not found")
        notif_data = {
            "notification_id": f"test_{uuid.uuid4().hex[:8]}",
            "channel":         req.channel,
            "recipient":       req.recipient.model_dump(),
            "content":         req.content.model_dump(),
            "attachments":     [],
            "tracking_enabled": False,
        }
        result = await h.send(notif_data)
        return {"channel": req.channel, "result": result, "timestamp": _now().isoformat()}

    # ── Stats ──────────────────────────────────────────────────────────────────
    async def get_stats(self, session: AsyncSession) -> Dict[str, Any]:
        total    = (await session.execute(select(func.count()).select_from(Notification))).scalar_one()
        by_status = {}
        for s in NotificationStatus:
            cnt = (await session.execute(
                select(func.count()).select_from(Notification).where(Notification.status == s.value)
            )).scalar_one()
            by_status[s.value] = cnt
        by_channel_rows = (await session.execute(
            select(Notification.channel, func.count(Notification.id).label("cnt"))
            .group_by(Notification.channel)
        )).all()
        tmpls = (await session.execute(select(func.count()).select_from(NotificationTemplate))).scalar_one()
        return {
            "total_notifications": total,
            "by_status":           by_status,
            "by_channel":          {r.channel: r.cnt for r in by_channel_rows},
            "total_templates":     tmpls,
            "active_handlers":     list(_handlers.keys()),
            "ws_connections":      _ws_mgr.count,
        }

# ── singleton service ──────────────────────────────────────────────────────────
_svc = NotificationService()

# ── helper ─────────────────────────────────────────────────────────────────────
def _row(obj: Any) -> Dict[str, Any]:
    if hasattr(obj, "__dict__"):
        return {k: v for k, v in obj.__dict__.items() if not k.startswith("_")}
    return dict(obj)

# ── FastAPI factory ────────────────────────────────────────────────────────────
def create_app() -> FastAPI:
    app = FastAPI(
        title="Notification Service",
        description="Multi-channel Notification Management (Part 10)",
        version="1.0.0",
    )

    @app.on_event("startup")
    async def _startup():
        async with _engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        await _redis_mgr.connect()
        await _queue.connect()
        asyncio.create_task(_expire_notifications_task())
        asyncio.create_task(_process_scheduled_task())
        asyncio.create_task(_queue.consume("notification.delayed",   _svc._dispatch_from_queue))
        asyncio.create_task(_queue.consume("notification.batch",     _svc._dispatch_from_queue))
        asyncio.create_task(_queue.consume("notification.scheduled", _svc._dispatch_from_queue))
        await _seed_demo_data()
        logger.info("Notification Service started on %s:%s", ServiceConfig.HOST, ServiceConfig.PORT)

    @app.on_event("shutdown")
    async def _shutdown():
        await _redis_mgr.close()
        await _queue.disconnect()
        await _engine.dispose()

    # ── health ─────────────────────────────────────────────────────────────────
    @app.get("/health", tags=["system"])
    async def health():
        return {"status": "ok", "service": "notification-service",
                "handlers": list(_handlers.keys()),
                "time": _now().isoformat()}

    @app.get("/metrics", tags=["system"])
    async def metrics():
        if not _HAS_PROMETHEUS:
            raise HTTPException(503, "prometheus_client not installed")
        return StreamingResponse(iter([generate_latest(_NS_REGISTRY)]), media_type=CONTENT_TYPE_LATEST)

    # ── WebSocket ──────────────────────────────────────────────────────────────
    @app.websocket("/ws/notifications")
    async def ws_notifications(ws: WebSocket, user_id: Optional[str] = Query(None)):
        cid = str(uuid.uuid4())
        await _ws_mgr.connect(ws, cid, user_id)
        if _HAS_PROMETHEUS: _m_ws_conn.set(_ws_mgr.count)
        try:
            while True:
                await ws.receive_text()
        except WebSocketDisconnect:
            pass
        finally:
            await _ws_mgr.disconnect(cid)
            if _HAS_PROMETHEUS: _m_ws_conn.set(_ws_mgr.count)

    # ── Notification CRUD ──────────────────────────────────────────────────────
    @app.post("/api/v1/notifications", status_code=201, tags=["notifications"])
    async def send_notification(
        req: SendNotificationRequest,
        sender_id: str = Query("system"),
        db: AsyncSession = Depends(get_db),
    ):
        return await _svc.send_notification(db, req, sender_id)

    @app.get("/api/v1/notifications", tags=["notifications"])
    async def list_notifications(
        notification_type: Optional[str] = None,
        status:            Optional[str] = None,
        channel:           Optional[str] = None,
        sender_id:         Optional[str] = None,
        template_id:       Optional[str] = None,
        page:              int = Query(1,  ge=1),
        page_size:         int = Query(20, ge=1, le=200),
        sort_order:        str = Query("desc"),
        db: AsyncSession = Depends(get_db),
    ):
        q = NotificationQuery(
            notification_type=notification_type, status=status, channel=channel,
            sender_id=sender_id, template_id=template_id,
            page=page, page_size=page_size, sort_order=sort_order,
        )
        result = await _svc.list_notifications(db, q)
        result["items"] = [_row(r) for r in result["items"]]
        return result

    @app.get("/api/v1/notifications/{notification_id}", tags=["notifications"])
    async def get_notification(notification_id: str, db: AsyncSession = Depends(get_db)):
        n = await _svc.get_notification(db, notification_id)
        return _row(n)

    @app.delete("/api/v1/notifications/{notification_id}", tags=["notifications"])
    async def cancel_notification(notification_id: str, db: AsyncSession = Depends(get_db)):
        return await _svc.cancel_notification(db, notification_id)

    @app.post("/api/v1/notifications/{notification_id}/retry", tags=["notifications"])
    async def retry_notification(notification_id: str, db: AsyncSession = Depends(get_db)):
        return await _svc.retry_notification(db, notification_id)

    @app.get("/api/v1/notifications/{notification_id}/logs", tags=["notifications"])
    async def get_notification_logs(
        notification_id: str,
        page:      int = Query(1,  ge=1),
        page_size: int = Query(20, ge=1, le=100),
        db: AsyncSession = Depends(get_db),
    ):
        result = await _svc.get_logs(db, notification_id, page, page_size)
        result["items"] = [_row(r) for r in result["items"]]
        return result

    # ── Batch send ─────────────────────────────────────────────────────────────
    @app.post("/api/v1/notifications/batch", tags=["notifications"])
    async def batch_send(
        requests: List[SendNotificationRequest],
        sender_id: str = Query("system"),
        db: AsyncSession = Depends(get_db),
    ):
        results = []
        for req in requests[:100]:  # max 100 per batch call
            try:
                r = await _svc.send_notification(db, req, sender_id)
                results.append({"success": True, **r})
            except HTTPException as e:
                results.append({"success": False, "error": e.detail})
        return {"results": results, "total": len(requests), "submitted": len(results)}

    # ── Templates ──────────────────────────────────────────────────────────────
    @app.post("/api/v1/templates", status_code=201, tags=["templates"])
    async def create_template(req: NotificationTemplateCreate, db: AsyncSession = Depends(get_db)):
        t = await _svc.create_template(db, req)
        return _row(t)

    @app.get("/api/v1/templates", tags=["templates"])
    async def list_templates(
        notification_type: Optional[str] = None,
        template_type:     Optional[str] = None,
        is_active:         Optional[bool] = None,
        page:      int = Query(1,  ge=1),
        page_size: int = Query(20, ge=1, le=100),
        db: AsyncSession = Depends(get_db),
    ):
        result = await _svc.list_templates(db, notification_type, template_type, is_active, page, page_size)
        result["items"] = [_row(r) for r in result["items"]]
        return result

    @app.get("/api/v1/templates/{template_id}", tags=["templates"])
    async def get_template(template_id: str, db: AsyncSession = Depends(get_db)):
        t = await _svc.get_template(db, template_id)
        return _row(t)

    @app.put("/api/v1/templates/{template_id}", tags=["templates"])
    async def update_template(
        template_id: str,
        updates: Dict[str, Any],
        db: AsyncSession = Depends(get_db),
    ):
        t = await _svc.update_template(db, template_id, updates)
        return _row(t)

    @app.delete("/api/v1/templates/{template_id}", tags=["templates"])
    async def delete_template(template_id: str, db: AsyncSession = Depends(get_db)):
        return await _svc.delete_template(db, template_id)

    @app.post("/api/v1/templates/{template_id}/preview", tags=["templates"])
    async def render_preview(
        template_id: str,
        data: Dict[str, Any],
        db: AsyncSession = Depends(get_db),
    ):
        return await _svc.render_preview(db, template_id, data)

    # ── Channels ───────────────────────────────────────────────────────────────
    @app.get("/api/v1/channels", tags=["channels"])
    async def list_channels():
        return {"channels": list(_handlers.keys()), "count": len(_handlers)}

    @app.get("/api/v1/channels/{channel}", tags=["channels"])
    async def get_channel_status(channel: str):
        return await _svc.get_channel_status(channel)

    @app.post("/api/v1/channels/{channel}/test", tags=["channels"])
    async def test_channel(channel: str, req: ChannelTestRequest, db: AsyncSession = Depends(get_db)):
        req.channel = channel
        return await _svc.test_channel(db, req)

    @app.put("/api/v1/channels/{channel}/enable", tags=["channels"])
    async def enable_channel(channel: str):
        if channel not in _handlers:
            raise HTTPException(404, f"Channel '{channel}' not found")
        return {"channel": channel, "status": "enabled"}

    @app.put("/api/v1/channels/{channel}/disable", tags=["channels"])
    async def disable_channel(channel: str):
        if channel not in _handlers:
            raise HTTPException(404, f"Channel '{channel}' not found")
        return {"channel": channel, "status": "disabled"}

    # ── Stats ──────────────────────────────────────────────────────────────────
    @app.get("/api/v1/stats", tags=["stats"])
    async def get_stats(db: AsyncSession = Depends(get_db)):
        return await _svc.get_stats(db)

    @app.get("/api/v1/stats/channels", tags=["stats"])
    async def get_channel_stats(db: AsyncSession = Depends(get_db)):
        rows = (await db.execute(
            select(Notification.channel,
                   Notification.status,
                   func.count(Notification.id).label("cnt"))
            .group_by(Notification.channel, Notification.status)
        )).all()
        result: Dict[str, Dict] = {}
        for r in rows:
            if r.channel not in result:
                result[r.channel] = {}
            result[r.channel][r.status] = r.cnt
        return result

    return app

# ── add _dispatch_from_queue helper to NotificationService ─────────────────────
async def _dispatch_from_queue_fn(data: Dict[str, Any]) -> None:
    notif_id = data.get("notification_id", "")
    channel  = data.get("channel", "")
    if notif_id and channel:
        await _svc._dispatch(notif_id, channel, data)

NotificationService._dispatch_from_queue = lambda self, data: _dispatch_from_queue_fn(data)

# ── background tasks ───────────────────────────────────────────────────────────
async def _expire_notifications_task() -> None:
    """Archive notifications past expire_time (every 5 min)."""
    while True:
        try:
            async with _SessionFactory() as session:
                now  = _now()
                rows = (await session.execute(
                    select(Notification).where(
                        and_(
                            Notification.expire_time != None,
                            Notification.expire_time <= now,
                            Notification.status == NotificationStatus.PENDING.value,
                        )
                    )
                )).scalars().all()
                for n in rows:
                    n.status     = NotificationStatus.CANCELLED.value
                    n.updated_at = now
                if rows:
                    await session.commit()
                    logger.info("Expired %d pending notifications", len(rows))
        except Exception as e:
            logger.error("_expire_notifications_task: %s", e)
        await asyncio.sleep(300)

async def _process_scheduled_task() -> None:
    """Fire scheduled notifications that are due (every 30s)."""
    while True:
        try:
            async with _SessionFactory() as session:
                now  = _now()
                rows = (await session.execute(
                    select(Notification).where(
                        and_(
                            Notification.send_strategy == SendStrategy.SCHEDULED.value,
                            Notification.schedule_time <= now,
                            Notification.status == NotificationStatus.PENDING.value,
                        )
                    ).limit(50)
                )).scalars().all()
                for n in rows:
                    notif_data = {
                        "notification_id": n.notification_id,
                        "channel":         n.channel,
                        "recipients":      n.recipients or [],
                        "content":         {"title": n.title, "content": n.content, "content_type": n.content_type},
                        "template_id":     n.template_id,
                        "template_data":   n.template_data or {},
                        "attachments":     n.attachments or [],
                        "tracking_enabled": n.tracking_enabled,
                        "tracking_id":     n.tracking_id,
                    }
                    asyncio.create_task(_svc._dispatch(n.notification_id, n.channel, notif_data))
        except Exception as e:
            logger.error("_process_scheduled_task: %s", e)
        await asyncio.sleep(30)

# ── seed demo data ─────────────────────────────────────────────────────────────
async def _seed_demo_data() -> None:
    async with _SessionFactory() as session:
        demo_templates = [
            {
                "template_id":       "welcome_email",
                "name":              "欢迎邮件",
                "notification_type": "email",
                "template_type":     "system",
                "subject_template":  "欢迎加入多模态商品识别系统 — {{ username }}",
                "content_template":  ("<h2>欢迎 {{ username }}！</h2>"
                                       "<p>您的账户已成功创建。</p>"
                                       "<p>Email: {{ email }}</p>"),
                "content_type":      "html",
                "variables":         ["username", "email"],
            },
            {
                "template_id":       "verification_sms",
                "name":              "验证码短信",
                "notification_type": "sms",
                "template_type":     "verification",
                "subject_template":  "验证码",
                "content_template":  "您的验证码是：{{ code }}，{{ expire_minutes }}分钟内有效，请勿泄露。",
                "content_type":      "plain_text",
                "variables":         ["code", "expire_minutes"],
            },
            {
                "template_id":       "order_shipped",
                "name":              "订单发货通知",
                "notification_type": "in_app",
                "template_type":     "transactional",
                "subject_template":  "您的订单 {{ order_id }} 已发货",
                "content_template":  "快递单号：{{ tracking_no }}，预计 {{ eta }} 送达。",
                "content_type":      "plain_text",
                "variables":         ["order_id", "tracking_no", "eta"],
            },
        ]
        for td in demo_templates:
            exists = (await session.execute(
                select(NotificationTemplate).where(NotificationTemplate.template_id == td["template_id"])
            )).scalars().first()
            if not exists:
                t = NotificationTemplate(
                    template_id       = td["template_id"],
                    name              = td["name"],
                    notification_type = td["notification_type"],
                    template_type     = td["template_type"],
                    language          = "zh_CN",
                    subject_template  = td["subject_template"],
                    content_template  = td["content_template"],
                    content_type      = td["content_type"],
                    variables         = td["variables"],
                    is_active         = True,
                    created_by        = "seed",
                    updated_by        = "seed",
                )
                session.add(t)
        try:
            await session.commit()
            logger.info("Demo templates seeded")
        except Exception as e:
            await session.rollback()
            logger.warning("Seed skipped: %s", e)

# ── entrypoint ─────────────────────────────────────────────────────────────────
app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "notification_service:app",
        host=ServiceConfig.HOST,
        port=ServiceConfig.PORT,
        reload=False,
        log_level="info",
    )
