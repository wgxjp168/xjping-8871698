package com.ilbuy.product.config;

import org.springframework.boot.autoconfigure.cache.RedisCacheManagerBuilderCustomizer;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.data.redis.cache.RedisCacheConfiguration;
import org.springframework.data.redis.serializer.GenericJackson2JsonRedisSerializer;
import org.springframework.data.redis.serializer.RedisSerializationContext;

import java.time.Duration;

@Configuration
public class CacheConfig {

    public static final String CACHE_PRODUCT_DETAIL    = "product:detail";
    public static final String CACHE_PRODUCT_SEARCH    = "product:search";
    public static final String CACHE_PRODUCT_CATEGORIES = "product:categories";

    @Bean
    public RedisCacheManagerBuilderCustomizer redisCacheManagerBuilderCustomizer() {
        return builder -> builder
            .withCacheConfiguration(CACHE_PRODUCT_DETAIL,
                defaultCacheConfig().entryTtl(Duration.ofMinutes(10)))
            .withCacheConfiguration(CACHE_PRODUCT_SEARCH,
                defaultCacheConfig().entryTtl(Duration.ofMinutes(2)))
            .withCacheConfiguration(CACHE_PRODUCT_CATEGORIES,
                defaultCacheConfig().entryTtl(Duration.ofHours(1)));
    }

    private RedisCacheConfiguration defaultCacheConfig() {
        return RedisCacheConfiguration.defaultCacheConfig()
            .serializeValuesWith(
                RedisSerializationContext.SerializationPair.fromSerializer(
                    new GenericJackson2JsonRedisSerializer()
                )
            );
    }
}
