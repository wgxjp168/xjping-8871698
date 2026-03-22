-- ============================================================
-- message_db 表结构 (06-message-db.sql)
-- ============================================================
USE message_db;

-- ── 消息模板 ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS `t_notify_template` (
  `id`               BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `code`             VARCHAR(64)     NOT NULL COMMENT '模板编码',
  `name`             VARCHAR(128)    NOT NULL COMMENT '模板名称',
  `channel`          VARCHAR(32)     NOT NULL DEFAULT 'internal' COMMENT 'internal|sms|email|push|all',
  `title_template`   VARCHAR(256)    DEFAULT '',
  `content_template` TEXT            NOT NULL COMMENT '模板内容，变量用 ${xxx} 占位',
  `variables`        VARCHAR(512)    DEFAULT '[]' COMMENT '变量列表 JSON',
  `status`           TINYINT         NOT NULL DEFAULT 1 COMMENT '1=启用 0=禁用',
  `create_time`      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_time`      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_code` (`code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='通知模板';

-- ── 站内消息 ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS `t_internal_message` (
  `id`          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `sender_id`   BIGINT UNSIGNED DEFAULT NULL COMMENT '发送者ID，NULL=系统消息',
  `receiver_id` BIGINT UNSIGNED NOT NULL COMMENT '接收者ID',
  `msg_type`    VARCHAR(32)     NOT NULL DEFAULT 'system' COMMENT 'system|business|personal|alert',
  `title`       VARCHAR(256)    NOT NULL,
  `content`     TEXT            NOT NULL,
  `biz_type`    VARCHAR(64)     DEFAULT '' COMMENT '业务类型',
  `biz_id`      BIGINT          DEFAULT 0 COMMENT '业务ID',
  `action_url`  VARCHAR(512)    DEFAULT '' COMMENT '跳转链接',
  `is_read`     TINYINT         NOT NULL DEFAULT 0,
  `read_at`     DATETIME,
  `create_time` DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_receiver_read` (`receiver_id`, `is_read`),
  KEY `idx_create_time`   (`create_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='站内消息';

-- ── 短信发送记录 ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS `t_sms_record` (
  `id`              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `phone`           VARCHAR(20)     NOT NULL,
  `template_code`   VARCHAR(64)     DEFAULT '',
  `params`          VARCHAR(512)    DEFAULT '{}',
  `content`         VARCHAR(512)    NOT NULL COMMENT '消息内容',
  `status`          TINYINT         NOT NULL DEFAULT 0 COMMENT '0=待发送 1=已发送 2=已送达 3=发送失败',
  `provider`        VARCHAR(32)     DEFAULT 'aliyun',
  `provider_msg_id` VARCHAR(128)    DEFAULT '',
  `error_msg`       VARCHAR(256)    DEFAULT '',
  `sent_at`         DATETIME,
  `create_time`     DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_phone_time`   (`phone`, `create_time`),
  KEY `idx_status`       (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='短信发送记录';

-- ── 邮件发送记录 ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS `t_email_record` (
  `id`            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `to_email`      VARCHAR(128)    NOT NULL,
  `cc_emails`     VARCHAR(512)    DEFAULT '' COMMENT '抄送 JSON',
  `subject`       VARCHAR(256)    NOT NULL,
  `body`          TEXT            NOT NULL,
  `body_type`     VARCHAR(16)     NOT NULL DEFAULT 'html',
  `template_code` VARCHAR(64)     DEFAULT '',
  `status`        TINYINT         NOT NULL DEFAULT 0 COMMENT '0=待发送 1=已发送 2=发送失败 3=退信',
  `error_msg`     VARCHAR(256)    DEFAULT '',
  `retry_count`   INT             NOT NULL DEFAULT 0,
  `sent_at`       DATETIME,
  `create_time`   DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_to_email_time` (`to_email`, `create_time`),
  KEY `idx_status`        (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='邮件发送记录';

-- ── 预置消息模板 ──────────────────────────────────────────
INSERT IGNORE INTO `t_notify_template` (`code`, `name`, `channel`, `title_template`, `content_template`, `variables`) VALUES
  ('ORDER_PAID',     '订单支付成功通知', 'all',      '您的订单已支付成功',       '您好 ${userName}，订单 ${orderNo} 已支付成功，金额 ${amount} 元。', '["userName","orderNo","amount"]'),
  ('ORDER_SHIPPED',  '订单发货通知',     'all',      '您的订单已发货',           '您好 ${userName}，订单 ${orderNo} 已通过 ${company} 发货，运单号 ${trackingNo}。', '["userName","orderNo","company","trackingNo"]'),
  ('SMS_VERIFY',     '短信验证码',       'sms',      '',                          '【来购ILbuy】您的验证码是 ${code}，${minutes} 分钟内有效，请勿泄露。', '["code","minutes"]'),
  ('SUPPLIER_AUDIT', '供应商审核通知',   'email',    '供应商审核结果通知',        '尊敬的供应商 ${supplierName}，您的入驻申请审核结果：${result}。', '["supplierName","result"]');
