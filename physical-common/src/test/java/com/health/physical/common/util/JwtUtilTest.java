package com.health.physical.common.util;

import io.jsonwebtoken.Claims;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.util.HashMap;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

/**
 * JWT工具类单元测试
 */
@DisplayName("JwtUtil - JWT令牌工具测试")
class JwtUtilTest {

    private static final String SECRET = "physical_health_system_jwt_secret_key_2024_secure_enough";
    private static final String SUBJECT = "testDoctor";

    @Test
    @DisplayName("生成Token并解析Subject成功")
    void generateAndParseToken_success() {
        Map<String, Object> claims = new HashMap<>();
        claims.put("docId", "DOC001");
        claims.put("name", "张三");
        claims.put("dept", "LAB");

        String token = JwtUtil.generateToken(SUBJECT, claims, 3600, SECRET);
        assertNotNull(token, "生成的Token不应为null");

        Claims parsed = JwtUtil.parseToken(token, SECRET);
        assertNotNull(parsed, "解析结果不应为null");
        assertEquals(SUBJECT, parsed.getSubject(), "Subject应匹配");
        assertEquals("DOC001", parsed.get("docId"), "docId应匹配");
        assertEquals("张三", parsed.get("name"), "name应匹配");
    }

    @Test
    @DisplayName("Token已过期时解析返回null")
    void parseToken_expired_returnsNull() throws InterruptedException {
        Map<String, Object> claims = new HashMap<>();
        // 生成1秒有效期的Token
        String token = JwtUtil.generateToken(SUBJECT, claims, 1, SECRET);
        // 等待过期
        Thread.sleep(1500);
        Claims parsed = JwtUtil.parseToken(token, SECRET);
        assertNull(parsed, "过期Token解析应返回null");
    }

    @Test
    @DisplayName("签名不匹配时解析返回null")
    void parseToken_wrongSecret_returnsNull() {
        Map<String, Object> claims = new HashMap<>();
        String token = JwtUtil.generateToken(SUBJECT, claims, 3600, SECRET);
        Claims parsed = JwtUtil.parseToken(token, "wrong_secret_key_that_is_also_32_bytes_long_xx");
        assertNull(parsed, "错误密钥解析应返回null");
    }

    @Test
    @DisplayName("Token格式错误时解析返回null")
    void parseToken_malformed_returnsNull() {
        Claims parsed = JwtUtil.parseToken("not.a.valid.token", SECRET);
        assertNull(parsed, "格式错误Token解析应返回null");
    }

    @Test
    @DisplayName("isValid校验有效Token")
    void isValid_validToken_returnsTrue() {
        Map<String, Object> claims = new HashMap<>();
        String token = JwtUtil.generateToken(SUBJECT, claims, 3600, SECRET);
        assertTrue(JwtUtil.isValid(token), "有效Token isValid应返回true");
    }

    @Test
    @DisplayName("getSubject正确提取Subject")
    void getSubject_validToken_returnsSubject() {
        Map<String, Object> claims = new HashMap<>();
        String token = JwtUtil.generateToken(SUBJECT, claims, 3600, SECRET);
        assertEquals(SUBJECT, JwtUtil.getSubject(token));
    }
}
