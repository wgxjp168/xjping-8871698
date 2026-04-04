"""
data_collection_processing.py
数据采集与处理层
包含：7大平台API调用、数据采集服务、数据处理管道、合规监控
"""

import asyncio
import json
import os
import time
import uuid
import hashlib
import random
import logging
import re
import copy
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod

# ── 可选重型依赖 ────────────────────────────────────────────────
try:
    import numpy as np
    _HAS_NUMPY = True
except ImportError:
    _HAS_NUMPY = False

try:
    import pandas as pd
    _HAS_PANDAS = True
except ImportError:
    _HAS_PANDAS = False

try:
    from bs4 import BeautifulSoup
    _HAS_BS4 = True
except ImportError:
    _HAS_BS4 = False

try:
    from tenacity import (retry as _tenacity_retry, stop_after_attempt,
                          wait_exponential, retry_if_exception_type)
    _HAS_TENACITY = True
except ImportError:
    _HAS_TENACITY = False

try:
    import yaml as _yaml
    _HAS_YAML = True
except ImportError:
    _HAS_YAML = False

try:
    from prometheus_client import (Counter as _PCounter, Histogram as _PHisto,
                                   Gauge as _PGauge, generate_latest,
                                   CONTENT_TYPE_LATEST, CollectorRegistry)
    _DC_REGISTRY = CollectorRegistry()   # per-service registry avoids name conflicts
    _HAS_PROMETHEUS = True
except ImportError:
    _HAS_PROMETHEUS = False
    _DC_REGISTRY = None  # type: ignore

import aiohttp
import redis.asyncio as aioredis

from sqlalchemy import Column, String, Integer, Float, Boolean, JSON, DateTime, Text, select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from pydantic import BaseModel, Field, validator
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Query
from fastapi.responses import JSONResponse

# ── helpers ──────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
)
logger = logging.getLogger(__name__)


def _make_counter(name: str, doc: str, labels=None):
    if not _HAS_PROMETHEUS:
        return None
    try:
        if labels:
            return _PCounter(name, doc, labels, registry=_DC_REGISTRY)
        return _PCounter(name, doc, registry=_DC_REGISTRY)
    except Exception:
        return None


def _make_histogram(name: str, doc: str, labels=None):
    if not _HAS_PROMETHEUS:
        return None
    try:
        if labels:
            return _PHisto(name, doc, labels, registry=_DC_REGISTRY)
        return _PHisto(name, doc, registry=_DC_REGISTRY)
    except Exception:
        return None


def _make_gauge(name: str, doc: str, labels=None):
    if not _HAS_PROMETHEUS:
        return None
    try:
        if labels:
            return _PGauge(name, doc, labels, registry=_DC_REGISTRY)
        return _PGauge(name, doc, registry=_DC_REGISTRY)
    except Exception:
        return None


# ==================== 枚举类型 ====================

class PlatformType(Enum):
    TAOBAO    = "taobao"
    TMALL     = "tmall"
    JD        = "jd"
    PINDUODUO = "pinduoduo"
    DOUYIN    = "douyin"
    VIP       = "vip"
    ALIBABA   = "alibaba"
    SUNING    = "suning"


class DataSourceType(Enum):
    API     = "api"
    WEB     = "web"
    MOBILE  = "mobile"
    PARTNER = "partner"


class DataStatus(Enum):
    RAW          = "raw"
    CLEANED      = "cleaned"
    STANDARDIZED = "standardized"
    SCORED       = "scored"
    VALIDATED    = "validated"
    FAILED       = "failed"


class ComplianceLevel(Enum):
    FULL      = "full"
    LIMITED   = "limited"
    RISKY     = "risky"
    VIOLATION = "violation"


# ==================== 数据类 ====================

@dataclass
class APIConfig:
    platform: PlatformType
    base_url: str
    api_version: str
    endpoints: Dict[str, str]
    rate_limit_per_minute: int
    rate_limit_per_day: int
    auth_type: str          # oauth2 | api_key | bearer_token
    auth_params: Dict[str, Any]
    timeout_seconds: int
    retry_attempts: int
    proxy_required: bool
    data_format: str        # json | xml

    def get_endpoint(self, endpoint_name: str, **params) -> str:
        tmpl = self.endpoints.get(endpoint_name)
        if not tmpl:
            raise ValueError(f"Endpoint '{endpoint_name}' not defined for {self.platform}")
        return f"{self.base_url}/{self.api_version}/{tmpl.format(**params)}"


@dataclass
class ProxyInfo:
    proxy_id: str
    host: str
    port: int
    username: Optional[str]   = None
    password: Optional[str]   = None
    protocol: str             = "http"
    location: Optional[str]   = None
    speed: float              = 0.0      # ms
    success_rate: float       = 1.0
    last_used: datetime       = field(default_factory=datetime.now)
    fail_count: int           = 0
    is_active: bool           = True

    def get_url(self) -> str:
        if self.username and self.password:
            return f"{self.protocol}://{self.username}:{self.password}@{self.host}:{self.port}"
        return f"{self.protocol}://{self.host}:{self.port}"

    def mark_success(self, response_time_ms: float):
        self.speed = (self.speed + response_time_ms) / 2
        self.success_rate = min(1.0, self.success_rate + 0.01)
        self.last_used = datetime.now()
        self.fail_count = 0

    def mark_failure(self):
        self.fail_count += 1
        self.success_rate = max(0.0, self.success_rate - 0.05)
        if self.fail_count > 10:
            self.is_active = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "proxy_id":     self.proxy_id,
            "host":         self.host,
            "port":         self.port,
            "protocol":     self.protocol,
            "location":     self.location,
            "speed":        round(self.speed, 2),
            "success_rate": round(self.success_rate, 2),
            "fail_count":   self.fail_count,
            "is_active":    self.is_active,
        }


@dataclass
class RawData:
    data_id: str
    platform: PlatformType
    source_type: DataSourceType
    raw_content: Any
    metadata: Dict[str, Any]
    status: DataStatus = DataStatus.RAW
    created_at: datetime = field(default_factory=datetime.now)
    processed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "data_id":      self.data_id,
            "platform":     self.platform.value,
            "source_type":  self.source_type.value,
            "status":       self.status.value,
            "metadata":     self.metadata,
            "created_at":   self.created_at.isoformat(),
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
        }


@dataclass
class CleanedData:
    data_id: str
    original_data_id: str
    platform: PlatformType
    cleaned_content: Dict[str, Any]
    cleaning_log: List[str]
    quality_score: float
    missing_fields: List[str]
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "data_id":          self.data_id,
            "original_data_id": self.original_data_id,
            "platform":         self.platform.value,
            "cleaned_content":  self.cleaned_content,
            "cleaning_log":     self.cleaning_log,
            "quality_score":    round(self.quality_score, 2),
            "missing_fields":   self.missing_fields,
            "created_at":       self.created_at.isoformat(),
        }


@dataclass
class StandardizedData:
    data_id: str
    cleaned_data_id: str
    platform: PlatformType
    standardized_product: Dict[str, Any]
    mapping_log: Dict[str, Any]
    standard_compliance: float
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "data_id":             self.data_id,
            "cleaned_data_id":     self.cleaned_data_id,
            "platform":            self.platform.value,
            "standardized_product": self.standardized_product,
            "mapping_log":         self.mapping_log,
            "standard_compliance": round(self.standard_compliance, 2),
            "created_at":          self.created_at.isoformat(),
        }


@dataclass
class ScoredData:
    data_id: str
    standardized_data_id: str
    platform: PlatformType
    product_scores: Dict[str, float]
    weighted_score: float
    score_breakdown: Dict[str, Any]
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "data_id":              self.data_id,
            "standardized_data_id": self.standardized_data_id,
            "platform":             self.platform.value,
            "product_scores":       {k: round(v, 2) for k, v in self.product_scores.items()},
            "weighted_score":       round(self.weighted_score, 2),
            "score_breakdown":      self.score_breakdown,
            "created_at":           self.created_at.isoformat(),
        }


@dataclass
class CollectionTask:
    task_id: str
    request_id: str
    platform: PlatformType
    query_params: Dict[str, Any]
    priority: int           # 1-10
    max_results: int
    source_type: DataSourceType
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: str = "pending"
    result_count: int = 0
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id":       self.task_id,
            "request_id":    self.request_id,
            "platform":      self.platform.value,
            "priority":      self.priority,
            "max_results":   self.max_results,
            "source_type":   self.source_type.value,
            "status":        self.status,
            "result_count":  self.result_count,
            "created_at":    self.created_at.isoformat(),
            "started_at":    self.started_at.isoformat() if self.started_at else None,
            "completed_at":  self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message,
        }


# ==================== 数据库模型 ====================

Base = declarative_base()


class APIConfigModel(Base):
    __tablename__ = "api_configs"
    id          = Column(Integer, primary_key=True, autoincrement=True)
    platform    = Column(String(32), index=True)
    config_name = Column(String(64))
    config_data = Column(JSON)
    is_active   = Column(Boolean, default=True)
    created_at  = Column(DateTime, default=datetime.now)
    updated_at  = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class ProxyPoolModel(Base):
    __tablename__ = "proxy_pool"
    proxy_id     = Column(String(64), primary_key=True)
    host         = Column(String(128))
    port         = Column(Integer)
    username     = Column(String(128), nullable=True)
    password     = Column(String(128), nullable=True)
    protocol     = Column(String(16), default="http")
    location     = Column(String(64), nullable=True)
    speed        = Column(Float, default=0.0)
    success_rate = Column(Float, default=1.0)
    fail_count   = Column(Integer, default=0)
    is_active    = Column(Boolean, default=True)
    last_used    = Column(DateTime, default=datetime.now)
    created_at   = Column(DateTime, default=datetime.now)
    updated_at   = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class CollectionTaskModel(Base):
    __tablename__  = "collection_tasks"
    task_id        = Column(String(64), primary_key=True)
    request_id     = Column(String(64), index=True)
    platform       = Column(String(32))
    query_params   = Column(JSON)
    priority       = Column(Integer, default=5)
    max_results    = Column(Integer, default=100)
    source_type    = Column(String(32))
    status         = Column(String(32), default="pending")
    result_count   = Column(Integer, default=0)
    error_message  = Column(Text, nullable=True)
    created_at     = Column(DateTime, default=datetime.now)
    started_at     = Column(DateTime, nullable=True)
    completed_at   = Column(DateTime, nullable=True)


class RawDataModel(Base):
    __tablename__  = "raw_data"
    data_id        = Column(String(64), primary_key=True)
    task_id        = Column(String(64), index=True)
    platform       = Column(String(32))
    source_type    = Column(String(32))
    raw_content    = Column(JSON)
    extra_metadata = Column(JSON)
    status         = Column(String(32), default="raw")
    created_at     = Column(DateTime, default=datetime.now)
    processed_at   = Column(DateTime, nullable=True)


class ProcessingPipelineModel(Base):
    __tablename__ = "processing_pipeline"
    id            = Column(Integer, primary_key=True, autoincrement=True)
    data_id       = Column(String(64), index=True)
    stage         = Column(String(32))   # cleaning | standardization | scoring
    input_data    = Column(JSON, nullable=True)
    output_data   = Column(JSON, nullable=True)
    status        = Column(String(32), default="pending")
    metrics       = Column(JSON, nullable=True)
    created_at    = Column(DateTime, default=datetime.now)
    completed_at  = Column(DateTime, nullable=True)


class ComplianceLogModel(Base):
    __tablename__   = "compliance_logs"
    id              = Column(Integer, primary_key=True, autoincrement=True)
    data_id         = Column(String(64), index=True)
    platform        = Column(String(32))
    compliance_level = Column(String(32))
    issues          = Column(JSON, nullable=True)
    action_taken    = Column(String(64), nullable=True)
    checked_at      = Column(DateTime, default=datetime.now)


# ==================== 速率限制器 ====================

class RateLimiter:
    """滑动窗口速率限制器（线程安全）"""

    def __init__(self, requests_per_minute: int, requests_per_day: int = 0):
        self._rpm      = max(1, requests_per_minute)
        self._rpd      = requests_per_day
        self._window   = 60.0               # 秒
        self._day_window = 86400.0
        self._calls: List[float] = []       # 分钟级窗口时间戳
        self._day_calls: List[float] = []   # 日级窗口时间戳
        self._lock     = asyncio.Lock()

    async def wait(self) -> None:
        """等待直到可以发送下一个请求"""
        async with self._lock:
            now = time.time()

            # 清理过期时间戳
            self._calls = [t for t in self._calls if now - t < self._window]
            self._day_calls = [t for t in self._day_calls if now - t < self._day_window]

            # 检查每分钟限制
            if len(self._calls) >= self._rpm:
                oldest = self._calls[0]
                wait_time = self._window - (now - oldest)
                if wait_time > 0:
                    await asyncio.sleep(wait_time)
                now = time.time()
                self._calls = [t for t in self._calls if now - t < self._window]

            # 检查每日限制
            if self._rpd and len(self._day_calls) >= self._rpd:
                oldest_day = self._day_calls[0]
                wait_time = self._day_window - (now - oldest_day)
                if wait_time > 0:
                    logger.warning("Daily rate limit reached, waiting %.0fs", wait_time)
                    await asyncio.sleep(min(wait_time, 10))  # 最长等10秒，上层应处理

            now = time.time()
            self._calls.append(now)
            self._day_calls.append(now)

    @property
    def current_rpm(self) -> int:
        now = time.time()
        return sum(1 for t in self._calls if now - t < self._window)


# ==================== 平台API适配器 ====================

class PlatformAPIAdapter(ABC):
    """平台API适配器基类"""

    def __init__(self, config: APIConfig, proxy_manager: "ProxyManager"):
        self.config        = config
        self.proxy_manager = proxy_manager
        self.rate_limiter  = RateLimiter(
            config.rate_limit_per_minute,
            config.rate_limit_per_day,
        )

    # ── abstract interface ──────────────────────────────────────

    @abstractmethod
    async def search_products(self, query_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """搜索商品"""

    @abstractmethod
    async def get_product_details(self, product_id: str) -> Dict[str, Any]:
        """获取商品详情"""

    @abstractmethod
    async def get_product_reviews(self, product_id: str, page: int = 1) -> List[Dict[str, Any]]:
        """获取商品评价"""

    @abstractmethod
    def parse_response(self, response_data: Any) -> List[Dict[str, Any]]:
        """解析响应数据"""

    # ── shared HTTP helper ──────────────────────────────────────

    async def _make_request(
        self,
        endpoint_name: str,
        method: str = "GET",
        url_params: Optional[Dict[str, Any]] = None,
        query_params: Optional[Dict[str, Any]] = None,
        body: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """发送 HTTP 请求（含速率限制 + 代理 + 重试）"""
        await self.rate_limiter.wait()
        proxy = await self.proxy_manager.get_proxy(self.config.platform)
        url   = self.config.get_endpoint(endpoint_name, **(url_params or {}))
        headers = self._build_headers()

        last_exc: Optional[Exception] = None
        for attempt in range(max(1, self.config.retry_attempts)):
            try:
                t0 = time.time()
                async with aiohttp.ClientSession() as sess:
                    async with sess.request(
                        method=method,
                        url=url,
                        params=query_params,
                        json=body,
                        headers=headers,
                        proxy=proxy.get_url() if proxy else None,
                        timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds),
                    ) as resp:
                        elapsed_ms = (time.time() - t0) * 1000
                        if resp.status == 200:
                            data = await resp.json(content_type=None)
                            if proxy:
                                proxy.mark_success(elapsed_ms)
                            return data
                        body_text = await resp.text()
                        raise aiohttp.ClientResponseError(
                            resp.request_info, resp.history,
                            status=resp.status, message=body_text,
                        )
            except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
                last_exc = exc
                if proxy:
                    proxy.mark_failure()
                wait = 2 ** attempt
                logger.warning("Request attempt %d/%d failed (%s), retrying in %ds",
                               attempt + 1, self.config.retry_attempts, exc, wait)
                if attempt + 1 < self.config.retry_attempts:
                    await asyncio.sleep(wait)

        raise last_exc or RuntimeError("All retry attempts exhausted")

    def _build_headers(self) -> Dict[str, str]:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
            ),
            "Accept":       "application/json",
            "Content-Type": "application/json",
        }
        if self.config.auth_type == "api_key":
            headers["API-Key"] = self.config.auth_params.get("api_key", "")
        elif self.config.auth_type == "bearer_token":
            headers["Authorization"] = f"Bearer {self.config.auth_params.get('token', '')}"
        elif self.config.auth_type == "oauth2":
            token = self.config.auth_params.get("access_token", "")
            if token:
                headers["Authorization"] = f"Bearer {token}"
        return headers


# ── Concrete adapters ──────────────────────────────────────────────────────────

class TaobaoAPIAdapter(PlatformAPIAdapter):

    async def search_products(self, query_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        params = {
            "q":         query_params.get("keyword", ""),
            "cat":       query_params.get("category_id", ""),
            "sale":      query_params.get("sort_by", "default"),
            "page_no":   query_params.get("page", 1),
            "page_size": min(query_params.get("page_size", 100), 100),
        }
        resp = await self._make_request("search", query_params=params)
        return self.parse_response(resp)

    async def get_product_details(self, product_id: str) -> Dict[str, Any]:
        resp = await self._make_request("item_get", query_params={"num_iid": product_id})
        return resp.get("item", {})

    async def get_product_reviews(self, product_id: str, page: int = 1) -> List[Dict[str, Any]]:
        resp = await self._make_request(
            "item_review", query_params={"num_iid": product_id, "page_no": page, "page_size": 20}
        )
        return resp.get("reviews", [])

    def parse_response(self, response_data: Any) -> List[Dict[str, Any]]:
        items = response_data.get("items", {}).get("item", [])
        return [{
            "product_id":     item.get("num_iid"),
            "title":          item.get("title"),
            "price":          float(item.get("price", 0)),
            "original_price": float(item.get("original_price", 0)),
            "sales":          int(item.get("sales", 0)),
            "shop_name":      item.get("nick"),
            "image_url":      item.get("pic_url"),
            "detail_url":     item.get("detail_url"),
            "location":       item.get("location"),
            "platform":       "taobao",
        } for item in items]


class TmallAPIAdapter(TaobaoAPIAdapter):
    def parse_response(self, response_data: Any) -> List[Dict[str, Any]]:
        items = super().parse_response(response_data)
        for item in items:
            item["is_tmall"]        = True
            item["tmall_guarantee"] = True
            item["platform"]        = "tmall"
        return items


class JDAPIAdapter(PlatformAPIAdapter):

    async def search_products(self, query_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        params = {
            "keyword":  query_params.get("keyword", ""),
            "cid1":     query_params.get("category_id", ""),
            "sort":     query_params.get("sort_by", ""),
            "page":     query_params.get("page", 1),
            "pageSize": min(query_params.get("page_size", 100), 100),
        }
        resp = await self._make_request("search", query_params=params)
        return self.parse_response(resp)

    async def get_product_details(self, product_id: str) -> Dict[str, Any]:
        resp = await self._make_request("sku_detail", query_params={"sku": product_id})
        return resp.get("data", {})

    async def get_product_reviews(self, product_id: str, page: int = 1) -> List[Dict[str, Any]]:
        resp = await self._make_request(
            "review_list", query_params={"sku": product_id, "page": page, "pageSize": 20}
        )
        return resp.get("comments", [])

    def parse_response(self, response_data: Any) -> List[Dict[str, Any]]:
        items = response_data.get("data", {}).get("products", [])
        return [{
            "product_id":       item.get("skuId"),
            "title":            item.get("name"),
            "price":            float((item.get("price") or {}).get("p", 0)),
            "original_price":   float((item.get("price") or {}).get("op", 0)),
            "sales":            int(item.get("sales", 0)),
            "brand":            item.get("brand"),
            "shop_id":          item.get("shopId"),
            "shop_name":        item.get("shopName"),
            "image_url":        item.get("imageUrl"),
            "is_self_operated": item.get("isSelfOperated", False),
            "platform":         "jd",
        } for item in items]


class PinduoduoAPIAdapter(PlatformAPIAdapter):

    async def search_products(self, query_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        params = {
            "keyword":   query_params.get("keyword", ""),
            "opt_id":    query_params.get("category_id", ""),
            "sort_type": query_params.get("sort_by", 0),
            "page":      query_params.get("page", 1),
            "page_size": min(query_params.get("page_size", 100), 100),
        }
        resp = await self._make_request("search", query_params=params)
        return self.parse_response(resp)

    async def get_product_details(self, product_id: str) -> Dict[str, Any]:
        resp = await self._make_request("goods_detail", query_params={"goods_id": product_id})
        return resp.get("goods_detail", {})

    async def get_product_reviews(self, product_id: str, page: int = 1) -> List[Dict[str, Any]]:
        resp = await self._make_request(
            "goods_review", query_params={"goods_id": product_id, "page": page, "page_size": 20}
        )
        return resp.get("review_list", [])

    def parse_response(self, response_data: Any) -> List[Dict[str, Any]]:
        items = response_data.get("goods_list", [])
        return [{
            "product_id":      item.get("goods_id"),
            "title":           item.get("goods_name"),
            "price":           float(item.get("min_group_price", 0)) / 100,
            "original_price":  float(item.get("market_price", 0)) / 100,
            "sales":           int(item.get("sales", 0)),
            "has_coupon":      item.get("has_coupon", False),
            "coupon_discount": float(item.get("coupon_discount", 0)) / 100,
            "shop_id":         item.get("mall_id"),
            "shop_name":       item.get("mall_name"),
            "image_url":       item.get("goods_image_url"),
            "platform":        "pinduoduo",
        } for item in items]


class DouyinAPIAdapter(PlatformAPIAdapter):

    async def search_products(self, query_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        params = {
            "keyword":   query_params.get("keyword", ""),
            "category":  query_params.get("category", ""),
            "sort":      query_params.get("sort_by", "default"),
            "page":      query_params.get("page", 1),
            "page_size": min(query_params.get("page_size", 100), 100),
        }
        resp = await self._make_request("search", query_params=params)
        return self.parse_response(resp)

    async def get_product_details(self, product_id: str) -> Dict[str, Any]:
        resp = await self._make_request("product_detail", query_params={"product_id": product_id})
        return resp.get("product", {})

    async def get_product_reviews(self, product_id: str, page: int = 1) -> List[Dict[str, Any]]:
        resp = await self._make_request(
            "product_review", query_params={"product_id": product_id, "page": page, "page_size": 20}
        )
        return resp.get("reviews", [])

    def parse_response(self, response_data: Any) -> List[Dict[str, Any]]:
        items = (response_data.get("data") or {}).get("products", [])
        return [{
            "product_id":      item.get("product_id"),
            "title":           item.get("title"),
            "price":           float(item.get("price", 0)),
            "original_price":  float(item.get("original_price", 0)),
            "sales":           int(item.get("sales", 0)),
            "author_id":       item.get("author_id"),
            "author_name":     item.get("author_name"),
            "video_id":        item.get("video_id"),
            "image_url":       item.get("cover"),
            "is_live_product": item.get("is_live_product", False),
            "platform":        "douyin",
        } for item in items]


class VIPAPIAdapter(PlatformAPIAdapter):
    """唯品会 API 适配器"""

    async def search_products(self, query_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        params = {
            "keyword":    query_params.get("keyword", ""),
            "cateId":     query_params.get("category_id", ""),
            "sortType":   query_params.get("sort_by", ""),
            "pageIndex":  query_params.get("page", 1),
            "pageSize":   min(query_params.get("page_size", 100), 100),
        }
        resp = await self._make_request("search", query_params=params)
        return self.parse_response(resp)

    async def get_product_details(self, product_id: str) -> Dict[str, Any]:
        resp = await self._make_request("product_detail", query_params={"productId": product_id})
        return resp.get("product", {})

    async def get_product_reviews(self, product_id: str, page: int = 1) -> List[Dict[str, Any]]:
        resp = await self._make_request(
            "review_list", query_params={"productId": product_id, "pageIndex": page}
        )
        return resp.get("reviewList", [])

    def parse_response(self, response_data: Any) -> List[Dict[str, Any]]:
        items = (response_data.get("data") or {}).get("productList", [])
        return [{
            "product_id":    item.get("productId"),
            "title":         item.get("productName"),
            "price":         float(item.get("salePrice", 0)),
            "original_price": float(item.get("marketPrice", 0)),
            "sales":         int(item.get("salesVolume", 0)),
            "brand":         item.get("brand"),
            "image_url":     item.get("mainImageUrl"),
            "platform":      "vip",
        } for item in items]


class AlibabaAPIAdapter(PlatformAPIAdapter):
    """阿里巴巴 1688 API 适配器（B2B）"""

    async def search_products(self, query_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        params = {
            "keywords":       query_params.get("keyword", ""),
            "categoryId":     query_params.get("category_id", ""),
            "pageIndex":      query_params.get("page", 1),
            "pageSize":       min(query_params.get("page_size", 100), 100),
            "beginPrice":     query_params.get("min_price", ""),
            "endPrice":       query_params.get("max_price", ""),
        }
        resp = await self._make_request("search", query_params=params)
        return self.parse_response(resp)

    async def get_product_details(self, product_id: str) -> Dict[str, Any]:
        resp = await self._make_request("item_get", query_params={"offerId": product_id})
        return resp.get("result", {})

    async def get_product_reviews(self, product_id: str, page: int = 1) -> List[Dict[str, Any]]:
        # 1688 评价通过供应商API获取
        return []

    def parse_response(self, response_data: Any) -> List[Dict[str, Any]]:
        items = (response_data.get("result") or {}).get("offerList", [])
        return [{
            "product_id":   item.get("offerId"),
            "title":        item.get("subjectTrans") or item.get("subject"),
            "price":        float(item.get("priceInfo", {}).get("price", 0)),
            "original_price": float(item.get("priceInfo", {}).get("originalPrice", 0)),
            "moq":          int(item.get("priceInfo", {}).get("startQuantity", 1)),
            "sales":        int(item.get("tradeCount", 0)),
            "shop_id":      item.get("memberId"),
            "shop_name":    item.get("companyName"),
            "is_verified":  item.get("supplierFlag", {}).get("is_verified", False),
            "image_url":    item.get("imageUrl"),
            "platform":     "alibaba",
        } for item in items]


class SuningAPIAdapter(PlatformAPIAdapter):
    """苏宁易购 API 适配器"""

    async def search_products(self, query_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        params = {
            "keywords": query_params.get("keyword", ""),
            "cateid":   query_params.get("category_id", ""),
            "pager":    query_params.get("page", 1),
            "pageSize": min(query_params.get("page_size", 100), 100),
        }
        resp = await self._make_request("search", query_params=params)
        return self.parse_response(resp)

    async def get_product_details(self, product_id: str) -> Dict[str, Any]:
        resp = await self._make_request("product_detail", query_params={"commodityCode": product_id})
        return resp.get("commodity", {})

    async def get_product_reviews(self, product_id: str, page: int = 1) -> List[Dict[str, Any]]:
        resp = await self._make_request(
            "review_list", query_params={"commodityCode": product_id, "page": page}
        )
        return resp.get("commentList", [])

    def parse_response(self, response_data: Any) -> List[Dict[str, Any]]:
        items = (response_data.get("data") or {}).get("commodityList", [])
        return [{
            "product_id":    item.get("commodityCode"),
            "title":         item.get("commodityName"),
            "price":         float(item.get("price", {}).get("salePrice", 0)),
            "original_price": float(item.get("price", {}).get("marketPrice", 0)),
            "sales":         int(item.get("saleCount", 0)),
            "brand":         item.get("brandName"),
            "shop_id":       item.get("shopCode"),
            "shop_name":     item.get("shopName"),
            "image_url":     item.get("commodityImg"),
            "is_self":       item.get("isSelfStore", False),
            "platform":      "suning",
        } for item in items]


# ==================== 代理IP管理器 ====================

class ProxyManager:
    """代理IP管理器（内存缓存 + SQLite 持久化）"""

    _PROXY_SOURCES = [
        "https://www.proxy-list.download/api/v1/get?type=http",
    ]

    def __init__(
        self,
        db_url: str = "sqlite+aiosqlite:///./proxy.db",
        min_proxies_per_platform: int = 5,
    ):
        self.db_url   = db_url
        self.min_proxies = min_proxies_per_platform
        self._engine  = create_async_engine(db_url, echo=False)
        self._session_factory = sessionmaker(
            self._engine, class_=AsyncSession, expire_on_commit=False
        )
        self._cache: Dict[str, List[ProxyInfo]] = {}
        self._lock = asyncio.Lock()

    async def startup(self):
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        # seed with local dev proxies so tests work without a real proxy source
        await self._seed_local_proxies()

    async def get_proxy(self, platform: PlatformType) -> Optional[ProxyInfo]:
        pk = platform.value
        async with self._lock:
            proxies = [p for p in self._cache.get(pk, []) if p.is_active]
        if not proxies:
            # fall back to DB
            proxies = await self._load_from_db()
            async with self._lock:
                self._cache[pk] = proxies
            proxies = [p for p in proxies if p.is_active]
        if not proxies:
            return None
        # weighted random selection: higher success_rate + faster speed wins
        weights = [p.success_rate * (1.0 / max(p.speed, 0.1)) for p in proxies]
        total = sum(weights)
        if total == 0:
            return proxies[0]
        weights = [w / total for w in weights]
        return random.choices(proxies, weights=weights, k=1)[0]

    async def refresh_proxies(self):
        logger.info("Refreshing proxy pool...")
        new_proxies: List[ProxyInfo] = []
        for src in self._PROXY_SOURCES:
            try:
                fetched = await self._fetch_from_source(src)
                new_proxies.extend(fetched)
            except Exception as e:
                logger.warning("Proxy source %s failed: %s", src, e)
        valid = await self._validate_proxies(new_proxies)
        await self._persist_proxies(valid)
        async with self._lock:
            self._cache.clear()
        logger.info("Proxy pool refreshed: %d valid proxies", len(valid))

    async def _load_from_db(self) -> List[ProxyInfo]:
        async with self._session_factory() as sess:
            result = await sess.execute(
                select(ProxyPoolModel)
                .where(ProxyPoolModel.is_active == True)  # noqa: E712
                .order_by(
                    ProxyPoolModel.success_rate.desc(),
                    ProxyPoolModel.speed.asc(),
                )
                .limit(50)
            )
            rows = result.scalars().all()
        return [
            ProxyInfo(
                proxy_id=r.proxy_id, host=r.host, port=r.port,
                username=r.username, password=r.password,
                protocol=r.protocol or "http", location=r.location,
                speed=r.speed or 0.0, success_rate=r.success_rate or 1.0,
                fail_count=r.fail_count or 0, is_active=bool(r.is_active),
                last_used=r.last_used or datetime.now(),
            )
            for r in rows
        ]

    async def _fetch_from_source(self, url: str) -> List[ProxyInfo]:
        async with aiohttp.ClientSession() as sess:
            async with sess.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    return []
                txt = await resp.text()
        proxies = []
        for line in txt.strip().splitlines():
            parts = line.strip().split(":")
            if len(parts) >= 2:
                try:
                    pid = hashlib.md5(line.strip().encode()).hexdigest()[:8]
                    proxies.append(ProxyInfo(proxy_id=pid, host=parts[0], port=int(parts[1])))
                except ValueError:
                    pass
        return proxies

    async def _validate_proxies(self, proxies: List[ProxyInfo]) -> List[ProxyInfo]:
        TEST_URL = "http://httpbin.org/ip"
        valid: List[ProxyInfo] = []

        async def _check(proxy: ProxyInfo) -> Optional[ProxyInfo]:
            try:
                t0 = time.time()
                async with aiohttp.ClientSession() as sess:
                    async with sess.get(
                        TEST_URL, proxy=proxy.get_url(),
                        timeout=aiohttp.ClientTimeout(total=5)
                    ) as resp:
                        if resp.status == 200:
                            proxy.speed = (time.time() - t0) * 1000
                            proxy.is_active = True
                            return proxy
            except Exception:
                pass
            proxy.is_active = False
            return None

        results = await asyncio.gather(*[_check(p) for p in proxies[:50]])
        return [r for r in results if r is not None]

    async def _persist_proxies(self, proxies: List[ProxyInfo]):
        async with self._session_factory() as sess:
            for proxy in proxies:
                row = await sess.get(ProxyPoolModel, proxy.proxy_id)
                if row:
                    row.speed = proxy.speed
                    row.success_rate = proxy.success_rate
                    row.is_active = proxy.is_active
                    row.updated_at = datetime.now()
                else:
                    sess.add(ProxyPoolModel(
                        proxy_id=proxy.proxy_id, host=proxy.host, port=proxy.port,
                        protocol=proxy.protocol, location=proxy.location,
                        speed=proxy.speed, success_rate=proxy.success_rate,
                        fail_count=proxy.fail_count, is_active=proxy.is_active,
                    ))
            await sess.commit()

    async def _seed_local_proxies(self):
        """Seed a no-op direct proxy so adapters always have something to call."""
        async with self._session_factory() as sess:
            result = await sess.execute(
                select(ProxyPoolModel).limit(1)
            )
            if result.scalars().first() is None:
                pass   # proxy pool is empty — adapters will pass proxy=None (direct)
            await sess.commit()


# ==================== API管理器 ====================

_ADAPTER_MAP: Dict[PlatformType, type] = {
    PlatformType.TAOBAO:    TaobaoAPIAdapter,
    PlatformType.TMALL:     TmallAPIAdapter,
    PlatformType.JD:        JDAPIAdapter,
    PlatformType.PINDUODUO: PinduoduoAPIAdapter,
    PlatformType.DOUYIN:    DouyinAPIAdapter,
    PlatformType.VIP:       VIPAPIAdapter,
    PlatformType.ALIBABA:   AlibabaAPIAdapter,
    PlatformType.SUNING:    SuningAPIAdapter,
}


class APIManager:
    """统一API调用管理器"""

    def __init__(
        self,
        configs: Dict[PlatformType, APIConfig],
        proxy_manager: ProxyManager,
    ):
        self.configs       = configs
        self.proxy_manager = proxy_manager
        self.adapters: Dict[PlatformType, PlatformAPIAdapter] = {}
        self._init_adapters()

        self._calls_total     = _make_counter("dc_api_calls_total",    "Total API calls",     ["platform", "endpoint", "status"])
        self._response_time   = _make_histogram("dc_api_latency_seconds", "API latency",      ["platform"])
        self._errors_total    = _make_counter("dc_api_errors_total",   "API errors",          ["platform", "error_type"])

    def _init_adapters(self):
        for platform, config in self.configs.items():
            cls = _ADAPTER_MAP.get(platform)
            if cls:
                self.adapters[platform] = cls(config, self.proxy_manager)

    async def search_products(
        self, platform: PlatformType, query_params: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        self._assert_platform(platform)
        t0 = time.time()
        try:
            products = await self.adapters[platform].search_products(query_params)
            self._record_call(platform, "search", "success", time.time() - t0)
            return products
        except Exception as exc:
            self._record_error(platform, "search", exc)
            raise

    async def get_product_details(
        self, platform: PlatformType, product_id: str
    ) -> Dict[str, Any]:
        self._assert_platform(platform)
        t0 = time.time()
        try:
            details = await self.adapters[platform].get_product_details(product_id)
            self._record_call(platform, "details", "success", time.time() - t0)
            return details
        except Exception as exc:
            self._record_error(platform, "details", exc)
            raise

    async def get_product_reviews(
        self, platform: PlatformType, product_id: str, page: int = 1
    ) -> List[Dict[str, Any]]:
        self._assert_platform(platform)
        t0 = time.time()
        try:
            reviews = await self.adapters[platform].get_product_reviews(product_id, page)
            self._record_call(platform, "reviews", "success", time.time() - t0)
            return reviews
        except Exception as exc:
            self._record_error(platform, "reviews", exc)
            raise

    async def batch_search(
        self,
        tasks: List[Tuple[PlatformType, Dict[str, Any]]],
    ) -> Dict[PlatformType, List[Dict[str, Any]]]:
        """并发批量搜索"""
        async def _one(platform: PlatformType, qp: Dict) -> Tuple:
            try:
                return platform, await self.search_products(platform, qp), None
            except Exception as e:
                return platform, [], e

        results_raw = await asyncio.gather(*[_one(p, q) for p, q in tasks])
        out: Dict[PlatformType, List[Dict[str, Any]]] = {}
        for platform, products, err in results_raw:
            if err:
                logger.warning("Batch search error [%s]: %s", platform.value, err)
            out.setdefault(platform, []).extend(products)
        return out

    def _assert_platform(self, platform: PlatformType):
        if platform not in self.adapters:
            raise ValueError(f"Platform {platform.value} not configured")

    def _record_call(self, platform: PlatformType, endpoint: str, status: str, elapsed: float):
        if self._calls_total:
            self._calls_total.labels(platform=platform.value, endpoint=endpoint, status=status).inc()
        if self._response_time:
            self._response_time.labels(platform=platform.value).observe(elapsed)

    def _record_error(self, platform: PlatformType, endpoint: str, exc: Exception):
        if self._calls_total:
            self._calls_total.labels(platform=platform.value, endpoint=endpoint, status="error").inc()
        if self._errors_total:
            self._errors_total.labels(platform=platform.value, error_type=type(exc).__name__).inc()
        logger.error("API error [%s/%s]: %s", platform.value, endpoint, exc)


# ==================== 数据采集服务 ====================

class DataCollectionService:
    """数据采集服务 — 任务队列 + 多 worker"""

    def __init__(
        self,
        api_manager: APIManager,
        proxy_manager: ProxyManager,
        db_url: str = "sqlite+aiosqlite:///./collection.db",
    ):
        self.api_manager   = api_manager
        self.proxy_manager = proxy_manager
        self._engine       = create_async_engine(db_url, echo=False)
        self._session_factory = sessionmaker(
            self._engine, class_=AsyncSession, expire_on_commit=False
        )
        self._task_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._workers: List[asyncio.Task] = []
        self._running = False

        self._collected_total  = _make_counter("dc_collected_items_total", "Collected items", ["platform"])
        self._collection_time  = _make_histogram("dc_collection_time_seconds", "Collection time")
        self._errors_total     = _make_counter("dc_collection_errors_total", "Collection errors", ["platform"])

    # ── lifecycle ────────────────────────────────────────────────

    async def startup(self, worker_count: int = 5):
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        self._running = True
        self._workers = [
            asyncio.create_task(self._worker(i))
            for i in range(worker_count)
        ]
        logger.info("DataCollectionService started (%d workers)", worker_count)

    async def shutdown(self):
        self._running = False
        for w in self._workers:
            w.cancel()
        await asyncio.gather(*self._workers, return_exceptions=True)
        logger.info("DataCollectionService stopped")

    # ── public API ───────────────────────────────────────────────

    async def submit_task(self, task: CollectionTask) -> str:
        async with self._session_factory() as sess:
            sess.add(CollectionTaskModel(
                task_id=task.task_id, request_id=task.request_id,
                platform=task.platform.value, query_params=task.query_params,
                priority=task.priority, max_results=task.max_results,
                source_type=task.source_type.value, status="pending",
            ))
            await sess.commit()
        # Priority queue: lower number = higher priority; invert so 10 = highest
        await self._task_queue.put((10 - task.priority, task))
        logger.info("Task submitted: %s (platform=%s)", task.task_id, task.platform.value)
        return task.task_id

    async def collect_data(
        self,
        request_id: str,
        platform: PlatformType,
        query_params: Dict[str, Any],
        max_results: int = 100,
        priority: int = 5,
    ) -> str:
        task = CollectionTask(
            task_id=f"task_{uuid.uuid4().hex[:8]}",
            request_id=request_id,
            platform=platform,
            query_params=query_params,
            priority=max(1, min(priority, 10)),
            max_results=max_results,
            source_type=DataSourceType.API,
        )
        return await self.submit_task(task)

    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        async with self._session_factory() as sess:
            row = await sess.get(CollectionTaskModel, task_id)
            if not row:
                return None
            return {
                "task_id":       row.task_id,
                "platform":      row.platform,
                "status":        row.status,
                "result_count":  row.result_count,
                "error_message": row.error_message,
                "created_at":    row.created_at.isoformat() if row.created_at else None,
                "started_at":    row.started_at.isoformat() if row.started_at else None,
                "completed_at":  row.completed_at.isoformat() if row.completed_at else None,
            }

    # ── worker loop ──────────────────────────────────────────────

    async def _worker(self, worker_id: int):
        logger.info("Worker-%d started", worker_id)
        while self._running:
            try:
                _, task = await asyncio.wait_for(self._task_queue.get(), timeout=1.0)
                await self._process_task(task, worker_id)
                self._task_queue.task_done()
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Worker-%d unhandled error: %s", worker_id, exc)

    async def _process_task(self, task: CollectionTask, worker_id: int):
        logger.info("Worker-%d processing %s", worker_id, task.task_id)
        task.started_at = datetime.now()
        task.status     = "running"
        await self._update_task(task)
        t0 = time.time()

        try:
            results = await self._collect_from_api(task)
            for item in results:
                raw = RawData(
                    data_id=f"raw_{uuid.uuid4().hex[:8]}",
                    platform=task.platform,
                    source_type=task.source_type,
                    raw_content=item,
                    metadata={
                        "task_id":    task.task_id,
                        "request_id": task.request_id,
                        "worker_id":  worker_id,
                        "collected_at": datetime.now().isoformat(),
                    },
                )
                await self._save_raw(raw)

            task.status       = "completed"
            task.result_count = len(results)
            task.completed_at = datetime.now()
            await self._update_task(task)

            elapsed = time.time() - t0
            if self._collection_time:
                self._collection_time.observe(elapsed)
            if self._collected_total:
                self._collected_total.labels(platform=task.platform.value).inc(len(results))
            logger.info("Task %s done: %d items in %.2fs", task.task_id, len(results), elapsed)

        except Exception as exc:
            task.status       = "failed"
            task.error_message = str(exc)
            task.completed_at  = datetime.now()
            await self._update_task(task)
            if self._errors_total:
                self._errors_total.labels(platform=task.platform.value).inc()
            logger.error("Task %s failed: %s", task.task_id, exc)

    async def _collect_from_api(self, task: CollectionTask) -> List[Dict[str, Any]]:
        all_results: List[Dict[str, Any]] = []
        page_size  = task.query_params.get("page_size", 100)
        max_pages  = max(1, (task.max_results + page_size - 1) // page_size)

        for page in range(1, max_pages + 1):
            qp = dict(task.query_params)
            qp["page"]      = page
            qp["page_size"] = min(page_size, task.max_results - len(all_results))
            try:
                items = await self.api_manager.search_products(task.platform, qp)
                all_results.extend(items)
                if len(all_results) >= task.max_results or not items:
                    break
                await asyncio.sleep(0.3)
            except Exception as exc:
                logger.warning("Page %d collection error: %s", page, exc)
                break

        return all_results[:task.max_results]

    async def _update_task(self, task: CollectionTask):
        async with self._session_factory() as sess:
            row = await sess.get(CollectionTaskModel, task.task_id)
            if row:
                row.status        = task.status
                row.started_at    = task.started_at
                row.completed_at  = task.completed_at
                row.result_count  = task.result_count
                row.error_message = task.error_message
                await sess.commit()

    async def _save_raw(self, raw: RawData):
        async with self._session_factory() as sess:
            sess.add(RawDataModel(
                data_id=raw.data_id,
                task_id=raw.metadata.get("task_id"),
                platform=raw.platform.value,
                source_type=raw.source_type.value,
                raw_content=raw.raw_content,
                extra_metadata=raw.metadata,
                status=raw.status.value,
                created_at=raw.created_at,
            ))
            await sess.commit()


# ==================== 数据清洗器 ====================

class DataCleaner:
    """数据清洗器"""

    def clean(self, raw_data: RawData) -> CleanedData:
        log: List[str] = []
        content = (
            copy.deepcopy(raw_data.raw_content)
            if isinstance(raw_data.raw_content, dict)
            else {"raw": raw_data.raw_content}
        )
        content = self._remove_empty(content, log)
        content = self._format_fields(content, log)
        content = self._validate_types(content, log)
        content, missing = self._fill_missing(content, log)
        content = self._sanitize_strings(content, log)
        quality = self._calc_quality(content, missing)
        return CleanedData(
            data_id=f"cleaned_{uuid.uuid4().hex[:8]}",
            original_data_id=raw_data.data_id,
            platform=raw_data.platform,
            cleaned_content=content,
            cleaning_log=log,
            quality_score=quality,
            missing_fields=missing,
        )

    @staticmethod
    def _remove_empty(data: Dict, log: List[str]) -> Dict:
        cleaned = {k: v for k, v in data.items()
                   if v is not None and v != "" and v != [] and v != {}}
        removed = len(data) - len(cleaned)
        if removed:
            log.append(f"Removed {removed} empty fields")
        return cleaned

    @staticmethod
    def _format_fields(data: Dict, log: List[str]) -> Dict:
        out = {}
        for k, v in data.items():
            if k in ("price", "original_price", "group_price", "coupon_discount"):
                try:
                    out[k] = round(float(v), 2)
                except (TypeError, ValueError):
                    out[k] = 0.0
                    log.append(f"Coerced {k} to 0.0 (was {v!r})")
            elif k in ("sales", "review_count", "moq"):
                try:
                    out[k] = max(0, int(v))
                except (TypeError, ValueError):
                    out[k] = 0
                    log.append(f"Coerced {k} to 0 (was {v!r})")
            elif k == "rating":
                try:
                    out[k] = max(0.0, min(5.0, float(v)))
                except (TypeError, ValueError):
                    out[k] = 0.0
            else:
                out[k] = v
        return out

    @staticmethod
    def _validate_types(data: Dict, log: List[str]) -> Dict:
        rules: Dict[str, type] = {
            "price": float, "sales": int, "title": str,
        }
        for field, expected in rules.items():
            if field in data and not isinstance(data[field], expected):
                log.append(f"Type mismatch: {field} expected {expected.__name__}, got {type(data[field]).__name__}")
        return data

    @staticmethod
    def _fill_missing(data: Dict, log: List[str]) -> Tuple[Dict, List[str]]:
        required = ["product_id", "title", "price"]
        missing = []
        for f in required:
            if f not in data or not data[f]:
                missing.append(f)
                if f == "product_id":
                    data[f] = f"unknown_{hashlib.md5(json.dumps(data, default=str).encode()).hexdigest()[:8]}"
                elif f == "title":
                    data[f] = "未命名商品"
                elif f == "price":
                    data[f] = 0.0
        if missing:
            log.append(f"Filled missing required fields: {missing}")
        return data, missing

    @staticmethod
    def _sanitize_strings(data: Dict, log: List[str]) -> Dict:
        for k, v in data.items():
            if isinstance(v, str):
                cleaned_v = re.sub(r"[\r\n\t]+", " ", v).strip()
                cleaned_v = re.sub(r" {2,}", " ", cleaned_v)
                if cleaned_v != v:
                    data[k] = cleaned_v
        return data

    @staticmethod
    def _calc_quality(data: Dict, missing: List[str]) -> float:
        # Completeness (40 pts)
        required = ["product_id", "title", "price", "platform"]
        present  = sum(1 for f in required if data.get(f))
        completeness = present / len(required) * 40

        # Accuracy (30 pts)
        accuracy = 0.0
        if isinstance(data.get("price"), float) and data["price"] > 0:
            accuracy += 10
        if isinstance(data.get("sales"), int) and data["sales"] >= 0:
            accuracy += 10
        if data.get("product_id"):
            accuracy += 10

        # Consistency (20 pts) — platform field present
        consistency = 20.0 if data.get("platform") else 0.0

        # Penalty for missing required fields (−5 per field)
        penalty = len(missing) * 5

        total = completeness + accuracy + consistency - penalty
        return max(0.0, min(1.0, total / 100.0))


# ==================== 数据标准化器 ====================

class DataStandardizer:
    """将各平台字段映射到统一标准模型"""

    _FIELD_MAP: Dict[str, Dict[str, str]] = {
        "taobao": {
            "product_id": "product_id", "title": "title", "price": "price",
            "original_price": "original_price", "sales": "sales",
            "shop_name": "shop_name", "image_url": "image_url",
        },
        "tmall": {
            "product_id": "product_id", "title": "title", "price": "price",
            "original_price": "original_price", "sales": "sales",
            "shop_name": "shop_name", "image_url": "image_url",
        },
        "jd": {
            "product_id": "product_id", "title": "title", "price": "price",
            "original_price": "original_price", "sales": "sales",
            "brand": "brand", "shop_name": "shop_name", "image_url": "image_url",
            "is_self_operated": "is_self_operated",
        },
        "pinduoduo": {
            "product_id": "product_id", "title": "title", "price": "price",
            "original_price": "original_price", "sales": "sales",
            "shop_name": "shop_name", "image_url": "image_url",
            "has_coupon": "has_coupon", "coupon_discount": "coupon_discount",
        },
        "douyin": {
            "product_id": "product_id", "title": "title", "price": "price",
            "original_price": "original_price", "sales": "sales",
            "image_url": "image_url", "is_live_product": "is_live_product",
        },
        "vip": {
            "product_id": "product_id", "title": "title", "price": "price",
            "original_price": "original_price", "sales": "sales",
            "brand": "brand", "image_url": "image_url",
        },
        "alibaba": {
            "product_id": "product_id", "title": "title", "price": "price",
            "original_price": "original_price", "sales": "sales",
            "shop_name": "shop_name", "image_url": "image_url",
            "moq": "moq", "is_verified": "is_verified_supplier",
        },
        "suning": {
            "product_id": "product_id", "title": "title", "price": "price",
            "original_price": "original_price", "sales": "sales",
            "brand": "brand", "shop_name": "shop_name", "image_url": "image_url",
            "is_self": "is_self_operated",
        },
    }

    _STANDARD_TEMPLATE: Dict[str, Any] = {
        "product_id": None, "title": None, "description": "",
        "price": 0.0, "original_price": 0.0, "currency": "CNY",
        "category": None, "brand": None, "sales": 0, "rating": 0.0,
        "review_count": 0, "shop_id": None, "shop_name": None,
        "shop_rating": 0.0, "image_urls": [], "specifications": {},
        "platform": None, "source_url": None, "collection_time": None,
        "is_self_operated": False, "is_verified_supplier": False,
        "moq": 1, "has_coupon": False, "coupon_discount": 0.0,
    }

    def standardize(self, cleaned: CleanedData) -> StandardizedData:
        std = copy.deepcopy(self._STANDARD_TEMPLATE)
        mlog: Dict[str, Any] = {}
        platform = cleaned.platform.value
        mapping = self._FIELD_MAP.get(platform, {})

        for src_field, dst_field in mapping.items():
            val = cleaned.cleaned_content.get(src_field)
            if val is not None:
                std[dst_field] = val
                mlog[dst_field] = {"source": src_field, "value": val}

        std["platform"]        = platform
        std["collection_time"] = datetime.now().isoformat()

        # Wrap single image_url into list
        img = std.pop("image_url", None) or cleaned.cleaned_content.get("image_url")
        if img and not std.get("image_urls"):
            std["image_urls"] = [img]

        compliance = self._calc_compliance(std)
        return StandardizedData(
            data_id=f"std_{uuid.uuid4().hex[:8]}",
            cleaned_data_id=cleaned.data_id,
            platform=cleaned.platform,
            standardized_product=std,
            mapping_log=mlog,
            standard_compliance=compliance,
        )

    @staticmethod
    def _calc_compliance(product: Dict) -> float:
        required = ["product_id", "title", "price", "platform"]
        present  = sum(1 for f in required if product.get(f))
        return round(present / len(required), 2)


# ==================== 评分计算器 ====================

class DataScorer:
    _WEIGHTS = {
        "price_score":        0.25,
        "sales_score":        0.20,
        "shop_score":         0.15,
        "platform_score":     0.10,
        "completeness_score": 0.15,
        "recency_score":      0.15,
    }

    _PLATFORM_TRUST = {
        "tmall": 1.0, "jd": 0.9, "suning": 0.85, "taobao": 0.80,
        "vip": 0.80, "alibaba": 0.80, "pinduoduo": 0.70, "douyin": 0.70,
    }

    def score(self, std: StandardizedData) -> ScoredData:
        p = std.standardized_product
        dims = {
            "price_score":        self._price(p),
            "sales_score":        self._sales(p),
            "shop_score":         self._shop(p),
            "platform_score":     self._platform(p),
            "completeness_score": self._completeness(p),
            "recency_score":      self._recency(p),
        }
        breakdown: Dict[str, Any] = {
            k: {"score": round(dims[k], 3), "weight": self._WEIGHTS[k]}
            for k in dims
        }
        weighted = round(sum(dims[k] * self._WEIGHTS[k] for k in dims), 4)

        return ScoredData(
            data_id=f"scored_{uuid.uuid4().hex[:8]}",
            standardized_data_id=std.data_id,
            platform=std.platform,
            product_scores={k: round(v, 4) for k, v in dims.items()},
            weighted_score=weighted,
            score_breakdown=breakdown,
        )

    @staticmethod
    def _price(p: Dict) -> float:
        price = p.get("price", 0)
        if not isinstance(price, (int, float)) or price <= 0:
            return 0.0
        if price > 1_000_000:
            return 0.05
        # log scale: cheaper → higher score, capped at ¥10 000
        norm = min(price / 10_000, 1.0)
        return round(1.0 - norm * 0.9, 3)

    @staticmethod
    def _sales(p: Dict) -> float:
        s = p.get("sales", 0)
        if s >= 10_000: return 1.0
        if s >= 1_000:  return 0.8
        if s >= 100:    return 0.6
        if s >= 10:     return 0.4
        if s > 0:       return 0.2
        return 0.0

    @staticmethod
    def _shop(p: Dict) -> float:
        sr = p.get("shop_rating", 0.0)
        if not sr:
            return 0.5   # neutral when unknown
        if sr >= 4.8: return 1.0
        if sr >= 4.5: return 0.8
        if sr >= 4.0: return 0.6
        if sr >= 3.5: return 0.4
        return 0.2

    def _platform(self, p: Dict) -> float:
        return self._PLATFORM_TRUST.get(p.get("platform", ""), 0.5)

    @staticmethod
    def _completeness(p: Dict) -> float:
        important = ["product_id", "title", "price", "description",
                     "category", "brand", "sales", "image_urls"]
        present = sum(1 for f in important if p.get(f))
        return round(present / len(important), 2)

    @staticmethod
    def _recency(_p: Dict) -> float:
        return 1.0   # just-collected data is always fresh


# ==================== 数据质量检查器 ====================

class DataQualityChecker:
    """数据质量检查器 — 返回 is_valid + issues + warnings"""

    _MAX_PRICE = 1_000_000   # 100万元
    _MIN_QUALITY_SCORE = 0.3

    def check(self, cleaned: CleanedData) -> Dict[str, Any]:
        issues: List[str]   = []
        warnings: List[str] = []
        data = cleaned.cleaned_content

        # 1. Required fields
        for f in ["product_id", "title", "price"]:
            if not data.get(f):
                issues.append(f"Missing required field: {f}")

        # 2. Price sanity
        price = data.get("price")
        if price is not None:
            if not isinstance(price, (int, float)):
                issues.append(f"Price is not numeric: {price!r}")
            elif price < 0:
                issues.append(f"Negative price: {price}")
            elif price == 0:
                warnings.append("Price is zero — may indicate missing data")
            elif price > self._MAX_PRICE:
                warnings.append(f"Unusually high price: ¥{price:,.2f}")

        # 3. Sales sanity
        sales = data.get("sales")
        if sales is not None and isinstance(sales, int) and sales < 0:
            issues.append(f"Negative sales count: {sales}")

        # 4. Rating sanity
        rating = data.get("rating")
        if rating is not None:
            if not isinstance(rating, (int, float)):
                warnings.append(f"Rating is not numeric: {rating!r}")
            elif not (0 <= rating <= 5):
                warnings.append(f"Rating out of [0,5] range: {rating}")

        # 5. Title length
        title = data.get("title", "")
        if isinstance(title, str) and len(title) < 2:
            warnings.append("Title is very short (< 2 chars)")

        # 6. Overall quality score threshold
        if cleaned.quality_score < self._MIN_QUALITY_SCORE:
            issues.append(
                f"Quality score {cleaned.quality_score:.2f} is below minimum "
                f"threshold {self._MIN_QUALITY_SCORE}"
            )

        # 7. Potential spam / placeholder titles
        spam_patterns = re.compile(r"(test|测试|placeholder|AAAA|unknown)", re.I)
        if isinstance(title, str) and spam_patterns.search(title):
            warnings.append(f"Title matches spam pattern: '{title}'")

        return {
            "is_valid": len(issues) == 0,
            "issues":   issues,
            "warnings": warnings,
            "quality_score": cleaned.quality_score,
        }


# ==================== 数据处理管道 ====================

class DataProcessingPipeline:
    """清洗 → 标准化 → 评分 三段式处理管道"""

    def __init__(self, db_url: str = "sqlite+aiosqlite:///./pipeline.db"):
        self._engine = create_async_engine(db_url, echo=False)
        self._session_factory = sessionmaker(
            self._engine, class_=AsyncSession, expire_on_commit=False
        )
        self.cleaner       = DataCleaner()
        self.standardizer  = DataStandardizer()
        self.scorer        = DataScorer()
        self.quality_check = DataQualityChecker()

        self._stage_total  = _make_counter("dc_pipeline_stages_total", "Pipeline stages", ["stage", "status"])
        self._stage_time   = _make_histogram("dc_pipeline_stage_seconds", "Stage processing time", ["stage"])
        self._quality_gauge = _make_gauge("dc_data_quality_score", "Data quality score", ["platform"])

    async def startup(self):
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def process_raw_data(self, raw_data_id: str) -> Optional[str]:
        """返回最终 scored data_id，失败返回 None。"""
        raw = await self._load_raw(raw_data_id)
        if raw is None:
            raise ValueError(f"RawData not found: {raw_data_id}")

        await self._log_stage(raw_data_id, "cleaning", "started")
        try:
            cleaned       = await self._step("cleaning", raw_data_id, lambda: self.cleaner.clean(raw))
            qc_result     = self.quality_check.check(cleaned)

            if self._quality_gauge:
                self._quality_gauge.labels(platform=raw.platform.value).set(cleaned.quality_score)

            if not qc_result["is_valid"]:
                issues = "; ".join(qc_result["issues"])
                await self._log_stage(raw_data_id, "cleaning", "failed", {"reason": issues})
                await self._mark_raw_failed(raw_data_id)
                logger.warning("QC failed for %s: %s", raw_data_id, issues)
                return None

            standardized  = await self._step("standardization", raw_data_id, lambda: self.standardizer.standardize(cleaned))
            scored        = await self._step("scoring",          raw_data_id, lambda: self.scorer.score(standardized))

            await self._log_stage(raw_data_id, "scoring", "completed", {"scored_id": scored.data_id})
            await self._mark_raw_processed(raw_data_id)
            return scored.data_id

        except Exception as exc:
            await self._log_stage(raw_data_id, "pipeline", "failed", {"error": str(exc)})
            await self._mark_raw_failed(raw_data_id)
            logger.error("Pipeline error for %s: %s", raw_data_id, exc)
            raise

    async def process_batch(self, raw_data_ids: List[str], concurrency: int = 10) -> Dict[str, Any]:
        """并发批量处理"""
        sem = asyncio.Semaphore(concurrency)
        results: Dict[str, Any] = {"success": [], "failed": []}

        async def _one(rid: str):
            async with sem:
                try:
                    scored_id = await self.process_raw_data(rid)
                    if scored_id:
                        results["success"].append(scored_id)
                    else:
                        results["failed"].append(rid)
                except Exception as e:
                    results["failed"].append(rid)
                    logger.error("Batch process error %s: %s", rid, e)

        await asyncio.gather(*[_one(r) for r in raw_data_ids])
        return results

    # ── private helpers ──────────────────────────────────────────

    async def _step(self, stage: str, data_id: str, fn: Callable) -> Any:
        t0 = time.time()
        try:
            result = fn()
            elapsed = time.time() - t0
            if self._stage_total:
                self._stage_total.labels(stage=stage, status="success").inc()
            if self._stage_time:
                self._stage_time.labels(stage=stage).observe(elapsed)
            await self._log_stage(data_id, stage, "completed")
            return result
        except Exception:
            if self._stage_total:
                self._stage_total.labels(stage=stage, status="error").inc()
            raise

    async def _load_raw(self, raw_data_id: str) -> Optional[RawData]:
        async with self._session_factory() as sess:
            row = await sess.get(RawDataModel, raw_data_id)
            if not row:
                return None
            return RawData(
                data_id=row.data_id,
                platform=PlatformType(row.platform),
                source_type=DataSourceType(row.source_type),
                raw_content=row.raw_content,
                metadata=row.metadata or {},
                status=DataStatus(row.status),
                created_at=row.created_at or datetime.now(),
            )

    async def _log_stage(self, data_id: str, stage: str, status: str, metrics: Optional[Dict] = None):
        async with self._session_factory() as sess:
            sess.add(ProcessingPipelineModel(
                data_id=data_id,
                stage=stage,
                status=status,
                metrics=metrics or {},
                created_at=datetime.now(),
                completed_at=datetime.now() if status in ("completed", "failed") else None,
            ))
            await sess.commit()

    async def _mark_raw_processed(self, data_id: str):
        async with self._session_factory() as sess:
            row = await sess.get(RawDataModel, data_id)
            if row:
                row.status       = DataStatus.SCORED.value
                row.processed_at = datetime.now()
                await sess.commit()

    async def _mark_raw_failed(self, data_id: str):
        async with self._session_factory() as sess:
            row = await sess.get(RawDataModel, data_id)
            if row:
                row.status       = DataStatus.FAILED.value
                row.processed_at = datetime.now()
                await sess.commit()


# ==================== 合规监控 ====================

class ComplianceMonitor:
    """合规监控服务 — 检查数据采集与使用是否符合平台协议及法规"""

    # 高风险关键词：命中任一即触发 VIOLATION
    _VIOLATION_PATTERNS = re.compile(
        r"(个人隐私|personal_data|身份证|id_card|手机号|phone_number|密码|password"
        r"|银行卡|bank_account|信用卡|credit_card)",
        re.I,
    )

    # 需警告的关键词
    _RISKY_PATTERNS = re.compile(
        r"(敏感词|涉黄|涉政|违禁|fake|counterfeit|仿冒|盗版|pirated)",
        re.I,
    )

    # 平台采集频率上限 (reqs/min)
    _PLATFORM_RATE_LIMITS: Dict[str, int] = {
        "taobao": 60, "tmall": 60, "jd": 100, "pinduoduo": 40,
        "douyin": 30, "vip": 50, "alibaba": 80, "suning": 60,
    }

    def __init__(self, db_url: str = "sqlite+aiosqlite:///./compliance.db"):
        self._engine = create_async_engine(db_url, echo=False)
        self._session_factory = sessionmaker(
            self._engine, class_=AsyncSession, expire_on_commit=False
        )
        self._rate_windows: Dict[str, List[float]] = {}
        self._lock = asyncio.Lock()

        self._violations_total = _make_counter("dc_compliance_violations_total", "Compliance violations", ["level", "platform"])

    async def startup(self):
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def check_data(self, data: Dict[str, Any], platform: str) -> Dict[str, Any]:
        """检查单条数据的合规性，返回 {level, issues, action}"""
        issues: List[str] = []
        level = ComplianceLevel.FULL

        # 1. 个人隐私违规检查
        data_str = json.dumps(data, ensure_ascii=False, default=str)
        if self._VIOLATION_PATTERNS.search(data_str):
            issues.append("Data contains personal/sensitive information")
            level = ComplianceLevel.VIOLATION

        # 2. 涉及风险内容
        if level != ComplianceLevel.VIOLATION and self._RISKY_PATTERNS.search(data_str):
            issues.append("Data may contain risky or prohibited content")
            level = ComplianceLevel.RISKY

        # 3. 价格异常（疑似刷单）
        price = data.get("price", 0)
        sales = data.get("sales", 0)
        if isinstance(price, (int, float)) and isinstance(sales, int):
            if price < 0.1 and sales > 10_000:
                issues.append("Suspicious: near-zero price with very high sales (possible fake)")
                level = max(level, ComplianceLevel.RISKY, key=lambda x: list(ComplianceLevel).index(x))

        # 4. 图片URL合规（不允许外部跟踪像素）
        for img_url in data.get("image_urls", []):
            if isinstance(img_url, str) and re.search(r"(pixel|tracker|beacon)", img_url, re.I):
                issues.append(f"Suspicious image URL: {img_url}")
                if level == ComplianceLevel.FULL:
                    level = ComplianceLevel.LIMITED

        action = self._determine_action(level)

        # Record in DB
        await self._log_compliance(
            data_id=data.get("product_id", "unknown"),
            platform=platform,
            level=level,
            issues=issues,
            action=action,
        )

        if self._violations_total and level in (ComplianceLevel.RISKY, ComplianceLevel.VIOLATION):
            self._violations_total.labels(level=level.value, platform=platform).inc()

        return {"level": level.value, "issues": issues, "action": action}

    async def check_rate_compliance(self, platform: str) -> bool:
        """检查是否超出平台速率限制，返回 True=合规"""
        limit = self._PLATFORM_RATE_LIMITS.get(platform, 60)
        now = time.time()
        async with self._lock:
            window = self._rate_windows.setdefault(platform, [])
            # keep last 60s
            window[:] = [t for t in window if now - t < 60]
            if len(window) >= limit:
                return False
            window.append(now)
        return True

    async def generate_compliance_report(
        self, platform: Optional[str] = None, since_hours: int = 24
    ) -> Dict[str, Any]:
        """生成合规报告"""
        since = datetime.now() - timedelta(hours=since_hours)
        async with self._session_factory() as sess:
            stmt = select(ComplianceLogModel).where(
                ComplianceLogModel.checked_at >= since
            )
            if platform:
                stmt = stmt.where(ComplianceLogModel.platform == platform)
            result = await sess.execute(stmt)
            rows = result.scalars().all()

        total = len(rows)
        by_level: Dict[str, int] = {}
        by_platform: Dict[str, int] = {}
        for row in rows:
            by_level[row.compliance_level] = by_level.get(row.compliance_level, 0) + 1
            by_platform[row.platform]       = by_platform.get(row.platform, 0) + 1

        violations   = by_level.get(ComplianceLevel.VIOLATION.value, 0)
        risky        = by_level.get(ComplianceLevel.RISKY.value, 0)
        compliance_rate = round((total - violations - risky) / max(total, 1), 4)

        return {
            "period_hours":    since_hours,
            "total_checked":   total,
            "by_level":        by_level,
            "by_platform":     by_platform,
            "compliance_rate": compliance_rate,
            "generated_at":    datetime.now().isoformat(),
        }

    @staticmethod
    def _determine_action(level: ComplianceLevel) -> str:
        return {
            ComplianceLevel.FULL:      "allow",
            ComplianceLevel.LIMITED:   "allow_with_warning",
            ComplianceLevel.RISKY:     "quarantine",
            ComplianceLevel.VIOLATION: "reject_and_delete",
        }[level]

    async def _log_compliance(
        self,
        data_id: str,
        platform: str,
        level: ComplianceLevel,
        issues: List[str],
        action: str,
    ):
        async with self._session_factory() as sess:
            sess.add(ComplianceLogModel(
                data_id=data_id,
                platform=platform,
                compliance_level=level.value,
                issues=issues,
                action_taken=action,
                checked_at=datetime.now(),
            ))
            await sess.commit()


# ==================== FastAPI 应用工厂 ====================

# ── Pydantic request/response models ─────────────────────────────

class CollectRequest(BaseModel):
    request_id:  str
    platform:    str
    keyword:     str
    category_id: Optional[str]  = None
    max_results: int             = Field(default=100, ge=1, le=1000)
    priority:    int             = Field(default=5, ge=1, le=10)
    page_size:   int             = Field(default=50, ge=1, le=100)

    @validator("platform")
    def valid_platform(cls, v):
        try:
            PlatformType(v)
        except ValueError:
            valid = [p.value for p in PlatformType]
            raise ValueError(f"platform must be one of: {valid}")
        return v

    @validator("keyword")
    def not_empty(cls, v):
        if not v.strip():
            raise ValueError("keyword must not be empty")
        return v.strip()


class ProcessRequest(BaseModel):
    raw_data_ids: List[str]
    concurrency:  int = Field(default=5, ge=1, le=20)


class HealthResponse(BaseModel):
    status:  str
    service: str
    version: str
    ts:      str


def create_dc_app(
    db_url: str = "sqlite+aiosqlite:///./dc.db",
    redis_url: Optional[str] = None,
) -> FastAPI:
    app = FastAPI(
        title="数据采集与处理层",
        description="ILbuy 数据采集与处理层 — 7大平台采集、数据处理管道、合规监控",
        version="1.0.0",
    )

    _state: Dict[str, Any] = {}

    # ── lifecycle ─────────────────────────────────────────────────

    @app.on_event("startup")
    async def _startup():
        # Proxy manager
        proxy_mgr = ProxyManager(db_url=db_url)
        await proxy_mgr.startup()
        _state["proxy_manager"] = proxy_mgr

        # Build default mock configs for all 7 platforms
        configs = _build_default_configs()
        api_mgr = APIManager(configs, proxy_mgr)
        _state["api_manager"] = api_mgr

        # Collection service
        collector = DataCollectionService(api_mgr, proxy_mgr, db_url=db_url)
        await collector.startup(worker_count=3)
        _state["collector"] = collector

        # Processing pipeline
        pipeline = DataProcessingPipeline(db_url=db_url)
        await pipeline.startup()
        _state["pipeline"] = pipeline

        # Compliance monitor
        compliance = ComplianceMonitor(db_url=db_url)
        await compliance.startup()
        _state["compliance"] = compliance

        logger.info("数据采集与处理层 startup complete")

    @app.on_event("shutdown")
    async def _shutdown():
        collector = _state.get("collector")
        if collector:
            await collector.shutdown()
        logger.info("数据采集与处理层 shutdown complete")

    # ── dependencies ──────────────────────────────────────────────

    def _get_collector() -> DataCollectionService:
        c = _state.get("collector")
        if not c:
            raise HTTPException(503, "Service initializing")
        return c

    def _get_pipeline() -> DataProcessingPipeline:
        p = _state.get("pipeline")
        if not p:
            raise HTTPException(503, "Service initializing")
        return p

    def _get_compliance() -> ComplianceMonitor:
        c = _state.get("compliance")
        if not c:
            raise HTTPException(503, "Service initializing")
        return c

    # ── routes ────────────────────────────────────────────────────

    @app.get("/health", response_model=HealthResponse, tags=["system"])
    async def health():
        return HealthResponse(
            status="ok", service="data-collection-processing",
            version="1.0.0", ts=datetime.utcnow().isoformat() + "Z",
        )

    @app.get("/metrics", tags=["system"])
    async def metrics():
        if not _HAS_PROMETHEUS:
            raise HTTPException(501, "Prometheus not available")
        from fastapi.responses import Response as _R
        from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
        return _R(content=generate_latest(_DC_REGISTRY), media_type=CONTENT_TYPE_LATEST)

    @app.post("/api/v1/collect", tags=["collection"])
    async def start_collection(
        req: CollectRequest,
        collector: DataCollectionService = Depends(_get_collector),
    ):
        """提交采集任务（异步，立即返回 task_id）"""
        task_id = await collector.collect_data(
            request_id=req.request_id,
            platform=PlatformType(req.platform),
            query_params={
                "keyword":     req.keyword,
                "category_id": req.category_id or "",
                "page_size":   req.page_size,
            },
            max_results=req.max_results,
            priority=req.priority,
        )
        return {"task_id": task_id, "status": "submitted"}

    @app.get("/api/v1/tasks/{task_id}", tags=["collection"])
    async def get_task_status(
        task_id: str,
        collector: DataCollectionService = Depends(_get_collector),
    ):
        """查询采集任务状态"""
        status = await collector.get_task_status(task_id)
        if not status:
            raise HTTPException(404, f"Task {task_id!r} not found")
        return status

    @app.post("/api/v1/process", tags=["pipeline"])
    async def process_data(
        req: ProcessRequest,
        pipeline: DataProcessingPipeline = Depends(_get_pipeline),
    ):
        """处理一批原始数据（清洗→标准化→评分）"""
        result = await pipeline.process_batch(
            req.raw_data_ids, concurrency=req.concurrency
        )
        return {
            "processed": len(result["success"]),
            "failed":    len(result["failed"]),
            "scored_ids": result["success"],
            "failed_ids":  result["failed"],
        }

    @app.post("/api/v1/process/{raw_data_id}", tags=["pipeline"])
    async def process_single(
        raw_data_id: str,
        pipeline: DataProcessingPipeline = Depends(_get_pipeline),
    ):
        """处理单条原始数据"""
        try:
            scored_id = await pipeline.process_raw_data(raw_data_id)
        except ValueError as e:
            raise HTTPException(404, str(e))
        if not scored_id:
            raise HTTPException(422, "Data failed quality check — check pipeline logs")
        return {"raw_data_id": raw_data_id, "scored_id": scored_id}

    @app.post("/api/v1/compliance/check", tags=["compliance"])
    async def compliance_check(
        body: Dict[str, Any],
        compliance: ComplianceMonitor = Depends(_get_compliance),
    ):
        """检查单条数据的合规性"""
        platform = body.pop("platform", "unknown")
        result = await compliance.check_data(body, platform)
        return result

    @app.get("/api/v1/compliance/report", tags=["compliance"])
    async def compliance_report(
        platform: Optional[str] = Query(None),
        hours: int = Query(24, ge=1, le=720),
        compliance: ComplianceMonitor = Depends(_get_compliance),
    ):
        """获取合规报告"""
        return await compliance.generate_compliance_report(platform, since_hours=hours)

    @app.get("/api/v1/platforms", tags=["info"])
    async def list_platforms():
        """返回支持的平台列表"""
        return {
            "platforms": [p.value for p in PlatformType],
            "count":     len(PlatformType),
        }

    return app


# ==================== 默认平台配置 ====================

def _build_default_configs() -> Dict[PlatformType, APIConfig]:
    """为所有平台生成默认（mock）配置，生产环境从 env/config 文件覆盖"""
    defaults = {
        PlatformType.TAOBAO:    ("https://gw.api.taobao.com",    "v2", 60),
        PlatformType.TMALL:     ("https://gw.api.tmall.com",     "v2", 60),
        PlatformType.JD:        ("https://api.jd.com",           "v1", 100),
        PlatformType.PINDUODUO: ("https://gapi.pinduoduo.com",   "v1", 40),
        PlatformType.DOUYIN:    ("https://open.douyin.com",      "v1", 30),
        PlatformType.VIP:       ("https://open.vip.com",         "v1", 50),
        PlatformType.ALIBABA:   ("https://gw.open.1688.com",     "v1", 80),
        PlatformType.SUNING:    ("https://open.suning.com",      "v1", 60),
    }
    endpoint_sets = {
        "taobao_like": {
            "search": "items/search", "item_get": "item/get",
            "item_review": "item/review/list",
        },
        "jd": {
            "search": "product/search", "sku_detail": "product/detail",
            "review_list": "review/list",
        },
        "pinduoduo": {
            "search": "goods/search", "goods_detail": "goods/detail",
            "goods_review": "goods/review/list",
        },
        "douyin": {
            "search": "product/search", "product_detail": "product/detail",
            "product_review": "product/review/list",
        },
        "vip": {
            "search": "product/search", "product_detail": "product/detail",
            "review_list": "review/list",
        },
        "alibaba": {
            "search": "offer/search", "item_get": "offer/get",
        },
        "suning": {
            "search": "commodity/search", "product_detail": "commodity/detail",
            "review_list": "review/list",
        },
    }
    ep_map = {
        PlatformType.TAOBAO:    endpoint_sets["taobao_like"],
        PlatformType.TMALL:     endpoint_sets["taobao_like"],
        PlatformType.JD:        endpoint_sets["jd"],
        PlatformType.PINDUODUO: endpoint_sets["pinduoduo"],
        PlatformType.DOUYIN:    endpoint_sets["douyin"],
        PlatformType.VIP:       endpoint_sets["vip"],
        PlatformType.ALIBABA:   endpoint_sets["alibaba"],
        PlatformType.SUNING:    endpoint_sets["suning"],
    }

    configs: Dict[PlatformType, APIConfig] = {}
    for platform, (base_url, ver, rpm) in defaults.items():
        configs[platform] = APIConfig(
            platform=platform,
            base_url=os.getenv(f"{platform.value.upper()}_API_BASE", base_url),
            api_version=ver,
            endpoints=ep_map[platform],
            rate_limit_per_minute=rpm,
            rate_limit_per_day=int(os.getenv(f"{platform.value.upper()}_DAILY_LIMIT", "50000")),
            auth_type="api_key",
            auth_params={"api_key": os.getenv(f"{platform.value.upper()}_API_KEY", "")},
            timeout_seconds=15,
            retry_attempts=3,
            proxy_required=False,
            data_format="json",
        )
    return configs


# ==================== 主入口 ====================

app = create_dc_app(
    db_url=os.getenv("DC_DB_URL", "sqlite+aiosqlite:///./dc.db"),
    redis_url=os.getenv("DC_REDIS_URL"),
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "data_collection_processing:app",
        host=os.getenv("DC_HOST", "0.0.0.0"),
        port=int(os.getenv("DC_PORT", "8004")),
        reload=os.getenv("DC_RELOAD", "false").lower() == "true",
        log_level=os.getenv("DC_LOG_LEVEL", "info"),
        workers=int(os.getenv("DC_WORKERS", "1")),
    )
