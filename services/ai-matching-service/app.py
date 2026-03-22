import os
import sqlite3
import uuid
from datetime import datetime, timezone

import requests
from flask import Flask, jsonify, request

app = Flask(__name__)

DB_PATH = "/tmp/ilbuy_ai.db"
PORT = int(os.environ.get("AI_SERVICE_PORT", 8003))
PROCUREMENT_SERVICE_URL = os.environ.get("PROCUREMENT_SERVICE_URL", "http://localhost:8002")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS t_match_task (
            id TEXT PRIMARY KEY,
            demand_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            keyword TEXT,
            category TEXT,
            budget REAL,
            status TEXT DEFAULT 'PROCESSING',
            progress INTEGER DEFAULT 0,
            created_at TEXT,
            completed_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS t_match_result (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT NOT NULL,
            supplier_id INTEGER NOT NULL,
            supplier_name TEXT NOT NULL,
            match_score REAL NOT NULL,
            estimated_price REAL,
            delivery_days INTEGER,
            reason TEXT,
            rank_order INTEGER
        )
    """)
    conn.commit()
    conn.close()


def resp(code=0, message="success", data=None):
    return jsonify({"code": code, "message": message, "data": data})


def now_str():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@app.route("/internal/match", methods=["POST"])
def create_match():
    body = request.get_json(silent=True) or {}
    demand_id = body.get("demandId")
    user_id = body.get("userId")
    keyword = body.get("keyword", "")
    category = body.get("category", "")
    budget = float(body.get("budget") or 0)

    if not demand_id or not user_id:
        return resp(400, "demandId and userId are required"), 400

    task_id = str(uuid.uuid4())
    created_at = now_str()

    conn = get_db()
    conn.execute(
        "INSERT INTO t_match_task (id, demand_id, user_id, keyword, category, budget, status, progress, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, 'PROCESSING', 0, ?)",
        (task_id, demand_id, user_id, keyword, category, budget, created_at),
    )

    suppliers = [
        (1001, "优选供应商A", 0.95, budget * 0.85, 5, "综合评分最高，历史成交稳定", 1),
        (1002, "优选供应商B", 0.88, budget * 0.90, 7, "价格优惠，按时交付率98%", 2),
        (1003, "优选供应商C", 0.82, budget * 0.95, 10, "资质齐全，支持定制", 3),
    ]
    for sup in suppliers:
        conn.execute(
            "INSERT INTO t_match_result (task_id, supplier_id, supplier_name, match_score, estimated_price, "
            "delivery_days, reason, rank_order) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (task_id,) + sup,
        )

    completed_at = now_str()
    conn.execute(
        "UPDATE t_match_task SET status='COMPLETED', progress=100, completed_at=? WHERE id=?",
        (completed_at, task_id),
    )
    conn.commit()
    conn.close()

    try:
        requests.put(
            f"{PROCUREMENT_SERVICE_URL}/internal/demands/{demand_id}/status",
            json={"status": "MATCHING", "aiTaskId": task_id},
            timeout=2,
        )
    except Exception:
        pass

    return resp(0, "success", {"taskId": task_id, "status": "COMPLETED", "resultCount": 3})


@app.route("/internal/match/<task_id>/status", methods=["GET"])
def get_task_status(task_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM t_match_task WHERE id=?", (task_id,)).fetchone()
    conn.close()
    if not row:
        return resp(404, "task not found"), 404
    return resp(0, "success", {
        "taskId": row["id"],
        "demandId": row["demand_id"],
        "status": row["status"],
        "progress": row["progress"],
        "createdAt": row["created_at"],
        "completedAt": row["completed_at"],
    })


@app.route("/internal/match/<task_id>/result", methods=["GET"])
def get_task_result(task_id):
    conn = get_db()
    task = conn.execute("SELECT * FROM t_match_task WHERE id=?", (task_id,)).fetchone()
    if not task:
        conn.close()
        return resp(404, "task not found"), 404
    if task["status"] == "PROCESSING":
        conn.close()
        return resp(202, "task still processing", {"taskId": task_id, "status": "PROCESSING"}), 202
    rows = conn.execute(
        "SELECT * FROM t_match_result WHERE task_id=? ORDER BY rank_order ASC", (task_id,)
    ).fetchall()
    conn.close()
    suppliers = [
        {
            "supplierId": r["supplier_id"],
            "supplierName": r["supplier_name"],
            "matchScore": r["match_score"],
            "estimatedPrice": r["estimated_price"],
            "deliveryDays": r["delivery_days"],
            "reason": r["reason"],
            "rank": r["rank_order"],
        }
        for r in rows
    ]
    return resp(0, "success", {
        "taskId": task_id,
        "status": task["status"],
        "demand": {
            "demandId": task["demand_id"],
            "keyword": task["keyword"],
            "category": task["category"],
        },
        "suppliers": suppliers,
    })


@app.route("/internal/suppliers/recommend", methods=["GET"])
def recommend_suppliers():
    keyword = request.args.get("keyword", "")
    category = request.args.get("category", "")
    limit = int(request.args.get("limit", 3))
    prefix = keyword if keyword else category if category else "通用"
    mock_suppliers = [
        {"id": 2001, "name": f"{prefix}供应商甲", "matchScore": 0.93, "avgPrice": 8500.0, "deliveryDays": 5, "rating": 4.9},
        {"id": 2002, "name": f"{prefix}供应商乙", "matchScore": 0.87, "avgPrice": 7800.0, "deliveryDays": 7, "rating": 4.7},
        {"id": 2003, "name": f"{prefix}供应商丙", "matchScore": 0.80, "avgPrice": 7200.0, "deliveryDays": 10, "rating": 4.5},
    ]
    return resp(0, "success", {"total": len(mock_suppliers[:limit]), "suppliers": mock_suppliers[:limit]})


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "UP", "service": "ai-matching-service"})


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=PORT)
