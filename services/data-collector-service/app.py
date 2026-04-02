import os
import sqlite3
import tempfile
from datetime import datetime
from flask import Flask, request, jsonify

app = Flask(__name__)

DB_PATH = os.environ.get('DB_PATH', os.path.join(tempfile.gettempdir(), 'ilbuy_data.db'))
PORT = int(os.environ.get("DATA_SERVICE_PORT", 8005))


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def resp(code=0, message="ok", data=None):
    return jsonify({"code": code, "message": message, "data": data})


def init_db():
    conn = get_db()
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS t_supplier (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT UNIQUE NOT NULL,
            credit_code TEXT UNIQUE NOT NULL,
            contact_person TEXT,
            contact_phone TEXT,
            address TEXT,
            business_scope TEXT,
            qualification_level TEXT DEFAULT 'A',
            rating REAL DEFAULT 4.5,
            status TEXT DEFAULT 'ACTIVE',
            registered_at TEXT
        );

        CREATE TABLE IF NOT EXISTS t_market_price (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            product_name TEXT NOT NULL,
            avg_price REAL NOT NULL,
            min_price REAL NOT NULL,
            max_price REAL NOT NULL,
            unit TEXT DEFAULT '件',
            data_source TEXT DEFAULT 'CRAWLER',
            updated_at TEXT
        );
    """)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # Use INSERT OR REPLACE with explicit IDs so seed always wins over stale data
    suppliers = [
        (1,  "北京创新科技供应链有限公司",   "91110108SUPPLY001", "张经理", "13800138001", "北京市海淀区中关村南大街5号", "IT设备/服务器/网络设备", "AAA", 4.8),
        (2,  "上海精密制造装备集团",         "91310101SUPPLY002", "李总监", "13800138002", "上海市浦东新区张江高科技园", "精密零件/机械设备/仪器", "AA",  4.6),
        (3,  "广州综合贸易供应商有限公司",   "91440101SUPPLY003", "陈主任", "13800138003", "广州市天河区珠江新城花城广场", "电子元件/通用物资/包装材料", "A", 4.4),
        (4,  "深圳华信电子科技有限公司",     "91440300SUPPLY004", "王总",   "13800138004", "深圳市南山区科技园北区", "IT设备/电子元件/芯片模块",  "AAA", 4.9),
        (5,  "成都西部工业供应链公司",       "91510100SUPPLY005", "刘经理", "13800138005", "成都市高新区天府大道北段", "工业设备/机床/电机/液压", "AA",  4.5),
        (6,  "天津滨海物资采购中心",         "91120116SUPPLY006", "赵总",   "13800138006", "天津市滨海新区经济技术开发区", "原材料/钢材/铝材/铜材", "AA",  4.3),
        (7,  "杭州数字化供应链科技有限公司", "91330108SUPPLY007", "孙总监", "13800138007", "杭州市余杭区未来科技城海创园", "IT设备/软硬件/SaaS服务", "AAA", 4.7),
        (8,  "武汉中南工业物资有限公司",     "91420100SUPPLY008", "周经理", "13800138008", "武汉市武汉经济技术开发区沌阳", "工业物资/耗材/备件/配件", "A",  4.2),
        (9,  "苏州精工机械配件供应商",       "91320508SUPPLY009", "吴经理", "13800138009", "苏州市工业园区苏绣路18号", "精密机械/液压件/传感器/阀门", "AA", 4.6),
        (10, "重庆西南建材物资供应链",       "91500100SUPPLY010", "郑总",   "13800138010", "重庆市渝北区两江新区龙盛片区", "建材/办公家具/工程材料", "A", 4.1),
    ]
    for s in suppliers:
        c.execute(
            "INSERT OR REPLACE INTO t_supplier "
            "(id, company_name, credit_code, contact_person, contact_phone, address, business_scope, qualification_level, rating, registered_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            s + (now,),
        )

    prices = [
        (1,  "IT设备",   "商务笔记本电脑（i7/16G/512G）",  6800.0,  4500.0,  9800.0,  "台"),
        (2,  "IT设备",   "高性能台式机（i9/32G/1T）",      8500.0,  6000.0, 12000.0,  "台"),
        (3,  "IT设备",   "企业级服务器（Dell PowerEdge）", 38000.0, 28000.0, 65000.0, "台"),
        (4,  "IT设备",   "彩色激光打印机（A4）",            2800.0,  1500.0,  4500.0,  "台"),
        (5,  "IT设备",   "液晶显示器（27寸4K）",            1800.0,   900.0,  3200.0,  "台"),
        (6,  "IT设备",   "企业级交换机（48口千兆）",        3500.0,  2000.0,  6000.0,  "台"),
        (7,  "办公用品", "A4复印纸（500张/包）",              38.0,    25.0,    55.0,  "包"),
        (8,  "办公用品", "人体工学办公椅",                    680.0,   380.0,  1200.0,  "把"),
        (9,  "办公用品", "钢制文件柜（四层）",                450.0,   280.0,   750.0,  "个"),
        (10, "办公用品", "会议室白板（120×180cm）",           320.0,   180.0,   580.0,  "块"),
        (11, "工业设备", "数控机床（三轴CNC）",             85000.0, 60000.0,130000.0,  "台"),
        (12, "工业设备", "工业电动机（30kW）",               4500.0,  3000.0,  7500.0,  "台"),
        (13, "工业设备", "液压泵站（中压型）",              12000.0,  8000.0, 20000.0,  "套"),
        (14, "原材料",   "不锈钢板（304# 2mm）",               35.0,    22.0,    52.0,  "kg"),
        (15, "原材料",   "铝合金型材（6063-T5）",              28.0,    18.0,    42.0,  "kg"),
        (16, "电子元件", "工业级继电器模块",                    18.0,     8.0,    32.0,  "个"),
        (17, "电子元件", "ARM 32位MCU微控制器",                 25.0,    12.0,    45.0,  "片"),
    ]
    for p in prices:
        c.execute(
            "INSERT OR REPLACE INTO t_market_price "
            "(id, category, product_name, avg_price, min_price, max_price, unit, updated_at) "
            "VALUES (?,?,?,?,?,?,?,?)",
            p + (now,),
        )

    conn.commit()
    conn.close()


# ── Supplier endpoints ────────────────────────────────────────────────────────

@app.post("/internal/suppliers")
@app.post("/internal/suppliers/register")
def register_supplier():
    body = request.get_json(force=True) or {}
    company_name = body.get("companyName", "").strip()
    credit_code = body.get("creditCode", "").strip()
    if not company_name or not credit_code:
        return resp(400, "companyName and creditCode are required"), 400

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO t_supplier (company_name, credit_code, contact_person, contact_phone, "
            "address, business_scope, qualification_level, registered_at) VALUES (?,?,?,?,?,?,?,?)",
            (company_name, credit_code, body.get("contactPerson"), body.get("contactPhone"),
             body.get("address"), body.get("businessScope"),
             body.get("qualificationLevel", "A"), now),
        )
        conn.commit()
        row = conn.execute("SELECT id FROM t_supplier WHERE company_name=?", (company_name,)).fetchone()
        return resp(0, "ok", {"id": row["id"], "companyName": company_name,
                              "creditCode": credit_code, "status": "ACTIVE"})
    except sqlite3.IntegrityError:
        return resp(409, "supplier already exists"), 409
    finally:
        conn.close()


@app.get("/internal/suppliers")
def list_suppliers():
    keyword = request.args.get("keyword", "").strip()
    status = request.args.get("status", "").strip()
    page = max(int(request.args.get("page", 0)), 0)
    size = max(int(request.args.get("size", 10)), 1)

    where, params = [], []
    if keyword:
        where.append("(company_name LIKE ? OR business_scope LIKE ?)")
        params += [f"%{keyword}%", f"%{keyword}%"]
    if status:
        where.append("status = ?")
        params.append(status)

    clause = ("WHERE " + " AND ".join(where)) if where else ""
    conn = get_db()
    total = conn.execute(f"SELECT COUNT(*) FROM t_supplier {clause}", params).fetchone()[0]
    rows = conn.execute(
        f"SELECT id, company_name, credit_code, contact_person, contact_phone, "
        f"address, business_scope, qualification_level, rating, status "
        f"FROM t_supplier {clause} LIMIT ? OFFSET ?",
        params + [size, page * size],
    ).fetchall()
    conn.close()

    items = [{
        "id": r["id"],
        "companyName": r["company_name"],
        "creditCode": r["credit_code"],
        "contactPerson": r["contact_person"],
        "contactPhone": r["contact_phone"],
        "address": r["address"],
        "mainCategory": r["business_scope"],
        "qualificationLevel": r["qualification_level"],
        "rating": r["rating"],
        "status": r["status"],
    } for r in rows]
    return resp(0, "ok", {"total": total, "items": items})


@app.get("/internal/suppliers/<int:supplier_id>")
def get_supplier(supplier_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM t_supplier WHERE id=?", (supplier_id,)).fetchone()
    conn.close()
    if not row:
        return resp(404, "supplier not found"), 404
    data = {
        "id": row["id"], "companyName": row["company_name"], "creditCode": row["credit_code"],
        "contactPerson": row["contact_person"], "contactPhone": row["contact_phone"],
        "address": row["address"], "businessScope": row["business_scope"],
        "qualificationLevel": row["qualification_level"], "rating": row["rating"],
        "status": row["status"], "registeredAt": row["registered_at"],
    }
    return resp(0, "ok", data)


# ── Market price endpoints ────────────────────────────────────────────────────

@app.get("/internal/market/prices")
def list_prices():
    category = request.args.get("category", "").strip()
    keyword = request.args.get("keyword", "").strip()

    where, params = [], []
    if category:
        where.append("category = ?")
        params.append(category)
    if keyword:
        where.append("product_name LIKE ?")
        params.append(f"%{keyword}%")

    clause = ("WHERE " + " AND ".join(where)) if where else ""
    conn = get_db()
    total = conn.execute(f"SELECT COUNT(*) FROM t_market_price {clause}", params).fetchone()[0]
    rows = conn.execute(
        f"SELECT id, category, product_name, avg_price, min_price, max_price, unit, updated_at "
        f"FROM t_market_price {clause}",
        params,
    ).fetchall()
    conn.close()

    items = [{"id": r["id"], "category": r["category"], "productName": r["product_name"],
              "avgPrice": r["avg_price"], "minPrice": r["min_price"], "maxPrice": r["max_price"],
              "unit": r["unit"], "updatedAt": r["updated_at"]} for r in rows]
    return resp(0, "ok", {"total": total, "items": items})


@app.get("/internal/market/prices/<int:price_id>")
def get_price(price_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM t_market_price WHERE id=?", (price_id,)).fetchone()
    conn.close()
    if not row:
        return resp(404, "price record not found"), 404
    data = {
        "id": row["id"], "category": row["category"], "productName": row["product_name"],
        "avgPrice": row["avg_price"], "minPrice": row["min_price"], "maxPrice": row["max_price"],
        "unit": row["unit"], "dataSource": row["data_source"], "updatedAt": row["updated_at"],
    }
    return resp(0, "ok", data)


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return jsonify({"status": "UP", "service": "data-collector-service"})


@app.errorhandler(404)
def not_found(e):
    return resp(404, "接口不存在"), 404

@app.errorhandler(500)
def internal_error(e):
    return resp(500, f"服务内部错误: {str(e)}"), 500

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=PORT)
