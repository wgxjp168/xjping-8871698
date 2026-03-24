package com.health.physical.auth.service;

import com.health.physical.auth.dto.LoginRequest;
import com.health.physical.auth.dto.LoginResponse;
import com.health.physical.auth.dto.PermCheckRequest;
import com.health.physical.auth.entity.DocPermission;
import com.health.physical.auth.entity.Doctor;

import java.util.List;

/**
 * 权限服务接口
 */
public interface AuthService {

    /**
     * 医生登录（网页端/移动端统一入口）
     */
    LoginResponse login(LoginRequest request);

    /**
     * 校验Token并返回医生信息
     */
    Doctor validateToken(String token);

    /**
     * 退出登录（清除缓存）
     */
    void logout(String token);

    /**
     * 校验医生是否有指定操作权限
     * @return true-有权限，false-无权限
     */
    boolean checkPermission(PermCheckRequest request);

    /**
     * 获取医生全部有效权限
     */
    List<DocPermission> getDoctorPermissions(String docId);

    /**
     * 从县域公卫系统同步医生账号和权限
     */
    void syncFromCounty();

    /**
     * 手动授权/撤权
     */
    void grantPermission(DocPermission permission, String operatorId);

    /**
     * 撤销权限
     */
    void revokePermission(Long permissionId, String operatorId);
}
