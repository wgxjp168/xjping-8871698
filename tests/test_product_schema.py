"""
tests/test_product_schema.py
ILbuy v2.0 商品 Schema 完整性测试套件

Run:
    pytest tests/test_product_schema.py -v
"""
from __future__ import annotations

import json
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from generate_ecommerce_test_data import (
    EcommerceProductGenerator,
    PLATFORMS,
    PLATFORM_NAMES,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def gen():
    return EcommerceProductGenerator(seed=99)


@pytest.fixture(scope="module")
def dataset(gen):
    return gen.generate_test_dataset(24)  # 4 per platform


@pytest.fixture(scope="module")
def products(dataset):
    return dataset["products"]


@pytest.fixture(scope="module")
def single_product(gen):
    return gen.generate_product("tmall")


# ── Schema envelope ───────────────────────────────────────────────────────────

class TestSchemaEnvelope:
    def test_schema_url(self, single_product):
        assert single_product["$schema"] == "https://ecommerce-product-schema.com/v2.0"

    def test_version(self, single_product):
        assert single_product["version"] == "2.0"

    def test_platform_is_known(self, single_product):
        assert single_product["platform"] in PLATFORMS

    def test_product_key_present(self, single_product):
        assert "product" in single_product


# ── basic_info ────────────────────────────────────────────────────────────────

class TestBasicInfo:
    def test_required_ids(self, products):
        for p in products:
            bi = p["product"]["basic_info"]
            assert bi["product_id"], f"product_id empty: {p}"
            assert bi["platform_product_id"]
            assert bi["spu_id"]

    def test_title_non_empty(self, products):
        for p in products:
            assert len(p["product"]["basic_info"]["title"]) >= 4

    def test_category_three_levels(self, products):
        for p in products:
            cat = p["product"]["basic_info"]["category"]
            assert "main_category" in cat and cat["main_category"]
            assert "sub_category" in cat and cat["sub_category"]
            assert "third_category" in cat

    def test_brand_fields(self, products):
        for p in products:
            brand = p["product"]["basic_info"]["brand"]
            assert "name" in brand and brand["name"]
            assert "id" in brand
            assert "logo_url" in brand

    def test_origin_fields(self, products):
        for p in products:
            origin = p["product"]["basic_info"]["origin"]
            assert "country" in origin
            assert isinstance(origin["is_imported"], bool)

    def test_status_enum(self, products):
        valid = {"on_sale", "off_shelf", "draft", "deleted"}
        for p in products:
            assert p["product"]["basic_info"]["status"] in valid

    def test_labels_is_list(self, products):
        for p in products:
            assert isinstance(p["product"]["basic_info"]["labels"], list)

    def test_certifications_is_list(self, products):
        for p in products:
            assert isinstance(p["product"]["basic_info"]["certifications"], list)


# ── price_info ────────────────────────────────────────────────────────────────

class TestPriceInfo:
    def test_current_price_positive(self, products):
        for p in products:
            assert p["product"]["price_info"]["current_price"] > 0

    def test_original_price_gte_current(self, products):
        for p in products:
            pi = p["product"]["price_info"]
            if pi.get("original_price"):
                assert pi["original_price"] >= pi["current_price"], \
                    f"orig_price < current_price: {p['product']['basic_info']['product_id']}"

    def test_discount_in_range(self, products):
        for p in products:
            d = p["product"]["price_info"]["discount"]
            assert 0 < d <= 1.0, f"discount out of range: {d}"

    def test_currency_enum(self, products):
        valid = {"CNY", "USD", "EUR"}
        for p in products:
            assert p["product"]["price_info"]["currency"] in valid

    def test_price_range_min_lte_max(self, products):
        for p in products:
            pr = p["product"]["price_info"]["price_range"]
            assert pr["min"] <= pr["max"], "price_range.min > max"

    def test_vat_included_bool(self, products):
        for p in products:
            assert isinstance(p["product"]["price_info"]["vat_included"], bool)


# ── inventory ─────────────────────────────────────────────────────────────────

class TestInventory:
    def test_stock_non_negative(self, products):
        for p in products:
            inv = p["product"]["inventory"]
            assert inv["stock_quantity"] >= 0
            assert inv["available_quantity"] >= 0
            assert inv["sold_quantity"] >= 0

    def test_available_lte_stock(self, products):
        for p in products:
            inv = p["product"]["inventory"]
            assert inv["available_quantity"] <= inv["stock_quantity"]

    def test_sku_stock_info_is_dict(self, products):
        for p in products:
            assert isinstance(p["product"]["inventory"]["sku_stock_info"], dict)

    def test_warehouse_info(self, products):
        for p in products:
            wi = p["product"]["inventory"]["warehouse_info"]
            assert "location" in wi and "ship_from" in wi


# ── sku_list ──────────────────────────────────────────────────────────────────

class TestSkuList:
    def test_at_least_one_sku(self, products):
        for p in products:
            assert len(p["product"]["sku_list"]) >= 1

    def test_sku_required_fields(self, products):
        required = {"sku_id", "sku_code", "specs", "price", "stock", "is_default"}
        for p in products:
            for sku in p["product"]["sku_list"]:
                missing = required - set(sku.keys())
                assert not missing, f"SKU missing fields {missing} in {p['product']['basic_info']['product_id']}"

    def test_exactly_one_default_sku(self, products):
        for p in products:
            defaults = [s for s in p["product"]["sku_list"] if s["is_default"]]
            assert len(defaults) == 1, f"Expected 1 default SKU, got {len(defaults)}"

    def test_sku_price_positive(self, products):
        for p in products:
            for sku in p["product"]["sku_list"]:
                assert sku["price"] > 0


# ── merchant ──────────────────────────────────────────────────────────────────

class TestMerchant:
    def test_required_merchant_fields(self, products):
        for p in products:
            mer = p["product"]["merchant"]
            assert mer["shop_id"] and mer["shop_name"]
            assert 1.0 <= mer["shop_rating"] <= 5.0
            assert isinstance(mer["is_official"], bool)
            assert isinstance(mer["is_verified"], bool)

    def test_follower_count_non_negative(self, products):
        for p in products:
            assert p["product"]["merchant"]["follower_count"] >= 0


# ── ratings ───────────────────────────────────────────────────────────────────

class TestRatings:
    def test_score_range(self, products):
        for p in products:
            score = p["product"]["ratings"]["average_score"]
            assert 1.0 <= score <= 5.0, f"score out of range: {score}"

    def test_positive_rate_range(self, products):
        for p in products:
            pr = p["product"]["ratings"]["positive_rate"]
            assert 0.0 <= pr <= 1.0

    def test_total_reviews_non_negative(self, products):
        for p in products:
            assert p["product"]["ratings"]["total_reviews"] >= 0

    def test_rating_distribution_has_five_keys(self, products):
        for p in products:
            dist = p["product"]["ratings"]["rating_distribution"]
            assert set(dist.keys()) == {"1", "2", "3", "4", "5"}


# ── platform_specific ─────────────────────────────────────────────────────────

class TestPlatformSpecific:
    def test_platform_specific_present(self, products):
        for p in products:
            assert "platform_specific" in p["product"]

    def test_tmall_specific_fields(self, gen):
        p = gen.generate_product("tmall")
        ps = p["product"]["platform_specific"]
        assert "tmall" in ps
        tmall = ps["tmall"]
        assert isinstance(tmall["tmall_quality"], bool)
        assert isinstance(tmall["tmall_global"], bool)
        assert isinstance(tmall["taojinbi_rate"], (int, float))
        assert "tmall_points" in tmall

    def test_jd_specific_fields(self, gen):
        p = gen.generate_product("jd")
        ps = p["product"]["platform_specific"]
        assert "jd" in ps
        jd = ps["jd"]
        assert isinstance(jd["jd_self_operated"], bool)
        assert isinstance(jd["jd_logistics"], bool)
        assert "jd_delivery_promise" in jd
        assert "delivery_by_time" in jd["jd_delivery_promise"]
        assert "jd_warranty" in jd

    def test_pinduoduo_specific_fields(self, gen):
        p = gen.generate_product("pinduoduo")
        ps = p["product"]["platform_specific"]
        assert "pinduoduo" in ps
        pdd = ps["pinduoduo"]
        assert isinstance(pdd["pdd_preferential"], bool)
        assert isinstance(pdd["free_trial"], bool)
        # group_buy or bargain can be None
        if pdd["group_buy"] is not None:
            gb = pdd["group_buy"]
            assert gb["group_price"] > 0
            assert gb["group_size"] >= 2

    def test_douyin_specific_fields(self, gen):
        p = gen.generate_product("douyin")
        ps = p["product"]["platform_specific"]
        assert "douyin" in ps
        dy = ps["douyin"]
        assert "douyin_promotion" in dy
        prom = dy["douyin_promotion"]
        assert 0 < prom["commission_rate"] < 1
        assert isinstance(prom["kol_list"], list)

    def test_vip_specific_fields(self, gen):
        p = gen.generate_product("vip")
        ps = p["product"]["platform_specific"]
        assert "vip" in ps
        vip = ps["vip"]
        assert "vip_price" in vip and "market_price" in vip
        assert isinstance(vip["brand_direct_sale"], bool)
        assert 0 < vip["discount_rate"] <= 1.0

    def test_1688_specific_fields(self, gen):
        p = gen.generate_product("1688")
        ps = p["product"]["platform_specific"]
        assert "alibaba" in ps
        ali = ps["alibaba"]
        ws = ali["wholesale"]
        assert ws["moq"] > 0
        assert len(ws["price_tiers"]) >= 2
        for tier in ws["price_tiers"]:
            assert "min_quantity" in tier and "price" in tier
            assert tier["price"] > 0
        assert "customization" in ali
        assert "b2b_features" in ali
        assert ali["b2b_features"]["trade_assurance"] in (True, False)


# ── sales_metrics ─────────────────────────────────────────────────────────────

class TestSalesMetrics:
    def test_sales_non_negative(self, products):
        for p in products:
            sm = p["product"]["sales_metrics"]
            assert sm["monthly_sales"] >= 0
            assert sm["total_sales"] >= 0
            assert sm["sales_volume"] >= 0

    def test_conversion_rate_range(self, products):
        for p in products:
            cr = p["product"]["sales_metrics"]["conversion_rate"]
            assert 0.0 <= cr <= 1.0

    def test_monthly_lte_total(self, products):
        for p in products:
            sm = p["product"]["sales_metrics"]
            assert sm["monthly_sales"] <= sm["total_sales"], \
                "monthly_sales cannot exceed total_sales"


# ── after_sales ───────────────────────────────────────────────────────────────

class TestAfterSales:
    def test_warranty_fields(self, products):
        for p in products:
            w = p["product"]["after_sales"]["warranty"]
            assert "period" in w and "type" in w and "scope" in w

    def test_service_promise_is_list(self, products):
        for p in products:
            sp = p["product"]["after_sales"]["service_promise"]
            assert isinstance(sp, list) and len(sp) > 0


# ── shipping ──────────────────────────────────────────────────────────────────

class TestShipping:
    def test_shipping_fee_non_negative(self, products):
        for p in products:
            assert p["product"]["shipping"]["shipping_fee"] >= 0

    def test_return_policy(self, products):
        for p in products:
            rp = p["product"]["shipping"]["return_policy"]
            assert isinstance(rp["can_return"], bool)

    def test_delivery_options(self, products):
        for p in products:
            opts = p["product"]["shipping"]["delivery_options"]
            assert isinstance(opts, list) and len(opts) >= 1


# ── serialization ─────────────────────────────────────────────────────────────

class TestSerialization:
    def test_json_serializable(self, products):
        for p in products:
            try:
                j = json.dumps(p, ensure_ascii=False)
                assert len(j) > 100
            except (TypeError, ValueError) as e:
                pytest.fail(f"JSON serialization failed for {p['product']['basic_info']['product_id']}: {e}")

    def test_json_roundtrip(self, products):
        for p in products:
            j = json.dumps(p, ensure_ascii=False)
            p2 = json.loads(j)
            assert p2["product"]["basic_info"]["product_id"] == p["product"]["basic_info"]["product_id"]

    def test_platform_distribution(self, dataset):
        dist = dataset["metadata"]["platform_distribution"]
        # Every platform should have at least one product
        for platform in PLATFORMS:
            assert dist.get(platform, 0) >= 1, f"Platform {platform} has no products"
