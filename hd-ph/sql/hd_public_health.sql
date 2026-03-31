-- ========================================================
-- 惠东县区域公卫体检集中系统 - 完整数据库脚本
-- Version: 1.0.0  Database: MySQL 8.0
-- ========================================================

CREATE DATABASE IF NOT EXISTS `hd_public_health`
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

USE `hd_public_health`;

-- ========================================================
-- 1. 系统科室表
-- ========================================================
DROP TABLE IF EXISTS `sys_dept`;
CREATE TABLE `sys_dept` (
  `id`            BIGINT       NOT NULL AUTO_INCREMENT COMMENT '科室ID',
  `dept_name`     VARCHAR(100) NOT NULL                COMMENT '科室名称',
  `dept_code`     VARCHAR(50)  DEFAULT NULL            COMMENT '科室编码',
  `dept_type`     TINYINT      DEFAULT 1               COMMENT '部门类型 1卫生院 2村卫生室 3社区卫生中心 9其他',
  `parent_id`     BIGINT       DEFAULT 0               COMMENT '父科室ID',
  `sort`          INT          DEFAULT 0               COMMENT '排序',
  `address`       VARCHAR(200) DEFAULT NULL            COMMENT '地址',
  `contact_phone` VARCHAR(20)  DEFAULT NULL            COMMENT '联系电话',
  `status`        TINYINT      DEFAULT 1               COMMENT '状态 1启用 0停用',
  `create_time`   DATETIME     DEFAULT CURRENT_TIMESTAMP,
  `update_time`   DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `deleted`       TINYINT      DEFAULT 0               COMMENT '逻辑删除',
  PRIMARY KEY (`id`),
  KEY `idx_parent_id` (`parent_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='系统科室表';

-- ========================================================
-- 2. 系统用户表
-- ========================================================
DROP TABLE IF EXISTS `sys_user`;
CREATE TABLE `sys_user` (
  `id`              BIGINT       NOT NULL AUTO_INCREMENT COMMENT '用户ID',
  `username`        VARCHAR(50)  NOT NULL               COMMENT '登录账号',
  `password`        VARCHAR(100) NOT NULL               COMMENT '密码(BCrypt)',
  `real_name`       VARCHAR(50)  DEFAULT NULL           COMMENT '真实姓名',
  `phone`           VARCHAR(20)  DEFAULT NULL           COMMENT '手机号',
  `dept_id`         BIGINT       DEFAULT NULL           COMMENT '科室ID',
  `user_type`       TINYINT      DEFAULT 1              COMMENT '1=操作员 2=医生 3=管理员',
  `status`          TINYINT      DEFAULT 1              COMMENT '1启用 0停用',
  `last_login_time` DATETIME     DEFAULT NULL           COMMENT '最后登录时间',
  `create_time`     DATETIME     DEFAULT CURRENT_TIMESTAMP,
  `update_time`     DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `deleted`         TINYINT      DEFAULT 0,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_username` (`username`),
  KEY `idx_dept_id` (`dept_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='系统用户表';

-- ========================================================
-- 3. 角色表
-- ========================================================
DROP TABLE IF EXISTS `sys_role`;
CREATE TABLE `sys_role` (
  `id`          BIGINT       NOT NULL AUTO_INCREMENT,
  `role_code`   VARCHAR(50)  NOT NULL               COMMENT '角色编码',
  `role_name`   VARCHAR(100) DEFAULT NULL           COMMENT '角色名称',
  `description` VARCHAR(200) DEFAULT NULL,
  `status`      TINYINT      DEFAULT 1,
  `create_time` DATETIME     DEFAULT CURRENT_TIMESTAMP,
  `update_time` DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `deleted`     TINYINT      DEFAULT 0,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_role_code` (`role_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='角色表';

-- ========================================================
-- 4. 用户-角色关联表
-- ========================================================
DROP TABLE IF EXISTS `sys_user_role`;
CREATE TABLE `sys_user_role` (
  `id`      BIGINT NOT NULL AUTO_INCREMENT,
  `user_id` BIGINT NOT NULL,
  `role_id` BIGINT NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_user_role` (`user_id`, `role_id`),
  KEY `idx_role_id` (`role_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户角色关联表';

-- ========================================================
-- 5. 权限表
-- ========================================================
DROP TABLE IF EXISTS `sys_permission`;
CREATE TABLE `sys_permission` (
  `id`          BIGINT       NOT NULL AUTO_INCREMENT,
  `perm_code`   VARCHAR(100) NOT NULL               COMMENT '权限编码',
  `perm_name`   VARCHAR(100) DEFAULT NULL           COMMENT '权限名称',
  `perm_type`   TINYINT      DEFAULT 1              COMMENT '1=菜单 2=按钮',
  `parent_code` VARCHAR(100) DEFAULT NULL           COMMENT '父权限编码',
  `sort`        INT          DEFAULT 0,
  `status`      TINYINT      DEFAULT 1,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_perm_code` (`perm_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='权限表';

-- ========================================================
-- 6. 角色-权限关联表
-- ========================================================
DROP TABLE IF EXISTS `sys_role_permission`;
CREATE TABLE `sys_role_permission` (
  `id`        BIGINT       NOT NULL AUTO_INCREMENT,
  `role_id`   BIGINT       NOT NULL,
  `perm_code` VARCHAR(100) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_role_perm` (`role_id`, `perm_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='角色权限关联表';

-- ========================================================
-- 7. 数据字典表
-- ========================================================
DROP TABLE IF EXISTS `sys_dict`;
CREATE TABLE `sys_dict` (
  `id`          BIGINT       NOT NULL AUTO_INCREMENT,
  `dict_type`   VARCHAR(100) NOT NULL               COMMENT '字典类型',
  `dict_name`   VARCHAR(100) DEFAULT NULL           COMMENT '字典名称',
  `status`      TINYINT      DEFAULT 1,
  `create_time` DATETIME     DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_dict_type` (`dict_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='数据字典类型';

DROP TABLE IF EXISTS `sys_dict_item`;
CREATE TABLE `sys_dict_item` (
  `id`          BIGINT       NOT NULL AUTO_INCREMENT,
  `dict_type`   VARCHAR(100) NOT NULL,
  `item_value`  VARCHAR(100) NOT NULL               COMMENT '字典值',
  `item_label`  VARCHAR(200) NOT NULL               COMMENT '字典标签',
  `sort`        INT          DEFAULT 0,
  `status`      TINYINT      DEFAULT 1,
  `remark`      VARCHAR(200) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_dict_type` (`dict_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='数据字典项';

-- ========================================================
-- 8. 居民信息表
-- ========================================================
DROP TABLE IF EXISTS `resident`;
CREATE TABLE `resident` (
  `id`           BIGINT       NOT NULL AUTO_INCREMENT COMMENT '居民ID',
  `name`         VARCHAR(50)  NOT NULL               COMMENT '姓名',
  `id_card`      VARCHAR(18)  NOT NULL               COMMENT '身份证号',
  `gender`       TINYINT      DEFAULT 1              COMMENT '1男 2女',
  `birth_date`   DATE         DEFAULT NULL           COMMENT '出生日期',
  `phone`        VARCHAR(20)  DEFAULT NULL           COMMENT '手机号',
  `address`      VARCHAR(200) DEFAULT NULL           COMMENT '住址',
  `village`      VARCHAR(100) DEFAULT NULL           COMMENT '所属村/社区',
  `town`         VARCHAR(100) DEFAULT NULL           COMMENT '所属乡镇/街道',
  `district`     VARCHAR(100) DEFAULT NULL           COMMENT '所属县区',
  `ethnicity`    VARCHAR(50)  DEFAULT NULL           COMMENT '民族',
  `blood_type`   VARCHAR(10)  DEFAULT NULL           COMMENT '血型',
  `chronic_flag` INT          DEFAULT 0              COMMENT '慢病标记：高血压=1, 糖尿病=2, 精神=4 (位运算组合)',
  `archive_no`   VARCHAR(50)  DEFAULT NULL           COMMENT '档案编号',
  `dept_id`      BIGINT       DEFAULT NULL           COMMENT '所属医疗机构ID',
  `status`       TINYINT      DEFAULT 1              COMMENT '状态 1正常',
  `create_time`  DATETIME     DEFAULT CURRENT_TIMESTAMP,
  `update_time`  DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `deleted`      TINYINT      DEFAULT 0              COMMENT '逻辑删除 0正常 1删除',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_id_card` (`id_card`),
  KEY `idx_name` (`name`),
  KEY `idx_town` (`town`),
  KEY `idx_dept_id` (`dept_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='居民信息表';

-- ========================================================
-- 9. 体检单表（由县域公卫系统开单下发）
-- ========================================================
DROP TABLE IF EXISTS `check_order`;
CREATE TABLE `check_order` (
  `id`             BIGINT       NOT NULL AUTO_INCREMENT COMMENT '体检单ID',
  `order_no`       VARCHAR(50)  NOT NULL               COMMENT '体检单号(条码)',
  `resident_id`    BIGINT       DEFAULT NULL           COMMENT '居民ID',
  `resident_name`  VARCHAR(50)  DEFAULT NULL           COMMENT '居民姓名',
  `id_card`        VARCHAR(18)  DEFAULT NULL           COMMENT '身份证号',
  `check_year`     INT          DEFAULT NULL           COMMENT '体检年份',
  `check_date`     DATE         DEFAULT NULL           COMMENT '体检日期',
  `dept_id`        BIGINT       DEFAULT NULL           COMMENT '体检机构ID',
  `check_type`     TINYINT      DEFAULT NULL           COMMENT '体检类型 1老年人 2高血压 3糖尿病 4孕产妇',
  `status`         TINYINT      DEFAULT 0              COMMENT '状态 0待体检 1体检中 2已完成 3已作废',
  `remark`         VARCHAR(500) DEFAULT NULL           COMMENT '备注',
  `create_time`    DATETIME     DEFAULT CURRENT_TIMESTAMP,
  `update_time`    DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `deleted`        TINYINT      DEFAULT 0,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_order_no` (`order_no`),
  KEY `idx_resident_id` (`resident_id`),
  KEY `idx_id_card` (`id_card`),
  KEY `idx_check_date` (`check_date`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='体检单表';

-- ========================================================
-- 10. 生命体征表（血压、体重、身高等）
-- ========================================================
DROP TABLE IF EXISTS `vital_sign`;
CREATE TABLE `vital_sign` (
  `id`                  BIGINT        NOT NULL AUTO_INCREMENT,
  `order_id`            BIGINT        NOT NULL               COMMENT '体检单ID',
  `order_no`            VARCHAR(50)   DEFAULT NULL,
  `resident_id`         BIGINT        DEFAULT NULL,
  `systolic_bp`         INT           DEFAULT NULL           COMMENT '收缩压 mmHg',
  `diastolic_bp`        INT           DEFAULT NULL           COMMENT '舒张压 mmHg',
  `heart_rate`          INT           DEFAULT NULL           COMMENT '心率 次/分',
  `weight`              DECIMAL(5,2)  DEFAULT NULL           COMMENT '体重 kg',
  `height`              DECIMAL(5,1)  DEFAULT NULL           COMMENT '身高 cm',
  `bmi`                 DECIMAL(5,2)  DEFAULT NULL           COMMENT 'BMI',
  `waist_circumference` DECIMAL(5,1)  DEFAULT NULL           COMMENT '腰围 cm',
  `temperature`         DECIMAL(4,1)  DEFAULT NULL           COMMENT '体温 ℃',
  `left_eye_vision`     DECIMAL(4,1)  DEFAULT NULL           COMMENT '左眼视力',
  `right_eye_vision`    DECIMAL(4,1)  DEFAULT NULL           COMMENT '右眼视力',
  `operator_id`         BIGINT        DEFAULT NULL           COMMENT '操作员',
  `operator_name`       VARCHAR(50)   DEFAULT NULL,
  `measure_time`        DATETIME      DEFAULT NULL,
  `upload_status`       TINYINT       DEFAULT 0              COMMENT '0未上传 1已上传',
  `create_time`         DATETIME      DEFAULT CURRENT_TIMESTAMP,
  `update_time`         DATETIME      DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_order_id` (`order_id`),
  KEY `idx_resident_id` (`resident_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='生命体征表';

-- ========================================================
-- 11. 问诊记录表
-- ========================================================
DROP TABLE IF EXISTS `consultation`;
CREATE TABLE `consultation` (
  `id`             BIGINT   NOT NULL AUTO_INCREMENT,
  `order_id`       BIGINT   NOT NULL,
  `order_no`       VARCHAR(50)  DEFAULT NULL,
  `resident_id`    BIGINT   DEFAULT NULL,
  `chief_complaint` TEXT    DEFAULT NULL COMMENT '主诉',
  `present_illness` TEXT    DEFAULT NULL COMMENT '现病史',
  `past_history`   TEXT     DEFAULT NULL COMMENT '既往史',
  `family_history` TEXT     DEFAULT NULL COMMENT '家族史',
  `allergy_history` TEXT    DEFAULT NULL COMMENT '过敏史',
  `smoking_history` VARCHAR(200) DEFAULT NULL COMMENT '吸烟史',
  `drinking_history` VARCHAR(200) DEFAULT NULL COMMENT '饮酒史',
  `physical_exam`  TEXT     DEFAULT NULL COMMENT '体格检查',
  `preliminary_diag` VARCHAR(500) DEFAULT NULL COMMENT '初步诊断',
  `doctor_id`      BIGINT   DEFAULT NULL,
  `doctor_name`    VARCHAR(50) DEFAULT NULL,
  `consult_time`   DATETIME DEFAULT NULL,
  `upload_status`  TINYINT  DEFAULT 0,
  `create_time`    DATETIME DEFAULT CURRENT_TIMESTAMP,
  `update_time`    DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_order_id` (`order_id`),
  KEY `idx_resident_id` (`resident_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='问诊记录表';

-- ========================================================
-- 12. 检验结果表（统一存储所有设备结果）
-- ========================================================
DROP TABLE IF EXISTS `check_result`;
CREATE TABLE `check_result` (
  `id`            BIGINT        NOT NULL AUTO_INCREMENT COMMENT '结果ID',
  `order_id`      BIGINT        DEFAULT NULL           COMMENT '体检单ID',
  `order_no`      VARCHAR(50)   DEFAULT NULL           COMMENT '体检单号',
  `resident_id`   BIGINT        DEFAULT NULL           COMMENT '居民ID',
  `category`      VARCHAR(20)   NOT NULL               COMMENT 'BIOCHEM/BLOOD/URINE/HBA1C',
  `item_code`     VARCHAR(50)   NOT NULL               COMMENT '项目编码',
  `item_name`     VARCHAR(100)  DEFAULT NULL           COMMENT '项目名称',
  `value_str`     VARCHAR(500)  DEFAULT NULL           COMMENT '结果文本',
  `value_num`     DECIMAL(12,4) DEFAULT NULL           COMMENT '数值结果',
  `unit`          VARCHAR(30)   DEFAULT NULL           COMMENT '单位',
  `ref_range`     VARCHAR(100)  DEFAULT NULL           COMMENT '参考范围',
  `flag`          VARCHAR(10)   DEFAULT 'N'            COMMENT 'H高/L低/N正常/A异常',
  `device_id`     BIGINT        DEFAULT NULL           COMMENT '设备ID',
  `device_code`   VARCHAR(50)   DEFAULT NULL           COMMENT '设备编码',
  `device_model`  VARCHAR(100)  DEFAULT NULL           COMMENT '设备型号',
  `data_source`   VARCHAR(20)   DEFAULT 'DEVICE'       COMMENT 'DEVICE/MANUAL',
  `sample_id`     VARCHAR(50)   DEFAULT NULL           COMMENT '样本号',
  `check_time`    DATETIME      DEFAULT NULL           COMMENT '检验时间',
  `upload_status` TINYINT       DEFAULT 0              COMMENT '0未上传 1已上传',
  `upload_time`   DATETIME      DEFAULT NULL,
  `create_time`   DATETIME      DEFAULT CURRENT_TIMESTAMP,
  `update_time`   DATETIME      DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_order_id` (`order_id`),
  KEY `idx_order_no` (`order_no`),
  KEY `idx_resident_id` (`resident_id`),
  KEY `idx_category` (`category`),
  KEY `idx_device_id` (`device_id`),
  KEY `idx_check_time` (`check_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='检验结果表';

-- ========================================================
-- 13. 设备信息表
-- ========================================================
DROP TABLE IF EXISTS `device_info`;
CREATE TABLE `device_info` (
  `id`             BIGINT       NOT NULL AUTO_INCREMENT COMMENT '设备ID',
  `device_code`    VARCHAR(50)  NOT NULL               COMMENT '设备编码',
  `device_name`    VARCHAR(100) NOT NULL               COMMENT '设备名称',
  `device_model`   VARCHAR(100) DEFAULT NULL           COMMENT '设备型号',
  `manufacturer`   VARCHAR(100) DEFAULT NULL           COMMENT '厂商',
  `category`       VARCHAR(20)  NOT NULL               COMMENT 'URINE/BIOCHEM/BLOOD/HBA1C/DR',
  `comm_type`      VARCHAR(20)  DEFAULT 'TCP'          COMMENT 'TCP/SERIAL/FILE',
  `comm_host`      VARCHAR(100) DEFAULT NULL           COMMENT 'IP地址(TCP模式)',
  `comm_port`      INT          DEFAULT 7100           COMMENT '端口/COM号',
  `baud_rate`      INT          DEFAULT 9600           COMMENT '波特率(串口)',
  `protocol`       VARCHAR(30)  DEFAULT 'ASTM'         COMMENT 'ASTM/MINDRAY/HL7',
  `dept_id`        BIGINT       DEFAULT NULL,
  `dept_name`      VARCHAR(100) DEFAULT NULL,
  `status`         VARCHAR(20)  DEFAULT 'OFFLINE'      COMMENT 'ONLINE/OFFLINE/ERROR',
  `last_heartbeat` DATETIME     DEFAULT NULL,
  `remark`         VARCHAR(200) DEFAULT NULL,
  `create_time`    DATETIME     DEFAULT CURRENT_TIMESTAMP,
  `update_time`    DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `deleted`        TINYINT      DEFAULT 0,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_device_code` (`device_code`),
  KEY `idx_category` (`category`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='设备信息表';

-- ========================================================
-- 14. 设备原始数据表（ASTM原始报文）
-- ========================================================
DROP TABLE IF EXISTS `device_raw_data`;
CREATE TABLE `device_raw_data` (
  `id`              BIGINT   NOT NULL AUTO_INCREMENT,
  `device_id`       BIGINT   DEFAULT NULL,
  `device_code`     VARCHAR(50)  DEFAULT NULL,
  `device_model`    VARCHAR(100) DEFAULT NULL,
  `raw_message`     TEXT         DEFAULT NULL COMMENT '原始ASTM报文',
  `parsed_json`     TEXT         DEFAULT NULL COMMENT '解析后JSON',
  `order_no`        VARCHAR(50)  DEFAULT NULL COMMENT '匹配到的体检单号',
  `resident_id`     BIGINT       DEFAULT NULL,
  `process_status`  VARCHAR(20)  DEFAULT 'PENDING' COMMENT 'PENDING/MATCHED/ERROR',
  `error_msg`       VARCHAR(500) DEFAULT NULL,
  `source_ip`       VARCHAR(50)  DEFAULT NULL COMMENT '设备IP',
  `receive_time`    DATETIME     DEFAULT CURRENT_TIMESTAMP,
  `process_time`    DATETIME     DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_device_id` (`device_id`),
  KEY `idx_order_no` (`order_no`),
  KEY `idx_process_status` (`process_status`),
  KEY `idx_receive_time` (`receive_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='设备原始数据表';

-- ========================================================
-- 15. DR申请单表
-- ========================================================
DROP TABLE IF EXISTS `dr_order`;
CREATE TABLE `dr_order` (
  `id`               BIGINT       NOT NULL AUTO_INCREMENT,
  `order_no`         VARCHAR(50)  NOT NULL               COMMENT 'DR申请单号',
  `barcode`          VARCHAR(50)  DEFAULT NULL            COMMENT '条码（与体检单条码对应）',
  `check_order_id`   BIGINT       DEFAULT NULL            COMMENT '关联体检单ID',
  `check_order_no`   VARCHAR(50)  DEFAULT NULL,
  `resident_id`      BIGINT       DEFAULT NULL,
  `resident_name`    VARCHAR(50)  DEFAULT NULL,
  `id_card`          VARCHAR(18)  DEFAULT NULL,
  `gender`           TINYINT      DEFAULT NULL,
  `age`              INT          DEFAULT NULL,
  `body_part`        VARCHAR(50)  DEFAULT '胸部'          COMMENT '检查部位',
  `view_position`    VARCHAR(100) DEFAULT '正位'          COMMENT '投照体位',
  `clinical_info`    VARCHAR(200) DEFAULT NULL            COMMENT '临床资料',
  `status`           VARCHAR(20)  DEFAULT 'PENDING'       COMMENT 'PENDING/SCANNED/REPORTED/UPLOADED',
  `create_doctor_id` BIGINT       DEFAULT NULL,
  `scan_time`        DATETIME     DEFAULT NULL            COMMENT '扫码时间',
  `create_time`      DATETIME     DEFAULT CURRENT_TIMESTAMP,
  `update_time`      DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `deleted`          TINYINT      DEFAULT 0,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_order_no` (`order_no`),
  KEY `idx_barcode` (`barcode`),
  KEY `idx_resident_id` (`resident_id`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='DR申请单表';

-- ========================================================
-- 16. DR报告表
-- ========================================================
DROP TABLE IF EXISTS `dr_report`;
CREATE TABLE `dr_report` (
  `id`             BIGINT   NOT NULL AUTO_INCREMENT,
  `dr_order_id`    BIGINT   NOT NULL,
  `order_no`       VARCHAR(50) DEFAULT NULL,
  `resident_id`    BIGINT   DEFAULT NULL,
  `image_path`     VARCHAR(500) DEFAULT NULL COMMENT '影像文件路径',
  `image_url`      VARCHAR(500) DEFAULT NULL COMMENT '影像访问URL',
  `findings`       TEXT     DEFAULT NULL COMMENT '影像所见',
  `impression`     TEXT     DEFAULT NULL COMMENT '诊断意见',
  `conclusion`     VARCHAR(500) DEFAULT NULL COMMENT '结论',
  `report_doctor_id`   BIGINT DEFAULT NULL COMMENT '报告医生',
  `report_doctor_name` VARCHAR(50) DEFAULT NULL,
  `report_time`    DATETIME DEFAULT NULL,
  `upload_status`  TINYINT  DEFAULT 0,
  `upload_time`    DATETIME DEFAULT NULL,
  `create_time`    DATETIME DEFAULT CURRENT_TIMESTAMP,
  `update_time`    DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_dr_order_id` (`dr_order_id`),
  KEY `idx_resident_id` (`resident_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='DR报告表';

-- ========================================================
-- 17. 上传任务表（到县域公卫系统）
-- ========================================================
DROP TABLE IF EXISTS `upload_task`;
CREATE TABLE `upload_task` (
  `id`           BIGINT       NOT NULL AUTO_INCREMENT,
  `task_type`    VARCHAR(30)  NOT NULL               COMMENT 'VITAL/CONSULT/RESULT/DR',
  `source_id`    BIGINT       NOT NULL               COMMENT '来源记录ID',
  `order_no`     VARCHAR(50)  DEFAULT NULL,
  `resident_id`  BIGINT       DEFAULT NULL,
  `id_card`      VARCHAR(18)  DEFAULT NULL,
  `payload`      TEXT         DEFAULT NULL           COMMENT '请求体JSON',
  `response`     TEXT         DEFAULT NULL           COMMENT '响应体',
  `status`       VARCHAR(20)  DEFAULT 'PENDING'      COMMENT 'PENDING/SUCCESS/FAILED',
  `error_msg`    VARCHAR(500) DEFAULT NULL,
  `retry_count`  INT          DEFAULT 0,
  `create_time`  DATETIME     DEFAULT CURRENT_TIMESTAMP,
  `upload_time`  DATETIME     DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_task_type` (`task_type`),
  KEY `idx_order_no` (`order_no`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='上传任务表';

-- ========================================================
-- 18. 操作日志表
-- ========================================================
DROP TABLE IF EXISTS `sys_log`;
CREATE TABLE `sys_log` (
  `id`          BIGINT       NOT NULL AUTO_INCREMENT,
  `user_id`     BIGINT       DEFAULT NULL,
  `username`    VARCHAR(50)  DEFAULT NULL,
  `module`      VARCHAR(50)  DEFAULT NULL,
  `action`      VARCHAR(100) DEFAULT NULL,
  `method`      VARCHAR(200) DEFAULT NULL,
  `ip`          VARCHAR(50)  DEFAULT NULL,
  `params`      TEXT         DEFAULT NULL,
  `result`      VARCHAR(20)  DEFAULT NULL COMMENT 'SUCCESS/FAIL',
  `cost_ms`     BIGINT       DEFAULT NULL,
  `create_time` DATETIME     DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_create_time` (`create_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='操作日志表';

-- ========================================================
-- 初始化数据
-- ========================================================

-- 科室（含21家卫生院）
INSERT INTO `sys_dept` (`id`,`dept_name`,`dept_code`,`dept_type`,`parent_id`,`sort`,`status`) VALUES
(1, '体检中心','DEPT_EXAM',9,0,1,1),
(2, '检验科','DEPT_LAB',9,1,2,1),
(3, '放射科','DEPT_DR',9,1,3,1),
(4, '内科','DEPT_MED',9,1,4,1),
(5, '公卫科','DEPT_PH',9,0,5,1),
(10,'增光卫生院','DEPT_ZG',1,0,10,1),
(11,'大岭卫生院','DEPT_DL',1,0,11,1),
(12,'白花卫生院','DEPT_BH',1,0,12,1),
(13,'梁化卫生院','DEPT_LH',1,0,13,1),
(14,'稔山卫生院','DEPT_RS',1,0,14,1),
(15,'铁涌卫生院','DEPT_TY',1,0,15,1),
(16,'平海卫生院','DEPT_PH2',1,0,16,1),
(17,'巽寮卫生院','DEPT_XL',1,0,17,1),
(18,'港口卫生院','DEPT_GK',1,0,18,1),
(19,'平山社区卫生服务中心','DEPT_PS',3,0,19,1),
(20,'吉隆卫生院','DEPT_JL',1,0,20,1),
(21,'黄埠卫生院','DEPT_HB',1,0,21,1),
(22,'盐洲卫生院','DEPT_YZ',1,0,22,1),
(23,'多祝卫生院','DEPT_DZ',1,0,23,1),
(24,'松坑卫生院','DEPT_SK',1,0,24,1),
(25,'安墩卫生院','DEPT_AD',1,0,25,1),
(26,'高潭卫生院','DEPT_GT',1,0,26,1),
(27,'宝口卫生院','DEPT_BK',1,0,27,1),
(28,'马山卫生院','DEPT_MS',1,0,28,1),
(29,'白盆珠卫生院','DEPT_BPZ',1,0,29,1),
(30,'新庵卫生院','DEPT_XA',1,0,30,1);

-- 权限（按项目分配）
INSERT INTO `sys_permission` (`perm_code`,`perm_name`,`perm_type`,`parent_code`,`sort`) VALUES
('SYS:ADMIN','系统管理',1,NULL,1),
('SYS:USER','用户管理',2,'SYS:ADMIN',1),
('SYS:ROLE','角色管理',2,'SYS:ADMIN',2),
('SYS:DEVICE','设备管理',2,'SYS:ADMIN',3),
('SYS:DEPT','机构管理',2,'SYS:ADMIN',4),
('SYS:AREA','区域管理',2,'SYS:ADMIN',5),
('RESIDENT:VIEW','居民查询',2,NULL,10),
('ORDER:VIEW','体检单查询',2,NULL,11),
('ORDER:CREATE','创建体检单',2,NULL,12),
('VITAL:VIEW','生命体征查看',2,NULL,20),
('VITAL:EDIT','生命体征录入',2,NULL,21),
('CONSULT:VIEW','问诊查看',2,NULL,22),
('CONSULT:EDIT','问诊录入',2,NULL,23),
('BIOCHEM:VIEW','生化结果查看',2,NULL,30),
('BIOCHEM:EDIT','生化结果编辑',2,NULL,31),
('BLOOD:VIEW','血常规结果查看',2,NULL,40),
('BLOOD:EDIT','血常规结果编辑',2,NULL,41),
('URINE:VIEW','尿常规结果查看',2,NULL,50),
('URINE:EDIT','尿常规结果编辑',2,NULL,51),
('HBA1C:VIEW','糖化血红蛋白查看',2,NULL,60),
('HBA1C:EDIT','糖化血红蛋白编辑',2,NULL,61),
('DR:VIEW','DR报告查看',2,NULL,70),
('DR:EDIT','DR报告编辑',2,NULL,71),
('ULTRASOUND:VIEW','B超结果查看',2,NULL,72),
('ULTRASOUND:EDIT','B超结果编辑',2,NULL,73),
('ECG:VIEW','心电图结果查看',2,NULL,74),
('ECG:EDIT','心电图结果编辑',2,NULL,75),
('UPLOAD:EXEC','上传到公卫系统',2,NULL,80);

-- 角色
-- userType: 3=超级管理员, 4=卫生院管理员, 2=责任医生, 1=普通操作员
INSERT INTO `sys_role` (`id`,`role_code`,`role_name`,`description`) VALUES
(1, 'ROLE_ADMIN','超级管理员','拥有所有权限，管理全系统'),
(2, 'ROLE_BIOCHEM_DOCTOR','生化医生','负责生化检验项目'),
(3, 'ROLE_BLOOD_DOCTOR','血常规医生','负责血常规项目'),
(4, 'ROLE_URINE_DOCTOR','尿常规医生','负责尿常规项目，含下乡尿机'),
(5, 'ROLE_HBA1C_DOCTOR','糖化血红蛋白医生','负责糖化血红蛋白项目'),
(6, 'ROLE_DR_DOCTOR','DR放射医生','负责DR放射项目'),
(7, 'ROLE_NURSE','护士/操作员','负责生命体征、问诊录入'),
(8, 'ROLE_OPERATOR','数据操作员','扫码、录入、基础查询'),
(9, 'ROLE_HOSPITAL_ADMIN','卫生院管理员','管理本卫生院用户和医生，查看本院数据'),
(10,'ROLE_ULTRASOUND_DOCTOR','B超医生','负责B超检查项目'),
(11,'ROLE_ECG_DOCTOR','心电图医生','负责心电图检查项目');

-- 超级管理员权限（全部）
INSERT INTO `sys_role_permission` (`role_id`,`perm_code`)
SELECT 1, `perm_code` FROM `sys_permission`;

-- 卫生院管理员（本院用户管理+医生管理+查看数据）
INSERT INTO `sys_role_permission` (`role_id`,`perm_code`) VALUES
(9,'SYS:USER'),(9,'RESIDENT:VIEW'),(9,'ORDER:VIEW'),(9,'ORDER:CREATE'),
(9,'VITAL:VIEW'),(9,'SYS:DEVICE'),(9,'UPLOAD:EXEC');

-- 生化医生
INSERT INTO `sys_role_permission` (`role_id`,`perm_code`) VALUES
(2,'RESIDENT:VIEW'),(2,'ORDER:VIEW'),(2,'BIOCHEM:VIEW'),(2,'BIOCHEM:EDIT'),(2,'UPLOAD:EXEC');

-- 血常规医生
INSERT INTO `sys_role_permission` (`role_id`,`perm_code`) VALUES
(3,'RESIDENT:VIEW'),(3,'ORDER:VIEW'),(3,'BLOOD:VIEW'),(3,'BLOOD:EDIT'),(3,'UPLOAD:EXEC');

-- 尿常规医生
INSERT INTO `sys_role_permission` (`role_id`,`perm_code`) VALUES
(4,'RESIDENT:VIEW'),(4,'ORDER:VIEW'),(4,'URINE:VIEW'),(4,'URINE:EDIT'),(4,'UPLOAD:EXEC');

-- 糖化血红蛋白医生
INSERT INTO `sys_role_permission` (`role_id`,`perm_code`) VALUES
(5,'RESIDENT:VIEW'),(5,'ORDER:VIEW'),(5,'HBA1C:VIEW'),(5,'HBA1C:EDIT'),(5,'UPLOAD:EXEC');

-- DR医生
INSERT INTO `sys_role_permission` (`role_id`,`perm_code`) VALUES
(6,'RESIDENT:VIEW'),(6,'ORDER:VIEW'),(6,'DR:VIEW'),(6,'DR:EDIT'),(6,'UPLOAD:EXEC');

-- B超医生
INSERT INTO `sys_role_permission` (`role_id`,`perm_code`) VALUES
(10,'RESIDENT:VIEW'),(10,'ORDER:VIEW'),(10,'ULTRASOUND:VIEW'),(10,'ULTRASOUND:EDIT'),(10,'UPLOAD:EXEC');

-- 心电图医生
INSERT INTO `sys_role_permission` (`role_id`,`perm_code`) VALUES
(11,'RESIDENT:VIEW'),(11,'ORDER:VIEW'),(11,'ECG:VIEW'),(11,'ECG:EDIT'),(11,'UPLOAD:EXEC');

-- 护士
INSERT INTO `sys_role_permission` (`role_id`,`perm_code`) VALUES
(7,'RESIDENT:VIEW'),(7,'ORDER:VIEW'),(7,'ORDER:CREATE'),
(7,'VITAL:VIEW'),(7,'VITAL:EDIT'),(7,'CONSULT:VIEW'),(7,'CONSULT:EDIT');

-- 操作员
INSERT INTO `sys_role_permission` (`role_id`,`perm_code`) VALUES
(8,'RESIDENT:VIEW'),(8,'ORDER:VIEW'),(8,'ORDER:CREATE'),
(8,'VITAL:VIEW'),(8,'VITAL:EDIT');

-- ================================================================
-- 用户 (密码均为 hd2024 的BCrypt加密)
-- BCrypt of 'hd2024': $2a$10$N.zmdr9k7uOCQb376NoUnuTJ8iAt6Z5EHsM8lE9lBpwTTyigZGaFS
-- userType: 3=超级管理员, 4=卫生院管理员, 2=责任医生, 1=普通操作员
-- ================================================================

-- 超级管理员
INSERT INTO `sys_user` (`id`,`username`,`password`,`real_name`,`phone`,`dept_id`,`user_type`,`status`) VALUES
(1, 'admin', '$2a$10$N.zmdr9k7uOCQb376NoUnuTJ8iAt6Z5EHsM8lE9lBpwTTyigZGaFS','超级管理员','13800000001',1,3,1);

-- 21家卫生院管理员 (userType=4, dept_id对应各卫生院)
INSERT INTO `sys_user` (`id`,`username`,`password`,`real_name`,`phone`,`dept_id`,`user_type`,`status`) VALUES
(100,'zg_admin',  '$2a$10$N.zmdr9k7uOCQb376NoUnuTJ8iAt6Z5EHsM8lE9lBpwTTyigZGaFS','增光卫生院管理员','13900100001',10,4,1),
(101,'dl_admin',  '$2a$10$N.zmdr9k7uOCQb376NoUnuTJ8iAt6Z5EHsM8lE9lBpwTTyigZGaFS','大岭卫生院管理员','13900100002',11,4,1),
(102,'bh_admin',  '$2a$10$N.zmdr9k7uOCQb376NoUnuTJ8iAt6Z5EHsM8lE9lBpwTTyigZGaFS','白花卫生院管理员','13900100003',12,4,1),
(103,'lh_admin',  '$2a$10$N.zmdr9k7uOCQb376NoUnuTJ8iAt6Z5EHsM8lE9lBpwTTyigZGaFS','梁化卫生院管理员','13900100004',13,4,1),
(104,'rs_admin',  '$2a$10$N.zmdr9k7uOCQb376NoUnuTJ8iAt6Z5EHsM8lE9lBpwTTyigZGaFS','稔山卫生院管理员','13900100005',14,4,1),
(105,'ty_admin',  '$2a$10$N.zmdr9k7uOCQb376NoUnuTJ8iAt6Z5EHsM8lE9lBpwTTyigZGaFS','铁涌卫生院管理员','13900100006',15,4,1),
(106,'ph_admin',  '$2a$10$N.zmdr9k7uOCQb376NoUnuTJ8iAt6Z5EHsM8lE9lBpwTTyigZGaFS','平海卫生院管理员','13900100007',16,4,1),
(107,'xl_admin',  '$2a$10$N.zmdr9k7uOCQb376NoUnuTJ8iAt6Z5EHsM8lE9lBpwTTyigZGaFS','巽寮卫生院管理员','13900100008',17,4,1),
(108,'gk_admin',  '$2a$10$N.zmdr9k7uOCQb376NoUnuTJ8iAt6Z5EHsM8lE9lBpwTTyigZGaFS','港口卫生院管理员','13900100009',18,4,1),
(109,'ps_admin',  '$2a$10$N.zmdr9k7uOCQb376NoUnuTJ8iAt6Z5EHsM8lE9lBpwTTyigZGaFS','平山社区管理员','13900100010',19,4,1),
(110,'jl_admin',  '$2a$10$N.zmdr9k7uOCQb376NoUnuTJ8iAt6Z5EHsM8lE9lBpwTTyigZGaFS','吉隆卫生院管理员','13900100011',20,4,1),
(111,'hb_admin',  '$2a$10$N.zmdr9k7uOCQb376NoUnuTJ8iAt6Z5EHsM8lE9lBpwTTyigZGaFS','黄埠卫生院管理员','13900100012',21,4,1),
(112,'yz_admin',  '$2a$10$N.zmdr9k7uOCQb376NoUnuTJ8iAt6Z5EHsM8lE9lBpwTTyigZGaFS','盐洲卫生院管理员','13900100013',22,4,1),
(113,'dz_admin',  '$2a$10$N.zmdr9k7uOCQb376NoUnuTJ8iAt6Z5EHsM8lE9lBpwTTyigZGaFS','多祝卫生院管理员','13900100014',23,4,1),
(114,'sk_admin',  '$2a$10$N.zmdr9k7uOCQb376NoUnuTJ8iAt6Z5EHsM8lE9lBpwTTyigZGaFS','松坑卫生院管理员','13900100015',24,4,1),
(115,'ad_admin',  '$2a$10$N.zmdr9k7uOCQb376NoUnuTJ8iAt6Z5EHsM8lE9lBpwTTyigZGaFS','安墩卫生院管理员','13900100016',25,4,1),
(116,'gt_admin',  '$2a$10$N.zmdr9k7uOCQb376NoUnuTJ8iAt6Z5EHsM8lE9lBpwTTyigZGaFS','高潭卫生院管理员','13900100017',26,4,1),
(117,'bk_admin',  '$2a$10$N.zmdr9k7uOCQb376NoUnuTJ8iAt6Z5EHsM8lE9lBpwTTyigZGaFS','宝口卫生院管理员','13900100018',27,4,1),
(118,'ms_admin',  '$2a$10$N.zmdr9k7uOCQb376NoUnuTJ8iAt6Z5EHsM8lE9lBpwTTyigZGaFS','马山卫生院管理员','13900100019',28,4,1),
(119,'bpz_admin', '$2a$10$N.zmdr9k7uOCQb376NoUnuTJ8iAt6Z5EHsM8lE9lBpwTTyigZGaFS','白盆珠卫生院管理员','13900100020',29,4,1),
(120,'xa_admin',  '$2a$10$N.zmdr9k7uOCQb376NoUnuTJ8iAt6Z5EHsM8lE9lBpwTTyigZGaFS','新庵卫生院管理员','13900100021',30,4,1);

-- 安墩卫生院(dept_id=25)示例责任医生 (userType=2, 7个专业)
INSERT INTO `sys_user` (`id`,`username`,`password`,`real_name`,`phone`,`dept_id`,`user_type`,`status`) VALUES
(200,'ad_biochem', '$2a$10$N.zmdr9k7uOCQb376NoUnuTJ8iAt6Z5EHsM8lE9lBpwTTyigZGaFS','安墩-生化医生','13900200001',25,2,1),
(201,'ad_blood',   '$2a$10$N.zmdr9k7uOCQb376NoUnuTJ8iAt6Z5EHsM8lE9lBpwTTyigZGaFS','安墩-血常规医生','13900200002',25,2,1),
(202,'ad_urine',   '$2a$10$N.zmdr9k7uOCQb376NoUnuTJ8iAt6Z5EHsM8lE9lBpwTTyigZGaFS','安墩-尿常规医生','13900200003',25,2,1),
(203,'ad_hba1c',   '$2a$10$N.zmdr9k7uOCQb376NoUnuTJ8iAt6Z5EHsM8lE9lBpwTTyigZGaFS','安墩-糖化医生','13900200004',25,2,1),
(204,'ad_dr',      '$2a$10$N.zmdr9k7uOCQb376NoUnuTJ8iAt6Z5EHsM8lE9lBpwTTyigZGaFS','安墩-DR放射医生','13900200005',25,2,1),
(205,'ad_us',      '$2a$10$N.zmdr9k7uOCQb376NoUnuTJ8iAt6Z5EHsM8lE9lBpwTTyigZGaFS','安墩-B超医生','13900200006',25,2,1),
(206,'ad_ecg',     '$2a$10$N.zmdr9k7uOCQb376NoUnuTJ8iAt6Z5EHsM8lE9lBpwTTyigZGaFS','安墩-心电图医生','13900200007',25,2,1);

-- 用户角色关联
-- 超级管理员
INSERT INTO `sys_user_role` (`user_id`,`role_id`) VALUES (1,1);
-- 21家卫生院管理员 → ROLE_HOSPITAL_ADMIN(role_id=9)
INSERT INTO `sys_user_role` (`user_id`,`role_id`) VALUES
(100,9),(101,9),(102,9),(103,9),(104,9),(105,9),(106,9),(107,9),(108,9),(109,9),
(110,9),(111,9),(112,9),(113,9),(114,9),(115,9),(116,9),(117,9),(118,9),(119,9),(120,9);
-- 安墩卫生院责任医生 → 各专业角色
INSERT INTO `sys_user_role` (`user_id`,`role_id`) VALUES
(200,2),(201,3),(202,4),(203,5),(204,6),(205,10),(206,11);

-- 设备信息（所有设备）
INSERT INTO `device_info`
(`id`,`device_code`,`device_name`,`device_model`,`manufacturer`,`category`,`comm_type`,`comm_host`,`comm_port`,`protocol`,`dept_id`,`dept_name`,`status`)
VALUES
(1,'DEV-URIT330','优利特尿常规分析仪','URIT-330','优利特','URINE','TCP','192.168.1.101',7100,'ASTM',2,'检验科','OFFLINE'),
(2,'DEV-JCH480','聚创全自动生化分析仪','JCH-S480','聚创','BIOCHEM','TCP','192.168.1.102',7100,'ASTM',2,'检验科','OFFLINE'),
(3,'DEV-BH5380','优利特全自动血细胞分析仪','BH-5380CRP','优利特','BLOOD','TCP','192.168.1.103',7100,'ASTM',2,'检验科','OFFLINE'),
(4,'DEV-BT400L','聚创全自动血细胞分析仪','BT-400L','聚创','BLOOD','TCP','192.168.1.104',7100,'ASTM',2,'检验科','OFFLINE'),
(5,'DEV-BC2600','迈瑞血细胞分析仪','BC-2600','迈瑞','BLOOD','TCP','192.168.1.105',7100,'ASTM',2,'检验科','OFFLINE'),
(6,'DEV-BS330','迈瑞全自动生化分析仪','BS-330','迈瑞','BIOCHEM','TCP','192.168.1.106',7100,'ASTM',2,'检验科','OFFLINE'),
(7,'DEV-BS830','万瑞全自动生化分析仪','BS-830','万瑞','BIOCHEM','TCP','192.168.1.107',7100,'ASTM',2,'检验科','OFFLINE'),
(8,'DEV-DS580I','理邦全自动血细胞分析仪','DS-580i','理邦','BLOOD','TCP','192.168.1.108',7100,'ASTM',2,'检验科','OFFLINE'),
(9,'DEV-URIT560','优利特尿液分析仪','URIT-560','优利特','URINE','TCP','192.168.1.109',7100,'ASTM',2,'检验科','OFFLINE'),
(10,'DEV-BC760CS','迈瑞五分类血细胞分析仪','BC-760CS','迈瑞','BLOOD','TCP','192.168.1.110',7100,'ASTM',2,'检验科','OFFLINE'),
(11,'DEV-LD600','雷诺华糖化血红蛋白仪','LD-600','LABNOVATION','HBA1C','TCP','192.168.1.111',7100,'ASTM',2,'检验科','OFFLINE');

-- 字典数据
INSERT INTO `sys_dict` (`dict_type`,`dict_name`) VALUES
('check_result_flag','检验结果标志'),
('device_category','设备类型'),
('device_status','设备状态'),
('order_status','体检单状态'),
('dr_status','DR状态'),
('upload_status','上传状态');

INSERT INTO `sys_dict_item` (`dict_type`,`item_value`,`item_label`,`sort`) VALUES
('check_result_flag','H','偏高',1),
('check_result_flag','L','偏低',2),
('check_result_flag','N','正常',3),
('check_result_flag','A','异常',4),
('device_category','BLOOD','血常规',1),
('device_category','BIOCHEM','生化',2),
('device_category','URINE','尿常规',3),
('device_category','HBA1C','糖化血红蛋白',4),
('device_category','DR','放射DR',5),
('device_status','ONLINE','在线',1),
('device_status','OFFLINE','离线',2),
('device_status','ERROR','故障',3),
('order_status','PENDING','待检查',1),
('order_status','IN_PROGRESS','检查中',2),
('order_status','COMPLETED','已完成',3),
('order_status','UPLOADED','已上传',4),
('dr_status','PENDING','待检查',1),
('dr_status','SCANNED','已扫码',2),
('dr_status','REPORTED','已出报告',3),
('dr_status','UPLOADED','已上传',4),
('upload_status','0','未上传',1),
('upload_status','1','已上传',2);

-- 测试居民数据
INSERT INTO `resident` (`id_card`,`name`,`gender`,`birth_date`,`age`,`phone`,`address`,`village_name`,`township`) VALUES
('441300199001011234','张三',1,'1990-01-01',35,'13900001001','惠东县平山镇XX村1号','XX村','平山镇'),
('441300198502021235','李四',2,'1985-02-02',40,'13900001002','惠东县平山镇XX村2号','XX村','平山镇'),
('441300197003031236','王五',1,'1970-03-03',55,'13900001003','惠东县多祝镇YY村3号','YY村','多祝镇');

-- 测试体检单（含条码）
INSERT INTO `check_order` (`order_no`,`resident_id`,`resident_name`,`id_card`,`check_year`,`check_date`,`team_name`,`location`,`status`) VALUES
('HD2025031400001',1,'张三','441300199001011234',2025,'2025-03-14','公卫体检队A组','平山镇卫生院','IN_PROGRESS'),
('HD2025031400002',2,'李四','441300198502021235',2025,'2025-03-14','公卫体检队A组','平山镇卫生院','PENDING'),
('HD2025031400003',3,'王五','441300197003031236',2025,'2025-03-14','公卫体检队B组','多祝镇卫生院','PENDING');
