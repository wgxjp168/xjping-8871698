# 07 · 设备接入与运维流程

## 7.1 设备接入总体流程

```
新设备到货
    ↓
1. 设备信息登记（系统）
    ↓
2. 网络配置（静态IP、路由）
    ↓
3. 设备ASTM协议配置（设备端）
    ↓
4. 联调测试（发送测试报文）
    ↓
5. 验证数据入库
    ↓
6. 上线投入使用
```

---

## 7.2 新设备接入操作手册

### Step 1: 系统登记设备信息

```
路径: 设备管理 → 新增设备

填写字段:
  设备编号:  [机构编码]-[设备类型]-[序号]，如 MZSY-BIOCHEM-001
  设备名称:  如 迈瑞BS-230全自动生化分析仪
  设备型号:  BS-230
  厂家:      迈瑞生物
  设备类型:  选择 BIOCHEM/BLOOD/URINE/HBA1C
  协议类型:  ASTM（当前所有设备均为ASTM）
  IP地址:    设备将要配置的静态IP（如 192.168.20.15）
  连接模式:  TCP_SERVER（设备主动连接我方TCP服务器）
  所属机构:  选择设备所在卫生院
```

### Step 2: 网络配置

```bash
# 在设备所在局域网交换机上:
# 1. 为设备分配静态IP（在DHCP排除范围内）
# 2. 确保设备IP与服务器IP路由可达

# 验证连通性（在服务器上执行）:
ping 192.168.20.15  # 设备IP

# 确认服务器TCP端口7100在监听:
netstat -tlnp | grep 7100
# 期望: tcp6   0   0 :::7100   :::*   LISTEN   [pid]/java

# 或在容器内确认:
docker exec hd-device netstat -tlnp | grep 7100
```

### Step 3: 设备端ASTM配置

**通用配置步骤（参考各厂家手册）**

```
以迈瑞BS-230为例:
1. 进入设备"通讯设置"菜单
2. 通讯方式: 选择 "LIS（ASTM）"
3. IP地址: 填入服务器IP（如 192.168.10.30）
4. 端口: 7100
5. 传输协议: TCP
6. 连接方式: 主动连接（Client模式）
7. 数据格式: ASTM E1394
8. 样本ID格式: 建议设置为与体检单号格式匹配
9. 自动发送: 开启（检测完成后自动推送结果）
10. 保存配置

以罗氏cobas c311为例:
1. 菜单 → Setup → Communication → LIS
2. LIS Connection: TCP/IP Active
3. Host IP: 192.168.10.30
4. Host Port: 7100
5. Protocol: ASTM
6. Auto-send results: Yes

对于迈瑞设备（使用MINDRAY私有协议的型号）:
  → 需要启用ASTM兼容模式
  → 部分型号需要厂家工程师现场配置
  → 联系迈瑞服务热线: 400-700-9998
```

### Step 4: 联调测试

**使用系统模拟测试工具**

```bash
# 方法1: 使用nc发送测试ASTM报文（在局域网任意机器）
echo -e "\x05" | nc 192.168.10.30 7100   # 发送ENQ
# 期望: 收到ACK (0x06)

# 方法2: 完整ASTM报文测试（Python脚本）
python3 test_astm_device.py \
  --host 192.168.10.30 \
  --port 7100 \
  --sample-id "CK20260325TEST" \
  --device-type BIOCHEM

# 方法3: 设备直接发送测试样本
# 在设备上检测QC质控品，确认数据传输
```

**检查数据入库**

```sql
-- 在MySQL中查询（联调完成后约30秒内）
SELECT id, device_id, sample_id, process_status, create_time
FROM device_raw_data
WHERE sample_id LIKE '%TEST%'
   OR create_time > DATE_SUB(NOW(), INTERVAL 5 MINUTE)
ORDER BY create_time DESC
LIMIT 10;

-- 期望: 出现新记录，process_status=1（已处理）
-- 或查看系统日志
docker logs hd-device --since 5m | grep -E "Parsed|saved|sampleId"
```

---

## 7.3 设备协议自动适配

### ASTM E1394 标准解析流程

```java
// 系统 AstmParser 支持的自适应逻辑：

1. 物理层解析 (ASTM E1381)
   - 支持标准帧格式: STX + frameNo + data + CR + checksum + ETX/ETB
   - 支持无帧格式（部分国产设备直接发送可读文本）
   - 自动判断: 若无STX/ETX，作为纯文本处理

2. 记录层解析 (ASTM E1394)
   - H记录: 消息头（主机信息、发送时间）
   - P记录: 患者信息（患者ID、姓名）
   - O记录: 样本信息（样本号、测试项目）
   - R记录: 结果（项目代码、值、单位、参考范围、标志）
   - L记录: 消息终止

3. R记录项目代码解析（支持多种格式）
   ^^^WBC      → 提取第4段 "WBC"
   WBC         → 直接使用
   ^WBC^白细胞 → 代码WBC，名称白细胞

4. 异常标志解析
   H/HH → 偏高 (abnormalFlag=1)
   L/LL → 偏低 (abnormalFlag=2)
   A/AA → 异常 (abnormalFlag=3)
   N    → 正常 (abnormalFlag=0)
```

### 新增设备协议扩展

若遇到不兼容设备（非标准ASTM）：

```java
// 在 hd-device/src/main/java/com/hd/device/protocol/ 新建解析器
// 例如: SysmexParser.java (希森美康特定格式)

public class SysmexParser {
    public static AstmMessage parse(byte[] rawData) {
        // 实现特定解析逻辑
        // 将结果封装为标准 AstmMessage 对象（与系统其他部分统一）
    }
}

// 在 DeviceDataService 中根据设备型号选择解析器:
if ("SYSMEX".equals(device.getManufacturer())) {
    message = SysmexParser.parse(rawData);
} else {
    List<String> lines = AstmParser.extractRecordLines(rawData);
    message = AstmParser.parseMessage(lines);
}
```

---

## 7.4 设备日常运维

### 每日巡检清单

```bash
#!/bin/bash
# /opt/hd-ph/scripts/device-check.sh
# 建议加入 cron: 0 8 * * * /opt/hd-ph/scripts/device-check.sh

echo "=== 设备状态日报 $(date) ==="

# 查看过去24小时内接收的设备数据量
docker exec hd-mysql mysql -uroot -p"${MYSQL_ROOT_PASSWORD}" \
  hd_public_health -e "
SELECT d.device_name, d.ip_address, COUNT(r.id) as records_24h,
       SUM(CASE WHEN r.process_status=2 THEN 1 ELSE 0 END) as failed
FROM device_info d
LEFT JOIN device_raw_data r ON d.id = r.device_id
  AND r.create_time > DATE_SUB(NOW(), INTERVAL 24 HOUR)
WHERE d.deleted=0
GROUP BY d.id, d.device_name, d.ip_address
ORDER BY d.device_type, d.device_name;
"

# 查看待处理（可能积压）的原始数据
docker exec hd-mysql mysql -uroot -p"${MYSQL_ROOT_PASSWORD}" \
  hd_public_health -e "
SELECT COUNT(*) as pending FROM device_raw_data
WHERE process_status=0 AND create_time < DATE_SUB(NOW(), INTERVAL 10 MINUTE);
" 2>/dev/null
```

### 设备连接故障处理

```
故障现象: 设备数据未入库（预期时间内无新记录）

排查步骤:

Step 1: 检查设备是否完成检测
  → 在设备屏幕上确认结果已显示
  → 查看设备通讯日志（设备菜单→系统日志→通讯记录）

Step 2: 检查网络连通性
  → 在服务器: ping [设备IP]
  → 在设备: ping [服务器IP]（部分设备支持）
  → 检查交换机端口状态

Step 3: 检查TCP服务
  → docker ps | grep hd-device  （确认容器Up）
  → docker logs hd-device --since 30m | grep -E "ERROR|WARN|connected"
  → 确认端口7100开放: netstat -tlnp | grep 7100

Step 4: 查看原始数据表
  → SELECT * FROM device_raw_data ORDER BY create_time DESC LIMIT 5;
  → 若有数据但process_status=2（失败），查看error_msg字段

Step 5: 常见解决方案
  - 设备通讯断开: 重启设备通讯模块（设备端操作）
  - 防火墙拦截: 检查iptables规则 iptables -L | grep 7100
  - 容器重启: docker-compose restart hd-device
  - IP变更: 设备管理中更新设备IP地址
```

---

## 7.5 故障自愈机制

### 服务自动重启

```yaml
# docker-compose.yml 中所有服务配置:
restart: always
# 效果: 容器崩溃后5秒自动重启
# 支持最多10次重试（超出后需人工干预）
```

### 设备数据补发

```
场景: 网络中断期间设备检测了多个样本，恢复后需要补发

方案1: 设备端补发（推荐）
  → 在设备LIS通讯界面找到"重传"/"补发"功能
  → 选择需要补发的样本/时间范围
  → 设备自动重新推送ASTM报文

方案2: 系统手动处理
  若设备不支持补发，在系统中手动录入:
  → 体检单详情 → 手动添加检验结果（"手动录入"按钮）
  → 录入后标注数据来源为"手工录入"
  → 审核医生核对原始报告后确认

方案3: 原始数据重解析
  若数据已到device_raw_data但process_status=2（解析失败）:
  → 设备管理 → 待处理数据 → 选中失败记录 → "重新处理"
  → 系统重新解析原始报文入库check_result
```

### TCP连接重试机制

```java
// AstmTcpServer 的连接自愈设计:
// 1. ServerSocket accept循环不中断（单次accept失败不影响其他连接）
// 2. 每个设备连接在独立线程中处理（互不影响）
// 3. Spring 服务重启后自动重新监听端口
// 4. 设备连接失败后会自动重连（设备端配置重连间隔10秒）
```

---

## 7.6 协议升级流程

```
触发条件:
  - 厂家提供新版ASTM报文格式
  - 新接入设备使用不同协议变体
  - 修复解析兼容性问题

升级步骤:
1. 在测试环境中修改 AstmParser.java / 新增解析器
2. 使用保存的历史原始报文（device_raw_data.raw_message）回归测试
3. 确认解析结果与人工预期一致
4. 编写测试用例（AstmParserTest.java）
5. 发布新版 hd-device JAR
6. 在生产环境滚动更新:
   docker-compose stop hd-device
   docker pull hd-device:[new-version]
   docker-compose up -d hd-device
7. 监控5分钟，确认设备数据正常入库
8. 记录升级日志（版本号/升级时间/影响范围）
```
