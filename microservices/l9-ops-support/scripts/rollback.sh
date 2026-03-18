#!/usr/bin/env bash
# =============================================================================
# ILbuy 快速回滚脚本
# 用法: bash rollback.sh -s <service> -n <namespace> [-t <tag>] [-v <revision>]
#
# 选项:
#   -s  服务名（必填）
#   -n  K8s 命名空间（必填）
#   -t  回滚到指定镜像 Tag（选填，优先级高于 -v）
#   -v  回滚到指定 Revision（选填，默认上一版本）
#   -l  列出可回滚的历史版本
#   -h  显示帮助
# =============================================================================
set -euo pipefail

REGISTRY="harbor.ilbuy.internal/ilbuy"
LIST_HISTORY=false
TAG=""
REVISION=""

log()  { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }
ok()   { echo -e "\033[32m[ OK ]\033[0m  $*"; }
warn() { echo -e "\033[33m[WARN]\033[0m  $*"; }
die()  { echo -e "\033[31m[ERR ]\033[0m  $*" >&2; exit 1; }

usage() {
    echo "用法: $(basename "$0") -s <service> -n <namespace> [选项]"
    echo ""
    echo "选项:"
    echo "  -s  服务名（必填）"
    echo "  -n  命名空间（必填）"
    echo "  -t  回滚到指定 Tag"
    echo "  -v  回滚到指定 Revision（默认 -1，即上一版本）"
    echo "  -l  列出历史版本"
    echo "  -h  显示帮助"
    exit 0
}

while getopts "s:n:t:v:lh" opt; do
    case "${opt}" in
        s) SERVICE="${OPTARG}" ;;
        n) NAMESPACE="${OPTARG}" ;;
        t) TAG="${OPTARG}" ;;
        v) REVISION="${OPTARG}" ;;
        l) LIST_HISTORY=true ;;
        h) usage ;;
        *) die "未知选项: -${OPTARG}" ;;
    esac
done

[ -z "${SERVICE:-}" ]   && die "必须指定 -s <service>"
[ -z "${NAMESPACE:-}" ] && die "必须指定 -n <namespace>"

command -v kubectl > /dev/null || die "kubectl 未安装"
kubectl get deployment "${SERVICE}" -n "${NAMESPACE}" > /dev/null 2>&1 || \
    die "Deployment ${SERVICE} 在 ${NAMESPACE} 中不存在"

# ── 列出历史版本 ─────────────────────────────────────────────────────────────
if [ "${LIST_HISTORY}" = true ]; then
    log "=== ${NAMESPACE}/${SERVICE} 部署历史 ==="
    kubectl rollout history deployment/"${SERVICE}" -n "${NAMESPACE}"

    # 显示 Annotation 中记录的上一版本
    PREV_IMAGE=$(kubectl get deployment "${SERVICE}" -n "${NAMESPACE}" \
        -o jsonpath='{.metadata.annotations.ilbuy\.io/prev-image}' 2>/dev/null || echo "未记录")
    PREV_TAG=$(kubectl get deployment "${SERVICE}" -n "${NAMESPACE}" \
        -o jsonpath='{.metadata.annotations.ilbuy\.io/last-tag}' 2>/dev/null || echo "未记录")
    log "上次部署 Tag: ${PREV_TAG}"
    log "上次镜像:    ${PREV_IMAGE}"
    exit 0
fi

# ── 获取当前镜像 ─────────────────────────────────────────────────────────────
CURRENT_IMAGE=$(kubectl get deployment "${SERVICE}" -n "${NAMESPACE}" \
    -o jsonpath="{.spec.template.spec.containers[0].image}" 2>/dev/null)
log "=== ILbuy 快速回滚 ==="
log "服务:    ${SERVICE}"
log "命名空间: ${NAMESPACE}"
log "当前镜像: ${CURRENT_IMAGE}"

# ── 确认回滚 ─────────────────────────────────────────────────────────────────
if [ -n "${TAG}" ]; then
    ROLLBACK_IMAGE="${REGISTRY}/${SERVICE}:${TAG}"
    log "回滚目标: ${ROLLBACK_IMAGE} (指定 Tag)"
    read -r -p "确认回滚？[y/N] " confirm
    [ "${confirm}" = "y" ] || [ "${confirm}" = "Y" ] || die "已取消"

    kubectl set image \
        deployment/"${SERVICE}" \
        "${SERVICE}=${ROLLBACK_IMAGE}" \
        -n "${NAMESPACE}"

elif [ -n "${REVISION}" ]; then
    log "回滚到 Revision: ${REVISION}"
    read -r -p "确认回滚？[y/N] " confirm
    [ "${confirm}" = "y" ] || [ "${confirm}" = "Y" ] || die "已取消"

    kubectl rollout undo \
        deployment/"${SERVICE}" \
        -n "${NAMESPACE}" \
        --to-revision="${REVISION}"

else
    # 回滚到上一版本
    log "回滚到上一个版本..."
    PREV_IMAGE=$(kubectl get deployment "${SERVICE}" -n "${NAMESPACE}" \
        -o jsonpath='{.metadata.annotations.ilbuy\.io/prev-image}' 2>/dev/null || echo "")
    [ -n "${PREV_IMAGE}" ] && log "上一镜像: ${PREV_IMAGE}" || warn "未找到 ilbuy.io/prev-image 注解，使用 K8s Rollout Undo"

    read -r -p "确认回滚到上一版本？[y/N] " confirm
    [ "${confirm}" = "y" ] || [ "${confirm}" = "Y" ] || die "已取消"

    kubectl rollout undo deployment/"${SERVICE}" -n "${NAMESPACE}"
fi

# ── 等待回滚完成 ─────────────────────────────────────────────────────────────
log "等待回滚完成..."
kubectl rollout status \
    deployment/"${SERVICE}" \
    -n "${NAMESPACE}" \
    --timeout=300s || die "回滚超时，请手动检查 Pod 状态"

# ── 验证 ─────────────────────────────────────────────────────────────────────
sleep 5
NEW_IMAGE=$(kubectl get deployment "${SERVICE}" -n "${NAMESPACE}" \
    -o jsonpath="{.spec.template.spec.containers[0].image}")
READY=$(kubectl get deployment "${SERVICE}" -n "${NAMESPACE}" \
    -o jsonpath='{.status.readyReplicas}' || echo 0)
DESIRED=$(kubectl get deployment "${SERVICE}" -n "${NAMESPACE}" \
    -o jsonpath='{.spec.replicas}')

ok "=== 回滚成功 ==="
log "回滚后镜像: ${NEW_IMAGE}"
log "就绪: ${READY:-0} / ${DESIRED}"
