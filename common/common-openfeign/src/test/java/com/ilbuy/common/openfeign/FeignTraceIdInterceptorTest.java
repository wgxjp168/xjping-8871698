package com.ilbuy.common.openfeign;

import com.ilbuy.common.core.constants.CommonConstants;
import com.ilbuy.common.openfeign.interceptor.FeignTraceIdInterceptor;
import feign.Request;
import feign.RequestTemplate;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.slf4j.MDC;

import java.nio.charset.StandardCharsets;
import java.util.Collection;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

@DisplayName("FeignTraceIdInterceptor 单元测试")
class FeignTraceIdInterceptorTest {

    private FeignTraceIdInterceptor interceptor;
    private RequestTemplate template;

    @BeforeEach
    void setUp() {
        interceptor = new FeignTraceIdInterceptor();
        template    = new RequestTemplate();
        template.method(Request.HttpMethod.GET);
        template.target("http://user-service");
        template.append("/api/user/profile");

        MDC.clear();
    }

    @Test
    @DisplayName("无上下文时生成新 traceId 并写入请求头")
    void apply_noContext_generatesTraceId() {
        interceptor.apply(template);

        Collection<String> traceIds = template.headers().get(CommonConstants.HEADER_TRACE_ID);
        assertThat(traceIds).isNotNull().isNotEmpty();
        String traceId = traceIds.iterator().next();
        assertThat(traceId).isNotBlank().hasSize(32); // UUID without dashes
    }

    @Test
    @DisplayName("MDC 中存在 traceId 时透传")
    void apply_mdcTraceId_propagated() {
        MDC.put(FeignTraceIdInterceptor.MDC_TRACE_ID_KEY, "mdc-trace-abc123");

        interceptor.apply(template);

        Collection<String> traceIds = template.headers().get(CommonConstants.HEADER_TRACE_ID);
        assertThat(traceIds).isNotNull().contains("mdc-trace-abc123");
    }

    @Test
    @DisplayName("每次调用无上下文时生成不同 traceId")
    void apply_multipleCallsWithoutContext_differentTraceIds() {
        interceptor.apply(template);
        String first = template.headers().get(CommonConstants.HEADER_TRACE_ID).iterator().next();

        RequestTemplate template2 = new RequestTemplate();
        template2.method(Request.HttpMethod.GET);
        template2.target("http://order-service");
        interceptor.apply(template2);
        String second = template2.headers().get(CommonConstants.HEADER_TRACE_ID).iterator().next();

        assertThat(first).isNotEqualTo(second);
    }

    @Test
    @DisplayName("generateTraceId 生成 32 位无连字符字符串")
    void generateTraceId_32CharsNoDash() {
        String traceId = FeignTraceIdInterceptor.generateTraceId();
        assertThat(traceId).hasSize(32).doesNotContain("-");
    }

    @Test
    @DisplayName("apply 同步 MDC traceId")
    void apply_syncsMdcTraceId() {
        interceptor.apply(template);
        // MDC 应当被设置
        assertThat(MDC.get(FeignTraceIdInterceptor.MDC_TRACE_ID_KEY)).isNotBlank();
    }
}
