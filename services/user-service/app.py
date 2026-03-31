import os
import sqlite3
import hashlib
import hmac
import base64
import json
import time
import tempfile
from flask import Flask, request, jsonify

app = Flask(__name__)

DB_PATH = os.environ.get('DB_PATH', os.path.join(tempfile.gettempdir(), 'ilbuy_user.db'))
JWT_SECRET = os.environ.get('JWT_SECRET', 'ILbuy@JWT@SecretKey@2024@Production')
PORT = int(os.environ.get('USER_SERVICE_PORT', 8001))
TOKEN_EXPIRY = 7200


# --- JWT helpers ---

def b64url_encode(data):
    if isinstance(data, str):
        data = data.encode()
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode()


def create_token(payload, secret):
    header = b64url_encode(json.dumps({"alg": "HS256", "typ": "JWT"}))
    p = b64url_encode(json.dumps(payload))
    sig = b64url_encode(hmac.new(secret.encode(), f"{header}.{p}".encode(), hashlib.sha256).digest())
    return f"{header}.{p}.{sig}"


def verify_token(token, secret):
    try:
        h, p, s = token.split('.')
        expected = b64url_encode(hmac.new(secret.encode(), f"{h}.{p}".encode(), hashlib.sha256).digest())
        if s != expected:
            return None
        payload = json.loads(base64.urlsafe_b64decode(p + '=='))
        if payload.get('exp', 0) < time.time():
            return None
        return payload
    except:
        return None


# --- Password helper ---

def hash_password(password):
    return hashlib.sha256(f"{password}:ILbuy2024".encode()).hexdigest()


# --- Response helper ---

def resp(code, message, data=None):
    return jsonify({"code": code, "message": message, "data": data})


# --- DB helpers ---

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS t_user (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            role TEXT DEFAULT 'BUYER',
            status TEXT DEFAULT 'ACTIVE',
            created_at TEXT
        )
    ''')
    seed_users = [
        ('buyer01',    'Buyer@123456',    'BUYER'),
        ('supplier01', 'Supplier@123456', 'SUPPLIER'),
        ('admin01',    'Admin@123456',    'ADMIN'),
    ]
    for username, password, role in seed_users:
        conn.execute(
            'INSERT OR IGNORE INTO t_user (username, password_hash, role, status, created_at) VALUES (?, ?, ?, ?, ?)',
            (username, hash_password(password), role, 'ACTIVE', time.strftime('%Y-%m-%dT%H:%M:%S'))
        )
    conn.commit()
    conn.close()


# --- Endpoints ---

@app.route('/internal/auth/login', methods=['POST'])
def login():
    body = request.get_json(force=True) or {}
    username = body.get('username', '')
    password = body.get('password', '')
    conn = get_db()
    user = conn.execute('SELECT * FROM t_user WHERE username = ?', (username,)).fetchone()
    conn.close()
    if not user or user['password_hash'] != hash_password(password):
        return resp(401, 'Invalid credentials', None), 401
    now = int(time.time())
    access_payload = {'userId': user['id'], 'username': user['username'], 'role': user['role'], 'exp': now + TOKEN_EXPIRY, 'type': 'access'}
    refresh_payload = {'userId': user['id'], 'username': user['username'], 'role': user['role'], 'exp': now + TOKEN_EXPIRY * 2, 'type': 'refresh'}
    return resp(0, 'success', {
        'userId': user['id'],
        'username': user['username'],
        'role': user['role'],
        'accessToken': create_token(access_payload, JWT_SECRET),
        'refreshToken': create_token(refresh_payload, JWT_SECRET),
        'expiresIn': TOKEN_EXPIRY,
    })


@app.route('/internal/auth/register', methods=['POST'])
def register():
    body = request.get_json(force=True) or {}
    username = body.get('username', '')
    password = body.get('password', '')
    email = body.get('email')
    phone = body.get('phone')
    role = body.get('role', 'BUYER')
    if role not in ('BUYER', 'SUPPLIER'):
        return resp(400, 'Invalid role', None), 400
    conn = get_db()
    try:
        cur = conn.execute(
            'INSERT INTO t_user (username, password_hash, email, phone, role, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)',
            (username, hash_password(password), email, phone, role, 'ACTIVE', time.strftime('%Y-%m-%dT%H:%M:%S'))
        )
        conn.commit()
        user_id = cur.lastrowid
    except sqlite3.IntegrityError:
        conn.close()
        return resp(409, 'Username already exists', None), 409
    conn.close()
    return resp(0, 'success', {'userId': user_id, 'username': username, 'role': role})


@app.route('/internal/auth/verify', methods=['POST'])
def verify():
    body = request.get_json(force=True) or {}
    token = body.get('token', '')
    payload = verify_token(token, JWT_SECRET)
    if not payload:
        return resp(40100, 'token invalid or expired', {'valid': False})
    return resp(0, 'success', {
        'userId': payload.get('userId'),
        'username': payload.get('username'),
        'role': payload.get('role'),
        'valid': True,
    })


@app.route('/internal/auth/refresh', methods=['POST'])
def refresh():
    body = request.get_json(force=True) or {}
    refresh_token = body.get('refreshToken', '')
    payload = verify_token(refresh_token, JWT_SECRET)
    if not payload or payload.get('type') != 'refresh':
        return resp(40100, 'token invalid or expired', {'valid': False}), 401
    now = int(time.time())
    access_payload = {'userId': payload['userId'], 'username': payload['username'], 'role': payload['role'], 'exp': now + TOKEN_EXPIRY, 'type': 'access'}
    return resp(0, 'success', {
        'accessToken': create_token(access_payload, JWT_SECRET),
        'expiresIn': TOKEN_EXPIRY,
    })


@app.route('/internal/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    conn = get_db()
    user = conn.execute('SELECT id, username, email, phone, role, status, created_at FROM t_user WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    if not user:
        return resp(404, 'User not found', None), 404
    return resp(0, 'success', dict(user))


@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "UP", "service": "user-service"})


if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=PORT)
