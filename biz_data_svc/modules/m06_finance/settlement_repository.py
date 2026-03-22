"""
结算单 Repository
继承 BaseRepository[Settlement]，提供 settlements 表完整操作。
"""
from __future__ import annotations

from typing import List, Optional

from ...common.base_repository import BaseRepository
from ...common.db import Database
from .models import Settlement


class SettlementRepository(BaseRepository[Settlement]):
    """settlements 表的数据访问层"""

    def __init__(self, db: Database):
        super().__init__(db)

    # ------------------------------------------------------------------ #
    #  BaseRepository 抽象方法实现                                          #
    # ------------------------------------------------------------------ #

    @property
    def table(self) -> str:
        return 'settlements'

    def _from_row(self, row) -> Settlement:
        return Settlement.from_row(row)

    # ------------------------------------------------------------------ #
    #  写操作                                                               #
    # ------------------------------------------------------------------ #

    def apply(self, settlement: Settlement) -> Settlement:
        """发起结算申请，插入结算单记录"""
        sql = '''
            INSERT INTO settlements
                (tenant_id, settle_no, supplier_id, reconciliation_id,
                 invoice_ids, amount, currency, payment_method, bank_account,
                 status, apply_at, approved_at, paid_at, approver_id,
                 operator_id, note)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        '''
        with self._db.transaction():
            cur = self._db.execute(sql, (
                settlement.tenant_id,
                settlement.settle_no,
                settlement.supplier_id,
                settlement.reconciliation_id,
                settlement.invoice_ids,
                settlement.amount,
                settlement.currency,
                settlement.payment_method,
                settlement.bank_account,
                settlement.status,
                settlement.apply_at,
                settlement.approved_at,
                settlement.paid_at,
                settlement.approver_id,
                settlement.operator_id,
                settlement.note,
            ))
            settlement.id = cur.lastrowid
        return settlement

    def approve(self, settle_id: int, approver_id: int) -> bool:
        """审批通过：status=approved, approved_at=now, approver_id"""
        cur = self._db.execute(
            '''UPDATE settlements
               SET status      = 'approved',
                   approved_at = CURRENT_TIMESTAMP,
                   approver_id = ?
               WHERE id = ?''',
            (approver_id, settle_id),
        )
        self._db.commit()
        return cur.rowcount > 0

    def reject(self, settle_id: int, approver_id: int) -> bool:
        """审批拒绝：status=rejected, approver_id"""
        cur = self._db.execute(
            '''UPDATE settlements
               SET status      = 'rejected',
                   approver_id = ?
               WHERE id = ?''',
            (approver_id, settle_id),
        )
        self._db.commit()
        return cur.rowcount > 0

    def pay(self, settle_id: int, operator_id: int) -> bool:
        """标记付款完成：status=paid, paid_at=now, operator_id"""
        cur = self._db.execute(
            '''UPDATE settlements
               SET status      = 'paid',
                   paid_at     = CURRENT_TIMESTAMP,
                   operator_id = ?
               WHERE id = ?''',
            (operator_id, settle_id),
        )
        self._db.commit()
        return cur.rowcount > 0

    def cancel(self, settle_id: int) -> bool:
        """取消结算单：status=cancelled"""
        cur = self._db.execute(
            "UPDATE settlements SET status = 'cancelled' WHERE id = ?",
            (settle_id,),
        )
        self._db.commit()
        return cur.rowcount > 0

    # ------------------------------------------------------------------ #
    #  查询操作                                                             #
    # ------------------------------------------------------------------ #

    def find_by_id(self, id: int) -> Optional[Settlement]:  # noqa: A002
        return self._fetchone(
            'SELECT * FROM settlements WHERE id = ?', (id,)
        )

    def find_by_tenant(
        self,
        tenant_id: int,
        status: Optional[str] = None,
    ) -> List[Settlement]:
        """按租户查询结算单，可选 status 过滤"""
        if status is None:
            return self._fetchall(
                'SELECT * FROM settlements WHERE tenant_id = ? ORDER BY id',
                (tenant_id,),
            )
        return self._fetchall(
            'SELECT * FROM settlements WHERE tenant_id = ? AND status = ? ORDER BY id',
            (tenant_id, status),
        )

    def find_by_supplier(
        self,
        supplier_id: int,
        status: Optional[str] = None,
    ) -> List[Settlement]:
        """按供应商查询结算单，可选 status 过滤"""
        if status is None:
            return self._fetchall(
                'SELECT * FROM settlements WHERE supplier_id = ? ORDER BY id',
                (supplier_id,),
            )
        return self._fetchall(
            'SELECT * FROM settlements WHERE supplier_id = ? AND status = ? ORDER BY id',
            (supplier_id, status),
        )

    def get_total_paid(self, supplier_id: int, tenant_id: int) -> float:
        """查询指定供应商在指定租户下的已付款总额"""
        result = self._scalar(
            '''SELECT COALESCE(SUM(amount), 0)
               FROM settlements
               WHERE supplier_id = ? AND tenant_id = ? AND status = 'paid' ''',
            (supplier_id, tenant_id),
        )
        return float(result or 0.0)
