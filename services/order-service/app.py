import os
import random
import sqlite3
import tempfile
from datetime import datetime, timezone
from flask import Flask, request, jsonify

app = Flask(__name__)
DB_PATH = os.environ.get('DB_PATH', os.path.join(tempfile.gettempdir(), 'ilbuy_order.db'))
PORT = int(os.environ.get("ORDER_SERVICE_PORT", 8004))


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS t_order (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_no TEXT UNIQUE NOT NULL,
            demand_id INTEGER NOT NULL,
            quote_id INTEGER NOT NULL,
            buyer_id INTEGER NOT NULL,
            supplier_id INTEGER NOT NULL,
            supplier_name TEXT,
            product_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price REAL NOT NULL,
            total_amount REAL NOT NULL,
            delivery_days INTEGER DEFAULT 7,
            payment_method TEXT DEFAULT 'BANK_TRANSFER',
            payment_status TEXT DEFAULT 'UNPAID',
            order_status TEXT DEFAULT 'CREATED',
            paid_at TEXT,
            shipped_at TEXT,
            delivered_at TEXT,
            completed_at TEXT,
            remark TEXT,
            created_at TEXT,
            updated_at TEXT
        )
    """)
    conn.commit()
    conn.close()


def resp(code=0, message="ok", data=None):
    return jsonify({"code": code, "message": message, "data": data})


def now_str():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def gen_order_no():
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    digits = f"{random.randint(0, 9999):04d}"
    return f"ILB{ts}{digits}"


@app.route("/health")
def health():
    return jsonify({"status": "UP", "service": "order-service"})


@app.route("/internal/orders", methods=["POST"])
def create_order():
    body = request.get_json(force=True, silent=True) or {}
    now = now_str()
    order_no = gen_order_no()
    conn = get_db()
    cur = conn.execute(
        """INSERT INTO t_order
           (order_no, demand_id, quote_id, buyer_id, supplier_id, supplier_name,
            product_name, quantity, unit_price, total_amount, delivery_days,
            payment_method, remark, created_at, updated_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            order_no, body.get("demandId"), body.get("quoteId"),
            body.get("buyerId"), body.get("supplierId"), body.get("supplierName"),
            body.get("productName"), body.get("quantity"), body.get("unitPrice"),
            body.get("totalAmount"), body.get("deliveryDays", 7),
            body.get("paymentMethod", "BANK_TRANSFER"), body.get("remark"),
            now, now,
        ),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM t_order WHERE id=?", (cur.lastrowid,)).fetchone()
    conn.close()
    return resp(data={
        "id": row["id"], "orderNo": row["order_no"], "demandId": row["demand_id"],
        "quoteId": row["quote_id"], "totalAmount": row["total_amount"],
        "orderStatus": row["order_status"], "paymentStatus": row["payment_status"],
        "createdAt": row["created_at"],
    })


@app.route("/internal/orders", methods=["GET"])
def list_orders():
    buyer_id = request.args.get("buyerId")
    supplier_id = request.args.get("supplierId")
    status = request.args.get("status")
    page = int(request.args.get("page", 0))
    size = int(request.args.get("size", 10))
    where, params = [], []
    if buyer_id:
        where.append("buyer_id=?"); params.append(buyer_id)
    if supplier_id:
        where.append("supplier_id=?"); params.append(supplier_id)
    if status:
        where.append("order_status=?"); params.append(status)
    clause = ("WHERE " + " AND ".join(where)) if where else ""
    conn = get_db()
    total = conn.execute(f"SELECT COUNT(*) FROM t_order {clause}", params).fetchone()[0]
    rows = conn.execute(
        f"SELECT * FROM t_order {clause} ORDER BY id DESC LIMIT ? OFFSET ?",
        params + [size, page * size],
    ).fetchall()
    conn.close()
    items = [
        {"id": r["id"], "orderNo": r["order_no"], "productName": r["product_name"],
         "totalAmount": r["total_amount"], "orderStatus": r["order_status"],
         "paymentStatus": r["payment_status"], "createdAt": r["created_at"]}
        for r in rows
    ]
    return resp(data={"total": total, "items": items})


@app.route("/internal/orders/<int:order_id>", methods=["GET"])
def get_order(order_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM t_order WHERE id=?", (order_id,)).fetchone()
    conn.close()
    if not row:
        return resp(code=404, message="Order not found"), 404
    return resp(data=dict(row))


@app.route("/internal/orders/<int:order_id>/pay", methods=["PUT"])
def pay_order(order_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM t_order WHERE id=?", (order_id,)).fetchone()
    if not row:
        conn.close(); return resp(code=404, message="Order not found"), 404
    if row["payment_status"] == "PAID":
        conn.close(); return resp(code=400, message="Order already paid"), 400
    body = request.get_json(force=True, silent=True) or {}
    now = now_str()
    payment_method = body.get("paymentMethod", row["payment_method"])
    conn.execute(
        "UPDATE t_order SET payment_status='PAID', order_status='PAID', paid_at=?, payment_method=?, updated_at=? WHERE id=?",
        (now, payment_method, now, order_id),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM t_order WHERE id=?", (order_id,)).fetchone()
    conn.close()
    return resp(data={"id": row["id"], "orderNo": row["order_no"],
                      "paymentStatus": row["payment_status"],
                      "orderStatus": row["order_status"], "paidAt": row["paid_at"]})


@app.route("/internal/orders/<int:order_id>/ship", methods=["PUT"])
def ship_order(order_id):
    now = now_str()
    conn = get_db()
    row = conn.execute("SELECT * FROM t_order WHERE id=?", (order_id,)).fetchone()
    if not row:
        conn.close(); return resp(code=404, message="Order not found"), 404
    conn.execute(
        "UPDATE t_order SET order_status='SHIPPED', shipped_at=?, updated_at=? WHERE id=?",
        (now, now, order_id),
    )
    conn.commit()
    conn.close()
    return resp(data={"id": order_id, "orderNo": row["order_no"], "orderStatus": "SHIPPED"})


@app.route("/internal/orders/<int:order_id>/confirm-receipt", methods=["PUT"])
def confirm_receipt(order_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM t_order WHERE id=?", (order_id,)).fetchone()
    if not row:
        conn.close(); return resp(code=404, message="Order not found"), 404
    if row["order_status"] not in ("SHIPPED", "PAID"):
        conn.close(); return resp(code=400, message="Order must be SHIPPED or PAID to confirm receipt"), 400
    now = now_str()
    conn.execute(
        "UPDATE t_order SET order_status='COMPLETED', delivered_at=?, completed_at=?, updated_at=? WHERE id=?",
        (now, now, now, order_id),
    )
    conn.commit()
    conn.close()
    return resp(data={"id": order_id, "orderNo": row["order_no"],
                      "orderStatus": "COMPLETED", "completedAt": now})


@app.route("/internal/orders/<int:order_id>/cancel", methods=["PUT"])
def cancel_order(order_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM t_order WHERE id=?", (order_id,)).fetchone()
    if not row:
        conn.close(); return resp(code=404, message="Order not found"), 404
    if row["order_status"] in ("COMPLETED", "SHIPPED"):
        conn.close(); return resp(code=400, message=f"Cannot cancel order in status {row['order_status']}"), 400
    now = now_str()
    conn.execute(
        "UPDATE t_order SET order_status='CANCELLED', updated_at=? WHERE id=?",
        (now, order_id),
    )
    conn.commit()
    conn.close()
    return resp(data={"id": order_id, "orderNo": row["order_no"], "orderStatus": "CANCELLED"})


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=PORT)
