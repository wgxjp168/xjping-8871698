-- =====================================================
-- 健康检查系统数据库脚本
-- Health Check System with Device Integration
-- Version: 1.0.0
-- =====================================================

CREATE DATABASE IF NOT EXISTS health_check DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE health_check;

-- =====================================================
-- 1. 用户表 (sys_user)
-- =====================================================
CREATE TABLE IF NOT EXISTS `sys_user` (
  `id`          BIGINT       NOT NULL AUTO_INCREMENT COMMENT '用户ID',
  `username`    VARCHAR(50)  NOT NULL COMMENT '用户名',
  `password`    VARCHAR(100) NOT NULL COMMENT '密码(BCrypt)',
  `real_name`   VARCHAR(50)  DEFAULT NULL COMMENT '真实姓名',
  `gender`      TINYINT(1)   DEFAULT 1 COMMENT '性别 1男 2女',
  `phone`       VARCHAR(20)  DEFAULT NULL COMMENT '手机号',
  `email`       VARCHAR(100) DEFAULT NULL COMMENT '邮箱',
  `avatar`      VARCHAR(255) DEFAULT NULL COMMENT '头像URL',
  `role`        VARCHAR(20)  NOT NULL DEFAULT 'USER' COMMENT '角色 ADMIN/DOCTOR/USER',
  `dept_id`     BIGINT       DEFAULT NULL COMMENT '科室ID',
  `status`      TINYINT(1)   DEFAULT 1 COMMENT '状态 1启用 0禁用',
  `last_login`  DATETIME     DEFAULT NULL COMMENT '最后登录时间',
  `create_time` DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `deleted`     TINYINT(1)   DEFAULT 0 COMMENT '逻辑删除 0正常 1删除',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_username` (`username`),
  KEY `idx_role` (`role`),
  KEY `idx_dept_id` (`dept_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='系统用户表';

-- =====================================================
-- 2. 科室表 (dept)
-- =====================================================
CREATE TABLE IF NOT EXISTS `dept` (
  `id`          BIGINT      NOT NULL AUTO_INCREMENT COMMENT '科室ID',
  `name`        VARCHAR(50) NOT NULL COMMENT '科室名称',
  `code`        VARCHAR(20) DEFAULT NULL COMMENT '科室编码',
  `parent_id`   BIGINT      DEFAULT 0 COMMENT '上级科室ID',
  `sort`        INT         DEFAULT 0 COMMENT '排序',
  `description` VARCHAR(200) DEFAULT NULL COMMENT '描述',
  `status`      TINYINT(1)  DEFAULT 1 COMMENT '状态',
  `create_time` DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_time` DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `deleted`     TINYINT(1)  DEFAULT 0,
  PRIMARY KEY (`id`),
  KEY `idx_parent_id` (`parent_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='科室表';

-- =====================================================
-- 3. 检查项目表 (check_item)
-- =====================================================
CREATE TABLE IF NOT EXISTS `check_item` (
  `id`          BIGINT       NOT NULL AUTO_INCREMENT COMMENT '检查项ID',
  `name`        VARCHAR(100) NOT NULL COMMENT '检查项名称',
  `code`        VARCHAR(50)  DEFAULT NULL COMMENT '检查项编码',
  `category`    VARCHAR(50)  DEFAULT NULL COMMENT '分类(体格/生化/影像/设备)',
  `unit`        VARCHAR(20)  DEFAULT NULL COMMENT '单位',
  `normal_min`  DECIMAL(10,2) DEFAULT NULL COMMENT '正常范围最小值',
  `normal_max`  DECIMAL(10,2) DEFAULT NULL COMMENT '正常范围最大值',
  `normal_text` VARCHAR(100) DEFAULT NULL COMMENT '正常范围文本说明',
  `device_type` VARCHAR(50)  DEFAULT NULL COMMENT '关联设备类型',
  `sort`        INT          DEFAULT 0 COMMENT '排序',
  `status`      TINYINT(1)   DEFAULT 1 COMMENT '状态',
  `create_time` DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_time` DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `deleted`     TINYINT(1)   DEFAULT 0,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_code` (`code`),
  KEY `idx_category` (`category`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='检查项目表';

-- =====================================================
-- 4. 套餐表 (check_package)
-- =====================================================
CREATE TABLE IF NOT EXISTS `check_package` (
  `id`          BIGINT       NOT NULL AUTO_INCREMENT COMMENT '套餐ID',
  `name`        VARCHAR(100) NOT NULL COMMENT '套餐名称',
  `code`        VARCHAR(50)  DEFAULT NULL COMMENT '套餐编码',
  `category`    VARCHAR(50)  DEFAULT NULL COMMENT '套餐分类',
  `price`       DECIMAL(10,2) DEFAULT 0 COMMENT '价格',
  `description` VARCHAR(500) DEFAULT NULL COMMENT '套餐描述',
  `image_url`   VARCHAR(255) DEFAULT NULL COMMENT '套餐图片',
  `status`      TINYINT(1)   DEFAULT 1 COMMENT '状态',
  `create_time` DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_time` DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `deleted`     TINYINT(1)   DEFAULT 0,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='检查套餐表';

-- =====================================================
-- 5. 套餐-检查项关联表
-- =====================================================
CREATE TABLE IF NOT EXISTS `check_package_item` (
  `id`         BIGINT NOT NULL AUTO_INCREMENT,
  `package_id` BIGINT NOT NULL COMMENT '套餐ID',
  `item_id`    BIGINT NOT NULL COMMENT '检查项ID',
  `sort`       INT    DEFAULT 0,
  PRIMARY KEY (`id`),
  KEY `idx_package_id` (`package_id`),
  KEY `idx_item_id` (`item_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='套餐检查项关联表';

-- =====================================================
-- 6. 设备表 (device)
-- =====================================================
CREATE TABLE IF NOT EXISTS `device` (
  `id`            BIGINT       NOT NULL AUTO_INCREMENT COMMENT '设备ID',
  `name`          VARCHAR(100) NOT NULL COMMENT '设备名称',
  `code`          VARCHAR(50)  NOT NULL COMMENT '设备编码',
  `type`          VARCHAR(50)  DEFAULT NULL COMMENT '设备类型(血压计/心电图/血糖仪等)',
  `model`         VARCHAR(100) DEFAULT NULL COMMENT '设备型号',
  `manufacturer`  VARCHAR(100) DEFAULT NULL COMMENT '生产厂商',
  `serial_no`     VARCHAR(100) DEFAULT NULL COMMENT '序列号',
  `dept_id`       BIGINT       DEFAULT NULL COMMENT '所属科室',
  `ip_address`    VARCHAR(50)  DEFAULT NULL COMMENT 'IP地址',
  `port`          INT          DEFAULT NULL COMMENT '端口号',
  `protocol`      VARCHAR(20)  DEFAULT 'HTTP' COMMENT '通信协议',
  `status`        VARCHAR(20)  DEFAULT 'OFFLINE' COMMENT '状态 ONLINE/OFFLINE/FAULT',
  `last_heartbeat` DATETIME    DEFAULT NULL COMMENT '最后心跳时间',
  `calibration_date` DATE      DEFAULT NULL COMMENT '校准日期',
  `description`   VARCHAR(200) DEFAULT NULL COMMENT '备注',
  `create_time`   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_time`   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `deleted`       TINYINT(1)   DEFAULT 0,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_code` (`code`),
  KEY `idx_type` (`type`),
  KEY `idx_dept_id` (`dept_id`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='医疗设备表';

-- =====================================================
-- 7. 设备数据记录表 (device_data)
-- =====================================================
CREATE TABLE IF NOT EXISTS `device_data` (
  `id`          BIGINT        NOT NULL AUTO_INCREMENT COMMENT '记录ID',
  `device_id`   BIGINT        NOT NULL COMMENT '设备ID',
  `device_code` VARCHAR(50)   DEFAULT NULL COMMENT '设备编码',
  `order_id`    BIGINT        DEFAULT NULL COMMENT '检查单ID',
  `patient_id`  BIGINT        DEFAULT NULL COMMENT '患者ID',
  `item_code`   VARCHAR(50)   DEFAULT NULL COMMENT '检查项编码',
  `value`       VARCHAR(200)  DEFAULT NULL COMMENT '检测值',
  `unit`        VARCHAR(20)   DEFAULT NULL COMMENT '单位',
  `raw_data`    TEXT          DEFAULT NULL COMMENT '原始数据(JSON)',
  `measure_time` DATETIME     DEFAULT NULL COMMENT '测量时间',
  `status`      VARCHAR(20)   DEFAULT 'PENDING' COMMENT '状态 PENDING/CONFIRMED/INVALID',
  `create_time` DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_device_id` (`device_id`),
  KEY `idx_order_id` (`order_id`),
  KEY `idx_patient_id` (`patient_id`),
  KEY `idx_measure_time` (`measure_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='设备采集数据表';

-- =====================================================
-- 8. 体检预约表 (check_appointment)
-- =====================================================
CREATE TABLE IF NOT EXISTS `check_appointment` (
  `id`           BIGINT      NOT NULL AUTO_INCREMENT COMMENT '预约ID',
  `patient_id`   BIGINT      NOT NULL COMMENT '患者ID',
  `package_id`   BIGINT      DEFAULT NULL COMMENT '套餐ID',
  `appoint_date` DATE        NOT NULL COMMENT '预约日期',
  `appoint_time` VARCHAR(20) DEFAULT NULL COMMENT '预约时段',
  `status`       VARCHAR(20) DEFAULT 'PENDING' COMMENT '状态 PENDING/CONFIRMED/CANCELLED/COMPLETED',
  `remark`       VARCHAR(200) DEFAULT NULL COMMENT '备注',
  `create_time`  DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_time`  DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_patient_id` (`patient_id`),
  KEY `idx_appoint_date` (`appoint_date`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='体检预约表';

-- =====================================================
-- 8.5 居民信息表 (resident)
-- =====================================================
CREATE TABLE IF NOT EXISTS `resident` (
  `id`           BIGINT       NOT NULL AUTO_INCREMENT COMMENT '居民ID',
  `name`         VARCHAR(50)  NOT NULL COMMENT '姓名',
  `id_card`      VARCHAR(18)  NOT NULL COMMENT '身份证号',
  `gender`       TINYINT(1)   DEFAULT 1 COMMENT '性别 1男 2女',
  `birth_date`   DATE         DEFAULT NULL COMMENT '出生日期',
  `phone`        VARCHAR(20)  DEFAULT NULL COMMENT '手机号',
  `address`      VARCHAR(200) DEFAULT NULL COMMENT '住址',
  `village`      VARCHAR(100) DEFAULT NULL COMMENT '所属村/社区',
  `town`         VARCHAR(100) DEFAULT NULL COMMENT '所属乡镇/街道',
  `district`     VARCHAR(100) DEFAULT NULL COMMENT '所属县区',
  `ethnicity`    VARCHAR(50)  DEFAULT NULL COMMENT '民族',
  `blood_type`   VARCHAR(10)  DEFAULT NULL COMMENT '血型',
  `chronic_flag` INT          DEFAULT 0 COMMENT '慢病标记：高血压=1, 糖尿病=2, 精神=4 (位运算组合)',
  `archive_no`   VARCHAR(50)  DEFAULT NULL COMMENT '档案编号',
  `dept_id`      BIGINT       DEFAULT NULL COMMENT '所属医疗机构ID',
  `status`       TINYINT(1)   DEFAULT 1 COMMENT '状态 1正常',
  `create_time`  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time`  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `deleted`      TINYINT(1)   DEFAULT 0 COMMENT '逻辑删除 0正常 1删除',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_id_card` (`id_card`),
  KEY `idx_name` (`name`),
  KEY `idx_town` (`town`),
  KEY `idx_dept_id` (`dept_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='居民信息表';

-- =====================================================
-- 9. 体检单表 (check_order)
-- =====================================================
CREATE TABLE IF NOT EXISTS `check_order` (
  `id`              BIGINT       NOT NULL AUTO_INCREMENT COMMENT '体检单ID',
  `order_no`        VARCHAR(50)  NOT NULL COMMENT '体检单号',
  `resident_id`     BIGINT       DEFAULT NULL COMMENT '居民ID',
  `resident_name`   VARCHAR(50)  DEFAULT NULL COMMENT '居民姓名',
  `id_card`         VARCHAR(18)  DEFAULT NULL COMMENT '居民身份证',
  `check_year`      INT          DEFAULT NULL COMMENT '体检年度',
  `check_date`      DATE         DEFAULT NULL COMMENT '体检日期',
  `dept_id`         BIGINT       DEFAULT NULL COMMENT '体检机构ID',
  `check_type`      TINYINT(1)   DEFAULT NULL COMMENT '体检类型 1老年人 2高血压 3糖尿病 4孕产妇',
  `status`          TINYINT(1)   DEFAULT 0 COMMENT '状态 0待体检 1体检中 2已完成 3已作废',
  `remark`          VARCHAR(500) DEFAULT NULL COMMENT '备注',
  `create_time`     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_time`     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `deleted`         TINYINT(1)   DEFAULT 0,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_order_no` (`order_no`),
  KEY `idx_resident_id` (`resident_id`),
  KEY `idx_id_card` (`id_card`),
  KEY `idx_check_date` (`check_date`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='体检单表';

-- =====================================================
-- 10. 体检结果明细表 (check_result)
-- =====================================================
CREATE TABLE IF NOT EXISTS `check_result` (
  `id`           BIGINT        NOT NULL AUTO_INCREMENT COMMENT '结果ID',
  `order_id`     BIGINT        NOT NULL COMMENT '体检单ID',
  `item_id`      BIGINT        NOT NULL COMMENT '检查项ID',
  `item_name`    VARCHAR(100)  DEFAULT NULL COMMENT '检查项名称',
  `value`        VARCHAR(200)  DEFAULT NULL COMMENT '检测值',
  `unit`         VARCHAR(20)   DEFAULT NULL COMMENT '单位',
  `normal_range` VARCHAR(100)  DEFAULT NULL COMMENT '参考范围',
  `flag`         VARCHAR(10)   DEFAULT 'NORMAL' COMMENT '标记 NORMAL/HIGH/LOW/ABNORMAL',
  `device_id`    BIGINT        DEFAULT NULL COMMENT '采集设备ID',
  `data_source`  VARCHAR(20)   DEFAULT 'MANUAL' COMMENT '数据来源 MANUAL/DEVICE',
  `doctor_id`    BIGINT        DEFAULT NULL COMMENT '检查医生',
  `remark`       VARCHAR(200)  DEFAULT NULL COMMENT '备注',
  `check_time`   DATETIME      DEFAULT NULL COMMENT '检查时间',
  `create_time`  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_time`  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_order_id` (`order_id`),
  KEY `idx_item_id` (`item_id`),
  KEY `idx_device_id` (`device_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='体检结果明细表';

-- =====================================================
-- 11. 诊断报告表 (diagnosis)
-- =====================================================
CREATE TABLE IF NOT EXISTS `diagnosis` (
  `id`              BIGINT   NOT NULL AUTO_INCREMENT COMMENT '诊断ID',
  `order_id`        BIGINT   NOT NULL COMMENT '体检单ID',
  `patient_id`      BIGINT   NOT NULL COMMENT '患者ID',
  `doctor_id`       BIGINT   NOT NULL COMMENT '诊断医生ID',
  `health_score`    INT      DEFAULT NULL COMMENT '健康评分(0-100)',
  `conclusion`      TEXT     DEFAULT NULL COMMENT '诊断结论',
  `suggestion`      TEXT     DEFAULT NULL COMMENT '健康建议',
  `abnormal_items`  TEXT     DEFAULT NULL COMMENT '异常项目JSON',
  `risk_level`      VARCHAR(20) DEFAULT 'LOW' COMMENT '风险等级 LOW/MEDIUM/HIGH',
  `status`          VARCHAR(20) DEFAULT 'DRAFT' COMMENT '状态 DRAFT/CONFIRMED/PUBLISHED',
  `confirm_time`    DATETIME DEFAULT NULL COMMENT '确认时间',
  `publish_time`    DATETIME DEFAULT NULL COMMENT '发布时间',
  `create_time`     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_time`     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `deleted`         TINYINT(1) DEFAULT 0,
  PRIMARY KEY (`id`),
  KEY `idx_order_id` (`order_id`),
  KEY `idx_patient_id` (`patient_id`),
  KEY `idx_doctor_id` (`doctor_id`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='诊断报告表';

-- =====================================================
-- 12. 操作日志表 (sys_log)
-- =====================================================
CREATE TABLE IF NOT EXISTS `sys_log` (
  `id`          BIGINT       NOT NULL AUTO_INCREMENT,
  `user_id`     BIGINT       DEFAULT NULL COMMENT '操作用户ID',
  `username`    VARCHAR(50)  DEFAULT NULL COMMENT '操作用户名',
  `module`      VARCHAR(50)  DEFAULT NULL COMMENT '操作模块',
  `action`      VARCHAR(50)  DEFAULT NULL COMMENT '操作动作',
  `description` VARCHAR(200) DEFAULT NULL COMMENT '操作描述',
  `ip`          VARCHAR(50)  DEFAULT NULL COMMENT '操作IP',
  `status`      TINYINT(1)   DEFAULT 1 COMMENT '状态 1成功 0失败',
  `error_msg`   TEXT         DEFAULT NULL COMMENT '错误信息',
  `cost_time`   BIGINT       DEFAULT NULL COMMENT '耗时(ms)',
  `create_time` DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_create_time` (`create_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='系统操作日志';

-- =====================================================
-- 初始化数据
-- =====================================================

-- 初始化科室
INSERT INTO `dept` (`id`, `name`, `code`, `parent_id`, `sort`, `description`) VALUES
(1, '体检中心', 'DEPT001', 0, 1, '综合体检中心'),
(2, '内科', 'DEPT002', 1, 2, '内科检查'),
(3, '外科', 'DEPT003', 1, 3, '外科检查'),
(4, '心血管科', 'DEPT004', 1, 4, '心血管检查'),
(5, '影像科', 'DEPT005', 1, 5, '影像学检查'),
(6, '检验科', 'DEPT006', 1, 6, '实验室检查');

-- 初始化用户 (密码均为 health123 的 BCrypt 加密)
INSERT INTO `sys_user` (`id`, `username`, `password`, `real_name`, `gender`, `phone`, `role`, `dept_id`, `status`) VALUES
(1, 'admin', '$2a$10$EqKpQ/aEjHqyWVWH8jnNbu.AUqSGgxVBb8JmjKBIlMXWPdlOxYNay', '系统管理员', 1, '13800000001', 'ADMIN', 1, 1),
(2, 'doctor01', '$2a$10$EqKpQ/aEjHqyWVWH8jnNbu.AUqSGgxVBb8JmjKBIlMXWPdlOxYNay', '张医生', 1, '13800000002', 'DOCTOR', 2, 1),
(3, 'doctor02', '$2a$10$EqKpQ/aEjHqyWVWH8jnNbu.AUqSGgxVBb8JmjKBIlMXWPdlOxYNay', '李医生', 2, '13800000003', 'DOCTOR', 4, 1),
(4, 'user01', '$2a$10$EqKpQ/aEjHqyWVWH8jnNbu.AUqSGgxVBb8JmjKBIlMXWPdlOxYNay', '王小明', 1, '13900000001', 'USER', NULL, 1),
(5, 'user02', '$2a$10$EqKpQ/aEjHqyWVWH8jnNbu.AUqSGgxVBb8JmjKBIlMXWPdlOxYNay', '李小红', 2, '13900000002', 'USER', NULL, 1);

-- 初始化检查项目
INSERT INTO `check_item` (`id`, `name`, `code`, `category`, `unit`, `normal_min`, `normal_max`, `normal_text`, `device_type`) VALUES
(1, '身高', 'CI001', '体格', 'cm', 140, 200, '140~200cm', NULL),
(2, '体重', 'CI002', '体格', 'kg', 40, 100, '40~100kg', NULL),
(3, '体重指数(BMI)', 'CI003', '体格', 'kg/m²', 18.5, 23.9, '18.5~23.9', NULL),
(4, '收缩压', 'CI004', '体格', 'mmHg', 90, 139, '90~139mmHg', 'BLOOD_PRESSURE'),
(5, '舒张压', 'CI005', '体格', 'mmHg', 60, 89, '60~89mmHg', 'BLOOD_PRESSURE'),
(6, '心率', 'CI006', '体格', '次/分', 60, 100, '60~100次/分', 'ECG'),
(7, '血氧饱和度', 'CI007', '体格', '%', 95, 100, '95~100%', 'OXIMETER'),
(8, '血糖(空腹)', 'CI008', '生化', 'mmol/L', 3.9, 6.1, '3.9~6.1mmol/L', 'GLUCOMETER'),
(9, '总胆固醇', 'CI009', '生化', 'mmol/L', 0, 5.2, '<5.2mmol/L', NULL),
(10, '甘油三酯', 'CI010', '生化', 'mmol/L', 0, 1.7, '<1.7mmol/L', NULL),
(11, '血红蛋白', 'CI011', '血常规', 'g/L', 120, 160, '120~160g/L', NULL),
(12, '白细胞计数', 'CI012', '血常规', '×10⁹/L', 4, 10, '4~10×10⁹/L', NULL),
(13, '心电图', 'CI013', '心电', NULL, NULL, NULL, '正常心电图', 'ECG'),
(14, '胸部X光', 'CI014', '影像', NULL, NULL, NULL, '肺部正常', 'XRAY'),
(15, '腹部超声', 'CI015', '影像', NULL, NULL, NULL, '腹部脏器未见异常', 'ULTRASOUND');

-- 初始化套餐
INSERT INTO `check_package` (`id`, `name`, `code`, `category`, `price`, `description`) VALUES
(1, '基础体检套餐', 'PKG001', 'BASIC', 199.00, '包含基本体格检查、血常规、血糖、血压等项目'),
(2, '标准健康套餐', 'PKG002', 'STANDARD', 399.00, '包含基础套餐全部项目，增加血脂、心电图等'),
(3, '全面健康套餐', 'PKG003', 'PREMIUM', 799.00, '包含标准套餐全部项目，增加影像学检查'),
(4, '心血管专项套餐', 'PKG004', 'SPECIAL', 599.00, '专注心血管系统检查，包含血压、心电图、心脏超声等');

-- 套餐检查项关联
INSERT INTO `check_package_item` (`package_id`, `item_id`, `sort`) VALUES
(1,1,1),(1,2,2),(1,3,3),(1,4,4),(1,5,5),(1,6,6),(1,8,7),(1,11,8),(1,12,9),
(2,1,1),(2,2,2),(2,3,3),(2,4,4),(2,5,5),(2,6,6),(2,7,7),(2,8,8),(2,9,9),(2,10,10),(2,11,11),(2,12,12),(2,13,13),
(3,1,1),(3,2,2),(3,3,3),(3,4,4),(3,5,5),(3,6,6),(3,7,7),(3,8,8),(3,9,9),(3,10,10),(3,11,11),(3,12,12),(3,13,13),(3,14,14),(3,15,15),
(4,4,1),(4,5,2),(4,6,3),(4,7,4),(4,9,5),(4,10,6),(4,13,7);

-- 初始化设备
INSERT INTO `device` (`id`, `name`, `code`, `type`, `model`, `manufacturer`, `serial_no`, `dept_id`, `ip_address`, `port`, `protocol`, `status`) VALUES
(1, '血压计-001', 'DEV001', 'BLOOD_PRESSURE', 'BP-3000', '欧姆龙', 'SN20240001', 2, '192.168.1.101', 8080, 'HTTP', 'ONLINE'),
(2, '12导联心电图仪', 'DEV002', 'ECG', 'ECG-1200', '迈瑞', 'SN20240002', 4, '192.168.1.102', 8080, 'HTTP', 'ONLINE'),
(3, '血糖仪-001', 'DEV003', 'GLUCOMETER', 'GL-500', '罗氏', 'SN20240003', 2, '192.168.1.103', 8080, 'HTTP', 'OFFLINE'),
(4, '血氧仪-001', 'DEV004', 'OXIMETER', 'OX-200', '鱼跃', 'SN20240004', 2, '192.168.1.104', 8080, 'HTTP', 'ONLINE'),
(5, '数字X光机', 'DEV005', 'XRAY', 'DR-5000', '联影', 'SN20240005', 5, '192.168.1.105', 8080, 'HTTP', 'ONLINE'),
(6, '超声诊断仪', 'DEV006', 'ULTRASOUND', 'US-8000', '迈瑞', 'SN20240006', 5, '192.168.1.106', 8080, 'HTTP', 'ONLINE');
