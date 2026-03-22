import os
import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify

app = Flask(__name__)

DB_PATH = "/tmp/ilbuy_procurement.db"
PORT = int(os.environ.get("PROCUREMENT_SERVICE_PORT", 8002))


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def now():
    return datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')


def resp(code=0, message="ok", data=None):
    return jsonify({"code": code, "message": message, "data": data})


def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS t_demand (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            unit TEXT DEFAULT '件',
            budget REAL,
            description TEXT,
            status TEXT DEFAULT 'PENDING',
            ai_task_id TEXT,
            created_at TEXT,
            updated_at TEXT
        );
        CREATE TABLE IF NOT EXISTS t_quote (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            demand_id INTEGER NOT NULL,
            supplier_id INTEGER NOT NULL,
            supplier_name TEXT,
            unit_price REAL NOT NULL,
            total_price REAL NOT NULL,
            delivery_days INTEGER DEFAULT 7,
            warranty_months INTEGER DEFAULT 12,
            status TEXT DEFAULT 'PENDING',
            remark TEXT,
            created_at TEXT
        );
    """)
    conn.commit()
    conn.close()


# ── Demands ──────────────────────────────────────────────────────────────────

@app.route("/internal/demands", methods=["POST"])
def create_demand():
    body = request.get_json() or {}
    user_id = body.get("userId")
    title = body.get("title")
    category = body.get("category")
    quantity = body.get("quantity")
    if not all([user_id, title, category, quantity]):
        return resp(400, "userId, title, category, quantity are required"), 400
    unit = body.get("unit", "件")
    budget = body.get("budget")
    description = body.get("description")
    ts = now()
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO t_demand (user_id, title, category, quantity, unit, budget, description, status, created_at, updated_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, 'PENDING', ?, ?)",
        (user_id, title, category, quantity, unit, budget, description, ts, ts),
    )
    conn.commit()
    row_id = cur.lastrowid
    conn.close()
    return resp(0, "ok", {"id": row_id, "title": title, "category": category,
                           "quantity": quantity, "status": "PENDING", "createdAt": ts})


@app.route("/internal/demands", methods=["GET"])
def list_demands():
    user_id = request.args.get("userId")
    status = request.args.get("status")
    page = int(request.args.get("page", 0))
    size = int(request.args.get("size", 10))
    offset = page * size

    where, params = [], []
    if user_id:
        where.append("user_id = ?")
        params.append(user_id)
    if status:
        where.append("status = ?")
        params.append(status)
    clause = ("WHERE " + " AND ".join(where)) if where else ""

    conn = get_db()
    total = conn.execute(f"SELECT COUNT(*) FROM t_demand {clause}", params).fetchone()[0]
    rows = conn.execute(
        f"SELECT * FROM t_demand {clause} ORDER BY id DESC LIMIT ? OFFSET ?",
        params + [size, offset],
    ).fetchall()
    conn.close()
    items = [dict(r) for r in rows]
    return resp(0, "ok", {"total": total, "items": items})


@app.route("/internal/demands/<int:demand_id>", methods=["GET"])
def get_demand(demand_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM t_demand WHERE id = ?", (demand_id,)).fetchone()
    conn.close()
    if not row:
        return resp(404, "demand not found"), 404
    return resp(0, "ok", dict(row))


@app.route("/internal/demands/<int:demand_id>/status", methods=["PUT"])
def update_demand_status(demand_id):
    body = request.get_json() or {}
    status = body.get("status")
    if not status:
        return resp(400, "status is required"), 400
    ai_task_id = body.get("aiTaskId")
    ts = now()
    conn = get_db()
    if ai_task_id is not None:
        conn.execute(
            "UPDATE t_demand SET status = ?, ai_task_id = ?, updated_at = ? WHERE id = ?",
            (status, ai_task_id, ts, demand_id),
        )
    else:
        conn.execute(
            "UPDATE t_demand SET status = ?, updated_at = ? WHERE id = ?",
            (status, ts, demand_id),
        )
    conn.commit()
    conn.close()
    return resp(0, "ok", {"id": demand_id, "status": status})


# ── Quotes ────────────────────────────────────────────────────────────────────

@app.route("/internal/quotes", methods=["POST"])
def create_quote():
    body = request.get_json() or {}
    demand_id = body.get("demandId")
    supplier_id = body.get("supplierId")
    unit_price = body.get("unitPrice")
    total_price = body.get("totalPrice")
    if not all([demand_id, supplier_id, unit_price is not None, total_price is not None]):
        return resp(400, "demandId, supplierId, unitPrice, totalPrice are required"), 400
    supplier_name = body.get("supplierName")
    delivery_days = body.get("deliveryDays", 7)
    warranty_months = body.get("warrantyMonths", 12)
    remark = body.get("remark")
    ts = now()
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO t_quote (demand_id, supplier_id, supplier_name, unit_price, total_price,"
        " delivery_days, warranty_months, remark, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (demand_id, supplier_id, supplier_name, unit_price, total_price,
         delivery_days, warranty_months, remark, ts),
    )
    conn.commit()
    row_id = cur.lastrowid
    conn.close()
    return resp(0, "ok", {"id": row_id, "demandId": demand_id, "supplierId": supplier_id,
                           "unitPrice": unit_price, "totalPrice": total_price})


@app.route("/internal/quotes", methods=["GET"])
def list_quotes():
    demand_id = request.args.get("demandId")
    supplier_id = request.args.get("supplierId")
    where, params = [], []
    if demand_id:
        where.append("demand_id = ?")
        params.append(demand_id)
    if supplier_id:
        where.append("supplier_id = ?")
        params.append(supplier_id)
    clause = ("WHERE " + " AND ".join(where)) if where else ""
    conn = get_db()
    total = conn.execute(f"SELECT COUNT(*) FROM t_quote {clause}", params).fetchone()[0]
    rows = conn.execute(f"SELECT * FROM t_quote {clause} ORDER BY id DESC", params).fetchall()
    conn.close()
    return resp(0, "ok", {"total": total, "items": [dict(r) for r in rows]})


@app.route("/internal/quotes/<int:quote_id>/accept", methods=["PUT"])
def accept_quote(quote_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM t_quote WHERE id = ?", (quote_id,)).fetchone()
    if not row:
        conn.close()
        return resp(404, "quote not found"), 404
    demand_id = row["demand_id"]
    conn.execute("UPDATE t_quote SET status = 'REJECTED' WHERE demand_id = ? AND id != ?",
                 (demand_id, quote_id))
    conn.execute("UPDATE t_quote SET status = 'ACCEPTED' WHERE id = ?", (quote_id,))
    conn.commit()
    conn.close()
    return resp(0, "ok", {"id": quote_id, "demandId": demand_id, "status": "ACCEPTED"})


# ── Health ────────────────────────────────────────────────────────────────────

@app.route("/health")
def health():
    return jsonify({"status": "UP", "service": "procurement-service"})


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=PORT)
