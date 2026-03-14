package com.ilbuy.common.redis.utils;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.data.redis.core.script.DefaultRedisScript;
import org.springframework.stereotype.Component;

import java.time.Duration;
import java.util.*;
import java.util.concurrent.TimeUnit;

/**
 * Redis 操作工具类
 *
 * <p>封装常用 Redis 操作：
 * <ul>
 *   <li>String 类型：set/get/delete/increment</li>
 *   <li>Hash 类型：hset/hget/hmset/hdel</li>
 *   <li>Set 类型：sadd/smembers/sismember</li>
 *   <li>ZSet 类型：zadd/zrange（排行榜场景）</li>
 *   <li>List 类型：lpush/rpush/lrange</li>
 *   <li>TTL管理：expire/ttl/persist</li>
 *   <li>原子操作：increment/decrement</li>
 * </ul>
 *
 * @author ILbuy Team
 * @version 1.0.0
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class RedisUtils {

    private final RedisTemplate<String, Object> redisTemplate;

    // ==================== String 操作 ====================

    /**
     * 设置缓存（无过期时间）
     */
    public void set(String key, Object value) {
        redisTemplate.opsForValue().set(key, value);
    }

    /**
     * 设置缓存（带过期时间）
     *
     * @param key     缓存键
     * @param value   缓存值
     * @param timeout 过期时间
     * @param unit    时间单位
     */
    public void set(String key, Object value, long timeout, TimeUnit unit) {
        redisTemplate.opsForValue().set(key, value, timeout, unit);
    }

    /**
     * 设置缓存（Duration方式）
     */
    public void set(String key, Object value, Duration duration) {
        redisTemplate.opsForValue().set(key, value, duration);
    }

    /**
     * 获取缓存
     */
    @SuppressWarnings("unchecked")
    public <T> T get(String key) {
        return (T) redisTemplate.opsForValue().get(key);
    }

    /**
     * 删除缓存
     *
     * @return true-删除成功，false-key不存在
     */
    public boolean delete(String key) {
        return Boolean.TRUE.equals(redisTemplate.delete(key));
    }

    /**
     * 批量删除
     *
     * @return 实际删除的数量
     */
    public long deleteBatch(Collection<String> keys) {
        Long count = redisTemplate.delete(keys);
        return count != null ? count : 0;
    }

    /**
     * 判断 Key 是否存在
     */
    public boolean hasKey(String key) {
        return Boolean.TRUE.equals(redisTemplate.hasKey(key));
    }

    /**
     * 设置过期时间
     *
     * @return true-设置成功
     */
    public boolean expire(String key, long timeout, TimeUnit unit) {
        return Boolean.TRUE.equals(redisTemplate.expire(key, timeout, unit));
    }

    /**
     * 获取剩余过期时间（秒）
     *
     * @return 剩余秒数，-1=永久，-2=key不存在
     */
    public long ttl(String key) {
        Long ttl = redisTemplate.getExpire(key, TimeUnit.SECONDS);
        return ttl != null ? ttl : -2;
    }

    /**
     * 原子递增
     *
     * @param key   键
     * @param delta 递增步长（正数）
     * @return 递增后的值
     */
    public long increment(String key, long delta) {
        Long result = redisTemplate.opsForValue().increment(key, delta);
        return result != null ? result : 0;
    }

    /**
     * 原子递减
     */
    public long decrement(String key, long delta) {
        Long result = redisTemplate.opsForValue().increment(key, -delta);
        return result != null ? result : 0;
    }

    /**
     * 仅在 Key 不存在时设置（分布式场景防重）
     *
     * @return true-设置成功（Key之前不存在）
     */
    public boolean setIfAbsent(String key, Object value, long timeout, TimeUnit unit) {
        return Boolean.TRUE.equals(
                redisTemplate.opsForValue().setIfAbsent(key, value, timeout, unit));
    }

    // ==================== Hash 操作 ====================

    /**
     * 设置 Hash 字段
     */
    public void hSet(String key, String field, Object value) {
        redisTemplate.opsForHash().put(key, field, value);
    }

    /**
     * 批量设置 Hash
     */
    public void hSetAll(String key, Map<String, Object> map) {
        redisTemplate.opsForHash().putAll(key, map);
    }

    /**
     * 获取 Hash 字段值
     */
    @SuppressWarnings("unchecked")
    public <T> T hGet(String key, String field) {
        return (T) redisTemplate.opsForHash().get(key, field);
    }

    /**
     * 获取 Hash 所有字段
     */
    public Map<Object, Object> hGetAll(String key) {
        return redisTemplate.opsForHash().entries(key);
    }

    /**
     * 删除 Hash 字段
     */
    public long hDelete(String key, Object... fields) {
        return redisTemplate.opsForHash().delete(key, fields);
    }

    // ==================== Set 操作 ====================

    /**
     * 向 Set 添加成员
     */
    public long sAdd(String key, Object... values) {
        Long count = redisTemplate.opsForSet().add(key, values);
        return count != null ? count : 0;
    }

    /**
     * 判断 Set 中是否包含成员
     */
    public boolean sIsMember(String key, Object value) {
        return Boolean.TRUE.equals(redisTemplate.opsForSet().isMember(key, value));
    }

    /**
     * 获取 Set 所有成员
     */
    public Set<Object> sMembers(String key) {
        return redisTemplate.opsForSet().members(key);
    }

    // ==================== 限流操作（Lua脚本原子执行）====================

    /**
     * 基于计数器的滑动窗口限流
     *
     * <p>使用 Lua 脚本保证原子性：
     * <ol>
     *   <li>计数器不存在则初始化为1，设置TTL</li>
     *   <li>计数器存在则自增1</li>
     *   <li>返回当前计数</li>
     * </ol>
     *
     * @param key      限流Key（如：ratelimit:b:192.168.1.1）
     * @param limit    限流阈值
     * @param windowMs 时间窗口（毫秒）
     * @return true-允许通过，false-超限
     */
    public boolean isAllowed(String key, long limit, long windowMs) {
        String luaScript = """
                local count = redis.call('incr', KEYS[1])
                if count == 1 then
                    redis.call('pexpire', KEYS[1], ARGV[2])
                end
                if count > tonumber(ARGV[1]) then
                    return 0
                end
                return 1
                """;
        DefaultRedisScript<Long> script = new DefaultRedisScript<>(luaScript, Long.class);
        Long result = redisTemplate.execute(script,
                Collections.singletonList(key),
                String.valueOf(limit),
                String.valueOf(windowMs));
        return Long.valueOf(1L).equals(result);
    }

    /**
     * 获取当前限流计数（剩余可用次数）
     *
     * @param key   限流Key
     * @param limit 限流阈值
     * @return 剩余可用次数（负数表示已超限）
     */
    public long getRemainingLimit(String key, long limit) {
        Object current = redisTemplate.opsForValue().get(key);
        if (current == null) {
            return limit;
        }
        long used = Long.parseLong(current.toString());
        return limit - used;
    }
}
