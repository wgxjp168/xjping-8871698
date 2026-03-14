-- =============================================
-- ILbuy AI采购决策平台 - 数据库初始化脚本
-- =============================================

CREATE DATABASE IF NOT EXISTS ilbuy_main CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS ilbuy_report CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS ilbuy_payment CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS nacos_config CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE ilbuy_main;

-- 用户表
CREATE TABLE IF NOT EXISTS ilbuy_user (
    id BIGINT PRIMARY KEY COMMENT '用户ID',
    username VARCHAR(64) NOT NULL UNIQUE COMMENT '用户名',
    password VARCHAR(128) NOT NULL COMMENT '加密密码',
    phone VARCHAR(20) UNIQUE COMMENT '手机号',
    email VARCHAR(128) UNIQUE COMMENT '邮箱',
    user_type VARCHAR(10) NOT NULL DEFAULT 'B2C' COMMENT '用户类型: B2B/B2C',
    company_name VARCHAR(128) COMMENT '企业名称',
    credit_code VARCHAR(64) COMMENT '统一社会信用代码',
    status TINYINT NOT NULL DEFAULT 1 COMMENT '状态: 0-禁用 1-正常',
    member_level VARCHAR(20) NOT NULL DEFAULT 'FREE' COMMENT '会员等级',
    member_expire_time DATETIME COMMENT '会员到期时间',
    decision_count INT NOT NULL DEFAULT 0 COMMENT '累计决策次数',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted TINYINT NOT NULL DEFAULT 0,
    INDEX idx_phone (phone),
    INDEX idx_email (email),
    INDEX idx_user_type (user_type)
) ENGINE=InnoDB COMMENT='用户表';

-- 用户画像表
CREATE TABLE IF NOT EXISTS ilbuy_user_profile (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT NOT NULL UNIQUE COMMENT '用户ID',
    industry VARCHAR(64) COMMENT '所属行业',
    budget_range VARCHAR(32) COMMENT '预算区间',
    preferred_categories JSON COMMENT '偏好商品类别',
    purchase_frequency VARCHAR(20) COMMENT '采购频率',
    extra_info JSON COMMENT '扩展画像信息',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id)
) ENGINE=InnoDB COMMENT='用户画像表';

-- 采购决策记录表
CREATE TABLE IF NOT EXISTS ilbuy_decision_record (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    session_id VARCHAR(64) NOT NULL UNIQUE COMMENT '会话ID',
    user_id BIGINT NOT NULL COMMENT '用户ID',
    user_type VARCHAR(10) COMMENT 'B2B/B2C',
    brand_status VARCHAR(20) COMMENT '品牌状态',
    product_category VARCHAR(64) COMMENT '商品类别',
    user_input TEXT COMMENT '用户输入',
    decision_result JSON COMMENT 'AI决策结果',
    report_id BIGINT COMMENT '关联报告ID',
    status VARCHAR(20) NOT NULL DEFAULT 'PROCESSING' COMMENT '状态: PROCESSING/DONE/FAILED',
    cost_ms INT COMMENT '耗时(ms)',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id),
    INDEX idx_session_id (session_id),
    INDEX idx_create_time (create_time)
) ENGINE=InnoDB COMMENT='采购决策记录表';

-- 订单表
CREATE TABLE IF NOT EXISTS ilbuy_order (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    order_no VARCHAR(32) NOT NULL UNIQUE COMMENT '订单号',
    user_id BIGINT NOT NULL COMMENT '用户ID',
    order_type VARCHAR(20) NOT NULL COMMENT '订单类型: DECISION_FEE/MEMBER/B2B_CUSTOM',
    amount DECIMAL(12,2) NOT NULL COMMENT '订单金额',
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING' COMMENT '订单状态',
    pay_channel VARCHAR(20) COMMENT '支付渠道: WECHAT/ALIPAY/UNIONPAY',
    pay_time DATETIME COMMENT '支付时间',
    remark VARCHAR(256) COMMENT '备注',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id),
    INDEX idx_order_no (order_no),
    INDEX idx_status (status)
) ENGINE=InnoDB COMMENT='订单表';

USE ilbuy_report;

-- 报告表
CREATE TABLE IF NOT EXISTS ilbuy_report (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    report_no VARCHAR(32) NOT NULL UNIQUE COMMENT '报告编号',
    user_id BIGINT NOT NULL COMMENT '用户ID',
    session_id VARCHAR(64) COMMENT '关联会话ID',
    report_type VARCHAR(30) NOT NULL COMMENT '报告类型: B2B/B2C_BRAND/B2C_NO_BRAND',
    title VARCHAR(256) COMMENT '报告标题',
    content LONGTEXT COMMENT '报告内容(HTML)',
    pdf_url VARCHAR(512) COMMENT 'PDF文件地址',
    excel_url VARCHAR(512) COMMENT 'Excel文件地址',
    status VARCHAR(20) NOT NULL DEFAULT 'GENERATING' COMMENT '状态',
    is_public TINYINT DEFAULT 0 COMMENT '是否公开',
    expire_time DATETIME COMMENT '过期时间',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id),
    INDEX idx_session_id (session_id)
) ENGINE=InnoDB COMMENT='采购决策报告表';
