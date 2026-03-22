"""
供应商目录报价 Repository
继承 BaseRepository[SupplierQuote]，管理供应商产品报价。
"""
from __future__ import annotations

from typing import List, Optional

from ...common.base_repository import BaseRepository
from ...common.db import Database
from .models import SupplierQuote


class QuoteRepository(BaseRepository[SupplierQuote]):
    """supplier_quotes 表的数据访问层"""

    def __init__(self, db: Database):
        super().__init__(db)

    # ------------------------------------------------------------------ #
    #  BaseRepository 抽象方法实现                                          #
    # ------------------------------------------------------------------ #

    @property
    def table(self) -> str:
        return 'supplier_quotes'

    def _from_row(self, row) -> SupplierQuote:
        return SupplierQuote.from_row(row)

    # ------------------------------------------------------------------ #
    #  写操作                                                               #
    # ------------------------------------------------------------------ #

    def add(self, quote: SupplierQuote) -> SupplierQuote:
        """新增供应商报价"""
        cur = self._db.execute(
            '''
            INSERT INTO supplier_quotes
                (supplier_id, tenant_id, product_name, spec, unit,
                 unit_price, currency, min_qty, delivery_days,
                 valid_until, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                quote.supplier_id, quote.tenant_id, quote.product_name,
                quote.spec, quote.unit, quote.unit_price, quote.currency,
                quote.min_qty, quote.delivery_days,
                quote.valid_until, quote.status,
            ),
        )
        self._db.commit()
        quote.id = cur.lastrowid
        return quote

    def withdraw(self, quote_id: int) -> bool:
        """撤回报价：status → withdrawn"""
        cur = self._db.execute(
            "UPDATE supplier_quotes SET status = 'withdrawn' WHERE id = ?",
            (quote_id,),
        )
        self._db.commit()
        return cur.rowcount > 0

    def expire_outdated(self) -> int:
        """
        将所有 valid_until < today 且 status='active' 的报价改为 'expired'。
        返回受影响的行数。
        """
        cur = self._db.execute(
            '''
            UPDATE supplier_quotes
            SET status = 'expired'
            WHERE status = 'active'
              AND valid_until IS NOT NULL
              AND valid_until < date('now')
            ''',
        )
        self._db.commit()
        return cur.rowcount

    # ------------------------------------------------------------------ #
    #  查询操作                                                             #
    # ------------------------------------------------------------------ #

    def find_by_supplier(self, supplier_id: int) -> List[SupplierQuote]:
        """查询某供应商的所有报价"""
        return self._fetchall(
            'SELECT * FROM supplier_quotes WHERE supplier_id = ? ORDER BY id DESC',
            (supplier_id,),
        )

    def find_active_by_product(
        self, tenant_id: int, product_name: str
    ) -> List[SupplierQuote]:
        """
        查询指定租户下某产品的有效报价，
        过滤条件：status='active' 且 valid_until >= today（或无到期日）
        按单价升序排列。
        """
        return self._fetchall(
            '''
            SELECT * FROM supplier_quotes
            WHERE tenant_id = ?
              AND product_name = ?
              AND status = 'active'
              AND (valid_until IS NULL OR valid_until >= date('now'))
            ORDER BY unit_price ASC
            ''',
            (tenant_id, product_name),
        )
