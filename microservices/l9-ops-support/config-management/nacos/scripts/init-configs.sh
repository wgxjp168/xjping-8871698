#!/usr/bin/env bash
# =============================================================================
# ILbuy Nacos 配置初始化脚本
# 在 Nacos 集群就绪后，初始化所有微服务配置
# 用法：bash init-configs.sh [NACOS_HOST] [NACOS_PORT] [USERNAME] [PASSWORD]
# =============================================================================
set -euo pipefail

NACOS_HOST="${1:-nacos-client.ilbuy-ops.svc.cluster.local}"
NACOS_PORT="${2:-8848}"
USERNAME="${3:-nacos}"
PASSWORD="${4:-${NACOS_PASSWORD:-nacos}}"
BASE_URL="http://${NACOS_HOST}:${NACOS_PORT}/nacos"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }
die() { echo "[ERROR] $*" >&2; exit 1; }

# ── 获取访问 Token ──────────────────────────────────────────────────────────
get_token() {
  local resp
  resp=$(curl -sf -X POST "${BASE_URL}/v1/auth/login" \
    -d "username=${USERNAME}&password=${PASSWORD}") || die "Nacos 登录失败，请检查连接和凭据"
  echo "${resp}" | python3 -c "import sys,json; print(json.load(sys.stdin)['accessToken'])"
}

# ── 发布配置 ────────────────────────────────────────────────────────────────
publish_config() {
  local namespace="$1" group="$2" data_id="$3" content="$4" type="${5:-properties}"
  curl -sf -X POST "${BASE_URL}/v1/cs/configs" \
    -H "Authorization: Bearer ${TOKEN}" \
    -d "tenant=${namespace}&group=${group}&dataId=${data_id}&type=${type}&content=$(python3 -c "import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1]))" "${content}")" \
    > /dev/null || die "发布配置失败: ${namespace}/${group}/${data_id}"
  log "已发布: [${namespace}] ${group}/${data_id}"
}

# ── 创建命名空间 ─────────────────────────────────────────────────────────────
create_namespace() {
  local ns_id="$1" ns_name="$2"
  curl -sf -X POST "${BASE_URL}/v1/console/namespaces" \
    -H "Authorization: Bearer ${TOKEN}" \
    -d "customNamespaceId=${ns_id}&namespaceName=${ns_name}&namespaceDesc=ILbuy ${ns_name} 层配置" \
    > /dev/null || log "命名空间 ${ns_id} 可能已存在，继续..."
  log "命名空间: ${ns_id} (${ns_name})"
}

# ═══════════════════════════════════════════════════════════════════════════
log "=== ILbuy Nacos 配置初始化开始 ==="
log "目标: ${BASE_URL}"

# 等待 Nacos 就绪
for i in $(seq 1 30); do
  if curl -sf "${BASE_URL}/v1/console/health/readiness" > /dev/null 2>&1; then
    log "Nacos 已就绪"
    break
  fi
  log "等待 Nacos 就绪... (${i}/30)"
  sleep 10
done

TOKEN=$(get_token)
log "登录成功，获取 Token"

# ── 创建命名空间 ─────────────────────────────────────────────────────────────
log "--- 创建命名空间 ---"
create_namespace "ilbuy-dev"  "开发环境"
create_namespace "ilbuy-staging" "预发环境"
create_namespace "ilbuy-prod" "生产环境"

# 后续配置均发布到生产命名空间
NS="ilbuy-prod"
ENV="prod"

# ── L1 用户权益层 ─────────────────────────────────────────────────────────
log "--- L1 用户权益层配置 ---"
publish_config "${NS}" "L1-USER-PROFILE" "user-profile-svc.properties" "
server.port=8011
spring.datasource.url=\${DB_URL}
spring.redis.host=redis.ilbuy-infra.svc.cluster.local
spring.redis.port=6379
spring.rabbitmq.host=rabbitmq.ilbuy-infra.svc.cluster.local
logging.level.com.ilbuy=INFO
user.profile.cache.ttl=3600
user.tag.max-count=50
"

# ── L2 AI决策层 ──────────────────────────────────────────────────────────
log "--- L2 AI决策层配置 ---"
publish_config "${NS}" "L2-AI-DECISION" "decision-svc.properties" "
server.port=8012
recommendation.model.update-interval=3600
recommendation.cache.ttl=300
recommendation.fallback-strategy=popular
ab.test.enabled=true
ab.test.traffic-split=0.5
openai.api.timeout=30
"

publish_config "${NS}" "L2-AI-DECISION" "model-serving-svc.properties" "
server.port=8021
model.store.path=/app/model_store
model.reload.interval=300
prediction.timeout=5
prediction.batch-size=32
"

# ── L5 报告生成层 ─────────────────────────────────────────────────────────
log "--- L5 报告生成层配置 ---"
publish_config "${NS}" "L5-REPORT" "report-generate-svc.properties" "
server.port=8051
report.pdf.timeout=60
report.cache.enabled=true
report.cache.ttl=1800
report.max-concurrent-generation=10
"

# ── L6 交付履约层 ─────────────────────────────────────────────────────────
log "--- L6 交付履约层配置 ---"
publish_config "${NS}" "L6-DELIVERY" "delivery-svc.properties" "
server.port=8061
delivery.retry.max-attempts=3
delivery.retry.backoff=5000
delivery.sla.standard-hours=24
delivery.notification.enabled=true
"

# ── L7 商业变现层 ─────────────────────────────────────────────────────────
log "--- L7 商业变现层配置 ---"
publish_config "${NS}" "L7-MONETIZATION" "billing-svc.properties" "
server.port=8071
payment.timeout=30
payment.retry.enabled=true
payment.wechat.enabled=true
payment.alipay.enabled=true
invoice.generate.async=true
"

# ── L8 反馈优化层 ─────────────────────────────────────────────────────────
log "--- L8 反馈优化层配置 ---"
publish_config "${NS}" "L8-FEEDBACK" "feedback-svc.properties" "
server.port=8060
feedback.followup.delay-hours=24
feedback.sentiment.enabled=true
feedback.alert.negative-threshold=0.30
"

publish_config "${NS}" "L8-FEEDBACK" "model-iteration-svc.properties" "
server.port=8062
model.min-training-samples=100
model.min-auc=0.65
model.min-f1=0.60
ab.test.min-sample-size=200
ab.test.confidence-level=0.95
"

# ── 公共配置 ──────────────────────────────────────────────────────────────
log "--- 公共配置 ---"
publish_config "${NS}" "COMMON" "ilbuy-common.properties" "
# 公共数据库连接池配置
spring.datasource.hikari.maximum-pool-size=20
spring.datasource.hikari.minimum-idle=5
spring.datasource.hikari.connection-timeout=30000

# 公共 RabbitMQ 配置
spring.rabbitmq.virtual-host=/ilbuy
spring.rabbitmq.publisher-confirm-type=correlated
spring.rabbitmq.publisher-returns=true
spring.rabbitmq.listener.simple.acknowledge-mode=manual

# 公共日志配置
logging.pattern.console=%d{yyyy-MM-dd HH:mm:ss} [%thread] %-5level %logger{36} - %msg%n
management.endpoints.web.exposure.include=health,info,prometheus,metrics
management.endpoint.health.show-details=always

# Jaeger 追踪
opentelemetry.exporter.otlp.endpoint=http://jaeger-collector.ilbuy-ops.svc.cluster.local:4317
opentelemetry.exporter.otlp.protocol=grpc
"

# ── 告警阈值配置 ───────────────────────────────────────────────────────────
log "--- 告警阈值配置 ---"
publish_config "${NS}" "OPS" "alert-thresholds.properties" "
alert.latency.p99.warning=2000
alert.latency.p99.critical=5000
alert.error-rate.warning=0.05
alert.error-rate.critical=0.10
alert.cpu.warning=0.85
alert.memory.warning=0.90
" yaml

log ""
log "=== ILbuy Nacos 配置初始化完成 ==="
log "请访问 Nacos 控制台验证: ${BASE_URL}/index.html"
