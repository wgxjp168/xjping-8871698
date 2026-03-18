# model-deploy-svc

L8 模型部署服务 | Python/FastAPI | Port: 8063

## 功能

- 消费 `l8.model.ready` 事件，自动部署经过评估的 ML 模型
- 蓝绿部署策略（Blue/Green）
- 模型版本管理与回滚
- 发布 `l8.model.deployed` 事件通知下游

## 数据流

```
model-iteration-svc → [l8.model.ready] → model-deploy-svc
                                          ↓ blue/green deploy
                                    [l8.model.deployed] → monitoring
```

## 本地启动

```bash
cp .env.dev .env
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8063
```

## 测试

```bash
pytest tests/ -v
```
