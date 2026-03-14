package com.ilbuy.common.mybatis.handler;

import com.baomidou.mybatisplus.core.handlers.MetaObjectHandler;
import com.ilbuy.common.security.context.LoginUser;
import com.ilbuy.common.security.context.SecurityUtils;
import lombok.extern.slf4j.Slf4j;
import org.apache.ibatis.reflection.MetaObject;
import org.springframework.stereotype.Component;

import java.time.LocalDateTime;

/**
 * MyBatis-Plus 字段自动填充处理器
 *
 * <p>自动填充以下字段（对应BaseEntity中的@TableField(fill=...)注解）：
 * <ul>
 *   <li>createTime - 插入时自动设置为当前时间</li>
 *   <li>updateTime - 插入和更新时自动设置为当前时间</li>
 *   <li>createBy - 插入时自动设置为当前登录用户ID（可选）</li>
 *   <li>updateBy - 更新时自动设置为当前登录用户ID（可选）</li>
 * </ul>
 *
 * @author ILbuy Team
 * @version 1.0.0
 */
@Slf4j
@Component
public class MetaObjectHandlerImpl implements MetaObjectHandler {

    @Override
    public void insertFill(MetaObject metaObject) {
        LocalDateTime now = LocalDateTime.now();
        // 自动填充创建时间（字段存在且为空时才填充）
        strictInsertFill(metaObject, "createTime", LocalDateTime.class, now);
        strictInsertFill(metaObject, "updateTime", LocalDateTime.class, now);

        // 填充创建人（从Security上下文获取当前用户ID）
        if (metaObject.hasSetter("createBy")) {
            Long currentUserId = getCurrentUserId();
            if (currentUserId != null) {
                strictInsertFill(metaObject, "createBy", Long.class, currentUserId);
                strictInsertFill(metaObject, "updateBy", Long.class, currentUserId);
            }
        }
    }

    @Override
    public void updateFill(MetaObject metaObject) {
        // 自动填充更新时间
        strictUpdateFill(metaObject, "updateTime", LocalDateTime.class, LocalDateTime.now());

        // 填充更新人
        if (metaObject.hasSetter("updateBy")) {
            Long currentUserId = getCurrentUserId();
            if (currentUserId != null) {
                strictUpdateFill(metaObject, "updateBy", Long.class, currentUserId);
            }
        }
    }

    /**
     * 安全获取当前登录用户ID
     * 非HTTP请求上下文（如定时任务、消息消费）时返回null
     */
    private Long getCurrentUserId() {
        try {
            LoginUser user = SecurityUtils.currentUserOrNull();
            return user != null ? user.getUserId() : null;
        } catch (Exception e) {
            log.debug("[MetaHandler] 无法获取当前用户ID（非HTTP请求上下文）");
            return null;
        }
    }
}
