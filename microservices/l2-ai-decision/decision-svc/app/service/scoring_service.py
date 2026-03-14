"""
评分引擎服务
实现三大评分模型:
  1. B2B评分模型 - 供应商资质/店龄/信用等级/认证
  2. B2C(已定品牌)评分模型 - 原厂正品/销量/质量/服务/评价
  3. B2C(未定品牌)评分模型 - 参数/质量/销量/服务/评价/店龄
"""
from dataclasses import dataclass
from typing import Optional
from enum import Enum


class ScoringModel(str, Enum):
    B2B = "B2B"
    B2C_BRAND = "B2C_BRAND"       # B2C 已定品牌
    B2C_NO_BRAND = "B2C_NO_BRAND"  # B2C 未定品牌


@dataclass
class ProductData:
    """商品/供应商原始数据"""
    product_id: str
    title: str
    price: float
    platform: str

    # 通用字段
    sales_volume: int = 0
    rating: float = 0.0
    review_count: int = 0
    shop_age_years: float = 0.0
    service_score: float = 0.0
    return_rate: float = 0.0

    # B2B 专用
    supplier_qualification: Optional[str] = None  # 供应商资质等级
    credit_level: Optional[str] = None            # 信用等级
    certifications: Optional[list] = None          # 认证列表（ISO/CE等）
    is_factory: bool = False

    # B2C 专用
    is_official: bool = False    # 是否官方旗舰店
    is_authentic: bool = True    # 是否正品
    quality_score: float = 0.0
    param_match_score: float = 0.0  # 参数匹配度


@dataclass
class ScoringResult:
    product_id: str
    total_score: float
    dimension_scores: dict
    recommendation_level: str  # 品质款 | 性价比款 | 不推荐
    score_reason: str


class ScoringService:

    # ---- B2B 评分权重 ----
    B2B_WEIGHTS = {
        "supplier_qualification": 0.30,  # 供应商资质
        "shop_age": 0.20,                # 店龄
        "credit_level": 0.25,            # 信用等级
        "certifications": 0.15,          # 认证资质
        "price_competitiveness": 0.10,   # 价格竞争力
    }

    # ---- B2C 已定品牌 评分权重 ----
    B2C_BRAND_WEIGHTS = {
        "authenticity": 0.35,    # 原厂正品
        "sales_volume": 0.20,    # 销量
        "quality": 0.20,         # 质量
        "service": 0.15,         # 服务
        "reviews": 0.10,         # 用户评价
    }

    # ---- B2C 未定品牌 评分权重 ----
    B2C_NO_BRAND_WEIGHTS = {
        "param_match": 0.25,     # 参数匹配
        "quality": 0.20,         # 质量
        "sales_volume": 0.20,    # 销量
        "service": 0.15,         # 服务
        "reviews": 0.10,         # 用户评价
        "shop_age": 0.10,        # 店龄
    }

    def score(self, product: ProductData, model: ScoringModel) -> ScoringResult:
        """对商品进行评分"""
        if model == ScoringModel.B2B:
            return self._score_b2b(product)
        elif model == ScoringModel.B2C_BRAND:
            return self._score_b2c_brand(product)
        else:
            return self._score_b2c_no_brand(product)

    def score_batch(self, products: list[ProductData], model: ScoringModel) -> list[ScoringResult]:
        """批量评分并排序"""
        results = [self.score(p, model) for p in products]
        return sorted(results, key=lambda r: r.total_score, reverse=True)

    def _score_b2b(self, p: ProductData) -> ScoringResult:
        """B2B评分：重点考察供应商资质"""
        qualification_score = self._map_qualification(p.supplier_qualification)
        shop_age_score = min(p.shop_age_years / 10, 1.0)
        credit_score = self._map_credit_level(p.credit_level)
        cert_score = min(len(p.certifications or []) / 5, 1.0)
        price_score = self._calc_price_competitiveness(p.price)

        w = self.B2B_WEIGHTS
        total = (
            qualification_score * w["supplier_qualification"]
            + shop_age_score * w["shop_age"]
            + credit_score * w["credit_level"]
            + cert_score * w["certifications"]
            + price_score * w["price_competitiveness"]
        )

        return ScoringResult(
            product_id=p.product_id,
            total_score=round(total * 100, 2),
            dimension_scores={
                "供应商资质": round(qualification_score * 100, 1),
                "店龄": round(shop_age_score * 100, 1),
                "信用等级": round(credit_score * 100, 1),
                "认证资质": round(cert_score * 100, 1),
                "价格竞争力": round(price_score * 100, 1),
            },
            recommendation_level=self._get_recommendation_level(total),
            score_reason=self._generate_b2b_reason(p, total),
        )

    def _score_b2c_brand(self, p: ProductData) -> ScoringResult:
        """B2C已定品牌评分：重点考察正品与口碑"""
        authenticity_score = 1.0 if (p.is_official and p.is_authentic) else (0.5 if p.is_authentic else 0.0)
        sales_score = min(p.sales_volume / 100000, 1.0)
        quality_score = p.quality_score
        service_score = p.service_score / 5.0
        review_score = p.rating / 5.0

        w = self.B2C_BRAND_WEIGHTS
        total = (
            authenticity_score * w["authenticity"]
            + sales_score * w["sales_volume"]
            + quality_score * w["quality"]
            + service_score * w["service"]
            + review_score * w["reviews"]
        )

        return ScoringResult(
            product_id=p.product_id,
            total_score=round(total * 100, 2),
            dimension_scores={
                "正品保障": round(authenticity_score * 100, 1),
                "销量": round(sales_score * 100, 1),
                "质量": round(quality_score * 100, 1),
                "服务": round(service_score * 100, 1),
                "用户评价": round(review_score * 100, 1),
            },
            recommendation_level=self._get_recommendation_level(total),
            score_reason=self._generate_b2c_brand_reason(p, total),
        )

    def _score_b2c_no_brand(self, p: ProductData) -> ScoringResult:
        """B2C未定品牌评分：综合参数+质量+口碑"""
        w = self.B2C_NO_BRAND_WEIGHTS
        total = (
            p.param_match_score * w["param_match"]
            + p.quality_score * w["quality"]
            + min(p.sales_volume / 50000, 1.0) * w["sales_volume"]
            + (p.service_score / 5.0) * w["service"]
            + (p.rating / 5.0) * w["reviews"]
            + min(p.shop_age_years / 5, 1.0) * w["shop_age"]
        )

        return ScoringResult(
            product_id=p.product_id,
            total_score=round(total * 100, 2),
            dimension_scores={
                "参数匹配": round(p.param_match_score * 100, 1),
                "质量": round(p.quality_score * 100, 1),
                "销量": round(min(p.sales_volume / 50000, 1.0) * 100, 1),
                "服务": round((p.service_score / 5.0) * 100, 1),
                "用户评价": round((p.rating / 5.0) * 100, 1),
                "店铺资历": round(min(p.shop_age_years / 5, 1.0) * 100, 1),
            },
            recommendation_level=self._get_recommendation_level(total),
            score_reason=self._generate_b2c_no_brand_reason(p, total),
        )

    def _get_recommendation_level(self, score: float) -> str:
        if score >= 0.85:
            return "品质款"
        elif score >= 0.65:
            return "性价比款"
        else:
            return "不推荐"

    def _map_qualification(self, qualification: Optional[str]) -> float:
        mapping = {"AAA": 1.0, "AA": 0.8, "A": 0.6, "B": 0.4, "C": 0.2}
        return mapping.get(qualification or "C", 0.3)

    def _map_credit_level(self, credit: Optional[str]) -> float:
        mapping = {"钻石": 1.0, "金冠": 0.85, "皇冠": 0.7, "金牌": 0.55, "普通": 0.3}
        return mapping.get(credit or "普通", 0.3)

    def _calc_price_competitiveness(self, price: float) -> float:
        # 实际应基于同类商品价格区间计算，此处简化
        return 0.7

    def _generate_b2b_reason(self, p: ProductData, score: float) -> str:
        certs = "、".join(p.certifications or []) or "无"
        return f"供应商综合评分{score*100:.1f}分，店龄{p.shop_age_years:.1f}年，认证：{certs}"

    def _generate_b2c_brand_reason(self, p: ProductData, score: float) -> str:
        official_text = "官方旗舰店" if p.is_official else "授权经销商"
        return f"{official_text}，评分{p.rating:.1f}分，销量{p.sales_volume}件"

    def _generate_b2c_no_brand_reason(self, p: ProductData, score: float) -> str:
        return f"综合评分{score*100:.1f}分，参数匹配度{p.param_match_score*100:.0f}%，用户评分{p.rating:.1f}"


scoring_service = ScoringService()
