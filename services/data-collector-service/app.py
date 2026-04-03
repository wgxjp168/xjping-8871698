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

        CREATE TABLE IF NOT EXISTS t_product (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            price REAL NOT NULL,
            original_price REAL,
            stock INTEGER DEFAULT 0,
            sales INTEGER DEFAULT 0,
            image TEXT,
            category TEXT,
            brand TEXT,
            shop_name TEXT,
            platform TEXT NOT NULL,
            platform_name TEXT NOT NULL,
            created_at TEXT
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


    products = [
        ("TB001", "联想ThinkPad E14笔记本电脑 i5 16G 512G", 5299.0, 5999.0, 85, 3200, "https://img.alicdn.com/tb001.jpg", "IT设备", "联想", "联想官方旗舰店", "taobao", "淘宝"),
        ("TB002", "华为MateBook D15 2024款笔记本电脑", 4599.0, 4999.0, 120, 5600, "https://img.alicdn.com/tb002.jpg", "IT设备", "华为", "华为授权体验店", "taobao", "淘宝"),
        ("TB003", "戴尔Dell灵越5000轻薄笔记本电脑", 4899.0, 5299.0, 60, 2100, "https://img.alicdn.com/tb003.jpg", "IT设备", "戴尔", "戴尔官方旗舰店", "taobao", "淘宝"),
        ("TB004", "A4复印纸70g 500张整箱8包装", 158.0, 188.0, 2000, 12000, "https://img.alicdn.com/tb004.jpg", "办公用品", "得力", "得力文具旗舰店", "taobao", "淘宝"),
        ("TB005", "晨光中性笔签字笔黑色0.5mm 20支", 18.9, 22.0, 5000, 45000, "https://img.alicdn.com/tb005.jpg", "办公用品", "晨光", "晨光文具旗舰店", "taobao", "淘宝"),
        ("TB006", "奥克斯暖风机取暖器办公室桌面小型", 99.0, 129.0, 300, 8900, "https://img.alicdn.com/tb006.jpg", "办公用品", "奥克斯", "奥克斯官方旗舰店", "taobao", "淘宝"),
        ("TB007", "飞利浦LED台灯护眼学习办公桌灯", 189.0, 239.0, 450, 6700, "https://img.alicdn.com/tb007.jpg", "办公用品", "飞利浦", "飞利浦灯具旗舰店", "taobao", "淘宝"),
        ("TB008", "西门子电动螺丝刀充电式家用电钻套装", 268.0, 328.0, 180, 3400, "https://img.alicdn.com/tb008.jpg", "工业设备", "西门子", "西门子工具旗舰店", "taobao", "淘宝"),
        ("TB009", "3M KN95口罩防尘防雾霾独立包装50只", 89.0, 108.0, 8000, 89000, "https://img.alicdn.com/tb009.jpg", "办公用品", "3M", "3M安全防护旗舰店", "taobao", "淘宝"),
        ("TB010", "罗技M705无线鼠标商务办公", 229.0, 289.0, 650, 12300, "https://img.alicdn.com/tb010.jpg", "IT设备", "罗技", "罗技官方旗舰店", "taobao", "淘宝"),
        ("TM001", "苹果Apple MacBook Pro 14寸 M3芯片", 14999.0, 15999.0, 45, 1800, "https://store.storeimages.cdn-apple.com/tm001.jpg", "IT设备", "苹果", "Apple官方旗舰店", "tmall", "天猫"),
        ("TM002", "索尼WH-1000XM5无线降噪耳机", 2099.0, 2499.0, 230, 5600, "https://img.tmall.com/tm002.jpg", "IT设备", "索尼", "索尼官方旗舰店", "tmall", "天猫"),
        ("TM003", "施乐Fuji Xerox VersaLink B7025多功能打印机", 8800.0, 9800.0, 30, 420, "https://img.tmall.com/tm003.jpg", "IT设备", "施乐", "施乐官方旗舰店", "tmall", "天猫"),
        ("TM004", "宜家IKEA MARKUS马库斯人体工学转椅", 1499.0, 1699.0, 120, 3800, "https://img.tmall.com/tm004.jpg", "办公用品", "宜家", "宜家官方旗舰店", "tmall", "天猫"),
        ("TM005", "西昊S300人体工学椅电脑椅老板椅", 2399.0, 2899.0, 85, 2300, "https://img.tmall.com/tm005.jpg", "办公用品", "西昊", "西昊官方旗舰店", "tmall", "天猫"),
        ("TM006", "美的MPM-400凉霸空调扇冷风机", 699.0, 899.0, 200, 7800, "https://img.tmall.com/tm006.jpg", "办公用品", "美的", "美的官方旗舰店", "tmall", "天猫"),
        ("TM007", "英威腾变频器三相380V 7.5KW工业级", 1280.0, 1580.0, 65, 890, "https://img.tmall.com/tm007.jpg", "工业设备", "英威腾", "英威腾官方旗舰店", "tmall", "天猫"),
        ("TM008", "欧姆龙E5CC-RX2ASM-800温控器PID", 320.0, 420.0, 280, 3600, "https://img.tmall.com/tm008.jpg", "工业设备", "欧姆龙", "欧姆龙官方旗舰店", "tmall", "天猫"),
        ("TM009", "海康威视DS-2CD3T47G2-L网络摄像机", 589.0, 699.0, 420, 8900, "https://img.tmall.com/tm009.jpg", "IT设备", "海康威视", "海康威视官方旗舰店", "tmall", "天猫"),
        ("TM010", "Epson爱普生L805照片打印机彩色6色", 1899.0, 2199.0, 95, 2400, "https://img.tmall.com/tm010.jpg", "IT设备", "爱普生", "爱普生官方旗舰店", "tmall", "天猫"),
        ("JD001", "Dell戴尔PowerEdge R750服务器 64G内存", 28800.0, 32000.0, 15, 320, "https://img.jd.com/jd001.jpg", "IT设备", "戴尔", "戴尔企业官方店", "jd", "京东"),
        ("JD002", "联想ThinkSystem SR650 V2企业级服务器", 35600.0, 38000.0, 8, 180, "https://img.jd.com/jd002.jpg", "IT设备", "联想", "联想企业级官方店", "jd", "京东"),
        ("JD003", "华为FusionServer Pro 2288H V6服务器", 42000.0, 45000.0, 12, 240, "https://img.jd.com/jd003.jpg", "IT设备", "华为", "华为企业官方店", "jd", "京东"),
        ("JD004", "思科Cisco Catalyst 2960-X 48口千兆交换机", 4800.0, 5600.0, 35, 680, "https://img.jd.com/jd004.jpg", "IT设备", "思科", "思科网络官方店", "jd", "京东"),
        ("JD005", "HP惠普LaserJet Pro M428fdn黑白多功能激光打印机", 2350.0, 2699.0, 85, 3200, "https://img.jd.com/jd005.jpg", "IT设备", "惠普", "惠普官方旗舰店", "jd", "京东"),
        ("JD006", "APC UPS不间断电源1500VA 900W SUA1500ICH", 2180.0, 2580.0, 55, 1200, "https://img.jd.com/jd006.jpg", "IT设备", "APC", "APC官方旗舰店", "jd", "京东"),
        ("JD007", "WD西部数据My Cloud EX2 Ultra NAS存储8TB", 3200.0, 3800.0, 30, 560, "https://img.jd.com/jd007.jpg", "IT设备", "WD", "西部数据官方旗舰店", "jd", "京东"),
        ("JD008", "正泰断路器NXB-63 4P 63A空气开关漏保", 128.0, 168.0, 2000, 28000, "https://img.jd.com/jd008.jpg", "工业设备", "正泰", "正泰电气旗舰店", "jd", "京东"),
        ("JD009", "FLUKE福禄克F302+钳形电流表数字万用表", 498.0, 598.0, 180, 4500, "https://img.jd.com/jd009.jpg", "工业设备", "福禄克", "福禄克工具旗舰店", "jd", "京东"),
        ("JD010", "德力西CDM-400/3300塑壳断路器400A", 1680.0, 1980.0, 65, 890, "https://img.jd.com/jd010.jpg", "工业设备", "德力西", "德力西电气旗舰店", "jd", "京东"),
        ("PDD001", "A4复印打印纸70g白色整箱10包装5000张", 128.0, 168.0, 5000, 56000, "https://img.pinduoduo.com/pdd001.jpg", "办公用品", "百旺", "百旺纸业专营店", "pinduoduo", "拼多多"),
        ("PDD002", "圆珠笔原子笔蓝色黑色红色100支装", 25.9, 35.0, 8000, 120000, "https://img.pinduoduo.com/pdd002.jpg", "办公用品", "贝发", "贝发文具专营店", "pinduoduo", "拼多多"),
        ("PDD003", "订书机24/6钉书机办公用品大号重型", 29.9, 39.9, 3000, 45000, "https://img.pinduoduo.com/pdd003.jpg", "办公用品", "得力", "得力文具专营店", "pinduoduo", "拼多多"),
        ("PDD004", "文件夹A4插页袋透明资料册30页", 6.9, 9.9, 12000, 230000, "https://img.pinduoduo.com/pdd004.jpg", "办公用品", "广博", "广博文具专营店", "pinduoduo", "拼多多"),
        ("PDD005", "双面胶强力胶带透明宽10mm 10卷装", 15.9, 22.0, 6000, 89000, "https://img.pinduoduo.com/pdd005.jpg", "办公用品", "齐心", "齐心办公专营店", "pinduoduo", "拼多多"),
        ("PDD006", "快递打包胶带透明封箱胶带宽4.5cm厚", 28.9, 38.0, 4000, 67000, "https://img.pinduoduo.com/pdd006.jpg", "办公用品", "鑫龙", "鑫龙包装专营店", "pinduoduo", "拼多多"),
        ("PDD007", "收纳箱塑料大号家用储物箱整理箱带盖", 35.9, 49.9, 2000, 34000, "https://img.pinduoduo.com/pdd007.jpg", "办公用品", "禧天龙", "禧天龙收纳旗舰店", "pinduoduo", "拼多多"),
        ("PDD008", "无纺布手提袋购物袋礼品袋100只装", 38.0, 52.0, 3500, 78000, "https://img.pinduoduo.com/pdd008.jpg", "办公用品", "嘉兴", "嘉兴包装专营店", "pinduoduo", "拼多多"),
        ("PDD009", "透明气泡膜泡泡纸防震包装材料60cm*50m", 45.0, 62.0, 1800, 23000, "https://img.pinduoduo.com/pdd009.jpg", "办公用品", "申通", "申通包装专营店", "pinduoduo", "拼多多"),
        ("PDD010", "编织袋蛇皮袋大号快递袋物流打包袋50只", 32.0, 45.0, 2500, 45000, "https://img.pinduoduo.com/pdd010.jpg", "办公用品", "正泰", "正泰包装专营店", "pinduoduo", "拼多多"),
        ("DY001", "大疆DJI Mini 4 Pro无人机航拍4K超高清", 4799.0, 5499.0, 65, 2300, "https://img.douyin.com/dy001.jpg", "IT设备", "大疆", "DJI大疆官方旗舰店", "douyin", "抖音"),
        ("DY002", "小米手环8 Pro智能运动健康手环NFC版", 399.0, 499.0, 850, 28000, "https://img.douyin.com/dy002.jpg", "IT设备", "小米", "小米官方旗舰店", "douyin", "抖音"),
        ("DY003", "华为Watch GT 4智能手表运动健康监测", 1188.0, 1488.0, 420, 12000, "https://img.douyin.com/dy003.jpg", "IT设备", "华为", "华为官方旗舰店", "douyin", "抖音"),
        ("DY004", "便携式蓝牙音箱防水户外低音炮大音量", 158.0, 218.0, 1200, 45000, "https://img.douyin.com/dy004.jpg", "IT设备", "JBL", "JBL官方旗舰店", "douyin", "抖音"),
        ("DY005", "Switch任天堂掌机游戏机OLED版主机", 2399.0, 2699.0, 180, 8900, "https://img.douyin.com/dy005.jpg", "IT设备", "任天堂", "任天堂官方旗舰店", "douyin", "抖音"),
        ("DY006", "三星S24 Ultra手机 12G+256G 钛黑色", 9499.0, 10999.0, 95, 3400, "https://img.douyin.com/dy006.jpg", "IT设备", "三星", "三星官方旗舰店", "douyin", "抖音"),
        ("DY007", "OPPO Find X7 Ultra 16G+512G 拍照旗舰", 6999.0, 7999.0, 120, 5600, "https://img.douyin.com/dy007.jpg", "IT设备", "OPPO", "OPPO官方旗舰店", "douyin", "抖音"),
        ("DY008", "vivo X100 Pro 天玑9300旗舰手机", 6499.0, 7499.0, 145, 6700, "https://img.douyin.com/dy008.jpg", "IT设备", "vivo", "vivo官方旗舰店", "douyin", "抖音"),
        ("DY009", "荣耀Magic6 Pro 5G智能手机 骁龙8 Gen3", 5299.0, 6299.0, 230, 9800, "https://img.douyin.com/dy009.jpg", "IT设备", "荣耀", "荣耀官方旗舰店", "douyin", "抖音"),
        ("DY010", "realme GT5 Pro 5G手机 第三代骁龙8", 3499.0, 4199.0, 350, 15000, "https://img.douyin.com/dy010.jpg", "IT设备", "realme", "realme官方旗舰店", "douyin", "抖音"),
        ("WPH001", "真维斯男装夹克外套春秋季休闲商务上衣", 299.0, 399.0, 680, 12300, "https://img.vip.com/wph001.jpg", "服装", "真维斯", "真维斯男装旗舰店", "weipinhui", "唯品会"),
        ("WPH002", "海澜之家男士T恤短袖夏季纯棉圆领打底衫", 89.0, 129.0, 1200, 45000, "https://img.vip.com/wph002.jpg", "服装", "海澜之家", "海澜之家官方旗舰店", "weipinhui", "唯品会"),
        ("WPH003", "太平鸟男装休闲裤宽松直筒九分裤潮流", 239.0, 329.0, 450, 8900, "https://img.vip.com/wph003.jpg", "服装", "太平鸟", "太平鸟男装旗舰店", "weipinhui", "唯品会"),
        ("WPH004", "杰克琼斯牛仔裤男士修身直筒黑色长裤", 289.0, 389.0, 380, 6700, "https://img.vip.com/wph004.jpg", "服装", "杰克琼斯", "杰克琼斯旗舰店", "weipinhui", "唯品会"),
        ("WPH005", "优衣库UNIQLO男装保暖内衣套装秋冬", 199.0, 249.0, 820, 28000, "https://img.vip.com/wph005.jpg", "服装", "优衣库", "UNIQLO官方旗舰店", "weipinhui", "唯品会"),
        ("WPH006", "李宁运动鞋男跑步鞋轻弹减震跑鞋", 399.0, 549.0, 560, 15600, "https://img.vip.com/wph006.jpg", "服装", "李宁", "李宁官方旗舰店", "weipinhui", "唯品会"),
        ("WPH007", "安踏男鞋运动鞋轻便缓震休闲跑步鞋", 279.0, 389.0, 780, 23000, "https://img.vip.com/wph007.jpg", "服装", "安踏", "安踏官方旗舰店", "weipinhui", "唯品会"),
        ("WPH008", "361度男款运动短裤夏季速干跑步训练裤", 79.0, 109.0, 1500, 56000, "https://img.vip.com/wph008.jpg", "服装", "361度", "361度官方旗舰店", "weipinhui", "唯品会"),
        ("WPH009", "特步男士运动背包双肩包大容量户外旅行", 129.0, 179.0, 650, 18000, "https://img.vip.com/wph009.jpg", "服装", "特步", "特步官方旗舰店", "weipinhui", "唯品会"),
        ("WPH010", "耐克Nike男款polo衫商务休闲短袖T恤", 299.0, 399.0, 420, 12000, "https://img.vip.com/wph010.jpg", "服装", "耐克", "Nike官方旗舰店", "weipinhui", "唯品会"),
        ("ALI001", "不锈钢板材304 2mm冷轧钢板零切加工定制", 28.5, 0.0, 50000, 2300, "https://img.1688.com/ali001.jpg", "原材料", "宝钢", "宝钢钢材专营店", "1688", "阿里巴巴1688"),
        ("ALI002", "铝合金6061 T6铝板铝棒铝管零切加工", 22.0, 0.0, 30000, 1800, "https://img.1688.com/ali002.jpg", "原材料", "南铝", "南铝铝材专营店", "1688", "阿里巴巴1688"),
        ("ALI003", "Q235钢板热轧钢板中厚板切割加工定制", 4.8, 0.0, 80000, 5600, "https://img.1688.com/ali003.jpg", "原材料", "鞍钢", "鞍钢钢材批发", "1688", "阿里巴巴1688"),
        ("ALI004", "铜板T2紫铜板铜条铜管零切加工批发", 65.0, 0.0, 8000, 890, "https://img.1688.com/ali004.jpg", "原材料", "宁铜", "宁铜铜材专营店", "1688", "阿里巴巴1688"),
        ("ALI005", "工业级继电器8脚14脚24V220V小型电磁继电器", 8.5, 0.0, 50000, 68000, "https://img.1688.com/ali005.jpg", "电子元件", "欧姆龙", "欧姆龙配件专营店", "1688", "阿里巴巴1688"),
        ("ALI006", "光电传感器漫反射对射U槽型NPN PNP开关", 12.8, 0.0, 30000, 45000, "https://img.1688.com/ali006.jpg", "电子元件", "奥托尼克斯", "传感器专营店", "1688", "阿里巴巴1688"),
        ("ALI007", "ARM STM32F103C8T6单片机最小系统板开发板", 15.9, 0.0, 20000, 35000, "https://img.1688.com/ali007.jpg", "电子元件", "意法半导体", "单片机专营店", "1688", "阿里巴巴1688"),
        ("ALI008", "开关电源24V10A工业级DC稳压电源模块", 68.0, 0.0, 5000, 12000, "https://img.1688.com/ali008.jpg", "电子元件", "明纬", "明纬电源专营店", "1688", "阿里巴巴1688"),
        ("ALI009", "SMC型气缸标准气缸双作用铝合金气缸", 45.0, 0.0, 8000, 15000, "https://img.1688.com/ali009.jpg", "工业设备", "SMC", "SMC气动元件专营店", "1688", "阿里巴巴1688"),
        ("ALI010", "导轨式断路器DZ47-63 1P 2P 3P 4P空气开关", 18.5, 0.0, 25000, 78000, "https://img.1688.com/ali010.jpg", "工业设备", "正泰", "正泰电气专营店", "1688", "阿里巴巴1688"),
        ("ALI011", "精密压力表不锈钢耐震压力表Y-60 0-1.6MPa", 25.0, 0.0, 15000, 23000, "https://img.1688.com/ali011.jpg", "工业设备", "上仪", "上仪集团专营店", "1688", "阿里巴巴1688"),
        ("ALI012", "304不锈钢螺丝螺母组合套装M3-M10全牙半牙", 0.12, 0.0, 500000, 890000, "https://img.1688.com/ali012.jpg", "工业设备", "永年", "永年标准件专营店", "1688", "阿里巴巴1688"),
        ("ALI013", "聚氨酯PU输送带白色食品级平皮带流水线用", 35.0, 0.0, 5000, 8900, "https://img.1688.com/ali013.jpg", "工业设备", "申联", "申联传动专营店", "1688", "阿里巴巴1688"),
        ("ALI014", "轴承深沟球轴承6200系列精密轴承钢球", 8.5, 0.0, 100000, 230000, "https://img.1688.com/ali014.jpg", "工业设备", "人本", "人本轴承专营店", "1688", "阿里巴巴1688"),
        ("ALI015", "工业橡胶管液压软管耐高压钢丝胶管总成", 28.0, 0.0, 20000, 45000, "https://img.1688.com/ali015.jpg", "工业设备", "帕克", "帕克液压专营店", "1688", "阿里巴巴1688"),
        ("ALI016", "PP聚丙烯塑料颗粒注塑级再生料白色抗静电", 9.8, 0.0, 50000, 12000, "https://img.1688.com/ali016.jpg", "原材料", "中化", "中化塑料专营店", "1688", "阿里巴巴1688"),
        ("ALI017", "环氧树脂AB胶双组份透明灌封胶绝缘胶", 32.0, 0.0, 3000, 5600, "https://img.1688.com/ali017.jpg", "原材料", "赛力特", "赛力特化工专营店", "1688", "阿里巴巴1688"),
        ("ALI018", "工业清洗剂金属除油剂铁锈清除剂脱脂剂", 18.0, 0.0, 8000, 23000, "https://img.1688.com/ali018.jpg", "原材料", "安得力", "安得力化工专营店", "1688", "阿里巴巴1688"),
        ("ALI019", "热缩管绝缘套管电线接头保护套黑色彩色", 0.5, 0.0, 200000, 450000, "https://img.1688.com/ali019.jpg", "电子元件", "科讯", "科讯电子专营店", "1688", "阿里巴巴1688"),
        ("ALI020", "工业防爆灯LED防爆灯100W200W仓库厂房用", 168.0, 0.0, 2000, 6700, "https://img.1688.com/ali020.jpg", "工业设备", "通明", "通明电气专营店", "1688", "阿里巴巴1688"),
    ]
    for prod in products:
        c.execute(
            "INSERT OR REPLACE INTO t_product "
            "(id, title, price, original_price, stock, sales, image, category, brand, shop_name, platform, platform_name, created_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            prod + (now,),
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
    keyword = request.args.get("keyword", "").strip()
    platform = request.args.get("platform", "").strip()
    category = request.args.get("category", "").strip()
    page = max(int(request.args.get("page", 1)), 1)
    size = max(int(request.args.get("size", 20)), 1)
    offset = (page - 1) * size

    where, params = [], []
    if keyword:
        where.append("(title LIKE ? OR brand LIKE ? OR shop_name LIKE ?)")
        params += [f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"]
    if platform:
        where.append("platform = ?")
        params.append(platform)
    if category:
        where.append("category LIKE ?")
        params.append(f"%{category}%")
    clause = ("WHERE " + " AND ".join(where)) if where else ""

    conn = get_db()
    total = conn.execute(f"SELECT COUNT(*) FROM t_product {clause}", params).fetchone()[0]
    rows = conn.execute(
        f"SELECT * FROM t_product {clause} ORDER BY sales DESC LIMIT ? OFFSET ?",
        params + [size, offset],
    ).fetchall()
    conn.close()

    items = [{
        "id": r["id"], "title": r["title"], "price": r["price"],
        "originalPrice": r["original_price"], "stock": r["stock"],
        "sales": r["sales"], "image": r["image"], "category": r["category"],
        "brand": r["brand"], "shopName": r["shop_name"],
        "platform": r["platform"], "platformName": r["platform_name"],
    } for r in rows]
    return resp(0, "ok", {"total": total, "page": page, "size": size, "items": items})


@app.get("/internal/products/<product_id>")
def get_product(product_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM t_product WHERE id=?", (product_id,)).fetchone()
    conn.close()
    if not row:
        return resp(404, "product not found"), 404
    return resp(0, "ok", {
        "id": row["id"], "title": row["title"], "price": row["price"],
        "originalPrice": row["original_price"], "stock": row["stock"],
        "sales": row["sales"], "image": row["image"], "category": row["category"],
        "brand": row["brand"], "shopName": row["shop_name"],
        "platform": row["platform"], "platformName": row["platform_name"],
        "createdAt": row["created_at"],
    })


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
