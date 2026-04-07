"""
product-service — ILbuy 商品服务
业务逻辑层：商品管理、SKU、价格历史、推荐、比价、价格提醒
Port: PRODUCT_SERVICE_PORT (default 8006)
"""
import json
import os
import sqlite3
import tempfile
import uuid
from datetime import datetime, timezone
from flask import Flask, request, jsonify

app = Flask(__name__)

DB_PATH = os.environ.get('DB_PATH', os.path.join(tempfile.gettempdir(), 'ilbuy_product.db'))
PORT = int(os.environ.get('PRODUCT_SERVICE_PORT', 8006))


# ── Helpers ───────────────────────────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def now_str():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def resp(code=0, message='ok', data=None):
    return jsonify({'code': code, 'message': message, 'data': data})


def _row_to_product(row):
    d = dict(row)
    d['isImported'] = bool(d.pop('is_imported', 0))
    d['canReturn']  = bool(d.pop('can_return', 1))
    extra = d.pop('extra_json', None)
    if extra:
        try:
            d['extraSchema'] = json.loads(extra)
        except Exception:
            d['extraSchema'] = None
    return d


def _check_price_alerts(conn, product_id, new_price):
    """Trigger any active price alerts where targetPrice >= new_price."""
    rows = conn.execute(
        "SELECT id FROM t_price_alert WHERE product_id=? AND status='active' AND target_price >= ?",
        (product_id, new_price)
    ).fetchall()
    if rows:
        ts = now_str()
        ids = [r['id'] for r in rows]
        conn.execute(
            f"UPDATE t_price_alert SET status='triggered', triggered_at=? "
            f"WHERE id IN ({','.join('?'*len(ids))})",
            [ts] + ids
        )


# ── DB Init ───────────────────────────────────────────────────────────────────

def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS t_product (
            id               TEXT PRIMARY KEY,
            platform         TEXT NOT NULL,
            platform_name    TEXT NOT NULL,
            title            TEXT NOT NULL,
            subtitle         TEXT,
            main_category    TEXT NOT NULL,
            sub_category     TEXT,
            third_category   TEXT,
            brand_id         TEXT,
            brand_name       TEXT,
            shop_id          TEXT,
            shop_name        TEXT,
            current_price    REAL NOT NULL,
            original_price   REAL,
            discount         REAL DEFAULT 1.0,
            currency         TEXT DEFAULT 'CNY',
            stock_quantity   INTEGER DEFAULT 0,
            available_quantity INTEGER DEFAULT 0,
            sold_quantity    INTEGER DEFAULT 0,
            monthly_sales    INTEGER DEFAULT 0,
            average_score    REAL DEFAULT 5.0,
            positive_rate    REAL DEFAULT 1.0,
            total_reviews    INTEGER DEFAULT 0,
            main_image       TEXT,
            status           TEXT DEFAULT 'on_sale',
            is_imported      INTEGER DEFAULT 0,
            country          TEXT DEFAULT '中国',
            shipping_fee     REAL DEFAULT 0.0,
            can_return       INTEGER DEFAULT 1,
            extra_json       TEXT,
            created_at       TEXT,
            updated_at       TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_product_category ON t_product(main_category);
        CREATE INDEX IF NOT EXISTS idx_product_status   ON t_product(status);
        CREATE INDEX IF NOT EXISTS idx_product_platform ON t_product(platform);
        CREATE INDEX IF NOT EXISTS idx_product_brand    ON t_product(brand_name);

        CREATE TABLE IF NOT EXISTS t_product_sku (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id TEXT NOT NULL,
            sku_id     TEXT NOT NULL,
            sku_code   TEXT,
            specs      TEXT,
            price      REAL NOT NULL,
            stock      INTEGER DEFAULT 0,
            is_default INTEGER DEFAULT 0,
            created_at TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_sku_product ON t_product_sku(product_id);

        CREATE TABLE IF NOT EXISTS t_price_history (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id     TEXT NOT NULL,
            price          REAL NOT NULL,
            original_price REAL,
            event_type     TEXT DEFAULT 'update',
            remark         TEXT,
            recorded_at    TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_ph_product ON t_price_history(product_id);

        CREATE TABLE IF NOT EXISTS t_product_view (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id TEXT NOT NULL,
            user_id    TEXT,
            session_id TEXT,
            source     TEXT DEFAULT 'direct',
            viewed_at  TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_view_product ON t_product_view(product_id);

        CREATE TABLE IF NOT EXISTS t_price_alert (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id   TEXT NOT NULL,
            user_id      TEXT NOT NULL,
            target_price REAL NOT NULL,
            status       TEXT DEFAULT 'active',
            triggered_at TEXT,
            created_at   TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_alert_user    ON t_price_alert(user_id);
        CREATE INDEX IF NOT EXISTS idx_alert_product ON t_price_alert(product_id);
    """)

    # ── Seed demo products ────────────────────────────────────────────────────
    ts = now_str()
    products = [
        ('PROD_001', 'jd',         '京东',   '联想ThinkPad E14 Gen5 笔记本 i7-1355U 16G 512G',
         '企业专供版 24期免息',     '电脑办公', '笔记本电脑', '商务本',
         'B001', '联想', 'SHOP_JD_LX', '联想京东自营', 5299.0, 5999.0, 0.883,
         485, 480, 12800, 850, 4.8, 0.976, 12500,
         'https://img.ilbuy.com/prod/PROD_001.jpg', 'on_sale', 0, '中国', 0.0, 1),
        ('PROD_002', 'tmall',      '天猫',   '华为MateBook X Pro 2024 笔记本 i9 32G 1T',
         '轻薄旗舰 三屏协同',       '电脑办公', '笔记本电脑', '超薄本',
         'B002', '华为', 'SHOP_TM_HW', '华为天猫旗舰', 9999.0, 11999.0, 0.833,
         320, 315, 8600, 420, 4.9, 0.988, 8200,
         'https://img.ilbuy.com/prod/PROD_002.jpg', 'on_sale', 0, '中国', 0.0, 1),
        ('PROD_003', 'jd',         '京东',   'Apple iPhone 15 Pro Max 256G 深空钛色',
         '钛金属边框 A17Pro芯片',   '手机通讯', '智能手机', '旗舰手机',
         'B003', '苹果', 'SHOP_JD_AP', '苹果京东官方', 9499.0, 9999.0, 0.950,
         1200, 1180, 45000, 3200, 4.9, 0.994, 42000,
         'https://img.ilbuy.com/prod/PROD_003.jpg', 'on_sale', 1, '美国', 0.0, 1),
        ('PROD_004', 'pinduoduo',  '拼多多', '小米Redmi Note 13 Pro 5G 手机 256G',
         '2亿像素 旗舰影像',        '手机通讯', '智能手机', '中端手机',
         'B004', '小米', 'SHOP_PDD_MI', '小米官方旗舰', 1599.0, 1999.0, 0.800,
         5000, 4980, 89000, 6800, 4.7, 0.962, 86000,
         'https://img.ilbuy.com/prod/PROD_004.jpg', 'on_sale', 0, '中国', 0.0, 1),
        ('PROD_005', 'tmall',      '天猫',   '格力空调 KFR-35GW 1.5匹 三级能效 变频',
         '新国标三级能效 静音节能', '家用电器', '空调', '壁挂式空调',
         'B005', '格力', 'SHOP_TM_GL', '格力官方旗舰', 2299.0, 2799.0, 0.821,
         800, 790, 22000, 1500, 4.8, 0.971, 21000,
         'https://img.ilbuy.com/prod/PROD_005.jpg', 'on_sale', 0, '中国', 0.0, 1),
        ('PROD_006', 'jd',         '京东',   '海尔冰箱 BCD-470WDPD 470L 对开门 一级能效',
         '风冷无霜 干湿分储',       '家用电器', '冰箱', '对开门冰箱',
         'B006', '海尔', 'SHOP_JD_HR', '海尔京东自营', 3299.0, 3999.0, 0.825,
         650, 640, 15000, 980, 4.7, 0.968, 14500,
         'https://img.ilbuy.com/prod/PROD_006.jpg', 'on_sale', 0, '中国', 0.0, 1),
        ('PROD_007', '1688',       '阿里1688', '西门子PLC S7-1200 CPU1214C AC/DC/RLY',
         '工业自动化控制器 原装正品','工业设备', '控制器', 'PLC',
         'B007', '西门子', 'SHOP_1688_SM', '西门子授权经销商', 4200.0, 4800.0, 0.875,
         200, 195, 3200, 180, 4.9, 0.991, 3100,
         'https://img.ilbuy.com/prod/PROD_007.jpg', 'on_sale', 1, '德国', 0.0, 1),
        ('PROD_008', '1688',       '阿里1688', '不锈钢板材 304# 厚2mm 1000×2000mm',
         'B2B批量价 可定制尺寸',    '原材料', '钢材', '不锈钢板',
         'B008', '宝钢', 'SHOP_1688_BG', '宝钢授权经销商', 85.0, 98.0, 0.867,
         50000, 49000, 120000, 8000, 4.6, 0.955, 18000,
         'https://img.ilbuy.com/prod/PROD_008.jpg', 'on_sale', 0, '中国', 0.0, 1),
    ]
    for p in products:
        (pid, platform, pname, title, subtitle, mcat, scat, tcat,
         bid, bname, shopid, shopname, cprice, oprice, disc,
         stock, avail, sold, msales, score, posrate, reviews,
         img, status, imported, country, sfee, canret) = p
        conn.execute(
            """INSERT OR REPLACE INTO t_product
               (id, platform, platform_name, title, subtitle,
                main_category, sub_category, third_category,
                brand_id, brand_name, shop_id, shop_name,
                current_price, original_price, discount,
                stock_quantity, available_quantity, sold_quantity, monthly_sales,
                average_score, positive_rate, total_reviews,
                main_image, status, is_imported, country,
                shipping_fee, can_return, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (pid, platform, pname, title, subtitle, mcat, scat, tcat,
             bid, bname, shopid, shopname, cprice, oprice, disc,
             stock, avail, sold, msales, score, posrate, reviews,
             img, status, imported, country, sfee, canret, ts, ts)
        )

    # Seed SKUs (2 per product)
    skus = [
        ('PROD_001', 'SKU_001_A', 'TP-E14-I7-16-512', '{"处理器":"i7-1355U","内存":"16G","硬盘":"512G SSD"}', 5299.0, 300, 1),
        ('PROD_001', 'SKU_001_B', 'TP-E14-I7-32-512', '{"处理器":"i7-1355U","内存":"32G","硬盘":"512G SSD"}', 5799.0, 185, 0),
        ('PROD_002', 'SKU_002_A', 'MB-XP-I9-32-1T',   '{"处理器":"i9-13900H","内存":"32G","硬盘":"1T SSD"}',  9999.0, 200, 1),
        ('PROD_002', 'SKU_002_B', 'MB-XP-I7-16-512',  '{"处理器":"i7-13700H","内存":"16G","硬盘":"512G"}',   7999.0, 120, 0),
        ('PROD_003', 'SKU_003_A', 'IP15PM-256-TIT',   '{"容量":"256G","颜色":"深空钛色"}',                    9499.0, 600, 1),
        ('PROD_003', 'SKU_003_B', 'IP15PM-512-TIT',   '{"容量":"512G","颜色":"深空钛色"}',                   10499.0, 600, 0),
        ('PROD_004', 'SKU_004_A', 'RN13P-256-BLK',    '{"容量":"256G","颜色":"子夜黑"}',                      1599.0, 3000, 1),
        ('PROD_004', 'SKU_004_B', 'RN13P-512-WHT',    '{"容量":"512G","颜色":"冰羽白"}',                      1799.0, 2000, 0),
        ('PROD_005', 'SKU_005_A', 'KFR35-L3-WHITE',   '{"颜色":"白色","能效等级":"三级"}',                    2299.0, 500, 1),
        ('PROD_005', 'SKU_005_B', 'KFR35-L1-WHITE',   '{"颜色":"白色","能效等级":"一级"}',                    2699.0, 300, 0),
        ('PROD_006', 'SKU_006_A', 'BCD470-SILVER',    '{"颜色":"银色","容量":"470L"}',                        3299.0, 400, 1),
        ('PROD_006', 'SKU_006_B', 'BCD470-BLACK',     '{"颜色":"黑色","容量":"470L"}',                        3399.0, 250, 0),
        ('PROD_007', 'SKU_007_A', 'S7-1214C-AC',      '{"型号":"CPU1214C","供电":"AC/DC/RLY"}',               4200.0, 120, 1),
        ('PROD_007', 'SKU_007_B', 'S7-1214C-DC',      '{"型号":"CPU1214C","供电":"DC/DC/DC"}',                4500.0,  80, 0),
        ('PROD_008', 'SKU_008_A', 'SS304-2MM-1X2',    '{"厚度":"2mm","尺寸":"1000×2000mm","数量":"1张"}',      85.0, 30000, 1),
        ('PROD_008', 'SKU_008_B', 'SS304-3MM-1X2',    '{"厚度":"3mm","尺寸":"1000×2000mm","数量":"1张"}',     118.0, 20000, 0),
    ]
    for (pid, sid, code, specs, price, stock, isdef) in skus:
        conn.execute(
            """INSERT OR REPLACE INTO t_product_sku
               (product_id, sku_id, sku_code, specs, price, stock, is_default, created_at)
               VALUES (?,?,?,?,?,?,?,?)
               ON CONFLICT(id) DO NOTHING""",
            (pid, sid, code, specs, price, stock, isdef, ts)
        )

    # Seed initial price history
    for p in products:
        pid, cprice, oprice = p[0], p[12], p[13]
        conn.execute(
            "INSERT INTO t_price_history (product_id, price, original_price, event_type, remark, recorded_at) "
            "VALUES (?,?,?,'initial','系统初始价格',?)",
            (pid, cprice, oprice, ts)
        )

    conn.commit()
    conn.close()


# ── Products: List / Search ───────────────────────────────────────────────────

@app.route('/internal/products', methods=['GET'])
def list_products():
    keyword   = request.args.get('keyword', '').strip()
    category  = request.args.get('category', '').strip()
    brand     = request.args.get('brand', '').strip()
    platform  = request.args.get('platform', '').strip()
    status    = request.args.get('status', 'on_sale').strip()
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
    sort      = request.args.get('sort', 'newest')
    page      = max(int(request.args.get('page', 0)), 0)
    size      = min(max(int(request.args.get('size', 20)), 1), 100)

    where, params = [], []
    if status:
        where.append('status = ?'); params.append(status)
    if keyword:
        where.append('(title LIKE ? OR subtitle LIKE ? OR brand_name LIKE ?)')
        params += [f'%{keyword}%', f'%{keyword}%', f'%{keyword}%']
    if category:
        where.append('(main_category = ? OR sub_category = ?)')
        params += [category, category]
    if brand:
        where.append('brand_name = ?'); params.append(brand)
    if platform:
        where.append('platform = ?'); params.append(platform)
    if min_price is not None:
        where.append('current_price >= ?'); params.append(min_price)
    if max_price is not None:
        where.append('current_price <= ?'); params.append(max_price)

    clause = ('WHERE ' + ' AND '.join(where)) if where else ''

    order_map = {
        'price_asc':  'current_price ASC',
        'price_desc': 'current_price DESC',
        'sales_desc': 'sold_quantity DESC',
        'score_desc': 'average_score DESC',
        'newest':     'created_at DESC',
    }
    order_by = order_map.get(sort, 'created_at DESC')

    conn = get_db()
    total = conn.execute(f'SELECT COUNT(*) FROM t_product {clause}', params).fetchone()[0]
    rows  = conn.execute(
        f'SELECT * FROM t_product {clause} ORDER BY {order_by} LIMIT ? OFFSET ?',
        params + [size, page * size]
    ).fetchall()
    conn.close()

    return resp(data={
        'total': total,
        'page':  page,
        'size':  size,
        'items': [_row_to_product(r) for r in rows],
    })


# ── Products: Detail ──────────────────────────────────────────────────────────

@app.route('/internal/products/<product_id>', methods=['GET'])
def get_product(product_id):
    conn = get_db()
    row = conn.execute('SELECT * FROM t_product WHERE id = ?', (product_id,)).fetchone()
    if not row:
        conn.close()
        return resp(404, 'Product not found'), 404
    product = _row_to_product(row)
    skus = conn.execute(
        'SELECT * FROM t_product_sku WHERE product_id = ? ORDER BY is_default DESC, id',
        (product_id,)
    ).fetchall()
    product['skus'] = [dict(s) for s in skus]
    conn.close()
    return resp(data=product)


# ── Products: Create ──────────────────────────────────────────────────────────

@app.route('/internal/products', methods=['POST'])
def create_product():
    body = request.get_json(force=True, silent=True) or {}
    if not body.get('title') or not body.get('platform') or not body.get('main_category'):
        return resp(400, 'title, platform, main_category are required'), 400
    if body.get('current_price') is None:
        return resp(400, 'current_price is required'), 400

    pid = body.get('id') or f'PROD_{uuid.uuid4().hex[:8].upper()}'
    ts  = now_str()
    conn = get_db()
    try:
        conn.execute(
            """INSERT INTO t_product
               (id, platform, platform_name, title, subtitle,
                main_category, sub_category, third_category,
                brand_id, brand_name, shop_id, shop_name,
                current_price, original_price, discount, currency,
                stock_quantity, available_quantity, sold_quantity, monthly_sales,
                average_score, positive_rate, total_reviews,
                main_image, status, is_imported, country,
                shipping_fee, can_return, extra_json, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (pid,
             body.get('platform'), body.get('platform_name', body.get('platform')),
             body['title'], body.get('subtitle'),
             body['main_category'], body.get('sub_category'), body.get('third_category'),
             body.get('brand_id'), body.get('brand_name'),
             body.get('shop_id'), body.get('shop_name'),
             float(body['current_price']),
             float(body['original_price']) if body.get('original_price') else None,
             float(body.get('discount', 1.0)),
             body.get('currency', 'CNY'),
             int(body.get('stock_quantity', 0)),
             int(body.get('available_quantity', 0)),
             int(body.get('sold_quantity', 0)),
             int(body.get('monthly_sales', 0)),
             float(body.get('average_score', 5.0)),
             float(body.get('positive_rate', 1.0)),
             int(body.get('total_reviews', 0)),
             body.get('main_image'),
             body.get('status', 'on_sale'),
             1 if body.get('is_imported') else 0,
             body.get('country', '中国'),
             float(body.get('shipping_fee', 0.0)),
             1 if body.get('can_return', True) else 0,
             json.dumps(body.get('extra_json')) if body.get('extra_json') else None,
             ts, ts)
        )
        # Record initial price history
        conn.execute(
            "INSERT INTO t_price_history (product_id, price, original_price, event_type, remark, recorded_at) "
            "VALUES (?,?,?,'initial','商品创建',?)",
            (pid, float(body['current_price']),
             float(body['original_price']) if body.get('original_price') else None, ts)
        )
        # Insert SKUs if provided
        for sku in body.get('skus', []):
            conn.execute(
                "INSERT INTO t_product_sku (product_id, sku_id, sku_code, specs, price, stock, is_default, created_at) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (pid,
                 sku.get('sku_id', f'SKU_{uuid.uuid4().hex[:6].upper()}'),
                 sku.get('sku_code'),
                 json.dumps(sku['specs']) if isinstance(sku.get('specs'), dict) else sku.get('specs'),
                 float(sku['price']),
                 int(sku.get('stock', 0)),
                 1 if sku.get('is_default') else 0,
                 ts)
            )
        conn.commit()
    except Exception as e:
        conn.close()
        return resp(500, str(e)), 500
    conn.close()
    return resp(data={'id': pid, 'title': body['title'], 'createdAt': ts}), 201


# ── Products: Update ──────────────────────────────────────────────────────────

@app.route('/internal/products/<product_id>', methods=['PUT'])
def update_product(product_id):
    body = request.get_json(force=True, silent=True) or {}
    if not body:
        return resp(400, 'request body required'), 400

    allowed = {
        'title', 'subtitle', 'main_category', 'sub_category', 'third_category',
        'brand_name', 'shop_name', 'original_price', 'discount', 'currency',
        'stock_quantity', 'available_quantity', 'monthly_sales',
        'average_score', 'positive_rate', 'total_reviews',
        'main_image', 'status', 'shipping_fee', 'can_return',
    }
    fields = {k: v for k, v in body.items() if k in allowed}
    if not fields:
        return resp(400, 'no updatable fields provided'), 400

    ts = now_str()
    fields['updated_at'] = ts
    set_clause = ', '.join(f'{k} = ?' for k in fields)
    values = list(fields.values()) + [product_id]

    conn = get_db()
    row = conn.execute('SELECT id FROM t_product WHERE id = ?', (product_id,)).fetchone()
    if not row:
        conn.close()
        return resp(404, 'Product not found'), 404
    conn.execute(f'UPDATE t_product SET {set_clause} WHERE id = ?', values)
    conn.commit()
    conn.close()
    return resp(data={'id': product_id, 'updatedAt': ts})


# ── Products: Soft Delete ─────────────────────────────────────────────────────

@app.route('/internal/products/<product_id>', methods=['DELETE'])
def delete_product(product_id):
    ts = now_str()
    conn = get_db()
    row = conn.execute('SELECT id FROM t_product WHERE id = ?', (product_id,)).fetchone()
    if not row:
        conn.close()
        return resp(404, 'Product not found'), 404
    conn.execute("UPDATE t_product SET status='deleted', updated_at=? WHERE id=?", (ts, product_id))
    conn.commit()
    conn.close()
    return resp(data={'id': product_id, 'status': 'deleted'})


# ── SKUs ──────────────────────────────────────────────────────────────────────

@app.route('/internal/products/<product_id>/skus', methods=['GET'])
def list_skus(product_id):
    conn = get_db()
    if not conn.execute('SELECT id FROM t_product WHERE id=?', (product_id,)).fetchone():
        conn.close()
        return resp(404, 'Product not found'), 404
    rows = conn.execute(
        'SELECT * FROM t_product_sku WHERE product_id=? ORDER BY is_default DESC, id',
        (product_id,)
    ).fetchall()
    conn.close()
    return resp(data={'productId': product_id, 'skus': [dict(r) for r in rows]})


@app.route('/internal/products/<product_id>/skus', methods=['POST'])
def add_sku(product_id):
    body = request.get_json(force=True, silent=True) or {}
    if body.get('price') is None:
        return resp(400, 'price is required'), 400
    conn = get_db()
    if not conn.execute('SELECT id FROM t_product WHERE id=?', (product_id,)).fetchone():
        conn.close()
        return resp(404, 'Product not found'), 404
    ts  = now_str()
    sid = body.get('sku_id') or f'SKU_{uuid.uuid4().hex[:6].upper()}'
    cur = conn.execute(
        "INSERT INTO t_product_sku (product_id, sku_id, sku_code, specs, price, stock, is_default, created_at) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (product_id, sid, body.get('sku_code'),
         json.dumps(body['specs']) if isinstance(body.get('specs'), dict) else body.get('specs'),
         float(body['price']), int(body.get('stock', 0)),
         1 if body.get('is_default') else 0, ts)
    )
    conn.commit()
    skuid = cur.lastrowid
    conn.close()
    return resp(data={'id': skuid, 'skuId': sid, 'productId': product_id}), 201


# ── Price History & Update ────────────────────────────────────────────────────

@app.route('/internal/products/<product_id>/price-history', methods=['GET'])
def price_history(product_id):
    limit = min(int(request.args.get('limit', 30)), 200)
    conn  = get_db()
    if not conn.execute('SELECT id FROM t_product WHERE id=?', (product_id,)).fetchone():
        conn.close()
        return resp(404, 'Product not found'), 404
    rows = conn.execute(
        'SELECT * FROM t_price_history WHERE product_id=? ORDER BY recorded_at DESC LIMIT ?',
        (product_id, limit)
    ).fetchall()
    conn.close()
    return resp(data={'productId': product_id, 'history': [dict(r) for r in rows]})


@app.route('/internal/products/<product_id>/price', methods=['POST'])
def update_price(product_id):
    body = request.get_json(force=True, silent=True) or {}
    new_price = body.get('price')
    if new_price is None:
        return resp(400, 'price is required'), 400
    new_price = float(new_price)
    ts = now_str()
    conn = get_db()
    if not conn.execute('SELECT id FROM t_product WHERE id=?', (product_id,)).fetchone():
        conn.close()
        return resp(404, 'Product not found'), 404
    conn.execute(
        'UPDATE t_product SET current_price=?, updated_at=? WHERE id=?',
        (new_price, ts, product_id)
    )
    conn.execute(
        "INSERT INTO t_price_history (product_id, price, original_price, event_type, remark, recorded_at) "
        "VALUES (?,?,?,?,?,?)",
        (product_id, new_price,
         float(body['original_price']) if body.get('original_price') else None,
         body.get('event_type', 'update'),
         body.get('remark'), ts)
    )
    _check_price_alerts(conn, product_id, new_price)
    conn.commit()
    conn.close()
    return resp(data={'productId': product_id, 'price': new_price, 'updatedAt': ts})


# ── Views & Popularity ────────────────────────────────────────────────────────

@app.route('/internal/products/<product_id>/view', methods=['POST'])
def record_view(product_id):
    body = request.get_json(force=True, silent=True) or {}
    conn = get_db()
    if not conn.execute("SELECT id FROM t_product WHERE id=? AND status!='deleted'",
                        (product_id,)).fetchone():
        conn.close()
        return resp(404, 'Product not found'), 404
    ts = now_str()
    conn.execute(
        "INSERT INTO t_product_view (product_id, user_id, session_id, source, viewed_at) VALUES (?,?,?,?,?)",
        (product_id, body.get('userId'), body.get('sessionId'),
         body.get('source', 'direct'), ts)
    )
    conn.commit()
    conn.close()
    return resp(data={'productId': product_id, 'viewedAt': ts})


@app.route('/internal/products/popular', methods=['GET'])
def popular_products():
    limit    = min(int(request.args.get('limit', 10)), 50)
    category = request.args.get('category', '').strip()
    conn     = get_db()
    if category:
        rows = conn.execute(
            """SELECT p.*, COUNT(v.id) AS view_count
               FROM t_product p
               LEFT JOIN t_product_view v ON v.product_id = p.id
               WHERE p.status='on_sale' AND p.main_category=?
               GROUP BY p.id
               ORDER BY view_count DESC, p.monthly_sales DESC
               LIMIT ?""",
            (category, limit)
        ).fetchall()
    else:
        rows = conn.execute(
            """SELECT p.*, COUNT(v.id) AS view_count
               FROM t_product p
               LEFT JOIN t_product_view v ON v.product_id = p.id
               WHERE p.status='on_sale'
               GROUP BY p.id
               ORDER BY view_count DESC, p.monthly_sales DESC
               LIMIT ?""",
            (limit,)
        ).fetchall()
    conn.close()
    items = []
    for r in rows:
        d = _row_to_product(r)
        d['viewCount'] = r['view_count'] if 'view_count' in r.keys() else 0
        items.append(d)
    return resp(data={'total': len(items), 'items': items})


# ── Recommendations ───────────────────────────────────────────────────────────

@app.route('/internal/products/<product_id>/recommendations', methods=['GET'])
def recommendations(product_id):
    limit = min(int(request.args.get('limit', 6)), 20)
    conn  = get_db()
    base  = conn.execute('SELECT * FROM t_product WHERE id=?', (product_id,)).fetchone()
    if not base:
        conn.close()
        return resp(404, 'Product not found'), 404

    # Same main_category, highest rated, exclude self
    rows = conn.execute(
        """SELECT * FROM t_product
           WHERE main_category=? AND id!=? AND status='on_sale'
           ORDER BY average_score DESC, sold_quantity DESC
           LIMIT ?""",
        (base['main_category'], product_id, limit)
    ).fetchall()

    # Pad with cross-category popular if not enough
    if len(rows) < limit:
        existing_ids = {product_id} | {r['id'] for r in rows}
        placeholders = ','.join('?' * len(existing_ids))
        extra = conn.execute(
            f"""SELECT * FROM t_product
                WHERE id NOT IN ({placeholders}) AND status='on_sale'
                ORDER BY average_score DESC LIMIT ?""",
            list(existing_ids) + [limit - len(rows)]
        ).fetchall()
        rows = list(rows) + list(extra)

    conn.close()
    return resp(data={
        'productId':     product_id,
        'basedOn':       base['main_category'],
        'total':         len(rows),
        'recommendations': [_row_to_product(r) for r in rows],
    })


# ── Comparison ────────────────────────────────────────────────────────────────

@app.route('/internal/products/compare', methods=['POST'])
def compare_products():
    body = request.get_json(force=True, silent=True) or {}
    ids  = body.get('productIds', [])
    if not isinstance(ids, list) or len(ids) < 2:
        return resp(400, 'productIds must be a list of at least 2 IDs'), 400
    if len(ids) > 5:
        return resp(400, 'Cannot compare more than 5 products at once'), 400

    conn = get_db()
    placeholders = ','.join('?' * len(ids))
    rows = conn.execute(
        f'SELECT * FROM t_product WHERE id IN ({placeholders})',
        ids
    ).fetchall()
    conn.close()

    if not rows:
        return resp(404, 'No products found'), 404

    products = [_row_to_product(r) for r in rows]
    prices   = [p['current_price'] for p in products]
    scores   = [p['average_score'] for p in products]
    sales    = [p['sold_quantity'] for p in products]

    best_price_idx  = prices.index(min(prices))
    best_score_idx  = scores.index(max(scores))
    best_sales_idx  = sales.index(max(sales))

    comparison = {
        'count':         len(products),
        'priceRange':    {'min': min(prices), 'max': max(prices)},
        'bestPrice':     {'productId': products[best_price_idx]['id'],
                          'title':     products[best_price_idx]['title'],
                          'price':     min(prices)},
        'bestRated':     {'productId': products[best_score_idx]['id'],
                          'title':     products[best_score_idx]['title'],
                          'score':     max(scores)},
        'bestSelling':   {'productId': products[best_sales_idx]['id'],
                          'title':     products[best_sales_idx]['title'],
                          'soldQty':   max(sales)},
        'attributes':    ['current_price', 'average_score', 'sold_quantity',
                          'brand_name', 'platform_name', 'stock_quantity'],
    }

    return resp(data={'products': products, 'comparison': comparison})


# ── Price Alerts ──────────────────────────────────────────────────────────────

@app.route('/internal/price-alerts', methods=['GET'])
def list_alerts():
    user_id = request.args.get('userId')
    conn    = get_db()
    if user_id:
        rows = conn.execute(
            "SELECT a.*, p.title, p.current_price FROM t_price_alert a "
            "LEFT JOIN t_product p ON p.id=a.product_id "
            "WHERE a.user_id=? ORDER BY a.id DESC",
            (user_id,)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT a.*, p.title, p.current_price FROM t_price_alert a "
            "LEFT JOIN t_product p ON p.id=a.product_id ORDER BY a.id DESC LIMIT 100"
        ).fetchall()
    conn.close()
    return resp(data={'total': len(rows), 'items': [dict(r) for r in rows]})


@app.route('/internal/price-alerts', methods=['POST'])
def create_alert():
    body = request.get_json(force=True, silent=True) or {}
    product_id   = body.get('productId')
    user_id      = body.get('userId')
    target_price = body.get('targetPrice')
    if not all([product_id, user_id, target_price is not None]):
        return resp(400, 'productId, userId, targetPrice are required'), 400

    ts = now_str()
    conn = get_db()
    if not conn.execute('SELECT id FROM t_product WHERE id=?', (product_id,)).fetchone():
        conn.close()
        return resp(404, 'Product not found'), 404
    cur = conn.execute(
        "INSERT INTO t_price_alert (product_id, user_id, target_price, status, created_at) VALUES (?,?,?,?,?)",
        (product_id, user_id, float(target_price), 'active', ts)
    )
    conn.commit()
    alert_id = cur.lastrowid
    conn.close()
    return resp(data={'id': alert_id, 'productId': product_id,
                      'userId': user_id, 'targetPrice': target_price,
                      'status': 'active', 'createdAt': ts}), 201


@app.route('/internal/price-alerts/<int:alert_id>/cancel', methods=['PUT'])
def cancel_alert(alert_id):
    ts = now_str()
    conn = get_db()
    row = conn.execute('SELECT id FROM t_price_alert WHERE id=?', (alert_id,)).fetchone()
    if not row:
        conn.close()
        return resp(404, 'Alert not found'), 404
    conn.execute("UPDATE t_price_alert SET status='cancelled' WHERE id=?", (alert_id,))
    conn.commit()
    conn.close()
    return resp(data={'id': alert_id, 'status': 'cancelled'})


# ── Categories ────────────────────────────────────────────────────────────────

@app.route('/internal/categories', methods=['GET'])
def list_categories():
    conn = get_db()
    rows = conn.execute(
        """SELECT main_category, COUNT(*) AS product_count
           FROM t_product WHERE status != 'deleted'
           GROUP BY main_category ORDER BY product_count DESC"""
    ).fetchall()
    conn.close()
    return resp(data={'total': len(rows), 'categories': [dict(r) for r in rows]})


# ── Health ────────────────────────────────────────────────────────────────────

@app.route('/health')
def health():
    conn = get_db()
    count = conn.execute("SELECT COUNT(*) FROM t_product WHERE status='on_sale'").fetchone()[0]
    conn.close()
    return jsonify({'status': 'UP', 'service': 'product-service', 'productsOnSale': count})


@app.errorhandler(404)
def not_found(e):
    return resp(404, '接口不存在'), 404


@app.errorhandler(500)
def internal_error(e):
    return resp(500, f'服务内部错误: {str(e)}'), 500


if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=PORT)
