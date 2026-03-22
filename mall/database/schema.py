"""数据库建表 SQL 语句"""

CREATE_USERS_TABLE = """
CREATE TABLE IF NOT EXISTS users (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    username    TEXT    NOT NULL UNIQUE,
    password    TEXT    NOT NULL,
    email       TEXT    NOT NULL UNIQUE,
    phone       TEXT    DEFAULT '',
    address     TEXT    DEFAULT '',
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP
)
"""

CREATE_CATEGORIES_TABLE = """
CREATE TABLE IF NOT EXISTS categories (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL UNIQUE,
    description TEXT    DEFAULT '',
    parent_id   INTEGER REFERENCES categories(id) ON DELETE SET NULL
)
"""

CREATE_PRODUCTS_TABLE = """
CREATE TABLE IF NOT EXISTS products (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL,
    price       REAL    NOT NULL CHECK(price >= 0),
    stock       INTEGER NOT NULL DEFAULT 0 CHECK(stock >= 0),
    category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE RESTRICT,
    description TEXT    DEFAULT '',
    image_url   TEXT    DEFAULT '',
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP
)
"""

CREATE_CART_TABLE = """
CREATE TABLE IF NOT EXISTS cart (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    product_id  INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    quantity    INTEGER NOT NULL DEFAULT 1 CHECK(quantity > 0),
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, product_id)
)
"""

CREATE_ORDERS_TABLE = """
CREATE TABLE IF NOT EXISTS orders (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    total_amount REAL    NOT NULL CHECK(total_amount >= 0),
    address      TEXT    NOT NULL,
    status       TEXT    NOT NULL DEFAULT 'pending'
                         CHECK(status IN ('pending','paid','shipped','delivered','cancelled')),
    created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at   DATETIME DEFAULT CURRENT_TIMESTAMP
)
"""

CREATE_ORDER_ITEMS_TABLE = """
CREATE TABLE IF NOT EXISTS order_items (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id    INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id  INTEGER NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
    quantity    INTEGER NOT NULL CHECK(quantity > 0),
    unit_price  REAL    NOT NULL CHECK(unit_price >= 0)
)
"""

ALL_TABLES = [
    CREATE_USERS_TABLE,
    CREATE_CATEGORIES_TABLE,
    CREATE_PRODUCTS_TABLE,
    CREATE_CART_TABLE,
    CREATE_ORDERS_TABLE,
    CREATE_ORDER_ITEMS_TABLE,
]


def init_db(conn) -> None:
    """初始化所有数据库表"""
    cursor = conn.cursor()
    for sql in ALL_TABLES:
        cursor.execute(sql)
    conn.commit()
