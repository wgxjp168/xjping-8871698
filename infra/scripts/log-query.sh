#!/usr/bin/env bash
# ============================================================
# ILbuy 日志查询脚本
# 用途：快速检索微服务日志，支持关键词过滤、时间范围、级别过滤
# 用法：
#   bash log-query.sh <服务名>                          # 查看最近 100 行日志
#   bash log-query.sh <服务名> -n 500                   # 指定行数
#   bash log-query.sh <服务名> -f                       # 实时追踪
#   bash log-query.sh <服务名> -l ERROR                 # 过滤日志级别
#   bash log-query.sh <服务名> -k "NullPointerException" # 关键词过滤
#   bash log-query.sh <服务名> -s "2026-03-22 10:00"   # 开始时间
#   bash log-query.sh <服务名> -e "2026-03-22 11:00"   # 结束时间
#   bash log-query.sh all -l ERROR -n 200               # 所有服务 ERROR 日志
#   bash log-query.sh <服务名> --export /tmp/out.log    # 导出日志
# 依赖：docker
# ============================================================
set -euo pipefail

# ──────────────────────────────────────────────────────────
#  服务名 -> 容器名映射
# ──────────────────────────────────────────────────────────
declare -A SVC_CONTAINERS=(
  [gateway]="ilbuy-gateway"
  [gateway-svc]="ilbuy-gateway"
  [user]="ilbuy-user-svc"
  [user-svc]="ilbuy-user-svc"
  [product]="ilbuy-product-svc"
  [product-svc]="ilbuy-product-svc"
  [order]="ilbuy-order-svc"
  [order-svc]="ilbuy-order-svc"
  [supplier]="ilbuy-supplier-svc"
  [supplier-svc]="ilbuy-supplier-svc"
  [finance]="ilbuy-finance-svc"
  [finance-svc]="ilbuy-finance-svc"
  [message]="ilbuy-message-svc"
  [message-svc]="ilbuy-message-svc"
  [biz-data]="ilbuy-biz-data-svc"
  [biz-data-svc]="ilbuy-biz-data-svc"
  [ai]="ilbuy-ai-svc"
  [ai-svc]="ilbuy-ai-svc"
  # 中间件
  [mysql]="ilbuy-mysql"
  [redis]="ilbuy-redis"
  [es]="ilbuy-es"
  [elasticsearch]="ilbuy-es"
  [rabbitmq]="ilbuy-rabbitmq"
  [nacos]="ilbuy-nacos"
  [minio]="ilbuy-minio"
  [clickhouse]="ilbuy-clickhouse"
  [canal]="ilbuy-canal"
)

ALL_APP_CONTAINERS=(
  ilbuy-gateway
  ilbuy-user-svc
  ilbuy-product-svc
  ilbuy-order-svc
  ilbuy-supplier-svc
  ilbuy-finance-svc
  ilbuy-message-svc
  ilbuy-biz-data-svc
  ilbuy-ai-svc
)

# ──────────────────────────────────────────────────────────
#  颜色输出
# ──────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; NC='\033[0m'

colorize_log() {
  # 对日志级别着色
  sed -e "s/\(ERROR\|FATAL\)/${RED}\1${NC}/g" \
      -e "s/\(WARN\|WARNING\)/${YELLOW}\1${NC}/g" \
      -e "s/\(INFO\)/${GREEN}\1${NC}/g" \
      -e "s/\(DEBUG\|TRACE\)/${CYAN}\1${NC}/g" \
      2>/dev/null || cat
}

# ──────────────────────────────────────────────────────────
#  参数解析
# ──────────────────────────────────────────────────────────
SVC="${1:-}"
if [[ -z "$SVC" ]]; then
  echo "用法: bash $0 <服务名|all> [选项]"
  echo ""
  echo "服务名: gateway user product order supplier finance message biz-data ai"
  echo "        mysql redis es rabbitmq nacos minio clickhouse canal"
  echo "        all (所有微服务)"
  echo ""
  echo "选项:"
  echo "  -n <行数>       显示最近 N 行（默认 100）"
  echo "  -f              实时追踪日志"
  echo "  -l <级别>       过滤日志级别 (ERROR|WARN|INFO|DEBUG)"
  echo "  -k <关键词>     关键词过滤（支持正则）"
  echo "  -s <时间>       开始时间 (如: '2026-03-22 10:00')"
  echo "  -e <时间>       结束时间"
  echo "  --export <文件> 导出到文件"
  echo "  --no-color      不着色输出"
  exit 1
fi
shift

LINES=100
FOLLOW=false
LEVEL=""
KEYWORD=""
START_TIME=""
END_TIME=""
EXPORT_FILE=""
COLOR=true

while [[ $# -gt 0 ]]; do
  case "$1" in
    -n)          LINES="${2:?}"; shift 2 ;;
    -f|--follow) FOLLOW=true; shift ;;
    -l|--level)  LEVEL="${2:?}"; shift 2 ;;
    -k|--keyword) KEYWORD="${2:?}"; shift 2 ;;
    -s|--since)  START_TIME="${2:?}"; shift 2 ;;
    -e|--until)  END_TIME="${2:?}"; shift 2 ;;
    --export)    EXPORT_FILE="${2:?}"; shift 2 ;;
    --no-color)  COLOR=false; shift ;;
    *)           shift ;;
  esac
done

# ──────────────────────────────────────────────────────────
#  构建过滤管道
# ──────────────────────────────────────────────────────────
build_filter() {
  local filter="cat"

  # 时间范围过滤（适用于标准 Spring Boot 日志格式: 2026-03-22T10:01:23）
  if [[ -n "$START_TIME" ]]; then
    filter="${filter} | awk -v start=\"${START_TIME}\" '\$1\" \"\$2 >= start || /^[^0-9]/ {print}'"
  fi
  if [[ -n "$END_TIME" ]]; then
    filter="${filter} | awk -v end=\"${END_TIME}\" '\$1\" \"\$2 <= end || /^[^0-9]/ {print}'"
  fi

  # 日志级别过滤
  if [[ -n "$LEVEL" ]]; then
    filter="${filter} | grep -i '${LEVEL}'"
  fi

  # 关键词过滤
  if [[ -n "$KEYWORD" ]]; then
    filter="${filter} | grep -E '${KEYWORD}'"
  fi

  echo "$filter"
}

# ──────────────────────────────────────────────────────────
#  查询单个容器日志
# ──────────────────────────────────────────────────────────
query_container() {
  local container="$1"
  local prefix="${2:-}"

  if ! docker inspect "$container" > /dev/null 2>&1; then
    echo -e "${RED}[错误]${NC} 容器不存在: ${container}" >&2
    return 1
  fi

  local docker_args=("logs")
  docker_args+=("--tail" "${LINES}")
  [[ "$FOLLOW" == "true" ]] && docker_args+=("-f")
  [[ -n "$START_TIME" ]] && docker_args+=("--since" "${START_TIME}")
  [[ -n "$END_TIME" ]] && docker_args+=("--until" "${END_TIME}")
  docker_args+=("${container}")

  # 构建过滤命令
  local filter_cmd="cat"
  [[ -n "$LEVEL" ]] && filter_cmd="${filter_cmd} | grep --color=never -i '${LEVEL}'"
  [[ -n "$KEYWORD" ]] && filter_cmd="${filter_cmd} | grep --color=never -E '${KEYWORD}'"

  # 添加服务前缀（多服务模式）
  if [[ -n "$prefix" ]]; then
    filter_cmd="${filter_cmd} | sed 's/^/[${prefix}] /'"
  fi

  if [[ -n "$EXPORT_FILE" ]]; then
    eval "docker ${docker_args[*]} 2>&1 | ${filter_cmd}" >> "${EXPORT_FILE}"
    echo -e "${GREEN}✓${NC} 日志已追加到: ${EXPORT_FILE}"
  elif [[ "$COLOR" == "true" ]]; then
    eval "docker ${docker_args[*]} 2>&1 | ${filter_cmd}" | colorize_log
  else
    eval "docker ${docker_args[*]} 2>&1 | ${filter_cmd}"
  fi
}

# ──────────────────────────────────────────────────────────
#  主逻辑
# ──────────────────────────────────────────────────────────
if [[ "$SVC" == "all" ]]; then
  # 查询所有微服务
  if [[ "$FOLLOW" == "true" ]]; then
    echo -e "${YELLOW}[警告]${NC} 多服务实时追踪模式，使用 Ctrl+C 退出"
    # 并发追踪所有容器
    for container in "${ALL_APP_CONTAINERS[@]}"; do
      local_name="${container#ilbuy-}"
      docker logs --tail "${LINES}" -f "${container}" 2>&1 \
        | sed "s/^/[${local_name}] /" &
    done
    wait
  else
    for container in "${ALL_APP_CONTAINERS[@]}"; do
      local_name="${container#ilbuy-}"
      echo -e "\n${BLUE}══ ${container} ══${NC}"
      query_container "$container" "" || true
    done
  fi
else
  # 查询单个服务
  container=""
  if [[ -v "SVC_CONTAINERS[$SVC]" ]]; then
    container="${SVC_CONTAINERS[$SVC]}"
  else
    # 尝试直接用作容器名
    container="$SVC"
  fi

  if [[ -n "$EXPORT_FILE" ]]; then
    echo "=== ${container} 日志导出 $(date) ===" > "${EXPORT_FILE}"
    query_container "$container"
  else
    echo -e "${BLUE}════════════════════════════════════════${NC}"
    echo -e "${BLUE}  ${container}  |  最近 ${LINES} 行${LEVEL:+  |  级别: $LEVEL}${KEYWORD:+  |  关键词: $KEYWORD}${NC}"
    echo -e "${BLUE}════════════════════════════════════════${NC}"
    query_container "$container"
  fi
fi
