"""
ILbuy 我来购采购平台 - 验收测试 Mock API
功能：实现核心REST接口 + 真实JWT认证 + 限流（100req/min）+ MySQL/Redis持久化
"""
import os, json, time, hmac, hashlib, base64, re, random, string
from datetime import datetime, timedelta
from functools import wraps

import pymysql, redis as redislib
from flask import Flask, request, jsonify, g
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# ===== 初始化 =====
app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False

# Redis连接（用于限流和缓存）
REDIS_HOST     = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT     = int(os.getenv('REDIS_PORT', 6379))
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', '')

redis_client = redislib.Redis(
    host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASSWORD,
    decode_responses=True, socket_connect_timeout=3
)

# 限流器：默认 100次/分钟，使用 Redis 存储
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["100 per minute"],
    storage_uri=f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/1",
    headers_enabled=True   # 在响应头暴露 X-RateLimit-* 信息
)

JWT_SECRET = os.getenv('JWT_SECRET', 'ilbuy-secret-key')

# ===== 数据库工具 =====
def get_db():
    if 'db' not in g:
        g.db = pymysql.connect(
            host=os.getenv('MYSQL_HOST', 'localhost'),
            port=int(os.getenv('MYSQL_PORT', 3306)),
            user=os.getenv('MYSQL_USER', 'ilbuy'),
            password=os.getenv('MYSQL_PASSWORD', ''),
            database=os.getenv('MYSQL_DB', 'ilbuy_test'),
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
    return g.db

@app.teardown_appcontext
def close_db(e=None):
    db = g.pop('db', None)
    if db:
        db.close()

def query_one(sql, args=()):
    db = get_db()
    with db.cursor() as cur:
        cur.execute(sql, args)
        return cur.fetchone()

def query_all(sql, args=()):
    db = get_db()
    with db.cursor() as cur:
        cur.execute(sql, args)
        return cur.fetchall()

def execute(sql, args=()):
    db = get_db()
    with db.cursor() as cur:
        cur.execute(sql, args)
        db.commit()
        return cur.lastrowid

# ===== JWT工具 =====
def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode()

def _sign(payload: dict) -> str:
    header  = _b64(json.dumps({"alg":"HS256","typ":"JWT"}).encode())
    body    = _b64(json.dumps(payload).encode())
    sig     = _b64(hmac.new(JWT_SECRET.encode(), f"{header}.{body}".encode(), hashlib.sha256).digest())
    return f"{header}.{body}.{sig}"

def _verify(token: str):
    try:
        h, b, s = token.split('.')
        expected = _b64(hmac.new(JWT_SECRET.encode(), f"{h}.{b}".encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(s, expected):
            return None
        pad = 4 - len(b) % 4
        payload = json.loads(base64.urlsafe_b64decode(b + '=' * pad))
        if payload.get('exp', 0) < time.time():
            return None
        return payload
    except Exception:
        return None

def require_auth(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        auth = request.headers.get('Authorization', '')
        if not auth.startswith('Bearer '):
            return jsonify({"code": 10002, "message": "未认证，请先登录", "data": None}), 401
        payload = _verify(auth[7:])
        if not payload:
            return jsonify({"code": 10002, "message": "Token无效或已过期", "data": None}), 401
        g.user_id = payload['userId']
        g.username = payload['username']
        g.user_type = payload.get('userType', 'ENTERPRISE')
        return f(*args, **kwargs)
    return wrapper

def success(data, status=200):
    return jsonify({"code": 0, "message": "success", "data": data}), status

def error(code, message, status=400):
    return jsonify({"code": code, "message": message, "data": None}), status

def gen_order_no(prefix='PRO'):
    return prefix + datetime.now().strftime('%Y%m%d%H%M%S') + ''.join(random.choices(string.digits, k=4))

# ===== 限流错误处理 =====
@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({
        "code": 42900,
        "message": f"请求过于频繁，已触发限流。限制：{e.description}。请稍后重试。",
        "data": None
    }), 429

# ===== 健康检查 =====
@app.route('/actuator/health', methods=['GET'])
@limiter.exempt
def health():
    checks = {"status": "UP", "components": {}}
    # MySQL检查
    try:
        query_one("SELECT 1")
        checks["components"]["mysql"] = {"status": "UP"}
    except Exception as ex:
        checks["components"]["mysql"] = {"status": "DOWN", "details": str(ex)}
        checks["status"] = "DOWN"
    # Redis检查
    try:
        redis_client.ping()
        checks["components"]["redis"] = {"status": "UP"}
    except Exception as ex:
        checks["components"]["redis"] = {"status": "DOWN", "details": str(ex)}
        checks["status"] = "DOWN"
    return jsonify(checks), 200 if checks["status"] == "UP" else 503

@app.route('/actuator/health/liveness',  methods=['GET'])
@limiter.exempt
def liveness():
    return jsonify({"status": "UP"}), 200

@app.route('/actuator/health/readiness', methods=['GET'])
@limiter.exempt
def readiness():
    return jsonify({"status": "UP"}), 200

@app.route('/actuator/info', methods=['GET'])
@limiter.exempt
def info():
    return jsonify({
        "app": {"name": "ilbuy-mock-api", "version": "1.0.0"},
        "build": {"time": "2024-03-22T00:00:00Z"}
    })

# ===== 认证模块 =====
@app.route('/api/v1/auth/login', methods=['POST'])
@limiter.limit("200 per minute")   # 登录接口专属限制
def login():
    body = request.get_json(silent=True) or {}
    username = body.get('username', '').strip()
    password = body.get('password', '').strip()
    if not username or not password:
        return error(10003, "用户名和密码不能为空")
    pw_hash = hashlib.sha256(password.encode()).hexdigest()
    user = query_one(
        "SELECT id, username, user_type, status FROM t_user WHERE username=%s AND password=%s",
        (username, pw_hash)
    )
    if not user:
        return error(10001, "用户名或密码错误", 401)
    if user['status'] != 'ACTIVE':
        return error(10004, "账号已被禁用", 401)
    now = time.time()
    access_payload  = {"userId": user['id'], "username": user['username'],
                       "userType": user['user_type'], "iat": now, "exp": now + 7200}
    refresh_payload = {"userId": user['id'], "iat": now, "exp": now + 86400 * 7, "type": "refresh"}
    # 写入Redis（用于Token撤销）
    try:
        redis_client.setex(f"token:user:{user['id']}", 7200, _sign(access_payload))
    except Exception:
        pass
    return success({
        "accessToken": _sign(access_payload),
        "refreshToken": _sign(refresh_payload),
        "tokenType": "Bearer",
        "expiresIn": 7200,
        "userId": user['id'],
        "username": user['username'],
        "userType": user['user_type'],
        "roles": [f"ROLE_{user['user_type']}"]
    })

@app.route('/api/v1/auth/refresh', methods=['POST'])
@limiter.limit("50 per minute")
def refresh_token():
    body = request.get_json(silent=True) or {}
    token = body.get('refreshToken', '')
    payload = _verify(token)
    if not payload or payload.get('type') != 'refresh':
        return error(10005, "Refresh Token无效或已过期", 401)
    user = query_one("SELECT id, username, user_type FROM t_user WHERE id=%s", (payload['userId'],))
    if not user:
        return error(10006, "用户不存在", 401)
    now = time.time()
    new_payload = {"userId": user['id'], "username": user['username'],
                   "userType": user['user_type'], "iat": now, "exp": now + 7200}
    return success({"accessToken": _sign(new_payload), "expiresIn": 7200})

@app.route('/api/v1/auth/logout', methods=['POST'])
@require_auth
def logout():
    try:
        redis_client.delete(f"token:user:{g.user_id}")
    except Exception:
        pass
    return success({"message": "已退出登录"})

# ===== 采购需求模块（核心限流接口）=====
@app.route('/api/v1/procurement/demands', methods=['POST'])
@require_auth
@limiter.limit("100 per minute")   # C端核心接口，100次/分钟
def create_demand():
    body = request.get_json(silent=True) or {}
    # 参数校验
    errors = []
    if not body.get('productName'):
        errors.append({"field": "productName", "message": "商品名称不能为空"})
    if not body.get('procurementType'):
        errors.append({"field": "procurementType", "message": "采购类型不能为空"})
    qty = body.get('quantity', 0)
    if not isinstance(qty, (int, float)) or qty <= 0:
        errors.append({"field": "quantity", "message": "数量必须大于0"})
    budget = body.get('budgetAmount', 0)
    if not isinstance(budget, (int, float)) or budget <= 0:
        errors.append({"field": "budgetAmount", "message": "预算金额必须大于0"})
    if errors:
        return jsonify({"code": 10003, "message": "参数校验失败", "errors": errors}), 400

    order_no = gen_order_no('PRO')
    demand_id = execute(
        """INSERT INTO t_procurement_demand
           (order_no, buyer_id, procurement_type, category_id, product_name, product_spec,
            quantity, unit, budget_amount, currency, delivery_deadline, delivery_address,
            contact_name, contact_phone, require_tax, invoice_type, remark, status)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'MATCHING')""",
        (order_no, g.user_id, body.get('procurementType','B2B'),
         body.get('categoryId'), body.get('productName'), body.get('productSpec',''),
         int(qty), body.get('unit','件'), float(budget), body.get('currency','CNY'),
         body.get('deliveryDeadline'), body.get('deliveryAddress',''),
         body.get('contactName',''), body.get('contactPhone',''),
         1 if body.get('requireTaxInvoice', True) else 0,
         body.get('invoiceType','SPECIAL_VAT'), body.get('remark',''))
    )
    # 模拟触发AI匹配（异步）
    try:
        redis_client.lpush("matching:queue", json.dumps({"demandId": demand_id, "ts": time.time()}))
    except Exception:
        pass
    return success({
        "demandId": demand_id,
        "orderNo": order_no,
        "status": "MATCHING",
        "estimatedMatchTime": (datetime.now() + timedelta(minutes=5)).strftime('%Y-%m-%dT%H:%M:%S'),
        "message": "需求已提交，正在为您智能匹配供应商"
    }, 201)

@app.route('/api/v1/procurement/demands', methods=['GET'])
@require_auth
@limiter.limit("300 per minute")   # 查询接口限流更宽松
def list_demands():
    page = max(0, int(request.args.get('page', 0)))
    size = min(50, max(1, int(request.args.get('size', 10))))
    status_filter = request.args.get('status')
    offset = page * size
    where = "WHERE buyer_id = %s"
    params = [g.user_id]
    if status_filter:
        where += " AND status = %s"
        params.append(status_filter)
    total = query_one(f"SELECT COUNT(*) AS cnt FROM t_procurement_demand {where}", params)['cnt']
    params += [size, offset]
    rows = query_all(
        f"SELECT * FROM t_procurement_demand {where} ORDER BY created_at DESC LIMIT %s OFFSET %s",
        params
    )
    # datetime -> str
    for r in rows:
        for k, v in r.items():
            if isinstance(v, datetime):
                r[k] = v.strftime('%Y-%m-%dT%H:%M:%S')
    return success({
        "content": rows, "totalElements": total,
        "totalPages": (total + size - 1) // size,
        "size": size, "number": page
    })

@app.route('/api/v1/procurement/demands/<int:demand_id>', methods=['GET'])
@require_auth
def get_demand(demand_id):
    row = query_one("SELECT * FROM t_procurement_demand WHERE id=%s AND buyer_id=%s", (demand_id, g.user_id))
    if not row:
        return error(10404, "采购需求不存在", 404)
    for k, v in row.items():
        if isinstance(v, datetime):
            row[k] = v.strftime('%Y-%m-%dT%H:%M:%S')
    row['matchedSuppliers'] = _get_mock_suppliers(demand_id)
    return success(row)

@app.route('/api/v1/procurement/demands/<int:demand_id>/cancel', methods=['PUT'])
@require_auth
def cancel_demand(demand_id):
    row = query_one("SELECT id, status FROM t_procurement_demand WHERE id=%s AND buyer_id=%s", (demand_id, g.user_id))
    if not row:
        return error(10404, "采购需求不存在", 404)
    if row['status'] in ('COMPLETED', 'CANCELLED'):
        return error(10007, f"当前状态 {row['status']} 不允许取消")
    body = request.get_json(silent=True) or {}
    execute("UPDATE t_procurement_demand SET status='CANCELLED' WHERE id=%s", (demand_id,))
    return success({"demandId": demand_id, "status": "CANCELLED", "reason": body.get('reason', '')})

# ===== AI匹配模块 =====
@app.route('/api/v1/matching/trigger', methods=['POST'])
@require_auth
@limiter.limit("50 per minute")
def trigger_matching():
    body = request.get_json(silent=True) or {}
    demand_id = body.get('demandId')
    if not demand_id:
        return error(10003, "demandId不能为空")
    task_id = f"match_task_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{demand_id}"
    try:
        redis_client.setex(f"matching:{task_id}", 3600, json.dumps({
            "status": "PROCESSING", "demandId": demand_id,
            "suppliers": _get_mock_suppliers(demand_id)
        }))
    except Exception:
        pass
    return success({
        "matchTaskId": task_id, "status": "PROCESSING",
        "estimatedSeconds": 30
    })

@app.route('/api/v1/matching/result/<task_id>', methods=['GET'])
@require_auth
def get_matching_result(task_id):
    try:
        data = redis_client.get(f"matching:{task_id}")
        if data:
            d = json.loads(data)
            d['status'] = 'COMPLETED'
            d['matchedSuppliers'] = d.get('suppliers', _get_mock_suppliers(0))
            d['aiAnalysis'] = '该需求品类明确，推荐优先联系综合评分最高的供应商，预计价格区间合理。'
            d['completedAt'] = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
            return success(d)
    except Exception:
        pass
    # fallback
    return success({
        "matchTaskId": task_id, "status": "COMPLETED",
        "matchedSuppliers": _get_mock_suppliers(0),
        "aiAnalysis": "匹配完成（降级模式）",
        "completedAt": datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
    })

def _get_mock_suppliers(demand_id):
    rows = query_all("SELECT id, company_name, avg_score, credit_rating FROM t_supplier WHERE status='ACTIVE' LIMIT 3")
    result = []
    for i, r in enumerate(rows):
        result.append({
            "supplierId": r['id'],
            "supplierName": r['company_name'],
            "matchScore": round(95 - i * 5 + random.uniform(-1, 1), 1),
            "matchReasons": ["历史成交匹配", "品类专业度高", "响应速度快"][: 3 - i],
            "estimatedPrice": round(random.uniform(40, 55), 2),
            "deliveryDays": 2 + i,
            "creditRating": r['credit_rating']
        })
    return result

# ===== 询价报价模块 =====
@app.route('/api/v1/inquiry', methods=['POST'])
@require_auth
@limiter.limit("100 per minute")
def create_inquiry():
    body = request.get_json(silent=True) or {}
    demand_id   = body.get('demandId')
    supplier_ids = body.get('supplierIds', [])
    if not demand_id or not supplier_ids:
        return error(10003, "demandId和supplierIds不能为空")
    deadline = body.get('inquiryDeadline', (datetime.now() + timedelta(days=3)).strftime('%Y-%m-%dT%H:%M:%S'))
    inquiry_id = execute(
        "INSERT INTO t_inquiry (demand_id, buyer_id, status, deadline, message) VALUES (%s,%s,'SENT',%s,%s)",
        (demand_id, g.user_id, deadline, body.get('message', ''))
    )
    return success({
        "inquiryId": inquiry_id, "status": "SENT",
        "supplierCount": len(supplier_ids),
        "deadline": deadline
    }, 201)

@app.route('/api/v1/inquiry/<int:inquiry_id>/quotes', methods=['POST'])
@require_auth
def submit_quote(inquiry_id):
    body = request.get_json(silent=True) or {}
    inq = query_one("SELECT id, status FROM t_inquiry WHERE id=%s", (inquiry_id,))
    if not inq:
        return error(10404, "询价单不存在", 404)
    quote_id = execute(
        """INSERT INTO t_quote (inquiry_id, supplier_id, unit_price, total_amount, tax_rate, delivery_days, valid_days, remark, status)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'SUBMITTED')""",
        (inquiry_id, g.user_id,
         body.get('unitPrice', 0), body.get('totalAmount', 0),
         body.get('taxRate', 0.13), body.get('deliveryDays', 3),
         body.get('validDays', 7), body.get('remark', ''))
    )
    execute("UPDATE t_inquiry SET status='QUOTED' WHERE id=%s", (inquiry_id,))
    return success({"quoteId": quote_id, "status": "SUBMITTED"}, 201)

@app.route('/api/v1/inquiry/<int:inquiry_id>/quotes/<int:quote_id>/accept', methods=['PUT'])
@require_auth
def accept_quote(inquiry_id, quote_id):
    quote = query_one("SELECT * FROM t_quote WHERE id=%s AND inquiry_id=%s", (quote_id, inquiry_id))
    if not quote:
        return error(10404, "报价单不存在", 404)
    if quote['status'] != 'SUBMITTED':
        return error(10008, f"报价状态 {quote['status']} 不允许接受")
    # 创建订单
    order_no = gen_order_no('ORD')
    inq = query_one("SELECT demand_id FROM t_inquiry WHERE id=%s", (inquiry_id,))
    order_id = execute(
        "INSERT INTO t_order (order_no, demand_id, buyer_id, supplier_id, total_amount, tax_amount, status) VALUES (%s,%s,%s,%s,%s,%s,'PENDING_PAYMENT')",
        (order_no, inq['demand_id'] if inq else None, g.user_id, quote['supplier_id'],
         float(quote['total_amount'] or 0), round(float(quote['total_amount'] or 0) * float(quote['tax_rate'] or 0.13), 2))
    )
    execute("UPDATE t_quote SET status='ACCEPTED' WHERE id=%s", (quote_id,))
    execute("UPDATE t_inquiry SET status='ACCEPTED' WHERE id=%s", (inquiry_id,))
    return success({"orderId": order_id, "orderNo": order_no, "orderStatus": "PENDING_PAYMENT"})

# ===== 订单模块 =====
@app.route('/api/v1/orders/<int:order_id>', methods=['GET'])
@require_auth
def get_order(order_id):
    row = query_one("SELECT * FROM t_order WHERE id=%s AND buyer_id=%s", (order_id, g.user_id))
    if not row:
        return error(10404, "订单不存在", 404)
    for k, v in row.items():
        if isinstance(v, datetime):
            row[k] = v.strftime('%Y-%m-%dT%H:%M:%S')
    row['orderId']     = row.pop('id')
    row['items']       = [{"productName": "采购商品", "quantity": 1, "unitPrice": float(row.get('total_amount') or 0)}]
    row['buyerInfo']   = {"buyerId": g.user_id, "name": g.username}
    row['supplierInfo']= {"supplierId": row.get('supplier_id')}
    return success(row)

@app.route('/api/v1/orders/<int:order_id>/confirm-receipt', methods=['PUT'])
@require_auth
def confirm_receipt(order_id):
    row = query_one("SELECT id, status FROM t_order WHERE id=%s AND buyer_id=%s", (order_id, g.user_id))
    if not row:
        return error(10404, "订单不存在", 404)
    execute("UPDATE t_order SET status='COMPLETED' WHERE id=%s", (order_id,))
    return success({"orderId": order_id, "orderStatus": "COMPLETED"})

# ===== 供应商模块 =====
@app.route('/api/v1/suppliers/register', methods=['POST'])
@limiter.limit("20 per minute")    # 注册接口严格限制
def register_supplier():
    body = request.get_json(silent=True) or {}
    if not body.get('companyName'):
        return error(10003, "企业名称不能为空")
    if not body.get('creditCode'):
        return error(10003, "统一社会信用代码不能为空")
    # 检查重复
    existing = query_one("SELECT id FROM t_supplier WHERE credit_code=%s", (body.get('creditCode'),))
    if existing:
        return error(10009, "该企业已申请入驻", 409)
    supplier_id = execute(
        "INSERT INTO t_supplier (company_name, credit_code, contact_name, contact_phone, contact_email, status) VALUES (%s,%s,%s,%s,%s,'REVIEWING')",
        (body['companyName'], body['creditCode'],
         body.get('contactName',''), body.get('contactPhone',''), body.get('contactEmail',''))
    )
    return success({"supplierId": supplier_id, "status": "REVIEWING",
                    "message": "申请已提交，审核周期1-3个工作日"}, 201)

# ===== 数据查询模块 =====
@app.route('/api/v1/data/market-price', methods=['GET'])
@require_auth
@limiter.limit("300 per minute")
def market_price():
    keyword = request.args.get('keyword', '').strip()
    if not keyword:
        return error(10003, "keyword不能为空")
    rows = query_all(
        "SELECT source, price, updated_at FROM t_market_price WHERE keyword=%s ORDER BY updated_at DESC",
        (keyword,)
    )
    if not rows:
        # 返回模拟数据
        rows = [{"source": "JD", "price": 48.00, "updated_at": datetime.now()},
                {"source": "TAOBAO", "price": 43.50, "updated_at": datetime.now()}]
    prices = [float(r['price']) for r in rows]
    sources = []
    for r in rows:
        ut = r['updated_at']
        sources.append({
            "source": r['source'],
            "price": float(r['price']),
            "updatedAt": ut.strftime('%Y-%m-%dT%H:%M:%S') if isinstance(ut, datetime) else str(ut)
        })
    return success({
        "keyword": keyword,
        "priceRange": {
            "min": min(prices), "max": max(prices),
            "avg": round(sum(prices) / len(prices), 2),
            "median": sorted(prices)[len(prices) // 2]
        },
        "sources": sources,
        "trend": "STABLE"
    })

# ===== 限流测试专用端点 =====
@app.route('/api/v1/test/rate-limit-check', methods=['GET'])
@require_auth
@limiter.limit("100 per minute")   # 和C端核心接口相同限制
def rate_limit_check():
    """专门用于验证限流是否生效的测试端点"""
    return success({
        "requestId": ''.join(random.choices(string.ascii_lowercase + string.digits, k=8)),
        "timestamp": datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3],
        "message": "请求通过"
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, threaded=True)
