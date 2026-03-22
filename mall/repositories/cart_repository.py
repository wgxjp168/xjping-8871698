import sqlite3
from typing import Optional, List
from ..models.cart import CartItem


class CartRepository:
    """购物车数据存储层 - 负责购物车的增删改查操作"""

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    # ------------------------------------------------------------------ #
    #  写操作                                                               #
    # ------------------------------------------------------------------ #

    def add_item(self, item: CartItem) -> CartItem:
        """向购物车添加商品；若商品已存在则累加数量"""
        sql = """
            INSERT INTO cart (user_id, product_id, quantity)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, product_id)
            DO UPDATE SET quantity = quantity + excluded.quantity
        """
        cursor = self._conn.cursor()
        cursor.execute(sql, (item.user_id, item.product_id, item.quantity))
        self._conn.commit()
        # 查出真实 id
        cursor.execute(
            'SELECT * FROM cart WHERE user_id = ? AND product_id = ?',
            (item.user_id, item.product_id),
        )
        row = cursor.fetchone()
        return CartItem.from_row(tuple(row)) if row else item

    def update_quantity(self, user_id: int, product_id: int, quantity: int) -> bool:
        """直接设置某商品的购物车数量（quantity 必须 > 0）"""
        if quantity <= 0:
            return self.remove_item(user_id, product_id)
        sql = """
            UPDATE cart
            SET quantity = ?
            WHERE user_id = ? AND product_id = ?
        """
        cursor = self._conn.cursor()
        cursor.execute(sql, (quantity, user_id, product_id))
        self._conn.commit()
        return cursor.rowcount > 0

    def remove_item(self, user_id: int, product_id: int) -> bool:
        """从购物车移除指定商品"""
        cursor = self._conn.cursor()
        cursor.execute(
            'DELETE FROM cart WHERE user_id = ? AND product_id = ?',
            (user_id, product_id),
        )
        self._conn.commit()
        return cursor.rowcount > 0

    def clear(self, user_id: int) -> int:
        """清空某用户的购物车，返回删除条数"""
        cursor = self._conn.cursor()
        cursor.execute('DELETE FROM cart WHERE user_id = ?', (user_id,))
        self._conn.commit()
        return cursor.rowcount

    # ------------------------------------------------------------------ #
    #  读操作                                                               #
    # ------------------------------------------------------------------ #

    def find_by_user(self, user_id: int) -> List[CartItem]:
        """查询某用户的所有购物车商品"""
        cursor = self._conn.cursor()
        cursor.execute(
            'SELECT * FROM cart WHERE user_id = ? ORDER BY id',
            (user_id,),
        )
        return [CartItem.from_row(tuple(row)) for row in cursor.fetchall()]

    def find_item(self, user_id: int, product_id: int) -> Optional[CartItem]:
        """查询购物车中某条目"""
        cursor = self._conn.cursor()
        cursor.execute(
            'SELECT * FROM cart WHERE user_id = ? AND product_id = ?',
            (user_id, product_id),
        )
        row = cursor.fetchone()
        return CartItem.from_row(tuple(row)) if row else None

    def count(self, user_id: int) -> int:
        """统计某用户购物车商品种数"""
        cursor = self._conn.cursor()
        cursor.execute(
            'SELECT COUNT(*) FROM cart WHERE user_id = ?',
            (user_id,),
        )
        return cursor.fetchone()[0]
