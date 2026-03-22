import sqlite3
from typing import Optional, List
from ..models.product import Product


class ProductRepository:
    """商品数据存储层 - 负责商品的增删改查操作"""

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    # ------------------------------------------------------------------ #
    #  写操作                                                               #
    # ------------------------------------------------------------------ #

    def add(self, product: Product) -> Product:
        """新增商品，返回含 id 的 Product 对象"""
        sql = """
            INSERT INTO products (name, price, stock, category_id, description, image_url)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        cursor = self._conn.cursor()
        cursor.execute(sql, (
            product.name, product.price, product.stock, product.category_id,
            product.description, product.image_url,
        ))
        self._conn.commit()
        product.id = cursor.lastrowid
        return product

    def update(self, product: Product) -> bool:
        """更新商品信息"""
        sql = """
            UPDATE products
            SET name = ?, price = ?, stock = ?, category_id = ?,
                description = ?, image_url = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """
        cursor = self._conn.cursor()
        cursor.execute(sql, (
            product.name, product.price, product.stock, product.category_id,
            product.description, product.image_url, product.id,
        ))
        self._conn.commit()
        return cursor.rowcount > 0

    def update_stock(self, product_id: int, delta: int) -> bool:
        """调整库存（delta 为正则增加，为负则减少），库存不能为负数"""
        sql = """
            UPDATE products
            SET stock = stock + ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND stock + ? >= 0
        """
        cursor = self._conn.cursor()
        cursor.execute(sql, (delta, product_id, delta))
        self._conn.commit()
        return cursor.rowcount > 0

    def delete(self, product_id: int) -> bool:
        """删除商品"""
        cursor = self._conn.cursor()
        cursor.execute('DELETE FROM products WHERE id = ?', (product_id,))
        self._conn.commit()
        return cursor.rowcount > 0

    # ------------------------------------------------------------------ #
    #  读操作                                                               #
    # ------------------------------------------------------------------ #

    def find_by_id(self, product_id: int) -> Optional[Product]:
        """按 id 查找商品"""
        cursor = self._conn.cursor()
        cursor.execute('SELECT * FROM products WHERE id = ?', (product_id,))
        row = cursor.fetchone()
        return Product.from_row(tuple(row)) if row else None

    def find_all(self) -> List[Product]:
        """查询所有商品"""
        cursor = self._conn.cursor()
        cursor.execute('SELECT * FROM products ORDER BY id')
        return [Product.from_row(tuple(row)) for row in cursor.fetchall()]

    def find_by_category(self, category_id: int) -> List[Product]:
        """按分类查询商品"""
        cursor = self._conn.cursor()
        cursor.execute(
            'SELECT * FROM products WHERE category_id = ? ORDER BY id',
            (category_id,),
        )
        return [Product.from_row(tuple(row)) for row in cursor.fetchall()]

    def find_by_name(self, keyword: str) -> List[Product]:
        """按关键字模糊搜索商品名称"""
        cursor = self._conn.cursor()
        cursor.execute(
            'SELECT * FROM products WHERE name LIKE ? ORDER BY id',
            (f'%{keyword}%',),
        )
        return [Product.from_row(tuple(row)) for row in cursor.fetchall()]

    def find_in_stock(self) -> List[Product]:
        """查询有库存的商品"""
        cursor = self._conn.cursor()
        cursor.execute('SELECT * FROM products WHERE stock > 0 ORDER BY id')
        return [Product.from_row(tuple(row)) for row in cursor.fetchall()]

    def find_by_price_range(self, min_price: float, max_price: float) -> List[Product]:
        """按价格区间查询商品"""
        cursor = self._conn.cursor()
        cursor.execute(
            'SELECT * FROM products WHERE price BETWEEN ? AND ? ORDER BY price',
            (min_price, max_price),
        )
        return [Product.from_row(tuple(row)) for row in cursor.fetchall()]
