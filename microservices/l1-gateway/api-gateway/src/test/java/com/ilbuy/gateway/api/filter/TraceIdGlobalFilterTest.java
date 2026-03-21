package com.ilbuy.gateway.api.filter;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.http.HttpHeaders;
import org.springframework.mock.http.server.reactive.MockServerHttpRequest;
import org.springframework.mock.web.server.MockServerWebExchange;
import reactor.core.publisher.Mono;
import reactor.test.StepVerifier;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;

/**
 * TraceIdGlobalFilter 单元测试
 */
@DisplayName("TraceIdGlobalFilter 单元测试")
@ExtendWith(MockitoExtension.class)
class TraceIdGlobalFilterTest {

    private TraceIdGlobalFilter filter;

    @Mock
    private GatewayFilterChain chain;

    @BeforeEach
    void setUp() {
        filter = new TraceIdGlobalFilter();
        when(chain.filter(any())).thenReturn(Mono.empty());
    }

    @Nested
    @DisplayName("TraceID 生成")
    class TraceIdGeneration {

        @Test
        @DisplayName("无上游 TraceID → 自动生成 32 位无连字符 UUID")
        void noUpstreamTraceId_generatesNew() {
            MockServerHttpRequest request = MockServerHttpRequest.get("/api/test").build();
            MockServerWebExchange exchange = MockServerWebExchange.from(request);

            StepVerifier.create(filter.filter(exchange, chain))
                    .verifyComplete();

            // 响应头中应包含自动生成的 TraceID
            String traceId = exchange.getResponse().getHeaders()
                    .getFirst(TraceIdGlobalFilter.TRACE_ID_HEADER);
            assertThat(traceId)
                    .isNotNull()
                    .hasSize(32)                    // UUID 去连字符 = 32 位
                    .doesNotContain("-");
        }

        @Test
        @DisplayName("有上游 TraceID → 透传原 ID，不重新生成")
        void upstreamTraceId_propagated() {
            String upstreamTraceId = "abc123def456789012345678901234ab";
            MockServerHttpRequest request = MockServerHttpRequest.get("/api/test")
                    .header(TraceIdGlobalFilter.TRACE_ID_HEADER, upstreamTraceId)
                    .build();
            MockServerWebExchange exchange = MockServerWebExchange.from(request);

            StepVerifier.create(filter.filter(exchange, chain))
                    .verifyComplete();

            String traceId = exchange.getResponse().getHeaders()
                    .getFirst(TraceIdGlobalFilter.TRACE_ID_HEADER);
            assertThat(traceId).isEqualTo(upstreamTraceId);
        }

        @Test
        @DisplayName("空白 TraceID 请求头 → 当作无 TraceID，重新生成")
        void blankTraceId_generatesNew() {
            MockServerHttpRequest request = MockServerHttpRequest.get("/api/test")
                    .header(TraceIdGlobalFilter.TRACE_ID_HEADER, "   ")
                    .build();
            MockServerWebExchange exchange = MockServerWebExchange.from(request);

            StepVerifier.create(filter.filter(exchange, chain))
                    .verifyComplete();

            String traceId = exchange.getResponse().getHeaders()
                    .getFirst(TraceIdGlobalFilter.TRACE_ID_HEADER);
            assertThat(traceId).isNotNull().hasSize(32);
        }
    }

    @Nested
    @DisplayName("Order 优先级")
    class OrderTest {

        @Test
        @DisplayName("Order 应为 -200（最高优先级之一）")
        void orderIsNegative200() {
            assertThat(filter.getOrder()).isEqualTo(-200);
        }
    }

    @Nested
    @DisplayName("响应头写入")
    class ResponseHeaderTest {

        @Test
        @DisplayName("TraceID 写入响应头，方便前端排查")
        void traceId_writtenToResponseHeader() {
            MockServerHttpRequest request = MockServerHttpRequest.get("/api/test").build();
            MockServerWebExchange exchange = MockServerWebExchange.from(request);

            StepVerifier.create(filter.filter(exchange, chain))
                    .verifyComplete();

            assertThat(exchange.getResponse().getHeaders()
                    .containsKey(TraceIdGlobalFilter.TRACE_ID_HEADER)).isTrue();
        }
    }
}
