# 我来购(ILbuy) AI采购决策平台

> AI驱动的智能采购决策系统，支持 B2B 企业采购 和 B2C 个人消费两大场景

---

## 项目简介

**ILbuy** 通过多模态输入（文本/图片/链接/语音）理解用户采购需求，在7大电商平台合规采集商品数据，运用三大评分模型进行智能分析，生成专业的采购决策报告（HTML/PDF/Excel），帮助用户做出最优采购决策。

---

## 核心特性

- **多模态输入**: 支持文本对话、图片识别、链接解析、语音转文本
- **AI决策八步流程**: 意图识别 → 品牌检测 → 参数提取 → 数据采集 → 智能评分 → 双档推荐 → 报告生成
- **三大评分模型**: B2B供应商评分 / B2C已定品牌评分 / B2C未定品牌评分
- **7大电商平台**: 淘宝/天猫/京东/拼多多/1688/唯品会/苏宁/抖音（合规采集）
- **双档推荐**: 品质款 + 性价比款，满足不同需求
- **多格式报告**: HTML交互式 / PDF可打印 / Excel数据 / API JSON
- **多渠道交付**: Web门户 / 移动App / 邮件 / 微信公众号

---

## 九层架构

```
L0  多模态用户输入
L1  接入网关层       (Kong/Nginx + Spring Boot JWT/OAuth2)
L2  AI决策中枢       (Python/FastAPI + Node.js + 大模型SDK)
L3  数据采集与处理层  (Python/Scrapy + ETL)
L4  数据存储层       (MySQL + Redis + ES + ClickHouse + MinIO)
L5  业务逻辑层       (Spring Boot + Go/Gin + Node.js)
L6  报告输出层       (Java + PDF/Excel生成)
L7  商业变现层       (Spring Boot + 微信/支付宝/银联)
L8  反馈与优化飞轮   (Python + A/B测试 + 模型训练)
L9  支撑与运维层     (K8s + Prometheus + ELK + Jaeger + Nacos)
```

---

## 快速开始（本地开发）

### 环境要求

- Docker 25+
- Docker Compose 2.x
- JDK 17+（Java服务开发）
- Python 3.11+（AI服务开发）
- Go 1.21+（Go服务开发）
- Node.js 20+（Node服务开发）

### 1. 克隆项目

```bash
git clone <repo-url>
cd ILbuy-AI-Purchase-Decision-Platform
```

### 2. 启动本地基础设施

```bash
# 一键启动所有中间件
bash infra/scripts/start-dev.sh
```

或手动启动：

```bash
# 启动基础中间件
docker compose up -d mysql redis elasticsearch rabbitmq minio nacos

# 启动监控
docker compose up -d prometheus grafana jaeger
```

### 3. 本地访问地址

| 服务 | 地址 | 账号 |
|------|------|------|
| Nacos配置中心 | http://localhost:8848/nacos | nacos/nacos |
| MySQL | localhost:3306 | root/ilbuy@2024 |
| Redis | localhost:6379 | - |
| Elasticsearch | http://localhost:9200 | - |
| Kibana | http://localhost:5601 | - |
| RabbitMQ管理台 | http://localhost:15672 | ilbuy/ilbuy@2024 |
| MinIO控制台 | http://localhost:9001 | ilbuy/ilbuy@2024 |
| Prometheus | http://localhost:9090 | - |
| Grafana | http://localhost:3000 | admin/ilbuy@2024 |
| Jaeger链路追踪 | http://localhost:16686 | - |

### 4. 启动核心微服务

```bash
# AI决策层（Python）
cd microservices/l2-ai-decision/intent-svc
pip install -r requirements.txt
python -m uvicorn app.main:app --port 8010 --reload

cd microservices/l2-ai-decision/llm-svc
pip install -r requirements.txt
python -m uvicorn app.main:app --port 8011 --reload

# 用户服务（Java）
cd microservices/l5-business-logic/user-svc
mvn spring-boot:run
```

---

## 项目结构

```
ILbuy-AI-Purchase-Decision-Platform/
├── docs/                          # 架构文档、部署手册、测试用例
├── infra/                         # 基础设施（配置/脚本/Docker Compose）
├── common/                        # 公共组件（安全/数据库/缓存/Feign）
├── microservices/                 # 核心微服务（按九层架构组织）
│   ├── l1-gateway/                # API网关
│   ├── l2-ai-decision/            # AI决策中枢（意图/LLM/决策/对话）
│   ├── l3-data-process/           # 数据采集与ETL
│   ├── l4-data-storage/           # 存储适配服务
│   ├── l5-business-logic/         # 业务服务（用户/商品/订单/报告）
│   ├── l6-report-output/          # 报告生成与输出
│   ├── l7-monetization/           # 支付与计费
│   ├── l8-feedback-optimize/      # 反馈收集与模型优化
│   └── l9-ops-support/            # 运维支撑配置
├── pom.xml                        # Maven父工程
├── docker-compose.yml             # 本地一键启动
└── README.md
```

---

## 技术栈

| 层级 | 技术 |
|------|------|
| 网关 | Spring Cloud Gateway / Kong |
| AI服务 | Python FastAPI + OpenAI/Claude/文心一言 |
| 业务服务 | Spring Boot 3.x / Go Gin / Node.js |
| 数据库 | MySQL 8.0 / Redis 7.2 / Elasticsearch 8.11 |
| 消息队列 | RabbitMQ 3.12 |
| 流处理 | Apache Flink |
| 对象存储 | MinIO |
| 日志分析 | ClickHouse |
| 容器编排 | Kubernetes 1.29 |
| 监控 | Prometheus + Grafana |
| 链路追踪 | Jaeger |
| 日志 | ELK Stack |
| 配置中心 | Nacos 2.3 |
| 密钥管理 | HashiCorp Vault |
| CI/CD | Jenkins / GitLab CI + ArgoCD |

---

## 文档

- [架构设计概览](docs/architecture/design-docs/architecture-overview.md)
- [API接口文档](docs/architecture/api-docs/)
- [部署手册](docs/deploy/)
- [测试用例](docs/test/)

---

## 性能指标

| 指标 | 目标 |
|------|------|
| AI决策响应 | < 3秒 |
| 核心接口P99 | < 500ms |
| 并发能力 | 10000+ QPS |
| 系统可用性 | 99.9% |

---

## 贡献

欢迎提交 Issue 和 Pull Request。

---

*我的梦想刚刚开始* 🚀
