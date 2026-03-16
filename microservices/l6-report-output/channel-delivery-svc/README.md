# channel-delivery-svc — L6 渠道交付服务

**技术栈**: Node.js 20 / Express 4 / Nodemailer / WeChat MP API / MinIO / PostgreSQL / Redis
**端口**: 8063
**职责**: 接收format-output-svc触发的交付请求，通过Web门户/移动App/邮件/微信公众号四大渠道完成报告交付，支持访问控制和交付日志。

---

## 交付渠道

| 渠道 | 技术 | 说明 |
|-----|------|------|
| Web门户 | Redis Pub/Sub + REST | 实时通知 + 用户通知列表，支持SSE/WebSocket |
| 邮件 | Nodemailer + SMTP | 精美HTML邮件模板，含报告下载直链 |
| 微信公众号 | 微信模板消息API | 模板消息推送，含小程序跳转链接 |
| 移动App | 统一推送网关 | 支持FCM/APNs，带有Deep Link跳转 |

---

## 目录结构

```
channel-delivery-svc/
├── src/
│   ├── app.js                        # Express应用入口
│   ├── config/
│   │   ├── database.js               # Knex PostgreSQL配置
│   │   ├── redis.js                  # ioredis配置
│   │   ├── logger.js                 # Winston日志
│   │   └── env.js                    # 环境变量集中管理
│   ├── migrations/
│   │   └── 20240101000000_init_delivery.js
│   ├── middleware/
│   │   ├── errorHandler.js
│   │   └── requestLogger.js
│   ├── models/
│   │   └── DeliveryTask.js           # DB操作模型
│   ├── routes/
│   │   ├── delivery.routes.js        # 交付API
│   │   └── health.routes.js          # 健康检查
│   └── services/
│       ├── deliveryOrchestrator.js   # 多渠道并发编排
│       ├── emailService.js           # 邮件交付
│       ├── wechatService.js          # 微信公众号交付
│       ├── appPushService.js         # 移动App推送
│       └── webPortalService.js       # Web门户通知
├── tests/
│   ├── delivery.test.js
│   └── deliveryOrchestrator.test.js
├── k8s/
├── .env.example
├── Dockerfile
└── README.md
```

---

## 核心数据流

```
format-output-svc
    │ POST /internal/v1/deliveries
    ▼
deliveryOrchestrator.orchestrate()
    │ (并发执行)
    ├──→ webPortalService.notifyReportReady()   → Redis Pub/Sub
    ├──→ emailService.sendReportEmail()         → SMTP
    ├──→ wechatService.sendTemplateMessage()    → 微信公众号 API
    └──→ appPushService.sendPush()              → 统一推送网关
    │
    ▼ 日志写入 l6_channel_logs
```

---

## 本地开发启动

### 前置依赖

```bash
# PostgreSQL + Redis
docker run -d --name postgres-l6 -p 5432:5432 \
  -e POSTGRES_DB=ilbuy_l6 -e POSTGRES_USER=ilbuy -e POSTGRES_PASSWORD=ilbuy123 \
  postgres:15-alpine

docker run -d --name redis-l6 -p 6379:6379 redis:7-alpine
```

### 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 填入真实配置
```

### 安装依赖并启动

```bash
npm install
npm run dev    # 开发模式（nodemon热重载）
# 或
npm start      # 生产模式
```

### 运行测试

```bash
npm test
```

---

## Docker

```bash
docker build -t ilbuy/channel-delivery-svc:latest .
docker run -p 8063:8063 --env-file .env ilbuy/channel-delivery-svc:latest
```

---

## K8s部署

```bash
kubectl apply -f k8s/deployment.yaml
kubectl rollout status deployment/channel-delivery-svc -n ilbuy-l6
```

---

## API接口

| 方法 | 路径 | 说明 |
|-----|------|------|
| POST | /internal/v1/deliveries | 触发多渠道交付 |
| GET | /internal/v1/deliveries/:deliveryNo | 查询交付状态和渠道日志 |
| GET | /internal/v1/deliveries/user/:userId/notifications | 获取用户通知列表 |
| GET | /internal/v1/deliveries/access-check/:l5ReportNo/:userId | 报告访问权限验证 |
| POST | /internal/v1/deliveries/:deliveryNo/monetize-hook | L7商业变现层接口预留 |
| POST | /internal/v1/deliveries/:deliveryNo/feedback-hook | L8反馈优化层接口预留 |
| GET | /actuator/health | 综合健康检查 |
