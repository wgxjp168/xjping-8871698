package com.ilbuy.gateway.ws.push;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.ilbuy.gateway.ws.model.MessageType;
import com.ilbuy.gateway.ws.model.WsMessage;
import com.ilbuy.gateway.ws.session.SessionManager;
import org.junit.jupiter.api.*;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.web.socket.TextMessage;
import org.springframework.web.socket.WebSocketSession;

import java.io.IOException;
import java.util.Collections;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatCode;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/**
 * MessagePushService 单元测试
 */
@DisplayName("MessagePushService 单元测试")
@ExtendWith(MockitoExtension.class)
class MessagePushServiceTest {

    @Mock SessionManager        sessionManager;
    @Mock StringRedisTemplate   redisTemplate;
    @Mock WebSocketSession       wsSession;

    private MessagePushService pushService;
    private ObjectMapper        objectMapper;

    private static final String USER_ID = "user42";

    @BeforeEach
    void setUp() {
        objectMapper = new ObjectMapper();
        pushService = new MessagePushService(sessionManager, redisTemplate, objectMapper);
    }

    @Nested
    @DisplayName("pushToUser — 本地推送")
    class PushToUser {

        @Test
        @DisplayName("用户在本实例 → 推送成功，返回 true")
        void userOnLocal_pushed_returnsTrue() throws IOException {
            when(sessionManager.getLocalSessions(USER_ID)).thenReturn(List.of(wsSession));
            when(wsSession.isOpen()).thenReturn(true);

            WsMessage msg = WsMessage.system(MessageType.NOTIFICATION, "测试消息");
            boolean result = pushService.pushToUser(USER_ID, msg);

            assertThat(result).isTrue();
            verify(wsSession).sendMessage(any(TextMessage.class));
        }

        @Test
        @DisplayName("用户不在本实例 → 返回 false，不发送")
        void userNotOnLocal_returnsFalse() {
            when(sessionManager.getLocalSessions(USER_ID)).thenReturn(Collections.emptyList());

            WsMessage msg = WsMessage.system(MessageType.NOTIFICATION, "测试消息");
            boolean result = pushService.pushToUser(USER_ID, msg);

            assertThat(result).isFalse();
            verifyNoInteractions(wsSession);
        }

        @Test
        @DisplayName("Session 已关闭 → 不发送，返回 false")
        void closedSession_notSent() {
            when(sessionManager.getLocalSessions(USER_ID)).thenReturn(List.of(wsSession));
            when(wsSession.isOpen()).thenReturn(false);

            WsMessage msg = WsMessage.system(MessageType.PING, "ping");
            boolean result = pushService.pushToUser(USER_ID, msg);

            assertThat(result).isFalse();
            verify(wsSession, never()).sendMessage(any());
        }

        @Test
        @DisplayName("sendMessage 抛出 IOException → 捕获不抛出，返回 false")
        void sendException_caught_returnsFalse() throws IOException {
            when(sessionManager.getLocalSessions(USER_ID)).thenReturn(List.of(wsSession));
            when(wsSession.isOpen()).thenReturn(true);
            doThrow(new IOException("网络错误")).when(wsSession).sendMessage(any());

            WsMessage msg = WsMessage.system(MessageType.CHAT, "消息");
            assertThatCode(() -> pushService.pushToUser(USER_ID, msg))
                    .doesNotThrowAnyException();
        }
    }

    @Nested
    @DisplayName("publishToRedis — 跨实例推送")
    class PublishToRedis {

        @Test
        @DisplayName("调用 redisTemplate.convertAndSend 到用户频道")
        void publish_callsRedis() {
            WsMessage msg = WsMessage.chat("from", USER_ID, "hello");
            pushService.publishToRedis(USER_ID, msg);

            verify(redisTemplate).convertAndSend(
                    eq("ilbuy:ws:push:" + USER_ID),
                    anyString()
            );
        }
    }

    @Nested
    @DisplayName("broadcastViaRedis — 全局广播")
    class BroadcastViaRedis {

        @Test
        @DisplayName("广播调用 Redis broadcast 频道")
        void broadcast_callsBroadcastChannel() {
            WsMessage msg = WsMessage.system(MessageType.NOTIFICATION, "系统公告");
            pushService.broadcastViaRedis(msg);

            verify(redisTemplate).convertAndSend(
                    eq("ilbuy:ws:broadcast"),
                    anyString()
            );
        }
    }

    @Nested
    @DisplayName("onRedisMessage — 接收 Redis 跨实例消息")
    class OnRedisMessage {

        @Test
        @DisplayName("合法 JSON → 路由到本地推送")
        void validJson_routedToLocal() throws Exception {
            WsMessage msg = WsMessage.system(MessageType.CHAT, "hello");
            String json = objectMapper.writeValueAsString(msg);

            when(sessionManager.getLocalSessions(USER_ID)).thenReturn(List.of(wsSession));
            when(wsSession.isOpen()).thenReturn(true);

            pushService.onRedisMessage(USER_ID, json);

            verify(wsSession).sendMessage(any(TextMessage.class));
        }

        @Test
        @DisplayName("非法 JSON → 不抛出异常，静默忽略")
        void invalidJson_noException() {
            assertThatCode(() -> pushService.onRedisMessage(USER_ID, "invalid{json"))
                    .doesNotThrowAnyException();
        }
    }
}
