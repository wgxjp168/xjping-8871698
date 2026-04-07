"""
feedback_loop_service.py — Part 9: Feedback & Optimization Flywheel
Production-grade: AI satisfaction follow-up, behavior tracking, A/B tests,
model training/evaluation/deployment, feature engineering, MLOps.
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
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta, date
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Query, Body
from fastapi.responses import JSONResponse
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

# ── Optional heavy deps ────────────────────────────────────────────────────────
try:
    import redis.asyncio as aioredis; _HAS_REDIS = True
except ImportError:
    aioredis = None; _HAS_REDIS = False  # type: ignore

try:
    import aiohttp; _HAS_AIOHTTP = True
except ImportError:
    aiohttp = None; _HAS_AIOHTTP = False  # type: ignore

try:
    import numpy as np; _HAS_NUMPY = True
except ImportError:
    np = None; _HAS_NUMPY = False  # type: ignore

try:
    import pandas as pd; _HAS_PANDAS = True
except ImportError:
    pd = None; _HAS_PANDAS = False  # type: ignore

try:
    from scipy import stats as scipy_stats; _HAS_SCIPY = True
except ImportError:
    scipy_stats = None; _HAS_SCIPY = False  # type: ignore

try:
    from sklearn.model_selection import train_test_split, cross_val_score
    from sklearn.metrics import (accuracy_score, precision_score, recall_score,
                                  f1_score, roc_auc_score, mean_squared_error, r2_score)
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler, LabelEncoder
    import joblib
    _HAS_SKLEARN = True
except ImportError:
    _HAS_SKLEARN = False

try:
    from nltk.sentiment.vader import SentimentIntensityAnalyzer as _VADER
    import nltk
    try: nltk.data.find('vader_lexicon')
    except LookupError:
        try: nltk.download('vader_lexicon', quiet=True)
        except Exception: pass
    _HAS_VADER = True
except ImportError:
    _VADER = None; _HAS_VADER = False  # type: ignore

try:
    from textblob import TextBlob as _TextBlob; _HAS_TEXTBLOB = True
except ImportError:
    _TextBlob = None; _HAS_TEXTBLOB = False  # type: ignore

try:
    from prometheus_client import Counter, Gauge, Histogram, CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST
    _HAS_PROMETHEUS = True
except ImportError:
    _HAS_PROMETHEUS = False

try:
    import mlflow; import mlflow.sklearn; from mlflow.tracking import MlflowClient
    _HAS_MLFLOW = True
except ImportError:
    mlflow = None; MlflowClient = None; _HAS_MLFLOW = False  # type: ignore

try:
    import optuna; _HAS_OPTUNA = True
except ImportError:
    optuna = None; _HAS_OPTUNA = False  # type: ignore

try:
    import aiofiles; _HAS_AIOFILES = True
except ImportError:
    aiofiles = None; _HAS_AIOFILES = False  # type: ignore

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s [%(filename)s:%(lineno)d] %(message)s",
)
logger = logging.getLogger("feedback_loop_service")

# ── Time helpers ───────────────────────────────────────────────────────────────
def _now() -> datetime:  return datetime.now(timezone.utc)
def _today() -> date:    return _now().date()
def _naive(dt: datetime) -> datetime:
    return dt.replace(tzinfo=None) if dt.tzinfo else dt
def _utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None: return None
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
def _fmt(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if dt else None

# ── Numeric helpers ────────────────────────────────────────────────────────────
def _mean(v: List[float]) -> float:
    if not v: return 0.0
    return float(np.mean(v)) if _HAS_NUMPY else statistics.mean(v)
def _std(v: List[float]) -> float:
    if len(v) < 2: return 0.0
    return float(np.std(v)) if _HAS_NUMPY else statistics.stdev(v)

# ── DB setup ───────────────────────────────────────────────────────────────────
DB_URL = os.getenv("FL_DB_URL", "sqlite:///./feedback_loop.db")
engine = create_engine(DB_URL, connect_args={"check_same_thread": False} if "sqlite" in DB_URL else {})
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

# ── Prometheus ─────────────────────────────────────────────────────────────────
_FL_REG = CollectorRegistry() if _HAS_PROMETHEUS else None
def _ctr(n,d,l=None):
    if not _HAS_PROMETHEUS: return None
    try: return Counter(n,d,l or [],registry=_FL_REG)
    except ValueError: return Counter(n,d,l or [],registry=CollectorRegistry())
def _gge(n,d,l=None):
    if not _HAS_PROMETHEUS: return None
    try: return Gauge(n,d,l or [],registry=_FL_REG)
    except ValueError: return Gauge(n,d,l or [],registry=CollectorRegistry())
def _hst(n,d,l=None):
    if not _HAS_PROMETHEUS: return None
    try: return Histogram(n,d,l or [],registry=_FL_REG)
    except ValueError: return Histogram(n,d,l or [],registry=CollectorRegistry())

FEEDBACKS_RX     = _ctr("fl_feedbacks_total",    "Total feedbacks",           ["type","sentiment"])
EVENTS_RX        = _ctr("fl_events_total",        "Total tracking events",     ["event_type"])
EXPERIMENTS_ACTIVE = _gge("fl_experiments_active","Active experiments")
MODELS_TRAINED   = _ctr("fl_models_trained_total","Total models trained",      ["algorithm","stage"])
REQ_LATENCY      = _hst("fl_request_latency_secs","Request latency",           ["endpoint"])

# ══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ══════════════════════════════════════════════════════════════════════════════
class FeedbackType(str, Enum):
    SATISFACTION    = "satisfaction"
    SENTIMENT       = "sentiment"
    BEHAVIOR        = "behavior"
    BUG             = "bug"
    FEATURE_REQUEST = "feature_request"
    NPS             = "nps"
    CSAT            = "csat"
    CES             = "ces"

class TrackingEventType(str, Enum):
    CLICK      = "click"
    VIEW       = "view"
    SEARCH     = "search"
    CONVERSION = "conversion"
    PURCHASE   = "purchase"
    SHARE      = "share"
    DOWNLOAD   = "download"
    UPLOAD     = "upload"
    LOGIN      = "login"
    LOGOUT     = "logout"

class ExperimentType(str, Enum):
    AB_TEST        = "a_b_test"
    MULTI_VARIANT  = "multi_variant"
    BANDIT         = "bandit"
    BAYESIAN       = "bayesian"
    OFFLINE        = "offline"

class ExperimentStatus(str, Enum):
    DRAFT     = "draft"
    ACTIVE    = "active"
    PAUSED    = "paused"
    COMPLETED = "completed"
    ARCHIVED  = "archived"

class ModelStage(str, Enum):
    DEVELOPMENT = "development"
    STAGING     = "staging"
    PRODUCTION  = "production"
    ARCHIVED    = "archived"

class DeploymentStrategy(str, Enum):
    CANARY     = "canary"
    BLUE_GREEN = "blue_green"
    ROLLING    = "rolling"
    RECREATE   = "recreate"
    SHADOW     = "shadow"

class ModelAlgorithm(str, Enum):
    RANDOM_FOREST = "random_forest"
    GRADIENT_BOOST= "gradient_boost"
    LOGISTIC_REG  = "logistic_regression"
    XGB           = "xgboost"
    LGB           = "lightgbm"
    NEURAL_NET    = "neural_net"
    CUSTOM        = "custom"

# ══════════════════════════════════════════════════════════════════════════════
# SERVICE CONFIG
# ══════════════════════════════════════════════════════════════════════════════
@dataclass
class ServiceConfig:
    database_url: str = DB_URL
    redis_url:    str = os.getenv("REDIS_URL", "redis://localhost:6379/8")
    host:         str = os.getenv("FL_HOST", "0.0.0.0")
    port:         int = int(os.getenv("FL_PORT", "8026"))
    debug:        bool = False

    mlflow_uri:   str = os.getenv("MLFLOW_URI",  "http://localhost:5000")
    mlflow_exp:   str = os.getenv("MLFLOW_EXP",  "feedback_loop")

    user_svc_url:          str = os.getenv("USER_SERVICE_URL",         "http://localhost:8020")
    notification_svc_url:  str = os.getenv("NOTIFICATION_SERVICE_URL", "http://localhost:8040")

    # Sentiment config
    sentiment_providers:  List[str] = field(default_factory=lambda: ["rule", "vader", "textblob"])
    # A/B test defaults
    ab_significance:      float = 0.05
    ab_min_sample:        int   = 100
    ab_max_days:          int   = 30
    # Model config
    model_storage_dir:    str = os.getenv("MODEL_STORAGE_DIR", "./model_storage")
    cross_val_folds:      int = 5
    # Survey triggers
    satisfaction_threshold: float = 3.0    # trigger followup if rating < this


# ══════════════════════════════════════════════════════════════════════════════
# PYDANTIC SCHEMAS
# ══════════════════════════════════════════════════════════════════════════════
class FeedbackRequest(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    user_id:      str
    session_id:   str
    feedback_type: FeedbackType
    content:      Optional[str]  = None
    rating:       Optional[float]= None
    nps_score:    Optional[int]  = None
    source:       str = "system"
    context:      Dict[str, Any] = {}
    metadata:     Dict[str, Any] = {}

    @field_validator("rating")
    @classmethod
    def validate_rating(cls, v):
        if v is not None and not (1 <= v <= 5):
            raise ValueError("rating must be 1–5")
        return v

    @field_validator("nps_score")
    @classmethod
    def validate_nps(cls, v):
        if v is not None and not (0 <= v <= 10):
            raise ValueError("nps_score must be 0–10")
        return v


class TrackingEventRequest(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    user_id:          str
    session_id:       str
    event_type:       TrackingEventType
    event_data:       Dict[str, Any] = {}
    page_url:         Optional[str]  = None
    referrer:         Optional[str]  = None
    device_info:      Optional[Dict[str, Any]] = None
    product_id:       Optional[str]  = None
    order_id:         Optional[str]  = None
    recommendation_id: Optional[str] = None
    metadata:         Dict[str, Any] = {}
    timestamp:        Optional[datetime] = None


class ExperimentRequest(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    experiment_name:   str
    experiment_type:   ExperimentType = ExperimentType.AB_TEST
    description:       str = ""
    variants:          List[Dict[str, Any]]
    target_metric:     str
    secondary_metrics: List[str] = []
    traffic_percentage: float = 100.0
    allocation_method: str = "uniform"
    target_sample_size: Optional[int] = None
    min_sample_size:   int = 100
    max_duration_days: int = 30
    audience_filters:  Dict[str, Any] = {}
    metadata:          Dict[str, Any] = {}

    @field_validator("variants")
    @classmethod
    def validate_variants(cls, v):
        if len(v) < 2:
            raise ValueError("at least 2 variants required")
        ids = [x.get("variant_id") for x in v]
        if len(set(ids)) != len(ids):
            raise ValueError("variant_id must be unique")
        return v

    @field_validator("traffic_percentage")
    @classmethod
    def validate_traffic(cls, v):
        if not (0 < v <= 100):
            raise ValueError("traffic_percentage must be (0,100]")
        return v


class ModelTrainingRequest(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    model_name:       str
    algorithm:        ModelAlgorithm = ModelAlgorithm.RANDOM_FOREST
    features:         List[str]
    target:           str
    training_data:    Dict[str, Any] = {}
    validation_split: float = 0.2
    hyperparameters:  Dict[str, Any] = {}
    cross_validation: bool = True
    metrics:          List[str] = ["accuracy", "f1"]
    metadata:         Dict[str, Any] = {}

    @field_validator("validation_split")
    @classmethod
    def validate_split(cls, v):
        if not (0 < v < 1): raise ValueError("validation_split must be (0,1)")
        return v


class ModelDeployRequest(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    model_id:          str
    strategy:          DeploymentStrategy = DeploymentStrategy.CANARY
    stage:             ModelStage = ModelStage.STAGING
    traffic_percentage: float = 10.0
    monitoring_metrics: List[str] = ["accuracy"]
    rollback_threshold: float = 0.95
    metadata:          Dict[str, Any] = {}


class ExperimentEventRequest(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    experiment_id: str
    user_id:       str
    variant:       str
    metric:        str
    value:         float
    metadata:      Dict[str, Any] = {}


# ══════════════════════════════════════════════════════════════════════════════
# ORM MODELS
# ══════════════════════════════════════════════════════════════════════════════
class FeedbackModel(Base):
    __tablename__ = "feedbacks"
    id            = Column(Integer, primary_key=True, autoincrement=True)
    feedback_id   = Column(String(64), unique=True, nullable=False, index=True)
    user_id       = Column(String(64), nullable=False, index=True)
    session_id    = Column(String(64), nullable=False)
    feedback_type = Column(String(32), nullable=False)
    content       = Column(Text,   nullable=True)
    rating        = Column(Float,  nullable=True)
    nps_score     = Column(Integer,nullable=True)
    sentiment     = Column(String(16), nullable=True)          # positive/negative/neutral
    sentiment_score = Column(Float, nullable=True)
    source        = Column(String(64), default="system")
    context_data  = Column("feedback_context",  JSON, default=dict)
    extra_metadata= Column("feedback_metadata", JSON, default=dict)
    is_processed  = Column(Boolean, default=False)
    processed_at  = Column(DateTime, nullable=True)
    followup_sent = Column(Boolean, default=False)
    created_at    = Column(DateTime, default=lambda: _naive(_now()))
    updated_at    = Column(DateTime, default=lambda: _naive(_now()), onupdate=lambda: _naive(_now()))
    __table_args__ = (Index("ix_fb_user_type", "user_id", "feedback_type"),)


class TrackingEventModel(Base):
    __tablename__ = "tracking_events"
    id             = Column(Integer, primary_key=True, autoincrement=True)
    event_id       = Column(String(64), unique=True, nullable=False, index=True)
    user_id        = Column(String(64), nullable=False, index=True)
    session_id     = Column(String(64), nullable=False, index=True)
    event_type     = Column(String(32), nullable=False)
    event_data     = Column("event_data_json",   JSON, default=dict)
    page_url       = Column(String(512), nullable=True)
    referrer       = Column(String(512), nullable=True)
    device_info    = Column("device_info_json",  JSON, nullable=True)
    product_id     = Column(String(64),  nullable=True, index=True)
    order_id       = Column(String(64),  nullable=True)
    recommendation_id = Column(String(64), nullable=True)
    extra_metadata = Column("event_metadata",    JSON, default=dict)
    created_at     = Column(DateTime, default=lambda: _naive(_now()))
    __table_args__  = (Index("ix_te_user_event", "user_id", "event_type"),)


class ExperimentModel(Base):
    __tablename__ = "experiments"
    id                = Column(Integer, primary_key=True, autoincrement=True)
    experiment_id     = Column(String(64), unique=True, nullable=False, index=True)
    experiment_name   = Column(String(256), nullable=False)
    experiment_type   = Column(String(32), nullable=False)
    description       = Column(Text, default="")
    status            = Column(String(32), default=ExperimentStatus.DRAFT.value)
    variants_config   = Column("variants_json",   JSON, default=list)
    target_metric     = Column(String(128), nullable=False)
    secondary_metrics = Column("secondary_metrics_json", JSON, default=list)
    traffic_percentage= Column(Float, default=100.0)
    allocation_method = Column(String(32), default="uniform")
    target_sample_size= Column(Integer, nullable=True)
    min_sample_size   = Column(Integer, default=100)
    max_duration_days = Column(Integer, default=30)
    audience_filters  = Column("audience_filters_json", JSON, default=dict)
    results           = Column("results_json",    JSON, default=dict)
    bandit_weights    = Column("bandit_weights_json", JSON, default=dict)
    winner_variant    = Column(String(64),  nullable=True)
    significance      = Column(Float, nullable=True)
    started_at        = Column(DateTime, nullable=True)
    ended_at          = Column(DateTime, nullable=True)
    extra_metadata    = Column("experiment_metadata", JSON, default=dict)
    created_at        = Column(DateTime, default=lambda: _naive(_now()))
    updated_at        = Column(DateTime, default=lambda: _naive(_now()), onupdate=lambda: _naive(_now()))


class ExperimentAssignmentModel(Base):
    __tablename__ = "experiment_assignments"
    id            = Column(Integer, primary_key=True, autoincrement=True)
    assignment_id = Column(String(64), unique=True, nullable=False)
    experiment_id = Column(String(64), nullable=False, index=True)
    user_id       = Column(String(64), nullable=False, index=True)
    variant_id    = Column(String(64), nullable=False)
    events        = Column("assignment_events_json", JSON, default=list)
    extra_metadata= Column("assignment_metadata", JSON, default=dict)
    created_at    = Column(DateTime, default=lambda: _naive(_now()))
    __table_args__ = (
        UniqueConstraint("experiment_id", "user_id", name="uq_exp_user"),
    )


class ModelModel(Base):
    __tablename__ = "ml_models"
    id              = Column(Integer, primary_key=True, autoincrement=True)
    model_id        = Column(String(64), unique=True, nullable=False, index=True)
    model_name      = Column(String(256), nullable=False)
    version         = Column(String(32), nullable=False)
    algorithm       = Column(String(64), nullable=False)
    stage           = Column(String(32), default=ModelStage.DEVELOPMENT.value)
    features        = Column("features_json",       JSON, default=list)
    target          = Column(String(128), nullable=False)
    hyperparameters = Column("hyperparams_json",    JSON, default=dict)
    training_metrics= Column("train_metrics_json",  JSON, default=dict)
    validation_metrics = Column("val_metrics_json", JSON, default=dict)
    cross_val_scores= Column("cv_scores_json",      JSON, default=list)
    artifact_path   = Column(String(512), nullable=True)
    mlflow_run_id   = Column(String(64),  nullable=True)
    description     = Column(Text, default="")
    extra_metadata  = Column("model_metadata",      JSON, default=dict)
    trained_at      = Column(DateTime, default=lambda: _naive(_now()))
    created_at      = Column(DateTime, default=lambda: _naive(_now()))
    updated_at      = Column(DateTime, default=lambda: _naive(_now()), onupdate=lambda: _naive(_now()))


class ModelDeploymentModel(Base):
    __tablename__ = "model_deployments"
    id                 = Column(Integer, primary_key=True, autoincrement=True)
    deployment_id      = Column(String(64), unique=True, nullable=False, index=True)
    model_id           = Column(String(64), nullable=False, index=True)
    strategy           = Column(String(32), nullable=False)
    stage              = Column(String(32), nullable=False)
    traffic_percentage = Column(Float, default=10.0)
    monitoring_metrics = Column("monitoring_metrics_json", JSON, default=list)
    rollback_threshold = Column(Float, default=0.95)
    is_active          = Column(Boolean, default=True)
    deployed_at        = Column(DateTime, default=lambda: _naive(_now()))
    rolled_back_at     = Column(DateTime, nullable=True)
    extra_metadata     = Column("deploy_metadata", JSON, default=dict)


Base.metadata.create_all(engine)


# ══════════════════════════════════════════════════════════════════════════════
# REDIS MANAGER
# ══════════════════════════════════════════════════════════════════════════════
class RedisManager:
    """Async Redis wrapper with in-memory fallback."""
    _client: Any = None
    _memory: Dict[str, Tuple[str, float]] = {}   # key -> (value, expire_ts)

    def __init__(self, url: str):
        self._url = url

    async def connect(self):
        if _HAS_REDIS:
            try:
                self._client = aioredis.from_url(self._url, decode_responses=True)
                await self._client.ping()
                logger.info("Redis connected: %s", self._url)
            except Exception as e:
                logger.warning("Redis unavailable (%s); using in-memory fallback", e)
                self._client = None
        else:
            self._client = None

    async def disconnect(self):
        if self._client:
            await self._client.close()

    async def get(self, key: str) -> Optional[str]:
        if self._client:
            try: return await self._client.get(key)
            except Exception: pass
        entry = self._memory.get(key)
        if entry and (entry[1] == 0 or time.time() < entry[1]):
            return entry[0]
        return None

    async def set(self, key: str, value: str, ttl: int = 0) -> bool:
        if self._client:
            try:
                if ttl: await self._client.setex(key, ttl, value)
                else:   await self._client.set(key, value)
                return True
            except Exception: pass
        self._memory[key] = (value, time.time() + ttl if ttl else 0)
        return True

    async def delete(self, key: str) -> int:
        if self._client:
            try: return await self._client.delete(key)
            except Exception: pass
        return 1 if self._memory.pop(key, None) else 0

    async def incr(self, key: str) -> int:
        if self._client:
            try: return await self._client.incr(key)
            except Exception: pass
        val = int((self._memory.get(key) or ("0", 0))[0])
        val += 1
        self._memory[key] = (str(val), 0)
        return val

    async def hset(self, name: str, key: str, value: str) -> int:
        full_key = f"{name}:{key}"
        return 1 if await self.set(full_key, value) else 0

    async def hget(self, name: str, key: str) -> Optional[str]:
        return await self.get(f"{name}:{key}")

    async def hgetall(self, name: str) -> Dict[str, str]:
        if self._client:
            try: return await self._client.hgetall(name) or {}
            except Exception: pass
        prefix = f"{name}:"
        return {k[len(prefix):]: v[0] for k, v in self._memory.items()
                if k.startswith(prefix) and (v[1] == 0 or time.time() < v[1])}


# ══════════════════════════════════════════════════════════════════════════════
# SENTIMENT ANALYZER
# ══════════════════════════════════════════════════════════════════════════════
_POS_WORDS = {"好", "棒", "赞", "优", "满意", "快", "喜欢", "excellent", "great", "good",
              "perfect", "love", "best", "awesome", "recommend", "happy", "satisfied"}
_NEG_WORDS = {"差", "烂", "慢", "贵", "失望", "差劲", "不满", "退款", "投诉",
              "bad", "terrible", "awful", "poor", "disappointed", "slow", "broken",
              "useless", "worst", "hate", "refund", "problem", "issue", "bug"}


class SentimentAnalyzer:
    """Multi-provider sentiment analysis with rule-based Chinese fallback."""

    def __init__(self, providers: List[str] = None):
        self._providers = providers or ["rule", "vader", "textblob"]
        self._vader_analyzer = _VADER() if _HAS_VADER else None

    def analyze(self, text: str) -> Dict[str, Any]:
        if not text or not text.strip():
            return {"label": "neutral", "score": 0.0, "provider": "rule"}
        for provider in self._providers:
            try:
                result = self._analyze_with(provider, text.strip())
                if result:
                    return result
            except Exception as e:
                logger.debug("Sentiment provider %s failed: %s", provider, e)
        return {"label": "neutral", "score": 0.0, "provider": "fallback"}

    def _analyze_with(self, provider: str, text: str) -> Optional[Dict[str, Any]]:
        if provider == "vader" and _HAS_VADER and self._vader_analyzer:
            scores = self._vader_analyzer.polarity_scores(text)
            compound = scores["compound"]
            label = "positive" if compound >= 0.05 else ("negative" if compound <= -0.05 else "neutral")
            return {"label": label, "score": round(compound, 4), "provider": "vader"}

        if provider == "textblob" and _HAS_TEXTBLOB:
            blob = _TextBlob(text)
            score = blob.sentiment.polarity  # type: ignore
            label = "positive" if score > 0.05 else ("negative" if score < -0.05 else "neutral")
            return {"label": label, "score": round(score, 4), "provider": "textblob"}

        if provider == "rule":
            return self._rule_based(text)

        return None

    def _rule_based(self, text: str) -> Dict[str, Any]:
        lower = text.lower()
        pos = sum(1 for w in _POS_WORDS if w in lower)
        neg = sum(1 for w in _NEG_WORDS if w in lower)
        total = pos + neg
        if total == 0:
            # Check rating-like patterns
            patterns_pos = re.findall(r"\b([4-5])\s*[分星]", text)
            patterns_neg = re.findall(r"\b([1-2])\s*[分星]", text)
            if patterns_pos: return {"label": "positive", "score": 0.6, "provider": "rule"}
            if patterns_neg: return {"label": "negative", "score": -0.6, "provider": "rule"}
            return {"label": "neutral", "score": 0.0, "provider": "rule"}
        score = round((pos - neg) / total, 4)
        label = "positive" if score > 0 else ("negative" if score < 0 else "neutral")
        return {"label": label, "score": score, "provider": "rule"}


# ══════════════════════════════════════════════════════════════════════════════
# A/B TEST ENGINE
# ══════════════════════════════════════════════════════════════════════════════
class ABTestEngine:
    """Statistical A/B test analysis: z-test or scipy t-test."""

    def __init__(self, significance: float = 0.05):
        self._alpha = significance

    # ── Assignment ────────────────────────────────────────────────────────────
    def assign_variant(self, user_id: str, experiment: ExperimentModel) -> str:
        """Deterministic assignment via hash, respects bandit weights."""
        method = experiment.allocation_method or "uniform"
        variants = experiment.variants_config or []
        if not variants:
            return "control"
        variant_ids = [v["variant_id"] for v in variants]

        if method == "bandit":
            return self._bandit_allocation(user_id, experiment, variant_ids)
        if method == "adaptive":
            return self._adaptive_allocation(user_id, experiment, variant_ids)
        # Default: uniform hash
        idx = int(hashlib.md5(f"{user_id}:{experiment.experiment_id}".encode()).hexdigest(), 16)
        return variant_ids[idx % len(variant_ids)]

    def _bandit_allocation(
        self, user_id: str, experiment: ExperimentModel, variant_ids: List[str]
    ) -> str:
        """UCB1 multi-armed bandit allocation."""
        weights = experiment.bandit_weights or {}
        results = experiment.results or {}
        n_total = sum(results.get(v, {}).get("n", 0) for v in variant_ids) + 1
        best_vid, best_score = variant_ids[0], -1.0
        for vid in variant_ids:
            vr = results.get(vid, {})
            n_i  = max(vr.get("n", 0), 1)
            mu_i = vr.get("mean", 0.5)
            # UCB1 score
            ucb = mu_i + math.sqrt(2.0 * math.log(n_total) / n_i)
            if ucb > best_score:
                best_score, best_vid = ucb, vid
        return best_vid

    def _adaptive_allocation(
        self, user_id: str, experiment: ExperimentModel, variant_ids: List[str]
    ) -> str:
        """Thompson Sampling (Beta distribution posterior) allocation."""
        results = experiment.results or {}
        if not _HAS_NUMPY:
            return self._bandit_allocation(user_id, experiment, variant_ids)
        best_vid, best_sample = variant_ids[0], -1.0
        for vid in variant_ids:
            vr = results.get(vid, {})
            alpha = max(vr.get("conversions", 0), 0) + 1
            beta  = max(vr.get("n", 0) - vr.get("conversions", 0), 0) + 1
            sample = float(np.random.beta(alpha, beta))
            if sample > best_sample:
                best_sample, best_vid = sample, vid
        return best_vid

    # ── Analysis ──────────────────────────────────────────────────────────────
    def analyze(self, experiment: ExperimentModel) -> Dict[str, Any]:
        """Run statistical analysis across all variants."""
        variants  = experiment.variants_config or []
        results   = experiment.results or {}
        if len(variants) < 2:
            return {"status": "insufficient_variants"}

        control_id = next((v["variant_id"] for v in variants if v.get("is_control")),
                          variants[0]["variant_id"])
        ctrl_data = results.get(control_id, {})
        ctrl_n    = ctrl_data.get("n", 0)
        ctrl_mean = ctrl_data.get("mean", 0.0)

        comparisons: Dict[str, Any] = {}
        winner = None
        best_improvement = 0.0

        for v in variants:
            vid = v["variant_id"]
            if vid == control_id:
                continue
            vdata = results.get(vid, {})
            vn    = vdata.get("n", 0)
            vmean = vdata.get("mean", 0.0)

            comp = self._compare(ctrl_n, ctrl_mean, ctrl_data.get("std", 0.1),
                                 vn, vmean, vdata.get("std", 0.1))
            comp["relative_improvement"] = (
                (vmean - ctrl_mean) / ctrl_mean * 100 if ctrl_mean else 0.0
            )
            comparisons[vid] = comp

            if comp.get("significant") and comp["relative_improvement"] > best_improvement:
                best_improvement = comp["relative_improvement"]
                winner = vid

        return {
            "status": "analyzed",
            "control": control_id,
            "comparisons": comparisons,
            "winner": winner,
            "sample_adequate": ctrl_n >= (experiment.min_sample_size or 100),
            "analyzed_at": _fmt(_now()),
        }

    def _compare(
        self, n1: int, m1: float, s1: float,
        n2: int, m2: float, s2: float,
    ) -> Dict[str, Any]:
        """Two-sample z-test (or scipy t-test if available)."""
        if n1 < 2 or n2 < 2:
            return {"p_value": 1.0, "z_stat": 0.0, "significant": False, "method": "insufficient"}

        if _HAS_SCIPY:
            # Welch t-test; build synthetic normal samples
            try:
                if _HAS_NUMPY:
                    rng = np.random.default_rng(42)
                    a = rng.normal(m1, max(s1, 1e-9), min(n1, 1000))
                    b = rng.normal(m2, max(s2, 1e-9), min(n2, 1000))
                    t_stat, p_val = scipy_stats.ttest_ind(a, b, equal_var=False)
                    return {"p_value": float(p_val), "t_stat": float(t_stat),
                            "significant": float(p_val) < self._alpha, "method": "welch_t"}
            except Exception:
                pass

        # Fallback: two-proportion z-test
        p1 = max(min(m1, 1.0), 0.0)
        p2 = max(min(m2, 1.0), 0.0)
        p_pool = (p1 * n1 + p2 * n2) / (n1 + n2)
        denom  = math.sqrt(p_pool * (1 - p_pool) * (1/n1 + 1/n2) + 1e-12)
        z_stat = (p1 - p2) / denom
        # Approximate two-tailed p-value using error function
        p_val  = 2.0 * (1.0 - _norm_cdf(abs(z_stat)))
        return {"p_value": round(p_val, 6), "z_stat": round(z_stat, 4),
                "significant": p_val < self._alpha, "method": "z_test"}


def _norm_cdf(x: float) -> float:
    """Standard normal CDF using math.erf."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


# ══════════════════════════════════════════════════════════════════════════════
# FEATURE ENGINEER
# ══════════════════════════════════════════════════════════════════════════════
class FeatureEngineer:
    """Simple feature extraction from feedback + tracking data."""

    def extract_feedback_features(self, feedbacks: List[Dict]) -> Dict[str, Any]:
        """Aggregate numeric features from a list of feedback dicts."""
        if not feedbacks:
            return {}
        ratings     = [f["rating"] for f in feedbacks if f.get("rating") is not None]
        nps_scores  = [f["nps_score"] for f in feedbacks if f.get("nps_score") is not None]
        sentiments  = [f.get("sentiment_score", 0.0) for f in feedbacks if f.get("sentiment_score") is not None]
        return {
            "count":           len(feedbacks),
            "avg_rating":      round(_mean(ratings), 4) if ratings else None,
            "std_rating":      round(_std(ratings),  4) if ratings else None,
            "avg_nps":         round(_mean(nps_scores), 4) if nps_scores else None,
            "nps_promoters":   sum(1 for n in nps_scores if n >= 9),
            "nps_detractors":  sum(1 for n in nps_scores if n <= 6),
            "avg_sentiment":   round(_mean(sentiments), 4) if sentiments else None,
            "positive_ratio":  round(sum(1 for f in feedbacks if f.get("sentiment")=="positive")/len(feedbacks), 4),
            "negative_ratio":  round(sum(1 for f in feedbacks if f.get("sentiment")=="negative")/len(feedbacks), 4),
        }

    def extract_event_features(self, events: List[Dict]) -> Dict[str, Any]:
        if not events:
            return {}
        types  = [e.get("event_type") for e in events]
        return {
            "total_events":    len(events),
            "unique_sessions": len({e.get("session_id") for e in events}),
            "click_count":     types.count("click"),
            "view_count":      types.count("view"),
            "search_count":    types.count("search"),
            "conversion_count":types.count("conversion"),
            "purchase_count":  types.count("purchase"),
            "conversion_rate": round(types.count("conversion") / max(types.count("view"), 1), 4),
        }


# ══════════════════════════════════════════════════════════════════════════════
# MODEL TRAINER
# ══════════════════════════════════════════════════════════════════════════════
class ModelTrainer:
    """sklearn-based model trainer with MLflow logging."""

    def __init__(self, cfg: ServiceConfig):
        self._cfg = cfg
        Path(cfg.model_storage_dir).mkdir(parents=True, exist_ok=True)

    def _build_estimator(self, algorithm: str, hp: Dict) -> Any:
        if not _HAS_SKLEARN:
            return None
        algo = ModelAlgorithm(algorithm)
        if algo == ModelAlgorithm.RANDOM_FOREST:
            return RandomForestClassifier(
                n_estimators=hp.get("n_estimators", 100),
                max_depth=hp.get("max_depth", None),
                random_state=hp.get("random_state", 42),
            )
        if algo == ModelAlgorithm.GRADIENT_BOOST:
            return GradientBoostingClassifier(
                n_estimators=hp.get("n_estimators", 100),
                learning_rate=hp.get("learning_rate", 0.1),
                max_depth=hp.get("max_depth", 3),
                random_state=hp.get("random_state", 42),
            )
        if algo == ModelAlgorithm.LOGISTIC_REG:
            return LogisticRegression(
                C=hp.get("C", 1.0),
                max_iter=hp.get("max_iter", 200),
                random_state=hp.get("random_state", 42),
            )
        # Default
        return RandomForestClassifier(n_estimators=50, random_state=42)

    def train(self, req: ModelTrainingRequest, data: Dict) -> Dict[str, Any]:
        """
        data = {"X": [[...], ...], "y": [...]}
        Returns training metrics dict.
        """
        if not _HAS_SKLEARN:
            return {"stub": True, "accuracy": 0.85, "f1": 0.84, "note": "sklearn not available"}

        X_raw = data.get("X", [])
        y_raw = data.get("y", [])
        if not X_raw or not y_raw:
            return {"error": "no training data provided"}

        if _HAS_NUMPY:
            X = np.array(X_raw, dtype=float)
            y = np.array(y_raw)
        else:
            X, y = X_raw, y_raw  # type: ignore

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=req.validation_split, random_state=42
        )
        scaler  = StandardScaler()
        X_train = scaler.fit_transform(X_train)
        X_test  = scaler.transform(X_test)

        model   = self._build_estimator(req.algorithm, req.hyperparameters)
        model.fit(X_train, y_train)
        y_pred  = model.predict(X_test)

        metrics: Dict[str, Any] = {"accuracy": float(accuracy_score(y_test, y_pred))}
        if "f1"        in req.metrics: metrics["f1"]        = float(f1_score(y_test, y_pred, average="weighted", zero_division=0))
        if "precision" in req.metrics: metrics["precision"] = float(precision_score(y_test, y_pred, average="weighted", zero_division=0))
        if "recall"    in req.metrics: metrics["recall"]    = float(recall_score(y_test, y_pred, average="weighted", zero_division=0))

        cv_scores: List[float] = []
        if req.cross_validation and len(X_raw) >= self._cfg.cross_val_folds * 5:
            try:
                scaler2 = StandardScaler()
                X_cv = scaler2.fit_transform(np.array(X_raw, dtype=float))
                scores = cross_val_score(model, X_cv, y, cv=self._cfg.cross_val_folds)
                cv_scores = [round(float(s), 4) for s in scores]
            except Exception as e:
                logger.warning("cross-validation failed: %s", e)

        # Save artifact
        artifact_path: Optional[str] = None
        if _HAS_SKLEARN:
            try:
                artifact_path = os.path.join(
                    self._cfg.model_storage_dir,
                    f"{req.model_name}_{uuid.uuid4().hex[:8]}.pkl"
                )
                joblib.dump({"model": model, "scaler": scaler}, artifact_path)
            except Exception as e:
                logger.warning("artifact save failed: %s", e)

        # MLflow logging
        mlflow_run_id: Optional[str] = None
        if _HAS_MLFLOW:
            try:
                mlflow.set_tracking_uri(self._cfg.mlflow_uri)
                mlflow.set_experiment(self._cfg.mlflow_exp)
                with mlflow.start_run(run_name=req.model_name) as run:
                    mlflow.log_params(req.hyperparameters)
                    mlflow.log_metrics(metrics)
                    if artifact_path: mlflow.sklearn.log_model(model, "model")
                    mlflow_run_id = run.info.run_id
            except Exception as e:
                logger.warning("MLflow logging failed: %s", e)

        return {
            "training_metrics": metrics,
            "cv_scores": cv_scores,
            "artifact_path": artifact_path,
            "mlflow_run_id": mlflow_run_id,
        }


# ══════════════════════════════════════════════════════════════════════════════
# FEEDBACK LOOP SERVICE
# ══════════════════════════════════════════════════════════════════════════════
class FeedbackLoopService:
    """Core service: feedback collection, A/B experiments, model MLOps."""

    def __init__(self, cfg: ServiceConfig):
        self._cfg      = cfg
        self._redis    = RedisManager(cfg.redis_url)
        self._sentiment= SentimentAnalyzer(cfg.sentiment_providers)
        self._ab       = ABTestEngine(cfg.ab_significance)
        self._trainer  = ModelTrainer(cfg)
        self._engineer = FeatureEngineer()

    async def startup(self):
        await self._redis.connect()
        logger.info("FeedbackLoopService started")

    async def shutdown(self):
        await self._redis.disconnect()
        logger.info("FeedbackLoopService stopped")

    # ── DB helpers ────────────────────────────────────────────────────────────
    def _db(self) -> Session:
        return SessionLocal()

    # ── Feedback ──────────────────────────────────────────────────────────────
    def collect_feedback(self, req: FeedbackRequest) -> Dict[str, Any]:
        sentiment_result = (
            self._sentiment.analyze(req.content)
            if req.content else {"label": "neutral", "score": 0.0, "provider": "none"}
        )
        fb_id = f"fb_{uuid.uuid4().hex}"
        row   = FeedbackModel(
            feedback_id   = fb_id,
            user_id       = req.user_id,
            session_id    = req.session_id,
            feedback_type = req.feedback_type,
            content       = req.content,
            rating        = req.rating,
            nps_score     = req.nps_score,
            sentiment     = sentiment_result["label"],
            sentiment_score= sentiment_result["score"],
            source        = req.source,
            context_data  = req.context,
            extra_metadata= req.metadata,
        )
        with self._db() as db:
            db.add(row)
            db.commit()
            db.refresh(row)
        if FEEDBACKS_RX:
            try: FEEDBACKS_RX.labels(type=req.feedback_type, sentiment=sentiment_result["label"]).inc()
            except Exception: pass
        return {
            "feedback_id": fb_id,
            "sentiment": sentiment_result,
            "created_at": _fmt(_now()),
        }

    def list_feedbacks(
        self,
        user_id: Optional[str] = None,
        feedback_type: Optional[str] = None,
        sentiment: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Dict[str, Any]:
        with self._db() as db:
            q = db.query(FeedbackModel)
            if user_id:        q = q.filter(FeedbackModel.user_id == user_id)
            if feedback_type:  q = q.filter(FeedbackModel.feedback_type == feedback_type)
            if sentiment:      q = q.filter(FeedbackModel.sentiment == sentiment)
            total = q.count()
            rows  = q.order_by(FeedbackModel.created_at.desc()).offset(skip).limit(limit).all()
        return {
            "total": total,
            "feedbacks": [_fb_to_dict(r) for r in rows],
        }

    def get_feedback(self, feedback_id: str) -> Optional[Dict]:
        with self._db() as db:
            row = db.query(FeedbackModel).filter(FeedbackModel.feedback_id == feedback_id).first()
        return _fb_to_dict(row) if row else None

    # ── Tracking Events ───────────────────────────────────────────────────────
    def track_event(self, req: TrackingEventRequest) -> Dict[str, Any]:
        evt_id = f"evt_{uuid.uuid4().hex}"
        ts     = req.timestamp or _now()
        row    = TrackingEventModel(
            event_id          = evt_id,
            user_id           = req.user_id,
            session_id        = req.session_id,
            event_type        = req.event_type,
            event_data        = req.event_data,
            page_url          = req.page_url,
            referrer          = req.referrer,
            device_info       = req.device_info,
            product_id        = req.product_id,
            order_id          = req.order_id,
            recommendation_id = req.recommendation_id,
            extra_metadata    = req.metadata,
            created_at        = _naive(ts),
        )
        with self._db() as db:
            db.add(row)
            db.commit()
        if EVENTS_RX:
            try: EVENTS_RX.labels(event_type=req.event_type).inc()
            except Exception: pass
        return {"event_id": evt_id, "created_at": _fmt(ts)}

    def list_events(
        self,
        user_id: Optional[str] = None,
        event_type: Optional[str] = None,
        product_id: Optional[str] = None,
        skip: int = 0, limit: int = 100,
    ) -> Dict[str, Any]:
        with self._db() as db:
            q = db.query(TrackingEventModel)
            if user_id:    q = q.filter(TrackingEventModel.user_id == user_id)
            if event_type: q = q.filter(TrackingEventModel.event_type == event_type)
            if product_id: q = q.filter(TrackingEventModel.product_id == product_id)
            total = q.count()
            rows  = q.order_by(TrackingEventModel.created_at.desc()).offset(skip).limit(limit).all()
        return {"total": total, "events": [_evt_to_dict(r) for r in rows]}

    # ── Experiments ───────────────────────────────────────────────────────────
    def create_experiment(self, req: ExperimentRequest) -> Dict[str, Any]:
        exp_id = f"exp_{uuid.uuid4().hex[:12]}"
        row    = ExperimentModel(
            experiment_id     = exp_id,
            experiment_name   = req.experiment_name,
            experiment_type   = req.experiment_type,
            description       = req.description,
            status            = ExperimentStatus.DRAFT.value,
            variants_config   = req.variants,
            target_metric     = req.target_metric,
            secondary_metrics = req.secondary_metrics,
            traffic_percentage= req.traffic_percentage,
            allocation_method = req.allocation_method,
            target_sample_size= req.target_sample_size,
            min_sample_size   = req.min_sample_size,
            max_duration_days = req.max_duration_days,
            audience_filters  = req.audience_filters,
            extra_metadata    = req.metadata,
            results           = {v["variant_id"]: {"n": 0, "mean": 0.0, "std": 0.0,
                                                     "sum": 0.0, "conversions": 0}
                                  for v in req.variants},
            bandit_weights    = {v["variant_id"]: 1.0 / len(req.variants) for v in req.variants},
        )
        with self._db() as db:
            db.add(row)
            db.commit()
            db.refresh(row)
        return {"experiment_id": exp_id, "status": ExperimentStatus.DRAFT.value,
                "created_at": _fmt(_now())}

    def start_experiment(self, experiment_id: str) -> Dict[str, Any]:
        with self._db() as db:
            row = db.query(ExperimentModel).filter(
                ExperimentModel.experiment_id == experiment_id).first()
            if not row: raise HTTPException(404, "Experiment not found")
            if row.status not in (ExperimentStatus.DRAFT.value, ExperimentStatus.PAUSED.value):
                raise HTTPException(400, f"Cannot start from status {row.status}")
            row.status     = ExperimentStatus.ACTIVE.value
            row.started_at = _naive(_now())
            db.commit()
        if EXPERIMENTS_ACTIVE:
            try: EXPERIMENTS_ACTIVE.inc()
            except Exception: pass
        return {"experiment_id": experiment_id, "status": ExperimentStatus.ACTIVE.value}

    def pause_experiment(self, experiment_id: str) -> Dict[str, Any]:
        with self._db() as db:
            row = db.query(ExperimentModel).filter(
                ExperimentModel.experiment_id == experiment_id).first()
            if not row: raise HTTPException(404, "Experiment not found")
            row.status = ExperimentStatus.PAUSED.value
            db.commit()
        return {"experiment_id": experiment_id, "status": ExperimentStatus.PAUSED.value}

    def stop_experiment(self, experiment_id: str) -> Dict[str, Any]:
        with self._db() as db:
            row = db.query(ExperimentModel).filter(
                ExperimentModel.experiment_id == experiment_id).first()
            if not row: raise HTTPException(404, "Experiment not found")
            row.status   = ExperimentStatus.COMPLETED.value
            row.ended_at = _naive(_now())
            # Run analysis before closing
            analysis = self._ab.analyze(row)
            row.results["-analysis"] = analysis
            row.winner_variant = analysis.get("winner")
            if analysis.get("comparisons"):
                p_vals = [c.get("p_value", 1.0) for c in analysis["comparisons"].values()]
                row.significance = min(p_vals) if p_vals else None
            db.commit()
        if EXPERIMENTS_ACTIVE:
            try: EXPERIMENTS_ACTIVE.dec()
            except Exception: pass
        return {"experiment_id": experiment_id, "status": ExperimentStatus.COMPLETED.value,
                "analysis": analysis}

    def assign_variant(self, experiment_id: str, user_id: str) -> Dict[str, Any]:
        with self._db() as db:
            exp = db.query(ExperimentModel).filter(
                ExperimentModel.experiment_id == experiment_id).first()
            if not exp: raise HTTPException(404, "Experiment not found")
            if exp.status != ExperimentStatus.ACTIVE.value:
                raise HTTPException(400, "Experiment is not active")

            # Check existing assignment
            existing = db.query(ExperimentAssignmentModel).filter(
                ExperimentAssignmentModel.experiment_id == experiment_id,
                ExperimentAssignmentModel.user_id       == user_id,
            ).first()
            if existing:
                return {"variant_id": existing.variant_id, "existing": True}

            # Traffic gate
            traffic_gate = int(hashlib.md5(f"traffic:{user_id}:{experiment_id}".encode()).hexdigest(), 16) % 100
            if traffic_gate >= exp.traffic_percentage:
                return {"variant_id": None, "in_experiment": False}

            variant_id = self._ab.assign_variant(user_id, exp)
            asgn = ExperimentAssignmentModel(
                assignment_id = f"asgn_{uuid.uuid4().hex}",
                experiment_id = experiment_id,
                user_id       = user_id,
                variant_id    = variant_id,
            )
            db.add(asgn)
            db.commit()
        return {"variant_id": variant_id, "in_experiment": True, "existing": False}

    def record_experiment_event(self, req: ExperimentEventRequest) -> Dict[str, Any]:
        with self._db() as db:
            exp = db.query(ExperimentModel).filter(
                ExperimentModel.experiment_id == req.experiment_id).first()
            if not exp: raise HTTPException(404, "Experiment not found")
            if exp.status != ExperimentStatus.ACTIVE.value:
                raise HTTPException(400, "Experiment is not active")

            results = dict(exp.results or {})
            vr      = results.setdefault(req.variant, {"n": 0, "mean": 0.0,
                                                         "std": 0.0, "sum": 0.0, "conversions": 0})
            n       = vr["n"] + 1
            old_mean= vr["mean"]
            new_mean= old_mean + (req.value - old_mean) / n  # Welford online mean
            vr.update({"n": n, "mean": round(new_mean, 6), "sum": vr["sum"] + req.value})
            if req.metric == "conversion" and req.value > 0:
                vr["conversions"] = vr.get("conversions", 0) + 1

            # Update bandit weights (UCB)
            if exp.experiment_type == ExperimentType.BANDIT.value:
                n_total = sum(r.get("n", 0) for r in results.values()) + 1
                weights = {}
                for vid, vdata in results.items():
                    ni  = max(vdata.get("n", 0), 1)
                    mui = vdata.get("mean", 0.5)
                    weights[vid] = mui + math.sqrt(2.0 * math.log(n_total) / ni)
                w_sum = sum(weights.values()) or 1.0
                exp.bandit_weights = {vid: round(w/w_sum, 4) for vid, w in weights.items()}

            exp.results = results
            db.commit()

            # Update assignment events
            asgn = db.query(ExperimentAssignmentModel).filter(
                ExperimentAssignmentModel.experiment_id == req.experiment_id,
                ExperimentAssignmentModel.user_id       == req.user_id,
            ).first()
            if asgn:
                events = list(asgn.events or [])
                events.append({"metric": req.metric, "value": req.value,
                                "ts": _fmt(_now()), "metadata": req.metadata})
                asgn.events = events
                db.commit()

        return {"recorded": True, "variant": req.variant, "metric": req.metric,
                "value": req.value, "new_n": n, "new_mean": round(new_mean, 6)}

    def analyze_experiment(self, experiment_id: str) -> Dict[str, Any]:
        with self._db() as db:
            exp = db.query(ExperimentModel).filter(
                ExperimentModel.experiment_id == experiment_id).first()
            if not exp: raise HTTPException(404, "Experiment not found")
            analysis = self._ab.analyze(exp)
            # Persist analysis
            results = dict(exp.results or {})
            results["-analysis"] = analysis
            exp.results = results
            db.commit()
        return {"experiment_id": experiment_id, **analysis}

    def list_experiments(
        self,
        status: Optional[str] = None,
        skip: int = 0, limit: int = 20,
    ) -> Dict[str, Any]:
        with self._db() as db:
            q = db.query(ExperimentModel)
            if status: q = q.filter(ExperimentModel.status == status)
            total = q.count()
            rows  = q.order_by(ExperimentModel.created_at.desc()).offset(skip).limit(limit).all()
        return {"total": total, "experiments": [_exp_to_dict(r) for r in rows]}

    # ── Models / MLOps ────────────────────────────────────────────────────────
    def train_model(self, req: ModelTrainingRequest) -> Dict[str, Any]:
        model_id = f"mdl_{uuid.uuid4().hex[:12]}"
        version  = f"v{int(_now().timestamp()) % 100000}"

        # In real use, data would come from the data store; here we accept inline data
        data      = req.training_data
        tr_result = self._trainer.train(req, data)

        row = ModelModel(
            model_id           = model_id,
            model_name         = req.model_name,
            version            = version,
            algorithm          = req.algorithm,
            stage              = ModelStage.DEVELOPMENT.value,
            features           = req.features,
            target             = req.target,
            hyperparameters    = req.hyperparameters,
            training_metrics   = tr_result.get("training_metrics", {}),
            validation_metrics = tr_result.get("training_metrics", {}),
            cross_val_scores   = tr_result.get("cv_scores", []),
            artifact_path      = tr_result.get("artifact_path"),
            mlflow_run_id      = tr_result.get("mlflow_run_id"),
            extra_metadata     = req.metadata,
        )
        with self._db() as db:
            db.add(row)
            db.commit()
            db.refresh(row)
        if MODELS_TRAINED:
            try: MODELS_TRAINED.labels(algorithm=req.algorithm, stage=ModelStage.DEVELOPMENT.value).inc()
            except Exception: pass
        return {"model_id": model_id, "version": version, **tr_result}

    def deploy_model(self, req: ModelDeployRequest) -> Dict[str, Any]:
        with self._db() as db:
            mdl = db.query(ModelModel).filter(ModelModel.model_id == req.model_id).first()
            if not mdl: raise HTTPException(404, "Model not found")

            # Promote stage (use_enum_values=True means req.stage is already a str)
            req_stage    = req.stage if isinstance(req.stage, str) else req.stage.value
            req_strategy = req.strategy if isinstance(req.strategy, str) else req.strategy.value
            old_stage    = mdl.stage
            mdl.stage    = req_stage
            mdl.updated_at = _naive(_now())

            dep = ModelDeploymentModel(
                deployment_id      = f"dep_{uuid.uuid4().hex[:12]}",
                model_id           = req.model_id,
                strategy           = req_strategy,
                stage              = req_stage,
                traffic_percentage = req.traffic_percentage,
                monitoring_metrics = req.monitoring_metrics,
                rollback_threshold = req.rollback_threshold,
                extra_metadata     = req.metadata,
            )
            db.add(dep)
            db.commit()
            db.refresh(dep)
        return {
            "deployment_id": dep.deployment_id,
            "model_id": req.model_id,
            "from_stage": old_stage,
            "to_stage": req_stage,
            "strategy": req_strategy,
            "traffic_percentage": req.traffic_percentage,
        }

    def promote_model(self, model_id: str, to_stage: str) -> Dict[str, Any]:
        """Promote model through dev→staging→production."""
        valid = [s.value for s in ModelStage]
        if to_stage not in valid:
            raise HTTPException(400, f"Invalid stage: {to_stage}")
        with self._db() as db:
            mdl = db.query(ModelModel).filter(ModelModel.model_id == model_id).first()
            if not mdl: raise HTTPException(404, "Model not found")
            old_stage  = mdl.stage
            mdl.stage  = to_stage
            mdl.updated_at = _naive(_now())
            db.commit()
        return {"model_id": model_id, "from_stage": old_stage, "to_stage": to_stage}

    def list_models(
        self,
        algorithm: Optional[str] = None,
        stage: Optional[str] = None,
        skip: int = 0, limit: int = 20,
    ) -> Dict[str, Any]:
        with self._db() as db:
            q = db.query(ModelModel)
            if algorithm: q = q.filter(ModelModel.algorithm == algorithm)
            if stage:     q = q.filter(ModelModel.stage == stage)
            total = q.count()
            rows  = q.order_by(ModelModel.created_at.desc()).offset(skip).limit(limit).all()
        return {"total": total, "models": [_mdl_to_dict(r) for r in rows]}

    def get_model(self, model_id: str) -> Optional[Dict]:
        with self._db() as db:
            row = db.query(ModelModel).filter(ModelModel.model_id == model_id).first()
        return _mdl_to_dict(row) if row else None

    def list_deployments(self, model_id: Optional[str] = None) -> Dict[str, Any]:
        with self._db() as db:
            q = db.query(ModelDeploymentModel)
            if model_id: q = q.filter(ModelDeploymentModel.model_id == model_id)
            rows = q.order_by(ModelDeploymentModel.deployed_at.desc()).limit(50).all()
        return {"deployments": [_dep_to_dict(r) for r in rows]}

    # ── Stats ─────────────────────────────────────────────────────────────────
    def stats(self) -> Dict[str, Any]:
        with self._db() as db:
            fb_total  = db.query(FeedbackModel).count()
            evt_total = db.query(TrackingEventModel).count()
            exp_active= db.query(ExperimentModel).filter(
                ExperimentModel.status == ExperimentStatus.ACTIVE.value).count()
            mdl_prod  = db.query(ModelModel).filter(
                ModelModel.stage == ModelStage.PRODUCTION.value).count()
        return {
            "feedbacks_total": fb_total,
            "events_total":    evt_total,
            "experiments_active": exp_active,
            "models_in_production": mdl_prod,
        }


# ── Serialisation helpers ─────────────────────────────────────────────────────
def _fb_to_dict(r: FeedbackModel) -> Dict:
    return {
        "feedback_id":   r.feedback_id,
        "user_id":       r.user_id,
        "session_id":    r.session_id,
        "feedback_type": r.feedback_type,
        "content":       r.content,
        "rating":        r.rating,
        "nps_score":     r.nps_score,
        "sentiment":     r.sentiment,
        "sentiment_score": r.sentiment_score,
        "source":        r.source,
        "is_processed":  r.is_processed,
        "followup_sent": r.followup_sent,
        "created_at":    _fmt(_utc(r.created_at)),
    }

def _evt_to_dict(r: TrackingEventModel) -> Dict:
    return {
        "event_id":   r.event_id,
        "user_id":    r.user_id,
        "session_id": r.session_id,
        "event_type": r.event_type,
        "event_data": r.event_data,
        "page_url":   r.page_url,
        "product_id": r.product_id,
        "order_id":   r.order_id,
        "created_at": _fmt(_utc(r.created_at)),
    }

def _exp_to_dict(r: ExperimentModel) -> Dict:
    return {
        "experiment_id":    r.experiment_id,
        "experiment_name":  r.experiment_name,
        "experiment_type":  r.experiment_type,
        "status":           r.status,
        "variants":         r.variants_config,
        "target_metric":    r.target_metric,
        "traffic_percentage": r.traffic_percentage,
        "allocation_method": r.allocation_method,
        "results":          r.results,
        "winner_variant":   r.winner_variant,
        "started_at":       _fmt(_utc(r.started_at)),
        "ended_at":         _fmt(_utc(r.ended_at)),
        "created_at":       _fmt(_utc(r.created_at)),
    }

def _mdl_to_dict(r: ModelModel) -> Dict:
    return {
        "model_id":          r.model_id,
        "model_name":        r.model_name,
        "version":           r.version,
        "algorithm":         r.algorithm,
        "stage":             r.stage,
        "features":          r.features,
        "target":            r.target,
        "training_metrics":  r.training_metrics,
        "cross_val_scores":  r.cross_val_scores,
        "artifact_path":     r.artifact_path,
        "trained_at":        _fmt(_utc(r.trained_at)),
        "created_at":        _fmt(_utc(r.created_at)),
    }

def _dep_to_dict(r: ModelDeploymentModel) -> Dict:
    return {
        "deployment_id":     r.deployment_id,
        "model_id":          r.model_id,
        "strategy":          r.strategy,
        "stage":             r.stage,
        "traffic_percentage":r.traffic_percentage,
        "is_active":         r.is_active,
        "deployed_at":       _fmt(_utc(r.deployed_at)),
    }


# ══════════════════════════════════════════════════════════════════════════════
# FASTAPI APP
# ══════════════════════════════════════════════════════════════════════════════
_cfg = ServiceConfig()
_svc: Optional[FeedbackLoopService] = None


def get_svc() -> FeedbackLoopService:
    global _svc
    if _svc is None:
        _svc = FeedbackLoopService(_cfg)
    return _svc


def create_app() -> FastAPI:
    app = FastAPI(
        title="ILbuy Feedback & Optimization Flywheel",
        version="1.0.0",
        description="Part 9: Feedback loop, A/B testing, model training and MLOps",
    )

    @app.on_event("startup")
    async def startup():
        global _svc
        _svc = FeedbackLoopService(_cfg)
        await _svc.startup()
        seed_data()
        asyncio.create_task(_bg_feedback_processor())
        asyncio.create_task(_bg_experiment_monitor())
        asyncio.create_task(_bg_model_monitor())

    @app.on_event("shutdown")
    async def shutdown():
        if _svc: await _svc.shutdown()

    # ── Health ────────────────────────────────────────────────────────────────
    @app.get("/health")
    async def health():
        return {"status": "healthy", "service": "feedback_loop_service", "ts": _fmt(_now())}

    @app.get("/api/v1/feedback/stats")
    async def fl_stats(svc: FeedbackLoopService = Depends(get_svc)):
        return svc.stats()

    # ── Feedback ──────────────────────────────────────────────────────────────
    @app.post("/api/v1/feedback", status_code=201)
    async def create_feedback(
        req: FeedbackRequest,
        bg: BackgroundTasks,
        svc: FeedbackLoopService = Depends(get_svc),
    ):
        result = svc.collect_feedback(req)
        # Trigger follow-up survey if rating below threshold
        if req.rating is not None and req.rating < _cfg.satisfaction_threshold:
            bg.add_task(_send_followup_survey, req.user_id, req.session_id, result["feedback_id"])
        return result

    @app.get("/api/v1/feedback")
    async def list_feedbacks(
        user_id: Optional[str]  = Query(None),
        feedback_type: Optional[str] = Query(None),
        sentiment: Optional[str]= Query(None),
        skip: int = Query(0, ge=0),
        limit: int = Query(50, ge=1, le=500),
        svc: FeedbackLoopService = Depends(get_svc),
    ):
        return svc.list_feedbacks(user_id=user_id, feedback_type=feedback_type,
                                  sentiment=sentiment, skip=skip, limit=limit)

    @app.get("/api/v1/feedback/{feedback_id}")
    async def get_feedback(feedback_id: str, svc: FeedbackLoopService = Depends(get_svc)):
        item = svc.get_feedback(feedback_id)
        if not item: raise HTTPException(404, "Feedback not found")
        return item

    # ── Tracking Events ───────────────────────────────────────────────────────
    @app.post("/api/v1/events", status_code=201)
    async def track_event(req: TrackingEventRequest, svc: FeedbackLoopService = Depends(get_svc)):
        return svc.track_event(req)

    @app.get("/api/v1/events")
    async def list_events(
        user_id: Optional[str]    = Query(None),
        event_type: Optional[str] = Query(None),
        product_id: Optional[str] = Query(None),
        skip: int  = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=1000),
        svc: FeedbackLoopService  = Depends(get_svc),
    ):
        return svc.list_events(user_id=user_id, event_type=event_type,
                               product_id=product_id, skip=skip, limit=limit)

    # ── Experiments ───────────────────────────────────────────────────────────
    @app.post("/api/v1/experiments", status_code=201)
    async def create_experiment(req: ExperimentRequest, svc: FeedbackLoopService = Depends(get_svc)):
        return svc.create_experiment(req)

    @app.get("/api/v1/experiments")
    async def list_experiments(
        status: Optional[str] = Query(None),
        skip: int  = Query(0, ge=0),
        limit: int = Query(20, ge=1, le=100),
        svc: FeedbackLoopService = Depends(get_svc),
    ):
        return svc.list_experiments(status=status, skip=skip, limit=limit)

    @app.post("/api/v1/experiments/{experiment_id}/start")
    async def start_experiment(experiment_id: str, svc: FeedbackLoopService = Depends(get_svc)):
        return svc.start_experiment(experiment_id)

    @app.post("/api/v1/experiments/{experiment_id}/pause")
    async def pause_experiment(experiment_id: str, svc: FeedbackLoopService = Depends(get_svc)):
        return svc.pause_experiment(experiment_id)

    @app.post("/api/v1/experiments/{experiment_id}/stop")
    async def stop_experiment(experiment_id: str, svc: FeedbackLoopService = Depends(get_svc)):
        return svc.stop_experiment(experiment_id)

    @app.post("/api/v1/experiments/{experiment_id}/assign")
    async def assign_variant(
        experiment_id: str,
        user_id: str = Query(...),
        svc: FeedbackLoopService = Depends(get_svc),
    ):
        return svc.assign_variant(experiment_id, user_id)

    @app.post("/api/v1/experiments/events")
    async def record_experiment_event(
        req: ExperimentEventRequest,
        svc: FeedbackLoopService = Depends(get_svc),
    ):
        return svc.record_experiment_event(req)

    @app.get("/api/v1/experiments/{experiment_id}/analysis")
    async def analyze_experiment(experiment_id: str, svc: FeedbackLoopService = Depends(get_svc)):
        return svc.analyze_experiment(experiment_id)

    # ── Models / MLOps ────────────────────────────────────────────────────────
    @app.post("/api/v1/models/train", status_code=201)
    async def train_model(req: ModelTrainingRequest, svc: FeedbackLoopService = Depends(get_svc)):
        return svc.train_model(req)

    @app.post("/api/v1/models/deploy", status_code=201)
    async def deploy_model(req: ModelDeployRequest, svc: FeedbackLoopService = Depends(get_svc)):
        return svc.deploy_model(req)

    @app.post("/api/v1/models/{model_id}/promote")
    async def promote_model(
        model_id: str,
        to_stage: str = Query(...),
        svc: FeedbackLoopService = Depends(get_svc),
    ):
        return svc.promote_model(model_id, to_stage)

    @app.get("/api/v1/models")
    async def list_models(
        algorithm: Optional[str] = Query(None),
        stage: Optional[str]     = Query(None),
        skip: int  = Query(0, ge=0),
        limit: int = Query(20, ge=1, le=100),
        svc: FeedbackLoopService = Depends(get_svc),
    ):
        return svc.list_models(algorithm=algorithm, stage=stage, skip=skip, limit=limit)

    @app.get("/api/v1/models/{model_id}")
    async def get_model(model_id: str, svc: FeedbackLoopService = Depends(get_svc)):
        item = svc.get_model(model_id)
        if not item: raise HTTPException(404, "Model not found")
        return item

    @app.get("/api/v1/models/{model_id}/deployments")
    async def list_deployments(model_id: str, svc: FeedbackLoopService = Depends(get_svc)):
        return svc.list_deployments(model_id=model_id)

    # ── Metrics ───────────────────────────────────────────────────────────────
    @app.get("/metrics")
    async def metrics():
        if not _HAS_PROMETHEUS or not _FL_REG:
            return JSONResponse({"error": "prometheus not available"}, status_code=503)
        from fastapi.responses import Response
        return Response(generate_latest(_FL_REG), media_type=CONTENT_TYPE_LATEST)

    return app


# ══════════════════════════════════════════════════════════════════════════════
# BACKGROUND TASKS
# ══════════════════════════════════════════════════════════════════════════════
async def _bg_feedback_processor():
    """Process unprocessed feedback: run sentiment, trigger surveys."""
    while True:
        try:
            await asyncio.sleep(30)
            svc = get_svc()
            with svc._db() as db:
                rows = (db.query(FeedbackModel)
                          .filter(FeedbackModel.is_processed == False)  # noqa
                          .limit(50).all())
                for row in rows:
                    if row.content and not row.sentiment:
                        result = svc._sentiment.analyze(row.content)
                        row.sentiment       = result["label"]
                        row.sentiment_score = result["score"]
                    row.is_processed = True
                    row.processed_at = _naive(_now())
                db.commit()
        except Exception as e:
            logger.warning("Feedback processor error: %s", e)
        finally:
            await asyncio.sleep(30)


async def _bg_experiment_monitor():
    """Auto-stop experiments that exceed max duration."""
    while True:
        try:
            await asyncio.sleep(3600)  # every hour
            svc = get_svc()
            with svc._db() as db:
                rows = (db.query(ExperimentModel)
                          .filter(ExperimentModel.status == ExperimentStatus.ACTIVE.value)
                          .all())
                for exp in rows:
                    if not exp.started_at: continue
                    started = _utc(exp.started_at)
                    if started and (_now() - started).days >= exp.max_duration_days:
                        exp.status   = ExperimentStatus.COMPLETED.value
                        exp.ended_at = _naive(_now())
                        analysis     = svc._ab.analyze(exp)
                        results      = dict(exp.results or {})
                        results["-analysis"] = analysis
                        exp.results  = results
                        exp.winner_variant = analysis.get("winner")
                        logger.info("Auto-stopped experiment %s", exp.experiment_id)
                db.commit()
        except Exception as e:
            logger.warning("Experiment monitor error: %s", e)


async def _bg_model_monitor():
    """Log production model count periodically."""
    while True:
        try:
            await asyncio.sleep(300)
            svc = get_svc()
            with svc._db() as db:
                prod_count = (db.query(ModelModel)
                                .filter(ModelModel.stage == ModelStage.PRODUCTION.value)
                                .count())
            logger.info("Production models: %d", prod_count)
        except Exception as e:
            logger.warning("Model monitor error: %s", e)


async def _send_followup_survey(user_id: str, session_id: str, feedback_id: str):
    """Async follow-up survey trigger (stub: log + optional HTTP call)."""
    logger.info("Follow-up survey triggered: user=%s, fb=%s", user_id, feedback_id)
    if _HAS_AIOHTTP and _cfg.notification_svc_url:
        try:
            async with aiohttp.ClientSession() as session:
                await session.post(
                    f"{_cfg.notification_svc_url}/api/v1/notify",
                    json={"user_id": user_id, "type": "survey", "feedback_id": feedback_id},
                    timeout=aiohttp.ClientTimeout(total=5),
                )
        except Exception as e:
            logger.debug("Followup notify failed: %s", e)


# ══════════════════════════════════════════════════════════════════════════════
# SEED DATA
# ══════════════════════════════════════════════════════════════════════════════
def seed_data():
    """Insert demo experiments and a sample model if DB is empty."""
    with SessionLocal() as db:
        if db.query(ExperimentModel).count() > 0:
            return

    # Experiment 1 — search ranking A/B test
    svc = get_svc()
    try:
        svc.create_experiment(ExperimentRequest(
            experiment_name   = "search_ranking_test",
            experiment_type   = ExperimentType.AB_TEST,
            description       = "Compare BM25 vs neural ranking for search results",
            variants          = [
                {"variant_id": "control",  "name": "BM25 ranking", "is_control": True,
                 "config": {"algorithm": "bm25"}},
                {"variant_id": "treatment","name": "Neural ranking","is_control": False,
                 "config": {"algorithm": "neural_v1"}},
            ],
            target_metric     = "conversion_rate",
            secondary_metrics = ["click_through_rate", "avg_session_time"],
            traffic_percentage= 20.0,
            min_sample_size   = 200,
            max_duration_days = 14,
        ))
    except Exception as e:
        logger.warning("seed exp1 failed: %s", e)

    # Experiment 2 — recommendation bandit
    try:
        svc.create_experiment(ExperimentRequest(
            experiment_name   = "recommendation_bandit",
            experiment_type   = ExperimentType.BANDIT,
            description       = "UCB bandit to select best recommendation strategy",
            variants          = [
                {"variant_id": "collab_filter",  "name": "Collaborative Filtering", "is_control": True},
                {"variant_id": "content_based",  "name": "Content-Based"},
                {"variant_id": "hybrid",          "name": "Hybrid Model"},
            ],
            target_metric     = "click_through_rate",
            traffic_percentage= 50.0,
            allocation_method = "bandit",
            min_sample_size   = 100,
            max_duration_days = 21,
        ))
    except Exception as e:
        logger.warning("seed exp2 failed: %s", e)

    # Experiment 3 — UI pricing display
    try:
        svc.create_experiment(ExperimentRequest(
            experiment_name   = "pricing_display_test",
            experiment_type   = ExperimentType.MULTI_VARIANT,
            description       = "Test 3 pricing display formats",
            variants          = [
                {"variant_id": "v_list",     "name": "List price",    "is_control": True},
                {"variant_id": "v_monthly",  "name": "Monthly price", "is_control": False},
                {"variant_id": "v_annual",   "name": "Annual saving", "is_control": False},
            ],
            target_metric     = "purchase_rate",
            traffic_percentage= 100.0,
            min_sample_size   = 150,
        ))
    except Exception as e:
        logger.warning("seed exp3 failed: %s", e)

    # Seed demo model
    try:
        svc.train_model(ModelTrainingRequest(
            model_name    = "churn_predictor_v1",
            algorithm     = ModelAlgorithm.RANDOM_FOREST,
            features      = ["avg_rating", "total_orders", "days_since_last_order",
                             "avg_session_time", "nps_score"],
            target        = "churned",
            training_data = {
                "X": [[4.5, 12, 5, 300, 8], [2.1, 2, 60, 90, 3], [3.8, 7, 15, 200, 7],
                      [1.5, 1, 90, 45, 2], [4.9, 25, 2, 450, 10]],
                "y": [0, 1, 0, 1, 0],
            },
            hyperparameters= {"n_estimators": 50},
            cross_validation= False,
            metadata       = {"purpose": "demo"},
        ))
    except Exception as e:
        logger.warning("seed model failed: %s", e)

    logger.info("Seed data inserted")


# ══════════════════════════════════════════════════════════════════════════════
# ENTRYPOINT
# ══════════════════════════════════════════════════════════════════════════════
app = create_app()

if __name__ == "__main__":
    try:
        import uvicorn
        uvicorn.run(
            "feedback_loop_service:app",
            host=_cfg.host,
            port=_cfg.port,
            reload=_cfg.debug,
            log_level="info",
        )
    except ImportError:
        logger.error("uvicorn not installed. Run: pip install uvicorn")

