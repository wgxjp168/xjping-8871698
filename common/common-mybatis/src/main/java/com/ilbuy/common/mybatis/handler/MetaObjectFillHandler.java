package com.ilbuy.common.mybatis.handler;

import com.baomidou.mybatisplus.core.handlers.MetaObjectHandler;
import lombok.extern.slf4j.Slf4j;
import org.apache.ibatis.reflection.MetaObject;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Component;

import java.time.LocalDateTime;

/**
 * MyBatis-Plus 字段自动填充处理器
 *
 * <p>在 INSERT 或 UPDATE 时自动填充：</p>
 * <ul>
 *   <li>createTime / updateTime — 当前时间</li>
 *   <li>createBy / updateBy     — 当前登录用户 ID（从 SecurityContext 取）</li>
 *   <li>deleted                 — 插入时置 0</li>
 *   <li>version                 — 插入时置 0</li>
 * </ul>
 */
@Slf4j
@Component
public class MetaObjectFillHandler implements MetaObjectHandler {

    @Override
    public void insertFill(MetaObject metaObject) {
        LocalDateTime now = LocalDateTime.now();
        Long userId = getCurrentUserId();

        fillIfNull(metaObject, "createTime", now);
        fillIfNull(metaObject, "updateTime", now);
        fillIfNull(metaObject, "createBy",   userId);
        fillIfNull(metaObject, "updateBy",   userId);
        fillIfNull(metaObject, "deleted",    0);
        fillIfNull(metaObject, "version",    0);
    }

    @Override
    public void updateFill(MetaObject metaObject) {
        LocalDateTime now = LocalDateTime.now();
        Long userId = getCurrentUserId();

        // 强制覆盖（无论是否已赋值）
        setFieldValByName("updateTime", now,    metaObject);
        setFieldValByName("updateBy",   userId, metaObject);
    }

    /**
     * 仅当字段值为 null 时才填充（避免覆盖业务代码手动设置的值）
     */
    private void fillIfNull(MetaObject metaObject, String fieldName, Object value) {
        if (metaObject.hasSetter(fieldName)) {
            Object existVal = getFieldValByName(fieldName, metaObject);
            if (existVal == null) {
                setFieldValByName(fieldName, value, metaObject);
            }
        }
    }

    /**
     * 从 Spring Security 上下文获取当前用户 ID
     * <p>若没有认证信息（如定时任务）返回 -1（系统账户）</p>
     */
    private Long getCurrentUserId() {
        try {
            Authentication auth = SecurityContextHolder.getContext().getAuthentication();
            if (auth != null && auth.isAuthenticated()
                    && auth.getPrincipal() instanceof com.ilbuy.common.security.model.LoginUser loginUser) {
                return loginUser.getUserId();
            }
        } catch (Exception e) {
            log.debug("[MetaObjectFillHandler] 获取当前用户 ID 失败（非 Web 上下文）: {}", e.getMessage());
        }
        return -1L; // 系统账户
    }
}
