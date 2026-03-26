-- =====================================================================
-- 修复状态列类型：将 VARCHAR 状态字段迁移为 TINYINT（与 Java 实体一致）
-- 执行方式：在 MySQL 中运行本脚本
-- =====================================================================

-- 1. 修复 check_order.status
--    PENDING=0, IN_PROGRESS=1, COMPLETED=2, UPLOADED=3
UPDATE check_order SET status = '0' WHERE status = 'PENDING';
UPDATE check_order SET status = '1' WHERE status = 'IN_PROGRESS';
UPDATE check_order SET status = '2' WHERE status = 'COMPLETED';
UPDATE check_order SET status = '3' WHERE status = 'UPLOADED';
ALTER TABLE check_order MODIFY COLUMN status TINYINT NOT NULL DEFAULT 0 COMMENT '0=待体检,1=体检中,2=已完成,3=已上传';

-- 2. 修复 dr_order.status
--    PENDING=0, SCANNED=1, REPORTED=2, UPLOADED=3
UPDATE dr_order SET status = '0' WHERE status = 'PENDING';
UPDATE dr_order SET status = '1' WHERE status = 'SCANNED';
UPDATE dr_order SET status = '2' WHERE status = 'REPORTED';
UPDATE dr_order SET status = '3' WHERE status = 'UPLOADED';
ALTER TABLE dr_order MODIFY COLUMN status TINYINT NOT NULL DEFAULT 0 COMMENT '0=待扫码,1=已扫码,2=已出报告,3=已上传,4=已作废';

-- 3. 修复 device_info.status
--    OFFLINE=0, ONLINE=1, ERROR=2
UPDATE device_info SET status = '0' WHERE status = 'OFFLINE';
UPDATE device_info SET status = '1' WHERE status = 'ONLINE';
UPDATE device_info SET status = '2' WHERE status = 'ERROR';
ALTER TABLE device_info MODIFY COLUMN status TINYINT NOT NULL DEFAULT 0 COMMENT '0=离线,1=在线,2=故障';

-- 4. 修复 device_raw_data.process_status
--    PENDING=0, MATCHED=1, ERROR=2
UPDATE device_raw_data SET process_status = '0' WHERE process_status = 'PENDING';
UPDATE device_raw_data SET process_status = '1' WHERE process_status = 'MATCHED';
UPDATE device_raw_data SET process_status = '2' WHERE process_status = 'ERROR';
ALTER TABLE device_raw_data MODIFY COLUMN process_status TINYINT NOT NULL DEFAULT 0 COMMENT '0=待处理,1=已匹配,2=处理失败';

SELECT 'status 列类型修复完成' AS result;
