# 惠东县区域公卫体检集中系统

> 云原生微服务架构 · Spring Boot 2.7.20 + Vue3 + Element Plus

## 系统架构

```
惠东县县域公卫系统（已有）
    ↕ 同步/回调
统一网关 (8888)
    ├── physical-auth   (9005) 权限服务 [NEW] 医生账号/项目权限/县域同步
    ├── physical-dr     (9011) DR服务   [NEW] DR条码解析/检查记录/同步县域
    ├── physical-core   (9001) 核心业务       体检记录/居民管理/检验汇聚
    ├── physical-sync   (9004) 同步服务       体检数据批量同步县域
    └── physical-urine  (9010) 尿机服务       优利特尿机4G数据接收
         ↕
physical-web (80)  Vue3网页端 [NEW] 化验室/DR室院内部署
```

## 核心新增功能

### 1. DR项目全闭环 [NEW]
- 县域公卫系统开DR单 → 打印DR条码
- 下乡体检携带DR条码
- 居民带条码回院内，DR技师扫码自动带出信息
- 录入检查结果，自动同步至县域公卫

### 2. 医生权限精细化管控 [NEW]
- 复用县域公卫系统医生账号（每日凌晨自动同步）
- 按项目：生化/血常规/糖化/尿常规/DR/血压/体重身高
- 按操作类型：查询/录入/审核
- 按范围：全院/本院/指定片区
- MAC地址绑定（网页端防越权）

### 3. 院内网页端部署 [NEW]
- 化验室/DR室电脑安装浏览器直接访问
- 访问地址：`http://网关IP:8888/web`
- 无需安装客户端，版本统一更新

## 技术栈

| 层次 | 技术 |
|------|------|
| 网关 | Spring Cloud Gateway |
| 服务 | Spring Boot 2.7.20, MyBatis-Plus 3.5.5 |
| 缓存 | Redis (Redisson) |
| 安全 | Spring Security + JWT (jjwt 0.11.5) |
| 数据库 | MySQL 8.0 |
| 前端 | Vue3 + Element Plus + Vite |
| 部署 | Docker + Docker Compose |

## 快速部署

```bash
# 1. 初始化数据库
mysql -uroot -p < sql/init.sql

# 2. 一键构建并启动（需要Docker环境）
chmod +x deploy/build.sh && ./deploy/build.sh

# 3. 访问
# 网页端: http://服务器IP:8888/web
# 默认账号: admin / Admin@2024
```

## 模块说明

```
physical-parent/
├── physical-common/    公共模块（实体/DTO/工具类）
├── physical-gateway/   统一网关（8888）
├── physical-auth/      权限服务（9005）[NEW]
├── physical-dr/        DR服务（9011）  [NEW]
├── physical-core/      核心业务（9001）
├── physical-sync/      同步服务（9004）
├── physical-urine/     尿机服务（9010）
├── physical-web/       Vue3前端（80）  [NEW]
├── sql/                数据库初始化脚本
└── deploy/             Docker部署配置
```

## 数据库表

| 表名 | 说明 |
|------|------|
| physical_resident | 居民信息 |
| physical_record | 体检记录 |
| physical_lab_result | 检验结果（生化/血常规/糖化） |
| physical_urine_result | 尿常规结果 |
| physical_doctor | 医生账号（县域同步）[NEW] |
| physical_doc_permission | 医生项目权限 [NEW] |
| physical_dr_record | DR检查记录 [NEW] |

## API文档

启动后访问：
- 权限服务：`http://localhost:9005/doc.html`
- DR服务：`http://localhost:9011/doc.html`
- 核心服务：`http://localhost:9001/doc.html`
