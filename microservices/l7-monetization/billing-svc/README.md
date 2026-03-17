# 计费服务 (billing-svc)

**端口**: 8075
**所属层**: L7 变现层
**模块**: 账单生成 / 退款处理 / 收益统计

---

## 服务简介

`billing-svc` 汇聚 C 端（消费者订单）、B 端（企业 SaaS/API）和数据变现三条业务线的计费信息，提供：

- **账单生成**：支付成功后自动开具发票（`INV-` 前缀编号）
- **退款处理**：创建退款单（`REF-` 前缀），调用 monetize-gateway-svc 发起退款，监听退款结果回调
- **收益统计**：每月 1 日 03:00 定时聚合上月各业务线净收益

---

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/v1/billing/invoices/{invoiceNo}` | 查询发票 |
| `POST` | `/api/v1/billing/refunds` | 发起退款 |
| `GET` | `/api/v1/billing/refunds/{refundNo}` | 查询退款进度 |

> 公开端点（无需 JWT）：`/actuator/**`、`/api/v1/billing/webhook`

---

## 数据流

```
RabbitMQ: payment.success.billing
    └─> PaymentEventListener.handlePaymentSuccess()
            └─> BillingService.issueInvoice()  →  Invoice (ISSUED)

RabbitMQ: refund.success
    └─> PaymentEventListener.handleRefundSuccess()
            └─> RefundRecord.status = COMPLETED

@Scheduled cron="0 0 3 1 * *"
    └─> BillingService.generateMonthlyRevenue()
            └─> RevenueRecord (per orderType: C_ORDER / B_ORDER / DATA_ORDER)
```

---

## 依赖中间件

| 中间件 | 用途 |
|--------|------|
| PostgreSQL | 发票、退款、收益持久化 |
| Redis | 缓存（会话/幂等键扩展点） |
| RabbitMQ | 监听 `payment.success.billing`、`refund.success` |
| monetize-gateway-svc (8071) | 下游退款调用 |

---

## 本地开发

```bash
# 启动依赖（PostgreSQL / Redis / RabbitMQ）
docker compose up -d postgres redis rabbitmq

# 运行服务（dev profile）
cd microservices/l7-monetization/billing-svc
mvn spring-boot:run -Dspring-boot.run.profiles=dev

# 运行测试
mvn test
```

---

## Docker 构建

```bash
docker build -t ilbuy/billing-svc:latest .
docker run -p 8075:8075 \
  -e SPRING_PROFILES_ACTIVE=prod \
  -e DB_HOST=localhost \
  -e DB_USERNAME=ilbuy \
  -e DB_PASSWORD=ilbuy \
  -e REDIS_HOST=localhost \
  -e RABBITMQ_HOST=localhost \
  -e JWT_SECRET=your-secret \
  ilbuy/billing-svc:latest
```

---

## K8s 部署

```bash
# 创建命名空间（如未创建）
kubectl create namespace ilbuy-l7

# 部署服务
kubectl apply -f k8s/deployment.yaml -n ilbuy-l7

# 查看状态
kubectl get pods,svc,hpa -n ilbuy-l7 -l app=billing-svc
```

---

## 环境变量（生产）

| 变量 | 来源 | 说明 |
|------|------|------|
| `DB_HOST` | ConfigMap `ilbuy-l7-config` | 数据库主机 |
| `DB_PORT` | ConfigMap `ilbuy-l7-config` | 数据库端口 |
| `DB_USERNAME` | Secret `ilbuy-l7-db-secret` | 数据库用户名 |
| `DB_PASSWORD` | Secret `ilbuy-l7-db-secret` | 数据库密码 |
| `REDIS_HOST` | ConfigMap `ilbuy-l7-config` | Redis 主机 |
| `REDIS_PASSWORD` | Secret `ilbuy-redis-secret` | Redis 密码 |
| `RABBITMQ_HOST` | ConfigMap `ilbuy-l7-config` | RabbitMQ 主机 |
| `RABBITMQ_USERNAME` | Secret `ilbuy-rabbitmq-secret` | RabbitMQ 用户名 |
| `RABBITMQ_PASSWORD` | Secret `ilbuy-rabbitmq-secret` | RabbitMQ 密码 |
| `MONETIZE_GATEWAY_URL` | ConfigMap `ilbuy-l7-config` | 网关服务地址 |
| `JWT_SECRET` | Secret `ilbuy-jwt-secret` | JWT 签名密钥 |
