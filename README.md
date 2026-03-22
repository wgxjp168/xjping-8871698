# ILbuy — 企业采购平台（我来购）

> 基于微服务架构的 B2B 企业采购平台，覆盖商品管理、订单、供应商评分、财务结算、智能推荐全链路。

---

## 项目总览

| 层次 | 技术栈 |
|------|--------|
| 网关 | Spring Cloud Gateway 3.1 |
| 微服务 | Spring Boot 2.7.18 + Spring Cloud 2021 |
| 服务注册/配置 | Nacos 2.3.2 |
| 数据库 | MySQL 8.0（主从），ClickHouse 23.12（OLAP） |
| 缓存 | Redis 7.2 |
| 搜索 | Elasticsearch 8.11 + IK 分词 |
| 消息队列 | RabbitMQ 3.12（Topic Exchange + DLX） |
| 对象存储 | MinIO |
| 数据同步 | Canal 1.1.7 + Flink（Binlog → ES/ClickHouse） |
| AI 服务 | Anthropic Claude / OpenAI GPT-4o / Qwen |
| 业务数据服务 | Python FastAPI + biz_data_svc |
| 密钥管理 | HashiCorp Vault（生产） |
| 容器化 | Docker Compose（本地）/ Kubernetes（生产） |

### 微服务端口

| 服务 | 端口 | 说明 |
|------|------|------|
| gateway-svc | 8080 | API 网关（统一入口、JWT 鉴权、限流） |
| user-svc | 8081 | 用户注册/登录/OAuth2 |
| product-svc | 8082 | 商品管理 + ES 搜索 |
| order-svc | 8083 | 订单全生命周期 + 支付 |
| supplier-svc | 8084 | 供应商管理 + 评分 |
| finance-svc | 8086 | 对账 + T+7 结算 |
| message-svc | 8087 | 短信/邮件/微信推送 |
| biz-data-svc | 8088 | 数据分析（Python FastAPI） |
| ai-svc | 8089 | 智能推荐/风控/报告 |

---

## 快速开始

### 环境要求

- Docker >= 24.0 + Docker Compose >= 2.20
- Java 17（用于本地构建 Java 服务）
- Python 3.11+（用于本地开发 biz_data_svc）
- 内存建议 ≥ 16GB（跑全栈）

### 一、启动中间件（本地开发推荐）

```bash
cd infra/docker-compose/middleware

# 可选：复制并修改密码
cp .env .env.local && vim .env.local

# 启动所有中间件
docker compose --env-file .env up -d

# 查看状态
docker compose ps
```

中间件访问地址：

| 服务 | 地址 | 账号/密码 |
|------|------|-----------|
| MySQL | localhost:3306 | root / ilbuy123 |
| Redis | localhost:6379 | 密码: ilbuy123 |
| Elasticsearch | http://localhost:9200 | 无认证 |
| Kibana | http://localhost:5601 | - |
| RabbitMQ 管理台 | http://localhost:15672 | guest / guest |
| Nacos 控制台 | http://localhost:8848/nacos | nacos / nacos |
| MinIO 控制台 | http://localhost:9001 | minioadmin / minioadmin |
| ClickHouse HTTP | http://localhost:8123 | 无密码 |

### 二、导入 Nacos 配置

```bash
# 导入开发环境配置（Nacos 启动后执行）
bash infra/common-config/nacos/nacos-import.sh dev

# 导入生产环境配置
NACOS_HOST=http://your-nacos:8848 bash infra/common-config/nacos/nacos-import.sh prod
```

### 三、构建微服务镜像

```bash
# 构建所有服务（需先确保 Maven 和 Docker 可用）
bash infra/scripts/build.sh

# 构建单个服务并推送
bash infra/scripts/build.sh -t v1.0.0 --push gateway-svc

# 构建所有服务并推送到仓库
REGISTRY=registry.cn-hangzhou.aliyuncs.com/myorg \
  bash infra/scripts/build.sh -t v1.0.0 --push
```

### 四、启动微服务（分开模式）

```bash
cd infra/docker-compose/services

# 启动所有微服务（中间件须已启动）
docker compose --env-file .env up -d

# 查看服务状态
bash infra/scripts/deploy.sh status
```

### 五、一键全栈启动（集成测试）

```bash
# 项目根目录
docker compose up -d

# 等待所有服务就绪（约 2-3 分钟）
docker compose ps

# 关闭并清理数据
docker compose down -v
```

---

## 生产部署

### K8s 部署

```bash
# 切换到 K8s 模式
export DEPLOY_MODE=k8s
export K8S_NS=ilbuy

# 部署所有服务
bash infra/scripts/deploy.sh start

# 查看 K8s 状态
bash infra/scripts/deploy.sh status

# 回滚单个服务
bash infra/scripts/deploy.sh rollback gateway-svc v1.1.0
```

### Vault 密钥管理

```bash
# 1. 参考模板创建 secrets
cp infra/common-config/vault/ilbuy-secrets-template.json secrets.json
vim secrets.json   # 替换所有 <REPLACE_ME>

# 2. 写入 Vault
vault kv put secret/ilbuy/db/user_db \
  host=10.0.0.1 username=ilbuy_user password=xxx

# 3. 应用策略
vault policy write ilbuy-policy infra/common-config/vault/ilbuy-policy.hcl

# 4. 绑定 K8s ServiceAccount
vault write auth/kubernetes/role/ilbuy-app \
  bound_service_account_names=ilbuy-app \
  bound_service_account_namespaces=ilbuy \
  policies=ilbuy-policy ttl=1h
```

---

## 运维脚本

| 脚本 | 用途 |
|------|------|
| `infra/scripts/build.sh` | 构建/推送 Docker 镜像 |
| `infra/scripts/deploy.sh` | 服务启停/重启/扩缩容/回滚 |
| `infra/scripts/backup.sh` | MySQL / Redis / ClickHouse / MinIO 数据备份 |
| `infra/scripts/monitor.sh` | 健康检查 + 企业微信/钉钉告警 |
| `infra/scripts/log-query.sh` | 服务日志检索（级别/关键词/时间范围过滤） |

```bash
# 每天凌晨 2 点全量备份
0 2 * * * BACKUP_DIR=/data/backups bash /opt/ilbuy/infra/scripts/backup.sh >> /var/log/ilbuy-backup.log 2>&1

# 持续监控（每分钟）
WECHAT_WEBHOOK=https://qyapi.weixin.qq.com/... \
  bash infra/scripts/monitor.sh --watch 60

# 查看 order-svc 最近 500 条 ERROR 日志
bash infra/scripts/log-query.sh order-svc -n 500 -l ERROR

# 实时追踪 gateway-svc 日志并过滤关键词
bash infra/scripts/log-query.sh gateway-svc -f -k "401|403|500"
```

---

## 目录结构

```
ilbuy/
├── docker-compose.yml              # 全栈一键启动（本地集成测试）
├── .gitignore
├── README.md
├── infra/
│   ├── common-config/
│   │   ├── nacos/
│   │   │   ├── dev/                # 开发环境 Nacos 配置（application-common, 各服务）
│   │   │   ├── prod/               # 生产环境 Nacos 配置
│   │   │   └── nacos-import.sh     # 批量导入脚本
│   │   └── vault/
│   │       ├── ilbuy-policy.hcl    # Vault 访问策略（最小权限）
│   │       └── ilbuy-secrets-template.json  # Secret 模板
│   ├── docker-compose/
│   │   ├── middleware/             # 中间件 Docker Compose（MySQL/Redis/ES/...）
│   │   └── services/               # 微服务 Docker Compose
│   └── scripts/
│       ├── build.sh                # 镜像构建
│       ├── deploy.sh               # 服务启停/回滚
│       ├── backup.sh               # 数据备份
│       ├── monitor.sh              # 监控告警
│       └── log-query.sh            # 日志查询
├── gateway-svc/                    # Spring Cloud Gateway
├── user-svc/                       # 用户服务
├── product-svc/                    # 商品服务
├── order-svc/                      # 订单服务
├── supplier-svc/                   # 供应商服务（含 supplier-score-java）
├── finance-svc/                    # 财务结算服务
├── message-svc/                    # 消息通知服务
├── ai-svc/                         # AI 智能服务
└── biz_data_svc/                   # 业务数据服务（Python FastAPI）
    ├── infra/                      # Redis/ES/MinIO/ClickHouse/RabbitMQ 客户端
    ├── sync/                       # Canal 消费 + Flink 同步
    └── modules/                    # 业务模块（用户/商品/订单/供应商/财务/消息/分析）
```

---

## 数据流架构

```
用户请求
  → Gateway（JWT验证、限流、路由）
  → 各微服务（MySQL 读写）
      → Canal 监听 Binlog
          → RabbitMQ（ilbuy.sync exchange）
              → biz-data-svc Flink Worker
                  → Elasticsearch（商品搜索索引）
                  → ClickHouse（行为日志、订单事件 OLAP）
      → Redis（Session缓存、热点商品、分布式锁）
      → MinIO（文件存储、报告、合同）
      → RabbitMQ（ilbuy.async exchange）
          → message-svc（短信/邮件/推送）
          → finance-svc（异步对账）
  → ai-svc（Claude/GPT-4o 智能推荐、风控、报告生成）
```

---

## 许可证

© 2024–2026 ILbuy. All rights reserved.
