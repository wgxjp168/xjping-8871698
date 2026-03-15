# crawler-svc — L3 数据采集服务

## 概览

| 项目       | 值                  |
|------------|---------------------|
| 端口       | 8030                |
| 技术栈     | Python 3.11 / FastAPI / APScheduler / httpx |
| 上游       | L2 `decision-svc`（POST /crawl/search）|
| 下游       | `etl-svc:8031`（自动 POST /etl/process）|
| 平台支持   | 淘宝 / 京东 / 1688 / 拼多多 / 唯品会 / 苏宁 / 抖音 |

## 核心功能

- **7大电商平台API封装**：统一 `BasePlatformAdapter` 接口，各平台独立实现签名/解析
- **API频率控制**：TokenBucket 算法，每平台独立 RPM 限制
- **错误重试 + 熔断**：指数退避重试（可配置），CircuitBreaker 防止级联故障
- **代理IP池**：轮询 + 成功率加权随机，自动健康检查，失败自动剔除
- **合规监控**：解析 robots.txt，强制 crawl-delay，可配置最小延迟
- **定时/即时采集**：APScheduler cron 任务 + 按需 job 提交，异步并发执行
- **ETL对接**：采集完成后自动 POST 到 etl-svc，支持 callback_url 自定义

## 快速启动

```bash
cd microservices/l3-data-process/crawler-svc

# 安装依赖
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 本地开发启动
ENV=development uvicorn app.main:app --reload --port 8030

# 运行测试
pip install pytest pytest-asyncio
pytest tests/ -v
```

## 环境变量

| 变量                    | 默认值                          | 说明                  |
|-------------------------|--------------------------------|-----------------------|
| `ENV`                   | `production`                   | 运行环境              |
| `PORT`                  | `8030`                         | 服务端口              |
| `ETL_SVC_URL`           | `http://etl-svc:8031`          | ETL服务地址           |
| `DECISION_SVC_URL`      | `http://decision-svc:8012`     | L2决策服务地址        |
| `REDIS_URL`             | `redis://redis:6379/2`         | Redis地址             |
| `PROXY_ENABLED`         | `false`                        | 是否启用代理IP池      |
| `TAOBAO_APP_KEY`        | `""`                           | 淘宝开放平台AppKey    |
| `JD_APP_KEY`            | `""`                           | 京东开放平台AppKey    |
| `PDD_CLIENT_ID`         | `""`                           | 拼多多客户端ID        |
| `TAOBAO_RPM`            | `30`                           | 淘宝每分钟请求上限    |

> **注意**：API Key 为空时自动使用模拟数据（mock），适合本地开发/测试。

## API 端点

```
POST /crawl/search          触发按需采集（L2 调用）
GET  /crawl/jobs/{job_id}   查询任务状态
GET  /crawl/jobs            列出活跃任务
POST /crawl/schedule        注册定时任务
GET  /crawl/schedule        列出定时任务
DELETE /crawl/schedule/{id} 删除定时任务
POST /proxy/add             添加代理IP
GET  /proxy/stats           代理池统计
GET  /compliance/report     合规状态报告
GET  /info                  平台状态
GET  /health                健康检查
GET  /docs                  Swagger UI
```

## Docker 构建

```bash
docker build -t ilbuy/crawler-svc:1.0.0 .
docker run -p 8030:8030 \
  -e ENV=development \
  ilbuy/crawler-svc:1.0.0
```

## K8s 部署

```bash
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
```
