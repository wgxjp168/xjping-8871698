# data-monetize-svc — 数据变现服务

## 服务描述

**数据变现服务**（L7 层）负责数据能力的对外输出与商业化，包括市场报告订阅、数据 API 接入计费以及数据集市产品销售。该服务向上对接 L6 `report-generator-svc`（报告生成），向下通过 `monetize-gateway-svc` 完成支付流转，并通过 RabbitMQ 接收支付结果事件。

- **端口**：`8074`
- **命名空间**：`ilbuy-l7`
- **依赖服务**：
  - `report-generator-svc:8061`（L6 报告生成服务）
  - `monetize-gateway-svc:8071`（L7 变现网关）

---

## API 接口

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| `GET` | `/api/v1/data-products` | 获取可用数据产品列表 | 公开 |
| `POST` | `/api/v1/data-orders` | 创建数据订单并发起支付 | JWT |
| `GET` | `/api/v1/data-orders/{orderNo}` | 查询订单详情 | JWT |
| `GET` | `/actuator/health` | 健康检查 | 公开 |

### 数据产品类别（category）

| 值 | 说明 |
|----|------|
| `MARKET_REPORT` | 市场分析报告，支付后自动触发 L6 报告生成任务 |
| `API_DATA` | 数据 API 接入授权 |
| `DATA_FEED` | 数据流订阅 |

---

## 数据流

```
report-generator-svc (L6, :8061)
        |
        v  触发报告生成任务（MARKET_REPORT 类型订单支付后）
data-monetize-svc (:8074)
        |
        v  发起支付请求
monetize-gateway-svc (:8071)
        |
        v  支付结果事件（RabbitMQ）
data-monetize-svc (PaymentEventListener)
  queue: payment.success.data
  queue: payment.failed.data
```

---

## 本地开发

```bash
# 启动本地依赖（PostgreSQL / Redis / RabbitMQ）
docker-compose up -d postgres redis rabbitmq

# 运行服务（dev profile）
cd microservices/l7-monetization/data-monetize-svc
mvn spring-boot:run -Dspring-boot.run.profiles=dev

# 运行单元测试
mvn test
```

---

## K8s 部署

```bash
# 构建镜像
docker build -t ilbuy/data-monetize-svc:latest .

# 部署到 K8s
kubectl apply -f k8s/deployment.yaml

# 查看 Pod 状态
kubectl get pods -n ilbuy-l7 -l app=data-monetize-svc
```

### 依赖的 ConfigMap / Secret

| 资源 | 类型 | 键 |
|------|------|----|
| `ilbuy-l7-config` | ConfigMap | `db.host`, `db.port`, `redis.host`, `redis.port`, `rabbitmq.host`, `monetize.gateway.url`, `l6.report.url` |
| `ilbuy-l7-db-secret` | Secret | `url`, `username`, `password` |
| `ilbuy-redis-secret` | Secret | `password` |
| `ilbuy-rabbitmq-secret` | Secret | `username`, `password` |
| `ilbuy-jwt-secret` | Secret | `secret` |
