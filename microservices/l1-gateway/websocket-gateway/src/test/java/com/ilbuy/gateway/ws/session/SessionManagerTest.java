package com.ilbuy.gateway.ws.session;

import org.junit.jupiter.api.*;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.redis.core.HashOperations;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.web.socket.WebSocketSession;

import java.util.List;
import java.util.Map;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/**
 * SessionManager 单元测试
 */
@DisplayName("SessionManager 单元测试")
@ExtendWith(MockitoExtension.class)
class SessionManagerTest {

    @Mock StringRedisTemplate              redisTemplate;
    @Mock HashOperations<String, Object, Object> hashOps;
    @Mock WebSocketSession                 session;

    private SessionManager sessionManager;
    private static final String USER_ID   = "user123";
    private static final String SESSION_ID = "sess-abc";

    @BeforeEach
    void setUp() {
        when(redisTemplate.opsForHash()).thenReturn(hashOps);
        sessionManager = new SessionManager(redisTemplate);
    }

    @Nested
    @DisplayName("会话注册")
    class Register {

        @BeforeEach
        void setupSession() {
            when(session.getId()).thenReturn(SESSION_ID);
            when(session.isOpen()).thenReturn(true);
        }

        @Test
        @DisplayName("注册后本地可查找到会话")
        void register_localSessionFound() {
            sessionManager.register(session, USER_ID);

            List<WebSocketSession> sessions = sessionManager.getLocalSessions(USER_ID);
            assertThat(sessions).hasSize(1).contains(session);
        }

        @Test
        @DisplayName("注册后 Redis 调用 hset")
        void register_redisUpdated() {
            sessionManager.register(session, USER_ID);

            verify(hashOps).put(contains(USER_ID), eq(SESSION_ID), anyString());
        }

        @Test
        @DisplayName("注册后 isOnline 返回 true")
        void register_userIsOnline() {
            sessionManager.register(session, USER_ID);

            when(hashOps.size(anyString())).thenReturn(1L);
            assertThat(sessionManager.isOnline(USER_ID)).isTrue();
        }
    }

    @Nested
    @DisplayName("会话注销")
    class Unregister {

        @BeforeEach
        void registerFirst() {
            when(session.getId()).thenReturn(SESSION_ID);
            when(session.isOpen()).thenReturn(true);
            sessionManager.register(session, USER_ID);
        }

        @Test
        @DisplayName("注销后本地会话不可查")
        void unregister_localSessionRemoved() {
            sessionManager.unregister(session, USER_ID);

            List<WebSocketSession> sessions = sessionManager.getLocalSessions(USER_ID);
            assertThat(sessions).isEmpty();
        }

        @Test
        @DisplayName("注销后 Redis 调用 hdel")
        void unregister_redisUpdated() {
            sessionManager.unregister(session, USER_ID);

            verify(hashOps).delete(contains(USER_ID), eq(SESSION_ID));
        }
    }

    @Nested
    @DisplayName("会话查询")
    class Query {

        @Test
        @DisplayName("按 sessionId 精确查询：不存在返回 Optional.empty")
        void getLocalSession_notFound_returnsEmpty() {
            Optional<WebSocketSession> result = sessionManager.getLocalSession("nonexistent");
            assertThat(result).isEmpty();
        }

        @Test
        @DisplayName("按 sessionId 精确查询：已注册且 open 返回 Optional.of")
        void getLocalSession_found_returnsSession() {
            when(session.getId()).thenReturn(SESSION_ID);
            when(session.isOpen()).thenReturn(true);
            sessionManager.register(session, USER_ID);

            Optional<WebSocketSession> result = sessionManager.getLocalSession(SESSION_ID);
            assertThat(result).contains(session);
        }

        @Test
        @DisplayName("Session 已关闭时不返回")
        void getLocalSession_closed_returnsEmpty() {
            when(session.getId()).thenReturn(SESSION_ID);
            when(session.isOpen()).thenReturn(true);
            sessionManager.register(session, USER_ID);

            // 模拟 session 关闭
            when(session.isOpen()).thenReturn(false);

            Optional<WebSocketSession> result = sessionManager.getLocalSession(SESSION_ID);
            assertThat(result).isEmpty();
        }

        @Test
        @DisplayName("localConnectionCount 返回当前在线数")
        void localConnectionCount_correct() {
            assertThat(sessionManager.localConnectionCount()).isZero();

            when(session.getId()).thenReturn(SESSION_ID);
            when(session.isOpen()).thenReturn(true);
            sessionManager.register(session, USER_ID);

            assertThat(sessionManager.localConnectionCount()).isEqualTo(1);
        }
    }

    @Nested
    @DisplayName("全局会话查询（Redis）")
    class GlobalQuery {

        @Test
        @DisplayName("getGlobalSessions 调用 Redis entries")
        void getGlobalSessions_callsRedis() {
            when(hashOps.entries(anyString())).thenReturn(Map.of("sess1", "inst1:123"));

            Map<Object, Object> result = sessionManager.getGlobalSessions(USER_ID);

            assertThat(result).containsKey("sess1");
            verify(hashOps).entries(contains(USER_ID));
        }
    }
}
