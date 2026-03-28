-- ========================================================
-- v3 设备数据对接扩展
-- 新增: 串口/文件模式设备配置、check_result表字段修复
-- 执行方式: source /path/to/v3_device_interface.sql
-- ========================================================

USE `hd_public_health`;

-- --------------------------------------------------------
-- 1. 修复 check_result 表字段（与entity对应）
-- --------------------------------------------------------
-- 注: 若列已存在此语句会报错，忽略即可
ALTER TABLE `check_result`
  ADD COLUMN IF NOT EXISTS `device_code`  VARCHAR(50)  DEFAULT NULL COMMENT '设备编码' AFTER `device_id`,
  ADD COLUMN IF NOT EXISTS `device_model` VARCHAR(100) DEFAULT NULL COMMENT '设备型号'  AFTER `device_code`,
  ADD COLUMN IF NOT EXISTS `data_source`  VARCHAR(20)  DEFAULT 'DEVICE' COMMENT 'DEVICE/MANUAL' AFTER `device_model`,
  ADD COLUMN IF NOT EXISTS `sample_id`    VARCHAR(50)  DEFAULT NULL COMMENT '样本号' AFTER `data_source`,
  ADD COLUMN IF NOT EXISTS `check_time`   DATETIME     DEFAULT NULL COMMENT '检验时间' AFTER `sample_id`,
  ADD COLUMN IF NOT EXISTS `upload_status` TINYINT     DEFAULT 0   COMMENT '0未上传 1已上传' AFTER `check_time`;

-- --------------------------------------------------------
-- 2. 修复 device_raw_data 表（添加patient_id/sample_id字段）
-- --------------------------------------------------------
ALTER TABLE `device_raw_data`
  ADD COLUMN IF NOT EXISTS `patient_id`  VARCHAR(50) DEFAULT NULL COMMENT '患者ID' AFTER `device_id`,
  ADD COLUMN IF NOT EXISTS `sample_id`   VARCHAR(50) DEFAULT NULL COMMENT '样本号'  AFTER `patient_id`;

-- --------------------------------------------------------
-- 3. 新增串口/文件模式设备配置
-- 将comm_type='TCP'改为'SERIAL'/'FILE'，comm_host改为COM口/目录路径
-- --------------------------------------------------------

-- 更新现有设备的 status 为数字类型（若fix_status_columns.sql已执行则忽略报错）
UPDATE `device_info` SET `status` = 0 WHERE `status` = 'OFFLINE' OR `status` IS NULL;
UPDATE `device_info` SET `status` = 1 WHERE `status` = 'ONLINE';
UPDATE `device_info` SET `status` = 2 WHERE `status` = 'ERROR';

-- 串口设备配置示例（根据实际COM口修改comm_host）
-- 说明：comm_type=SERIAL, comm_host=COM口名, baud_rate=波特率
-- 若设备已配置TCP模式，只需修改comm_type和comm_host即可切换

-- 优利特URIT-330 尿常规 (串口示例)
INSERT IGNORE INTO `device_info`
  (`device_code`,`device_name`,`device_model`,`manufacturer`,`category`,`comm_type`,`comm_host`,`baud_rate`,`protocol`,`dept_id`,`status`)
VALUES
  ('DEV-URIT330-S', '优利特尿常规分析仪(串口)', 'URIT-330',   '优利特', 'URINE',  'SERIAL', 'COM3', 9600, 'ASTM', 2, 0),
  ('DEV-BH5380-S',  '优利特血常规分析仪(串口)',  'BH-5380CRP', '优利特', 'BLOOD',  'SERIAL', 'COM4', 9600, 'ASTM', 2, 0),
  ('DEV-URIT560-S', '优利特尿常规分析仪560(串口)','URIT-560',  '优利特', 'URINE',  'SERIAL', 'COM5', 9600, 'ASTM', 2, 0),
  ('DEV-LD600-S',   '雷诺华糖化血红蛋白仪(串口)', 'LD-600',   '雷诺华', 'HBA1C',  'SERIAL', 'COM6', 9600, 'ASTM', 2, 0),
  ('DEV-DS580I-S',  '理邦血常规分析仪(串口)',     'DS-580i',  '理邦',   'BLOOD',  'SERIAL', 'COM7', 9600, 'ASTM', 2, 0);

-- 文件监控设备配置示例（根据实际LIS输出路径修改comm_host）
-- 说明：comm_type=FILE, comm_host=LIS文件输出目录路径
INSERT IGNORE INTO `device_info`
  (`device_code`,`device_name`,`device_model`,`manufacturer`,`category`,`comm_type`,`comm_host`,`protocol`,`dept_id`,`status`)
VALUES
  ('DEV-BS330-F',  '迈瑞全自动生化分析仪(文件)',  'BS-330', '迈瑞',   'BIOCHEM', 'FILE', 'C:\\LIS\\BS330',  'ASTM', 2, 0),
  ('DEV-BS830-F',  '万瑞全自动生化分析仪(文件)',  'BS-830', '万瑞',   'BIOCHEM', 'FILE', 'C:\\LIS\\BS830',  'ASTM', 2, 0);

-- --------------------------------------------------------
-- 4. 设备对接使用说明（注释形式）
-- --------------------------------------------------------
/*
  【TCP模式设备配置】（已在系统中配置）
  设备: 聚创JCH-S480、迈瑞BC2600、迈瑞BC-760CS 等
  配置: comm_type=TCP, comm_host=设备IP, comm_port=设备端口(默认7100)
  操作: 在设备上配置"LIS服务器IP"为本机IP，端口7100

  【串口模式设备配置】
  设备: 优利特URIT-330/560、BH-5380CRP、雷诺华LD-600、理邦DS-580i
  配置: comm_type=SERIAL, comm_host=COM口名(如COM3), baud_rate=9600
  操作: 用USB转RS232线连接设备与电脑，在系统管理>设备管理中修改配置

  【文件模式设备配置】
  设备: 迈瑞BS-330、万瑞BS-830
  配置: comm_type=FILE, comm_host=LIS文件输出目录(如 C:\LIS\BS330)
  操作: 在设备LIS设置中将输出路径指向上述目录，系统会自动检测并处理

  【公卫平台上传】
  在 application.yml 中配置:
    pubhealth.upload.enabled: true
    pubhealth.upload.url: <卫生局提供的接口地址>
    pubhealth.upload.api-key: <接入密钥>
    pubhealth.upload.hospital-code: <机构编码>
  或在界面中手动点击体检单的"上传"按钮
*/
