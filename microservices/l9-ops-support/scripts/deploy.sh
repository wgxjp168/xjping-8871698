#!/usr/bin/env bash
# =============================================================================
# ILbuy 微服务滚动发布脚本
# 用法: bash deploy.sh -s <service> -t <tag> -n <namespace> [-w <timeout>] [-d]
#
# 选项:
#   -s  服务名（如 feedback-svc）
#   -t  镜像 Tag（如 a1b2c3d4）
#   -n  K8s 命名空间（如 ilbuy-l8）
#   -r  Harbor 仓库（默认 harbor.ilbuy.internal/ilbuy）
#   -w  等待超时，秒（默认 600）
#   -d  演练模式（dry-run，不实际执行）
#   -h  显示帮助
# =============================================================================
set -euo pipefail

# ── 默认值 ─────────────────────────────────────────────────────────────────
REGISTRY="harbor.ilbuy.internal/ilbuy"
TIMEOUT=600
DRY_RUN=false

log()    { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }
info()   { echo -e "\033[36m[INFO]\033[0m  $*"; }
ok()     { echo -e "\033[32m[ OK ]\033[0m  $*"; }
warn()   { echo -e "\033[33m[WARN]\033[0m  $*"; }
die()    { echo -e "\033[31m[ERR ]\033[0m  $*" >&2; exit 1; }
run()    { if [ "${DRY_RUN}" = true ]; then echo "[DRY-RUN] $*"; else eval "$*"; fi; }

usage() {
    echo "用法: $(basename "$0") -s <service> -t <tag> -n <namespace> [选项]"
    echo ""
    echo "选项:"
    echo "  -s  服务名（必填）"
    echo "  -t  镜像 Tag（必填）"
    echo "  -n  命名空间（必填）"
    echo "  -r  Harbor 仓库（默认: ${REGISTRY}）"
    echo "  -w  滚动超时秒数（默认: ${TIMEOUT}）"
    echo "  -d  Dry Run 模式"
    echo "  -h  显示帮助"
    exit 0
}

# ── 参数解析 ─────────────────────────────────────────────────────────────────
while getopts "s:t:n:r:w:dh" opt; do
    case "${opt}" in
        s) SERVICE="${OPTARG}" ;;
        t) TAG="${OPTARG}" ;;
        n) NAMESPACE="${OPTARG}" ;;
        r) REGISTRY="${OPTARG}" ;;
        w) TIMEOUT="${OPTARG}" ;;
        d) DRY_RUN=true ;;
        h) usage ;;
        *) die "未知选项: -${OPTARG}" ;;
    esac
done

[ -z "${SERVICE:-}" ] && die "必须指定 -s <service>"
[ -z "${TAG:-}" ]     && die "必须指定 -t <tag>"
[ -z "${NAMESPACE:-}" ] && die "必须指定 -n <namespace>"

FULL_IMAGE="${REGISTRY}/${SERVICE}:${TAG}"

# ── 前置检查 ─────────────────────────────────────────────────────────────────
log "=== ILbuy 滚动发布 ==="
info "服务:    ${SERVICE}"
info "命名空间: ${NAMESPACE}"
info "镜像:    ${FULL_IMAGE}"
[ "${DRY_RUN}" = true ] && warn "DRY RUN 模式 — 不实际执行"

# 检查工具
command -v kubectl > /dev/null || die "kubectl 未安装"

# 检查 Deployment 是否存在
kubectl get deployment "${SERVICE}" -n "${NAMESPACE}" > /dev/null 2>&1 || \
    die "Deployment ${SERVICE} 在 ${NAMESPACE} 中不存在"

# 检查目标 Pod 的当前状态
CURRENT_READY=$(kubectl get deployment "${SERVICE}" -n "${NAMESPACE}" \
    -o jsonpath='{.status.readyReplicas}' 2>/dev/null || echo 0)
DESIRED=$(kubectl get deployment "${SERVICE}" -n "${NAMESPACE}" \
    -o jsonpath='{.spec.replicas}' 2>/dev/null || echo 1)
info "当前就绪: ${CURRENT_READY:-0} / ${DESIRED}"

# 记录当前镜像（用于回滚）
PREV_IMAGE=$(kubectl get deployment "${SERVICE}" -n "${NAMESPACE}" \
    -o jsonpath="{.spec.template.spec.containers[0].image}" 2>/dev/null || echo "unknown")
info "当前镜像: ${PREV_IMAGE}"
log "新镜像: ${FULL_IMAGE}"

# ── 发布标注（记录发布信息）───────────────────────────────────────────────────
DEPLOY_TIME=$(date -u +%Y-%m-%dT%H:%M:%SZ)
run kubectl annotate deployment "${SERVICE}" \
    -n "${NAMESPACE}" \
    "ilbuy.io/last-deployed=${DEPLOY_TIME}" \
    "ilbuy.io/last-tag=${TAG}" \
    "ilbuy.io/prev-image=${PREV_IMAGE}" \
    --overwrite

# ── 执行滚动更新 ─────────────────────────────────────────────────────────────
log "开始滚动更新..."
run kubectl set image \
    deployment/"${SERVICE}" \
    "${SERVICE}=${FULL_IMAGE}" \
    -n "${NAMESPACE}"

# ── 等待 Rollout 完成 ────────────────────────────────────────────────────────
log "等待滚动更新完成（超时: ${TIMEOUT}s）..."
if [ "${DRY_RUN}" = false ]; then
    kubectl rollout status \
        deployment/"${SERVICE}" \
        -n "${NAMESPACE}" \
        --timeout="${TIMEOUT}s" || {
            warn "滚动更新超时或失败，执行自动回滚..."
            kubectl rollout undo deployment/"${SERVICE}" -n "${NAMESPACE}"
            kubectl rollout status deployment/"${SERVICE}" -n "${NAMESPACE}" --timeout=300s
            die "部署失败，已回滚至 ${PREV_IMAGE}"
        }
fi

# ── 部署后验证 ───────────────────────────────────────────────────────────────
log "验证部署结果..."
if [ "${DRY_RUN}" = false ]; then
    sleep 10
    READY=$(kubectl get deployment "${SERVICE}" -n "${NAMESPACE}" \
        -o jsonpath='{.status.readyReplicas}')
    DESIRED=$(kubectl get deployment "${SERVICE}" -n "${NAMESPACE}" \
        -o jsonpath='{.spec.replicas}')

    if [ "${READY}" != "${DESIRED}" ]; then
        warn "Pod 就绪数 (${READY}) 少于期望数 (${DESIRED})，检查 Pod 事件..."
        kubectl get pods -n "${NAMESPACE}" -l "app=${SERVICE}"
        die "部署未完全就绪"
    fi

    # 检查健康端点
    POD=$(kubectl get pods -n "${NAMESPACE}" -l "app=${SERVICE}" \
        -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")
    if [ -n "${POD}" ]; then
        HEALTH=$(kubectl exec "${POD}" -n "${NAMESPACE}" -- \
            wget -qO- http://localhost/health/liveness 2>/dev/null || echo '{"status":"UNKNOWN"}')
        STATUS=$(echo "${HEALTH}" | python3 -c "import sys,json; print(json.loads(sys.stdin.read()).get('status','?'))" 2>/dev/null || echo "?")
        if [ "${STATUS}" = "UP" ]; then
            ok "健康检查通过: ${STATUS}"
        else
            warn "健康状态: ${STATUS}"
        fi
    fi
fi

ok "=== 部署成功 ==="
info "服务: ${SERVICE} @ ${FULL_IMAGE}"
info "命名空间: ${NAMESPACE}"
log "发布时间: ${DEPLOY_TIME}"
