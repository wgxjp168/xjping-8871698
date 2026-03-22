"""
ILbuy 我来购采购平台 - 本地验收测试服务
依赖：Flask + Flask-Limiter + Redis（已启动）+ SQLite（内置）
启动：python3 run_local.py
"""
import os, json, time, hmac, hashlib, base64, sqlite3, random, string, threading
from datetime import datetime, timedelta
from functools import wraps

import redis as redislib
from flask import Flask, request, jsonify, g
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# ===== 配置 =====
DB_PATH        = "/tmp/ilbuy_test.db"
REDIS_HOST     = "localhost"
REDIS_PORT     = 6379
REDIS_PASSWORD = "ILbuy@Redis2024"
JWT_SECRET     = "ILbuy@JWT@SecretKey@2024"
PORT           = 8080

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False

redis_client = redislib.Redis(
    host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASSWORD,
    decode_responses=True, socket_connect_timeout=3
)

# === 限流器：默认 100次/分钟，Redis存储 ===
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["100 per minute"],
    storage_uri=f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/1",
    headers_enabled=True
)

# ===== SQLite 初始化 =====
def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS t_user (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL,
        email TEXT,
        user_type TEXT NOT NULL DEFAULT 'ENTERPRISE',
        company_name TEXT,
        status TEXT NOT NULL DEFAULT 'ACTIVE',
        created_at TEXT DEFAULT (datetime('now'))
    );
    CREATE TABLE IF NOT EXISTS t_procurement_demand (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_no TEXT NOT NULL UNIQUE,
        buyer_id INTEGER NOT NULL,
        procurement_type TEXT NOT NULL,
        category_id INTEGER,
        product_name TEXT NOT NULL,
        product_spec TEXT,
        quantity INTEGER NOT NULL,
        unit TEXT,
        budget_amount REAL,
        currency TEXT DEFAULT 'CNY',
        delivery_deadline TEXT,
        delivery_address TEXT,
        contact_name TEXT,
        contact_phone TEXT,
        require_tax INTEGER DEFAULT 1,
        invoice_type TEXT DEFAULT 'SPECIAL_VAT',
        remark TEXT,
        status TEXT NOT NULL DEFAULT 'MATCHING',
        created_at TEXT DEFAULT (datetime('now')),
        updated_at TEXT DEFAULT (datetime('now'))
    );
    CREATE TABLE IF NOT EXISTS t_inquiry (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        demand_id INTEGER NOT NULL,
        buyer_id INTEGER NOT NULL,
        status TEXT DEFAULT 'SENT',
        deadline TEXT,
        message TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    );
    CREATE TABLE IF NOT EXISTS t_quote (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        inquiry_id INTEGER NOT NULL,
        supplier_id INTEGER NOT NULL,
        unit_price REAL,
        total_amount REAL,
        tax_rate REAL DEFAULT 0.13,
        delivery_days INTEGER,
        valid_days INTEGER,
        remark TEXT,
        status TEXT DEFAULT 'SUBMITTED',
        created_at TEXT DEFAULT (datetime('now'))
    );
    CREATE TABLE IF NOT EXISTS t_order (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_no TEXT NOT NULL UNIQUE,
        demand_id INTEGER,
        buyer_id INTEGER NOT NULL,
        supplier_id INTEGER NOT NULL,
        total_amount REAL,
        tax_amount REAL,
        status TEXT DEFAULT 'PENDING_PAYMENT',
        created_at TEXT DEFAULT (datetime('now'))
    );
    CREATE TABLE IF NOT EXISTS t_supplier (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_name TEXT NOT NULL,
        credit_code TEXT,
        contact_name TEXT,
        contact_phone TEXT,
        contact_email TEXT,
        status TEXT DEFAULT 'REVIEWING',
        credit_rating TEXT,
        avg_score REAL DEFAULT 5.0,
        created_at TEXT DEFAULT (datetime('now'))
    );
    CREATE TABLE IF NOT EXISTS t_market_price (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        keyword TEXT NOT NULL,
        source TEXT NOT NULL,
        price REAL,
        updated_at TEXT DEFAULT (datetime('now'))
    );
    """)
    # 初始化测试数据
    def sha256(s): return hashlib.sha256(s.encode()).hexdigest()
    users = [
        ('test_buyer_001', sha256('Test@123456'), 'buyer001@test.com', 'ENTERPRISE', '测试企业采购有限公司'),
        ('test_buyer_002', sha256('Test@123456'), 'buyer002@test.com', 'ENTERPRISE', '示范科技集团'),
        ('test_supplier_001', sha256('Test@123456'), 'sup001@test.com', 'SUPPLIER', None),
        ('test_supplier_002', sha256('Test@123456'), 'sup002@test.com', 'SUPPLIER', None),
        ('perf_buyer_001', sha256('Test@123456'), 'perf001@test.com', 'ENTERPRISE', '性能测试企业'),
        ('smoke_test', sha256('Test@123456'), 'smoke@test.com', 'ENTERPRISE', '冒烟测试账号'),
    ]
    for u in users:
        cur.execute("INSERT OR IGNORE INTO t_user (username,password,email,user_type,company_name) VALUES (?,?,?,?,?)", u)

    suppliers = [
        (5001,'北京文具联盟有限公司','91110108MA01AB1234','ACTIVE','AAA',4.80),
        (5002,'上海办公用品总仓','91310000MA01CD5678','ACTIVE','AA',4.60),
        (5003,'深圳数码优选科技','91440300MA01EF9012','ACTIVE','AA',4.50),
    ]
    for s in suppliers:
        cur.execute("INSERT OR IGNORE INTO t_supplier (id,company_name,credit_code,status,credit_rating,avg_score) VALUES (?,?,?,?,?,?)", s)

    prices = [
        ('A4打印纸','JD',48.00),('A4打印纸','TAOBAO',43.50),('A4打印纸','PDD',38.90),
        ('碳粉盒','JD',280.00),('碳粉盒','TAOBAO',260.00),
        ('笔记本电脑','JD',5999.00),('笔记本电脑','TAOBAO',5699.00),
        ('办公桌椅','JD',1580.00),('办公桌椅','TAOBAO',1360.00),
    ]
    for p in prices:
        cur.execute("INSERT OR IGNORE INTO t_market_price (keyword,source,price) VALUES (?,?,?)", p)

    conn.commit()
    conn.close()
    print(f"[DB] SQLite数据库初始化完成: {DB_PATH}")

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(e=None):
    db = g.pop('db', None)
    if db: db.close()

def qone(sql, args=()):
    r = get_db().execute(sql, args).fetchone()
    return dict(r) if r else None

def qall(sql, args=()):
    return [dict(r) for r in get_db().execute(sql, args).fetchall()]

def exe(sql, args=()):
    db = get_db()
    cur = db.execute(sql, args)
    db.commit()
    return cur.lastrowid

# ===== JWT =====
def _b64(data):
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode()

def make_token(payload):
    h = _b64(json.dumps({"alg":"HS256","typ":"JWT"}).encode())
    b = _b64(json.dumps(payload).encode())
    s = _b64(hmac.new(JWT_SECRET.encode(), f"{h}.{b}".encode(), hashlib.sha256).digest())
    return f"{h}.{b}.{s}"

def verify_token(token):
    try:
        h, b, s = token.split('.')
        exp = _b64(hmac.new(JWT_SECRET.encode(), f"{h}.{b}".encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(s, exp): return None
        pad = 4 - len(b) % 4
        p = json.loads(base64.urlsafe_b64decode(b + '='*pad))
        if p.get('exp', 0) < time.time(): return None
        return p
    except: return None

def require_auth(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        auth = request.headers.get('Authorization', '')
        if not auth.startswith('Bearer '):
            return jsonify({"code":10002,"message":"未认证，请先登录","data":None}), 401
        p = verify_token(auth[7:])
        if not p:
            return jsonify({"code":10002,"message":"Token无效或已过期","data":None}), 401
        g.user_id   = p['userId']
        g.username  = p['username']
        g.user_type = p.get('userType','ENTERPRISE')
        return f(*args, **kwargs)
    return wrapper

def ok(data, status=200):
    return jsonify({"code":0,"message":"success","data":data}), status

def err(code, msg, status=400):
    return jsonify({"code":code,"message":msg,"data":None}), status

def gen_no(prefix='PRO'):
    return prefix + datetime.now().strftime('%Y%m%d%H%M%S') + ''.join(random.choices(string.digits, k=4))

@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({
        "code": 42900,
        "message": f"请求过于频繁，已触发限流拦截。规则：{e.description}。请60秒后重试。",
        "data": None,
        "rateLimitRule": str(e.description)
    }), 429

# ===== 健康检查 =====
@app.route('/actuator/health')
@limiter.exempt
def health():
    db_ok    = bool(qone("SELECT 1 AS x"))
    redis_ok = True
    try: redis_client.ping()
    except: redis_ok = False
    status = "UP" if (db_ok and redis_ok) else "DOWN"
    return jsonify({
        "status": status,
        "components": {
            "db":    {"status":"UP" if db_ok    else "DOWN","details":{"database":"SQLite"}},
            "redis": {"status":"UP" if redis_ok else "DOWN"}
        }
    }), 200 if status=="UP" else 503

@app.route('/actuator/health/liveness')
@limiter.exempt
def liveness(): return jsonify({"status":"UP"}), 200

@app.route('/actuator/health/readiness')
@limiter.exempt
def readiness(): return jsonify({"status":"UP"}), 200

@app.route('/actuator/info')
@limiter.exempt
def info():
    return jsonify({"app":{"name":"ilbuy-api","version":"1.0.0"},"environment":"test"})

# ===== 认证 =====
@app.route('/api/v1/auth/login', methods=['POST'])
@limiter.limit("200 per minute")
def login():
    body = request.get_json(silent=True) or {}
    uname = body.get('username','').strip()
    passwd = body.get('password','').strip()
    if not uname or not passwd:
        return err(10003, "用户名和密码不能为空")
    pw_hash = hashlib.sha256(passwd.encode()).hexdigest()
    user = qone("SELECT id,username,user_type,status FROM t_user WHERE username=? AND password=?", (uname, pw_hash))
    if not user:
        return err(10001, "用户名或密码错误", 401)
    if user['status'] != 'ACTIVE':
        return err(10004, "账号已被禁用", 401)
    now = time.time()
    at = make_token({"userId":user['id'],"username":user['username'],"userType":user['user_type'],"iat":now,"exp":now+7200})
    rt = make_token({"userId":user['id'],"iat":now,"exp":now+604800,"type":"refresh"})
    try: redis_client.setex(f"token:{user['id']}", 7200, at)
    except: pass
    return ok({"accessToken":at,"refreshToken":rt,"tokenType":"Bearer","expiresIn":7200,
               "userId":user['id'],"username":user['username'],"userType":user['user_type'],
               "roles":[f"ROLE_{user['user_type']}"]})

@app.route('/api/v1/auth/refresh', methods=['POST'])
@limiter.limit("50 per minute")
def refresh():
    body = request.get_json(silent=True) or {}
    p = verify_token(body.get('refreshToken',''))
    if not p or p.get('type') != 'refresh':
        return err(10005, "Refresh Token无效", 401)
    user = qone("SELECT id,username,user_type FROM t_user WHERE id=?", (p['userId'],))
    if not user: return err(10006, "用户不存在", 401)
    now = time.time()
    at = make_token({"userId":user['id'],"username":user['username'],"userType":user['user_type'],"iat":now,"exp":now+7200})
    return ok({"accessToken":at,"expiresIn":7200})

@app.route('/api/v1/auth/logout', methods=['POST'])
@require_auth
def logout():
    try: redis_client.delete(f"token:{g.user_id}")
    except: pass
    return ok({"message":"已退出登录"})

# ===== 采购需求 =====
@app.route('/api/v1/procurement/demands', methods=['POST'])
@require_auth
@limiter.limit("100 per minute")   # ← C端核心限流：100次/分钟
def create_demand():
    body = request.get_json(silent=True) or {}
    errors = []
    if not body.get('productName'):     errors.append({"field":"productName","message":"商品名称不能为空"})
    if not body.get('procurementType'): errors.append({"field":"procurementType","message":"采购类型不能为空"})
    qty = body.get('quantity', 0)
    if not isinstance(qty,(int,float)) or qty<=0: errors.append({"field":"quantity","message":"数量必须大于0"})
    bgt = body.get('budgetAmount', 0)
    if not isinstance(bgt,(int,float)) or bgt<=0: errors.append({"field":"budgetAmount","message":"预算金额必须大于0"})
    if errors:
        return jsonify({"code":10003,"message":"参数校验失败","errors":errors}), 400
    no = gen_no('PRO')
    did = exe("""INSERT INTO t_procurement_demand
        (order_no,buyer_id,procurement_type,category_id,product_name,product_spec,
         quantity,unit,budget_amount,currency,delivery_deadline,delivery_address,
         contact_name,contact_phone,require_tax,invoice_type,remark,status)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'MATCHING')""",
        (no,g.user_id,body.get('procurementType','B2B'),body.get('categoryId'),
         body['productName'],body.get('productSpec',''),int(qty),body.get('unit','件'),
         float(bgt),body.get('currency','CNY'),body.get('deliveryDeadline'),
         body.get('deliveryAddress',''),body.get('contactName',''),body.get('contactPhone',''),
         1,body.get('invoiceType','SPECIAL_VAT'),body.get('remark','')))
    try: redis_client.lpush("matching:queue", json.dumps({"demandId":did,"ts":time.time()}))
    except: pass
    return ok({"demandId":did,"orderNo":no,"status":"MATCHING",
               "estimatedMatchTime":(datetime.now()+timedelta(minutes=5)).strftime('%Y-%m-%dT%H:%M:%S'),
               "message":"需求已提交，正在为您智能匹配供应商"}, 201)

@app.route('/api/v1/procurement/demands', methods=['GET'])
@require_auth
@limiter.limit("300 per minute")
def list_demands():
    page = max(0, int(request.args.get('page',0)))
    size = min(50, max(1, int(request.args.get('size',10))))
    sf   = request.args.get('status')
    where = "WHERE buyer_id=?"; params=[g.user_id]
    if sf: where+=" AND status=?"; params.append(sf)
    total = qone(f"SELECT COUNT(*) AS cnt FROM t_procurement_demand {where}", params)['cnt']
    rows  = qall(f"SELECT * FROM t_procurement_demand {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
                 params+[size, page*size])
    return ok({"content":rows,"totalElements":total,"totalPages":(total+size-1)//size,"size":size,"number":page})

@app.route('/api/v1/procurement/demands/<int:did>', methods=['GET'])
@require_auth
def get_demand(did):
    row = qone("SELECT * FROM t_procurement_demand WHERE id=? AND buyer_id=?", (did,g.user_id))
    if not row: return err(10404,"采购需求不存在",404)
    row['matchedSuppliers'] = _mock_suppliers()
    return ok(row)

@app.route('/api/v1/procurement/demands/<int:did>/cancel', methods=['PUT'])
@require_auth
def cancel_demand(did):
    row = qone("SELECT id,status FROM t_procurement_demand WHERE id=? AND buyer_id=?", (did,g.user_id))
    if not row: return err(10404,"采购需求不存在",404)
    if row['status'] in ('COMPLETED','CANCELLED'):
        return err(10007,f"当前状态 {row['status']} 不允许取消")
    body = request.get_json(silent=True) or {}
    exe("UPDATE t_procurement_demand SET status='CANCELLED' WHERE id=?", (did,))
    return ok({"demandId":did,"status":"CANCELLED","reason":body.get('reason','')})

# ===== AI匹配 =====
@app.route('/api/v1/matching/trigger', methods=['POST'])
@require_auth
@limiter.limit("50 per minute")
def trigger_matching():
    body=request.get_json(silent=True) or {}
    did=body.get('demandId')
    if not did: return err(10003,"demandId不能为空")
    task_id=f"match_task_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{did}"
    try: redis_client.setex(f"matching:{task_id}",3600,json.dumps({"status":"PROCESSING","demandId":did,"suppliers":_mock_suppliers()}))
    except: pass
    return ok({"matchTaskId":task_id,"status":"PROCESSING","estimatedSeconds":30})

@app.route('/api/v1/matching/result/<task_id>', methods=['GET'])
@require_auth
def get_match_result(task_id):
    try:
        data=redis_client.get(f"matching:{task_id}")
        if data:
            d=json.loads(data)
            return ok({**d,"status":"COMPLETED","matchedSuppliers":d.get("suppliers",_mock_suppliers()),
                       "aiAnalysis":"AI分析：该需求品类明确，推荐优先联系综合评分最高的供应商，价格区间合理。",
                       "completedAt":datetime.now().strftime('%Y-%m-%dT%H:%M:%S')})
    except: pass
    return ok({"matchTaskId":task_id,"status":"COMPLETED","matchedSuppliers":_mock_suppliers(),
               "aiAnalysis":"匹配完成（降级模式-规则引擎）","completedAt":datetime.now().strftime('%Y-%m-%dT%H:%M:%S')})

def _mock_suppliers():
    rows=qall("SELECT id,company_name,avg_score,credit_rating FROM t_supplier WHERE status='ACTIVE' LIMIT 3")
    return [{"supplierId":r['id'],"supplierName":r['company_name'],
             "matchScore":round(95-i*5+random.uniform(-1,1),1),
             "matchReasons":["历史成交匹配","品类专业度高","响应速度快"][:3-i],
             "estimatedPrice":round(random.uniform(40,55),2),
             "deliveryDays":2+i,"creditRating":r['credit_rating']}
            for i,r in enumerate(rows)]

# ===== 询价报价 =====
@app.route('/api/v1/inquiry', methods=['POST'])
@require_auth
@limiter.limit("100 per minute")
def create_inquiry():
    body=request.get_json(silent=True) or {}
    did=body.get('demandId'); sids=body.get('supplierIds',[])
    if not did or not sids: return err(10003,"demandId和supplierIds不能为空")
    dl=body.get('inquiryDeadline',(datetime.now()+timedelta(days=3)).strftime('%Y-%m-%dT%H:%M:%S'))
    iid=exe("INSERT INTO t_inquiry (demand_id,buyer_id,status,deadline,message) VALUES (?,?,'SENT',?,?)",
            (did,g.user_id,dl,body.get('message','')))
    return ok({"inquiryId":iid,"status":"SENT","supplierCount":len(sids),"deadline":dl},201)

@app.route('/api/v1/inquiry/<int:iid>/quotes', methods=['POST'])
@require_auth
def submit_quote(iid):
    body=request.get_json(silent=True) or {}
    inq=qone("SELECT id,status FROM t_inquiry WHERE id=?", (iid,))
    if not inq: return err(10404,"询价单不存在",404)
    qid=exe("INSERT INTO t_quote (inquiry_id,supplier_id,unit_price,total_amount,tax_rate,delivery_days,valid_days,remark,status) VALUES (?,?,?,?,?,?,?,?,'SUBMITTED')",
            (iid,g.user_id,body.get('unitPrice',0),body.get('totalAmount',0),
             body.get('taxRate',0.13),body.get('deliveryDays',3),body.get('validDays',7),body.get('remark','')))
    exe("UPDATE t_inquiry SET status='QUOTED' WHERE id=?", (iid,))
    return ok({"quoteId":qid,"status":"SUBMITTED"},201)

@app.route('/api/v1/inquiry/<int:iid>/quotes/<int:qid>/accept', methods=['PUT'])
@require_auth
def accept_quote(iid,qid):
    q=qone("SELECT * FROM t_quote WHERE id=? AND inquiry_id=?", (qid,iid))
    if not q: return err(10404,"报价单不存在",404)
    if q['status']!='SUBMITTED': return err(10008,f"报价状态 {q['status']} 不允许接受")
    inq=qone("SELECT demand_id FROM t_inquiry WHERE id=?", (iid,))
    no=gen_no('ORD')
    oid=exe("INSERT INTO t_order (order_no,demand_id,buyer_id,supplier_id,total_amount,tax_amount,status) VALUES (?,?,?,?,?,?,'PENDING_PAYMENT')",
            (no,inq['demand_id'] if inq else None,g.user_id,q['supplier_id'],
             float(q['total_amount'] or 0),round(float(q['total_amount'] or 0)*float(q['tax_rate'] or 0.13),2)))
    exe("UPDATE t_quote SET status='ACCEPTED' WHERE id=?", (qid,))
    exe("UPDATE t_inquiry SET status='ACCEPTED' WHERE id=?", (iid,))
    return ok({"orderId":oid,"orderNo":no,"orderStatus":"PENDING_PAYMENT"})

# ===== 订单 =====
@app.route('/api/v1/orders/<int:oid>', methods=['GET'])
@require_auth
def get_order(oid):
    row=qone("SELECT * FROM t_order WHERE id=? AND buyer_id=?", (oid,g.user_id))
    if not row: return err(10404,"订单不存在",404)
    row['orderId']=row.pop('id'); row['items']=[{"productName":"采购商品","quantity":1,"unitPrice":float(row.get('total_amount') or 0)}]
    row['buyerInfo']={"buyerId":g.user_id,"name":g.username}; row['supplierInfo']={"supplierId":row.get('supplier_id')}
    return ok(row)

@app.route('/api/v1/orders/<int:oid>/confirm-receipt', methods=['PUT'])
@require_auth
def confirm_receipt(oid):
    row=qone("SELECT id,status FROM t_order WHERE id=? AND buyer_id=?", (oid,g.user_id))
    if not row: return err(10404,"订单不存在",404)
    exe("UPDATE t_order SET status='COMPLETED' WHERE id=?", (oid,))
    return ok({"orderId":oid,"orderStatus":"COMPLETED"})

# ===== 供应商 =====
@app.route('/api/v1/suppliers/register', methods=['POST'])
@limiter.limit("20 per minute")
def register_supplier():
    body=request.get_json(silent=True) or {}
    if not body.get('companyName'): return err(10003,"企业名称不能为空")
    if not body.get('creditCode'):  return err(10003,"统一社会信用代码不能为空")
    if qone("SELECT id FROM t_supplier WHERE credit_code=?", (body['creditCode'],)):
        return err(10009,"该企业已申请入驻",409)
    sid=exe("INSERT INTO t_supplier (company_name,credit_code,contact_name,contact_phone,contact_email,status) VALUES (?,?,?,?,?,'REVIEWING')",
            (body['companyName'],body['creditCode'],body.get('contactName',''),body.get('contactPhone',''),body.get('contactEmail','')))
    return ok({"supplierId":sid,"status":"REVIEWING","message":"申请已提交，审核周期1-3个工作日"},201)

# ===== 数据查询 =====
@app.route('/api/v1/data/market-price', methods=['GET'])
@require_auth
@limiter.limit("300 per minute")
def market_price():
    kw=request.args.get('keyword','').strip()
    if not kw: return err(10003,"keyword不能为空")
    rows=qall("SELECT source,price,updated_at FROM t_market_price WHERE keyword=?", (kw,))
    if not rows: rows=[{"source":"JD","price":48.00,"updated_at":datetime.now().strftime('%Y-%m-%dT%H:%M:%S')},
                       {"source":"TAOBAO","price":43.50,"updated_at":datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}]
    prices=[float(r['price']) for r in rows]
    return ok({"keyword":kw,"priceRange":{"min":min(prices),"max":max(prices),
               "avg":round(sum(prices)/len(prices),2),"median":sorted(prices)[len(prices)//2]},
               "sources":rows,"trend":"STABLE"})

# ===== 限流测试端点 =====
@app.route('/api/v1/test/rate-limit-check', methods=['GET'])
@require_auth
@limiter.limit("100 per minute")    # C端核心限流标准
def rate_limit_check():
    return ok({"requestId":''.join(random.choices(string.ascii_lowercase+string.digits,k=8)),
               "timestamp":datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3],"passed":True})

if __name__ == '__main__':
    init_db()
    print(f"[INFO] ILbuy Mock API 启动中，端口 {PORT} ...")
    app.run(host='0.0.0.0', port=PORT, threaded=True, debug=False)
