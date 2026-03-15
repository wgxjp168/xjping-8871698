# data-svc — ILbuy L4 数据存储服务

## 服务概览

| 属性 | 值 |
|------|-----|
| 端口 | 8035 |
| 技术栈 | Spring Boot 3.2.3 / Java 17 / JPA / Spring Data Redis / Spring Data ES |
| 存储后端 | MySQL 8.0 · Redis 7.2 · Elasticsearch 8.11 · ClickHouse · MinIO |
| 消息队列 | RabbitMQ 3.12 |
| CDC 同步 | Canal 1.1.7 (MySQL → ES 增量同步) |

---

## 目录结构

```
data-svc/
├── src/main/java/com/ilbuy/datasvc/
│   ├── DataSvcApplication.java          # 主入口
│   ├── api/                             # REST 控制器
│   │   ├── IngestController.java        # POST /ingest
│   │   ├── SearchController.java        # GET/POST /products/search
│   │   └── StatsController.java         # GET /stats, /health
│   ├── model/
│   │   ├── dto/                         # 请求/响应 DTO
│   │   ├── entity/                      # JPA 实体（MySQL）
│   │   └── document/                    # ES 文档模型
│   ├── repository/
│   │   ├── mysql/                       # Spring Data JPA
│   │   ├── es/                          # Spring Data ES
│   │   └── clickhouse/                  # JdbcTemplate ClickHouse
│   ├── service/
│   │   ├── IngestService.java           # 核心写入编排
│   │   ├── CacheService.java            # Redis 缓存 / ZSet 热榜
│   │   ├── ProductSearchService.java    # ES 全文检索
│   │   ├── AnalyticsService.java        # ClickHouse 分析写入
│   │   └── MinioStorageService.java     # 对象存储
│   ├── mq/
│   │   ├── config/RabbitMQConfig.java   # Exchange / Queue / DLQ 声明
│   │   ├── producer/IngestProducer.java
│   │   └── consumer/IngestConsumer.java
│   ├── canal/CanalSyncHandler.java      # MySQL binlog → ES CDC
│   └── config/                          # Minio / ClickHouse / Async / Jackson
├── src/main/resources/
│   ├── application.yml                  # 公共配置
│   ├── application-dev.yml              # 开发环境
│   └── application-prod.yml             # 生产环境
├── src/test/                            # 单元测试
├── Dockerfile                           # 多阶段镜像
├── k8s/
│   ├── configmap.yaml
│   ├── deployment.yaml                  # HPA / topologySpreadConstraints
│   └── service.yaml
└── README.md
```

---

## 数据流

```
L3 ETL (crawler-svc)
        │  HTTP POST /ingest
        ▼
  IngestService
  ├── MySQL  upsert (products / price_history)
  ├── Redis  cache  (product:{id}, ZSet hot-list)
  └── RabbitMQ publish
          ├── ilbuy.q.es        → IngestConsumer → Elasticsearch
          └── ilbuy.q.analytics → IngestConsumer → ClickHouse
                                                          ▲
                                                    Flink Job
                                         (RabbitMQ → enrich → ClickHouse)

Canal (可选)
  MySQL binlog → CanalSyncHandler → Elasticsearch (增量同步)

L5 业务层
  GET /products/search  → ProductSearchService → Elasticsearch
  GET /products/{id}    → CacheService (Redis)  → MySQL fallback
```

---

## 本地快速启动

### 前置依赖

```bash
# 启动依赖中间件（Docker Compose）
docker compose -f ../../infrastructure/docker-compose.dev.yml up -d \
  mysql redis elasticsearch rabbitmq minio clickhouse
```

### 配置

```bash
cd data-svc
# 复制开发配置（无需修改，默认连接 localhost）
# application-dev.yml 已预设所有本地默认值
```

### 运行

```bash
mvn spring-boot:run -Dspring-boot.run.profiles=dev
# 或
mvn package -DskipTests
java -jar target/data-svc-1.0.0.jar --spring.profiles.active=dev
```

### 验证

```bash
# 健康检查
curl http://localhost:8035/health

# 写入商品数据
curl -X POST http://localhost:8035/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "jobId": "test-001",
    "sessionId": "sess-001",
    "products": [{
      "canonical_id": "tb-12345",
      "platform": "TAOBAO",
      "product_id": "12345",
      "title_cleaned": "测试商品",
      "brand_normalised": "测试品牌",
      "price": 99.00,
      "total_score": 88.5,
      "grade": "A",
      "in_stock": true,
      "is_mock": false,
      "crawled_at": "2026-03-15T10:00:00"
    }]
  }'

# 搜索
curl "http://localhost:8035/products/search?keyword=测试&platform=TAOBAO"

# 平台统计
curl http://localhost:8035/stats
```

---

## 运行测试

```bash
mvn test
```

测试覆盖：
- `IngestServiceTest` — 新增/更新/部分失败/空列表场景
- `CacheServiceTest` — Redis ZSet 热榜、缓存读写、异常容忍
- `IngestProducerConsumerTest` — MQ 发送和异常安全
- `IngestControllerTest` — REST 接口参数校验（400/200）

---

## Docker 构建

```bash
docker build -t ilbuy/data-svc:1.0.0 .

docker run -d \
  -p 8035:8035 \
  -e SPRING_PROFILES_ACTIVE=prod \
  -e DB_HOST=mysql \
  -e DB_PASSWORD=secret \
  -e REDIS_HOST=redis \
  -e ES_URIS=http://elasticsearch:9200 \
  -e RABBITMQ_HOST=rabbitmq \
  -e MINIO_ENDPOINT=http://minio:9000 \
  -e MINIO_ACCESS_KEY=minioadmin \
  -e MINIO_SECRET_KEY=minioadmin \
  -e CLICKHOUSE_URL=jdbc:clickhouse://clickhouse:8123/ilbuy_analytics \
  ilbuy/data-svc:1.0.0
```

---

## Kubernetes 部署

```bash
# 1. 创建 Secrets（生产环境先填写真实值）
kubectl create secret generic data-svc-secrets \
  --from-literal=db-password=<DB_PASS> \
  --from-literal=redis-password=<REDIS_PASS> \
  --from-literal=rabbitmq-password=<MQ_PASS> \
  --from-literal=minio-access-key=<MINIO_AK> \
  --from-literal=minio-secret-key=<MINIO_SK> \
  --from-literal=es-password=<ES_PASS> \
  --from-literal=clickhouse-password=<CH_PASS> \
  --from-literal=canal-password=<CANAL_PASS> \
  -n ilbuy

# 2. 应用 K8s 配置
kubectl apply -f k8s/ -n ilbuy

# 3. 验证
kubectl get pods -n ilbuy -l app=data-svc
kubectl get hpa  -n ilbuy data-svc-hpa
```

### HPA 配置

| 参数 | 值 |
|------|----|
| minReplicas | 2 |
| maxReplicas | 8 |
| CPU 目标 | 70% |
| Memory 目标 | 80% |

---

## 核心 API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/ingest` | 批量写入商品数据（L3→L4 入口） |
| GET | `/products/search` | 全文检索（ES） |
| POST | `/products/search` | 全文检索（JSON body） |
| GET | `/products/{canonicalId}/cache` | Redis 缓存查询 |
| GET | `/stats` | 平台统计 + Redis 计数 |
| GET | `/health` | 健康状态 |

### POST /ingest 请求示例

```json
{
  "jobId": "job-20260315-001",
  "sessionId": "sess-abc123",
  "products": [
    {
      "canonical_id": "tb-987654321",
      "platform": "TAOBAO",
      "product_id": "987654321",
      "title_cleaned": "Nike Air Max 2024 运动鞋",
      "brand_normalised": "Nike",
      "price": 899.00,
      "original_price": 1199.00,
      "discount_pct": 25.0,
      "total_score": 91.5,
      "grade": "S",
      "price_score": 88.0,
      "popularity_score": 95.0,
      "rating_score": 92.0,
      "availability_score": 98.0,
      "value_for_money_score": 85.0,
      "sales_count": 15000,
      "review_count": 3200,
      "average_rating": 4.8,
      "in_stock": true,
      "is_mock": false,
      "crawled_at": "2026-03-15T10:30:00"
    }
  ]
}
```

### GET /products/search 参数

| 参数 | 类型 | 说明 |
|------|------|------|
| keyword | String | 全文关键词（IK 分词） |
| platform | String | 平台过滤（TAOBAO/JD/...） |
| brand | String | 品牌过滤 |
| priceMin | BigDecimal | 最低价 |
| priceMax | BigDecimal | 最高价 |
| grade | String | 评级过滤（S/A/B/C） |
| sortBy | String | 排序字段（默认 totalScore） |
| sortOrder | String | ASC/DESC（默认 DESC） |
| page | int | 页码（0起，默认0） |
| size | int | 每页条数（默认20） |

---

## Canal 增量同步（可选）

默认关闭，生产环境启用：

```yaml
# application-prod.yml
ilbuy:
  canal:
    enabled: true
    host: canal-server
    port: 11111
    destination: ilbuy_mysql
    username: canal
    password: ${CANAL_PASSWORD}
```

Canal Server 需提前配置 MySQL binlog 订阅，详见 `infrastructure/canal/` 目录。

---

## 环境变量（生产）

| 变量 | 说明 |
|------|------|
| `DB_HOST` | MySQL 主机 |
| `DB_PORT` | MySQL 端口（默认3306） |
| `DB_NAME` | 数据库名（默认ilbuy） |
| `DB_PASSWORD` | MySQL 密码 |
| `REDIS_HOST` | Redis 主机 |
| `REDIS_PASSWORD` | Redis 密码 |
| `ES_URIS` | ES 地址（逗号分隔） |
| `ES_PASSWORD` | ES 密码 |
| `RABBITMQ_HOST` | RabbitMQ 主机 |
| `RABBITMQ_PASSWORD` | RabbitMQ 密码 |
| `MINIO_ENDPOINT` | MinIO 地址 |
| `MINIO_ACCESS_KEY` | MinIO AK |
| `MINIO_SECRET_KEY` | MinIO SK |
| `CLICKHOUSE_URL` | ClickHouse JDBC URL |
| `CLICKHOUSE_PASSWORD` | ClickHouse 密码 |
| `CANAL_ENABLED` | Canal 开关（true/false） |
| `CANAL_HOST` | Canal Server 主机 |
| `CANAL_PASSWORD` | Canal 密码 |
