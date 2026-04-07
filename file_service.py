"""
file_service.py — Production-grade File Service (Part 11)
Async FastAPI microservice for file storage, processing, and distribution.
Features: B2B batch/watermark/OCR/version-control, B2C beautify/collage/filters/sharing.
"""

from __future__ import annotations

import asyncio
import base64
import csv
import hashlib
import io
import json
import logging
import mimetypes
import os
import re
import secrets
import shutil
import tempfile
import time
import uuid
import zipfile
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ── optional deps ──────────────────────────────────────────────────────────────
try:
    from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont
    _HAS_PIL = True
except ImportError:
    _HAS_PIL = False

try:
    import minio as _minio_mod
    from minio.error import S3Error as _S3Error
    _HAS_MINIO = True
except ImportError:
    _HAS_MINIO = False

try:
    import boto3 as _boto3
    _HAS_BOTO3 = True
except ImportError:
    _HAS_BOTO3 = False

try:
    import magic as _magic
    _HAS_MAGIC = True
except ImportError:
    _HAS_MAGIC = False

try:
    import pytesseract as _tesseract
    _HAS_OCR = True
except ImportError:
    _HAS_OCR = False

try:
    from pypdf import PdfReader as _PdfReader
    _HAS_PDF = True
except ImportError:
    _HAS_PDF = False

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
    import yaml as _yaml_mod
    _HAS_YAML = True
except ImportError:
    _HAS_YAML = False

try:
    from prometheus_client import (
        CollectorRegistry, Counter, Gauge, Histogram,
        generate_latest, CONTENT_TYPE_LATEST,
    )
    _HAS_PROMETHEUS = True
except ImportError:
    _HAS_PROMETHEUS = False

from fastapi import (
    BackgroundTasks, Depends, FastAPI, File, Form, HTTPException,
    Query, UploadFile,
)
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import (
    Boolean, Column, DateTime, Float, Index, Integer, String, Text,
    UniqueConstraint, and_, func, or_, select, update,
)
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# ── logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("file_service")

# ── enums ──────────────────────────────────────────────────────────────────────
class FileType(str, Enum):
    IMAGE    = "image"
    VIDEO    = "video"
    DOCUMENT = "document"
    AUDIO    = "audio"
    ARCHIVE  = "archive"
    DATA     = "data"
    OTHER    = "other"

class StorageProvider(str, Enum):
    LOCAL = "local"
    MINIO = "minio"
    S3    = "s3"

class FileStatus(str, Enum):
    UPLOADING  = "uploading"
    PROCESSING = "processing"
    ACTIVE     = "active"
    ARCHIVED   = "archived"
    DELETED    = "deleted"
    BLOCKED    = "blocked"

class AccessLevel(str, Enum):
    PRIVATE   = "private"
    PUBLIC    = "public"
    PROTECTED = "protected"
    SHARED    = "shared"
    INTERNAL  = "internal"

class WatermarkType(str, Enum):
    TEXT   = "text"
    IMAGE  = "image"
    QRCODE = "qrcode"

class ProcessingStatus(str, Enum):
    PENDING    = "pending"
    PROCESSING = "processing"
    COMPLETED  = "completed"
    FAILED     = "failed"

# ── ServiceConfig ──────────────────────────────────────────────────────────────
class ServiceConfig:
    DB_URL:              str  = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./file_service.db")
    REDIS_URL:           str  = os.getenv("REDIS_URL", "redis://localhost:6379/6")
    HOST:                str  = os.getenv("HOST", "0.0.0.0")
    PORT:                int  = int(os.getenv("PORT", "8007"))
    # Storage
    STORAGE_BASE:        str  = os.getenv("STORAGE_BASE", "./file_service_data")
    STORAGE_TEMP:        str  = os.getenv("STORAGE_TEMP", "./file_service_temp")
    MINIO_ENDPOINT:      str  = os.getenv("MINIO_ENDPOINT", "localhost:9000")
    MINIO_ACCESS_KEY:    str  = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    MINIO_SECRET_KEY:    str  = os.getenv("MINIO_SECRET_KEY", "minioadmin")
    MINIO_SECURE:        bool = os.getenv("MINIO_SECURE", "false").lower() == "true"
    DEFAULT_PROVIDER:    str  = os.getenv("DEFAULT_PROVIDER", "local")
    # Limits
    MAX_FILE_MB:         int  = int(os.getenv("MAX_FILE_MB", "500"))
    ALLOWED_EXTENSIONS:  set  = {
        "jpg","jpeg","png","gif","bmp","webp","svg","tiff",
        "mp4","avi","mov","wmv","mkv","webm",
        "pdf","doc","docx","xls","xlsx","ppt","pptx","txt","csv","md",
        "zip","rar","7z","tar","gz",
        "json","xml","yaml","yml",
    }
    # Processing
    THUMB_SIZES: List[Dict] = [
        {"size_type": "small",  "width": 100, "height": 100, "quality": 80},
        {"size_type": "medium", "width": 400, "height": 400, "quality": 85},
        {"size_type": "large",  "width": 800, "height": 800, "quality": 85},
    ]
    IMG_QUALITY:         int  = int(os.getenv("IMG_QUALITY", "85"))
    # B2B
    B2B_MAX_BATCH:       int  = int(os.getenv("B2B_MAX_BATCH", "100"))
    # Cleanup
    TEMP_TTL_HOURS:      int  = int(os.getenv("TEMP_TTL_HOURS", "24"))
    DELETED_TTL_DAYS:    int  = int(os.getenv("DELETED_TTL_DAYS", "30"))
    SECRET_KEY:          str  = os.getenv("SECRET_KEY", secrets.token_hex(32))

    @classmethod
    def ensure_dirs(cls):
        for d in [cls.STORAGE_BASE, cls.STORAGE_TEMP]:
            Path(d).mkdir(parents=True, exist_ok=True)
        for sub in ["b2b", "b2c", "temp", "archive", "thumbnails"]:
            (Path(cls.STORAGE_BASE) / sub).mkdir(parents=True, exist_ok=True)

# ── ORM ────────────────────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    pass

def _now() -> datetime:
    return datetime.now(timezone.utc)

class FileRecord(Base):
    __tablename__ = "t_files"

    id                = Column(Integer, primary_key=True, autoincrement=True)
    file_id           = Column(String(64), unique=True, nullable=False)
    filename          = Column(String(500), nullable=False)
    original_filename = Column(String(500), nullable=False)
    file_type         = Column(String(20), nullable=False)
    content_type      = Column(String(100), nullable=False)
    extension         = Column(String(20), nullable=False)
    size              = Column(Integer, nullable=False)
    md5               = Column(String(32), nullable=False)
    sha256            = Column(String(64), nullable=True)
    width             = Column(Integer, nullable=True)
    height            = Column(Integer, nullable=True)
    duration          = Column(Float, nullable=True)
    page_count        = Column(Integer, nullable=True)
    storage_provider  = Column(String(20), nullable=False, default="local")
    storage_path      = Column(String(1000), nullable=False)
    bucket            = Column(String(100), nullable=False)
    object_key        = Column(String(500), nullable=False)
    access_level      = Column(String(20), nullable=False, default="private")
    status            = Column(String(20), nullable=False, default="active")
    is_encrypted      = Column(Boolean, nullable=False, default=False)
    user_id           = Column(String(64), nullable=False)
    user_role         = Column(String(20), nullable=False, default="user")
    company_id        = Column(String(64), nullable=True)
    project_id        = Column(String(64), nullable=True)
    category          = Column(String(100), nullable=True)
    description       = Column(Text, nullable=True)
    tags              = Column("file_tags",         JSON, nullable=True)
    version           = Column(Integer, nullable=False, default=1)
    parent_file_id    = Column(String(64), nullable=True)
    is_latest         = Column(Boolean, nullable=False, default=True)
    proc_status       = Column(String(20), nullable=False, default="completed")
    proc_options      = Column("proc_options",      JSON, nullable=True)
    processed_files   = Column("processed_files",   JSON, nullable=True)
    thumbnails        = Column("file_thumbnails",   JSON, nullable=True)
    download_count    = Column(Integer, nullable=False, default=0)
    view_count        = Column(Integer, nullable=False, default=0)
    share_count       = Column(Integer, nullable=False, default=0)
    watermark_type    = Column(String(20), nullable=True)
    watermark_conf    = Column("wm_config",         JSON, nullable=True)
    ocr_text          = Column(Text, nullable=True)
    expires_at        = Column(DateTime(timezone=True), nullable=True)
    deleted_at        = Column(DateTime(timezone=True), nullable=True)
    uploaded_by       = Column(String(64), nullable=False, default="system")
    updated_by        = Column(String(64), nullable=False, default="system")
    extra_metadata    = Column("file_metadata",     JSON, nullable=True)
    created_at        = Column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at        = Column(DateTime(timezone=True), nullable=False, default=_now, onupdate=_now)

    __table_args__ = (
        Index("idx_file_user_status",    "user_id", "status"),
        Index("idx_file_company",        "company_id", "status"),
        Index("idx_file_type",           "file_type", "status"),
        Index("idx_file_access",         "access_level", "status"),
        Index("idx_file_md5",            "md5"),
        Index("idx_file_parent",         "parent_file_id"),
        Index("idx_file_created",        "created_at"),
    )

class FileShare(Base):
    __tablename__ = "t_file_shares"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    share_id       = Column(String(64), unique=True, nullable=False)
    file_id        = Column(String(64), nullable=False)
    share_type     = Column(String(20), nullable=False, default="link")
    access_token   = Column(String(100), unique=True, nullable=False)
    password_hash  = Column(String(100), nullable=True)
    short_code     = Column(String(20), unique=True, nullable=True)
    can_download   = Column(Boolean, nullable=False, default=True)
    can_view       = Column(Boolean, nullable=False, default=True)
    max_downloads  = Column(Integer, nullable=True)
    download_count = Column(Integer, nullable=False, default=0)
    view_count     = Column(Integer, nullable=False, default=0)
    recipient_email = Column(String(255), nullable=True)
    message        = Column(Text, nullable=True)
    is_active      = Column(Boolean, nullable=False, default=True)
    created_by     = Column(String(64), nullable=False, default="system")
    expires_at     = Column(DateTime(timezone=True), nullable=True)
    last_accessed  = Column(DateTime(timezone=True), nullable=True)
    extra_metadata = Column("share_metadata", JSON, nullable=True)
    created_at     = Column(DateTime(timezone=True), nullable=False, default=_now)

    __table_args__ = (
        Index("idx_share_file",  "file_id", "is_active"),
        Index("idx_share_token", "access_token"),
        Index("idx_share_code",  "short_code"),
        Index("idx_share_exp",   "expires_at", "is_active"),
    )

class FileActivity(Base):
    __tablename__ = "t_file_activities"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    activity_id    = Column(String(64), unique=True, nullable=False)
    file_id        = Column(String(64), nullable=False)
    activity_type  = Column(String(50), nullable=False)
    activity_action = Column(String(100), nullable=False)
    result         = Column(String(20), nullable=False, default="success")
    performed_by   = Column(String(64), nullable=True)
    ip_address     = Column(String(50), nullable=True)
    user_agent     = Column(String(300), nullable=True)
    extra_metadata = Column("activity_metadata", JSON, nullable=True)
    created_at     = Column(DateTime(timezone=True), nullable=False, default=_now)

    __table_args__ = (
        Index("idx_act_file",  "file_id", "activity_type"),
        Index("idx_act_user",  "performed_by"),
        Index("idx_act_time",  "created_at"),
    )

class FileProcessingJob(Base):
    __tablename__ = "t_file_processing"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    job_id         = Column(String(64), unique=True, nullable=False)
    file_id        = Column(String(64), nullable=False)
    job_type       = Column(String(50), nullable=False)
    status         = Column(String(20), nullable=False, default="pending")
    operations     = Column("job_operations", JSON, nullable=True)
    output_file_id = Column(String(64), nullable=True)
    output_size    = Column(Integer, nullable=True)
    proc_time_ms   = Column(Integer, nullable=True)
    error_message  = Column(Text, nullable=True)
    callback_url   = Column(String(500), nullable=True)
    retry_count    = Column(Integer, nullable=False, default=0)
    extra_metadata = Column("job_metadata", JSON, nullable=True)
    created_at     = Column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at     = Column(DateTime(timezone=True), nullable=False, default=_now, onupdate=_now)
    completed_at   = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_job_file",   "file_id", "status"),
        Index("idx_job_type",   "job_type", "status"),
    )

# ── Pydantic v2 models ─────────────────────────────────────────────────────────
class UploadOptions(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    user_id:          str
    user_role:        str = "user"
    access_level:     AccessLevel = AccessLevel.PRIVATE
    category:         Optional[str] = None
    tags:             List[str] = Field(default_factory=list)
    description:      Optional[str] = None
    expire_days:      Optional[int] = None
    watermark:        Optional[Dict[str, Any]] = None
    add_watermark:    bool = False
    generate_thumbs:  bool = True
    run_ocr:          bool = False
    project_id:       Optional[str] = None
    company_id:       Optional[str] = None
    extra_metadata:   Dict[str, Any] = Field(default_factory=dict)

class ShareRequest(BaseModel):
    file_id:       str
    share_type:    str = "link"
    expire_days:   Optional[int] = Field(None, ge=1, le=365)
    password:      Optional[str] = None
    max_downloads: Optional[int] = Field(None, ge=1)
    recipient_email: Optional[str] = None
    message:       Optional[str] = None
    can_download:  bool = True

class SearchRequest(BaseModel):
    query:        Optional[str] = None
    file_type:    Optional[str] = None
    tags:         Optional[List[str]] = None
    start_date:   Optional[datetime] = None
    end_date:     Optional[datetime] = None
    min_size:     Optional[int] = None
    max_size:     Optional[int] = None
    user_id:      Optional[str] = None
    company_id:   Optional[str] = None
    access_level: Optional[str] = None
    status:       Optional[str] = None
    page:         int = Field(1, ge=1)
    page_size:    int = Field(20, ge=1, le=200)
    sort_by:      str = "created_at"
    sort_order:   str = "desc"

class ProcessingRequest(BaseModel):
    file_id:       str
    operations:    List[Dict[str, Any]]
    output_format: Optional[str] = None
    quality:       Optional[int] = Field(None, ge=1, le=100)
    watermark:     Optional[Dict[str, Any]] = None
    callback_url:  Optional[str] = None

class BeautifyRequest(BaseModel):
    file_id:     str
    brightness:  float = Field(1.0, ge=0.1, le=3.0)
    contrast:    float = Field(1.0, ge=0.1, le=3.0)
    saturation:  float = Field(1.0, ge=0.1, le=3.0)
    sharpness:   float = Field(1.0, ge=0.1, le=3.0)
    filter_type: Optional[str] = None   # blur, sharpen, contour, edge_enhance
    blur_radius: float = Field(0.0, ge=0.0, le=10.0)
    output_format: str = "jpeg"
    quality:     int = Field(85, ge=1, le=100)

class WatermarkRequest(BaseModel):
    file_id:      str
    wm_type:      WatermarkType = WatermarkType.TEXT
    text:         Optional[str] = None
    font_size:    int = Field(24, ge=8, le=120)
    color:        str = "#888888"
    opacity:      float = Field(0.5, ge=0.0, le=1.0)
    position:     str = "bottom-right"  # top-left, top-right, bottom-left, bottom-right, center
    output_format: str = "jpeg"
    quality:      int = Field(85, ge=1, le=100)

class CollageRequest(BaseModel):
    file_ids:  List[str] = Field(..., min_length=2, max_length=9)
    layout:    str = "grid"   # grid, horizontal, vertical
    gap:       int = Field(10, ge=0, le=50)
    bg_color:  str = "#ffffff"
    output_format: str = "jpeg"
    quality:   int = Field(85, ge=1, le=100)

    @field_validator("file_ids")
    @classmethod
    def validate_count(cls, v: List[str]) -> List[str]:
        if len(v) < 2:
            raise ValueError("collage需要至少2个文件")
        return v

class B2BBatchRequest(BaseModel):
    user_id:           str
    company_id:        str
    project_id:        Optional[str] = None
    access_level:      AccessLevel = AccessLevel.PRIVATE
    tags:              List[str] = Field(default_factory=list)
    category:          Optional[str] = None
    watermark_config:  Optional[Dict[str, Any]] = None
    run_ocr:           bool = False
    processing_pipeline: List[str] = Field(default_factory=list)
    extra_metadata:    Dict[str, Any] = Field(default_factory=dict)

class VersionCreateRequest(BaseModel):
    file_id:       str
    user_id:       str
    change_note:   Optional[str] = None

class ExportRequest(BaseModel):
    company_id:   Optional[str] = None
    user_id:      Optional[str] = None
    file_type:    Optional[str] = None
    start_date:   Optional[datetime] = None
    end_date:     Optional[datetime] = None
    format:       str = "json"   # json, csv, yaml

# ── StorageManager ─────────────────────────────────────────────────────────────
class StorageManager:
    """Local filesystem (always) + MinIO (optional)."""

    def __init__(self):
        self._minio: Any = None
        if _HAS_MINIO and ServiceConfig.MINIO_ENDPOINT:
            try:
                self._minio = _minio_mod.Minio(
                    ServiceConfig.MINIO_ENDPOINT,
                    access_key=ServiceConfig.MINIO_ACCESS_KEY,
                    secret_key=ServiceConfig.MINIO_SECRET_KEY,
                    secure=ServiceConfig.MINIO_SECURE,
                )
                logger.info("MinIO client initialized: %s", ServiceConfig.MINIO_ENDPOINT)
            except Exception as e:
                logger.warning("MinIO init failed (%s), using local storage", e)

    # ── write ──────────────────────────────────────────────────────────────────
    async def write(self, bucket: str, object_key: str,
                    data: bytes, content_type: str = "application/octet-stream",
                    provider: Optional[str] = None) -> Dict[str, Any]:
        p = provider or ServiceConfig.DEFAULT_PROVIDER
        if p == "minio" and self._minio:
            return await self._write_minio(bucket, object_key, data, content_type)
        return await self._write_local(bucket, object_key, data)

    async def _write_local(self, bucket: str, object_key: str, data: bytes) -> Dict[str, Any]:
        full = Path(ServiceConfig.STORAGE_BASE) / bucket / object_key
        full.parent.mkdir(parents=True, exist_ok=True)
        if _HAS_AIOFILES:
            async with _aiofiles.open(full, "wb") as f:
                await f.write(data)
        else:
            full.write_bytes(data)
        return {"provider": "local", "bucket": bucket, "object_key": object_key,
                "path": str(full), "size": len(data)}

    async def _write_minio(self, bucket: str, object_key: str,
                            data: bytes, content_type: str) -> Dict[str, Any]:
        try:
            if not self._minio.bucket_exists(bucket):
                self._minio.make_bucket(bucket)
            result = self._minio.put_object(
                bucket, object_key, io.BytesIO(data), len(data),
                content_type=content_type,
            )
            return {"provider": "minio", "bucket": bucket, "object_key": object_key,
                    "etag": result.etag, "size": len(data)}
        except Exception as e:
            logger.warning("MinIO write failed (%s), fallback local", e)
            return await self._write_local(bucket, object_key, data)

    # ── read ───────────────────────────────────────────────────────────────────
    async def read(self, bucket: str, object_key: str, provider: str = "local") -> bytes:
        if provider == "minio" and self._minio:
            try:
                resp = self._minio.get_object(bucket, object_key)
                data = resp.read()
                resp.close(); resp.release_conn()
                return data
            except Exception as e:
                logger.warning("MinIO read failed (%s), fallback local", e)
        return await self._read_local(bucket, object_key)

    async def _read_local(self, bucket: str, object_key: str) -> bytes:
        full = Path(ServiceConfig.STORAGE_BASE) / bucket / object_key
        if not full.exists():
            raise FileNotFoundError(f"File not found: {full}")
        if _HAS_AIOFILES:
            async with _aiofiles.open(full, "rb") as f:
                return await f.read()
        return full.read_bytes()

    # ── delete ─────────────────────────────────────────────────────────────────
    async def delete(self, bucket: str, object_key: str, provider: str = "local") -> bool:
        if provider == "minio" and self._minio:
            try:
                self._minio.remove_object(bucket, object_key)
                return True
            except Exception:
                pass
        full = Path(ServiceConfig.STORAGE_BASE) / bucket / object_key
        if full.exists():
            full.unlink()
        return True

    # ── presigned URL ──────────────────────────────────────────────────────────
    def get_url(self, bucket: str, object_key: str,
                provider: str = "local", expires: int = 3600) -> str:
        if provider == "minio" and self._minio:
            try:
                return self._minio.presigned_get_object(
                    bucket, object_key, expires=timedelta(seconds=expires))
            except Exception:
                pass
        return f"/api/v1/files/raw/{bucket}/{object_key}"

# ── FileProcessor ──────────────────────────────────────────────────────────────
class FileProcessor:
    """Image processing via PIL (conditional). All video/OCR are conditional stubs."""

    # ── helpers ────────────────────────────────────────────────────────────────
    @staticmethod
    def _open_image(data: bytes) -> "Image.Image":
        if not _HAS_PIL:
            raise RuntimeError("Pillow not installed")
        return Image.open(io.BytesIO(data))

    @staticmethod
    def _save_image(img: "Image.Image", fmt: str = "JPEG", quality: int = 85) -> bytes:
        buf = io.BytesIO()
        save_fmt = fmt.upper()
        if save_fmt in ("JPG", "JPEG"):
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            img.save(buf, format="JPEG", quality=quality, optimize=True)
        elif save_fmt == "PNG":
            img.save(buf, format="PNG", optimize=True)
        elif save_fmt == "WEBP":
            img.save(buf, format="WEBP", quality=quality)
        else:
            img.save(buf, format="JPEG", quality=quality)
        return buf.getvalue()

    # ── detect file type ───────────────────────────────────────────────────────
    @staticmethod
    def detect_type(filename: str, data: bytes) -> Tuple[str, str, str]:
        ext = Path(filename).suffix.lstrip(".").lower() or "bin"
        # try magic first
        ct: Optional[str] = None
        if _HAS_MAGIC:
            try:
                ct = _magic.from_buffer(data[:4096], mime=True)
            except Exception:
                pass
        if not ct:
            ct, _ = mimetypes.guess_type(filename)
            ct = ct or "application/octet-stream"
        # map to FileType
        if ct.startswith("image/"): ft = FileType.IMAGE.value
        elif ct.startswith("video/"): ft = FileType.VIDEO.value
        elif ct.startswith("audio/"): ft = FileType.AUDIO.value
        elif ct in ("application/pdf",
                    "application/msword",
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    "application/vnd.ms-excel",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    "text/plain", "text/csv"):
            ft = FileType.DOCUMENT.value
        elif ct in ("application/zip", "application/x-rar-compressed",
                    "application/x-7z-compressed", "application/gzip"):
            ft = FileType.ARCHIVE.value
        elif ct in ("application/json", "application/xml", "text/xml"):
            ft = FileType.DATA.value
        else:
            ft = FileType.OTHER.value
        return ft, ct, ext

    # ── media info ─────────────────────────────────────────────────────────────
    @staticmethod
    def extract_media_info(data: bytes, file_type: str) -> Dict[str, Any]:
        info: Dict[str, Any] = {}
        if file_type == FileType.IMAGE.value and _HAS_PIL:
            try:
                img = Image.open(io.BytesIO(data))
                info["width"]  = img.width
                info["height"] = img.height
                info["mode"]   = img.mode
                if hasattr(img, "_getexif") and img._getexif():
                    info["has_exif"] = True
            except Exception:
                pass
        elif file_type == FileType.DOCUMENT.value and _HAS_PDF:
            try:
                pdf = _PdfReader(io.BytesIO(data))
                info["page_count"] = len(pdf.pages)
            except Exception:
                pass
        return info

    # ── resize ─────────────────────────────────────────────────────────────────
    async def resize(self, data: bytes, width: int, height: int,
                     fmt: str = "JPEG", quality: int = 85) -> bytes:
        if not _HAS_PIL:
            return data
        img = self._open_image(data)
        img.thumbnail((width, height), Image.Resampling.LANCZOS)
        return self._save_image(img, fmt, quality)

    # ── thumbnail generation ───────────────────────────────────────────────────
    async def generate_thumbnails(self, data: bytes, file_type: str) -> Dict[str, bytes]:
        if file_type != FileType.IMAGE.value or not _HAS_PIL:
            return {}
        thumbs: Dict[str, bytes] = {}
        try:
            img = self._open_image(data)
            for cfg in ServiceConfig.THUMB_SIZES:
                t = img.copy()
                t.thumbnail((cfg["width"], cfg["height"]), Image.Resampling.LANCZOS)
                thumbs[cfg["size_type"]] = self._save_image(t, "JPEG", cfg["quality"])
        except Exception as e:
            logger.error("Thumbnail generation failed: %s", e)
        return thumbs

    # ── beautify ───────────────────────────────────────────────────────────────
    async def beautify(self, data: bytes, req: "BeautifyRequest") -> bytes:
        if not _HAS_PIL:
            return data
        try:
            img = self._open_image(data)
            if req.brightness != 1.0:
                img = ImageEnhance.Brightness(img).enhance(req.brightness)
            if req.contrast != 1.0:
                img = ImageEnhance.Contrast(img).enhance(req.contrast)
            if req.saturation != 1.0:
                if img.mode not in ("RGB", "RGBA"):
                    img = img.convert("RGB")
                img = ImageEnhance.Color(img).enhance(req.saturation)
            if req.sharpness != 1.0:
                img = ImageEnhance.Sharpness(img).enhance(req.sharpness)
            if req.filter_type == "blur" and req.blur_radius > 0:
                img = img.filter(ImageFilter.GaussianBlur(req.blur_radius))
            elif req.filter_type == "sharpen":
                img = img.filter(ImageFilter.SHARPEN)
            elif req.filter_type == "contour":
                img = img.filter(ImageFilter.CONTOUR)
            elif req.filter_type == "edge_enhance":
                img = img.filter(ImageFilter.EDGE_ENHANCE)
            elif req.filter_type == "detail":
                img = img.filter(ImageFilter.DETAIL)
            return self._save_image(img, req.output_format, req.quality)
        except Exception as e:
            logger.error("Beautify failed: %s", e)
            return data

    # ── watermark ─────────────────────────────────────────────────────────────
    async def add_watermark(self, data: bytes, req: "WatermarkRequest") -> bytes:
        if not _HAS_PIL:
            return data
        try:
            img = self._open_image(data)
            if img.mode not in ("RGB", "RGBA"):
                img = img.convert("RGBA")
            overlay = Image.new("RGBA", img.size, (255, 255, 255, 0))
            draw = ImageDraw.Draw(overlay)
            text = req.text or "© Watermark"
            # try to load a font
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", req.font_size)
            except Exception:
                font = ImageFont.load_default()
            # color
            hx = req.color.lstrip("#")
            r, g, b = int(hx[0:2],16), int(hx[2:4],16), int(hx[4:6],16)
            a = int(req.opacity * 255)
            # bbox
            try:
                bb = draw.textbbox((0, 0), text, font=font)
                tw, th = bb[2]-bb[0], bb[3]-bb[1]
            except Exception:
                tw, th = len(text) * req.font_size // 2, req.font_size
            # position
            w, h = img.size
            _POS = {
                "top-left":     (10, 10),
                "top-right":    (w - tw - 10, 10),
                "bottom-left":  (10, h - th - 10),
                "bottom-right": (w - tw - 10, h - th - 10),
                "center":       ((w - tw) // 2, (h - th) // 2),
            }
            pos = _POS.get(req.position, _POS["bottom-right"])
            draw.text(pos, text, font=font, fill=(r, g, b, a))
            if img.mode != "RGBA":
                img = img.convert("RGBA")
            merged = Image.alpha_composite(img, overlay).convert("RGB")
            return self._save_image(merged, req.output_format, req.quality)
        except Exception as e:
            logger.error("Watermark failed: %s", e)
            return data

    # ── collage ────────────────────────────────────────────────────────────────
    async def create_collage(self, images: List[bytes], req: "CollageRequest") -> bytes:
        if not _HAS_PIL or not images:
            return images[0] if images else b""
        try:
            imgs = [Image.open(io.BytesIO(d)).convert("RGB") for d in images]
            cell_w = max(i.width for i in imgs)
            cell_h = max(i.height for i in imgs)
            n = len(imgs)
            gap = req.gap
            # parse bg color
            hx = req.bg_color.lstrip("#")
            bg = (int(hx[0:2],16), int(hx[2:4],16), int(hx[4:6],16))
            if req.layout == "horizontal":
                W = cell_w * n + gap * (n - 1)
                H = cell_h
                canvas = Image.new("RGB", (W, H), bg)
                for i, img in enumerate(imgs):
                    img.thumbnail((cell_w, cell_h), Image.Resampling.LANCZOS)
                    canvas.paste(img, (i * (cell_w + gap), 0))
            elif req.layout == "vertical":
                W = cell_w
                H = cell_h * n + gap * (n - 1)
                canvas = Image.new("RGB", (W, H), bg)
                for i, img in enumerate(imgs):
                    img.thumbnail((cell_w, cell_h), Image.Resampling.LANCZOS)
                    canvas.paste(img, (0, i * (cell_h + gap)))
            else:  # grid
                cols = min(n, 3)
                rows = (n + cols - 1) // cols
                W = cell_w * cols + gap * (cols - 1)
                H = cell_h * rows + gap * (rows - 1)
                canvas = Image.new("RGB", (W, H), bg)
                for i, img in enumerate(imgs):
                    img.thumbnail((cell_w, cell_h), Image.Resampling.LANCZOS)
                    r, c = divmod(i, cols)
                    canvas.paste(img, (c * (cell_w + gap), r * (cell_h + gap)))
            return self._save_image(canvas, req.output_format, req.quality)
        except Exception as e:
            logger.error("Collage failed: %s", e)
            return images[0] if images else b""

    # ── OCR ────────────────────────────────────────────────────────────────────
    async def extract_text(self, data: bytes, file_type: str) -> str:
        if file_type == FileType.IMAGE.value and _HAS_OCR and _HAS_PIL:
            try:
                img = Image.open(io.BytesIO(data))
                return _tesseract.image_to_string(img).strip()
            except Exception as e:
                logger.warning("OCR failed: %s", e)
        elif file_type == FileType.DOCUMENT.value and _HAS_PDF:
            try:
                pdf = _PdfReader(io.BytesIO(data))
                return "\n".join(p.extract_text() or "" for p in pdf.pages).strip()
            except Exception as e:
                logger.warning("PDF text extraction failed: %s", e)
        return ""

    # ── QR code ────────────────────────────────────────────────────────────────
    async def generate_qr(self, content: str) -> bytes:
        if _HAS_QRCODE:
            try:
                qr = _qrcode.QRCode(box_size=10, border=4)
                qr.add_data(content)
                qr.make(fit=True)
                img = qr.make_image(fill_color="black", back_color="white")
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                return buf.getvalue()
            except Exception as e:
                logger.warning("QR generation failed: %s", e)
        if _HAS_PIL:
            img = Image.new("RGB", (200, 200), "white")
            draw = ImageDraw.Draw(img)
            draw.text((10, 90), "QR:" + content[:20], fill="black")
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            return buf.getvalue()
        return b""

# ── RedisManager ───────────────────────────────────────────────────────────────
class RedisManager:
    def __init__(self, url: str):
        self._url  = url
        self._cli: Any = None
        self._mem: Dict[str, Tuple[str, float]] = {}

    async def connect(self) -> None:
        if _HAS_REDIS:
            try:
                self._cli = _redis_mod.from_url(self._url, decode_responses=True)
                await self._cli.ping()
                logger.info("Redis connected")
                return
            except Exception as e:
                logger.warning("Redis unavailable (%s), using mock", e)
        self._cli = None

    async def get(self, key: str) -> Optional[str]:
        if self._cli: return await self._cli.get(key)
        e = self._mem.get(key)
        if e and (e[1] == 0 or e[1] > time.time()): return e[0]
        self._mem.pop(key, None); return None

    async def set(self, key: str, val: str, ex: int = 0) -> None:
        if self._cli:
            await (self._cli.set(key, val, ex=ex) if ex else self._cli.set(key, val))
        else: self._mem[key] = (val, time.time()+ex if ex else 0)

    async def delete(self, key: str) -> None:
        if self._cli: await self._cli.delete(key)
        else: self._mem.pop(key, None)

    async def close(self) -> None:
        if self._cli: await self._cli.close()

# ── Prometheus (duplicate-safe) ────────────────────────────────────────────────
if _HAS_PROMETHEUS:
    _FS_REGISTRY = CollectorRegistry()
    def _c(n,d,l):
        try: return Counter(n,d,l,registry=_FS_REGISTRY)
        except ValueError: return Counter(n,d,l,registry=CollectorRegistry())
    def _g(n,d,l=[]):
        try: return Gauge(n,d,l,registry=_FS_REGISTRY)
        except ValueError: return Gauge(n,d,l,registry=CollectorRegistry())
    def _h(n,d,l):
        try: return Histogram(n,d,l,registry=_FS_REGISTRY)
        except ValueError: return Histogram(n,d,l,registry=CollectorRegistry())
    _m_upload    = _c("fs_uploads_total",    "Total uploads",   ["file_type","role"])
    _m_download  = _c("fs_downloads_total",  "Total downloads", ["file_type"])
    _m_size      = _g("fs_storage_bytes",    "Storage bytes",   ["bucket"])
    _m_latency   = _h("fs_latency_s",        "Latency",         ["op"])

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
ServiceConfig.ensure_dirs()
_storage   = StorageManager()
_processor = FileProcessor()
_redis_mgr = RedisManager(ServiceConfig.REDIS_URL)

# ── FileService ────────────────────────────────────────────────────────────────
class FileService:

    # ── upload ─────────────────────────────────────────────────────────────────
    async def upload(
        self,
        session: AsyncSession,
        file: UploadFile,
        opts: UploadOptions,
    ) -> Dict[str, Any]:
        t0 = time.monotonic()
        data = await file.read()
        size = len(data)

        # validation
        max_bytes = ServiceConfig.MAX_FILE_MB * 1024 * 1024
        if size > max_bytes:
            raise HTTPException(413, f"文件超过 {ServiceConfig.MAX_FILE_MB} MB 限制")
        fname = file.filename or "unnamed"
        ext   = Path(fname).suffix.lstrip(".").lower()
        if ext and ext not in ServiceConfig.ALLOWED_EXTENSIONS:
            raise HTTPException(415, f"不支持的文件类型: .{ext}")

        file_type, content_type, extension = _processor.detect_type(fname, data)
        media_info = _processor.extract_media_info(data, file_type)

        file_id = f"f_{uuid.uuid4().hex[:12]}"
        bucket  = "b2b" if opts.user_role in ("b2b", "b2b_buyer", "enterprise") else "b2c"
        obj_key = f"{opts.user_id}/{file_id}.{extension}"

        result = await _storage.write(bucket, obj_key, data, content_type)

        # thumbnails
        thumbnails: Dict[str, str] = {}
        if opts.generate_thumbs and file_type == FileType.IMAGE.value:
            thumbs = await _processor.generate_thumbnails(data, file_type)
            for st, tb_data in thumbs.items():
                tb_key = f"{opts.user_id}/{file_id}_thumb_{st}.jpg"
                await _storage.write("thumbnails", tb_key, tb_data)
                thumbnails[st] = tb_key

        # watermark
        if opts.add_watermark and file_type == FileType.IMAGE.value:
            wm_cfg = opts.watermark or {}
            wm_req = WatermarkRequest(
                file_id=file_id,
                text=wm_cfg.get("text", "© ILbuy"),
                opacity=wm_cfg.get("opacity", 0.4),
                position=wm_cfg.get("position", "bottom-right"),
            )
            wm_data = await _processor.add_watermark(data, wm_req)
            wm_key  = f"{opts.user_id}/{file_id}_wm.jpg"
            await _storage.write(bucket, wm_key, wm_data)

        # OCR (async background)
        ocr_text: Optional[str] = None
        if opts.run_ocr:
            ocr_text = await _processor.extract_text(data, file_type)

        md5    = hashlib.md5(data).hexdigest()
        sha256 = hashlib.sha256(data).hexdigest()

        rec = FileRecord(
            file_id           = file_id,
            filename          = fname,
            original_filename = fname,
            file_type         = file_type,
            content_type      = content_type,
            extension         = extension,
            size              = size,
            md5               = md5,
            sha256            = sha256,
            width             = media_info.get("width"),
            height            = media_info.get("height"),
            duration          = media_info.get("duration"),
            page_count        = media_info.get("page_count"),
            storage_provider  = result["provider"],
            storage_path      = obj_key,
            bucket            = bucket,
            object_key        = obj_key,
            access_level      = opts.access_level if isinstance(opts.access_level, str) else opts.access_level.value,
            user_id           = opts.user_id,
            user_role         = opts.user_role,
            company_id        = opts.company_id,
            project_id        = opts.project_id,
            category          = opts.category,
            tags              = opts.tags,
            description       = opts.description,
            thumbnails        = thumbnails,
            ocr_text          = ocr_text,
            expires_at        = _now() + timedelta(days=opts.expire_days) if opts.expire_days else None,
            uploaded_by       = opts.user_id,
            updated_by        = opts.user_id,
            extra_metadata    = opts.extra_metadata,
        )
        session.add(rec)
        await self._log(session, file_id, "upload", "upload_file", "success", opts.user_id)
        await session.commit()
        await session.refresh(rec)

        if _HAS_PROMETHEUS:
            _m_upload.labels(file_type=file_type, role=opts.user_role).inc()
            _m_latency.labels(op="upload").observe(time.monotonic() - t0)

        return {
            "file_id":         file_id,
            "filename":        fname,
            "file_type":       file_type,
            "content_type":    content_type,
            "size":            size,
            "md5":             md5,
            "storage_provider": result["provider"],
            "thumbnails":      thumbnails,
            "url":             _storage.get_url(bucket, obj_key, result["provider"]),
            "ocr_text":        ocr_text,
        }

    # ── B2B batch upload ───────────────────────────────────────────────────────
    async def batch_upload(
        self,
        session: AsyncSession,
        files: List[UploadFile],
        opts: B2BBatchRequest,
    ) -> Dict[str, Any]:
        if len(files) > ServiceConfig.B2B_MAX_BATCH:
            raise HTTPException(400, f"批量上传最多 {ServiceConfig.B2B_MAX_BATCH} 个文件")
        results, errors = [], []
        for f in files:
            try:
                up_opts = UploadOptions(
                    user_id    = opts.user_id,
                    user_role  = "b2b",
                    access_level = opts.access_level,
                    tags       = opts.tags,
                    category   = opts.category,
                    company_id = opts.company_id,
                    project_id = opts.project_id,
                    add_watermark = bool(opts.watermark_config),
                    watermark  = opts.watermark_config,
                    run_ocr    = opts.run_ocr,
                    extra_metadata = opts.extra_metadata,
                )
                r = await self.upload(session, f, up_opts)
                results.append({"success": True, **r})
            except HTTPException as e:
                errors.append({"filename": f.filename, "error": e.detail})
            except Exception as e:
                errors.append({"filename": f.filename, "error": str(e)})
        return {"uploaded": len(results), "failed": len(errors),
                "results": results, "errors": errors}

    # ── get file info ──────────────────────────────────────────────────────────
    async def get_file(self, session: AsyncSession, file_id: str) -> FileRecord:
        rec = (await session.execute(
            select(FileRecord).where(
                and_(FileRecord.file_id == file_id,
                     FileRecord.status != FileStatus.DELETED.value))
        )).scalars().first()
        if not rec:
            raise HTTPException(404, f"File '{file_id}' not found")
        return rec

    # ── download ───────────────────────────────────────────────────────────────
    async def download(
        self, session: AsyncSession, file_id: str, user_id: Optional[str] = None
    ) -> Tuple[bytes, str, str]:
        rec = await self.get_file(session, file_id)
        data = await _storage.read(rec.bucket, rec.object_key, rec.storage_provider)
        # increment counter
        await session.execute(
            update(FileRecord).where(FileRecord.file_id == file_id)
            .values(download_count=FileRecord.download_count + 1)
        )
        await self._log(session, file_id, "download", "download_file", "success", user_id)
        await session.commit()
        if _HAS_PROMETHEUS:
            _m_download.labels(file_type=rec.file_type).inc()
        return data, rec.content_type, rec.original_filename

    # ── delete (soft) ──────────────────────────────────────────────────────────
    async def delete_file(
        self, session: AsyncSession, file_id: str, user_id: str = "system"
    ) -> Dict[str, Any]:
        rec = await self.get_file(session, file_id)
        rec.status     = FileStatus.DELETED.value
        rec.deleted_at = _now()
        rec.updated_by = user_id
        await self._log(session, file_id, "delete", "delete_file", "success", user_id)
        await session.commit()
        return {"file_id": file_id, "status": "deleted"}

    # ── search ─────────────────────────────────────────────────────────────────
    async def search(
        self, session: AsyncSession, req: SearchRequest
    ) -> Dict[str, Any]:
        conds = [FileRecord.status != FileStatus.DELETED.value]
        if req.query:
            kw = f"%{req.query}%"
            conds.append(or_(FileRecord.filename.ilike(kw),
                              FileRecord.description.ilike(kw)))
        if req.file_type:    conds.append(FileRecord.file_type    == req.file_type)
        if req.user_id:      conds.append(FileRecord.user_id      == req.user_id)
        if req.company_id:   conds.append(FileRecord.company_id   == req.company_id)
        if req.access_level: conds.append(FileRecord.access_level == req.access_level)
        if req.status:       conds.append(FileRecord.status       == req.status)
        if req.min_size:     conds.append(FileRecord.size >= req.min_size)
        if req.max_size:     conds.append(FileRecord.size <= req.max_size)
        if req.start_date:   conds.append(FileRecord.created_at   >= req.start_date)
        if req.end_date:     conds.append(FileRecord.created_at   <= req.end_date)

        total = (await session.execute(
            select(func.count()).select_from(FileRecord).where(and_(*conds))
        )).scalar_one()
        order = (FileRecord.created_at.desc() if req.sort_order == "desc"
                 else FileRecord.created_at.asc())
        rows  = (await session.execute(
            select(FileRecord).where(and_(*conds)).order_by(order)
            .offset((req.page - 1) * req.page_size).limit(req.page_size)
        )).scalars().all()
        return {"items": rows, "total": total,
                "page": req.page, "page_size": req.page_size,
                "total_pages": (total + req.page_size - 1) // req.page_size}

    # ── share ──────────────────────────────────────────────────────────────────
    async def create_share(
        self, session: AsyncSession, req: ShareRequest
    ) -> Dict[str, Any]:
        rec = await self.get_file(session, req.file_id)
        share_id    = f"sh_{uuid.uuid4().hex[:12]}"
        token       = secrets.token_urlsafe(32)
        short_code  = secrets.token_urlsafe(6)
        pwd_hash    = hashlib.sha256(req.password.encode()).hexdigest() if req.password else None
        expires     = _now() + timedelta(days=req.expire_days) if req.expire_days else None

        sh = FileShare(
            share_id        = share_id,
            file_id         = req.file_id,
            share_type      = req.share_type,
            access_token    = token,
            short_code      = short_code,
            password_hash   = pwd_hash,
            can_download    = req.can_download,
            max_downloads   = req.max_downloads,
            recipient_email = req.recipient_email,
            message         = req.message,
            created_by      = "system",
            expires_at      = expires,
        )
        session.add(sh)
        await session.execute(
            update(FileRecord).where(FileRecord.file_id == req.file_id)
            .values(share_count=FileRecord.share_count + 1)
        )
        await self._log(session, req.file_id, "share", "create_share", "success", None)
        await session.commit()
        return {
            "share_id":   share_id,
            "token":      token,
            "short_code": short_code,
            "url":        f"/api/v1/files/share/{short_code}",
            "expires_at": expires.isoformat() if expires else None,
        }

    async def get_share(
        self, session: AsyncSession, token_or_code: str, password: Optional[str] = None
    ) -> Tuple[FileRecord, FileShare]:
        sh = (await session.execute(
            select(FileShare).where(
                and_(
                    or_(FileShare.access_token == token_or_code,
                        FileShare.short_code   == token_or_code),
                    FileShare.is_active == True,
                )
            )
        )).scalars().first()
        if not sh:
            raise HTTPException(404, "分享链接不存在或已失效")
        exp = sh.expires_at
        if exp and exp.tzinfo is None: exp = exp.replace(tzinfo=timezone.utc)
        if exp and exp < _now():
            raise HTTPException(410, "分享链接已过期")
        if sh.password_hash:
            if not password:
                raise HTTPException(401, "此分享需要密码")
            if hashlib.sha256(password.encode()).hexdigest() != sh.password_hash:
                raise HTTPException(403, "密码错误")
        if sh.max_downloads and sh.download_count >= sh.max_downloads:
            raise HTTPException(429, "下载次数已达上限")
        rec = await self.get_file(session, sh.file_id)
        return rec, sh

    # ── B2B bulk download (zip) ────────────────────────────────────────────────
    async def bulk_download(
        self, session: AsyncSession, file_ids: List[str], user_id: str
    ) -> bytes:
        if len(file_ids) > ServiceConfig.B2B_MAX_BATCH:
            raise HTTPException(400, f"最多 {ServiceConfig.B2B_MAX_BATCH} 个文件")
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for fid in file_ids:
                try:
                    rec  = await self.get_file(session, fid)
                    data = await _storage.read(rec.bucket, rec.object_key, rec.storage_provider)
                    zf.writestr(rec.original_filename, data)
                except Exception as e:
                    logger.warning("bulk_download skip %s: %s", fid, e)
        return buf.getvalue()

    # ── export metadata ────────────────────────────────────────────────────────
    async def export_metadata(
        self, session: AsyncSession, req: ExportRequest
    ) -> Tuple[str, str]:
        conds = [FileRecord.status != FileStatus.DELETED.value]
        if req.company_id: conds.append(FileRecord.company_id == req.company_id)
        if req.user_id:    conds.append(FileRecord.user_id    == req.user_id)
        if req.file_type:  conds.append(FileRecord.file_type  == req.file_type)
        if req.start_date: conds.append(FileRecord.created_at >= req.start_date)
        if req.end_date:   conds.append(FileRecord.created_at <= req.end_date)
        rows = (await session.execute(
            select(FileRecord).where(and_(*conds)).order_by(FileRecord.created_at.desc())
        )).scalars().all()

        data_list = [{
            "file_id":    r.file_id,
            "filename":   r.filename,
            "file_type":  r.file_type,
            "size":       r.size,
            "md5":        r.md5,
            "status":     r.status,
            "user_id":    r.user_id,
            "company_id": r.company_id,
            "tags":       r.tags,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        } for r in rows]

        fmt = req.format.lower()
        if fmt == "json":
            return json.dumps(data_list, ensure_ascii=False, indent=2), "application/json"
        elif fmt == "csv":
            si = io.StringIO()
            if data_list:
                w = csv.DictWriter(si, fieldnames=list(data_list[0].keys()))
                w.writeheader(); w.writerows(data_list)
            return si.getvalue(), "text/csv"
        elif fmt in ("yaml", "yml") and _HAS_YAML:
            return _yaml_mod.dump(data_list, allow_unicode=True), "text/yaml"
        else:
            return json.dumps(data_list, ensure_ascii=False, indent=2), "application/json"

    # ── B2C beautify ───────────────────────────────────────────────────────────
    async def beautify(
        self, session: AsyncSession, req: BeautifyRequest, user_id: str
    ) -> Dict[str, Any]:
        rec  = await self.get_file(session, req.file_id)
        if rec.file_type != FileType.IMAGE.value:
            raise HTTPException(422, "仅支持图片文件")
        data = await _storage.read(rec.bucket, rec.object_key, rec.storage_provider)
        out  = await _processor.beautify(data, req)

        new_id  = f"f_{uuid.uuid4().hex[:12]}"
        obj_key = f"{rec.user_id}/{new_id}_beautified.{req.output_format}"
        result  = await _storage.write(rec.bucket, obj_key, out, f"image/{req.output_format}")

        new_rec = FileRecord(
            file_id           = new_id,
            filename          = f"{Path(rec.filename).stem}_beautified.{req.output_format}",
            original_filename = rec.original_filename,
            file_type         = FileType.IMAGE.value,
            content_type      = f"image/{req.output_format}",
            extension         = req.output_format,
            size              = len(out),
            md5               = hashlib.md5(out).hexdigest(),
            storage_provider  = result["provider"],
            storage_path      = obj_key,
            bucket            = rec.bucket,
            object_key        = obj_key,
            access_level      = rec.access_level,
            user_id           = rec.user_id,
            user_role         = rec.user_role,
            parent_file_id    = rec.file_id,
            uploaded_by       = user_id,
            updated_by        = user_id,
        )
        session.add(new_rec)
        await session.commit()
        return {"file_id": new_id, "url": _storage.get_url(rec.bucket, obj_key)}

    # ── B2C watermark ──────────────────────────────────────────────────────────
    async def apply_watermark(
        self, session: AsyncSession, req: WatermarkRequest, user_id: str
    ) -> Dict[str, Any]:
        rec  = await self.get_file(session, req.file_id)
        if rec.file_type != FileType.IMAGE.value:
            raise HTTPException(422, "仅支持图片文件")
        data = await _storage.read(rec.bucket, rec.object_key, rec.storage_provider)
        out  = await _processor.add_watermark(data, req)
        new_id  = f"f_{uuid.uuid4().hex[:12]}"
        obj_key = f"{rec.user_id}/{new_id}_wm.{req.output_format}"
        result  = await _storage.write(rec.bucket, obj_key, out, f"image/{req.output_format}")
        new_rec = FileRecord(
            file_id           = new_id,
            filename          = f"{Path(rec.filename).stem}_wm.{req.output_format}",
            original_filename = rec.original_filename,
            file_type         = FileType.IMAGE.value,
            content_type      = f"image/{req.output_format}",
            extension         = req.output_format,
            size              = len(out),
            md5               = hashlib.md5(out).hexdigest(),
            storage_provider  = result["provider"],
            storage_path      = obj_key,
            bucket            = rec.bucket,
            object_key        = obj_key,
            access_level      = rec.access_level,
            user_id           = rec.user_id,
            user_role         = rec.user_role,
            watermark_type    = req.wm_type.value,
            watermark_conf    = req.model_dump(),
            parent_file_id    = rec.file_id,
            uploaded_by       = user_id,
            updated_by        = user_id,
        )
        session.add(new_rec)
        await session.commit()
        return {"file_id": new_id, "url": _storage.get_url(rec.bucket, obj_key)}

    # ── B2C collage ────────────────────────────────────────────────────────────
    async def create_collage(
        self, session: AsyncSession, req: CollageRequest, user_id: str
    ) -> Dict[str, Any]:
        images_data: List[bytes] = []
        owner_id = user_id
        for fid in req.file_ids:
            rec  = await self.get_file(session, fid)
            if rec.file_type != FileType.IMAGE.value:
                raise HTTPException(422, f"文件 {fid} 不是图片")
            images_data.append(await _storage.read(rec.bucket, rec.object_key, rec.storage_provider))
            owner_id = rec.user_id

        out     = await _processor.create_collage(images_data, req)
        new_id  = f"f_{uuid.uuid4().hex[:12]}"
        obj_key = f"{owner_id}/{new_id}_collage.{req.output_format}"
        result  = await _storage.write("b2c", obj_key, out, f"image/{req.output_format}")
        new_rec = FileRecord(
            file_id           = new_id,
            filename          = f"collage_{new_id}.{req.output_format}",
            original_filename = f"collage.{req.output_format}",
            file_type         = FileType.IMAGE.value,
            content_type      = f"image/{req.output_format}",
            extension         = req.output_format,
            size              = len(out),
            md5               = hashlib.md5(out).hexdigest(),
            storage_provider  = result["provider"],
            storage_path      = obj_key,
            bucket            = "b2c",
            object_key        = obj_key,
            access_level      = AccessLevel.PRIVATE.value,
            user_id           = user_id,
            user_role         = "b2c",
            uploaded_by       = user_id,
            updated_by        = user_id,
            extra_metadata    = {"source_file_ids": req.file_ids},
        )
        session.add(new_rec)
        await session.commit()
        return {"file_id": new_id, "url": _storage.get_url("b2c", obj_key)}

    # ── version control ────────────────────────────────────────────────────────
    async def create_version(
        self, session: AsyncSession, req: VersionCreateRequest,
        file: UploadFile,
    ) -> Dict[str, Any]:
        parent = await self.get_file(session, req.file_id)
        # mark old version as not-latest
        await session.execute(
            update(FileRecord).where(FileRecord.file_id == req.file_id)
            .values(is_latest=False)
        )
        opts = UploadOptions(
            user_id       = req.user_id,
            user_role     = parent.user_role,
            access_level  = parent.access_level,
            tags          = parent.tags or [],
            category      = parent.category,
            company_id    = parent.company_id,
            project_id    = parent.project_id,
            extra_metadata = {"parent_file_id": req.file_id,
                              "change_note":    req.change_note,
                              "version":        parent.version + 1},
        )
        result = await self.upload(session, file, opts)
        new_id = result["file_id"]
        await session.execute(
            update(FileRecord).where(FileRecord.file_id == new_id)
            .values(parent_file_id=req.file_id, version=parent.version + 1)
        )
        await session.commit()
        return {**result, "version": parent.version + 1, "parent_file_id": req.file_id}

    async def get_version_history(
        self, session: AsyncSession, file_id: str
    ) -> List[Dict[str, Any]]:
        rec   = await self.get_file(session, file_id)
        # walk up the parent chain
        chain: List[Dict] = []
        rows  = (await session.execute(
            select(FileRecord).where(
                or_(FileRecord.file_id == file_id,
                    FileRecord.parent_file_id == file_id)
            ).order_by(FileRecord.version.desc())
        )).scalars().all()
        return [_row(r) for r in rows]

    # ── OCR ────────────────────────────────────────────────────────────────────
    async def run_ocr(
        self, session: AsyncSession, file_id: str
    ) -> Dict[str, Any]:
        rec  = await self.get_file(session, file_id)
        data = await _storage.read(rec.bucket, rec.object_key, rec.storage_provider)
        text = await _processor.extract_text(data, rec.file_type)
        await session.execute(
            update(FileRecord).where(FileRecord.file_id == file_id)
            .values(ocr_text=text)
        )
        await session.commit()
        return {"file_id": file_id, "text": text, "char_count": len(text)}

    # ── stats ──────────────────────────────────────────────────────────────────
    async def get_stats(self, session: AsyncSession) -> Dict[str, Any]:
        total   = (await session.execute(
            select(func.count()).select_from(FileRecord)
            .where(FileRecord.status != FileStatus.DELETED.value)
        )).scalar_one()
        total_sz = (await session.execute(
            select(func.sum(FileRecord.size)).select_from(FileRecord)
            .where(FileRecord.status != FileStatus.DELETED.value)
        )).scalar_one() or 0
        by_type_rows = (await session.execute(
            select(FileRecord.file_type, func.count(FileRecord.id).label("cnt"),
                   func.sum(FileRecord.size).label("sz"))
            .where(FileRecord.status != FileStatus.DELETED.value)
            .group_by(FileRecord.file_type)
        )).all()
        return {
            "total_files":    total,
            "total_size_bytes": total_sz,
            "total_size_mb":  round(total_sz / 1024 / 1024, 2),
            "by_type":        {r.file_type: {"count": r.cnt, "size_bytes": r.sz or 0}
                               for r in by_type_rows},
            "pil_available":  _HAS_PIL,
            "minio_available": bool(_storage._minio),
            "ocr_available":  _HAS_OCR,
        }

    # ── internal helpers ───────────────────────────────────────────────────────
    async def _log(
        self, session: AsyncSession, file_id: str,
        act_type: str, action: str, result: str,
        user_id: Optional[str],
    ) -> None:
        session.add(FileActivity(
            activity_id     = f"act_{uuid.uuid4().hex[:12]}",
            file_id         = file_id,
            activity_type   = act_type,
            activity_action = action,
            result          = result,
            performed_by    = user_id,
        ))

# ── singleton service ──────────────────────────────────────────────────────────
_svc = FileService()

# ── row helper ─────────────────────────────────────────────────────────────────
def _row(obj: Any) -> Dict[str, Any]:
    if hasattr(obj, "__dict__"):
        return {k: v for k, v in obj.__dict__.items() if not k.startswith("_")}
    return dict(obj)

# ── FastAPI factory ────────────────────────────────────────────────────────────
def create_app() -> FastAPI:
    app = FastAPI(
        title="File Service",
        description="B2B/B2C File Storage, Processing & Distribution (Part 11)",
        version="1.0.0",
    )

    @app.on_event("startup")
    async def _startup():
        async with _engine.begin() as c:
            await c.run_sync(Base.metadata.create_all)
        await _redis_mgr.connect()
        asyncio.create_task(_cleanup_temp_task())
        asyncio.create_task(_cleanup_deleted_task())
        logger.info("File Service started on %s:%s", ServiceConfig.HOST, ServiceConfig.PORT)

    @app.on_event("shutdown")
    async def _shutdown():
        await _redis_mgr.close()
        await _engine.dispose()

    # ── health ─────────────────────────────────────────────────────────────────
    @app.get("/health", tags=["system"])
    async def health():
        return {"status": "ok", "service": "file-service",
                "pil": _HAS_PIL, "minio": _HAS_MINIO, "ocr": _HAS_OCR,
                "time": _now().isoformat()}

    @app.get("/metrics", tags=["system"])
    async def metrics():
        if not _HAS_PROMETHEUS:
            raise HTTPException(503, "prometheus_client not installed")
        return StreamingResponse(iter([generate_latest(_FS_REGISTRY)]),
                                 media_type=CONTENT_TYPE_LATEST)

    # ── upload ─────────────────────────────────────────────────────────────────
    @app.post("/api/v1/files/upload", status_code=201, tags=["files"])
    async def upload_file(
        file:          UploadFile = File(...),
        user_id:       str = Form(...),
        user_role:     str = Form("user"),
        access_level:  str = Form("private"),
        category:      Optional[str] = Form(None),
        tags:          Optional[str] = Form(None),
        description:   Optional[str] = Form(None),
        expire_days:   Optional[int] = Form(None),
        add_watermark: bool = Form(False),
        generate_thumbs: bool = Form(True),
        run_ocr:       bool = Form(False),
        company_id:    Optional[str] = Form(None),
        project_id:    Optional[str] = Form(None),
        db: AsyncSession = Depends(get_db),
    ):
        opts = UploadOptions(
            user_id       = user_id,
            user_role     = user_role,
            access_level  = AccessLevel(access_level),
            category      = category,
            tags          = json.loads(tags) if tags else [],
            description   = description,
            expire_days   = expire_days,
            add_watermark = add_watermark,
            generate_thumbs = generate_thumbs,
            run_ocr       = run_ocr,
            company_id    = company_id,
            project_id    = project_id,
        )
        return await _svc.upload(db, file, opts)

    @app.post("/api/v1/files/batch-upload", status_code=201, tags=["b2b"])
    async def batch_upload(
        files:      List[UploadFile] = File(...),
        user_id:    str = Form(...),
        company_id: str = Form(...),
        project_id: Optional[str] = Form(None),
        run_ocr:    bool = Form(False),
        db: AsyncSession = Depends(get_db),
    ):
        opts = B2BBatchRequest(user_id=user_id, company_id=company_id,
                               project_id=project_id, run_ocr=run_ocr)
        return await _svc.batch_upload(db, files, opts)

    # ── file CRUD ──────────────────────────────────────────────────────────────
    @app.get("/api/v1/files", tags=["files"])
    async def list_files(
        query:        Optional[str] = None,
        file_type:    Optional[str] = None,
        user_id:      Optional[str] = None,
        company_id:   Optional[str] = None,
        access_level: Optional[str] = None,
        status:       Optional[str] = None,
        min_size:     Optional[int] = None,
        max_size:     Optional[int] = None,
        page:         int = Query(1,  ge=1),
        page_size:    int = Query(20, ge=1, le=200),
        sort_order:   str = Query("desc"),
        db: AsyncSession = Depends(get_db),
    ):
        req = SearchRequest(query=query, file_type=file_type, user_id=user_id,
                            company_id=company_id, access_level=access_level,
                            status=status, min_size=min_size, max_size=max_size,
                            page=page, page_size=page_size, sort_order=sort_order)
        result = await _svc.search(db, req)
        result["items"] = [_row(r) for r in result["items"]]
        return result

    @app.post("/api/v1/files/search", tags=["files"])
    async def search_files(req: SearchRequest, db: AsyncSession = Depends(get_db)):
        result = await _svc.search(db, req)
        result["items"] = [_row(r) for r in result["items"]]
        return result

    @app.get("/api/v1/files/{file_id}", tags=["files"])
    async def get_file(file_id: str, db: AsyncSession = Depends(get_db)):
        return _row(await _svc.get_file(db, file_id))

    @app.delete("/api/v1/files/{file_id}", tags=["files"])
    async def delete_file(
        file_id: str,
        user_id: str = Query("system"),
        db: AsyncSession = Depends(get_db),
    ):
        return await _svc.delete_file(db, file_id, user_id)

    # ── download ───────────────────────────────────────────────────────────────
    @app.get("/api/v1/files/{file_id}/download", tags=["files"])
    async def download_file(
        file_id: str,
        user_id: Optional[str] = Query(None),
        db: AsyncSession = Depends(get_db),
    ):
        data, ct, fname = await _svc.download(db, file_id, user_id)
        safe = re.sub(r'[^\w\.\-]', '_', fname)
        return StreamingResponse(
            iter([data]),
            media_type=ct,
            headers={"Content-Disposition": f'attachment; filename="{safe}"',
                     "Content-Length": str(len(data))},
        )

    @app.get("/api/v1/files/{file_id}/url", tags=["files"])
    async def get_file_url(
        file_id:  str,
        expires:  int = Query(3600, ge=60),
        db: AsyncSession = Depends(get_db),
    ):
        rec = await _svc.get_file(db, file_id)
        url = _storage.get_url(rec.bucket, rec.object_key, rec.storage_provider, expires)
        return {"file_id": file_id, "url": url, "expires_in": expires}

    # ── raw file (local path) ──────────────────────────────────────────────────
    @app.get("/api/v1/files/raw/{bucket}/{object_key:path}", tags=["files"])
    async def get_raw_file(bucket: str, object_key: str):
        try:
            data = await _storage._read_local(bucket, object_key)
        except FileNotFoundError:
            raise HTTPException(404, "File not found")
        ct, _ = mimetypes.guess_type(object_key)
        ct = ct or "application/octet-stream"
        return StreamingResponse(iter([data]), media_type=ct)

    # ── thumbnails ─────────────────────────────────────────────────────────────
    @app.get("/api/v1/files/{file_id}/thumbnails", tags=["files"])
    async def get_thumbnails(file_id: str, db: AsyncSession = Depends(get_db)):
        rec = await _svc.get_file(db, file_id)
        thumbs = rec.thumbnails or {}
        return {"file_id": file_id, "thumbnails": {
            st: _storage.get_url("thumbnails", key) for st, key in thumbs.items()
        }}

    # ── share ──────────────────────────────────────────────────────────────────
    @app.post("/api/v1/files/{file_id}/share", tags=["sharing"])
    async def share_file(
        file_id: str,
        req: ShareRequest,
        db: AsyncSession = Depends(get_db),
    ):
        req.file_id = file_id
        return await _svc.create_share(db, req)

    @app.get("/api/v1/files/share/{token_or_code}", tags=["sharing"])
    async def access_share(
        token_or_code: str,
        password: Optional[str] = Query(None),
        db: AsyncSession = Depends(get_db),
    ):
        rec, sh = await _svc.get_share(db, token_or_code, password)
        return {"file": _row(rec), "share": _row(sh)}

    @app.get("/api/v1/files/share/{token_or_code}/download", tags=["sharing"])
    async def download_via_share(
        token_or_code: str,
        password: Optional[str] = Query(None),
        db: AsyncSession = Depends(get_db),
    ):
        rec, sh = await _svc.get_share(db, token_or_code, password)
        if not sh.can_download:
            raise HTTPException(403, "此分享不允许下载")
        data = await _storage.read(rec.bucket, rec.object_key, rec.storage_provider)
        # increment share download count
        await db.execute(
            update(FileShare).where(FileShare.share_id == sh.share_id)
            .values(download_count=FileShare.download_count + 1,
                    last_accessed=_now())
        )
        await db.commit()
        safe = re.sub(r'[^\w\.\-]', '_', rec.original_filename)
        return StreamingResponse(iter([data]), media_type=rec.content_type,
                                 headers={"Content-Disposition": f'attachment; filename="{safe}"'})

    # ── B2B endpoints ──────────────────────────────────────────────────────────
    @app.post("/api/v1/files/b2b/bulk-download", tags=["b2b"])
    async def bulk_download(
        file_ids: List[str],
        user_id: str = Query("system"),
        db: AsyncSession = Depends(get_db),
    ):
        data = await _svc.bulk_download(db, file_ids, user_id)
        return StreamingResponse(iter([data]), media_type="application/zip",
                                 headers={"Content-Disposition": 'attachment; filename="bulk_download.zip"'})

    @app.post("/api/v1/files/b2b/export", tags=["b2b"])
    async def export_metadata(req: ExportRequest, db: AsyncSession = Depends(get_db)):
        content, mime = await _svc.export_metadata(db, req)
        ext = "json" if "json" in mime else ("csv" if "csv" in mime else "yaml")
        return StreamingResponse(iter([content.encode()]), media_type=mime,
                                 headers={"Content-Disposition": f'attachment; filename="file_export.{ext}"'})

    @app.get("/api/v1/files/{file_id}/history", tags=["b2b"])
    async def version_history(file_id: str, db: AsyncSession = Depends(get_db)):
        return {"file_id": file_id, "versions": await _svc.get_version_history(db, file_id)}

    @app.post("/api/v1/files/{file_id}/version", status_code=201, tags=["b2b"])
    async def create_version(
        file_id: str,
        file:    UploadFile = File(...),
        user_id: str = Form(...),
        change_note: Optional[str] = Form(None),
        db: AsyncSession = Depends(get_db),
    ):
        req = VersionCreateRequest(file_id=file_id, user_id=user_id, change_note=change_note)
        return await _svc.create_version(db, req, file)

    @app.post("/api/v1/files/{file_id}/ocr", tags=["b2b"])
    async def run_ocr(file_id: str, db: AsyncSession = Depends(get_db)):
        return await _svc.run_ocr(db, file_id)

    # ── B2C endpoints ──────────────────────────────────────────────────────────
    @app.post("/api/v1/files/b2c/beautify", tags=["b2c"])
    async def beautify(
        req: BeautifyRequest,
        user_id: str = Query("system"),
        db: AsyncSession = Depends(get_db),
    ):
        return await _svc.beautify(db, req, user_id)

    @app.post("/api/v1/files/b2c/watermark", tags=["b2c"])
    async def add_watermark(
        req: WatermarkRequest,
        user_id: str = Query("system"),
        db: AsyncSession = Depends(get_db),
    ):
        return await _svc.apply_watermark(db, req, user_id)

    @app.post("/api/v1/files/b2c/collage", status_code=201, tags=["b2c"])
    async def create_collage(
        req: CollageRequest,
        user_id: str = Query("system"),
        db: AsyncSession = Depends(get_db),
    ):
        return await _svc.create_collage(db, req, user_id)

    # ── stats ──────────────────────────────────────────────────────────────────
    @app.get("/api/v1/stats", tags=["stats"])
    async def get_stats(db: AsyncSession = Depends(get_db)):
        return await _svc.get_stats(db)

    @app.get("/api/v1/stats/by-user/{user_id}", tags=["stats"])
    async def user_stats(user_id: str, db: AsyncSession = Depends(get_db)):
        total = (await db.execute(
            select(func.count(), func.sum(FileRecord.size)).select_from(FileRecord)
            .where(and_(FileRecord.user_id == user_id,
                        FileRecord.status != FileStatus.DELETED.value))
        )).first()
        return {"user_id": user_id, "file_count": total[0] or 0,
                "total_size_bytes": total[1] or 0}

    return app

# ── background tasks ───────────────────────────────────────────────────────────
async def _cleanup_temp_task() -> None:
    while True:
        try:
            temp_path = Path(ServiceConfig.STORAGE_TEMP)
            if temp_path.exists():
                cutoff = time.time() - ServiceConfig.TEMP_TTL_HOURS * 3600
                for f in temp_path.rglob("*"):
                    if f.is_file() and f.stat().st_mtime < cutoff:
                        f.unlink()
        except Exception as e:
            logger.error("_cleanup_temp_task: %s", e)
        await asyncio.sleep(3600)

async def _cleanup_deleted_task() -> None:
    while True:
        try:
            async with _SessionFactory() as session:
                cutoff = _now() - timedelta(days=ServiceConfig.DELETED_TTL_DAYS)
                rows = (await session.execute(
                    select(FileRecord).where(
                        and_(FileRecord.status == FileStatus.DELETED.value,
                             FileRecord.deleted_at <= cutoff)
                    )
                )).scalars().all()
                for rec in rows:
                    try:
                        await _storage.delete(rec.bucket, rec.object_key, rec.storage_provider)
                    except Exception:
                        pass
                if rows:
                    await session.commit()
                    logger.info("Purged %d hard-deleted files", len(rows))
        except Exception as e:
            logger.error("_cleanup_deleted_task: %s", e)
        await asyncio.sleep(86400)

# ── entrypoint ─────────────────────────────────────────────────────────────────
app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "file_service:app",
        host=ServiceConfig.HOST,
        port=ServiceConfig.PORT,
        reload=False,
        log_level="info",
    )
