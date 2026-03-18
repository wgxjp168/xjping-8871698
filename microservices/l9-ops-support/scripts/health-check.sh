#!/usr/bin/env bash
# =============================================================================
# ILbuy 全服务健康检查脚本
# 用法: bash health-check.sh [--namespace <ns>] [--output json|text]
# =============================================================================
set -euo pipefail

OUTPUT_FORMAT="${1:-text}"
FAILED_SERVICES=()

log()  { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }
ok()   { echo -e "  \033[32m✓\033[0m $*"; }
fail() { echo -e "  \033[31m✗\033[0m $*"; FAILED_SERVICES+=("$1"); }
warn() { echo -e "  \033[33m⚠\033[0m $*"; }

# ── 全部 ilbuy-* 服务清单 ────────────────────────────────────────────────────
declare -A SERVICES=(
    # namespace:service:port:health_path
    ["ilbuy-l1:user-profile-svc"]="8011:/health/liveness"
    ["ilbuy-l2:decision-svc"]="8012:/health/liveness"
    ["ilbuy-l2:model-serving-svc"]="8021:/health/liveness"
    ["ilbuy-l3:etl-svc"]="8031:/health/liveness"
    ["ilbuy-l3:crawler-svc"]="8032:/health/liveness"
    ["ilbuy-l4:query-svc"]="8041:/health/liveness"
    ["ilbuy-l4:data-svc"]="8042:/health/liveness"
    ["ilbuy-l5:report-generate-svc"]="8051:/health/liveness"
    ["ilbuy-l6:delivery-svc"]="8061:/health/liveness"
    ["ilbuy-l7:billing-svc"]="8071:/health/liveness"
    ["ilbuy-l8:feedback-svc"]="8060:/health/liveness"
    ["ilbuy-l8:behavior-track-svc"]="8061:/health/liveness"
    ["ilbuy-l8:model-iteration-svc"]="8062:/health/liveness"
    ["ilbuy-l8:model-deploy-svc"]="8063:/health/liveness"
    ["ilbuy-ops:prometheus"]="9090:/-/healthy"
    ["ilbuy-ops:grafana"]="3000:/api/health"
    ["ilbuy-ops:alertmanager"]="9093:/-/healthy"
    ["ilbuy-ops:jaeger-query"]="16686:/"
)

log "=== ILbuy 全服务健康检查 ==="
echo ""

TOTAL=0
PASS=0
WARN=0
FAIL=0

check_deployment() {
    local ns="$1" svc="$2"
    local ready desired

    ready=$(kubectl get deployment "${svc}" -n "${ns}" \
        -o jsonpath='{.status.readyReplicas}' 2>/dev/null || echo 0)
    desired=$(kubectl get deployment "${svc}" -n "${ns}" \
        -o jsonpath='{.spec.replicas}' 2>/dev/null || echo "?")

    TOTAL=$((TOTAL + 1))
    if [ "${ready}" = "${desired}" ] && [ "${ready}" != "0" ]; then
        PASS=$((PASS + 1))
        ok "[${ns}] ${svc}: Ready ${ready}/${desired}"
        return 0
    elif [ "${ready}" = "0" ]; then
        FAIL=$((FAIL + 1))
        fail "${ns}/${svc}" "[${ns}] ${svc}: Down (0/${desired})"
        return 1
    else
        WARN=$((WARN + 1))
        warn "[${ns}] ${svc}: Degraded (${ready}/${desired})"
        return 0
    fi
}

check_endpoint() {
    local ns="$1" svc="$2" port="$3" path="$4"
    local pod http_status

    pod=$(kubectl get pods -n "${ns}" -l "app=${svc}" \
        -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")

    if [ -z "${pod}" ]; then
        warn "[${ns}] ${svc}: 无 Pod 可执行健康检查"
        return
    fi

    http_status=$(kubectl exec "${pod}" -n "${ns}" -- \
        wget -qO- --server-response "http://localhost:${port}${path}" 2>&1 | \
        grep "HTTP/" | awk '{print $2}' | tail -1 || echo "000")

    if [ "${http_status}" = "200" ]; then
        ok "[${ns}] ${svc} ${path}: HTTP ${http_status}"
    else
        warn "[${ns}] ${svc} ${path}: HTTP ${http_status}"
    fi
}

# ── 检查各命名空间 Deployment ────────────────────────────────────────────────
for key in "${!SERVICES[@]}"; do
    ns="${key%%:*}"
    svc="${key##*:}"
    check_deployment "${ns}" "${svc}" || true
done

echo ""
echo "─────────────────────────────────────────────"

# ── 检查基础设施 ────────────────────────────────────────────────────────────
log "检查基础设施服务..."
echo ""

check_infra() {
    local name="$1" cmd="$2"
    TOTAL=$((TOTAL + 1))
    if eval "${cmd}" > /dev/null 2>&1; then
        PASS=$((PASS + 1))
        ok "基础设施 [${name}]: 正常"
    else
        FAIL=$((FAIL + 1))
        fail "${name}" "基础设施 [${name}]: 异常"
    fi
}

# PostgreSQL
check_infra "PostgreSQL" "kubectl exec -n ilbuy-infra postgres-0 -- pg_isready -U ilbuy 2>/dev/null"

# Redis
check_infra "Redis" "kubectl exec -n ilbuy-infra redis-master-0 -- redis-cli ping 2>/dev/null | grep -q PONG"

# RabbitMQ
check_infra "RabbitMQ" "kubectl exec -n ilbuy-infra rabbitmq-0 -- rabbitmq-diagnostics ping 2>/dev/null"

# Nacos
check_infra "Nacos" "kubectl exec -n ilbuy-ops nacos-0 -- wget -qO- http://localhost:8848/nacos/actuator/health/readiness 2>/dev/null"

# Elasticsearch
check_infra "Elasticsearch" "kubectl exec -n ilbuy-ops elasticsearch-0 -- wget -qO- 'https://localhost:9200/_cluster/health?local=true' --no-check-certificate 2>/dev/null"

echo ""
echo "─────────────────────────────────────────────"

# ── 汇总报告 ─────────────────────────────────────────────────────────────────
echo ""
log "=== 检查汇总 ==="
echo "  总计: ${TOTAL} | ✓ 正常: ${PASS} | ⚠ 降级: ${WARN} | ✗ 异常: ${FAIL}"
echo ""

if [ ${FAIL} -gt 0 ]; then
    echo -e "\033[31m异常服务列表:\033[0m"
    for svc in "${FAILED_SERVICES[@]}"; do
        echo "  - ${svc}"
    done
    echo ""
    exit 1
fi

if [ ${WARN} -gt 0 ]; then
    warn "存在降级服务，建议检查"
    exit 0
fi

ok "所有服务运行正常"
exit 0
