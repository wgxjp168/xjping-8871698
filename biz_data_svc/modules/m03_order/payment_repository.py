"""
支付 Repository
继承 BaseRepository[Payment]，提供 payments 表完整操作。
"""
from __future__ import annotations

from typing import List, Optional

from ...common.base_repository import BaseRepository
from ...common.db import Database
from .models import Payment


class PaymentRepository(BaseRepository[Payment]):
    """payments 表的数据访问层"""

    def __init__(self, db: Database):
        super().__init__(db)

    # ------------------------------------------------------------------ #
    #  BaseRepository 抽象方法实现                                          #
    # ------------------------------------------------------------------ #

    @property
    def table(self) -> str:
        return 'payments'

    def _from_row(self, row) -> Payment:
        return Payment.from_row(row)

    # ------------------------------------------------------------------ #
    #  写操作                                                               #
    # ------------------------------------------------------------------ #

    def create(self, payment: Payment) -> Payment:
        """插入新支付记录，返回带有 id 的 Payment 对象"""
        sql = '''
            INSERT INTO payments (
                order_id, payment_no, amount, method,
                channel_no, status, paid_at, expired_at, extra
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        '''
        params = (
            payment.order_id,
            payment.payment_no,
            payment.amount,
            payment.method,
            payment.channel_no,
            payment.status,
            payment.paid_at,
            payment.expired_at,
            payment.extra,
        )
        cur = self._db.execute(sql, params)
        self._db.commit()
        payment.id = cur.lastrowid
        return payment

    def mark_success(self, payment_id: int, channel_no: str = '') -> bool:
        """将支付记录标记为成功，记录第三方流水号与支付时间"""
        sql = '''
            UPDATE payments
            SET status = 'success',
                paid_at = datetime('now'),
                channel_no = ?
            WHERE id = ?
        '''
        cur = self._db.execute(sql, (channel_no, payment_id))
        self._db.commit()
        return cur.rowcount > 0

    def mark_failed(self, payment_id: int) -> bool:
        """将支付记录标记为失败"""
        sql = "UPDATE payments SET status = 'failed' WHERE id = ?"
        cur = self._db.execute(sql, (payment_id,))
        self._db.commit()
        return cur.rowcount > 0

    def cancel_payment(self, payment_id: int) -> bool:
        """取消支付记录"""
        sql = "UPDATE payments SET status = 'cancelled' WHERE id = ?"
        cur = self._db.execute(sql, (payment_id,))
        self._db.commit()
        return cur.rowcount > 0

    # ------------------------------------------------------------------ #
    #  查询操作                                                             #
    # ------------------------------------------------------------------ #

    def find_by_id(self, id: int) -> Optional[Payment]:  # noqa: A002
        """按主键查询支付记录"""
        return self._fetchone('SELECT * FROM payments WHERE id = ?', (id,))

    def find_by_order(self, order_id: int) -> List[Payment]:
        """查询指定订单的所有支付记录，按 id 升序"""
        return self._fetchall(
            'SELECT * FROM payments WHERE order_id = ? ORDER BY id',
            (order_id,),
        )

    def find_by_payment_no(self, payment_no: str) -> Optional[Payment]:
        """按业务支付单号查询"""
        return self._fetchone(
            'SELECT * FROM payments WHERE payment_no = ?', (payment_no,)
        )

    def get_paid_amount(self, order_id: int) -> float:
        """
        汇总指定订单所有状态为 success 的支付金额。
        返回 float，若无成功支付则返回 0.0。
        """
        sql = '''
            SELECT COALESCE(SUM(amount), 0)
            FROM payments
            WHERE order_id = ? AND status = 'success'
        '''
        result = self._scalar(sql, (order_id,))
        return float(result) if result is not None else 0.0
