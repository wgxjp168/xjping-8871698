# 惠东县区域公卫体检集中系统 - 启动手册

## 一、系统架构

```
前端 (Vue3+ElementPlus)  →  Spring Cloud Gateway (9090)
                               ├── hd-auth     (8001) 认证授权
                               ├── hd-resident (8002) 居民档案
                               ├── hd-device   (8003) 设备集成 + ASTM TCP(7100)
                               ├── hd-check    (8004) 体检业务
                               └── hd-dr       (8005) DR影像
```

## 二、环境要求

| 组件 | 版本 | 说明 |
|------|------|------|
| JDK | 11+ | 推荐 OpenJDK 11 |
| Maven | 3.6+ | |
| MySQL | 8.0+ | 端口 3306 |
| Redis | 6.0+ | 端口 6379，无密码 |
| Node.js | 18+ | 前端构建 |

## 三、快速启动

### 3.1 准备数据库

```bash
# 登录MySQL（账号root/root123）
mysql -u root -proot123

# 初始化数据库（系统会自动执行，也可手动）
mysql -u root -proot123 < sql/hd_public_health.sql
```

### 3.2 一键启动后端

```bash
cd /path/to/hd-ph
bash start-all.sh
```

### 3.3 启动前端

```bash
cd hd-frontend
npm install
npm run dev
```

## 四、访问地址

| 服务 | 地址 |
|------|------|
| **前端系统** | http://localhost:3000 |
| **API网关** | http://localhost:9090 |
| 认证服务API文档 | http://localhost:8001/doc.html |
| 居民服务API文档 | http://localhost:8002/doc.html |
| 设备服务API文档 | http://localhost:8003/doc.html |
| 体检服务API文档 | http://localhost:8004/doc.html |
| DR服务API文档 | http://localhost:8005/doc.html |

## 五、测试账号

| 账号 | 密码 | 角色 | 说明 |
|------|------|------|------|
| admin | hd2024 | 超级管理员 | 所有权限 |
| doctor01 | hd2024 | 医生 | 体检+DR权限 |
| doctor02 | hd2024 | 生化医生 | 生化检验权限 |
| doctor03 | hd2024 | 血常规医生 | 血常规权限 |
| nurse01 | hd2024 | 护士 | 体征录入权限 |
| lab01 | hd2024 | 检验员 | 设备数据权限 |
| dr_tech | hd2024 | DR技师 | DR影像权限 |
| county_admin | hd2024 | 县级管理员 | 统计查看权限 |

## 六、主要业务流程

### 6.1 居民体检流程
1. 登录系统 → 居民管理 → 查找/新增居民
2. 点击"建体检单"→ 填写体检信息 → 创建
3. 体检单管理 → 点击"开始体检"
4. 体检详情 → 录入生命体征
5. 设备通过ASTM协议自动上传检验数据到 TCP:7100
6. 系统自动解析并存入检验结果表
7. 体检详情页查看各类检验结果

### 6.2 DR业务流程
1. 体检单 → "DR申请" → 创建DR申请单（系统自动生成条码号）
2. 打印条码贴到申请单纸质文件
3. 居民持纸质单到有DR设备的卫生院
4. 工作人员扫描条码 → DR扫码签到页面
5. 完成DR检查 → 上传图像 → 填写报告
6. 报告上传到平台（状态更新为"已上传"）

### 6.3 设备集成
- 系统在端口 **7100** 监听 TCP 连接
- 设备完成检查后主动连接并发送 ASTM E1394 格式数据
- 系统自动解析：患者ID、样本号、所有检验项目结果
- 数据先存入 `device_raw_data` 表（待处理状态）
- 再由 check 服务写入 `check_result` 表

## 七、设备配置

系统预置了11台设备（见 `device_info` 表），均支持 ASTM E1394 协议：

| 设备 | 型号 | 类型 |
|------|------|------|
| 迈瑞BS-230 | 全自动生化分析仪 | BIOCHEM |
| 罗氏cobas c311 | 全自动生化分析仪 | BIOCHEM |
| 西门子ADVIA120 | 全自动血液分析仪 | BLOOD |
| 迈瑞BC-5390 | 血常规分析仪 | BLOOD |
| 希森美康XE-2100 | 血细胞分析仪 | BLOOD |
| 迈瑞BU-680 | 全自动尿分析仪 | URINE |
| 爱威CV-600 | 尿液分析仪 | URINE |
| 博科BK-200 | 尿干化学分析仪 | URINE |
| 爱科来HA-8180 | 糖化血红蛋白仪 | HBA1C |
| Bio-Rad D-10 | 糖化血红蛋白仪 | HBA1C |
| 伯乐Variant II | 糖化血红蛋白仪 | HBA1C |

## 八、停止服务

```bash
bash stop-all.sh
```

## 九、常见问题

**Q: 服务无法连接数据库**
A: 检查 MySQL 是否启动，账号密码是否为 root/root123

**Q: JWT token 无效**
A: 检查 Redis 是否启动，Gateway 黑名单依赖 Redis

**Q: 设备数据没有入库**
A: 检查 hd-device 是否正常启动，端口 7100 是否被占用

**Q: 前端无法访问接口**
A: 确认 Gateway 正常运行于 9090 端口，前端代理配置为 http://localhost:9090
