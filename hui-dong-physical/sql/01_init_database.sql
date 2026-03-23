-- ============================================================
-- 惠东县区域公卫体检集中系统 - 数据库初始化脚本
-- 数据库: physical_db
-- MySQL版本: 8.0.39
-- ============================================================

CREATE DATABASE IF NOT EXISTS physical_db
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;

USE physical_db;

-- ============================================================
-- 1. 居民信息缓存表（从县域公卫平台同步）
-- ============================================================
CREATE TABLE IF NOT EXISTS t_resident (
    id             BIGINT       NOT NULL COMMENT '主键ID（雪花）',
    resident_code  VARCHAR(64)  NOT NULL COMMENT '居民编码（对应县域平台ID）',
    id_card        VARCHAR(18)  NOT NULL COMMENT '身份证号',
    name           VARCHAR(50)  NOT NULL COMMENT '姓名',
    gender         TINYINT      NOT NULL DEFAULT 1 COMMENT '性别 0=女 1=男',
    birth_date     VARCHAR(10)  COMMENT '出生日期 yyyy-MM-dd',
    phone          VARCHAR(20)  COMMENT '手机号',
    village        VARCHAR(100) COMMENT '所属村/社区',
    town           VARCHAR(100) COMMENT '所属乡镇',
    chronic_tags   JSON         COMMENT '慢病标签',
    enabled        TINYINT      NOT NULL DEFAULT 1 COMMENT '是否启用',
    create_time    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    create_by      VARCHAR(64)  COMMENT '创建人',
    update_by      VARCHAR(64)  COMMENT '更新人',
    deleted        TINYINT      NOT NULL DEFAULT 0 COMMENT '逻辑删除 0=未删除 1=已删除',
    PRIMARY KEY (id),
    UNIQUE KEY uk_resident_code (resident_code),
    UNIQUE KEY uk_id_card (id_card),
    KEY idx_name (name)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COMMENT = '居民信息缓存表';

-- ============================================================
-- 2. 体检主表
-- ============================================================
CREATE TABLE IF NOT EXISTS t_exam_record (
    id                 BIGINT       NOT NULL COMMENT '主键ID',
    exam_no            VARCHAR(32)  NOT NULL COMMENT '体检单号 PE+日期+序号',
    resident_id        BIGINT       NOT NULL COMMENT '居民ID',
    resident_code      VARCHAR(64)  NOT NULL COMMENT '居民编码',
    exam_type          TINYINT      NOT NULL DEFAULT 1 COMMENT '体检类型 1=下乡 2=院内',
    exam_date          DATE         NOT NULL COMMENT '体检日期',
    exam_location      VARCHAR(200) COMMENT '体检地点',
    exam_status        TINYINT      NOT NULL DEFAULT 0 COMMENT '体检状态 0=待体检 1=体检中 2=标本已采集 3=检验中 4=已完成 5=已取消',
    systolic_pressure  SMALLINT     COMMENT '收缩压 mmHg',
    diastolic_pressure SMALLINT     COMMENT '舒张压 mmHg',
    weight             DECIMAL(5,1) COMMENT '体重 kg',
    height             DECIMAL(5,1) COMMENT '身高 cm',
    bmi                DECIMAL(5,2) COMMENT 'BMI',
    inquiry_info       JSON         COMMENT '问诊信息',
    sync_status        TINYINT      NOT NULL DEFAULT 0 COMMENT '同步状态 0=待同步 1=已同步 2=失败',
    sync_time          DATETIME     COMMENT '同步时间',
    remark             VARCHAR(500) COMMENT '备注',
    create_time        DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time        DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    create_by          VARCHAR(64)  COMMENT '创建人',
    update_by          VARCHAR(64)  COMMENT '更新人',
    deleted            TINYINT      NOT NULL DEFAULT 0 COMMENT '逻辑删除',
    PRIMARY KEY (id),
    UNIQUE KEY uk_exam_no (exam_no),
    KEY idx_resident_id (resident_id),
    KEY idx_exam_date (exam_date),
    KEY idx_sync_status (sync_status, exam_status),
    KEY idx_resident_code (resident_code)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COMMENT = '体检主表';

-- ============================================================
-- 3. 标本表
-- ============================================================
CREATE TABLE IF NOT EXISTS t_specimen (
    id               BIGINT       NOT NULL COMMENT '主键ID',
    specimen_no      VARCHAR(32)  COMMENT '标本编号 SP+日期+序号',
    exam_record_id   BIGINT       COMMENT '体检单ID',
    resident_id      BIGINT       COMMENT '居民ID',
    specimen_type    TINYINT      COMMENT '标本类型 1=血液 2=尿液 3=糖化',
    collect_location TINYINT      COMMENT '采集地点 1=下乡 2=院内',
    collect_time     DATETIME     COMMENT '采集时间',
    collect_by       VARCHAR(64)  COMMENT '采集人',
    specimen_status  TINYINT      NOT NULL DEFAULT 0 COMMENT '状态 0=待检 1=检验中 2=已完成 3=作废',
    barcode_no       VARCHAR(64)  COMMENT '条码号（扫码枪）',
    remark           VARCHAR(500) COMMENT '备注',
    create_time      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_time      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    create_by        VARCHAR(64),
    update_by        VARCHAR(64),
    deleted          TINYINT      NOT NULL DEFAULT 0,
    PRIMARY KEY (id),
    KEY idx_exam_record_id (exam_record_id),
    KEY idx_barcode_no (barcode_no),
    KEY idx_resident_id (resident_id)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COMMENT = '标本表';

-- ============================================================
-- 4. 检验结果统一表（生化/血常规/糖化/尿常规）
-- ============================================================
CREATE TABLE IF NOT EXISTS t_lab_result (
    id              BIGINT       NOT NULL COMMENT '主键ID',
    specimen_id     BIGINT       COMMENT '标本ID',
    exam_record_id  BIGINT       NOT NULL COMMENT '体检单ID',
    resident_id     BIGINT       NOT NULL COMMENT '居民ID',
    lab_type        TINYINT      NOT NULL COMMENT '检验类型 1=生化 2=血常规 3=糖化 4=尿常规',
    device_code     VARCHAR(64)  COMMENT '设备编码',
    device_type     VARCHAR(32)  COMMENT '设备类型',
    item_code       VARCHAR(64)  COMMENT '检验项目代码（LOINC）',
    item_name       VARCHAR(100) COMMENT '检验项目名称',
    result_value    VARCHAR(100) COMMENT '结果值',
    unit            VARCHAR(50)  COMMENT '单位',
    reference_range VARCHAR(200) COMMENT '参考范围',
    result_flag     VARCHAR(10)  COMMENT '结果标志 N=正常 H=高 L=低',
    lab_time        DATETIME     COMMENT '检验时间',
    raw_hl7_message LONGTEXT     COMMENT '原始HL7报文',
    sync_status     TINYINT      NOT NULL DEFAULT 0 COMMENT '同步状态 0=待同步 1=已同步 2=失败',
    source_type     TINYINT      NOT NULL DEFAULT 2 COMMENT '来源 1=下乡 2=院内',
    create_time     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_time     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    create_by       VARCHAR(64),
    update_by       VARCHAR(64),
    deleted         TINYINT      NOT NULL DEFAULT 0,
    PRIMARY KEY (id),
    KEY idx_exam_record_id (exam_record_id),
    KEY idx_resident_id (resident_id),
    KEY idx_lab_type (lab_type),
    KEY idx_sync_status (sync_status),
    KEY idx_source_type (source_type)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COMMENT = '检验结果统一表';

-- ============================================================
-- 5. 设备信息表
-- ============================================================
CREATE TABLE IF NOT EXISTS t_device (
    id              BIGINT       NOT NULL COMMENT '主键ID',
    device_code     VARCHAR(64)  NOT NULL COMMENT '设备编码',
    device_name     VARCHAR(100) NOT NULL COMMENT '设备名称',
    device_type     VARCHAR(32)  NOT NULL COMMENT '设备类型',
    device_model    VARCHAR(100) COMMENT '设备型号',
    manufacturer    VARCHAR(100) COMMENT '厂商',
    connect_type    VARCHAR(20)  COMMENT '连接方式 SERIAL/TCP/HL7',
    ip_address      VARCHAR(50)  COMMENT 'IP地址',
    port            INT          COMMENT '端口',
    serial_port     VARCHAR(20)  COMMENT '串口号',
    location        TINYINT      NOT NULL DEFAULT 2 COMMENT '位置 1=下乡 2=院内',
    online_status   TINYINT      NOT NULL DEFAULT 0 COMMENT '在线状态 0=离线 1=在线',
    last_heartbeat  DATETIME     COMMENT '最后心跳时间',
    enabled         TINYINT      NOT NULL DEFAULT 1 COMMENT '是否启用',
    remark          VARCHAR(500) COMMENT '备注',
    create_time     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_time     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    create_by       VARCHAR(64),
    update_by       VARCHAR(64),
    deleted         TINYINT      NOT NULL DEFAULT 0,
    PRIMARY KEY (id),
    UNIQUE KEY uk_device_code (device_code),
    KEY idx_device_type (device_type),
    KEY idx_location (location)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COMMENT = '设备信息表';

-- ============================================================
-- 6. 上传日志表（下乡尿机4G/5G上传记录）
-- ============================================================
CREATE TABLE IF NOT EXISTS t_upload_log (
    id               BIGINT       NOT NULL COMMENT '主键ID',
    upload_id        VARCHAR(64)  NOT NULL COMMENT '客户端幂等上传ID',
    resident_id      BIGINT       COMMENT '居民ID',
    device_code      VARCHAR(64)  COMMENT '设备编码',
    upload_status    TINYINT      NOT NULL DEFAULT 0 COMMENT '状态 0=处理中 1=成功 2=失败',
    network_type     VARCHAR(20)  COMMENT '网络类型 4G/5G/WIFI',
    raw_data         LONGTEXT     COMMENT '原始数据',
    error_msg        VARCHAR(500) COMMENT '错误信息',
    create_time      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_time      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    create_by        VARCHAR(64),
    update_by        VARCHAR(64),
    deleted          TINYINT      NOT NULL DEFAULT 0,
    PRIMARY KEY (id),
    UNIQUE KEY uk_upload_id (upload_id),
    KEY idx_resident_id (resident_id),
    KEY idx_device_code (device_code)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COMMENT = '下乡尿机上传日志表';

-- ============================================================
-- 7. 同步日志表（上报县域公卫平台记录）
-- ============================================================
CREATE TABLE IF NOT EXISTS t_sync_log (
    id               BIGINT       NOT NULL COMMENT '主键ID',
    biz_type         VARCHAR(20)  NOT NULL COMMENT '业务类型 EXAM/LAB',
    biz_id           BIGINT       NOT NULL COMMENT '业务ID',
    resident_code    VARCHAR(64)  COMMENT '居民编码',
    sync_status      TINYINT      NOT NULL DEFAULT 0 COMMENT '同步状态 0=待上报 1=成功 2=失败 3=重试中 4=耗尽',
    retry_count      INT          NOT NULL DEFAULT 0 COMMENT '重试次数',
    last_sync_time   DATETIME     COMMENT '上次上报时间',
    next_retry_time  DATETIME     COMMENT '下次重试时间',
    request_body     LONGTEXT     COMMENT '上报请求体',
    response_body    TEXT         COMMENT '上报响应体',
    error_msg        VARCHAR(1000) COMMENT '错误信息',
    create_time      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_time      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    create_by        VARCHAR(64),
    update_by        VARCHAR(64),
    deleted          TINYINT      NOT NULL DEFAULT 0,
    PRIMARY KEY (id),
    KEY idx_biz (biz_type, biz_id),
    KEY idx_sync_status (sync_status),
    KEY idx_next_retry (next_retry_time, sync_status)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COMMENT = '同步上报日志表';
