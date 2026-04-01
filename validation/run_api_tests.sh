#!/bin/bash
# ILbuy API 功能验收测试脚本 v2（修正JSON格式匹配）
BASE="http://localhost:8080"
PASS=0; FAIL=0; TOTAL=0
START_TIME=$(date +%s%3N)
G='\033[0;32m'; R='\033[0;31m'; Y='\033[1;33m'; B='\033[0;34m'; N='\033[0m'

assert() {
    local id="$1" desc="$2" actual="$3" expect="$4"
    TOTAL=$((TOTAL+1))
    if [ "$actual" = "$expect" ]; then
        echo -e "  ${G}✓${N} [$id] $desc"
        PASS=$((PASS+1))
    else
        echo -e "  ${R}✗${N} [$id] $desc  期望=${expect} 实际=${actual}"
        FAIL=$((FAIL+1))
    fi
}

# 在原始compact JSON中搜索，使用不带空格的模式
assert_json() {
    local id="$1" desc="$2" body="$3" key="$4" val="$5"
    TOTAL=$((TOTAL+1))
    # 支持 "key":"val" 和 "key": "val" 两种格式
    if echo "$body" | grep -qE "\"${key}\":\s*\"?${val}\"?"; then
        echo -e "  ${G}✓${N} [$id] $desc"
        PASS=$((PASS+1))
    else
        echo -e "  ${R}✗${N} [$id] $desc  期望字段 ${key}=${val}"
        echo "      响应: $(echo $body | cut -c1-200)"
        FAIL=$((FAIL+1))
    fi
}

assert_contains() {
    local id="$1" desc="$2" body="$3" kw="$4"
    TOTAL=$((TOTAL+1))
    if echo "$body" | grep -q "$kw"; then
        echo -e "  ${G}✓${N} [$id] $desc"
        PASS=$((PASS+1))
    else
        echo -e "  ${R}✗${N} [$id] $desc  未找到: $kw"
        echo "      响应: $(echo $body | cut -c1-200)"
        FAIL=$((FAIL+1))
    fi
}

assert_time() {
    local id="$1" desc="$2" ms="$3" max="$4"
    TOTAL=$((TOTAL+1))
    if [ "${ms:-9999}" -le "$max" ] 2>/dev/null; then
        echo -e "  ${G}✓${N} [$id] $desc  ${ms}ms ≤ ${max}ms"
        PASS=$((PASS+1))
    else
        echo -e "  ${Y}⚠${N} [$id] $desc  ${ms}ms > ${max}ms (性能偏慢)"
        FAIL=$((FAIL+1))
    fi
}

# 带计时的curl请求，结果存入全局变量
do_request() {
    local method="$1" url="$2" body="$3" token="$4"
    local tmpfile=$(mktemp)
    local args=(-s -o "$tmpfile" -w "%{http_code}|%{time_total}" -X "$method")
    args+=(-H "Content-Type: application/json")
    [ -n "$token" ] && args+=(-H "Authorization: Bearer $token")
    [ -n "$body"  ] && args+=(-d "$body")
    local meta; meta=$(curl "${args[@]}" "$url" 2>/dev/null)
    RESP_BODY=$(cat "$tmpfile"); rm -f "$tmpfile"
    RESP_CODE=$(echo "$meta" | cut -d'|' -f1)
    RESP_MS=$(echo "$meta" | cut -d'|' -f2 | awk '{printf "%d", $1*1000}')
}

echo ""
echo -e "${B}╔══════════════════════════════════════════════════════════╗${N}"
echo -e "${B}║       ILbuy 我来购  API 功能验收测试  v2.0              ║${N}"
echo -e "${B}║       环境: $BASE                    ║${N}"
echo -e "${B}╚══════════════════════════════════════════════════════════╝${N}"
echo ""

# ══════════════════════════════════════
echo -e "${B}【模块0】服务健康检查${N}"
do_request GET "$BASE/actuator/health"
assert "HC-001" "健康检查HTTP 200" "$RESP_CODE" "200"
assert_json "HC-001b" "整体status=UP" "$RESP_BODY" "status" "UP"
assert_time "HC-001c" "响应<500ms" "$RESP_MS" 500
do_request GET "$BASE/actuator/health/liveness"
assert "HC-002" "存活探针HTTP 200" "$RESP_CODE" "200"
do_request GET "$BASE/actuator/health/readiness"
assert "HC-003" "就绪探针HTTP 200" "$RESP_CODE" "200"

# ══════════════════════════════════════
echo ""; echo -e "${B}【模块1】认证接口（Auth）${N}"

# 正常登录
do_request POST "$BASE/api/v1/auth/login" \
  '{"username":"test_buyer_001","password":"Test@123456","captchaToken":"bypass"}'
assert "TC-API-001a" "登录HTTP 200" "$RESP_CODE" "200"
assert_contains "TC-API-001b" "返回accessToken" "$RESP_BODY" '"accessToken"'
assert_json "TC-API-001c" "expiresIn=7200" "$RESP_BODY" "expiresIn" "7200"
assert_json "TC-API-001d" "userType=ENTERPRISE" "$RESP_BODY" "userType" "ENTERPRISE"
assert_time "TC-API-001e" "登录响应<500ms" "$RESP_MS" 500
TOKEN=$(echo "$RESP_BODY" | python3 -c "import sys,json;d=json.load(sys.stdin);print(d['data']['accessToken'])" 2>/dev/null | tr -d '\r')
RT=$(echo "$RESP_BODY" | python3 -c "import sys,json;d=json.load(sys.stdin);print(d['data']['refreshToken'])" 2>/dev/null | tr -d '\r')

# 密码错误
do_request POST "$BASE/api/v1/auth/login" \
  '{"username":"test_buyer_001","password":"WrongPassword123"}'
assert "TC-API-002a" "密码错误HTTP 401" "$RESP_CODE" "401"
assert_json "TC-API-002b" "错误码10001" "$RESP_BODY" "code" "10001"

# Token刷新
do_request POST "$BASE/api/v1/auth/refresh" "{\"refreshToken\":\"$RT\"}"
assert "TC-API-003a" "Token刷新HTTP 200" "$RESP_CODE" "200"
assert_contains "TC-API-003b" "返回新accessToken" "$RESP_BODY" '"accessToken"'

# 未认证访问
do_request GET "$BASE/api/v1/procurement/demands"
assert "TC-API-070a" "未认证返回HTTP 401" "$RESP_CODE" "401"
assert_json "TC-API-070b" "错误码10002" "$RESP_BODY" "code" "10002"

# ══════════════════════════════════════
echo ""; echo -e "${B}【模块2】采购需求（Procurement）${N}"

# 创建B2B需求
do_request POST "$BASE/api/v1/procurement/demands" \
  '{"procurementType":"B2B","categoryId":1,"productName":"A4打印纸","productSpec":"70g 500张/包","quantity":100,"unit":"箱","budgetAmount":5000.00,"currency":"CNY","deliveryDeadline":"2024-12-31","deliveryAddress":"北京市朝阳区建国路88号","contactName":"张采购","contactPhone":"13800138001","requireTaxInvoice":true,"invoiceType":"SPECIAL_VAT","remark":"品牌不限"}' \
  "$TOKEN"
assert "TC-API-010a" "创建B2B需求HTTP 201" "$RESP_CODE" "201"
assert_contains "TC-API-010b" "返回demandId" "$RESP_BODY" '"demandId"'
assert_contains "TC-API-010c" "orderNo格式PRO" "$RESP_BODY" '"orderNo":"PRO'
assert_json "TC-API-010d" "状态MATCHING" "$RESP_BODY" "status" "MATCHING"
assert_time "TC-API-010e" "创建响应<1000ms" "$RESP_MS" 1000
DEMAND_ID=$(echo "$RESP_BODY" | python3 -c "import sys,json;d=json.load(sys.stdin);print(d['data']['demandId'])" 2>/dev/null | tr -d '\r')

# B2C未定品牌
do_request POST "$BASE/api/v1/procurement/demands" \
  '{"procurementType":"B2C_UNDECIDED","productName":"办公桌椅套装","quantity":20,"unit":"套","budgetAmount":40000.00,"deliveryAddress":"北京市海淀区"}' \
  "$TOKEN"
assert "TC-API-010f" "B2C未定品牌需求HTTP 201" "$RESP_CODE" "201"

# 查询详情
do_request GET "$BASE/api/v1/procurement/demands/$DEMAND_ID" "" "$TOKEN"
assert "TC-API-011a" "查询需求详情HTTP 200" "$RESP_CODE" "200"
assert_contains "TC-API-011b" "包含matchedSuppliers" "$RESP_BODY" '"matchedSuppliers"'

# 分页列表
do_request GET "$BASE/api/v1/procurement/demands?page=0&size=10" "" "$TOKEN"
assert "TC-API-012a" "分页列表HTTP 200" "$RESP_CODE" "200"
assert_contains "TC-API-012b" "包含totalElements" "$RESP_BODY" '"totalElements"'
assert_contains "TC-API-012c" "包含content数组" "$RESP_BODY" '"content"'

# 参数校验（缺字段）
do_request POST "$BASE/api/v1/procurement/demands" \
  '{"procurementType":"B2B","quantity":-1,"budgetAmount":0}' \
  "$TOKEN"
assert "TC-API-071a" "参数校验HTTP 400" "$RESP_CODE" "400"
assert_json "TC-API-071b" "错误码10003" "$RESP_BODY" "code" "10003"
assert_contains "TC-API-071c" "返回errors数组" "$RESP_BODY" '"errors"'

# ══════════════════════════════════════
echo ""; echo -e "${B}【模块3】AI匹配（Matching）${N}"

do_request POST "$BASE/api/v1/matching/trigger" \
  "{\"demandId\":$DEMAND_ID,\"matchMode\":\"AUTO\",\"maxSuppliers\":5}" \
  "$TOKEN"
assert "TC-API-020a" "触发AI匹配HTTP 200" "$RESP_CODE" "200"
assert_contains "TC-API-020b" "返回matchTaskId" "$RESP_BODY" '"matchTaskId"'
assert_json "TC-API-020c" "状态PROCESSING" "$RESP_BODY" "status" "PROCESSING"
TASK_ID=$(echo "$RESP_BODY" | python3 -c "import sys,json;d=json.load(sys.stdin);print(d['data']['matchTaskId'])" 2>/dev/null | tr -d '\r')

sleep 1
do_request GET "$BASE/api/v1/matching/result/$TASK_ID" "" "$TOKEN"
TASK_ID=$(echo "$TASK_ID" | tr -d '[:space:]')
assert "TC-API-021a" "查询匹配结果HTTP 200" "$RESP_CODE" "200"
assert_json "TC-API-021b" "结果状态COMPLETED" "$RESP_BODY" "status" "COMPLETED"
assert_contains "TC-API-021c" "包含matchedSuppliers" "$RESP_BODY" '"matchedSuppliers"'
assert_contains "TC-API-021d" "包含AI分析" "$RESP_BODY" '"aiAnalysis"'

# ══════════════════════════════════════
echo ""; echo -e "${B}【模块4】询价报价（Inquiry）${N}"

do_request POST "$BASE/api/v1/inquiry" \
  "{\"demandId\":$DEMAND_ID,\"supplierIds\":[5001,5002],\"inquiryDeadline\":\"2099-12-31T18:00:00\",\"message\":\"请按需求规格报价\"}" \
  "$TOKEN"
assert "TC-API-030a" "发起询价HTTP 201" "$RESP_CODE" "201"
assert_contains "TC-API-030b" "返回inquiryId" "$RESP_BODY" '"inquiryId"'
assert_json "TC-API-030c" "状态SENT" "$RESP_BODY" "status" "SENT"
assert_json "TC-API-030d" "supplierCount=2" "$RESP_BODY" "supplierCount" "2"
INQUIRY_ID=$(echo "$RESP_BODY" | python3 -c "import sys,json;d=json.load(sys.stdin);print(d['data']['inquiryId'])" 2>/dev/null | tr -d '\r')

# 供应商登录并提交报价
do_request POST "$BASE/api/v1/auth/login" \
  '{"username":"test_supplier_001","password":"Test@123456","captchaToken":"bypass"}'
SUP_TOKEN=$(echo "$RESP_BODY" | python3 -c "import sys,json;d=json.load(sys.stdin);print(d['data']['accessToken'])" 2>/dev/null | tr -d '\r')

do_request POST "$BASE/api/v1/inquiry/$INQUIRY_ID/quotes" \
  '{"unitPrice":46.50,"currency":"CNY","totalAmount":4650.00,"taxRate":0.13,"deliveryDays":2,"validDays":7,"remark":"现货供应，当日可发货"}' \
  "$SUP_TOKEN"
assert "TC-API-031a" "供应商报价HTTP 201" "$RESP_CODE" "201"
assert_contains "TC-API-031b" "返回quoteId" "$RESP_BODY" '"quoteId"'
assert_json "TC-API-031c" "状态SUBMITTED" "$RESP_BODY" "status" "SUBMITTED"
QUOTE_ID=$(echo "$RESP_BODY" | python3 -c "import sys,json;d=json.load(sys.stdin);print(d['data']['quoteId'])" 2>/dev/null | tr -d '\r')

do_request PUT "$BASE/api/v1/inquiry/$INQUIRY_ID/quotes/$QUOTE_ID/accept" "" "$TOKEN"
assert "TC-API-032a" "接受报价HTTP 200" "$RESP_CODE" "200"
assert_contains "TC-API-032b" "返回orderId" "$RESP_BODY" '"orderId"'
assert_json "TC-API-032c" "订单状态PENDING_PAYMENT" "$RESP_BODY" "orderStatus" "PENDING_PAYMENT"
ORDER_ID=$(echo "$RESP_BODY" | python3 -c "import sys,json;d=json.load(sys.stdin);print(d['data']['orderId'])" 2>/dev/null | tr -d '\r')

# ══════════════════════════════════════
echo ""; echo -e "${B}【模块5】订单（Order）${N}"

do_request GET "$BASE/api/v1/orders/$ORDER_ID" "" "$TOKEN"
assert "TC-API-040a" "查询订单详情HTTP 200" "$RESP_CODE" "200"
assert_contains "TC-API-040b" "包含orderId" "$RESP_BODY" '"orderId"'
assert_contains "TC-API-040c" "包含items数组" "$RESP_BODY" '"items"'
assert_contains "TC-API-040d" "包含buyerInfo" "$RESP_BODY" '"buyerInfo"'

do_request PUT "$BASE/api/v1/orders/$ORDER_ID/confirm-receipt" \
  '{"receiptTime":"2024-03-25T10:00:00","quantity":100,"qualityOk":true,"remark":"货物完好"}' \
  "$TOKEN"
assert "TC-API-041a" "确认收货HTTP 200" "$RESP_CODE" "200"
assert_json "TC-API-041b" "订单状态COMPLETED" "$RESP_BODY" "orderStatus" "COMPLETED"

# ══════════════════════════════════════
echo ""; echo -e "${B}【模块6】供应商（Supplier）${N}"

UNIQ=$(date +%s)
do_request POST "$BASE/api/v1/suppliers/register" \
  "{\"companyName\":\"API-Test-Supplier-${UNIQ}\",\"creditCode\":\"9111TEST${UNIQ}\",\"contactName\":\"TestContact\",\"contactPhone\":\"13900139001\",\"contactEmail\":\"supply${UNIQ}@valtest.com\"}"
assert "TC-API-050a" "供应商申请HTTP 201" "$RESP_CODE" "201"
assert_contains "TC-API-050b" "返回supplierId" "$RESP_BODY" '"supplierId"'
assert_json "TC-API-050c" "状态REVIEWING" "$RESP_BODY" "status" "REVIEWING"

do_request POST "$BASE/api/v1/suppliers/register" \
  "{\"companyName\":\"DuplicateTest\",\"creditCode\":\"9111TEST${UNIQ}\",\"contactName\":\"Dup\",\"contactPhone\":\"13900000000\"}"
assert "TC-API-050d" "重复申请HTTP 409" "$RESP_CODE" "409"

# ══════════════════════════════════════
echo ""; echo -e "${B}【模块7】市场数据（Data）${N}"

do_request GET "$BASE/api/v1/data/market-price?keyword=A4%E6%89%93%E5%8D%B0%E7%BA%B8" "" "$TOKEN"
assert "TC-API-060a" "市场价格查询HTTP 200" "$RESP_CODE" "200"
assert_contains "TC-API-060b" "包含priceRange" "$RESP_BODY" '"priceRange"'
assert_contains "TC-API-060c" "包含sources数组" "$RESP_BODY" '"sources"'
assert_json "TC-API-060d" "trend字段STABLE" "$RESP_BODY" "trend" "STABLE"
assert_time "TC-API-060e" "价格查询响应<300ms" "$RESP_MS" 300

do_request PUT "$BASE/api/v1/procurement/demands/$DEMAND_ID/cancel" \
  '{"reason":"验收测试完成-取消需求"}' \
  "$TOKEN"
assert "TC-API-013a" "取消需求HTTP 200" "$RESP_CODE" "200"
assert_json "TC-API-013b" "状态CANCELLED" "$RESP_BODY" "status" "CANCELLED"

# ══════════════════════════════════════
END_TIME=$(date +%s%3N)
ELAPSED=$((END_TIME-START_TIME))
RATE=$(awk "BEGIN{printf \"%.1f\", $PASS/$TOTAL*100}")

echo ""
echo -e "${B}══════════════════════════════════════════════════════════${N}"
echo -e "  API功能测试结果"
echo -e "${B}══════════════════════════════════════════════════════════${N}"
printf "  总用例: %-5d  通过: ${G}%-5d${N}  失败: ${R}%-5d${N}\n" $TOTAL $PASS $FAIL
echo -e "  通过率: ${RATE}%   耗时: ${ELAPSED}ms"
[ "$FAIL" -eq 0 ] && echo -e "  ${G}✓ 全部通过！${N}" || echo -e "  ${R}✗ 存在${FAIL}个失败用例${N}"
echo -e "${B}══════════════════════════════════════════════════════════${N}"

cat > /tmp/api_test_result.json << EOF
{"module":"API功能测试","total":$TOTAL,"pass":$PASS,"fail":$FAIL,"passRate":"$RATE%","durationMs":$ELAPSED,"timestamp":"$(date '+%Y-%m-%dT%H:%M:%S')"}
EOF
exit $FAIL
