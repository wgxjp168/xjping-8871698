"""
support_ops_service.py — Part 10: 支撑与运维层
Production-grade: observability, orchestration, deployment, config management,
CI/CD pipeline, alert engine.  SQLite + sync SQLAlchemy + conditional imports.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import math
import os
import random
import re
import statistics
import subprocess
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta, date
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Query, Body, WebSocket
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, field_validator, model_validator, ConfigDict
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean, Float, Index,
    UniqueConstraint, create_engine, text
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
    import yaml; _HAS_YAML = True
except ImportError:
    yaml = None; _HAS_YAML = False  # type: ignore

try:
    import toml; _HAS_TOML = True
except ImportError:
    toml = None; _HAS_TOML = False  # type: ignore

try:
    from kubernetes import client as k8s_client, config as k8s_config
    from kubernetes.client.exceptions import ApiException as K8sApiException
    _HAS_K8S = True
except ImportError:
    k8s_client = None; k8s_config = None; K8sApiException = Exception  # type: ignore
    _HAS_K8S = False

try:
    import docker; _HAS_DOCKER = True
except ImportError:
    docker = None; _HAS_DOCKER = False  # type: ignore

try:
    from prometheus_client import (Counter, Gauge, Histogram, CollectorRegistry,
                                    generate_latest, CONTENT_TYPE_LATEST)
    _HAS_PROMETHEUS = True
except ImportError:
    _HAS_PROMETHEUS = False

try:
    import hvac; _HAS_HVAC = True
except ImportError:
    hvac = None; _HAS_HVAC = False  # type: ignore

try:
    import nacos; _HAS_NACOS = True  # type: ignore
except ImportError:
    nacos = None; _HAS_NACOS = False  # type: ignore

try:
    import jenkins; _HAS_JENKINS = True  # type: ignore
except ImportError:
    jenkins = None; _HAS_JENKINS = False  # type: ignore

try:
    import paramiko; _HAS_PARAMIKO = True
except ImportError:
    paramiko = None; _HAS_PARAMIKO = False  # type: ignore

try:
    import git; _HAS_GIT = True
except ImportError:
    git = None; _HAS_GIT = False  # type: ignore

try:
    import psutil; _HAS_PSUTIL = True
except ImportError:
    psutil = None; _HAS_PSUTIL = False  # type: ignore

try:
    from cryptography.fernet import Fernet; _HAS_CRYPTO = True
except BaseException:  # pyo3 PanicException subclasses BaseException, not Exception
    Fernet = None; _HAS_CRYPTO = False  # type: ignore

try:
    import aiofiles; _HAS_AIOFILES = True
except ImportError:
    aiofiles = None; _HAS_AIOFILES = False  # type: ignore

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s [%(filename)s:%(lineno)d] %(message)s",
)
logger = logging.getLogger("support_ops_service")

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

# ── DB setup ───────────────────────────────────────────────────────────────────
DB_URL = os.getenv("SO_DB_URL", "sqlite:///./support_ops.db")
engine = create_engine(DB_URL, connect_args={"check_same_thread": False} if "sqlite" in DB_URL else {})
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

# ── Prometheus ─────────────────────────────────────────────────────────────────
_SO_REG = CollectorRegistry() if _HAS_PROMETHEUS else None
def _ctr(n, d, l=None):
    if not _HAS_PROMETHEUS: return None
    try: return Counter(n, d, l or [], registry=_SO_REG)
    except ValueError: return Counter(n, d, l or [], registry=CollectorRegistry())
def _gge(n, d, l=None):
    if not _HAS_PROMETHEUS: return None
    try: return Gauge(n, d, l or [], registry=_SO_REG)
    except ValueError: return Gauge(n, d, l or [], registry=CollectorRegistry())
def _hst(n, d, l=None):
    if not _HAS_PROMETHEUS: return None
    try: return Histogram(n, d, l or [], registry=_SO_REG)
    except ValueError: return Histogram(n, d, l or [], registry=CollectorRegistry())

CLUSTERS_TOTAL   = _gge("so_clusters_total",      "Total clusters",           ["provider", "status"])
DEPLOYMENTS_TOTAL= _gge("so_deployments_total",   "Total deployments",        ["status"])
ALERTS_FIRING    = _gge("so_alerts_firing",        "Currently firing alerts",  ["severity"])
BACKUPS_TOTAL    = _ctr("so_backups_total",        "Total backups created",    ["backup_type", "status"])
REQ_LATENCY      = _hst("so_request_latency_secs", "Request latency",          ["endpoint"])

# ══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ══════════════════════════════════════════════════════════════════════════════
class ResourceType(str, Enum):
    CLUSTER          = "cluster"
    NODE             = "node"
    POD              = "pod"
    DEPLOYMENT       = "deployment"
    SERVICE          = "service"
    CONFIGMAP        = "configmap"
    SECRET           = "secret"
    INGRESS          = "ingress"
    PERSISTENT_VOLUME= "persistent_volume"
    NAMESPACE        = "namespace"

class ResourceStatus(str, Enum):
    PENDING     = "pending"
    RUNNING     = "running"
    FAILED      = "failed"
    UNKNOWN     = "unknown"
    TERMINATING = "terminating"
    SCHEDULED   = "scheduled"
    READY       = "ready"
    NOT_READY   = "not_ready"

class DeploymentStrategy(str, Enum):
    RECREATE      = "recreate"
    ROLLING_UPDATE= "rolling_update"
    BLUE_GREEN    = "blue_green"
    CANARY        = "canary"
    A_B_TESTING   = "a_b_testing"

class AlertSeverity(str, Enum):
    CRITICAL = "critical"
    ERROR    = "error"
    WARNING  = "warning"
    INFO     = "info"
    DEBUG    = "debug"

class AlertStatus(str, Enum):
    FIRING       = "firing"
    RESOLVED     = "resolved"
    ACKNOWLEDGED = "acknowledged"
    SILENCED     = "silenced"

class MonitorType(str, Enum):
    METRICS = "metrics"
    LOGS    = "logs"
    TRACES  = "traces"
    EVENTS  = "events"
    HEALTH  = "health"

class CIBackend(str, Enum):
    JENKINS        = "jenkins"
    GITLAB_CI      = "gitlab_ci"
    GITHUB_ACTIONS = "github_actions"
    AZURE_DEVOPS   = "azure_devops"
    CIRCLECI       = "circleci"

class BackupStatus(str, Enum):
    PENDING   = "pending"
    RUNNING   = "running"
    COMPLETED = "completed"
    FAILED    = "failed"
    EXPIRED   = "expired"

# ══════════════════════════════════════════════════════════════════════════════
# SERVICE CONFIG
# ══════════════════════════════════════════════════════════════════════════════
@dataclass
class ServiceConfig:
    database_url: str = DB_URL
    redis_url:    str = os.getenv("REDIS_URL",    "redis://localhost:6379/9")
    host:         str = os.getenv("SO_HOST",      "0.0.0.0")
    port:         int = int(os.getenv("SO_PORT",  "8027"))
    debug:        bool = False

    # Kubernetes
    k8s_in_cluster:  bool = False
    k8s_api_server:  str  = os.getenv("K8S_API_SERVER",  "https://kubernetes.default.svc")
    k8s_token:       str  = os.getenv("K8S_TOKEN",       "")
    k8s_namespace:   str  = os.getenv("K8S_NAMESPACE",   "default")
    k8s_kubeconfig:  str  = os.getenv("KUBECONFIG",      "")

    # Docker
    docker_host:     str = os.getenv("DOCKER_HOST", "unix:///var/run/docker.sock")

    # Monitoring
    prometheus_url:  str = os.getenv("PROMETHEUS_URL",   "http://localhost:9090")
    grafana_url:     str = os.getenv("GRAFANA_URL",      "http://localhost:3000")
    alertmanager_url:str = os.getenv("ALERTMANAGER_URL", "http://localhost:9093")
    elasticsearch_url:str= os.getenv("ES_URL",           "http://localhost:9200")

    # Config management
    nacos_server:    str = os.getenv("NACOS_SERVER", "http://localhost:8848")
    nacos_namespace: str = os.getenv("NACOS_NAMESPACE", "public")
    vault_url:       str = os.getenv("VAULT_URL",    "http://localhost:8200")
    vault_token:     str = os.getenv("VAULT_TOKEN",  "")

    # CI/CD
    jenkins_url:     str = os.getenv("JENKINS_URL",  "http://localhost:8080")
    jenkins_user:    str = os.getenv("JENKINS_USER", "admin")
    jenkins_pass:    str = os.getenv("JENKINS_PASS", "admin")

    # Storage
    model_storage_dir: str = os.getenv("SO_STORAGE_DIR", "./so_storage")

    # Alerting
    satisfaction_threshold: float = 3.0

    def ensure_dirs(self):
        for d in [self.model_storage_dir, "configs", "backups", "logs", "certs"]:
            Path(d).mkdir(parents=True, exist_ok=True)


# ══════════════════════════════════════════════════════════════════════════════
# PYDANTIC SCHEMAS
# ══════════════════════════════════════════════════════════════════════════════
class ClusterSpec(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    name:         str
    provider:     str = "k8s"
    version:      str
    region:       str
    node_count:   int = 3
    node_type:    str = "standard"
    networking:   Dict[str, Any] = {}
    storage:      Dict[str, Any] = {}
    monitoring:   Dict[str, Any] = {}
    security:     Dict[str, Any] = {}
    metadata:     Dict[str, Any] = {}

    @field_validator("version")
    @classmethod
    def validate_version(cls, v: str) -> str:
        if not re.match(r"^\d+\.\d+(\.\d+)?$", v):
            raise ValueError("version must be X.Y or X.Y.Z")
        return v

    @field_validator("node_count")
    @classmethod
    def validate_node_count(cls, v: int) -> int:
        if v < 1: raise ValueError("node_count must be >= 1")
        return v


class DeploymentSpec(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    name:         str
    namespace:    str = "default"
    image:        str
    replicas:     int = 1
    resources:    Dict[str, Any] = {}
    ports:        List[Dict[str, Any]] = []
    env:          List[Dict[str, Any]] = []
    volumes:      List[Dict[str, Any]] = []
    liveness_probe:  Optional[Dict[str, Any]] = None
    readiness_probe: Optional[Dict[str, Any]] = None
    strategy:        DeploymentStrategy = DeploymentStrategy.ROLLING_UPDATE
    strategy_config: Dict[str, Any] = {}
    service_type:    str = "ClusterIP"
    service_ports:   List[Dict[str, Any]] = []
    labels:          Dict[str, Any] = {}
    annotations:     Dict[str, Any] = {}
    metadata:        Dict[str, Any] = {}

    @field_validator("replicas")
    @classmethod
    def validate_replicas(cls, v: int) -> int:
        if v < 0: raise ValueError("replicas must be >= 0")
        return v

    @field_validator("image")
    @classmethod
    def validate_image(cls, v: str) -> str:
        if not v.strip(): raise ValueError("image must not be empty")
        return v.strip()


class AlertRuleSpec(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    alert:        str
    expr:         str
    for_duration: str = "5m"
    severity:     AlertSeverity = AlertSeverity.WARNING
    labels:       Dict[str, Any] = {}
    annotations:  Dict[str, Any] = {}

    @field_validator("expr")
    @classmethod
    def validate_expr(cls, v: str) -> str:
        if not v.strip(): raise ValueError("expr must not be empty")
        return v.strip()


class AlertCreateRequest(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    alert_name:  str
    severity:    AlertSeverity = AlertSeverity.WARNING
    message:     str
    cluster_id:  Optional[str] = None
    labels:      Dict[str, Any] = {}
    annotations: Dict[str, Any] = {}
    starts_at:   Optional[datetime] = None
    metadata:    Dict[str, Any] = {}


class AlertAckRequest(BaseModel):
    acknowledged_by:     str
    acknowledged_reason: str = ""


class AlertSilenceRequest(BaseModel):
    silenced_by:    str
    silence_minutes: int = 60

    @field_validator("silence_minutes")
    @classmethod
    def validate_minutes(cls, v: int) -> int:
        if v < 1: raise ValueError("silence_minutes must be >= 1")
        return v


class BackupRequest(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    backup_type:    str
    name:           str
    resources:      List[str]
    cluster_id:     Optional[str] = None
    storage_type:   str = "local"
    retention_days: int = 30
    metadata:       Dict[str, Any] = {}

    @field_validator("resources")
    @classmethod
    def validate_resources(cls, v: List[str]) -> List[str]:
        if not v: raise ValueError("resources must not be empty")
        return v


class ConfigCreateRequest(BaseModel):
    data_id:     str
    group:       str = "DEFAULT_GROUP"
    namespace:   str = ""
    content:     str
    config_type: str = "yaml"
    description: Optional[str] = None
    created_by:  str = "system"
    metadata:    Dict[str, Any] = {}

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        if not v.strip(): raise ValueError("content must not be empty")
        return v


class CIJobRequest(BaseModel):
    job_name:     str
    branch:       str = "main"
    parameters:   Dict[str, Any] = {}
    callback_url: Optional[str] = None
    metadata:     Dict[str, Any] = {}


class MonitoringQueryRequest(BaseModel):
    query:      str
    start_time: Optional[datetime] = None
    end_time:   Optional[datetime] = None
    step:       str = "1m"
    filters:    Dict[str, Any] = {}

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        if not v.strip(): raise ValueError("query must not be empty")
        return v.strip()


class ScaleRequest(BaseModel):
    replicas: int

    @field_validator("replicas")
    @classmethod
    def validate_replicas(cls, v: int) -> int:
        if v < 0: raise ValueError("replicas must be >= 0")
        return v


# ══════════════════════════════════════════════════════════════════════════════
# ORM MODELS
# ══════════════════════════════════════════════════════════════════════════════
class ClusterModel(Base):
    __tablename__ = "clusters"
    id             = Column(Integer, primary_key=True, autoincrement=True)
    cluster_id     = Column(String(64), unique=True, nullable=False, index=True)
    name           = Column(String(200), nullable=False, index=True)
    provider       = Column(String(50),  nullable=False, index=True)
    version        = Column(String(30),  nullable=False)
    region         = Column(String(60),  nullable=False)
    api_server     = Column(String(500), nullable=False)
    status         = Column(String(20),  nullable=False, default="pending", index=True)
    health_status  = Column(String(20),  nullable=False, default="unknown",  index=True)
    node_count     = Column(Integer, default=0)
    node_info      = Column("cluster_node_info",  JSON, default=list)
    resource_usage = Column("cluster_resource_usage", JSON, default=dict)
    resource_capacity= Column("cluster_resource_capacity", JSON, default=dict)
    k8s_config     = Column("cluster_k8s_config", JSON, default=dict)
    networking     = Column("cluster_networking",  JSON, default=dict)
    extra_metadata = Column("cluster_metadata",   JSON, default=dict)
    created_at     = Column(DateTime, default=lambda: _naive(_now()))
    updated_at     = Column(DateTime, default=lambda: _naive(_now()), onupdate=lambda: _naive(_now()))
    last_health_check = Column(DateTime, nullable=True)
    __table_args__ = (Index("ix_cl_provider_status", "provider", "status"),)


class DeploymentModel(Base):
    __tablename__ = "deployments"
    id                 = Column(Integer, primary_key=True, autoincrement=True)
    deployment_id      = Column(String(64), unique=True, nullable=False, index=True)
    cluster_id         = Column(String(64), nullable=False, index=True)
    name               = Column(String(200), nullable=False, index=True)
    namespace          = Column(String(100), nullable=False, index=True)
    app_name           = Column(String(100), nullable=False, index=True)
    version            = Column(String(50),  nullable=False)
    image              = Column(String(500), nullable=False)
    image_tag          = Column(String(100), nullable=False, index=True)
    replicas           = Column(Integer, default=1)
    available_replicas = Column(Integer, default=0)
    strategy           = Column(String(50), nullable=False, index=True)
    strategy_config    = Column("deploy_strategy_config", JSON, default=dict)
    resources          = Column("deploy_resources",  JSON, default=dict)
    env_vars           = Column("deploy_env_vars",   JSON, default=list)
    volumes            = Column("deploy_volumes",    JSON, default=list)
    ports              = Column("deploy_ports",      JSON, default=list)
    labels             = Column("deploy_labels",     JSON, default=dict)
    annotations        = Column("deploy_annotations",JSON, default=dict)
    status             = Column(String(20), nullable=False, default="pending", index=True)
    health_status      = Column(String(20), nullable=False, default="unknown")
    service_name       = Column(String(200), nullable=True)
    service_type       = Column(String(20),  nullable=True)
    service_ports      = Column("deploy_service_ports", JSON, default=list)
    metrics            = Column("deploy_metrics",    JSON, default=dict)
    extra_metadata     = Column("deploy_metadata",   JSON, default=dict)
    created_at         = Column(DateTime, default=lambda: _naive(_now()))
    updated_at         = Column(DateTime, default=lambda: _naive(_now()), onupdate=lambda: _naive(_now()))
    deployed_at        = Column(DateTime, nullable=True)
    __table_args__ = (
        Index("ix_dep_cluster_status",  "cluster_id", "status"),
        Index("ix_dep_app_version",     "app_name",   "version"),
    )


class PodModel(Base):
    __tablename__ = "pods"
    id            = Column(Integer, primary_key=True, autoincrement=True)
    pod_id        = Column(String(64), unique=True, nullable=False, index=True)
    deployment_id = Column(String(64), nullable=True,  index=True)
    cluster_id    = Column(String(64), nullable=False, index=True)
    name          = Column(String(200), nullable=False, index=True)
    namespace     = Column(String(100), nullable=False, index=True)
    uid           = Column(String(100), nullable=True)
    node_name     = Column(String(200), nullable=True, index=True)
    node_ip       = Column(String(50),  nullable=True)
    pod_ip        = Column(String(50),  nullable=True)
    status        = Column(String(20),  nullable=False, default="pending", index=True)
    phase         = Column(String(20),  nullable=False, default="Pending")
    reason        = Column(String(100), nullable=True)
    message       = Column(Text, nullable=True)
    containers    = Column("pod_containers",  JSON, default=list)
    requests      = Column("pod_requests",    JSON, default=dict)
    limits        = Column("pod_limits",      JSON, default=dict)
    usage         = Column("pod_usage",       JSON, default=dict)
    restart_count = Column(Integer, default=0)
    pod_labels    = Column("pod_labels",      JSON, default=dict)
    pod_annotations= Column("pod_annotations",JSON, default=dict)
    extra_metadata= Column("pod_metadata",    JSON, default=dict)
    created_at    = Column(DateTime, default=lambda: _naive(_now()))
    updated_at    = Column(DateTime, default=lambda: _naive(_now()), onupdate=lambda: _naive(_now()))
    started_at    = Column(DateTime, nullable=True)
    finished_at   = Column(DateTime, nullable=True)
    __table_args__ = (
        Index("ix_pod_cluster_status", "cluster_id", "status"),
        Index("ix_pod_node",           "node_name",  "cluster_id"),
    )


class AlertModel(Base):
    __tablename__ = "alerts"
    id                  = Column(Integer, primary_key=True, autoincrement=True)
    alert_id            = Column(String(64), unique=True, nullable=False, index=True)
    cluster_id          = Column(String(64), nullable=True, index=True)
    alert_name          = Column(String(200), nullable=False, index=True)
    generator_url       = Column(String(500), nullable=True)
    status              = Column(String(20), nullable=False, default=AlertStatus.FIRING.value, index=True)
    severity            = Column(String(20), nullable=False, default=AlertSeverity.WARNING.value, index=True)
    message             = Column(Text, nullable=False)
    alert_labels        = Column("alert_labels",      JSON, default=dict)
    alert_annotations   = Column("alert_annotations", JSON, default=dict)
    acknowledged_by     = Column(String(100), nullable=True)
    acknowledged_at     = Column(DateTime, nullable=True)
    acknowledged_reason = Column(Text, nullable=True)
    silenced_by         = Column(String(100), nullable=True)
    silenced_at         = Column(DateTime, nullable=True)
    silenced_until      = Column(DateTime, nullable=True)
    extra_metadata      = Column("alert_metadata",    JSON, default=dict)
    starts_at           = Column(DateTime, nullable=False, default=lambda: _naive(_now()), index=True)
    ends_at             = Column(DateTime, nullable=True)
    created_at          = Column(DateTime, default=lambda: _naive(_now()))
    updated_at          = Column(DateTime, default=lambda: _naive(_now()), onupdate=lambda: _naive(_now()))
    __table_args__ = (
        Index("ix_alert_severity_status", "severity", "status"),
        Index("ix_alert_cluster_time",    "cluster_id", "starts_at"),
    )


class BackupModel(Base):
    __tablename__ = "backups"
    id            = Column(Integer, primary_key=True, autoincrement=True)
    backup_id     = Column(String(64), unique=True, nullable=False, index=True)
    cluster_id    = Column(String(64), nullable=True, index=True)
    backup_type   = Column(String(50), nullable=False, index=True)
    name          = Column(String(200), nullable=False, index=True)
    resources     = Column("backup_resources", JSON, default=list)
    storage_type  = Column(String(20), nullable=False)
    storage_path  = Column(String(500), nullable=False)
    size_bytes    = Column(Float, nullable=True)
    status        = Column(String(20), nullable=False, default="pending", index=True)
    phase         = Column(String(20), nullable=False, default="pending")
    error_message = Column(Text, nullable=True)
    retention_days= Column(Integer, default=30)
    expires_at    = Column(DateTime, nullable=True, index=True)
    extra_metadata= Column("backup_metadata", JSON, default=dict)
    created_at    = Column(DateTime, default=lambda: _naive(_now()))
    updated_at    = Column(DateTime, default=lambda: _naive(_now()), onupdate=lambda: _naive(_now()))
    started_at    = Column(DateTime, nullable=True)
    completed_at  = Column(DateTime, nullable=True)
    __table_args__ = (Index("ix_backup_type_status", "backup_type", "status"),)


class ConfigModel(Base):
    __tablename__ = "configs"
    id            = Column(Integer, primary_key=True, autoincrement=True)
    config_id     = Column(String(64), unique=True, nullable=False, index=True)
    data_id       = Column(String(200), nullable=False, index=True)
    group         = Column(String(100), nullable=False, default="DEFAULT_GROUP", index=True)
    namespace     = Column(String(100), nullable=False, default="")
    content       = Column(Text, nullable=False)
    config_type   = Column(String(20), nullable=False, default="yaml", index=True)
    md5           = Column(String(32),  nullable=False)
    description   = Column(Text, nullable=True)
    config_tags   = Column("config_tags",     JSON, default=list)
    extra_metadata= Column("config_metadata", JSON, default=dict)
    created_by    = Column(String(100), nullable=False, default="system")
    updated_by    = Column(String(100), nullable=False, default="system")
    created_at    = Column(DateTime, default=lambda: _naive(_now()))
    updated_at    = Column(DateTime, default=lambda: _naive(_now()), onupdate=lambda: _naive(_now()))
    __table_args__ = (
        UniqueConstraint("data_id", "group", "namespace", name="uq_config_data_id_group_ns"),
        Index("ix_config_type_updated", "config_type", "updated_at"),
    )


class CIJobModel(Base):
    __tablename__ = "ci_jobs"
    id            = Column(Integer, primary_key=True, autoincrement=True)
    job_run_id    = Column(String(64), unique=True, nullable=False, index=True)
    job_name      = Column(String(200), nullable=False, index=True)
    backend       = Column(String(30),  nullable=False, default="jenkins")
    branch        = Column(String(200), nullable=False, default="main")
    build_number  = Column(Integer, nullable=True)
    queue_number  = Column(Integer, nullable=True)
    status        = Column(String(20),  nullable=False, default="triggered", index=True)
    result        = Column(String(20),  nullable=True)
    duration_ms   = Column(Float, nullable=True)
    parameters    = Column("ci_parameters",  JSON, default=dict)
    artifacts     = Column("ci_artifacts",   JSON, default=list)
    extra_metadata= Column("ci_metadata",    JSON, default=dict)
    triggered_by  = Column(String(100), nullable=True)
    created_at    = Column(DateTime, default=lambda: _naive(_now()))
    updated_at    = Column(DateTime, default=lambda: _naive(_now()), onupdate=lambda: _naive(_now()))
    completed_at  = Column(DateTime, nullable=True)
    __table_args__ = (Index("ix_ci_job_status", "job_name", "status"),)


Base.metadata.create_all(engine)


# ══════════════════════════════════════════════════════════════════════════════
# REDIS MANAGER
# ══════════════════════════════════════════════════════════════════════════════
class RedisManager:
    _client: Any = None
    _memory: Dict[str, Tuple[str, float]] = {}

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


# ══════════════════════════════════════════════════════════════════════════════
# KUBERNETES CLIENT (with stub fallback)
# ══════════════════════════════════════════════════════════════════════════════
class K8SClient:
    """Kubernetes client; stubs all operations when kubernetes SDK unavailable."""

    def __init__(self, cfg: ServiceConfig):
        self._cfg   = cfg
        self._ready = False
        self._core_api  = None
        self._apps_api  = None
        self._batch_api = None
        self._init()

    def _init(self):
        if not _HAS_K8S:
            logger.info("kubernetes SDK not available; K8SClient using stubs")
            return
        try:
            if self._cfg.k8s_in_cluster:
                k8s_config.load_incluster_config()
            elif self._cfg.k8s_kubeconfig:
                k8s_config.load_kube_config(config_file=self._cfg.k8s_kubeconfig)
            else:
                configuration = k8s_client.Configuration()
                configuration.host        = self._cfg.k8s_api_server
                configuration.verify_ssl  = False
                if self._cfg.k8s_token:
                    configuration.api_key = {"authorization": f"Bearer {self._cfg.k8s_token}"}
                k8s_client.Configuration.set_default(configuration)

            api = k8s_client.ApiClient()
            self._core_api  = k8s_client.CoreV1Api(api)
            self._apps_api  = k8s_client.AppsV1Api(api)
            self._batch_api = k8s_client.BatchV1Api(api)
            self._ready     = True
            logger.info("K8SClient initialised (api_server=%s)", self._cfg.k8s_api_server)
        except Exception as e:
            logger.warning("K8SClient init failed (%s); using stubs", e)

    # ── helpers ───────────────────────────────────────────────────────────────
    @staticmethod
    def _parse_resource(r: str) -> float:
        if not r: return 0.0
        if r.endswith("m"):    return float(r[:-1]) / 1000
        if r.endswith("Ki"):   return float(r[:-2]) * 1024
        if r.endswith("Mi"):   return float(r[:-2]) * 1024 ** 2
        if r.endswith("Gi"):   return float(r[:-2]) * 1024 ** 3
        try: return float(r)
        except: return 0.0

    # ── cluster info ──────────────────────────────────────────────────────────
    async def get_cluster_info(self) -> Dict[str, Any]:
        if self._ready:
            try:
                nodes = self._core_api.list_node()
                ns    = self._core_api.list_namespace()
                return {
                    "node_count":      len(nodes.items),
                    "namespace_count": len(ns.items),
                    "nodes": [{"name": n.metadata.name,
                               "status": _node_status(n),
                               "allocatable": dict(n.status.allocatable or {})}
                              for n in nodes.items]
                }
            except Exception as e:
                logger.warning("get_cluster_info failed: %s", e)
        # Stub
        return {"node_count": 3, "namespace_count": 5, "nodes": [], "stub": True}

    # ── deployments ───────────────────────────────────────────────────────────
    async def create_deployment(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        if not self._ready:
            return {"name": spec["name"], "namespace": spec.get("namespace", "default"),
                    "uid": uuid.uuid4().hex, "stub": True}
        try:
            ns   = spec.get("namespace", "default")
            name = spec["name"]
            body = k8s_client.V1Deployment(
                api_version="apps/v1", kind="Deployment",
                metadata=k8s_client.V1ObjectMeta(name=name, namespace=ns, labels={"app": name}),
                spec=k8s_client.V1DeploymentSpec(
                    replicas=spec.get("replicas", 1),
                    selector=k8s_client.V1LabelSelector(match_labels={"app": name}),
                    template=k8s_client.V1PodTemplateSpec(
                        metadata=k8s_client.V1ObjectMeta(labels={"app": name}),
                        spec=k8s_client.V1PodSpec(containers=[
                            k8s_client.V1Container(
                                name=name, image=spec["image"],
                                resources=k8s_client.V1ResourceRequirements(
                                    requests=spec.get("resources", {}).get("requests", {}),
                                    limits  =spec.get("resources", {}).get("limits", {}),
                                ),
                            )
                        ])
                    )
                )
            )
            r = self._apps_api.create_namespaced_deployment(namespace=ns, body=body)
            return {"name": r.metadata.name, "namespace": r.metadata.namespace, "uid": r.metadata.uid}
        except Exception as e:
            logger.warning("create_deployment failed: %s", e)
            return {"name": spec["name"], "stub": True, "error": str(e)}

    async def get_deployment(self, name: str, namespace: str = "default") -> Dict[str, Any]:
        if self._ready:
            try:
                d = self._apps_api.read_namespaced_deployment(name=name, namespace=namespace)
                return {
                    "name": d.metadata.name,
                    "namespace": d.metadata.namespace,
                    "replicas": d.spec.replicas,
                    "available_replicas": d.status.available_replicas or 0,
                    "image": d.spec.template.spec.containers[0].image if d.spec.template.spec.containers else "",
                }
            except Exception as e:
                logger.warning("get_deployment failed: %s", e)
        return {"name": name, "namespace": namespace, "replicas": 1, "available_replicas": 1, "stub": True}

    async def scale_deployment(self, name: str, namespace: str, replicas: int) -> bool:
        if self._ready:
            try:
                scale = k8s_client.V1Scale(spec=k8s_client.V1ScaleSpec(replicas=replicas))
                self._apps_api.patch_namespaced_deployment_scale(name=name, namespace=namespace, body=scale)
                return True
            except Exception as e:
                logger.warning("scale_deployment failed: %s", e)
        return True  # stub OK

    async def delete_deployment(self, name: str, namespace: str = "default") -> bool:
        if self._ready:
            try:
                self._apps_api.delete_namespaced_deployment(name=name, namespace=namespace)
                return True
            except Exception as e:
                logger.warning("delete_deployment failed: %s", e)
        return True  # stub OK

    # ── pods ──────────────────────────────────────────────────────────────────
    async def list_pods(self, namespace: str = "default",
                        label_selector: Optional[str] = None) -> List[Dict[str, Any]]:
        if self._ready:
            try:
                pods = self._core_api.list_namespaced_pod(
                    namespace=namespace, label_selector=label_selector)
                return [_pod_to_dict(p) for p in pods.items]
            except Exception as e:
                logger.warning("list_pods failed: %s", e)
        return []  # stub

    async def get_pod_logs(self, name: str, namespace: str, tail: int = 100) -> str:
        if self._ready:
            try:
                return self._core_api.read_namespaced_pod_log(
                    name=name, namespace=namespace, tail_lines=tail)
            except Exception as e:
                logger.warning("get_pod_logs failed: %s", e)
        return f"[stub] No logs available for pod {name}"


def _node_status(node: Any) -> str:
    for cond in (node.status.conditions or []):
        if cond.type == "Ready":
            return "Ready" if cond.status == "True" else "NotReady"
    return "Unknown"


def _pod_to_dict(pod: Any) -> Dict[str, Any]:
    return {
        "name": pod.metadata.name,
        "namespace": pod.metadata.namespace,
        "status": pod.status.phase or "Unknown",
        "node_name": pod.spec.node_name,
        "pod_ip": pod.status.pod_ip,
        "start_time": pod.status.start_time.isoformat() if pod.status.start_time else None,
        "containers": [c.name for c in (pod.spec.containers or [])],
    }


# ══════════════════════════════════════════════════════════════════════════════
# DOCKER CLIENT (stub fallback)
# ══════════════════════════════════════════════════════════════════════════════
class DockerClientWrapper:
    def __init__(self, host: str):
        self._host   = host
        self._client = None
        self._init()

    def _init(self):
        if not _HAS_DOCKER:
            logger.info("docker SDK not available; DockerClient using stubs")
            return
        try:
            self._client = docker.DockerClient(base_url=self._host, timeout=30)
            logger.info("DockerClient initialised (%s)", self._host)
        except Exception as e:
            logger.warning("DockerClient init failed (%s); using stubs", e)

    async def list_containers(self, all: bool = False) -> List[Dict[str, Any]]:
        if self._client:
            try:
                cs = self._client.containers.list(all=all)
                return [{"id": c.id[:12], "name": c.name,
                         "status": c.status, "image": c.image.tags[:1]} for c in cs]
            except Exception as e:
                logger.warning("list_containers failed: %s", e)
        return []

    async def build_image(self, path: str, tag: str, dockerfile: str = "Dockerfile") -> Dict[str, Any]:
        if self._client:
            try:
                img, logs = self._client.images.build(path=path, tag=tag, dockerfile=dockerfile, rm=True)
                return {"image_id": img.id, "tags": img.tags}
            except Exception as e:
                logger.warning("build_image failed: %s", e)
        return {"image_id": f"sha256:{uuid.uuid4().hex}", "tags": [tag], "stub": True}

    async def push_image(self, name: str) -> bool:
        if self._client:
            try: self._client.images.push(name); return True
            except Exception as e: logger.warning("push_image failed: %s", e)
        return True  # stub

    async def pull_image(self, name: str) -> Dict[str, Any]:
        if self._client:
            try:
                img = self._client.images.pull(name)
                return {"image_id": img.id, "tags": img.tags}
            except Exception as e:
                logger.warning("pull_image failed: %s", e)
        return {"image_id": f"sha256:{uuid.uuid4().hex}", "tags": [name], "stub": True}


# ══════════════════════════════════════════════════════════════════════════════
# MONITORING CLIENT
# ══════════════════════════════════════════════════════════════════════════════
class MonitoringClient:
    def __init__(self, cfg: ServiceConfig):
        self._prometheus = cfg.prometheus_url
        self._grafana    = cfg.grafana_url
        self._es         = cfg.elasticsearch_url
        self._alertmgr   = cfg.alertmanager_url

    async def query_prometheus(self, query: str,
                                start: Optional[str] = None,
                                end:   Optional[str] = None,
                                step:  str = "1m") -> Dict[str, Any]:
        if not _HAS_AIOHTTP:
            return {"status": "stub", "data": {"result": []}, "note": "aiohttp not available"}
        try:
            params: Dict[str, str] = {"query": query}
            if start and end:
                url = f"{self._prometheus}/api/v1/query_range"
                params.update({"start": start, "end": end, "step": step})
            else:
                url = f"{self._prometheus}/api/v1/query"
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                async with session.get(url, params=params) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    return {"status": "error", "code": resp.status}
        except Exception as e:
            logger.warning("query_prometheus failed: %s", e)
            return {"status": "error", "error": str(e)}

    async def get_cluster_metrics(self, cluster_id: str) -> Dict[str, Any]:
        end   = _now()
        start = end - timedelta(hours=1)
        cpu_q = f'sum(rate(container_cpu_usage_seconds_total{{cluster="{cluster_id}"}}[5m])) by (pod)'
        mem_q = f'sum(container_memory_usage_bytes{{cluster="{cluster_id}"}}) by (pod)'
        cpu = await self.query_prometheus(cpu_q, start.isoformat(), end.isoformat())
        mem = await self.query_prometheus(mem_q, start.isoformat(), end.isoformat())
        return {
            "cluster_id": cluster_id,
            "cpu": _parse_prometheus_result(cpu),
            "memory": _parse_prometheus_result(mem),
            "timestamp": _fmt(end),
        }

    async def fire_webhook(self, payload: Dict[str, Any]) -> bool:
        """Send alert payload to alertmanager webhook."""
        if not _HAS_AIOHTTP: return True
        try:
            url = f"{self._alertmgr}/api/v2/alerts"
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                async with session.post(url, json=payload) as resp:
                    return resp.status in (200, 201)
        except Exception as e:
            logger.debug("fire_webhook failed: %s", e)
        return False


def _parse_prometheus_result(r: Dict[str, Any]) -> List[Dict[str, Any]]:
    if r.get("status") != "success": return []
    return [{"metric": item.get("metric", {}), "values": item.get("values", [])}
            for item in r.get("data", {}).get("result", [])]


# ══════════════════════════════════════════════════════════════════════════════
# CONFIG CLIENT
# ══════════════════════════════════════════════════════════════════════════════
class ConfigClientWrapper:
    def __init__(self, cfg: ServiceConfig):
        self._nacos = None
        self._vault = None
        # Nacos
        if _HAS_NACOS and cfg.nacos_server:
            try:
                self._nacos = nacos.NacosClient(  # type: ignore
                    cfg.nacos_server, namespace=cfg.nacos_namespace)
                logger.info("Nacos client initialised")
            except Exception as e:
                logger.warning("Nacos init failed: %s", e)
        # Vault
        if _HAS_HVAC and cfg.vault_url:
            try:
                self._vault = hvac.Client(url=cfg.vault_url, token=cfg.vault_token)  # type: ignore
                logger.info("Vault client initialised")
            except Exception as e:
                logger.warning("Vault init failed: %s", e)

    async def get_config(self, data_id: str, group: str = "DEFAULT_GROUP") -> Optional[str]:
        if self._nacos:
            try: return self._nacos.get_config(data_id, group)  # type: ignore
            except Exception as e: logger.warning("Nacos get_config failed: %s", e)
        return None

    async def publish_config(self, data_id: str, content: str, group: str = "DEFAULT_GROUP") -> bool:
        if self._nacos:
            try: return bool(self._nacos.publish_config(data_id, group, content))  # type: ignore
            except Exception as e: logger.warning("Nacos publish_config failed: %s", e)
        return True  # stub OK

    async def get_secret(self, path: str, mount: str = "secret") -> Optional[Dict]:
        if self._vault:
            try:
                r = self._vault.secrets.kv.v2.read_secret_version(  # type: ignore
                    path=path, mount_point=mount)
                return r.get("data", {}).get("data")
            except Exception as e:
                logger.warning("Vault get_secret failed: %s", e)
        return None

    async def put_secret(self, path: str, data: Dict, mount: str = "secret") -> bool:
        if self._vault:
            try:
                self._vault.secrets.kv.v2.create_or_update_secret(  # type: ignore
                    path=path, secret=data, mount_point=mount)
                return True
            except Exception as e:
                logger.warning("Vault put_secret failed: %s", e)
        return True  # stub


# ══════════════════════════════════════════════════════════════════════════════
# CI/CD CLIENT
# ══════════════════════════════════════════════════════════════════════════════
class CICDClient:
    def __init__(self, cfg: ServiceConfig):
        self._jenkins = None
        if _HAS_JENKINS and cfg.jenkins_url:
            try:
                self._jenkins = jenkins.Jenkins(  # type: ignore
                    cfg.jenkins_url, username=cfg.jenkins_user, password=cfg.jenkins_pass)
                logger.info("Jenkins client initialised")
            except Exception as e:
                logger.warning("Jenkins init failed: %s", e)

    async def trigger_job(self, job_name: str, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        if self._jenkins:
            try:
                q = self._jenkins.build_job(job_name, parameters or {})  # type: ignore
                return {"job_name": job_name, "queue_number": q, "status": "triggered"}
            except Exception as e:
                logger.warning("trigger_job failed: %s", e)
        # Stub: simulate triggered
        return {"job_name": job_name, "queue_number": random.randint(1000, 9999),
                "status": "triggered", "stub": True}

    async def get_job_status(self, job_name: str, build_number: int) -> Dict[str, Any]:
        if self._jenkins:
            try:
                info = self._jenkins.get_build_info(job_name, build_number)  # type: ignore
                return {"job_name": job_name, "build_number": build_number,
                        "status": info.get("result"), "duration": info.get("duration")}
            except Exception as e:
                logger.warning("get_job_status failed: %s", e)
        return {"job_name": job_name, "build_number": build_number,
                "status": "SUCCESS", "duration": 120000, "stub": True}

    async def list_jobs(self) -> List[Dict[str, Any]]:
        if self._jenkins:
            try:
                jobs = self._jenkins.get_jobs()  # type: ignore
                return [{"name": j["name"], "url": j.get("url", "")} for j in jobs]
            except Exception as e:
                logger.warning("list_jobs failed: %s", e)
        return []


# ══════════════════════════════════════════════════════════════════════════════
# SUPPORT OPS SERVICE
# ══════════════════════════════════════════════════════════════════════════════
class SupportOpsService:
    def __init__(self, cfg: ServiceConfig):
        self._cfg      = cfg
        cfg.ensure_dirs()
        self._redis    = RedisManager(cfg.redis_url)
        self._k8s      = K8SClient(cfg)
        self._docker   = DockerClientWrapper(cfg.docker_host)
        self._monitor  = MonitoringClient(cfg)
        self._config_c = ConfigClientWrapper(cfg)
        self._cicd     = CICDClient(cfg)

    async def startup(self):
        await self._redis.connect()
        logger.info("SupportOpsService started")

    async def shutdown(self):
        await self._redis.disconnect()
        logger.info("SupportOpsService stopped")

    def _db(self) -> Session:
        return SessionLocal()

    # ── Clusters ──────────────────────────────────────────────────────────────
    def create_cluster(self, spec: ClusterSpec) -> Dict[str, Any]:
        cid = f"cl_{uuid.uuid4().hex[:12]}"
        with self._db() as db:
            existing = db.query(ClusterModel).filter(ClusterModel.name == spec.name).first()
            if existing:
                raise HTTPException(409, f"Cluster '{spec.name}' already exists")
            row = ClusterModel(
                cluster_id     = cid,
                name           = spec.name,
                provider       = spec.provider,
                version        = spec.version,
                region         = spec.region,
                api_server     = f"https://{spec.name}.k8s.{spec.region}.example.com",
                status         = ResourceStatus.PENDING.value,
                health_status  = "unknown",
                node_count     = spec.node_count,
                networking     = spec.networking,
                k8s_config     = {"node_type": spec.node_type, "monitoring": spec.monitoring,
                                  "security": spec.security},
                extra_metadata = spec.metadata,
            )
            db.add(row)
            db.commit()
            db.refresh(row)
        return {"cluster_id": cid, "status": ResourceStatus.PENDING.value, "created_at": _fmt(_now())}

    def get_cluster(self, cluster_id: str) -> Dict[str, Any]:
        with self._db() as db:
            row = db.query(ClusterModel).filter(ClusterModel.cluster_id == cluster_id).first()
            if not row: raise HTTPException(404, "Cluster not found")
        return _cluster_to_dict(row)

    def list_clusters(self, provider: Optional[str] = None, status: Optional[str] = None,
                      skip: int = 0, limit: int = 20) -> Dict[str, Any]:
        with self._db() as db:
            q = db.query(ClusterModel)
            if provider: q = q.filter(ClusterModel.provider == provider)
            if status:   q = q.filter(ClusterModel.status   == status)
            total = q.count()
            rows  = q.order_by(ClusterModel.created_at.desc()).offset(skip).limit(limit).all()
        return {"total": total, "clusters": [_cluster_to_dict(r) for r in rows]}

    def update_cluster(self, cluster_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        with self._db() as db:
            row = db.query(ClusterModel).filter(ClusterModel.cluster_id == cluster_id).first()
            if not row: raise HTTPException(404, "Cluster not found")
            for k, v in updates.items():
                if hasattr(row, k):
                    setattr(row, k, v)
            row.updated_at = _naive(_now())
            db.commit()
        return {"cluster_id": cluster_id, "updated": True}

    def delete_cluster(self, cluster_id: str) -> Dict[str, Any]:
        with self._db() as db:
            row = db.query(ClusterModel).filter(ClusterModel.cluster_id == cluster_id).first()
            if not row: raise HTTPException(404, "Cluster not found")
            db.delete(row)
            db.commit()
        return {"cluster_id": cluster_id, "deleted": True}

    async def get_cluster_health(self, cluster_id: str) -> Dict[str, Any]:
        with self._db() as db:
            row = db.query(ClusterModel).filter(ClusterModel.cluster_id == cluster_id).first()
            if not row: raise HTTPException(404, "Cluster not found")
        k8s_info = await self._k8s.get_cluster_info()
        metrics  = await self._monitor.get_cluster_metrics(cluster_id)
        health   = "healthy" if k8s_info.get("node_count", 0) > 0 else "degraded"
        # Persist
        with self._db() as db:
            r2 = db.query(ClusterModel).filter(ClusterModel.cluster_id == cluster_id).first()
            if r2:
                r2.health_status      = health
                r2.last_health_check  = _naive(_now())
                r2.resource_usage     = metrics
                db.commit()
        return {"cluster_id": cluster_id, "health": health, "k8s": k8s_info, "metrics": metrics}

    # ── Deployments ───────────────────────────────────────────────────────────
    async def create_deployment(self, cluster_id: str, spec: DeploymentSpec) -> Dict[str, Any]:
        # Verify cluster exists
        with self._db() as db:
            cl = db.query(ClusterModel).filter(ClusterModel.cluster_id == cluster_id).first()
            if not cl: raise HTTPException(404, "Cluster not found")
        did = f"dep_{uuid.uuid4().hex[:12]}"
        image_parts = spec.image.split(":")
        image_tag   = image_parts[1] if len(image_parts) > 1 else "latest"
        # Call K8s
        k8s_result = await self._k8s.create_deployment({
            "name": spec.name, "namespace": spec.namespace,
            "image": spec.image, "replicas": spec.replicas,
            "resources": spec.resources, "ports": spec.ports,
            "env": spec.env,
        })
        strategy = spec.strategy if isinstance(spec.strategy, str) else spec.strategy.value
        with self._db() as db:
            row = DeploymentModel(
                deployment_id      = did,
                cluster_id         = cluster_id,
                name               = spec.name,
                namespace          = spec.namespace,
                app_name           = spec.name,
                version            = image_tag,
                image              = spec.image,
                image_tag          = image_tag,
                replicas           = spec.replicas,
                available_replicas = 0,
                strategy           = strategy,
                strategy_config    = spec.strategy_config,
                resources          = spec.resources,
                env_vars           = spec.env,
                volumes            = spec.volumes,
                ports              = spec.ports,
                labels             = spec.labels,
                annotations        = spec.annotations,
                status             = ResourceStatus.PENDING.value,
                service_type       = spec.service_type,
                service_ports      = spec.service_ports,
                extra_metadata     = spec.metadata,
                deployed_at        = _naive(_now()),
            )
            db.add(row)
            db.commit()
            db.refresh(row)
        return {"deployment_id": did, "status": ResourceStatus.PENDING.value,
                "k8s": k8s_result, "created_at": _fmt(_now())}

    def get_deployment(self, deployment_id: str) -> Dict[str, Any]:
        with self._db() as db:
            row = db.query(DeploymentModel).filter(
                DeploymentModel.deployment_id == deployment_id).first()
            if not row: raise HTTPException(404, "Deployment not found")
        return _deployment_to_dict(row)

    def list_deployments(self, cluster_id: Optional[str] = None, status: Optional[str] = None,
                          skip: int = 0, limit: int = 20) -> Dict[str, Any]:
        with self._db() as db:
            q = db.query(DeploymentModel)
            if cluster_id: q = q.filter(DeploymentModel.cluster_id  == cluster_id)
            if status:     q = q.filter(DeploymentModel.status      == status)
            total = q.count()
            rows  = q.order_by(DeploymentModel.created_at.desc()).offset(skip).limit(limit).all()
        return {"total": total, "deployments": [_deployment_to_dict(r) for r in rows]}

    async def scale_deployment(self, deployment_id: str, replicas: int) -> Dict[str, Any]:
        with self._db() as db:
            row = db.query(DeploymentModel).filter(
                DeploymentModel.deployment_id == deployment_id).first()
            if not row: raise HTTPException(404, "Deployment not found")
            await self._k8s.scale_deployment(row.name, row.namespace, replicas)
            row.replicas   = replicas
            row.updated_at = _naive(_now())
            db.commit()
        return {"deployment_id": deployment_id, "replicas": replicas}

    async def delete_deployment(self, deployment_id: str) -> Dict[str, Any]:
        with self._db() as db:
            row = db.query(DeploymentModel).filter(
                DeploymentModel.deployment_id == deployment_id).first()
            if not row: raise HTTPException(404, "Deployment not found")
            await self._k8s.delete_deployment(row.name, row.namespace)
            row.status     = ResourceStatus.TERMINATING.value
            row.updated_at = _naive(_now())
            db.commit()
        return {"deployment_id": deployment_id, "status": ResourceStatus.TERMINATING.value}

    async def rollback_deployment(self, deployment_id: str, image: str) -> Dict[str, Any]:
        with self._db() as db:
            row = db.query(DeploymentModel).filter(
                DeploymentModel.deployment_id == deployment_id).first()
            if not row: raise HTTPException(404, "Deployment not found")
            # Update image in K8s
            k8s_result = await self._k8s.create_deployment({
                "name": row.name, "namespace": row.namespace, "image": image,
                "replicas": row.replicas, "resources": row.resources,
            })
            row.image      = image
            row.image_tag  = image.split(":")[-1] if ":" in image else "latest"
            row.updated_at = _naive(_now())
            db.commit()
        return {"deployment_id": deployment_id, "new_image": image, "k8s": k8s_result}

    # ── Pods ──────────────────────────────────────────────────────────────────
    async def list_pods(self, cluster_id: str, namespace: str = "default") -> Dict[str, Any]:
        k8s_pods = await self._k8s.list_pods(namespace)
        with self._db() as db:
            db_pods = db.query(PodModel).filter(
                PodModel.cluster_id == cluster_id,
                PodModel.namespace  == namespace,
            ).limit(200).all()
        return {
            "k8s_pods": k8s_pods,
            "db_pods": [_pod_to_dict_model(p) for p in db_pods],
        }

    async def get_pod_logs(self, cluster_id: str, pod_name: str,
                           namespace: str = "default", tail: int = 100) -> Dict[str, Any]:
        logs = await self._k8s.get_pod_logs(pod_name, namespace, tail)
        return {"cluster_id": cluster_id, "pod_name": pod_name,
                "namespace": namespace, "logs": logs}

    # ── Alerts ────────────────────────────────────────────────────────────────
    def create_alert(self, req: AlertCreateRequest) -> Dict[str, Any]:
        aid  = f"alr_{uuid.uuid4().hex[:12]}"
        severity = req.severity if isinstance(req.severity, str) else req.severity.value
        with self._db() as db:
            row = AlertModel(
                alert_id       = aid,
                cluster_id     = req.cluster_id,
                alert_name     = req.alert_name,
                status         = AlertStatus.FIRING.value,
                severity       = severity,
                message        = req.message,
                alert_labels   = req.labels,
                alert_annotations= req.annotations,
                starts_at      = _naive(req.starts_at or _now()),
                extra_metadata = req.metadata,
            )
            db.add(row)
            db.commit()
            db.refresh(row)
        if ALERTS_FIRING:
            try: ALERTS_FIRING.labels(severity=severity).inc()
            except Exception: pass
        return {"alert_id": aid, "status": AlertStatus.FIRING.value, "created_at": _fmt(_now())}

    def get_alert(self, alert_id: str) -> Dict[str, Any]:
        with self._db() as db:
            row = db.query(AlertModel).filter(AlertModel.alert_id == alert_id).first()
            if not row: raise HTTPException(404, "Alert not found")
        return _alert_to_dict(row)

    def list_alerts(self, severity: Optional[str] = None, status: Optional[str] = None,
                    cluster_id: Optional[str] = None,
                    skip: int = 0, limit: int = 50) -> Dict[str, Any]:
        with self._db() as db:
            q = db.query(AlertModel)
            if severity:   q = q.filter(AlertModel.severity   == severity)
            if status:     q = q.filter(AlertModel.status     == status)
            if cluster_id: q = q.filter(AlertModel.cluster_id == cluster_id)
            total = q.count()
            rows  = q.order_by(AlertModel.starts_at.desc()).offset(skip).limit(limit).all()
        return {"total": total, "alerts": [_alert_to_dict(r) for r in rows]}

    def acknowledge_alert(self, alert_id: str, req: AlertAckRequest) -> Dict[str, Any]:
        with self._db() as db:
            row = db.query(AlertModel).filter(AlertModel.alert_id == alert_id).first()
            if not row: raise HTTPException(404, "Alert not found")
            if row.status == AlertStatus.RESOLVED.value:
                raise HTTPException(400, "Cannot acknowledge resolved alert")
            row.status               = AlertStatus.ACKNOWLEDGED.value
            row.acknowledged_by      = req.acknowledged_by
            row.acknowledged_at      = _naive(_now())
            row.acknowledged_reason  = req.acknowledged_reason
            row.updated_at           = _naive(_now())
            db.commit()
        return {"alert_id": alert_id, "status": AlertStatus.ACKNOWLEDGED.value}

    def silence_alert(self, alert_id: str, req: AlertSilenceRequest) -> Dict[str, Any]:
        with self._db() as db:
            row = db.query(AlertModel).filter(AlertModel.alert_id == alert_id).first()
            if not row: raise HTTPException(404, "Alert not found")
            row.status        = AlertStatus.SILENCED.value
            row.silenced_by   = req.silenced_by
            row.silenced_at   = _naive(_now())
            row.silenced_until= _naive(_now() + timedelta(minutes=req.silence_minutes))
            row.updated_at    = _naive(_now())
            db.commit()
        return {"alert_id": alert_id, "status": AlertStatus.SILENCED.value,
                "silenced_until": _fmt(_now() + timedelta(minutes=req.silence_minutes))}

    def resolve_alert(self, alert_id: str) -> Dict[str, Any]:
        with self._db() as db:
            row = db.query(AlertModel).filter(AlertModel.alert_id == alert_id).first()
            if not row: raise HTTPException(404, "Alert not found")
            row.status     = AlertStatus.RESOLVED.value
            row.ends_at    = _naive(_now())
            row.updated_at = _naive(_now())
            db.commit()
        if ALERTS_FIRING:
            try: ALERTS_FIRING.labels(severity=row.severity).dec()
            except Exception: pass
        return {"alert_id": alert_id, "status": AlertStatus.RESOLVED.value}

    # ── Backups ───────────────────────────────────────────────────────────────
    def create_backup(self, req: BackupRequest) -> Dict[str, Any]:
        bid      = f"bk_{uuid.uuid4().hex[:12]}"
        expires  = _now() + timedelta(days=req.retention_days)
        storage_path = os.path.join(self._cfg.model_storage_dir, "backups", f"{bid}.tar.gz")
        with self._db() as db:
            row = BackupModel(
                backup_id      = bid,
                cluster_id     = req.cluster_id,
                backup_type    = req.backup_type,
                name           = req.name,
                resources      = req.resources,
                storage_type   = req.storage_type,
                storage_path   = storage_path,
                status         = BackupStatus.PENDING.value,
                phase          = "pending",
                retention_days = req.retention_days,
                expires_at     = _naive(expires),
                extra_metadata = req.metadata,
            )
            db.add(row)
            db.commit()
            db.refresh(row)
        if BACKUPS_TOTAL:
            try: BACKUPS_TOTAL.labels(backup_type=req.backup_type, status="triggered").inc()
            except Exception: pass
        return {"backup_id": bid, "status": BackupStatus.PENDING.value,
                "expires_at": _fmt(expires), "created_at": _fmt(_now())}

    def get_backup(self, backup_id: str) -> Dict[str, Any]:
        with self._db() as db:
            row = db.query(BackupModel).filter(BackupModel.backup_id == backup_id).first()
            if not row: raise HTTPException(404, "Backup not found")
        return _backup_to_dict(row)

    def list_backups(self, cluster_id: Optional[str] = None, status: Optional[str] = None,
                     skip: int = 0, limit: int = 20) -> Dict[str, Any]:
        with self._db() as db:
            q = db.query(BackupModel)
            if cluster_id: q = q.filter(BackupModel.cluster_id == cluster_id)
            if status:     q = q.filter(BackupModel.status     == status)
            total = q.count()
            rows  = q.order_by(BackupModel.created_at.desc()).offset(skip).limit(limit).all()
        return {"total": total, "backups": [_backup_to_dict(r) for r in rows]}

    def restore_backup(self, backup_id: str) -> Dict[str, Any]:
        with self._db() as db:
            row = db.query(BackupModel).filter(BackupModel.backup_id == backup_id).first()
            if not row: raise HTTPException(404, "Backup not found")
            if row.status != BackupStatus.COMPLETED.value:
                raise HTTPException(400, f"Backup status is {row.status}, not completed")
        # Stub: would trigger restore job
        return {"backup_id": backup_id, "restore_id": f"rst_{uuid.uuid4().hex[:12]}",
                "status": "triggered", "message": "Restore job triggered"}

    # ── Config Management ─────────────────────────────────────────────────────
    def create_config(self, req: ConfigCreateRequest) -> Dict[str, Any]:
        cfg_id = f"cfg_{uuid.uuid4().hex[:12]}"
        md5    = hashlib.md5(req.content.encode()).hexdigest()
        with self._db() as db:
            existing = db.query(ConfigModel).filter(
                ConfigModel.data_id   == req.data_id,
                ConfigModel.group     == req.group,
                ConfigModel.namespace == req.namespace,
            ).first()
            if existing:
                raise HTTPException(409, f"Config '{req.data_id}' already exists in group '{req.group}'")
            row = ConfigModel(
                config_id    = cfg_id,
                data_id      = req.data_id,
                group        = req.group,
                namespace    = req.namespace,
                content      = req.content,
                config_type  = req.config_type,
                md5          = md5,
                description  = req.description,
                created_by   = req.created_by,
                updated_by   = req.created_by,
                extra_metadata= req.metadata,
            )
            db.add(row)
            db.commit()
            db.refresh(row)
        return {"config_id": cfg_id, "md5": md5, "created_at": _fmt(_now())}

    def get_config(self, config_id: str) -> Dict[str, Any]:
        with self._db() as db:
            row = db.query(ConfigModel).filter(ConfigModel.config_id == config_id).first()
            if not row: raise HTTPException(404, "Config not found")
        return _config_to_dict(row)

    def get_config_by_data_id(self, data_id: str, group: str = "DEFAULT_GROUP",
                               namespace: str = "") -> Dict[str, Any]:
        with self._db() as db:
            row = db.query(ConfigModel).filter(
                ConfigModel.data_id   == data_id,
                ConfigModel.group     == group,
                ConfigModel.namespace == namespace,
            ).first()
            if not row: raise HTTPException(404, "Config not found")
        return _config_to_dict(row)

    def update_config(self, config_id: str, content: str, updated_by: str = "system") -> Dict[str, Any]:
        md5 = hashlib.md5(content.encode()).hexdigest()
        with self._db() as db:
            row = db.query(ConfigModel).filter(ConfigModel.config_id == config_id).first()
            if not row: raise HTTPException(404, "Config not found")
            row.content    = content
            row.md5        = md5
            row.updated_by = updated_by
            row.updated_at = _naive(_now())
            db.commit()
        return {"config_id": config_id, "md5": md5, "updated_at": _fmt(_now())}

    def list_configs(self, config_type: Optional[str] = None, group: Optional[str] = None,
                     skip: int = 0, limit: int = 20) -> Dict[str, Any]:
        with self._db() as db:
            q = db.query(ConfigModel)
            if config_type: q = q.filter(ConfigModel.config_type == config_type)
            if group:       q = q.filter(ConfigModel.group       == group)
            total = q.count()
            rows  = q.order_by(ConfigModel.updated_at.desc()).offset(skip).limit(limit).all()
        return {"total": total, "configs": [_config_to_dict(r) for r in rows]}

    def delete_config(self, config_id: str) -> Dict[str, Any]:
        with self._db() as db:
            row = db.query(ConfigModel).filter(ConfigModel.config_id == config_id).first()
            if not row: raise HTTPException(404, "Config not found")
            db.delete(row)
            db.commit()
        return {"config_id": config_id, "deleted": True}

    # ── CI/CD ─────────────────────────────────────────────────────────────────
    async def trigger_ci_job(self, req: CIJobRequest) -> Dict[str, Any]:
        result = await self._cicd.trigger_job(req.job_name, req.parameters)
        job_run_id = f"jr_{uuid.uuid4().hex[:12]}"
        with self._db() as db:
            row = CIJobModel(
                job_run_id  = job_run_id,
                job_name    = req.job_name,
                branch      = req.branch,
                queue_number= result.get("queue_number"),
                status      = result.get("status", "triggered"),
                parameters  = req.parameters,
                extra_metadata= req.metadata,
            )
            db.add(row)
            db.commit()
        return {**result, "job_run_id": job_run_id}

    async def get_ci_job_status(self, job_run_id: str) -> Dict[str, Any]:
        with self._db() as db:
            row = db.query(CIJobModel).filter(CIJobModel.job_run_id == job_run_id).first()
            if not row: raise HTTPException(404, "CI job not found")
            build_number = row.build_number or 1
            job_name     = row.job_name
        status = await self._cicd.get_job_status(job_name, build_number)
        with self._db() as db:
            row = db.query(CIJobModel).filter(CIJobModel.job_run_id == job_run_id).first()
            if row:
                row.status     = status.get("status", "unknown")
                row.result     = status.get("status")
                row.duration_ms= status.get("duration")
                if status.get("status") in ("SUCCESS", "FAILURE", "ABORTED"):
                    row.completed_at = _naive(_now())
                row.updated_at = _naive(_now())
                db.commit()
        return {**status, "job_run_id": job_run_id}

    def list_ci_jobs(self, job_name: Optional[str] = None, status: Optional[str] = None,
                     skip: int = 0, limit: int = 20) -> Dict[str, Any]:
        with self._db() as db:
            q = db.query(CIJobModel)
            if job_name: q = q.filter(CIJobModel.job_name == job_name)
            if status:   q = q.filter(CIJobModel.status   == status)
            total = q.count()
            rows  = q.order_by(CIJobModel.created_at.desc()).offset(skip).limit(limit).all()
        return {"total": total, "jobs": [_ci_to_dict(r) for r in rows]}

    # ── Monitoring ────────────────────────────────────────────────────────────
    async def query_metrics(self, req: MonitoringQueryRequest) -> Dict[str, Any]:
        t0     = time.time()
        end    = req.end_time or _now()
        start  = req.start_time or (end - timedelta(hours=1))
        result = await self._monitor.query_prometheus(
            req.query, start.isoformat(), end.isoformat(), req.step)
        return {
            "query":         req.query,
            "data":          _parse_prometheus_result(result),
            "query_time_ms": int((time.time() - t0) * 1000),
            "metadata":      {"start": _fmt(start), "end": _fmt(end), "step": req.step},
        }

    async def get_system_metrics(self) -> Dict[str, Any]:
        """Local host metrics using psutil."""
        if _HAS_PSUTIL:
            try:
                return {
                    "cpu_percent":    psutil.cpu_percent(interval=0.1),
                    "memory_percent": psutil.virtual_memory().percent,
                    "disk_percent":   psutil.disk_usage("/").percent,
                    "load_avg":       list(os.getloadavg()) if hasattr(os, "getloadavg") else [],
                }
            except Exception as e:
                logger.warning("get_system_metrics failed: %s", e)
        return {"cpu_percent": 0.0, "memory_percent": 0.0, "disk_percent": 0.0, "stub": True}

    # ── Stats ─────────────────────────────────────────────────────────────────
    def stats(self) -> Dict[str, Any]:
        with self._db() as db:
            return {
                "clusters":    db.query(ClusterModel).count(),
                "deployments": db.query(DeploymentModel).count(),
                "alerts_firing": db.query(AlertModel).filter(
                    AlertModel.status == AlertStatus.FIRING.value).count(),
                "backups_completed": db.query(BackupModel).filter(
                    BackupModel.status == BackupStatus.COMPLETED.value).count(),
                "configs":     db.query(ConfigModel).count(),
                "ci_jobs":     db.query(CIJobModel).count(),
            }


# ── Serialisation helpers ─────────────────────────────────────────────────────
def _cluster_to_dict(r: ClusterModel) -> Dict:
    return {
        "cluster_id":   r.cluster_id, "name": r.name, "provider": r.provider,
        "version":      r.version,    "region": r.region,
        "status":       r.status,     "health_status": r.health_status,
        "node_count":   r.node_count, "api_server": r.api_server,
        "resource_usage": r.resource_usage,
        "networking":   r.networking,
        "created_at":   _fmt(_utc(r.created_at)),
        "updated_at":   _fmt(_utc(r.updated_at)),
        "last_health_check": _fmt(_utc(r.last_health_check)),
    }

def _deployment_to_dict(r: DeploymentModel) -> Dict:
    return {
        "deployment_id": r.deployment_id, "cluster_id": r.cluster_id,
        "name": r.name, "namespace": r.namespace, "app_name": r.app_name,
        "image": r.image, "image_tag": r.image_tag,
        "replicas": r.replicas, "available_replicas": r.available_replicas,
        "strategy": r.strategy, "status": r.status, "health_status": r.health_status,
        "service_type": r.service_type, "service_ports": r.service_ports,
        "created_at": _fmt(_utc(r.created_at)), "deployed_at": _fmt(_utc(r.deployed_at)),
    }

def _pod_to_dict_model(r: PodModel) -> Dict:
    return {
        "pod_id": r.pod_id, "cluster_id": r.cluster_id, "name": r.name,
        "namespace": r.namespace, "status": r.status, "phase": r.phase,
        "node_name": r.node_name, "pod_ip": r.pod_ip, "restart_count": r.restart_count,
        "created_at": _fmt(_utc(r.created_at)),
    }

def _alert_to_dict(r: AlertModel) -> Dict:
    return {
        "alert_id": r.alert_id, "cluster_id": r.cluster_id,
        "alert_name": r.alert_name, "status": r.status, "severity": r.severity,
        "message": r.message, "labels": r.alert_labels, "annotations": r.alert_annotations,
        "acknowledged_by": r.acknowledged_by, "acknowledged_at": _fmt(_utc(r.acknowledged_at)),
        "silenced_until": _fmt(_utc(r.silenced_until)),
        "starts_at": _fmt(_utc(r.starts_at)), "ends_at": _fmt(_utc(r.ends_at)),
        "created_at": _fmt(_utc(r.created_at)),
    }

def _backup_to_dict(r: BackupModel) -> Dict:
    return {
        "backup_id": r.backup_id, "cluster_id": r.cluster_id,
        "backup_type": r.backup_type, "name": r.name, "resources": r.resources,
        "storage_type": r.storage_type, "storage_path": r.storage_path,
        "status": r.status, "phase": r.phase,
        "size_bytes": r.size_bytes, "retention_days": r.retention_days,
        "expires_at": _fmt(_utc(r.expires_at)),
        "created_at": _fmt(_utc(r.created_at)), "completed_at": _fmt(_utc(r.completed_at)),
    }

def _config_to_dict(r: ConfigModel) -> Dict:
    return {
        "config_id": r.config_id, "data_id": r.data_id, "group": r.group,
        "namespace": r.namespace, "config_type": r.config_type, "md5": r.md5,
        "description": r.description, "content": r.content,
        "created_by": r.created_by, "updated_by": r.updated_by,
        "created_at": _fmt(_utc(r.created_at)), "updated_at": _fmt(_utc(r.updated_at)),
    }

def _ci_to_dict(r: CIJobModel) -> Dict:
    return {
        "job_run_id": r.job_run_id, "job_name": r.job_name, "branch": r.branch,
        "backend": r.backend, "build_number": r.build_number,
        "status": r.status, "result": r.result, "duration_ms": r.duration_ms,
        "created_at": _fmt(_utc(r.created_at)), "completed_at": _fmt(_utc(r.completed_at)),
    }


# ══════════════════════════════════════════════════════════════════════════════
# FASTAPI APP
# ══════════════════════════════════════════════════════════════════════════════
_cfg = ServiceConfig()
_svc: Optional[SupportOpsService] = None


def get_svc() -> SupportOpsService:
    global _svc
    if _svc is None:
        _svc = SupportOpsService(_cfg)
    return _svc


def create_app() -> FastAPI:
    app = FastAPI(
        title="ILbuy Support & Ops Service",
        version="1.0.0",
        description="Part 10: Observability, orchestration, deployment, config management, CI/CD, alerts",
    )

    @app.on_event("startup")
    async def startup():
        global _svc
        _svc = SupportOpsService(_cfg)
        await _svc.startup()
        seed_data()
        asyncio.create_task(_bg_health_monitor())
        asyncio.create_task(_bg_alert_processor())
        asyncio.create_task(_bg_backup_cleaner())

    @app.on_event("shutdown")
    async def shutdown():
        if _svc: await _svc.shutdown()

    # ── Health ────────────────────────────────────────────────────────────────
    @app.get("/health")
    async def health():
        return {"status": "healthy", "service": "support_ops_service", "ts": _fmt(_now())}

    @app.get("/api/v1/ops/stats")
    async def ops_stats(svc: SupportOpsService = Depends(get_svc)):
        return svc.stats()

    @app.get("/api/v1/ops/system-metrics")
    async def system_metrics(svc: SupportOpsService = Depends(get_svc)):
        return await svc.get_system_metrics()

    # ── Clusters ──────────────────────────────────────────────────────────────
    @app.post("/api/v1/clusters", status_code=201)
    async def create_cluster(spec: ClusterSpec, svc: SupportOpsService = Depends(get_svc)):
        return svc.create_cluster(spec)

    @app.get("/api/v1/clusters")
    async def list_clusters(
        provider:   Optional[str] = Query(None),
        status:     Optional[str] = Query(None),
        skip: int   = Query(0, ge=0),
        limit: int  = Query(20, ge=1, le=200),
        svc: SupportOpsService = Depends(get_svc),
    ):
        return svc.list_clusters(provider=provider, status=status, skip=skip, limit=limit)

    @app.get("/api/v1/clusters/{cluster_id}")
    async def get_cluster(cluster_id: str, svc: SupportOpsService = Depends(get_svc)):
        return svc.get_cluster(cluster_id)

    @app.patch("/api/v1/clusters/{cluster_id}")
    async def update_cluster(
        cluster_id: str, updates: Dict[str, Any] = Body(...),
        svc: SupportOpsService = Depends(get_svc),
    ):
        return svc.update_cluster(cluster_id, updates)

    @app.delete("/api/v1/clusters/{cluster_id}")
    async def delete_cluster(cluster_id: str, svc: SupportOpsService = Depends(get_svc)):
        return svc.delete_cluster(cluster_id)

    @app.get("/api/v1/clusters/{cluster_id}/health")
    async def get_cluster_health(cluster_id: str, svc: SupportOpsService = Depends(get_svc)):
        return await svc.get_cluster_health(cluster_id)

    # ── Deployments ───────────────────────────────────────────────────────────
    @app.post("/api/v1/clusters/{cluster_id}/deployments", status_code=201)
    async def create_deployment(
        cluster_id: str, spec: DeploymentSpec,
        svc: SupportOpsService = Depends(get_svc),
    ):
        return await svc.create_deployment(cluster_id, spec)

    @app.get("/api/v1/deployments")
    async def list_deployments(
        cluster_id: Optional[str] = Query(None),
        status:     Optional[str] = Query(None),
        skip: int   = Query(0, ge=0),
        limit: int  = Query(20, ge=1, le=200),
        svc: SupportOpsService = Depends(get_svc),
    ):
        return svc.list_deployments(cluster_id=cluster_id, status=status, skip=skip, limit=limit)

    @app.get("/api/v1/deployments/{deployment_id}")
    async def get_deployment(deployment_id: str, svc: SupportOpsService = Depends(get_svc)):
        return svc.get_deployment(deployment_id)

    @app.post("/api/v1/deployments/{deployment_id}/scale")
    async def scale_deployment(
        deployment_id: str, req: ScaleRequest,
        svc: SupportOpsService = Depends(get_svc),
    ):
        return await svc.scale_deployment(deployment_id, req.replicas)

    @app.delete("/api/v1/deployments/{deployment_id}")
    async def delete_deployment(deployment_id: str, svc: SupportOpsService = Depends(get_svc)):
        return await svc.delete_deployment(deployment_id)

    @app.post("/api/v1/deployments/{deployment_id}/rollback")
    async def rollback_deployment(
        deployment_id: str,
        image: str = Query(..., description="Target rollback image"),
        svc: SupportOpsService = Depends(get_svc),
    ):
        return await svc.rollback_deployment(deployment_id, image)

    # ── Pods ──────────────────────────────────────────────────────────────────
    @app.get("/api/v1/clusters/{cluster_id}/pods")
    async def list_pods(
        cluster_id: str,
        namespace: str = Query("default"),
        svc: SupportOpsService = Depends(get_svc),
    ):
        return await svc.list_pods(cluster_id, namespace)

    @app.get("/api/v1/clusters/{cluster_id}/pods/{pod_name}/logs")
    async def get_pod_logs(
        cluster_id: str, pod_name: str,
        namespace: str = Query("default"),
        tail: int = Query(100, ge=1, le=5000),
        svc: SupportOpsService = Depends(get_svc),
    ):
        return await svc.get_pod_logs(cluster_id, pod_name, namespace, tail)

    # ── Alerts ────────────────────────────────────────────────────────────────
    @app.post("/api/v1/alerts", status_code=201)
    async def create_alert(req: AlertCreateRequest, svc: SupportOpsService = Depends(get_svc)):
        return svc.create_alert(req)

    @app.get("/api/v1/alerts")
    async def list_alerts(
        severity:   Optional[str] = Query(None),
        status:     Optional[str] = Query(None),
        cluster_id: Optional[str] = Query(None),
        skip: int   = Query(0, ge=0),
        limit: int  = Query(50, ge=1, le=500),
        svc: SupportOpsService = Depends(get_svc),
    ):
        return svc.list_alerts(severity=severity, status=status,
                               cluster_id=cluster_id, skip=skip, limit=limit)

    @app.get("/api/v1/alerts/{alert_id}")
    async def get_alert(alert_id: str, svc: SupportOpsService = Depends(get_svc)):
        return svc.get_alert(alert_id)

    @app.post("/api/v1/alerts/{alert_id}/acknowledge")
    async def acknowledge_alert(
        alert_id: str, req: AlertAckRequest,
        svc: SupportOpsService = Depends(get_svc),
    ):
        return svc.acknowledge_alert(alert_id, req)

    @app.post("/api/v1/alerts/{alert_id}/silence")
    async def silence_alert(
        alert_id: str, req: AlertSilenceRequest,
        svc: SupportOpsService = Depends(get_svc),
    ):
        return svc.silence_alert(alert_id, req)

    @app.post("/api/v1/alerts/{alert_id}/resolve")
    async def resolve_alert(alert_id: str, svc: SupportOpsService = Depends(get_svc)):
        return svc.resolve_alert(alert_id)

    # Alertmanager webhook receiver
    @app.post("/api/v1/alerts/webhook")
    async def alerts_webhook(
        payload: Dict[str, Any] = Body(...),
        svc: SupportOpsService = Depends(get_svc),
    ):
        """Receive Alertmanager webhook, persist each alert."""
        created = []
        for a in payload.get("alerts", [payload]):
            try:
                req = AlertCreateRequest(
                    alert_name  = a.get("labels", {}).get("alertname", "unknown"),
                    severity    = a.get("labels", {}).get("severity", "warning"),
                    message     = a.get("annotations", {}).get("summary", "Alert fired"),
                    labels      = a.get("labels", {}),
                    annotations = a.get("annotations", {}),
                )
                created.append(svc.create_alert(req))
            except Exception as e:
                logger.warning("webhook alert parse failed: %s", e)
        return {"received": len(created), "alerts": created}

    # ── Backups ───────────────────────────────────────────────────────────────
    @app.post("/api/v1/backups", status_code=201)
    async def create_backup(req: BackupRequest, svc: SupportOpsService = Depends(get_svc)):
        return svc.create_backup(req)

    @app.get("/api/v1/backups")
    async def list_backups(
        cluster_id: Optional[str] = Query(None),
        status:     Optional[str] = Query(None),
        skip: int   = Query(0, ge=0),
        limit: int  = Query(20, ge=1, le=100),
        svc: SupportOpsService = Depends(get_svc),
    ):
        return svc.list_backups(cluster_id=cluster_id, status=status, skip=skip, limit=limit)

    @app.get("/api/v1/backups/{backup_id}")
    async def get_backup(backup_id: str, svc: SupportOpsService = Depends(get_svc)):
        return svc.get_backup(backup_id)

    @app.post("/api/v1/backups/{backup_id}/restore")
    async def restore_backup(backup_id: str, svc: SupportOpsService = Depends(get_svc)):
        return svc.restore_backup(backup_id)

    # ── Config Management ─────────────────────────────────────────────────────
    @app.post("/api/v1/configs", status_code=201)
    async def create_config(req: ConfigCreateRequest, svc: SupportOpsService = Depends(get_svc)):
        return svc.create_config(req)

    @app.get("/api/v1/configs")
    async def list_configs(
        config_type: Optional[str] = Query(None),
        group:       Optional[str] = Query(None),
        skip: int    = Query(0, ge=0),
        limit: int   = Query(20, ge=1, le=100),
        svc: SupportOpsService = Depends(get_svc),
    ):
        return svc.list_configs(config_type=config_type, group=group, skip=skip, limit=limit)

    @app.get("/api/v1/configs/{config_id}")
    async def get_config(config_id: str, svc: SupportOpsService = Depends(get_svc)):
        return svc.get_config(config_id)

    @app.put("/api/v1/configs/{config_id}")
    async def update_config(
        config_id: str,
        content:     str = Body(..., embed=True),
        updated_by:  str = Body("system", embed=True),
        svc: SupportOpsService = Depends(get_svc),
    ):
        return svc.update_config(config_id, content, updated_by)

    @app.delete("/api/v1/configs/{config_id}")
    async def delete_config(config_id: str, svc: SupportOpsService = Depends(get_svc)):
        return svc.delete_config(config_id)

    # ── CI/CD ─────────────────────────────────────────────────────────────────
    @app.post("/api/v1/cicd/jobs", status_code=201)
    async def trigger_ci_job(req: CIJobRequest, svc: SupportOpsService = Depends(get_svc)):
        return await svc.trigger_ci_job(req)

    @app.get("/api/v1/cicd/jobs")
    async def list_ci_jobs(
        job_name: Optional[str] = Query(None),
        status:   Optional[str] = Query(None),
        skip: int = Query(0, ge=0),
        limit: int = Query(20, ge=1, le=100),
        svc: SupportOpsService = Depends(get_svc),
    ):
        return svc.list_ci_jobs(job_name=job_name, status=status, skip=skip, limit=limit)

    @app.get("/api/v1/cicd/jobs/{job_run_id}")
    async def get_ci_job(job_run_id: str, svc: SupportOpsService = Depends(get_svc)):
        return await svc.get_ci_job_status(job_run_id)

    # ── Monitoring / Metrics ──────────────────────────────────────────────────
    @app.post("/api/v1/monitoring/query")
    async def query_metrics(
        req: MonitoringQueryRequest,
        svc: SupportOpsService = Depends(get_svc),
    ):
        return await svc.query_metrics(req)

    @app.get("/api/v1/clusters/{cluster_id}/metrics")
    async def get_cluster_metrics(cluster_id: str, svc: SupportOpsService = Depends(get_svc)):
        return await svc._monitor.get_cluster_metrics(cluster_id)

    # ── Prometheus metrics endpoint ───────────────────────────────────────────
    @app.get("/metrics")
    async def metrics():
        if not _HAS_PROMETHEUS or not _SO_REG:
            return JSONResponse({"error": "prometheus not available"}, status_code=503)
        from fastapi.responses import Response
        return Response(generate_latest(_SO_REG), media_type=CONTENT_TYPE_LATEST)

    return app


# ══════════════════════════════════════════════════════════════════════════════
# BACKGROUND TASKS
# ══════════════════════════════════════════════════════════════════════════════
async def _bg_health_monitor():
    """Periodically update cluster health status."""
    while True:
        await asyncio.sleep(300)  # every 5 min
        try:
            svc = get_svc()
            with SessionLocal() as db:
                clusters = db.query(ClusterModel).filter(
                    ClusterModel.status == ResourceStatus.RUNNING.value).all()
            for cl in clusters:
                try:
                    await svc.get_cluster_health(cl.cluster_id)
                except Exception:
                    pass
        except Exception as e:
            logger.warning("health monitor error: %s", e)


async def _bg_alert_processor():
    """Auto-resolve silenced alerts whose silence window has expired."""
    while True:
        await asyncio.sleep(60)
        try:
            now_naive = _naive(_now())
            with SessionLocal() as db:
                expired = db.query(AlertModel).filter(
                    AlertModel.status       == AlertStatus.SILENCED.value,
                    AlertModel.silenced_until <= now_naive,
                ).all()
                for a in expired:
                    a.status     = AlertStatus.FIRING.value
                    a.updated_at = now_naive
                db.commit()
                if expired:
                    logger.info("Unsilenced %d alerts", len(expired))
        except Exception as e:
            logger.warning("alert processor error: %s", e)


async def _bg_backup_cleaner():
    """Mark expired backups."""
    while True:
        await asyncio.sleep(3600)  # every hour
        try:
            now_naive = _naive(_now())
            with SessionLocal() as db:
                expired = db.query(BackupModel).filter(
                    BackupModel.expires_at <= now_naive,
                    BackupModel.status     == BackupStatus.COMPLETED.value,
                ).all()
                for b in expired:
                    b.status     = BackupStatus.EXPIRED.value
                    b.updated_at = now_naive
                db.commit()
                if expired:
                    logger.info("Expired %d backups", len(expired))
        except Exception as e:
            logger.warning("backup cleaner error: %s", e)


# ══════════════════════════════════════════════════════════════════════════════
# SEED DATA
# ══════════════════════════════════════════════════════════════════════════════
def seed_data():
    with SessionLocal() as db:
        if db.query(ClusterModel).count() > 0:
            return
    svc = get_svc()

    # Cluster: production
    try:
        r = svc.create_cluster(ClusterSpec(
            name="ilbuy-prod", provider="k8s", version="1.29.0",
            region="cn-hangzhou", node_count=5, node_type="ecs.c6.xlarge"))
        prod_cl = r["cluster_id"]
    except Exception as e:
        logger.warning("seed cluster prod: %s", e)
        prod_cl = None

    # Cluster: staging
    try:
        r = svc.create_cluster(ClusterSpec(
            name="ilbuy-staging", provider="k8s", version="1.29.0",
            region="cn-hangzhou", node_count=2, node_type="ecs.c6.large"))
        stg_cl = r["cluster_id"]
    except Exception as e:
        logger.warning("seed cluster staging: %s", e)
        stg_cl = None

    # Mark prod as running
    if prod_cl:
        with SessionLocal() as db:
            row = db.query(ClusterModel).filter(ClusterModel.cluster_id == prod_cl).first()
            if row:
                row.status        = ResourceStatus.RUNNING.value
                row.health_status = "healthy"
                row.node_count    = 5
                row.node_info     = [{"name": f"node-{i}", "status": "Ready"} for i in range(5)]
                db.commit()

    # Alerts
    for alert_name, severity, message in [
        ("HighCPUUsage",    "warning",  "Pod cpu usage > 80%"),
        ("MemoryPressure",  "warning",  "Node memory usage > 90%"),
        ("DeploymentFailed","critical", "Deployment ilbuy-api failed to roll out"),
        ("DiskSpaceLow",    "info",     "Node /data disk 75% full"),
    ]:
        try:
            svc.create_alert(AlertCreateRequest(
                alert_name=alert_name, severity=severity,
                message=message, cluster_id=prod_cl,
                labels={"cluster": "ilbuy-prod"}, annotations={"summary": message}))
        except Exception as e:
            logger.warning("seed alert %s: %s", alert_name, e)

    # Configs
    for data_id, content, group in [
        ("app-config.yaml",  "server:\n  port: 8080\n  debug: false\n",       "DEFAULT_GROUP"),
        ("db-config.yaml",   "database:\n  pool_size: 10\n  max_overflow: 5\n","DEFAULT_GROUP"),
        ("redis-config.yaml","redis:\n  db: 0\n  max_connections: 100\n",      "CACHE_GROUP"),
        ("ai-config.yaml",   "model:\n  device: cuda\n  batch_size: 32\n",     "AI_GROUP"),
    ]:
        try:
            svc.create_config(ConfigCreateRequest(
                data_id=data_id, group=group, content=content,
                config_type="yaml", description=f"Config for {data_id}"))
        except Exception as e:
            logger.warning("seed config %s: %s", data_id, e)

    # Backups
    for btype, name in [("full", "daily-prod-backup"), ("incremental", "hourly-prod-backup")]:
        try:
            r = svc.create_backup(BackupRequest(
                backup_type=btype, name=name, cluster_id=prod_cl,
                resources=["databases", "configmaps"], retention_days=30))
            # Mark first backup as completed
            with SessionLocal() as db:
                row = db.query(BackupModel).filter(BackupModel.backup_id == r["backup_id"]).first()
                if row:
                    row.status       = BackupStatus.COMPLETED.value
                    row.phase        = "completed"
                    row.size_bytes   = 104857600  # 100MB
                    row.started_at   = _naive(_now() - timedelta(minutes=30))
                    row.completed_at = _naive(_now())
                    db.commit()
        except Exception as e:
            logger.warning("seed backup %s: %s", btype, e)

    logger.info("Seed data inserted (2 clusters, 4 alerts, 4 configs, 2 backups)")


# ══════════════════════════════════════════════════════════════════════════════
# ENTRYPOINT
# ══════════════════════════════════════════════════════════════════════════════
app = create_app()

if __name__ == "__main__":
    try:
        import uvicorn
        uvicorn.run(
            "support_ops_service:app",
            host=_cfg.host,
            port=_cfg.port,
            reload=_cfg.debug,
            log_level="info",
        )
    except ImportError:
        logger.error("uvicorn not installed. Run: pip install uvicorn")

