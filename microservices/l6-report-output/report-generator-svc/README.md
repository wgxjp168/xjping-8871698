# report-generator-svc — L6 Report Output Layer

**技术栈**: Java 17 / Spring Boot 3.2 / PostgreSQL / RabbitMQ / Redis
**端口**: 8061
**职责**: 根据客户类型（B2B / B2C已定品牌 / B2C未定品牌）生成专属结构化报告，对接L5 report-svc，输出给format-output-svc。

---

## 目录结构

```
report-generator-svc/
├── src/main/java/com/ilbuy/reportgen/
│   ├── ReportGeneratorApplication.java
│   ├── api/                    # REST controllers (内部接口)
│   │   └── ReportJobController.java
│   ├── client/                 # HTTP clients
│   │   ├── L5ReportClient.java         # 调用L5 report-svc获取数据
│   │   └── FormatOutputClient.java     # 推送给format-output-svc
│   ├── config/
│   │   ├── AsyncConfig.java
│   │   ├── RabbitMQConfig.java
│   │   └── SecurityConfig.java
│   ├── exception/
│   │   └── GlobalExceptionHandler.java
│   ├── model/
│   │   ├── dto/                # 数据传输对象
│   │   ├── entity/             # JPA实体
│   │   └── enums/              # 枚举类型
│   ├── mq/
│   │   └── ReportGenerateConsumer.java  # 消费L5 MQ消息
│   ├── repository/             # JPA Repositories
│   └── service/
│       ├── ReportGeneratorService.java  # 主服务编排
│       └── generator/          # 策略模式实现
│           ├── ReportGeneratorStrategy.java  (接口)
│           ├── B2BReportGenerator.java
│           ├── B2CDefinedBrandReportGenerator.java
│           └── B2CUndefinedBrandReportGenerator.java
├── src/main/resources/
│   ├── application.yml
│   ├── application-prod.yml
│   └── db/migration/V1__init_report_generator.sql
├── src/test/
├── k8s/
│   ├── deployment.yaml         # Deployment + Service + HPA
│   └── configmap.yaml
├── Dockerfile
└── README.md
```

---

## 核心数据流

```
L5 REPORT_SVC
    │ MQ: l5.report.exchange → l6.report.generate.request
    ▼
ReportGenerateConsumer
    │
    ▼
ReportGeneratorService (策略模式路由)
    ├── B2BReportGenerator          → 6个B2B专属章节
    ├── B2CDefinedBrandReportGenerator  → 6个已定品牌章节
    └── B2CUndefinedBrandReportGenerator → 6个未定品牌章节
    │
    ▼ HTTP POST /internal/v1/format-jobs
format-output-svc (port 8062)
```

---

## 报告章节

| 客户类型 | 章节 |
|---------|------|
| B2B | 执行摘要、供应商格局、价格基准、合规检查、风险评估、采购建议 |
| B2C已定品牌 | 品牌分析、价格对比、竞争对手映射、渠道表现、市场份额、战略洞察 |
| B2C未定品牌 | 市场总览、品类趋势、品牌发现、价格区间分析、消费者情感、入场策略 |

---

## 本地开发启动

### 前置依赖
```bash
# 启动基础设施
docker-compose -f ../../../infra/docker-compose.yml up -d postgres rabbitmq redis
```

### 创建数据库
```sql
CREATE DATABASE ilbuy_l6;
CREATE USER ilbuy WITH PASSWORD 'ilbuy123';
GRANT ALL PRIVILEGES ON DATABASE ilbuy_l6 TO ilbuy;
```

### 编译运行
```bash
mvn clean package -DskipTests
java -jar target/report-generator-svc-1.0.0.jar --spring.profiles.active=dev
```

或直接：
```bash
mvn spring-boot:run -Dspring-boot.run.profiles=dev
```

### 运行测试
```bash
mvn test
```

---

## Docker构建

```bash
docker build -t ilbuy/report-generator-svc:latest .
docker run -p 8061:8061 \
  -e DB_URL=jdbc:postgresql://host.docker.internal:5432/ilbuy_l6 \
  -e RABBITMQ_HOST=host.docker.internal \
  ilbuy/report-generator-svc:latest
```

---

## K8s部署

```bash
kubectl create namespace ilbuy-l6
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/deployment.yaml
kubectl rollout status deployment/report-generator-svc -n ilbuy-l6
```

---

## API接口

| 方法 | 路径 | 说明 |
|-----|------|------|
| GET | /internal/v1/generator-jobs/{jobNo} | 查询生成任务状态 |
| GET | /internal/v1/generator-jobs/health | 健康检查 |
| POST | /internal/v1/generator-jobs/{jobNo}/monetize-hook | L7商业变现层接口预留 |
| POST | /internal/v1/generator-jobs/{jobNo}/feedback-hook | L8反馈优化层接口预留 |

---

## 环境变量

| 变量 | 说明 | 默认值 |
|-----|------|-------|
| DB_URL | PostgreSQL连接串 | jdbc:postgresql://localhost:5432/ilbuy_l6 |
| RABBITMQ_HOST | RabbitMQ地址 | localhost |
| REDIS_HOST | Redis地址 | localhost |
| L5_REPORT_SVC_URL | L5 report-svc地址 | http://localhost:8051 |
| L6_FORMAT_OUTPUT_SVC_URL | format-output-svc地址 | http://localhost:8062 |
| JWT_SECRET | JWT签名密钥 | (必须配置) |
