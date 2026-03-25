# 09 · 系统运维保障

## 9.1 系统监控体系

### 监控栈（推荐）

```
┌─────────────────────────────────────────────────────────┐
│  告警通知层:  企业微信群机器人 / 短信 / 邮件               │
├─────────────────────────────────────────────────────────┤
│  可视化层:   Grafana Dashboard                           │
├────────────────────────┬────────────────────────────────┤
│  指标收集:  Prometheus  │  日志收集: ELK Stack            │
│  Node Exporter (主机)  │  Filebeat (日志采集)            │
│  JVM Micrometer (Java) │  Elasticsearch (存储)           │
│  MySQL Exporter        │  Kibana (查询/分析)              │
│  Redis Exporter        │                                 │
└────────────────────────┴────────────────────────────────┘
```

### 关键监控指标与告警阈值

```yaml
# Prometheus告警规则示例
# /opt/monitoring/alerts.yml

groups:
  - name: hd-ph-critical
    rules:
      # 服务不可用
      - alert: ServiceDown
        expr: up{job=~"hd-.*"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "服务 {{ $labels.job }} 不可用，请立即处理"

      # API响应时间过高
      - alert: APIResponseTimeTooHigh
        expr: http_server_requests_seconds_p95 > 2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "API P95响应时间超过2秒"

      # MySQL连接数过多
      - alert: MySQLTooManyConnections
        expr: mysql_global_status_threads_connected / mysql_global_variables_max_connections > 0.8
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "MySQL连接数使用率 > 80%"

      # 磁盘空间不足（DR影像存储）
      - alert: DiskSpaceLow
        expr: disk_free_percent{mountpoint="/opt/hd-ph/data"} < 20
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "DR影像存储磁盘空间不足20%，请立即扩容"

      # Redis内存使用率高
      - alert: RedisMemoryHigh
        expr: redis_memory_used_bytes / redis_memory_max_bytes > 0.9
        for: 5m
        labels:
          severity: warning

      # 设备数据积压
      - alert: DeviceDataBacklog
        expr: mysql_device_pending_records > 10
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "设备原始数据积压超过10条，请检查hd-device服务"

      # 上报失败积压
      - alert: UploadFailureBacklog
        expr: mysql_upload_failed_records > 5
        for: 30m
        labels:
          severity: warning
```

### 健康检查端点

```bash
# 检查所有服务健康状态的脚本
#!/bin/bash
# /opt/hd-ph/scripts/health-check.sh

SERVICES=(
  "http://localhost:8001/actuator/health|hd-auth"
  "http://localhost:8002/api/residents/health|hd-resident"
  "http://localhost:8003/api/devices/health|hd-device"
  "http://localhost:8004/api/vital-signs/health|hd-check"
  "http://localhost:8005/api/dr-orders/health|hd-dr"
  "http://localhost:9090/actuator/health|hd-gateway"
)

FAILED=0
for item in "${SERVICES[@]}"; do
  URL=$(echo $item | cut -d'|' -f1)
  NAME=$(echo $item | cut -d'|' -f2)
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 "$URL")
  if [ "$STATUS" != "200" ]; then
    echo "❌ $NAME FAILED (HTTP $STATUS)"
    FAILED=$((FAILED+1))
  else
    echo "✅ $NAME OK"
  fi
done

if [ $FAILED -gt 0 ]; then
  # 发送告警
  curl -s -X POST "${WECHAT_WEBHOOK}" \
    -H "Content-Type: application/json" \
    -d "{\"msgtype\":\"text\",\"text\":{\"content\":\"⚠️ 公卫体检系统告警: ${FAILED}个服务异常，请立即处理！\"}}"
fi
```

---

## 9.2 备份策略

### 备份计划

| 类型 | 内容 | 频率 | 保留期 | 存储位置 |
|------|------|------|--------|---------|
| 全量备份 | MySQL全库 | 每周日02:00 | 4周 | 本地+异地 |
| 增量备份 | MySQL binlog | 每日01:00 | 7天 | 本地 |
| 配置备份 | 所有yml/env/nginx配置 | 每次变更后 | 永久 | Git仓库 |
| DR影像备份 | /data/images/ | 每日00:30 | 1年 | NAS |
| 日志备份 | /logs/ | 每日压缩 | 3个月 | 本地 |

### 备份脚本

```bash
#!/bin/bash
# /opt/hd-ph/scripts/backup.sh
# cron: 0 1 * * * /opt/hd-ph/scripts/backup.sh

BACKUP_DIR="/opt/hd-ph/backup"
DATE=$(date +%Y%m%d_%H%M%S)
MYSQL_PWD="${MYSQL_ROOT_PASSWORD}"

mkdir -p "$BACKUP_DIR/mysql" "$BACKUP_DIR/images" "$BACKUP_DIR/logs"

# 1. MySQL备份
echo "[$(date)] 开始MySQL备份..."
docker exec hd-mysql mysqldump \
  -uroot -p"${MYSQL_PWD}" \
  --single-transaction \
  --routines \
  --triggers \
  --events \
  hd_public_health | gzip > "$BACKUP_DIR/mysql/hd_ph_${DATE}.sql.gz"

# 验证备份文件大小（应 > 100KB）
BACKUP_SIZE=$(stat -c%s "$BACKUP_DIR/mysql/hd_ph_${DATE}.sql.gz")
if [ "$BACKUP_SIZE" -lt 102400 ]; then
  echo "[WARN] 备份文件异常小 ($BACKUP_SIZE bytes)，请检查！"
  # 发送告警
fi
echo "[$(date)] MySQL备份完成，大小: ${BACKUP_SIZE} bytes"

# 2. DR影像备份（增量）
rsync -avz --delete \
  /opt/hd-ph/data/images/ \
  /backup-nas/hd-ph/images/ \
  >> "$BACKUP_DIR/logs/rsync_${DATE}.log" 2>&1

# 3. 清理7天前的旧备份
find "$BACKUP_DIR/mysql" -name "*.sql.gz" -mtime +7 -delete

echo "[$(date)] 备份任务完成"
```

### 恢复演练（每季度执行一次）

```bash
# 在测试环境验证备份可恢复性
# ！！！严禁在生产环境直接执行！！！

# 1. 启动测试MySQL容器
docker run -d --name mysql-restore-test \
  -e MYSQL_ROOT_PASSWORD=test123 \
  -p 3307:3306 mysql:8.0

# 2. 恢复备份
gunzip -c /opt/hd-ph/backup/mysql/hd_ph_20260101_010000.sql.gz | \
  mysql -h127.0.0.1 -P3307 -uroot -ptest123

# 3. 验证数据完整性
mysql -h127.0.0.1 -P3307 -uroot -ptest123 hd_public_health \
  -e "SELECT table_name, table_rows FROM information_schema.tables
      WHERE table_schema='hd_public_health' ORDER BY table_name;"

# 4. 清理测试环境
docker stop mysql-restore-test && docker rm mysql-restore-test
echo "恢复演练完成"
```

---

## 9.3 扩容方案

### 当前瓶颈与扩容触发条件

```
触发扩容的指标:

CPU使用率持续 > 70%:
  → 应用服务器: 升级CPU核数 或 新增应用服务器节点（水平扩容）

内存使用率持续 > 80%:
  → 应用服务器: 增加内存
  → MySQL服务器: 增加innodb_buffer_pool_size

磁盘使用率 > 70%:
  → DR影像磁盘: 挂载新磁盘 或 迁移至OSS
  → MySQL数据: 扩展存储 或 历史数据归档

MySQL慢查询增多:
  → 分析慢查询日志
  → 优化索引（重点: check_result表按category+order_id复合索引）
  → 考虑读写分离（主写从读）

并发用户超过200:
  → 新增应用服务器
  → 配置Nginx负载均衡
  → Redis集群化
```

### 水平扩容配置（Nginx负载均衡）

```nginx
# 新增第二台应用服务器后 Nginx 配置
upstream hd-gateway {
    least_conn;  # 最少连接数算法
    server 192.168.10.30:9090 weight=1;
    server 192.168.10.31:9090 weight=1;  # 新增节点
    keepalive 32;
}

upstream hd-check {
    server 192.168.10.30:8004;
    server 192.168.10.31:8004;
}
# 注意: hd-device (TCP:7100) 需特殊处理，不能简单负载均衡
```

---

## 9.4 安全策略

### 应用安全

```
【防SQL注入】
  - 全部使用 MyBatis-Plus 参数化查询，不拼接SQL
  - 动态SQL使用 <if> 标签，参数通过 #{} 传入（非 ${}）
  - 定期使用 SQLMap 扫描

【防XSS】
  - 前端 Vue3 自动转义 HTML 特殊字符
  - 后端接口输入参数使用 @Valid 校验长度和格式
  - 内容安全策略 (CSP) 在 Nginx 响应头中配置

【JWT安全】
  - 密钥长度 ≥ 32位随机字符串，存储于环境变量
  - Token 有效期: 8小时（与工作日时长匹配）
  - 退出登录后 Token 即时加入 Redis 黑名单
  - 不在 URL 参数中传递 Token

【接口安全】
  - 所有 /api/auth/login 以外的接口均需 Token
  - 登录失败 5 次后锁定账号 30 分钟（待二期实现）
  - 敏感操作（导出/删除）记录详细审计日志
  - 接口限流: login 接口 10次/分钟/IP（待二期实现）
```

### 网络安全

```
【HTTPS强制】
  所有HTTP请求302跳转到HTTPS
  HSTS: max-age=31536000（1年）

【内网隔离】
  设备网络(192.168.20.0/24) 与业务网络(192.168.10.0/24) 分离
  仅 hd-device 容器可访问设备网络
  数据库端口不对外暴露

【定期安全扫描】
  每月: OWASP ZAP 自动扫描
  每季度: 渗透测试（内部或外包）
  发现漏洞 → 按CVSS评分分级修复

【敏感数据保护】
  居民身份证号: 接口返回前4位+***+后4位（如 4441***1234）
  手机号: 接口返回前3位+****+后4位（如 138****8888）
  完整数据: 仅具有特定权限的角色可查看
  数据库密码: 禁止明文出现在代码/日志中
```

---

## 9.5 应急处理预案

### 预案一: 系统完全不可访问

```
现象: 所有用户无法登录，页面504/502

排查步骤（限时15分钟）:
1. 检查Nginx
   → curl http://192.168.10.10/health
   → docker ps | grep nginx

2. 检查Gateway
   → curl http://192.168.10.30:9090/actuator/health
   → docker ps | grep hd-gateway

3. 检查基础服务
   → docker exec hd-redis redis-cli ping
   → docker exec hd-mysql mysql -uroot -p"${PWD}" -e "select 1"

4. 快速恢复
   → docker-compose down && docker-compose up -d
   → 等待2分钟服务启动完成
   → 重新验证: curl health接口

5. 若容器无法启动
   → docker logs [container] --since 30m | tail -100
   → 检查磁盘空间: df -h
   → 检查内存: free -h
```

### 预案二: 数据库故障

```
现象: 服务报 DataSource / Connection 异常

紧急措施:
1. 检查MySQL状态
   docker exec hd-mysql mysql -uroot -p"${PWD}" -e "status"

2. MySQL崩溃恢复
   docker-compose restart mysql
   # 等待innodb自动恢复（最多3分钟）

3. 若数据文件损坏
   # 停止所有服务
   docker-compose stop
   # 从最近备份恢复
   gunzip -c /opt/hd-ph/backup/mysql/hd_ph_[最新日期].sql.gz | \
     docker exec -i hd-mysql mysql -uroot -p"${PWD}"
   # 重启服务
   docker-compose up -d

4. 数据损失评估
   记录备份时间点，评估丢失的增量数据
   联系相关机构核对当日体检记录进行手工补录
```

### 预案三: TCP设备连接全部中断

```
现象: 所有设备数据停止入库，device_raw_data 无新记录

排查:
1. 确认 hd-device 容器运行
   docker ps | grep hd-device

2. 确认端口7100监听
   netstat -tlnp | grep 7100

3. 测试连通性
   telnet [设备IP] 7100  # 测试从服务器出去
   nc -zv 192.168.10.30 7100  # 测试设备到服务器

4. 恢复方案
   → 重启 hd-device 服务: docker-compose restart hd-device
   → 在设备端触发重连（重启LIS通讯模块）
   → 临时方案: 切换为人工录入模式，后续设备恢复后补发数据

5. 业务连续性
   通知检验科启用"手工录入"备用流程（见OPS-05操作手册）
```

### 预案四: 存储空间耗尽

```
现象: 服务报 No space left on device，无法写入

紧急措施（优先顺序）:
1. 释放日志空间（最快）
   find /opt/hd-ph/logs -name "*.log" -mtime +30 -delete
   docker system prune -f  # 清理无用镜像/容器

2. 压缩历史DR影像
   find /opt/hd-ph/data/images -mtime +180 -exec gzip {} \;

3. 归档历史数据库记录
   -- 将3年前的device_raw_data归档到独立表
   CREATE TABLE device_raw_data_archive LIKE device_raw_data;
   INSERT INTO device_raw_data_archive
   SELECT * FROM device_raw_data WHERE create_time < '2023-01-01';
   DELETE FROM device_raw_data WHERE create_time < '2023-01-01';
   OPTIMIZE TABLE device_raw_data;

4. 挂载新磁盘
   mkfs.ext4 /dev/sdb
   mount /dev/sdb /mnt/storage-expand
   # 将data目录迁移或软链接到新磁盘
```

---

## 9.6 变更管理

```
【变更类型与审批要求】

紧急变更 (P1故障修复):
  → 值班负责人批准即可执行
  → 事后48小时内完成变更报告

常规变更 (功能更新/优化):
  → 提前3个工作日提交变更申请
  → 技术负责人审批
  → 在维护窗口执行（每周三20:00-22:00）
  → 准备回滚方案

重大变更 (架构调整/数据库结构变更):
  → 提前1周提交方案
  → 卫健局信息科批准
  → 演练环境验证通过
  → 在业务低峰期执行（周末夜间）
  → 准备完整回滚方案并演练

【变更记录格式】
变更编号: CHG-2026-001
变更类型: 常规变更
变更描述: 升级 hd-device 版本至 1.1.0（新增设备协议支持）
影响范围: hd-device 服务，约5分钟不可用
执行时间: 2026-03-25 21:00
执行人员: 张工 / 李工（审核）
回滚方案: docker-compose rollback hd-device （回退至 1.0.0 镜像）
执行结果: [成功/失败/回滚]
验证结果: 新设备已成功传输测试数据
```
