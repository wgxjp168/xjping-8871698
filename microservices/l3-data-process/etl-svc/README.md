# etl-svc — L3 ETL数据清洗服务

## 概览

| 项目       | 值                                          |
|------------|---------------------------------------------|
| 端口       | 8031                                        |
| 技术栈     | Python 3.11 / FastAPI / httpx               |
| 上游       | `crawler-svc:8030`（POST /etl/process）     |
| 下游       | L4 `l4-data-svc:8040`（接口预留，POST /ingest）|

## ETL 流水线

```
crawler-svc → [清洗] → [去重] → [评分预计算] → [标准化] → L4数据层
```

1. **清洗（Cleaner）**：验证必填字段，去除HTML/emoji，修正价格范围，过滤非法URL
2. **去重（Deduplicator）**：同平台按product_id去重，跨平台按标题指纹+价格相似度去重
3. **评分预计算（Scorer）**：5维度加权评分（价格/热度/评价/库存/性价比），输出0-100分 + A-D等级
4. **标准化（Normalizer）**：品牌别名映射、类目路径解析、规格值标准化、生成canonical_id

## 快速启动

```bash
cd microservices/l3-data-process/etl-svc

python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 启动服务
ENV=development uvicorn app.main:app --reload --port 8031

# 运行测试
pip install pytest pytest-asyncio
pytest tests/ -v
```

## 测试 ETL 流程

```bash
curl -X POST http://localhost:8031/etl/process \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "test-job-001",
    "session_id": "sess-001",
    "raw_products": [{
      "platform": "jd",
      "product_id": "jd_12345",
      "title": "小米13 Pro 手机 黑色 256GB",
      "price": 3999.0,
      "original_price": 4499.0,
      "brand": "小米",
      "category": "手机>智能手机",
      "specs": {"颜色": "黑色", "存储": "256GB"},
      "images": ["https://img.jd.com/product.jpg"],
      "sales_count": 5000,
      "review_count": 2000,
      "average_rating": 4.7,
      "in_stock": true,
      "delivery_days": 2
    }],
    "deduplicate": true,
    "normalize": true,
    "compute_scores": true
  }'
```

## 环境变量

| 变量                  | 默认值                         | 说明                     |
|-----------------------|-------------------------------|--------------------------|
| `ENV`                 | `production`                  | 运行环境                 |
| `PORT`                | `8031`                        | 服务端口                 |
| `L4_DATA_SVC_URL`     | `http://l4-data-svc:8040`     | L4数据服务地址（预留）   |
| `L4_INGEST_ENABLED`   | `false`                       | 是否启用L4转发           |
| `REDIS_URL`           | `redis://redis:6379/3`        | Redis地址（去重缓存）    |
| `MAX_BATCH_SIZE`      | `1000`                        | 单批次最大商品数         |
| `WEIGHT_PRICE`        | `0.25`                        | 价格维度权重             |
| `WEIGHT_POPULARITY`   | `0.25`                        | 热度维度权重             |
| `WEIGHT_RATING`       | `0.25`                        | 评分维度权重             |
| `WEIGHT_AVAILABILITY` | `0.15`                        | 库存/物流维度权重        |
| `WEIGHT_VALUE`        | `0.10`                        | 性价比维度权重           |

## API 端点

```
POST /etl/process    接收并处理采集数据批次
GET  /etl/stats      流水线统计信息
GET  /health         健康检查
GET  /docs           Swagger UI
```

## L4 接口预留

当 `L4_INGEST_ENABLED=true` 时，ETL完成后异步 POST 到：
```
POST {L4_DATA_SVC_URL}/ingest
Body: { job_id, session_id, products: [CleanProduct...] }
```

## Docker 构建

```bash
docker build -t ilbuy/etl-svc:1.0.0 .
docker run -p 8031:8031 -e ENV=development ilbuy/etl-svc:1.0.0
```
