# feedback-svc

L8 用户反馈服务 | Python/FastAPI | Port: 8060

## 功能

- 用户AI报告满意度反馈采集（1-5星评分 + 评论）
- SnowNLP 中文情感分析（正向/中性/负向）+ 关键词增强
- AI满意度回访调度（L6 delivery.completed事件触发，24h后发送）
- 发布 `l8.feedback.collected` 事件供行为追踪层消费

## 数据流

```
L6 delivery-svc → [l6.delivery.completed] → feedback-svc
                                              ↓ schedule 24h followup
User feedback → POST /api/v1/feedback → NLP sentiment → [l8.feedback.collected] → behavior-track-svc
```

## 本地启动

```bash
cp .env.dev .env
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8060
```

## 测试

```bash
pytest tests/ -v
```

## API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/v1/feedback | 提交反馈 |
| GET | /api/v1/feedback/{id} | 获取反馈详情 |
| GET | /api/v1/feedback/report/{reportId} | 按报告查询 |
| GET | /api/v1/feedback/analytics/summary | 汇总分析 |
| GET | /health/liveness | 存活探针 |
| GET | /health/readiness | 就绪探针 |
