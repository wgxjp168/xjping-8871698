"""
退款 Repository
继承 BaseRepository[Refund]，提供 refunds 表完整操作。
"""
from __future__ import annotations

from typing import List, Optional

from ...common.base_repository import BaseRepository
from ...common.db import Database
from .models import Refund


class RefundRepository(BaseRepository[Refund]):
    """refunds 表的数据访问层"""

    def __init__(self, db: Database):
        super().__init__(db)

    # ------------------------------------------------------------------ #
    #  BaseRepository 抽象方法实现                                          #
    # ------------------------------------------------------------------ #

    @property
    def table(self) -> str:
        return 'refunds'

    def _from_row(self, row) -> Refund:
        return Refund.from_row(row)

    # ------------------------------------------------------------------ #
    #  写操作                                                               #
    # ------------------------------------------------------------------ #

    def apply(self, refund: Refund) -> Refund:
        """
        创建退款申请，apply_at 由数据库写入当前时间。
        返回带有 id 的 Refund 对象。
        """
        sql = '''
            INSERT INTO refunds (
                order_id, payment_id, refund_no, amount,
                refund_type, reason, images, status, reject_reason,
                apply_at, approve_at, complete_at, operator_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), ?, ?, ?)
        '''
        params = (
            refund.order_id,
            refund.payment_id,
            refund.refund_no,
            refund.amount,
            refund.refund_type,
            refund.reason,
            refund.images,
            refund.status,
            refund.reject_reason,
            refund.approve_at,
            refund.complete_at,
            refund.operator_id,
        )
        cur = self._db.execute(sql, params)
        self._db.commit()
        refund.id = cur.lastrowid
        return refund

    def approve(self, refund_id: int, operator_id: int) -> bool:
        """
        审批通过退款申请：
        status → approved，approve_at = now，记录操作人。
        """
        sql = '''
            UPDATE refunds
            SET status      = 'approved',
                approve_at  = datetime('now'),
                operator_id = ?
            WHERE id = ?
        '''
        cur = self._db.execute(sql, (operator_id, refund_id))
        self._db.commit()
        return cur.rowcount > 0

    def reject(self, refund_id: int, operator_id: int, reason: str) -> bool:
        """
        拒绝退款申请：
        status → rejected，记录拒绝原因与操作人。
        """
        sql = '''
            UPDATE refunds
            SET status        = 'rejected',
                reject_reason = ?,
                operator_id   = ?
            WHERE id = ?
        '''
        cur = self._db.execute(sql, (reason, operator_id, refund_id))
        self._db.commit()
        return cur.rowcount > 0

    def process(self, refund_id: int) -> bool:
        """将退款申请置为处理中（status → processing）"""
        sql = "UPDATE refunds SET status = 'processing' WHERE id = ?"
        cur = self._db.execute(sql, (refund_id,))
        self._db.commit()
        return cur.rowcount > 0

    def complete(self, refund_id: int) -> bool:
        """
        完成退款：
        status → completed，complete_at = now。
        """
        sql = '''
            UPDATE refunds
            SET status      = 'completed',
                complete_at = datetime('now')
            WHERE id = ?
        '''
        cur = self._db.execute(sql, (refund_id,))
        self._db.commit()
        return cur.rowcount > 0

    def cancel(self, refund_id: int) -> bool:
        """取消退款申请（status → cancelled）"""
        sql = "UPDATE refunds SET status = 'cancelled' WHERE id = ?"
        cur = self._db.execute(sql, (refund_id,))
        self._db.commit()
        return cur.rowcount > 0

    # ------------------------------------------------------------------ #
    #  查询操作                                                             #
    # ------------------------------------------------------------------ #

    def find_by_id(self, id: int) -> Optional[Refund]:  # noqa: A002
        """按主键查询退款记录"""
        return self._fetchone('SELECT * FROM refunds WHERE id = ?', (id,))

    def find_by_order(self, order_id: int) -> List[Refund]:
        """查询指定订单的所有退款记录，按 id 升序"""
        return self._fetchall(
            'SELECT * FROM refunds WHERE order_id = ? ORDER BY id',
            (order_id,),
        )

    def get_refunded_amount(self, order_id: int) -> float:
        """
        汇总指定订单所有状态为 completed 的退款金额。
        返回 float，若无已完成退款则返回 0.0。
        """
        sql = '''
            SELECT COALESCE(SUM(amount), 0)
            FROM refunds
            WHERE order_id = ? AND status = 'completed'
        '''
        result = self._scalar(sql, (order_id,))
        return float(result) if result is not None else 0.0
