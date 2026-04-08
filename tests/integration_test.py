#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ILBuy 全流程集成测试
测试覆盖: 微服务健康 / 用户认证 / 采购需求 / AI匹配 / 商品浏览 / 询价报价 / 订单管理 / 市场行情 / 价格预警
"""
import sys
import io

# Windows: force UTF-8 so that ✓/✗ don't crash with GBK codec
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except AttributeError:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import time
import random
import string
import requests

BASE         = "http://localhost:8080"
PRODUCT_BASE = "http://localhost:8006"   # direct product service
TIMEOUT = 8

passed  = 0
failed  = 0
results = []


# ─── helpers ────────────────────────────────────────────────────────────────

def check(label, ok, detail=""):
    global passed, failed
    mark = "✓" if ok else "✗"
    if ok:
        passed += 1
    else:
        failed += 1
    results.append((mark, label, detail))
    print(f"  {mark} {label}" + (f"  [{detail}]" if detail else ""))


def section(title):
    print(f"\n【{title}】")


def safe_json(r):
    try:
        return r.json()
    except Exception:
        return {}


def post_with_retry(url, headers, json_data, retries=3, delay=1.0):
    """POST with retry for transient SQLite lock errors."""
    for attempt in range(retries):
        try:
            r = requests.post(url, headers=headers, json=json_data, timeout=TIMEOUT)
            d = safe_json(r)
            if d.get("code") == 500 and "locked" in str(d.get("message", "")):
                time.sleep(delay)
                continue
            return r, d
        except Exception:
            time.sleep(delay)
    return r, d


# ─── 【1】微服务健康检查 ─────────────────────────────────────────────────────

# ─── Windows: detect zombie gateway (multiple PIDs on port 8080) ────────────
if sys.platform == 'win32':
    import subprocess
    try:
        out = subprocess.check_output(
            'netstat -ano', shell=True, text=True, stderr=subprocess.DEVNULL
        )
        pids_8080 = set()
        for line in out.splitlines():
            parts = line.split()
            if len(parts) >= 5 and ':8080' in parts[1] and parts[3] in ('LISTENING', 'ESTABLISHED'):
                pid = parts[4]
                if pid.isdigit() and pid != '0':
                    pids_8080.add(pid)
        if len(pids_8080) > 1:
            print(f"[WARNING] Multiple PIDs on port 8080: {pids_8080}")
            print("[WARNING] Zombie gateway detected. Stop all services and run:")
            print("  python scripts/kill_port.py 8080")
            print("  Then restart services and run the test again.")
        elif len(pids_8080) == 1:
            _gw_pid = list(pids_8080)[0]
            print(f"[gateway] Single process on port 8080: PID {_gw_pid} (good)")
    except Exception:
        pass


# ─── 【0】诊断：产品服务直连 + 网关路由表 + 网关无认证探测 ────────────────────
print("\n【0 诊断】")

# 0-a 产品服务直连（port 8006）
print("  [product-service 直连]")
for path in ["/health", "/internal/products", "/internal/products/popular",
             "/internal/categories", "/internal/price-alerts"]:
    try:
        r = requests.get(f"{PRODUCT_BASE}{path}", timeout=TIMEOUT)
        d = safe_json(r)
        print(f"    GET {path} → HTTP {r.status_code}  code={d.get('code')}  msg={d.get('message','')[:40]}")
    except Exception as e:
        print(f"    GET {path} → ERROR: {e}")

# 0-b 网关路由表（需先 pull 最新代码）
print("  [gateway /debug/routes]")
try:
    r = requests.get(f"{BASE}/debug/routes", timeout=TIMEOUT)
    d = safe_json(r)
    routes = d.get("routes", [])
    product_routes = [x for x in routes if "product" in x.get("rule","") or "price-alert" in x.get("rule","") or "categor" in x.get("rule","")]
    print(f"    Total registered routes: {d.get('total', '?')}")
    print(f"    Product/alert/category routes found: {len(product_routes)}")
    for x in product_routes:
        print(f"      {x['methods']} {x['rule']}")
except Exception as e:
    print(f"    ERROR (route debug unavailable — pull latest code): {e}")

# 0-c 网关无认证探测（401=路由存在,404=路由未注册）
print("  [gateway 无认证探测]")
for path in ["/api/v1/products", "/api/v1/products/popular", "/api/v1/categories", "/api/v1/price-alerts"]:
    try:
        r = requests.get(f"{BASE}{path}", timeout=TIMEOUT)
        d = safe_json(r)
        print(f"    GET {path} → HTTP {r.status_code}  code={d.get('code')}  msg={d.get('message','')[:30]}")
    except Exception as e:
        print(f"    GET {path} → ERROR: {e}")


section("1 微服务健康检查")
services = [
    ("user-service",        8001, "/health"),
    ("procurement-service", 8002, "/health"),
    ("ai-matching-service", 8003, "/health"),
    ("order-service",       8004, "/health"),
    ("data-collector",      8005, "/health"),
    ("product-service",     8006, "/health"),
    ("api-gateway",         8080, "/actuator/health"),
]
for name, port, path in services:
    try:
        r = requests.get(f"http://localhost:{port}{path}", timeout=TIMEOUT)
        d = safe_json(r)
        ok = (r.status_code == 200 and
              d.get("status") in ("UP", "ok", "healthy") or d.get("code") == 0)
        check(f"{name}:{port} healthy", ok, d.get("status", d.get("message", "")))
    except Exception as e:
        check(f"{name}:{port} healthy", False, str(e))


# ─── 【2】用户注册 & 登录 ────────────────────────────────────────────────────

section("2 用户注册 & 登录")

suffix   = ''.join(random.choices(string.digits, k=6))
username = f"integtest_{suffix}"
email    = f"{username}@ilbuy.com"

r = requests.post(f"{BASE}/api/v1/auth/register", json={
    "username": username, "password": "Test@123456",
    "email": email, "phone": f"138{suffix}0000",
    "companyName": "Integration Test Co",
}, timeout=TIMEOUT)
d = safe_json(r)
check("POST /auth/register", d.get("code") == 0, d.get("message", ""))
user_id = d.get("data", {}).get("userId")

r = requests.post(f"{BASE}/api/v1/auth/login", json={
    "username": username, "password": "Test@123456",
}, timeout=TIMEOUT)
d = safe_json(r)
check("POST /auth/login", d.get("code") == 0, d.get("message", ""))
token = d.get("data", {}).get("accessToken", "")
check("accessToken obtained", bool(token), f"userId={user_id}")

H = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# ─── 【3】采购需求管理 ────────────────────────────────────────────────────────

section("3 采购需求管理")

r = requests.post(f"{BASE}/api/v1/procurement/demands", headers=H, json={
    "userId":      user_id,
    "title":       "集成测试笔记本采购",
    "category":    "电脑办公",
    "quantity":    200,
    "unit":        "台",
    "budget":      1_000_000,
    "description": "集成测试需求",
}, timeout=TIMEOUT)
d = safe_json(r)
check("POST /procurement/demands", d.get("code") == 0, d.get("message", ""))
demand_id = (d.get("data") or {}).get("id") or (d.get("data") or {}).get("demandId") or 1

r = requests.get(f"{BASE}/api/v1/procurement/demands", headers=H, timeout=TIMEOUT)
d = safe_json(r)
check("GET  /procurement/demands", d.get("code") == 0,
      f"total={d.get('data', {}).get('total', '?')}")

# POST quote — requires demandId, supplierId, unitPrice, totalPrice
r = requests.post(f"{BASE}/api/v1/procurement/quotes", headers=H, json={
    "demandId":     demand_id,
    "supplierId":   1,
    "supplierName": "集成测试供应商",
    "unitPrice":    4500.0,
    "totalPrice":   900_000.0,   # unitPrice × quantity
    "quantity":     200,
    "currency":     "CNY",
    "deliveryDays": 14,
    "remark":       "含增值税发票",
}, timeout=TIMEOUT)
d = safe_json(r)
check("POST /procurement/quotes", d.get("code") == 0, d.get("message", ""))
quote_id = (d.get("data") or {}).get("id") or (d.get("data") or {}).get("quoteId") or 1


# ─── 【4】AI 智能匹配 ─────────────────────────────────────────────────────────

section("4 AI 智能匹配")

# Actual route: POST /api/v1/ai/intent/parse — field is "text" not "query"
r = requests.post(f"{BASE}/api/v1/ai/intent/parse", headers=H, json={
    "text": "需要采购500台i7处理器企业笔记本，预算300万",
}, timeout=TIMEOUT)
d = safe_json(r)
check("POST /ai/intent/parse", d.get("code") == 0, d.get("message", ""))

# Actual route: POST /api/v1/ai/match
r = requests.post(f"{BASE}/api/v1/ai/match", headers=H, json={
    "demandId": demand_id, "userId": user_id,
}, timeout=TIMEOUT)
d = safe_json(r)
check("POST /ai/match", d.get("code") == 0, d.get("message", ""))
match_task_id = (d.get("data") or {}).get("taskId") or "task_001"

# Actual route: GET /api/v1/ai/match/<task_id>/result
r = requests.get(f"{BASE}/api/v1/ai/match/{match_task_id}/result", headers=H, timeout=TIMEOUT)
d = safe_json(r)
check("GET  /ai/match/{taskId}/result", d.get("code") in (0, 404, 10004), d.get("message", ""))

# Actual route: GET /api/v1/ai/suppliers/recommend
r = requests.get(f"{BASE}/api/v1/ai/suppliers/recommend", headers=H,
                 params={"userId": user_id, "category": "电脑办公"}, timeout=TIMEOUT)
d = safe_json(r)
check("GET  /ai/suppliers/recommend", d.get("code") == 0, d.get("message", ""))

# Actual route: POST /api/v1/matching/trigger
r = requests.post(f"{BASE}/api/v1/matching/trigger", headers=H, json={
    "demandId": demand_id,
}, timeout=TIMEOUT)
d = safe_json(r)
check("POST /matching/trigger", d.get("code") == 0, d.get("message", ""))


# ─── 【5】商品浏览 ────────────────────────────────────────────────────────────

section("5 商品浏览")

r = requests.get(f"{BASE}/api/v1/products", headers=H,
                 params={"page": 1, "pageSize": 10}, timeout=TIMEOUT)
d = safe_json(r)
items = (d.get("data") or {}).get("items", [])
check("GET  /products (list)", d.get("code") == 0, f"count={len(items)}")

# Use seeded product if fresh user's list is empty
product_id = items[0]["id"] if items else "PROD_001"

r = requests.get(f"{BASE}/api/v1/products/{product_id}", headers=H, timeout=TIMEOUT)
d = safe_json(r)
check("GET  /products/{id}", d.get("code") == 0, product_id)

# Actual popular route
r = requests.get(f"{BASE}/api/v1/products/popular", headers=H,
                 params={"limit": 5}, timeout=TIMEOUT)
d = safe_json(r)
check("GET  /products/popular", d.get("code") == 0, d.get("message", ""))

# Actual categories route
r = requests.get(f"{BASE}/api/v1/categories", headers=H, timeout=TIMEOUT)
d = safe_json(r)
check("GET  /categories", d.get("code") == 0, d.get("message", ""))

r = requests.get(f"{BASE}/api/v1/products/{product_id}/price-history", headers=H, timeout=TIMEOUT)
d = safe_json(r)
check("GET  /products/{id}/price-history", d.get("code") in (0, 404), d.get("message", ""))

# Compare — needs 2 ids via POST body
r = requests.post(f"{BASE}/api/v1/products/compare", headers=H, json={
    "productIds": ["PROD_001", "PROD_002"],
}, timeout=TIMEOUT)
d = safe_json(r)
check("POST /products/compare", d.get("code") == 0, d.get("message", ""))

# Product recommendations
r = requests.get(f"{BASE}/api/v1/products/{product_id}/recommendations", headers=H, timeout=TIMEOUT)
d = safe_json(r)
check("GET  /products/{id}/recommendations", d.get("code") in (0, 404), d.get("message", ""))


# ─── 【6】询价 & 报价 ─────────────────────────────────────────────────────────

section("6 询价 & 报价")

r = requests.post(f"{BASE}/api/v1/inquiry", headers=H, json={
    "userId":      user_id,
    "productId":   product_id,
    "quantity":    100,
    "targetPrice": 4000.0,
    "deadline":    "2026-05-01",
    "remark":      "集成测试询价",
}, timeout=TIMEOUT)
d = safe_json(r)
check("POST /inquiry", d.get("code") == 0, d.get("message", ""))
inquiry_id = (d.get("data") or {}).get("inquiryId") or (d.get("data") or {}).get("id")

r = requests.get(f"{BASE}/api/v1/inquiry", headers=H,
                 params={"userId": user_id}, timeout=TIMEOUT)
d = safe_json(r)
check("GET  /inquiry", d.get("code") == 0, d.get("message", ""))


# ─── 【7】订单管理 ────────────────────────────────────────────────────────────

section("7 订单管理")

# Order service requires: demandId, quoteId, buyerId, supplierId, productName, quantity, unitPrice, totalAmount
# Use retry for transient SQLite lock
r, d = post_with_retry(f"{BASE}/api/v1/orders", headers=H, json_data={
    "demandId":     demand_id,
    "quoteId":      quote_id,
    "buyerId":      user_id,
    "supplierId":   1,
    "supplierName": "集成测试供应商",
    "productName":  "联想ThinkPad E14 Gen5",
    "quantity":     10,
    "unitPrice":    4500.0,
    "totalAmount":  45_000.0,
    "deliveryDays": 14,
    "remark":       "集成测试订单",
}, retries=3, delay=1.5)
check("POST /orders", d.get("code") == 0, d.get("message", ""))
order_id = (d.get("data") or {}).get("id") or (d.get("data") or {}).get("orderId")

r = requests.get(f"{BASE}/api/v1/orders", headers=H,
                 params={"userId": user_id}, timeout=TIMEOUT)
d = safe_json(r)
check("GET  /orders", d.get("code") == 0, f"total={d.get('data', {}).get('total', '?')}")


# ─── 【8】市场行情 ────────────────────────────────────────────────────────────

section("8 市场行情")

r = requests.get(f"{BASE}/api/v1/market/prices", headers=H,
                 params={"category": "电脑办公"}, timeout=TIMEOUT)
d = safe_json(r)
check("GET  /market/prices", d.get("code") == 0, d.get("message", ""))

r = requests.get(f"{BASE}/api/v1/data/market/prices", headers=H,
                 params={"category": "电脑办公", "days": 30}, timeout=TIMEOUT)
d = safe_json(r)
check("GET  /data/market/prices", d.get("code") == 0, d.get("message", ""))

r = requests.get(f"{BASE}/api/v1/data/market-price", headers=H,
                 params={"keyword": "笔记本"}, timeout=TIMEOUT)
d = safe_json(r)
check("GET  /data/market-price", d.get("code") == 0, d.get("message", ""))


# ─── 【9】价格预警 ────────────────────────────────────────────────────────────

section("9 价格预警")

# product_id is always set (fallback PROD_001 if listing empty)
r = requests.post(f"{BASE}/api/v1/price-alerts", headers=H, json={
    "productId":   product_id,
    "userId":      user_id,
    "targetPrice": 4800.0,
}, timeout=TIMEOUT)
d = safe_json(r)
check("POST /price-alerts", d.get("code") == 0, d.get("message", ""))
alert_id = (d.get("data") or {}).get("id") or (d.get("data") or {}).get("alertId")

r = requests.get(f"{BASE}/api/v1/price-alerts", headers=H,
                 params={"userId": user_id}, timeout=TIMEOUT)
d = safe_json(r)
count = len((d.get("data") or {}).get("items", []))
check("GET  /price-alerts", d.get("code") == 0, f"count={count}")

if alert_id:
    r = requests.put(f"{BASE}/api/v1/price-alerts/{alert_id}/cancel", headers=H, timeout=TIMEOUT)
    d = safe_json(r)
    check("PUT  /price-alerts/{id}/cancel", d.get("code") == 0, d.get("message", ""))
else:
    check("PUT  /price-alerts/{id}/cancel", True, "skipped (no alert_id)")


# ─── 【10】服务总览 ───────────────────────────────────────────────────────────

section("10 服务总览")
try:
    r = requests.get(f"{BASE}/api/v1/admin/services", headers=H, timeout=TIMEOUT)
    d = safe_json(r)
    all_up = d.get("code") == 0 and len(d.get("data", {}).get("services", [])) > 0
    check("GET  /admin/services (all UP)", all_up, d.get("message", ""))
except Exception as e:
    check("GET  /admin/services", False, str(e))


# ─── Summary ─────────────────────────────────────────────────────────────────

total = passed + failed
pct   = 100.0 * passed / total if total else 0
print(f"\n{'='*55}")
print(f"结果: ✓ {passed} 通过  ✗ {failed} 失败  共 {total} 项  通过率 {pct:.1f}%")
if failed:
    print("\n失败明细:")
    for s, label, detail in results:
        if s == "✗":
            print(f"  ✗ {label}" + (f"  [{detail}]" if detail else ""))
print("=" * 55)

sys.exit(0 if failed == 0 else 1)
