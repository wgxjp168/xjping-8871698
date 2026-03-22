# 阶段5：代码二次校验 + 本地/测试环境联调

## 目录结构（标准化）

```
xjping-8871698/
├── README.md                          # 项目说明
├── Makefile                           # 一键操作命令
├── docker-compose.yml                 # 本地全量 Docker 启动
├── .env.example                       # 环境变量模板
│
├── services/                          # 微服务源码
│   ├── api-gateway/                   # API 网关（Flask + Flask-Limiter，端口 8080）
│   │   ├── app.py                     # 路由代理 + JWT 鉴权 + 限流
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   ├── user-service/                  # 用户认证服务（端口 8001）
│   │   ├── app.py                     # 登录/注册/Token 管理
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   ├── procurement-service/           # 采购服务（端口 8002）
│   │   ├── app.py                     # 需求/报价 CRUD
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   ├── ai-matching-service/           # AI 匹配服务（端口 8003）
│   │   ├── app.py                     # 智能供应商匹配
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   ├── order-service/                 # 订单服务（端口 8004）
│   │   ├── app.py                     # 订单全生命周期
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   └── data-collector-service/        # 数据采集服务（端口 8005）
│       ├── app.py                     # 供应商/市场价格数据
│       ├── requirements.txt
│       └── Dockerfile
│
├── k8s/                               # K8s 部署配置
│   ├── namespace-and-rbac.yaml        # 命名空间 + RBAC
│   ├── configmap-and-secrets.yaml     # 配置 + 密钥
│   ├── api-gateway-deployment.yaml    # 网关（3副本 + HPA + Ingress）
│   ├── services-deployment.yaml       # 5个后端服务
│   ├── procurement-service-deployment.yaml  # 采购服务完整配置
│   ├── hpa-and-pdb.yaml              # HPA + PDB
│   └── all-services-quick-deploy.yaml # 快速部署（原有）
│
├── monitoring/                        # 监控配置
│   └── prometheus-rules.yaml          # 8 条 PrometheusRule 告警规则
│
├── scripts/                           # 运维脚本
│   ├── start-local.sh                 # 本地进程启动
│   ├── stop-local.sh                  # 停止所有服务
│   ├── health-check.sh               # 全服务健康检查
│   └── e2e-scenario-test.sh          # B2B 全链路 E2E 测试
│
├── validation/                        # 测试验证（阶段4）
│   ├── run_local.py                   # 单体 Flask 验证服务
│   ├── run_api_tests.sh              # 64条接口测试
│   └── run_ratelimit_perf_tests.py   # 限流 + 性能测试
│
└── docs/
    ├── phase4/                        # 阶段4文档（测试用例+部署手册）
    └── phase5/                        # 阶段5文档（本文件）
        ├── README.md
        └── phase5-acceptance-report.md
```

## 快速启动

```bash
# 方式1: 本地进程（无 Docker，推荐开发）
make start
make health
make e2e

# 方式2: Docker Compose（需要 Docker）
make docker-up

# 方式3: K8s（需要 kubectl 和集群）
make k8s-deploy
make k8s-status
```
