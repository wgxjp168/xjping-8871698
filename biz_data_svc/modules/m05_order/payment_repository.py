from typing import List, Optional
from ...common.base_repository import BaseRepository
from ...common.db import Database
from .models import Payment


class PaymentRepository(BaseRepository[Payment]):
    """支付数据存储层"""

    def __init__(self, db: Database):
        super().__init__(db)

    @property
    def table(self) -> str:
        return 'payments'

    def _from_row(self, row) -> Payment:
        return Payment.from_row(row)

    def create(self, payment: Payment) -> Payment:
        cur = self._db.execute(
            '''INSERT INTO payments (order_id,payment_no,amount,method,status)
               VALUES (?,?,?,?,?)''',
            (payment.order_id, payment.payment_no, payment.amount,
             payment.method, payment.status),
        )
        self._db.commit()
        payment.id = cur.lastrowid
        return payment

    def mark_success(self, payment_id: int) -> bool:
        cur = self._db.execute(
            '''UPDATE payments SET status='success', paid_at=CURRENT_TIMESTAMP
               WHERE id=? AND status='pending' ''',
            (payment_id,),
        )
        self._db.commit()
        return cur.rowcount > 0

    def mark_failed(self, payment_id: int) -> bool:
        cur = self._db.execute(
            "UPDATE payments SET status='failed' WHERE id=? AND status='pending'",
            (payment_id,),
        )
        self._db.commit()
        return cur.rowcount > 0

    def refund(self, payment_id: int) -> bool:
        cur = self._db.execute(
            "UPDATE payments SET status='refunded' WHERE id=? AND status='success'",
            (payment_id,),
        )
        self._db.commit()
        return cur.rowcount > 0

    def find_by_order(self, order_id: int) -> List[Payment]:
        return self._fetchall(
            'SELECT * FROM payments WHERE order_id=? ORDER BY created_at DESC', (order_id,))

    def find_by_payment_no(self, payment_no: str) -> Optional[Payment]:
        return self._fetchone('SELECT * FROM payments WHERE payment_no=?', (payment_no,))
