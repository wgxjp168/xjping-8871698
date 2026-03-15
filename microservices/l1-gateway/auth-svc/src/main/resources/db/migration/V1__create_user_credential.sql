-- =====================================================
-- auth-svc: 用户凭证表（认证专用，业务信息由 user-svc 维护）
-- =====================================================
CREATE DATABASE IF NOT EXISTS ilbuy_auth
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;

USE ilbuy_auth;

CREATE TABLE IF NOT EXISTS user_credential
(
    id            BIGINT       NOT NULL AUTO_INCREMENT COMMENT '主键',
    user_id       BIGINT       NOT NULL COMMENT '关联 user-svc 用户ID',
    username      VARCHAR(64)  NOT NULL COMMENT '用户名（唯一）',
    phone         VARCHAR(20)  NULL COMMENT '手机号（唯一）',
    email         VARCHAR(128) NULL COMMENT '邮箱（唯一）',
    password_hash VARCHAR(128) NOT NULL COMMENT 'BCrypt 密码哈希',
    user_type     VARCHAR(16)  NOT NULL DEFAULT 'CONSUMER' COMMENT '用户类型: BUSINESS/CONSUMER',
    roles         VARCHAR(256) NOT NULL DEFAULT 'ROLE_USER' COMMENT '角色（逗号分隔）',
    enabled       TINYINT(1)   NOT NULL DEFAULT 1 COMMENT '账号状态: 1=启用 0=禁用',
    created_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (id),
    UNIQUE KEY uk_user_id (user_id),
    UNIQUE KEY uk_username (username),
    UNIQUE KEY uk_phone (phone),
    UNIQUE KEY uk_email (email)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_unicode_ci
    COMMENT = '用户凭证表（认证授权服务专用）';

-- 初始化测试账号（开发环境，密码均为 Test@123456）
-- BCrypt hash of 'Test@123456'
INSERT INTO user_credential (user_id, username, phone, email, password_hash, user_type, roles)
VALUES
    (10001, 'consumer_test', '13800138001', 'consumer@ilbuy.com',
     '$2a$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LJxHrGhHRw/QDQ5W.',
     'CONSUMER', 'ROLE_USER'),
    (10002, 'business_test', '13800138002', 'business@ilbuy.com',
     '$2a$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LJxHrGhHRw/QDQ5W.',
     'BUSINESS', 'ROLE_ENTERPRISE,ROLE_USER'),
    (10003, 'admin', '13800138000', 'admin@ilbuy.com',
     '$2a$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LJxHrGhHRw/QDQ5W.',
     'BUSINESS', 'ROLE_ADMIN,ROLE_ENTERPRISE,ROLE_USER');
