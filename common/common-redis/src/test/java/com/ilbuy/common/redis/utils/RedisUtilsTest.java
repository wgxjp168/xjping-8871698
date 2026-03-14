package com.ilbuy.common.redis.utils;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.redis.core.HashOperations;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.data.redis.core.SetOperations;
import org.springframework.data.redis.core.ValueOperations;
import org.springframework.data.redis.core.script.DefaultRedisScript;

import java.time.Duration;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.TimeUnit;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/**
 * RedisUtils 单元测试（全部使用 Mock，不依赖真实 Redis）
 *
 * @author ILbuy Team
 */
@ExtendWith(MockitoExtension.class)
@DisplayName("RedisUtils 测试")
class RedisUtilsTest {

    @Mock
    private RedisTemplate<String, Object> redisTemplate;

    @Mock
    private ValueOperations<String, Object> valueOps;

    @Mock
    private HashOperations<String, Object, Object> hashOps;

    @Mock
    private SetOperations<String, Object> setOps;

    private RedisUtils redisUtils;

    @BeforeEach
    void setUp() {
        lenient().when(redisTemplate.opsForValue()).thenReturn(valueOps);
        lenient().when(redisTemplate.opsForHash()).thenReturn(hashOps);
        lenient().when(redisTemplate.opsForSet()).thenReturn(setOps);
        redisUtils = new RedisUtils(redisTemplate);
    }

    // ================================================================
    //  String 操作
    // ================================================================

    @Nested
    @DisplayName("String 操作")
    class StringOpsTests {

        @Test
        @DisplayName("set(key, value) 调用 ValueOps.set")
        void set_noExpiry() {
            redisUtils.set("k1", "v1");
            verify(valueOps).set("k1", "v1");
        }

        @Test
        @DisplayName("set(key, value, timeout, unit) 调用带 TTL 的 set")
        void set_withExpiry() {
            redisUtils.set("k1", "v1", 30L, TimeUnit.MINUTES);
            verify(valueOps).set("k1", "v1", 30L, TimeUnit.MINUTES);
        }

        @Test
        @DisplayName("set(key, value, Duration) 调用 Duration 重载")
        void set_withDuration() {
            redisUtils.set("k1", "v1", Duration.ofHours(1));
            verify(valueOps).set("k1", "v1", Duration.ofHours(1));
        }

        @Test
        @DisplayName("get 返回 ValueOps.get 的结果")
        void get_returnsValue() {
            when(valueOps.get("k1")).thenReturn("hello");
            String result = redisUtils.get("k1");
            assertThat(result).isEqualTo("hello");
        }

        @Test
        @DisplayName("delete 返回 true 当 redisTemplate.delete 返回 true")
        void delete_returnsTrue() {
            when(redisTemplate.delete("k1")).thenReturn(true);
            assertThat(redisUtils.delete("k1")).isTrue();
        }

        @Test
        @DisplayName("delete 返回 false 当 key 不存在（null）")
        void delete_nullReturnsFalse() {
            when(redisTemplate.delete("missing")).thenReturn(null);
            assertThat(redisUtils.delete("missing")).isFalse();
        }

        @Test
        @DisplayName("hasKey 返回 Boolean.TRUE 时为 true")
        void hasKey_true() {
            when(redisTemplate.hasKey("k1")).thenReturn(true);
            assertThat(redisUtils.hasKey("k1")).isTrue();
        }

        @Test
        @DisplayName("increment 返回递增后的值")
        void increment_returnsNewValue() {
            when(valueOps.increment("counter", 5L)).thenReturn(10L);
            assertThat(redisUtils.increment("counter", 5L)).isEqualTo(10L);
        }

        @Test
        @DisplayName("decrement 内部使用负数调用 increment")
        void decrement_usesNegativeDelta() {
            when(valueOps.increment("counter", -3L)).thenReturn(7L);
            assertThat(redisUtils.decrement("counter", 3L)).isEqualTo(7L);
        }

        @Test
        @DisplayName("setIfAbsent 返回 true 时表示设置成功")
        void setIfAbsent_success() {
            when(valueOps.setIfAbsent("lock", "1", 10L, TimeUnit.SECONDS)).thenReturn(true);
            assertThat(redisUtils.setIfAbsent("lock", "1", 10L, TimeUnit.SECONDS)).isTrue();
        }

        @Test
        @DisplayName("expire 调用 redisTemplate.expire 并返回结果")
        void expire_setsExpiry() {
            when(redisTemplate.expire("k1", 60L, TimeUnit.SECONDS)).thenReturn(true);
            assertThat(redisUtils.expire("k1", 60L, TimeUnit.SECONDS)).isTrue();
        }

        @Test
        @DisplayName("ttl 返回剩余秒数")
        void ttl_returnsSeconds() {
            when(redisTemplate.getExpire("k1", TimeUnit.SECONDS)).thenReturn(300L);
            assertThat(redisUtils.ttl("k1")).isEqualTo(300L);
        }

        @Test
        @DisplayName("ttl 在 key 不存在（null）时返回 -2")
        void ttl_nullReturnsNegativeTwo() {
            when(redisTemplate.getExpire("missing", TimeUnit.SECONDS)).thenReturn(null);
            assertThat(redisUtils.ttl("missing")).isEqualTo(-2L);
        }
    }

    // ================================================================
    //  Hash 操作
    // ================================================================

    @Nested
    @DisplayName("Hash 操作")
    class HashOpsTests {

        @Test
        @DisplayName("hSet 调用 HashOps.put")
        void hSet_delegatesToPut() {
            redisUtils.hSet("hash-key", "field", "value");
            verify(hashOps).put("hash-key", "field", "value");
        }

        @Test
        @DisplayName("hSetAll 调用 HashOps.putAll")
        void hSetAll_delegatesToPutAll() {
            Map<String, Object> map = Map.of("f1", "v1", "f2", "v2");
            redisUtils.hSetAll("hash-key", map);
            verify(hashOps).putAll("hash-key", map);
        }

        @Test
        @DisplayName("hGet 返回 HashOps.get 结果")
        void hGet_returnsValue() {
            when(hashOps.get("hash-key", "field")).thenReturn("v1");
            String result = redisUtils.hGet("hash-key", "field");
            assertThat(result).isEqualTo("v1");
        }

        @Test
        @DisplayName("hDelete 调用 HashOps.delete 并返回删除数")
        void hDelete_returnsCount() {
            when(hashOps.delete("hash-key", "f1", "f2")).thenReturn(2L);
            assertThat(redisUtils.hDelete("hash-key", "f1", "f2")).isEqualTo(2L);
        }
    }

    // ================================================================
    //  Set 操作
    // ================================================================

    @Nested
    @DisplayName("Set 操作")
    class SetOpsTests {

        @Test
        @DisplayName("sAdd 返回实际添加数量")
        void sAdd_returnsCount() {
            when(setOps.add("set-key", "v1", "v2")).thenReturn(2L);
            assertThat(redisUtils.sAdd("set-key", "v1", "v2")).isEqualTo(2L);
        }

        @Test
        @DisplayName("sIsMember 返回 true 当成员存在")
        void sIsMember_true() {
            when(setOps.isMember("set-key", "v1")).thenReturn(true);
            assertThat(redisUtils.sIsMember("set-key", "v1")).isTrue();
        }

        @Test
        @DisplayName("sMembers 返回所有成员")
        void sMembers_returnsAll() {
            when(setOps.members("set-key")).thenReturn(Set.of("a", "b", "c"));
            assertThat(redisUtils.sMembers("set-key")).containsExactlyInAnyOrder("a", "b", "c");
        }
    }

    // ================================================================
    //  限流操作
    // ================================================================

    @Nested
    @DisplayName("isAllowed 限流")
    class RateLimitTests {

        @Test
        @DisplayName("Lua 脚本返回 1L 时 isAllowed 为 true")
        void isAllowed_scriptReturns1_true() {
            when(redisTemplate.execute(any(DefaultRedisScript.class), anyList(), any(), any()))
                    .thenReturn(1L);
            assertThat(redisUtils.isAllowed("rate:user:1", 100, 60_000)).isTrue();
        }

        @Test
        @DisplayName("Lua 脚本返回 0L 时 isAllowed 为 false（超限）")
        void isAllowed_scriptReturns0_false() {
            when(redisTemplate.execute(any(DefaultRedisScript.class), anyList(), any(), any()))
                    .thenReturn(0L);
            assertThat(redisUtils.isAllowed("rate:user:1", 100, 60_000)).isFalse();
        }

        @Test
        @DisplayName("B2B 限流阈值 1000/min 调用正确参数")
        void isAllowed_b2bLimit() {
            when(redisTemplate.execute(any(DefaultRedisScript.class),
                    eq(List.of("rate:b:192.168.1.1")),
                    eq("1000"), eq("60000")))
                    .thenReturn(1L);
            boolean allowed = redisUtils.isAllowed("rate:b:192.168.1.1", 1000, 60_000);
            assertThat(allowed).isTrue();
        }
    }
}
