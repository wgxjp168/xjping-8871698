package com.ilbuy.common.security.token;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;

import static org.assertj.core.api.Assertions.assertThat;

@DisplayName("ClientType 多端枚举测试")
class ClientTypeTest {

    @ParameterizedTest(name = "code={0} → {1}")
    @CsvSource({
            "mobile, MOBILE",
            "web,    WEB",
            "admin,  ADMIN",
            "open,   OPEN",
            "device, DEVICE",
            "MOBILE, MOBILE",   // 大写兼容
            "WEB,    WEB",
    })
    @DisplayName("of() 根据 code 查找枚举（不区分大小写）")
    void of_found(String code, String expected) {
        assertThat(ClientType.of(code)).isEqualTo(ClientType.valueOf(expected));
    }

    @Test
    @DisplayName("of() 未知 code 返回 WEB（默认端）")
    void of_unknown_returnsWeb() {
        assertThat(ClientType.of("unknown")).isEqualTo(ClientType.WEB);
        assertThat(ClientType.of(null)).isEqualTo(ClientType.WEB);
    }

    @Test
    @DisplayName("MOBILE 有效期 > WEB 有效期 > ADMIN 有效期")
    void expiry_order() {
        assertThat(ClientType.MOBILE.getAccessTokenExpire())
                .isGreaterThan(ClientType.WEB.getAccessTokenExpire());
        assertThat(ClientType.WEB.getAccessTokenExpire())
                .isGreaterThan(ClientType.ADMIN.getAccessTokenExpire());
    }

    @Test
    @DisplayName("所有端的 refreshTokenExpire >= accessTokenExpire")
    void refreshExpiry_gtAccessExpiry() {
        for (ClientType ct : ClientType.values()) {
            assertThat(ct.getRefreshTokenExpire())
                    .as("ClientType=%s", ct)
                    .isGreaterThanOrEqualTo(ct.getAccessTokenExpire());
        }
    }

    @Test
    @DisplayName("DEVICE 的 Access Token 有效期最长")
    void device_longestAccess() {
        for (ClientType ct : ClientType.values()) {
            if (ct != ClientType.DEVICE) {
                assertThat(ClientType.DEVICE.getAccessTokenExpire())
                        .isGreaterThanOrEqualTo(ct.getAccessTokenExpire());
            }
        }
    }

    @Test
    @DisplayName("getCode() 不含大写字母（约定小写）")
    void code_isLowercase() {
        for (ClientType ct : ClientType.values()) {
            assertThat(ct.getCode()).isEqualTo(ct.getCode().toLowerCase());
        }
    }
}
