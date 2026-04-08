#!/usr/bin/env bash
# ILbuy 全服务健康检查
# 用法: ./health-check.sh [base_url]

BASE="${1:-http://localhost:8080}"
PASS=0; FAIL=0

check() {
    local name="$1" url="$2" key="${3:-status}" val="${4:-UP}"
    local body; body=$(curl -sf "$url" 2>/dev/null)
    if echo "$body" | grep -qE "\"${key}\":\s*\"?${val}\"?"; then
        echo "  ✅ $name"
        ((PASS++))
    else
        echo "  ❌ $name  → $url"
        echo "     响应: $(echo "$body" | head -c 200)"
        ((FAIL++))
    fi
}

echo "=== ILbuy 健康检查 ==="
echo "时间: $(date)"
echo ""

echo "【API网关】"
check "Gateway /actuator/health"  "$BASE/actuator/health"  "status" "UP"

echo ""
echo "【下游服务】"
check "user-service"              "http://localhost:8001/health" "status" "UP"
check "procurement-service"       "http://localhost:8002/health" "status" "UP"
check "ai-matching-service"       "http://localhost:8003/health" "status" "UP"
check "order-service"             "http://localhost:8004/health" "status" "UP"
check "data-collector-service"    "http://localhost:8005/health" "status" "UP"
check "product-service"           "http://localhost:8006/health" "status" "UP"

echo ""
echo "【Redis】"
if redis-cli -a "ILbuy@Redis2024" ping 2>/dev/null | grep -q PONG; then
    echo "  ✅ Redis"
    ((PASS++))
else
    echo "  ❌ Redis (localhost:6379)"
    ((FAIL++))
fi

echo ""
echo "─────────────────────────"
echo "通过: $PASS  失败: $FAIL"
[ $FAIL -eq 0 ] && echo "状态: ✅ ALL HEALTHY" || echo "状态: ⚠️  DEGRADED"
