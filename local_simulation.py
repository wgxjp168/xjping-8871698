"""
local_simulation.py
ILbuy 本地多模态商品助手 - 无需外部 API 密钥的生产级测试系统

支持四种输入模式：
  - text  : 文字查询
  - voice : 语音输入（本地模拟 ASR）
  - image : 图片输入（本地模拟图像识别）
  - link  : 商品链接解析

运行方式：
  python local_simulation.py        # 快速演示
  python local_simulation.py test   # 综合测试
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import random
import re
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse, unquote

try:
    import requests as _req
    _HAS_REQUESTS = True
except ImportError:
    _HAS_REQUESTS = False

GATEWAY_URL = "http://localhost:8080"
BUYER_USERNAME = "buyer01"
BUYER_PASSWORD = "Test@123456"


# ── Fallback local product data (used when ILbuy gateway is unreachable) ─────
LOCAL_PRODUCTS: list[dict] = [
    {'$schema': 'https://ecommerce-product-schema.com/v2.0', 'version': '2.0', 'platform': 'taobao', 'id': 'TB_V2_001', 'title': '联想ThinkPad E14 Gen5 笔记本电脑 i7-1355U 16G 512G SSD', 'price': 5299.0, 'originalPrice': 5999.0, 'discount': 0.883, 'stock': 485, 'sales': 3200, 'image': 'https://img.alicdn.com/tb_v2_001_main.jpg', 'category': '电脑办公', 'brand': '联想', 'shopName': '联想官方旗舰店', 'platformName': '淘宝', 'basicInfo': {'product_id': 'TB_V2_001', 'platform_product_id': 'taobao_TB_V2_001', 'spu_id': 'SPU_TB_V2_001', 'title': '联想ThinkPad E14 Gen5 笔记本电脑 i7-1355U 16G 512G SSD', 'subtitle': '官方正品 24期免息 企业大客户专属价', 'description': 'ThinkPad E14 Gen5商务本，军规认证，14寸2.2K屏，i7处理器，适合企业批量采购。', 'category': {'main_category': '电脑办公', 'sub_category': '笔记本电脑', 'third_category': '商务办公本'}, 'brand': {'id': 'B001', 'name': '联想', 'logo_url': 'https://img.ilbuy.com/brand/B001.png'}, 'origin': {'country': '中国', 'region': '北京', 'is_imported': False}, 'labels': ['企业专供', '24期免息', '7天退货'], 'certifications': ['3C认证', '能效认证', '军规MIL-STD-810H'], 'status': 'on_sale'}, 'priceInfo': {'current_price': 5299.0, 'original_price': 5999.0, 'discount': 0.883, 'discount_text': '8.8折', 'price_range': {'min': 4999.0, 'max': 5799.0}, 'currency': 'CNY', 'vat_included': True, 'platform_promotion': {'type': 'coupon', 'discount_amount': 700.0, 'discount_rule': '限时优惠'}, 'merchant_promotion': {'type': 'gift', 'details': '购买赠礼品'}}, 'inventory': {'stock_quantity': 485, 'available_quantity': 480, 'sold_quantity': 3200, 'sku_stock_info': {'SKU_TP_I5': {'stock': 150, 'available': 148}, 'SKU_TP_I7': {'stock': 200, 'available': 198}, 'SKU_TP_I7P': {'stock': 135, 'available': 133}}, 'warehouse_info': {'location': '北京仓', 'ship_from': '北京'}}, 'merchant': {'shop_id': 'SHOP_LX_001', 'shop_name': '联想官方旗舰店', 'shop_logo': 'https://img.ilbuy.com/shop/SHOP_LX_001.png', 'shop_rating': 4.9, 'shop_level': '天猫超级旗舰', 'follower_count': 625000, 'is_official': True, 'is_verified': True, 'location': '北京'}, 'ratingSummary': {'averageScore': 4.8, 'totalReviews': 12500, 'positiveRate': 0.976}, 'salesMetrics': {'monthly_sales': 850, 'total_sales': 3200, 'sales_volume': 16956800.0, 'conversion_rate': 0.065, 'view_count': 48000, 'favorite_count': 1066, 'cart_addition_count': 1600}},
    {'$schema': 'https://ecommerce-product-schema.com/v2.0', 'version': '2.0', 'platform': 'taobao', 'id': 'TB_V2_002', 'title': '惠普HP LaserJet MFP M429dw 黑白激光打印机 自动双面 无线WiFi', 'price': 2350.0, 'originalPrice': 2699.0, 'discount': 0.871, 'stock': 320, 'sales': 1850, 'image': 'https://img.alicdn.com/tb_v2_002_main.jpg', 'category': '电脑办公', 'brand': '惠普', 'shopName': '惠普官方旗舰店', 'platformName': '淘宝', 'basicInfo': {'product_id': 'TB_V2_002', 'platform_product_id': 'taobao_TB_V2_002', 'spu_id': 'SPU_TB_V2_002', 'title': '惠普HP LaserJet MFP M429dw 黑白激光打印机 自动双面 无线WiFi', 'subtitle': '企业办公首选 支持增值税发票', 'description': 'HP LaserJet M429dw黑白多功能打印机，40ppm高速打印，支持WiFi无线连接。', 'category': {'main_category': '电脑办公', 'sub_category': '打印机/一体机', 'third_category': '激光打印机'}, 'brand': {'id': 'B002', 'name': '惠普', 'logo_url': 'https://img.ilbuy.com/brand/B002.png'}, 'origin': {'country': '中国', 'region': '上海', 'is_imported': False}, 'labels': ['企业开票', '以旧换新', '7天退货'], 'certifications': ['3C认证', '能效标识'], 'status': 'on_sale'}, 'priceInfo': {'current_price': 2350.0, 'original_price': 2699.0, 'discount': 0.871, 'discount_text': '8.7折', 'price_range': {'min': 2350.0, 'max': 2350.0}, 'currency': 'CNY', 'vat_included': True, 'platform_promotion': {'type': 'coupon', 'discount_amount': 349.0, 'discount_rule': '限时优惠'}, 'merchant_promotion': {'type': 'gift', 'details': '购买赠礼品'}}, 'inventory': {'stock_quantity': 320, 'available_quantity': 315, 'sold_quantity': 1850, 'sku_stock_info': {'SKU_M429DW': {'stock': 320, 'available': 318}}, 'warehouse_info': {'location': '上海仓', 'ship_from': '上海'}}, 'merchant': {'shop_id': 'SHOP_HP_001', 'shop_name': '惠普官方旗舰店', 'shop_logo': 'https://img.ilbuy.com/shop/SHOP_HP_001.png', 'shop_rating': 4.8, 'shop_level': '天猫超级旗舰', 'follower_count': 280000, 'is_official': True, 'is_verified': True, 'location': '上海'}, 'ratingSummary': {'averageScore': 4.7, 'totalReviews': 5600, 'positiveRate': 0.958}, 'salesMetrics': {'monthly_sales': 420, 'total_sales': 1850, 'sales_volume': 4347500.0, 'conversion_rate': 0.065, 'view_count': 27750, 'favorite_count': 616, 'cart_addition_count': 925}},
    {'$schema': 'https://ecommerce-product-schema.com/v2.0', 'version': '2.0', 'platform': 'tmall', 'id': 'TM_V2_001', 'title': 'Apple MacBook Pro 14寸 M3 Pro芯片 18G 512G 深空黑', 'price': 14999.0, 'originalPrice': 15999.0, 'discount': 0.937, 'stock': 180, 'sales': 1800, 'image': 'https://img.tmall.com/tm_v2_001_main.jpg', 'category': '电脑办公', 'brand': '苹果', 'shopName': 'Apple官方旗舰店', 'platformName': '天猫', 'basicInfo': {'product_id': 'TM_V2_001', 'platform_product_id': 'tmall_TM_V2_001', 'spu_id': 'SPU_TM_V2_001', 'title': 'Apple MacBook Pro 14寸 M3 Pro芯片 18G 512G 深空黑', 'subtitle': '官方正品 Apple Care+ 可选', 'description': 'MacBook Pro 14寸，M3 Pro芯片，Liquid Retina XDR屏幕，18小时续航。', 'category': {'main_category': '电脑办公', 'sub_category': '笔记本电脑', 'third_category': '高性能本'}, 'brand': {'id': 'B003', 'name': '苹果', 'logo_url': 'https://img.ilbuy.com/brand/B003.png'}, 'origin': {'country': '中国', 'region': '郑州', 'is_imported': False}, 'labels': ['Apple官方授权', '以旧换新', '24期免息'], 'certifications': ['3C认证', 'FCC认证'], 'status': 'on_sale'}, 'priceInfo': {'current_price': 14999.0, 'original_price': 15999.0, 'discount': 0.937, 'discount_text': '9.4折', 'price_range': {'min': 14999.0, 'max': 17499.0}, 'currency': 'CNY', 'vat_included': True, 'platform_promotion': {'type': 'coupon', 'discount_amount': 1000.0, 'discount_rule': '限时优惠'}, 'merchant_promotion': {'type': 'gift', 'details': '购买赠礼品'}}, 'inventory': {'stock_quantity': 180, 'available_quantity': 175, 'sold_quantity': 1800, 'sku_stock_info': {'SKU_MBP14_512': {'stock': 80, 'available': 78}, 'SKU_MBP14_1T': {'stock': 60, 'available': 58}}, 'warehouse_info': {'location': '上海仓', 'ship_from': '上海'}}, 'merchant': {'shop_id': 'SHOP_APPLE_001', 'shop_name': 'Apple官方旗舰店', 'shop_logo': 'https://img.ilbuy.com/shop/SHOP_APPLE_001.png', 'shop_rating': 4.95, 'shop_level': '天猫超级旗舰', 'follower_count': 445000, 'is_official': True, 'is_verified': True, 'location': '上海'}, 'ratingSummary': {'averageScore': 4.9, 'totalReviews': 8900, 'positiveRate': 0.989}, 'salesMetrics': {'monthly_sales': 320, 'total_sales': 1800, 'sales_volume': 26998200.0, 'conversion_rate': 0.065, 'view_count': 27000, 'favorite_count': 600, 'cart_addition_count': 900}},
    {'$schema': 'https://ecommerce-product-schema.com/v2.0', 'version': '2.0', 'platform': 'tmall', 'id': 'TM_V2_002', 'title': '西昊S300人体工学椅 电脑椅老板椅 4D扶手 企业团购', 'price': 2399.0, 'originalPrice': 2899.0, 'discount': 0.828, 'stock': 580, 'sales': 15600, 'image': 'https://img.tmall.com/tm_v2_002_main.jpg', 'category': '家具家居', 'brand': '西昊', 'shopName': '西昊官方旗舰店', 'platformName': '天猫', 'basicInfo': {'product_id': 'TM_V2_002', 'platform_product_id': 'tmall_TM_V2_002', 'spu_id': 'SPU_TM_V2_002', 'title': '西昊S300人体工学椅 电脑椅老板椅 4D扶手 企业团购', 'subtitle': '人体工程学设计 30天试坐', 'description': '西昊S300人体工学椅，4D扶手调节，3段腰托，超厚座垫，适合久坐办公。', 'category': {'main_category': '家具家居', 'sub_category': '办公家具', 'third_category': '人体工学椅'}, 'brand': {'id': 'B004', 'name': '西昊', 'logo_url': 'https://img.ilbuy.com/brand/B004.png'}, 'origin': {'country': '中国', 'region': '广东佛山', 'is_imported': False}, 'labels': ['人体工学', '企业团购', '30天试坐'], 'certifications': ['BIFMA认证', 'ISO9001'], 'status': 'on_sale'}, 'priceInfo': {'current_price': 2399.0, 'original_price': 2899.0, 'discount': 0.828, 'discount_text': '8.3折', 'price_range': {'min': 2399.0, 'max': 2399.0}, 'currency': 'CNY', 'vat_included': True, 'platform_promotion': {'type': 'coupon', 'discount_amount': 500.0, 'discount_rule': '限时优惠'}, 'merchant_promotion': {'type': 'gift', 'details': '购买赠礼品'}}, 'inventory': {'stock_quantity': 580, 'available_quantity': 575, 'sold_quantity': 15600, 'sku_stock_info': {'SKU_S300_BK': {'stock': 280, 'available': 278}, 'SKU_S300_GY': {'stock': 180, 'available': 178}}, 'warehouse_info': {'location': '广东省仓', 'ship_from': '广东省'}}, 'merchant': {'shop_id': 'SHOP_SIHOO_001', 'shop_name': '西昊官方旗舰店', 'shop_logo': 'https://img.ilbuy.com/shop/SHOP_SIHOO_001.png', 'shop_rating': 4.85, 'shop_level': '天猫旗舰', 'follower_count': 1400000, 'is_official': True, 'is_verified': True, 'location': '广东省'}, 'ratingSummary': {'averageScore': 4.85, 'totalReviews': 28000, 'positiveRate': 0.975}, 'salesMetrics': {'monthly_sales': 1800, 'total_sales': 15600, 'sales_volume': 37424400.0, 'conversion_rate': 0.065, 'view_count': 234000, 'favorite_count': 5200, 'cart_addition_count': 7800}},
    {'$schema': 'https://ecommerce-product-schema.com/v2.0', 'version': '2.0', 'platform': 'jd', 'id': 'JD_V2_001', 'title': 'Dell PowerEdge R750xa服务器 Gold6346×2 64G DDR4 3.84T SSD', 'price': 28800.0, 'originalPrice': 32000.0, 'discount': 0.9, 'stock': 15, 'sales': 320, 'image': 'https://img.jd.com/jd_v2_001_main.jpg', 'category': 'IT设备', 'brand': '戴尔', 'shopName': '戴尔企业官方旗舰店', 'platformName': '京东', 'basicInfo': {'product_id': 'JD_V2_001', 'platform_product_id': 'jd_JD_V2_001', 'spu_id': 'SPU_JD_V2_001', 'title': 'Dell PowerEdge R750xa服务器 Gold6346×2 64G DDR4 3.84T SSD', 'subtitle': '企业级高性能服务器 7×24小时服务', 'description': 'Dell PowerEdge R750xa企业级服务器，双路Xeon Gold，适合数据中心部署。', 'category': {'main_category': 'IT设备', 'sub_category': '服务器', 'third_category': '企业级机架服务器'}, 'brand': {'id': 'B_DELL', 'name': '戴尔', 'logo_url': 'https://img.ilbuy.com/brand/B_DELL.png'}, 'origin': {'country': '中国', 'region': '北京', 'is_imported': False}, 'labels': ['企业专供', '增值税发票', '7×24客服'], 'certifications': ['3C认证', 'CE认证'], 'status': 'on_sale'}, 'priceInfo': {'current_price': 28800.0, 'original_price': 32000.0, 'discount': 0.9, 'discount_text': '9.0折', 'price_range': {'min': 28800.0, 'max': 28800.0}, 'currency': 'CNY', 'vat_included': True, 'platform_promotion': {'type': 'coupon', 'discount_amount': 3200.0, 'discount_rule': '限时优惠'}, 'merchant_promotion': {'type': 'gift', 'details': '购买赠礼品'}}, 'inventory': {'stock_quantity': 15, 'available_quantity': 10, 'sold_quantity': 320, 'sku_stock_info': {'SKU_R750_64': {'stock': 15, 'available': 13}}, 'warehouse_info': {'location': '北京仓', 'ship_from': '北京'}}, 'merchant': {'shop_id': 'SHOP_DELL_JD', 'shop_name': '戴尔企业官方旗舰店', 'shop_logo': 'https://img.ilbuy.com/shop/SHOP_DELL_JD.png', 'shop_rating': 4.9, 'shop_level': '京东超级旗舰', 'follower_count': 92500, 'is_official': True, 'is_verified': True, 'location': '北京'}, 'ratingSummary': {'averageScore': 4.8, 'totalReviews': 1850, 'positiveRate': 0.972}, 'salesMetrics': {'monthly_sales': 62, 'total_sales': 320, 'sales_volume': 9216000.0, 'conversion_rate': 0.065, 'view_count': 4800, 'favorite_count': 106, 'cart_addition_count': 160}},
    {'$schema': 'https://ecommerce-product-schema.com/v2.0', 'version': '2.0', 'platform': 'jd', 'id': 'JD_V2_002', 'title': '思科Cisco Catalyst 9200L-48P 48口PoE千兆交换机 企业级', 'price': 12800.0, 'originalPrice': 14500.0, 'discount': 0.883, 'stock': 35, 'sales': 680, 'image': 'https://img.jd.com/jd_v2_002_main.jpg', 'category': 'IT设备', 'brand': '思科', 'shopName': '思科网络官方旗舰店', 'platformName': '京东', 'basicInfo': {'product_id': 'JD_V2_002', 'platform_product_id': 'jd_JD_V2_002', 'spu_id': 'SPU_JD_V2_002', 'title': '思科Cisco Catalyst 9200L-48P 48口PoE千兆交换机 企业级', 'subtitle': '企业级托管交换机 PoE供电', 'description': '思科Catalyst 9200L 48口PoE交换机，802.3at标准，适合企业园区网络。', 'category': {'main_category': 'IT设备', 'sub_category': '网络设备', 'third_category': '以太网交换机'}, 'brand': {'id': 'B_CISCO', 'name': '思科', 'logo_url': 'https://img.ilbuy.com/brand/B_CISCO.png'}, 'origin': {'country': '中国', 'region': '上海', 'is_imported': False}, 'labels': ['企业网络', 'PoE供电', '官方正品'], 'certifications': ['FCC认证', 'CE认证'], 'status': 'on_sale'}, 'priceInfo': {'current_price': 12800.0, 'original_price': 14500.0, 'discount': 0.883, 'discount_text': '8.8折', 'price_range': {'min': 12800.0, 'max': 12800.0}, 'currency': 'CNY', 'vat_included': True, 'platform_promotion': {'type': 'coupon', 'discount_amount': 1700.0, 'discount_rule': '限时优惠'}, 'merchant_promotion': {'type': 'gift', 'details': '购买赠礼品'}}, 'inventory': {'stock_quantity': 35, 'available_quantity': 30, 'sold_quantity': 680, 'sku_stock_info': {'SKU_C9200L': {'stock': 35, 'available': 33}}, 'warehouse_info': {'location': '上海仓', 'ship_from': '上海'}}, 'merchant': {'shop_id': 'SHOP_CISCO_JD', 'shop_name': '思科网络官方旗舰店', 'shop_logo': 'https://img.ilbuy.com/shop/SHOP_CISCO_JD.png', 'shop_rating': 4.85, 'shop_level': '京东旗舰', 'follower_count': 160000, 'is_official': True, 'is_verified': True, 'location': '上海'}, 'ratingSummary': {'averageScore': 4.82, 'totalReviews': 3200, 'positiveRate': 0.968}, 'salesMetrics': {'monthly_sales': 120, 'total_sales': 680, 'sales_volume': 8704000.0, 'conversion_rate': 0.065, 'view_count': 10200, 'favorite_count': 226, 'cart_addition_count': 340}},
    {'$schema': 'https://ecommerce-product-schema.com/v2.0', 'version': '2.0', 'platform': 'pinduoduo', 'id': 'PDD_V2_001', 'title': '永丰牌A4复印纸 70克 500张/包 整箱10包装', 'price': 135.0, 'originalPrice': 168.0, 'discount': 0.804, 'stock': 5000, 'sales': 56000, 'image': 'https://img.pinduoduo.com/pdd_v2_001_main.jpg', 'category': '办公用品', 'brand': '永丰', 'shopName': '永丰纸业官方专营店', 'platformName': '拼多多', 'basicInfo': {'product_id': 'PDD_V2_001', 'platform_product_id': 'pinduoduo_PDD_V2_001', 'spu_id': 'SPU_PDD_V2_001', 'title': '永丰牌A4复印纸 70克 500张/包 整箱10包装', 'subtitle': '白度≥92% 适合激光/喷墨/复印机', 'description': '永丰A4复印纸，白度≥92%，适合所有复印机和打印机，整箱性价比高。', 'category': {'main_category': '办公用品', 'sub_category': '纸张/标签', 'third_category': '复印纸'}, 'brand': {'id': 'B_YF', 'name': '永丰', 'logo_url': 'https://img.ilbuy.com/brand/B_YF.png'}, 'origin': {'country': '中国', 'region': '广东东莞', 'is_imported': False}, 'labels': ['拼单优惠', '工厂直供', '企业发票'], 'certifications': ['ISO9001', '中国环境标志'], 'status': 'on_sale'}, 'priceInfo': {'current_price': 135.0, 'original_price': 168.0, 'discount': 0.804, 'discount_text': '8.0折', 'price_range': {'min': 135.0, 'max': 135.0}, 'currency': 'CNY', 'vat_included': True, 'platform_promotion': {'type': 'coupon', 'discount_amount': 33.0, 'discount_rule': '限时优惠'}, 'merchant_promotion': {'type': 'gift', 'details': '购买赠礼品'}}, 'inventory': {'stock_quantity': 5000, 'available_quantity': 4995, 'sold_quantity': 56000, 'sku_stock_info': {'SKU_A4_70G': {'stock': 5000, 'available': 4998}}, 'warehouse_info': {'location': '广东省仓', 'ship_from': '广东省'}}, 'merchant': {'shop_id': 'SHOP_YF_PDD', 'shop_name': '永丰纸业官方专营店', 'shop_logo': 'https://img.ilbuy.com/shop/SHOP_YF_PDD.png', 'shop_rating': 4.75, 'shop_level': '拼多多旗舰', 'follower_count': 1900000, 'is_official': True, 'is_verified': True, 'location': '广东省'}, 'ratingSummary': {'averageScore': 4.6, 'totalReviews': 38000, 'positiveRate': 0.934}, 'salesMetrics': {'monthly_sales': 4200, 'total_sales': 56000, 'sales_volume': 7560000.0, 'conversion_rate': 0.065, 'view_count': 840000, 'favorite_count': 18666, 'cart_addition_count': 28000}},
    {'$schema': 'https://ecommerce-product-schema.com/v2.0', 'version': '2.0', 'platform': 'pinduoduo', 'id': 'PDD_V2_002', 'title': '晨光中性笔 0.5mm黑色 100支装 签字笔水笔碳素笔', 'price': 28.9, 'originalPrice': 38.0, 'discount': 0.761, 'stock': 8000, 'sales': 230000, 'image': 'https://img.pinduoduo.com/pdd_v2_002_main.jpg', 'category': '办公用品', 'brand': '晨光', 'shopName': '晨光文具官方专营店', 'platformName': '拼多多', 'basicInfo': {'product_id': 'PDD_V2_002', 'platform_product_id': 'pinduoduo_PDD_V2_002', 'spu_id': 'SPU_PDD_V2_002', 'title': '晨光中性笔 0.5mm黑色 100支装 签字笔水笔碳素笔', 'subtitle': '书写流畅 墨水均匀 企业批发', 'description': '晨光中性笔0.5mm，书写流畅，100支装适合企业批量采购。', 'category': {'main_category': '办公用品', 'sub_category': '笔类', 'third_category': '中性笔'}, 'brand': {'id': 'B_CG', 'name': '晨光', 'logo_url': 'https://img.ilbuy.com/brand/B_CG.png'}, 'origin': {'country': '中国', 'region': '上海', 'is_imported': False}, 'labels': ['拼单优惠', '国民品牌', '100支装'], 'certifications': ['ISO9001'], 'status': 'on_sale'}, 'priceInfo': {'current_price': 28.9, 'original_price': 38.0, 'discount': 0.761, 'discount_text': '7.6折', 'price_range': {'min': 28.9, 'max': 28.9}, 'currency': 'CNY', 'vat_included': True, 'platform_promotion': {'type': 'coupon', 'discount_amount': 9.1, 'discount_rule': '限时优惠'}, 'merchant_promotion': {'type': 'gift', 'details': '购买赠礼品'}}, 'inventory': {'stock_quantity': 8000, 'available_quantity': 7995, 'sold_quantity': 230000, 'sku_stock_info': {'SKU_PEN_BK': {'stock': 8000, 'available': 7998}, 'SKU_PEN_BL': {'stock': 3000, 'available': 2998}}, 'warehouse_info': {'location': '上海仓', 'ship_from': '上海'}}, 'merchant': {'shop_id': 'SHOP_CG_PDD', 'shop_name': '晨光文具官方专营店', 'shop_logo': 'https://img.ilbuy.com/shop/SHOP_CG_PDD.png', 'shop_rating': 4.7, 'shop_level': '拼多多旗舰', 'follower_count': 4450000, 'is_official': True, 'is_verified': True, 'location': '上海'}, 'ratingSummary': {'averageScore': 4.5, 'totalReviews': 89000, 'positiveRate': 0.921}, 'salesMetrics': {'monthly_sales': 8500, 'total_sales': 230000, 'sales_volume': 6647000.0, 'conversion_rate': 0.065, 'view_count': 3450000, 'favorite_count': 76666, 'cart_addition_count': 115000}},
    {'$schema': 'https://ecommerce-product-schema.com/v2.0', 'version': '2.0', 'platform': 'douyin', 'id': 'DY_V2_001', 'title': '华为Mate 60 Pro+ 手机 16GB+1TB 砚黑 卫星通话', 'price': 9999.0, 'originalPrice': 10999.0, 'discount': 0.909, 'stock': 320, 'sales': 8900, 'image': 'https://img.douyin.com/dy_v2_001_main.jpg', 'category': '手机通讯', 'brand': '华为', 'shopName': '华为官方旗舰店', 'platformName': '抖音', 'basicInfo': {'product_id': 'DY_V2_001', 'platform_product_id': 'douyin_DY_V2_001', 'spu_id': 'SPU_DY_V2_001', 'title': '华为Mate 60 Pro+ 手机 16GB+1TB 砚黑 卫星通话', 'subtitle': '卫星通话 昆仑玻璃 徕卡影像', 'description': '华为Mate 60 Pro+，麒麟9000S，支持卫星通话，徕卡专业影像。', 'category': {'main_category': '手机通讯', 'sub_category': '手机', 'third_category': '智能手机'}, 'brand': {'id': 'B_HW', 'name': '华为', 'logo_url': 'https://img.ilbuy.com/brand/B_HW.png'}, 'origin': {'country': '中国', 'region': '广东深圳', 'is_imported': False}, 'labels': ['官方旗舰', '以旧换新', '分期免息'], 'certifications': ['3C认证', 'SAR检测'], 'status': 'on_sale'}, 'priceInfo': {'current_price': 9999.0, 'original_price': 10999.0, 'discount': 0.909, 'discount_text': '9.1折', 'price_range': {'min': 8999.0, 'max': 9999.0}, 'currency': 'CNY', 'vat_included': True, 'platform_promotion': {'type': 'coupon', 'discount_amount': 1000.0, 'discount_rule': '限时优惠'}, 'merchant_promotion': {'type': 'gift', 'details': '购买赠礼品'}}, 'inventory': {'stock_quantity': 320, 'available_quantity': 315, 'sold_quantity': 8900, 'sku_stock_info': {'SKU_M60PP_1T': {'stock': 120, 'available': 118}, 'SKU_M60PP_512': {'stock': 200, 'available': 198}}, 'warehouse_info': {'location': '广东省仓', 'ship_from': '广东省'}}, 'merchant': {'shop_id': 'SHOP_HW_DY', 'shop_name': '华为官方旗舰店', 'shop_logo': 'https://img.ilbuy.com/shop/SHOP_HW_DY.png', 'shop_rating': 4.92, 'shop_level': '抖音旗舰', 'follower_count': 2800000, 'is_official': True, 'is_verified': True, 'location': '广东省'}, 'ratingSummary': {'averageScore': 4.88, 'totalReviews': 56000, 'positiveRate': 0.981}, 'salesMetrics': {'monthly_sales': 1200, 'total_sales': 8900, 'sales_volume': 88991100.0, 'conversion_rate': 0.065, 'view_count': 133500, 'favorite_count': 2966, 'cart_addition_count': 4450}},
    {'$schema': 'https://ecommerce-product-schema.com/v2.0', 'version': '2.0', 'platform': 'douyin', 'id': 'DY_V2_002', 'title': '小米14 Ultra 手机 16GB+512GB 白色 徕卡影像旗舰', 'price': 5999.0, 'originalPrice': 6499.0, 'discount': 0.923, 'stock': 580, 'sales': 23000, 'image': 'https://img.douyin.com/dy_v2_002_main.jpg', 'category': '手机通讯', 'brand': '小米', 'shopName': '小米官方旗舰店', 'platformName': '抖音', 'basicInfo': {'product_id': 'DY_V2_002', 'platform_product_id': 'douyin_DY_V2_002', 'spu_id': 'SPU_DY_V2_002', 'title': '小米14 Ultra 手机 16GB+512GB 白色 徕卡影像旗舰', 'subtitle': '骁龙8 Gen3 小米澎湃OS 24期免息', 'description': '小米14 Ultra，骁龙8 Gen3，徕卡联合调校影像，IP68防水。', 'category': {'main_category': '手机通讯', 'sub_category': '手机', 'third_category': '智能手机'}, 'brand': {'id': 'B_MI', 'name': '小米', 'logo_url': 'https://img.ilbuy.com/brand/B_MI.png'}, 'origin': {'country': '中国', 'region': '北京', 'is_imported': False}, 'labels': ['官方旗舰', '以旧换新', '24期免息'], 'certifications': ['3C认证'], 'status': 'on_sale'}, 'priceInfo': {'current_price': 5999.0, 'original_price': 6499.0, 'discount': 0.923, 'discount_text': '9.2折', 'price_range': {'min': 5999.0, 'max': 5999.0}, 'currency': 'CNY', 'vat_included': True, 'platform_promotion': {'type': 'coupon', 'discount_amount': 500.0, 'discount_rule': '限时优惠'}, 'merchant_promotion': {'type': 'gift', 'details': '购买赠礼品'}}, 'inventory': {'stock_quantity': 580, 'available_quantity': 575, 'sold_quantity': 23000, 'sku_stock_info': {'SKU_MI14U_W': {'stock': 250, 'available': 248}, 'SKU_MI14U_B': {'stock': 330, 'available': 328}}, 'warehouse_info': {'location': '北京仓', 'ship_from': '北京'}}, 'merchant': {'shop_id': 'SHOP_MI_DY', 'shop_name': '小米官方旗舰店', 'shop_logo': 'https://img.ilbuy.com/shop/SHOP_MI_DY.png', 'shop_rating': 4.85, 'shop_level': '抖音旗舰', 'follower_count': 4450000, 'is_official': True, 'is_verified': True, 'location': '北京'}, 'ratingSummary': {'averageScore': 4.82, 'totalReviews': 89000, 'positiveRate': 0.974}, 'salesMetrics': {'monthly_sales': 3500, 'total_sales': 23000, 'sales_volume': 137977000.0, 'conversion_rate': 0.065, 'view_count': 345000, 'favorite_count': 7666, 'cart_addition_count': 11500}},
    {'$schema': 'https://ecommerce-product-schema.com/v2.0', 'version': '2.0', 'platform': 'vip', 'id': 'VIP_V2_001', 'title': '李宁赤兔6 PRO 男跑步鞋 碳板竞速 马拉松专业跑鞋', 'price': 649.0, 'originalPrice': 899.0, 'discount': 0.722, 'stock': 850, 'sales': 35000, 'image': 'https://img.vip.com/vip_v2_001_main.jpg', 'category': '运动户外', 'brand': '李宁', 'shopName': '李宁官方旗舰店', 'platformName': '唯品会', 'basicInfo': {'product_id': 'VIP_V2_001', 'platform_product_id': 'vip_VIP_V2_001', 'spu_id': 'SPU_VIP_V2_001', 'title': '李宁赤兔6 PRO 男跑步鞋 碳板竞速 马拉松专业跑鞋', 'subtitle': '䨻+碳板 超弹回 轻至206g', 'description': '李宁赤兔6 PRO碳板竞速跑鞋，超弹回弹，鞋重206g，助力PB。', 'category': {'main_category': '运动户外', 'sub_category': '跑步鞋', 'third_category': '专业竞速跑鞋'}, 'brand': {'id': 'B_LN', 'name': '李宁', 'logo_url': 'https://img.ilbuy.com/brand/B_LN.png'}, 'origin': {'country': '中国', 'region': '广东广州', 'is_imported': False}, 'labels': ['品牌特卖', '限时折扣', '专业竞速'], 'certifications': ['ISO9001'], 'status': 'on_sale'}, 'priceInfo': {'current_price': 649.0, 'original_price': 899.0, 'discount': 0.722, 'discount_text': '7.2折', 'price_range': {'min': 649.0, 'max': 649.0}, 'currency': 'CNY', 'vat_included': True, 'platform_promotion': {'type': 'coupon', 'discount_amount': 250.0, 'discount_rule': '限时优惠'}, 'merchant_promotion': {'type': 'gift', 'details': '购买赠礼品'}}, 'inventory': {'stock_quantity': 850, 'available_quantity': 845, 'sold_quantity': 35000, 'sku_stock_info': {'SKU_CT6P_40': {'stock': 120, 'available': 118}, 'SKU_CT6P_42': {'stock': 300, 'available': 298}, 'SKU_CT6P_44': {'stock': 200, 'available': 198}}, 'warehouse_info': {'location': '广东省仓', 'ship_from': '广东省'}}, 'merchant': {'shop_id': 'SHOP_LN_VIP', 'shop_name': '李宁官方旗舰店', 'shop_logo': 'https://img.ilbuy.com/shop/SHOP_LN_VIP.png', 'shop_rating': 4.88, 'shop_level': '唯品会旗舰', 'follower_count': 1400000, 'is_official': True, 'is_verified': True, 'location': '广东省'}, 'ratingSummary': {'averageScore': 4.78, 'totalReviews': 28000, 'positiveRate': 0.965}, 'salesMetrics': {'monthly_sales': 2800, 'total_sales': 35000, 'sales_volume': 22715000.0, 'conversion_rate': 0.065, 'view_count': 525000, 'favorite_count': 11666, 'cart_addition_count': 17500}},
    {'$schema': 'https://ecommerce-product-schema.com/v2.0', 'version': '2.0', 'platform': 'vip', 'id': 'VIP_V2_002', 'title': '优衣库UNIQLO 男士羽绒服 Ultra Light Down 550蓬 轻量保暖', 'price': 499.0, 'originalPrice': 699.0, 'discount': 0.714, 'stock': 1200, 'sales': 68000, 'image': 'https://img.vip.com/vip_v2_002_main.jpg', 'category': '服装', 'brand': '优衣库', 'shopName': 'UNIQLO优衣库旗舰店', 'platformName': '唯品会', 'basicInfo': {'product_id': 'VIP_V2_002', 'platform_product_id': 'vip_VIP_V2_002', 'spu_id': 'SPU_VIP_V2_002', 'title': '优衣库UNIQLO 男士羽绒服 Ultra Light Down 550蓬 轻量保暖', 'subtitle': '超轻便携 可折叠 多色可选', 'description': '优衣库超轻量羽绒服，550蓬，100%白鸭绒，可折叠收纳，轻便保暖。', 'category': {'main_category': '服装', 'sub_category': '男装', 'third_category': '羽绒服'}, 'brand': {'id': 'B_UQ', 'name': '优衣库', 'logo_url': 'https://img.ilbuy.com/brand/B_UQ.png'}, 'origin': {'country': '中国', 'region': '上海', 'is_imported': False}, 'labels': ['品牌特卖', '超轻便携', '多色'], 'certifications': ['ISO9001'], 'status': 'on_sale'}, 'priceInfo': {'current_price': 499.0, 'original_price': 699.0, 'discount': 0.714, 'discount_text': '7.1折', 'price_range': {'min': 499.0, 'max': 499.0}, 'currency': 'CNY', 'vat_included': True, 'platform_promotion': {'type': 'coupon', 'discount_amount': 200.0, 'discount_rule': '限时优惠'}, 'merchant_promotion': {'type': 'gift', 'details': '购买赠礼品'}}, 'inventory': {'stock_quantity': 1200, 'available_quantity': 1195, 'sold_quantity': 68000, 'sku_stock_info': {'SKU_ULD_S': {'stock': 300, 'available': 298}, 'SKU_ULD_M': {'stock': 400, 'available': 398}, 'SKU_ULD_L': {'stock': 250, 'available': 248}}, 'warehouse_info': {'location': '上海仓', 'ship_from': '上海'}}, 'merchant': {'shop_id': 'SHOP_UQ_VIP', 'shop_name': 'UNIQLO优衣库旗舰店', 'shop_logo': 'https://img.ilbuy.com/shop/SHOP_UQ_VIP.png', 'shop_rating': 4.82, 'shop_level': '唯品会旗舰', 'follower_count': 6750000, 'is_official': True, 'is_verified': True, 'location': '上海'}, 'ratingSummary': {'averageScore': 4.75, 'totalReviews': 135000, 'positiveRate': 0.958}, 'salesMetrics': {'monthly_sales': 5600, 'total_sales': 68000, 'sales_volume': 33932000.0, 'conversion_rate': 0.065, 'view_count': 1020000, 'favorite_count': 22666, 'cart_addition_count': 34000}},
    {'$schema': 'https://ecommerce-product-schema.com/v2.0', 'version': '2.0', 'platform': '1688', 'id': 'ALI_V2_001', 'title': '304不锈钢板 冷轧2mm*1220mm*2440mm 零切定制', 'price': 28.5, 'originalPrice': 0.0, 'discount': 1.0, 'stock': 50000, 'sales': 2300, 'image': 'https://img.1688.com/ali_v2_001_main.jpg', 'category': '金属材料', 'brand': '宝钢', 'shopName': '宝钢钢材官方专营店', 'platformName': '阿里巴巴1688', 'basicInfo': {'product_id': 'ALI_V2_001', 'platform_product_id': '1688_ALI_V2_001', 'spu_id': 'SPU_ALI_V2_001', 'title': '304不锈钢板 冷轧2mm*1220mm*2440mm 零切定制', 'subtitle': '宝钢原料 Ra≤0.8 增值税发票', 'description': '宝钢304不锈钢冷轧板2mm，GB/T3280标准，可零切定制加工。', 'category': {'main_category': '金属材料', 'sub_category': '不锈钢', 'third_category': '不锈钢板'}, 'brand': {'id': 'B_BS', 'name': '宝钢', 'logo_url': 'https://img.ilbuy.com/brand/B_BS.png'}, 'origin': {'country': '中国', 'region': '上海宝山', 'is_imported': False}, 'labels': ['工厂直供', '量大优惠', '开增值税票'], 'certifications': ['GB/T3280-2015'], 'status': 'on_sale'}, 'priceInfo': {'current_price': 28.5, 'original_price': 0.0, 'discount': 1.0, 'discount_text': '10.0折', 'price_range': {'min': 28.5, 'max': 34.0}, 'currency': 'CNY', 'vat_included': True, 'platform_promotion': {'type': 'coupon', 'discount_amount': -28.5, 'discount_rule': '限时优惠'}, 'merchant_promotion': {'type': 'gift', 'details': '购买赠礼品'}}, 'inventory': {'stock_quantity': 50000, 'available_quantity': 49995, 'sold_quantity': 2300, 'sku_stock_info': {'SKU_304_2MM': {'stock': 50000, 'available': 49998}, 'SKU_304_3MM': {'stock': 30000, 'available': 29998}}, 'warehouse_info': {'location': '上海仓', 'ship_from': '上海'}}, 'merchant': {'shop_id': 'SHOP_BS_ALI', 'shop_name': '宝钢钢材官方专营店', 'shop_logo': 'https://img.ilbuy.com/shop/SHOP_BS_ALI.png', 'shop_rating': 4.78, 'shop_level': '金牌供应商', 'follower_count': 445000, 'is_official': True, 'is_verified': True, 'location': '上海'}, 'ratingSummary': {'averageScore': 4.65, 'totalReviews': 8900, 'positiveRate': 0.956}, 'salesMetrics': {'monthly_sales': 380, 'total_sales': 2300, 'sales_volume': 65550.0, 'conversion_rate': 0.065, 'view_count': 34500, 'favorite_count': 766, 'cart_addition_count': 1150}},
    {'$schema': 'https://ecommerce-product-schema.com/v2.0', 'version': '2.0', 'platform': '1688', 'id': 'ALI_V2_002', 'title': '欧姆龙OMRON MY2N-J DC24V 小型继电器 8脚插座式 原装正品', 'price': 12.8, 'originalPrice': 0.0, 'discount': 1.0, 'stock': 100000, 'sales': 68000, 'image': 'https://img.1688.com/ali_v2_002_main.jpg', 'category': '电子元件', 'brand': '欧姆龙', 'shopName': '欧姆龙电气授权店', 'platformName': '阿里巴巴1688', 'basicInfo': {'product_id': 'ALI_V2_002', 'platform_product_id': '1688_ALI_V2_002', 'spu_id': 'SPU_ALI_V2_002', 'title': '欧姆龙OMRON MY2N-J DC24V 小型继电器 8脚插座式 原装正品', 'subtitle': '寿命≥1000万次 触点5A 工厂直供', 'description': '欧姆龙MY2N-J小型继电器，DC24V，5A触点，1000万次寿命，适合工控自动化。', 'category': {'main_category': '电子元件', 'sub_category': '继电器', 'third_category': '小型继电器'}, 'brand': {'id': 'B_OR', 'name': '欧姆龙', 'logo_url': 'https://img.ilbuy.com/brand/B_OR.png'}, 'origin': {'country': '中国', 'region': '广东深圳', 'is_imported': False}, 'labels': ['原装正品', '量大从优', '企业采购'], 'certifications': ['UL认证', 'CE认证', 'CCC认证'], 'status': 'on_sale'}, 'priceInfo': {'current_price': 12.8, 'original_price': 0.0, 'discount': 1.0, 'discount_text': '10.0折', 'price_range': {'min': 12.8, 'max': 13.5}, 'currency': 'CNY', 'vat_included': True, 'platform_promotion': {'type': 'coupon', 'discount_amount': -12.8, 'discount_rule': '限时优惠'}, 'merchant_promotion': {'type': 'gift', 'details': '购买赠礼品'}}, 'inventory': {'stock_quantity': 100000, 'available_quantity': 99995, 'sold_quantity': 68000, 'sku_stock_info': {'SKU_MY2N_24V': {'stock': 100000, 'available': 99998}, 'SKU_MY2N_220V': {'stock': 80000, 'available': 79998}}, 'warehouse_info': {'location': '广东省仓', 'ship_from': '广东省'}}, 'merchant': {'shop_id': 'SHOP_OR_ALI', 'shop_name': '欧姆龙电气授权店', 'shop_logo': 'https://img.ilbuy.com/shop/SHOP_OR_ALI.png', 'shop_rating': 4.88, 'shop_level': '金牌供应商', 'follower_count': 1400000, 'is_official': True, 'is_verified': True, 'location': '广东省'}, 'ratingSummary': {'averageScore': 4.82, 'totalReviews': 28000, 'positiveRate': 0.978}, 'salesMetrics': {'monthly_sales': 5600, 'total_sales': 68000, 'sales_volume': 870400.0, 'conversion_rate': 0.065, 'view_count': 1020000, 'favorite_count': 22666, 'cart_addition_count': 34000}},
]

# Inject platform_specific into LOCAL_PRODUCTS so matched_products expose these fields
_PLATFORM_SPECIFIC_LOCAL: dict[str, dict] = {
    "taobao": {
        "platform": "taobao",
        "taobao_score": 4.9,
        "support_huabei": True,
        "support_baitiao": False,
        "supports_7day_return": True,
        "service_fee_rate": 0.005,
        "淘金币": 50,
    },
    "tmall": {
        "platform": "tmall",
        "tmall_score": 4.9,
        "annual_fee_cny": 60000,
        "is_super_brand": False,
        "supports_installment": True,
        "supports_7day_return": True,
        "tmall_genie_compatible": False,
    },
    "jd": {
        "platform": "jd",
        "jd_score": 4.8,
        "plus_price": None,
        "jd_logistics": True,
        "self_operated": True,
        "supports_30day_return": True,
        "jd_finance_installment": True,
    },
    "pinduoduo": {
        "platform": "pinduoduo",
        "百亿补贴": True,
        "秒杀": False,
        "supports_refund_only": True,
        "group_buy_price": None,
        "新人价": None,
        "credit_score": 4.85,
    },
    "douyin": {
        "platform": "douyin",
        "live_price": None,
        "supports_1h_delivery": False,
        "creator_commission_rate": 0.1,
        "video_commerce": True,
        "douyin_score": 4.7,
        "cart_link": None,
    },
    "vip": {
        "platform": "vip",
        "brand_sale": True,
        "authentic_guarantee": True,
        "vip_exclusive": True,
        "sale_discount": 0.7,
        "vip_score": 4.75,
        "supports_7day_return": True,
    },
    "1688": {
        "platform": "1688",
        "moq": 10,
        "price_tiers": [
            {"min_quantity": 10,  "price": 28.5},
            {"min_quantity": 100, "price": 26.0},
            {"min_quantity": 500, "price": 24.0},
        ],
        "is_manufacturer": True,
        "trade_assurance": True,
        "credit_score": 4.88,
        "supports_customization": True,
        "vat_invoice": True,
    },
}

for _p in LOCAL_PRODUCTS:
    if "platform_specific" not in _p:
        _p["platform_specific"] = _PLATFORM_SPECIFIC_LOCAL.get(_p.get("platform", ""), {})

LOCAL_MARKET_PRICES: list[dict] = [
    {"id": 1, "category": "IT设备", "productName": "商务笔记本电脑（i7/16G/512G）", "avgPrice": 6800.0, "minPrice": 4500.0, "maxPrice": 9800.0, "unit": "台"},
    {"id": 3, "category": "IT设备", "productName": "企业级服务器（Dell PowerEdge）", "avgPrice": 38000.0, "minPrice": 28000.0, "maxPrice": 65000.0, "unit": "台"},
    {"id": 7, "category": "办公用品", "productName": "A4复印纸（500张/包）", "avgPrice": 38.0, "minPrice": 25.0, "maxPrice": 55.0, "unit": "包"},
    {"id": 11, "category": "工业设备", "productName": "数控机床（三轴CNC）", "avgPrice": 85000.0, "minPrice": 60000.0, "maxPrice": 130000.0, "unit": "台"},
    {"id": 14, "category": "原材料", "productName": "不锈钢板（304# 2mm）", "avgPrice": 35.0, "minPrice": 22.0, "maxPrice": 52.0, "unit": "kg"},
    {"id": 16, "category": "电子元件", "productName": "工业级继电器模块", "avgPrice": 18.0, "minPrice": 8.0, "maxPrice": 32.0, "unit": "个"},
]


# ── ILbuy API client ──────────────────────────────────────────────────────────

class ILbuyClient:
    """HTTP client for the ILbuy API gateway. Falls back to local data on failure."""

    def __init__(self, base_url: str = GATEWAY_URL):
        self.base_url = base_url
        self._token: str | None = None
        self._available: bool | None = None  # None = not checked yet

    def _is_available(self) -> bool:
        if self._available is not None:
            return self._available
        if not _HAS_REQUESTS:
            self._available = False
            return False
        try:
            r = _req.get(f"{self.base_url}/actuator/health", timeout=2)
            self._available = r.status_code == 200
        except Exception:
            self._available = False
        return self._available

    def _login(self) -> str | None:
        if not _HAS_REQUESTS:
            return None
        try:
            r = _req.post(
                f"{self.base_url}/api/v1/auth/login",
                json={"username": BUYER_USERNAME, "password": BUYER_PASSWORD},
                timeout=5,
            )
            data = r.json()
            if data.get("code") == 0:
                return data["data"]["accessToken"]
        except Exception:
            pass
        return None

    def _headers(self) -> dict[str, str]:
        if self._token is None:
            self._token = self._login()
        return {"Authorization": f"Bearer {self._token}"} if self._token else {}

    def search_products(self, keyword: str = "", platform: str = "", category: str = "", page: int = 1, size: int = 10) -> list[dict]:
        if not self._is_available():
            return self._local_search_products(keyword, platform, category)
        try:
            params: dict[str, Any] = {"page": page, "size": size}
            if keyword:
                params["keyword"] = keyword
            if platform:
                params["platform"] = platform
            if category:
                params["category"] = category
            r = _req.get(f"{self.base_url}/api/v1/data/products", params=params, headers=self._headers(), timeout=5)
            data = r.json()
            if data.get("code") == 0:
                return data["data"].get("items", data["data"].get("content", []))
        except Exception:
            pass
        return self._local_search_products(keyword, platform, category)

    def get_market_prices(self, keyword: str = "", category: str = "") -> list[dict]:
        if not self._is_available():
            return self._local_market_prices(keyword, category)
        try:
            params: dict[str, Any] = {}
            if keyword:
                params["keyword"] = keyword
            if category:
                params["category"] = category
            r = _req.get(f"{self.base_url}/api/v1/data/market-prices", params=params, headers=self._headers(), timeout=5)
            data = r.json()
            if data.get("code") == 0:
                return data["data"].get("items", [])
        except Exception:
            pass
        return self._local_market_prices(keyword, category)

    # ── local fallbacks ───────────────────────────────────────────────────────

    @staticmethod
    def _local_search_products(keyword: str, platform: str, category: str) -> list[dict]:
        raw_tokens = re.split(r"[\uff0c,\u3002!?\s]+", keyword.lower().strip())
        tokens = [t for t in raw_tokens if len(t) >= 1]
        if not tokens and keyword:
            tokens = [keyword.lower()]
        results = []
        for p in LOCAL_PRODUCTS:
            if platform and p["platform"] != platform:
                continue
            # Support both v2.0 category field and legacy category
            p_category = p.get("category", "")
            if category and category not in p_category:
                continue
            score = 0
            title = p["title"].lower()
            # Support both v2.0 brand field name and legacy
            brand = p.get("brand", "").lower()
            shop  = p.get("shopName", "").lower()
            cat   = p_category.lower()
            for tok in tokens:
                if tok in title:
                    score += 3
                if tok in brand:
                    score += 2
                if tok in cat:
                    score += 2
                if tok in shop:
                    score += 1
            if tokens and score == 0:
                continue
            results.append((score, p))
        results.sort(key=lambda x: (-x[0], -x[1].get("sales", 0)))
        return [p for _, p in results]

    @staticmethod
    def _local_market_prices(keyword: str, category: str) -> list[dict]:
        kw = keyword.lower()
        cat = category.lower()
        return [
            mp for mp in LOCAL_MARKET_PRICES
            if (not kw or kw in mp["productName"].lower())
            and (not cat or cat in mp["category"].lower())
        ]


# ── Intent recognition ────────────────────────────────────────────────────────

class Intent:
    SEARCH = "SEARCH"
    PRICE_QUERY = "PRICE_QUERY"
    PURCHASE = "PURCHASE"
    COMPARE = "COMPARE"
    STOCK_CHECK = "STOCK_CHECK"
    UNKNOWN = "UNKNOWN"

_INTENT_RULES: list[tuple[str, list[str]]] = [
    (Intent.PURCHASE,    ["买", "购买", "想买", "采购", "下单", "订购", "要买"]),
    (Intent.PRICE_QUERY, ["多少钱", "价格", "价位", "报价", "行情", "多钱", "贵不贵", "市场价"]),
    (Intent.COMPARE,     ["对比", "比较", "哪个好", "有什么区别", "区别", "怎么选"]),
    (Intent.STOCK_CHECK, ["有货", "有货吗", "有没有", "库存", "有吗", "现货", "缺货"]),
    (Intent.SEARCH,      ["找", "搜索", "查找", "看看", "浏览", "推荐", "介绍", "帮我找"]),
]

_CATEGORY_HINTS: dict[str, list[str]] = {
    "IT设备":  ["电脑", "笔记本", "服务器", "打印机", "交换机", "路由器", "显示器", "显卡", "内存"],
    "办公用品": ["复印纸", "椅", "椅子", "办公椅", "桌子", "文件柜", "白板", "笔", "文具", "耗材", "办公"],
    "工业设备": ["机床", "电机", "液压", "变频器", "传感器", "气缸", "泵站", "工业", "设备"],
    "原材料":  ["钢板", "铝材", "铜材", "不锈钢", "铝合金", "钢材", "型材"],
    "电子元件": ["继电器", "芯片", "单片机", "传感器", "电阻", "电容", "模块", "mcu"],
}

def _extract_intent(text: str) -> str:
    t = text.lower()
    for intent, patterns in _INTENT_RULES:
        if any(p in t for p in patterns):
            return intent
    return Intent.UNKNOWN

def _extract_keywords(text: str) -> list[str]:
    """Simple keyword extraction: split on common delimiters and filter short tokens."""
    tokens = re.split(r"[，,。！？\s]+", text.strip())
    return [tok for tok in tokens if len(tok) >= 2]

def _infer_category(text: str) -> str:
    t = text.lower()
    for category, hints in _CATEGORY_HINTS.items():
        if any(h in t for h in hints):
            return category
    return ""


def _extract_search_term(text: str) -> str:
    """
    Extract the most searchable product keyword from a natural language query.
    Prefers shorter, general terms over longer compound words to improve DB match recall.
    Falls back to the last 2 CJK tokens.
    """
    t_lower = text.lower()
    candidates: list[str] = []
    for hints in _CATEGORY_HINTS.values():
        for hint in hints:
            if hint in t_lower and len(hint) >= 1:
                candidates.append(hint)
    if candidates:
        # Prefer longer hints (more specific) unless they are compound terms
        # that are unlikely to appear verbatim in product titles (len > 3)
        short = [c for c in candidates if len(c) <= 3]
        long  = [c for c in candidates if len(c) > 3]
        # Use the longest of the short ones (most specific yet likely to match)
        if short:
            return max(short, key=len)
        return max(long, key=len)
    # Fallback: last 2 non-trivial tokens
    tokens = [tok for tok in re.split(r"[\uff0c,\u3002!?\s]+", text.strip()) if len(tok) >= 2]
    return " ".join(tokens[-2:]) if tokens else text[:20]


# ── Text processor ────────────────────────────────────────────────────────────

class TextProcessor:
    def __init__(self, client: ILbuyClient):
        self.client = client

    async def process(self, text: str, session: dict) -> dict:
        await asyncio.sleep(0)  # yield to event loop
        intent = _extract_intent(text)
        keywords = _extract_keywords(text)
        category = _infer_category(text)

        # combine with session context for follow-up queries
        if intent == Intent.UNKNOWN and session.get("last_intent") not in (None, Intent.UNKNOWN):
            intent = session["last_intent"]
        search_term = _extract_search_term(text)

        if intent == Intent.PRICE_QUERY:
            prices = self.client.get_market_prices(keyword=search_term, category=category)
            # Don't filter by category for live API (category naming may differ)
            products = self.client.search_products(keyword=search_term, size=5)
            return {
                "intent": intent, "keywords": keywords, "category": category,
                "matched_products": products[:3], "market_prices": prices[:3],
                "response": _format_price_response(search_term, prices, products),
            }
        else:
            products = self.client.search_products(keyword=search_term, size=6)
            return {
                "intent": intent, "keywords": keywords, "category": category,
                "matched_products": products[:3], "market_prices": [],
                "response": _format_product_response(intent, search_term, products),
            }


def _format_product_response(intent: str, query: str, products: list[dict]) -> str:
    if not products:
        return f"抱歉，没有找到与「{query}」相关的商品，请尝试其他关键词。"
    p = products[0]
    if intent == Intent.PURCHASE:
        return (f"为您找到适合采购的商品：【{p['title']}】，"
                f"{p['brand']}品牌，¥{p['price']:.2f}/件，"
                f"来自{p['platformName']} · {p['shopName']}，"
                f"库存{p['stock']}件，已售{p['sales']}件。")
    if intent == Intent.COMPARE and len(products) >= 2:
        p2 = products[1]
        return (f"为您找到{len(products)}款相关商品可供对比：\n"
                f"① {p['title']} ({p['brand']}) ¥{p['price']:.2f}\n"
                f"② {p2['title']} ({p2['brand']}) ¥{p2['price']:.2f}")
    if intent == Intent.STOCK_CHECK:
        status = "有货" if p["stock"] > 0 else "暂时缺货"
        return (f"【{p['title']}】{status}，"
                f"当前库存{p['stock']}件，来自{p['platformName']}。")
    return (f"找到{len(products)}款相关商品，推荐：【{p['title']}】，"
            f"{p['brand']}，¥{p['price']:.2f}，{p['platformName']}。")


def _format_price_response(query: str, prices: list[dict], products: list[dict]) -> str:
    if prices:
        mp = prices[0]
        return (f"「{mp['productName']}」市场参考价："
                f"均价¥{mp['avgPrice']:.2f}/{mp['unit']}，"
                f"价格区间¥{mp['minPrice']:.2f}–¥{mp['maxPrice']:.2f}。")
    if products:
        p = products[0]
        return f"【{p['title']}】在{p['platformName']}售价¥{p['price']:.2f}，供参考。"
    return f"暂未找到「{query}」的市场价格数据，建议直接联系供应商询价。"


# ── Voice processor (mock ASR) ────────────────────────────────────────────────

_MOCK_UTTERANCES: list[tuple[str, float]] = [
    ("我想采购一批联想笔记本电脑，大概100台", 0.94),
    ("不锈钢板材304号两毫米的价格是多少", 0.91),
    ("帮我查一下办公椅的库存情况", 0.89),
    ("戴尔服务器和华为服务器哪个性价比高", 0.87),
    ("我们需要采购A4复印纸500箱，请报价", 0.93),
    ("工业级继电器模块现在有没有货", 0.88),
    ("推荐几款企业级交换机，48口千兆的", 0.90),
    ("ARM单片机STM32开发板的价格和库存", 0.86),
    ("请问变频器7.5千瓦三相380伏的市场价", 0.92),
    ("查询阿里巴巴1688上不锈钢螺丝的报价", 0.85),
]


class VoiceProcessor:
    """Simulates ASR by deterministically mapping audio bytes to Chinese utterances."""

    def __init__(self, text_processor: TextProcessor):
        self.text_processor = text_processor

    async def process(self, audio_data: bytes, session: dict) -> dict:
        await asyncio.sleep(random.uniform(0.05, 0.15))  # simulate processing time
        idx = int(hashlib.md5(audio_data[:512]).hexdigest(), 16) % len(_MOCK_UTTERANCES)
        text, confidence = _MOCK_UTTERANCES[idx]

        result = await self.text_processor.process(text, session)
        return {
            **result,
            "transcribed_text": text,
            "asr_confidence": confidence,
        }


# ── Image processor (mock CV) ─────────────────────────────────────────────────

@dataclass
class ImageRecognitionResult:
    labels: list[dict]      # [{"name": str, "confidence": float}]
    brands: list[str]
    objects: list[str]
    ocr_text: str
    search_keyword: str     # derived keyword for product search

_MOCK_IMAGE_RESULTS: list[ImageRecognitionResult] = [
    ImageRecognitionResult(
        labels=[{"name": "笔记本电脑", "confidence": 0.96}, {"name": "IT设备", "confidence": 0.91}],
        brands=["联想", "ThinkPad"],
        objects=["笔记本", "键盘", "屏幕"],
        ocr_text="ThinkPad E14 Gen 5\ni5-1340P 16GB 512GB\n¥5299",
        search_keyword="联想笔记本电脑",
    ),
    ImageRecognitionResult(
        labels=[{"name": "服务器", "confidence": 0.94}, {"name": "机架式设备", "confidence": 0.88}],
        brands=["戴尔", "Dell"],
        objects=["服务器", "机架", "指示灯"],
        ocr_text="Dell PowerEdge R750\nDual Xeon Gold 6348\n2x 32GB DDR4",
        search_keyword="戴尔服务器",
    ),
    ImageRecognitionResult(
        labels=[{"name": "工业设备", "confidence": 0.89}, {"name": "变频器", "confidence": 0.85}],
        brands=["英威腾", "Inovance"],
        objects=["变频器", "控制面板", "接线端子"],
        ocr_text="INVT MD500T7R5G3\n三相380V 7.5kW\nIP20防护等级",
        search_keyword="变频器7.5KW",
    ),
    ImageRecognitionResult(
        labels=[{"name": "不锈钢板材", "confidence": 0.91}, {"name": "原材料", "confidence": 0.87}],
        brands=["宝钢", "BAOSTEEL"],
        objects=["钢板", "金属板材", "切割板"],
        ocr_text="304不锈钢冷轧板\n2.0mm*1220mm*2440mm\n≥28.5元/kg",
        search_keyword="不锈钢板材304",
    ),
    ImageRecognitionResult(
        labels=[{"name": "办公椅", "confidence": 0.93}, {"name": "家具", "confidence": 0.88}],
        brands=["西昊", "SIHOO"],
        objects=["椅子", "扶手", "滚轮底座"],
        ocr_text="SIHOO S300\n人体工学电脑椅\n¥2399 原价¥2899",
        search_keyword="人体工学办公椅",
    ),
]


class ImageProcessor:
    """Simulates computer vision by mapping image bytes to mock recognition results."""

    def __init__(self, client: ILbuyClient):
        self.client = client

    async def process(self, image_data: bytes, session: dict) -> dict:
        await asyncio.sleep(random.uniform(0.1, 0.3))  # simulate CV latency
        idx = int(hashlib.md5(image_data[:512]).hexdigest(), 16) % len(_MOCK_IMAGE_RESULTS)
        rec = _MOCK_IMAGE_RESULTS[idx]

        category = _infer_category(rec.search_keyword)
        products = self.client.search_products(keyword=rec.search_keyword, category=category, size=5)

        brand_str = "、".join(rec.brands) if rec.brands else "未识别"
        response = (
            f"图像识别到{rec.labels[0]['name']}（置信度{rec.labels[0]['confidence']:.0%}），"
            f"品牌：{brand_str}。"
            f"OCR识别文字：「{rec.ocr_text.split(chr(10))[0]}」。"
        )
        if products:
            p = products[0]
            response += f" 推荐商品：【{p['title']}】¥{p['price']:.2f}，{p['platformName']}。"

        return {
            "intent": Intent.SEARCH,
            "keywords": rec.objects,
            "category": category,
            "matched_products": products[:3],
            "market_prices": [],
            "image_labels": rec.labels,
            "image_brands": rec.brands,
            "ocr_text": rec.ocr_text,
            "response": response,
        }


# ── Link processor ────────────────────────────────────────────────────────────

_PLATFORM_DOMAINS: dict[str, str] = {
    "taobao.com": "taobao",
    "tmall.com": "tmall",
    "jd.com": "jd",
    "pinduoduo.com": "pinduoduo",
    "yangkeduo.com": "pinduoduo",
    "douyin.com": "douyin",
    "vip.com": "weipinhui",
    "1688.com": "1688",
}

_PLATFORM_NAMES: dict[str, str] = {
    "taobao": "淘宝", "tmall": "天猫", "jd": "京东",
    "pinduoduo": "拼多多", "douyin": "抖音",
    "weipinhui": "唯品会", "1688": "阿里巴巴1688",
}

_PATH_KEYWORDS: list[tuple[str, str]] = [
    ("laptop", "笔记本电脑"), ("notebook", "笔记本电脑"), ("server", "服务器"),
    ("printer", "打印机"), ("switch", "交换机"), ("chair", "办公椅"),
    ("paper", "复印纸"), ("steel", "钢板"), ("inverter", "变频器"),
    ("relay", "继电器"), ("mcu", "单片机"), ("sensor", "传感器"),
]


class LinkProcessor:
    def __init__(self, client: ILbuyClient):
        self.client = client

    async def process(self, url: str, session: dict) -> dict:
        await asyncio.sleep(0.05)
        parsed = urlparse(url)
        domain = parsed.netloc.lower().lstrip("www.")

        # detect platform
        platform = ""
        platform_name = "未知平台"
        for d, plat in _PLATFORM_DOMAINS.items():
            if d in domain:
                platform = plat
                platform_name = _PLATFORM_NAMES.get(plat, plat)
                break

        # extract keyword from path
        path = unquote(parsed.path + " " + (parsed.query or "")).lower()
        keyword = ""
        for path_token, kw in _PATH_KEYWORDS:
            if path_token in path:
                keyword = kw
                break
        # also try to grab meaningful Chinese-looking or product-name segments
        if not keyword:
            # take last non-empty path segment (often item name / item id)
            segments = [s for s in parsed.path.split("/") if s]
            if segments:
                raw = unquote(segments[-1]).replace("-", " ").replace("_", " ")
                keyword = raw[:40]

        category = _infer_category(keyword)
        products = self.client.search_products(keyword=keyword, platform=platform, category=category, size=5)

        response = f"解析到{platform_name}商品链接，"
        if keyword:
            response += f"关键词「{keyword}」，"
        if products:
            p = products[0]
            response += f"推荐：【{p['title']}】¥{p['price']:.2f}，库存{p['stock']}件。"
        else:
            response += "暂未找到精确匹配商品，请尝试更具体的搜索关键词。"

        return {
            "intent": Intent.SEARCH,
            "keywords": [keyword] if keyword else [],
            "category": category,
            "platform": platform,
            "platform_name": platform_name,
            "matched_products": products[:3],
            "market_prices": [],
            "response": response,
        }


# ── Session management ────────────────────────────────────────────────────────

@dataclass
class Session:
    session_id: str
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_activity: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    interaction_count: int = 0
    last_intent: str = Intent.UNKNOWN
    last_keywords: list[str] = field(default_factory=list)
    history: deque = field(default_factory=lambda: deque(maxlen=5))  # last 5 exchanges

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "created_at": self.created_at,
            "last_activity": self.last_activity,
            "interaction_count": self.interaction_count,
            "last_intent": self.last_intent,
            "last_keywords": self.last_keywords,
            "history_len": len(self.history),
        }

    def record(self, input_type: str, user_input: str, response: str, intent: str, keywords: list[str]) -> None:
        self.interaction_count += 1
        self.last_activity = datetime.now(timezone.utc).isoformat()
        self.last_intent = intent
        self.last_keywords = keywords
        self.history.append({
            "turn": self.interaction_count,
            "input_type": input_type,
            "user": user_input[:80],
            "assistant": response[:120],
        })


# ── Multimodal assistant ──────────────────────────────────────────────────────

class MultimodalAssistant:
    """
    Orchestrates all input processors.
    Maintains per-session context for multi-round conversations.
    """

    def __init__(self, gateway_url: str = GATEWAY_URL):
        self._client = ILbuyClient(base_url=gateway_url)
        self._text = TextProcessor(self._client)
        self._voice = VoiceProcessor(self._text)
        self._image = ImageProcessor(self._client)
        self._link = LinkProcessor(self._client)
        self._sessions: dict[str, Session] = {}

    def _get_session(self, session_id: str) -> Session:
        if session_id not in self._sessions:
            self._sessions[session_id] = Session(session_id=session_id)
        return self._sessions[session_id]

    async def process(
        self,
        session_id: str,
        input_type: str,
        content: str | bytes,
    ) -> dict:
        """
        Route input to the correct processor and return a unified response dict.

        Parameters
        ----------
        session_id : str
            Conversation session identifier.
        input_type : str
            One of: "text", "voice", "image", "link".
        content : str | bytes
            The user's input (text/link as str; voice/image as bytes).

        Returns
        -------
        dict with keys:
            session_id, input_type, intent, keywords, category,
            matched_products, market_prices, response, timestamp, session_info
        """
        session = self._get_session(session_id)
        session_dict = session.to_dict()

        if input_type == "text":
            assert isinstance(content, str)
            result = await self._text.process(content, session_dict)
            display_input = content
        elif input_type == "voice":
            assert isinstance(content, bytes)
            result = await self._voice.process(content, session_dict)
            display_input = result.get("transcribed_text", "<audio>")
        elif input_type == "image":
            assert isinstance(content, bytes)
            result = await self._image.process(content, session_dict)
            display_input = "<image>"
        elif input_type == "link":
            assert isinstance(content, str)
            result = await self._link.process(content, session_dict)
            display_input = content
        else:
            return {
                "session_id": session_id,
                "input_type": input_type,
                "error": f"Unsupported input_type: {input_type!r}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        # update session state
        session.record(
            input_type=input_type,
            user_input=display_input,
            response=result.get("response", ""),
            intent=result.get("intent", Intent.UNKNOWN),
            keywords=result.get("keywords", []),
        )

        return {
            "session_id": session_id,
            "input_type": input_type,
            **result,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session_info": session.to_dict(),
        }

    def get_session_history(self, session_id: str) -> list[dict]:
        s = self._sessions.get(session_id)
        return list(s.history) if s else []


# ── Test client ───────────────────────────────────────────────────────────────

class TestClient:
    """Comprehensive test runner for all four input modes."""

    def __init__(self, gateway_url: str = GATEWAY_URL):
        self.assistant = MultimodalAssistant(gateway_url=gateway_url)

    async def run_comprehensive_test(self) -> None:
        sep = "=" * 65
        print(sep)
        print("  ILbuy 本地多模态商品助手 — 综合测试")
        print(sep)

        session_id = f"test_{int(time.time())}"

        # ── 1. Text input ──────────────────────────────────────────────────
        print("\n【1/4】文字输入测试")
        text_cases = [
            "我想采购100台联想笔记本电脑",
            "不锈钢板材304号的市场价格",
            "办公椅有库存吗",
        ]
        for text in text_cases:
            r = await self.assistant.process(session_id, "text", text)
            print(f"  用户: {text}")
            print(f"  意图: {r['intent']}  |  匹配商品数: {len(r['matched_products'])}")
            print(f"  回复: {r['response']}")
            print()

        # ── 2. Voice input ─────────────────────────────────────────────────
        print("\n【2/4】语音输入测试")
        voice_session = f"voice_{int(time.time())}"
        for audio_seed in [b"audio_laptop", b"audio_steel", b"audio_relay"]:
            r = await self.assistant.process(voice_session, "voice", audio_seed)
            print(f"  ASR识别: {r.get('transcribed_text', '')} (置信度: {r.get('asr_confidence', 0):.0%})")
            print(f"  意图: {r['intent']}  |  匹配商品数: {len(r['matched_products'])}")
            print(f"  回复: {r['response']}")
            print()

        # ── 3. Image input ─────────────────────────────────────────────────
        print("\n【3/4】图片输入测试")
        image_session = f"img_{int(time.time())}"
        image_cases = [
            (b"img_thinkpad_e14", "笔记本电脑图片"),
            (b"img_dell_server",  "服务器图片"),
            (b"img_steel_plate",  "钢板材料图片"),
        ]
        for img_bytes, desc in image_cases:
            r = await self.assistant.process(image_session, "image", img_bytes)
            labels = [lb["name"] for lb in r.get("image_labels", [])[:2]]
            print(f"  图片: {desc}")
            print(f"  识别标签: {labels}  品牌: {r.get('image_brands', [])}")
            print(f"  回复: {r['response']}")
            print()

        # ── 4. Link input ──────────────────────────────────────────────────
        print("\n【4/4】链接输入测试")
        link_session = f"link_{int(time.time())}"
        links = [
            "https://item.taobao.com/item.htm?id=12345&title=laptop-thinkpad",
            "https://detail.tmall.com/item.htm?server-poweredge-dell",
            "https://item.jd.com/10043656.html#steel-plate-304",
            "https://detail.1688.com/offer/relay-industrial-88.html",
        ]
        for url in links:
            r = await self.assistant.process(link_session, "link", url)
            print(f"  链接: {url[:60]}...")
            print(f"  平台: {r.get('platform_name', '未知')}  关键词: {r.get('keywords', [])}")
            print(f"  回复: {r['response']}")
            print()

        # ── 5. Multi-round conversation ────────────────────────────────────
        print("\n【5/5】多轮对话测试")
        multi_session = f"multi_{int(time.time())}"
        turns = [
            ("text", "推荐一些工业设备"),
            ("text", "价格怎么样"),
            ("voice", b"audio_inverter_query"),
        ]
        for input_type, content in turns:
            r = await self.assistant.process(multi_session, input_type, content)
            if input_type == "voice":
                user_str = f"[语音] {r.get('transcribed_text', '')}"
            else:
                user_str = content
            print(f"  用户({input_type}): {user_str}")
            print(f"  回复: {r['response']}")

        history = self.assistant.get_session_history(multi_session)
        print(f"\n  对话历史 ({len(history)} 轮):")
        for turn in history:
            print(f"    Turn {turn['turn']}: [{turn['input_type']}] {turn['user'][:40]} → {turn['assistant'][:50]}...")

        print(f"\n{sep}")
        print("  测试完成！")
        print(sep)


# ── Quick start demo ──────────────────────────────────────────────────────────

async def quick_start() -> None:
    print("ILbuy 多模态商品助手 — 快速演示\n")
    assistant = MultimodalAssistant()

    # Text
    r = await assistant.process("demo", "text", "我想采购一批服务器")
    print(f"[文字] 我想采购一批服务器")
    print(f"  → {r['response']}\n")

    # Voice
    r = await assistant.process("demo", "voice", b"voice_check")
    print(f"[语音] ASR识别: {r.get('transcribed_text')}")
    print(f"  → {r['response']}\n")

    # Image
    r = await assistant.process("demo", "image", b"image_demo_office_chair")
    print(f"[图片] 识别: {[lb['name'] for lb in r.get('image_labels', [])[:2]]}")
    print(f"  → {r['response']}\n")

    # Link
    r = await assistant.process("demo", "link", "https://detail.1688.com/offer/relay-88.html")
    print(f"[链接] https://detail.1688.com/offer/relay-88.html")
    print(f"  → {r['response']}\n")

    session_info = r["session_info"]
    print(f"会话信息: {session_info['interaction_count']} 次交互 | 最后意图: {session_info['last_intent']}")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        client = TestClient()
        asyncio.run(client.run_comprehensive_test())
    else:
        asyncio.run(quick_start())
