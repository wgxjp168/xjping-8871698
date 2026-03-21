package com.ilbuy.common.openfeign;

import com.ilbuy.common.core.constants.CommonConstants;
import com.ilbuy.common.openfeign.interceptor.FeignTokenRelayInterceptor;
import feign.RequestTemplate;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;

import java.util.Collection;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * FeignTokenRelayInterceptor 单元测试
 *
 * <p>覆盖场景：
 * <ol>
 *   <li>有 HTTP 上下文：从请求头透传 Authorization/TraceId/TenantId/UserId/Username</li>
 *   <li>空请求头：不向 Feign 模板写入该头（避免写入空值）</li>
 *   <li>无 HTTP 上下文 + SecurityContext 有 Token：从 SecurityContext 构建 Authorization</li>
 *   <li>无 HTTP 上下文 + SecurityContext 无 Token：跳过，不写入 Authorization</li>
 * </ol>
 * </p>
 */
@DisplayName("FeignTokenRelayInterceptor 单元测试")
@ExtendWith(MockitoExtension.class)
class FeignTokenRelayInterceptorTest {

    private FeignTokenRelayInterceptor interceptor;
    private RequestTemplate template;

    @BeforeEach
    void setUp() {
        interceptor = new FeignTokenRelayInterceptor();
        template    = new RequestTemplate();

        // 清空 RequestContextHolder 和 SecurityContext
        RequestContextHolder.resetRequestAttributes();
        SecurityContextHolder.clearContext();
    }

    // ═══════════════ HTTP 上下文场景 ═══════════════

    @Nested
    @DisplayName("有 HTTP 请求上下文")
    class WithHttpContext {

        private MockHttpServletRequest request;

        @BeforeEach
        void setUp() {
            request = new MockHttpServletRequest();
            RequestContextHolder.setRequestAttributes(new ServletRequestAttributes(request));
        }

        @Test
        @DisplayName("Authorization 头正常透传")
        void propagatesAuthorizationHeader() {
            request.addHeader(CommonConstants.HEADER_AUTHORIZATION, "Bearer token123");

            interceptor.apply(template);

            Collection<String> values = template.headers().get(CommonConstants.HEADER_AUTHORIZATION);
            assertThat(values).isNotEmpty().contains("Bearer token123");
        }

        @Test
        @DisplayName("TraceId 头正常透传")
        void propagatesTraceIdHeader() {
            request.addHeader(CommonConstants.HEADER_TRACE_ID, "trace-abc-123");

            interceptor.apply(template);

            Collection<String> values = template.headers().get(CommonConstants.HEADER_TRACE_ID);
            assertThat(values).isNotEmpty().contains("trace-abc-123");
        }

        @Test
        @DisplayName("TenantId / UserId / Username 同时透传")
        void propagatesMultipleHeaders() {
            request.addHeader(CommonConstants.HEADER_TENANT_ID, "tenant-001");
            request.addHeader(CommonConstants.HEADER_USER_ID,   "42");
            request.addHeader(CommonConstants.HEADER_USERNAME,  "zhangsan");

            interceptor.apply(template);

            assertThat(template.headers().get(CommonConstants.HEADER_TENANT_ID)).contains("tenant-001");
            assertThat(template.headers().get(CommonConstants.HEADER_USER_ID)).contains("42");
            assertThat(template.headers().get(CommonConstants.HEADER_USERNAME)).contains("zhangsan");
        }

        @Test
        @DisplayName("空请求头不写入 Feign 模板（避免空值污染）")
        void emptyHeader_notPropagated() {
            // 没有设置任何头
            interceptor.apply(template);

            assertThat(template.headers()).doesNotContainKey(CommonConstants.HEADER_AUTHORIZATION);
            assertThat(template.headers()).doesNotContainKey(CommonConstants.HEADER_TRACE_ID);
        }
    }

    // ═══════════════ 无 HTTP 上下文（异步/批处理场景） ═══════════════

    @Nested
    @DisplayName("无 HTTP 请求上下文（异步/批处理）")
    class WithoutHttpContext {

        @Test
        @DisplayName("SecurityContext 有 Bearer Token → 写入 Authorization 头")
        void securityContextToken_propagated() {
            // 模拟 SecurityContext 中存有 Token
            UsernamePasswordAuthenticationToken auth =
                    new UsernamePasswordAuthenticationToken("user", "jwt-token-xyz");
            SecurityContextHolder.getContext().setAuthentication(auth);

            interceptor.apply(template);

            Collection<String> values = template.headers().get(CommonConstants.HEADER_AUTHORIZATION);
            assertThat(values).isNotEmpty();
            assertThat(values.iterator().next())
                    .startsWith(CommonConstants.TOKEN_PREFIX)
                    .contains("jwt-token-xyz");
        }

        @Test
        @DisplayName("SecurityContext 无 Token → 不写入 Authorization 头")
        void noSecurityContext_notPropagated() {
            // SecurityContext 已清空（setUp 中已做）
            interceptor.apply(template);

            assertThat(template.headers()).doesNotContainKey(CommonConstants.HEADER_AUTHORIZATION);
        }

        @Test
        @DisplayName("SecurityContext credentials 不是 String → 不写入 Authorization 头")
        void nonStringCredentials_notPropagated() {
            // credentials 为非 String 类型
            UsernamePasswordAuthenticationToken auth =
                    new UsernamePasswordAuthenticationToken("user", 12345);
            SecurityContextHolder.getContext().setAuthentication(auth);

            interceptor.apply(template);

            assertThat(template.headers()).doesNotContainKey(CommonConstants.HEADER_AUTHORIZATION);
        }
    }
}
