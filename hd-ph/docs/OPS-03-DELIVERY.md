# 03 · 系统上线交付步骤

## 总体时间线

```
Week 1        Week 2        Week 3        Week 4        Week 5+
│             │             │             │             │
├── 验收测试 ──┼── 上线准备 ──┼── 切换上线 ──┼── 试运行 ───┼── 正式运营
│  UAT/SIT   │  数据迁移   │  灰度切换   │  双跑期     │  持续迭代
│  性能测试   │  培训       │  监控加强   │  问题修复   │
```

---

## 3.1 第一阶段：验收测试（W1，5个工作日）

### Day 1-2: 系统集成测试 (SIT)

**测试环境部署**

```bash
# 1. 拉取代码
git clone git@github.com:wgxjp168/xjping-8871698.git
cd xjping-8871698/hd-ph

# 2. 配置测试环境变量
cp .env.example .env
vim .env  # 填入测试数据库密码

# 3. 启动全量服务
docker-compose up -d

# 4. 初始化数据库
docker exec hd-mysql mysql -uroot -p"${MYSQL_ROOT_PASSWORD}" \
  < /opt/hd-ph/sql/hd_public_health.sql

# 5. 验证服务状态
docker-compose ps
curl http://localhost:9090/api/auth/health
curl http://localhost:8002/api/residents/health
curl http://localhost:8003/api/devices/health
curl http://localhost:8004/api/vital-signs/health
curl http://localhost:8005/api/dr-orders/health
```

**接口自动化测试**

```bash
# 运行Postman/Newman测试集合（测试覆盖所有API端点）
newman run hd-ph-api-tests.json \
  --environment test-env.json \
  --reporters cli,html \
  --reporter-html-export report.html
```

**核心测试用例清单**

| 模块 | 测试场景 | 预期结果 |
|------|---------|---------|
| 认证 | admin正确密码登录 | 返回token+权限列表 |
| 认证 | 错误密码登录 | 返回401错误信息 |
| 认证 | token过期请求 | Gateway拦截返回401 |
| 认证 | 登出后token访问 | Redis黑名单拦截 |
| 居民 | 新增居民（唯一身份证） | 成功插入 |
| 居民 | 重复身份证新增 | 返回业务错误 |
| 体检 | 创建体检单（自动生成单号） | 单号格式CK+日期+4位 |
| 体检 | 录入生命体征（自动计算BMI） | BMI=体重/(身高/100)² |
| 设备 | 模拟ASTM报文发送至TCP:7100 | 解析入库device_raw_data |
| DR | 创建申请单（生成条码号） | barcodeNo格式BC+时间戳 |
| DR | 扫码签到 | 状态0→1，记录scanTime |
| DR | 重复扫码 | 返回业务错误"已扫码" |
| 权限 | doctor01无法访问/api/users | Gateway返回403 |

### Day 3: 用户验收测试 (UAT)

**参与人员**: 各卫生院护士长1人、公卫科长1人、信息科员1人（共3人）

**验收脚本**（实际操作走查）

```
场景1: 居民建档
  操作: 新增居民 → 填写身份证/姓名/性别/联系方式/地址
  验收: 档案号自动生成，可检索查询

场景2: 体检单创建
  操作: 从居民档案页点击"建体检单" → 选类型 → 提交
  验收: 体检单号生成，状态"待体检"

场景3: 体征录入
  操作: 打开体检详情 → 录入身高体重血压 → 保存
  验收: BMI自动计算并显示，血压值显示正常/异常标记

场景4: 设备数据采集（联调）
  操作: 在真实设备上检测测试样本，触发ASTM上传
  验收: 系统检验结果页出现对应数据，项目名称/值/单位正确

场景5: DR扫码签到
  操作: 手机/扫码枪扫描测试条码 → 确认签到
  验收: 状态变为"已签到"，显示签到时间

场景6: DR报告提交
  操作: 填写影像所见/诊断意见 → 提交
  验收: 申请单状态变为"已完成"

场景7: 退出登录
  操作: 点击退出
  验收: token失效，再次访问跳转登录页
```

### Day 4: 性能测试

```bash
# 使用 JMeter 或 k6 进行压测
# 目标: 50并发用户，持续10分钟，P95响应时间 < 500ms

k6 run --vus 50 --duration 10m performance-test.js

# 关键接口压测目标
# POST /api/auth/login    ≤ 300ms P95
# GET  /api/residents     ≤ 200ms P95
# GET  /api/check-orders  ≤ 300ms P95
# POST /api/vital-signs   ≤ 200ms P95
```

### Day 5: 安全测试

```
□ SQL注入扫描（所有带参数接口）
□ XSS测试（所有输入框）
□ 弱口令扫描（默认账号需改密码）
□ 未授权访问测试（不带token访问所有接口）
□ 越权测试（A用户访问B用户数据）
□ HTTPS证书有效性验证
□ 敏感信息泄露检查（接口不返回password字段）
```

---

## 3.2 第二阶段：上线准备（W2，5个工作日）

### Day 1-2: 生产环境准备

```bash
# 生产服务器初始化
# 1. 操作系统加固
yum update -y
yum install -y docker-ce docker-compose-plugin
systemctl enable docker && systemctl start docker

# 2. 创建专用用户（不用root运行服务）
useradd -m -s /bin/bash hdapp
usermod -aG docker hdapp

# 3. 目录结构初始化
mkdir -p /opt/hd-ph/{data/{mysql,redis,images},logs/{gateway,auth,resident,device,check,dr},nginx/ssl,mysql/{init,conf},redis}
chown -R hdapp:hdapp /opt/hd-ph

# 4. 生产镜像构建
cd /home/user/xjping-8871698/hd-ph
mvn clean package -DskipTests
docker build -t hd-gateway:1.0.0 hd-gateway/
docker build -t hd-auth:1.0.0 hd-auth/
docker build -t hd-resident:1.0.0 hd-resident/
docker build -t hd-device:1.0.0 hd-device/
docker build -t hd-check:1.0.0 hd-check/
docker build -t hd-dr:1.0.0 hd-dr/

# 5. 前端生产构建
cd hd-frontend
npm install && npm run build
# 产物: dist/ 目录
```

### Day 3: 历史数据迁移（如有）

```sql
-- 从旧系统迁移居民档案（示例）
-- 步骤1: 导出旧系统数据为CSV
-- 步骤2: 清洗（去重、格式化身份证、补全字段）
-- 步骤3: 通过LOAD DATA INFILE批量导入

LOAD DATA INFILE '/tmp/residents_import.csv'
INTO TABLE resident
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(name, id_card, gender, birth_date, phone, address, town, village, dept_id)
SET create_time = NOW(), update_time = NOW(), deleted = 0, status = 1;

-- 验证迁移记录数
SELECT COUNT(*) FROM resident WHERE deleted = 0;
```

### Day 4-5: 系统培训

**培训计划**

| 场次 | 对象 | 时长 | 内容 |
|------|------|------|------|
| 第1场 | 管理员（各机构信息员） | 4h | 系统管理、账号管理、日志查看 |
| 第2场 | 医生/护士 | 3h | 居民建档、体检录入、结果查阅 |
| 第3场 | DR技师 | 2h | DR申请、扫码签到、报告填写 |
| 第4场 | 公卫科长 | 2h | 数据统计、导出、上报操作 |

---

## 3.3 第三阶段：切换上线（W3，3个工作日）

### Day 1: 数据库最终同步

```bash
# 旧系统只读模式
# 最终全量导出
mysqldump -u root -p olddb > final_dump.sql

# 生产库导入
mysql -u root -p hd_public_health < final_dump.sql

# 验证关键数量
mysql -e "SELECT '居民' AS t, COUNT(*) FROM resident WHERE deleted=0
UNION ALL SELECT '体检单', COUNT(*) FROM check_order WHERE deleted=0;"
```

### Day 2: 灰度切换（并行双跑开始）

```
1. DNS/Nginx 切换: 5%流量 → 新系统
2. 旧系统继续保持运行（只读）
3. 监控新系统错误率: 要求 < 0.1%
4. 24小时后扩大至50%
5. 48小时后全量切换至新系统
```

### Day 3: 全量切换

```bash
# 全量切换确认清单
□ 新系统所有服务 docker-compose ps 均为 Up
□ 最近1小时无 ERROR 级别日志
□ 数据库主从延迟 < 1s
□ Redis连接正常
□ 至少1台设备完成联调（ASTM数据成功入库）
□ 管理员账号密码已从hd2024修改为强密码
□ SSL证书有效期 > 90天
□ 备份任务已设置并验证成功

# 旧系统下线
systemctl stop old-system
# 保留旧系统数据库只读归档 30天
```

---

## 3.4 第四阶段：试运行（W4，持续2周）

### 试运行监控要点

```
每日检查项:
□ 所有容器状态 (docker-compose ps)
□ 错误日志 (grep ERROR /opt/hd-ph/logs/**/*.log | tail -100)
□ 数据库慢查询 (show processlist)
□ Redis内存使用 (redis-cli info memory)
□ 磁盘使用率 (df -h | grep /opt)
□ 当日体检单创建数量（与实际核对）

每周检查项:
□ 数据库备份文件完整性验证
□ 性能指标回顾（接口响应时间P95）
□ 设备连接日志（所有设备至少成功传输1次）
□ 安全扫描
```

### 试运行问题处理流程

```
问题发现 → 登记问题单 → 分级 (P1/P2/P3)
  P1(系统不可用):  1小时内响应，4小时修复
  P2(功能异常):    4小时内响应，当日修复
  P3(体验问题):    次日响应，下个版本修复
```

---

## 3.5 第五阶段：正式运营（W5+）

### 正式上线确认标准

```
□ 试运行2周，P1问题0个
□ 试运行2周，P2问题已全部修复
□ 所有参与机构至少完成10例完整体检流程
□ 至少3台设备成功完成ASTM自动采集
□ DR流程（申请→扫码→报告）完成≥5例
□ 数据备份连续成功7天
□ 用户满意度调查≥80%满意
```

### 上线公告模板

```
【系统上线通知】

惠东县区域公卫体检集中系统已于[日期]正式上线运行。

访问地址: https://phcheck.huidong.gov.cn
账号申请: 请联系各机构信息员或拨打运维热线 0752-XXXXXXX

本系统支持功能:
- 居民档案统一建档与查询
- 体检全流程信息化管理
- 检验设备数据自动采集（11种设备）
- DR影像条码追溯管理
- 公卫数据自动上报

如遇问题请及时反馈，感谢各机构配合！

惠东县卫生健康局信息科
[日期]
```
