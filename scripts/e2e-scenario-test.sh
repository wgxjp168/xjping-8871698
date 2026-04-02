#!/usr/bin/env bash
# ════════════════════════════════════════════════════════
# ILbuy E2E 全链路业务场景测试
# 覆盖: B2B采购需求提交 → AI决策匹配 → 报价确认 → 支付 → 确认收货
# 用法: ./e2e-scenario-test.sh [base_url]
# ════════════════════════════════════════════════════════
set -euo pipefail

BASE="${1:-http://localhost:8080}"
PASS=0; FAIL=0; SKIP=0
STEP=0

# ─── 颜色 & 工具函数 ─────────────────────
GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

step()  { STEP=$((STEP+1)); echo -e "\n${CYAN}${BOLD}[步骤 ${STEP}] $*${NC}"; }
pass()  { PASS=$((PASS+1)); echo -e "  ${GREEN}✓ $*${NC}"; }
fail()  { FAIL=$((FAIL+1)); echo -e "  ${RED}✗ $*${NC}"; }
info()  { echo -e "  ${YELLOW}→ $*${NC}"; }
banner(){ echo -e "\n${BOLD}══════════════════════════════════════════${NC}"; echo -e "${BOLD}  $*${NC}"; echo -e "${BOLD}══════════════════════════════════════════${NC}"; }

# HTTP 请求工具
do_req() {
    local method="$1" url="$2" body="${3:-}" token="${4:-}"
    local tmpfile; tmpfile=$(mktemp)
    local args=(-s -o "$tmpfile" -w "%{http_code}" -X "$method" -H "Content-Type: application/json")
    [ -n "$token" ] && args+=(-H "Authorization: Bearer $token")
    [ -n "$body"  ] && args+=(-d "$body")
    HTTP_CODE=$(curl "${args[@]}" "$url" 2>/dev/null)
    RESP=$(cat "$tmpfile"); rm -f "$tmpfile"
}

assert_code() {
    local expected="$1" desc="$2"
    if [ "$HTTP_CODE" = "$expected" ]; then
        pass "$desc (HTTP $HTTP_CODE)"
    else
        fail "$desc (期望 HTTP $expected, 实际 $HTTP_CODE)"
        info "响应: $(echo "$RESP" | head -c 300)"
    fi
}

assert_field() {
    local key="$1" val="$2" desc="$3"
    if echo "$RESP" | grep -qE "\"${key}\":\s*\"?${val}\"?"; then
        pass "$desc"
    else
        fail "$desc (字段 ${key}=${val} 未找到)"
        info "响应: $(echo "$RESP" | head -c 300)"
    fi
}

extract() {
    # 提取 JSON 字段值 (简单版)
    echo "$RESP" | grep -oE "\"$1\":\s*[0-9]+" | head -1 | grep -oE "[0-9]+$" || \
    echo "$RESP" | grep -oP "\"$1\":\s*\"\K[^\"]*" | head -1 || echo ""
}

echo ""
banner "ILbuy E2E 全链路业务场景测试"
echo "  目标: $BASE"
echo "  时间: $(date)"
echo "  场景: B2B采购 → AI匹配 → 报价 → 支付 → 确认收货"

# ════════════════════════════════════════════════════════
banner "场景一: 服务健康检查"
# ════════════════════════════════════════════════════════

step "检查 API 网关健康状态"
do_req GET "$BASE/actuator/health"
assert_code 200 "健康检查接口"
assert_field "status" "UP" "系统状态 UP"

# ════════════════════════════════════════════════════════
banner "场景二: 用户认证流程"
# ════════════════════════════════════════════════════════

step "采购方登录（B2B买家）"
do_req POST "$BASE/api/v1/auth/login" '{"username":"buyer01","password":"Buyer@123456"}'
assert_code 200 "买家登录"
assert_field "code" "0" "业务码=0"
BUYER_TOKEN=$(extract "accessToken")
BUYER_ID=$(extract "userId")
info "买家 ID=$BUYER_ID Token 前缀: ${BUYER_TOKEN:0:20}..."

step "供应商登录（报价方）"
do_req POST "$BASE/api/v1/auth/login" '{"username":"supplier01","password":"Supplier@123456"}'
assert_code 200 "供应商登录"
SUPPLIER_TOKEN=$(extract "accessToken")
SUPPLIER_ID=$(extract "userId")
info "供应商 ID=$SUPPLIER_ID"

step "Token 验证（受保护接口）"
do_req GET "$BASE/api/v1/procurement/demands?page=0&size=5" "" "$BUYER_TOKEN"
assert_code 200 "携带Token访问受保护接口"

step "无 Token 访问被拒绝"
do_req GET "$BASE/api/v1/procurement/demands"
assert_code 401 "未授权访问返回 401"

# ════════════════════════════════════════════════════════
banner "场景三: B2B 采购需求提交"
# ════════════════════════════════════════════════════════
UNIQ=$(date +%s)

step "创建采购需求（办公设备）"
DEMAND_BODY="{\"userId\":$BUYER_ID,\"title\":\"E2E-Test-Laptop-${UNIQ}\",\"category\":\"IT\",\"quantity\":20,\"unit\":\"unit\",\"budget\":130000.00,\"description\":\"Purchase 20 business laptops i7 16G 512G SSD\"}"
do_req POST "$BASE/api/v1/procurement/demands" "$DEMAND_BODY" "$BUYER_TOKEN"
assert_code 200 "创建采购需求"
assert_field "code" "0" "业务码=0"
DEMAND_ID=$(extract "id")
info "采购需求 ID=$DEMAND_ID"

step "查询采购需求列表"
do_req GET "$BASE/api/v1/procurement/demands?page=0&size=10" "" "$BUYER_TOKEN"
assert_code 200 "查询需求列表"
assert_field "total" "[1-9][0-9]*" "列表有数据"

step "查询采购需求详情"
do_req GET "$BASE/api/v1/procurement/demands/$DEMAND_ID" "" "$BUYER_TOKEN"
assert_code 200 "查询需求详情"
assert_field "status" "PENDING" "需求状态=PENDING"

# ════════════════════════════════════════════════════════
banner "场景四: AI 智能匹配决策"
# ════════════════════════════════════════════════════════

step "触发 AI 智能供应商匹配"
AI_BODY="{\"demandId\":$DEMAND_ID,\"userId\":$BUYER_ID,\"keyword\":\"Laptop\",\"category\":\"IT\",\"budget\":130000.00}"
do_req POST "$BASE/api/v1/ai/match" "$AI_BODY" "$BUYER_TOKEN"
assert_code 200 "触发AI匹配"
assert_field "code" "0" "业务码=0"
TASK_ID=$(echo "$RESP" | grep -oP '"taskId":\s*"\K[^"]*' | head -1 || echo "")
info "匹配任务 ID=$TASK_ID"

step "查询 AI 匹配状态"
do_req GET "$BASE/api/v1/ai/match/${TASK_ID}/result" "" "$BUYER_TOKEN"
assert_code 200 "查询匹配结果"
assert_field "status" "COMPLETED" "匹配已完成"

step "验证匹配结果包含供应商"
if echo "$RESP" | grep -q "suppliers"; then
    pass "匹配结果包含供应商列表"
    SUPPLIER_NAME=$(echo "$RESP" | grep -oP '"supplierName":\s*"\K[^"]*' | head -1 || echo "优选供应商A")
    info "推荐供应商: $SUPPLIER_NAME"
else
    fail "匹配结果缺少 suppliers 字段"
fi

step "获取 AI 推荐供应商（关键词搜索）"
do_req GET "$BASE/api/v1/ai/suppliers/recommend?keyword=laptop&category=IT" "" "$BUYER_TOKEN"
assert_code 200 "AI推荐供应商"

# ════════════════════════════════════════════════════════
banner "场景五: 供应商报价"
# ════════════════════════════════════════════════════════

step "注册测试供应商（数据采集服务）"
SUP_BODY="{\"companyName\":\"E2E-Test-Supplier-${UNIQ}\",\"creditCode\":\"91110TEST${UNIQ}\",\"contactPerson\":\"TestManager\",\"contactPhone\":\"13800${UNIQ:0:6}\",\"address\":\"TestAddress-1\",\"businessScope\":\"IT/Laptop/Server\",\"qualificationLevel\":\"AA\"}"
do_req POST "$BASE/api/v1/suppliers" "$SUP_BODY" "$SUPPLIER_TOKEN"
assert_code 200 "注册供应商"
TEST_SUPPLIER_ID=$(extract "id")
info "测试供应商 ID=$TEST_SUPPLIER_ID"

step "供应商提交报价"
QUOTE_BODY="{\"demandId\":$DEMAND_ID,\"supplierId\":$TEST_SUPPLIER_ID,\"supplierName\":\"E2E-Test-Supplier-${UNIQ}\",\"unitPrice\":5800.00,\"totalPrice\":116000.00,\"deliveryDays\":7,\"warrantyMonths\":24,\"remark\":\"Brand-new 7-day-return\"}"
do_req POST "$BASE/api/v1/procurement/quotes" "$QUOTE_BODY" "$SUPPLIER_TOKEN"
assert_code 200 "提交报价"
QUOTE_ID=$(extract "id")
info "报价 ID=$QUOTE_ID"

step "买家查询报价列表"
do_req GET "$BASE/api/v1/procurement/quotes?demandId=$DEMAND_ID" "" "$BUYER_TOKEN"
assert_code 200 "查询报价列表"
assert_field "total" "[1-9]" "报价列表有数据"

step "买家接受报价"
do_req PUT "$BASE/api/v1/procurement/quotes/$QUOTE_ID/accept" '{}' "$BUYER_TOKEN"
assert_code 200 "接受报价"
assert_field "status" "ACCEPTED" "报价状态=ACCEPTED"

# ════════════════════════════════════════════════════════
banner "场景六: 创建订单 & 支付"
# ════════════════════════════════════════════════════════

step "根据报价创建订单"
ORDER_BODY="{\"demandId\":$DEMAND_ID,\"quoteId\":$QUOTE_ID,\"buyerId\":$BUYER_ID,\"supplierId\":$TEST_SUPPLIER_ID,\"supplierName\":\"E2E-Test-Supplier-${UNIQ}\",\"productName\":\"Laptop-i7-16G-512G\",\"quantity\":20,\"unitPrice\":5800.00,\"totalAmount\":116000.00,\"deliveryDays\":7,\"paymentMethod\":\"BANK_TRANSFER\",\"remark\":\"E2E-Full-Chain-Test\"}"
do_req POST "$BASE/api/v1/orders" "$ORDER_BODY" "$BUYER_TOKEN"
assert_code 200 "创建订单"
assert_field "code" "0" "业务码=0"
ORDER_ID=$(extract "id")
ORDER_NO=$(echo "$RESP" | grep -oP '"orderNo":\s*"\K[^"]*' | head -1 || echo "")
info "订单 ID=$ORDER_ID  订单号=$ORDER_NO"

step "查询订单详情（状态=CREATED）"
do_req GET "$BASE/api/v1/orders/$ORDER_ID" "" "$BUYER_TOKEN"
assert_code 200 "查询订单详情"
assert_field "order_status" "CREATED" "订单状态=CREATED"
assert_field "payment_status" "UNPAID" "支付状态=UNPAID"

step "买家完成支付"
do_req PUT "$BASE/api/v1/orders/$ORDER_ID/pay" '{"paymentMethod":"BANK_TRANSFER"}' "$BUYER_TOKEN"
assert_code 200 "完成支付"
assert_field "paymentStatus" "PAID" "支付状态=PAID"

step "重复支付被拒绝（幂等性）"
do_req PUT "$BASE/api/v1/orders/$ORDER_ID/pay" '{}' "$BUYER_TOKEN"
assert_code 400 "重复支付返回 400"

# ════════════════════════════════════════════════════════
banner "场景七: 发货 & 确认收货"
# ════════════════════════════════════════════════════════

step "供应商确认发货"
do_req PUT "$BASE/api/v1/orders/$ORDER_ID/ship" '{}' "$SUPPLIER_TOKEN"
assert_code 200 "确认发货"
assert_field "orderStatus" "SHIPPED" "订单状态=SHIPPED"

step "买家确认收货（完成交易）"
do_req PUT "$BASE/api/v1/orders/$ORDER_ID/confirm-receipt" '{}' "$BUYER_TOKEN"
assert_code 200 "确认收货"
assert_field "orderStatus" "COMPLETED" "订单状态=COMPLETED"

step "验证完整订单最终状态"
do_req GET "$BASE/api/v1/orders/$ORDER_ID" "" "$BUYER_TOKEN"
assert_code 200 "查询最终订单"
assert_field "order_status" "COMPLETED" "最终状态=COMPLETED"
assert_field "payment_status" "PAID" "支付状态=PAID"

# ════════════════════════════════════════════════════════
banner "场景八: 市场数据查询"
# ════════════════════════════════════════════════════════

step "查询市场参考价格（IT设备）"
do_req GET "$BASE/api/v1/market/prices" "" "$BUYER_TOKEN"
assert_code 200 "查询市场价格"
assert_field "total" "[1-9]" "有价格数据"

step "查询供应商列表"
do_req GET "$BASE/api/v1/suppliers" "" "$BUYER_TOKEN"
assert_code 200 "查询供应商列表"

# ════════════════════════════════════════════════════════
banner "场景九: 异常场景验证"
# ════════════════════════════════════════════════════════

step "查询不存在的订单（404）"
do_req GET "$BASE/api/v1/orders/999999" "" "$BUYER_TOKEN"
assert_code 404 "不存在资源返回 404"

step "创建需求缺少必填字段（400）"
do_req POST "$BASE/api/v1/procurement/demands" '{"category":"IT"}' "$BUYER_TOKEN"
assert_code 400 "缺少必填字段返回 400"

step "错误密码登录（401）"
do_req POST "$BASE/api/v1/auth/login" '{"username":"buyer01","password":"WrongPassword"}'
assert_code 401 "错误密码返回 401"

# ════════════════════════════════════════════════════════
# 汇总
# ════════════════════════════════════════════════════════
TOTAL=$((PASS + FAIL))
echo ""
banner "E2E 测试结果汇总"
echo ""
printf "  %-20s %s\n" "测试步骤总数:" "$STEP"
printf "  %-20s ${GREEN}%s${NC}\n" "断言通过:" "$PASS"
printf "  %-20s ${RED}%s${NC}\n" "断言失败:" "$FAIL"
printf "  %-20s %s\n" "通过率:" "$(python3 -c "print(round($PASS*100/max($TOTAL,1),1))" 2>/dev/null || python -c "print(round($PASS*100/max($TOTAL,1),1))")%"
echo ""
if [ $FAIL -eq 0 ]; then
    echo -e "  ${GREEN}${BOLD}✅ 全链路业务场景验证通过！${NC}"
    echo -e "  ${GREEN}完整B2B采购流程（共 $STEP 步）端到端验证成功${NC}"
    exit 0
else
    echo -e "  ${RED}${BOLD}⚠️  $FAIL 项断言失败，请检查服务状态${NC}"
    exit 1
fi
