-- ========================================================
-- v2 机构管理扩展 - 区域地址、医生筛选配置、21家乡镇卫生院、新角色
-- 在MySQL命令行中执行: source /path/to/v2_org_management.sql
-- 注意: 部分ALTER TABLE若列已存在会报错，可忽略重复执行报错
-- ========================================================

USE `hd_public_health`;

-- --------------------------------------------------------
-- 1. 补充 sys_dept 表缺失字段
-- --------------------------------------------------------
ALTER TABLE `sys_dept`
  ADD COLUMN IF NOT EXISTS `dept_type`     TINYINT      DEFAULT 1    COMMENT '1=卫生院 2=村卫生室 3=社区卫生中心 9=其他' AFTER `dept_code`,
  ADD COLUMN IF NOT EXISTS `address`       VARCHAR(200) DEFAULT NULL  COMMENT '地址' AFTER `sort`,
  ADD COLUMN IF NOT EXISTS `contact_phone` VARCHAR(20)  DEFAULT NULL  COMMENT '联系电话' AFTER `address`;

-- --------------------------------------------------------
-- 2. 区域地址表
-- --------------------------------------------------------
CREATE TABLE IF NOT EXISTS `sys_area` (
  `id`          BIGINT       NOT NULL AUTO_INCREMENT COMMENT '区域ID',
  `area_name`   VARCHAR(100) NOT NULL                COMMENT '区域名称',
  `area_code`   VARCHAR(50)  DEFAULT NULL            COMMENT '区域编码',
  `parent_id`   BIGINT       DEFAULT 0               COMMENT '父区域ID，0表示顶级',
  `area_level`  TINYINT      DEFAULT 3               COMMENT '级别：1=市 2=区县 3=镇街道 4=村',
  `sort`        INT          DEFAULT 0               COMMENT '排序',
  `remark`      VARCHAR(200) DEFAULT NULL            COMMENT '备注',
  `status`      TINYINT      DEFAULT 1               COMMENT '1=启用 0=禁用',
  `create_time` DATETIME     DEFAULT CURRENT_TIMESTAMP,
  `update_time` DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `deleted`     TINYINT      DEFAULT 0               COMMENT '逻辑删除',
  PRIMARY KEY (`id`),
  KEY `idx_parent_id` (`parent_id`),
  KEY `idx_area_level` (`area_level`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='区域地址表';

-- --------------------------------------------------------
-- 3. 责任医生筛选条件配置表
-- --------------------------------------------------------
CREATE TABLE IF NOT EXISTS `sys_doctor_filter` (
  `id`             BIGINT       NOT NULL AUTO_INCREMENT COMMENT '配置ID',
  `filter_name`    VARCHAR(100) NOT NULL                COMMENT '筛选条件名称',
  `filter_field`   VARCHAR(50)  NOT NULL                COMMENT '对应字段名',
  `filter_type`    VARCHAR(20)  DEFAULT 'TEXT'          COMMENT '筛选类型：TEXT/SELECT/NUMBER',
  `filter_options` TEXT         DEFAULT NULL            COMMENT '选项列表，JSON格式（SELECT类型用）',
  `sort`           INT          DEFAULT 0               COMMENT '排序',
  `status`         TINYINT      DEFAULT 1               COMMENT '1=启用 0=禁用',
  `create_time`    DATETIME     DEFAULT CURRENT_TIMESTAMP,
  `update_time`    DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `deleted`        TINYINT      DEFAULT 0,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='责任医生筛选条件配置表';

-- --------------------------------------------------------
-- 4. 21家乡镇卫生院（基层医疗机构）
-- --------------------------------------------------------
INSERT IGNORE INTO `sys_dept` (`id`,`dept_name`,`dept_code`,`dept_type`,`parent_id`,`sort`,`status`) VALUES
(10, '增光卫生院',           'DEPT_ZG',  1, 0, 10, 1),
(11, '大岭卫生院',           'DEPT_DL',  1, 0, 11, 1),
(12, '白花卫生院',           'DEPT_BH',  1, 0, 12, 1),
(13, '梁化卫生院',           'DEPT_LH',  1, 0, 13, 1),
(14, '稔山卫生院',           'DEPT_RS',  1, 0, 14, 1),
(15, '铁涌卫生院',           'DEPT_TY',  1, 0, 15, 1),
(16, '平海卫生院',           'DEPT_PH',  1, 0, 16, 1),
(17, '巽寮卫生院',           'DEPT_XL',  1, 0, 17, 1),
(18, '港口卫生院',           'DEPT_GK',  1, 0, 18, 1),
(19, '平山社区卫生服务中心', 'DEPT_PS',  3, 0, 19, 1),
(20, '吉隆卫生院',           'DEPT_JL',  1, 0, 20, 1),
(21, '黄埠卫生院',           'DEPT_HB',  1, 0, 21, 1),
(22, '盐洲卫生院',           'DEPT_YZ',  1, 0, 22, 1),
(23, '多祝卫生院',           'DEPT_DZ',  1, 0, 23, 1),
(24, '松坑卫生院',           'DEPT_SK',  1, 0, 24, 1),
(25, '安墩卫生院',           'DEPT_AD',  1, 0, 25, 1),
(26, '高潭卫生院',           'DEPT_GT',  1, 0, 26, 1),
(27, '宝口卫生院',           'DEPT_BK',  1, 0, 27, 1),
(28, '马山卫生院',           'DEPT_MS',  1, 0, 28, 1),
(29, '白盆珠卫生院',         'DEPT_BPZ', 1, 0, 29, 1),
(30, '新庵卫生院',           'DEPT_XA',  1, 0, 30, 1);

-- --------------------------------------------------------
-- 5. 新增权限项
-- --------------------------------------------------------
INSERT IGNORE INTO `sys_permission` (`perm_code`,`perm_name`,`perm_type`,`parent_code`,`sort`) VALUES
('SYS:DEPT',           '机构管理',           2, 'SYS:ADMIN', 4),
('SYS:AREA',           '区域地址管理',        2, 'SYS:ADMIN', 5),
('SYS:DOCTOR_FILTER',  '医生筛选条件配置',    2, 'SYS:ADMIN', 6),
('SYS:PERM',           '权限管理',           2, 'SYS:ADMIN', 7),
('DOCTOR:VIEW',        '责任医生查询',        2, NULL, 90),
('LAB:VIEW',           '化验项目查看',        2, NULL, 91),
('LAB:EDIT',           '化验项目录入',        2, NULL, 92);

-- --------------------------------------------------------
-- 6. 三种新角色
-- --------------------------------------------------------
INSERT IGNORE INTO `sys_role` (`id`,`role_code`,`role_name`,`description`,`status`) VALUES
(9,  'ROLE_SUPER_ADMIN',  '超级管理员',         '惠东县区域公卫体检集中系统平台超级管理员，开放整个平台所有权限', 1),
(10, 'ROLE_CLINIC_ADMIN', '卫生院管理员',       '21家乡镇卫生院管理员，只能开放本卫生院权限', 1),
(11, 'ROLE_DOCTOR_LAB',   '院内责任医生',       '院内责任医生，只能开放化验项目权限', 1);

-- 超级管理员 - 全部权限
INSERT IGNORE INTO `sys_role_permission` (`role_id`,`perm_code`)
SELECT 9, `perm_code` FROM `sys_permission`;

-- 卫生院管理员 - 本院范围权限
INSERT IGNORE INTO `sys_role_permission` (`role_id`,`perm_code`) VALUES
(10,'RESIDENT:VIEW'),
(10,'ORDER:VIEW'),
(10,'ORDER:CREATE'),
(10,'VITAL:VIEW'),
(10,'VITAL:EDIT'),
(10,'CONSULT:VIEW'),
(10,'CONSULT:EDIT'),
(10,'DOCTOR:VIEW'),
(10,'LAB:VIEW');

-- 院内责任医生 - 仅化验权限
INSERT IGNORE INTO `sys_role_permission` (`role_id`,`perm_code`) VALUES
(11,'RESIDENT:VIEW'),
(11,'ORDER:VIEW'),
(11,'LAB:VIEW'),
(11,'LAB:EDIT'),
(11,'BIOCHEM:VIEW'),
(11,'BIOCHEM:EDIT'),
(11,'BLOOD:VIEW'),
(11,'BLOOD:EDIT'),
(11,'URINE:VIEW'),
(11,'URINE:EDIT'),
(11,'HBA1C:VIEW'),
(11,'HBA1C:EDIT');

-- --------------------------------------------------------
-- 7. 惠东县区域地址初始数据
-- --------------------------------------------------------
INSERT IGNORE INTO `sys_area` (`id`,`area_name`,`area_code`,`parent_id`,`area_level`,`sort`) VALUES
(1,  '惠东县',               'HUIDONG',    0,  2, 1),
(2,  '增光镇',               'ZG_TOWN',    1,  3, 1),
(3,  '大岭镇',               'DL_TOWN',    1,  3, 2),
(4,  '白花镇',               'BH_TOWN',    1,  3, 3),
(5,  '梁化镇',               'LH_TOWN',    1,  3, 4),
(6,  '稔山镇',               'RS_TOWN',    1,  3, 5),
(7,  '铁涌镇',               'TY_TOWN',    1,  3, 6),
(8,  '平海镇',               'PH_TOWN',    1,  3, 7),
(9,  '巽寮镇',               'XL_TOWN',    1,  3, 8),
(10, '港口镇',               'GK_TOWN',    1,  3, 9),
(11, '平山镇',               'PS_TOWN',    1,  3, 10),
(12, '吉隆镇',               'JL_TOWN',    1,  3, 11),
(13, '黄埠镇',               'HB_TOWN',    1,  3, 12),
(14, '盐洲镇',               'YZ_TOWN',    1,  3, 13),
(15, '多祝镇',               'DZ_TOWN',    1,  3, 14),
(16, '松坑镇',               'SK_TOWN',    1,  3, 15),
(17, '安墩镇',               'AD_TOWN',    1,  3, 16),
(18, '高潭镇',               'GT_TOWN',    1,  3, 17),
(19, '宝口镇',               'BK_TOWN',    1,  3, 18),
(20, '马山镇',               'MS_TOWN',    1,  3, 19),
(21, '白盆珠镇',             'BPZ_TOWN',   1,  3, 20),
(22, '新庵镇',               'XA_TOWN',    1,  3, 21);

-- --------------------------------------------------------
-- 8. 责任医生筛选条件初始配置
-- --------------------------------------------------------
INSERT IGNORE INTO `sys_doctor_filter` (`filter_name`,`filter_field`,`filter_type`,`filter_options`,`sort`) VALUES
('姓名',     'realName', 'TEXT',   NULL, 1),
('手机号',   'phone',    'TEXT',   NULL, 2),
('所属机构', 'deptId',   'SELECT', NULL, 3),
('状态',     'status',   'SELECT', '[{"label":"启用","value":1},{"label":"禁用","value":0}]', 4);
