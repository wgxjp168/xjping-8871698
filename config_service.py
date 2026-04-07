"""
config_service.py — Production-grade Config Service (Part 9)
Async FastAPI microservice for centralized configuration management.
"""

from __future__ import annotations

import asyncio
import base64
import csv
import hashlib
import hmac
import io
import json
import logging
import os
import re
import secrets
import time
import uuid
import xml.etree.ElementTree as ET
from configparser import ConfigParser
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

# ── optional deps ──────────────────────────────────────────────────────────────
try:
    import yaml as _yaml_mod
    _HAS_YAML = True
except ImportError:
    _HAS_YAML = False

try:
    import toml as _toml_mod
    _HAS_TOML = True
except ImportError:
    _HAS_TOML = False

try:
    import hcl2 as _hcl2_mod
    _HAS_HCL2 = True
except ImportError:
    _HAS_HCL2 = False

try:
    import redis.asyncio as _redis_mod
    _HAS_REDIS = True
except ImportError:
    _HAS_REDIS = False

try:
    from watchfiles import awatch as _awatch
    _HAS_WATCHFILES = True
except ImportError:
    _HAS_WATCHFILES = False

try:
    import nacos as _nacos_mod
    _HAS_NACOS = True
except ImportError:
    _HAS_NACOS = False

try:
    import consul as _consul_mod
    _HAS_CONSUL = True
except ImportError:
    _HAS_CONSUL = False

from fastapi import (
    BackgroundTasks, Depends, FastAPI, HTTPException, Query,
    WebSocket, WebSocketDisconnect,
)
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy import (
    Boolean, Column, DateTime, Float, Index, Integer, String, Text, JSON,
    select, update, delete, and_, or_, func,
)
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

try:
    from prometheus_client import (
        CollectorRegistry, Counter, Gauge, Histogram, generate_latest,
        CONTENT_TYPE_LATEST,
    )
    _HAS_PROMETHEUS = True
except ImportError:
    _HAS_PROMETHEUS = False

# ── logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("config_service")

# ── enums ──────────────────────────────────────────────────────────────────────
class ConfigType(str, Enum):
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    JSON = "json"
    YAML = "yaml"
    PROPERTIES = "properties"
    XML = "xml"
    TOML = "toml"
    HCL = "hcl"
    ENV = "env"

class ConfigStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"

class ConfigEnvironment(str, Enum):
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"
    ALL = "all"

class ChangeType(str, Enum):
    CREATED = "created"
    UPDATED = "updated"
    PUBLISHED = "published"
    ROLLED_BACK = "rolled_back"
    DELETED = "deleted"
    IMPORTED = "imported"

class EncryptionType(str, Enum):
    NONE = "none"
    SYMMETRIC = "symmetric"
    HASH = "hash"

# ── service config ─────────────────────────────────────────────────────────────
class ServiceConfig:
    DB_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./config_service.db")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/3")
    SECRET_KEY: str = os.getenv("SECRET_KEY", secrets.token_hex(32))
    ENCRYPTION_KEY: str = os.getenv("ENCRYPTION_KEY", secrets.token_hex(16))
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8005"))
    WATCH_POLL_INTERVAL: float = float(os.getenv("WATCH_POLL_INTERVAL", "2.0"))
    MAX_VERSIONS: int = int(os.getenv("MAX_VERSIONS", "50"))
    CACHE_TTL: int = int(os.getenv("CACHE_TTL", "300"))
    LONG_POLL_TIMEOUT: float = float(os.getenv("LONG_POLL_TIMEOUT", "30.0"))

# ── ORM ────────────────────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    pass

def _now() -> datetime:
    return datetime.now(timezone.utc)

class ConfigItem(Base):
    __tablename__ = "t_config_items"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    config_key    = Column(String(512), nullable=False)
    namespace     = Column(String(128), nullable=False, default="default")
    group         = Column(String(128), nullable=False, default="DEFAULT_GROUP")
    environment   = Column(String(32), nullable=False, default="all")
    config_type   = Column(String(32), nullable=False, default="string")
    config_value  = Column(Text, nullable=True)
    status        = Column(String(32), nullable=False, default="draft")
    version       = Column(Integer, nullable=False, default=1)
    description   = Column(Text, nullable=True)
    tags          = Column("config_tags", JSON, nullable=True)
    extra_metadata = Column("config_metadata", JSON, nullable=True)
    is_encrypted  = Column(Boolean, nullable=False, default=False)
    encryption_type = Column(String(32), nullable=False, default="none")
    checksum      = Column(String(64), nullable=True)
    created_by    = Column(String(64), nullable=False, default="system")
    updated_by    = Column(String(64), nullable=False, default="system")
    created_at    = Column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at    = Column(DateTime(timezone=True), nullable=False, default=_now, onupdate=_now)
    published_at  = Column(DateTime(timezone=True), nullable=True)
    expires_at    = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_cfg_key_ns_env", "config_key", "namespace", "environment"),
        Index("idx_cfg_group_ns", "group", "namespace"),
        Index("idx_cfg_status", "status"),
    )

class ConfigHistory(Base):
    __tablename__ = "t_config_history"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    config_id     = Column(Integer, nullable=False)
    config_key    = Column(String(512), nullable=False)
    namespace     = Column(String(128), nullable=False)
    group         = Column(String(128), nullable=False)
    environment   = Column(String(32), nullable=False)
    config_type   = Column(String(32), nullable=False)
    config_value  = Column(Text, nullable=True)
    version       = Column(Integer, nullable=False)
    change_type   = Column(String(32), nullable=False)
    change_reason = Column(Text, nullable=True)
    changed_by    = Column(String(64), nullable=False, default="system")
    checksum      = Column(String(64), nullable=True)
    extra_metadata = Column("history_metadata", JSON, nullable=True)
    created_at    = Column(DateTime(timezone=True), nullable=False, default=_now)

    __table_args__ = (
        Index("idx_hist_config_id", "config_id"),
        Index("idx_hist_key_ns", "config_key", "namespace"),
    )

class ConfigNamespace(Base):
    __tablename__ = "t_config_namespaces"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    name        = Column(String(128), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    owner       = Column(String(64), nullable=True)
    is_public   = Column(Boolean, nullable=False, default=True)
    extra_metadata = Column("ns_metadata", JSON, nullable=True)
    created_at  = Column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at  = Column(DateTime(timezone=True), nullable=False, default=_now, onupdate=_now)

class ConfigTag(Base):
    __tablename__ = "t_config_tags"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    name        = Column(String(64), nullable=False, unique=True)
    color       = Column(String(16), nullable=True)
    description = Column(Text, nullable=True)
    created_at  = Column(DateTime(timezone=True), nullable=False, default=_now)

class ConfigSubscription(Base):
    __tablename__ = "t_config_subscriptions"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    subscriber_id = Column(String(128), nullable=False)
    config_key    = Column(String(512), nullable=True)
    namespace     = Column(String(128), nullable=True)
    group         = Column(String(128), nullable=True)
    environment   = Column(String(32), nullable=True)
    callback_url  = Column(String(512), nullable=True)
    is_active     = Column(Boolean, nullable=False, default=True)
    extra_metadata = Column("sub_metadata", JSON, nullable=True)
    created_at    = Column(DateTime(timezone=True), nullable=False, default=_now)
    last_notified_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_sub_subscriber", "subscriber_id"),
        Index("idx_sub_key_ns", "config_key", "namespace"),
    )

# ── Pydantic v2 models ─────────────────────────────────────────────────────────
_KEY_RE = re.compile(r'^[a-zA-Z0-9_\-\.\/]+$')

class ConfigCreateRequest(BaseModel):
    config_key:   str = Field(..., min_length=1, max_length=512)
    namespace:    str = Field("default", max_length=128)
    group:        str = Field("DEFAULT_GROUP", max_length=128)
    environment:  ConfigEnvironment = ConfigEnvironment.ALL
    config_type:  ConfigType = ConfigType.STRING
    config_value: Optional[str] = None
    description:  Optional[str] = None
    tags:         Optional[List[str]] = None
    extra_metadata: Optional[Dict[str, Any]] = None
    is_encrypted: bool = False
    encryption_type: EncryptionType = EncryptionType.NONE
    created_by:   str = Field("system", max_length=64)
    expires_at:   Optional[datetime] = None

    @field_validator("config_key")
    @classmethod
    def validate_key(cls, v: str) -> str:
        if not _KEY_RE.match(v):
            raise ValueError("config_key may only contain [a-zA-Z0-9_\\-./]")
        return v

    @field_validator("namespace", "group")
    @classmethod
    def validate_slug(cls, v: str) -> str:
        if not re.match(r'^[a-zA-Z0-9_\-]+$', v):
            raise ValueError("must contain only [a-zA-Z0-9_-]")
        return v

class ConfigUpdateRequest(BaseModel):
    config_value:  Optional[str] = None
    description:   Optional[str] = None
    tags:          Optional[List[str]] = None
    extra_metadata: Optional[Dict[str, Any]] = None
    is_encrypted:  Optional[bool] = None
    encryption_type: Optional[EncryptionType] = None
    updated_by:    str = Field("system", max_length=64)
    expires_at:    Optional[datetime] = None
    change_reason: Optional[str] = None

class ConfigPublishRequest(BaseModel):
    published_by:  str = Field("system", max_length=64)
    change_reason: Optional[str] = None

class ConfigRollbackRequest(BaseModel):
    target_version: int = Field(..., ge=1)
    rolled_back_by: str = Field("system", max_length=64)
    change_reason:  Optional[str] = None

class ConfigQueryRequest(BaseModel):
    namespace:    Optional[str] = None
    group:        Optional[str] = None
    environment:  Optional[ConfigEnvironment] = None
    config_type:  Optional[ConfigType] = None
    status:       Optional[ConfigStatus] = None
    tags:         Optional[List[str]] = None
    keyword:      Optional[str] = None
    page:         int = Field(1, ge=1)
    page_size:    int = Field(20, ge=1, le=200)

class ConfigImportRequest(BaseModel):
    namespace:    str = Field("default", max_length=128)
    group:        str = Field("DEFAULT_GROUP", max_length=128)
    environment:  ConfigEnvironment = ConfigEnvironment.ALL
    format:       str = Field("json")
    content:      str
    overwrite:    bool = False
    imported_by:  str = Field("system", max_length=64)

class ConfigExportRequest(BaseModel):
    namespace:    Optional[str] = None
    group:        Optional[str] = None
    environment:  Optional[ConfigEnvironment] = None
    format:       str = Field("json")
    include_metadata: bool = True

class NamespaceCreateRequest(BaseModel):
    name:        str = Field(..., min_length=1, max_length=128)
    description: Optional[str] = None
    owner:       Optional[str] = None
    is_public:   bool = True

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not re.match(r'^[a-zA-Z0-9_\-]+$', v):
            raise ValueError("name must be [a-zA-Z0-9_-]")
        return v

class SubscriptionCreateRequest(BaseModel):
    subscriber_id: str = Field(..., min_length=1, max_length=128)
    config_key:    Optional[str] = None
    namespace:     Optional[str] = None
    group:         Optional[str] = None
    environment:   Optional[ConfigEnvironment] = None
    callback_url:  Optional[str] = None

    @model_validator(mode='after')
    def check_at_least_one_filter(self) -> "SubscriptionCreateRequest":
        if not any([self.config_key, self.namespace, self.group]):
            raise ValueError("At least one of config_key, namespace, or group must be set")
        return self

class ConfigItemResponse(BaseModel):
    id:             int
    config_key:     str
    namespace:      str
    group:          str
    environment:    str
    config_type:    str
    config_value:   Optional[str]
    status:         str
    version:        int
    description:    Optional[str]
    tags:           Optional[List[str]]
    extra_metadata: Optional[Dict[str, Any]]
    is_encrypted:   bool
    checksum:       Optional[str]
    created_by:     str
    updated_by:     str
    created_at:     datetime
    updated_at:     datetime
    published_at:   Optional[datetime]
    expires_at:     Optional[datetime]

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
                logger.info("Redis connected: %s", self._url)
                return
            except Exception as e:
                logger.warning("Redis unavailable (%s), using in-memory mock", e)
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
            if ex:
                await self._client.set(key, value, ex=ex)
            else:
                await self._client.set(key, value)
            return
        expire = time.time() + ex if ex else 0
        self._mock[key] = (value, expire)

    async def delete(self, key: str) -> None:
        if self._client:
            await self._client.delete(key)
        else:
            self._mock.pop(key, None)

    async def publish(self, channel: str, message: str) -> None:
        if self._client:
            await self._client.publish(channel, message)

    async def close(self) -> None:
        if self._client:
            await self._client.close()

# ── EncryptionManager (stdlib only) ───────────────────────────────────────────
class EncryptionManager:
    """AES-free symmetric encryption using PBKDF2 + HMAC + XOR stream."""

    _SALT_LEN = 16
    _KEY_LEN  = 32
    _ITER     = 100_000

    def __init__(self, secret: str):
        self._secret = secret.encode()

    def _derive(self, salt: bytes) -> bytes:
        return hashlib.pbkdf2_hmac("sha256", self._secret, salt, self._ITER, self._KEY_LEN)

    def encrypt(self, plaintext: str) -> str:
        data = plaintext.encode()
        salt = os.urandom(self._SALT_LEN)
        key  = self._derive(salt)
        # XOR-stream cipher with key expanded via HMAC chain
        enc  = self._xor_stream(data, key)
        mac  = hmac.new(key, salt + enc, hashlib.sha256).digest()
        payload = salt + enc + mac
        return base64.urlsafe_b64encode(payload).decode()

    def decrypt(self, token: str) -> str:
        payload = base64.urlsafe_b64decode(token.encode())
        salt    = payload[:self._SALT_LEN]
        mac     = payload[-32:]
        enc     = payload[self._SALT_LEN:-32]
        key     = self._derive(salt)
        expected = hmac.new(key, salt + enc, hashlib.sha256).digest()
        if not hmac.compare_digest(expected, mac):
            raise ValueError("HMAC mismatch — tampered ciphertext")
        return self._xor_stream(enc, key).decode()

    @staticmethod
    def _xor_stream(data: bytes, key: bytes) -> bytes:
        out, pos = bytearray(len(data)), 0
        block = key
        for i, b in enumerate(data):
            if pos >= len(block):
                block = hashlib.sha256(block).digest()
                pos   = 0
            out[i] = b ^ block[pos]
            pos    += 1
        return bytes(out)

    @staticmethod
    def checksum(value: str) -> str:
        return hashlib.sha256(value.encode()).hexdigest()

# ── WebSocketManager ───────────────────────────────────────────────────────────
class WebSocketManager:
    """Tracks connected WebSocket clients and broadcasts config-change events."""

    def __init__(self):
        # client_id → (websocket, filters)
        self._connections: Dict[str, Tuple[WebSocket, Dict[str, Any]]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket, client_id: str,
                      filters: Optional[Dict[str, Any]] = None) -> None:
        await ws.accept()
        async with self._lock:
            self._connections[client_id] = (ws, filters or {})
        logger.info("WS client connected: %s (total=%d)", client_id, len(self._connections))

    async def disconnect(self, client_id: str) -> None:
        async with self._lock:
            self._connections.pop(client_id, None)
        logger.info("WS client disconnected: %s", client_id)

    def _matches(self, filters: Dict[str, Any], event: Dict[str, Any]) -> bool:
        for k, v in filters.items():
            if v and event.get(k) != v:
                return False
        return True

    async def broadcast(self, event: Dict[str, Any]) -> None:
        msg = json.dumps(event, default=str)
        dead: List[str] = []
        async with self._lock:
            targets = list(self._connections.items())
        for cid, (ws, filters) in targets:
            if not self._matches(filters, event):
                continue
            try:
                await ws.send_text(msg)
            except Exception:
                dead.append(cid)
        for cid in dead:
            await self.disconnect(cid)

    @property
    def connection_count(self) -> int:
        return len(self._connections)

# ── Prometheus ─────────────────────────────────────────────────────────────────
if _HAS_PROMETHEUS:
    _CS_REGISTRY = CollectorRegistry()

    def _counter(name: str, desc: str, labels: list):
        try:
            return Counter(name, desc, labels, registry=_CS_REGISTRY)
        except ValueError:
            return Counter(name, desc, labels, registry=CollectorRegistry())

    def _histogram(name: str, desc: str, labels: list, buckets=None):
        kw = {"registry": _CS_REGISTRY}
        if buckets:
            kw["buckets"] = buckets
        try:
            return Histogram(name, desc, labels, **kw)
        except ValueError:
            return Histogram(name, desc, labels, registry=CollectorRegistry())

    def _gauge(name: str, desc: str, labels: list):
        try:
            return Gauge(name, desc, labels, registry=_CS_REGISTRY)
        except ValueError:
            return Gauge(name, desc, labels, registry=CollectorRegistry())

    _m_req     = _counter("cs_requests_total", "Total requests", ["method", "endpoint", "status"])
    _m_lat     = _histogram("cs_request_latency_s", "Request latency", ["endpoint"])
    _m_cfg_ops = _counter("cs_config_ops_total", "Config operations", ["operation", "namespace"])
    _m_ws_conn = _gauge("cs_ws_connections", "WS connections", [])
    _m_cache   = _counter("cs_cache_ops_total", "Cache ops", ["result"])

# ── DB engine ──────────────────────────────────────────────────────────────────
_engine = create_async_engine(
    ServiceConfig.DB_URL,
    echo=False,
    pool_pre_ping=True,
    connect_args={"check_same_thread": False} if "sqlite" in ServiceConfig.DB_URL else {},
)
_AsyncSessionFactory = sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)

async def get_db() -> AsyncSession:
    async with _AsyncSessionFactory() as session:
        yield session

# ── ConfigService ──────────────────────────────────────────────────────────────
class ConfigService:
    def __init__(
        self,
        redis: RedisManager,
        encryption: EncryptionManager,
        ws_manager: WebSocketManager,
    ):
        self._redis  = redis
        self._enc    = encryption
        self._ws     = ws_manager

    # ── internal helpers ───────────────────────────────────────────────────────
    def _cache_key(self, key: str, ns: str, env: str) -> str:
        return f"cfg:{ns}:{env}:{key}"

    async def _invalidate(self, cfg: ConfigItem) -> None:
        await self._redis.delete(self._cache_key(cfg.config_key, cfg.namespace, cfg.environment))

    async def _record_history(
        self,
        session: AsyncSession,
        cfg: ConfigItem,
        change_type: ChangeType,
        changed_by: str,
        reason: Optional[str] = None,
    ) -> None:
        h = ConfigHistory(
            config_id    = cfg.id,
            config_key   = cfg.config_key,
            namespace    = cfg.namespace,
            group        = cfg.group,
            environment  = cfg.environment,
            config_type  = cfg.config_type,
            config_value = cfg.config_value,
            version      = cfg.version,
            change_type  = change_type.value,
            change_reason= reason,
            changed_by   = changed_by,
            checksum     = cfg.checksum,
        )
        session.add(h)
        await session.flush()

    async def _broadcast_change(self, cfg: ConfigItem, change_type: ChangeType) -> None:
        event = {
            "event":       "config_changed",
            "change_type": change_type.value,
            "config_key":  cfg.config_key,
            "namespace":   cfg.namespace,
            "group":       cfg.group,
            "environment": cfg.environment,
            "version":     cfg.version,
            "status":      cfg.status,
            "timestamp":   datetime.now(timezone.utc).isoformat(),
        }
        await self._ws.broadcast(event)
        await self._redis.publish(f"cfg_changes:{cfg.namespace}", json.dumps(event, default=str))

    # ── CRUD ───────────────────────────────────────────────────────────────────
    async def create_config(
        self, session: AsyncSession, req: ConfigCreateRequest
    ) -> ConfigItem:
        # duplicate check
        stmt = select(ConfigItem).where(
            and_(
                ConfigItem.config_key  == req.config_key,
                ConfigItem.namespace   == req.namespace,
                ConfigItem.environment == req.environment.value,
                ConfigItem.status      != ConfigStatus.ARCHIVED.value,
            )
        )
        existing = (await session.execute(stmt)).scalars().first()
        if existing:
            raise HTTPException(409, f"Config '{req.config_key}' already exists in ns={req.namespace} env={req.environment}")

        value = req.config_value
        enc_type = req.encryption_type.value
        if req.is_encrypted and value:
            value    = self._enc.encrypt(value)
            enc_type = EncryptionType.SYMMETRIC.value

        checksum = self._enc.checksum(value) if value else None

        cfg = ConfigItem(
            config_key      = req.config_key,
            namespace       = req.namespace,
            group           = req.group,
            environment     = req.environment.value,
            config_type     = req.config_type.value,
            config_value    = value,
            status          = ConfigStatus.DRAFT.value,
            version         = 1,
            description     = req.description,
            tags            = req.tags,
            extra_metadata  = req.extra_metadata,
            is_encrypted    = req.is_encrypted,
            encryption_type = enc_type,
            checksum        = checksum,
            created_by      = req.created_by,
            updated_by      = req.created_by,
            expires_at      = req.expires_at,
        )
        session.add(cfg)
        await session.flush()
        await self._record_history(session, cfg, ChangeType.CREATED, req.created_by)
        await session.commit()
        await session.refresh(cfg)
        if _HAS_PROMETHEUS:
            _m_cfg_ops.labels(operation="create", namespace=req.namespace).inc()
        await self._broadcast_change(cfg, ChangeType.CREATED)
        return cfg

    async def get_config(
        self,
        session: AsyncSession,
        config_key: str,
        namespace: str = "default",
        environment: str = "all",
        decrypt: bool = False,
    ) -> ConfigItem:
        cache_key = self._cache_key(config_key, namespace, environment)
        cached = await self._redis.get(cache_key)
        if _HAS_PROMETHEUS:
            _m_cache.labels(result="hit" if cached else "miss").inc()

        stmt = select(ConfigItem).where(
            and_(
                ConfigItem.config_key == config_key,
                ConfigItem.namespace  == namespace,
                or_(
                    ConfigItem.environment == environment,
                    ConfigItem.environment == ConfigEnvironment.ALL.value,
                ),
                ConfigItem.status == ConfigStatus.PUBLISHED.value,
            )
        ).order_by(ConfigItem.environment.desc())
        cfg = (await session.execute(stmt)).scalars().first()
        if not cfg:
            raise HTTPException(404, f"Config '{config_key}' not found in ns={namespace}")

        # cache — use __dict__ to avoid DB-column-name vs attr-name mismatch
        row = {k: v for k, v in cfg.__dict__.items() if not k.startswith("_")}
        await self._redis.set(cache_key, json.dumps(row, default=str), ex=ServiceConfig.CACHE_TTL)

        if decrypt and cfg.is_encrypted and cfg.config_value:
            cfg.config_value = self._enc.decrypt(cfg.config_value)
        return cfg

    async def update_config(
        self,
        session: AsyncSession,
        config_id: int,
        req: ConfigUpdateRequest,
    ) -> ConfigItem:
        cfg = await session.get(ConfigItem, config_id)
        if not cfg:
            raise HTTPException(404, f"Config id={config_id} not found")

        if req.config_value is not None:
            value = req.config_value
            is_enc = req.is_encrypted if req.is_encrypted is not None else cfg.is_encrypted
            if is_enc:
                value = self._enc.encrypt(value)
                cfg.is_encrypted    = True
                cfg.encryption_type = EncryptionType.SYMMETRIC.value
            cfg.config_value = value
            cfg.checksum     = self._enc.checksum(value)

        if req.description   is not None: cfg.description   = req.description
        if req.tags          is not None: cfg.tags          = req.tags
        if req.extra_metadata is not None: cfg.extra_metadata = req.extra_metadata
        if req.expires_at    is not None: cfg.expires_at    = req.expires_at
        if req.is_encrypted  is not None: cfg.is_encrypted  = req.is_encrypted

        cfg.version    += 1
        cfg.status      = ConfigStatus.DRAFT.value
        cfg.updated_by  = req.updated_by
        cfg.updated_at  = _now()

        await session.flush()
        await self._record_history(session, cfg, ChangeType.UPDATED, req.updated_by, req.change_reason)
        await session.commit()
        await session.refresh(cfg)
        await self._invalidate(cfg)
        if _HAS_PROMETHEUS:
            _m_cfg_ops.labels(operation="update", namespace=cfg.namespace).inc()
        await self._broadcast_change(cfg, ChangeType.UPDATED)
        return cfg

    async def publish_config(
        self,
        session: AsyncSession,
        config_id: int,
        req: ConfigPublishRequest,
    ) -> ConfigItem:
        cfg = await session.get(ConfigItem, config_id)
        if not cfg:
            raise HTTPException(404, f"Config id={config_id} not found")
        if cfg.status == ConfigStatus.PUBLISHED.value:
            raise HTTPException(409, "Config is already published")

        cfg.status       = ConfigStatus.PUBLISHED.value
        cfg.published_at = _now()
        cfg.updated_by   = req.published_by
        cfg.updated_at   = _now()

        await session.flush()
        await self._record_history(session, cfg, ChangeType.PUBLISHED, req.published_by, req.change_reason)
        await session.commit()
        await session.refresh(cfg)
        await self._invalidate(cfg)
        if _HAS_PROMETHEUS:
            _m_cfg_ops.labels(operation="publish", namespace=cfg.namespace).inc()
        await self._broadcast_change(cfg, ChangeType.PUBLISHED)
        return cfg

    async def rollback_config(
        self,
        session: AsyncSession,
        config_id: int,
        req: ConfigRollbackRequest,
    ) -> ConfigItem:
        cfg = await session.get(ConfigItem, config_id)
        if not cfg:
            raise HTTPException(404, f"Config id={config_id} not found")

        # find the target version in history
        stmt = select(ConfigHistory).where(
            and_(
                ConfigHistory.config_id == config_id,
                ConfigHistory.version   == req.target_version,
            )
        ).order_by(ConfigHistory.created_at.desc())
        hist = (await session.execute(stmt)).scalars().first()
        if not hist:
            raise HTTPException(404, f"Version {req.target_version} not found for config id={config_id}")

        cfg.config_value = hist.config_value
        cfg.config_type  = hist.config_type
        cfg.checksum     = hist.checksum
        cfg.version     += 1
        cfg.status       = ConfigStatus.DRAFT.value
        cfg.updated_by   = req.rolled_back_by
        cfg.updated_at   = _now()

        await session.flush()
        await self._record_history(session, cfg, ChangeType.ROLLED_BACK, req.rolled_back_by,
                                    req.change_reason or f"Rolled back to v{req.target_version}")
        await session.commit()
        await session.refresh(cfg)
        await self._invalidate(cfg)
        if _HAS_PROMETHEUS:
            _m_cfg_ops.labels(operation="rollback", namespace=cfg.namespace).inc()
        await self._broadcast_change(cfg, ChangeType.ROLLED_BACK)
        return cfg

    async def delete_config(
        self,
        session: AsyncSession,
        config_id: int,
        deleted_by: str = "system",
    ) -> Dict[str, Any]:
        cfg = await session.get(ConfigItem, config_id)
        if not cfg:
            raise HTTPException(404, f"Config id={config_id} not found")

        cfg.status     = ConfigStatus.ARCHIVED.value
        cfg.updated_by = deleted_by
        cfg.updated_at = _now()
        await session.flush()
        await self._record_history(session, cfg, ChangeType.DELETED, deleted_by)
        await session.commit()
        await self._invalidate(cfg)
        if _HAS_PROMETHEUS:
            _m_cfg_ops.labels(operation="delete", namespace=cfg.namespace).inc()
        await self._broadcast_change(cfg, ChangeType.DELETED)
        return {"message": f"Config id={config_id} archived", "config_key": cfg.config_key}

    async def query_configs(
        self,
        session: AsyncSession,
        params: ConfigQueryRequest,
    ) -> Dict[str, Any]:
        stmt = select(ConfigItem)
        conditions = [ConfigItem.status != ConfigStatus.ARCHIVED.value]

        if params.namespace:
            conditions.append(ConfigItem.namespace == params.namespace)
        if params.group:
            conditions.append(ConfigItem.group == params.group)
        if params.environment:
            conditions.append(ConfigItem.environment == params.environment.value)
        if params.config_type:
            conditions.append(ConfigItem.config_type == params.config_type.value)
        if params.status:
            conditions.append(ConfigItem.status == params.status.value)
        if params.keyword:
            kw = f"%{params.keyword}%"
            conditions.append(
                or_(
                    ConfigItem.config_key.ilike(kw),
                    ConfigItem.description.ilike(kw),
                )
            )

        stmt = stmt.where(and_(*conditions)).order_by(ConfigItem.updated_at.desc())

        count_stmt = select(func.count()).select_from(ConfigItem).where(and_(*conditions))
        total = (await session.execute(count_stmt)).scalar_one()

        offset = (params.page - 1) * params.page_size
        rows   = (await session.execute(stmt.offset(offset).limit(params.page_size))).scalars().all()

        return {
            "items":       rows,
            "total":       total,
            "page":        params.page,
            "page_size":   params.page_size,
            "total_pages": (total + params.page_size - 1) // params.page_size,
        }

    async def watch_configs(
        self,
        session: AsyncSession,
        namespace: str,
        group: Optional[str],
        environment: Optional[str],
        last_version_map: Dict[str, int],
        timeout: float = 30.0,
    ) -> List[Dict[str, Any]]:
        """Long-poll: waits up to `timeout` seconds for any config change."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            stmt = select(ConfigItem).where(
                and_(
                    ConfigItem.namespace == namespace,
                    ConfigItem.status    == ConfigStatus.PUBLISHED.value,
                )
            )
            if group:
                stmt = stmt.where(ConfigItem.group == group)
            if environment:
                stmt = stmt.where(ConfigItem.environment == environment)

            cfgs = (await session.execute(stmt)).scalars().all()
            changes: List[Dict[str, Any]] = []
            for c in cfgs:
                prev_v = last_version_map.get(c.config_key, 0)
                if c.version > prev_v:
                    changes.append({
                        "config_key": c.config_key,
                        "version":    c.version,
                        "checksum":   c.checksum,
                    })
            if changes:
                return changes
            await asyncio.sleep(ServiceConfig.WATCH_POLL_INTERVAL)
        return []  # timeout — no changes

    # ── import / export ────────────────────────────────────────────────────────
    async def import_config(
        self,
        session: AsyncSession,
        req: ConfigImportRequest,
    ) -> Dict[str, Any]:
        fmt = req.format.lower()
        try:
            if fmt == "json":
                data = json.loads(req.content)
            elif fmt in ("yaml", "yml"):
                if not _HAS_YAML:
                    raise HTTPException(422, "PyYAML not installed")
                data = _yaml_mod.safe_load(req.content)
            elif fmt == "properties":
                cp = ConfigParser()
                cp.read_string("[root]\n" + req.content)
                data = dict(cp["root"])
            elif fmt == "env":
                data = {}
                for line in req.content.splitlines():
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, _, v = line.partition("=")
                        data[k.strip()] = v.strip()
            elif fmt == "xml":
                root = ET.fromstring(req.content)
                data = {child.tag: child.text for child in root}
            elif fmt == "toml":
                if not _HAS_TOML:
                    raise HTTPException(422, "toml not installed")
                data = _toml_mod.loads(req.content)
            elif fmt == "hcl":
                if not _HAS_HCL2:
                    raise HTTPException(422, "python-hcl2 not installed")
                import io as _io
                data = _hcl2_mod.load(_io.StringIO(req.content))
            else:
                raise HTTPException(422, f"Unsupported import format: {fmt}")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(422, f"Parse error ({fmt}): {e}")

        if not isinstance(data, dict):
            raise HTTPException(422, "Imported data must be a key-value mapping")

        created = updated = skipped = 0
        for k, v in data.items():
            str_val = json.dumps(v) if not isinstance(v, str) else v
            v_type  = ConfigType.JSON.value if not isinstance(v, str) else ConfigType.STRING.value
            stmt = select(ConfigItem).where(
                and_(
                    ConfigItem.config_key  == k,
                    ConfigItem.namespace   == req.namespace,
                    ConfigItem.environment == req.environment.value,
                    ConfigItem.status      != ConfigStatus.ARCHIVED.value,
                )
            )
            existing = (await session.execute(stmt)).scalars().first()
            if existing:
                if not req.overwrite:
                    skipped += 1
                    continue
                existing.config_value = str_val
                existing.config_type  = v_type
                existing.version     += 1
                existing.updated_by   = req.imported_by
                existing.updated_at   = _now()
                await session.flush()
                await self._record_history(session, existing, ChangeType.IMPORTED, req.imported_by)
                updated += 1
            else:
                cfg = ConfigItem(
                    config_key    = k,
                    namespace     = req.namespace,
                    group         = req.group,
                    environment   = req.environment.value,
                    config_type   = v_type,
                    config_value  = str_val,
                    status        = ConfigStatus.DRAFT.value,
                    version       = 1,
                    created_by    = req.imported_by,
                    updated_by    = req.imported_by,
                    checksum      = self._enc.checksum(str_val),
                )
                session.add(cfg)
                await session.flush()
                await self._record_history(session, cfg, ChangeType.IMPORTED, req.imported_by)
                created += 1

        await session.commit()
        return {"created": created, "updated": updated, "skipped": skipped, "total": len(data)}

    async def export_config(
        self,
        session: AsyncSession,
        req: ConfigExportRequest,
    ) -> Tuple[str, str]:
        stmt = select(ConfigItem).where(
            ConfigItem.status != ConfigStatus.ARCHIVED.value
        )
        if req.namespace:   stmt = stmt.where(ConfigItem.namespace   == req.namespace)
        if req.group:       stmt = stmt.where(ConfigItem.group       == req.group)
        if req.environment: stmt = stmt.where(ConfigItem.environment == req.environment.value)

        rows = (await session.execute(stmt)).scalars().all()
        data = {r.config_key: r.config_value for r in rows}

        fmt = req.format.lower()
        if fmt == "json":
            content  = json.dumps(data, ensure_ascii=False, indent=2)
            mimetype = "application/json"
        elif fmt in ("yaml", "yml"):
            if not _HAS_YAML:
                raise HTTPException(422, "PyYAML not installed")
            content  = _yaml_mod.dump(data, allow_unicode=True, default_flow_style=False)
            mimetype = "text/yaml"
        elif fmt == "properties":
            lines = [f"{k}={v}" for k, v in data.items()]
            content  = "\n".join(lines)
            mimetype = "text/plain"
        elif fmt == "env":
            content  = "\n".join(f"{k}={v}" for k, v in data.items())
            mimetype = "text/plain"
        elif fmt == "xml":
            root = ET.Element("configs")
            for k, v in data.items():
                child = ET.SubElement(root, re.sub(r'[^a-zA-Z0-9_]', '_', k))
                child.text = v or ""
            content  = ET.tostring(root, encoding="unicode", xml_declaration=False)
            mimetype = "application/xml"
        elif fmt == "toml":
            if not _HAS_TOML:
                raise HTTPException(422, "toml not installed")
            content  = _toml_mod.dumps(data)
            mimetype = "application/toml"
        else:
            raise HTTPException(422, f"Unsupported export format: {fmt}")

        return content, mimetype

    # ── history / stats ────────────────────────────────────────────────────────
    async def get_history(
        self,
        session: AsyncSession,
        config_id: int,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        stmt  = select(ConfigHistory).where(
            ConfigHistory.config_id == config_id
        ).order_by(ConfigHistory.created_at.desc())
        total = (await session.execute(
            select(func.count()).select_from(ConfigHistory).where(ConfigHistory.config_id == config_id)
        )).scalar_one()
        offset = (page - 1) * page_size
        rows   = (await session.execute(stmt.offset(offset).limit(page_size))).scalars().all()
        return {"items": rows, "total": total, "page": page, "page_size": page_size}

    async def get_stats(self, session: AsyncSession) -> Dict[str, Any]:
        total   = (await session.execute(select(func.count()).select_from(ConfigItem))).scalar_one()
        pub     = (await session.execute(
            select(func.count()).select_from(ConfigItem).where(ConfigItem.status == "published")
        )).scalar_one()
        draft   = (await session.execute(
            select(func.count()).select_from(ConfigItem).where(ConfigItem.status == "draft")
        )).scalar_one()
        arch    = (await session.execute(
            select(func.count()).select_from(ConfigItem).where(ConfigItem.status == "archived")
        )).scalar_one()
        ns_rows = (await session.execute(
            select(ConfigItem.namespace, func.count(ConfigItem.id).label("cnt"))
            .group_by(ConfigItem.namespace)
        )).all()
        hist_total = (await session.execute(select(func.count()).select_from(ConfigHistory))).scalar_one()
        return {
            "total_configs":   total,
            "published":       pub,
            "draft":           draft,
            "archived":        arch,
            "history_entries": hist_total,
            "ws_connections":  self._ws.connection_count,
            "by_namespace":    {r.namespace: r.cnt for r in ns_rows},
        }

    async def list_namespaces(self, session: AsyncSession) -> List[ConfigNamespace]:
        rows = (await session.execute(
            select(ConfigNamespace).order_by(ConfigNamespace.name)
        )).scalars().all()
        return list(rows)

    async def create_namespace(
        self, session: AsyncSession, req: NamespaceCreateRequest
    ) -> ConfigNamespace:
        stmt = select(ConfigNamespace).where(ConfigNamespace.name == req.name)
        if (await session.execute(stmt)).scalars().first():
            raise HTTPException(409, f"Namespace '{req.name}' already exists")
        ns = ConfigNamespace(
            name        = req.name,
            description = req.description,
            owner       = req.owner,
            is_public   = req.is_public,
        )
        session.add(ns)
        await session.commit()
        await session.refresh(ns)
        return ns

    async def create_subscription(
        self, session: AsyncSession, req: SubscriptionCreateRequest
    ) -> ConfigSubscription:
        sub = ConfigSubscription(
            subscriber_id = req.subscriber_id,
            config_key    = req.config_key,
            namespace     = req.namespace,
            group         = req.group,
            environment   = req.environment.value if req.environment else None,
            callback_url  = req.callback_url,
        )
        session.add(sub)
        await session.commit()
        await session.refresh(sub)
        return sub

    async def list_subscriptions(
        self, session: AsyncSession, subscriber_id: str
    ) -> List[ConfigSubscription]:
        rows = (await session.execute(
            select(ConfigSubscription).where(
                and_(
                    ConfigSubscription.subscriber_id == subscriber_id,
                    ConfigSubscription.is_active == True,
                )
            )
        )).scalars().all()
        return list(rows)

# ── singletons ─────────────────────────────────────────────────────────────────
_redis_mgr   = RedisManager(ServiceConfig.REDIS_URL)
_enc_mgr     = EncryptionManager(ServiceConfig.ENCRYPTION_KEY)
_ws_mgr      = WebSocketManager()
_cfg_svc     = ConfigService(_redis_mgr, _enc_mgr, _ws_mgr)

# ── FastAPI factory ────────────────────────────────────────────────────────────
def _row_to_dict(obj: Any) -> Dict[str, Any]:
    if hasattr(obj, "__dict__"):
        return {k: v for k, v in obj.__dict__.items() if not k.startswith("_")}
    return dict(obj)

def create_app() -> FastAPI:
    app = FastAPI(
        title       = "Config Service",
        description = "Centralized Configuration Management (Part 9)",
        version     = "1.0.0",
    )

    # ── lifecycle ──────────────────────────────────────────────────────────────
    @app.on_event("startup")
    async def _startup():
        async with _engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        await _redis_mgr.connect()
        asyncio.create_task(_expire_configs_task())
        await _seed_demo_data()
        logger.info("Config Service started on %s:%s", ServiceConfig.HOST, ServiceConfig.PORT)

    @app.on_event("shutdown")
    async def _shutdown():
        await _redis_mgr.close()
        await _engine.dispose()

    # ── health ─────────────────────────────────────────────────────────────────
    @app.get("/health", tags=["system"])
    async def health():
        return {"status": "ok", "service": "config-service", "time": datetime.now(timezone.utc).isoformat()}

    # ── metrics ────────────────────────────────────────────────────────────────
    @app.get("/metrics", tags=["system"])
    async def metrics():
        if not _HAS_PROMETHEUS:
            raise HTTPException(503, "prometheus_client not installed")
        return StreamingResponse(
            iter([generate_latest(_CS_REGISTRY)]),
            media_type=CONTENT_TYPE_LATEST,
        )

    # ── WebSocket ──────────────────────────────────────────────────────────────
    @app.websocket("/ws/configs")
    async def ws_configs(ws: WebSocket):
        client_id = str(uuid.uuid4())
        filters: Dict[str, Any] = {}
        # read optional filter params from query string
        for k in ("namespace", "group", "environment", "config_key"):
            v = ws.query_params.get(k)
            if v:
                filters[k] = v
        await _ws_mgr.connect(ws, client_id, filters)
        if _HAS_PROMETHEUS:
            _m_ws_conn.labels().set(_ws_mgr.connection_count)
        try:
            while True:
                await ws.receive_text()   # keep-alive / ping from client
        except WebSocketDisconnect:
            pass
        finally:
            await _ws_mgr.disconnect(client_id)
            if _HAS_PROMETHEUS:
                _m_ws_conn.labels().set(_ws_mgr.connection_count)

    # ── namespace endpoints ────────────────────────────────────────────────────
    @app.get("/api/v1/namespaces", tags=["namespaces"])
    async def list_namespaces(db: AsyncSession = Depends(get_db)):
        rows = await _cfg_svc.list_namespaces(db)
        return {"items": [_row_to_dict(r) for r in rows]}

    @app.post("/api/v1/namespaces", status_code=201, tags=["namespaces"])
    async def create_namespace(req: NamespaceCreateRequest, db: AsyncSession = Depends(get_db)):
        ns = await _cfg_svc.create_namespace(db, req)
        return _row_to_dict(ns)

    # ── config CRUD ────────────────────────────────────────────────────────────
    @app.post("/api/v1/configs", status_code=201, tags=["configs"])
    async def create_config(req: ConfigCreateRequest, db: AsyncSession = Depends(get_db)):
        cfg = await _cfg_svc.create_config(db, req)
        return _row_to_dict(cfg)

    @app.get("/api/v1/configs", tags=["configs"])
    async def query_configs(
        namespace:   Optional[str]  = None,
        group:       Optional[str]  = None,
        environment: Optional[str]  = None,
        config_type: Optional[str]  = None,
        status:      Optional[str]  = None,
        keyword:     Optional[str]  = None,
        page:        int = Query(1,  ge=1),
        page_size:   int = Query(20, ge=1, le=200),
        db:          AsyncSession = Depends(get_db),
    ):
        env_enum  = ConfigEnvironment(environment) if environment else None
        type_enum = ConfigType(config_type)        if config_type else None
        st_enum   = ConfigStatus(status)           if status      else None
        params = ConfigQueryRequest(
            namespace=namespace, group=group, environment=env_enum,
            config_type=type_enum, status=st_enum, keyword=keyword,
            page=page, page_size=page_size,
        )
        result = await _cfg_svc.query_configs(db, params)
        result["items"] = [_row_to_dict(r) for r in result["items"]]
        return result

    @app.get("/api/v1/configs/{config_id}", tags=["configs"])
    async def get_config_by_id(config_id: int, db: AsyncSession = Depends(get_db)):
        cfg = await db.get(ConfigItem, config_id)
        if not cfg:
            raise HTTPException(404, f"Config id={config_id} not found")
        return _row_to_dict(cfg)

    @app.get("/api/v1/configs/key/{config_key:path}", tags=["configs"])
    async def get_config_by_key(
        config_key:  str,
        namespace:   str  = "default",
        environment: str  = "all",
        decrypt:     bool = False,
        db:          AsyncSession = Depends(get_db),
    ):
        cfg = await _cfg_svc.get_config(db, config_key, namespace, environment, decrypt)
        return _row_to_dict(cfg)

    @app.put("/api/v1/configs/{config_id}", tags=["configs"])
    async def update_config(
        config_id: int,
        req: ConfigUpdateRequest,
        db:  AsyncSession = Depends(get_db),
    ):
        cfg = await _cfg_svc.update_config(db, config_id, req)
        return _row_to_dict(cfg)

    @app.post("/api/v1/configs/{config_id}/publish", tags=["configs"])
    async def publish_config(
        config_id: int,
        req: ConfigPublishRequest,
        db:  AsyncSession = Depends(get_db),
    ):
        cfg = await _cfg_svc.publish_config(db, config_id, req)
        return _row_to_dict(cfg)

    @app.post("/api/v1/configs/{config_id}/rollback", tags=["configs"])
    async def rollback_config(
        config_id: int,
        req: ConfigRollbackRequest,
        db:  AsyncSession = Depends(get_db),
    ):
        cfg = await _cfg_svc.rollback_config(db, config_id, req)
        return _row_to_dict(cfg)

    @app.delete("/api/v1/configs/{config_id}", tags=["configs"])
    async def delete_config(
        config_id:  int,
        deleted_by: str = Query("system"),
        db:         AsyncSession = Depends(get_db),
    ):
        return await _cfg_svc.delete_config(db, config_id, deleted_by)

    # ── history ────────────────────────────────────────────────────────────────
    @app.get("/api/v1/configs/{config_id}/history", tags=["configs"])
    async def get_history(
        config_id: int,
        page:      int = Query(1,  ge=1),
        page_size: int = Query(20, ge=1, le=100),
        db:        AsyncSession = Depends(get_db),
    ):
        result = await _cfg_svc.get_history(db, config_id, page, page_size)
        result["items"] = [_row_to_dict(r) for r in result["items"]]
        return result

    # ── watch (long-poll) ──────────────────────────────────────────────────────
    @app.get("/api/v1/configs/watch", tags=["configs"])
    async def watch_configs(
        namespace:        str  = Query("default"),
        group:            Optional[str] = None,
        environment:      Optional[str] = None,
        timeout:          float = Query(30.0, ge=1, le=120),
        version_map_json: Optional[str] = Query(None, alias="versions"),
        db:               AsyncSession = Depends(get_db),
    ):
        last_map: Dict[str, int] = {}
        if version_map_json:
            try:
                last_map = json.loads(version_map_json)
            except Exception:
                raise HTTPException(422, "versions must be valid JSON object")
        changes = await _cfg_svc.watch_configs(db, namespace, group, environment, last_map, timeout)
        return {"changes": changes, "count": len(changes)}

    # ── import / export ────────────────────────────────────────────────────────
    @app.post("/api/v1/configs/import", tags=["configs"])
    async def import_configs(req: ConfigImportRequest, db: AsyncSession = Depends(get_db)):
        return await _cfg_svc.import_config(db, req)

    @app.post("/api/v1/configs/export", tags=["configs"])
    async def export_configs(req: ConfigExportRequest, db: AsyncSession = Depends(get_db)):
        content, mimetype = await _cfg_svc.export_config(db, req)
        return StreamingResponse(
            iter([content.encode()]),
            media_type=mimetype,
            headers={"Content-Disposition": f'attachment; filename="configs.{req.format}"'},
        )

    # ── subscriptions ──────────────────────────────────────────────────────────
    @app.post("/api/v1/subscriptions", status_code=201, tags=["subscriptions"])
    async def create_subscription(req: SubscriptionCreateRequest, db: AsyncSession = Depends(get_db)):
        sub = await _cfg_svc.create_subscription(db, req)
        return _row_to_dict(sub)

    @app.get("/api/v1/subscriptions/{subscriber_id}", tags=["subscriptions"])
    async def list_subscriptions(subscriber_id: str, db: AsyncSession = Depends(get_db)):
        subs = await _cfg_svc.list_subscriptions(db, subscriber_id)
        return {"items": [_row_to_dict(s) for s in subs]}

    # ── stats ──────────────────────────────────────────────────────────────────
    @app.get("/api/v1/stats", tags=["stats"])
    async def get_stats(db: AsyncSession = Depends(get_db)):
        return await _cfg_svc.get_stats(db)

    return app

# ── background tasks ───────────────────────────────────────────────────────────
async def _expire_configs_task() -> None:
    """Archive configs that have passed their expiry date (every 5 min)."""
    while True:
        try:
            async with _AsyncSessionFactory() as session:
                now = _now()
                stmt = select(ConfigItem).where(
                    and_(
                        ConfigItem.expires_at != None,
                        ConfigItem.expires_at <= now,
                        ConfigItem.status     != ConfigStatus.ARCHIVED.value,
                    )
                )
                expired = (await session.execute(stmt)).scalars().all()
                for cfg in expired:
                    cfg.status     = ConfigStatus.ARCHIVED.value
                    cfg.updated_at = now
                    await _redis_mgr.delete(_cfg_svc._cache_key(cfg.config_key, cfg.namespace, cfg.environment))
                if expired:
                    await session.commit()
                    logger.info("Archived %d expired configs", len(expired))
        except Exception as e:
            logger.error("_expire_configs_task error: %s", e)
        await asyncio.sleep(300)

# ── seed demo data ─────────────────────────────────────────────────────────────
async def _seed_demo_data() -> None:
    async with _AsyncSessionFactory() as session:
        # ensure 'default' namespace
        stmt = select(ConfigNamespace).where(ConfigNamespace.name == "default")
        if not (await session.execute(stmt)).scalars().first():
            session.add(ConfigNamespace(name="default", description="Default namespace", owner="admin"))
            await session.flush()

        demo_configs = [
            {
                "config_key":   "app.name",
                "config_value": "ILbuy Platform",
                "config_type":  ConfigType.STRING.value,
                "namespace":    "default",
                "group":        "APP",
                "environment":  "all",
                "description":  "Application name",
            },
            {
                "config_key":   "app.version",
                "config_value": "2.0.0",
                "config_type":  ConfigType.STRING.value,
                "namespace":    "default",
                "group":        "APP",
                "environment":  "all",
                "description":  "Application version",
            },
            {
                "config_key":   "feature.ai_matching",
                "config_value": "true",
                "config_type":  ConfigType.BOOLEAN.value,
                "namespace":    "default",
                "group":        "FEATURES",
                "environment":  "production",
                "description":  "Enable AI product matching",
            },
            {
                "config_key":   "database.pool_size",
                "config_value": "10",
                "config_type":  ConfigType.NUMBER.value,
                "namespace":    "default",
                "group":        "DATABASE",
                "environment":  "production",
                "description":  "DB connection pool size",
            },
            {
                "config_key":   "rate_limit.config",
                "config_value": '{"requests_per_second": 100, "burst": 200}',
                "config_type":  ConfigType.JSON.value,
                "namespace":    "default",
                "group":        "SECURITY",
                "environment":  "all",
                "description":  "Rate limiting configuration",
            },
        ]

        for d in demo_configs:
            existing = (await session.execute(
                select(ConfigItem).where(
                    and_(
                        ConfigItem.config_key == d["config_key"],
                        ConfigItem.namespace  == d["namespace"],
                        ConfigItem.environment == d["environment"],
                    )
                )
            )).scalars().first()
            if existing:
                continue
            cfg = ConfigItem(
                status     = ConfigStatus.PUBLISHED.value,
                version    = 1,
                created_by = "seed",
                updated_by = "seed",
                published_at = _now(),
                checksum   = _enc_mgr.checksum(d["config_value"]),
                **d,
            )
            session.add(cfg)

        try:
            await session.commit()
            logger.info("Demo configs seeded")
        except Exception as e:
            await session.rollback()
            logger.warning("Seed skipped (already exists): %s", e)

# ── entrypoint ─────────────────────────────────────────────────────────────────
app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "config_service:app",
        host=ServiceConfig.HOST,
        port=ServiceConfig.PORT,
        reload=False,
        log_level="info",
    )
