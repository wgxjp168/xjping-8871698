"""
数据采集模拟层
在 L3 数据采集服务就绪前，提供模拟商品数据用于测试 L2 决策流程。
实际生产中替换为对 L3 服务的 HTTP 调用。
"""
import random
from typing import List
from app.service.scoring_service import ProductData


# ---- 模拟平台商品数据库 ----
MOCK_PRODUCTS = {
    "平板电脑": [
        ProductData(
            product_id="pd_001", title="华为 MatePad 11 2023 旗舰店",
            price=2699.0, platform="京东", sales_volume=85000, rating=4.8,
            review_count=12500, shop_age_years=8.0, service_score=4.9,
            return_rate=0.01, is_official=True, is_authentic=True,
            quality_score=0.92, param_match_score=0.95,
            shop_name="华为官方旗舰店",
        ),
        ProductData(
            product_id="pd_002", title="华为 MatePad 11 2023 高配版",
            price=2899.0, platform="天猫", sales_volume=42000, rating=4.7,
            review_count=8800, shop_age_years=5.0, service_score=4.7,
            return_rate=0.015, is_official=False, is_authentic=True,
            quality_score=0.89, param_match_score=0.93,
            shop_name="华为体验授权店",
        ),
        ProductData(
            product_id="pd_003", title="华为 MatePad 11 2023 标准版",
            price=2499.0, platform="拼多多", sales_volume=18000, rating=4.5,
            review_count=3200, shop_age_years=2.0, service_score=4.3,
            return_rate=0.025, is_official=False, is_authentic=True,
            quality_score=0.75, param_match_score=0.88,
            shop_name="数码优选旗舰店",
        ),
    ],
    "手机": [
        ProductData(
            product_id="ph_001", title="小米 14 Pro 官方旗舰店",
            price=4299.0, platform="京东", sales_volume=120000, rating=4.9,
            review_count=35000, shop_age_years=10.0, service_score=4.9,
            return_rate=0.008, is_official=True, is_authentic=True,
            quality_score=0.95, param_match_score=0.90,
            shop_name="小米官方旗舰店",
        ),
        ProductData(
            product_id="ph_002", title="小米 14 256GB 星云蓝",
            price=3999.0, platform="淘宝", sales_volume=65000, rating=4.7,
            review_count=18000, shop_age_years=4.0, service_score=4.6,
            return_rate=0.012, is_official=False, is_authentic=True,
            quality_score=0.85, param_match_score=0.88,
            shop_name="小米授权专卖店",
        ),
    ],
    "笔记本电脑": [
        ProductData(
            product_id="nb_001", title="联想 ThinkPad X1 Carbon 2024",
            price=9999.0, platform="京东", sales_volume=32000, rating=4.8,
            review_count=8900, shop_age_years=12.0, service_score=4.85,
            return_rate=0.005, is_official=True, is_authentic=True,
            quality_score=0.93, param_match_score=0.91,
            shop_name="联想官方旗舰店",
        ),
        ProductData(
            product_id="nb_002", title="戴尔 XPS 15 2024 高性能版",
            price=11999.0, platform="天猫", sales_volume=15000, rating=4.7,
            review_count=4200, shop_age_years=7.0, service_score=4.7,
            return_rate=0.008, is_official=True, is_authentic=True,
            quality_score=0.91, param_match_score=0.87,
            shop_name="戴尔官方旗舰店",
        ),
        ProductData(
            product_id="nb_003", title="华为 MateBook 16s 2024",
            price=8999.0, platform="京东", sales_volume=28000, rating=4.75,
            review_count=7800, shop_age_years=8.0, service_score=4.8,
            return_rate=0.007, is_official=True, is_authentic=True,
            quality_score=0.90, param_match_score=0.89,
            shop_name="华为官方旗舰店",
        ),
    ],
    "家用电器": [
        ProductData(
            product_id="ha_001", title="美的空调 酷省电 1.5匹变频",
            price=2199.0, platform="京东", sales_volume=580000, rating=4.7,
            review_count=92000, shop_age_years=9.0, service_score=4.6,
            return_rate=0.02, is_official=True, is_authentic=True,
            quality_score=0.87, param_match_score=0.80,
            shop_name="美的官方旗舰店",
        ),
        ProductData(
            product_id="ha_002", title="格力空调 悦风 1.5匹变频",
            price=2399.0, platform="天猫", sales_volume=320000, rating=4.8,
            review_count=65000, shop_age_years=11.0, service_score=4.7,
            return_rate=0.015, is_official=True, is_authentic=True,
            quality_score=0.90, param_match_score=0.82,
            shop_name="格力官方旗舰店",
        ),
    ],
}

# B2B 供应商数据
MOCK_B2B_SUPPLIERS = [
    ProductData(
        product_id="sup_001", title="深圳宏达电子科技有限公司",
        price=150.0, platform="1688", sales_volume=50000, rating=4.7,
        review_count=2800, shop_age_years=8.0, service_score=4.6,
        return_rate=0.01, supplier_qualification="AA", credit_level="钻石",
        certifications=["ISO9001", "CE", "RoHS"], is_factory=True,
    ),
    ProductData(
        product_id="sup_002", title="广州联合供应链管理有限公司",
        price=145.0, platform="1688", sales_volume=35000, rating=4.5,
        review_count=1900, shop_age_years=5.0, service_score=4.4,
        return_rate=0.015, supplier_qualification="A", credit_level="金冠",
        certifications=["ISO9001", "CE"], is_factory=False,
    ),
    ProductData(
        product_id="sup_003", title="苏州精密制造科技股份有限公司",
        price=160.0, platform="1688", sales_volume=80000, rating=4.9,
        review_count=4200, shop_age_years=12.0, service_score=4.85,
        return_rate=0.005, supplier_qualification="AAA", credit_level="钻石",
        certifications=["ISO9001", "ISO14001", "CE", "RoHS", "UL"],
        is_factory=True,
    ),
]


def get_mock_products(category: str, brand: str = None, user_type: str = "B2C") -> List[ProductData]:
    """
    获取模拟商品数据（L3数据采集服务的桩实现）

    Args:
        category: 商品类别
        brand: 品牌（已定品牌时传入）
        user_type: B2B/B2C
    """
    if user_type == "B2B":
        return MOCK_B2B_SUPPLIERS

    products = MOCK_PRODUCTS.get(category, [])

    # 如果没有匹配类别，生成通用模拟数据
    if not products:
        products = _generate_generic_products(category, brand)

    # 如果有指定品牌，过滤相关商品
    if brand and user_type == "B2C":
        brand_products = [p for p in products if brand in p.title]
        if brand_products:
            return brand_products

    return products


def _generate_generic_products(category: str, brand: str = None) -> List[ProductData]:
    """生成通用模拟商品数据"""
    platforms = ["京东", "天猫", "淘宝", "拼多多"]
    brand_name = brand or "通用品牌"

    return [
        ProductData(
            product_id=f"gen_{i:03d}",
            title=f"{brand_name} {category} {'高配版' if i == 0 else '标准版' if i == 1 else '经济版'}",
            price=round(random.uniform(100, 5000), 2),
            platform=platforms[i % len(platforms)],
            sales_volume=random.randint(1000, 100000),
            rating=round(random.uniform(3.8, 5.0), 1),
            review_count=random.randint(100, 10000),
            shop_age_years=round(random.uniform(1, 10), 1),
            service_score=round(random.uniform(3.5, 5.0), 1),
            return_rate=round(random.uniform(0.005, 0.05), 3),
            is_official=(i == 0),
            is_authentic=True,
            quality_score=round(random.uniform(0.6, 0.95), 2),
            param_match_score=round(random.uniform(0.6, 0.95), 2),
        )
        for i in range(3)
    ]
