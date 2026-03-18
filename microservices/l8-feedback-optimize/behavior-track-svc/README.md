# behavior-track-svc

L8 用户行为追踪服务 | Python/FastAPI | Port: 8061

## 功能

- 用户点击/页面浏览/报告查看/转化/满意度信号追踪
- 单条/批量埋点接口（每批最多500条）
- ClickHouse(L4)写入，MergeTree引擎，按月分区，365天TTL
- 转化漏斗追踪（VIEW→DETAIL→CART→PURCHASE）
- 消费 `l8.feedback.collected`，生成满意度行为信号
- 定时聚合 → 发布 `l8.behavior.aggregated` → model-iteration-svc

## 数据流

```
L8 feedback-svc → [l8.feedback.collected] → behavior-track-svc
Client SDK → POST /api/v1/track/event → ClickHouse(L4)
behavior-track-svc → [l8.behavior.aggregated] → model-iteration-svc
```

## 本地启动

```bash
cp .env.dev .env
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8061
```

## 测试

```bash
pytest tests/ -v
```

## API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/v1/track/event | 单条埋点 |
| POST | /api/v1/track/batch | 批量埋点(max 500) |
| GET | /api/v1/track/funnel/{reportId} | 转化漏斗 |
| GET | /api/v1/track/session/{userId} | 用户会话 |
| GET | /api/v1/track/metrics | 汇总指标 |
