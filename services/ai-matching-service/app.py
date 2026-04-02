import os
import re
import sqlite3
import tempfile
import uuid
from datetime import datetime, timezone

import requests
from flask import Flask, jsonify, request

app = Flask(__name__)

DB_PATH = os.environ.get('DB_PATH', os.path.join(tempfile.gettempdir(), 'ilbuy_ai.db'))
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
            demand_type TEXT DEFAULT 'B2B',
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
            score_qualification INTEGER DEFAULT 0,
            score_credit INTEGER DEFAULT 0,
            score_price INTEGER DEFAULT 0,
            score_delivery INTEGER DEFAULT 0,
            score_service INTEGER DEFAULT 0,
            estimated_price REAL,
            delivery_days INTEGER,
            rating REAL DEFAULT 4.5,
            certifications TEXT DEFAULT '',
            established TEXT DEFAULT '',
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


# ── Intent Parsing ────────────────────────────────────────────────────────────

PRODUCT_MAP = {
    'IT设备':   ['笔记本', '电脑', '台式机', '服务器', '打印机', '投影仪', '显示器', '键盘', '鼠标', '路由器', '交换机', '防火墙'],
    '办公用品': ['桌椅', '文具', '纸张', '复印纸', '档案柜', '白板', '投影'],
    '工业设备': ['机床', '电机', '水泵', '阀门', '传感器', '仪器', '模具', '压缩机'],
    '原材料':   ['钢材', '铝材', '铜材', '塑料', '橡胶', '布料', '木材', '化工'],
    '电子元件': ['芯片', '电容', '电阻', '模块', '电路板', 'PCB', '继电器'],
    '医疗物资': ['口罩', '手套', '防护服', '消毒液', '医疗', '试剂'],
    '食品':     ['食品', '饮料', '茶叶', '咖啡', '零食', '调料'],
}
BRANDS = ['华为', 'HUAWEI', '联想', 'Lenovo', '苹果', 'Apple', '小米', 'OPPO', 'vivo',
          '三星', 'Samsung', 'HP', '惠普', 'Dell', '戴尔', 'IBM', '思科', 'Cisco',
          '海尔', '格力', '美的', '西门子', '施耐德']


@app.route("/internal/intent/parse", methods=["POST"])
def parse_intent():
    body = request.get_json(force=True) or {}
    text = body.get("text", "").strip()
    if not text:
        return resp(400, "text is required"), 400

    # Extract quantity
    qty_match = re.search(r'(\d+)\s*(?:台|个|件|套|只|箱|包|吨|千克|公斤|kg|升|L|米|平方米|m²)', text)
    quantity = int(qty_match.group(1)) if qty_match else 1

    # Extract budget
    budget = 0.0
    bm = re.search(r'(?:预算|约|大概|不超过|控制在|花费|花)?\s*(\d+(?:\.\d+)?)\s*(万元|万|千元|元)', text)
    if bm:
        budget = float(bm.group(1))
        if '万' in bm.group(2):
            budget *= 10000

    # Detect brand first
    detected_brand = next((b for b in BRANDS if b.lower() in text.lower()), None)
    brand_required = detected_brand is not None

    # Detect category and matched keyword
    category, matched_kw = '通用物资', None
    for cat, keywords in PRODUCT_MAP.items():
        for kw in keywords:
            if kw in text:
                category, matched_kw = cat, kw
                break
        else:
            continue
        break

    # Build a meaningful product name
    if matched_kw:
        if detected_brand:
            # e.g. "联想" + "笔记本" → "联想笔记本"
            product_name = detected_brand + matched_kw
        else:
            # Try to expand: grab up to 2 chars before the keyword for adjectives
            idx = text.find(matched_kw)
            prefix = re.sub(r'[\d，。、！？\s]', '', text[max(0, idx-4):idx])[-2:]
            product_name = prefix + matched_kw if prefix else matched_kw
    else:
        # No keyword match: strip stop-words and return core noun phrase
        clean = re.sub(r'采购|需要|购买|想买|要买|帮我|请问|我们?需要', '', text)
        clean = re.sub(r'\d+\s*(?:台|个|件|套|只|箱|包|吨|千克|公斤|kg|升|L|米)', '', clean)
        clean = re.sub(r'(?:预算|约|不超过|控制在)\s*\d+\s*(?:万元|万|千元|元)', '', clean)
        clean = re.sub(r'用于\S{1,6}', '', clean).strip('，。、 ')
        product_name = (detected_brand + clean[:8] if detected_brand else clean[:12]) or text[:12]

    demand_type = 'B2B' if (quantity >= 10 or budget >= 50000) else 'B2C'

    return resp(0, "success", {
        "productName":    product_name.strip(),
        "category":       category,
        "quantity":       quantity,
        "budgetAmount":   budget,
        "procurementType": demand_type,
        "brandRequired":  brand_required,
        "detectedBrand":  detected_brand,
        "description":    text,
        "confidence":     0.92,
    })


# ── AI Matching ───────────────────────────────────────────────────────────────

_SUPPLIER_POOL = [
    {"id": 1001, "name": "华信科技供应链",   "sq": 95, "sc": 92, "sp": 85, "sd": 98, "ss": 94,
     "factor": 0.85, "days": 5,  "rating": 4.9, "certs": "ISO9001,ISO14001,IATF16949", "est": "2008年",
     "reason": "综合评分最高，历史成交1200+单，按时交付率98%，获评年度优质供应商"},
    {"id": 1002, "name": "价优商贸集团",      "sq": 88, "sc": 90, "sp": 96, "sd": 85, "ss": 87,
     "factor": 0.90, "days": 7,  "rating": 4.7, "certs": "ISO9001,CE认证", "est": "2012年",
     "reason": "价格竞争力强，比市场均价低12%，适合大批量采购场景"},
    {"id": 1003, "name": "精诚专业供应商",    "sq": 91, "sc": 85, "sp": 80, "sd": 92, "ss": 90,
     "factor": 0.95, "days": 10, "rating": 4.6, "certs": "ISO9001,SGS认证,RoHS", "est": "2010年",
     "reason": "专业资质齐全，支持定制化生产，技术服务响应及时"},
    {"id": 1004, "name": "速达物流科技",      "sq": 82, "sc": 88, "sp": 78, "sd": 99, "ss": 85,
     "factor": 0.88, "days": 3,  "rating": 4.5, "certs": "ISO9001,AAA信用", "est": "2015年",
     "reason": "交货速度最快，自有仓库支持48小时急单发货"},
    {"id": 1005, "name": "信诚品质联盟",      "sq": 93, "sc": 94, "sp": 82, "sd": 88, "ss": 96,
     "factor": 0.92, "days": 8,  "rating": 4.8, "certs": "ISO9001,ISO14001,五星服务商", "est": "2006年",
     "reason": "客户满意度99.2%，提供全程品质追溯体系"},
]

# B2B scoring weights: qualification heavy, price moderate
_B2B_WEIGHTS = {"sq": 0.25, "sc": 0.20, "sp": 0.25, "sd": 0.20, "ss": 0.10}
# B2C weights: price and service heavy
_B2C_WEIGHTS = {"sq": 0.15, "sc": 0.15, "sp": 0.35, "sd": 0.15, "ss": 0.20}


def _calc_score(sup, weights):
    raw = (sup["sq"] * weights["sq"] + sup["sc"] * weights["sc"] +
           sup["sp"] * weights["sp"] + sup["sd"] * weights["sd"] +
           sup["ss"] * weights["ss"])
    return round(raw / 100, 4)


@app.route("/internal/match", methods=["POST"])
def create_match():
    body = request.get_json(silent=True) or {}
    demand_id = body.get("demandId")
    user_id   = body.get("userId")
    keyword   = body.get("keyword", "")
    category  = body.get("category", "")
    budget    = float(body.get("budget") or 0)
    demand_type = body.get("demandType", "B2B").upper()

    if not demand_id or not user_id:
        return resp(400, "demandId and userId are required"), 400

    task_id    = str(uuid.uuid4())
    created_at = now_str()
    weights    = _B2B_WEIGHTS if demand_type == "B2B" else _B2C_WEIGHTS

    scored = sorted(
        [{"sup": s, "score": _calc_score(s, weights)} for s in _SUPPLIER_POOL],
        key=lambda x: -x["score"]
    )[:3]

    conn = get_db()
    conn.execute(
        "INSERT INTO t_match_task (id, demand_id, user_id, keyword, category, budget, demand_type, status, progress, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, 'COMPLETED', 100, ?)",
        (task_id, demand_id, user_id, keyword, category, budget, demand_type, created_at),
    )
    for rank, item in enumerate(scored, 1):
        s = item["sup"]
        est_price = (budget / 1 if budget > 0 else 10000) * s["factor"] / max(1, int(body.get("quantity") or 1))
        conn.execute(
            "INSERT INTO t_match_result (task_id, supplier_id, supplier_name, match_score, "
            "score_qualification, score_credit, score_price, score_delivery, score_service, "
            "estimated_price, delivery_days, rating, certifications, established, reason, rank_order) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (task_id, s["id"], s["name"], item["score"],
             s["sq"], s["sc"], s["sp"], s["sd"], s["ss"],
             est_price, s["days"], s["rating"], s["certs"], s["est"], s["reason"], rank),
        )

    completed_at = now_str()
    conn.execute("UPDATE t_match_task SET completed_at=? WHERE id=?", (completed_at, task_id))
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

    return resp(0, "success", {"taskId": task_id, "status": "COMPLETED", "resultCount": len(scored)})


@app.route("/internal/match/<task_id>/status", methods=["GET"])
def get_task_status(task_id):
    conn = get_db()
    row  = conn.execute("SELECT * FROM t_match_task WHERE id=?", (task_id,)).fetchone()
    conn.close()
    if not row:
        return resp(404, "task not found"), 404
    return resp(0, "success", {
        "taskId": row["id"], "demandId": row["demand_id"],
        "status": row["status"], "progress": row["progress"],
        "createdAt": row["created_at"], "completedAt": row["completed_at"],
    })


@app.route("/internal/match/<task_id>/result", methods=["GET"])
def get_task_result(task_id):
    conn  = get_db()
    task  = conn.execute("SELECT * FROM t_match_task WHERE id=?", (task_id,)).fetchone()
    if not task:
        conn.close()
        return resp(404, "task not found"), 404
    if task["status"] == "PROCESSING":
        conn.close()
        return resp(202, "task still processing", {"taskId": task_id, "status": "PROCESSING"}), 202
    rows  = conn.execute(
        "SELECT * FROM t_match_result WHERE task_id=? ORDER BY rank_order ASC", (task_id,)
    ).fetchall()
    conn.close()

    suppliers = [{
        "supplierId":    r["supplier_id"],
        "supplierName":  r["supplier_name"],
        "matchScore":    r["match_score"],
        "scores": {
            "qualification": r["score_qualification"],
            "credit":        r["score_credit"],
            "price":         r["score_price"],
            "delivery":      r["score_delivery"],
            "service":       r["score_service"],
        },
        "estimatedPrice":  r["estimated_price"],
        "deliveryDays":    r["delivery_days"],
        "rating":          r["rating"],
        "certifications":  r["certifications"].split(",") if r["certifications"] else [],
        "established":     r["established"],
        "reason":          r["reason"],
        "rank":            r["rank_order"],
    } for r in rows]

    demand_type = task["demand_type"] or "B2B"
    weights = _B2B_WEIGHTS if demand_type == "B2B" else _B2C_WEIGHTS
    model_name = "B2B企业采购评分模型" if demand_type == "B2B" else "B2C消费者评分模型"
    weight_desc = {
        "资质评分": f"{int(weights['sq']*100)}%",
        "信用评分": f"{int(weights['sc']*100)}%",
        "价格竞争力": f"{int(weights['sp']*100)}%",
        "交货能力": f"{int(weights['sd']*100)}%",
        "服务评分": f"{int(weights['ss']*100)}%",
    }

    return resp(0, "success", {
        "taskId":   task_id,
        "status":   task["status"],
        "matchedSuppliers": suppliers,
        "aiAnalysis": {
            "model":   model_name,
            "weights": weight_desc,
            "summary": f"基于{model_name}，从{len(_SUPPLIER_POOL)}家候选供应商中筛选出{len(suppliers)}家最优推荐，综合考量资质、信用、价格、交货、服务五大维度。",
        },
        "demand": {
            "demandId": task["demand_id"],
            "keyword":  task["keyword"],
            "category": task["category"],
            "demandType": demand_type,
        },
    })


@app.route("/internal/suppliers/recommend", methods=["GET"])
def recommend_suppliers():
    keyword  = request.args.get("keyword", "")
    category = request.args.get("category", "")
    limit    = int(request.args.get("limit", 3))
    prefix   = keyword if keyword else category if category else "通用"
    result   = [{
        "id": s["id"], "name": f"{prefix[:4]}{s['name']}", "matchScore": round(_calc_score(s, _B2B_WEIGHTS), 2),
        "avgPrice": round(s["factor"] * 10000, 0),
        "deliveryDays": s["days"], "rating": s["rating"],
    } for s in _SUPPLIER_POOL[:limit]]
    return resp(0, "success", {"total": len(result), "suppliers": result})


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "UP", "service": "ai-matching-service"})


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=PORT)
