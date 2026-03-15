package com.ilbuy.auth.api;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.ilbuy.auth.dto.LoginRequest;
import com.ilbuy.auth.dto.LoginResponse;
import com.ilbuy.auth.service.AuthService;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.csrf;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

/**
 * AuthController 接口测试（MockMvc）
 */
@WebMvcTest(AuthController.class)
@DisplayName("AuthController 接口测试")
class AuthControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    @MockBean
    private AuthService authService;

    @Test
    @DisplayName("POST /auth/login - 正常登录返回 200 及 Token")
    void login_shouldReturn200WithTokens() throws Exception {
        LoginResponse mockResponse = LoginResponse.builder()
            .accessToken("eyJhbGciOiJIUzI1NiJ9.test.token")
            .refreshToken("refresh_token_here")
            .tokenType("Bearer")
            .expiresIn(7200)
            .userId("10001")
            .userType("CONSUMER")
            .roles("ROLE_USER")
            .build();

        when(authService.login(any(LoginRequest.class))).thenReturn(mockResponse);

        LoginRequest request = new LoginRequest();
        request.setLoginId("consumer@test.com");
        request.setPassword("Test@123456");

        mockMvc.perform(post("/auth/login")
                .with(csrf())
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(request)))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.code").value(200))
            .andExpect(jsonPath("$.data.accessToken").isNotEmpty())
            .andExpect(jsonPath("$.data.tokenType").value("Bearer"))
            .andExpect(jsonPath("$.data.userType").value("CONSUMER"));
    }

    @Test
    @DisplayName("POST /auth/login - 请求参数为空返回 400")
    void login_emptyBody_shouldReturn400() throws Exception {
        LoginRequest request = new LoginRequest();
        // loginId 和 password 均为空

        mockMvc.perform(post("/auth/login")
                .with(csrf())
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(request)))
            .andExpect(status().isBadRequest());
    }
}
