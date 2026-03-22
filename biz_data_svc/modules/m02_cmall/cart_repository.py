"""
C端商城模块 — 购物车 Repository
表：cart_items
"""
from __future__ import annotations

from typing import List, Optional

from ...common.base_repository import BaseRepository
from ...common.db import Database
from .models import CartItem


class CartRepository(BaseRepository[CartItem]):
    """购物车数据访问层"""

    def __init__(self, db: Database):
        super().__init__(db)

    # ------------------------------------------------------------------ #
    #  BaseRepository 抽象实现                                              #
    # ------------------------------------------------------------------ #

    @property
    def table(self) -> str:
        return 'cart_items'

    def _from_row(self, row) -> CartItem:
        return CartItem.from_row(tuple(row))

    # ------------------------------------------------------------------ #
    #  写操作                                                               #
    # ------------------------------------------------------------------ #

    def add_or_update(self, item: CartItem) -> CartItem:
        """
        加入购物车。
        若 (user_id, sku_id) 已存在则累加数量；否则新增记录。
        返回最终的 CartItem 对象。
        """
        existing = self._fetchone(
            'SELECT * FROM cart_items WHERE user_id=? AND sku_id=?',
            (item.user_id, item.sku_id),
        )
        if existing is not None:
            new_qty = existing.quantity + item.quantity
            sql = """
                UPDATE cart_items
                SET quantity=?, is_selected=?,
                    updated_at=CURRENT_TIMESTAMP
                WHERE user_id=? AND sku_id=?
            """
            self._db.execute(sql, (
                new_qty,
                int(item.is_selected),
                item.user_id,
                item.sku_id,
            ))
            self._db.commit()
            return self._fetchone(
                'SELECT * FROM cart_items WHERE user_id=? AND sku_id=?',
                (item.user_id, item.sku_id),
            )
        else:
            sql = """
                INSERT INTO cart_items
                    (user_id, tenant_id, product_id, sku_id,
                     quantity, is_selected)
                VALUES (?, ?, ?, ?, ?, ?)
            """
            cur = self._db.execute(sql, (
                item.user_id,
                item.tenant_id,
                item.product_id,
                item.sku_id,
                item.quantity,
                int(item.is_selected),
            ))
            self._db.commit()
            return self._fetchone(
                'SELECT * FROM cart_items WHERE id=?', (cur.lastrowid,)
            )

    def update_quantity(self, user_id: int, sku_id: int, quantity: int) -> bool:
        """
        设置购物车商品数量。
        quantity=0 时自动删除该条目。
        """
        if quantity == 0:
            return self.remove_item(user_id, sku_id)
        if quantity < 0:
            return False

        sql = """
            UPDATE cart_items
            SET quantity=?, updated_at=CURRENT_TIMESTAMP
            WHERE user_id=? AND sku_id=?
        """
        cur = self._db.execute(sql, (quantity, user_id, sku_id))
        self._db.commit()
        return cur.rowcount > 0

    def remove_item(self, user_id: int, sku_id: int) -> bool:
        """从购物车删除指定 SKU 的条目。"""
        cur = self._db.execute(
            'DELETE FROM cart_items WHERE user_id=? AND sku_id=?',
            (user_id, sku_id),
        )
        self._db.commit()
        return cur.rowcount > 0

    def select_item(self, user_id: int, sku_id: int, selected: bool) -> bool:
        """设置单个条目的选中状态。"""
        cur = self._db.execute(
            """
            UPDATE cart_items
            SET is_selected=?, updated_at=CURRENT_TIMESTAMP
            WHERE user_id=? AND sku_id=?
            """,
            (int(selected), user_id, sku_id),
        )
        self._db.commit()
        return cur.rowcount > 0

    def select_all(self, user_id: int, tenant_id: int, selected: bool) -> int:
        """
        全选或取消全选购物车。
        返回受影响行数。
        """
        cur = self._db.execute(
            """
            UPDATE cart_items
            SET is_selected=?, updated_at=CURRENT_TIMESTAMP
            WHERE user_id=? AND tenant_id=?
            """,
            (int(selected), user_id, tenant_id),
        )
        self._db.commit()
        return cur.rowcount

    def clear(self, user_id: int, tenant_id: int) -> int:
        """
        清空整个购物车。
        返回被删除的条目数。
        """
        cur = self._db.execute(
            'DELETE FROM cart_items WHERE user_id=? AND tenant_id=?',
            (user_id, tenant_id),
        )
        self._db.commit()
        return cur.rowcount

    def clear_selected(self, user_id: int, tenant_id: int) -> int:
        """
        仅清空已选中的购物车条目（下单后调用）。
        返回被删除的条目数。
        """
        cur = self._db.execute(
            'DELETE FROM cart_items WHERE user_id=? AND tenant_id=? AND is_selected=1',
            (user_id, tenant_id),
        )
        self._db.commit()
        return cur.rowcount

    # ------------------------------------------------------------------ #
    #  查询操作                                                             #
    # ------------------------------------------------------------------ #

    def find_by_user(self, user_id: int, tenant_id: int) -> List[CartItem]:
        """查询用户购物车所有条目，按创建时间倒序。"""
        return self._fetchall(
            'SELECT * FROM cart_items WHERE user_id=? AND tenant_id=? '
            'ORDER BY created_at DESC',
            (user_id, tenant_id),
        )

    def find_selected(self, user_id: int, tenant_id: int) -> List[CartItem]:
        """查询用户购物车中已选中的条目。"""
        return self._fetchall(
            'SELECT * FROM cart_items WHERE user_id=? AND tenant_id=? '
            'AND is_selected=1 ORDER BY created_at DESC',
            (user_id, tenant_id),
        )

    def count(self, user_id: int, tenant_id: int) -> int:
        """返回购物车条目总数（SKU 种类数，不是商品总数量）。"""
        val = self._scalar(
            'SELECT COUNT(*) FROM cart_items WHERE user_id=? AND tenant_id=?',
            (user_id, tenant_id),
        )
        return val or 0
