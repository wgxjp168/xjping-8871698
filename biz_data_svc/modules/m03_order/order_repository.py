"""
订单 Repository
继承 BaseRepository[Order]，提供 orders + order_items 完整操作。
"""
from __future__ import annotations

from typing import List, Optional, Tuple

from ...common.base_repository import BaseRepository
from ...common.db import Database
from .models import Order, OrderItem


class OrderRepository(BaseRepository[Order]):
    """orders 表的数据访问层（附带 order_items 级联操作）"""

    def __init__(self, db: Database):
        super().__init__(db)

    # ------------------------------------------------------------------ #
    #  BaseRepository 抽象方法实现                                          #
    # ------------------------------------------------------------------ #

    @property
    def table(self) -> str:
        return 'orders'

    def _from_row(self, row) -> Order:
        return Order.from_row(row)

    # ------------------------------------------------------------------ #
    #  内部辅助                                                             #
    # ------------------------------------------------------------------ #

    def _load_items(self, order_id: int) -> List[OrderItem]:
        """加载指定订单的所有明细行"""
        sql = '''
            SELECT id, order_id, product_id, sku_id, product_name,
                   sku_attrs, quantity, unit_price, subtotal,
                   refund_qty, refund_amount
            FROM order_items
            WHERE order_id = ?
            ORDER BY id
        '''
        rows = self._db.execute(sql, (order_id,)).fetchall()
        return [OrderItem.from_row(r) for r in rows]

    def _attach_items(self, order: Optional[Order]) -> Optional[Order]:
        """为 Order 对象填充 items 列表；若 order 为 None 则直接返回"""
        if order is not None:
            order.items = self._load_items(order.id)
        return order

    # ------------------------------------------------------------------ #
    #  写操作                                                               #
    # ------------------------------------------------------------------ #

    def create(self, order: Order) -> Order:
        """
        在事务内同时插入 orders 主表与所有 order_items 明细行。
        返回带有 id 的 Order 对象（items 已填充 id）。
        """
        order_sql = '''
            INSERT INTO orders (
                tenant_id, order_no, user_id,
                receiver_name, receiver_phone,
                province, city, district, address_detail,
                status, total_amount, discount_amount, shipping_fee, pay_amount,
                payment_method, paid_at, remark, cancel_reason, source
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        '''
        order_params = (
            order.tenant_id,
            order.order_no,
            order.user_id,
            order.receiver_name,
            order.receiver_phone,
            order.province,
            order.city,
            order.district,
            order.address_detail,
            order.status,
            order.total_amount,
            order.discount_amount,
            order.shipping_fee,
            order.pay_amount,
            order.payment_method,
            order.paid_at,
            order.remark,
            order.cancel_reason,
            order.source,
        )

        item_sql = '''
            INSERT INTO order_items (
                order_id, product_id, sku_id, product_name,
                sku_attrs, quantity, unit_price, subtotal,
                refund_qty, refund_amount
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        '''

        with self._db.transaction():
            cur = self._db.execute(order_sql, order_params)
            order.id = cur.lastrowid

            for item in order.items:
                item.order_id = order.id
                item_params = (
                    item.order_id,
                    item.product_id,
                    item.sku_id,
                    item.product_name,
                    item.sku_attrs,
                    item.quantity,
                    item.unit_price,
                    item.subtotal,
                    item.refund_qty,
                    item.refund_amount,
                )
                ic = self._db.execute(item_sql, item_params)
                item.id = ic.lastrowid

        return order

    def update_status(self, order_id: int, status: str) -> bool:
        """更新订单状态"""
        sql = "UPDATE orders SET status = ?, updated_at = datetime('now') WHERE id = ?"
        cur = self._db.execute(sql, (status, order_id))
        self._db.commit()
        return cur.rowcount > 0

    def cancel(self, order_id: int, reason: str) -> bool:
        """将订单标记为已取消，并记录取消原因"""
        sql = '''
            UPDATE orders
            SET status = 'cancelled',
                cancel_reason = ?,
                updated_at = datetime('now')
            WHERE id = ?
        '''
        cur = self._db.execute(sql, (reason, order_id))
        self._db.commit()
        return cur.rowcount > 0

    def pay(self, order_id: int, method: str) -> bool:
        """将订单标记为已支付，记录支付方式与支付时间"""
        sql = '''
            UPDATE orders
            SET status = 'paid',
                payment_method = ?,
                paid_at = datetime('now'),
                updated_at = datetime('now')
            WHERE id = ?
        '''
        cur = self._db.execute(sql, (method, order_id))
        self._db.commit()
        return cur.rowcount > 0

    def complete(self, order_id: int) -> bool:
        """将订单标记为已完成"""
        sql = '''
            UPDATE orders
            SET status = 'completed',
                updated_at = datetime('now')
            WHERE id = ?
        '''
        cur = self._db.execute(sql, (order_id,))
        self._db.commit()
        return cur.rowcount > 0

    def delete(self, order_id: int) -> bool:  # noqa: A002
        """删除订单（物理删除）"""
        cur = self._db.execute('DELETE FROM orders WHERE id = ?', (order_id,))
        self._db.commit()
        return cur.rowcount > 0

    # ------------------------------------------------------------------ #
    #  查询操作                                                             #
    # ------------------------------------------------------------------ #

    def find_by_id(self, order_id: int) -> Optional[Order]:  # noqa: A002
        """按主键查询订单，附带明细行"""
        order = self._fetchone('SELECT * FROM orders WHERE id = ?', (order_id,))
        return self._attach_items(order)

    def find_by_order_no(self, order_no: str) -> Optional[Order]:
        """按业务单号查询订单，附带明细行"""
        order = self._fetchone('SELECT * FROM orders WHERE order_no = ?', (order_no,))
        return self._attach_items(order)

    def find_by_user(
        self,
        user_id: int,
        status: Optional[str] = None,
        page: int = 1,
        size: int = 20,
    ) -> Tuple[List[Order], int]:
        """
        按用户 ID 分页查询订单（可按状态过滤）。
        返回 (orders, total)，每条 Order 不附带 items（列表场景无需 N+1）。
        """
        if status is not None:
            where = 'user_id = ? AND status = ?'
            params: tuple = (user_id, status)
        else:
            where = 'user_id = ?'
            params = (user_id,)
        return self.paginate(page=page, size=size, where=where, params=params)

    def find_by_tenant(
        self,
        tenant_id: int,
        status: Optional[str] = None,
        page: int = 1,
        size: int = 20,
    ) -> Tuple[List[Order], int]:
        """
        按租户 ID 分页查询订单（可按状态过滤）。
        返回 (orders, total)，每条 Order 不附带 items（列表场景无需 N+1）。
        """
        if status is not None:
            where = 'tenant_id = ? AND status = ?'
            params: tuple = (tenant_id, status)
        else:
            where = 'tenant_id = ?'
            params = (tenant_id,)
        return self.paginate(page=page, size=size, where=where, params=params)
