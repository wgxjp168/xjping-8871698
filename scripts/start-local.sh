#!/usr/bin/env bash
# ILbuy 本地进程模式启动脚本（无Docker）
# 适用于开发调试、CI环境
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="/tmp/ilbuy-logs"
PID_FILE="/tmp/ilbuy.pids"
VENV_DIR="/tmp/ilbuy-venv"

# ─── 颜色输出 ─────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

# ─── 依赖检查 ─────────────────────────────
check_deps() {
    command -v python3 >/dev/null || error "需要 python3"
    command -v redis-cli >/dev/null || warn "redis-cli 未找到，跳过 Redis 检查"
    redis-cli -a "ILbuy@Redis2024" ping 2>/dev/null | grep -q PONG || \
        warn "Redis 未运行！限流功能将降级，请先启动: redis-server --requirepass ILbuy@Redis2024"
}

# ─── 虚拟环境 ─────────────────────────────
setup_venv() {
    if [ ! -d "$VENV_DIR" ]; then
        info "创建 Python 虚拟环境..."
        python3 -m venv "$VENV_DIR"
    fi
    source "$VENV_DIR/bin/activate"
    info "安装依赖..."
    pip install -q flask==3.1.3 flask-limiter==4.1.1 gunicorn==23.0.0 requests==2.32.3 redis==7.3.0 \
        --ignore-installed blinker 2>/dev/null
}

# ─── 启动单个服务 ─────────────────────────
start_service() {
    local name="$1" port="$2" app_dir="$3" extra_env="${4:-}"
    local log="$LOG_DIR/${name}.log"

    mkdir -p "$LOG_DIR"

    # 设置环境变量
    export JWT_SECRET="ILbuy@JWT@SecretKey@2024@Production"
    export REDIS_HOST="localhost"
    export REDIS_PORT="6379"
    export REDIS_PASSWORD="ILbuy@Redis2024"
    export USER_SERVICE_URL="http://localhost:8001"
    export PROCUREMENT_SERVICE_URL="http://localhost:8002"
    export AI_SERVICE_URL="http://localhost:8003"
    export ORDER_SERVICE_URL="http://localhost:8004"
    export DATA_SERVICE_URL="http://localhost:8005"
    [ -n "$extra_env" ] && eval "export $extra_env"

    info "启动 ${name} (端口 ${port})..."
    cd "$app_dir"

    # 初始化 DB（user-service 需要 seed 数据）
    python3 app.py 2>/dev/null &
    local init_pid=$!
    sleep 1
    kill $init_pid 2>/dev/null || true

    # 启动 gunicorn
    gunicorn -w 2 -b "0.0.0.0:${port}" --timeout 60 \
        --log-level warning --access-logfile - \
        app:app >> "$log" 2>&1 &
    echo "$! $name" >> "$PID_FILE"
    info "  → PID $! | 日志: $log"
}

# ─── 等待服务健康 ─────────────────────────
wait_healthy() {
    local url="$1" name="$2" max="${3:-30}"
    for i in $(seq 1 $max); do
        if curl -sf "$url" >/dev/null 2>&1; then
            info "  ✓ $name 健康"
            return 0
        fi
        sleep 1
    done
    warn "$name 在 ${max}s 内未就绪，继续..."
}

# ─── 主流程 ───────────────────────────────
main() {
    info "=== ILbuy 本地进程模式启动 ==="
    check_deps
    setup_venv
    source "$VENV_DIR/bin/activate"

    # 清理旧进程
    if [ -f "$PID_FILE" ]; then
        info "停止旧进程..."
        while read -r pid name; do
            kill "$pid" 2>/dev/null && info "  停止 $name (PID $pid)" || true
        done < "$PID_FILE"
        rm -f "$PID_FILE"
        sleep 2
    fi

    # 清理旧 DB（可选：--clean 参数）
    if [[ "${1:-}" == "--clean" ]]; then
        info "清理旧数据库..."
        rm -f /tmp/ilbuy_*.db
    fi

    touch "$PID_FILE"

    # 按依赖顺序启动
    start_service "user-service"            8001 "$REPO_ROOT/services/user-service"
    wait_healthy "http://localhost:8001/health" "user-service"

    start_service "procurement-service"     8002 "$REPO_ROOT/services/procurement-service"
    wait_healthy "http://localhost:8002/health" "procurement-service"

    start_service "ai-matching-service"     8003 "$REPO_ROOT/services/ai-matching-service"
    wait_healthy "http://localhost:8003/health" "ai-matching-service"

    start_service "order-service"           8004 "$REPO_ROOT/services/order-service"
    wait_healthy "http://localhost:8004/health" "order-service"

    start_service "data-collector-service"  8005 "$REPO_ROOT/services/data-collector-service"
    wait_healthy "http://localhost:8005/health" "data-collector-service"

    start_service "product-service"         8006 "$REPO_ROOT/services/product-service"
    wait_healthy "http://localhost:8006/health" "product-service"

    start_service "api-gateway"             8080 "$REPO_ROOT/services/api-gateway"
    wait_healthy "http://localhost:8080/actuator/health" "api-gateway" 40

    echo ""
    info "=== 所有服务已启动 ==="
    echo ""
    echo "  API 网关:             http://localhost:8080"
    echo "  用户服务:             http://localhost:8001"
    echo "  采购服务:             http://localhost:8002"
    echo "  AI匹配服务:           http://localhost:8003"
    echo "  订单服务:             http://localhost:8004"
    echo "  数据采集服务:          http://localhost:8005"
    echo "  商品服务:             http://localhost:8006"
    echo ""
    echo "  日志目录:  $LOG_DIR"
    echo "  停止所有:  $REPO_ROOT/scripts/stop-local.sh"
    echo ""
}

main "$@"
