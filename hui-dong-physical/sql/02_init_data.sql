-- ============================================================
-- 初始化数据 - 设备信息
-- ============================================================

USE physical_db;

INSERT INTO t_device (id, device_code, device_name, device_type, device_model, manufacturer,
                      connect_type, location, enabled, create_time, update_time, deleted)
VALUES
-- 下乡尿机（优利特）
(1001, 'URINE-FIELD-001', '下乡尿机01', 'URINE', 'UriTek-300', '优利特', 'TCP', 1, 1, NOW(), NOW(), 0),

-- 院内设备
(1002, 'BIO-INHOS-001',   '院内生化仪', 'BIO',   'BS-240', '迈瑞', 'HL7',    2, 1, NOW(), NOW(), 0),
(1003, 'CBC-INHOS-001',   '院内血常规仪', 'CBC', 'BC-5390', '万瑞', 'HL7',   2, 1, NOW(), NOW(), 0),
(1004, 'HBA1C-INHOS-001', '院内糖化血红蛋白仪', 'HBA1C', 'HA-8380', '万瑞', 'HL7', 2, 1, NOW(), NOW(), 0),
(1005, 'URINE-INHOS-001', '院内尿机', 'URINE',  'UriTek-500', '优利特', 'HL7', 2, 1, NOW(), NOW(), 0);
