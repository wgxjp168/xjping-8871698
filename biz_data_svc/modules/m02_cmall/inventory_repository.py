"""
C端商城模块 — 库存 Repository
表：product_inventory
"""
from __future__ import annotations

from typing import List, Optional

from ...common.base_repository import BaseRepository
from ...common.db import Database
from .models import ProductInventory


class InventoryRepository(BaseRepository[ProductInventory]):
    """商品库存数据访问层"""

    def __init__(self, db: Database):
        super().__init__(db)

    # ------------------------------------------------------------------ #
    #  BaseRepository 抽象实现                                              #
    # ------------------------------------------------------------------ #

    @property
    def table(self) -> str:
        return 'product_inventory'

    def _from_row(self, row) -> ProductInventory:
        return ProductInventory.from_row(tuple(row))

    # ------------------------------------------------------------------ #
    #  初始化库存                                                            #
    # ------------------------------------------------------------------ #

    def init(self, inventory: ProductInventory) -> ProductInventory:
        """
        初始化库存记录（INSERT OR IGNORE）。
        若 (sku_id, warehouse_id) 已存在则忽略，返回当前库存记录。
        """
        sql = """
            INSERT OR IGNORE INTO product_inventory
                (sku_id, warehouse_id, quantity, reserved, safety_stock)
            VALUES (?, ?, ?, ?, ?)
        """
        self._db.execute(sql, (
            inventory.sku_id,
            inventory.warehouse_id,
            inventory.quantity,
            inventory.reserved,
            inventory.safety_stock,
        ))
        self._db.commit()
        return self.find_by_sku_warehouse(inventory.sku_id, inventory.warehouse_id)

    # ------------------------------------------------------------------ #
    #  库存调整操作                                                          #
    # ------------------------------------------------------------------ #

    def adjust(self, sku_id: int, warehouse_id: int, delta: int,
               check_negative: bool = True) -> bool:
        """
        调整库存数量。
        delta > 0：入库（增加）；delta < 0：出库（减少）。
        check_negative=True 时：若调整后 quantity < 0 则返回 False，不执行更新。
        """
        if delta == 0:
            return True

        if check_negative and delta < 0:
            # 检查库存是否充足
            inv = self.find_by_sku_warehouse(sku_id, warehouse_id)
            if inv is None:
                return False
            if inv.quantity + delta < 0:
                return False

        sql = """
            UPDATE product_inventory
            SET quantity = quantity + ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE sku_id=? AND warehouse_id=?
        """
        cur = self._db.execute(sql, (delta, sku_id, warehouse_id))
        self._db.commit()
        return cur.rowcount > 0

    def reserve(self, sku_id: int, warehouse_id: int, qty: int) -> bool:
        """
        预占库存：reserved += qty。
        前提：quantity - reserved >= qty（可用库存充足）。
        库存不足时返回 False。
        """
        if qty <= 0:
            return False

        # 原子 CAS 更新：只有满足条件时才执行
        sql = """
            UPDATE product_inventory
            SET reserved = reserved + ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE sku_id=? AND warehouse_id=?
              AND (quantity - reserved) >= ?
        """
        cur = self._db.execute(sql, (qty, sku_id, warehouse_id, qty))
        self._db.commit()
        return cur.rowcount > 0

    def release_reserve(self, sku_id: int, warehouse_id: int, qty: int) -> bool:
        """
        释放预占库存：reserved -= qty。
        保证 reserved 不低于 0。
        """
        if qty <= 0:
            return False

        sql = """
            UPDATE product_inventory
            SET reserved = MAX(0, reserved - ?),
                updated_at = CURRENT_TIMESTAMP
            WHERE sku_id=? AND warehouse_id=?
        """
        cur = self._db.execute(sql, (qty, sku_id, warehouse_id))
        self._db.commit()
        return cur.rowcount > 0

    def deduct_reserved(self, sku_id: int, warehouse_id: int, qty: int) -> bool:
        """
        确认扣减预占库存（订单完成）：
        quantity -= qty，reserved -= qty。
        同时保证 quantity >= 0 且 reserved >= 0。
        """
        if qty <= 0:
            return False

        sql = """
            UPDATE product_inventory
            SET quantity = quantity - ?,
                reserved = MAX(0, reserved - ?),
                updated_at = CURRENT_TIMESTAMP
            WHERE sku_id=? AND warehouse_id=?
              AND quantity >= ?
        """
        cur = self._db.execute(sql, (qty, qty, sku_id, warehouse_id, qty))
        self._db.commit()
        return cur.rowcount > 0

    def set_safety_stock(self, sku_id: int, warehouse_id: int, safety: int) -> bool:
        """设置安全库存阈值。"""
        sql = """
            UPDATE product_inventory
            SET safety_stock=?, updated_at=CURRENT_TIMESTAMP
            WHERE sku_id=? AND warehouse_id=?
        """
        cur = self._db.execute(sql, (safety, sku_id, warehouse_id))
        self._db.commit()
        return cur.rowcount > 0

    # ------------------------------------------------------------------ #
    #  查询操作                                                             #
    # ------------------------------------------------------------------ #

    def find_by_sku(self, sku_id: int) -> List[ProductInventory]:
        """查询某 SKU 在所有仓库的库存记录。"""
        return self._fetchall(
            'SELECT * FROM product_inventory WHERE sku_id=? ORDER BY warehouse_id',
            (sku_id,),
        )

    def find_by_sku_warehouse(self, sku_id: int,
                              warehouse_id: int) -> Optional[ProductInventory]:
        """查询某 SKU 在指定仓库的库存记录。"""
        return self._fetchone(
            'SELECT * FROM product_inventory WHERE sku_id=? AND warehouse_id=?',
            (sku_id, warehouse_id),
        )

    def find_low_stock(self, warehouse_id: int) -> List[ProductInventory]:
        """
        查询指定仓库低于安全库存的 SKU 列表。
        条件：quantity - reserved <= safety_stock
        """
        return self._fetchall(
            """
            SELECT * FROM product_inventory
            WHERE warehouse_id=?
              AND (quantity - reserved) <= safety_stock
            ORDER BY (quantity - reserved) ASC
            """,
            (warehouse_id,),
        )

    def get_available(self, sku_id: int, warehouse_id: int) -> int:
        """
        返回可用库存数量（quantity - reserved）。
        若记录不存在则返回 0。
        """
        val = self._scalar(
            """
            SELECT quantity - reserved
            FROM product_inventory
            WHERE sku_id=? AND warehouse_id=?
            """,
            (sku_id, warehouse_id),
        )
        return max(0, val) if val is not None else 0
