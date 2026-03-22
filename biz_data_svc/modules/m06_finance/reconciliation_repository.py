"""
对账单 Repository
继承 BaseRepository[Reconciliation]，提供 reconciliations 表完整操作。
"""
from __future__ import annotations

from typing import List, Optional

from ...common.base_repository import BaseRepository
from ...common.db import Database
from .models import Reconciliation


class ReconciliationRepository(BaseRepository[Reconciliation]):
    """reconciliations 表的数据访问层"""

    def __init__(self, db: Database):
        super().__init__(db)

    # ------------------------------------------------------------------ #
    #  BaseRepository 抽象方法实现                                          #
    # ------------------------------------------------------------------ #

    @property
    def table(self) -> str:
        return 'reconciliations'

    def _from_row(self, row) -> Reconciliation:
        return Reconciliation.from_row(row)

    # ------------------------------------------------------------------ #
    #  写操作                                                               #
    # ------------------------------------------------------------------ #

    def create(self, recon: Reconciliation) -> Reconciliation:
        """
        创建对账单，自动计算 diff_amount = order_amount - invoice_amount。
        """
        recon.diff_amount = round(recon.order_amount - recon.invoice_amount, 2)

        sql = '''
            INSERT INTO reconciliations
                (tenant_id, recon_no, supplier_id, period_start, period_end,
                 order_amount, invoice_amount, diff_amount, status,
                 supplier_confirmed, confirmed_at, note, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        '''
        with self._db.transaction():
            cur = self._db.execute(sql, (
                recon.tenant_id,
                recon.recon_no,
                recon.supplier_id,
                recon.period_start,
                recon.period_end,
                recon.order_amount,
                recon.invoice_amount,
                recon.diff_amount,
                recon.status,
                recon.supplier_confirmed,
                recon.confirmed_at,
                recon.note,
                recon.created_by,
            ))
            recon.id = cur.lastrowid
        return recon

    def send(self, recon_id: int) -> bool:
        """状态推进：draft → sent"""
        cur = self._db.execute(
            "UPDATE reconciliations SET status = 'sent' WHERE id = ? AND status = 'draft'",
            (recon_id,),
        )
        self._db.commit()
        return cur.rowcount > 0

    def dispute(self, recon_id: int, note: str = '') -> bool:
        """状态推进：→ disputed，可附加备注"""
        sql = "UPDATE reconciliations SET status = 'disputed'"
        params: list = []
        if note:
            sql += ', note = ?'
            params.append(note)
        sql += ' WHERE id = ?'
        params.append(recon_id)
        cur = self._db.execute(sql, tuple(params))
        self._db.commit()
        return cur.rowcount > 0

    def confirm(self, recon_id: int) -> bool:
        """状态推进：→ confirmed，confirmed_at=now"""
        cur = self._db.execute(
            '''UPDATE reconciliations
               SET status = 'confirmed',
                   confirmed_at = CURRENT_TIMESTAMP
               WHERE id = ?''',
            (recon_id,),
        )
        self._db.commit()
        return cur.rowcount > 0

    def supplier_confirm(self, recon_id: int) -> bool:
        """供应商确认：supplier_confirmed=1, confirmed_at=now"""
        cur = self._db.execute(
            '''UPDATE reconciliations
               SET supplier_confirmed = 1,
                   confirmed_at = CURRENT_TIMESTAMP
               WHERE id = ?''',
            (recon_id,),
        )
        self._db.commit()
        return cur.rowcount > 0

    def close(self, recon_id: int) -> bool:
        """状态推进：→ closed"""
        cur = self._db.execute(
            "UPDATE reconciliations SET status = 'closed' WHERE id = ?",
            (recon_id,),
        )
        self._db.commit()
        return cur.rowcount > 0

    def update_amounts(
        self,
        recon_id: int,
        order_amount: float,
        invoice_amount: float,
    ) -> bool:
        """更新金额并自动重算 diff_amount"""
        diff_amount = round(order_amount - invoice_amount, 2)
        cur = self._db.execute(
            '''UPDATE reconciliations
               SET order_amount   = ?,
                   invoice_amount = ?,
                   diff_amount    = ?
               WHERE id = ?''',
            (order_amount, invoice_amount, diff_amount, recon_id),
        )
        self._db.commit()
        return cur.rowcount > 0

    # ------------------------------------------------------------------ #
    #  查询操作                                                             #
    # ------------------------------------------------------------------ #

    def find_by_id(self, id: int) -> Optional[Reconciliation]:  # noqa: A002
        return self._fetchone(
            'SELECT * FROM reconciliations WHERE id = ?', (id,)
        )

    def find_by_supplier(
        self,
        supplier_id: int,
        status: Optional[str] = None,
    ) -> List[Reconciliation]:
        """按供应商查询对账单，可选 status 过滤"""
        if status is None:
            return self._fetchall(
                'SELECT * FROM reconciliations WHERE supplier_id = ? ORDER BY id',
                (supplier_id,),
            )
        return self._fetchall(
            'SELECT * FROM reconciliations WHERE supplier_id = ? AND status = ? ORDER BY id',
            (supplier_id, status),
        )

    def find_by_tenant(
        self,
        tenant_id: int,
        status: Optional[str] = None,
    ) -> List[Reconciliation]:
        """按租户查询对账单，可选 status 过滤"""
        if status is None:
            return self._fetchall(
                'SELECT * FROM reconciliations WHERE tenant_id = ? ORDER BY id',
                (tenant_id,),
            )
        return self._fetchall(
            'SELECT * FROM reconciliations WHERE tenant_id = ? AND status = ? ORDER BY id',
            (tenant_id, status),
        )
