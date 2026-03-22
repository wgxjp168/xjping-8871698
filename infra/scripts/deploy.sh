#!/usr/bin/env bash
# ============================================================
# ILbuy 服务启停脚本
# 用途：启动、停止、重启、查看状态 微服务（本地 Docker Compose 或 K8s）
# 用法：
#   bash deploy.sh start                 # 启动所有服务
#   bash deploy.sh stop                  # 停止所有服务
#   bash deploy.sh restart               # 重启所有服务
#   bash deploy.sh restart gateway-svc   # 重启单个服务
#   bash deploy.sh status                # 查看服务状态
#   bash deploy.sh logs gateway-svc      # 查看服务日志（实时）
#   bash deploy.sh rollback gateway-svc v1.1.0  # 回滚到指定版本
#   bash deploy.sh scale product-svc 3   # 扩缩容
# 依赖：docker compose 或 kubectl
# ============================================================
set -euo pipefail

# ──────────────────────────────────────────────────────────
#  配置
# ──────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
INFRA_DIR="${PROJECT_ROOT}/infra"
MIDDLEWARE_COMPOSE="${INFRA_DIR}/docker-compose/middleware/docker-compose.yml"
SERVICES_COMPOSE="${INFRA_DIR}/docker-compose/services/docker-compose.yml"
REGISTRY="${REGISTRY:-registry.cn-hangzhou.aliyuncs.com/ilbuy}"
DEPLOY_MODE="${DEPLOY_MODE:-compose}"   # compose | k8s
K8S_NS="${K8S_NS:-ilbuy}"
WAIT_TIMEOUT="${WAIT_TIMEOUT:-120}"     # 等待健康检查超时(秒)

# ──────────────────────────────────────────────────────────
#  颜色输出
# ──────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
info()    { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*" >&2; }
section() { echo -e "\n${BLUE}══ $* ══${NC}\n"; }

# ──────────────────────────────────────────────────────────
#  Docker Compose 操作
# ──────────────────────────────────────────────────────────
compose_up() {
  local svc="${1:-}"
  section "启动服务${svc:+: $svc}"

  # 先确保中间件已启动
  if ! docker compose -f "${MIDDLEWARE_COMPOSE}" --env-file "${INFRA_DIR}/docker-compose/middleware/.env" ps -q 2>/dev/null | grep -q .; then
    warn "中间件未启动，先启动中间件..."
    docker compose -f "${MIDDLEWARE_COMPOSE}" \
      --env-file "${INFRA_DIR}/docker-compose/middleware/.env" \
      up -d
    info "等待中间件就绪（60s）..."
    sleep 60
  fi

  # 启动微服务
  docker compose -f "${SERVICES_COMPOSE}" \
    --env-file "${INFRA_DIR}/docker-compose/services/.env" \
    up -d ${svc:+--no-deps "$svc"}

  info "✓ 服务已启动"
  compose_status
}

compose_down() {
  local svc="${1:-}"
  section "停止服务${svc:+: $svc}"
  docker compose -f "${SERVICES_COMPOSE}" \
    --env-file "${INFRA_DIR}/docker-compose/services/.env" \
    ${svc:+stop "$svc"} ${svc:-down}
  info "✓ 服务已停止"
}

compose_restart() {
  local svc="${1:-}"
  section "重启服务${svc:+: $svc}"
  docker compose -f "${SERVICES_COMPOSE}" \
    --env-file "${INFRA_DIR}/docker-compose/services/.env" \
    restart ${svc:-}
  info "✓ 服务已重启"
}

compose_status() {
  section "服务状态"
  echo "── 中间件 ────────────────────────────────────"
  docker compose -f "${MIDDLEWARE_COMPOSE}" \
    --env-file "${INFRA_DIR}/docker-compose/middleware/.env" \
    ps 2>/dev/null || warn "中间件未运行"

  echo ""
  echo "── 微服务 ────────────────────────────────────"
  docker compose -f "${SERVICES_COMPOSE}" \
    --env-file "${INFRA_DIR}/docker-compose/services/.env" \
    ps 2>/dev/null || warn "微服务未运行"
}

compose_logs() {
  local svc="${1:-}"
  local lines="${2:-100}"
  docker compose -f "${SERVICES_COMPOSE}" \
    --env-file "${INFRA_DIR}/docker-compose/services/.env" \
    logs --tail="${lines}" -f ${svc:-}
}

compose_scale() {
  local svc="$1"
  local replicas="$2"
  section "扩缩容: ${svc} -> ${replicas} 个副本"
  docker compose -f "${SERVICES_COMPOSE}" \
    --env-file "${INFRA_DIR}/docker-compose/services/.env" \
    up -d --scale "${svc}=${replicas}" --no-recreate
  info "✓ 扩缩容完成"
}

compose_rollback() {
  local svc="$1"
  local version="$2"
  section "回滚: ${svc} -> ${version}"

  # 修改 .env 中的 IMAGE_TAG 后重新部署
  local env_file="${INFRA_DIR}/docker-compose/services/.env"
  local backup_file="${env_file}.bak.$(date +%Y%m%d%H%M%S)"
  cp "${env_file}" "${backup_file}"
  info "已备份 .env: ${backup_file}"

  # 临时设置 IMAGE_TAG 并拉取 + 重启
  IMAGE_TAG="${version}" docker compose -f "${SERVICES_COMPOSE}" \
    --env-file "${env_file}" \
    up -d --no-deps "${svc}"
  info "✓ 回滚完成: ${svc} -> ${version}"
}

# ──────────────────────────────────────────────────────────
#  等待服务健康
# ──────────────────────────────────────────────────────────
wait_healthy() {
  local svc="$1"
  local timeout="${WAIT_TIMEOUT}"
  local elapsed=0
  info "等待 ${svc} 健康检查通过（最多 ${timeout}s）..."

  while [[ $elapsed -lt $timeout ]]; do
    local status
    status=$(docker inspect --format='{{.State.Health.Status}}' "ilbuy-${svc}" 2>/dev/null || echo "not_found")
    case "$status" in
      healthy)
        info "✓ ${svc} 健康"
        return 0 ;;
      not_found)
        warn "${svc} 容器不存在"
        return 1 ;;
    esac
    sleep 5
    elapsed=$((elapsed + 5))
    echo -n "."
  done
  echo ""
  error "${svc} 健康检查超时 (${timeout}s)"
  return 1
}

# ──────────────────────────────────────────────────────────
#  K8s 操作（生产环境）
# ──────────────────────────────────────────────────────────
k8s_up() {
  local svc="${1:-}"
  section "K8s 部署${svc:+: $svc}"
  local manifest_dir="${INFRA_DIR}/k8s"
  if [[ ! -d "$manifest_dir" ]]; then
    error "K8s manifest 目录不存在: ${manifest_dir}"
    exit 1
  fi
  if [[ -n "$svc" ]]; then
    kubectl apply -f "${manifest_dir}/${svc}/" -n "${K8S_NS}"
  else
    kubectl apply -f "${manifest_dir}/" -n "${K8S_NS}" --recursive
  fi
  info "✓ K8s 部署完成"
}

k8s_status() {
  section "K8s 服务状态 (namespace: ${K8S_NS})"
  kubectl get pods,svc,deploy -n "${K8S_NS}" -o wide 2>/dev/null || warn "kubectl 不可用"
}

k8s_rollback() {
  local svc="$1"
  local version="${2:-}"
  section "K8s 回滚: ${svc}"
  if [[ -n "$version" ]]; then
    kubectl set image "deployment/${svc}" "${svc}=${REGISTRY}/${svc}:${version}" -n "${K8S_NS}"
  else
    kubectl rollout undo "deployment/${svc}" -n "${K8S_NS}"
  fi
  kubectl rollout status "deployment/${svc}" -n "${K8S_NS}" --timeout="${WAIT_TIMEOUT}s"
  info "✓ 回滚完成"
}

# ──────────────────────────────────────────────────────────
#  主流程
# ──────────────────────────────────────────────────────────
usage() {
  echo "用法: bash $0 <命令> [服务名] [参数]"
  echo ""
  echo "命令:"
  echo "  start [svc]           启动服务（默认全部）"
  echo "  stop [svc]            停止服务（默认全部）"
  echo "  restart [svc]         重启服务（默认全部）"
  echo "  status                查看服务状态"
  echo "  logs [svc] [lines]    查看日志（默认100行，实时追踪）"
  echo "  rollback <svc> <ver>  回滚到指定版本"
  echo "  scale <svc> <n>       扩缩容到 n 个副本"
  echo ""
  echo "环境变量:"
  echo "  DEPLOY_MODE=compose|k8s  部署模式（默认 compose）"
  echo "  K8S_NS=ilbuy             K8s 命名空间"
}

CMD="${1:-help}"
shift || true
SVC="${1:-}" && shift || true

case "$DEPLOY_MODE" in
  compose)
    case "$CMD" in
      start)   compose_up "$SVC" ;;
      stop)    compose_down "$SVC" ;;
      restart) compose_restart "$SVC" ;;
      status)  compose_status ;;
      logs)    compose_logs "$SVC" "${1:-100}" ;;
      rollback) compose_rollback "$SVC" "${1:-}" ;;
      scale)   compose_scale "$SVC" "${1:?'请指定副本数'}" ;;
      wait)    wait_healthy "$SVC" ;;
      *)       usage; exit 1 ;;
    esac ;;
  k8s)
    case "$CMD" in
      start|deploy) k8s_up "$SVC" ;;
      status)  k8s_status ;;
      rollback) k8s_rollback "$SVC" "${1:-}" ;;
      *)       usage; exit 1 ;;
    esac ;;
  *)
    error "未知 DEPLOY_MODE: ${DEPLOY_MODE}"
    exit 1 ;;
esac
