package com.ilbuy.gateway.ws.config;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import com.ilbuy.gateway.ws.push.MessagePushService;
import lombok.RequiredArgsConstructor;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.data.redis.connection.RedisConnectionFactory;
import org.springframework.data.redis.listener.PatternTopic;
import org.springframework.data.redis.listener.RedisMessageListenerContainer;
import org.springframework.data.redis.listener.adapter.MessageListenerAdapter;

/**
 * Redis Pub/Sub 配置（跨实例消息广播）
 *
 * <p>订阅策略：
 * <ul>
 *   <li>用户维度频道：{@code ilbuy:ws:push:*}（Pattern 订阅）</li>
 *   <li>全局广播频道：{@code ilbuy:ws:broadcast}（固定 Topic）</li>
 * </ul>
 * </p>
 *
 * <p>收到 Redis 消息时，路由到 {@link MessagePushService} 处理本地推送。</p>
 */
@Configuration
@RequiredArgsConstructor
public class RedisMessageConfig {

    private final MessagePushService messagePushService;

    @Bean
    public RedisMessageListenerContainer redisMessageListenerContainer(
            RedisConnectionFactory connectionFactory) {

        RedisMessageListenerContainer container = new RedisMessageListenerContainer();
        container.setConnectionFactory(connectionFactory);

        // 订阅用户维度消息（Pattern：ilbuy:ws:push:*）
        container.addMessageListener(
                userMessageAdapter(),
                new PatternTopic("ilbuy:ws:push:*")
        );

        // 订阅全局广播
        container.addMessageListener(
                broadcastMessageAdapter(),
                messagePushService.broadcastTopic()
        );

        return container;
    }

    /**
     * 用户消息监听适配器（从频道名提取 userId 并路由到本地推送）
     */
    @Bean
    public MessageListenerAdapter userMessageAdapter() {
        return new MessageListenerAdapter(new Object() {
            /**
             * @param message 消息体（JSON）
             * @param channel 频道名（ilbuy:ws:push:{userId}）
             */
            @SuppressWarnings("unused")
            public void handleMessage(String message, String channel) {
                // 从频道名解析 userId
                String prefix = "ilbuy:ws:push:";
                if (channel.startsWith(prefix)) {
                    String userId = channel.substring(prefix.length());
                    messagePushService.onRedisMessage(userId, message);
                }
            }
        }, "handleMessage");
    }

    /**
     * 全局广播监听适配器
     */
    @Bean
    public MessageListenerAdapter broadcastMessageAdapter() {
        return new MessageListenerAdapter(new Object() {
            @SuppressWarnings("unused")
            public void handleMessage(String message) {
                messagePushService.onBroadcastMessage(message);
            }
        }, "handleMessage");
    }

    @Bean
    public ObjectMapper objectMapper() {
        ObjectMapper om = new ObjectMapper();
        om.registerModule(new JavaTimeModule());
        om.disable(SerializationFeature.WRITE_DATES_AS_TIMESTAMPS);
        return om;
    }
}
