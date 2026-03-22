-- ============================================================
-- user_db 表结构 (01-user-db.sql)
-- ============================================================
USE user_db;

-- ── 用户表 ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS `t_user` (
  `id`              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '用户ID',
  `username`        VARCHAR(64)     NOT NULL                COMMENT '用户名',
  `password_hash`   VARCHAR(128)    NOT NULL                COMMENT 'BCrypt密码',
  `phone`           VARCHAR(20)     NOT NULL DEFAULT ''     COMMENT '手机号',
  `email`           VARCHAR(128)    NOT NULL DEFAULT ''     COMMENT '邮箱',
  `real_name`       VARCHAR(64)     DEFAULT ''              COMMENT '真实姓名',
  `avatar_url`      VARCHAR(512)    DEFAULT ''              COMMENT '头像URL',
  `gender`          TINYINT         NOT NULL DEFAULT 0      COMMENT '性别: 0=未知 1=男 2=女',
  `birthday`        DATE                                    COMMENT '生日',
  `status`          TINYINT         NOT NULL DEFAULT 1      COMMENT '状态: 0=禁用 1=正常 2=待审',
  `login_fail_cnt`  INT             NOT NULL DEFAULT 0      COMMENT '连续登录失败次数',
  `locked_until`    DATETIME                                COMMENT '账号锁定到期时间',
  `last_login_at`   DATETIME                                COMMENT '最后登录时间',
  `last_login_ip`   VARCHAR(64)     DEFAULT ''              COMMENT '最后登录IP',
  `create_time`     DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_time`     DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `is_deleted`      TINYINT         NOT NULL DEFAULT 0,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_username` (`username`),
  KEY `idx_phone`   (`phone`),
  KEY `idx_email`   (`email`),
  KEY `idx_status`  (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户表';

-- ── 角色表 ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS `t_role` (
  `id`          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `name`        VARCHAR(64)     NOT NULL COMMENT '角色名称',
  `code`        VARCHAR(64)     NOT NULL COMMENT '角色编码',
  `description` VARCHAR(256)    DEFAULT '' COMMENT '描述',
  `is_system`   TINYINT         NOT NULL DEFAULT 0 COMMENT '是否系统角色',
  `status`      TINYINT         NOT NULL DEFAULT 1,
  `create_time` DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_time` DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_code` (`code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='角色表';

-- ── 权限表 ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS `t_permission` (
  `id`          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `code`        VARCHAR(128)    NOT NULL COMMENT '权限编码',
  `name`        VARCHAR(64)     NOT NULL COMMENT '权限名称',
  `module`      VARCHAR(64)     DEFAULT '' COMMENT '模块',
  `resource`    VARCHAR(128)    DEFAULT '' COMMENT '资源',
  `action`      VARCHAR(64)     DEFAULT '' COMMENT '操作',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_code` (`code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='权限表';

-- ── 用户角色关联 ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS `t_user_role` (
  `user_id`     BIGINT UNSIGNED NOT NULL,
  `role_id`     BIGINT UNSIGNED NOT NULL,
  `create_time` DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`user_id`, `role_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户角色关联';

-- ── 角色权限关联 ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS `t_role_permission` (
  `role_id`        BIGINT UNSIGNED NOT NULL,
  `permission_id`  BIGINT UNSIGNED NOT NULL,
  PRIMARY KEY (`role_id`, `permission_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='角色权限关联';

-- ── 用户 Session ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS `t_user_session` (
  `id`            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `user_id`       BIGINT UNSIGNED NOT NULL,
  `token`         VARCHAR(512)    NOT NULL COMMENT 'JWT Token',
  `refresh_token` VARCHAR(512)    COMMENT '刷新Token',
  `device_type`   VARCHAR(32)     DEFAULT 'web' COMMENT 'web|ios|android|api',
  `ip_address`    VARCHAR(64)     DEFAULT '',
  `user_agent`    VARCHAR(512)    DEFAULT '',
  `expires_at`    DATETIME        NOT NULL,
  `create_time`   DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_token` (`token`(255)),
  KEY `idx_user_id`    (`user_id`),
  KEY `idx_expires_at` (`expires_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户会话表';

-- ── 初始数据 ──────────────────────────────────────────────
INSERT IGNORE INTO `t_role` (`id`, `name`, `code`, `is_system`) VALUES
  (1, '超级管理员', 'SUPER_ADMIN', 1),
  (2, '普通用户',   'USER',        1),
  (3, '采购员',     'PURCHASER',   1),
  (4, '财务',       'FINANCE',     1),
  (5, '供应商管理', 'SUPPLIER_MGR',1);
