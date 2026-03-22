from typing import List, Optional
from ...common.base_repository import BaseRepository
from ...common.db import Database
from .models import Coupon, CouponRecord


class CouponRepository(BaseRepository[Coupon]):
    """优惠券数据存储层"""

    def __init__(self, db: Database):
        super().__init__(db)

    @property
    def table(self) -> str:
        return 'coupons'

    def _from_row(self, row) -> Coupon:
        return Coupon.from_row(row)

    def add(self, coupon: Coupon) -> Coupon:
        cur = self._db.execute(
            '''INSERT INTO coupons
               (tenant_id,promotion_id,code,face_value,min_amount,
                total_qty,used_qty,per_user_limit,start_at,end_at,status)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)''',
            (coupon.tenant_id, coupon.promotion_id, coupon.code,
             coupon.face_value, coupon.min_amount, coupon.total_qty,
             coupon.used_qty, coupon.per_user_limit,
             coupon.start_at, coupon.end_at, coupon.status),
        )
        self._db.commit()
        coupon.id = cur.lastrowid
        return coupon

    def find_by_code(self, code: str) -> Optional[Coupon]:
        return self._fetchone('SELECT * FROM coupons WHERE code=?', (code,))

    def find_active_by_tenant(self, tenant_id: int) -> List[Coupon]:
        return self._fetchall(
            """SELECT * FROM coupons
               WHERE tenant_id=? AND status='active'
                 AND start_at <= CURRENT_TIMESTAMP AND end_at >= CURRENT_TIMESTAMP
               ORDER BY created_at DESC""",
            (tenant_id,),
        )

    # ---- 领券 ----

    def claim(self, coupon_id: int, customer_id: int) -> CouponRecord:
        """
        客户领券（事务）：
        1. 检查券是否有效、有余量
        2. 检查客户是否已领
        3. 更新 used_qty
        4. 写入领券记录
        """
        with self._db.transaction():
            row = self._db.execute(
                'SELECT * FROM coupons WHERE id=? AND status="active"', (coupon_id,)
            ).fetchone()
            if not row:
                raise LookupError(f'券 {coupon_id} 不存在或已失效')
            coupon = Coupon.from_row(row)
            if coupon.remaining_qty <= 0:
                raise ValueError('券已被领完')
            exist = self._db.execute(
                'SELECT id FROM coupon_records WHERE coupon_id=? AND customer_id=?',
                (coupon_id, customer_id),
            ).fetchone()
            if exist:
                raise ValueError('您已领取过此券')
            self._db.execute(
                'UPDATE coupons SET used_qty=used_qty+1 WHERE id=?', (coupon_id,))
            cur = self._db.execute(
                '''INSERT INTO coupon_records (coupon_id,customer_id,order_id,used_at)
                   VALUES (?,?,NULL,NULL)''',
                (coupon_id, customer_id),
            )
            rec_id = cur.lastrowid

        return CouponRecord(id=rec_id, coupon_id=coupon_id, customer_id=customer_id)

    def use(self, coupon_id: int, customer_id: int, order_id: int) -> bool:
        """核销券（将已领取的券关联到订单）"""
        cur = self._db.execute(
            '''UPDATE coupon_records
               SET order_id=?, used_at=CURRENT_TIMESTAMP
               WHERE coupon_id=? AND customer_id=? AND used_at IS NULL''',
            (order_id, coupon_id, customer_id),
        )
        self._db.commit()
        return cur.rowcount > 0

    def list_customer_coupons(self, customer_id: int) -> List[CouponRecord]:
        rows = self._db.execute(
            'SELECT * FROM coupon_records WHERE customer_id=? ORDER BY created_at DESC',
            (customer_id,),
        ).fetchall()
        return [CouponRecord.from_row(r) for r in rows]

    def update_status(self, coupon_id: int, status: str) -> bool:
        cur = self._db.execute(
            'UPDATE coupons SET status=? WHERE id=?', (status, coupon_id))
        self._db.commit()
        return cur.rowcount > 0
