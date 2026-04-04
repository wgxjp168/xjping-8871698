"""
gateway_layer.py
接入层 - 统一入口与网关
包含：API网关、认证授权、限流熔断、WebSocket服务、SSE推送
"""

import asyncio
import json
import time
import uuid
import hashlib
import base64
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, AsyncGenerator
from dataclasses import dataclass, field
from enum import Enum
import logging
from contextlib import asynccontextmanager
from collections import defaultdict

from fastapi import (FastAPI, WebSocket, WebSocketDisconnect,
                     HTTPException, Depends, Request, Header, Body, Response)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, validator
# jwt replaced with stdlib hmac/hashlib to avoid broken cryptography Rust extension
import hmac as _hmac
import struct as _struct

class _JWT:
    """Minimal HS256 JWT — encode/decode only. Production: use PyJWT or python-jose."""
    @staticmethod
    def _b64url_encode(data: bytes) -> str:
        import base64
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

    @staticmethod
    def _b64url_decode(s: str) -> bytes:
        import base64
        pad = 4 - len(s) % 4
        return base64.urlsafe_b64decode(s + "=" * (pad % 4))

    def encode(self, payload: dict, key: str, algorithm: str = "HS256") -> str:
        import json, time
        hdr = self._b64url_encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
        # convert datetime → timestamp in payload copy
        p = {}
        for k, v in payload.items():
            from datetime import datetime
            p[k] = int(v.timestamp()) if isinstance(v, datetime) else v
        bod = self._b64url_encode(json.dumps(p, separators=(",", ":")).encode())
        sig_input = f"{hdr}.{bod}".encode()
        sig = _hmac.new(key.encode(), sig_input, hashlib.sha256).digest()
        return f"{hdr}.{bod}.{self._b64url_encode(sig)}"

    def decode(self, token: str, key: str, algorithms=None) -> dict:
        import json, time
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("Invalid token format")
        hdr_b, bod_b, sig_b = parts
        sig_input = f"{hdr_b}.{bod_b}".encode()
        expected  = _hmac.new(key.encode(), sig_input, hashlib.sha256).digest()
        actual    = self._b64url_decode(sig_b)
        if not _hmac.compare_digest(expected, actual):
            raise ValueError("Signature verification failed")  # maps to InvalidTokenError
        payload = json.loads(self._b64url_decode(bod_b))
        exp = payload.get("exp")
        if exp and time.time() > exp:
            raise _JWTExpiredError("Token expired")
        return payload

class _JWTExpiredError(Exception): pass

class _JWTError(Exception): pass

# Expose a jwt-like namespace
class _JWTModule:
    ExpiredSignatureError = _JWTExpiredError
    InvalidTokenError     = _JWTError

    def __init__(self):
        self._impl = _JWT()

    def encode(self, payload, key, algorithm="HS256"):
        return self._impl.encode(payload, key, algorithm)

    def decode(self, token, key, algorithms=None):
        try:
            return self._impl.decode(token, key, algorithms)
        except _JWTExpiredError:
            raise
        except Exception as e:
            raise _JWTError(str(e)) from e

jwt = _JWTModule()

try:
    import redis.asyncio as aioredis
    from redis.exceptions import RedisError
    _HAS_REDIS = True
except ImportError:
    _HAS_REDIS = False
    RedisError = Exception  # type: ignore

try:
    from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST, REGISTRY
    _HAS_PROMETHEUS = True
except ImportError:
    _HAS_PROMETHEUS = False

try:
    from sse_starlette.sse import EventSourceResponse
    _HAS_SSE = True
except ImportError:
    _HAS_SSE = False

try:
    import aiohttp
    _HAS_AIOHTTP = True
except ImportError:
    _HAS_AIOHTTP = False

import uvicorn

# ==================== 配置和日志 ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
)
logger = logging.getLogger(__name__)

# Bearer token 提取器（auto_error=False → 未携带token时返回 None 而非 401）
_bearer_scheme = HTTPBearer(auto_error=False)


# ==================== 数据模型 ====================
class UserType(Enum):
    B2B_BUYER    = "b2b_buyer"
    B2C_CONSUMER = "b2c_consumer"
    INTERNAL     = "internal"
    PARTNER      = "partner"


class ClientType(Enum):
    WEB     = "web"
    MOBILE  = "mobile"
    DESKTOP = "desktop"
    API     = "api"


@dataclass
class UserIdentity:
    user_id:     str
    username:    str
    user_type:   UserType
    company_id:  Optional[str]       = None
    department:  Optional[str]       = None
    roles:       List[str]           = field(default_factory=list)
    permissions: List[str]           = field(default_factory=list)
    created_at:  datetime            = field(default_factory=datetime.now)
    expires_at:  Optional[datetime]  = None

    def is_valid(self) -> bool:
        return not (self.expires_at and datetime.now() > self.expires_at)

    def has_permission(self, permission: str) -> bool:
        if f"{permission.split(':')[0]}:*" in self.permissions:
            return True
        return permission in self.permissions

    def has_role(self, role: str) -> bool:
        return role in self.roles

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id":    self.user_id,
            "username":   self.username,
            "user_type":  self.user_type.value,
            "company_id": self.company_id,
            "department": self.department,
            "roles":      self.roles,
            "permissions": self.permissions,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }


@dataclass
class ClientInfo:
    client_id:   str
    client_type: ClientType
    ip_address:  str
    user_agent:  Optional[str] = None
    app_version: Optional[str] = None
    device_id:   Optional[str] = None
    platform:    Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "client_id":   self.client_id,
            "client_type": self.client_type.value,
            "ip_address":  self.ip_address,
            "user_agent":  self.user_agent,
            "app_version": self.app_version,
            "device_id":   self.device_id,
            "platform":    self.platform,
        }


@dataclass
class RateLimitConfig:
    limit:  int        # 请求次数上限
    window: int        # 时间窗口（秒）
    burst:  int = 0    # 允许的突发量（预留）

    def redis_key(self, user_id: str, endpoint: str) -> str:
        return f"rate_limit:{user_id}:{endpoint}"


@dataclass
class CircuitBreakerConfig:
    failure_threshold: int   = 5    # 触发熔断的连续失败次数
    recovery_timeout:  int   = 30   # 熔断恢复等待秒数
    half_open_max:     int   = 3    # 半开状态最大试探请求数


# ==================== API 请求 / 响应模型 ====================
class TokenRequest(BaseModel):
    username:    str        = Field(..., min_length=1, max_length=50)
    password:    str        = Field(..., min_length=6, max_length=100)
    client_type: ClientType = Field(default=ClientType.WEB)
    device_id:   Optional[str] = None


class TokenResponse(BaseModel):
    access_token:  str
    refresh_token: str
    token_type:    str = "Bearer"
    expires_in:    int
    user_id:       str
    user_type:     str


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., description="刷新令牌")


class APIRequest(BaseModel):
    session_id: Optional[str] = Field(default_factory=lambda: f"session_{uuid.uuid4().hex[:8]}")
    input_type: str            = Field(..., description="输入类型: text | image | voice | link")
    content:    str            = Field(..., description="输入内容（文本或 base64 编码）")
    metadata:   Optional[Dict[str, Any]] = Field(default_factory=dict)

    @validator("input_type")
    def _validate_input_type(cls, v):
        if v not in ("text", "image", "voice", "link"):
            raise ValueError("input_type 必须是 text / image / voice / link 之一")
        return v


class WebSocketMessage(BaseModel):
    message_id: str      = Field(default_factory=lambda: str(uuid.uuid4()))
    type:       str      = Field(..., description="消息类型: text | voice | command")
    content:    str
    timestamp:  datetime = Field(default_factory=datetime.now)
    metadata:   Optional[Dict[str, Any]] = Field(default_factory=dict)

    @validator("type")
    def _validate_type(cls, v):
        if v not in ("text", "voice", "command"):
            raise ValueError("消息类型必须是 text / voice / command 之一")
        return v


# ==================== 认证服务 ====================
class AuthenticationService:
    """JWT 认证 + 令牌黑名单"""

    def __init__(self,
                 secret_key:                   str,
                 algorithm:                    str = "HS256",
                 access_token_expire_minutes:  int = 30,
                 refresh_token_expire_days:    int = 7):
        self.secret_key                  = secret_key
        self.algorithm                   = algorithm
        self.access_token_expire_minutes = access_token_expire_minutes
        # BUG FIX: skeleton stored as self.refresh_token_expire but used
        # self.refresh_token_expire_days in create_refresh_token → use one name
        self.refresh_token_expire_days   = refresh_token_expire_days
        self.users_db                    = self._init_users_db()
        # 黑名单用 set；生产环境应存入 Redis
        self._token_blacklist: set       = set()

    @staticmethod
    def _hash_password(password: str) -> str:
        return hashlib.sha256(password.encode()).hexdigest()

    def _init_users_db(self) -> Dict[str, Dict[str, Any]]:
        return {
            "b2b_user_001": {
                "username":      "b2b_buyer",
                "password_hash": self._hash_password("b2b_password_123"),
                "user_type":     UserType.B2B_BUYER,
                "company_id":    "company_001",
                "department":    "采购部",
                "roles":         ["buyer", "approver"],
                "permissions":   ["product:view", "product:purchase", "order:create"],
            },
            "b2c_user_001": {
                "username":      "b2c_consumer",
                "password_hash": self._hash_password("b2c_password_123"),
                "user_type":     UserType.B2C_CONSUMER,
                "roles":         ["consumer"],
                "permissions":   ["product:view", "product:purchase", "cart:manage"],
            },
            "internal_user_001": {
                "username":      "internal_admin",
                "password_hash": self._hash_password("internal_password_123"),
                "user_type":     UserType.INTERNAL,
                "department":    "技术部",
                "roles":         ["admin", "developer"],
                "permissions":   ["product:*", "order:*", "user:*"],
            },
        }

    def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        pw_hash = self._hash_password(password)
        for uid, data in self.users_db.items():
            if data["username"] == username and data["password_hash"] == pw_hash:
                return {"user_id": uid, **data}
        return None

    def create_access_token(self, user_data: Dict[str, Any]) -> str:
        expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        payload: Dict[str, Any] = {
            "sub":         user_data["user_id"],
            "username":    user_data["username"],
            "user_type":   user_data["user_type"].value,
            "exp":         expire,
            "iat":         datetime.utcnow(),
            "jti":         str(uuid.uuid4()),
            "roles":       user_data.get("roles", []),
            "permissions": user_data.get("permissions", []),
        }
        if "company_id" in user_data:
            payload["company_id"] = user_data["company_id"]
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def create_refresh_token(self, user_id: str) -> str:
        # BUG FIX: was self.refresh_token_expire_days (undefined) in skeleton
        expire = datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)
        payload = {
            "sub":  user_id,
            "type": "refresh",
            "exp":  expire,
            "iat":  datetime.utcnow(),
            "jti":  str(uuid.uuid4()),
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        if token in self._token_blacklist:
            logger.warning("Attempt to use revoked token")
            return None
        try:
            return jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
        except jwt.ExpiredSignatureError:
            logger.info("Token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None

    def revoke_token(self, token: str) -> bool:
        self._token_blacklist.add(token)
        return True

    def refresh_access_token(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        payload = self.verify_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            return None
        uid = payload.get("sub")
        if not uid or uid not in self.users_db:
            return None
        user_data = {"user_id": uid, **self.users_db[uid]}
        return {
            "access_token":  self.create_access_token(user_data),
            "refresh_token": refresh_token,  # 复用原 refresh_token
            "user_id":       uid,
            "user_type":     self.users_db[uid]["user_type"].value,
        }


# ==================== 限流服务 ====================
class _InMemoryRateLimiter:
    """Redis 不可用时的内存滑动窗口限流回退实现"""

    def __init__(self):
        self._windows: Dict[str, List[float]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def check(self, key: str, limit: int, window: int) -> Tuple[bool, int]:
        """返回 (is_limited, remaining)"""
        now = time.monotonic()
        cutoff = now - window
        async with self._lock:
            ts = [t for t in self._windows[key] if t > cutoff]
            is_limited = len(ts) >= limit
            if not is_limited:
                ts.append(now)
            self._windows[key] = ts
        remaining = max(0, limit - len(ts))
        return is_limited, remaining


class RateLimitService:
    """滑动窗口限流服务（Redis 优先，内存回退）"""

    # BUG FIX: skeleton's rate_limits dict keyed by UserType, but the
    # is_rate_limited / check_rate_limit method signatures were inconsistent.
    # Unified into a single check_rate_limit(user_id, user_type, endpoint).

    _RATE_LIMITS: Dict[UserType, Dict[str, RateLimitConfig]] = {
        UserType.B2B_BUYER: {
            "default":     RateLimitConfig(limit=1000, window=60),
            "api_process": RateLimitConfig(limit=500,  window=60),
            "ws_chat":     RateLimitConfig(limit=200,  window=60),
        },
        UserType.B2C_CONSUMER: {
            "default":     RateLimitConfig(limit=100,  window=60),
            "api_process": RateLimitConfig(limit=50,   window=60),
            "ws_chat":     RateLimitConfig(limit=20,   window=60),
        },
        UserType.INTERNAL: {
            "default":     RateLimitConfig(limit=10000, window=60),
            "api_process": RateLimitConfig(limit=5000,  window=60),
            "ws_chat":     RateLimitConfig(limit=1000,  window=60),
        },
        UserType.PARTNER: {
            "default":     RateLimitConfig(limit=500,  window=60),
            "api_process": RateLimitConfig(limit=200,  window=60),
            "ws_chat":     RateLimitConfig(limit=100,  window=60),
        },
    }

    def __init__(self, redis_client: Optional[Any] = None):
        self.redis        = redis_client
        self._mem_limiter = _InMemoryRateLimiter()

    def _get_config(self, user_type: UserType, endpoint: str) -> RateLimitConfig:
        limits = self._RATE_LIMITS.get(user_type, self._RATE_LIMITS[UserType.B2C_CONSUMER])
        return limits.get(endpoint, limits["default"])

    async def check_rate_limit(self,
                               user_id: str,
                               user_type: UserType,
                               endpoint: str) -> Tuple[bool, Dict[str, Any]]:
        """
        返回 (is_limited, info_dict)
        info_dict: {limited, limit, remaining, reset, window}
        """
        cfg = self._get_config(user_type, endpoint)
        now = int(time.time())

        if self.redis is not None:
            try:
                key         = cfg.redis_key(user_id, endpoint)
                window_start = now - cfg.window
                pipe        = self.redis.pipeline()
                pipe.zremrangebyscore(key, 0, window_start)
                pipe.zcard(key)
                pipe.zadd(key, {str(uuid.uuid4()): now})
                pipe.expire(key, cfg.window + 10)
                results     = await pipe.execute()
                count       = results[1]
                is_limited  = count >= cfg.limit
                remaining   = max(0, cfg.limit - count - (0 if is_limited else 1))
                return is_limited, {
                    "limited":   is_limited,
                    "limit":     cfg.limit,
                    "remaining": remaining,
                    "reset":     now + cfg.window,
                    "window":    cfg.window,
                }
            except Exception as e:
                logger.warning(f"Redis rate-limit error, falling back to memory: {e}")

        # 内存回退
        key        = f"{user_id}:{endpoint}"
        is_limited, remaining = await self._mem_limiter.check(key, cfg.limit, cfg.window)
        return is_limited, {
            "limited":   is_limited,
            "limit":     cfg.limit,
            "remaining": remaining,
            "reset":     now + cfg.window,
            "window":    cfg.window,
        }


# ==================== 熔断器 ====================
class CircuitBreakerService:
    """手动实现的轻量熔断器（closed → open → half-open → closed）"""

    def __init__(self):
        # {service_name: {state, failure_count, half_open_calls,
        #                  last_failure_time, last_state_change}}
        self._circuits: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    def _get_or_create(self, service_name: str) -> Dict[str, Any]:
        if service_name not in self._circuits:
            self._circuits[service_name] = {
                "state":           "closed",
                "failure_count":   0,
                "half_open_calls": 0,
                "last_failure_time":  None,
                "last_state_change":  datetime.now(),
            }
        return self._circuits[service_name]

    def get_state(self, service_name: str) -> Dict[str, Any]:
        return dict(self._get_or_create(service_name))

    def should_allow_request(self,
                              service_name: str,
                              cfg: CircuitBreakerConfig) -> bool:
        c = self._get_or_create(service_name)
        if c["state"] == "closed":
            return True
        if c["state"] == "open":
            elapsed = (datetime.now() - c["last_state_change"]).total_seconds()
            if elapsed >= cfg.recovery_timeout:
                c["state"]            = "half-open"
                c["half_open_calls"]  = 0
                c["last_state_change"] = datetime.now()
                logger.info(f"Circuit '{service_name}' → half-open")
                return True
            return False
        # half-open: allow limited probe requests
        if c["half_open_calls"] < cfg.half_open_max:
            c["half_open_calls"] += 1
            return True
        return False

    def record_success(self, service_name: str):
        c = self._get_or_create(service_name)
        if c["state"] in ("half-open", "open"):
            c["state"]            = "closed"
            c["last_state_change"] = datetime.now()
            logger.info(f"Circuit '{service_name}' → closed (recovered)")
        c["failure_count"]  = 0
        c["half_open_calls"] = 0

    def record_failure(self, service_name: str, cfg: CircuitBreakerConfig):
        c = self._get_or_create(service_name)
        c["failure_count"]    += 1
        c["last_failure_time"] = datetime.now()
        if c["state"] == "closed" and c["failure_count"] >= cfg.failure_threshold:
            c["state"]            = "open"
            c["last_state_change"] = datetime.now()
            logger.warning(f"Circuit '{service_name}' → open "
                           f"(failures={c['failure_count']})")
        elif c["state"] == "half-open":
            # probe request failed → re-open
            c["state"]            = "open"
            c["last_state_change"] = datetime.now()
            logger.warning(f"Circuit '{service_name}' → open (half-open probe failed)")


# ==================== WebSocket 连接管理器 ====================
class WebSocketConnectionManager:
    """WebSocket 连接池 + 消息投递"""

    def __init__(self):
        # {connection_id: {websocket, user_id, client_info, connected_at, last_activity}}
        self._connections: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def connect(self,
                      websocket: WebSocket,
                      user_id: str,
                      client_info: ClientInfo) -> str:
        connection_id = f"ws_{user_id}_{uuid.uuid4().hex[:8]}"
        await websocket.accept()
        async with self._lock:
            self._connections[connection_id] = {
                "websocket":    websocket,
                "user_id":      user_id,
                "client_info":  client_info,
                "connected_at": datetime.now(),
                "last_activity": datetime.now(),
            }
        logger.info(f"WS connected  conn={connection_id} user={user_id}")
        return connection_id

    async def disconnect(self, connection_id: str):
        async with self._lock:
            info = self._connections.pop(connection_id, None)
        if info:
            logger.info(f"WS disconnected conn={connection_id} user={info['user_id']}")

    async def send(self, connection_id: str, message: Dict[str, Any]) -> bool:
        """发送消息；返回 False 表示连接已断开"""
        async with self._lock:
            conn = self._connections.get(connection_id)
        if not conn:
            return False
        try:
            await conn["websocket"].send_json(message)
            conn["last_activity"] = datetime.now()
            return True
        except Exception as e:
            logger.warning(f"WS send error conn={connection_id}: {e}")
            await self.disconnect(connection_id)
            return False

    async def broadcast(self,
                        message: Dict[str, Any],
                        exclude: Optional[List[str]] = None):
        exclude = set(exclude or [])
        async with self._lock:
            targets = list(self._connections.keys())
        for cid in targets:
            if cid not in exclude:
                await self.send(cid, message)

    def get_connection_info(self, connection_id: str) -> Optional[Dict[str, Any]]:
        conn = self._connections.get(connection_id)
        if not conn:
            return None
        return {
            "connection_id":  connection_id,
            "user_id":        conn["user_id"],
            "client_info":    conn["client_info"].to_dict(),
            "connected_at":   conn["connected_at"].isoformat(),
            "last_activity":  conn["last_activity"].isoformat(),
        }

    def get_all_connections(self) -> List[Dict[str, Any]]:
        return [self.get_connection_info(cid)
                for cid in list(self._connections.keys())
                if self.get_connection_info(cid)]

    async def cleanup_inactive(self, timeout_seconds: int = 300):
        cutoff = datetime.now()
        async with self._lock:
            stale = [cid for cid, c in self._connections.items()
                     if (cutoff - c["last_activity"]).total_seconds() > timeout_seconds]
        for cid in stale:
            logger.info(f"Evicting stale WS conn={cid}")
            await self.disconnect(cid)

    @property
    def active_count(self) -> int:
        return len(self._connections)


# ==================== API 网关服务 ====================
class APIGatewayService:
    """代理 + 鉴权 + 熔断 + Prometheus 指标收集"""

    _CB_CONFIG = CircuitBreakerConfig(failure_threshold=5, recovery_timeout=30)

    def __init__(self,
                 auth_service:          AuthenticationService,
                 rate_limit_service:    RateLimitService,
                 circuit_breaker:       CircuitBreakerService,
                 backend_service_url:   str = "http://localhost:8010"):
        self.auth           = auth_service
        self.rate_limiter   = rate_limit_service
        self.circuit_breaker = circuit_breaker
        self.backend_url    = backend_service_url.rstrip("/")
        self._http: Optional[Any] = None   # aiohttp.ClientSession
        self._start_time    = time.monotonic()
        self._req_counts: Dict[str, int] = defaultdict(int)
        self._req_errors:  Dict[str, int] = defaultdict(int)

        # Prometheus 指标（可选）
        if _HAS_PROMETHEUS:
            try:
                self._req_counter = Counter(
                    "gw_requests_total", "Total gateway requests",
                    ["method", "endpoint", "status"])
                self._req_latency = Histogram(
                    "gw_request_duration_seconds", "Request latency",
                    ["method", "endpoint"])
            except Exception:
                self._req_counter = None   # type: ignore
                self._req_latency = None   # type: ignore
        else:
            self._req_counter = None  # type: ignore
            self._req_latency = None  # type: ignore

    async def startup(self):
        if _HAS_AIOHTTP:
            self._http = aiohttp.ClientSession(
                connector=aiohttp.TCPConnector(limit=100),
                timeout=aiohttp.ClientTimeout(total=30),
            )

    async def shutdown(self):
        if self._http:
            await self._http.close()

    # ── 认证 ───────────────────────────────────────────────────
    def authenticate_token(self, token: str) -> Optional[UserIdentity]:
        payload = self.auth.verify_token(token)
        if not payload:
            return None
        try:
            return UserIdentity(
                user_id=payload["sub"],
                username=payload["username"],
                user_type=UserType(payload["user_type"]),
                company_id=payload.get("company_id"),
                roles=payload.get("roles", []),
                permissions=payload.get("permissions", []),
                expires_at=datetime.fromtimestamp(payload["exp"]) if "exp" in payload else None,
            )
        except Exception as e:
            logger.warning(f"Identity construction error: {e}")
            return None

    # ── 代理转发 ────────────────────────────────────────────────
    async def forward(self,
                      method: str,
                      path: str,
                      identity: Optional[UserIdentity] = None,
                      data: Optional[Dict] = None,
                      params: Optional[Dict] = None,
                      extra_headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        if not self.circuit_breaker.should_allow_request("backend", self._CB_CONFIG):
            raise HTTPException(status_code=503,
                                detail="Service temporarily unavailable — circuit open")

        url = f"{self.backend_url}{path}"
        headers: Dict[str, str] = extra_headers or {}
        if identity:
            headers["X-User-Id"]   = identity.user_id
            headers["X-User-Type"] = identity.user_type.value

        t0 = time.monotonic()
        label = path.split("?")[0][:40]
        self._req_counts[label] += 1

        try:
            if self._http:
                async with self._http.request(
                    method, url, json=data, params=params,
                    headers=headers,
                ) as resp:
                    latency = time.monotonic() - t0
                    body    = await resp.json(content_type=None)
                    self._record_metrics(method, label, resp.status < 400, latency)
                    if resp.status >= 400:
                        self.circuit_breaker.record_failure("backend", self._CB_CONFIG)
                    else:
                        self.circuit_breaker.record_success("backend")
                    return {"status_code": resp.status, "data": body}
            else:
                # aiohttp 不可用 → 返回模拟成功（仅用于单元测试）
                self.circuit_breaker.record_success("backend")
                return {"status_code": 200, "data": {"success": True, "message": "mock"}}
        except Exception as exc:
            self._req_errors[label] += 1
            self.circuit_breaker.record_failure("backend", self._CB_CONFIG)
            logger.error(f"Backend forward error {method} {url}: {exc}")
            raise HTTPException(status_code=502, detail="Backend service error")

    def _record_metrics(self, method: str, endpoint: str, ok: bool, latency: float):
        if self._req_counter:
            try:
                status = "success" if ok else "error"
                self._req_counter.labels(method=method, endpoint=endpoint, status=status).inc()
                self._req_latency.labels(method=method, endpoint=endpoint).observe(latency)
            except Exception:
                pass

    async def process_multimodal_request(self,
                                          identity: UserIdentity,
                                          request_data: Dict[str, Any]) -> Dict[str, Any]:
        if not identity.has_permission("product:view"):
            raise HTTPException(status_code=403, detail="权限不足")
        result = await self.forward("POST", "/process", identity=identity, data=request_data)
        return result.get("data", {})

    async def get_metrics(self) -> Dict[str, Any]:
        return {
            "uptime_seconds":     round(time.monotonic() - self._start_time, 1),
            "circuit_state":      self.circuit_breaker.get_state("backend"),
            "request_counts":     dict(self._req_counts),
            "request_errors":     dict(self._req_errors),
            "backend_url":        self.backend_url,
        }


# ==================== FastAPI 网关应用 ====================
class GatewayApplication:
    """
    API 网关 FastAPI 应用。

    架构修正说明（相对于骨架代码）：
    1. FastAPI 依赖注入使用 HTTPBearer + Depends 闭包，而非裸 Optional[str] 参数。
    2. _get_admin_user 正确地依赖 _require_user 闭包，而非未绑定方法。
    3. refresh_token 端点接受 RefreshRequest body，而非 str Body embed。
    4. /metrics 端点返回 text/plain（Prometheus 格式），而非 JSON。
    5. 新增 GET /api/v1/events/{session_id} — SSE 实时推送端点。
    6. RateLimitService 统一调用 check_rate_limit(user_id, user_type, endpoint)。
    7. Redis 不可用时透明回退到内存限流，不阻断请求。
    8. 所有 ClientType 解析做 try/except，无效值回退到 ClientType.API。
    """

    def __init__(self,
                 secret_key:          str = "CHANGE_ME_IN_PRODUCTION",
                 redis_url:           str = "redis://localhost:6379",
                 backend_service_url: str = "http://localhost:8010"):
        self._secret_key  = secret_key
        self._redis_url   = redis_url
        self._backend_url = backend_service_url

        self.auth         = AuthenticationService(
            secret_key=secret_key,
            access_token_expire_minutes=30,
            refresh_token_expire_days=7,
        )
        self.circuit_breaker = CircuitBreakerService()
        self.ws_manager      = WebSocketConnectionManager()

        # 延迟初始化（在 startup 中完成）
        self._redis:        Optional[Any]            = None
        self.rate_limiter:  Optional[RateLimitService]  = None
        self.gateway:       Optional[APIGatewayService] = None

        self.app = FastAPI(
            title="多模态商品识别系统 — 接入层",
            description="API 网关 · JWT 认证 · 滑动窗口限流 · 熔断器 · WebSocket · SSE",
            version="1.0.0",
            docs_url="/api/docs",
            redoc_url="/api/redoc",
        )

        self._setup_middleware()
        self._setup_routes()
        self._setup_lifespan()

    # ── 中间件 ──────────────────────────────────────────────────
    def _setup_middleware(self):
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        @self.app.middleware("http")
        async def _request_id_middleware(request: Request, call_next):
            request_id = request.headers.get("X-Request-Id", str(uuid.uuid4()))
            response   = await call_next(request)
            response.headers["X-Request-Id"] = request_id
            return response

    # ── 依赖函数（闭包绑定到 self）─────────────────────────────
    def _make_optional_user_dep(self):
        """返回可选鉴权依赖：未携带 token → None"""
        gw = self  # close over self

        async def _dep(
            credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
        ) -> Optional[UserIdentity]:
            if not credentials:
                return None
            identity = gw.gateway.authenticate_token(credentials.credentials)
            return identity

        return _dep

    def _make_require_user_dep(self):
        """返回必须鉴权依赖：未携带或无效 token → 401"""
        opt_dep = self._make_optional_user_dep()

        async def _dep(
            identity: Optional[UserIdentity] = Depends(opt_dep),
        ) -> UserIdentity:
            if not identity or not identity.is_valid():
                raise HTTPException(
                    status_code=401,
                    detail="未认证，请提供有效的 Bearer token",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            return identity

        return _dep

    def _make_admin_dep(self):
        req_dep = self._make_require_user_dep()

        async def _dep(
            identity: UserIdentity = Depends(req_dep),
        ) -> UserIdentity:
            if not identity.has_role("admin"):
                raise HTTPException(status_code=403, detail="需要管理员权限")
            return identity

        return _dep

    @staticmethod
    def _extract_client_info(request: Request) -> ClientInfo:
        raw_ct = request.headers.get("X-Client-Type", "api")
        try:
            ct = ClientType(raw_ct.lower())
        except ValueError:
            ct = ClientType.API
        ip = request.client.host if request.client else "unknown"
        return ClientInfo(
            client_id=request.headers.get("X-Client-Id", str(uuid.uuid4())),
            client_type=ct,
            ip_address=ip,
            user_agent=request.headers.get("user-agent"),
            app_version=request.headers.get("X-App-Version"),
            device_id=request.headers.get("X-Device-Id"),
            platform=request.headers.get("X-Platform"),
        )

    # ── 限流辅助 ────────────────────────────────────────────────
    async def _enforce_rate_limit(self,
                                   identity: UserIdentity,
                                   endpoint: str):
        is_limited, info = await self.rate_limiter.check_rate_limit(
            identity.user_id, identity.user_type, endpoint)
        if is_limited:
            raise HTTPException(
                status_code=429,
                detail="请求过于频繁，请稍后再试",
                headers={
                    "X-RateLimit-Limit":     str(info["limit"]),
                    "X-RateLimit-Remaining": str(info["remaining"]),
                    "X-RateLimit-Reset":     str(info["reset"]),
                    "Retry-After":           str(info["window"]),
                },
            )
        return info

    # ── 路由 ────────────────────────────────────────────────────
    def _setup_routes(self):
        app = self.app

        # ── 健康检查 ─────────────────────────────────────────
        @app.get("/health", tags=["运维"])
        async def health_check():
            return {
                "status":    "healthy",
                "timestamp": datetime.now().isoformat(),
                "services": {
                    "authentication": "ok",
                    "rate_limit":  "ok" if self.rate_limiter else "not_initialized",
                    "circuit_breaker": "ok",
                    "websocket":  "ok",
                    "api_gateway": "ok" if self.gateway else "not_initialized",
                },
            }

        # ── Prometheus 指标 ───────────────────────────────────
        @app.get("/metrics", tags=["运维"])
        async def prometheus_metrics():
            if not _HAS_PROMETHEUS:
                return PlainTextResponse("# prometheus_client not installed\n",
                                         media_type="text/plain")
            return PlainTextResponse(
                generate_latest(REGISTRY).decode(),
                media_type="text/plain; version=0.0.4",
            )

        # ── 登录 ─────────────────────────────────────────────
        @app.post("/api/v1/auth/token", response_model=TokenResponse, tags=["认证"])
        async def login(req: TokenRequest):
            user_data = self.auth.authenticate_user(req.username, req.password)
            if not user_data:
                raise HTTPException(status_code=401, detail="用户名或密码错误")
            access_token  = self.auth.create_access_token(user_data)
            refresh_token = self.auth.create_refresh_token(user_data["user_id"])
            return TokenResponse(
                access_token=access_token,
                refresh_token=refresh_token,
                expires_in=self.auth.access_token_expire_minutes * 60,
                user_id=user_data["user_id"],
                user_type=user_data["user_type"].value,
            )

        # ── 刷新 Token ───────────────────────────────────────
        # BUG FIX: skeleton used `str = Body(..., embed=True)` without Body imported;
        # replaced with a proper Pydantic body model.
        @app.post("/api/v1/auth/refresh", tags=["认证"])
        async def refresh_token(req: RefreshRequest):
            result = self.auth.refresh_access_token(req.refresh_token)
            if not result:
                raise HTTPException(status_code=401, detail="无效或已过期的 refresh_token")
            return result

        # ── 登出 ─────────────────────────────────────────────
        # BUG FIX: skeleton used `authorization: Optional[str] = None` which FastAPI
        # won't auto-populate from the Authorization header.  Use HTTPBearer.
        _require_user = self._make_require_user_dep()

        @app.post("/api/v1/auth/logout", tags=["认证"])
        async def logout(
            credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
            _identity: UserIdentity = Depends(_require_user),
        ):
            if credentials:
                self.auth.revoke_token(credentials.credentials)
            return {"message": "已成功登出"}

        # ── 多模态处理 ───────────────────────────────────────
        @app.post("/api/v1/process", tags=["多模态"])
        async def process_multimodal(
            req:      APIRequest,
            request:  Request,
            identity: UserIdentity = Depends(_require_user),
        ):
            rate_info   = await self._enforce_rate_limit(identity, "api_process")
            client_info = self._extract_client_info(request)
            req_dict    = req.dict()
            req_dict["metadata"] = req_dict.get("metadata") or {}
            req_dict["metadata"]["client_info"] = client_info.to_dict()
            req_dict["user_id"] = identity.user_id
            result      = await self.gateway.process_multimodal_request(identity, req_dict)
            result["rate_limit"] = rate_info
            return result

        # ── SSE 实时推送 ─────────────────────────────────────
        # BUG FIX: skeleton imported EventSourceResponse but never used it.
        @app.get("/api/v1/events/{session_id}", tags=["多模态"])
        async def sse_events(
            session_id: str,
            identity:   UserIdentity = Depends(_require_user),
        ):
            """Server-Sent Events 端点，每秒推送一次心跳（可扩展为真实事件流）"""
            if not _HAS_SSE:
                raise HTTPException(status_code=501,
                                    detail="sse-starlette 未安装")

            async def _generator() -> AsyncGenerator[Dict[str, str], None]:
                for i in range(30):           # 最长 30 秒
                    yield {
                        "event": "heartbeat",
                        "data":  json.dumps({
                            "session_id": session_id,
                            "seq":        i,
                            "timestamp":  datetime.now().isoformat(),
                        }),
                    }
                    await asyncio.sleep(1)
                yield {"event": "close", "data": json.dumps({"session_id": session_id})}

            return EventSourceResponse(_generator())

        # ── WebSocket 聊天 ───────────────────────────────────
        @app.websocket("/ws/v1/chat")
        async def ws_chat(websocket: WebSocket, token: Optional[str] = None):
            if not token:
                await websocket.close(code=1008, reason="Authentication required")
                return
            identity = self.gateway.authenticate_token(token)
            if not identity or not identity.is_valid():
                await websocket.close(code=1008, reason="Invalid token")
                return
            ip = websocket.client.host if websocket.client else "unknown"
            client_info = ClientInfo(
                client_id=str(uuid.uuid4()), client_type=ClientType.WEB,
                ip_address=ip, user_agent=websocket.headers.get("user-agent"),
            )
            conn_id = await self.ws_manager.connect(websocket, identity.user_id, client_info)
            await self.ws_manager.send(conn_id, {
                "type": "system", "connection_id": conn_id,
                "message": "已连接多模态聊天服务",
                "timestamp": datetime.now().isoformat(),
            })
            try:
                while True:
                    raw = await websocket.receive_json()
                    try:
                        msg = WebSocketMessage(**raw)
                    except Exception as ve:
                        await self.ws_manager.send(conn_id, {
                            "type": "error", "message": f"消息格式错误: {ve}",
                            "timestamp": datetime.now().isoformat(),
                        })
                        continue
                    if   msg.type == "text":    await self._ws_handle_text(conn_id, identity, msg)
                    elif msg.type == "voice":   await self._ws_handle_voice(conn_id, identity, msg)
                    elif msg.type == "command": await self._ws_handle_command(conn_id, identity, msg)
            except WebSocketDisconnect:
                pass
            except Exception as exc:
                logger.error(f"WS error conn={conn_id}: {exc}")
            finally:
                await self.ws_manager.disconnect(conn_id)

        # ── 管理端点 ─────────────────────────────────────────
        _admin_dep = self._make_admin_dep()

        @app.get("/api/v1/admin/connections", tags=["管理"])
        async def admin_connections(identity: UserIdentity = Depends(_admin_dep)):
            conns = self.ws_manager.get_all_connections()
            return {"total": len(conns), "connections": conns}

        @app.get("/api/v1/admin/metrics", tags=["管理"])
        async def admin_metrics(identity: UserIdentity = Depends(_admin_dep)):
            return await self.gateway.get_metrics()

        @app.get("/api/v1/admin/circuit/{service}", tags=["管理"])
        async def admin_circuit(service: str,
                                identity: UserIdentity = Depends(_admin_dep)):
            return self.circuit_breaker.get_state(service)

        @app.get("/api/v1/admin/rate-limit/{user_id}", tags=["管理"])
        async def admin_rate_limit(
            user_id:  str,
            endpoint: str = "api_process",
            ut:       str = "b2c_consumer",
            identity: UserIdentity = Depends(_admin_dep),
        ):
            try:
                user_type = UserType(ut)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"未知 user_type: {ut!r}")
            _, info = await self.rate_limiter.check_rate_limit(user_id, user_type, endpoint)
            return info

        # ── 全局错误处理 ─────────────────────────────────────
        @app.exception_handler(HTTPException)
        async def _http_exc(request: Request, exc: HTTPException):
            return JSONResponse(
                status_code=exc.status_code,
                content={"success": False, "error": exc.detail},
                headers=getattr(exc, "headers", None) or {},
            )

        @app.exception_handler(Exception)
        async def _generic_exc(request: Request, exc: Exception):
            logger.error(f"Unhandled: {exc}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content={"success": False, "error": "服务内部错误"},
            )

    # ── WebSocket 消息处理器 ────────────────────────────────────
    async def _ws_handle_text(self, conn_id: str,
                               identity: UserIdentity,
                               msg: WebSocketMessage):
        _, rate_info = await self.rate_limiter.check_rate_limit(
            identity.user_id, identity.user_type, "ws_chat")
        if rate_info["limited"]:
            await self.ws_manager.send(conn_id, {
                "type": "error", "message": "请求过于频繁，请稍后再试",
                "rate_limit": rate_info, "timestamp": datetime.now().isoformat(),
            })
            return
        req_data = {
            "session_id": msg.metadata.get("session_id", f"ws_{conn_id}"),
            "user_id":    identity.user_id,
            "input_type": "text",
            "content":    msg.content,
            "metadata":   msg.metadata or {},
        }
        try:
            result = await self.gateway.process_multimodal_request(identity, req_data)
            await self.ws_manager.send(conn_id, {
                "type":       "response",
                "message":    result.get("response", {}).get("message", ""),
                "products":   result.get("response", {}).get("products", []),
                "rate_limit": rate_info,
                "timestamp":  datetime.now().isoformat(),
            })
        except Exception as exc:
            logger.error(f"WS text handler error: {exc}")
            await self.ws_manager.send(conn_id, {
                "type": "error", "message": str(exc),
                "timestamp": datetime.now().isoformat(),
            })

    async def _ws_handle_voice(self, conn_id: str,
                                identity: UserIdentity,
                                msg: WebSocketMessage):
        _, rate_info = await self.rate_limiter.check_rate_limit(
            identity.user_id, identity.user_type, "ws_chat")
        if rate_info["limited"]:
            await self.ws_manager.send(conn_id, {
                "type": "error", "message": "请求过于频繁，请稍后再试",
                "rate_limit": rate_info, "timestamp": datetime.now().isoformat(),
            })
            return
        try:
            # content 必须是 base64 编码的音频字节
            audio_b64 = msg.content
            base64.b64decode(audio_b64, validate=True)  # 验证合法性
            req_data = {
                "session_id": msg.metadata.get("session_id", f"ws_{conn_id}"),
                "user_id":    identity.user_id,
                "input_type": "voice",
                "content":    audio_b64,
                "metadata":   msg.metadata or {},
            }
            result = await self.gateway.process_multimodal_request(identity, req_data)
            await self.ws_manager.send(conn_id, {
                "type":       "response",
                "message":    result.get("response", {}).get("message", ""),
                "products":   result.get("response", {}).get("products", []),
                "rate_limit": rate_info,
                "timestamp":  datetime.now().isoformat(),
            })
        except Exception as exc:
            logger.error(f"WS voice handler error: {exc}")
            await self.ws_manager.send(conn_id, {
                "type": "error", "message": f"语音处理错误: {exc}",
                "timestamp": datetime.now().isoformat(),
            })

    async def _ws_handle_command(self, conn_id: str,
                                  identity: UserIdentity,
                                  msg: WebSocketMessage):
        cmd = msg.content.strip().lower()
        if cmd == "help":
            text = ("可用命令:\n"
                    "  help     — 显示帮助\n"
                    "  status   — 连接状态\n"
                    "  ping     — 延迟测试\n"
                    "  clear    — 清空本地对话（客户端侧）")
        elif cmd == "status":
            info = self.ws_manager.get_connection_info(conn_id) or {}
            text = json.dumps(info, ensure_ascii=False, indent=2)
        elif cmd == "ping":
            text = f"pong  {datetime.now().isoformat()}"
        elif cmd == "clear":
            text = "已发送清空指令（客户端执行）"
        else:
            text = f"未知命令: {cmd!r}，输入 help 查看可用命令"
        await self.ws_manager.send(conn_id, {
            "type": "system", "message": text,
            "timestamp": datetime.now().isoformat(),
        })

    # ── 生命周期 ────────────────────────────────────────────────
    def _setup_lifespan(self):
        # BUG FIX: skeleton tried to assign self.app.router.lifespan_context
        # which is not the public FastAPI lifespan API.
        # Correct approach: on_event decorators (compatible with FastAPI ≤ 0.95)
        # or lifespan= constructor parameter (FastAPI ≥ 0.95).

        @self.app.on_event("startup")
        async def _startup():
            await self._startup()

        @self.app.on_event("shutdown")
        async def _shutdown():
            await self._shutdown()

    async def _startup(self):
        logger.info("Gateway startup…")

        # Redis（可选）
        if _HAS_REDIS:
            try:
                self._redis = aioredis.from_url(
                    self._redis_url, encoding="utf-8", decode_responses=True)
                await self._redis.ping()
                logger.info("Redis connected")
            except Exception as e:
                logger.warning(f"Redis unavailable ({e}), using in-memory rate limiter")
                self._redis = None

        self.rate_limiter = RateLimitService(self._redis)
        self.gateway      = APIGatewayService(
            auth_service=self.auth,
            rate_limit_service=self.rate_limiter,
            circuit_breaker=self.circuit_breaker,
            backend_service_url=self._backend_url,
        )
        await self.gateway.startup()

        # 后台任务：每 60 秒清理不活跃的 WS 连接
        asyncio.create_task(self._periodic_cleanup())
        logger.info("Gateway started")

    async def _shutdown(self):
        logger.info("Gateway shutdown…")
        if self.gateway:
            await self.gateway.shutdown()
        if self._redis:
            try:
                await self._redis.close()
            except Exception:
                pass
        logger.info("Gateway stopped")

    async def _periodic_cleanup(self):
        while True:
            await asyncio.sleep(60)
            try:
                await self.ws_manager.cleanup_inactive(timeout_seconds=300)
            except Exception as e:
                logger.error(f"Cleanup error: {e}")


# ==================== 工厂函数 & 主入口 ====================
def create_app(secret_key:          str = "CHANGE_ME_IN_PRODUCTION",
               redis_url:           str = "redis://localhost:6379",
               backend_service_url: str = "http://localhost:8010") -> FastAPI:
    """创建并返回 FastAPI 应用（供 ASGI 服务器挂载或测试使用）"""
    gw = GatewayApplication(
        secret_key=secret_key,
        redis_url=redis_url,
        backend_service_url=backend_service_url,
    )
    return gw.app


if __name__ == "__main__":
    import os
    uvicorn.run(
        create_app(
            secret_key=os.getenv("JWT_SECRET", "CHANGE_ME_IN_PRODUCTION"),
            redis_url=os.getenv("REDIS_URL", "redis://localhost:6379"),
            backend_service_url=os.getenv("BACKEND_URL", "http://localhost:8010"),
        ),
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8001")),
        log_level="info",
        access_log=True,
    )
