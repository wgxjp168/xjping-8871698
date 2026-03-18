# L9 运维支撑层 — ILbuy 我来购

## 概述

L9 是 ILbuy 平台的运维支撑层，为 L1-L8 所有微服务提供：

| 能力域 | 组件 | 端口/访问 |
|--------|------|----------|
| 指标采集 | Prometheus 2.51 | 9090 |
| 监控看板 | Grafana 10.4 | 3000 |
| 告警引擎 | AlertManager 0.27 | 9093 |
| 分布式追踪 | Jaeger 1.57 | 16686 |
| 日志采集 | Filebeat → Logstash → ES | — |
| 日志存储 | Elasticsearch 8.13 | 9200 |
| 日志看板 | Kibana 8.13 | 5601 |
| 配置中心 | Nacos 2.3 | 8848 |
| Secret管理 | Vault 1.16 | 8200 |
| CI/CD | Jenkins 2.460 + GitLab CI | 8080 |
| 代码质量 | SonarQube 10.5 | 9000 |

## 快速部署

### 前置条件

- Kubernetes 1.29+，kubectl 已配置
- Helm 3.14+
- Docker 25+（镜像构建节点）
- 存储类 `ilbuy-ssd`（ReadWriteOnce）和 `ilbuy-nfs`（ReadWriteMany）

### 1. 初始化命名空间和基础资源

```bash
kubectl apply -f k8s/namespaces.yaml
kubectl apply -f k8s/rbac.yaml
kubectl apply -f k8s/storage/pvcs.yaml
kubectl apply -f k8s/network-policy/default-deny.yaml
```

### 2. 部署可观测性栈

```bash
# Prometheus + AlertManager
kubectl apply -f observability/prometheus/k8s/deployment.yaml
kubectl apply -f observability/alertmanager/k8s/deployment.yaml

# Grafana
kubectl apply -f observability/grafana/k8s/deployment.yaml

# ELK
kubectl apply -f observability/elk/elasticsearch/k8s/statefulset.yaml
kubectl apply -f observability/elk/logstash/k8s/deployment.yaml
kubectl apply -f observability/elk/kibana/k8s/deployment.yaml
kubectl apply -f observability/elk/filebeat/k8s/daemonset.yaml

# Jaeger
kubectl apply -f observability/jaeger/k8s/deployment.yaml
```

### 3. 部署配置管理

```bash
# Nacos 集群
kubectl apply -f config-management/nacos/k8s/statefulset.yaml
# 等待 Nacos 就绪后初始化配置
kubectl exec -n ilbuy-ops nacos-0 -- bash /scripts/init-configs.sh

# Vault
kubectl apply -f config-management/vault/k8s/deployment.yaml
# 初始化 Vault
bash config-management/vault/scripts/init-vault.sh
```

### 4. 部署 CI/CD

```bash
kubectl apply -f cicd/jenkins/k8s/deployment.yaml
kubectl apply -f cicd/sonarqube/k8s/deployment.yaml
```

### 5. 配置 Ingress

```bash
kubectl apply -f k8s/ingress/ingress.yaml
```

## 访问地址（生产 Ingress）

| 服务 | URL |
|------|-----|
| Grafana | https://grafana.ilbuy.internal |
| Prometheus | https://prometheus.ilbuy.internal |
| AlertManager | https://alertmanager.ilbuy.internal |
| Jaeger | https://jaeger.ilbuy.internal |
| Kibana | https://kibana.ilbuy.internal |
| Nacos | https://nacos.ilbuy.internal |
| Jenkins | https://jenkins.ilbuy.internal |
| SonarQube | https://sonar.ilbuy.internal |

## 运维脚本

```bash
# 发布服务
bash scripts/deploy.sh -s <service-name> -t <image-tag> -n <namespace>

# 回滚
bash scripts/rollback.sh -s <service-name> -n <namespace> [-t <tag>]

# 全服务健康检查
bash scripts/health-check.sh

# 数据备份
bash scripts/backup.sh
```

## 与 L1-L8 集成方式

所有微服务通过以下方式集成 L9：

1. **指标**：`/actuator/prometheus` 端点，Prometheus Operator ServiceMonitor 自动发现
2. **日志**：标准输出 JSON 格式，Filebeat DaemonSet 自动采集
3. **追踪**：OpenTelemetry SDK，Jaeger Collector 接收（OTLP gRPC:4317）
4. **配置**：通过 Nacos Spring/Python SDK 拉取，Vault Agent Injector 注入 Secret

## 目录说明

```
l9-ops-support/
├── observability/   # Prometheus/Grafana/Alertmanager/Jaeger/ELK
├── config-management/ # Nacos + Vault
├── cicd/            # Jenkins + GitLab CI + SonarQube
├── k8s/             # 集群基础配置（NS/RBAC/PVC/Ingress）
└── scripts/         # 运维脚本
```
