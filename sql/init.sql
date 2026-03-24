-- ============================================================
-- 惠东县区域公卫体检集中系统 - 数据库初始化脚本
-- DB: physical_health  charset: utf8mb4_unicode_ci
-- Version: 2.0  (2026-03)
-- ============================================================

CREATE DATABASE IF NOT EXISTS physical_health DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE physical_health;

-- ============================================================
-- 1. 居民信息表
-- ============================================================
CREATE TABLE IF NOT EXISTS `physical_resident` (
    `id`                 BIGINT        AUTO_INCREMENT PRIMARY KEY COMMENT '主键',
    `id_card`            VARCHAR(18)   NOT NULL                   COMMENT '居民身份证号（唯一）',
    `name`               VARCHAR(50)   NOT NULL                   COMMENT '居民姓名',
    `gender`             TINYINT       NOT NULL DEFAULT 1         COMMENT '性别：1-男，2-女',
    `birth_date`         DATE                                     COMMENT '出生日期',
    `phone`              VARCHAR(20)                              COMMENT '手机号',
    `address`            VARCHAR(200)                             COMMENT '家庭地址',
    `village`            VARCHAR(50)                              COMMENT '所属村/社区',
    `town`               VARCHAR(50)                              COMMENT '所属乡镇',
    `county_resident_id` VARCHAR(50)                              COMMENT '县域居民ID（县级系统ID）',
    `status`             TINYINT       DEFAULT 1                  COMMENT '状态：1-正常，0-禁用',
    `create_time`        DATETIME      DEFAULT CURRENT_TIMESTAMP  COMMENT '创建时间',
    `update_time`        DATETIME      DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `deleted`            TINYINT       DEFAULT 0                  COMMENT '逻辑删除：0-正常，1-已删除',
    UNIQUE KEY `uk_id_card`          (`id_card`),
    KEY        `idx_village`         (`village`),
    KEY        `idx_town`            (`town`),
    KEY        `idx_county_resident` (`county_resident_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='居民信息表';

-- ============================================================
-- 2. 体检记录表
-- ============================================================
CREATE TABLE IF NOT EXISTS `physical_record` (
    `id`                BIGINT        AUTO_INCREMENT PRIMARY KEY COMMENT '主键',
    `resident_id`       BIGINT        NOT NULL                   COMMENT '居民ID',
    `exam_date`         DATE          NOT NULL                   COMMENT '体检日期',
    `batch_no`          VARCHAR(30)                              COMMENT '体检批次号',
    `org_name`          VARCHAR(100)                             COMMENT '组织单位（乡镇/村）',
    `weight`            DECIMAL(5,1)                             COMMENT '体重(kg)',
    `height`            DECIMAL(5,1)                             COMMENT '身高(cm)',
    `bmi`               DECIMAL(5,2)                             COMMENT 'BMI',
    `systolic_bp`       SMALLINT                                 COMMENT '收缩压(mmHg)',
    `diastolic_bp`      SMALLINT                                 COMMENT '舒张压(mmHg)',
    `sync_status`       TINYINT       DEFAULT 0                  COMMENT '同步状态：0-未同步，1-已同步，2-同步失败',
    `county_physical_id` VARCHAR(50)                             COMMENT '县域体检ID',
    `status`            TINYINT       DEFAULT 1                  COMMENT '状态：1-进行中，2-已完成，3-已取消',
    `operator`          VARCHAR(50)                              COMMENT '录入操作员（doc_id）',
    `create_time`       DATETIME      DEFAULT CURRENT_TIMESTAMP  COMMENT '创建时间',
    `update_time`       DATETIME      DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `deleted`           TINYINT       DEFAULT 0                  COMMENT '逻辑删除',
    KEY `idx_resident_id`  (`resident_id`),
    KEY `idx_batch_no`     (`batch_no`),
    KEY `idx_exam_date`    (`exam_date`),
    KEY `idx_sync_status`  (`sync_status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='体检记录表';

-- ============================================================
-- 3. 检验结果表（生化/血常规/糖化/尿常规统一存储）
--    ON DUPLICATE KEY UPDATE 依赖 uk_physical_item_project 唯一索引
-- ============================================================
CREATE TABLE IF NOT EXISTS `physical_lab_result` (
    `id`            BIGINT        AUTO_INCREMENT PRIMARY KEY COMMENT '主键',
    `physical_id`   BIGINT        NOT NULL                   COMMENT '关联体检记录ID',
    `resident_id`   BIGINT        NOT NULL                   COMMENT '居民ID',
    `project_code`  VARCHAR(20)   NOT NULL                   COMMENT '项目编码：BIOCHEM/CBC/HBA1C/URINE',
    `project_name`  VARCHAR(50)                              COMMENT '项目名称',
    `item_code`     VARCHAR(30)   NOT NULL                   COMMENT '检验指标编码（如 GLU/CHOL）',
    `item_name`     VARCHAR(50)                              COMMENT '检验指标名称',
    `result_value`  VARCHAR(50)                              COMMENT '检验结果值',
    `result_num`    DECIMAL(12,4)                            COMMENT '结果数值（用于异常比较）',
    `unit`          VARCHAR(20)                              COMMENT '单位',
    `ref_low`       DECIMAL(12,4)                            COMMENT '参考范围下限',
    `ref_high`      DECIMAL(12,4)                            COMMENT '参考范围上限',
    `abnormal_flag` VARCHAR(5)                               COMMENT '异常标志：N-正常，L-偏低，H-偏高，C-危急',
    `device_code`   VARCHAR(30)                              COMMENT '检验仪器编号',
    `operator`      VARCHAR(30)                              COMMENT '操作员',
    `exam_time`     DATETIME                                 COMMENT '检验时间',
    `sync_status`   TINYINT       DEFAULT 0                  COMMENT '同步状态',
    `status`        TINYINT       DEFAULT 1                  COMMENT '状态',
    `create_time`   DATETIME      DEFAULT CURRENT_TIMESTAMP  COMMENT '创建时间',
    `update_time`   DATETIME      DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `deleted`       TINYINT       DEFAULT 0                  COMMENT '逻辑删除',
    -- 唯一索引：同一体检单、同一项目下每个指标只允许一条记录
    -- batchInsertOrUpdate 的 ON DUPLICATE KEY UPDATE 依赖此索引
    UNIQUE KEY `uk_physical_item_project` (`physical_id`, `project_code`, `item_code`),
    KEY        `idx_resident_id`          (`resident_id`),
    KEY        `idx_sync_status`          (`sync_status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='检验结果表（生化/血常规/糖化/尿常规）';

-- ============================================================
-- 4. 尿常规检验结果表（优利特尿机专用，含原始数据）
-- ============================================================
CREATE TABLE IF NOT EXISTS `physical_urine_result` (
    `id`               BIGINT        AUTO_INCREMENT PRIMARY KEY COMMENT '主键',
    `physical_id`      BIGINT                                   COMMENT '关联体检记录ID',
    `resident_id`      BIGINT                                   COMMENT '居民ID',
    `device_id`        VARCHAR(30)                              COMMENT '设备ID（优利特尿机SN）',
    `barcode`          VARCHAR(30)   NOT NULL                   COMMENT '标本条码（唯一）',
    `color`            VARCHAR(20)                              COMMENT '颜色',
    `clarity`          VARCHAR(20)                              COMMENT '透明度',
    `specific_gravity` VARCHAR(20)                              COMMENT '比重',
    `ph`               VARCHAR(10)                              COMMENT 'pH',
    `leu`              VARCHAR(20)                              COMMENT '白细胞 LEU',
    `nit`              VARCHAR(20)                              COMMENT '亚硝酸盐 NIT',
    `pro`              VARCHAR(20)                              COMMENT '尿蛋白 PRO',
    `glu`              VARCHAR(20)                              COMMENT '葡萄糖 GLU',
    `ket`              VARCHAR(20)                              COMMENT '酮体 KET',
    `bil`              VARCHAR(20)                              COMMENT '胆红素 BIL',
    `uro`              VARCHAR(20)                              COMMENT '尿胆原 URO',
    `ery`              VARCHAR(20)                              COMMENT '红细胞 ERY',
    `bld`              VARCHAR(20)                              COMMENT '隐血 BLD',
    `vc`               VARCHAR(20)                              COMMENT '维生素C VC',
    `malb`             VARCHAR(20)                              COMMENT '微白蛋白 mALB',
    `raw_data`         TEXT                                     COMMENT '原始JSON/ASTM报文',
    `collect_time`     DATETIME                                 COMMENT '采集时间（下乡）',
    `upload_time`      DATETIME                                 COMMENT '上传时间（4G/5G）',
    `sync_status`      TINYINT       DEFAULT 0                  COMMENT '同步状态：0-未同步，1-已同步，2-失败',
    `status`           TINYINT       DEFAULT 1                  COMMENT '状态：1-正常，0-禁用',
    `create_time`      DATETIME      DEFAULT CURRENT_TIMESTAMP  COMMENT '创建时间',
    `update_time`      DATETIME      DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `deleted`          TINYINT       DEFAULT 0                  COMMENT '逻辑删除',
    UNIQUE KEY `uk_barcode`      (`barcode`),
    KEY        `idx_physical_id` (`physical_id`),
    KEY        `idx_resident_id` (`resident_id`),
    KEY        `idx_sync_status` (`sync_status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='尿常规检验结果表（优利特尿机）';

-- ============================================================
-- 5. 医生账号表（从县域公卫系统同步）
-- ============================================================
CREATE TABLE IF NOT EXISTS `physical_doctor` (
    `id`               BIGINT        AUTO_INCREMENT PRIMARY KEY COMMENT '主键',
    `doc_id`           VARCHAR(50)   NOT NULL                   COMMENT '县域医生ID（全局唯一）',
    `username`         VARCHAR(50)   NOT NULL                   COMMENT '登录用户名',
    `password`         VARCHAR(100)                             COMMENT '密码（BCrypt加密）',
    `name`             VARCHAR(50)   NOT NULL                   COMMENT '姓名',
    `phone`            VARCHAR(20)                              COMMENT '手机号',
    `dept`             VARCHAR(30)                              COMMENT '科室编码',
    `dept_name`        VARCHAR(50)                              COMMENT '科室名称',
    `title`            VARCHAR(30)                              COMMENT '职称',
    `mac_addresses`    VARCHAR(200)                             COMMENT '绑定MAC地址（逗号分隔，网页端防越权）',
    `last_login_time`  DATETIME                                 COMMENT '最后登录时间',
    `last_login_ip`    VARCHAR(50)                              COMMENT '最后登录IP/MAC',
    `status`           TINYINT       DEFAULT 1                  COMMENT '状态：1-正常，0-禁用',
    `county_synced`    TINYINT       DEFAULT 0                  COMMENT '是否从县域同步：1-是，0-否',
    `create_time`      DATETIME      DEFAULT CURRENT_TIMESTAMP  COMMENT '创建时间',
    `update_time`      DATETIME      DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `deleted`          TINYINT       DEFAULT 0                  COMMENT '逻辑删除',
    UNIQUE KEY `uk_doc_id`   (`doc_id`),
    UNIQUE KEY `uk_username` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='医生账号表';

-- ============================================================
-- 6. 医生项目权限表（细粒度：按项目+操作类型）
-- ============================================================
CREATE TABLE IF NOT EXISTS `physical_doc_permission` (
    `id`           BIGINT        AUTO_INCREMENT PRIMARY KEY COMMENT '主键',
    `doc_id`       VARCHAR(50)   NOT NULL                   COMMENT '医生ID（县域同步）',
    `doc_name`     VARCHAR(50)                              COMMENT '医生姓名',
    `dept`         VARCHAR(30)                              COMMENT '所属科室编码',
    `dept_name`    VARCHAR(50)                              COMMENT '所属科室名称',
    `project_code` VARCHAR(20)   NOT NULL                   COMMENT '项目编码（BIOCHEM/CBC/HBA1C/URINE/DR/BP/BODY）',
    `project_name` VARCHAR(100)                             COMMENT '项目名称',
    `operate_type` VARCHAR(20)   NOT NULL                   COMMENT '操作类型（QUERY/INPUT/AUDIT）',
    `scope`        VARCHAR(10)   DEFAULT 'ALL'              COMMENT '权限范围：ALL-全部，OWN-本人，ZONE-片区',
    `zone_codes`   VARCHAR(200)                             COMMENT '片区编码（scope=ZONE时有效，逗号分隔）',
    `status`       TINYINT       DEFAULT 1                  COMMENT '状态：1-有效，0-禁用',
    `granted_by`   VARCHAR(50)                              COMMENT '授权人docId',
    `create_time`  DATETIME      DEFAULT CURRENT_TIMESTAMP  COMMENT '授权时间',
    `update_time`  DATETIME      DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    -- 唯一约束：同一医生对同一项目同一操作类型只允许一条权限记录
    UNIQUE KEY `uk_doc_project_operate` (`doc_id`, `project_code`, `operate_type`),
    KEY        `idx_doc_id`             (`doc_id`),
    KEY        `idx_project_code`       (`project_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='医生项目权限表';

-- ============================================================
-- 7. DR检查记录表（DR闭环核心）
-- ============================================================
CREATE TABLE IF NOT EXISTS `physical_dr_record` (
    `id`              BIGINT        AUTO_INCREMENT PRIMARY KEY COMMENT '主键',
    `dr_code`         VARCHAR(50)   NOT NULL                   COMMENT 'DR条码（县域打印，全局唯一）',
    `resident_id`     BIGINT                                   COMMENT '居民ID',
    `resident_name`   VARCHAR(50)                              COMMENT '居民姓名',
    `id_card`         VARCHAR(18)                              COMMENT '居民身份证号',
    `physical_id`     BIGINT                                   COMMENT '关联体检单ID',
    `apply_no`        VARCHAR(50)                              COMMENT 'DR申请单号（县域生成）',
    `exam_part`       VARCHAR(50)                              COMMENT '检查部位（如：胸部正位）',
    `exam_doctor_id`  VARCHAR(50)                              COMMENT '检查医生ID',
    `exam_doctor`     VARCHAR(50)                              COMMENT '检查医生姓名',
    `exam_time`       DATETIME                                 COMMENT '检查时间',
    `dr_result`       VARCHAR(500)                             COMMENT 'DR结果描述',
    `conclusion`      VARCHAR(20)                              COMMENT 'DR结论：NORMAL/ABNORMAL/RECHECK',
    `image_path`      VARCHAR(200)                             COMMENT '影像文件路径（DICOM/JPEG）',
    `report_path`     VARCHAR(200)                             COMMENT '报告PDF路径',
    `status`          TINYINT       DEFAULT 0                  COMMENT '状态：0-待检查，1-检查中，2-已完成，3-已同步，4-已取消',
    `scan_operator`   VARCHAR(50)                              COMMENT '扫码操作员',
    `scan_time`       DATETIME                                 COMMENT '扫码时间',
    `sync_time`       DATETIME                                 COMMENT '同步县域时间',
    `remark`          VARCHAR(200)                             COMMENT '备注',
    `create_time`     DATETIME      DEFAULT CURRENT_TIMESTAMP  COMMENT '创建时间',
    `update_time`     DATETIME      DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `deleted`         TINYINT       DEFAULT 0                  COMMENT '逻辑删除',
    UNIQUE KEY `uk_dr_code`         (`dr_code`),
    KEY        `idx_resident_id`    (`resident_id`),
    KEY        `idx_physical_id`    (`physical_id`),
    KEY        `idx_status`         (`status`),
    KEY        `idx_exam_doctor_id` (`exam_doctor_id`),
    KEY        `idx_scan_time`      (`scan_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='DR检查记录表（DR闭环核心）';

-- ============================================================
-- 初始化管理员账号（密码：Admin@2024，BCrypt散列）
-- ============================================================
INSERT IGNORE INTO `physical_doctor`
    (`doc_id`, `username`, `password`, `name`, `dept`, `dept_name`, `status`, `county_synced`)
VALUES
    ('ADMIN001', 'admin',
     '$2a$10$N.zmdr9k7uOCQb376NoUnuTJ8iAt6Z5EHsM8lE9lBpwTkMTLTa0xm',
     '系统管理员', 'ADMIN', '系统管理', 1, 0);

-- ============================================================
-- 初始化管理员全量权限（7项目 × 3操作 共16条，血压/体重仅查询）
-- ============================================================
INSERT IGNORE INTO `physical_doc_permission`
    (`doc_id`, `doc_name`, `dept`, `dept_name`, `project_code`, `project_name`, `operate_type`, `scope`, `status`, `granted_by`)
VALUES
-- 生化 BIOCHEM
('ADMIN001','系统管理员','ADMIN','系统管理','BIOCHEM','生化检验','QUERY','ALL',1,'SYSTEM'),
('ADMIN001','系统管理员','ADMIN','系统管理','BIOCHEM','生化检验','INPUT','ALL',1,'SYSTEM'),
('ADMIN001','系统管理员','ADMIN','系统管理','BIOCHEM','生化检验','AUDIT','ALL',1,'SYSTEM'),
-- 血常规 CBC
('ADMIN001','系统管理员','ADMIN','系统管理','CBC',   '血常规',  'QUERY','ALL',1,'SYSTEM'),
('ADMIN001','系统管理员','ADMIN','系统管理','CBC',   '血常规',  'INPUT','ALL',1,'SYSTEM'),
('ADMIN001','系统管理员','ADMIN','系统管理','CBC',   '血常规',  'AUDIT','ALL',1,'SYSTEM'),
-- 糖化血红蛋白 HBA1C
('ADMIN001','系统管理员','ADMIN','系统管理','HBA1C','糖化血红蛋白','QUERY','ALL',1,'SYSTEM'),
('ADMIN001','系统管理员','ADMIN','系统管理','HBA1C','糖化血红蛋白','INPUT','ALL',1,'SYSTEM'),
('ADMIN001','系统管理员','ADMIN','系统管理','HBA1C','糖化血红蛋白','AUDIT','ALL',1,'SYSTEM'),
-- 尿常规 URINE
('ADMIN001','系统管理员','ADMIN','系统管理','URINE','尿常规',  'QUERY','ALL',1,'SYSTEM'),
('ADMIN001','系统管理员','ADMIN','系统管理','URINE','尿常规',  'INPUT','ALL',1,'SYSTEM'),
-- DR放射
('ADMIN001','系统管理员','ADMIN','系统管理','DR',   'DR放射',  'QUERY','ALL',1,'SYSTEM'),
('ADMIN001','系统管理员','ADMIN','系统管理','DR',   'DR放射',  'INPUT','ALL',1,'SYSTEM'),
('ADMIN001','系统管理员','ADMIN','系统管理','DR',   'DR放射',  'AUDIT','ALL',1,'SYSTEM'),
-- 血压（仅查询）
('ADMIN001','系统管理员','ADMIN','系统管理','BP',   '血压',    'QUERY','ALL',1,'SYSTEM'),
-- 体重身高（仅查询）
('ADMIN001','系统管理员','ADMIN','系统管理','BODY', '体重身高','QUERY','ALL',1,'SYSTEM');
