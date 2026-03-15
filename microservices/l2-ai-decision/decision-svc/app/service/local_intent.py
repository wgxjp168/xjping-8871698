"""
本地兜底意图分析
当 intent-svc 不可达时，使用本地规则引擎进行简单意图分析。
功能与 intent-svc 保持一致，但准确率较低（不含深度NLP模型）。
"""
import re
from typing import Optional

# ---- 规则库 ----
KNOWN_BRANDS = {
    "华为", "苹果", "Apple", "iPhone", "小米", "联想", "戴尔", "惠普",
    "三星", "索尼", "飞利浦", "西门子", "美的", "格力", "海尔",
    "九阳", "苏泊尔", "耐克", "阿迪达斯", "李宁", "安踏", "OPPO", "vivo",
}

B2B_KEYWORDS = {"批量", "采购", "供应商", "企业", "公司", "工厂", "批发", "定制", "招标", "商务"}

CATEGORY_MAP = {
    "平板电脑": ["平板", "ipad", "MatePad", "pad"],
    "手机": ["手机", "iPhone", "安卓", "5G"],
    "笔记本电脑": ["笔记本", "laptop", "电脑", "MacBook", "ThinkPad"],
    "家用电器": ["冰箱", "洗衣机", "空调", "电视", "微波炉", "热水器"],
    "办公用品": ["打印机", "复印机", "文具", "办公"],
    "工业设备": ["机械", "设备", "机器", "工业"],
    "数码配件": ["耳机", "键盘", "鼠标", "充电器", "数据线"],
}

PARAM_PATTERNS = {
    "quantity": re.compile(r"(\d+)\s*(?:件|个|台|套|箱|吨|千克|kg)"),
    "budget": re.compile(r"预算[约为]?\s*(\d+(?:\.\d+)?)\s*[元万]?"),
    "power": re.compile(r"(\d+(?:\.\d+)?)\s*[Ww瓦]"),
    "capacity": re.compile(r"(\d+(?:\.\d+)?)\s*(?:L|升|ml|毫升|GB|TB)"),
}


def local_analyze(session_id: str, user_id: str, text: str) -> dict:
    """本地规则意图分析，返回与 intent-svc 相同格式的字典"""
    user_type = "B2B" if any(kw in text for kw in B2B_KEYWORDS) else "B2C"
    brand, brand_status = _detect_brand(text)
    category = _detect_category(text)
    params = _extract_params(text)
    if brand:
        params["brand"] = brand

    need_clarification, questions = _check_clarification(user_type, brand_status, params, category)
    confidence = 0.72 if category != "未知" else 0.45   # 本地规则置信度较低

    return {
        "session_id": session_id,
        "user_type": user_type,
        "brand_status": brand_status,
        "product_category": category,
        "extracted_params": params,
        "confidence": confidence,
        "need_clarification": need_clarification,
        "clarification_questions": questions if need_clarification else None,
        "raw_intent": text[:200],
    }


def _detect_brand(text: str):
    for brand in KNOWN_BRANDS:
        if brand in text:
            return brand, "decided"
    return None, "undecided"


def _detect_category(text: str) -> str:
    text_lower = text.lower()
    for category, keywords in CATEGORY_MAP.items():
        if any(kw.lower() in text_lower for kw in keywords):
            return category
    return "未知"


def _extract_params(text: str) -> dict:
    params: dict = {}
    for field, pattern in PARAM_PATTERNS.items():
        match = pattern.search(text)
        if match:
            value = match.group(1)
            if field == "quantity":
                params["quantity"] = int(value)
            elif field == "budget":
                params["budget"] = float(value)
            elif field == "power":
                params["power"] = f"{value}W"
            elif field == "capacity":
                params["capacity"] = match.group(0)
    return params


def _check_clarification(user_type: str, brand_status: str, params: dict, category: str):
    questions = []
    if category == "未知":
        questions.append("请问您想采购什么类型的商品？")
    if user_type == "B2B" and "quantity" not in params:
        questions.append("请问您需要采购的数量是多少？")
    if "budget" not in params:
        questions.append("请问您的预算大概是多少？")
    return len(questions) > 0, questions
