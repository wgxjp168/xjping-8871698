# L6 报告输出层 (Report Output Layer)

**我来购ILbuy 智能采购报告平台** — 第6层：报告输出层

---

## L6层服务清单

| 服务 | 技术栈 | 端口 | 职责 |
|-----|--------|------|------|
| **report-generator-svc** | Java 17 / Spring Boot 3.2 | 8061 | B2B/B2C报告类型生成 (策略模式) |
| **format-output-svc** | Java 17 / Spring Boot 3.2 | 8062 | HTML/PDF/Excel/JSON多格式输出 |
| **channel-delivery-svc** | Node.js 20 / Express 4 | 8063 | Web/邮件/微信/App多渠道交付 |

---

## 架构图

```
L5 REPORT_SVC (port 8051)
       │
       │ RabbitMQ: l5.report.exchange → l6.report.generate.request
       ▼
┌─────────────────────────────────┐
│   report-generator-svc :8061   │   Java / Spring Boot 3.2
│                                 │
│  策略路由 (ClientType)          │
│  ├── B2BReportGenerator        │   6个B2B专属章节
│  ├── B2CDefinedBrandGenerator  │   6个已定品牌章节
│  └── B2CUndefinedBrandGenerator│   6个未定品牌章节
└────────────┬────────────────────┘
             │ HTTP POST /internal/v1/format-jobs
             ▼
┌─────────────────────────────────┐
│   format-output-svc :8062      │   Java / Spring Boot 3.2
│                                 │
│  ├── HtmlFormatter (Thymeleaf) │ → MinIO (ilbuy-reports-html)
│  ├── PdfFormatter (FlyingSaucer│ → MinIO (ilbuy-reports-pdf)
│  └── ExcelFormatter (Apache POI│ → MinIO (ilbuy-reports-excel)
└────────────┬────────────────────┘
             │ HTTP POST /internal/v1/deliveries
             ▼
┌─────────────────────────────────┐
│  channel-delivery-svc :8063   │   Node.js 20 / Express
│                                 │
│  ├── Web门户  → Redis Pub/Sub  │
│  ├── 邮件     → SMTP (Nodemailer)│
│  ├── 微信公众号→ 模板消息API   │
│  └── 移动App  → 统一推送网关   │
└─────────────────────────────────┘
             │
             │ 预留接口
             ├──→ L7 商业变现层 (monetize-hook)
             └──→ L8 反馈优化层 (feedback-hook)
```

---

## 报告类型矩阵

| 客户类型 | 报告章节 |
|---------|---------|
| **B2B** 企业采购 | 执行摘要 · 供应商格局 · 价格基准 · 合规检查 · 风险评估 · 采购建议 |
| **B2C_DEFINED** 已定品牌 | 品牌分析 · 价格对比 · 竞争对手 · 渠道表现 · 市场份额 · 战略洞察 |
| **B2C_UNDEFINED** 未定品牌 | 市场总览 · 品类趋势 · 品牌发现 · 价格区间 · 消费者情感 · 入场策略 |

---

## 数据库表

| 表名 | 服务 | 说明 |
|-----|------|------|
| l6_report_jobs | report-generator-svc | 生成任务记录 |
| l6_report_sections | report-generator-svc | 报告章节数据 |
| l6_format_jobs | format-output-svc | 格式化任务记录 |
| l6_format_access_log | format-output-svc | 文件访问日志 |
| l6_delivery_tasks | channel-delivery-svc | 交付任务记录 |
| l6_channel_logs | channel-delivery-svc | 渠道交付日志 |

---

## 一键本地启动

```bash
# 1. 启动基础设施
docker-compose -f ../../infra/docker-compose.yml up -d postgres rabbitmq redis minio

# 2. 启动 report-generator-svc
cd report-generator-svc && mvn spring-boot:run -Dspring-boot.run.profiles=dev &

# 3. 启动 format-output-svc
cd format-output-svc && mvn spring-boot:run -Dspring-boot.run.profiles=dev &

# 4. 启动 channel-delivery-svc
cd channel-delivery-svc && npm install && npm run dev &
```

---

## K8s全量部署

```bash
kubectl create namespace ilbuy-l6
kubectl apply -f report-generator-svc/k8s/configmap.yaml
kubectl apply -f report-generator-svc/k8s/deployment.yaml
kubectl apply -f format-output-svc/k8s/deployment.yaml
kubectl apply -f channel-delivery-svc/k8s/deployment.yaml

# 验证
kubectl get pods -n ilbuy-l6
kubectl get svc -n ilbuy-l6
```

---

## 与上下游层的接口

| 方向 | 接口 | 说明 |
|-----|------|------|
| ← L5 REPORT_SVC | RabbitMQ queue `l6.report.generate.request` | 报告生成请求 |
| ← L5 REPORT_SVC | HTTP GET `/internal/v1/reports/{no}/data` | 获取报告数据 |
| → L7 商业变现层 | POST `/{id}/monetize-hook` | 付费报告/水印/升级推送（预留）|
| → L8 反馈优化层 | POST `/{id}/feedback-hook` | 用户评分/模型反馈（预留）|
