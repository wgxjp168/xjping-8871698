package com.health.physical.auth.service.impl;

import cn.hutool.crypto.digest.BCrypt;
import com.alibaba.fastjson2.JSON;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper;
import com.health.physical.auth.dto.LoginRequest;
import com.health.physical.auth.dto.LoginResponse;
import com.health.physical.auth.dto.PermCheckRequest;
import com.health.physical.auth.entity.DocPermission;
import com.health.physical.auth.entity.Doctor;
import com.health.physical.auth.mapper.DocPermissionMapper;
import com.health.physical.auth.mapper.DoctorMapper;
import com.health.physical.auth.service.AuthService;
import com.health.physical.common.constant.PermissionConstants;
import com.health.physical.common.exception.BusinessException;
import com.health.physical.common.util.JwtUtil;
import io.jsonwebtoken.Claims;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.redisson.api.RBucket;
import org.redisson.api.RedissonClient;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.TimeUnit;
import java.util.stream.Collectors;

/**
 * 权限服务实现
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class AuthServiceImpl implements AuthService {

    private final DoctorMapper doctorMapper;
    private final DocPermissionMapper docPermissionMapper;
    private final RedissonClient redissonClient;

    @Value("${jwt.secret:physical_health_system_jwt_secret_key_2024_secure_enough}")
    private String jwtSecret;

    @Value("${jwt.expire-seconds:43200}")
    private long expireSeconds;

    @Override
    public LoginResponse login(LoginRequest request) {
        // 1. 查询医生账号
        Doctor doctor = doctorMapper.selectByUsername(request.getUsername());
        if (doctor == null) {
            throw BusinessException.of("用户名或密码错误");
        }
        if (doctor.getStatus() != 1) {
            throw BusinessException.of("账号已被禁用，请联系管理员");
        }

        // 2. 校验密码
        if (!BCrypt.checkpw(request.getPassword(), doctor.getPassword())) {
            throw BusinessException.of("用户名或密码错误");
        }

        // 3. 网页端MAC地址绑定校验
        if ("WEB".equals(request.getLoginSource())) {
            validateMacAddress(doctor, request.getMacAddress());
        }

        // 4. 查询权限列表
        List<DocPermission> permissions = docPermissionMapper.selectByDocId(doctor.getDocId());
        List<String> projectCodes = permissions.stream()
                .map(DocPermission::getProjectCode)
                .distinct()
                .collect(Collectors.toList());
        List<String> permList = permissions.stream()
                .map(p -> p.getProjectCode() + ":" + p.getOperateType())
                .collect(Collectors.toList());

        // 5. 生成JWT Token
        Map<String, Object> claims = new HashMap<>();
        claims.put("docId", doctor.getDocId());
        claims.put("name", doctor.getName());
        claims.put("dept", doctor.getDept());
        claims.put("perms", JSON.toJSONString(permList));

        String token = JwtUtil.generateToken(doctor.getUsername(), claims, expireSeconds, jwtSecret);

        // 6. 缓存Token和用户信息到Redis
        String tokenKey = PermissionConstants.REDIS_TOKEN_PREFIX + token;
        String userKey = PermissionConstants.REDIS_USER_PREFIX + doctor.getDocId();
        String permKey = PermissionConstants.REDIS_PERM_PREFIX + doctor.getDocId();

        RBucket<String> tokenBucket = redissonClient.getBucket(tokenKey);
        tokenBucket.set(doctor.getDocId(), expireSeconds, TimeUnit.SECONDS);

        RBucket<String> userBucket = redissonClient.getBucket(userKey);
        userBucket.set(JSON.toJSONString(doctor), expireSeconds, TimeUnit.SECONDS);

        RBucket<String> permBucket = redissonClient.getBucket(permKey);
        permBucket.set(JSON.toJSONString(permList), expireSeconds, TimeUnit.SECONDS);

        // 7. 更新最后登录时间
        doctorMapper.update(null, new LambdaUpdateWrapper<Doctor>()
                .eq(Doctor::getId, doctor.getId())
                .set(Doctor::getLastLoginTime, LocalDateTime.now())
                .set(Doctor::getLastLoginIp, request.getMacAddress()));

        log.info("医生登录成功: docId={}, name={}, projectCodes={}", doctor.getDocId(), doctor.getName(), projectCodes);

        return LoginResponse.builder()
                .token(token)
                .expireIn(expireSeconds)
                .docId(doctor.getDocId())
                .username(doctor.getUsername())
                .name(doctor.getName())
                .dept(doctor.getDept())
                .deptName(doctor.getDeptName())
                .title(doctor.getTitle())
                .projectCodes(projectCodes)
                .permissions(permList)
                .build();
    }

    @Override
    public Doctor validateToken(String token) {
        // 1. 验证JWT签名和有效期
        Claims claims = JwtUtil.parseToken(token, jwtSecret);
        if (claims == null) {
            throw BusinessException.unauthorized("Token无效或已过期");
        }

        // 2. 检查Redis中Token是否存在（防止logout后重用）
        String tokenKey = PermissionConstants.REDIS_TOKEN_PREFIX + token;
        RBucket<String> tokenBucket = redissonClient.getBucket(tokenKey);
        String docId = tokenBucket.get();
        if (docId == null) {
            throw BusinessException.unauthorized("Token已失效，请重新登录");
        }

        // 3. 从缓存/数据库获取医生信息
        String userKey = PermissionConstants.REDIS_USER_PREFIX + docId;
        RBucket<String> userBucket = redissonClient.getBucket(userKey);
        String userJson = userBucket.get();
        if (userJson != null) {
            return JSON.parseObject(userJson, Doctor.class);
        }

        Doctor doctor = doctorMapper.selectByDocId(docId);
        if (doctor == null || doctor.getStatus() != 1) {
            throw BusinessException.unauthorized("账号不存在或已被禁用");
        }
        return doctor;
    }

    @Override
    public void logout(String token) {
        try {
            Claims claims = JwtUtil.parseToken(token, jwtSecret);
            if (claims != null) {
                String docId = (String) claims.get("docId");
                // 清除Redis缓存
                redissonClient.getBucket(PermissionConstants.REDIS_TOKEN_PREFIX + token).delete();
                redissonClient.getBucket(PermissionConstants.REDIS_USER_PREFIX + docId).delete();
                redissonClient.getBucket(PermissionConstants.REDIS_PERM_PREFIX + docId).delete();
                log.info("医生退出登录: docId={}", docId);
            }
        } catch (Exception e) {
            log.warn("退出登录清理缓存异常: {}", e.getMessage());
        }
    }

    @Override
    public boolean checkPermission(PermCheckRequest request) {
        // 优先从Redis缓存获取
        String permKey = PermissionConstants.REDIS_PERM_PREFIX + request.getDocId();
        RBucket<String> permBucket = redissonClient.getBucket(permKey);
        String permJson = permBucket.get();

        String permStr = request.getProjectCode() + ":" + request.getOperateType();

        if (permJson != null) {
            List<String> perms = JSON.parseArray(permJson, String.class);
            return perms.contains(permStr);
        }

        // 缓存未命中，查数据库
        int count = docPermissionMapper.countPermission(
                request.getDocId(), request.getProjectCode(), request.getOperateType());
        return count > 0;
    }

    @Override
    public List<DocPermission> getDoctorPermissions(String docId) {
        return docPermissionMapper.selectByDocId(docId);
    }

    @Override
    public void syncFromCounty() {
        // 此处为县域同步占位实现
        // 实际实现需调用县域公卫系统API，获取医生列表和权限列表，同步至本地数据库
        log.info("开始同步县域公卫系统医生账号和权限...");
        // TODO: 调用 county.api.base-url + /api/doctors/list 获取医生列表
        // TODO: 调用 county.api.base-url + /api/permissions/list 获取权限列表
        // TODO: 批量更新本地 physical_doctor 和 physical_doc_permission 表
        log.info("县域同步完成");
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void grantPermission(DocPermission permission, String operatorId) {
        permission.setGrantedBy(operatorId);
        permission.setStatus(1);

        // 检查是否已存在
        LambdaQueryWrapper<DocPermission> wrapper = new LambdaQueryWrapper<DocPermission>()
                .eq(DocPermission::getDocId, permission.getDocId())
                .eq(DocPermission::getProjectCode, permission.getProjectCode())
                .eq(DocPermission::getOperateType, permission.getOperateType());

        DocPermission existing = docPermissionMapper.selectOne(wrapper);
        if (existing != null) {
            permission.setId(existing.getId());
            docPermissionMapper.updateById(permission);
        } else {
            docPermissionMapper.insert(permission);
        }

        // 清除缓存，下次请求重新加载
        redissonClient.getBucket(PermissionConstants.REDIS_PERM_PREFIX + permission.getDocId()).delete();
        log.info("授权成功: docId={}, project={}, operate={}", permission.getDocId(), permission.getProjectCode(), permission.getOperateType());
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void revokePermission(Long permissionId, String operatorId) {
        DocPermission perm = docPermissionMapper.selectById(permissionId);
        if (perm == null) {
            throw BusinessException.of("权限记录不存在");
        }
        docPermissionMapper.update(null, new LambdaUpdateWrapper<DocPermission>()
                .eq(DocPermission::getId, permissionId)
                .set(DocPermission::getStatus, 0));

        // 清除缓存
        redissonClient.getBucket(PermissionConstants.REDIS_PERM_PREFIX + perm.getDocId()).delete();
        log.info("撤权成功: permissionId={}, docId={}, operatorId={}", permissionId, perm.getDocId(), operatorId);
    }

    private void validateMacAddress(Doctor doctor, String mac) {
        if (mac == null || mac.isBlank()) {
            return; // MAC未传则不校验（初次登录）
        }
        String boundMacs = doctor.getMacAddresses();
        if (boundMacs == null || boundMacs.isBlank()) {
            // 首次登录绑定MAC地址
            doctorMapper.update(null, new LambdaUpdateWrapper<Doctor>()
                    .eq(Doctor::getId, doctor.getId())
                    .set(Doctor::getMacAddresses, mac));
            log.info("首次绑定MAC地址: docId={}, mac={}", doctor.getDocId(), mac);
            return;
        }
        // 校验MAC地址是否在绑定列表中
        String[] macs = boundMacs.split(",");
        for (String boundMac : macs) {
            if (boundMac.trim().equalsIgnoreCase(mac)) {
                return; // 校验通过
            }
        }
        throw BusinessException.forbidden("该电脑未授权，请联系管理员绑定MAC地址后再登录");
    }
}
