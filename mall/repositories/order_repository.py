import sqlite3
from typing import Optional, List
from ..models.order import Order, OrderItem


class OrderRepository:
    """订单数据存储层 - 负责订单及订单明细的增删改查操作"""

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    # ------------------------------------------------------------------ #
    #  写操作                                                               #
    # ------------------------------------------------------------------ #

    def create_order(self, order: Order) -> Order:
        """创建订单及其所有明细（事务操作）"""
        cursor = self._conn.cursor()
        try:
            # 1. 插入订单主记录
            cursor.execute(
                """
                INSERT INTO orders (user_id, total_amount, address, status)
                VALUES (?, ?, ?, ?)
                """,
                (order.user_id, order.total_amount, order.address, order.status),
            )
            order.id = cursor.lastrowid

            # 2. 插入订单明细
            for item in order.items:
                item.order_id = order.id
                cursor.execute(
                    """
                    INSERT INTO order_items (order_id, product_id, quantity, unit_price)
                    VALUES (?, ?, ?, ?)
                    """,
                    (item.order_id, item.product_id, item.quantity, item.unit_price),
                )
                item.id = cursor.lastrowid

            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise
        return order

    def update_status(self, order_id: int, status: str) -> bool:
        """更新订单状态"""
        valid_statuses = {'pending', 'paid', 'shipped', 'delivered', 'cancelled'}
        if status not in valid_statuses:
            raise ValueError(f'无效的订单状态: {status}，合法值: {valid_statuses}')
        sql = """
            UPDATE orders
            SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """
        cursor = self._conn.cursor()
        cursor.execute(sql, (status, order_id))
        self._conn.commit()
        return cursor.rowcount > 0

    def delete(self, order_id: int) -> bool:
        """删除订单（明细会级联删除）"""
        cursor = self._conn.cursor()
        cursor.execute('DELETE FROM orders WHERE id = ?', (order_id,))
        self._conn.commit()
        return cursor.rowcount > 0

    # ------------------------------------------------------------------ #
    #  读操作                                                               #
    # ------------------------------------------------------------------ #

    def find_by_id(self, order_id: int) -> Optional[Order]:
        """按 id 查找订单（含明细）"""
        cursor = self._conn.cursor()
        cursor.execute('SELECT * FROM orders WHERE id = ?', (order_id,))
        row = cursor.fetchone()
        if not row:
            return None
        order = Order.from_row(tuple(row))
        order.items = self._load_items(order_id)
        return order

    def find_by_user(self, user_id: int) -> List[Order]:
        """查询某用户的所有订单（含明细）"""
        cursor = self._conn.cursor()
        cursor.execute(
            'SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC',
            (user_id,),
        )
        orders = [Order.from_row(tuple(row)) for row in cursor.fetchall()]
        for order in orders:
            order.items = self._load_items(order.id)
        return orders

    def find_by_status(self, status: str) -> List[Order]:
        """按状态查询所有订单"""
        cursor = self._conn.cursor()
        cursor.execute(
            'SELECT * FROM orders WHERE status = ? ORDER BY created_at DESC',
            (status,),
        )
        orders = [Order.from_row(tuple(row)) for row in cursor.fetchall()]
        for order in orders:
            order.items = self._load_items(order.id)
        return orders

    def find_all(self) -> List[Order]:
        """查询所有订单（含明细）"""
        cursor = self._conn.cursor()
        cursor.execute('SELECT * FROM orders ORDER BY created_at DESC')
        orders = [Order.from_row(tuple(row)) for row in cursor.fetchall()]
        for order in orders:
            order.items = self._load_items(order.id)
        return orders

    # ------------------------------------------------------------------ #
    #  私有辅助方法                                                          #
    # ------------------------------------------------------------------ #

    def _load_items(self, order_id: int) -> List[OrderItem]:
        """加载订单明细"""
        cursor = self._conn.cursor()
        cursor.execute(
            'SELECT * FROM order_items WHERE order_id = ? ORDER BY id',
            (order_id,),
        )
        return [OrderItem.from_row(tuple(row)) for row in cursor.fetchall()]
