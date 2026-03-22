#!/usr/bin/env bash
# ============================================================
# ILbuy 监控告警脚本
# 用途：检查所有服务和中间件健康状态，异常时发送告警
# 用法：
#   bash monitor.sh                    # 检查一次
#   bash monitor.sh --watch 60         # 每 60 秒检查一次
#   bash monitor.sh --service mysql    # 检查单个服务
#   bash monitor.sh --alert-only       # 仅输出告警信息
# 依赖：docker, curl
# 告警渠道：企业微信 Webhook（配置 WECHAT_WEBHOOK）
#           钉钉 Webhook（配置 DINGTALK_WEBHOOK）
#           SMTP 邮件（配置 MAIL_* 变量）
# ============================================================
set -euo pipefail

# ──────────────────────────────────────────────────────────
#  配置
# ──────────────────────────────────────────────────────────
WECHAT_WEBHOOK="${WECHAT_WEBHOOK:-}"
DINGTALK_WEBHOOK="${DINGTALK_WEBHOOK:-}"
MAIL_TO="${MAIL_TO:-}"
MAIL_FROM="${MAIL_FROM:-alert@ilbuy.com}"
SMTP_HOST="${SMTP_HOST:-}"
ALERT_ONLY=false
WATCH_INTERVAL=0
ENV_NAME="${ENV_NAME:-local}"

# 阈值
CPU_WARN=80     # CPU 使用率警告阈值 (%)
CPU_CRIT=95     # CPU 使用率严重阈值 (%)
MEM_WARN=80     # 内存使用率警告阈值 (%)
MEM_CRIT=95     # 内存使用率严重阈值 (%)
DISK_WARN=80    # 磁盘使用率警告阈值 (%)
DISK_CRIT=95    # 磁盘使用率严重阈值 (%)

# 服务端口健康检查列表（容器名:健康检查URL）
declare -A SVC_HEALTH=(
  [ilbuy-gateway]="http://localhost:8080/actuator/health"
  [ilbuy-user-svc]="http://localhost:8081/actuator/health"
  [ilbuy-product-svc]="http://localhost:8082/actuator/health"
  [ilbuy-order-svc]="http://localhost:8083/actuator/health"
  [ilbuy-supplier-svc]="http://localhost:8084/actuator/health"
  [ilbuy-finance-svc]="http://localhost:8086/actuator/health"
  [ilbuy-message-svc]="http://localhost:8087/actuator/health"
  [ilbuy-biz-data-svc]="http://localhost:8088/health"
  [ilbuy-ai-svc]="http://localhost:8089/actuator/health"
)

# 中间件容器检查
MIDDLEWARE_CONTAINERS=(
  ilbuy-mysql
  ilbuy-redis
  ilbuy-es
  ilbuy-rabbitmq
  ilbuy-nacos
  ilbuy-minio
  ilbuy-clickhouse
  ilbuy-canal
)

# ──────────────────────────────────────────────────────────
#  颜色输出
# ──────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
info()    { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[CRIT]${NC}  $*"; }
section() { echo -e "\n${BLUE}══ $* ══${NC}\n"; }

# 告警收集器
ALERTS=()
WARNINGS=()
CHECK_RESULTS=()

add_alert()   { ALERTS+=("$1"); }
add_warning() { WARNINGS+=("$1"); }
add_result()  { CHECK_RESULTS+=("$1"); }

# ──────────────────────────────────────────────────────────
#  Docker 容器状态检查
# ──────────────────────────────────────────────────────────
check_container() {
  local container="$1"
  local status health

  status=$(docker inspect --format='{{.State.Status}}' "${container}" 2>/dev/null || echo "not_found")
  health=$(docker inspect --format='{{.State.Health.Status}}' "${container}" 2>/dev/null || echo "none")

  if [[ "$status" == "not_found" ]]; then
    add_alert "容器不存在: ${container}"
    add_result "  ${container}: [不存在]"
    return 1
  elif [[ "$status" != "running" ]]; then
    add_alert "容器未运行: ${container} (状态: ${status})"
    add_result "  ${container}: [${status}]"
    return 1
  elif [[ "$health" == "unhealthy" ]]; then
    add_alert "容器不健康: ${container}"
    add_result "  ${container}: [running/unhealthy]"
    return 1
  elif [[ "$health" == "starting" ]]; then
    add_warning "容器健康检查进行中: ${container}"
    add_result "  ${container}: [starting]"
    return 0
  else
    add_result "  ${container}: [OK]"
    return 0
  fi
}

# ──────────────────────────────────────────────────────────
#  HTTP 健康检查
# ──────────────────────────────────────────────────────────
check_http() {
  local name="$1"
  local url="$2"
  local resp

  resp=$(curl -sf --max-time 5 "$url" 2>/dev/null || echo "")
  if [[ -z "$resp" ]]; then
    add_alert "HTTP 健康检查失败: ${name} (${url})"
    add_result "  ${name}: [HTTP_FAIL]"
    return 1
  elif echo "$resp" | grep -q '"status":"DOWN"' 2>/dev/null; then
    add_alert "服务状态 DOWN: ${name}"
    add_result "  ${name}: [DOWN]"
    return 1
  else
    add_result "  ${name}: [OK]"
    return 0
  fi
}

# ──────────────────────────────────────────────────────────
#  资源使用检查
# ──────────────────────────────────────────────────────────
check_resources() {
  section "系统资源"

  # CPU
  local cpu_usage
  cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d. -f1 2>/dev/null || echo "0")
  if [[ $cpu_usage -ge $CPU_CRIT ]]; then
    add_alert "CPU 使用率过高: ${cpu_usage}%"
    error "CPU: ${cpu_usage}% (严重 ≥${CPU_CRIT}%)"
  elif [[ $cpu_usage -ge $CPU_WARN ]]; then
    add_warning "CPU 使用率偏高: ${cpu_usage}%"
    warn "CPU: ${cpu_usage}% (警告 ≥${CPU_WARN}%)"
  else
    info "CPU: ${cpu_usage}%"
  fi

  # 内存
  local mem_total mem_used mem_pct
  mem_total=$(free -m | awk '/^Mem:/ {print $2}')
  mem_used=$(free -m | awk '/^Mem:/ {print $3}')
  mem_pct=$((mem_used * 100 / mem_total))
  if [[ $mem_pct -ge $MEM_CRIT ]]; then
    add_alert "内存使用率过高: ${mem_pct}% (${mem_used}M/${mem_total}M)"
    error "内存: ${mem_pct}% (严重 ≥${MEM_CRIT}%)"
  elif [[ $mem_pct -ge $MEM_WARN ]]; then
    add_warning "内存使用率偏高: ${mem_pct}%"
    warn "内存: ${mem_pct}% (警告 ≥${MEM_WARN}%)"
  else
    info "内存: ${mem_pct}% (${mem_used}M/${mem_total}M)"
  fi

  # 磁盘
  while IFS= read -r line; do
    local mount usage
    mount=$(echo "$line" | awk '{print $6}')
    usage=$(echo "$line" | awk '{print $5}' | tr -d '%')
    if [[ $usage -ge $DISK_CRIT ]]; then
      add_alert "磁盘使用率过高: ${mount} ${usage}%"
      error "磁盘 ${mount}: ${usage}% (严重)"
    elif [[ $usage -ge $DISK_WARN ]]; then
      add_warning "磁盘使用率偏高: ${mount} ${usage}%"
      warn "磁盘 ${mount}: ${usage}% (警告)"
    else
      info "磁盘 ${mount}: ${usage}%"
    fi
  done < <(df -h | awk 'NR>1 && $6 ~ /^\/(data|var|home)?$/ {print}' 2>/dev/null || true)
}

# ──────────────────────────────────────────────────────────
#  检查所有中间件
# ──────────────────────────────────────────────────────────
check_middleware() {
  section "中间件状态"
  for container in "${MIDDLEWARE_CONTAINERS[@]}"; do
    check_container "$container" || true
  done
  printf '%s\n' "${CHECK_RESULTS[@]}" 2>/dev/null || true
  CHECK_RESULTS=()
}

# ──────────────────────────────────────────────────────────
#  检查所有微服务
# ──────────────────────────────────────────────────────────
check_services() {
  section "微服务状态"
  for container in "${!SVC_HEALTH[@]}"; do
    check_container "$container" || true
  done
  printf '%s\n' "${CHECK_RESULTS[@]}" 2>/dev/null || true
  CHECK_RESULTS=()

  section "微服务 HTTP 健康检查"
  for container in "${!SVC_HEALTH[@]}"; do
    local url="${SVC_HEALTH[$container]}"
    check_http "$container" "$url" || true
  done
  printf '%s\n' "${CHECK_RESULTS[@]}" 2>/dev/null || true
  CHECK_RESULTS=()
}

# ──────────────────────────────────────────────────────────
#  发送告警
# ──────────────────────────────────────────────────────────
send_alert() {
  local level="$1"   # CRITICAL | WARNING
  local message="$2"
  local timestamp
  timestamp=$(date '+%Y-%m-%d %H:%M:%S')
  local title="[${level}] ILbuy ${ENV_NAME} 环境告警 - ${timestamp}"

  # 企业微信
  if [[ -n "$WECHAT_WEBHOOK" ]]; then
    local payload
    payload=$(cat <<EOF
{
  "msgtype": "markdown",
  "markdown": {
    "content": "## ${title}\n\n${message}"
  }
}
EOF
)
    curl -sf -X POST "$WECHAT_WEBHOOK" \
      -H 'Content-Type: application/json' \
      -d "$payload" > /dev/null 2>&1 || warn "企业微信告警发送失败"
  fi

  # 钉钉
  if [[ -n "$DINGTALK_WEBHOOK" ]]; then
    local payload
    payload=$(cat <<EOF
{
  "msgtype": "markdown",
  "markdown": {
    "title": "${title}",
    "text": "## ${title}\n\n${message}"
  },
  "at": {"isAtAll": false}
}
EOF
)
    curl -sf -X POST "$DINGTALK_WEBHOOK" \
      -H 'Content-Type: application/json' \
      -d "$payload" > /dev/null 2>&1 || warn "钉钉告警发送失败"
  fi
}

# ──────────────────────────────────────────────────────────
#  汇总并告警
# ──────────────────────────────────────────────────────────
report_and_alert() {
  section "检查汇总"
  local has_issue=false

  if [[ ${#ALERTS[@]} -gt 0 ]]; then
    has_issue=true
    error "严重告警 (${#ALERTS[@]} 条):"
    local alert_text=""
    for alert in "${ALERTS[@]}"; do
      error "  - ${alert}"
      alert_text+="- ${alert}\n"
    done
    send_alert "CRITICAL" "$alert_text"
  fi

  if [[ ${#WARNINGS[@]} -gt 0 ]]; then
    has_issue=true
    warn "警告 (${#WARNINGS[@]} 条):"
    local warn_text=""
    for warning in "${WARNINGS[@]}"; do
      warn "  - ${warning}"
      warn_text+="- ${warning}\n"
    done
    [[ ${#ALERTS[@]} -eq 0 ]] && send_alert "WARNING" "$warn_text"
  fi

  if [[ "$has_issue" == "false" ]]; then
    info "✓ 所有服务健康，无告警"
  fi

  return $([[ "$has_issue" == "false" ]] && echo 0 || echo 1) 2>/dev/null || true
}

# ──────────────────────────────────────────────────────────
#  参数解析
# ──────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --watch)     WATCH_INTERVAL="${2:-60}"; shift 2 ;;
    --alert-only) ALERT_ONLY=true; shift ;;
    --service)
      TARGET_SVC="${2:-}"; shift 2
      check_container "$TARGET_SVC" || true
      printf '%s\n' "${CHECK_RESULTS[@]}" 2>/dev/null || true
      exit 0 ;;
    *)           shift ;;
  esac
done

# ──────────────────────────────────────────────────────────
#  主流程
# ──────────────────────────────────────────────────────────
run_checks() {
  ALERTS=()
  WARNINGS=()
  CHECK_RESULTS=()

  echo -e "${BLUE}════════════════════════════════════════${NC}"
  echo -e "${BLUE}  ILbuy 监控检查  $(date '+%Y-%m-%d %H:%M:%S')${NC}"
  echo -e "${BLUE}════════════════════════════════════════${NC}"

  check_middleware
  check_services
  check_resources
  report_and_alert || true
}

if [[ $WATCH_INTERVAL -gt 0 ]]; then
  info "启动持续监控（间隔 ${WATCH_INTERVAL}s，Ctrl+C 停止）"
  while true; do
    run_checks
    sleep "${WATCH_INTERVAL}"
  done
else
  run_checks
fi
