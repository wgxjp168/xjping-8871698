import os
import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify

app = Flask(__name__)

DB_PATH = "/tmp/ilbuy_data.db"
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
    suppliers = [
        ("北京创新科技供应商", "91110108SUPPLY001", "张经理", "13800138001", "北京市海淀区", "IT设备/办公用品", "AAA", 4.8),
        ("上海精密制造供应商", "91310101SUPPLY002", "李总监", "13800138002", "上海市浦东新区", "精密零件/机械设备", "AA", 4.6),
        ("广州综合贸易供应商", "91440101SUPPLY003", "陈主任", "13800138003", "广州市天河区", "电子元件/通用物资", "A", 4.4),
    ]
    c.executemany(
        "INSERT OR IGNORE INTO t_supplier "
        "(company_name, credit_code, contact_person, contact_phone, address, business_scope, qualification_level, rating, registered_at) "
        "VALUES (?,?,?,?,?,?,?,?,?)",
        [s + (now,) for s in suppliers],
    )

    prices = [
        ("办公用品", "钢笔套装", 89.00, 65.00, 120.00, "套"),
        ("IT设备", "笔记本电脑", 6500.00, 4500.00, 9800.00, "台"),
        ("IT设备", "显示器", 1200.00, 800.00, 2500.00, "台"),
        ("机械设备", "液压阀", 450.00, 280.00, 680.00, "件"),
        ("电子元件", "电阻套装", 35.00, 18.00, 55.00, "包"),
        ("办公用品", "打印机", 2200.00, 1500.00, 3500.00, "台"),
    ]
    c.executemany(
        "INSERT OR IGNORE INTO t_market_price "
        "(category, product_name, avg_price, min_price, max_price, unit, updated_at) "
        "VALUES (?,?,?,?,?,?,?)",
        [p + (now,) for p in prices],
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
        f"SELECT id, company_name, contact_person, qualification_level, rating, status "
        f"FROM t_supplier {clause} LIMIT ? OFFSET ?",
        params + [size, page * size],
    ).fetchall()
    conn.close()

    items = [{"id": r["id"], "companyName": r["company_name"], "contactPerson": r["contact_person"],
              "qualificationLevel": r["qualification_level"], "rating": r["rating"],
              "status": r["status"]} for r in rows]
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


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=PORT)
