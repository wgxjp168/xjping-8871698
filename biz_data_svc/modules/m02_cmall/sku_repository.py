"""
C端商城模块 — SKU Repository
表：product_skus
"""
from __future__ import annotations

from typing import List, Optional

from ...common.base_repository import BaseRepository
from ...common.db import Database
from .models import ProductSku


class SkuRepository(BaseRepository[ProductSku]):
    """商品 SKU 数据访问层"""

    def __init__(self, db: Database):
        super().__init__(db)

    # ------------------------------------------------------------------ #
    #  BaseRepository 抽象实现                                              #
    # ------------------------------------------------------------------ #

    @property
    def table(self) -> str:
        return 'product_skus'

    def _from_row(self, row) -> ProductSku:
        return ProductSku.from_row(tuple(row))

    # ------------------------------------------------------------------ #
    #  写操作                                                               #
    # ------------------------------------------------------------------ #

    def add(self, sku: ProductSku) -> ProductSku:
        """新增单个 SKU，返回带自增 id 的对象。"""
        sql = """
            INSERT INTO product_skus
                (product_id, sku_code, barcode, attributes,
                 cost_price, market_price, sale_price, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        cur = self._db.execute(sql, (
            sku.product_id,
            sku.sku_code,
            sku.barcode,
            sku.attributes,
            sku.cost_price,
            sku.market_price,
            sku.sale_price,
            sku.status,
        ))
        self._db.commit()
        return self.find_by_id(cur.lastrowid)

    def add_batch(self, skus: List[ProductSku]) -> List[ProductSku]:
        """
        批量新增 SKU，在单个事务中执行。
        返回带自增 id 的对象列表。
        """
        if not skus:
            return []

        sql = """
            INSERT INTO product_skus
                (product_id, sku_code, barcode, attributes,
                 cost_price, market_price, sale_price, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        inserted_ids: List[int] = []
        with self._db.transaction():
            for sku in skus:
                cur = self._db.execute(sql, (
                    sku.product_id,
                    sku.sku_code,
                    sku.barcode,
                    sku.attributes,
                    sku.cost_price,
                    sku.market_price,
                    sku.sale_price,
                    sku.status,
                ))
                inserted_ids.append(cur.lastrowid)

        result: List[ProductSku] = []
        for new_id in inserted_ids:
            obj = self.find_by_id(new_id)
            if obj:
                result.append(obj)
        return result

    def update(self, sku: ProductSku) -> bool:
        """更新 SKU 完整信息。"""
        sql = """
            UPDATE product_skus
            SET product_id=?, sku_code=?, barcode=?, attributes=?,
                cost_price=?, market_price=?, sale_price=?, status=?,
                updated_at=CURRENT_TIMESTAMP
            WHERE id=?
        """
        cur = self._db.execute(sql, (
            sku.product_id,
            sku.sku_code,
            sku.barcode,
            sku.attributes,
            sku.cost_price,
            sku.market_price,
            sku.sale_price,
            sku.status,
            sku.id,
        ))
        self._db.commit()
        return cur.rowcount > 0

    def update_price(self, sku_id: int, sale_price: float,
                     market_price: Optional[float] = None) -> bool:
        """
        更新售价，可选同时更新市场价。
        仅更新非 None 的价格字段。
        """
        if market_price is not None:
            sql = """
                UPDATE product_skus
                SET sale_price=?, market_price=?, updated_at=CURRENT_TIMESTAMP
                WHERE id=?
            """
            cur = self._db.execute(sql, (sale_price, market_price, sku_id))
        else:
            sql = """
                UPDATE product_skus
                SET sale_price=?, updated_at=CURRENT_TIMESTAMP
                WHERE id=?
            """
            cur = self._db.execute(sql, (sale_price, sku_id))
        self._db.commit()
        return cur.rowcount > 0

    # ------------------------------------------------------------------ #
    #  查询操作                                                             #
    # ------------------------------------------------------------------ #

    def find_by_product(self, product_id: int) -> List[ProductSku]:
        """查询商品下所有 SKU，按 id 排序。"""
        return self._fetchall(
            'SELECT * FROM product_skus WHERE product_id=? ORDER BY id',
            (product_id,),
        )

    def find_by_sku_code(self, sku_code: str) -> Optional[ProductSku]:
        """按 SKU 编码查询（sku_code 全局唯一）。"""
        return self._fetchone(
            'SELECT * FROM product_skus WHERE sku_code=?', (sku_code,)
        )

    def find_by_id(self, id: int) -> Optional[ProductSku]:
        """按主键查询。"""
        return self._fetchone(
            'SELECT * FROM product_skus WHERE id=?', (id,)
        )
