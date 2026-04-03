"""
generate_ecommerce_test_data.py
电商商品测试数据生成器 — ILbuy v2.0 Schema

Usage:
    python scripts/generate_ecommerce_test_data.py              # 生成20条并打印汇总
    python scripts/generate_ecommerce_test_data.py --count 50   # 生成指定数量
    python scripts/generate_ecommerce_test_data.py --multimodal # 同时生成多模态测试用例
    python scripts/generate_ecommerce_test_data.py --seed 42    # 固定随机种子（可重现）
"""
from __future__ import annotations

import argparse
import json
import random
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any


# ── Constants ─────────────────────────────────────────────────────────────────

PLATFORMS = ["tmall", "jd", "pinduoduo", "douyin", "vip", "1688"]

PLATFORM_NAMES = {
    "tmall": "天猫", "jd": "京东", "pinduoduo": "拼多多",
    "douyin": "抖音", "vip": "唯品会", "1688": "阿里巴巴1688",
}

CATEGORIES: dict[str, list[str]] = {
    "手机通讯": ["智能手机", "老人机", "5G手机", "游戏手机"],
    "电脑办公": ["笔记本电脑", "台式机", "平板电脑", "显示器", "打印机"],
    "家用电器": ["冰箱", "洗衣机", "空调", "电视", "热水器"],
    "服装": ["T恤", "衬衫", "裤子", "裙子", "外套", "羽绒服"],
    "鞋靴": ["运动鞋", "皮鞋", "凉鞋", "拖鞋", "跑步鞋"],
    "美妆护肤": ["护肤品", "彩妆", "香水", "化妆工具", "面膜"],
    "食品饮料": ["零食", "饮料", "生鲜", "粮油", "保健品"],
    "母婴玩具": ["奶粉", "尿裤", "玩具", "童装", "童鞋"],
    "运动户外": ["健身器材", "运动服饰", "户外装备", "跑步鞋"],
    "家居家纺": ["家具", "家纺", "厨具", "收纳", "灯具"],
    "工业设备": ["机床", "电机", "液压", "传感器", "变频器"],
    "原材料": ["钢材", "铝材", "铜材", "塑料", "化工原料"],
    "电子元件": ["继电器", "芯片", "电容电阻", "传感器模块"],
}

BRANDS_BY_CATEGORY: dict[str, list[str]] = {
    "手机通讯": ["苹果", "华为", "小米", "OPPO", "vivo", "三星", "荣耀"],
    "电脑办公": ["联想", "戴尔", "惠普", "华为", "苹果", "华硕", "宏碁"],
    "家用电器": ["海尔", "美的", "格力", "小米", "松下", "西门子"],
    "服装": ["优衣库", "ZARA", "李宁", "安踏", "太平鸟", "海澜之家"],
    "鞋靴": ["耐克", "阿迪达斯", "安踏", "李宁", "新百伦", "特步"],
    "美妆护肤": ["雅诗兰黛", "兰蔻", "SK-II", "完美日记", "花西子"],
    "食品饮料": ["三只松鼠", "良品铺子", "百草味", "伊利", "蒙牛"],
    "母婴玩具": ["费雪", "美赞臣", "帮宝适", "好奇", "乐高"],
    "运动户外": ["耐克", "阿迪达斯", "安踏", "李宁", "迪卡侬", "始祖鸟"],
    "家居家纺": ["宜家", "全友", "顾家", "恒洁", "九牧"],
    "工业设备": ["西门子", "ABB", "三菱", "英威腾", "汇川"],
    "原材料": ["宝钢", "鞍钢", "南铝", "中化", "万华化学"],
    "电子元件": ["欧姆龙", "意法半导体", "英飞凌", "德州仪器", "NXP"],
}

PRICE_RANGES: dict[str, tuple[float, float]] = {
    "手机通讯": (500, 15000), "电脑办公": (1000, 30000),
    "家用电器": (300, 20000), "服装": (30, 3000), "鞋靴": (50, 5000),
    "美妆护肤": (20, 5000), "食品饮料": (5, 500), "母婴玩具": (15, 5000),
    "运动户外": (50, 15000), "家居家纺": (20, 20000),
    "工业设备": (500, 200000), "原材料": (5, 500), "电子元件": (1, 500),
}

ADJECTIVES = ["新款", "2024款", "爆款", "热销", "正品", "旗舰版", "升级版"]
FEATURES   = ["大容量", "高颜值", "智能", "便携", "多功能", "超薄", "节能"]

# ── Platform-specific generators ──────────────────────────────────────────────

def _ps_tmall(price: float, is_imported: bool, is_official: bool) -> dict:
    return {"tmall": {
        "tmall_quality": is_official and random.random() < 0.5,
        "tmall_global": is_imported,
        "tmall_supermarket": random.random() < 0.1,
        "fresh": random.random() < 0.05,
        "cross_border": is_imported,
        "haitao": is_imported and random.random() < 0.3,
        "taojinbi_rate": random.choice([0, 0.01, 0.02, 0.05]),
        "ji_fen": int(price // 10),
        "tmall_points": int(price * random.uniform(1, 3)),
    }}

def _ps_jd(price: float, is_official: bool) -> dict:
    return {"jd": {
        "jd_self_operated": is_official and random.random() < 0.6,
        "jd_logistics": random.random() < 0.8,
        "jd_supermarket": random.random() < 0.1,
        "jd_global": random.random() < 0.1,
        "jd_plus_discount": random.random() < 0.5,
        "jd_delivery_promise": {
            "delivery_by_time": random.choice(["次日达", "当日达", "预约配送"]),
            "installation_service": price > 2000 and random.random() < 0.5,
        },
        "jd_warranty": {
            "extended_warranty": price > 3000 and random.random() < 0.4,
            "only_for_jd": is_official,
        },
    }}

def _ps_pinduoduo(price: float, sold: int) -> dict:
    group_active = random.random() < 0.65
    return {"pinduoduo": {
        "group_buy": {
            "group_price": round(price * random.uniform(0.85, 0.95), 2),
            "group_size": random.choice([2, 3, 5]),
            "group_duration": random.choice([12, 24, 48]),
            "already_joined": sold // random.randint(8, 20),
        } if group_active else None,
        "bargain": {
            "original_price": price,
            "target_price": round(price * 0.5, 2),
            "current_price": round(price * random.uniform(0.6, 0.85), 2),
            "helpers_needed": random.randint(1, 10),
        } if not group_active and random.random() < 0.3 else None,
        "pdd_preferential": price < 300 and random.random() < 0.4,
        "free_trial": random.random() < 0.05,
        "limited_time_deal": random.random() < 0.3,
    }}

def _ps_douyin(price: float, sold: int) -> dict:
    h = abs(hash(str(price) + str(sold))) % 100000
    return {"douyin": {
        "live_stream": {
            "is_live_product": random.random() < 0.6,
            "live_room_id": f"LR_{h:05d}",
            "anchor_id": f"ANC_{h % 10000:04d}",
            "next_live_time": (datetime.now(timezone.utc) + timedelta(days=random.randint(1, 7))).strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        } if random.random() < 0.5 else None,
        "short_video": {
            "video_id": f"VID_{h:05d}",
            "author_id": f"AUT_{h % 10000:04d}",
            "view_count": sold * random.randint(5, 20),
        },
        "douyin_promotion": {
            "commission_rate": round(random.uniform(0.05, 0.20), 2),
            "kol_list": [f"达人{chr(65+i)}" for i in range(random.randint(1, 3))],
            "topic": f"好物推荐#{random.randint(1000, 9999)}",
        },
        "douyin_points": round(price * random.uniform(3, 8)),
    }}

def _ps_vip(price: float, orig_price: float) -> dict:
    return {"vip": {
        "vip_price": price,
        "market_price": orig_price,
        "discount_rate": round(price / orig_price, 3) if orig_price else 1.0,
        "flash_sale": {
            "start_time": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+08:00"),
            "end_time": (datetime.now(timezone.utc) + timedelta(days=random.randint(3, 30))).strftime("%Y-%m-%dT%H:%M:%S+08:00"),
            "limit_per_user": random.choice([1, 2, 3, 5]),
        } if random.random() < 0.6 else None,
        "vip_member_price": round(price * random.uniform(0.90, 0.97), 2),
        "brand_direct_sale": random.random() < 0.5,
    }}

def _ps_1688(price: float) -> dict:
    moq = random.choice([10, 50, 100, 500, 1000])
    return {"alibaba": {
        "wholesale": {
            "moq": moq,
            "price_tiers": [
                {"min_quantity": moq, "max_quantity": moq * 4, "price": price},
                {"min_quantity": moq * 5, "max_quantity": moq * 19, "price": round(price * 0.9, 2)},
                {"min_quantity": moq * 20, "max_quantity": None, "price": round(price * 0.78, 2)},
            ],
            "sample_available": random.random() < 0.7,
            "sample_price": round(price * random.uniform(1.2, 2.0), 2),
        },
        "customization": {
            "support_custom": random.random() < 0.6,
            "custom_types": random.sample(["logo", "color", "packaging", "size"], random.randint(1, 4)),
            "lead_time": random.randint(7, 30),
        },
        "b2b_features": {
            "factory_direct": random.random() < 0.7,
            "trade_assurance": random.random() < 0.8,
            "inspection_service": random.random() < 0.5,
        },
    }}


def _platform_specific(platform: str, price: float, orig_price: float,
                        is_imported: bool, is_official: bool, sold: int) -> dict:
    if platform == "tmall":
        return _ps_tmall(price, is_imported, is_official)
    if platform == "jd":
        return _ps_jd(price, is_official)
    if platform == "pinduoduo":
        return _ps_pinduoduo(price, sold)
    if platform == "douyin":
        return _ps_douyin(price, sold)
    if platform == "vip":
        return _ps_vip(price, orig_price)
    if platform == "1688":
        return _ps_1688(price)
    return {}


# ── Main generator class ──────────────────────────────────────────────────────

class EcommerceProductGenerator:
    """电商商品测试数据生成器 — 支持 ILbuy v2.0 Schema"""

    def __init__(self, seed: int | None = None):
        if seed is not None:
            random.seed(seed)

    # ── Public API ────────────────────────────────────────────────────────────

    def generate_product(self, platform: str | None = None) -> dict[str, Any]:
        """生成单个完整 v2.0 商品对象"""
        platform = platform or random.choice(PLATFORMS)
        main_cat = random.choice(list(CATEGORIES))
        sub_cat  = random.choice(CATEGORIES[main_cat])
        brand    = random.choice(BRANDS_BY_CATEGORY.get(main_cat, ["其他"]))

        lo, hi  = PRICE_RANGES.get(main_cat, (10, 1000))
        cur_price   = round(random.uniform(lo, hi), 2)
        orig_price  = round(cur_price * random.uniform(1.15, 2.2), 2)
        discount    = round(cur_price / orig_price, 3)
        is_imported = random.random() < 0.1
        is_official = random.random() < 0.55

        pid     = uuid.uuid4().hex[:8].upper()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        title   = f"{random.choice(ADJECTIVES)} {brand} {random.choice(FEATURES)} {sub_cat}"
        stock   = random.randint(10, 5000)
        sold    = random.randint(50, 50000)
        monthly = sold // random.randint(2, 8)

        ps = _platform_specific(platform, cur_price, orig_price, is_imported, is_official, sold)

        return {
            "$schema": "https://ecommerce-product-schema.com/v2.0",
            "version": "2.0",
            "platform": platform,
            "product": {
                "basic_info": {
                    "product_id": pid,
                    "platform_product_id": f"{platform}_{pid}",
                    "spu_id": f"SPU_{pid}",
                    "title": title,
                    "subtitle": f"{brand}官方旗舰店 正品保证",
                    "description": f"{title}，品质卓越，服务一流。",
                    "category": {"main_category": main_cat, "sub_category": sub_cat, "third_category": sub_cat},
                    "brand": {"id": brand[:4], "name": brand, "logo_url": f"https://img.ilbuy.com/brand/{brand}.png"},
                    "origin": {"country": "中国", "region": "广东", "is_imported": is_imported},
                    "labels": random.sample(["新品", "热销", "包邮", "正品保证", "7天退货"], 2),
                    "certifications": ["3C认证"] if main_cat in ("手机通讯", "电脑办公", "家用电器") else [],
                    "status": "on_sale",
                },
                "price_info": {
                    "current_price": cur_price, "original_price": orig_price,
                    "discount": discount, "discount_text": f"{round(discount*10,1)}折",
                    "price_range": {"min": cur_price, "max": orig_price},
                    "currency": "CNY", "vat_included": True,
                    "platform_promotion": {"type": "coupon", "discount_amount": round(orig_price - cur_price, 2), "discount_rule": "限时优惠"},
                    "merchant_promotion": {"type": "gift", "details": "购买赠礼品"},
                },
                "inventory": {
                    "stock_quantity": stock, "available_quantity": max(stock - 5, 0),
                    "sold_quantity": sold,
                    "sku_stock_info": {f"SKU_{pid}": {"stock": stock, "available": max(stock - 5, 0)}},
                    "warehouse_info": {"location": "广东仓", "ship_from": "广东"},
                },
                "media": {
                    "main_images": [f"https://img.ilbuy.com/{pid}_main.jpg"],
                    "detail_images": [f"https://img.ilbuy.com/{pid}_detail.jpg"],
                    "video_urls": [], "360_view_url": None, "ar_view_url": None,
                },
                "specifications": {
                    "key_attributes": {},
                    "detailed_specs": {"section": "商品规格", "attributes": []},
                },
                "sku_list": [{
                    "sku_id": f"SKU_{pid}", "sku_code": f"SKU_{pid}", "specs": {},
                    "price": cur_price, "original_price": orig_price,
                    "stock": stock, "available": max(stock - 5, 0),
                    "barcode": f"690{abs(hash(pid))%10000000:07d}",
                    "image_url": f"https://img.ilbuy.com/{pid}_sku.jpg",
                    "weight": round(random.uniform(0.1, 5.0), 2),
                    "volume": round(random.uniform(0.001, 0.1), 4),
                    "is_default": True,
                }],
                "shipping": {
                    "template_id": f"TMPL_{platform.upper()}", "shipping_fee": 0.0,
                    "free_shipping_condition": {"condition": "amount", "threshold": 0},
                    "delivery_options": [{"type": "express", "provider": "顺丰速运", "estimated_days": 3, "cost": 0.0}],
                    "return_policy": {"can_return": True, "return_days": 7, "condition": "全新未使用"},
                },
                "merchant": {
                    "shop_id": f"SHOP_{pid}", "shop_name": f"{brand}官方旗舰店",
                    "shop_logo": f"https://img.ilbuy.com/shop/SHOP_{pid}.png",
                    "shop_rating": round(random.uniform(4.0, 5.0), 2),
                    "shop_level": random.choice(["旗舰店", "专营店", "专卖店"]),
                    "follower_count": sold * random.randint(5, 30),
                    "is_official": is_official, "is_verified": True,
                    "location": random.choice(["广东省", "浙江省", "上海市", "北京市", "江苏省"]),
                },
                "ratings": {
                    "average_score": round(random.uniform(3.8, 5.0), 2),
                    "total_reviews": sold // random.randint(5, 15),
                    "positive_rate": round(random.uniform(0.88, 0.99), 3),
                    "rating_distribution": {
                        "5": int(sold // 8 * 0.8), "4": int(sold // 8 * 0.14),
                        "3": int(sold // 8 * 0.03), "2": int(sold // 8 * 0.02), "1": int(sold // 8 * 0.01),
                    },
                    "reviews": [], "tags": [brand, main_cat, sub_cat, "好评"],
                },
                "sales_metrics": {
                    "monthly_sales": monthly, "total_sales": sold,
                    "sales_volume": round(sold * cur_price, 2),
                    "conversion_rate": round(random.uniform(0.02, 0.12), 3),
                    "view_count": sold * random.randint(8, 25),
                    "favorite_count": sold // random.randint(3, 8),
                    "cart_addition_count": sold // random.randint(2, 5),
                },
                "after_sales": {
                    "warranty": {"period": "1年", "type": "全国联保", "scope": "硬件故障免费维修"},
                    "support": {
                        "installment": cur_price >= 1000, "insurance": cur_price >= 3000,
                        "quality_assurance": True,
                    },
                    "service_promise": ["7天无理由退货", "全国联保1年", "正品保证"],
                },
                "seo": {
                    "keywords": [brand, main_cat, sub_cat, title.split()[0]],
                    "meta_description": f"{title} - {brand}",
                    "url_slug": pid.lower(),
                },
                "timestamps": {
                    "created_at": now_str, "updated_at": now_str,
                    "published_at": now_str, "valid_until": None,
                },
                "platform_specific": ps,
            },
        }

    def generate_test_dataset(self, num_products: int = 20) -> dict[str, Any]:
        """生成测试数据集，保证每个平台至少有一条数据"""
        products: list[dict] = []
        dist: dict[str, int] = {p: 0 for p in PLATFORMS}

        for i in range(num_products):
            platform = PLATFORMS[i % len(PLATFORMS)] if i < len(PLATFORMS) else random.choice(PLATFORMS)
            product  = self.generate_product(platform)
            products.append(product)
            dist[platform] += 1

        return {
            "metadata": {
                "$schema": "https://ecommerce-product-schema.com/v2.0",
                "generated_at": datetime.now().isoformat(),
                "total_products": num_products,
                "platform_distribution": dist,
                "generator": "EcommerceProductGenerator v1.0",
            },
            "products": products,
        }

    def generate_for_multimodal_test(self) -> dict[str, Any]:
        """生成多模态输入测试用例集"""
        dataset = self.generate_test_dataset(20)
        pids = [p["product"]["basic_info"]["product_id"] for p in dataset["products"]]

        return {
            "test_cases": {
                "text": [
                    {"input": "智能手机最新款", "expected_category": "手机通讯", "description": "品类关键词查询"},
                    {"input": "5000元以下的笔记本电脑", "expected_category": "电脑办公", "description": "价格区间+品类"},
                    {"input": "帮我找一双耐克运动鞋", "expected_category": "鞋靴", "description": "品牌+品类口语查询"},
                    {"input": "工厂采购500件T恤定制logo", "expected_platform": "1688", "description": "B2B批发查询"},
                ],
                "image": [
                    {"image_type": "product_photo", "image_features": ["手机外观", "屏幕", "摄像头"], "expected_category": "手机通讯", "description": "智能手机图像识别"},
                    {"image_type": "product_photo", "image_features": ["键盘", "屏幕", "笔记本"], "expected_category": "电脑办公", "description": "笔记本电脑图像识别"},
                    {"image_type": "product_photo", "image_features": ["运动鞋底", "鞋面材质"], "expected_category": "鞋靴", "description": "运动鞋图像识别"},
                ],
                "voice": [
                    {"transcript": "我想买一部苹果手机", "expected_intent": "PURCHASE", "expected_category": "手机通讯", "description": "购买意图+品牌"},
                    {"transcript": "不锈钢板材今天的价格是多少", "expected_intent": "PRICE_QUERY", "expected_category": "原材料", "description": "价格查询"},
                    {"transcript": "有没有耐克的跑步鞋", "expected_intent": "STOCK_CHECK", "expected_category": "鞋靴", "description": "库存查询"},
                ],
                "link": [
                    {"url": "https://item.taobao.com/item.htm?id=1234567890", "expected_platform": "taobao", "description": "淘宝商品链接"},
                    {"url": "https://item.jd.com/100088888.html", "expected_platform": "jd", "description": "京东商品链接"},
                    {"url": "https://detail.1688.com/offer/12345.html", "expected_platform": "1688", "description": "1688商品链接"},
                    {"url": "https://v.douyin.com/iFeNS9Sb/", "expected_platform": "douyin", "description": "抖音商品短链"},
                ],
            },
            "products": dataset,
        }


# ── CLI entry point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ILbuy 电商商品测试数据生成器")
    parser.add_argument("--count", type=int, default=20, help="生成商品数量（默认20）")
    parser.add_argument("--seed", type=int, default=None, help="随机种子（默认随机）")
    parser.add_argument("--multimodal", action="store_true", help="同时生成多模态测试用例")
    parser.add_argument("--output", type=str, default=None, help="输出文件路径（默认打印到控制台）")
    args = parser.parse_args()

    gen = EcommerceProductGenerator(seed=args.seed)

    if args.multimodal:
        data = gen.generate_for_multimodal_test()
        filename = args.output or "multimodal_test_cases.json"
    else:
        data = gen.generate_test_dataset(args.count)
        filename = args.output or "ecommerce_test_data.json"

    if args.output:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"已保存到 {filename}")
    else:
        dist = data.get("metadata", {}).get("platform_distribution", {})
        total = data.get("metadata", {}).get("total_products", args.count)
        print(f"已生成 {total} 个商品测试数据")
        print(f"平台分布: {dist}")
        if args.multimodal:
            tc = data["test_cases"]
            print(f"多模态测试用例: text×{len(tc['text'])} image×{len(tc['image'])} voice×{len(tc['voice'])} link×{len(tc['link'])}")
