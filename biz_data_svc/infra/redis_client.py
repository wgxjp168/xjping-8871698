"""
Redis 7.2 Cluster 客户端封装
职责：
  1. 会话缓存 (JWT Token)  — TTL 24 小时
  2. 热点商品数据缓存       — TTL 5~30 分钟（随机抖动防缓存雪崩）
  3. 限流计数器             — 滑动窗口 + 固定窗口
  4. 分布式锁               — SET NX PX + Lua 原子释放
"""
from __future__ import annotations

import json
import logging
import random
import time
import uuid
from typing import Any, Dict, Optional

try:
    from redis.cluster import RedisCluster, ClusterNode
    from redis.exceptions import RedisClusterException, RedisError
    _REDIS_AVAILABLE = True
except ImportError:  # pragma: no cover
    _REDIS_AVAILABLE = False

from ..config.settings import Settings

logger = logging.getLogger(__name__)

# Lua 脚本：原子释放锁（只释放自己持有的锁）
_RELEASE_LOCK_SCRIPT = """
if redis.call("GET", KEYS[1]) == ARGV[1] then
    return redis.call("DEL", KEYS[1])
else
    return 0
end
"""


class RedisClient:
    """
    Redis Cluster 客户端，惰性初始化。
    所有方法在 Redis 不可用时降级（日志警告 + 返回 None/False），
    确保业务主流程不因缓存层故障而中断。
    """

    def __init__(self, settings: Optional[Settings] = None):
        self._cfg = settings or Settings()
        self._client: Optional[Any] = None

    # ------------------------------------------------------------------ #
    #  连接管理                                                             #
    # ------------------------------------------------------------------ #

    def _get_client(self):
        """惰性获取 RedisCluster 连接。"""
        if self._client is not None:
            return self._client
        if not _REDIS_AVAILABLE:
            logger.warning('redis-py 未安装，Redis 功能不可用')
            return None
        try:
            nodes = [
                ClusterNode(host=n.split(':')[0], port=int(n.split(':')[1]))
                for n in self._cfg.redis_nodes.split(',')
                if ':' in n
            ]
            self._client = RedisCluster(
                startup_nodes=nodes,
                password=self._cfg.redis_password or None,
                decode_responses=True,
                max_connections=self._cfg.redis_max_connections,
                skip_full_coverage_check=True,
            )
            logger.info('Redis Cluster 连接成功，节点: %s', self._cfg.redis_nodes)
        except (RedisClusterException, Exception) as exc:
            logger.error('Redis Cluster 连接失败: %s', exc)
            self._client = None
        return self._client

    def ping(self) -> bool:
        """健康检查。"""
        c = self._get_client()
        try:
            return bool(c and c.ping())
        except RedisError:
            return False

    # ------------------------------------------------------------------ #
    #  1. 会话缓存（JWT Token）                                            #
    # ------------------------------------------------------------------ #

    def set_session(self, token: str, payload: Dict[str, Any]) -> bool:
        """
        存储 JWT Token 对应的会话数据，TTL = 24 小时。
        key: sess:<token>
        """
        c = self._get_client()
        if not c:
            return False
        key = self._cfg.redis_key_prefix_session + token
        try:
            c.setex(key, self._cfg.redis_ttl_session, json.dumps(payload, ensure_ascii=False))
            return True
        except RedisError as exc:
            logger.error('set_session 失败: %s', exc)
            return False

    def get_session(self, token: str) -> Optional[Dict[str, Any]]:
        """读取会话数据，不存在或已过期返回 None。"""
        c = self._get_client()
        if not c:
            return None
        key = self._cfg.redis_key_prefix_session + token
        try:
            raw = c.get(key)
            return json.loads(raw) if raw else None
        except (RedisError, json.JSONDecodeError) as exc:
            logger.error('get_session 失败: %s', exc)
            return None

    def delete_session(self, token: str) -> bool:
        """登出时删除会话（Token 吊销）。"""
        c = self._get_client()
        if not c:
            return False
        key = self._cfg.redis_key_prefix_session + token
        try:
            return bool(c.delete(key))
        except RedisError as exc:
            logger.error('delete_session 失败: %s', exc)
            return False

    def refresh_session(self, token: str) -> bool:
        """滑动续期：重置 TTL 为 24 小时。"""
        c = self._get_client()
        if not c:
            return False
        key = self._cfg.redis_key_prefix_session + token
        try:
            return bool(c.expire(key, self._cfg.redis_ttl_session))
        except RedisError as exc:
            logger.error('refresh_session 失败: %s', exc)
            return False

    # ------------------------------------------------------------------ #
    #  2. 热点商品缓存                                                     #
    # ------------------------------------------------------------------ #

    def cache_product(self, product_id: int, data: Dict[str, Any],
                      ttl: Optional[int] = None) -> bool:
        """
        缓存商品信息。
        TTL 在 [ttl_product_min, ttl_product_max] 随机抖动，防缓存雪崩。
        key: prod:<product_id>
        """
        c = self._get_client()
        if not c:
            return False
        if ttl is None:
            ttl = random.randint(
                self._cfg.redis_ttl_product_min,
                self._cfg.redis_ttl_product_max,
            )
        key = self._cfg.redis_key_prefix_product + str(product_id)
        try:
            c.setex(key, ttl, json.dumps(data, ensure_ascii=False, default=str))
            return True
        except RedisError as exc:
            logger.error('cache_product 失败: %s', exc)
            return False

    def get_product(self, product_id: int) -> Optional[Dict[str, Any]]:
        """读取商品缓存，未命中返回 None。"""
        c = self._get_client()
        if not c:
            return None
        key = self._cfg.redis_key_prefix_product + str(product_id)
        try:
            raw = c.get(key)
            return json.loads(raw) if raw else None
        except (RedisError, json.JSONDecodeError) as exc:
            logger.error('get_product 失败: %s', exc)
            return None

    def invalidate_product(self, product_id: int) -> bool:
        """商品更新时主动失效缓存。"""
        c = self._get_client()
        if not c:
            return False
        key = self._cfg.redis_key_prefix_product + str(product_id)
        try:
            return bool(c.delete(key))
        except RedisError as exc:
            logger.error('invalidate_product 失败: %s', exc)
            return False

    # ------------------------------------------------------------------ #
    #  3. 限流计数器（固定窗口）                                            #
    # ------------------------------------------------------------------ #

    def check_rate_limit(self, resource: str, identifier: str,
                         limit: int, window_s: Optional[int] = None) -> bool:
        """
        检查并增加计数。若当前计数 <= limit 则允许通过，否则拒绝。
        key: ratelimit:<resource>:<identifier>
        window_s: 窗口时长（秒），默认取配置的 redis_ttl_rate_limit。
        返回: True = 允许；False = 超限
        """
        c = self._get_client()
        if not c:
            return True   # Redis 不可用时放行，避免误拦截
        if window_s is None:
            window_s = self._cfg.redis_ttl_rate_limit
        key = f'{self._cfg.redis_key_prefix_rate_limit}{resource}:{identifier}'
        try:
            pipe = c.pipeline(raised=False)
            pipe.incr(key)
            pipe.expire(key, window_s)
            results = pipe.execute()
            current = results[0]
            return current <= limit
        except RedisError as exc:
            logger.error('check_rate_limit 失败: %s', exc)
            return True

    def get_rate_limit_count(self, resource: str, identifier: str) -> int:
        """查询当前窗口计数。"""
        c = self._get_client()
        if not c:
            return 0
        key = f'{self._cfg.redis_key_prefix_rate_limit}{resource}:{identifier}'
        try:
            val = c.get(key)
            return int(val) if val else 0
        except (RedisError, ValueError):
            return 0

    # ------------------------------------------------------------------ #
    #  4. 分布式锁                                                         #
    # ------------------------------------------------------------------ #

    def acquire_lock(self, resource: str, ttl_s: Optional[int] = None) -> Optional[str]:
        """
        尝试获取分布式锁。
        返回 lock_token（字符串）表示成功，None 表示锁已被持有。
        key: lock:<resource>
        """
        c = self._get_client()
        if not c:
            return str(uuid.uuid4())   # 降级：直接返回 token
        if ttl_s is None:
            ttl_s = self._cfg.redis_ttl_lock
        key = self._cfg.redis_key_prefix_lock + resource
        token = str(uuid.uuid4())
        try:
            ok = c.set(key, token, nx=True, ex=ttl_s)
            return token if ok else None
        except RedisError as exc:
            logger.error('acquire_lock 失败: %s', exc)
            return None

    def release_lock(self, resource: str, token: str) -> bool:
        """
        原子释放锁（Lua 脚本保证只释放自己持有的锁）。
        """
        c = self._get_client()
        if not c:
            return True
        key = self._cfg.redis_key_prefix_lock + resource
        try:
            result = c.eval(_RELEASE_LOCK_SCRIPT, 1, key, token)
            return bool(result)
        except RedisError as exc:
            logger.error('release_lock 失败: %s', exc)
            return False

    def acquire_lock_blocking(self, resource: str, timeout_s: float = 10.0,
                              ttl_s: Optional[int] = None,
                              retry_interval_s: float = 0.1) -> Optional[str]:
        """
        阻塞式获取锁，最多等待 timeout_s 秒。
        返回 lock_token 或 None（超时）。
        """
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            token = self.acquire_lock(resource, ttl_s)
            if token:
                return token
            time.sleep(retry_interval_s)
        logger.warning('acquire_lock_blocking 超时: resource=%s', resource)
        return None
