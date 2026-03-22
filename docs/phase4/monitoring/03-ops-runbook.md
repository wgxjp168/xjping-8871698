# 我来购ILbuy 日常运维手册

---

## 一、监控配置（Prometheus + Grafana）

### Step 1：部署 Prometheus Stack

```bash
# 添加kube-prometheus-stack Helm仓库
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

# 安装完整监控栈
helm install kube-prometheus-stack prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace \
  --set prometheus.prometheusSpec.retention=30d \
  --set prometheus.prometheusSpec.storageSpec.volumeClaimTemplate.spec.storageClassName=standard \
  --set prometheus.prometheusSpec.storageSpec.volumeClaimTemplate.spec.resources.requests.storage=100Gi \
  --set grafana.adminPassword=ILbuy@Grafana2024 \
  --set grafana.persistence.enabled=true \
  --set grafana.persistence.size=10Gi \
  --set alertmanager.alertmanagerSpec.storage.volumeClaimTemplate.spec.resources.requests.storage=10Gi \
  -f monitoring-values.yaml

# 等待就绪
kubectl wait --for=condition=Ready pod -l app.kubernetes.io/name=prometheus -n monitoring --timeout=300s

# 获取Grafana访问地址
kubectl get svc kube-prometheus-stack-grafana -n monitoring
```

### Step 2：配置应用指标采集

**ServiceMonitor配置（ilbuy-service-monitor.yaml）：**

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: ilbuy-services-monitor
  namespace: monitoring
  labels:
    release: kube-prometheus-stack
spec:
  namespaceSelector:
    matchNames:
    - ilbuy-prod
  selector:
    matchLabels:
      monitoring: "true"
  endpoints:
  - port: management
    path: /actuator/prometheus
    interval: 15s
    scrapeTimeout: 10s
```

```bash
kubectl apply -f ilbuy-service-monitor.yaml

# 给需要监控的Service加标签
kubectl label svc procurement-service monitoring=true -n ilbuy-prod
kubectl label svc ai-matching-service monitoring=true -n ilbuy-prod
kubectl label svc order-service monitoring=true -n ilbuy-prod
```

### Step 3：Grafana Dashboard 导入

```bash
# 访问Grafana（通过port-forward）
kubectl port-forward svc/kube-prometheus-stack-grafana 3000:80 -n monitoring

# 导入ILbuy自定义Dashboard（Dashboard ID或JSON文件）
# 推荐导入的Dashboard：
# - JVM Overview: ID 4701
# - Spring Boot Statistics: ID 6756
# - Kubernetes Pod Monitoring: ID 6781
# - MySQL Overview: ID 7362
# - Redis Dashboard: ID 11835
# - Kafka Overview: ID 7589

# 通过API批量导入
curl -X POST http://admin:ILbuy@Grafana2024@localhost:3000/api/dashboards/import \
  -H "Content-Type: application/json" \
  -d @dashboards/ilbuy-overview.json
```

---

### 告警规则配置

```yaml
# ilbuy-alerts.yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: ilbuy-alerts
  namespace: monitoring
  labels:
    release: kube-prometheus-stack
spec:
  groups:
  - name: ilbuy.service
    rules:
    # Pod重启告警
    - alert: PodRestartingFrequently
      expr: rate(kube_pod_container_status_restarts_total{namespace="ilbuy-prod"}[15m]) > 0
      for: 5m
      labels:
        severity: warning
        team: ops
      annotations:
        summary: "Pod {{ $labels.pod }} 频繁重启"
        description: "Pod {{ $labels.pod }} 在过去15分钟内重启 {{ $value | humanize }} 次"

    # 服务不可用告警
    - alert: ServiceDown
      expr: up{job=~"ilbuy.*"} == 0
      for: 2m
      labels:
        severity: critical
        team: ops
      annotations:
        summary: "服务 {{ $labels.job }} 不可用"
        description: "服务 {{ $labels.job }} 已宕机超过2分钟"

    # 高错误率告警
    - alert: HighErrorRate
      expr: |
        sum(rate(http_server_requests_seconds_count{namespace="ilbuy-prod", status=~"5.."}[5m]))
        / sum(rate(http_server_requests_seconds_count{namespace="ilbuy-prod"}[5m])) > 0.05
      for: 3m
      labels:
        severity: critical
      annotations:
        summary: "HTTP错误率过高：{{ $value | humanizePercentage }}"

    # 响应时间告警
    - alert: SlowAPIResponse
      expr: |
        histogram_quantile(0.99,
          sum(rate(http_server_requests_seconds_bucket{namespace="ilbuy-prod"}[5m])) by (le, uri)
        ) > 2
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "接口 {{ $labels.uri }} P99延迟超过2秒"

    # JVM内存告警
    - alert: JvmMemoryHigh
      expr: |
        jvm_memory_used_bytes{namespace="ilbuy-prod", area="heap"}
        / jvm_memory_max_bytes{namespace="ilbuy-prod", area="heap"} > 0.85
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "JVM堆内存使用率超过85%：{{ $labels.pod }}"

    # MySQL复制延迟告警
    - alert: MySQLReplicationLag
      expr: mysql_slave_status_seconds_behind_master > 60
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "MySQL主从延迟超过60秒：{{ $value }}s"

    # Redis内存告警
    - alert: RedisMemoryHigh
      expr: redis_memory_used_bytes / redis_memory_max_bytes > 0.80
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "Redis内存使用率超过80%"

    # Kafka消费积压告警
    - alert: KafkaConsumerLag
      expr: kafka_consumergroup_lag_sum{consumergroup="ilbuy-matching-group"} > 1000
      for: 10m
      labels:
        severity: warning
      annotations:
        summary: "Kafka消费积压超过1000条：{{ $value }}"
```

```bash
kubectl apply -f ilbuy-alerts.yaml
```

---

## 二、日志查询（ELK Stack）

### Step 1：部署 ELK Stack

```bash
# 使用ECK（Elastic Cloud on Kubernetes）部署
kubectl create -f https://download.elastic.co/downloads/eck/2.9.0/crds.yaml
kubectl apply -f https://download.elastic.co/downloads/eck/2.9.0/operator.yaml

# 部署Elasticsearch集群
cat << 'EOF' | kubectl apply -f -
apiVersion: elasticsearch.k8s.elastic.co/v1
kind: Elasticsearch
metadata:
  name: ilbuy-es
  namespace: logging
spec:
  version: 8.10.2
  nodeSets:
  - name: default
    count: 3
    config:
      node.store.allow_mmap: false
      xpack.security.enabled: true
    podTemplate:
      spec:
        containers:
        - name: elasticsearch
          resources:
            limits:
              memory: 16Gi
              cpu: 4
            requests:
              memory: 8Gi
              cpu: 2
          env:
          - name: ES_JAVA_OPTS
            value: "-Xms4g -Xmx4g"
    volumeClaimTemplates:
    - metadata:
        name: elasticsearch-data
      spec:
        accessModes:
        - ReadWriteOnce
        resources:
          requests:
            storage: 1Ti
        storageClassName: standard
EOF

# 部署Kibana
cat << 'EOF' | kubectl apply -f -
apiVersion: kibana.k8s.elastic.co/v1
kind: Kibana
metadata:
  name: ilbuy-kibana
  namespace: logging
spec:
  version: 8.10.2
  count: 1
  elasticsearchRef:
    name: ilbuy-es
  http:
    tls:
      selfSignedCertificate:
        disabled: true
EOF
```

### Step 2：部署 Filebeat（日志采集）

```yaml
# filebeat-daemonset.yaml（DaemonSet方式，每节点一个）
apiVersion: beat.k8s.elastic.co/v1beta1
kind: Beat
metadata:
  name: filebeat
  namespace: logging
spec:
  type: filebeat
  version: 8.10.2
  elasticsearchRef:
    name: ilbuy-es
  config:
    filebeat.inputs:
    - type: container
      paths:
      - /var/log/containers/*ilbuy-prod*.log
      processors:
      - add_kubernetes_metadata:
          host: ${NODE_NAME}
          matchers:
          - logs_path:
              logs_path: "/var/log/containers/"
      - decode_json_fields:
          fields: ["message"]
          target: ""
          overwrite_keys: true
      - drop_event:
          when:
            or:
            - equals:
                kubernetes.labels.app: "kube-proxy"
            - equals:
                kubernetes.labels.app: "calico-node"
    output.elasticsearch:
      hosts:
      - https://ilbuy-es-es-http.logging:9200
      index: "ilbuy-logs-%{+yyyy.MM.dd}"
      ssl.verification_mode: none
    setup.ilm.enabled: true
    setup.ilm.policy_name: ilbuy-logs-policy
    setup.ilm.rollover_alias: ilbuy-logs
  daemonSet:
    podTemplate:
      spec:
        containers:
        - name: filebeat
          volumeMounts:
          - name: varlogcontainers
            mountPath: /var/log/containers
          - name: varlogpods
            mountPath: /var/log/pods
          - name: varlibdockercontainers
            mountPath: /var/lib/docker/containers
          env:
          - name: NODE_NAME
            valueFrom:
              fieldRef:
                fieldPath: spec.nodeName
        volumes:
        - name: varlogcontainers
          hostPath:
            path: /var/log/containers
        - name: varlogpods
          hostPath:
            path: /var/log/pods
        - name: varlibdockercontainers
          hostPath:
            path: /var/lib/docker/containers
```

```bash
kubectl apply -f filebeat-daemonset.yaml
```

---

### 常用日志查询语句

**在Kibana Discover / Dev Tools中执行：**

```json
// 1. 查询最近10分钟错误日志
GET ilbuy-logs-*/_search
{
  "query": {
    "bool": {
      "filter": [
        {"range": {"@timestamp": {"gte": "now-10m"}}},
        {"term": {"level": "ERROR"}}
      ]
    }
  },
  "sort": [{"@timestamp": "desc"}],
  "size": 50
}

// 2. 按TraceId查询全链路日志
GET ilbuy-logs-*/_search
{
  "query": {
    "match": {"traceId": "abc123def456"}
  },
  "sort": [{"@timestamp": "asc"}]
}

// 3. 查询特定服务的慢响应
GET ilbuy-logs-*/_search
{
  "query": {
    "bool": {
      "filter": [
        {"term": {"kubernetes.labels.app": "procurement-service"}},
        {"range": {"duration": {"gte": 1000}}}
      ]
    }
  },
  "sort": [{"duration": "desc"}],
  "size": 20
}

// 4. 统计各接口错误率（最近1小时）
GET ilbuy-logs-*/_search
{
  "query": {
    "bool": {
      "filter": [
        {"range": {"@timestamp": {"gte": "now-1h"}}},
        {"term": {"type": "ACCESS_LOG"}}
      ]
    }
  },
  "aggs": {
    "by_uri": {
      "terms": {"field": "uri.keyword", "size": 20},
      "aggs": {
        "error_count": {"filter": {"range": {"statusCode": {"gte": 500}}}},
        "total_count": {"value_count": {"field": "@timestamp"}}
      }
    }
  }
}
```

---

## 三、数据备份

### MySQL 自动备份配置

```bash
# 创建备份脚本
cat > /opt/scripts/mysql-backup.sh << 'SCRIPT'
#!/bin/bash
set -e

BACKUP_DIR="/data/backup/mysql"
RETAIN_DAYS=30
DATE=$(date '+%Y%m%d_%H%M%S')
MYSQL_HOST="192.168.1.31"
MYSQL_USER="ilbuy"
MYSQL_PASS="ILbuy@DB2024"

mkdir -p ${BACKUP_DIR}/${DATE}

# 备份各业务库
databases=(ilbuy_user ilbuy_procurement ilbuy_order ilbuy_supplier ilbuy_inquiry ilbuy_matching ilbuy_data ilbuy_notification)

for db in "${databases[@]}"; do
  echo "备份数据库：${db} ..."
  mysqldump -h ${MYSQL_HOST} -u ${MYSQL_USER} -p${MYSQL_PASS} \
    --single-transaction \
    --master-data=2 \
    --routines \
    --triggers \
    --events \
    --hex-blob \
    ${db} | gzip > ${BACKUP_DIR}/${DATE}/${db}.sql.gz
  echo "  ✓ ${db} 备份完成"
done

# 计算校验和
md5sum ${BACKUP_DIR}/${DATE}/*.gz > ${BACKUP_DIR}/${DATE}/checksums.md5

# 上传到对象存储（阿里云OSS / 腾讯云COS）
ossutil cp -r ${BACKUP_DIR}/${DATE}/ \
  oss://ilbuy-backup/mysql/${DATE}/ \
  --access-key-id ${OSS_KEY} \
  --access-key-secret ${OSS_SECRET}

# 删除30天前的本地备份
find ${BACKUP_DIR} -maxdepth 1 -type d -mtime +${RETAIN_DAYS} -exec rm -rf {} +

echo "MySQL备份完成：${DATE}"
SCRIPT

chmod +x /opt/scripts/mysql-backup.sh

# 配置定时任务（每天凌晨2点）
echo "0 2 * * * root /opt/scripts/mysql-backup.sh >> /var/log/mysql-backup.log 2>&1" > /etc/cron.d/mysql-backup
```

### Redis 持久化备份

```bash
# 触发RDB快照
redis-cli -h 192.168.1.41 -p 7001 -a ILbuy@Redis2024 BGSAVE

# 等待快照完成
redis-cli -h 192.168.1.41 -p 7001 -a ILbuy@Redis2024 LASTSAVE

# 拷贝RDB文件
cp /data/redis-cluster/node-7001/data/dump.rdb \
   /data/backup/redis/dump_$(date '+%Y%m%d_%H%M%S').rdb
```

---

## 四、滚动发布操作手册

### 标准滚动发布流程

```bash
#!/bin/bash
# rolling-deploy.sh - 滚动发布脚本

SERVICE=$1
VERSION=$2
NAMESPACE="ilbuy-prod"
REGISTRY="registry.ilbuy.com/ilbuy"

if [ -z "$SERVICE" ] || [ -z "$VERSION" ]; then
  echo "用法: $0 <service-name> <version>"
  echo "示例: $0 procurement-service 1.0.1"
  exit 1
fi

echo "========================================"
echo "  开始滚动发布"
echo "  服务：${SERVICE}"
echo "  版本：${VERSION}"
echo "  时间：$(date '+%Y-%m-%d %H:%M:%S')"
echo "========================================"

# Step 1: 确认镜像存在
echo ""
echo "Step 1: 验证镜像..."
if ! docker manifest inspect ${REGISTRY}/${SERVICE}:${VERSION} > /dev/null 2>&1; then
  echo "✗ 镜像不存在：${REGISTRY}/${SERVICE}:${VERSION}"
  exit 1
fi
echo "✓ 镜像已验证"

# Step 2: 查看当前版本
echo ""
echo "Step 2: 当前版本信息..."
kubectl get deployment ${SERVICE} -n ${NAMESPACE} \
  -o jsonpath='当前镜像: {.spec.template.spec.containers[0].image}{"\n"}'
CURRENT_REPLICAS=$(kubectl get deployment ${SERVICE} -n ${NAMESPACE} -o jsonpath='{.spec.replicas}')
echo "当前副本数: ${CURRENT_REPLICAS}"

# Step 3: 执行滚动更新
echo ""
echo "Step 3: 执行滚动更新..."
kubectl set image deployment/${SERVICE} \
  ${SERVICE}=${REGISTRY}/${SERVICE}:${VERSION} \
  -n ${NAMESPACE} \
  --record

# Step 4: 监控更新进度
echo ""
echo "Step 4: 监控发布进度（超时300秒）..."
if kubectl rollout status deployment/${SERVICE} -n ${NAMESPACE} --timeout=300s; then
  echo "✓ 发布成功"
else
  echo "✗ 发布超时或失败，执行自动回滚..."
  kubectl rollout undo deployment/${SERVICE} -n ${NAMESPACE}
  kubectl rollout status deployment/${SERVICE} -n ${NAMESPACE} --timeout=120s
  echo "回滚完成，请排查问题后重新发布"
  exit 1
fi

# Step 5: 验证新版本
echo ""
echo "Step 5: 验证新版本..."
sleep 10  # 等待健康检查

READY_PODS=$(kubectl get deployment ${SERVICE} -n ${NAMESPACE} \
  -o jsonpath='{.status.readyReplicas}')
DESIRED_PODS=$(kubectl get deployment ${SERVICE} -n ${NAMESPACE} \
  -o jsonpath='{.spec.replicas}')

if [ "$READY_PODS" = "$DESIRED_PODS" ]; then
  echo "✓ 所有Pod就绪：${READY_PODS}/${DESIRED_PODS}"
else
  echo "⚠ 部分Pod未就绪：${READY_PODS}/${DESIRED_PODS}"
fi

# Step 6: 冒烟测试
echo ""
echo "Step 6: 执行冒烟测试..."
HEALTH=$(kubectl exec -it deploy/api-gateway -n ${NAMESPACE} -- \
  curl -sf http://${SERVICE}.${NAMESPACE}.svc.cluster.local:8080/actuator/health 2>/dev/null | \
  python3 -c "import sys,json;print(json.load(sys.stdin).get('status','UNKNOWN'))" 2>/dev/null)

if [ "$HEALTH" = "UP" ]; then
  echo "✓ 健康检查通过"
else
  echo "⚠ 健康检查状态：${HEALTH}"
fi

echo ""
echo "========================================"
echo "  发布完成：${SERVICE} → ${VERSION}"
echo "  时间：$(date '+%Y-%m-%d %H:%M:%S')"
echo "========================================"

# 记录发布日志
cat >> /var/log/ilbuy-deployments.log << EOF
$(date '+%Y-%m-%d %H:%M:%S') | DEPLOY | ${SERVICE} | ${VERSION} | SUCCESS
EOF
```

---

## 五、日常运维检查清单

### 每日检查（Morning Check）

```bash
#!/bin/bash
# daily-check.sh

NAMESPACE="ilbuy-prod"
echo "===== ILbuy 每日检查 $(date '+%Y-%m-%d') ====="

echo ""
echo "【Pod状态】"
kubectl get pods -n $NAMESPACE | grep -v Running | grep -v NAME

echo ""
echo "【资源使用 TOP10】"
kubectl top pods -n $NAMESPACE --sort-by=cpu 2>/dev/null | head -11

echo ""
echo "【昨日错误日志统计】"
# 通过Elasticsearch API查询
curl -sf "http://es-http.logging:9200/ilbuy-logs-$(date '+%Y.%m.%d' -d 'yesterday')/_count?q=level:ERROR" | \
  python3 -c "import sys,json;d=json.load(sys.stdin);print(f'  错误总数：{d[\"count\"]}')"

echo ""
echo "【MySQL主从状态】"
mysql -h 192.168.1.32 -u root -pILbuy@MySQL2024 -e "SHOW REPLICA STATUS\G" 2>/dev/null | \
  grep -E "Replica_IO_Running|Replica_SQL_Running|Seconds_Behind_Source"

echo ""
echo "【Redis集群状态】"
redis-cli -h 192.168.1.41 -p 7001 -a ILbuy@Redis2024 cluster info 2>/dev/null | \
  grep -E "cluster_state|cluster_size"

echo ""
echo "【昨日备份状态】"
ls -lh /data/backup/mysql/$(date '+%Y%m%d' -d 'yesterday')*.gz 2>/dev/null | wc -l
echo "个数据库备份文件"

echo ""
echo "【K8s节点状态】"
kubectl get nodes
```

---

## 六、紧急操作手册

### 紧急扩容（流量突增）

```bash
# 快速扩容核心服务
kubectl scale deployment procurement-service --replicas=10 -n ilbuy-prod
kubectl scale deployment api-gateway --replicas=6 -n ilbuy-prod
kubectl scale deployment order-service --replicas=8 -n ilbuy-prod

# 确认扩容完成
watch kubectl get pods -n ilbuy-prod | head -20
```

### 紧急限流（防止雪崩）

```bash
# 通过Nacos动态推送限流配置
curl -X POST "http://nacos-headless.middleware:8848/nacos/v1/cs/configs" \
  -d "dataId=ilbuy-gateway-prod.yaml&group=DEFAULT_GROUP&namespace=prod&content=$(cat << 'EOF'
sentinel:
  flow:
    rules:
    - resource: "/api/v1/procurement/demands POST"
      grade: 1
      count: 20   # 从50降低到20，紧急限流
      strategy: 0
    - resource: "/api/v1/auth/login POST"
      grade: 1
      count: 50
      strategy: 0
EOF
)"
```

### 紧急停服某个功能

```bash
# 通过Feature Flag关闭AI匹配（降级到规则引擎）
kubectl set env deployment/ai-matching-service -n ilbuy-prod \
  FEATURE_AI_ENABLED=false \
  MATCHING_FALLBACK_ONLY=true

# 关闭数据采集任务（减轻系统压力）
kubectl scale deployment data-collector-service --replicas=0 -n ilbuy-prod
```
