"""
意图识别核心服务
实现: 意图分类、品牌检测、参数提取
"""
import re
from typing import List, Optional

from app.models.request import (
    IntentRequest, IntentResponse, ExtractedParams,
    UserType, BrandStatus
)
from app.core.config import settings


# 已知品牌列表（实际应从DB加载）
KNOWN_BRANDS = {
    "华为", "苹果", "小米", "联想", "戴尔", "惠普", "三星", "索尼",
    "飞利浦", "西门子", "美的", "格力", "海尔", "九阳", "苏泊尔",
    "耐克", "阿迪达斯", "李宁", "安踏",
}

# B2B关键词
B2B_KEYWORDS = {"批量", "采购", "供应商", "企业", "公司", "工厂", "批发", "定制", "招标"}

# 参数提取正则
PARAM_PATTERNS = {
    "quantity": re.compile(r"(\d+)\s*(?:件|个|台|套|箱|吨|千克|kg)"),
    "budget": re.compile(r"预算[约为]?\s*(\d+(?:\.\d+)?)\s*[元万]"),
    "power": re.compile(r"(\d+(?:\.\d+)?)\s*[Ww瓦]"),
    "capacity": re.compile(r"(\d+(?:\.\d+)?)\s*(?:L|升|ml|毫升|GB|TB)"),
}


class IntentService:

    async def analyze(self, request: IntentRequest) -> IntentResponse:
        """
        核心意图分析方法
        1. 分类 B2B/B2C
        2. 检测品牌状态
        3. 提取结构化参数
        4. 判断是否需要追问
        """
        text = request.content

        # 1. 用户类型判断
        user_type = self._classify_user_type(text)

        # 2. 品牌检测
        brand, brand_status = self._detect_brand(text)

        # 3. 参数提取
        params = self._extract_params(text)
        if brand:
            params.brand = brand

        # 4. 商品类别识别（简化实现，实际用NLP模型）
        category = self._extract_category(text)

        # 5. 判断是否需要追问
        need_clarification, questions = self._check_clarification(
            user_type, brand_status, params, category
        )

        # 6. 置信度（实际由模型输出）
        confidence = 0.85 if category != "未知" else 0.5

        return IntentResponse(
            session_id=request.session_id,
            user_type=user_type,
            brand_status=brand_status,
            product_category=category,
            extracted_params=params,
            confidence=confidence,
            need_clarification=need_clarification,
            clarification_questions=questions if need_clarification else None,
            raw_intent=text[:200],
        )

    def _classify_user_type(self, text: str) -> UserType:
        """判断 B2B/B2C"""
        for kw in B2B_KEYWORDS:
            if kw in text:
                return UserType.B2B
        return UserType.B2C

    def _detect_brand(self, text: str):
        """检测品牌，返回 (brand_name, brand_status)"""
        for brand in KNOWN_BRANDS:
            if brand in text:
                return brand, BrandStatus.DECIDED
        return None, BrandStatus.UNDECIDED

    def _extract_params(self, text: str) -> ExtractedParams:
        """提取结构化参数"""
        params = ExtractedParams()
        for field, pattern in PARAM_PATTERNS.items():
            match = pattern.search(text)
            if match:
                value = match.group(1)
                if field == "quantity":
                    params.quantity = int(value)
                elif field == "budget":
                    params.budget = float(value)
                elif field == "power":
                    params.power = f"{value}W"
                elif field == "capacity":
                    params.capacity = match.group(0)
        return params

    def _extract_category(self, text: str) -> str:
        """商品类别识别（简化版，实际用NLP模型）"""
        categories = {
            "手机": ["手机", "iPhone", "安卓"],
            "笔记本电脑": ["笔记本", "电脑", "laptop"],
            "家用电器": ["冰箱", "洗衣机", "空调", "电视"],
            "办公用品": ["打印机", "复印机", "文具"],
            "工业设备": ["机械", "设备", "机器"],
        }
        for category, keywords in categories.items():
            if any(kw in text for kw in keywords):
                return category
        return "未知"

    def _check_clarification(
        self, user_type: UserType, brand_status: BrandStatus,
        params: ExtractedParams, category: str
    ):
        """判断是否需要追问缺失的关键信息"""
        questions = []
        if category == "未知":
            questions.append("请问您想采购什么类型的商品？")
        if user_type == UserType.B2B and not params.quantity:
            questions.append("请问您需要采购的数量是多少？")
        if not params.budget:
            questions.append("请问您的预算大概是多少？")
        return len(questions) > 0, questions


intent_service = IntentService()
