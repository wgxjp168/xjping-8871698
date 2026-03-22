-- ============================================================
-- biz_data_svc  生产级完整 DDL
-- 涵盖 7 个核心业务模块，共 35 张表
-- ============================================================
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

-- ============================================================
-- 模块 1: 用户与租户
-- ============================================================

CREATE TABLE IF NOT EXISTS tenants (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT    NOT NULL UNIQUE,
    code            TEXT    NOT NULL UNIQUE,
    status          TEXT    NOT NULL DEFAULT 'active'
                            CHECK(status IN ('active','suspended','cancelled')),
    plan            TEXT    NOT NULL DEFAULT 'basic'
                            CHECK(plan IN ('basic','pro','enterprise')),
    contact_name    TEXT    DEFAULT '',
    contact_phone   TEXT    DEFAULT '',
    contact_email   TEXT    DEFAULT '',
    address         TEXT    DEFAULT '',
    logo_url        TEXT    DEFAULT '',
    expired_at      DATETIME,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS users (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id       INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    username        TEXT    NOT NULL,
    password_hash   TEXT    NOT NULL,
    email           TEXT    NOT NULL DEFAULT '',
    phone           TEXT    NOT NULL DEFAULT '',
    real_name       TEXT    DEFAULT '',
    avatar_url      TEXT    DEFAULT '',
    gender          TEXT    DEFAULT 'unknown'
                            CHECK(gender IN ('male','female','unknown')),
    birthday        DATE,
    status          TEXT    NOT NULL DEFAULT 'active'
                            CHECK(status IN ('active','disabled','pending')),
    last_login_at   DATETIME,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tenant_id, username),
    UNIQUE(tenant_id, email)
);

CREATE TABLE IF NOT EXISTS roles (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id       INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name            TEXT    NOT NULL,
    code            TEXT    NOT NULL,
    description     TEXT    DEFAULT '',
    is_system       INTEGER NOT NULL DEFAULT 0 CHECK(is_system IN (0,1)),
    status          TEXT    NOT NULL DEFAULT 'active'
                            CHECK(status IN ('active','disabled')),
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tenant_id, code)
);

CREATE TABLE IF NOT EXISTS permissions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    code            TEXT    NOT NULL UNIQUE,
    name            TEXT    NOT NULL,
    module          TEXT    NOT NULL DEFAULT '',
    resource        TEXT    NOT NULL DEFAULT '',
    action          TEXT    NOT NULL DEFAULT '',
    description     TEXT    DEFAULT ''
);

CREATE TABLE IF NOT EXISTS user_roles (
    user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id         INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    granted_by      INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, role_id)
);

CREATE TABLE IF NOT EXISTS role_permissions (
    role_id         INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    permission_id   INTEGER NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    PRIMARY KEY (role_id, permission_id)
);

CREATE TABLE IF NOT EXISTS user_sessions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token           TEXT    NOT NULL UNIQUE,
    refresh_token   TEXT    UNIQUE,
    device_type     TEXT    DEFAULT 'web'
                            CHECK(device_type IN ('web','ios','android','api')),
    ip_address      TEXT    DEFAULT '',
    user_agent      TEXT    DEFAULT '',
    expires_at      DATETIME NOT NULL,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- 模块 2: C端商城
-- ============================================================

CREATE TABLE IF NOT EXISTS categories (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id       INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name            TEXT    NOT NULL,
    parent_id       INTEGER REFERENCES categories(id) ON DELETE SET NULL,
    icon_url        TEXT    DEFAULT '',
    banner_url      TEXT    DEFAULT '',
    sort_order      INTEGER DEFAULT 0,
    level           INTEGER NOT NULL DEFAULT 1,
    path            TEXT    DEFAULT '',
    status          TEXT    NOT NULL DEFAULT 'active'
                            CHECK(status IN ('active','disabled')),
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS products (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id       INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    category_id     INTEGER NOT NULL REFERENCES categories(id) ON DELETE RESTRICT,
    supplier_id     INTEGER,
    name            TEXT    NOT NULL,
    subtitle        TEXT    DEFAULT '',
    description     TEXT    DEFAULT '',
    cover_image     TEXT    DEFAULT '',
    unit            TEXT    DEFAULT '件',
    weight          REAL    DEFAULT 0,
    status          TEXT    NOT NULL DEFAULT 'on_sale'
                            CHECK(status IN ('on_sale','off_shelf','discontinued','draft')),
    is_featured     INTEGER NOT NULL DEFAULT 0 CHECK(is_featured IN (0,1)),
    tags            TEXT    DEFAULT '[]',
    sales_count     INTEGER NOT NULL DEFAULT 0,
    view_count      INTEGER NOT NULL DEFAULT 0,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS product_skus (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id      INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    sku_code        TEXT    NOT NULL UNIQUE,
    barcode         TEXT    DEFAULT '',
    attributes      TEXT    DEFAULT '{}',
    cost_price      REAL    NOT NULL DEFAULT 0 CHECK(cost_price >= 0),
    market_price    REAL    NOT NULL DEFAULT 0 CHECK(market_price >= 0),
    sale_price      REAL    NOT NULL DEFAULT 0 CHECK(sale_price >= 0),
    status          TEXT    NOT NULL DEFAULT 'active'
                            CHECK(status IN ('active','disabled')),
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS product_inventory (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    sku_id          INTEGER NOT NULL REFERENCES product_skus(id) ON DELETE CASCADE,
    warehouse_id    INTEGER NOT NULL DEFAULT 1,
    quantity        INTEGER NOT NULL DEFAULT 0 CHECK(quantity >= 0),
    reserved        INTEGER NOT NULL DEFAULT 0 CHECK(reserved >= 0),
    safety_stock    INTEGER NOT NULL DEFAULT 0,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(sku_id, warehouse_id)
);

CREATE TABLE IF NOT EXISTS product_images (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id      INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    sku_id          INTEGER REFERENCES product_skus(id) ON DELETE SET NULL,
    url             TEXT    NOT NULL,
    sort_order      INTEGER DEFAULT 0,
    is_cover        INTEGER DEFAULT 0 CHECK(is_cover IN (0,1))
);

CREATE TABLE IF NOT EXISTS cart_items (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tenant_id       INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    product_id      INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    sku_id          INTEGER NOT NULL REFERENCES product_skus(id) ON DELETE CASCADE,
    quantity        INTEGER NOT NULL DEFAULT 1 CHECK(quantity > 0),
    is_selected     INTEGER NOT NULL DEFAULT 1 CHECK(is_selected IN (0,1)),
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, sku_id)
);

CREATE TABLE IF NOT EXISTS delivery_addresses (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    receiver_name   TEXT    NOT NULL,
    phone           TEXT    NOT NULL,
    province        TEXT    NOT NULL DEFAULT '',
    city            TEXT    NOT NULL DEFAULT '',
    district        TEXT    NOT NULL DEFAULT '',
    street          TEXT    DEFAULT '',
    address_detail  TEXT    NOT NULL,
    postal_code     TEXT    DEFAULT '',
    is_default      INTEGER NOT NULL DEFAULT 0 CHECK(is_default IN (0,1)),
    tag             TEXT    DEFAULT '',
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- 模块 3: 订单交易
-- ============================================================

CREATE TABLE IF NOT EXISTS orders (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id       INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    order_no        TEXT    NOT NULL UNIQUE,
    user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    receiver_name   TEXT    NOT NULL,
    receiver_phone  TEXT    NOT NULL,
    province        TEXT    DEFAULT '',
    city            TEXT    DEFAULT '',
    district        TEXT    DEFAULT '',
    address_detail  TEXT    NOT NULL,
    status          TEXT    NOT NULL DEFAULT 'pending'
                            CHECK(status IN ('pending','paid','processing',
                                            'shipped','delivered','completed',
                                            'cancelled','refunding','refunded')),
    total_amount    REAL    NOT NULL DEFAULT 0 CHECK(total_amount >= 0),
    discount_amount REAL    NOT NULL DEFAULT 0 CHECK(discount_amount >= 0),
    shipping_fee    REAL    NOT NULL DEFAULT 0 CHECK(shipping_fee >= 0),
    pay_amount      REAL    NOT NULL DEFAULT 0 CHECK(pay_amount >= 0),
    payment_method  TEXT    DEFAULT ''
                            CHECK(payment_method IN ('','alipay','wechat','card','balance','cod')),
    paid_at         DATETIME,
    remark          TEXT    DEFAULT '',
    cancel_reason   TEXT    DEFAULT '',
    source          TEXT    DEFAULT 'pc'
                            CHECK(source IN ('pc','ios','android','mini_program','api')),
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS order_items (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id        INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id      INTEGER NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
    sku_id          INTEGER NOT NULL REFERENCES product_skus(id) ON DELETE RESTRICT,
    product_name    TEXT    NOT NULL,
    sku_attrs       TEXT    DEFAULT '{}',
    quantity        INTEGER NOT NULL CHECK(quantity > 0),
    unit_price      REAL    NOT NULL CHECK(unit_price >= 0),
    subtotal        REAL    NOT NULL CHECK(subtotal >= 0),
    refund_qty      INTEGER NOT NULL DEFAULT 0,
    refund_amount   REAL    NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS payments (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id        INTEGER NOT NULL REFERENCES orders(id) ON DELETE RESTRICT,
    payment_no      TEXT    NOT NULL UNIQUE,
    amount          REAL    NOT NULL CHECK(amount > 0),
    method          TEXT    NOT NULL DEFAULT 'alipay'
                            CHECK(method IN ('alipay','wechat','card','balance','cod')),
    channel_no      TEXT    DEFAULT '',
    status          TEXT    NOT NULL DEFAULT 'pending'
                            CHECK(status IN ('pending','success','failed','cancelled')),
    paid_at         DATETIME,
    expired_at      DATETIME,
    extra           TEXT    DEFAULT '{}',
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS refunds (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id        INTEGER NOT NULL REFERENCES orders(id) ON DELETE RESTRICT,
    payment_id      INTEGER REFERENCES payments(id) ON DELETE SET NULL,
    refund_no       TEXT    NOT NULL UNIQUE,
    amount          REAL    NOT NULL CHECK(amount > 0),
    refund_type     TEXT    NOT NULL DEFAULT 'refund_only'
                            CHECK(refund_type IN ('refund_only','return_refund')),
    reason          TEXT    NOT NULL DEFAULT '',
    images          TEXT    DEFAULT '[]',
    status          TEXT    NOT NULL DEFAULT 'pending'
                            CHECK(status IN ('pending','approved','rejected',
                                            'processing','completed','cancelled')),
    reject_reason   TEXT    DEFAULT '',
    apply_at        DATETIME DEFAULT CURRENT_TIMESTAMP,
    approve_at      DATETIME,
    complete_at     DATETIME,
    operator_id     INTEGER REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS logistics (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id        INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    company         TEXT    NOT NULL DEFAULT '',
    company_code    TEXT    DEFAULT '',
    tracking_no     TEXT    NOT NULL DEFAULT '',
    status          TEXT    NOT NULL DEFAULT 'pending'
                            CHECK(status IN ('pending','in_transit','out_for_delivery',
                                            'delivered','exception','returned')),
    signed_at       DATETIME,
    receiver        TEXT    DEFAULT '',
    traces          TEXT    DEFAULT '[]',
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- 模块 4: B端采购
-- ============================================================

CREATE TABLE IF NOT EXISTS purchase_requests (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id       INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    req_no          TEXT    NOT NULL UNIQUE,
    title           TEXT    NOT NULL,
    requester_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    dept            TEXT    DEFAULT '',
    category        TEXT    DEFAULT '',
    budget          REAL    DEFAULT 0 CHECK(budget >= 0),
    currency        TEXT    DEFAULT 'CNY',
    priority        TEXT    NOT NULL DEFAULT 'normal'
                            CHECK(priority IN ('low','normal','high','urgent')),
    required_date   DATE,
    reason          TEXT    DEFAULT '',
    status          TEXT    NOT NULL DEFAULT 'draft'
                            CHECK(status IN ('draft','submitted','approving',
                                            'approved','rejected','sourcing',
                                            'contracted','closed','cancelled')),
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS purchase_request_items (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id      INTEGER NOT NULL REFERENCES purchase_requests(id) ON DELETE CASCADE,
    product_name    TEXT    NOT NULL,
    spec            TEXT    DEFAULT '',
    quantity        REAL    NOT NULL CHECK(quantity > 0),
    unit            TEXT    DEFAULT '个',
    estimated_price REAL    DEFAULT 0 CHECK(estimated_price >= 0),
    note            TEXT    DEFAULT ''
);

CREATE TABLE IF NOT EXISTS approval_workflows (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id       INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name            TEXT    NOT NULL,
    business_type   TEXT    NOT NULL,
    status          TEXT    NOT NULL DEFAULT 'active'
                            CHECK(status IN ('active','disabled')),
    is_default      INTEGER NOT NULL DEFAULT 0 CHECK(is_default IN (0,1)),
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS approval_nodes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    workflow_id     INTEGER NOT NULL REFERENCES approval_workflows(id) ON DELETE CASCADE,
    node_name       TEXT    NOT NULL,
    node_type       TEXT    NOT NULL DEFAULT 'person'
                            CHECK(node_type IN ('person','role','dept_head','auto')),
    approver_ids    TEXT    DEFAULT '[]',
    sort_order      INTEGER NOT NULL DEFAULT 1,
    condition_expr  TEXT    DEFAULT '',
    action_type     TEXT    NOT NULL DEFAULT 'any'
                            CHECK(action_type IN ('any','all'))
);

CREATE TABLE IF NOT EXISTS approval_instances (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    workflow_id     INTEGER NOT NULL REFERENCES approval_workflows(id) ON DELETE RESTRICT,
    business_type   TEXT    NOT NULL,
    business_id     INTEGER NOT NULL,
    current_node    INTEGER DEFAULT 1,
    status          TEXT    NOT NULL DEFAULT 'pending'
                            CHECK(status IN ('pending','approved','rejected','cancelled')),
    started_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at    DATETIME,
    completed_by    INTEGER REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS approval_records (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    instance_id     INTEGER NOT NULL REFERENCES approval_instances(id) ON DELETE CASCADE,
    node_id         INTEGER NOT NULL REFERENCES approval_nodes(id) ON DELETE RESTRICT,
    node_order      INTEGER NOT NULL DEFAULT 1,
    approver_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    action          TEXT    NOT NULL
                            CHECK(action IN ('approve','reject','transfer','recall')),
    comment         TEXT    DEFAULT '',
    attachments     TEXT    DEFAULT '[]',
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sourcing_events (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id       INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    request_id      INTEGER REFERENCES purchase_requests(id) ON DELETE SET NULL,
    event_no        TEXT    NOT NULL UNIQUE,
    title           TEXT    NOT NULL,
    description     TEXT    DEFAULT '',
    deadline        DATETIME NOT NULL,
    status          TEXT    NOT NULL DEFAULT 'draft'
                            CHECK(status IN ('draft','published','closed','cancelled')),
    winner_supplier_id INTEGER,
    created_by      INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sourcing_quotes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id        INTEGER NOT NULL REFERENCES sourcing_events(id) ON DELETE CASCADE,
    supplier_id     INTEGER NOT NULL,
    unit_price      REAL    NOT NULL CHECK(unit_price >= 0),
    total_price     REAL    NOT NULL CHECK(total_price >= 0),
    currency        TEXT    DEFAULT 'CNY',
    delivery_days   INTEGER DEFAULT 0,
    warranty_months INTEGER DEFAULT 0,
    note            TEXT    DEFAULT '',
    attachments     TEXT    DEFAULT '[]',
    is_winner       INTEGER NOT NULL DEFAULT 0 CHECK(is_winner IN (0,1)),
    submitted_at    DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS contracts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id       INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    contract_no     TEXT    NOT NULL UNIQUE,
    title           TEXT    NOT NULL,
    contract_type   TEXT    NOT NULL DEFAULT 'purchase'
                            CHECK(contract_type IN ('purchase','framework','service','other')),
    party_a         TEXT    NOT NULL DEFAULT '',
    party_b         TEXT    NOT NULL DEFAULT '',
    supplier_id     INTEGER,
    sourcing_id     INTEGER REFERENCES sourcing_events(id) ON DELETE SET NULL,
    amount          REAL    NOT NULL DEFAULT 0 CHECK(amount >= 0),
    currency        TEXT    DEFAULT 'CNY',
    sign_date       DATE,
    start_date      DATE,
    end_date        DATE,
    payment_terms   TEXT    DEFAULT '',
    status          TEXT    NOT NULL DEFAULT 'draft'
                            CHECK(status IN ('draft','reviewing','active',
                                            'expired','terminated','cancelled')),
    file_url        TEXT    DEFAULT '',
    signed_by       INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- 模块 5: 供应商
-- ============================================================

CREATE TABLE IF NOT EXISTS suppliers (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id       INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name            TEXT    NOT NULL,
    code            TEXT    NOT NULL,
    short_name      TEXT    DEFAULT '',
    supplier_type   TEXT    NOT NULL DEFAULT 'manufacturer'
                            CHECK(supplier_type IN ('manufacturer','distributor',
                                                   'agent','service','other')),
    status          TEXT    NOT NULL DEFAULT 'pending'
                            CHECK(status IN ('pending','reviewing','active',
                                            'suspended','blacklisted')),
    contact_name    TEXT    DEFAULT '',
    phone           TEXT    DEFAULT '',
    email           TEXT    DEFAULT '',
    address         TEXT    DEFAULT '',
    website         TEXT    DEFAULT '',
    tax_no          TEXT    DEFAULT '',
    bank_account    TEXT    DEFAULT '',
    bank_name       TEXT    DEFAULT '',
    payment_terms   TEXT    DEFAULT 'net30',
    credit_limit    REAL    DEFAULT 0,
    reviewer_id     INTEGER REFERENCES users(id) ON DELETE SET NULL,
    reviewed_at     DATETIME,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tenant_id, code)
);

CREATE TABLE IF NOT EXISTS supplier_qualifications (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_id     INTEGER NOT NULL REFERENCES suppliers(id) ON DELETE CASCADE,
    qual_type       TEXT    NOT NULL,
    name            TEXT    NOT NULL,
    issue_org       TEXT    DEFAULT '',
    issue_date      DATE,
    expire_date     DATE,
    file_url        TEXT    DEFAULT '',
    status          TEXT    NOT NULL DEFAULT 'valid'
                            CHECK(status IN ('valid','expired','pending','rejected')),
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS supplier_quotes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_id     INTEGER NOT NULL REFERENCES suppliers(id) ON DELETE CASCADE,
    tenant_id       INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    product_name    TEXT    NOT NULL,
    spec            TEXT    DEFAULT '',
    unit            TEXT    DEFAULT '个',
    unit_price      REAL    NOT NULL CHECK(unit_price >= 0),
    currency        TEXT    DEFAULT 'CNY',
    min_qty         REAL    DEFAULT 1,
    delivery_days   INTEGER DEFAULT 0,
    valid_until     DATE,
    status          TEXT    NOT NULL DEFAULT 'active'
                            CHECK(status IN ('active','expired','withdrawn')),
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS supplier_scores (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_id     INTEGER NOT NULL REFERENCES suppliers(id) ON DELETE CASCADE,
    tenant_id       INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    period          TEXT    NOT NULL,
    quality_score   REAL    NOT NULL DEFAULT 0 CHECK(quality_score BETWEEN 0 AND 100),
    delivery_score  REAL    NOT NULL DEFAULT 0 CHECK(delivery_score BETWEEN 0 AND 100),
    price_score     REAL    NOT NULL DEFAULT 0 CHECK(price_score BETWEEN 0 AND 100),
    service_score   REAL    NOT NULL DEFAULT 0 CHECK(service_score BETWEEN 0 AND 100),
    total_score     REAL    NOT NULL DEFAULT 0 CHECK(total_score BETWEEN 0 AND 100),
    level           TEXT    NOT NULL DEFAULT 'C'
                            CHECK(level IN ('S','A','B','C','D')),
    evaluator_id    INTEGER REFERENCES users(id) ON DELETE SET NULL,
    note            TEXT    DEFAULT '',
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(supplier_id, tenant_id, period)
);

CREATE TABLE IF NOT EXISTS supplier_risks (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_id     INTEGER NOT NULL REFERENCES suppliers(id) ON DELETE CASCADE,
    risk_type       TEXT    NOT NULL
                            CHECK(risk_type IN ('financial','compliance','operational',
                                               'reputation','delivery','quality','other')),
    level           TEXT    NOT NULL DEFAULT 'medium'
                            CHECK(level IN ('low','medium','high','critical')),
    description     TEXT    NOT NULL,
    source          TEXT    DEFAULT '',
    status          TEXT    NOT NULL DEFAULT 'open'
                            CHECK(status IN ('open','mitigating','resolved','accepted')),
    found_at        DATETIME DEFAULT CURRENT_TIMESTAMP,
    resolved_at     DATETIME,
    resolver_id     INTEGER REFERENCES users(id) ON DELETE SET NULL,
    resolution_note TEXT    DEFAULT ''
);

-- ============================================================
-- 模块 6: 发票与对账
-- ============================================================

CREATE TABLE IF NOT EXISTS invoices (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id       INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    invoice_no      TEXT    NOT NULL UNIQUE,
    invoice_type    TEXT    NOT NULL DEFAULT 'special_vat'
                            CHECK(invoice_type IN ('special_vat','ordinary_vat',
                                                  'electronic','receipt')),
    direction       TEXT    NOT NULL DEFAULT 'in'
                            CHECK(direction IN ('in','out')),
    supplier_id     INTEGER REFERENCES suppliers(id) ON DELETE SET NULL,
    order_ids       TEXT    DEFAULT '[]',
    amount          REAL    NOT NULL CHECK(amount >= 0),
    tax_rate        REAL    NOT NULL DEFAULT 0.13 CHECK(tax_rate >= 0 AND tax_rate <= 1),
    tax_amount      REAL    NOT NULL DEFAULT 0 CHECK(tax_amount >= 0),
    total_amount    REAL    NOT NULL CHECK(total_amount >= 0),
    issue_date      DATE    NOT NULL,
    buyer_name      TEXT    DEFAULT '',
    buyer_tax_no    TEXT    DEFAULT '',
    seller_name     TEXT    DEFAULT '',
    seller_tax_no   TEXT    DEFAULT '',
    status          TEXT    NOT NULL DEFAULT 'pending'
                            CHECK(status IN ('pending','verified','rejected','cancelled')),
    file_url        TEXT    DEFAULT '',
    verified_by     INTEGER REFERENCES users(id) ON DELETE SET NULL,
    verified_at     DATETIME,
    reject_reason   TEXT    DEFAULT '',
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS invoice_items (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id      INTEGER NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
    product_name    TEXT    NOT NULL,
    spec            TEXT    DEFAULT '',
    unit            TEXT    DEFAULT '件',
    quantity        REAL    NOT NULL CHECK(quantity > 0),
    unit_price      REAL    NOT NULL CHECK(unit_price >= 0),
    amount          REAL    NOT NULL CHECK(amount >= 0),
    tax_rate        REAL    NOT NULL DEFAULT 0.13,
    tax_amount      REAL    NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS reconciliations (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id       INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    recon_no        TEXT    NOT NULL UNIQUE,
    supplier_id     INTEGER NOT NULL REFERENCES suppliers(id) ON DELETE RESTRICT,
    period_start    DATE    NOT NULL,
    period_end      DATE    NOT NULL,
    order_amount    REAL    NOT NULL DEFAULT 0,
    invoice_amount  REAL    NOT NULL DEFAULT 0,
    diff_amount     REAL    NOT NULL DEFAULT 0,
    status          TEXT    NOT NULL DEFAULT 'draft'
                            CHECK(status IN ('draft','sent','disputed','confirmed','closed')),
    supplier_confirmed INTEGER NOT NULL DEFAULT 0 CHECK(supplier_confirmed IN (0,1)),
    confirmed_at    DATETIME,
    note            TEXT    DEFAULT '',
    created_by      INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS settlements (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id       INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    settle_no       TEXT    NOT NULL UNIQUE,
    supplier_id     INTEGER NOT NULL REFERENCES suppliers(id) ON DELETE RESTRICT,
    reconciliation_id INTEGER REFERENCES reconciliations(id) ON DELETE SET NULL,
    invoice_ids     TEXT    DEFAULT '[]',
    amount          REAL    NOT NULL CHECK(amount > 0),
    currency        TEXT    DEFAULT 'CNY',
    payment_method  TEXT    NOT NULL DEFAULT 'bank_transfer'
                            CHECK(payment_method IN ('bank_transfer','check',
                                                    'cash','alipay','other')),
    bank_account    TEXT    DEFAULT '',
    status          TEXT    NOT NULL DEFAULT 'pending'
                            CHECK(status IN ('pending','approved','paid',
                                            'rejected','cancelled')),
    apply_at        DATETIME DEFAULT CURRENT_TIMESTAMP,
    approved_at     DATETIME,
    paid_at         DATETIME,
    approver_id     INTEGER REFERENCES users(id) ON DELETE SET NULL,
    operator_id     INTEGER REFERENCES users(id) ON DELETE SET NULL,
    note            TEXT    DEFAULT '',
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- 模块 7: 消息通知
-- ============================================================

CREATE TABLE IF NOT EXISTS notification_templates (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id       INTEGER REFERENCES tenants(id) ON DELETE CASCADE,
    code            TEXT    NOT NULL UNIQUE,
    name            TEXT    NOT NULL,
    channel         TEXT    NOT NULL DEFAULT 'internal'
                            CHECK(channel IN ('internal','sms','email','push','all')),
    title_template  TEXT    DEFAULT '',
    content_template TEXT   NOT NULL,
    variables       TEXT    DEFAULT '[]',
    status          TEXT    NOT NULL DEFAULT 'active'
                            CHECK(status IN ('active','disabled')),
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS internal_messages (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id       INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    sender_id       INTEGER REFERENCES users(id) ON DELETE SET NULL,
    receiver_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    msg_type        TEXT    NOT NULL DEFAULT 'system'
                            CHECK(msg_type IN ('system','business','personal','alert')),
    title           TEXT    NOT NULL,
    content         TEXT    NOT NULL,
    biz_type        TEXT    DEFAULT '',
    biz_id          INTEGER DEFAULT 0,
    action_url      TEXT    DEFAULT '',
    is_read         INTEGER NOT NULL DEFAULT 0 CHECK(is_read IN (0,1)),
    read_at         DATETIME,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sms_records (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id       INTEGER REFERENCES tenants(id) ON DELETE SET NULL,
    phone           TEXT    NOT NULL,
    template_code   TEXT    DEFAULT '',
    params          TEXT    DEFAULT '{}',
    content         TEXT    NOT NULL,
    status          TEXT    NOT NULL DEFAULT 'pending'
                            CHECK(status IN ('pending','sent','delivered','failed')),
    provider        TEXT    DEFAULT 'aliyun'
                            CHECK(provider IN ('aliyun','tencent','netease','other')),
    provider_msg_id TEXT    DEFAULT '',
    error_msg       TEXT    DEFAULT '',
    sent_at         DATETIME,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS email_records (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id       INTEGER REFERENCES tenants(id) ON DELETE SET NULL,
    to_email        TEXT    NOT NULL,
    cc_emails       TEXT    DEFAULT '[]',
    bcc_emails      TEXT    DEFAULT '[]',
    subject         TEXT    NOT NULL,
    body            TEXT    NOT NULL,
    body_type       TEXT    NOT NULL DEFAULT 'html'
                            CHECK(body_type IN ('html','text')),
    template_code   TEXT    DEFAULT '',
    attachments     TEXT    DEFAULT '[]',
    status          TEXT    NOT NULL DEFAULT 'pending'
                            CHECK(status IN ('pending','sent','failed','bounced')),
    error_msg       TEXT    DEFAULT '',
    retry_count     INTEGER NOT NULL DEFAULT 0,
    sent_at         DATETIME,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- 索引
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_users_tenant        ON users(tenant_id, status);
CREATE INDEX IF NOT EXISTS idx_users_phone         ON users(phone);
CREATE INDEX IF NOT EXISTS idx_user_sessions_token ON user_sessions(token);
CREATE INDEX IF NOT EXISTS idx_user_roles_user     ON user_roles(user_id);
CREATE INDEX IF NOT EXISTS idx_user_roles_role     ON user_roles(role_id);

CREATE INDEX IF NOT EXISTS idx_products_tenant     ON products(tenant_id, status);
CREATE INDEX IF NOT EXISTS idx_products_category   ON products(category_id);
CREATE INDEX IF NOT EXISTS idx_skus_product        ON product_skus(product_id);
CREATE INDEX IF NOT EXISTS idx_inventory_sku       ON product_inventory(sku_id);
CREATE INDEX IF NOT EXISTS idx_cart_user           ON cart_items(user_id);
CREATE INDEX IF NOT EXISTS idx_addresses_user      ON delivery_addresses(user_id, is_default);

CREATE INDEX IF NOT EXISTS idx_orders_tenant       ON orders(tenant_id, status);
CREATE INDEX IF NOT EXISTS idx_orders_user         ON orders(user_id);
CREATE INDEX IF NOT EXISTS idx_orders_no           ON orders(order_no);
CREATE INDEX IF NOT EXISTS idx_payments_order      ON payments(order_id);
CREATE INDEX IF NOT EXISTS idx_refunds_order       ON refunds(order_id);
CREATE INDEX IF NOT EXISTS idx_logistics_order     ON logistics(order_id);

CREATE INDEX IF NOT EXISTS idx_pr_tenant           ON purchase_requests(tenant_id, status);
CREATE INDEX IF NOT EXISTS idx_pr_requester        ON purchase_requests(requester_id);
CREATE INDEX IF NOT EXISTS idx_ai_business         ON approval_instances(business_type, business_id);
CREATE INDEX IF NOT EXISTS idx_contracts_tenant    ON contracts(tenant_id, status);

CREATE INDEX IF NOT EXISTS idx_suppliers_tenant    ON suppliers(tenant_id, status);
CREATE INDEX IF NOT EXISTS idx_sup_scores_period   ON supplier_scores(supplier_id, period);
CREATE INDEX IF NOT EXISTS idx_sup_risks_status    ON supplier_risks(supplier_id, status);

CREATE INDEX IF NOT EXISTS idx_invoices_tenant     ON invoices(tenant_id, status);
CREATE INDEX IF NOT EXISTS idx_invoices_supplier   ON invoices(supplier_id);
CREATE INDEX IF NOT EXISTS idx_recon_supplier      ON reconciliations(supplier_id, status);
CREATE INDEX IF NOT EXISTS idx_settlements_status  ON settlements(tenant_id, status);

CREATE INDEX IF NOT EXISTS idx_messages_receiver   ON internal_messages(receiver_id, is_read);
CREATE INDEX IF NOT EXISTS idx_sms_phone           ON sms_records(phone, created_at);
CREATE INDEX IF NOT EXISTS idx_email_to            ON email_records(to_email, created_at);
