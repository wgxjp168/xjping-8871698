package com.health.physical.auth.service;

import cn.hutool.crypto.digest.BCrypt;
import com.alibaba.fastjson2.JSON;
import com.health.physical.auth.dto.LoginRequest;
import com.health.physical.auth.dto.LoginResponse;
import com.health.physical.auth.dto.PermCheckRequest;
import com.health.physical.auth.entity.DocPermission;
import com.health.physical.auth.entity.Doctor;
import com.health.physical.auth.mapper.DocPermissionMapper;
import com.health.physical.auth.mapper.DoctorMapper;
import com.health.physical.auth.service.impl.AuthServiceImpl;
import com.health.physical.common.exception.BusinessException;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.redisson.api.RBucket;
import org.redisson.api.RedissonClient;
import org.springframework.test.util.ReflectionTestUtils;

import java.util.Arrays;
import java.util.Collections;
import java.util.List;
import java.util.concurrent.TimeUnit;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/**
 * 权限服务单元测试（Mockito，无需启动Spring容器）
 */
@ExtendWith(MockitoExtension.class)
@DisplayName("AuthService - 医生权限服务测试")
class AuthServiceTest {

    @Mock private DoctorMapper doctorMapper;
    @Mock private DocPermissionMapper docPermissionMapper;
    @Mock private RedissonClient redissonClient;
    @Mock private RBucket<String> rBucket;

    @InjectMocks
    private AuthServiceImpl authService;

    private Doctor mockDoctor;
    private static final String RAW_PASSWORD = "Test@1234";
    private static final String HASHED_PASSWORD = BCrypt.hashpw(RAW_PASSWORD, BCrypt.gensalt());

    @BeforeEach
    void setUp() {
        ReflectionTestUtils.setField(authService, "jwtSecret",
                "physical_health_system_jwt_secret_key_2024_secure_enough");
        ReflectionTestUtils.setField(authService, "expireSeconds", 43200L);

        mockDoctor = new Doctor();
        mockDoctor.setId(1L);
        mockDoctor.setDocId("DOC001");
        mockDoctor.setUsername("zhangsan");
        mockDoctor.setPassword(HASHED_PASSWORD);
        mockDoctor.setName("张三");
        mockDoctor.setDept("LAB");
        mockDoctor.setDeptName("化验室");
        mockDoctor.setStatus(1);
    }

    @Test
    @DisplayName("登录成功 - 正确用户名密码返回Token")
    void login_validCredentials_returnsToken() {
        // given
        LoginRequest request = new LoginRequest();
        request.setUsername("zhangsan");
        request.setPassword(RAW_PASSWORD);
        request.setLoginSource("WEB");

        when(doctorMapper.selectByUsername("zhangsan")).thenReturn(mockDoctor);

        List<DocPermission> perms = buildPermissions("DOC001");
        when(docPermissionMapper.selectByDocId("DOC001")).thenReturn(perms);

        // 模拟 Redis RBucket
        when(redissonClient.getBucket(anyString())).thenReturn(rBucket);
        doNothing().when(rBucket).set(anyString(), anyLong(), any(TimeUnit.class));

        // when
        LoginResponse response = authService.login(request);

        // then
        assertNotNull(response.getToken(), "Token不应为null");
        assertEquals("DOC001", response.getDocId());
        assertEquals("张三", response.getName());
        assertEquals("LAB", response.getDept());
        assertFalse(response.getProjectCodes().isEmpty(), "项目权限列表不应为空");
        assertTrue(response.getPermissions().contains("BIOCHEM:INPUT"), "应包含生化录入权限");
    }

    @Test
    @DisplayName("登录失败 - 用户不存在")
    void login_userNotFound_throwsBusinessException() {
        LoginRequest request = new LoginRequest();
        request.setUsername("nobody");
        request.setPassword("any");
        when(doctorMapper.selectByUsername("nobody")).thenReturn(null);

        BusinessException ex = assertThrows(BusinessException.class, () -> authService.login(request));
        assertEquals("用户名或密码错误", ex.getMessage());
    }

    @Test
    @DisplayName("登录失败 - 密码错误")
    void login_wrongPassword_throwsBusinessException() {
        LoginRequest request = new LoginRequest();
        request.setUsername("zhangsan");
        request.setPassword("wrong_password");
        when(doctorMapper.selectByUsername("zhangsan")).thenReturn(mockDoctor);

        BusinessException ex = assertThrows(BusinessException.class, () -> authService.login(request));
        assertEquals("用户名或密码错误", ex.getMessage());
    }

    @Test
    @DisplayName("登录失败 - 账号禁用")
    void login_disabledAccount_throwsBusinessException() {
        mockDoctor.setStatus(0);
        LoginRequest request = new LoginRequest();
        request.setUsername("zhangsan");
        request.setPassword(RAW_PASSWORD);
        when(doctorMapper.selectByUsername("zhangsan")).thenReturn(mockDoctor);

        BusinessException ex = assertThrows(BusinessException.class, () -> authService.login(request));
        assertTrue(ex.getMessage().contains("禁用"), "异常消息应包含'禁用'");
    }

    @Test
    @DisplayName("权限校验 - 有权限返回true（Redis命中）")
    void checkPermission_hasPermission_fromCache_returnsTrue() {
        PermCheckRequest request = new PermCheckRequest();
        request.setDocId("DOC001");
        request.setProjectCode("BIOCHEM");
        request.setOperateType("INPUT");

        List<String> cachedPerms = Arrays.asList("BIOCHEM:INPUT", "BIOCHEM:QUERY", "DR:INPUT");
        when(redissonClient.getBucket(anyString())).thenReturn(rBucket);
        when(rBucket.get()).thenReturn(JSON.toJSONString(cachedPerms));

        boolean result = authService.checkPermission(request);
        assertTrue(result, "有BIOCHEM:INPUT权限时应返回true");
    }

    @Test
    @DisplayName("权限校验 - 无权限返回false（Redis命中）")
    void checkPermission_noPermission_fromCache_returnsFalse() {
        PermCheckRequest request = new PermCheckRequest();
        request.setDocId("DOC001");
        request.setProjectCode("DR");
        request.setOperateType("AUDIT");

        List<String> cachedPerms = Arrays.asList("BIOCHEM:INPUT", "BIOCHEM:QUERY");
        when(redissonClient.getBucket(anyString())).thenReturn(rBucket);
        when(rBucket.get()).thenReturn(JSON.toJSONString(cachedPerms));

        boolean result = authService.checkPermission(request);
        assertFalse(result, "无DR:AUDIT权限时应返回false");
    }

    @Test
    @DisplayName("权限校验 - Redis未命中时查DB")
    void checkPermission_noCache_queriesDB() {
        PermCheckRequest request = new PermCheckRequest();
        request.setDocId("DOC001");
        request.setProjectCode("CBC");
        request.setOperateType("INPUT");

        when(redissonClient.getBucket(anyString())).thenReturn(rBucket);
        when(rBucket.get()).thenReturn(null); // 缓存未命中
        when(docPermissionMapper.countPermission("DOC001", "CBC", "INPUT")).thenReturn(1);

        boolean result = authService.checkPermission(request);
        assertTrue(result);
        verify(docPermissionMapper).countPermission("DOC001", "CBC", "INPUT");
    }

    @Test
    @DisplayName("退出登录 - 清除Redis缓存")
    void logout_clearsRedisCache() {
        // 生成一个有效Token
        List<DocPermission> perms = buildPermissions("DOC001");
        when(doctorMapper.selectByUsername("zhangsan")).thenReturn(mockDoctor);
        when(docPermissionMapper.selectByDocId("DOC001")).thenReturn(perms);
        when(redissonClient.getBucket(anyString())).thenReturn(rBucket);
        doNothing().when(rBucket).set(anyString(), anyLong(), any(TimeUnit.class));

        LoginRequest req = new LoginRequest();
        req.setUsername("zhangsan");
        req.setPassword(RAW_PASSWORD);
        LoginResponse resp = authService.login(req);

        // 退出登录
        when(rBucket.delete()).thenReturn(true);
        authService.logout(resp.getToken());

        // 验证 delete 被调用了至少一次（token/user/perm 各一次）
        verify(rBucket, atLeast(1)).delete();
    }

    // ===== helpers =====
    private List<DocPermission> buildPermissions(String docId) {
        DocPermission p1 = new DocPermission();
        p1.setDocId(docId);
        p1.setProjectCode("BIOCHEM");
        p1.setProjectName("生化检验");
        p1.setOperateType("INPUT");
        p1.setStatus(1);

        DocPermission p2 = new DocPermission();
        p2.setDocId(docId);
        p2.setProjectCode("BIOCHEM");
        p2.setProjectName("生化检验");
        p2.setOperateType("QUERY");
        p2.setStatus(1);

        DocPermission p3 = new DocPermission();
        p3.setDocId(docId);
        p3.setProjectCode("DR");
        p3.setProjectName("DR放射");
        p3.setOperateType("INPUT");
        p3.setStatus(1);

        return Arrays.asList(p1, p2, p3);
    }
}
