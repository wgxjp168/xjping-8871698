# 阶段4：我来购ILbuy 全量测试用例 + 生产部署手册

## 文档目录

```
docs/phase4/
├── README.md                              ← 本文件（目录索引）
│
├── test-cases/                            ← 测试用例
│   ├── 01-unit-test-cases.md             ← 单元测试用例（JUnit5+Mockito）
│   ├── 02-api-test-cases.md              ← 接口测试用例（Postman/Newman）
│   ├── 03-integration-test-cases.md      ← 集成测试用例（TestContainers）
│   └── 04-scenario-test-cases.md         ← 场景测试用例（B2B/B2C/异常）
│
├── postman/                               ← Postman 测试集合
│   ├── ilbuy_api_tests.postman_collection.json   ← 可直接导入Postman
│   └── ilbuy_test_env.postman_environment.json   ← 环境变量配置
│
├── jmeter/                                ← JMeter 性能测试
│   ├── ilbuy_performance_test.jmx        ← JMeter测试脚本（可直接导入）
│   ├── test_users.csv                    ← 测试用户数据
│   ├── product_keywords.csv             ← 商品关键词数据
│   └── README-jmeter.md                 ← JMeter使用说明
│
├── test-reports/                          ← 测试报告
│   └── test-report-template.md          ← 测试报告模板
│
├── deployment/                            ← 生产部署手册
│   ├── 01-production-deployment-manual.md ← 完整部署手册（带命令）
│   └── 02-troubleshooting-guide.md       ← 故障排查手册
│
├── k8s/                                   ← K8s 部署配置
│   ├── all-services-quick-deploy.yaml    ← 全量服务快速部署（一键）
│   ├── api-gateway-deployment.yaml       ← API网关详细配置
│   └── procurement-service-deployment.yaml ← 采购服务详细配置（含HPA/PDB）
│
└── monitoring/                            ← 监控运维
    └── 03-ops-runbook.md                 ← 运维手册（监控/日志/备份/发布）
```

---

## 快速开始

### 一、导入 Postman 测试集合

```bash
# 方式1：Postman GUI导入
# 打开Postman → Import → 选择以下两个文件：
# - postman/ilbuy_api_tests.postman_collection.json
# - postman/ilbuy_test_env.postman_environment.json

# 方式2：Newman命令行运行
npm install -g newman newman-reporter-htmlextra

newman run postman/ilbuy_api_tests.postman_collection.json \
  -e postman/ilbuy_test_env.postman_environment.json \
  -r cli,htmlextra \
  --reporter-htmlextra-export reports/api-test-report.html
```

### 二、运行 JMeter 性能测试

```bash
# 下载JMeter 5.6.2
wget https://archive.apache.org/dist/jmeter/binaries/apache-jmeter-5.6.2.tgz
tar xzf apache-jmeter-5.6.2.tgz

# 运行性能测试
./apache-jmeter-5.6.2/bin/jmeter -n \
  -t jmeter/ilbuy_performance_test.jmx \
  -JBASE_URL=your-test-env.ilbuy.com \
  -JPROTOCOL=https \
  -l results/perf_result.jtl \
  -e -o reports/perf_report/
```

### 三、执行 K8s 部署

```bash
# 一键部署所有服务
kubectl apply -f k8s/all-services-quick-deploy.yaml

# 部署API网关
kubectl apply -f k8s/api-gateway-deployment.yaml -n ilbuy-prod

# 部署采购服务
kubectl apply -f k8s/procurement-service-deployment.yaml -n ilbuy-prod

# 查看部署状态
kubectl get pods -n ilbuy-prod -w
```

---

## 测试覆盖范围

| 测试类型 | 覆盖模块 | 用例数量 | 工具 |
|---------|---------|---------|------|
| 单元测试 | 全部微服务核心类 | ~50条 | JUnit5+Mockito |
| 接口测试 | 40+个REST接口 | ~40条 | Postman/Newman |
| 集成测试 | 微服务间调用+MQ | ~10条 | TestContainers |
| 性能测试 | 5大核心接口场景 | 5场景 | JMeter |
| 场景测试 | B2B/B2C/异常 | ~10条 | 手工+自动化 |

---

## 部署手册关键章节

| 章节 | 说明 |
|------|------|
| 服务器初始化 | OS配置、Docker安装、K8s节点初始化 |
| K8s集群搭建 | 3Master高可用集群、Calico网络 |
| 中间件部署 | MySQL主从、Redis集群、Kafka、Nacos |
| Nacos配置导入 | 批量导入应用配置脚本 |
| 微服务部署 | 镜像构建推送、K8s Deployment部署 |
| 服务校验 | 健康检查、冒烟测试脚本 |
| 高可用配置 | PodAntiAffinity、HPA、PDB |
| 故障排查 | 7类常见故障诊断和解决方案 |
| 监控告警 | Prometheus规则、Grafana Dashboard |
| 日志查询 | ELK配置、Kibana查询语句 |
| 数据备份 | MySQL自动备份脚本（定时任务） |
| 滚动发布 | 零停机更新脚本、自动回滚 |
