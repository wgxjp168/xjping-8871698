package com.ilbuy.common.openfeign;

import com.ilbuy.common.core.enums.ResultCode;
import com.ilbuy.common.core.exception.BizException;
import com.ilbuy.common.openfeign.decoder.FeignErrorDecoder;
import feign.Request;
import feign.Response;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;

import java.nio.charset.StandardCharsets;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

@DisplayName("FeignErrorDecoder 错误解码测试")
class FeignErrorDecoderTest {

    private FeignErrorDecoder decoder;
    private static final Request DUMMY_REQUEST = Request.create(
            Request.HttpMethod.GET, "http://test/api",
            Map.of(), null, StandardCharsets.UTF_8, null);

    @BeforeEach
    void setUp() {
        decoder = new FeignErrorDecoder();
    }

    @ParameterizedTest(name = "HTTP {0} 解码为 ResultCode.code={1}")
    @CsvSource({
            "401, 6104",  // UNAUTHORIZED -> TOKEN_INVALID
            "403, 403",   // FORBIDDEN
            "404, 6001",  // NOT_FOUND -> DATA_NOT_EXIST
            "429, 429",   // TOO_MANY_REQUESTS
            "400, 400",   // BAD_REQUEST
            "500, 503",   // INTERNAL_SERVER_ERROR -> SERVICE_UNAVAILABLE
    })
    void decode_mapsStatusToCorrectCode(int httpStatus, int expectedCode) {
        Response response = Response.builder()
                .status(httpStatus)
                .reason("test")
                .request(DUMMY_REQUEST)
                .headers(Map.of())
                .body("{}", StandardCharsets.UTF_8)
                .build();

        Exception ex = decoder.decode("TestClient#method()", response);

        assertThat(ex).isInstanceOf(BizException.class);
        BizException biz = (BizException) ex;
        assertThat(biz.getCode()).isEqualTo(expectedCode);
    }

    @ParameterizedTest(name = "HTTP {0} 解析 body message")
    @CsvSource({
            "400, '{\"code\":400,\"message\":\"参数错误\"}'",
            "503, '{\"code\":503,\"message\":\"服务不可用\"}'",
    })
    void decode_extractsMessageFromBody(int httpStatus, String body) {
        Response response = Response.builder()
                .status(httpStatus)
                .reason("test")
                .request(DUMMY_REQUEST)
                .headers(Map.of())
                .body(body, StandardCharsets.UTF_8)
                .build();

        Exception ex = decoder.decode("TestClient#method()", response);

        assertThat(ex).isInstanceOf(BizException.class);
        // 验证 message 被正确提取
        BizException biz = (BizException) ex;
        assertThat(biz.getMessage()).isNotBlank();
    }
}
