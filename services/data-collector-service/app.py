import os
import sqlite3
import tempfile
from datetime import datetime
from flask import Flask, request, jsonify

app = Flask(__name__)

DB_PATH = os.environ.get('DB_PATH', os.path.join(tempfile.gettempdir(), 'ilbuy_data.db'))
PORT = int(os.environ.get("DATA_SERVICE_PORT", 8005))


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def resp(code=0, message="ok", data=None):
    return jsonify({"code": code, "message": message, "data": data})


def init_db():
    conn = get_db()
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS t_supplier (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT UNIQUE NOT NULL,
            credit_code TEXT UNIQUE NOT NULL,
            contact_person TEXT,
            contact_phone TEXT,
            address TEXT,
            business_scope TEXT,
            qualification_level TEXT DEFAULT 'A',
            rating REAL DEFAULT 4.5,
            status TEXT DEFAULT 'ACTIVE',
            registered_at TEXT
        );

        CREATE TABLE IF NOT EXISTS t_market_price (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            product_name TEXT NOT NULL,
            avg_price REAL NOT NULL,
            min_price REAL NOT NULL,
            max_price REAL NOT NULL,
            unit TEXT DEFAULT '件',
            data_source TEXT DEFAULT 'CRAWLER',
            updated_at TEXT
        );

        DROP TABLE IF EXISTS t_product;
        CREATE TABLE IF NOT EXISTS t_product (
            id              TEXT PRIMARY KEY,
            platform        TEXT NOT NULL,
            platform_name   TEXT NOT NULL,
            title           TEXT NOT NULL,
            subtitle        TEXT,
            current_price   REAL NOT NULL,
            original_price  REAL,
            discount        REAL,
            currency        TEXT DEFAULT 'CNY',
            stock_quantity  INTEGER DEFAULT 0,
            available_quantity INTEGER DEFAULT 0,
            sold_quantity   INTEGER DEFAULT 0,
            main_category   TEXT,
            sub_category    TEXT,
            third_category  TEXT,
            brand_id        TEXT,
            brand_name      TEXT,
            brand_logo      TEXT,
            shop_id         TEXT,
            shop_name       TEXT,
            shop_rating     REAL,
            shop_level      TEXT,
            is_official     INTEGER DEFAULT 0,
            location        TEXT,
            average_score   REAL,
            total_reviews   INTEGER DEFAULT 0,
            positive_rate   REAL,
            monthly_sales   INTEGER DEFAULT 0,
            total_sales     INTEGER DEFAULT 0,
            status          TEXT DEFAULT 'on_sale',
            main_image      TEXT,
            product_json    TEXT,
            created_at      TEXT,
            updated_at      TEXT,
            published_at    TEXT
        );
    """)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # Use INSERT OR REPLACE with explicit IDs so seed always wins over stale data
    suppliers = [
        (1,  "北京创新科技供应链有限公司",   "91110108SUPPLY001", "张经理", "13800138001", "北京市海淀区中关村南大街5号", "IT设备/服务器/网络设备", "AAA", 4.8),
        (2,  "上海精密制造装备集团",         "91310101SUPPLY002", "李总监", "13800138002", "上海市浦东新区张江高科技园", "精密零件/机械设备/仪器", "AA",  4.6),
        (3,  "广州综合贸易供应商有限公司",   "91440101SUPPLY003", "陈主任", "13800138003", "广州市天河区珠江新城花城广场", "电子元件/通用物资/包装材料", "A", 4.4),
        (4,  "深圳华信电子科技有限公司",     "91440300SUPPLY004", "王总",   "13800138004", "深圳市南山区科技园北区", "IT设备/电子元件/芯片模块",  "AAA", 4.9),
        (5,  "成都西部工业供应链公司",       "91510100SUPPLY005", "刘经理", "13800138005", "成都市高新区天府大道北段", "工业设备/机床/电机/液压", "AA",  4.5),
        (6,  "天津滨海物资采购中心",         "91120116SUPPLY006", "赵总",   "13800138006", "天津市滨海新区经济技术开发区", "原材料/钢材/铝材/铜材", "AA",  4.3),
        (7,  "杭州数字化供应链科技有限公司", "91330108SUPPLY007", "孙总监", "13800138007", "杭州市余杭区未来科技城海创园", "IT设备/软硬件/SaaS服务", "AAA", 4.7),
        (8,  "武汉中南工业物资有限公司",     "91420100SUPPLY008", "周经理", "13800138008", "武汉市武汉经济技术开发区沌阳", "工业物资/耗材/备件/配件", "A",  4.2),
        (9,  "苏州精工机械配件供应商",       "91320508SUPPLY009", "吴经理", "13800138009", "苏州市工业园区苏绣路18号", "精密机械/液压件/传感器/阀门", "AA", 4.6),
        (10, "重庆西南建材物资供应链",       "91500100SUPPLY010", "郑总",   "13800138010", "重庆市渝北区两江新区龙盛片区", "建材/办公家具/工程材料", "A", 4.1),
    ]
    for s in suppliers:
        c.execute(
            "INSERT OR REPLACE INTO t_supplier "
            "(id, company_name, credit_code, contact_person, contact_phone, address, business_scope, qualification_level, rating, registered_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            s + (now,),
        )

    prices = [
        (1,  "IT设备",   "商务笔记本电脑（i7/16G/512G）",  6800.0,  4500.0,  9800.0,  "台"),
        (2,  "IT设备",   "高性能台式机（i9/32G/1T）",      8500.0,  6000.0, 12000.0,  "台"),
        (3,  "IT设备",   "企业级服务器（Dell PowerEdge）", 38000.0, 28000.0, 65000.0, "台"),
        (4,  "IT设备",   "彩色激光打印机（A4）",            2800.0,  1500.0,  4500.0,  "台"),
        (5,  "IT设备",   "液晶显示器（27寸4K）",            1800.0,   900.0,  3200.0,  "台"),
        (6,  "IT设备",   "企业级交换机（48口千兆）",        3500.0,  2000.0,  6000.0,  "台"),
        (7,  "办公用品", "A4复印纸（500张/包）",              38.0,    25.0,    55.0,  "包"),
        (8,  "办公用品", "人体工学办公椅",                    680.0,   380.0,  1200.0,  "把"),
        (9,  "办公用品", "钢制文件柜（四层）",                450.0,   280.0,   750.0,  "个"),
        (10, "办公用品", "会议室白板（120×180cm）",           320.0,   180.0,   580.0,  "块"),
        (11, "工业设备", "数控机床（三轴CNC）",             85000.0, 60000.0,130000.0,  "台"),
        (12, "工业设备", "工业电动机（30kW）",               4500.0,  3000.0,  7500.0,  "台"),
        (13, "工业设备", "液压泵站（中压型）",              12000.0,  8000.0, 20000.0,  "套"),
        (14, "原材料",   "不锈钢板（304# 2mm）",               35.0,    22.0,    52.0,  "kg"),
        (15, "原材料",   "铝合金型材（6063-T5）",              28.0,    18.0,    42.0,  "kg"),
        (16, "电子元件", "工业级继电器模块",                    18.0,     8.0,    32.0,  "个"),
        (17, "电子元件", "ARM 32位MCU微控制器",                 25.0,    12.0,    45.0,  "片"),
    ]
    for p in prices:
        c.execute(
            "INSERT OR REPLACE INTO t_market_price "
            "(id, category, product_name, avg_price, min_price, max_price, unit, updated_at) "
            "VALUES (?,?,?,?,?,?,?,?)",
            p + (now,),
        )


    products_v2 = [
                ("TB_V2_001","taobao","淘宝",'联想ThinkPad E14 Gen5 笔记本电脑 i7-1355U 16G 512G SSD','官方正品 24期免息 企业大客户专属价',5299.0,5999.0,0.883,485,480,3200,'电脑办公','笔记本电脑','商务办公本','B001','联想',"SHOP_LX_001",'联想官方旗舰店',4.9,'天猫超级旗舰',1,'北京',4.8,12500,0.976,850,3200,"on_sale",'https://img.alicdn.com/tb_v2_001_main.jpg','{"$schema": "https://ecommerce-product-schema.com/v2.0", "version": "2.0", "platform": "taobao", "product": {"basic_info": {"product_id": "TB_V2_001", "platform_product_id": "taobao_TB_V2_001", "spu_id": "SPU_TB_V2_001", "title": "联想ThinkPad E14 Gen5 笔记本电脑 i7-1355U 16G 512G SSD", "subtitle": "官方正品 24期免息 企业大客户专属价", "description": "ThinkPad E14 Gen5商务本，军规认证，14寸2.2K屏，i7处理器，适合企业批量采购。", "category": {"main_category": "电脑办公", "sub_category": "笔记本电脑", "third_category": "商务办公本"}, "brand": {"id": "B001", "name": "联想", "logo_url": "https://img.ilbuy.com/brand/B001.png"}, "origin": {"country": "中国", "region": "北京", "is_imported": false}, "labels": ["企业专供", "24期免息", "7天退货"], "certifications": ["3C认证", "能效认证", "军规MIL-STD-810H"], "status": "on_sale"}, "price_info": {"current_price": 5299.0, "original_price": 5999.0, "discount": 0.883, "discount_text": "8.8折", "price_range": {"min": 4999.0, "max": 5799.0}, "currency": "CNY", "vat_included": true, "platform_promotion": {"type": "coupon", "discount_amount": 700.0, "discount_rule": "限时优惠"}, "merchant_promotion": {"type": "gift", "details": "购买赠礼品"}}, "inventory": {"stock_quantity": 485, "available_quantity": 480, "sold_quantity": 3200, "sku_stock_info": {"SKU_TP_I5": {"stock": 150, "available": 148}, "SKU_TP_I7": {"stock": 200, "available": 198}, "SKU_TP_I7P": {"stock": 135, "available": 133}}, "warehouse_info": {"location": "北京仓", "ship_from": "北京"}}, "media": {"main_images": ["https://img.alicdn.com/tb_v2_001_main.jpg", "https://img.alicdn.com/tb_v2_001_02.jpg"], "detail_images": ["https://img.alicdn.com/tb_v2_001_detail_01.jpg"], "video_urls": [], "360_view_url": null, "ar_view_url": null}, "specifications": {"key_attributes": {}, "detailed_specs": {"section": "商品规格", "attributes": []}}, "sku_list": [{"sku_id": "SKU_TP_I5", "sku_code": "SKU_TP_I5", "specs": {"处理器": "i5-1335U", "内存": "16GB"}, "price": 4999.0, "original_price": 5499.0, "stock": 150, "available": 148, "barcode": "6905158254", "image_url": "https://img.ilbuy.com/sku/SKU_TP_I5.jpg", "weight": 1.0, "volume": 0.01, "is_default": true}, {"sku_id": "SKU_TP_I7", "sku_code": "SKU_TP_I7", "specs": {"处理器": "i7-1355U", "内存": "16GB"}, "price": 5299.0, "original_price": 5999.0, "stock": 200, "available": 198, "barcode": "6906559339", "image_url": "https://img.ilbuy.com/sku/SKU_TP_I7.jpg", "weight": 1.0, "volume": 0.01, "is_default": true}, {"sku_id": "SKU_TP_I7P", "sku_code": "SKU_TP_I7P", "specs": {"处理器": "i7-1355U", "内存": "32GB"}, "price": 5799.0, "original_price": 6499.0, "stock": 135, "available": 133, "barcode": "6909915444", "image_url": "https://img.ilbuy.com/sku/SKU_TP_I7P.jpg", "weight": 1.0, "volume": 0.01, "is_default": true}], "shipping": {"template_id": "TMPL_TAOBAO", "shipping_fee": 0.0, "free_shipping_condition": {"condition": "amount", "threshold": 0}, "delivery_options": [{"type": "express", "provider": "顺丰速运", "estimated_days": 3, "cost": 0.0}], "return_policy": {"can_return": true, "return_days": 7, "condition": "全新未使用"}}, "merchant": {"shop_id": "SHOP_LX_001", "shop_name": "联想官方旗舰店", "shop_logo": "https://img.ilbuy.com/shop/SHOP_LX_001.png", "shop_rating": 4.9, "shop_level": "天猫超级旗舰", "follower_count": 625000, "is_official": true, "is_verified": true, "location": "北京"}, "ratings": {"average_score": 4.8, "total_reviews": 12500, "positive_rate": 0.976, "rating_distribution": {"5": 10370, "4": 1830, "3": 150, "2": 90, "1": 60}, "reviews": [], "tags": ["联想ThinkPad", "笔记本电脑", "商务办公", "企业采购"]}, "sales_metrics": {"monthly_sales": 850, "total_sales": 3200, "sales_volume": 16956800.0, "conversion_rate": 0.065, "view_count": 48000, "favorite_count": 1066, "cart_addition_count": 1600}, "after_sales": {"warranty": {"period": "1年", "type": "全国联保", "scope": "硬件故障免费维修"}, "support": {"installment": true, "insurance": true, "quality_assurance": true}, "service_promise": ["7天无理由退货", "全国联保1年", "正品保证"]}, "seo": {"keywords": ["联想ThinkPad", "笔记本电脑", "商务办公", "企业采购"], "meta_description": "联想ThinkPad E14 Gen5 笔记本电脑 i7-1355U 16G 512G SSD - 联想", "url_slug": "tb-v2-001"}, "timestamps": {"created_at": "2025-01-01 00:00:00", "updated_at": "2026-04-03 12:48:33", "published_at": "2025-01-15 00:00:00", "valid_until": null}, "platform_specific": {}}}'),
                ("TB_V2_002","taobao","淘宝",'惠普HP LaserJet MFP M429dw 黑白激光打印机 自动双面 无线WiFi','企业办公首选 支持增值税发票',2350.0,2699.0,0.871,320,315,1850,'电脑办公','打印机/一体机','激光打印机','B002','惠普',"SHOP_HP_001",'惠普官方旗舰店',4.8,'天猫超级旗舰',1,'上海',4.7,5600,0.958,420,1850,"on_sale",'https://img.alicdn.com/tb_v2_002_main.jpg','{"$schema": "https://ecommerce-product-schema.com/v2.0", "version": "2.0", "platform": "taobao", "product": {"basic_info": {"product_id": "TB_V2_002", "platform_product_id": "taobao_TB_V2_002", "spu_id": "SPU_TB_V2_002", "title": "惠普HP LaserJet MFP M429dw 黑白激光打印机 自动双面 无线WiFi", "subtitle": "企业办公首选 支持增值税发票", "description": "HP LaserJet M429dw黑白多功能打印机，40ppm高速打印，支持WiFi无线连接。", "category": {"main_category": "电脑办公", "sub_category": "打印机/一体机", "third_category": "激光打印机"}, "brand": {"id": "B002", "name": "惠普", "logo_url": "https://img.ilbuy.com/brand/B002.png"}, "origin": {"country": "中国", "region": "上海", "is_imported": false}, "labels": ["企业开票", "以旧换新", "7天退货"], "certifications": ["3C认证", "能效标识"], "status": "on_sale"}, "price_info": {"current_price": 2350.0, "original_price": 2699.0, "discount": 0.871, "discount_text": "8.7折", "price_range": {"min": 2350.0, "max": 2350.0}, "currency": "CNY", "vat_included": true, "platform_promotion": {"type": "coupon", "discount_amount": 349.0, "discount_rule": "限时优惠"}, "merchant_promotion": {"type": "gift", "details": "购买赠礼品"}}, "inventory": {"stock_quantity": 320, "available_quantity": 315, "sold_quantity": 1850, "sku_stock_info": {"SKU_M429DW": {"stock": 320, "available": 318}}, "warehouse_info": {"location": "上海仓", "ship_from": "上海"}}, "media": {"main_images": ["https://img.alicdn.com/tb_v2_002_main.jpg", "https://img.alicdn.com/tb_v2_002_02.jpg"], "detail_images": ["https://img.alicdn.com/tb_v2_002_detail_01.jpg"], "video_urls": [], "360_view_url": null, "ar_view_url": null}, "specifications": {"key_attributes": {}, "detailed_specs": {"section": "商品规格", "attributes": []}}, "sku_list": [{"sku_id": "SKU_M429DW", "sku_code": "SKU_M429DW", "specs": {"型号": "M429dw"}, "price": 2350.0, "original_price": 2699.0, "stock": 320, "available": 318, "barcode": "6905502552", "image_url": "https://img.ilbuy.com/sku/SKU_M429DW.jpg", "weight": 1.0, "volume": 0.01, "is_default": true}], "shipping": {"template_id": "TMPL_TAOBAO", "shipping_fee": 0.0, "free_shipping_condition": {"condition": "amount", "threshold": 0}, "delivery_options": [{"type": "express", "provider": "顺丰速运", "estimated_days": 3, "cost": 0.0}], "return_policy": {"can_return": true, "return_days": 7, "condition": "全新未使用"}}, "merchant": {"shop_id": "SHOP_HP_001", "shop_name": "惠普官方旗舰店", "shop_logo": "https://img.ilbuy.com/shop/SHOP_HP_001.png", "shop_rating": 4.8, "shop_level": "天猫超级旗舰", "follower_count": 280000, "is_official": true, "is_verified": true, "location": "上海"}, "ratings": {"average_score": 4.7, "total_reviews": 5600, "positive_rate": 0.958, "rating_distribution": {"5": 4560, "4": 804, "3": 117, "2": 70, "1": 47}, "reviews": [], "tags": ["惠普打印机", "激光打印机", "黑白打印", "企业办公"]}, "sales_metrics": {"monthly_sales": 420, "total_sales": 1850, "sales_volume": 4347500.0, "conversion_rate": 0.065, "view_count": 27750, "favorite_count": 616, "cart_addition_count": 925}, "after_sales": {"warranty": {"period": "1年", "type": "全国联保", "scope": "硬件故障免费维修"}, "support": {"installment": true, "insurance": false, "quality_assurance": true}, "service_promise": ["7天无理由退货", "全国联保1年", "正品保证"]}, "seo": {"keywords": ["惠普打印机", "激光打印机", "黑白打印", "企业办公"], "meta_description": "惠普HP LaserJet MFP M429dw 黑白激光打印机 自动双面 无线WiFi - 惠普", "url_slug": "tb-v2-002"}, "timestamps": {"created_at": "2025-01-01 00:00:00", "updated_at": "2026-04-03 12:48:33", "published_at": "2025-01-15 00:00:00", "valid_until": null}, "platform_specific": {}}}'),
                ("TM_V2_001","tmall","天猫",'Apple MacBook Pro 14寸 M3 Pro芯片 18G 512G 深空黑','官方正品 Apple Care+ 可选',14999.0,15999.0,0.937,180,175,1800,'电脑办公','笔记本电脑','高性能本','B003','苹果',"SHOP_APPLE_001",'Apple官方旗舰店',4.95,'天猫超级旗舰',1,'上海',4.9,8900,0.989,320,1800,"on_sale",'https://img.tmall.com/tm_v2_001_main.jpg','{"$schema": "https://ecommerce-product-schema.com/v2.0", "version": "2.0", "platform": "tmall", "product": {"basic_info": {"product_id": "TM_V2_001", "platform_product_id": "tmall_TM_V2_001", "spu_id": "SPU_TM_V2_001", "title": "Apple MacBook Pro 14寸 M3 Pro芯片 18G 512G 深空黑", "subtitle": "官方正品 Apple Care+ 可选", "description": "MacBook Pro 14寸，M3 Pro芯片，Liquid Retina XDR屏幕，18小时续航。", "category": {"main_category": "电脑办公", "sub_category": "笔记本电脑", "third_category": "高性能本"}, "brand": {"id": "B003", "name": "苹果", "logo_url": "https://img.ilbuy.com/brand/B003.png"}, "origin": {"country": "中国", "region": "郑州", "is_imported": false}, "labels": ["Apple官方授权", "以旧换新", "24期免息"], "certifications": ["3C认证", "FCC认证"], "status": "on_sale"}, "price_info": {"current_price": 14999.0, "original_price": 15999.0, "discount": 0.937, "discount_text": "9.4折", "price_range": {"min": 14999.0, "max": 17499.0}, "currency": "CNY", "vat_included": true, "platform_promotion": {"type": "coupon", "discount_amount": 1000.0, "discount_rule": "限时优惠"}, "merchant_promotion": {"type": "gift", "details": "购买赠礼品"}}, "inventory": {"stock_quantity": 180, "available_quantity": 175, "sold_quantity": 1800, "sku_stock_info": {"SKU_MBP14_512": {"stock": 80, "available": 78}, "SKU_MBP14_1T": {"stock": 60, "available": 58}}, "warehouse_info": {"location": "上海仓", "ship_from": "上海"}}, "media": {"main_images": ["https://img.tmall.com/tm_v2_001_main.jpg", "https://img.tmall.com/tm_v2_001_02.jpg"], "detail_images": ["https://img.tmall.com/tm_v2_001_detail_01.jpg"], "video_urls": [], "360_view_url": null, "ar_view_url": null}, "specifications": {"key_attributes": {}, "detailed_specs": {"section": "商品规格", "attributes": []}}, "sku_list": [{"sku_id": "SKU_MBP14_512", "sku_code": "SKU_MBP14_512", "specs": {"芯片": "M3 Pro", "内存": "18GB", "存储": "512GB", "颜色": "深空黑"}, "price": 14999.0, "original_price": 15999.0, "stock": 80, "available": 78, "barcode": "6900816049", "image_url": "https://img.ilbuy.com/sku/SKU_MBP14_512.jpg", "weight": 1.0, "volume": 0.01, "is_default": true}, {"sku_id": "SKU_MBP14_1T", "sku_code": "SKU_MBP14_1T", "specs": {"芯片": "M3 Pro", "内存": "18GB", "存储": "1TB", "颜色": "深空黑"}, "price": 17499.0, "original_price": 18499.0, "stock": 60, "available": 58, "barcode": "6909565188", "image_url": "https://img.ilbuy.com/sku/SKU_MBP14_1T.jpg", "weight": 1.0, "volume": 0.01, "is_default": true}], "shipping": {"template_id": "TMPL_TMALL", "shipping_fee": 0.0, "free_shipping_condition": {"condition": "amount", "threshold": 0}, "delivery_options": [{"type": "express", "provider": "顺丰速运", "estimated_days": 3, "cost": 0.0}], "return_policy": {"can_return": true, "return_days": 7, "condition": "全新未使用"}}, "merchant": {"shop_id": "SHOP_APPLE_001", "shop_name": "Apple官方旗舰店", "shop_logo": "https://img.ilbuy.com/shop/SHOP_APPLE_001.png", "shop_rating": 4.95, "shop_level": "天猫超级旗舰", "follower_count": 445000, "is_official": true, "is_verified": true, "location": "上海"}, "ratings": {"average_score": 4.9, "total_reviews": 8900, "positive_rate": 0.989, "rating_distribution": {"5": 7481, "4": 1320, "3": 48, "2": 29, "1": 19}, "reviews": [], "tags": ["MacBook Pro", "苹果笔记本", "M3芯片", "高性能"]}, "sales_metrics": {"monthly_sales": 320, "total_sales": 1800, "sales_volume": 26998200.0, "conversion_rate": 0.065, "view_count": 27000, "favorite_count": 600, "cart_addition_count": 900}, "after_sales": {"warranty": {"period": "1年", "type": "全国联保", "scope": "硬件故障免费维修"}, "support": {"installment": true, "insurance": true, "quality_assurance": true}, "service_promise": ["7天无理由退货", "全国联保1年", "正品保证"]}, "seo": {"keywords": ["MacBook Pro", "苹果笔记本", "M3芯片", "高性能"], "meta_description": "Apple MacBook Pro 14寸 M3 Pro芯片 18G 512G 深空黑 - 苹果", "url_slug": "tm-v2-001"}, "timestamps": {"created_at": "2025-01-01 00:00:00", "updated_at": "2026-04-03 12:48:33", "published_at": "2025-01-15 00:00:00", "valid_until": null}, "platform_specific": {}}}'),
                ("TM_V2_002","tmall","天猫",'西昊S300人体工学椅 电脑椅老板椅 4D扶手 企业团购','人体工程学设计 30天试坐',2399.0,2899.0,0.828,580,575,15600,'家具家居','办公家具','人体工学椅','B004','西昊',"SHOP_SIHOO_001",'西昊官方旗舰店',4.85,'天猫旗舰',1,'广东省',4.85,28000,0.975,1800,15600,"on_sale",'https://img.tmall.com/tm_v2_002_main.jpg','{"$schema": "https://ecommerce-product-schema.com/v2.0", "version": "2.0", "platform": "tmall", "product": {"basic_info": {"product_id": "TM_V2_002", "platform_product_id": "tmall_TM_V2_002", "spu_id": "SPU_TM_V2_002", "title": "西昊S300人体工学椅 电脑椅老板椅 4D扶手 企业团购", "subtitle": "人体工程学设计 30天试坐", "description": "西昊S300人体工学椅，4D扶手调节，3段腰托，超厚座垫，适合久坐办公。", "category": {"main_category": "家具家居", "sub_category": "办公家具", "third_category": "人体工学椅"}, "brand": {"id": "B004", "name": "西昊", "logo_url": "https://img.ilbuy.com/brand/B004.png"}, "origin": {"country": "中国", "region": "广东佛山", "is_imported": false}, "labels": ["人体工学", "企业团购", "30天试坐"], "certifications": ["BIFMA认证", "ISO9001"], "status": "on_sale"}, "price_info": {"current_price": 2399.0, "original_price": 2899.0, "discount": 0.828, "discount_text": "8.3折", "price_range": {"min": 2399.0, "max": 2399.0}, "currency": "CNY", "vat_included": true, "platform_promotion": {"type": "coupon", "discount_amount": 500.0, "discount_rule": "限时优惠"}, "merchant_promotion": {"type": "gift", "details": "购买赠礼品"}}, "inventory": {"stock_quantity": 580, "available_quantity": 575, "sold_quantity": 15600, "sku_stock_info": {"SKU_S300_BK": {"stock": 280, "available": 278}, "SKU_S300_GY": {"stock": 180, "available": 178}}, "warehouse_info": {"location": "广东省仓", "ship_from": "广东省"}}, "media": {"main_images": ["https://img.tmall.com/tm_v2_002_main.jpg", "https://img.tmall.com/tm_v2_002_02.jpg"], "detail_images": ["https://img.tmall.com/tm_v2_002_detail_01.jpg"], "video_urls": [], "360_view_url": null, "ar_view_url": null}, "specifications": {"key_attributes": {}, "detailed_specs": {"section": "商品规格", "attributes": []}}, "sku_list": [{"sku_id": "SKU_S300_BK", "sku_code": "SKU_S300_BK", "specs": {"颜色": "经典黑"}, "price": 2399.0, "original_price": 2899.0, "stock": 280, "available": 278, "barcode": "6902112913", "image_url": "https://img.ilbuy.com/sku/SKU_S300_BK.jpg", "weight": 1.0, "volume": 0.01, "is_default": true}, {"sku_id": "SKU_S300_GY", "sku_code": "SKU_S300_GY", "specs": {"颜色": "雾霾灰"}, "price": 2399.0, "original_price": 2899.0, "stock": 180, "available": 178, "barcode": "6907032488", "image_url": "https://img.ilbuy.com/sku/SKU_S300_GY.jpg", "weight": 1.0, "volume": 0.01, "is_default": true}], "shipping": {"template_id": "TMPL_TMALL", "shipping_fee": 0.0, "free_shipping_condition": {"condition": "amount", "threshold": 0}, "delivery_options": [{"type": "express", "provider": "顺丰速运", "estimated_days": 3, "cost": 0.0}], "return_policy": {"can_return": true, "return_days": 7, "condition": "全新未使用"}}, "merchant": {"shop_id": "SHOP_SIHOO_001", "shop_name": "西昊官方旗舰店", "shop_logo": "https://img.ilbuy.com/shop/SHOP_SIHOO_001.png", "shop_rating": 4.85, "shop_level": "天猫旗舰", "follower_count": 1400000, "is_official": true, "is_verified": true, "location": "广东省"}, "ratings": {"average_score": 4.85, "total_reviews": 28000, "positive_rate": 0.975, "rating_distribution": {"5": 23205, "4": 4095, "3": 350, "2": 210, "1": 140}, "reviews": [], "tags": ["人体工学椅", "办公椅", "西昊", "久坐舒适"]}, "sales_metrics": {"monthly_sales": 1800, "total_sales": 15600, "sales_volume": 37424400.0, "conversion_rate": 0.065, "view_count": 234000, "favorite_count": 5200, "cart_addition_count": 7800}, "after_sales": {"warranty": {"period": "1年", "type": "全国联保", "scope": "硬件故障免费维修"}, "support": {"installment": true, "insurance": false, "quality_assurance": true}, "service_promise": ["7天无理由退货", "全国联保1年", "正品保证"]}, "seo": {"keywords": ["人体工学椅", "办公椅", "西昊", "久坐舒适"], "meta_description": "西昊S300人体工学椅 电脑椅老板椅 4D扶手 企业团购 - 西昊", "url_slug": "tm-v2-002"}, "timestamps": {"created_at": "2025-01-01 00:00:00", "updated_at": "2026-04-03 12:48:33", "published_at": "2025-01-15 00:00:00", "valid_until": null}, "platform_specific": {}}}'),
                ("JD_V2_001","jd","京东",'Dell PowerEdge R750xa服务器 Gold6346×2 64G DDR4 3.84T SSD','企业级高性能服务器 7×24小时服务',28800.0,32000.0,0.9,15,10,320,'IT设备','服务器','企业级机架服务器','B_DELL','戴尔',"SHOP_DELL_JD",'戴尔企业官方旗舰店',4.9,'京东超级旗舰',1,'北京',4.8,1850,0.972,62,320,"on_sale",'https://img.jd.com/jd_v2_001_main.jpg','{"$schema": "https://ecommerce-product-schema.com/v2.0", "version": "2.0", "platform": "jd", "product": {"basic_info": {"product_id": "JD_V2_001", "platform_product_id": "jd_JD_V2_001", "spu_id": "SPU_JD_V2_001", "title": "Dell PowerEdge R750xa服务器 Gold6346×2 64G DDR4 3.84T SSD", "subtitle": "企业级高性能服务器 7×24小时服务", "description": "Dell PowerEdge R750xa企业级服务器，双路Xeon Gold，适合数据中心部署。", "category": {"main_category": "IT设备", "sub_category": "服务器", "third_category": "企业级机架服务器"}, "brand": {"id": "B_DELL", "name": "戴尔", "logo_url": "https://img.ilbuy.com/brand/B_DELL.png"}, "origin": {"country": "中国", "region": "北京", "is_imported": false}, "labels": ["企业专供", "增值税发票", "7×24客服"], "certifications": ["3C认证", "CE认证"], "status": "on_sale"}, "price_info": {"current_price": 28800.0, "original_price": 32000.0, "discount": 0.9, "discount_text": "9.0折", "price_range": {"min": 28800.0, "max": 28800.0}, "currency": "CNY", "vat_included": true, "platform_promotion": {"type": "coupon", "discount_amount": 3200.0, "discount_rule": "限时优惠"}, "merchant_promotion": {"type": "gift", "details": "购买赠礼品"}}, "inventory": {"stock_quantity": 15, "available_quantity": 10, "sold_quantity": 320, "sku_stock_info": {"SKU_R750_64": {"stock": 15, "available": 13}}, "warehouse_info": {"location": "北京仓", "ship_from": "北京"}}, "media": {"main_images": ["https://img.jd.com/jd_v2_001_main.jpg", "https://img.jd.com/jd_v2_001_02.jpg"], "detail_images": ["https://img.jd.com/jd_v2_001_detail_01.jpg"], "video_urls": [], "360_view_url": null, "ar_view_url": null}, "specifications": {"key_attributes": {}, "detailed_specs": {"section": "商品规格", "attributes": []}}, "sku_list": [{"sku_id": "SKU_R750_64", "sku_code": "SKU_R750_64", "specs": {"内存": "64GB", "存储": "3.84TB SSD"}, "price": 28800.0, "original_price": 32000.0, "stock": 15, "available": 13, "barcode": "6904158787", "image_url": "https://img.ilbuy.com/sku/SKU_R750_64.jpg", "weight": 1.0, "volume": 0.01, "is_default": true}], "shipping": {"template_id": "TMPL_JD", "shipping_fee": 0.0, "free_shipping_condition": {"condition": "amount", "threshold": 0}, "delivery_options": [{"type": "express", "provider": "顺丰速运", "estimated_days": 3, "cost": 0.0}], "return_policy": {"can_return": true, "return_days": 7, "condition": "全新未使用"}}, "merchant": {"shop_id": "SHOP_DELL_JD", "shop_name": "戴尔企业官方旗舰店", "shop_logo": "https://img.ilbuy.com/shop/SHOP_DELL_JD.png", "shop_rating": 4.9, "shop_level": "京东超级旗舰", "follower_count": 92500, "is_official": true, "is_verified": true, "location": "北京"}, "ratings": {"average_score": 4.8, "total_reviews": 1850, "positive_rate": 0.972, "rating_distribution": {"5": 1528, "4": 269, "3": 25, "2": 15, "1": 10}, "reviews": [], "tags": ["戴尔服务器", "PowerEdge", "企业服务器", "机架服务器"]}, "sales_metrics": {"monthly_sales": 62, "total_sales": 320, "sales_volume": 9216000.0, "conversion_rate": 0.065, "view_count": 4800, "favorite_count": 106, "cart_addition_count": 160}, "after_sales": {"warranty": {"period": "1年", "type": "全国联保", "scope": "硬件故障免费维修"}, "support": {"installment": true, "insurance": true, "quality_assurance": true}, "service_promise": ["7天无理由退货", "全国联保1年", "正品保证"]}, "seo": {"keywords": ["戴尔服务器", "PowerEdge", "企业服务器", "机架服务器"], "meta_description": "Dell PowerEdge R750xa服务器 Gold6346×2 64G DDR4 3.84T SSD - 戴尔", "url_slug": "jd-v2-001"}, "timestamps": {"created_at": "2025-01-01 00:00:00", "updated_at": "2026-04-03 12:48:33", "published_at": "2025-01-15 00:00:00", "valid_until": null}, "platform_specific": {}}}'),
                ("JD_V2_002","jd","京东",'思科Cisco Catalyst 9200L-48P 48口PoE千兆交换机 企业级','企业级托管交换机 PoE供电',12800.0,14500.0,0.883,35,30,680,'IT设备','网络设备','以太网交换机','B_CISCO','思科',"SHOP_CISCO_JD",'思科网络官方旗舰店',4.85,'京东旗舰',1,'上海',4.82,3200,0.968,120,680,"on_sale",'https://img.jd.com/jd_v2_002_main.jpg','{"$schema": "https://ecommerce-product-schema.com/v2.0", "version": "2.0", "platform": "jd", "product": {"basic_info": {"product_id": "JD_V2_002", "platform_product_id": "jd_JD_V2_002", "spu_id": "SPU_JD_V2_002", "title": "思科Cisco Catalyst 9200L-48P 48口PoE千兆交换机 企业级", "subtitle": "企业级托管交换机 PoE供电", "description": "思科Catalyst 9200L 48口PoE交换机，802.3at标准，适合企业园区网络。", "category": {"main_category": "IT设备", "sub_category": "网络设备", "third_category": "以太网交换机"}, "brand": {"id": "B_CISCO", "name": "思科", "logo_url": "https://img.ilbuy.com/brand/B_CISCO.png"}, "origin": {"country": "中国", "region": "上海", "is_imported": false}, "labels": ["企业网络", "PoE供电", "官方正品"], "certifications": ["FCC认证", "CE认证"], "status": "on_sale"}, "price_info": {"current_price": 12800.0, "original_price": 14500.0, "discount": 0.883, "discount_text": "8.8折", "price_range": {"min": 12800.0, "max": 12800.0}, "currency": "CNY", "vat_included": true, "platform_promotion": {"type": "coupon", "discount_amount": 1700.0, "discount_rule": "限时优惠"}, "merchant_promotion": {"type": "gift", "details": "购买赠礼品"}}, "inventory": {"stock_quantity": 35, "available_quantity": 30, "sold_quantity": 680, "sku_stock_info": {"SKU_C9200L": {"stock": 35, "available": 33}}, "warehouse_info": {"location": "上海仓", "ship_from": "上海"}}, "media": {"main_images": ["https://img.jd.com/jd_v2_002_main.jpg", "https://img.jd.com/jd_v2_002_02.jpg"], "detail_images": ["https://img.jd.com/jd_v2_002_detail_01.jpg"], "video_urls": [], "360_view_url": null, "ar_view_url": null}, "specifications": {"key_attributes": {}, "detailed_specs": {"section": "商品规格", "attributes": []}}, "sku_list": [{"sku_id": "SKU_C9200L", "sku_code": "SKU_C9200L", "specs": {"版本": "LAN Base"}, "price": 12800.0, "original_price": 14500.0, "stock": 35, "available": 33, "barcode": "6906847658", "image_url": "https://img.ilbuy.com/sku/SKU_C9200L.jpg", "weight": 1.0, "volume": 0.01, "is_default": true}], "shipping": {"template_id": "TMPL_JD", "shipping_fee": 0.0, "free_shipping_condition": {"condition": "amount", "threshold": 0}, "delivery_options": [{"type": "express", "provider": "顺丰速运", "estimated_days": 3, "cost": 0.0}], "return_policy": {"can_return": true, "return_days": 7, "condition": "全新未使用"}}, "merchant": {"shop_id": "SHOP_CISCO_JD", "shop_name": "思科网络官方旗舰店", "shop_logo": "https://img.ilbuy.com/shop/SHOP_CISCO_JD.png", "shop_rating": 4.85, "shop_level": "京东旗舰", "follower_count": 160000, "is_official": true, "is_verified": true, "location": "上海"}, "ratings": {"average_score": 4.82, "total_reviews": 3200, "positive_rate": 0.968, "rating_distribution": {"5": 2632, "4": 464, "3": 51, "2": 30, "1": 20}, "reviews": [], "tags": ["思科交换机", "Catalyst", "企业网络", "PoE"]}, "sales_metrics": {"monthly_sales": 120, "total_sales": 680, "sales_volume": 8704000.0, "conversion_rate": 0.065, "view_count": 10200, "favorite_count": 226, "cart_addition_count": 340}, "after_sales": {"warranty": {"period": "1年", "type": "全国联保", "scope": "硬件故障免费维修"}, "support": {"installment": true, "insurance": true, "quality_assurance": true}, "service_promise": ["7天无理由退货", "全国联保1年", "正品保证"]}, "seo": {"keywords": ["思科交换机", "Catalyst", "企业网络", "PoE"], "meta_description": "思科Cisco Catalyst 9200L-48P 48口PoE千兆交换机 企业级 - 思科", "url_slug": "jd-v2-002"}, "timestamps": {"created_at": "2025-01-01 00:00:00", "updated_at": "2026-04-03 12:48:33", "published_at": "2025-01-15 00:00:00", "valid_until": null}, "platform_specific": {}}}'),
                ("PDD_V2_001","pinduoduo","拼多多",'永丰牌A4复印纸 70克 500张/包 整箱10包装','白度≥92% 适合激光/喷墨/复印机',135.0,168.0,0.804,5000,4995,56000,'办公用品','纸张/标签','复印纸','B_YF','永丰',"SHOP_YF_PDD",'永丰纸业官方专营店',4.75,'拼多多旗舰',1,'广东省',4.6,38000,0.934,4200,56000,"on_sale",'https://img.pinduoduo.com/pdd_v2_001_main.jpg','{"$schema": "https://ecommerce-product-schema.com/v2.0", "version": "2.0", "platform": "pinduoduo", "product": {"basic_info": {"product_id": "PDD_V2_001", "platform_product_id": "pinduoduo_PDD_V2_001", "spu_id": "SPU_PDD_V2_001", "title": "永丰牌A4复印纸 70克 500张/包 整箱10包装", "subtitle": "白度≥92% 适合激光/喷墨/复印机", "description": "永丰A4复印纸，白度≥92%，适合所有复印机和打印机，整箱性价比高。", "category": {"main_category": "办公用品", "sub_category": "纸张/标签", "third_category": "复印纸"}, "brand": {"id": "B_YF", "name": "永丰", "logo_url": "https://img.ilbuy.com/brand/B_YF.png"}, "origin": {"country": "中国", "region": "广东东莞", "is_imported": false}, "labels": ["拼单优惠", "工厂直供", "企业发票"], "certifications": ["ISO9001", "中国环境标志"], "status": "on_sale"}, "price_info": {"current_price": 135.0, "original_price": 168.0, "discount": 0.804, "discount_text": "8.0折", "price_range": {"min": 135.0, "max": 135.0}, "currency": "CNY", "vat_included": true, "platform_promotion": {"type": "coupon", "discount_amount": 33.0, "discount_rule": "限时优惠"}, "merchant_promotion": {"type": "gift", "details": "购买赠礼品"}}, "inventory": {"stock_quantity": 5000, "available_quantity": 4995, "sold_quantity": 56000, "sku_stock_info": {"SKU_A4_70G": {"stock": 5000, "available": 4998}}, "warehouse_info": {"location": "广东省仓", "ship_from": "广东省"}}, "media": {"main_images": ["https://img.pinduoduo.com/pdd_v2_001_main.jpg", "https://img.pinduoduo.com/pdd_v2_001_02.jpg"], "detail_images": ["https://img.pinduoduo.com/pdd_v2_001_detail_01.jpg"], "video_urls": [], "360_view_url": null, "ar_view_url": null}, "specifications": {"key_attributes": {}, "detailed_specs": {"section": "商品规格", "attributes": []}}, "sku_list": [{"sku_id": "SKU_A4_70G", "sku_code": "SKU_A4_70G", "specs": {"克重": "70g"}, "price": 135.0, "original_price": 168.0, "stock": 5000, "available": 4998, "barcode": "6906432962", "image_url": "https://img.ilbuy.com/sku/SKU_A4_70G.jpg", "weight": 1.0, "volume": 0.01, "is_default": true}], "shipping": {"template_id": "TMPL_PINDUODUO", "shipping_fee": 0.0, "free_shipping_condition": {"condition": "amount", "threshold": 0}, "delivery_options": [{"type": "express", "provider": "顺丰速运", "estimated_days": 3, "cost": 0.0}], "return_policy": {"can_return": true, "return_days": 7, "condition": "全新未使用"}}, "merchant": {"shop_id": "SHOP_YF_PDD", "shop_name": "永丰纸业官方专营店", "shop_logo": "https://img.ilbuy.com/shop/SHOP_YF_PDD.png", "shop_rating": 4.75, "shop_level": "拼多多旗舰", "follower_count": 1900000, "is_official": true, "is_verified": true, "location": "广东省"}, "ratings": {"average_score": 4.6, "total_reviews": 38000, "positive_rate": 0.934, "rating_distribution": {"5": 30168, "4": 5323, "3": 1253, "2": 752, "1": 501}, "reviews": [], "tags": ["A4复印纸", "70g", "复印纸", "办公用纸"]}, "sales_metrics": {"monthly_sales": 4200, "total_sales": 56000, "sales_volume": 7560000.0, "conversion_rate": 0.065, "view_count": 840000, "favorite_count": 18666, "cart_addition_count": 28000}, "after_sales": {"warranty": {"period": "1年", "type": "全国联保", "scope": "硬件故障免费维修"}, "support": {"installment": false, "insurance": false, "quality_assurance": true}, "service_promise": ["7天无理由退货", "全国联保1年", "正品保证"]}, "seo": {"keywords": ["A4复印纸", "70g", "复印纸", "办公用纸"], "meta_description": "永丰牌A4复印纸 70克 500张/包 整箱10包装 - 永丰", "url_slug": "pdd-v2-001"}, "timestamps": {"created_at": "2025-01-01 00:00:00", "updated_at": "2026-04-03 12:48:33", "published_at": "2025-01-15 00:00:00", "valid_until": null}, "platform_specific": {}}}'),
                ("PDD_V2_002","pinduoduo","拼多多",'晨光中性笔 0.5mm黑色 100支装 签字笔水笔碳素笔','书写流畅 墨水均匀 企业批发',28.9,38.0,0.761,8000,7995,230000,'办公用品','笔类','中性笔','B_CG','晨光',"SHOP_CG_PDD",'晨光文具官方专营店',4.7,'拼多多旗舰',1,'上海',4.5,89000,0.921,8500,230000,"on_sale",'https://img.pinduoduo.com/pdd_v2_002_main.jpg','{"$schema": "https://ecommerce-product-schema.com/v2.0", "version": "2.0", "platform": "pinduoduo", "product": {"basic_info": {"product_id": "PDD_V2_002", "platform_product_id": "pinduoduo_PDD_V2_002", "spu_id": "SPU_PDD_V2_002", "title": "晨光中性笔 0.5mm黑色 100支装 签字笔水笔碳素笔", "subtitle": "书写流畅 墨水均匀 企业批发", "description": "晨光中性笔0.5mm，书写流畅，100支装适合企业批量采购。", "category": {"main_category": "办公用品", "sub_category": "笔类", "third_category": "中性笔"}, "brand": {"id": "B_CG", "name": "晨光", "logo_url": "https://img.ilbuy.com/brand/B_CG.png"}, "origin": {"country": "中国", "region": "上海", "is_imported": false}, "labels": ["拼单优惠", "国民品牌", "100支装"], "certifications": ["ISO9001"], "status": "on_sale"}, "price_info": {"current_price": 28.9, "original_price": 38.0, "discount": 0.761, "discount_text": "7.6折", "price_range": {"min": 28.9, "max": 28.9}, "currency": "CNY", "vat_included": true, "platform_promotion": {"type": "coupon", "discount_amount": 9.1, "discount_rule": "限时优惠"}, "merchant_promotion": {"type": "gift", "details": "购买赠礼品"}}, "inventory": {"stock_quantity": 8000, "available_quantity": 7995, "sold_quantity": 230000, "sku_stock_info": {"SKU_PEN_BK": {"stock": 8000, "available": 7998}, "SKU_PEN_BL": {"stock": 3000, "available": 2998}}, "warehouse_info": {"location": "上海仓", "ship_from": "上海"}}, "media": {"main_images": ["https://img.pinduoduo.com/pdd_v2_002_main.jpg", "https://img.pinduoduo.com/pdd_v2_002_02.jpg"], "detail_images": ["https://img.pinduoduo.com/pdd_v2_002_detail_01.jpg"], "video_urls": [], "360_view_url": null, "ar_view_url": null}, "specifications": {"key_attributes": {}, "detailed_specs": {"section": "商品规格", "attributes": []}}, "sku_list": [{"sku_id": "SKU_PEN_BK", "sku_code": "SKU_PEN_BK", "specs": {"颜色": "黑色"}, "price": 28.9, "original_price": 38.0, "stock": 8000, "available": 7998, "barcode": "6901710375", "image_url": "https://img.ilbuy.com/sku/SKU_PEN_BK.jpg", "weight": 1.0, "volume": 0.01, "is_default": true}, {"sku_id": "SKU_PEN_BL", "sku_code": "SKU_PEN_BL", "specs": {"颜色": "蓝色"}, "price": 28.9, "original_price": 38.0, "stock": 3000, "available": 2998, "barcode": "6905026261", "image_url": "https://img.ilbuy.com/sku/SKU_PEN_BL.jpg", "weight": 1.0, "volume": 0.01, "is_default": true}], "shipping": {"template_id": "TMPL_PINDUODUO", "shipping_fee": 0.0, "free_shipping_condition": {"condition": "amount", "threshold": 0}, "delivery_options": [{"type": "express", "provider": "顺丰速运", "estimated_days": 3, "cost": 0.0}], "return_policy": {"can_return": true, "return_days": 7, "condition": "全新未使用"}}, "merchant": {"shop_id": "SHOP_CG_PDD", "shop_name": "晨光文具官方专营店", "shop_logo": "https://img.ilbuy.com/shop/SHOP_CG_PDD.png", "shop_rating": 4.7, "shop_level": "拼多多旗舰", "follower_count": 4450000, "is_official": true, "is_verified": true, "location": "上海"}, "ratings": {"average_score": 4.5, "total_reviews": 89000, "positive_rate": 0.921, "rating_distribution": {"5": 69673, "4": 12295, "3": 3515, "2": 2109, "1": 1406}, "reviews": [], "tags": ["晨光中性笔", "签字笔", "0.5mm", "办公用笔"]}, "sales_metrics": {"monthly_sales": 8500, "total_sales": 230000, "sales_volume": 6647000.0, "conversion_rate": 0.065, "view_count": 3450000, "favorite_count": 76666, "cart_addition_count": 115000}, "after_sales": {"warranty": {"period": "1年", "type": "全国联保", "scope": "硬件故障免费维修"}, "support": {"installment": false, "insurance": false, "quality_assurance": true}, "service_promise": ["7天无理由退货", "全国联保1年", "正品保证"]}, "seo": {"keywords": ["晨光中性笔", "签字笔", "0.5mm", "办公用笔"], "meta_description": "晨光中性笔 0.5mm黑色 100支装 签字笔水笔碳素笔 - 晨光", "url_slug": "pdd-v2-002"}, "timestamps": {"created_at": "2025-01-01 00:00:00", "updated_at": "2026-04-03 12:48:33", "published_at": "2025-01-15 00:00:00", "valid_until": null}, "platform_specific": {}}}'),
                ("DY_V2_001","douyin","抖音",'华为Mate 60 Pro+ 手机 16GB+1TB 砚黑 卫星通话','卫星通话 昆仑玻璃 徕卡影像',9999.0,10999.0,0.909,320,315,8900,'手机通讯','手机','智能手机','B_HW','华为',"SHOP_HW_DY",'华为官方旗舰店',4.92,'抖音旗舰',1,'广东省',4.88,56000,0.981,1200,8900,"on_sale",'https://img.douyin.com/dy_v2_001_main.jpg','{"$schema": "https://ecommerce-product-schema.com/v2.0", "version": "2.0", "platform": "douyin", "product": {"basic_info": {"product_id": "DY_V2_001", "platform_product_id": "douyin_DY_V2_001", "spu_id": "SPU_DY_V2_001", "title": "华为Mate 60 Pro+ 手机 16GB+1TB 砚黑 卫星通话", "subtitle": "卫星通话 昆仑玻璃 徕卡影像", "description": "华为Mate 60 Pro+，麒麟9000S，支持卫星通话，徕卡专业影像。", "category": {"main_category": "手机通讯", "sub_category": "手机", "third_category": "智能手机"}, "brand": {"id": "B_HW", "name": "华为", "logo_url": "https://img.ilbuy.com/brand/B_HW.png"}, "origin": {"country": "中国", "region": "广东深圳", "is_imported": false}, "labels": ["官方旗舰", "以旧换新", "分期免息"], "certifications": ["3C认证", "SAR检测"], "status": "on_sale"}, "price_info": {"current_price": 9999.0, "original_price": 10999.0, "discount": 0.909, "discount_text": "9.1折", "price_range": {"min": 8999.0, "max": 9999.0}, "currency": "CNY", "vat_included": true, "platform_promotion": {"type": "coupon", "discount_amount": 1000.0, "discount_rule": "限时优惠"}, "merchant_promotion": {"type": "gift", "details": "购买赠礼品"}}, "inventory": {"stock_quantity": 320, "available_quantity": 315, "sold_quantity": 8900, "sku_stock_info": {"SKU_M60PP_1T": {"stock": 120, "available": 118}, "SKU_M60PP_512": {"stock": 200, "available": 198}}, "warehouse_info": {"location": "广东省仓", "ship_from": "广东省"}}, "media": {"main_images": ["https://img.douyin.com/dy_v2_001_main.jpg", "https://img.douyin.com/dy_v2_001_02.jpg"], "detail_images": ["https://img.douyin.com/dy_v2_001_detail_01.jpg"], "video_urls": [], "360_view_url": null, "ar_view_url": null}, "specifications": {"key_attributes": {}, "detailed_specs": {"section": "商品规格", "attributes": []}}, "sku_list": [{"sku_id": "SKU_M60PP_1T", "sku_code": "SKU_M60PP_1T", "specs": {"颜色": "砚黑", "存储": "1TB"}, "price": 9999.0, "original_price": 10999.0, "stock": 120, "available": 118, "barcode": "6907533534", "image_url": "https://img.ilbuy.com/sku/SKU_M60PP_1T.jpg", "weight": 1.0, "volume": 0.01, "is_default": true}, {"sku_id": "SKU_M60PP_512", "sku_code": "SKU_M60PP_512", "specs": {"颜色": "砚黑", "存储": "512GB"}, "price": 8999.0, "original_price": 9999.0, "stock": 200, "available": 198, "barcode": "6903208320", "image_url": "https://img.ilbuy.com/sku/SKU_M60PP_512.jpg", "weight": 1.0, "volume": 0.01, "is_default": true}], "shipping": {"template_id": "TMPL_DOUYIN", "shipping_fee": 0.0, "free_shipping_condition": {"condition": "amount", "threshold": 0}, "delivery_options": [{"type": "express", "provider": "顺丰速运", "estimated_days": 3, "cost": 0.0}], "return_policy": {"can_return": true, "return_days": 7, "condition": "全新未使用"}}, "merchant": {"shop_id": "SHOP_HW_DY", "shop_name": "华为官方旗舰店", "shop_logo": "https://img.ilbuy.com/shop/SHOP_HW_DY.png", "shop_rating": 4.92, "shop_level": "抖音旗舰", "follower_count": 2800000, "is_official": true, "is_verified": true, "location": "广东省"}, "ratings": {"average_score": 4.88, "total_reviews": 56000, "positive_rate": 0.981, "rating_distribution": {"5": 46695, "4": 8240, "3": 532, "2": 319, "1": 212}, "reviews": [], "tags": ["华为Mate60", "旗舰手机", "卫星通话", "徕卡"]}, "sales_metrics": {"monthly_sales": 1200, "total_sales": 8900, "sales_volume": 88991100.0, "conversion_rate": 0.065, "view_count": 133500, "favorite_count": 2966, "cart_addition_count": 4450}, "after_sales": {"warranty": {"period": "1年", "type": "全国联保", "scope": "硬件故障免费维修"}, "support": {"installment": true, "insurance": true, "quality_assurance": true}, "service_promise": ["7天无理由退货", "全国联保1年", "正品保证"]}, "seo": {"keywords": ["华为Mate60", "旗舰手机", "卫星通话", "徕卡"], "meta_description": "华为Mate 60 Pro+ 手机 16GB+1TB 砚黑 卫星通话 - 华为", "url_slug": "dy-v2-001"}, "timestamps": {"created_at": "2025-01-01 00:00:00", "updated_at": "2026-04-03 12:48:33", "published_at": "2025-01-15 00:00:00", "valid_until": null}, "platform_specific": {}}}'),
                ("DY_V2_002","douyin","抖音",'小米14 Ultra 手机 16GB+512GB 白色 徕卡影像旗舰','骁龙8 Gen3 小米澎湃OS 24期免息',5999.0,6499.0,0.923,580,575,23000,'手机通讯','手机','智能手机','B_MI','小米',"SHOP_MI_DY",'小米官方旗舰店',4.85,'抖音旗舰',1,'北京',4.82,89000,0.974,3500,23000,"on_sale",'https://img.douyin.com/dy_v2_002_main.jpg','{"$schema": "https://ecommerce-product-schema.com/v2.0", "version": "2.0", "platform": "douyin", "product": {"basic_info": {"product_id": "DY_V2_002", "platform_product_id": "douyin_DY_V2_002", "spu_id": "SPU_DY_V2_002", "title": "小米14 Ultra 手机 16GB+512GB 白色 徕卡影像旗舰", "subtitle": "骁龙8 Gen3 小米澎湃OS 24期免息", "description": "小米14 Ultra，骁龙8 Gen3，徕卡联合调校影像，IP68防水。", "category": {"main_category": "手机通讯", "sub_category": "手机", "third_category": "智能手机"}, "brand": {"id": "B_MI", "name": "小米", "logo_url": "https://img.ilbuy.com/brand/B_MI.png"}, "origin": {"country": "中国", "region": "北京", "is_imported": false}, "labels": ["官方旗舰", "以旧换新", "24期免息"], "certifications": ["3C认证"], "status": "on_sale"}, "price_info": {"current_price": 5999.0, "original_price": 6499.0, "discount": 0.923, "discount_text": "9.2折", "price_range": {"min": 5999.0, "max": 5999.0}, "currency": "CNY", "vat_included": true, "platform_promotion": {"type": "coupon", "discount_amount": 500.0, "discount_rule": "限时优惠"}, "merchant_promotion": {"type": "gift", "details": "购买赠礼品"}}, "inventory": {"stock_quantity": 580, "available_quantity": 575, "sold_quantity": 23000, "sku_stock_info": {"SKU_MI14U_W": {"stock": 250, "available": 248}, "SKU_MI14U_B": {"stock": 330, "available": 328}}, "warehouse_info": {"location": "北京仓", "ship_from": "北京"}}, "media": {"main_images": ["https://img.douyin.com/dy_v2_002_main.jpg", "https://img.douyin.com/dy_v2_002_02.jpg"], "detail_images": ["https://img.douyin.com/dy_v2_002_detail_01.jpg"], "video_urls": [], "360_view_url": null, "ar_view_url": null}, "specifications": {"key_attributes": {}, "detailed_specs": {"section": "商品规格", "attributes": []}}, "sku_list": [{"sku_id": "SKU_MI14U_W", "sku_code": "SKU_MI14U_W", "specs": {"颜色": "白色", "存储": "512GB"}, "price": 5999.0, "original_price": 6499.0, "stock": 250, "available": 248, "barcode": "6903045045", "image_url": "https://img.ilbuy.com/sku/SKU_MI14U_W.jpg", "weight": 1.0, "volume": 0.01, "is_default": true}, {"sku_id": "SKU_MI14U_B", "sku_code": "SKU_MI14U_B", "specs": {"颜色": "黑色", "存储": "512GB"}, "price": 5999.0, "original_price": 6499.0, "stock": 330, "available": 328, "barcode": "6907296411", "image_url": "https://img.ilbuy.com/sku/SKU_MI14U_B.jpg", "weight": 1.0, "volume": 0.01, "is_default": true}], "shipping": {"template_id": "TMPL_DOUYIN", "shipping_fee": 0.0, "free_shipping_condition": {"condition": "amount", "threshold": 0}, "delivery_options": [{"type": "express", "provider": "顺丰速运", "estimated_days": 3, "cost": 0.0}], "return_policy": {"can_return": true, "return_days": 7, "condition": "全新未使用"}}, "merchant": {"shop_id": "SHOP_MI_DY", "shop_name": "小米官方旗舰店", "shop_logo": "https://img.ilbuy.com/shop/SHOP_MI_DY.png", "shop_rating": 4.85, "shop_level": "抖音旗舰", "follower_count": 4450000, "is_official": true, "is_verified": true, "location": "北京"}, "ratings": {"average_score": 4.82, "total_reviews": 89000, "positive_rate": 0.974, "rating_distribution": {"5": 73683, "4": 13002, "3": 1157, "2": 694, "1": 462}, "reviews": [], "tags": ["小米14Ultra", "骁龙8Gen3", "徕卡影像", "旗舰"]}, "sales_metrics": {"monthly_sales": 3500, "total_sales": 23000, "sales_volume": 137977000.0, "conversion_rate": 0.065, "view_count": 345000, "favorite_count": 7666, "cart_addition_count": 11500}, "after_sales": {"warranty": {"period": "1年", "type": "全国联保", "scope": "硬件故障免费维修"}, "support": {"installment": true, "insurance": true, "quality_assurance": true}, "service_promise": ["7天无理由退货", "全国联保1年", "正品保证"]}, "seo": {"keywords": ["小米14Ultra", "骁龙8Gen3", "徕卡影像", "旗舰"], "meta_description": "小米14 Ultra 手机 16GB+512GB 白色 徕卡影像旗舰 - 小米", "url_slug": "dy-v2-002"}, "timestamps": {"created_at": "2025-01-01 00:00:00", "updated_at": "2026-04-03 12:48:33", "published_at": "2025-01-15 00:00:00", "valid_until": null}, "platform_specific": {}}}'),
                ("VIP_V2_001","vip","唯品会",'李宁赤兔6 PRO 男跑步鞋 碳板竞速 马拉松专业跑鞋','䨻+碳板 超弹回 轻至206g',649.0,899.0,0.722,850,845,35000,'运动户外','跑步鞋','专业竞速跑鞋','B_LN','李宁',"SHOP_LN_VIP",'李宁官方旗舰店',4.88,'唯品会旗舰',1,'广东省',4.78,28000,0.965,2800,35000,"on_sale",'https://img.vip.com/vip_v2_001_main.jpg','{"$schema": "https://ecommerce-product-schema.com/v2.0", "version": "2.0", "platform": "vip", "product": {"basic_info": {"product_id": "VIP_V2_001", "platform_product_id": "vip_VIP_V2_001", "spu_id": "SPU_VIP_V2_001", "title": "李宁赤兔6 PRO 男跑步鞋 碳板竞速 马拉松专业跑鞋", "subtitle": "䨻+碳板 超弹回 轻至206g", "description": "李宁赤兔6 PRO碳板竞速跑鞋，超弹回弹，鞋重206g，助力PB。", "category": {"main_category": "运动户外", "sub_category": "跑步鞋", "third_category": "专业竞速跑鞋"}, "brand": {"id": "B_LN", "name": "李宁", "logo_url": "https://img.ilbuy.com/brand/B_LN.png"}, "origin": {"country": "中国", "region": "广东广州", "is_imported": false}, "labels": ["品牌特卖", "限时折扣", "专业竞速"], "certifications": ["ISO9001"], "status": "on_sale"}, "price_info": {"current_price": 649.0, "original_price": 899.0, "discount": 0.722, "discount_text": "7.2折", "price_range": {"min": 649.0, "max": 649.0}, "currency": "CNY", "vat_included": true, "platform_promotion": {"type": "coupon", "discount_amount": 250.0, "discount_rule": "限时优惠"}, "merchant_promotion": {"type": "gift", "details": "购买赠礼品"}}, "inventory": {"stock_quantity": 850, "available_quantity": 845, "sold_quantity": 35000, "sku_stock_info": {"SKU_CT6P_40": {"stock": 120, "available": 118}, "SKU_CT6P_42": {"stock": 300, "available": 298}, "SKU_CT6P_44": {"stock": 200, "available": 198}}, "warehouse_info": {"location": "广东省仓", "ship_from": "广东省"}}, "media": {"main_images": ["https://img.vip.com/vip_v2_001_main.jpg", "https://img.vip.com/vip_v2_001_02.jpg"], "detail_images": ["https://img.vip.com/vip_v2_001_detail_01.jpg"], "video_urls": [], "360_view_url": null, "ar_view_url": null}, "specifications": {"key_attributes": {}, "detailed_specs": {"section": "商品规格", "attributes": []}}, "sku_list": [{"sku_id": "SKU_CT6P_40", "sku_code": "SKU_CT6P_40", "specs": {"尺码": "40"}, "price": 649.0, "original_price": 899.0, "stock": 120, "available": 118, "barcode": "6907263547", "image_url": "https://img.ilbuy.com/sku/SKU_CT6P_40.jpg", "weight": 1.0, "volume": 0.01, "is_default": true}, {"sku_id": "SKU_CT6P_42", "sku_code": "SKU_CT6P_42", "specs": {"尺码": "42"}, "price": 649.0, "original_price": 899.0, "stock": 300, "available": 298, "barcode": "6904158972", "image_url": "https://img.ilbuy.com/sku/SKU_CT6P_42.jpg", "weight": 1.0, "volume": 0.01, "is_default": true}, {"sku_id": "SKU_CT6P_44", "sku_code": "SKU_CT6P_44", "specs": {"尺码": "44"}, "price": 649.0, "original_price": 899.0, "stock": 200, "available": 198, "barcode": "6905453815", "image_url": "https://img.ilbuy.com/sku/SKU_CT6P_44.jpg", "weight": 1.0, "volume": 0.01, "is_default": true}], "shipping": {"template_id": "TMPL_VIP", "shipping_fee": 0.0, "free_shipping_condition": {"condition": "amount", "threshold": 0}, "delivery_options": [{"type": "express", "provider": "顺丰速运", "estimated_days": 3, "cost": 0.0}], "return_policy": {"can_return": true, "return_days": 7, "condition": "全新未使用"}}, "merchant": {"shop_id": "SHOP_LN_VIP", "shop_name": "李宁官方旗舰店", "shop_logo": "https://img.ilbuy.com/shop/SHOP_LN_VIP.png", "shop_rating": 4.88, "shop_level": "唯品会旗舰", "follower_count": 1400000, "is_official": true, "is_verified": true, "location": "广东省"}, "ratings": {"average_score": 4.78, "total_reviews": 28000, "positive_rate": 0.965, "rating_distribution": {"5": 22967, "4": 4053, "3": 490, "2": 294, "1": 196}, "reviews": [], "tags": ["李宁跑鞋", "赤兔6", "碳板跑鞋", "马拉松"]}, "sales_metrics": {"monthly_sales": 2800, "total_sales": 35000, "sales_volume": 22715000.0, "conversion_rate": 0.065, "view_count": 525000, "favorite_count": 11666, "cart_addition_count": 17500}, "after_sales": {"warranty": {"period": "1年", "type": "全国联保", "scope": "硬件故障免费维修"}, "support": {"installment": false, "insurance": false, "quality_assurance": true}, "service_promise": ["7天无理由退货", "全国联保1年", "正品保证"]}, "seo": {"keywords": ["李宁跑鞋", "赤兔6", "碳板跑鞋", "马拉松"], "meta_description": "李宁赤兔6 PRO 男跑步鞋 碳板竞速 马拉松专业跑鞋 - 李宁", "url_slug": "vip-v2-001"}, "timestamps": {"created_at": "2025-01-01 00:00:00", "updated_at": "2026-04-03 12:48:33", "published_at": "2025-01-15 00:00:00", "valid_until": null}, "platform_specific": {}}}'),
                ("VIP_V2_002","vip","唯品会",'优衣库UNIQLO 男士羽绒服 Ultra Light Down 550蓬 轻量保暖','超轻便携 可折叠 多色可选',499.0,699.0,0.714,1200,1195,68000,'服装','男装','羽绒服','B_UQ','优衣库',"SHOP_UQ_VIP",'UNIQLO优衣库旗舰店',4.82,'唯品会旗舰',1,'上海',4.75,135000,0.958,5600,68000,"on_sale",'https://img.vip.com/vip_v2_002_main.jpg','{"$schema": "https://ecommerce-product-schema.com/v2.0", "version": "2.0", "platform": "vip", "product": {"basic_info": {"product_id": "VIP_V2_002", "platform_product_id": "vip_VIP_V2_002", "spu_id": "SPU_VIP_V2_002", "title": "优衣库UNIQLO 男士羽绒服 Ultra Light Down 550蓬 轻量保暖", "subtitle": "超轻便携 可折叠 多色可选", "description": "优衣库超轻量羽绒服，550蓬，100%白鸭绒，可折叠收纳，轻便保暖。", "category": {"main_category": "服装", "sub_category": "男装", "third_category": "羽绒服"}, "brand": {"id": "B_UQ", "name": "优衣库", "logo_url": "https://img.ilbuy.com/brand/B_UQ.png"}, "origin": {"country": "中国", "region": "上海", "is_imported": false}, "labels": ["品牌特卖", "超轻便携", "多色"], "certifications": ["ISO9001"], "status": "on_sale"}, "price_info": {"current_price": 499.0, "original_price": 699.0, "discount": 0.714, "discount_text": "7.1折", "price_range": {"min": 499.0, "max": 499.0}, "currency": "CNY", "vat_included": true, "platform_promotion": {"type": "coupon", "discount_amount": 200.0, "discount_rule": "限时优惠"}, "merchant_promotion": {"type": "gift", "details": "购买赠礼品"}}, "inventory": {"stock_quantity": 1200, "available_quantity": 1195, "sold_quantity": 68000, "sku_stock_info": {"SKU_ULD_S": {"stock": 300, "available": 298}, "SKU_ULD_M": {"stock": 400, "available": 398}, "SKU_ULD_L": {"stock": 250, "available": 248}}, "warehouse_info": {"location": "上海仓", "ship_from": "上海"}}, "media": {"main_images": ["https://img.vip.com/vip_v2_002_main.jpg", "https://img.vip.com/vip_v2_002_02.jpg"], "detail_images": ["https://img.vip.com/vip_v2_002_detail_01.jpg"], "video_urls": [], "360_view_url": null, "ar_view_url": null}, "specifications": {"key_attributes": {}, "detailed_specs": {"section": "商品规格", "attributes": []}}, "sku_list": [{"sku_id": "SKU_ULD_S", "sku_code": "SKU_ULD_S", "specs": {"尺码": "S", "颜色": "黑色"}, "price": 499.0, "original_price": 699.0, "stock": 300, "available": 298, "barcode": "6909018802", "image_url": "https://img.ilbuy.com/sku/SKU_ULD_S.jpg", "weight": 1.0, "volume": 0.01, "is_default": true}, {"sku_id": "SKU_ULD_M", "sku_code": "SKU_ULD_M", "specs": {"尺码": "M", "颜色": "黑色"}, "price": 499.0, "original_price": 699.0, "stock": 400, "available": 398, "barcode": "6905145400", "image_url": "https://img.ilbuy.com/sku/SKU_ULD_M.jpg", "weight": 1.0, "volume": 0.01, "is_default": true}, {"sku_id": "SKU_ULD_L", "sku_code": "SKU_ULD_L", "specs": {"尺码": "L", "颜色": "黑色"}, "price": 499.0, "original_price": 699.0, "stock": 250, "available": 248, "barcode": "6907490693", "image_url": "https://img.ilbuy.com/sku/SKU_ULD_L.jpg", "weight": 1.0, "volume": 0.01, "is_default": true}], "shipping": {"template_id": "TMPL_VIP", "shipping_fee": 0.0, "free_shipping_condition": {"condition": "amount", "threshold": 0}, "delivery_options": [{"type": "express", "provider": "顺丰速运", "estimated_days": 3, "cost": 0.0}], "return_policy": {"can_return": true, "return_days": 7, "condition": "全新未使用"}}, "merchant": {"shop_id": "SHOP_UQ_VIP", "shop_name": "UNIQLO优衣库旗舰店", "shop_logo": "https://img.ilbuy.com/shop/SHOP_UQ_VIP.png", "shop_rating": 4.82, "shop_level": "唯品会旗舰", "follower_count": 6750000, "is_official": true, "is_verified": true, "location": "上海"}, "ratings": {"average_score": 4.75, "total_reviews": 135000, "positive_rate": 0.958, "rating_distribution": {"5": 109930, "4": 19399, "3": 2835, "2": 1701, "1": 1134}, "reviews": [], "tags": ["优衣库羽绒服", "超轻羽绒", "UNIQLO", "保暖"]}, "sales_metrics": {"monthly_sales": 5600, "total_sales": 68000, "sales_volume": 33932000.0, "conversion_rate": 0.065, "view_count": 1020000, "favorite_count": 22666, "cart_addition_count": 34000}, "after_sales": {"warranty": {"period": "1年", "type": "全国联保", "scope": "硬件故障免费维修"}, "support": {"installment": false, "insurance": false, "quality_assurance": true}, "service_promise": ["7天无理由退货", "全国联保1年", "正品保证"]}, "seo": {"keywords": ["优衣库羽绒服", "超轻羽绒", "UNIQLO", "保暖"], "meta_description": "优衣库UNIQLO 男士羽绒服 Ultra Light Down 550蓬 轻量保暖 - 优衣库", "url_slug": "vip-v2-002"}, "timestamps": {"created_at": "2025-01-01 00:00:00", "updated_at": "2026-04-03 12:48:33", "published_at": "2025-01-15 00:00:00", "valid_until": null}, "platform_specific": {}}}'),
                ("ALI_V2_001","1688","阿里巴巴1688",'304不锈钢板 冷轧2mm*1220mm*2440mm 零切定制','宝钢原料 Ra≤0.8 增值税发票',28.5,0.0,1.0,50000,49995,2300,'金属材料','不锈钢','不锈钢板','B_BS','宝钢',"SHOP_BS_ALI",'宝钢钢材官方专营店',4.78,'金牌供应商',1,'上海',4.65,8900,0.956,380,2300,"on_sale",'https://img.1688.com/ali_v2_001_main.jpg','{"$schema": "https://ecommerce-product-schema.com/v2.0", "version": "2.0", "platform": "1688", "product": {"basic_info": {"product_id": "ALI_V2_001", "platform_product_id": "1688_ALI_V2_001", "spu_id": "SPU_ALI_V2_001", "title": "304不锈钢板 冷轧2mm*1220mm*2440mm 零切定制", "subtitle": "宝钢原料 Ra≤0.8 增值税发票", "description": "宝钢304不锈钢冷轧板2mm，GB/T3280标准，可零切定制加工。", "category": {"main_category": "金属材料", "sub_category": "不锈钢", "third_category": "不锈钢板"}, "brand": {"id": "B_BS", "name": "宝钢", "logo_url": "https://img.ilbuy.com/brand/B_BS.png"}, "origin": {"country": "中国", "region": "上海宝山", "is_imported": false}, "labels": ["工厂直供", "量大优惠", "开增值税票"], "certifications": ["GB/T3280-2015"], "status": "on_sale"}, "price_info": {"current_price": 28.5, "original_price": 0.0, "discount": 1.0, "discount_text": "10.0折", "price_range": {"min": 28.5, "max": 34.0}, "currency": "CNY", "vat_included": true, "platform_promotion": {"type": "coupon", "discount_amount": -28.5, "discount_rule": "限时优惠"}, "merchant_promotion": {"type": "gift", "details": "购买赠礼品"}}, "inventory": {"stock_quantity": 50000, "available_quantity": 49995, "sold_quantity": 2300, "sku_stock_info": {"SKU_304_2MM": {"stock": 50000, "available": 49998}, "SKU_304_3MM": {"stock": 30000, "available": 29998}}, "warehouse_info": {"location": "上海仓", "ship_from": "上海"}}, "media": {"main_images": ["https://img.1688.com/ali_v2_001_main.jpg", "https://img.1688.com/ali_v2_001_02.jpg"], "detail_images": ["https://img.1688.com/ali_v2_001_detail_01.jpg"], "video_urls": [], "360_view_url": null, "ar_view_url": null}, "specifications": {"key_attributes": {}, "detailed_specs": {"section": "商品规格", "attributes": []}}, "sku_list": [{"sku_id": "SKU_304_2MM", "sku_code": "SKU_304_2MM", "specs": {"厚度": "2mm"}, "price": 28.5, "original_price": 0.0, "stock": 50000, "available": 49998, "barcode": "6903871583", "image_url": "https://img.ilbuy.com/sku/SKU_304_2MM.jpg", "weight": 1.0, "volume": 0.01, "is_default": true}, {"sku_id": "SKU_304_3MM", "sku_code": "SKU_304_3MM", "specs": {"厚度": "3mm"}, "price": 34.0, "original_price": 0.0, "stock": 30000, "available": 29998, "barcode": "6909232154", "image_url": "https://img.ilbuy.com/sku/SKU_304_3MM.jpg", "weight": 1.0, "volume": 0.01, "is_default": true}], "shipping": {"template_id": "TMPL_1688", "shipping_fee": 0.0, "free_shipping_condition": {"condition": "amount", "threshold": 0}, "delivery_options": [{"type": "express", "provider": "顺丰速运", "estimated_days": 3, "cost": 0.0}], "return_policy": {"can_return": true, "return_days": 7, "condition": "全新未使用"}}, "merchant": {"shop_id": "SHOP_BS_ALI", "shop_name": "宝钢钢材官方专营店", "shop_logo": "https://img.ilbuy.com/shop/SHOP_BS_ALI.png", "shop_rating": 4.78, "shop_level": "金牌供应商", "follower_count": 445000, "is_official": true, "is_verified": true, "location": "上海"}, "ratings": {"average_score": 4.65, "total_reviews": 8900, "positive_rate": 0.956, "rating_distribution": {"5": 7232, "4": 1276, "3": 195, "2": 117, "1": 78}, "reviews": [], "tags": ["不锈钢板", "304不锈钢", "宝钢", "金属板材"]}, "sales_metrics": {"monthly_sales": 380, "total_sales": 2300, "sales_volume": 65550.0, "conversion_rate": 0.065, "view_count": 34500, "favorite_count": 766, "cart_addition_count": 1150}, "after_sales": {"warranty": {"period": "1年", "type": "全国联保", "scope": "硬件故障免费维修"}, "support": {"installment": false, "insurance": false, "quality_assurance": true}, "service_promise": ["7天无理由退货", "全国联保1年", "正品保证"]}, "seo": {"keywords": ["不锈钢板", "304不锈钢", "宝钢", "金属板材"], "meta_description": "304不锈钢板 冷轧2mm*1220mm*2440mm 零切定制 - 宝钢", "url_slug": "ali-v2-001"}, "timestamps": {"created_at": "2025-01-01 00:00:00", "updated_at": "2026-04-03 12:48:33", "published_at": "2025-01-15 00:00:00", "valid_until": null}, "platform_specific": {}}}'),
                ("ALI_V2_002","1688","阿里巴巴1688",'欧姆龙OMRON MY2N-J DC24V 小型继电器 8脚插座式 原装正品','寿命≥1000万次 触点5A 工厂直供',12.8,0.0,1.0,100000,99995,68000,'电子元件','继电器','小型继电器','B_OR','欧姆龙',"SHOP_OR_ALI",'欧姆龙电气授权店',4.88,'金牌供应商',1,'广东省',4.82,28000,0.978,5600,68000,"on_sale",'https://img.1688.com/ali_v2_002_main.jpg','{"$schema": "https://ecommerce-product-schema.com/v2.0", "version": "2.0", "platform": "1688", "product": {"basic_info": {"product_id": "ALI_V2_002", "platform_product_id": "1688_ALI_V2_002", "spu_id": "SPU_ALI_V2_002", "title": "欧姆龙OMRON MY2N-J DC24V 小型继电器 8脚插座式 原装正品", "subtitle": "寿命≥1000万次 触点5A 工厂直供", "description": "欧姆龙MY2N-J小型继电器，DC24V，5A触点，1000万次寿命，适合工控自动化。", "category": {"main_category": "电子元件", "sub_category": "继电器", "third_category": "小型继电器"}, "brand": {"id": "B_OR", "name": "欧姆龙", "logo_url": "https://img.ilbuy.com/brand/B_OR.png"}, "origin": {"country": "中国", "region": "广东深圳", "is_imported": false}, "labels": ["原装正品", "量大从优", "企业采购"], "certifications": ["UL认证", "CE认证", "CCC认证"], "status": "on_sale"}, "price_info": {"current_price": 12.8, "original_price": 0.0, "discount": 1.0, "discount_text": "10.0折", "price_range": {"min": 12.8, "max": 13.5}, "currency": "CNY", "vat_included": true, "platform_promotion": {"type": "coupon", "discount_amount": -12.8, "discount_rule": "限时优惠"}, "merchant_promotion": {"type": "gift", "details": "购买赠礼品"}}, "inventory": {"stock_quantity": 100000, "available_quantity": 99995, "sold_quantity": 68000, "sku_stock_info": {"SKU_MY2N_24V": {"stock": 100000, "available": 99998}, "SKU_MY2N_220V": {"stock": 80000, "available": 79998}}, "warehouse_info": {"location": "广东省仓", "ship_from": "广东省"}}, "media": {"main_images": ["https://img.1688.com/ali_v2_002_main.jpg", "https://img.1688.com/ali_v2_002_02.jpg"], "detail_images": ["https://img.1688.com/ali_v2_002_detail_01.jpg"], "video_urls": [], "360_view_url": null, "ar_view_url": null}, "specifications": {"key_attributes": {}, "detailed_specs": {"section": "商品规格", "attributes": []}}, "sku_list": [{"sku_id": "SKU_MY2N_24V", "sku_code": "SKU_MY2N_24V", "specs": {"电压": "DC24V"}, "price": 12.8, "original_price": 0.0, "stock": 100000, "available": 99998, "barcode": "6907855969", "image_url": "https://img.ilbuy.com/sku/SKU_MY2N_24V.jpg", "weight": 1.0, "volume": 0.01, "is_default": true}, {"sku_id": "SKU_MY2N_220V", "sku_code": "SKU_MY2N_220V", "specs": {"电压": "AC220V"}, "price": 13.5, "original_price": 0.0, "stock": 80000, "available": 79998, "barcode": "6906424208", "image_url": "https://img.ilbuy.com/sku/SKU_MY2N_220V.jpg", "weight": 1.0, "volume": 0.01, "is_default": true}], "shipping": {"template_id": "TMPL_1688", "shipping_fee": 0.0, "free_shipping_condition": {"condition": "amount", "threshold": 0}, "delivery_options": [{"type": "express", "provider": "顺丰速运", "estimated_days": 3, "cost": 0.0}], "return_policy": {"can_return": true, "return_days": 7, "condition": "全新未使用"}}, "merchant": {"shop_id": "SHOP_OR_ALI", "shop_name": "欧姆龙电气授权店", "shop_logo": "https://img.ilbuy.com/shop/SHOP_OR_ALI.png", "shop_rating": 4.88, "shop_level": "金牌供应商", "follower_count": 1400000, "is_official": true, "is_verified": true, "location": "广东省"}, "ratings": {"average_score": 4.82, "total_reviews": 28000, "positive_rate": 0.978, "rating_distribution": {"5": 23276, "4": 4107, "3": 308, "2": 184, "1": 123}, "reviews": [], "tags": ["欧姆龙继电器", "MY2N", "小型继电器", "工控"]}, "sales_metrics": {"monthly_sales": 5600, "total_sales": 68000, "sales_volume": 870400.0, "conversion_rate": 0.065, "view_count": 1020000, "favorite_count": 22666, "cart_addition_count": 34000}, "after_sales": {"warranty": {"period": "1年", "type": "全国联保", "scope": "硬件故障免费维修"}, "support": {"installment": false, "insurance": false, "quality_assurance": true}, "service_promise": ["7天无理由退货", "全国联保1年", "正品保证"]}, "seo": {"keywords": ["欧姆龙继电器", "MY2N", "小型继电器", "工控"], "meta_description": "欧姆龙OMRON MY2N-J DC24V 小型继电器 8脚插座式 原装正品 - 欧姆龙", "url_slug": "ali-v2-002"}, "timestamps": {"created_at": "2025-01-01 00:00:00", "updated_at": "2026-04-03 12:48:33", "published_at": "2025-01-15 00:00:00", "valid_until": null}, "platform_specific": {}}}'),
    ]
    for pv2 in products_v2:
        c.execute(
            "INSERT OR REPLACE INTO t_product "
            "(id, platform, platform_name, title, subtitle, current_price, original_price, discount, "
            "stock_quantity, available_quantity, sold_quantity, main_category, sub_category, "
            "third_category, brand_id, brand_name, shop_id, shop_name, shop_rating, shop_level, "
            "is_official, location, average_score, total_reviews, positive_rate, monthly_sales, "
            "total_sales, status, main_image, product_json, created_at, updated_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            pv2 + (now, now),
        )

    conn.commit()
    conn.close()


# ── Supplier endpoints ────────────────────────────────────────────────────────

@app.post("/internal/suppliers")
@app.post("/internal/suppliers/register")
def register_supplier():
    body = request.get_json(force=True) or {}
    company_name = body.get("companyName", "").strip()
    credit_code = body.get("creditCode", "").strip()
    if not company_name or not credit_code:
        return resp(400, "companyName and creditCode are required"), 400

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO t_supplier (company_name, credit_code, contact_person, contact_phone, "
            "address, business_scope, qualification_level, registered_at) VALUES (?,?,?,?,?,?,?,?)",
            (company_name, credit_code, body.get("contactPerson"), body.get("contactPhone"),
             body.get("address"), body.get("businessScope"),
             body.get("qualificationLevel", "A"), now),
        )
        conn.commit()
        row = conn.execute("SELECT id FROM t_supplier WHERE company_name=?", (company_name,)).fetchone()
        return resp(0, "ok", {"id": row["id"], "companyName": company_name,
                              "creditCode": credit_code, "status": "ACTIVE"})
    except sqlite3.IntegrityError:
        return resp(409, "supplier already exists"), 409
    finally:
        conn.close()


@app.get("/internal/suppliers")
def list_suppliers():
    keyword = request.args.get("keyword", "").strip()
    status = request.args.get("status", "").strip()
    page = max(int(request.args.get("page", 0)), 0)
    size = max(int(request.args.get("size", 10)), 1)

    where, params = [], []
    if keyword:
        where.append("(company_name LIKE ? OR business_scope LIKE ?)")
        params += [f"%{keyword}%", f"%{keyword}%"]
    if status:
        where.append("status = ?")
        params.append(status)

    clause = ("WHERE " + " AND ".join(where)) if where else ""
    conn = get_db()
    total = conn.execute(f"SELECT COUNT(*) FROM t_supplier {clause}", params).fetchone()[0]
    rows = conn.execute(
        f"SELECT id, company_name, credit_code, contact_person, contact_phone, "
        f"address, business_scope, qualification_level, rating, status "
        f"FROM t_supplier {clause} LIMIT ? OFFSET ?",
        params + [size, page * size],
    ).fetchall()
    conn.close()

    items = [{
        "id": r["id"],
        "companyName": r["company_name"],
        "creditCode": r["credit_code"],
        "contactPerson": r["contact_person"],
        "contactPhone": r["contact_phone"],
        "address": r["address"],
        "mainCategory": r["business_scope"],
        "qualificationLevel": r["qualification_level"],
        "rating": r["rating"],
        "status": r["status"],
    } for r in rows]
    return resp(0, "ok", {"total": total, "items": items})


@app.get("/internal/suppliers/<int:supplier_id>")
def get_supplier(supplier_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM t_supplier WHERE id=?", (supplier_id,)).fetchone()
    conn.close()
    if not row:
        return resp(404, "supplier not found"), 404
    data = {
        "id": row["id"], "companyName": row["company_name"], "creditCode": row["credit_code"],
        "contactPerson": row["contact_person"], "contactPhone": row["contact_phone"],
        "address": row["address"], "businessScope": row["business_scope"],
        "qualificationLevel": row["qualification_level"], "rating": row["rating"],
        "status": row["status"], "registeredAt": row["registered_at"],
    }
    return resp(0, "ok", data)


# ── Market price endpoints ────────────────────────────────────────────────────

@app.get("/internal/market/prices")
def list_prices():
    category = request.args.get("category", "").strip()
    keyword = request.args.get("keyword", "").strip()

    where, params = [], []
    if category:
        where.append("category = ?")
        params.append(category)
    if keyword:
        where.append("product_name LIKE ?")
        params.append(f"%{keyword}%")

    clause = ("WHERE " + " AND ".join(where)) if where else ""
    conn = get_db()
    total = conn.execute(f"SELECT COUNT(*) FROM t_market_price {clause}", params).fetchone()[0]
    rows = conn.execute(
        f"SELECT id, category, product_name, avg_price, min_price, max_price, unit, updated_at "
        f"FROM t_market_price {clause}",
        params,
    ).fetchall()
    conn.close()

    items = [{"id": r["id"], "category": r["category"], "productName": r["product_name"],
              "avgPrice": r["avg_price"], "minPrice": r["min_price"], "maxPrice": r["max_price"],
              "unit": r["unit"], "updatedAt": r["updated_at"]} for r in rows]
    return resp(0, "ok", {"total": total, "items": items})


@app.get("/internal/market/prices/<int:price_id>")
def get_price(price_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM t_market_price WHERE id=?", (price_id,)).fetchone()
    conn.close()
    if not row:
        return resp(404, "price record not found"), 404
    data = {
        "id": row["id"], "category": row["category"], "productName": row["product_name"],
        "avgPrice": row["avg_price"], "minPrice": row["min_price"], "maxPrice": row["max_price"],
        "unit": row["unit"], "dataSource": row["data_source"], "updatedAt": row["updated_at"],
    }
    return resp(0, "ok", data)



# ── Product endpoints ─────────────────────────────────────────────────────────

@app.get("/internal/products")
def list_products():
    keyword  = request.args.get("keyword",  "").strip()
    platform = request.args.get("platform", "").strip()
    category = request.args.get("category", "").strip()
    page = max(int(request.args.get("page", 1)), 1)
    size = max(int(request.args.get("size", 20)), 1)
    offset = (page - 1) * size

    where, params = [], []
    if keyword:
        where.append("(title LIKE ? OR brand_name LIKE ? OR shop_name LIKE ?)")
        params += [f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"]
    if platform:
        where.append("platform = ?")
        params.append(platform)
    if category:
        where.append("(main_category LIKE ? OR sub_category LIKE ?)")
        params += [f"%{category}%", f"%{category}%"]
    clause = ("WHERE " + " AND ".join(where)) if where else ""

    conn = get_db()
    total = conn.execute(f"SELECT COUNT(*) FROM t_product {clause}", params).fetchone()[0]
    rows  = conn.execute(
        f"SELECT * FROM t_product {clause} ORDER BY total_sales DESC LIMIT ? OFFSET ?",
        params + [size, offset],
    ).fetchall()
    conn.close()

    items = [_row_to_v2_summary(r) for r in rows]
    return resp(0, "ok", {"total": total, "page": page, "size": size, "items": items})


@app.get("/internal/products/<product_id>")
def get_product(product_id):
    conn = get_db()
    row  = conn.execute("SELECT * FROM t_product WHERE id=?", (product_id,)).fetchone()
    conn.close()
    if not row:
        return resp(404, "product not found"), 404
    # return full v2.0 JSON if available, else summary
    if row["product_json"]:
        import json as _json
        full = _json.loads(row["product_json"])
        return resp(0, "ok", full)
    return resp(0, "ok", _row_to_v2_summary(row))


def _row_to_v2_summary(r) -> dict:
    """Convert a t_product DB row to a v2.0-compatible summary dict."""
    import json as _json
    # If full product_json exists, return parsed summary fields from it
    if r["product_json"]:
        try:
            full = _json.loads(r["product_json"])
            pi   = full["product"]["basic_info"]
            pri  = full["product"]["price_info"]
            inv  = full["product"]["inventory"]
            mer  = full["product"]["merchant"]
            rat  = full["product"]["ratings"]
            sm   = full["product"]["sales_metrics"]
            return {
                # v2.0 top-level
                "$schema": full.get("$schema", "https://ecommerce-product-schema.com/v2.0"),
                "version": "2.0",
                "platform": full["platform"],
                # legacy-compatible flat fields (for existing frontends)
                "id": pi["product_id"],
                "title": pi["title"],
                "price": pri["current_price"],
                "originalPrice": pri["original_price"],
                "discount": pri["discount"],
                "stock": inv["stock_quantity"],
                "sales": inv["sold_quantity"],
                "image": full["product"]["media"]["main_images"][0] if full["product"]["media"]["main_images"] else None,
                "category": pi["category"]["main_category"],
                "brand": pi["brand"]["name"],
                "shopName": mer["shop_name"],
                "platformName": {"taobao":"淘宝","tmall":"天猫","jd":"京东","pinduoduo":"拼多多","douyin":"抖音","vip":"唯品会","1688":"阿里巴巴1688"}.get(full["platform"], full["platform"]),
                # v2.0 extended
                "basicInfo": pi,
                "priceInfo": pri,
                "inventory": inv,
                "merchant": mer,
                "ratingSummary": {"averageScore": rat["average_score"], "totalReviews": rat["total_reviews"], "positiveRate": rat["positive_rate"]},
                "salesMetrics": sm,
            }
        except Exception:
            pass
    # fallback for legacy rows
    return {
        "$schema": "https://ecommerce-product-schema.com/v2.0", "version": "2.0",
        "id": r["id"], "platform": r["platform"],
        "title": r["title"],
        "price": r["current_price"], "originalPrice": r["original_price"],
        "stock": r["stock_quantity"], "sales": r["sold_quantity"],
        "category": r["main_category"], "brand": r["brand_name"],
        "shopName": r["shop_name"], "platformName": r["platform_name"],
        "image": r["main_image"],
    }


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return jsonify({"status": "UP", "service": "data-collector-service"})


@app.errorhandler(404)
def not_found(e):
    return resp(404, "接口不存在"), 404

@app.errorhandler(500)
def internal_error(e):
    return resp(500, f"服务内部错误: {str(e)}"), 500

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=PORT)
