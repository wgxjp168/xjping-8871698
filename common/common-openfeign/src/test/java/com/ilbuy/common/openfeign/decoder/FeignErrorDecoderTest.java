package com.ilbuy.common.openfeign.decoder;

import com.ilbuy.common.core.exception.BizException;
import com.ilbuy.common.core.result.ResultCode;
import feign.Request;
import feign.Response;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;

import java.nio.charset.StandardCharsets;
import java.util.Collections;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * FeignErrorDecoder 单元测试
 *
 * @author ILbuy Team
 */
@DisplayName("FeignErrorDecoder 测试")
class FeignErrorDecoderTest {

    private FeignErrorDecoder decoder;
    private static final String METHOD_KEY = "UserService#getUser(Long)";

    @BeforeEach
    void setUp() {
        decoder = new FeignErrorDecoder();
    }

    private Response buildResponse(int status, String body) {
        Request request = Request.create(
                Request.HttpMethod.GET,
                "http://user-svc/api/v1/users/1",
                Collections.emptyMap(),
                null,
                StandardCharsets.UTF_8,
                null
        );
        return Response.builder()
                .status(status)
                .request(request)
                .headers(Collections.emptyMap())
                .body(body != null ? body.getBytes(StandardCharsets.UTF_8) : null)
                .build();
    }

    // ================================================================
    //  标准 HTTP 状态码映射
    // ================================================================

    @Nested
    @DisplayName("HTTP 状态码映射")
    class StatusCodeMappingTests {

        @Test
        @DisplayName("400 Bad Request → ResultCode.BAD_REQUEST")
        void status400_badRequest() {
            Response response = buildResponse(400, null);
            Exception ex = decoder.decode(METHOD_KEY, response);

            assertThat(ex).isInstanceOf(BizException.class);
            assertThat(((BizException) ex).getCode()).isEqualTo(ResultCode.BAD_REQUEST.getCode());
        }

        @Test
        @DisplayName("401 Unauthorized → ResultCode.UNAUTHORIZED")
        void status401_unauthorized() {
            Response response = buildResponse(401, null);
            Exception ex = decoder.decode(METHOD_KEY, response);

            assertThat(ex).isInstanceOf(BizException.class);
            assertThat(((BizException) ex).getCode()).isEqualTo(ResultCode.UNAUTHORIZED.getCode());
        }

        @Test
        @DisplayName("403 Forbidden → ResultCode.FORBIDDEN")
        void status403_forbidden() {
            Response response = buildResponse(403, null);
            Exception ex = decoder.decode(METHOD_KEY, response);

            assertThat(ex).isInstanceOf(BizException.class);
            assertThat(((BizException) ex).getCode()).isEqualTo(ResultCode.FORBIDDEN.getCode());
        }

        @Test
        @DisplayName("404 Not Found → ResultCode.NOT_FOUND")
        void status404_notFound() {
            Response response = buildResponse(404, null);
            Exception ex = decoder.decode(METHOD_KEY, response);

            assertThat(ex).isInstanceOf(BizException.class);
            assertThat(((BizException) ex).getCode()).isEqualTo(ResultCode.NOT_FOUND.getCode());
        }

        @Test
        @DisplayName("429 Too Many Requests → ResultCode.TOO_MANY_REQUESTS")
        void status429_tooManyRequests() {
            Response response = buildResponse(429, null);
            Exception ex = decoder.decode(METHOD_KEY, response);

            assertThat(ex).isInstanceOf(BizException.class);
            assertThat(((BizException) ex).getCode()).isEqualTo(ResultCode.TOO_MANY_REQUESTS.getCode());
        }

        @Test
        @DisplayName("503 Service Unavailable → ResultCode.SERVICE_UNAVAILABLE")
        void status503_serviceUnavailable() {
            Response response = buildResponse(503, null);
            Exception ex = decoder.decode(METHOD_KEY, response);

            assertThat(ex).isInstanceOf(BizException.class);
            assertThat(((BizException) ex).getCode()).isEqualTo(ResultCode.SERVICE_UNAVAILABLE.getCode());
        }

        @Test
        @DisplayName("500 Internal Server Error → ResultCode.INTERNAL_ERROR")
        void status500_internalError() {
            Response response = buildResponse(500, null);
            Exception ex = decoder.decode(METHOD_KEY, response);

            assertThat(ex).isInstanceOf(BizException.class);
            assertThat(((BizException) ex).getCode()).isEqualTo(ResultCode.INTERNAL_ERROR.getCode());
        }

        @Test
        @DisplayName("502 Bad Gateway（其他5xx）→ ResultCode.INTERNAL_ERROR")
        void status502_alsoInternalError() {
            Response response = buildResponse(502, null);
            Exception ex = decoder.decode(METHOD_KEY, response);

            assertThat(ex).isInstanceOf(BizException.class);
            assertThat(((BizException) ex).getCode()).isEqualTo(ResultCode.INTERNAL_ERROR.getCode());
        }
    }

    // ================================================================
    //  响应体解析
    // ================================================================

    @Nested
    @DisplayName("响应体解析")
    class ResponseBodyParsingTests {

        @Test
        @DisplayName("标准 Result JSON 体被正确解析（自定义 code + message）")
        void standardResultBody_parsed() {
            String body = "{\"code\":2001,\"message\":\"用户不存在\",\"data\":null}";
            Response response = buildResponse(400, body);
            Exception ex = decoder.decode(METHOD_KEY, response);

            assertThat(ex).isInstanceOf(BizException.class);
            BizException biz = (BizException) ex;
            assertThat(biz.getCode()).isEqualTo(2001);
            assertThat(biz.getMessage()).isEqualTo("用户不存在");
        }

        @Test
        @DisplayName("空响应体时按状态码降级处理")
        void emptyBody_fallsBackToStatusCode() {
            Response response = buildResponse(404, null);
            Exception ex = decoder.decode(METHOD_KEY, response);

            assertThat(ex).isInstanceOf(BizException.class);
            assertThat(((BizException) ex).getCode()).isEqualTo(ResultCode.NOT_FOUND.getCode());
        }

        @Test
        @DisplayName("非 Result 格式 JSON 体时按状态码降级处理")
        void invalidJsonBody_fallsBackToStatusCode() {
            Response response = buildResponse(500, "Internal Server Error");
            Exception ex = decoder.decode(METHOD_KEY, response);

            assertThat(ex).isInstanceOf(BizException.class);
            assertThat(((BizException) ex).getCode()).isEqualTo(ResultCode.INTERNAL_ERROR.getCode());
        }

        @Test
        @DisplayName("响应体 code=200 时按状态码降级处理（下游误用）")
        void resultBodyWithCode200_fallsBackToStatusCode() {
            String body = "{\"code\":200,\"message\":\"ok\",\"data\":null}";
            Response response = buildResponse(400, body);
            Exception ex = decoder.decode(METHOD_KEY, response);

            // code=200 不会被当做错误，退回状态码映射
            assertThat(ex).isInstanceOf(BizException.class);
            assertThat(((BizException) ex).getCode()).isEqualTo(ResultCode.BAD_REQUEST.getCode());
        }
    }
}
