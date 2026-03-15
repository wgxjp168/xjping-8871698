package com.ilbuy.websocket.handler;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.ilbuy.websocket.dto.ChatMessage;
import com.ilbuy.websocket.service.SessionManagerService;
import com.ilbuy.websocket.service.L2ConversationService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.web.socket.CloseStatus;
import org.springframework.web.socket.TextMessage;
import org.springframework.web.socket.WebSocketSession;

import java.util.HashMap;
import java.util.Map;

import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/**
 * ChatWebSocketHandler 单元测试
 */
@ExtendWith(MockitoExtension.class)
@DisplayName("ChatWebSocketHandler 单元测试")
class ChatWebSocketHandlerTest {

    @Mock
    private SessionManagerService sessionManager;

    @Mock
    private L2ConversationService conversationService;

    @Mock
    private WebSocketSession wsSession;

    @InjectMocks
    private ChatWebSocketHandler handler;

    private ObjectMapper objectMapper;
    private Map<String, Object> attrs;

    @BeforeEach
    void setUp() {
        objectMapper = new ObjectMapper();
        handler = new ChatWebSocketHandler(sessionManager, conversationService, objectMapper);

        attrs = new HashMap<>();
        attrs.put("userId", "10001");
        attrs.put("userType", "CONSUMER");
        attrs.put("clientIp", "127.0.0.1");

        when(wsSession.getId()).thenReturn("ws-session-001");
        when(wsSession.getAttributes()).thenReturn(attrs);
        when(wsSession.isOpen()).thenReturn(true);
    }

    @Test
    @DisplayName("连接建立后注册会话")
    void afterConnectionEstablished_shouldRegisterSession() throws Exception {
        handler.afterConnectionEstablished(wsSession);
        verify(sessionManager).register(wsSession, "10001", "CONSUMER", "127.0.0.1");
    }

    @Test
    @DisplayName("PING 消息返回 PONG")
    void handlePing_shouldSendPong() throws Exception {
        ChatMessage ping = ChatMessage.builder().type("PING").build();
        handler.handleTextMessage(wsSession, new TextMessage(objectMapper.writeValueAsString(ping)));

        verify(wsSession).sendMessage(argThat(msg -> {
            String payload = ((TextMessage) msg).getPayload();
            return payload.contains("PONG");
        }));
    }

    @Test
    @DisplayName("JSON 格式错误返回 ERROR 响应")
    void handleInvalidJson_shouldSendError() throws Exception {
        handler.handleTextMessage(wsSession, new TextMessage("invalid json}}}"));

        verify(wsSession).sendMessage(argThat(msg -> {
            String payload = ((TextMessage) msg).getPayload();
            return payload.contains("ERROR");
        }));
    }

    @Test
    @DisplayName("连接关闭后移除会话")
    void afterConnectionClosed_shouldRemoveSession() throws Exception {
        handler.afterConnectionClosed(wsSession, CloseStatus.NORMAL);
        verify(sessionManager).remove("ws-session-001");
    }

    @Test
    @DisplayName("TEXT 消息触发 L2 对话服务")
    void handleTextMessage_shouldCallL2Service() throws Exception {
        ChatMessage textMsg = ChatMessage.builder()
            .type("TEXT")
            .sessionId("session-abc")
            .content("帮我推荐一款笔记本电脑")
            .build();

        handler.handleTextMessage(wsSession, new TextMessage(objectMapper.writeValueAsString(textMsg)));

        verify(conversationService).processText(eq("10001"), eq("session-abc"),
            eq("帮我推荐一款笔记本电脑"), any(), any(), any());
    }
}
