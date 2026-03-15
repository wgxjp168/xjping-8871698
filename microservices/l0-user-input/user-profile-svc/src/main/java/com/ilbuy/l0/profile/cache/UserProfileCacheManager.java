package com.ilbuy.l0.profile.cache;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.ilbuy.l0.profile.domain.vo.UserProfileVO;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;

import java.time.Duration;
import java.util.Optional;

/**
 * 用户画像 Redis 缓存管理器
 *
 * <p>缓存策略：Cache-Aside 模式
 * <ul>
 *   <li>读：先查Redis，命中则返回；未命中则查MySQL，写入Redis后返回</li>
 *   <li>写：更新MySQL后，主动删除Redis缓存（延迟双删防止脏读）</li>
 * </ul>
 *
 * <p>Key 规则：{@code ilbuy:profile:{userId}}
 * <p>TTL：30分钟（活跃用户访问频繁时自动续期）
 *
 * @author ILbuy Team
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class UserProfileCacheManager {

    private static final String KEY_PREFIX    = "ilbuy:profile:";
    private static final Duration CACHE_TTL   = Duration.ofMinutes(30);

    private final StringRedisTemplate redisTemplate;
    private final ObjectMapper         objectMapper;

    /**
     * 从缓存获取用户画像
     *
     * @param userId 用户ID
     * @return Optional，缓存未命中时为 empty
     */
    public Optional<UserProfileVO> get(Long userId) {
        String key  = buildKey(userId);
        String json = redisTemplate.opsForValue().get(key);
        if (json == null) {
            log.debug("[ProfileCache] 未命中: userId={}", userId);
            return Optional.empty();
        }
        try {
            UserProfileVO vo = objectMapper.readValue(json, UserProfileVO.class);
            // 每次命中时续期（滑动TTL）
            redisTemplate.expire(key, CACHE_TTL);
            log.debug("[ProfileCache] 命中: userId={}", userId);
            return Optional.of(vo);
        } catch (Exception e) {
            log.warn("[ProfileCache] 反序列化失败，删除脏数据: userId={}", userId, e);
            redisTemplate.delete(key);
            return Optional.empty();
        }
    }

    /**
     * 写入缓存
     *
     * @param profile 用户画像
     */
    public void put(UserProfileVO profile) {
        if (profile == null || profile.getUserId() == null) return;
        String key = buildKey(profile.getUserId());
        try {
            String json = objectMapper.writeValueAsString(profile);
            redisTemplate.opsForValue().set(key, json, CACHE_TTL);
            log.debug("[ProfileCache] 写入缓存: userId={}", profile.getUserId());
        } catch (Exception e) {
            log.warn("[ProfileCache] 写入缓存失败: userId={}", profile.getUserId(), e);
        }
    }

    /**
     * 删除缓存（更新后主动淘汰）
     *
     * @param userId 用户ID
     */
    public void evict(Long userId) {
        String key = buildKey(userId);
        Boolean deleted = redisTemplate.delete(key);
        log.debug("[ProfileCache] 淘汰缓存: userId={}, deleted={}", userId, deleted);
    }

    /**
     * 延迟双删（防止写后读到旧数据的竞态问题）
     * 在异步线程中延迟 500ms 后再次删除缓存
     *
     * @param userId 用户ID
     */
    public void delayedEvict(Long userId) {
        evict(userId);
        Thread.ofVirtual().start(() -> {
            try {
                Thread.sleep(500);
                evict(userId);
                log.debug("[ProfileCache] 延迟双删完成: userId={}", userId);
            } catch (InterruptedException ignored) {}
        });
    }

    private String buildKey(Long userId) {
        return KEY_PREFIX + userId;
    }
}
