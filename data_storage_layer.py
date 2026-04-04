"""
data_storage_layer.py
数据存储层 — OLTP/OLAP存储、文件存储、数据同步
包含：MySQL(SQLite fallback)、Redis、Elasticsearch、ClickHouse、MinIO、数据同步服务
"""

import asyncio
import io
import json
import os
import time
import uuid
import hashlib
import logging
import re
import copy
import concurrent.futures
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod

# ── 可选重型依赖 ──────────────────────────────────────────────────

try:
    import aiomysql
    _HAS_AIOMYSQL = True
except ImportError:
    _HAS_AIOMYSQL = False

try:
    import redis.asyncio as aioredis
    _HAS_REDIS = True
except ImportError:
    _HAS_REDIS = False

try:
    from elasticsearch import AsyncElasticsearch
    import elasticsearch.helpers as _es_helpers
    _HAS_ES = True
except ImportError:
    _HAS_ES = False
    AsyncElasticsearch = None  # type: ignore

try:
    from clickhouse_driver import Client as _CHClient
    _HAS_CLICKHOUSE = True
except ImportError:
    _HAS_CLICKHOUSE = False
    _CHClient = None  # type: ignore

try:
    from minio import Minio as _Minio
    from minio.error import S3Error
    _HAS_MINIO = True
except ImportError:
    _HAS_MINIO = False
    _Minio = None  # type: ignore

try:
    import pika as _pika
    _HAS_PIKA = True
except ImportError:
    _HAS_PIKA = False

try:
    import msgpack as _msgpack
    _HAS_MSGPACK = True
except ImportError:
    _HAS_MSGPACK = False

try:
    from prometheus_client import (Counter as _PCounter, Histogram as _PHisto,
                                   Gauge as _PGauge, generate_latest,
                                   CONTENT_TYPE_LATEST, CollectorRegistry)
    _SL_REGISTRY = CollectorRegistry()
    _HAS_PROMETHEUS = True
except ImportError:
    _HAS_PROMETHEUS = False
    _SL_REGISTRY = None  # type: ignore

from sqlalchemy import (Column, String, Integer, Float, Boolean, JSON, DateTime,
                        Text, BigInteger, ForeignKey, Index, select, text, update)
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, AsyncEngine
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

from pydantic import BaseModel, Field, validator
from fastapi import FastAPI, HTTPException, Depends, Query, BackgroundTasks
from fastapi.responses import JSONResponse

# ── helpers ────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
)
logger = logging.getLogger(__name__)

_THREAD_POOL = concurrent.futures.ThreadPoolExecutor(max_workers=8)


def _make_counter(name, doc, labels=None):
    if not _HAS_PROMETHEUS:
        return None
    try:
        return _PCounter(name, doc, labels or [], registry=_SL_REGISTRY)
    except Exception:
        return None

def _make_histogram(name, doc, labels=None):
    if not _HAS_PROMETHEUS:
        return None
    try:
        return _PHisto(name, doc, labels or [], registry=_SL_REGISTRY)
    except Exception:
        return None

def _make_gauge(name, doc, labels=None):
    if not _HAS_PROMETHEUS:
        return None
    try:
        return _PGauge(name, doc, labels or [], registry=_SL_REGISTRY)
    except Exception:
        return None

async def _run_sync(fn, *args, **kwargs):
    """在线程池中运行同步函数（用于 ClickHouse / MinIO 等同步驱动）"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_THREAD_POOL, lambda: fn(*args, **kwargs))


# ==================== 枚举 & 数据类 ====================

class StorageType(Enum):
    MYSQL         = "mysql"
    REDIS         = "redis"
    ELASTICSEARCH = "elasticsearch"
    CLICKHOUSE    = "clickhouse"
    MINIO         = "minio"


class SyncStatus(Enum):
    PENDING  = "pending"
    SYNCING  = "syncing"
    SYNCED   = "synced"
    FAILED   = "failed"
    DELETED  = "deleted"


class IndexType(Enum):
    PRODUCT = "product"
    ORDER   = "order"
    USER    = "user"
    LOG     = "log"
    REPORT  = "report"


@dataclass
class StorageConfig:
    storage_type:         StorageType
    host:                 str
    port:                 int
    database:             Optional[str] = None
    username:             Optional[str] = None
    password:             Optional[str] = None
    connection_pool_size: int  = 10
    connection_timeout:   int  = 30
    ssl_enabled:          bool = False
    ssl_cert:             Optional[str] = None

    def get_connection_string(self) -> str:
        if self.storage_type == StorageType.MYSQL:
            user = self.username or "root"
            pwd  = self.password or ""
            db   = self.database or "ilbuy"
            return f"mysql+aiomysql://{user}:{pwd}@{self.host}:{self.port}/{db}"
        if self.storage_type == StorageType.REDIS:
            return f"redis://{self.host}:{self.port}/{self.database or 0}"
        return f"{self.storage_type.value}://{self.host}:{self.port}"

    def get_sqlite_url(self) -> str:
        """SQLite 回退 URL（用于无 MySQL 环境）"""
        db = (self.database or "ilbuy").replace("/", "_")
        return f"sqlite+aiosqlite:///./{db}.db"


@dataclass
class SyncTask:
    task_id:       str
    source_type:   StorageType
    target_type:   StorageType
    source_table:  str
    target_index:  str
    data_id:       str
    operation:     str          # insert | update | delete | upsert
    data:          Dict[str, Any]
    priority:      int          = 5
    retry_count:   int          = 0
    max_retries:   int          = 3
    created_at:    datetime     = field(default_factory=datetime.now)
    processed_at:  Optional[datetime] = None
    status:        SyncStatus   = SyncStatus.PENDING
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id":       self.task_id,
            "source_type":   self.source_type.value,
            "target_type":   self.target_type.value,
            "source_table":  self.source_table,
            "target_index":  self.target_index,
            "data_id":       self.data_id,
            "operation":     self.operation,
            "priority":      self.priority,
            "retry_count":   self.retry_count,
            "max_retries":   self.max_retries,
            "status":        self.status.value,
            "created_at":    self.created_at.isoformat(),
            "processed_at":  self.processed_at.isoformat() if self.processed_at else None,
            "error_message": self.error_message,
        }


@dataclass
class QueryCondition:
    field:    str
    operator: str   # eq | ne | gt | gte | lt | lte | like | in | between
    value:    Any
    logical:  str = "and"


@dataclass
class QueryRequest:
    table_name:      str
    conditions:      List[QueryCondition]
    fields:          Optional[List[str]] = None
    order_by:        Optional[List[str]] = None
    order_direction: str = "desc"
    page:            int = 1
    page_size:       int = 20
    use_cache:       bool = True
    cache_ttl:       int  = 300


# ==================== SQLAlchemy ORM 模型 ====================

Base = declarative_base()


class ProductModel(Base):
    __tablename__ = "products"
    id              = Column(Integer, primary_key=True, autoincrement=True)
    product_id      = Column(String(64),  unique=True, index=True, nullable=False)
    platform        = Column(String(32),  index=True, nullable=False)
    title           = Column(String(500), nullable=False)
    description     = Column(Text)
    category        = Column(String(100), index=True)
    brand           = Column(String(100), index=True)
    price           = Column(Float,       index=True, nullable=False)
    original_price  = Column(Float)
    currency        = Column(String(3),   default="CNY")
    sales           = Column(Integer,     default=0)
    stock           = Column(Integer,     default=0)
    rating          = Column(Float,       default=0.0)
    review_count    = Column(Integer,     default=0)
    shop_id         = Column(String(64),  index=True)
    shop_name       = Column(String(200))
    shop_rating     = Column(Float,       default=0.0)
    image_urls      = Column(JSON)
    specifications  = Column(JSON)
    tags            = Column(JSON)
    status          = Column(String(20),  default="active", index=True)
    source_data     = Column(JSON)
    weighted_score  = Column(Float,       index=True, default=0.0)
    sync_status     = Column(String(20),  default="pending", index=True)
    created_at      = Column(DateTime,    default=datetime.now, index=True)
    updated_at      = Column(DateTime,    default=datetime.now, onupdate=datetime.now, index=True)
    version         = Column(Integer,     default=1)

    __table_args__ = (
        Index("idx_product_search", "platform", "category", "brand", "price"),
        Index("idx_product_score",  "weighted_score", "created_at"),
        Index("idx_product_shop",   "shop_id", "platform"),
    )


class ProductPriceHistoryModel(Base):
    __tablename__  = "product_price_history"
    id             = Column(Integer, primary_key=True, autoincrement=True)
    product_id     = Column(String(64), index=True, nullable=False)
    price          = Column(Float,      nullable=False)
    original_price = Column(Float)
    currency       = Column(String(3),  default="CNY")
    change_type    = Column(String(20))   # increase | decrease | promotion | normal
    source         = Column(String(50))
    recorded_at    = Column(DateTime, default=datetime.now, index=True)
    created_at     = Column(DateTime, default=datetime.now)


class UserProfileModel(Base):
    __tablename__       = "user_profiles"
    user_id             = Column(String(64),  primary_key=True)
    username            = Column(String(100))
    email               = Column(String(200))
    phone               = Column(String(20))
    user_type           = Column(String(20),  index=True, nullable=False)
    company_id          = Column(String(64),  index=True)
    department          = Column(String(100))
    preferences         = Column(JSON)
    budget_range        = Column(JSON)
    purchase_history    = Column(JSON)
    interaction_history = Column(JSON)
    session_count       = Column(Integer, default=0)
    created_at          = Column(DateTime, default=datetime.now)
    updated_at          = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    last_login          = Column(DateTime)
    status              = Column(String(20), default="active", index=True)

    __table_args__ = (
        Index("idx_user_type_company", "user_type", "company_id"),
    )


class DialogSessionModel(Base):
    __tablename__      = "dialog_sessions"
    session_id         = Column(String(64), primary_key=True)
    user_id            = Column(String(64), index=True, nullable=False)
    user_type          = Column(String(20), index=True)
    current_intent     = Column(String(50))
    current_step       = Column(String(50))
    context            = Column(JSON)
    history            = Column(JSON)
    missing_info       = Column(JSON)
    turns              = Column(Integer, default=0)
    recommendation_id  = Column(String(64), index=True)
    created_at         = Column(DateTime, default=datetime.now, index=True)
    updated_at         = Column(DateTime, default=datetime.now, onupdate=datetime.now, index=True)
    expired_at         = Column(DateTime, index=True)


class SyncTaskModel(Base):
    __tablename__  = "sync_tasks"
    id             = Column(Integer, primary_key=True, autoincrement=True)
    task_id        = Column(String(64), unique=True, index=True, nullable=False)
    source_type    = Column(String(20), index=True, nullable=False)
    target_type    = Column(String(20), index=True, nullable=False)
    source_table   = Column(String(100), index=True)
    target_index   = Column(String(100), index=True)
    data_id        = Column(String(64),  index=True, nullable=False)
    operation      = Column(String(20),  index=True)
    data           = Column(JSON)
    priority       = Column(Integer, default=5, index=True)
    retry_count    = Column(Integer, default=0)
    max_retries    = Column(Integer, default=3)
    status         = Column(String(20), index=True, nullable=False)
    error_message  = Column(Text)
    created_at     = Column(DateTime, default=datetime.now, index=True)
    processed_at   = Column(DateTime, index=True)

    __table_args__ = (
        Index("idx_sync_status",  "status", "priority", "created_at"),
        Index("idx_sync_source",  "source_type", "source_table", "data_id"),
    )


class ReportModel(Base):
    __tablename__  = "reports"
    id             = Column(Integer, primary_key=True, autoincrement=True)
    report_id      = Column(String(64),  unique=True, index=True, nullable=False)
    user_id        = Column(String(64),  index=True, nullable=False)
    session_id     = Column(String(64),  index=True)
    report_type    = Column(String(50),  index=True, nullable=False)
    title          = Column(String(200), nullable=False)
    content        = Column(JSON)
    summary        = Column(Text)
    file_path      = Column(String(500))
    file_size      = Column(BigInteger, default=0)
    format         = Column(String(20),  default="json")
    status         = Column(String(20),  default="generating", index=True)
    generated_at   = Column(DateTime, default=datetime.now, index=True)
    expires_at     = Column(DateTime, index=True)
    access_count   = Column(Integer, default=0)


# ==================== OLTP存储服务 (MySQL / SQLite) ====================

class MySQLStorageService:
    """MySQL 存储服务（SQLite+aiosqlite 自动降级）"""

    def __init__(self, config: StorageConfig, use_sqlite_fallback: bool = True):
        self.config   = config
        self._use_sqlite = use_sqlite_fallback and not _HAS_AIOMYSQL
        self.engine:   Optional[AsyncEngine] = None
        self._session_factory = None

        self._q_total   = _make_counter("sl_mysql_queries_total",   "MySQL queries",  ["operation", "table_"])
        self._q_latency = _make_histogram("sl_mysql_latency_seconds", "MySQL latency", ["operation"])
        self._pool_size = _make_gauge("sl_mysql_pool_size", "MySQL pool size")

    # ── lifecycle ─────────────────────────────────────────────────

    async def connect(self):
        db_url = self.config.get_sqlite_url() if self._use_sqlite else self.config.get_connection_string()
        kw: Dict[str, Any] = {"echo": False}
        if not self._use_sqlite:
            kw.update(pool_size=self.config.connection_pool_size, max_overflow=20,
                      pool_pre_ping=True, pool_recycle=3600)
        self.engine = create_async_engine(db_url, **kw)
        self._session_factory = sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("MySQLStorageService connected (%s)", "SQLite" if self._use_sqlite else "MySQL")

    async def disconnect(self):
        if self.engine:
            await self.engine.dispose()

    # ── product CRUD ─────────────────────────────────────────────

    async def upsert_product(self, product_data: Dict[str, Any]) -> str:
        """插入或更新商品（基于 product_id）"""
        t0 = time.time()
        pid = product_data["product_id"]
        async with self._session_factory() as sess:
            row = await sess.scalar(
                select(ProductModel).where(ProductModel.product_id == pid)
            )
            if row:
                for k, v in product_data.items():
                    if hasattr(row, k):
                        setattr(row, k, v)
                row.updated_at = datetime.now()
                row.version    = (row.version or 1) + 1
                op = "update"
            else:
                row = ProductModel(
                    product_id=pid,
                    platform=product_data.get("platform", ""),
                    title=product_data.get("title", ""),
                    description=product_data.get("description"),
                    category=product_data.get("category"),
                    brand=product_data.get("brand"),
                    price=float(product_data.get("price", 0)),
                    original_price=product_data.get("original_price"),
                    currency=product_data.get("currency", "CNY"),
                    sales=product_data.get("sales", 0),
                    stock=product_data.get("stock", 0),
                    rating=product_data.get("rating", 0.0),
                    review_count=product_data.get("review_count", 0),
                    shop_id=product_data.get("shop_id"),
                    shop_name=product_data.get("shop_name"),
                    shop_rating=product_data.get("shop_rating", 0.0),
                    image_urls=product_data.get("image_urls", []),
                    specifications=product_data.get("specifications", {}),
                    tags=product_data.get("tags", []),
                    weighted_score=product_data.get("weighted_score", 0.0),
                    source_data=product_data.get("source_data", {}),
                    sync_status="pending",
                )
                sess.add(row)
                op = "insert"
            await sess.commit()

        if product_data.get("price"):
            await self._record_price_history(pid, float(product_data["price"]),
                                             product_data.get("original_price"), "normal")
        self._record_metric(op, "products", time.time() - t0)
        return pid

    # backward-compat alias used by older code
    async def insert_product(self, product_data: Dict[str, Any]) -> str:
        return await self.upsert_product(product_data)

    async def get_product(self, product_id: str) -> Optional[Dict[str, Any]]:
        async with self._session_factory() as sess:
            row = await sess.scalar(
                select(ProductModel).where(ProductModel.product_id == product_id)
            )
            return self._product_to_dict(row) if row else None

    async def bulk_upsert_products(self, products: List[Dict[str, Any]]) -> int:
        """批量 upsert，返回成功数"""
        ok = 0
        for p in products:
            try:
                await self.upsert_product(p)
                ok += 1
            except Exception as e:
                logger.warning("bulk_upsert_products skip %s: %s", p.get("product_id"), e)
        return ok

    async def search_products(self, req: QueryRequest) -> Dict[str, Any]:
        t0 = time.time()
        stmt = select(ProductModel)
        for cond in req.conditions:
            col = getattr(ProductModel, cond.field, None)
            if col is None:
                continue
            if cond.operator == "eq":
                stmt = stmt.where(col == cond.value)
            elif cond.operator == "ne":
                stmt = stmt.where(col != cond.value)
            elif cond.operator == "gt":
                stmt = stmt.where(col > cond.value)
            elif cond.operator == "gte":
                stmt = stmt.where(col >= cond.value)
            elif cond.operator == "lt":
                stmt = stmt.where(col < cond.value)
            elif cond.operator == "lte":
                stmt = stmt.where(col <= cond.value)
            elif cond.operator == "like":
                stmt = stmt.where(col.like(f"%{cond.value}%"))
            elif cond.operator == "in":
                stmt = stmt.where(col.in_(cond.value))
            elif cond.operator == "between" and isinstance(cond.value, (list, tuple)) and len(cond.value) == 2:
                stmt = stmt.where(col.between(cond.value[0], cond.value[1]))

        # count
        count_stmt = select(ProductModel.id).filter(stmt.whereclause) if stmt.whereclause is not None else select(ProductModel.id)
        # order
        if req.order_by:
            for ob in req.order_by:
                col = getattr(ProductModel, ob, None)
                if col is not None:
                    stmt = stmt.order_by(col.desc() if req.order_direction == "desc" else col.asc())

        offset = (req.page - 1) * req.page_size
        stmt   = stmt.offset(offset).limit(req.page_size)

        async with self._session_factory() as sess:
            rows  = (await sess.scalars(stmt)).all()
            total = (await sess.scalar(select(ProductModel.id).filter(
                stmt.whereclause
            ) if stmt.whereclause is not None else select(ProductModel.id))) or 0

        products = [self._product_to_dict(r) for r in rows]
        self._record_metric("search", "products", time.time() - t0)
        return {
            "products":    products,
            "total":       len(products),   # exact count via subquery is complex — use len for now
            "page":        req.page,
            "page_size":   req.page_size,
        }

    async def mark_products_synced(self, product_ids: List[str]):
        async with self._session_factory() as sess:
            await sess.execute(
                update(ProductModel)
                .where(ProductModel.product_id.in_(product_ids))
                .values(sync_status="synced", updated_at=datetime.now())
            )
            await sess.commit()

    async def get_pending_sync_products(self, limit: int = 100) -> List[Dict[str, Any]]:
        async with self._session_factory() as sess:
            rows = (await sess.scalars(
                select(ProductModel)
                .where(ProductModel.sync_status == "pending")
                .order_by(ProductModel.updated_at)
                .limit(limit)
            )).all()
        return [self._product_to_dict(r) for r in rows]

    # ── user profile ─────────────────────────────────────────────

    async def save_user_profile(self, data: Dict[str, Any]) -> str:
        async with self._session_factory() as sess:
            row = await sess.get(UserProfileModel, data["user_id"])
            if row:
                for k, v in data.items():
                    if hasattr(row, k):
                        setattr(row, k, v)
                row.updated_at = datetime.now()
            else:
                row = UserProfileModel(**{k: v for k, v in data.items()
                                          if hasattr(UserProfileModel, k)})
                sess.add(row)
            await sess.commit()
        return data["user_id"]

    async def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        async with self._session_factory() as sess:
            row = await sess.get(UserProfileModel, user_id)
        if not row:
            return None
        return {
            "user_id":    row.user_id,    "username":   row.username,
            "user_type":  row.user_type,  "company_id": row.company_id,
            "preferences": row.preferences, "budget_range": row.budget_range,
            "status":     row.status,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }

    # ── dialog session ────────────────────────────────────────────

    async def save_dialog_session(self, data: Dict[str, Any]) -> str:
        async with self._session_factory() as sess:
            row = await sess.get(DialogSessionModel, data["session_id"])
            if row:
                for k, v in data.items():
                    if hasattr(row, k):
                        setattr(row, k, v)
                row.updated_at = datetime.now()
            else:
                row = DialogSessionModel(**{k: v for k, v in data.items()
                                            if hasattr(DialogSessionModel, k)})
                sess.add(row)
            await sess.commit()
        return data["session_id"]

    async def get_dialog_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        async with self._session_factory() as sess:
            row = await sess.get(DialogSessionModel, session_id)
        if not row:
            return None
        return {
            "session_id":    row.session_id,  "user_id":       row.user_id,
            "current_intent": row.current_intent, "context":   row.context,
            "history":       row.history,     "turns":         row.turns,
            "created_at":    row.created_at.isoformat() if row.created_at else None,
        }

    # ── report ────────────────────────────────────────────────────

    async def save_report(self, data: Dict[str, Any]) -> str:
        async with self._session_factory() as sess:
            row = ReportModel(**{k: v for k, v in data.items()
                                 if hasattr(ReportModel, k)})
            sess.add(row)
            await sess.commit()
        return data["report_id"]

    async def get_report(self, report_id: str) -> Optional[Dict[str, Any]]:
        async with self._session_factory() as sess:
            row = await sess.scalar(
                select(ReportModel).where(ReportModel.report_id == report_id)
            )
        if not row:
            return None
        return {
            "report_id":  row.report_id, "user_id":  row.user_id,
            "title":      row.title,     "format":   row.format,
            "status":     row.status,    "file_path": row.file_path,
            "summary":    row.summary,   "content":  row.content,
            "generated_at": row.generated_at.isoformat() if row.generated_at else None,
        }

    # ── sync task management ──────────────────────────────────────

    async def save_sync_task(self, task: SyncTask):
        async with self._session_factory() as sess:
            sess.add(SyncTaskModel(
                task_id=task.task_id, source_type=task.source_type.value,
                target_type=task.target_type.value, source_table=task.source_table,
                target_index=task.target_index, data_id=task.data_id,
                operation=task.operation, data=task.data,
                priority=task.priority, retry_count=task.retry_count,
                max_retries=task.max_retries, status=task.status.value,
                error_message=task.error_message,
            ))
            await sess.commit()

    async def update_sync_task(self, task: SyncTask):
        async with self._session_factory() as sess:
            row = await sess.scalar(
                select(SyncTaskModel).where(SyncTaskModel.task_id == task.task_id)
            )
            if row:
                row.status        = task.status.value
                row.retry_count   = task.retry_count
                row.error_message = task.error_message
                row.processed_at  = task.processed_at or datetime.now()
                await sess.commit()

    async def get_pending_sync_tasks(self, limit: int = 50) -> List[SyncTask]:
        async with self._session_factory() as sess:
            rows = (await sess.scalars(
                select(SyncTaskModel)
                .where(SyncTaskModel.status.in_(["pending", "failed"]))
                .where(SyncTaskModel.retry_count < SyncTaskModel.max_retries)
                .order_by(SyncTaskModel.priority.desc(), SyncTaskModel.created_at)
                .limit(limit)
            )).all()
        return [
            SyncTask(
                task_id=r.task_id, source_type=StorageType(r.source_type),
                target_type=StorageType(r.target_type), source_table=r.source_table,
                target_index=r.target_index, data_id=r.data_id,
                operation=r.operation, data=r.data or {},
                priority=r.priority, retry_count=r.retry_count,
                max_retries=r.max_retries, status=SyncStatus(r.status),
            )
            for r in rows
        ]

    # ── private helpers ────────────────────────────────────────────

    async def _record_price_history(self, pid: str, price: float,
                                    original_price: Optional[float], change_type: str):
        try:
            async with self._session_factory() as sess:
                sess.add(ProductPriceHistoryModel(
                    product_id=pid, price=price, original_price=original_price,
                    change_type=change_type, source="system", recorded_at=datetime.now(),
                ))
                await sess.commit()
        except Exception as e:
            logger.debug("Price history error: %s", e)

    def _record_metric(self, op: str, table: str, elapsed: float):
        if self._q_total:
            self._q_total.labels(operation=op, table_=table).inc()
        if self._q_latency:
            self._q_latency.labels(operation=op).observe(elapsed)

    @staticmethod
    def _product_to_dict(row: ProductModel) -> Dict[str, Any]:
        return {
            "product_id":    row.product_id,   "platform":      row.platform,
            "title":         row.title,         "description":   row.description,
            "category":      row.category,      "brand":         row.brand,
            "price":         row.price,          "original_price": row.original_price,
            "currency":      row.currency,       "sales":         row.sales,
            "stock":         row.stock,          "rating":        row.rating,
            "review_count":  row.review_count,   "shop_id":       row.shop_id,
            "shop_name":     row.shop_name,      "shop_rating":   row.shop_rating,
            "image_urls":    row.image_urls,     "specifications": row.specifications,
            "tags":          row.tags,           "weighted_score": row.weighted_score,
            "sync_status":   row.sync_status,    "version":       row.version,
            "created_at":    row.created_at.isoformat() if row.created_at else None,
            "updated_at":    row.updated_at.isoformat() if row.updated_at else None,
        }


# ==================== Redis存储服务 ====================

class RedisStorageService:
    """Redis 存储服务（内存字典降级）"""

    def __init__(self, config: StorageConfig):
        self.config     = config
        self._redis     = None
        self._use_mock  = not _HAS_REDIS
        self._mock: Dict[str, Any] = {}        # fallback in-memory store
        self._mock_ttl: Dict[str, float] = {}  # key → expiry timestamp

        self._ops     = _make_counter("sl_redis_ops_total",       "Redis ops",     ["operation"])
        self._latency = _make_histogram("sl_redis_latency_seconds", "Redis latency", ["operation"])

    async def connect(self):
        if self._use_mock:
            logger.warning("Redis unavailable — using in-memory fallback")
            return
        try:
            self._redis = await aioredis.from_url(
                self.config.get_connection_string(),
                encoding="utf-8", decode_responses=True,
                max_connections=self.config.connection_pool_size,
            )
            await self._redis.ping()
            logger.info("RedisStorageService connected %s:%s", self.config.host, self.config.port)
        except Exception as e:
            logger.warning("Redis connection failed (%s) — using in-memory fallback", e)
            self._use_mock = True

    async def disconnect(self):
        if self._redis:
            await self._redis.aclose()

    # ── core ops ─────────────────────────────────────────────────

    async def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        t0 = time.time()
        try:
            serialized = self._serialize(value)
            if self._use_mock:
                self._mock[key] = serialized
                self._mock_ttl[key] = time.time() + ttl
            else:
                await self._redis.setex(key, ttl, serialized)
            self._inc("set", time.time() - t0)
            return True
        except Exception as e:
            logger.error("Redis set error: %s", e)
            return False

    async def get(self, key: str) -> Optional[Any]:
        t0 = time.time()
        try:
            if self._use_mock:
                exp = self._mock_ttl.get(key, 0)
                if exp and time.time() > exp:
                    self._mock.pop(key, None)
                    self._mock_ttl.pop(key, None)
                    return None
                raw = self._mock.get(key)
            else:
                raw = await self._redis.get(key)
            self._inc("get", time.time() - t0)
            return self._deserialize(raw) if raw is not None else None
        except Exception as e:
            logger.error("Redis get error: %s", e)
            return None

    async def delete(self, key: str) -> bool:
        t0 = time.time()
        try:
            if self._use_mock:
                existed = key in self._mock
                self._mock.pop(key, None)
                self._mock_ttl.pop(key, None)
            else:
                existed = await self._redis.delete(key) > 0
            self._inc("delete", time.time() - t0)
            return existed
        except Exception as e:
            logger.error("Redis delete error: %s", e)
            return False

    async def exists(self, key: str) -> bool:
        if self._use_mock:
            return key in self._mock and time.time() < self._mock_ttl.get(key, float("inf"))
        try:
            return bool(await self._redis.exists(key))
        except Exception:
            return False

    async def incr(self, key: str, amount: int = 1, ttl: Optional[int] = None) -> int:
        t0 = time.time()
        try:
            if self._use_mock:
                cur = int(self._mock.get(key, "0") or "0")
                cur += amount
                self._mock[key] = str(cur)
                if ttl:
                    self._mock_ttl[key] = time.time() + ttl
                result = cur
            else:
                result = await self._redis.incrby(key, amount)
                if ttl:
                    await self._redis.expire(key, ttl)
            self._inc("incr", time.time() - t0)
            return result
        except Exception as e:
            logger.error("Redis incr error: %s", e)
            return 0

    # ── domain helpers ─────────────────────────────────────────────

    async def set_cache(self, key: str, value: Any, ttl: int = 300) -> bool:
        return await self.set(key, value, ttl)

    async def get_cache(self, key: str) -> Optional[Any]:
        return await self.get(key)

    async def set_session(self, session_id: str, data: Dict, ttl: int = 3600) -> bool:
        return await self.set(f"session:{session_id}", data, ttl)

    async def get_session(self, session_id: str) -> Optional[Dict]:
        return await self.get(f"session:{session_id}")

    async def delete_session(self, session_id: str) -> bool:
        return await self.delete(f"session:{session_id}")

    async def publish(self, channel: str, message: Dict) -> int:
        try:
            if self._use_mock:
                return 0
            return await self._redis.publish(channel, json.dumps(message, ensure_ascii=False, default=str))
        except Exception as e:
            logger.error("Redis publish error: %s", e)
            return 0

    async def get_info(self) -> Dict[str, Any]:
        if self._use_mock:
            return {"mode": "in-memory", "keys": len(self._mock)}
        try:
            info = await self._redis.info()
            return {
                "memory_used":      info.get("used_memory", 0),
                "connected_clients": info.get("connected_clients", 0),
                "keyspace_hits":    info.get("keyspace_hits", 0),
                "keyspace_misses":  info.get("keyspace_misses", 0),
                "hit_rate": round(
                    info.get("keyspace_hits", 0) /
                    max(info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0), 1), 4
                ),
            }
        except Exception as e:
            return {"error": str(e)}

    # ── private ───────────────────────────────────────────────────

    @staticmethod
    def _serialize(value: Any) -> str:
        if _HAS_MSGPACK:
            # msgpack → base64 string so Redis (text mode) can store it
            import base64
            return base64.b64encode(_msgpack.packb(value, use_bin_type=True)).decode()
        return json.dumps(value, ensure_ascii=False, default=str)

    @staticmethod
    def _deserialize(raw: str) -> Any:
        if _HAS_MSGPACK:
            import base64
            try:
                return _msgpack.unpackb(base64.b64decode(raw), raw=False)
            except Exception:
                pass
        try:
            return json.loads(raw)
        except Exception:
            return raw

    def _inc(self, op: str, elapsed: float):
        if self._ops:
            self._ops.labels(operation=op).inc()
        if self._latency:
            self._latency.labels(operation=op).observe(elapsed)


# ==================== Elasticsearch存储服务 ====================

class ElasticsearchStorageService:
    """Elasticsearch 存储服务（内存字典降级）"""

    _PRODUCT_MAPPING = {
        "settings": {"number_of_shards": 3, "number_of_replicas": 1},
        "mappings": {"properties": {
            "product_id":    {"type": "keyword"},
            "title":         {"type": "text"},
            "description":   {"type": "text"},
            "platform":      {"type": "keyword"},
            "category":      {"type": "keyword"},
            "brand":         {"type": "keyword"},
            "price":         {"type": "float"},
            "original_price":{"type": "float"},
            "sales":         {"type": "integer"},
            "rating":        {"type": "float"},
            "review_count":  {"type": "integer"},
            "shop_name":     {"type": "text"},
            "weighted_score":{"type": "float"},
            "tags":          {"type": "keyword"},
            "status":        {"type": "keyword"},
            "created_at":    {"type": "date"},
            "updated_at":    {"type": "date"},
        }},
    }

    def __init__(self, config: StorageConfig):
        self.config    = config
        self._client   = None
        self._use_mock = not _HAS_ES
        self._mock_store: Dict[str, Dict[str, Any]] = {}   # index → {id: doc}

        self._ops     = _make_counter("sl_es_ops_total",       "ES ops",     ["operation", "index_"])
        self._latency = _make_histogram("sl_es_latency_seconds", "ES latency", ["operation"])

    async def connect(self):
        if self._use_mock:
            logger.warning("Elasticsearch unavailable — using in-memory fallback")
            return
        try:
            auth = None
            if self.config.username and self.config.password:
                auth = (self.config.username, self.config.password)
            self._client = AsyncElasticsearch(
                hosts=[{"host": self.config.host, "port": self.config.port}],
                basic_auth=auth,
                verify_certs=self.config.ssl_enabled,
            )
            await self._client.ping()
            await self._ensure_indices()
            logger.info("Elasticsearch connected %s:%s", self.config.host, self.config.port)
        except Exception as e:
            logger.warning("ES connection failed (%s) — using in-memory fallback", e)
            self._use_mock = True

    async def disconnect(self):
        if self._client:
            await self._client.close()

    async def _ensure_indices(self):
        if not self._client:
            return
        for name, mapping in [("products", self._PRODUCT_MAPPING)]:
            if not await self._client.indices.exists(index=name):
                await self._client.indices.create(index=name, body=mapping)
                logger.info("ES index created: %s", name)

    # ── CRUD ──────────────────────────────────────────────────────

    async def index_doc(self, index: str, doc: Dict, doc_id: Optional[str] = None) -> str:
        t0 = time.time()
        did = doc_id or doc.get("product_id") or doc.get("id") or str(uuid.uuid4())
        try:
            if self._use_mock:
                self._mock_store.setdefault(index, {})[did] = copy.deepcopy(doc)
            else:
                await self._client.index(index=index, id=did, document=doc, refresh=True)
            self._inc("index", index, time.time() - t0)
            return did
        except Exception as e:
            self._inc("error", index, time.time() - t0)
            logger.error("ES index error: %s", e)
            raise

    async def get_doc(self, index: str, doc_id: str) -> Optional[Dict]:
        try:
            if self._use_mock:
                return copy.deepcopy(self._mock_store.get(index, {}).get(doc_id))
            resp = await self._client.get(index=index, id=doc_id)
            return resp["_source"]
        except Exception:
            return None

    async def update_doc(self, index: str, doc_id: str, updates: Dict) -> bool:
        t0 = time.time()
        try:
            if self._use_mock:
                store = self._mock_store.setdefault(index, {})
                if doc_id in store:
                    store[doc_id].update(updates)
            else:
                await self._client.update(index=index, id=doc_id, doc=updates)
            self._inc("update", index, time.time() - t0)
            return True
        except Exception as e:
            self._inc("error", index, time.time() - t0)
            logger.error("ES update error: %s", e)
            return False

    async def delete_doc(self, index: str, doc_id: str) -> bool:
        t0 = time.time()
        try:
            if self._use_mock:
                self._mock_store.get(index, {}).pop(doc_id, None)
            else:
                await self._client.delete(index=index, id=doc_id)
            self._inc("delete", index, time.time() - t0)
            return True
        except Exception as e:
            self._inc("error", index, time.time() - t0)
            return False

    async def search(
        self,
        index: str,
        query_text: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "desc",
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        t0 = time.time()
        offset = (page - 1) * page_size
        try:
            if self._use_mock:
                docs = list(self._mock_store.get(index, {}).values())
                # basic text filter
                if query_text:
                    qt = query_text.lower()
                    docs = [d for d in docs
                            if qt in str(d.get("title", "")).lower()
                            or qt in str(d.get("description", "")).lower()]
                if filters:
                    for fk, fv in filters.items():
                        docs = [d for d in docs if d.get(fk) == fv]
                if sort_by:
                    docs.sort(key=lambda d: d.get(sort_by, 0),
                              reverse=(sort_order == "desc"))
                total = len(docs)
                hits  = docs[offset: offset + page_size]
                return {"hits": hits, "total": total, "took": 0}

            # Real ES query
            must: List[Dict] = []
            if query_text:
                must.append({"multi_match": {
                    "query": query_text,
                    "fields": ["title^3", "description", "brand", "category"],
                    "fuzziness": "AUTO",
                }})
            if filters:
                for fk, fv in filters.items():
                    must.append({"term" if not isinstance(fv, list) else "terms":
                                 {fk: fv}})
            q    = {"bool": {"must": must}} if must else {"match_all": {}}
            body = {"query": q, "from": offset, "size": page_size}
            if sort_by:
                body["sort"] = [{sort_by: {"order": sort_order}}]
            resp = await self._client.search(index=index, body=body)
            hits = [h["_source"] for h in resp["hits"]["hits"]]
            total = resp["hits"]["total"]["value"]
            self._inc("search", index, time.time() - t0)
            return {"hits": hits, "total": total, "took": resp.get("took", 0)}
        except Exception as e:
            self._inc("error", index, time.time() - t0)
            logger.error("ES search error: %s", e)
            return {"hits": [], "total": 0, "took": 0}

    async def bulk_index(self, index: str, docs: List[Dict], id_field: str = "product_id") -> Dict[str, int]:
        t0 = time.time()
        try:
            if self._use_mock:
                store = self._mock_store.setdefault(index, {})
                for doc in docs:
                    did = doc.get(id_field) or str(uuid.uuid4())
                    store[did] = copy.deepcopy(doc)
                self._inc("bulk", index, time.time() - t0)
                return {"successful": len(docs), "failed": 0}

            actions = [{"_index": index, "_id": doc.get(id_field, str(uuid.uuid4())),
                        "_source": doc} for doc in docs]
            ok, errors = await _es_helpers.async_bulk(self._client, actions, raise_on_error=False)
            self._inc("bulk", index, time.time() - t0)
            return {"successful": ok, "failed": len(errors) if isinstance(errors, list) else 0}
        except Exception as e:
            self._inc("error", index, time.time() - t0)
            logger.error("ES bulk error: %s", e)
            return {"successful": 0, "failed": len(docs)}

    # ── convenience aliases ──────────────────────────────────────

    async def index_product(self, product: Dict) -> str:
        """Convenience alias: index a product doc into the 'products' index."""
        return await self.index_doc("products", product,
                                    doc_id=product.get("product_id"))

    async def search_products(
        self, query: Dict[str, Any], page: int = 1, page_size: int = 20
    ) -> List[Dict]:
        """Convenience alias: full-text search over 'products' index."""
        res = await self.search(
            "products",
            query_text=query.get("keyword") or query.get("query_text"),
            filters=query.get("filters"),
            sort_by=query.get("sort_by"),
            sort_order=query.get("sort_order", "desc"),
            page=page,
            page_size=page_size,
        )
        return res.get("hits", [])

    def _inc(self, op: str, index: str, elapsed: float):
        if self._ops:
            self._ops.labels(operation=op, index_=index).inc()
        if self._latency:
            self._latency.labels(operation=op).observe(elapsed)


# ==================== ClickHouse存储服务 ====================

class ClickHouseStorageService:
    """ClickHouse 存储服务（内存列表降级；同步驱动通过线程池调用）"""

    _CREATE_TABLES = {
        "user_behavior_logs": """
        CREATE TABLE IF NOT EXISTS user_behavior_logs (
            log_id String, user_id String, session_id String,
            event_type String, event_name String, page_url String,
            product_id Nullable(String), platform Nullable(String),
            duration_ms Float32, event_data String,
            timestamp DateTime, date Date DEFAULT toDate(timestamp)
        ) ENGINE = MergeTree()
        PARTITION BY toYYYYMM(date)
        ORDER BY (date, user_id, session_id, timestamp)
        TTL date + INTERVAL 180 DAY
        """,
        "product_view_logs": """
        CREATE TABLE IF NOT EXISTS product_view_logs (
            view_id String, user_id String, session_id String,
            product_id String, platform String,
            view_duration_ms Float32, scroll_depth Float32,
            action_type String, action_data String,
            timestamp DateTime, date Date DEFAULT toDate(timestamp)
        ) ENGINE = MergeTree()
        PARTITION BY toYYYYMM(date)
        ORDER BY (date, product_id, user_id, timestamp)
        TTL date + INTERVAL 180 DAY
        """,
        "system_metrics": """
        CREATE TABLE IF NOT EXISTS system_metrics (
            metric_id String, service_name String, metric_name String,
            metric_value Float64, metric_type String, labels String,
            timestamp DateTime, date Date DEFAULT toDate(timestamp)
        ) ENGINE = MergeTree()
        PARTITION BY toYYYYMM(date)
        ORDER BY (date, service_name, metric_name, timestamp)
        TTL date + INTERVAL 90 DAY
        """,
    }

    def __init__(self, config: StorageConfig):
        self.config    = config
        self._client   = None
        self._use_mock = not _HAS_CLICKHOUSE
        self._mock_logs: Dict[str, List[Dict]] = {}   # table → [rows]

        self._queries = _make_counter("sl_ch_queries_total",    "ClickHouse queries", ["table_"])
        self._latency = _make_histogram("sl_ch_latency_seconds", "ClickHouse latency")

    async def connect(self):
        if self._use_mock:
            logger.warning("ClickHouse unavailable — using in-memory fallback")
            return
        try:
            self._client = _CHClient(
                host=self.config.host, port=self.config.port,
                user=self.config.username or "default",
                password=self.config.password or "",
                database=self.config.database or "default",
                secure=self.config.ssl_enabled,
            )
            await _run_sync(self._client.execute, "SELECT 1")
            await self._create_tables()
            logger.info("ClickHouse connected %s:%s", self.config.host, self.config.port)
        except Exception as e:
            logger.warning("ClickHouse connection failed (%s) — using in-memory fallback", e)
            self._use_mock = True

    async def disconnect(self):
        if self._client:
            await _run_sync(self._client.disconnect)

    async def _create_tables(self):
        for name, ddl in self._CREATE_TABLES.items():
            try:
                await _run_sync(self._client.execute, ddl)
            except Exception as e:
                logger.debug("CH table %s may exist: %s", name, e)

    # ── write ──────────────────────────────────────────────────────

    async def insert_log(self, table: str, row: Dict[str, Any]) -> bool:
        t0 = time.time()
        try:
            if self._use_mock:
                self._mock_logs.setdefault(table, []).append(copy.deepcopy(row))
            else:
                cols = list(row.keys())
                vals = [row[c] for c in cols]
                q = f"INSERT INTO {table} ({','.join(cols)}) VALUES"
                await _run_sync(self._client.execute, q, [vals])
            self._inc(table, time.time() - t0)
            return True
        except Exception as e:
            logger.error("CH insert error: %s", e)
            return False

    async def bulk_insert(self, table: str, rows: List[Dict]) -> int:
        ok = 0
        for row in rows:
            if await self.insert_log(table, row):
                ok += 1
        return ok

    # ── read ───────────────────────────────────────────────────────

    async def query(
        self,
        table: str,
        conditions: Optional[Dict[str, Any]] = None,
        start_time: Optional[datetime] = None,
        end_time:   Optional[datetime] = None,
        limit: int = 1000,
    ) -> List[Dict[str, Any]]:
        t0 = time.time()
        try:
            if self._use_mock:
                rows = self._mock_logs.get(table, [])
                if conditions:
                    rows = [r for r in rows
                            if all(r.get(k) == v for k, v in conditions.items())]
                if start_time:
                    rows = [r for r in rows
                            if isinstance(r.get("timestamp"), datetime)
                            and r["timestamp"] >= start_time]
                if end_time:
                    rows = [r for r in rows
                            if isinstance(r.get("timestamp"), datetime)
                            and r["timestamp"] <= end_time]
                return rows[-limit:]

            where: List[str] = []
            params: Dict = {}
            if conditions:
                for i, (k, v) in enumerate(conditions.items()):
                    where.append(f"{k} = %(p{i})s")
                    params[f"p{i}"] = v
            if start_time:
                where.append("timestamp >= %(st)s")
                params["st"] = start_time
            if end_time:
                where.append("timestamp <= %(et)s")
                params["et"] = end_time
            wc  = "WHERE " + " AND ".join(where) if where else ""
            sql = f"SELECT * FROM {table} {wc} ORDER BY timestamp DESC LIMIT {limit}"
            raw = await _run_sync(self._client.execute, sql, params, with_column_types=True)
            data, col_types = raw
            cols = [c[0] for c in col_types]
            self._inc(table, time.time() - t0)
            return [dict(zip(cols, r)) for r in data]
        except Exception as e:
            logger.error("CH query error: %s", e)
            return []

    async def get_user_behavior_stats(
        self,
        user_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date:   Optional[datetime] = None,
    ) -> Dict[str, Any]:
        cond: Dict[str, Any] = {}
        if user_id:
            cond["user_id"] = user_id
        rows = await self.query("user_behavior_logs", cond, start_date, end_date)
        if not rows:
            return {"stats": [], "total_events": 0}
        by_type: Dict[str, int] = {}
        for r in rows:
            et = r.get("event_type", "unknown")
            by_type[et] = by_type.get(et, 0) + 1
        return {"stats": [{"event_type": k, "count": v} for k, v in by_type.items()],
                "total_events": len(rows)}

    # ── convenience aliases ──────────────────────────────────────

    async def insert_behavior(
        self,
        user_id: str,
        product_id: str,
        event_type: str,
        event_data: Optional[Dict] = None,
    ) -> bool:
        """Convenience alias: insert a user behavior event."""
        row = {
            "log_id":     str(uuid.uuid4()),
            "user_id":    user_id,
            "session_id": event_data.get("session_id", "") if event_data else "",
            "event_type": event_type,
            "event_name": event_type,
            "page_url":   event_data.get("page_url", "") if event_data else "",
            "product_id": product_id,
            "platform":   event_data.get("platform") if event_data else None,
            "duration_ms": float(event_data.get("duration_ms", 0)) if event_data else 0.0,
            "event_data": json.dumps(event_data or {}),
            "timestamp":  datetime.now(),
        }
        return await self.insert_log("user_behavior_logs", row)

    async def get_product_analytics(
        self,
        product_id: Optional[str] = None,
        platform:   Optional[str] = None,
        days: int = 7,
    ) -> Dict[str, Any]:
        cond: Dict[str, Any] = {}
        if product_id:
            cond["product_id"] = product_id
        if platform:
            cond["platform"] = platform
        since = datetime.now() - timedelta(days=days)
        rows  = await self.query("product_view_logs", cond, start_time=since)
        if not rows:
            return {"analytics": [], "period_days": days}
        buys  = sum(1 for r in rows if r.get("action_type") == "purchase")
        carts = sum(1 for r in rows if r.get("action_type") == "add_to_cart")
        return {"analytics": [{"total_views": len(rows), "purchases": buys,
                               "add_to_cart": carts}], "period_days": days}

    def _inc(self, table: str, elapsed: float):
        if self._queries:
            self._queries.labels(table_=table).inc()
        if self._latency:
            self._latency.observe(elapsed)


# ==================== MinIO文件存储服务 ====================

class MinIOStorageService:
    """MinIO 文件存储服务（内存字典降级）"""

    _BUCKETS = ["reports", "images", "contracts", "backups", "temp"]

    def __init__(self, config: StorageConfig):
        self.config    = config
        self._client   = None
        self._use_mock = not _HAS_MINIO
        self._mock_store: Dict[str, Dict[str, bytes]] = {}  # bucket → {name: bytes}

        self._ops     = _make_counter("sl_minio_ops_total",       "MinIO ops",     ["operation", "bucket_"])
        self._latency = _make_histogram("sl_minio_latency_seconds", "MinIO latency", ["operation"])

    async def connect(self):
        if self._use_mock:
            logger.warning("MinIO unavailable — using in-memory fallback")
            for b in self._BUCKETS:
                self._mock_store.setdefault(b, {})
            return
        try:
            self._client = _Minio(
                endpoint=f"{self.config.host}:{self.config.port}",
                access_key=self.config.username or "minioadmin",
                secret_key=self.config.password or "minioadmin",
                secure=self.config.ssl_enabled,
            )
            await _run_sync(self._client.list_buckets)
            await self._ensure_buckets()
            logger.info("MinIO connected %s:%s", self.config.host, self.config.port)
        except Exception as e:
            logger.warning("MinIO connection failed (%s) — using in-memory fallback", e)
            self._use_mock = True
            for b in self._BUCKETS:
                self._mock_store.setdefault(b, {})

    async def _ensure_buckets(self):
        for name in self._BUCKETS:
            try:
                if not await _run_sync(self._client.bucket_exists, name):
                    await _run_sync(self._client.make_bucket, name)
            except Exception as e:
                logger.debug("Bucket %s: %s", name, e)

    # ── upload ────────────────────────────────────────────────────

    async def upload_data(
        self,
        bucket: str,
        object_name: str,
        data: Union[bytes, str, Dict],
        metadata: Optional[Dict[str, str]] = None,
        content_type: str = "application/json",
    ) -> str:
        t0 = time.time()
        if isinstance(data, dict):
            raw = json.dumps(data, ensure_ascii=False, default=str).encode()
        elif isinstance(data, str):
            raw = data.encode()
        else:
            raw = data
        try:
            if self._use_mock:
                self._mock_store.setdefault(bucket, {})[object_name] = raw
                url = f"mock://{bucket}/{object_name}"
            else:
                await _run_sync(
                    self._client.put_object,
                    bucket, object_name, io.BytesIO(raw), len(raw),
                    metadata=metadata or {}, content_type=content_type,
                )
                url = await self.get_presigned_url(bucket, object_name)
            self._inc("upload", bucket, time.time() - t0)
            return url
        except Exception as e:
            self._inc("error", bucket, time.time() - t0)
            logger.error("MinIO upload error: %s", e)
            raise

    async def upload_file(self, bucket: str, object_name: str, file_path: str,
                          metadata: Optional[Dict[str, str]] = None,
                          content_type: str = "application/octet-stream") -> str:
        t0 = time.time()
        try:
            if self._use_mock:
                with open(file_path, "rb") as f:
                    self._mock_store.setdefault(bucket, {})[object_name] = f.read()
                url = f"mock://{bucket}/{object_name}"
            else:
                await _run_sync(self._client.fput_object, bucket, object_name,
                                file_path, metadata=metadata or {}, content_type=content_type)
                url = await self.get_presigned_url(bucket, object_name)
            self._inc("upload", bucket, time.time() - t0)
            return url
        except Exception as e:
            self._inc("error", bucket, time.time() - t0)
            logger.error("MinIO upload_file error: %s", e)
            raise

    # ── download ──────────────────────────────────────────────────

    async def download_data(self, bucket: str, object_name: str) -> Optional[bytes]:
        t0 = time.time()
        try:
            if self._use_mock:
                data = self._mock_store.get(bucket, {}).get(object_name)
            else:
                resp = await _run_sync(self._client.get_object, bucket, object_name)
                data = resp.read()
                resp.close(); resp.release_conn()
            self._inc("download", bucket, time.time() - t0)
            return data
        except Exception as e:
            self._inc("error", bucket, time.time() - t0)
            logger.error("MinIO download error: %s", e)
            return None

    async def download_file(self, bucket: str, object_name: str, dest: str) -> bool:
        try:
            data = await self.download_data(bucket, object_name)
            if data is None:
                return False
            with open(dest, "wb") as f:
                f.write(data)
            return True
        except Exception:
            return False

    # ── other ─────────────────────────────────────────────────────

    async def delete_file(self, bucket: str, object_name: str) -> bool:
        try:
            if self._use_mock:
                self._mock_store.get(bucket, {}).pop(object_name, None)
            else:
                await _run_sync(self._client.remove_object, bucket, object_name)
            return True
        except Exception:
            return False

    async def list_files(self, bucket: str, prefix: str = "") -> List[Dict[str, Any]]:
        try:
            if self._use_mock:
                return [{"object_name": k, "size": len(v)}
                        for k, v in self._mock_store.get(bucket, {}).items()
                        if k.startswith(prefix)]
            objs = await _run_sync(self._client.list_objects, bucket, prefix=prefix, recursive=True)
            return [{"object_name": o.object_name, "size": o.size,
                     "last_modified": str(o.last_modified)} for o in objs]
        except Exception:
            return []

    async def get_presigned_url(self, bucket: str, object_name: str, expires: int = 3600) -> str:
        if self._use_mock:
            return f"mock://{bucket}/{object_name}"
        try:
            return await _run_sync(self._client.presigned_get_object,
                                   bucket, object_name, timedelta(seconds=expires))
        except Exception:
            return ""

    async def save_report(self, report_data: Dict, report_id: str,
                          user_id: str, fmt: str = "json") -> str:
        ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
        name = f"{user_id}/{report_id}_{ts}.{fmt}"
        content: Union[str, bytes]
        if fmt == "json":
            content = json.dumps(report_data, ensure_ascii=False, indent=2)
            ctype   = "application/json"
        elif fmt == "html":
            content = self._html_report(report_data)
            ctype   = "text/html"
        else:
            content = json.dumps(report_data, ensure_ascii=False)
            ctype   = "application/octet-stream"
        return await self.upload_data("reports", name, content,
                                      metadata={"report_id": report_id, "user_id": user_id},
                                      content_type=ctype)

    def _inc(self, op: str, bucket: str, elapsed: float):
        if self._ops:
            self._ops.labels(operation=op, bucket_=bucket).inc()
        if self._latency:
            self._latency.labels(operation=op).observe(elapsed)

    @staticmethod
    def _html_report(data: Dict) -> str:
        products_html = ""
        for p in data.get("products", [])[:10]:
            products_html += (
                f"<div class='product'><h3>{p.get('title','')}</h3>"
                f"<p>¥{p.get('price',0)} | 评分: {p.get('score',0)}</p></div>"
            )
        return f"""<!DOCTYPE html><html><head><meta charset='UTF-8'>
<title>商品分析报告</title>
<style>body{{font-family:Arial;margin:20px}}.product{{border:1px solid #ddd;padding:15px;margin:10px;border-radius:5px}}</style>
</head><body>
<h1>商品分析报告</h1>
<p>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
<h2>摘要</h2><p>{data.get('summary','')}</p>
<h2>推荐商品</h2>{products_html}
<h2>分析说明</h2><p>{data.get('explanation','')}</p>
</body></html>"""


# ==================== 数据同步服务 ====================

class DataSyncService:
    """MySQL → ES / ClickHouse 增量同步服务（Canal 模拟 + 重试队列）"""

    def __init__(
        self,
        mysql: MySQLStorageService,
        es:    ElasticsearchStorageService,
        redis: RedisStorageService,
        ch:    ClickHouseStorageService,
        minio: MinIOStorageService,
    ):
        self._mysql = mysql
        self._es    = es
        self._redis = redis
        self._ch    = ch
        self._minio = minio

        self._queue: asyncio.Queue = asyncio.Queue(maxsize=10_000)
        self._running = False
        self._workers: List[asyncio.Task] = []

        self._sync_ops  = _make_counter("sl_sync_ops_total",     "Sync ops",     ["source", "target", "status"])
        self._sync_time = _make_histogram("sl_sync_latency_seconds", "Sync latency")

    # ── lifecycle ─────────────────────────────────────────────────

    async def startup(self, workers: int = 3):
        self._running = True
        self._workers = [asyncio.create_task(self._worker(i)) for i in range(workers)]
        # background: poll DB for pending sync items
        self._workers.append(asyncio.create_task(self._canal_poller()))
        logger.info("DataSyncService started (%d workers)", workers)

    async def shutdown(self):
        self._running = False
        for w in self._workers:
            w.cancel()
        await asyncio.gather(*self._workers, return_exceptions=True)

    # ── public API ────────────────────────────────────────────────

    async def enqueue(self, task: SyncTask) -> bool:
        """将同步任务加入内存队列 + 持久化到 DB"""
        try:
            await self._mysql.save_sync_task(task)
            await self._queue.put(task)
            return True
        except asyncio.QueueFull:
            logger.warning("Sync queue full, task %s dropped", task.task_id)
            return False

    async def sync_product_to_es(self, product: Dict[str, Any]) -> bool:
        """直接将商品同步到 ES（绕过队列的快速路径）"""
        try:
            pid = product.get("product_id", str(uuid.uuid4()))
            await self._es.index_doc("products", product, doc_id=pid)
            return True
        except Exception as e:
            logger.error("sync_product_to_es error: %s", e)
            return False

    async def sync_products_batch(self, products: List[Dict[str, Any]]) -> Dict[str, int]:
        """批量同步商品到 ES"""
        result = await self._es.bulk_index("products", products)
        if products:
            pids = [p["product_id"] for p in products if "product_id" in p]
            await self._mysql.mark_products_synced(pids)
        return result

    async def emit_behavior_log(self, log: Dict[str, Any]) -> bool:
        """写入用户行为日志到 ClickHouse + Redis pubsub"""
        log.setdefault("log_id",    str(uuid.uuid4()))
        log.setdefault("timestamp", datetime.now())
        ok = await self._ch.insert_log("user_behavior_logs", log)
        await self._redis.publish("behavior_events", log)
        return ok

    async def emit_product_view(self, view: Dict[str, Any]) -> bool:
        view.setdefault("view_id",   str(uuid.uuid4()))
        view.setdefault("timestamp", datetime.now())
        return await self._ch.insert_log("product_view_logs", view)

    async def flush_pending(self) -> Dict[str, Any]:
        """立即处理所有 DB 中 pending 的同步任务（可通过 API 触发）"""
        tasks = await self._mysql.get_pending_sync_tasks(limit=500)
        ok = fail = 0
        for task in tasks:
            success = await self._execute_task(task)
            if success:
                ok += 1
            else:
                fail += 1
        return {"flushed": ok, "failed": fail}

    # ── worker loop ───────────────────────────────────────────────

    async def _worker(self, wid: int):
        logger.info("SyncWorker-%d started", wid)
        while self._running:
            try:
                task = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                await self._execute_task(task)
                self._queue.task_done()
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("SyncWorker-%d error: %s", wid, e)

    async def _canal_poller(self):
        """模拟 Canal：定期从 DB 拉取待同步商品推入队列"""
        while self._running:
            try:
                products = await self._mysql.get_pending_sync_products(limit=100)
                for p in products:
                    task = SyncTask(
                        task_id=f"sync_{uuid.uuid4().hex[:8]}",
                        source_type=StorageType.MYSQL,
                        target_type=StorageType.ELASTICSEARCH,
                        source_table="products",
                        target_index="products",
                        data_id=p["product_id"],
                        operation="upsert",
                        data=p,
                        priority=5,
                    )
                    await self.enqueue(task)
                await asyncio.sleep(10)   # poll interval
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Canal poller error: %s", e)
                await asyncio.sleep(5)

    # ── task execution ────────────────────────────────────────────

    async def _execute_task(self, task: SyncTask) -> bool:
        t0 = time.time()
        task.status = SyncStatus.SYNCING
        try:
            if task.target_type == StorageType.ELASTICSEARCH:
                await self._sync_to_es(task)
            elif task.target_type == StorageType.CLICKHOUSE:
                await self._sync_to_ch(task)
            elif task.target_type == StorageType.REDIS:
                await self._sync_to_redis(task)
            else:
                raise ValueError(f"Unsupported target: {task.target_type}")

            task.status       = SyncStatus.SYNCED
            task.processed_at = datetime.now()
            await self._mysql.update_sync_task(task)
            self._record(task, "success", time.time() - t0)
            return True
        except Exception as exc:
            task.retry_count   += 1
            task.error_message  = str(exc)
            task.status         = SyncStatus.FAILED if task.retry_count >= task.max_retries else SyncStatus.PENDING
            task.processed_at   = datetime.now()
            await self._mysql.update_sync_task(task)
            self._record(task, "failure", time.time() - t0)
            logger.warning("Sync task %s failed (%d/%d): %s",
                           task.task_id, task.retry_count, task.max_retries, exc)
            # Re-enqueue for retry if not exhausted
            if task.retry_count < task.max_retries:
                await asyncio.sleep(2 ** task.retry_count)
                await self._queue.put(task)
            return False

    async def _sync_to_es(self, task: SyncTask):
        if task.operation == "delete":
            await self._es.delete_doc(task.target_index, task.data_id)
        else:
            await self._es.index_doc(task.target_index, task.data, doc_id=task.data_id)
        # Mark MySQL product as synced
        if task.source_table == "products":
            await self._mysql.mark_products_synced([task.data_id])

    async def _sync_to_ch(self, task: SyncTask):
        await self._ch.insert_log(task.target_index, task.data)

    async def _sync_to_redis(self, task: SyncTask):
        if task.operation == "delete":
            await self._redis.delete(f"cache:{task.target_index}:{task.data_id}")
        else:
            await self._redis.set(
                f"cache:{task.target_index}:{task.data_id}",
                task.data, ttl=3600,
            )

    def _record(self, task: SyncTask, status: str, elapsed: float):
        if self._sync_ops:
            self._sync_ops.labels(source=task.source_type.value,
                                   target=task.target_type.value, status=status).inc()
        if self._sync_time:
            self._sync_time.observe(elapsed)


# ==================== StorageManager 编排器 ====================

class StorageManager:
    """统一存储编排层：一站式连接所有存储后端，提供聚合接口"""

    def __init__(
        self,
        mysql_cfg:  StorageConfig,
        redis_cfg:  StorageConfig,
        es_cfg:     StorageConfig,
        ch_cfg:     StorageConfig,
        minio_cfg:  StorageConfig,
    ):
        self.mysql = MySQLStorageService(mysql_cfg)
        self.redis = RedisStorageService(redis_cfg)
        self.es    = ElasticsearchStorageService(es_cfg)
        self.ch    = ClickHouseStorageService(ch_cfg)
        self.minio = MinIOStorageService(minio_cfg)
        self.sync  = DataSyncService(self.mysql, self.es, self.redis, self.ch, self.minio)

    async def startup(self):
        await asyncio.gather(
            self.mysql.connect(),
            self.redis.connect(),
            self.es.connect(),
            self.ch.connect(),
            self.minio.connect(),
            return_exceptions=True,
        )
        await self.sync.startup(workers=3)
        logger.info("StorageManager fully started")

    async def shutdown(self):
        await self.sync.shutdown()
        await asyncio.gather(
            self.mysql.disconnect(),
            self.redis.disconnect(),
            self.es.disconnect(),
            self.ch.disconnect(),
            return_exceptions=True,
        )
        logger.info("StorageManager shut down")

    # ── high-level business operations ────────────────────────────

    async def save_and_index_product(self, product: Dict) -> str:
        """Save to MySQL, then async-sync to ES."""
        pid = await self.mysql.upsert_product(product)
        # fast path: try immediate ES sync
        try:
            await self.es.index_doc("products", product, doc_id=pid)
            await self.mysql.mark_products_synced([pid])
        except Exception:
            pass   # Canal poller will retry
        return pid

    async def search_products_cached(
        self, query: str, filters: Optional[Dict] = None,
        page: int = 1, page_size: int = 20,
    ) -> Dict:
        cache_key = f"search:{hashlib.md5(f'{query}{filters}{page}{page_size}'.encode()).hexdigest()}"
        cached    = await self.redis.get(cache_key)
        if cached:
            return cached
        result = await self.es.search(
            "products", query_text=query, filters=filters,
            page=page, page_size=page_size,
        )
        await self.redis.set(cache_key, result, ttl=120)
        return result

    async def get_product_cached(self, product_id: str) -> Optional[Dict]:
        cache_key = f"product:{product_id}"
        cached    = await self.redis.get(cache_key)
        if cached:
            return cached
        product = await self.mysql.get_product(product_id)
        if product:
            await self.redis.set(cache_key, product, ttl=600)
        return product

    async def invalidate_product_cache(self, product_id: str):
        await self.redis.delete(f"product:{product_id}")
        await self.redis.delete(f"search:*")  # broad invalidation

    async def health_check(self) -> Dict[str, Any]:
        checks: Dict[str, str] = {}
        # MySQL
        try:
            await self.mysql.get_product("_health_probe_")
            checks["mysql"] = "ok"
        except Exception:
            checks["mysql"] = "ok (sqlite)"
        # Redis
        try:
            await self.redis.set("_hc_", "1", ttl=5)
            checks["redis"] = "ok" if not self.redis._use_mock else "mock"
        except Exception as e:
            checks["redis"] = f"error: {e}"
        # ES
        checks["elasticsearch"] = "ok" if not self.es._use_mock else "mock"
        # ClickHouse
        checks["clickhouse"] = "ok" if not self.ch._use_mock else "mock"
        # MinIO
        checks["minio"] = "ok" if not self.minio._use_mock else "mock"
        return {"status": "ok", "backends": checks, "ts": datetime.utcnow().isoformat()}


# ==================== FastAPI 应用工厂 ====================

# ── Pydantic models ───────────────────────────────────────────────

class ProductUpsertRequest(BaseModel):
    product_id:    str
    platform:      str
    title:         str
    price:         float
    description:   Optional[str]  = None
    category:      Optional[str]  = None
    brand:         Optional[str]  = None
    sales:         int            = 0
    rating:        float          = 0.0
    weighted_score: float         = 0.0
    image_urls:    List[str]      = Field(default_factory=list)

    @validator("price")
    def positive_price(cls, v):
        if v < 0:
            raise ValueError("price must be >= 0")
        return v


class SearchRequest(BaseModel):
    query:     str                      = ""
    filters:   Optional[Dict[str, Any]] = None
    page:      int                      = Field(1, ge=1)
    page_size: int                      = Field(20, ge=1, le=100)


class BehaviorLogRequest(BaseModel):
    user_id:    str
    session_id: str
    event_type: str
    event_name: str
    product_id: Optional[str] = None
    platform:   Optional[str] = None
    duration_ms: float        = 0.0
    event_data:  Optional[str] = None


class HealthResponse(BaseModel):
    status:   str
    service:  str
    version:  str
    backends: Dict[str, str]
    ts:       str


def _build_default_storage_configs() -> Dict[str, StorageConfig]:
    return {
        "mysql": StorageConfig(
            StorageType.MYSQL,
            host=os.getenv("MYSQL_HOST", "127.0.0.1"),
            port=int(os.getenv("MYSQL_PORT", "3306")),
            database=os.getenv("MYSQL_DB", "ilbuy"),
            username=os.getenv("MYSQL_USER", "root"),
            password=os.getenv("MYSQL_PASSWORD", ""),
        ),
        "redis": StorageConfig(
            StorageType.REDIS,
            host=os.getenv("REDIS_HOST", "127.0.0.1"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            database=os.getenv("REDIS_DB", "0"),
        ),
        "es": StorageConfig(
            StorageType.ELASTICSEARCH,
            host=os.getenv("ES_HOST", "127.0.0.1"),
            port=int(os.getenv("ES_PORT", "9200")),
            username=os.getenv("ES_USER", ""),
            password=os.getenv("ES_PASSWORD", ""),
        ),
        "ch": StorageConfig(
            StorageType.CLICKHOUSE,
            host=os.getenv("CH_HOST", "127.0.0.1"),
            port=int(os.getenv("CH_PORT", "9000")),
            database=os.getenv("CH_DB", "default"),
            username=os.getenv("CH_USER", "default"),
            password=os.getenv("CH_PASSWORD", ""),
        ),
        "minio": StorageConfig(
            StorageType.MINIO,
            host=os.getenv("MINIO_HOST", "127.0.0.1"),
            port=int(os.getenv("MINIO_PORT", "9000")),
            username=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
            password=os.getenv("MINIO_SECRET_KEY", "minioadmin"),
        ),
    }


def create_storage_app() -> FastAPI:
    app = FastAPI(
        title="数据存储层",
        description="ILbuy 数据存储层 — MySQL/Redis/ES/ClickHouse/MinIO 统一接口",
        version="1.0.0",
    )

    _state: Dict[str, Any] = {}

    @app.on_event("startup")
    async def _startup():
        cfgs = _build_default_storage_configs()
        mgr  = StorageManager(
            mysql_cfg=cfgs["mysql"], redis_cfg=cfgs["redis"],
            es_cfg=cfgs["es"], ch_cfg=cfgs["ch"], minio_cfg=cfgs["minio"],
        )
        await mgr.startup()
        _state["mgr"] = mgr
        logger.info("数据存储层 startup complete")

    @app.on_event("shutdown")
    async def _shutdown():
        mgr = _state.get("mgr")
        if mgr:
            await mgr.shutdown()

    def _mgr() -> StorageManager:
        m = _state.get("mgr")
        if not m:
            raise HTTPException(503, "Service initializing")
        return m

    # ── health ────────────────────────────────────────────────────

    @app.get("/health", response_model=HealthResponse, tags=["system"])
    async def health(mgr: StorageManager = Depends(_mgr)):
        hc = await mgr.health_check()
        return HealthResponse(status=hc["status"], service="data-storage-layer",
                               version="1.0.0", backends=hc["backends"], ts=hc["ts"])

    @app.get("/metrics", tags=["system"])
    async def metrics():
        if not _HAS_PROMETHEUS:
            raise HTTPException(501, "Prometheus not available")
        from fastapi.responses import Response as _R
        from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
        return _R(content=generate_latest(_SL_REGISTRY), media_type=CONTENT_TYPE_LATEST)

    # ── product ───────────────────────────────────────────────────

    @app.post("/api/v1/products", tags=["product"])
    async def upsert_product(req: ProductUpsertRequest, mgr: StorageManager = Depends(_mgr)):
        pid = await mgr.save_and_index_product(req.dict())
        return {"product_id": pid, "status": "saved"}

    @app.get("/api/v1/products/{product_id}", tags=["product"])
    async def get_product(product_id: str, mgr: StorageManager = Depends(_mgr)):
        p = await mgr.get_product_cached(product_id)
        if not p:
            raise HTTPException(404, f"Product {product_id!r} not found")
        return p

    @app.post("/api/v1/products/search", tags=["product"])
    async def search_products(req: SearchRequest, mgr: StorageManager = Depends(_mgr)):
        return await mgr.search_products_cached(
            req.query, filters=req.filters, page=req.page, page_size=req.page_size
        )

    @app.post("/api/v1/products/bulk", tags=["product"])
    async def bulk_upsert(products: List[Dict[str, Any]], mgr: StorageManager = Depends(_mgr),
                          bg: BackgroundTasks = BackgroundTasks()):
        # save to MySQL synchronously, ES in background
        ok = await mgr.mysql.bulk_upsert_products(products)
        bg.add_task(mgr.sync.sync_products_batch, products)
        return {"saved": ok, "total": len(products)}

    # ── user ──────────────────────────────────────────────────────

    @app.post("/api/v1/users", tags=["user"])
    async def save_user(data: Dict[str, Any], mgr: StorageManager = Depends(_mgr)):
        uid = await mgr.mysql.save_user_profile(data)
        await mgr.redis.set(f"user:{uid}", data, ttl=3600)
        return {"user_id": uid}

    @app.get("/api/v1/users/{user_id}", tags=["user"])
    async def get_user(user_id: str, mgr: StorageManager = Depends(_mgr)):
        cached = await mgr.redis.get(f"user:{user_id}")
        if cached:
            return cached
        u = await mgr.mysql.get_user_profile(user_id)
        if not u:
            raise HTTPException(404, f"User {user_id!r} not found")
        await mgr.redis.set(f"user:{user_id}", u, ttl=3600)
        return u

    # ── dialog session ────────────────────────────────────────────

    @app.post("/api/v1/sessions", tags=["session"])
    async def save_session(data: Dict[str, Any], mgr: StorageManager = Depends(_mgr)):
        sid = await mgr.mysql.save_dialog_session(data)
        await mgr.redis.set_session(sid, data)
        return {"session_id": sid}

    @app.get("/api/v1/sessions/{session_id}", tags=["session"])
    async def get_session(session_id: str, mgr: StorageManager = Depends(_mgr)):
        cached = await mgr.redis.get_session(session_id)
        if cached:
            return cached
        sess = await mgr.mysql.get_dialog_session(session_id)
        if not sess:
            raise HTTPException(404, f"Session {session_id!r} not found")
        await mgr.redis.set_session(session_id, sess)
        return sess

    # ── analytics ─────────────────────────────────────────────────

    @app.post("/api/v1/analytics/behavior", tags=["analytics"])
    async def log_behavior(req: BehaviorLogRequest, mgr: StorageManager = Depends(_mgr)):
        ok = await mgr.sync.emit_behavior_log(req.dict())
        return {"logged": ok}

    @app.get("/api/v1/analytics/behavior/{user_id}", tags=["analytics"])
    async def get_behavior_stats(user_id: str, days: int = Query(7, ge=1, le=90),
                                 mgr: StorageManager = Depends(_mgr)):
        since = datetime.now() - timedelta(days=days)
        return await mgr.ch.get_user_behavior_stats(user_id=user_id, start_date=since)

    @app.get("/api/v1/analytics/products/{product_id}", tags=["analytics"])
    async def get_product_analytics(product_id: str, days: int = Query(7, ge=1, le=90),
                                    mgr: StorageManager = Depends(_mgr)):
        return await mgr.ch.get_product_analytics(product_id=product_id, days=days)

    # ── reports ───────────────────────────────────────────────────

    @app.post("/api/v1/reports", tags=["report"])
    async def save_report(data: Dict[str, Any], mgr: StorageManager = Depends(_mgr)):
        fmt     = data.get("format", "json")
        rid     = data.get("report_id", str(uuid.uuid4()))
        uid     = data.get("user_id", "anonymous")
        file_url = await mgr.minio.save_report(data, rid, uid, fmt=fmt)
        data["file_path"] = file_url
        data.setdefault("report_id", rid)
        db_rid = await mgr.mysql.save_report(data)
        return {"report_id": db_rid, "file_url": file_url}

    @app.get("/api/v1/reports/{report_id}", tags=["report"])
    async def get_report(report_id: str, mgr: StorageManager = Depends(_mgr)):
        r = await mgr.mysql.get_report(report_id)
        if not r:
            raise HTTPException(404, f"Report {report_id!r} not found")
        return r

    # ── sync control ──────────────────────────────────────────────

    @app.post("/api/v1/sync/flush", tags=["sync"])
    async def flush_sync(mgr: StorageManager = Depends(_mgr)):
        return await mgr.sync.flush_pending()

    @app.post("/api/v1/sync/product/{product_id}", tags=["sync"])
    async def force_sync_product(product_id: str, mgr: StorageManager = Depends(_mgr)):
        p = await mgr.mysql.get_product(product_id)
        if not p:
            raise HTTPException(404, f"Product {product_id!r} not found")
        ok = await mgr.sync.sync_product_to_es(p)
        if ok:
            await mgr.mysql.mark_products_synced([product_id])
        return {"product_id": product_id, "synced": ok}

    return app


# ==================== 主入口 ====================

app = create_storage_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "data_storage_layer:app",
        host=os.getenv("SL_HOST", "0.0.0.0"),
        port=int(os.getenv("SL_PORT", "8005")),
        reload=os.getenv("SL_RELOAD", "false").lower() == "true",
        log_level=os.getenv("SL_LOG_LEVEL", "info"),
        workers=int(os.getenv("SL_WORKERS", "1")),
    )
