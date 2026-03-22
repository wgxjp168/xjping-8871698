import os
from functools import wraps

import requests as req_lib
from flask import Flask, Response, g, jsonify, request
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

# --- Rate limiter ---
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per minute"],
    storage_uri=f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/1",
    headers_enabled=True,
    on_breach=lambda l: (
        jsonify({
            "code": 42900,
            "message": f"请求过于频繁，已触发限流拦截。规则：{l.description}。请60秒后重试。",
            "rateLimitRule": l.description,
            "data": None,
        }),
        429,
    ),
)


# --- Auth middleware ---
def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get('Authorization', '')
        if not auth.startswith('Bearer '):
            return jsonify({"code": 40100, "message": "未提供认证Token", "data": None}), 401
        token = auth[7:]
        try:
            r = req_lib.post(
                f"{USER_SERVICE_URL}/internal/auth/verify",
                json={"token": token},
                timeout=3,
            )
            data = r.json()
            if data.get('code') != 0 or not data.get('data', {}).get('valid'):
                return jsonify({"code": 40100, "message": "Token无效或已过期", "data": None}), 401
            g.user_id = str(data['data']['userId'])
            g.user_role = data['data']['role']
        except Exception:
            return jsonify({"code": 50001, "message": "认证服务异常", "data": None}), 503
        return f(*args, **kwargs)
    return decorated


# --- Generic proxy helper ---
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


def auth_headers():
    return {'X-User-Id': g.user_id, 'X-User-Role': g.user_role}


# --- Health check ---
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
    statuses = {}
    all_up = True
    for name, base_url in services.items():
        try:
            r = req_lib.get(f"{base_url}/health", timeout=3)
            statuses[name] = 'UP' if r.status_code == 200 else 'DOWN'
        except Exception:
            statuses[name] = 'DOWN'
        if statuses[name] != 'UP':
            all_up = False
    return jsonify({
        "code": 0,
        "message": "success",
        "data": {
            "status": "UP" if all_up else "DEGRADED",
            "services": statuses,
        },
    })


# --- Auth routes ---
@app.route('/api/v1/auth/login', methods=['POST'])
@limiter.limit("200 per minute")
def auth_login():
    return proxy(f"{USER_SERVICE_URL}/internal/auth/login")


@app.route('/api/v1/auth/register', methods=['POST'])
def auth_register():
    return proxy(f"{USER_SERVICE_URL}/internal/auth/register")


@app.route('/api/v1/auth/refresh', methods=['POST'])
@require_auth
def auth_refresh():
    return proxy(f"{USER_SERVICE_URL}/internal/auth/refresh", auth_headers())


# --- Procurement: demands ---
@app.route('/api/v1/procurement/demands', methods=['GET', 'POST'])
@limiter.limit("100 per minute")
@require_auth
def procurement_demands():
    url = f"{PROCUREMENT_SERVICE_URL}/internal/demands"
    if request.method == 'POST':
        return proxy(url, {**auth_headers(), 'X-User-Id': g.user_id})
    return proxy(url, auth_headers())


@app.route('/api/v1/procurement/demands/<int:demand_id>', methods=['GET', 'PUT'])
@require_auth
def procurement_demand(demand_id):
    return proxy(f"{PROCUREMENT_SERVICE_URL}/internal/demands/{demand_id}", auth_headers())


@app.route('/api/v1/procurement/demands/<int:demand_id>/status', methods=['PUT'])
@require_auth
def procurement_demand_status(demand_id):
    return proxy(f"{PROCUREMENT_SERVICE_URL}/internal/demands/{demand_id}/status", auth_headers())


# --- Procurement: quotes ---
@app.route('/api/v1/procurement/quotes', methods=['GET', 'POST'])
@require_auth
def procurement_quotes():
    return proxy(f"{PROCUREMENT_SERVICE_URL}/internal/quotes", auth_headers())


@app.route('/api/v1/procurement/quotes/<int:quote_id>/accept', methods=['PUT'])
@require_auth
def procurement_quote_accept(quote_id):
    return proxy(f"{PROCUREMENT_SERVICE_URL}/internal/quotes/{quote_id}/accept", auth_headers())


# --- AI routes ---
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


# --- Order routes ---
@app.route('/api/v1/orders', methods=['GET', 'POST'])
@require_auth
def orders():
    return proxy(f"{ORDER_SERVICE_URL}/internal/orders", auth_headers())


@app.route('/api/v1/orders/<int:order_id>', methods=['GET'])
@require_auth
def order(order_id):
    return proxy(f"{ORDER_SERVICE_URL}/internal/orders/{order_id}", auth_headers())


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
    return proxy(f"{ORDER_SERVICE_URL}/internal/orders/{order_id}/confirm-receipt", auth_headers())


# --- Supplier routes ---
@app.route('/api/v1/suppliers', methods=['GET', 'POST'])
@app.route('/api/v1/suppliers/register', methods=['POST'])
@require_auth
def suppliers():
    if request.method == 'POST':
        return proxy(f"{DATA_SERVICE_URL}/internal/suppliers/register", auth_headers())
    return proxy(f"{DATA_SERVICE_URL}/internal/suppliers", auth_headers())


@app.route('/api/v1/suppliers/<int:supplier_id>', methods=['GET'])
@require_auth
def supplier(supplier_id):
    return proxy(f"{DATA_SERVICE_URL}/internal/suppliers/{supplier_id}", auth_headers())


# --- Market routes ---
@app.route('/api/v1/market/prices', methods=['GET'])
@require_auth
def market_prices():
    return proxy(f"{DATA_SERVICE_URL}/internal/market/prices", auth_headers())


# --- Test route ---
@app.route('/api/v1/test/rate-limit-check', methods=['GET'])
@limiter.limit("100 per minute")
@require_auth
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
