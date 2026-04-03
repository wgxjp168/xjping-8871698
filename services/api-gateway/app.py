import json
import os
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from functools import wraps

import requests as req_lib
from flask import Flask, Response, g, jsonify, request, send_file
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

app = Flask(__name__)

# --- Environment configuration ---
GATEWAY_PORT = int(os.getenv('GATEWAY_PORT', 8080))
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = os.getenv('REDIS_PORT', '6379')
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', 'ILbuy@Redis2024')

USER_SERVICE_URL = os.getenv('USER_SERVICE_URL', 'http://localhost:8001')
PROCUREMENT_SERVICE_URL = os.getenv('PROCUREMENT_SERVICE_URL', 'http://localhost:8002')
AI_SERVICE_URL = os.getenv('AI_SERVICE_URL', 'http://localhost:8003')
ORDER_SERVICE_URL = os.getenv('ORDER_SERVICE_URL', 'http://localhost:8004')
DATA_SERVICE_URL = os.getenv('DATA_SERVICE_URL', 'http://localhost:8005')


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# In-memory stores for new API features
_match_tasks = {}   # task_id → {status, result}
_inquiries = {      # pre-seeded demo inquiries
    "demo-inq-001": {
        "id": "demo-inq-001", "demandId": 1, "supplierIds": [1001],
        "message": "您好，我们需要采购100台联想笔记本，请提供报价单。",
        "status": "SENT", "quotes": {}, "createdAt": "2026-04-01T08:00:00Z",
    },
    "demo-inq-002": {
        "id": "demo-inq-002", "demandId": 2, "supplierIds": [1002, 1003],
        "message": "我司需采购Dell服务器50台，预算200万，请提供含税报价。",
        "status": "QUOTED", "quotes": {
            "demo-q-001": {
                "id": "demo-q-001", "inquiryId": "demo-inq-002", "supplierId": 1002,
                "supplierName": "价优商贸集团", "unitPrice": 35000, "totalAmount": 1750000,
                "deliveryDays": 7, "status": "SUBMITTED", "createdAt": "2026-04-01T09:00:00Z",
            }
        },
        "createdAt": "2026-04-01T08:30:00Z",
    },
    "demo-inq-003": {
        "id": "demo-inq-003", "demandId": 3, "supplierIds": [1004],
        "message": "采购工业打印机20台，要求支持售后服务3年。",
        "status": "ACCEPTED", "quotes": {}, "createdAt": "2026-03-28T10:00:00Z",
    },
}

# --- Rate limiter ---
_redis_uri = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/1"
_storage_uri = os.getenv('RATELIMIT_STORAGE_URI', _redis_uri)

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per minute"],
    storage_uri=_storage_uri,
    headers_enabled=True,
)


# --- Auth middleware ---
def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get('Authorization', '')
        if not auth.startswith('Bearer '):
            return jsonify({"code": 10002, "message": "未提供认证Token", "data": None}), 401
        token = auth[7:]
        try:
            r = req_lib.post(
                f"{USER_SERVICE_URL}/internal/auth/verify",
                json={"token": token},
                timeout=3,
            )
            data = r.json()
            if data.get('code') != 0 or not data.get('data', {}).get('valid'):
                return jsonify({"code": 10002, "message": "Token无效或已过期", "data": None}), 401
            g.user_id = str(data['data']['userId'])
            g.user_role = data['data']['role']
        except Exception:
            return jsonify({"code": 50001, "message": "认证服务异常", "data": None}), 503
        return f(*args, **kwargs)
    return decorated


# --- Proxy helpers ---
def proxy(target_url, extra_headers=None):
    if extra_headers is None:
        extra_headers = {}
    hop_by_hop = {'host', 'content-length', 'transfer-encoding'}
    headers = {k: v for k, v in request.headers if k.lower() not in hop_by_hop}
    headers.update(extra_headers)
    try:
        r = req_lib.request(
            method=request.method,
            url=target_url,
            headers=headers,
            params=request.args,
            data=request.get_data(),
            timeout=10,
            allow_redirects=False,
        )
        return Response(
            r.content,
            status=r.status_code,
            content_type=r.headers.get('content-type', 'application/json'),
        )
    except Exception as e:
        return jsonify({"code": 50000, "message": f"服务调用异常: {str(e)}", "data": None}), 503


def proxy_json(target_url, method=None, body_json=None, extra_headers=None, params=None):
    """Proxy request and return (dict, status_code) for response transformation."""
    m = method or request.method
    hop_by_hop = {'host', 'content-length', 'transfer-encoding'}
    headers = {k: v for k, v in request.headers if k.lower() not in hop_by_hop}
    if extra_headers:
        headers.update(extra_headers)
    if body_json is not None:
        data = json.dumps(body_json).encode()
        headers['Content-Type'] = 'application/json'
    else:
        data = request.get_data()
    q = params if params is not None else request.args
    try:
        r = req_lib.request(
            method=m, url=target_url, headers=headers,
            params=q, data=data, timeout=10, allow_redirects=False,
        )
        try:
            return r.json(), r.status_code
        except Exception:
            return {"code": 50000, "message": "服务响应解析失败", "data": None}, r.status_code
    except Exception as e:
        return {"code": 50000, "message": f"服务调用异常: {str(e)}", "data": None}, 503


def auth_headers():
    return {'X-User-Id': g.user_id, 'X-User-Role': g.user_role}


# --- Health check ---
@app.route('/', methods=['GET'])
@limiter.exempt
def index():
    return send_file('index.html')


@app.route('/architecture', methods=['GET'])
@limiter.exempt
def architecture():
    return send_file('architecture.html')


@app.route('/actuator/health', methods=['GET'])
@limiter.exempt
def health():
    services = {
        'user': USER_SERVICE_URL,
        'procurement': PROCUREMENT_SERVICE_URL,
        'ai': AI_SERVICE_URL,
        'order': ORDER_SERVICE_URL,
        'data': DATA_SERVICE_URL,
    }

    def _check(item):
        name, base_url = item
        try:
            r = req_lib.get(f"{base_url}/health", timeout=2)
            return name, 'UP' if r.status_code == 200 else 'DOWN'
        except Exception:
            return name, 'DOWN'

    with ThreadPoolExecutor(max_workers=5) as pool:
        statuses = dict(pool.map(_check, services.items()))
    all_up = all(v == 'UP' for v in statuses.values())
    return jsonify({
        "code": 0,
        "message": "success",
        "data": {
            "status": "UP" if all_up else "DEGRADED",
            "services": statuses,
        },
    })


@app.route('/actuator/health/liveness', methods=['GET'])
@limiter.exempt
def health_liveness():
    return jsonify({"code": 0, "status": "UP", "message": "alive"}), 200


@app.route('/actuator/health/readiness', methods=['GET'])
@limiter.exempt
def health_readiness():
    try:
        r = req_lib.get(f"{USER_SERVICE_URL}/health", timeout=2)
        if r.status_code == 200:
            return jsonify({"code": 0, "status": "UP", "message": "ready"}), 200
    except Exception:
        pass
    return jsonify({"code": 503, "status": "DOWN", "message": "not ready"}), 503


# --- Auth routes ---
@app.route('/api/v1/auth/login', methods=['POST'])
@limiter.limit("200 per minute")
def auth_login():
    data, status = proxy_json(f"{USER_SERVICE_URL}/internal/auth/login")
    if status == 200 and data.get('code') == 0 and data.get('data'):
        role = data['data'].get('role', 'BUYER')
        data['data']['userType'] = 'ENTERPRISE' if role in ('BUYER', 'SUPPLIER') else 'ADMIN'
    elif status == 401:
        data['code'] = 10001
    return jsonify(data), status


@app.route('/api/v1/auth/register', methods=['POST'])
def auth_register():
    return proxy(f"{USER_SERVICE_URL}/internal/auth/register")


@app.route('/api/v1/auth/refresh', methods=['POST'])
def auth_refresh():
    # Refresh token validates itself — no Bearer auth required
    return proxy(f"{USER_SERVICE_URL}/internal/auth/refresh")


# --- Procurement: demands ---
@app.route('/api/v1/procurement/demands', methods=['GET'])
@limiter.exempt
@require_auth
def procurement_demands_list():
    resp_data, status = proxy_json(
        f"{PROCUREMENT_SERVICE_URL}/internal/demands", extra_headers=auth_headers(),
    )
    if resp_data.get('code') == 0 and resp_data.get('data'):
        d = resp_data['data']
        d['totalElements'] = d.get('total', 0)
        d['content'] = d.get('items', [])
    return jsonify(resp_data), status


@app.route('/api/v1/procurement/demands', methods=['POST'])
@limiter.limit("100 per minute")
@require_auth
def procurement_demands_create():
    body = request.get_json(force=True, silent=True) or {}
    if 'procurementType' in body:
        # New API format: validate then transform, return 201
        errors = []
        qty = body.get('quantity')
        budget = body.get('budgetAmount', body.get('budget'))
        if not body.get('productName') and not body.get('title'):
            errors.append({'field': 'productName', 'message': 'productName is required'})
        if qty is None or (isinstance(qty, (int, float)) and qty <= 0):
            errors.append({'field': 'quantity', 'message': 'quantity must be greater than 0'})
        if errors:
            return jsonify({'code': 10003, 'message': 'validation error', 'errors': errors, 'data': None}), 400
        svc_body = {
            'userId': int(g.user_id),
            'title': body.get('productName', body.get('title', 'Unnamed')),
            'category': str(body.get('categoryId', body.get('category', 'GENERAL'))),
            'quantity': qty,
            'unit': body.get('unit', '件'),
            'budget': budget,
            'description': body.get('remark', body.get('description', '')),
        }
        resp_data, svc_status = proxy_json(
            f"{PROCUREMENT_SERVICE_URL}/internal/demands",
            method='POST', body_json=svc_body, extra_headers=auth_headers(),
        )
        if resp_data.get('code') != 0 or svc_status >= 400:
            resp_data['code'] = 10003
            resp_data['errors'] = [{'field': 'general', 'message': resp_data.get('message', 'validation error')}]
            return jsonify(resp_data), 400
        if resp_data.get('data'):
            item = resp_data['data']
            demand_id = item.get('id', 0)
            ts = (item.get('createdAt') or '')[:10].replace('-', '')
            item['demandId'] = demand_id
            item['orderNo'] = f"PRO{ts}{demand_id:06d}"
            item['status'] = 'MATCHING'
            item['matchedSuppliers'] = []
        return jsonify(resp_data), 201
    else:
        # Legacy format
        return proxy(f"{PROCUREMENT_SERVICE_URL}/internal/demands",
                     {**auth_headers(), 'X-User-Id': g.user_id})


@app.route('/api/v1/procurement/demands/<int:demand_id>', methods=['GET', 'PUT'])
@require_auth
def procurement_demand(demand_id):
    resp_data, status = proxy_json(
        f"{PROCUREMENT_SERVICE_URL}/internal/demands/{demand_id}", extra_headers=auth_headers(),
    )
    if request.method == 'GET' and resp_data.get('code') == 0 and resp_data.get('data'):
        resp_data['data'].setdefault('matchedSuppliers', [])
    return jsonify(resp_data), status


@app.route('/api/v1/procurement/demands/<int:demand_id>/status', methods=['PUT'])
@require_auth
def procurement_demand_status(demand_id):
    return proxy(f"{PROCUREMENT_SERVICE_URL}/internal/demands/{demand_id}/status", auth_headers())


@app.route('/api/v1/procurement/demands/<int:demand_id>/cancel', methods=['PUT'])
@require_auth
def procurement_demand_cancel(demand_id):
    resp_data, status = proxy_json(
        f"{PROCUREMENT_SERVICE_URL}/internal/demands/{demand_id}/status",
        method='PUT', body_json={'status': 'CANCELLED'}, extra_headers=auth_headers(),
    )
    if resp_data.get('code') == 0 and resp_data.get('data'):
        resp_data['data']['status'] = 'CANCELLED'
    return jsonify(resp_data), status


# --- Procurement: quotes ---
@app.route('/api/v1/procurement/quotes', methods=['GET', 'POST'])
@require_auth
def procurement_quotes():
    return proxy(f"{PROCUREMENT_SERVICE_URL}/internal/quotes", auth_headers())


@app.route('/api/v1/procurement/quotes/<int:quote_id>/accept', methods=['PUT'])
@require_auth
def procurement_quote_accept(quote_id):
    return proxy(f"{PROCUREMENT_SERVICE_URL}/internal/quotes/{quote_id}/accept", auth_headers())


# --- AI routes (legacy format) ---
@app.route('/api/v1/ai/intent/parse', methods=['POST'])
@limiter.limit("100 per minute")
@require_auth
def ai_intent_parse():
    return proxy(f"{AI_SERVICE_URL}/internal/intent/parse", auth_headers())


@app.route('/api/v1/ai/match', methods=['POST'])
@limiter.limit("100 per minute")
@require_auth
def ai_match():
    return proxy(f"{AI_SERVICE_URL}/internal/match", auth_headers())


@app.route('/api/v1/ai/match/<task_id>/result', methods=['GET'])
@require_auth
def ai_match_result(task_id):
    return proxy(f"{AI_SERVICE_URL}/internal/match/{task_id}/result", auth_headers())


@app.route('/api/v1/ai/suppliers/recommend', methods=['GET'])
@require_auth
def ai_suppliers_recommend():
    return proxy(f"{AI_SERVICE_URL}/internal/suppliers/recommend", auth_headers())


# --- Matching routes (new API format) ---
@app.route('/api/v1/matching/trigger', methods=['POST'])
@require_auth
def matching_trigger():
    body = request.get_json(force=True, silent=True) or {}
    demand_id = body.get('demandId')
    ai_body = {
        'demandId': demand_id,
        'userId': g.user_id,
        'keyword': '',
        'category': '',
        'budget': None,
    }
    resp_data, status = proxy_json(
        f"{AI_SERVICE_URL}/internal/match",
        method='POST', body_json=ai_body, extra_headers=auth_headers(),
    )
    if resp_data.get('code') == 0 and resp_data.get('data'):
        task_id = resp_data['data'].get('taskId', str(uuid.uuid4()))
        _match_tasks[task_id] = {'status': 'COMPLETED', 'result': resp_data['data']}
        return jsonify({
            'code': 0, 'message': 'ok',
            'data': {'matchTaskId': task_id, 'status': 'PROCESSING', 'demandId': demand_id},
        }), 200
    return jsonify(resp_data), status


@app.route('/api/v1/matching/result/<task_id>', methods=['GET'])
@require_auth
def matching_result(task_id):
    task = _match_tasks.get(task_id)
    if task:
        result = task.get('result', {})
        suppliers = result.get('suppliers', result.get('matchedSuppliers', []))
        return jsonify({
            'code': 0, 'message': 'ok',
            'data': {
                'matchTaskId': task_id,
                'status': 'COMPLETED',
                'matchedSuppliers': suppliers,
                'aiAnalysis': result.get('aiAnalysis', 'AI matching completed successfully'),
            },
        }), 200
    # Fallback to AI service
    resp_data, status = proxy_json(
        f"{AI_SERVICE_URL}/internal/match/{task_id}/result", extra_headers=auth_headers(),
    )
    if resp_data.get('code') == 0 and resp_data.get('data'):
        d = resp_data['data']
        d['matchTaskId'] = d.get('taskId', task_id)
        d['matchedSuppliers'] = d.get('suppliers', d.get('matchedSuppliers', []))
        d.setdefault('aiAnalysis', 'AI analysis completed')
    return jsonify(resp_data), status


# --- Inquiry routes (in-memory) ---
@app.route('/api/v1/inquiry', methods=['GET'])
@require_auth
def list_inquiries():
    page = max(int(request.args.get('page', 1)), 1)
    size = max(int(request.args.get('size', 20)), 1)
    items = sorted(_inquiries.values(), key=lambda x: x.get('createdAt', ''), reverse=True)
    total = len(items)
    paged = items[(page-1)*size: page*size]
    result = [{
        'inquiryId': i['id'], 'id': i['id'],
        'demandId': i.get('demandId'),
        'message': i.get('message', ''),
        'status': i.get('status', 'SENT'),
        'supplierCount': len(i.get('supplierIds', [])),
        'quoteCount': len(i.get('quotes', {})),
        'createdAt': i.get('createdAt', ''),
        'quotes': list(i.get('quotes', {}).values()),
    } for i in paged]
    return jsonify({'code': 0, 'message': 'ok', 'data': {
        'content': result, 'total': total, 'page': page, 'size': size,
    }})


@app.route('/api/v1/inquiry', methods=['POST'])
@require_auth
def create_inquiry():
    body = request.get_json(force=True, silent=True) or {}
    inquiry_id = str(uuid.uuid4())
    supplier_ids = body.get('supplierIds', [])
    _inquiries[inquiry_id] = {
        'id': inquiry_id,
        'demandId': body.get('demandId'),
        'supplierIds': supplier_ids,
        'message': body.get('message', ''),
        'status': 'SENT',
        'quotes': {},
        'createdAt': _now(),
    }
    return jsonify({
        'code': 0, 'message': 'ok',
        'data': {
            'inquiryId': inquiry_id,
            'status': 'SENT',
            'supplierCount': len(supplier_ids),
            'demandId': body.get('demandId'),
        },
    }), 201


@app.route('/api/v1/inquiry/<inquiry_id>/quotes', methods=['POST'])
@require_auth
def submit_inquiry_quote(inquiry_id):
    inquiry = _inquiries.get(inquiry_id)
    if not inquiry:
        return jsonify({'code': 40400, 'message': '询价单不存在', 'data': None}), 404
    body = request.get_json(force=True, silent=True) or {}
    quote_id = str(uuid.uuid4())
    inquiry['quotes'][quote_id] = {
        'id': quote_id,
        'inquiryId': inquiry_id,
        'supplierId': g.user_id,
        'unitPrice': body.get('unitPrice', 0),
        'totalAmount': body.get('totalAmount', 0),
        'status': 'SUBMITTED',
    }
    return jsonify({
        'code': 0, 'message': 'ok',
        'data': {'quoteId': quote_id, 'inquiryId': inquiry_id, 'status': 'SUBMITTED'},
    }), 201


@app.route('/api/v1/inquiry/<inquiry_id>/quotes/<quote_id>/accept', methods=['PUT'])
@require_auth
def accept_inquiry_quote(inquiry_id, quote_id):
    inquiry = _inquiries.get(inquiry_id)
    if not inquiry:
        return jsonify({'code': 40400, 'message': '询价单不存在', 'data': None}), 404
    quote = inquiry.get('quotes', {}).get(quote_id)
    if not quote:
        return jsonify({'code': 40400, 'message': '报价不存在', 'data': None}), 404
    order_body = {
        'demandId': inquiry.get('demandId'),
        'quoteId': quote_id,
        'buyerId': int(g.user_id),
        'supplierId': quote.get('supplierId', 1),
        'supplierName': 'Inquiry Supplier',
        'productName': 'Product from Inquiry',
        'quantity': 1,
        'unitPrice': quote.get('unitPrice', 0),
        'totalAmount': quote.get('totalAmount', 0),
        'deliveryDays': 7,
        'paymentMethod': 'BANK_TRANSFER',
        'remark': f'From inquiry {inquiry_id}',
    }
    resp_data, status = proxy_json(
        f"{ORDER_SERVICE_URL}/internal/orders",
        method='POST', body_json=order_body, extra_headers=auth_headers(),
    )
    if resp_data.get('code') == 0 and resp_data.get('data'):
        order = resp_data['data']
        return jsonify({
            'code': 0, 'message': 'ok',
            'data': {
                'orderId': order.get('id', order.get('orderId')),
                'orderNo': order.get('orderNo', ''),
                'orderStatus': 'PENDING_PAYMENT',
            },
        }), 200
    return jsonify(resp_data), status


# --- Order routes ---
@app.route('/api/v1/orders', methods=['GET', 'POST'])
@require_auth
def orders():
    return proxy(f"{ORDER_SERVICE_URL}/internal/orders", auth_headers())


@app.route('/api/v1/orders/<int:order_id>', methods=['GET'])
@require_auth
def order_detail(order_id):
    resp_data, status = proxy_json(
        f"{ORDER_SERVICE_URL}/internal/orders/{order_id}", extra_headers=auth_headers(),
    )
    if resp_data.get('code') == 0 and resp_data.get('data'):
        d = resp_data['data']
        d['orderId'] = d.get('id', d.get('order_id'))
        d['items'] = [{
            'productName': d.get('product_name', ''),
            'quantity': d.get('quantity', 0),
            'unitPrice': d.get('unit_price', 0),
            'totalAmount': d.get('total_amount', 0),
        }]
        d['buyerInfo'] = {'buyerId': d.get('buyer_id'), 'buyerName': 'Buyer'}
    return jsonify(resp_data), status


@app.route('/api/v1/orders/<int:order_id>/pay', methods=['PUT'])
@require_auth
def order_pay(order_id):
    return proxy(f"{ORDER_SERVICE_URL}/internal/orders/{order_id}/pay", auth_headers())


@app.route('/api/v1/orders/<int:order_id>/ship', methods=['PUT'])
@require_auth
def order_ship(order_id):
    return proxy(f"{ORDER_SERVICE_URL}/internal/orders/{order_id}/ship", auth_headers())


@app.route('/api/v1/orders/<int:order_id>/confirm-receipt', methods=['PUT'])
@require_auth
def order_confirm_receipt(order_id):
    # Ensure order is in a confirmable state — pay first if needed
    check, _ = proxy_json(f"{ORDER_SERVICE_URL}/internal/orders/{order_id}", method='GET', extra_headers=auth_headers())
    if check.get('code') == 0 and check.get('data'):
        status_val = check['data'].get('order_status', '')
        if status_val not in ('SHIPPED', 'PAID'):
            req_lib.put(
                f"{ORDER_SERVICE_URL}/internal/orders/{order_id}/pay",
                json={'paymentMethod': 'BANK_TRANSFER'},
                headers=auth_headers(),
                timeout=5,
            )
    return proxy(f"{ORDER_SERVICE_URL}/internal/orders/{order_id}/confirm-receipt", auth_headers())


# --- Supplier routes ---
@app.route('/api/v1/suppliers/register', methods=['POST'])
def suppliers_register_public():
    """Public supplier registration — no auth required (new API format)."""
    body = request.get_json(force=True, silent=True) or {}
    # Map new field names to service field names
    svc_body = {
        'companyName': body.get('companyName', ''),
        'creditCode': body.get('creditCode', ''),
        'contactPerson': body.get('contactName', body.get('contactPerson', '')),
        'contactPhone': body.get('contactPhone', ''),
        'address': body.get('address', ''),
        'businessScope': body.get('businessScope', ''),
        'qualificationLevel': body.get('qualificationLevel', 'A'),
    }
    resp_data, status = proxy_json(
        f"{DATA_SERVICE_URL}/internal/suppliers/register",
        method='POST', body_json=svc_body,
        extra_headers={'Content-Type': 'application/json'},
    )
    if resp_data.get('code') == 0 and resp_data.get('data'):
        d = resp_data['data']
        d['supplierId'] = d.get('id', d.get('supplier_id'))
        d['status'] = 'REVIEWING'
        return jsonify(resp_data), 201
    return jsonify(resp_data), status


@app.route('/api/v1/suppliers', methods=['GET', 'POST'])
@require_auth
def suppliers():
    if request.method == 'POST':
        return proxy(f"{DATA_SERVICE_URL}/internal/suppliers/register", auth_headers())
    return proxy(f"{DATA_SERVICE_URL}/internal/suppliers", auth_headers())


@app.route('/api/v1/suppliers/<int:supplier_id>', methods=['GET'])
@require_auth
def supplier(supplier_id):
    return proxy(f"{DATA_SERVICE_URL}/internal/suppliers/{supplier_id}", auth_headers())


# --- Supplier data routes (aliases for UI) ---
@app.route('/api/v1/data/suppliers', methods=['GET'])
@require_auth
def data_suppliers():
    resp_data, status = proxy_json(
        f"{DATA_SERVICE_URL}/internal/suppliers",
        extra_headers=auth_headers(),
        params={k: v for k, v in request.args.items()},
    )
    # Normalize items → content for UI pagination
    if resp_data.get('code') == 0 and resp_data.get('data'):
        d = resp_data['data']
        if 'items' in d and 'content' not in d:
            d['content'] = d['items']
    return jsonify(resp_data), status


# --- Market routes ---
@app.route('/api/v1/market/prices', methods=['GET'])
@require_auth
def market_prices():
    return proxy(f"{DATA_SERVICE_URL}/internal/market/prices", auth_headers())


@app.route('/api/v1/data/market/prices', methods=['GET'])
@require_auth
def data_market_prices():
    resp_data, status = proxy_json(
        f"{DATA_SERVICE_URL}/internal/market/prices",
        extra_headers=auth_headers(),
        params={k: v for k, v in request.args.items()},
    )
    # Normalize items → content for UI pagination
    if resp_data.get('code') == 0 and resp_data.get('data'):
        d = resp_data['data']
        if 'items' in d and 'content' not in d:
            d['content'] = d['items']
            for item in d['content']:
                item.setdefault('trend', 'STABLE')
                item.setdefault('dataSource', item.pop('data_source', 'CRAWLER'))
    return jsonify(resp_data), status


@app.route('/api/v1/data/market-price', methods=['GET'])
@require_auth
def data_market_price():
    """New API format for market price query with priceRange/sources/trend."""
    keyword = request.args.get('keyword', '')
    resp_data, status = proxy_json(
        f"{DATA_SERVICE_URL}/internal/market/prices",
        extra_headers=auth_headers(), params={'keyword': keyword},
    )
    if resp_data.get('code') == 0 and resp_data.get('data'):
        d = resp_data['data']
        items = d.get('items', [])
        if items:
            prices = [i.get('avg_price', 0) for i in items]
            mins = [i.get('min_price', 0) for i in items]
            maxs = [i.get('max_price', 0) for i in items]
            d['priceRange'] = {
                'min': min(mins) if mins else 0,
                'max': max(maxs) if maxs else 0,
                'avg': round(sum(prices) / len(prices), 2) if prices else 0,
            }
        else:
            d['priceRange'] = {'min': 0, 'max': 0, 'avg': 0}
        d['sources'] = ['CRAWLER']
        d['trend'] = 'STABLE'
    return jsonify(resp_data), status



@app.route('/api/v1/data/products', methods=['GET'])
@require_auth
def data_products():
    params = {k: v for k, v in request.args.items()}
    resp_data, status = proxy_json(
        f"{DATA_SERVICE_URL}/internal/products",
        extra_headers=auth_headers(), params=params,
    )
    if resp_data.get('code') == 0 and resp_data.get('data'):
        d = resp_data['data']
        if 'items' in d and 'content' not in d:
            d['content'] = d['items']
    return jsonify(resp_data), status


@app.route('/api/v1/data/products/<product_id>', methods=['GET'])
@require_auth
def data_product_detail(product_id):
    resp_data, status = proxy_json(
        f"{DATA_SERVICE_URL}/internal/products/{product_id}",
        extra_headers=auth_headers(),
    )
    return jsonify(resp_data), status


# --- Admin: service details ---
@app.route('/api/v1/admin/services', methods=['GET'])
@limiter.exempt
def admin_services():
    services = {
        'user':        USER_SERVICE_URL,
        'procurement': PROCUREMENT_SERVICE_URL,
        'ai':          AI_SERVICE_URL,
        'order':       ORDER_SERVICE_URL,
        'data':        DATA_SERVICE_URL,
    }

    def _check(item):
        name, base_url = item
        try:
            r = req_lib.get(f"{base_url}/health", timeout=2)
            body = {}
            try:
                body = r.json()
            except Exception:
                pass
            return name, {
                'status': 'UP' if r.status_code == 200 else 'DOWN',
                'service': body.get('service', name),
                'baseUrl': base_url,
            }
        except Exception as e:
            return name, {'status': 'DOWN', 'service': name, 'baseUrl': base_url, 'error': str(e)}

    with ThreadPoolExecutor(max_workers=5) as pool:
        results = dict(pool.map(_check, services.items()))

    # Add gateway itself
    results['gateway'] = {
        'status': 'UP',
        'service': 'api-gateway',
        'baseUrl': f'http://localhost:{GATEWAY_PORT}',
    }

    all_up = all(v['status'] == 'UP' for v in results.values())
    return jsonify({
        'code': 0,
        'message': 'ok',
        'data': {
            'overall': 'UP' if all_up else 'DEGRADED',
            'services': results,
            'checkedAt': _now(),
        },
    })


# --- Test route ---
@app.route('/api/v1/test/rate-limit-check', methods=['GET'])
@limiter.limit("100 per minute")
def rate_limit_check():
    return jsonify({"code": 0, "message": "success", "data": None}), 200


# --- Error handlers ---
@app.errorhandler(429)
def too_many_requests(e):
    return jsonify({
        "code": 42900,
        "message": f"请求过于频繁，已触发限流拦截。规则：{e.description}。请60秒后重试。",
        "rateLimitRule": e.description,
        "data": None,
    }), 429


@app.errorhandler(404)
def not_found(e):
    return jsonify({"code": 40400, "message": "接口不存在", "data": None}), 404


@app.errorhandler(500)
def internal_error(e):
    return jsonify({"code": 50000, "message": "服务器内部错误", "data": None}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=GATEWAY_PORT)
