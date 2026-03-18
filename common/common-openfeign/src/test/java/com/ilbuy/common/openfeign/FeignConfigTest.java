package com.ilbuy.common.openfeign;

import com.ilbuy.common.openfeign.config.FeignConfig;
import com.ilbuy.common.openfeign.decoder.FeignErrorDecoder;
import com.ilbuy.common.openfeign.interceptor.FeignTokenRelayInterceptor;
import feign.Logger;
import feign.Request;
import feign.Retryer;
import feign.codec.ErrorDecoder;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.util.concurrent.TimeUnit;

import static org.assertj.core.api.Assertions.assertThat;

@DisplayName("FeignConfig 单元测试")
class FeignConfigTest {

    private FeignConfig feignConfig;

    @BeforeEach
    void setUp() {
        feignConfig = new FeignConfig();
    }

    @Test
    @DisplayName("requestOptions 超时配置正确")
    void requestOptions_timeoutCorrect() {
        Request.Options options = feignConfig.requestOptions();
        assertThat(options.connectTimeoutMillis())
                .isEqualTo((int) TimeUnit.SECONDS.toMillis(3));
        assertThat(options.readTimeoutMillis())
                .isEqualTo((int) TimeUnit.SECONDS.toMillis(10));
        assertThat(options.isFollowRedirects()).isTrue();
    }

    @Test
    @DisplayName("retryer 配置不为 null")
    void retryer_notNull() {
        Retryer retryer = feignConfig.retryer();
        assertThat(retryer).isNotNull();
        assertThat(retryer).isInstanceOf(Retryer.Default.class);
    }

    @Test
    @DisplayName("FeignTokenRelayInterceptor Bean 正常创建")
    void tokenInterceptor_created() {
        FeignTokenRelayInterceptor interceptor = feignConfig.feignTokenRelayInterceptor();
        assertThat(interceptor).isNotNull();
    }

    @Test
    @DisplayName("ErrorDecoder 是 FeignErrorDecoder 类型")
    void errorDecoder_isFeignErrorDecoder() {
        ErrorDecoder decoder = feignConfig.errorDecoder();
        assertThat(decoder).isInstanceOf(FeignErrorDecoder.class);
    }

    @Test
    @DisplayName("日志级别为 FULL")
    void loggerLevel_isFull() {
        Logger.Level level = feignConfig.feignLoggerLevel();
        assertThat(level).isEqualTo(Logger.Level.FULL);
    }
}
