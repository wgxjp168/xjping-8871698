-- 创建数据库
CREATE DATABASE IF NOT EXISTS physical_db DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE physical_db;

-- ----------------------------
-- 1. 公共基础表
-- ----------------------------
DROP TABLE IF EXISTS sys_dict;
CREATE TABLE sys_dict (
    id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    dict_code VARCHAR(50) NOT NULL COMMENT '字典编码',
    dict_name VARCHAR(100) NOT NULL COMMENT '字典名称',
    dict_value VARCHAR(255) COMMENT '字典值',
    sort INT DEFAULT 0 COMMENT '排序',
    status TINYINT DEFAULT 1 COMMENT '状态（1-正常，0-禁用）',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (id),
    UNIQUE KEY uk_dict_code (dict_code)
) ENGINE=InnoDB COMMENT '系统字典表';

DROP TABLE IF EXISTS sys_equipment;
CREATE TABLE sys_equipment (
    id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    equipment_code VARCHAR(50) NOT NULL COMMENT '设备编号',
    equipment_name VARCHAR(100) NOT NULL COMMENT '设备名称',
    equipment_type VARCHAR(50) NOT NULL COMMENT '设备类型（生化/血常规/糖化/尿机）',
    manufacturer VARCHAR(100) COMMENT '生产厂家',
    model VARCHAR(50) COMMENT '设备型号',
    ip_address VARCHAR(50) COMMENT 'IP地址',
    port INT COMMENT '端口号',
    protocol_type VARCHAR(20) DEFAULT 'HL7' COMMENT '协议类型',
    status TINYINT DEFAULT 1 COMMENT '状态',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_equipment_code (equipment_code)
) ENGINE=InnoDB COMMENT '设备信息表';

-- ----------------------------
-- 2. 居民与体检核心表
-- ----------------------------
DROP TABLE IF EXISTS physical_resident;
CREATE TABLE physical_resident (
    id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    archive_id VARCHAR(50) NOT NULL COMMENT '居民档案号（关联县域公卫）',
    id_card_no VARCHAR(18) NOT NULL COMMENT '身份证号码',
    name VARCHAR(50) NOT NULL COMMENT '姓名',
    gender TINYINT COMMENT '性别（1-男，2-女）',
    age INT COMMENT '年龄',
    phone VARCHAR(20) COMMENT '联系电话',
    address VARCHAR(255) COMMENT '家庭住址',
    nation VARCHAR(50) COMMENT '民族',
    marital_status VARCHAR(20) COMMENT '婚姻状况',
    occupation VARCHAR(50) COMMENT '职业',
    education VARCHAR(50) COMMENT '文化程度',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_id_card (id_card_no),
    UNIQUE KEY uk_archive_id (archive_id),
    KEY idx_name (name),
    KEY idx_phone (phone)
) ENGINE=InnoDB COMMENT '居民信息表';

DROP TABLE IF EXISTS physical_examination;
CREATE TABLE physical_examination (
    id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    physical_code VARCHAR(50) NOT NULL COMMENT '体检单号',
    resident_id BIGINT NOT NULL COMMENT '居民ID',
    archive_id VARCHAR(50) NOT NULL COMMENT '关联档案号',
    id_card_no VARCHAR(18) NOT NULL COMMENT '身份证号',
    exam_date DATE NOT NULL COMMENT '体检日期',
    exam_org VARCHAR(100) NOT NULL COMMENT '体检机构',
    examiner VARCHAR(50) COMMENT '体检医生',
    status TINYINT DEFAULT 1 COMMENT '状态（1-待检，2-体检中，3-已完成，4-已作废）',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_physical_code (physical_code),
    KEY idx_resident_id (resident_id),
    KEY idx_exam_date (exam_date),
    KEY idx_status (status)
) ENGINE=InnoDB COMMENT '体检主表';

-- ----------------------------
-- 3. 标本管理表
-- ----------------------------
DROP TABLE IF EXISTS physical_sample;
CREATE TABLE physical_sample (
    id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    sample_code VARCHAR(50) NOT NULL COMMENT '标本条码号',
    physical_id BIGINT NOT NULL COMMENT '体检单ID',
    physical_code VARCHAR(50) NOT NULL COMMENT '体检单号',
    resident_id BIGINT NOT NULL COMMENT '居民ID',
    id_card_no VARCHAR(18) NOT NULL COMMENT '身份证号',
    sample_type TINYINT NOT NULL COMMENT '标本类型（1-血液，2-尿液）',
    collect_time DATETIME NOT NULL COMMENT '采集时间',
    collect_org VARCHAR(100) NOT NULL COMMENT '采集机构',
    collector VARCHAR(50) NOT NULL COMMENT '采集人',
    status TINYINT DEFAULT 1 COMMENT '状态（1-已采集，2-已接收，3-化验中，4-已完成，5-已废弃）',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_sample_code (sample_code),
    KEY idx_physical_id (physical_id),
    KEY idx_resident_id (resident_id),
    KEY idx_collect_time (collect_time),
    KEY idx_status (status)
) ENGINE=InnoDB COMMENT '标本管理表';

-- ----------------------------
-- 4. 检验结果明细表（分表存储）
-- ----------------------------
DROP TABLE IF EXISTS physical_biochemistry_result;
CREATE TABLE physical_biochemistry_result (
    id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    sample_id BIGINT NOT NULL COMMENT '标本ID',
    sample_code VARCHAR(50) NOT NULL COMMENT '标本条码',
    physical_id BIGINT NOT NULL COMMENT '体检单ID',
    project_code VARCHAR(50) NOT NULL COMMENT '项目编码',
    project_name VARCHAR(100) NOT NULL COMMENT '项目名称',
    result_value VARCHAR(50) NOT NULL COMMENT '结果值',
    unit VARCHAR(20) COMMENT '单位',
    reference_range VARCHAR(100) COMMENT '参考范围',
    abnormal_flag TINYINT DEFAULT 0 COMMENT '异常标志（0-正常，1-异常）',
    equipment_id BIGINT COMMENT '检测设备ID',
    exam_time DATETIME NOT NULL COMMENT '检测时间',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_sample_id (sample_id),
    KEY idx_physical_id (physical_id),
    KEY idx_project_code (project_code),
    KEY idx_exam_time (exam_time)
) ENGINE=InnoDB COMMENT '生化检验结果表';

DROP TABLE IF EXISTS physical_cbc_result;
CREATE TABLE physical_cbc_result (
    id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    sample_id BIGINT NOT NULL COMMENT '标本ID',
    sample_code VARCHAR(50) NOT NULL COMMENT '标本条码',
    physical_id BIGINT NOT NULL COMMENT '体检单ID',
    project_code VARCHAR(50) NOT NULL COMMENT '项目编码',
    project_name VARCHAR(100) NOT NULL COMMENT '项目名称',
    result_value VARCHAR(50) NOT NULL COMMENT '结果值',
    unit VARCHAR(20) COMMENT '单位',
    reference_range VARCHAR(100) COMMENT '参考范围',
    abnormal_flag TINYINT DEFAULT 0 COMMENT '异常标志',
    equipment_id BIGINT COMMENT '检测设备ID',
    exam_time DATETIME NOT NULL COMMENT '检测时间',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_sample_id (sample_id),
    KEY idx_physical_id (physical_id),
    KEY idx_exam_time (exam_time)
) ENGINE=InnoDB COMMENT '血常规检验结果表';

DROP TABLE IF EXISTS physical_hba1c_result;
CREATE TABLE physical_hba1c_result (
    id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    sample_id BIGINT NOT NULL COMMENT '标本ID',
    sample_code VARCHAR(50) NOT NULL COMMENT '标本条码',
    physical_id BIGINT NOT NULL COMMENT '体检单ID',
    project_code VARCHAR(50) NOT NULL COMMENT '项目编码',
    project_name VARCHAR(100) NOT NULL COMMENT '项目名称',
    result_value VARCHAR(50) NOT NULL COMMENT '结果值',
    unit VARCHAR(20) COMMENT '单位',
    reference_range VARCHAR(100) COMMENT '参考范围',
    abnormal_flag TINYINT DEFAULT 0 COMMENT '异常标志',
    equipment_id BIGINT COMMENT '检测设备ID',
    exam_time DATETIME NOT NULL COMMENT '检测时间',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_sample_id (sample_id),
    KEY idx_physical_id (physical_id),
    KEY idx_exam_time (exam_time)
) ENGINE=InnoDB COMMENT '糖化血红蛋白检验结果表';

DROP TABLE IF EXISTS physical_urine_result;
CREATE TABLE physical_urine_result (
    id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    sample_id BIGINT NOT NULL COMMENT '标本ID',
    sample_code VARCHAR(50) NOT NULL COMMENT '标本条码',
    physical_id BIGINT NOT NULL COMMENT '体检单ID',
    project_code VARCHAR(50) NOT NULL COMMENT '项目编码',
    project_name VARCHAR(100) NOT NULL COMMENT '项目名称',
    result_value VARCHAR(50) NOT NULL COMMENT '结果值',
    unit VARCHAR(20) COMMENT '单位',
    reference_range VARCHAR(100) COMMENT '参考范围',
    abnormal_flag TINYINT DEFAULT 0 COMMENT '异常标志',
    equipment_id BIGINT COMMENT '检测设备ID',
    exam_time DATETIME NOT NULL COMMENT '检测时间',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_sample_id (sample_id),
    KEY idx_physical_id (physical_id),
    KEY idx_exam_time (exam_time)
) ENGINE=InnoDB COMMENT '尿常规检验结果表';

-- ----------------------------
-- 5. 同步日志表
-- ----------------------------
DROP TABLE IF EXISTS physical_sync_log;
CREATE TABLE physical_sync_log (
    id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    sync_code VARCHAR(50) NOT NULL COMMENT '同步流水号',
    business_type TINYINT NOT NULL COMMENT '业务类型（1-体检，2-生化，3-血常规，4-糖化，5-尿常规）',
    business_id BIGINT NOT NULL COMMENT '业务数据ID',
    sync_status TINYINT DEFAULT 0 COMMENT '同步状态（0-失败，1-成功，2-处理中）',
    request_data LONGTEXT COMMENT '请求参数',
    response_data LONGTEXT COMMENT '响应参数',
    error_msg TEXT COMMENT '错误信息',
    retry_count INT DEFAULT 0 COMMENT '重试次数',
    next_retry_time DATETIME COMMENT '下次重试时间',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_sync_code (sync_code),
    KEY idx_business_type (business_type),
    KEY idx_sync_status (sync_status),
    KEY idx_create_time (create_time)
) ENGINE=InnoDB COMMENT '数据同步日志表';

-- ----------------------------
-- 初始数据插入
-- ----------------------------
-- 插入设备初始数据
INSERT INTO sys_equipment (equipment_code, equipment_name, equipment_type, manufacturer, model, status) VALUES
('EQ-001', '迈瑞生化分析仪', '生化', '迈瑞医疗', 'BS-480', 1),
('EQ-002', '万瑞血常规分析仪', '血常规', '万瑞生物', 'BC-5000', 1),
('EQ-003', '万瑞糖化血红蛋白分析仪', '糖化', '万瑞生物', 'HA-8160', 1),
('EQ-004', '优利特尿机', '尿机', '优利特', 'URIT-180', 1);

-- 插入字典数据
INSERT INTO sys_dict (dict_code, dict_name, dict_value, sort) VALUES
('EXAM_STATUS', '体检状态', '[{"code":1,"name":"待检"},{"code":2,"name":"体检中"},{"code":3,"name":"已完成"},{"code":4,"name":"已作废"}]', 1),
('SAMPLE_TYPE', '标本类型', '[{"code":1,"name":"血液"},{"code":2,"name":"尿液"}]', 2),
('SAMPLE_STATUS', '标本状态', '[{"code":1,"name":"已采集"},{"code":2,"name":"已接收"},{"code":3,"name":"化验中"},{"code":4,"name":"已完成"},{"code":5,"name":"已废弃"}]', 3);
