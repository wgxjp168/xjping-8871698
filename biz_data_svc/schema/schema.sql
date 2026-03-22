-- ============================================================
-- biz-data-svc  完整数据库 DDL
-- 覆盖 7 个业务模块
-- ============================================================

PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

-- ============================================================
-- 模块 1: 用户与租户
-- ============================================================

CREATE TABLE IF NOT EXISTS tenants (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL UNIQUE,
    code        TEXT    NOT NULL UNIQUE,          -- 租户唯一编码
    status      TEXT    NOT NULL DEFAULT 'active'
                        CHECK(status IN ('active','suspended','cancelled')),
    plan        TEXT    NOT NULL DEFAULT 'basic'
                        CHECK(plan IN ('basic','pro','enterprise')),
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS users (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id   INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    username    TEXT    NOT NULL,
    password    TEXT    NOT NULL,
    email       TEXT    NOT NULL,
    phone       TEXT    DEFAULT '',
    avatar_url  TEXT    DEFAULT '',
    is_active   INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0,1)),
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tenant_id, username),
    UNIQUE(tenant_id, email)
);

CREATE TABLE IF NOT EXISTS user_sessions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token       TEXT    NOT NULL UNIQUE,
    expires_at  DATETIME NOT NULL,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- 模块 2: 商场基础信息
-- ============================================================

CREATE TABLE IF NOT EXISTS malls (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id   INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name        TEXT    NOT NULL,
    address     TEXT    NOT NULL DEFAULT '',
    city        TEXT    NOT NULL DEFAULT '',
    province    TEXT    NOT NULL DEFAULT '',
    phone       TEXT    DEFAULT '',
    status      TEXT    NOT NULL DEFAULT 'open'
                        CHECK(status IN ('open','closed','renovation')),
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS floors (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    mall_id     INTEGER NOT NULL REFERENCES malls(id) ON DELETE CASCADE,
    floor_no    TEXT    NOT NULL,               -- 如 "B1","1F","2F"
    description TEXT    DEFAULT '',
    UNIQUE(mall_id, floor_no)
);

CREATE TABLE IF NOT EXISTS shops (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    mall_id     INTEGER NOT NULL REFERENCES malls(id) ON DELETE CASCADE,
    floor_id    INTEGER REFERENCES floors(id) ON DELETE SET NULL,
    name        TEXT    NOT NULL,
    shop_no     TEXT    NOT NULL,               -- 铺位编号
    area        REAL    DEFAULT 0,              -- 面积 m²
    status      TEXT    NOT NULL DEFAULT 'vacant'
                        CHECK(status IN ('vacant','leased','renovation')),
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(mall_id, shop_no)
);

-- ============================================================
-- 模块 3: 员工与角色权限
-- ============================================================

CREATE TABLE IF NOT EXISTS roles (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id   INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name        TEXT    NOT NULL,
    description TEXT    DEFAULT '',
    UNIQUE(tenant_id, name)
);

CREATE TABLE IF NOT EXISTS permissions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    code        TEXT    NOT NULL UNIQUE,        -- 权限代码，如 "order:read"
    description TEXT    DEFAULT ''
);

CREATE TABLE IF NOT EXISTS role_permissions (
    role_id       INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    permission_id INTEGER NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    PRIMARY KEY (role_id, permission_id)
);

CREATE TABLE IF NOT EXISTS staff (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id   INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    mall_id     INTEGER REFERENCES malls(id) ON DELETE SET NULL,
    user_id     INTEGER REFERENCES users(id) ON DELETE SET NULL,
    name        TEXT    NOT NULL,
    employee_no TEXT    NOT NULL,
    position    TEXT    DEFAULT '',
    phone       TEXT    DEFAULT '',
    status      TEXT    NOT NULL DEFAULT 'active'
                        CHECK(status IN ('active','inactive','resigned')),
    hired_at    DATE,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tenant_id, employee_no)
);

CREATE TABLE IF NOT EXISTS staff_roles (
    staff_id INTEGER NOT NULL REFERENCES staff(id) ON DELETE CASCADE,
    role_id  INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    PRIMARY KEY (staff_id, role_id)
);

-- ============================================================
-- 模块 4: 商品与类目
-- ============================================================

CREATE TABLE IF NOT EXISTS categories (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id   INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name        TEXT    NOT NULL,
    parent_id   INTEGER REFERENCES categories(id) ON DELETE SET NULL,
    sort_order  INTEGER DEFAULT 0,
    UNIQUE(tenant_id, name, parent_id)
);

CREATE TABLE IF NOT EXISTS brands (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id   INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name        TEXT    NOT NULL,
    logo_url    TEXT    DEFAULT '',
    UNIQUE(tenant_id, name)
);

CREATE TABLE IF NOT EXISTS products (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id   INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE RESTRICT,
    brand_id    INTEGER REFERENCES brands(id) ON DELETE SET NULL,
    name        TEXT    NOT NULL,
    sku         TEXT    NOT NULL,
    barcode     TEXT    DEFAULT '',
    unit        TEXT    DEFAULT '件',
    cost_price  REAL    NOT NULL DEFAULT 0 CHECK(cost_price >= 0),
    sale_price  REAL    NOT NULL DEFAULT 0 CHECK(sale_price >= 0),
    description TEXT    DEFAULT '',
    image_url   TEXT    DEFAULT '',
    status      TEXT    NOT NULL DEFAULT 'on_sale'
                        CHECK(status IN ('on_sale','off_shelf','discontinued')),
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tenant_id, sku)
);

-- ============================================================
-- 模块 5: 订单与支付
-- ============================================================

CREATE TABLE IF NOT EXISTS customers (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id   INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id     INTEGER REFERENCES users(id) ON DELETE SET NULL,
    name        TEXT    NOT NULL DEFAULT '',
    phone       TEXT    NOT NULL DEFAULT '',
    email       TEXT    DEFAULT '',
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS orders (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id     INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    mall_id       INTEGER REFERENCES malls(id) ON DELETE SET NULL,
    customer_id   INTEGER REFERENCES customers(id) ON DELETE SET NULL,
    order_no      TEXT    NOT NULL UNIQUE,
    total_amount  REAL    NOT NULL DEFAULT 0 CHECK(total_amount >= 0),
    discount_amount REAL  NOT NULL DEFAULT 0 CHECK(discount_amount >= 0),
    pay_amount    REAL    NOT NULL DEFAULT 0 CHECK(pay_amount >= 0),
    status        TEXT    NOT NULL DEFAULT 'pending'
                          CHECK(status IN ('pending','paid','processing',
                                          'shipped','delivered','cancelled','refunded')),
    remark        TEXT    DEFAULT '',
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS order_items (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id    INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id  INTEGER NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
    product_name TEXT   NOT NULL,              -- 快照冗余，防止商品改名后订单失真
    quantity    INTEGER NOT NULL CHECK(quantity > 0),
    unit_price  REAL    NOT NULL CHECK(unit_price >= 0),
    subtotal    REAL    NOT NULL CHECK(subtotal >= 0)
);

CREATE TABLE IF NOT EXISTS payments (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id     INTEGER NOT NULL REFERENCES orders(id) ON DELETE RESTRICT,
    payment_no   TEXT    NOT NULL UNIQUE,
    amount       REAL    NOT NULL CHECK(amount > 0),
    method       TEXT    NOT NULL DEFAULT 'cash'
                          CHECK(method IN ('cash','alipay','wechat','card','other')),
    status       TEXT    NOT NULL DEFAULT 'pending'
                          CHECK(status IN ('pending','success','failed','refunded')),
    paid_at      DATETIME,
    created_at   DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- 模块 6: 库存与仓储
-- ============================================================

CREATE TABLE IF NOT EXISTS warehouses (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id   INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    mall_id     INTEGER REFERENCES malls(id) ON DELETE SET NULL,
    name        TEXT    NOT NULL,
    address     TEXT    DEFAULT '',
    UNIQUE(tenant_id, name)
);

CREATE TABLE IF NOT EXISTS inventory (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    warehouse_id  INTEGER NOT NULL REFERENCES warehouses(id) ON DELETE CASCADE,
    product_id    INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    quantity      INTEGER NOT NULL DEFAULT 0 CHECK(quantity >= 0),
    safety_stock  INTEGER NOT NULL DEFAULT 0,  -- 安全库存预警值
    updated_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(warehouse_id, product_id)
);

CREATE TABLE IF NOT EXISTS stock_movements (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    warehouse_id  INTEGER NOT NULL REFERENCES warehouses(id) ON DELETE CASCADE,
    product_id    INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    movement_type TEXT    NOT NULL
                          CHECK(movement_type IN ('in','out','adjust','transfer')),
    quantity      INTEGER NOT NULL,            -- 正数入库，负数出库
    ref_type      TEXT    DEFAULT '',          -- 关联单据类型：order / purchase / adjust
    ref_id        INTEGER DEFAULT 0,           -- 关联单据 id
    remark        TEXT    DEFAULT '',
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- 模块 7: 营销与促销
-- ============================================================

CREATE TABLE IF NOT EXISTS promotions (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id     INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name          TEXT    NOT NULL,
    promo_type    TEXT    NOT NULL
                          CHECK(promo_type IN ('discount','full_reduce','gift','flash_sale')),
    discount_rate REAL    DEFAULT 1.0 CHECK(discount_rate > 0 AND discount_rate <= 1),
    reduce_amount REAL    DEFAULT 0   CHECK(reduce_amount >= 0),
    min_amount    REAL    DEFAULT 0   CHECK(min_amount >= 0),  -- 满减门槛
    start_at      DATETIME NOT NULL,
    end_at        DATETIME NOT NULL,
    status        TEXT    NOT NULL DEFAULT 'draft'
                          CHECK(status IN ('draft','active','paused','ended')),
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS promotion_products (
    promotion_id INTEGER NOT NULL REFERENCES promotions(id) ON DELETE CASCADE,
    product_id   INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    PRIMARY KEY (promotion_id, product_id)
);

CREATE TABLE IF NOT EXISTS coupons (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id     INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    promotion_id  INTEGER REFERENCES promotions(id) ON DELETE SET NULL,
    code          TEXT    NOT NULL UNIQUE,
    face_value    REAL    NOT NULL CHECK(face_value > 0),  -- 券面值
    min_amount    REAL    NOT NULL DEFAULT 0,              -- 使用门槛
    total_qty     INTEGER NOT NULL DEFAULT 1,
    used_qty      INTEGER NOT NULL DEFAULT 0,
    per_user_limit INTEGER NOT NULL DEFAULT 1,
    start_at      DATETIME NOT NULL,
    end_at        DATETIME NOT NULL,
    status        TEXT    NOT NULL DEFAULT 'active'
                          CHECK(status IN ('active','paused','exhausted','expired'))
);

CREATE TABLE IF NOT EXISTS coupon_records (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    coupon_id   INTEGER NOT NULL REFERENCES coupons(id) ON DELETE CASCADE,
    customer_id INTEGER NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    order_id    INTEGER REFERENCES orders(id) ON DELETE SET NULL,
    used_at     DATETIME,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(coupon_id, customer_id)   -- 每客户限领一次
);

-- ============================================================
-- 索引 (提升常用查询性能)
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_users_tenant      ON users(tenant_id);
CREATE INDEX IF NOT EXISTS idx_staff_tenant      ON staff(tenant_id);
CREATE INDEX IF NOT EXISTS idx_products_tenant   ON products(tenant_id);
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category_id);
CREATE INDEX IF NOT EXISTS idx_orders_tenant     ON orders(tenant_id);
CREATE INDEX IF NOT EXISTS idx_orders_customer   ON orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_status     ON orders(status);
CREATE INDEX IF NOT EXISTS idx_inventory_product ON inventory(product_id);
CREATE INDEX IF NOT EXISTS idx_stock_movements   ON stock_movements(product_id, created_at);
CREATE INDEX IF NOT EXISTS idx_promotions_tenant ON promotions(tenant_id, status);
