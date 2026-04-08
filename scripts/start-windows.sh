#!/usr/bin/env bash
# ILbuy Windows 本地启动脚本（Git Bash）
# 无需 Docker / Redis / gunicorn
# 用法: bash scripts/start-windows.sh

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="/tmp/ilbuy-logs"
PID_FILE="/tmp/ilbuy.pids"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; }

# 检测 python 命令（Windows 通常是 python，Linux 是 python3）
PYTHON=""
for cmd in python python3; do
    if command -v "$cmd" >/dev/null 2>&1; then
        ver=$("$cmd" --version 2>&1)
        if echo "$ver" | grep -q "Python 3"; then
            PYTHON="$cmd"
            break
        fi
    fi
done
if [ -z "$PYTHON" ]; then
    error "未找到 Python 3，请先安装 Python 3.8+"
    exit 1
fi
info "使用 Python: $PYTHON ($($PYTHON --version 2>&1))"

# 安装依赖
install_deps() {
    info "检查并安装依赖..."
    "$PYTHON" -m pip install -q flask flask-limiter requests 2>/dev/null && \
        info "  依赖已就绪" || warn "  pip 安装可能有警告，继续..."
}

# 停止旧进程
stop_old() {
    if [ -f "$PID_FILE" ]; then
        info "停止旧进程..."
        while IFS=' ' read -r pid name; do
            if kill "$pid" 2>/dev/null; then
                info "  停止 $name (PID $pid)"
            fi
        done < "$PID_FILE"
        rm -f "$PID_FILE"
        sleep 2
    fi
    # 释放端口（强制）
    for port in 8001 8002 8003 8004 8005 8006 8080; do
        pid=$(netstat -ano 2>/dev/null | grep ":${port} " | grep LISTEN | awk '{print $NF}' | head -1)
        if [ -n "$pid" ] && [ "$pid" != "0" ]; then
            taskkill //F //PID "$pid" 2>/dev/null || true
        fi
    done
}

# 启动单个服务
start_service() {
    local name="$1"
    local port="$2"
    local svc_dir="$3"
    local log="$LOG_DIR/${name}.log"

    mkdir -p "$LOG_DIR"

    export JWT_SECRET="ILbuy@JWT@SecretKey@2024@Production"
    export USER_SERVICE_URL="http://localhost:8001"
    export PROCUREMENT_SERVICE_URL="http://localhost:8002"
    export AI_SERVICE_URL="http://localhost:8003"
    export ORDER_SERVICE_URL="http://localhost:8004"
    export DATA_SERVICE_URL="http://localhost:8005"
    export PRODUCT_SERVICE_URL="http://localhost:8006"
    # 使用内存限流（无需 Redis）
    export RATELIMIT_STORAGE_URI="memory://"

    info "启动 ${name} (端口 ${port})..."
    (
        cd "$svc_dir"
        export FLASK_ENV=development
        "$PYTHON" app.py > "$log" 2>&1
    ) &
    local pid=$!
    echo "$pid $name" >> "$PID_FILE"
    info "  → PID $pid | 日志: $log"
}

# 等待服务就绪
wait_healthy() {
    local url="$1" name="$2" max="${3:-20}"
    for i in $(seq 1 $max); do
        if curl -sf "$url" >/dev/null 2>&1; then
            info "  ✓ ${name} 健康"
            return 0
        fi
        sleep 1
    done
    warn "  ✗ ${name} ${max}s 内未就绪，查看日志: $LOG_DIR/${name}.log"
    return 1
}

# 主流程
main() {
    info "=== ILbuy Windows 本地启动 ==="
    info "项目目录: $REPO_ROOT"

    install_deps
    stop_old
    touch "$PID_FILE"

    start_service "user-service"           8001 "$REPO_ROOT/services/user-service"
    wait_healthy   "http://localhost:8001/health" "user-service"

    start_service "procurement-service"    8002 "$REPO_ROOT/services/procurement-service"
    wait_healthy   "http://localhost:8002/health" "procurement-service"

    start_service "ai-matching-service"    8003 "$REPO_ROOT/services/ai-matching-service"
    wait_healthy   "http://localhost:8003/health" "ai-matching-service"

    start_service "order-service"          8004 "$REPO_ROOT/services/order-service"
    wait_healthy   "http://localhost:8004/health" "order-service"

    start_service "data-collector-service" 8005 "$REPO_ROOT/services/data-collector-service"
    wait_healthy   "http://localhost:8005/health" "data-collector-service"

    start_service "product-service"        8006 "$REPO_ROOT/services/product-service"
    wait_healthy   "http://localhost:8006/health" "product-service"

    start_service "api-gateway"            8080 "$REPO_ROOT/services/api-gateway"
    wait_healthy   "http://localhost:8080/actuator/health" "api-gateway" 30

    echo ""
    info "=== 所有服务已启动 ==="
    echo ""
    echo "  API 网关:       http://localhost:8080/actuator/health"
    echo "  用户服务:       http://localhost:8001/health"
    echo "  采购服务:       http://localhost:8002/health"
    echo "  AI匹配服务:     http://localhost:8003/health"
    echo "  订单服务:       http://localhost:8004/health"
    echo "  数据采集服务:   http://localhost:8005/health"
    echo "  商品服务:       http://localhost:8006/health"
    echo ""
    echo "  日志目录:       $LOG_DIR"
    echo "  停止所有:       bash scripts/stop-local.sh"
    echo ""
    echo "  运行集成测试:"
    echo "    PYTHONIOENCODING=utf-8 $PYTHON tests/integration_test.py"
    echo ""
}

main "$@"
