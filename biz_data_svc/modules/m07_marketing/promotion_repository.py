from typing import List, Optional
from ...common.base_repository import BaseRepository
from ...common.db import Database
from .models import Promotion


class PromotionRepository(BaseRepository[Promotion]):
    """促销活动数据存储层"""

    def __init__(self, db: Database):
        super().__init__(db)

    @property
    def table(self) -> str:
        return 'promotions'

    def _from_row(self, row) -> Promotion:
        return Promotion.from_row(row)

    def add(self, promo: Promotion) -> Promotion:
        cur = self._db.execute(
            '''INSERT INTO promotions
               (tenant_id,name,promo_type,discount_rate,reduce_amount,
                min_amount,start_at,end_at,status)
               VALUES (?,?,?,?,?,?,?,?,?)''',
            (promo.tenant_id, promo.name, promo.promo_type,
             promo.discount_rate, promo.reduce_amount, promo.min_amount,
             promo.start_at, promo.end_at, promo.status),
        )
        self._db.commit()
        promo.id = cur.lastrowid
        return promo

    def update_status(self, promo_id: int, status: str) -> bool:
        cur = self._db.execute(
            'UPDATE promotions SET status=? WHERE id=?', (status, promo_id))
        self._db.commit()
        return cur.rowcount > 0

    def find_active(self, tenant_id: int) -> List[Promotion]:
        return self._fetchall(
            """SELECT * FROM promotions
               WHERE tenant_id=? AND status='active'
                 AND start_at <= CURRENT_TIMESTAMP AND end_at >= CURRENT_TIMESTAMP
               ORDER BY created_at DESC""",
            (tenant_id,),
        )

    def find_by_tenant(self, tenant_id: int) -> List[Promotion]:
        return self._fetchall(
            'SELECT * FROM promotions WHERE tenant_id=? ORDER BY created_at DESC',
            (tenant_id,),
        )

    # ---- 促销-商品关联 ----

    def add_product(self, promo_id: int, product_id: int) -> bool:
        try:
            self._db.execute(
                'INSERT OR IGNORE INTO promotion_products (promotion_id,product_id) VALUES (?,?)',
                (promo_id, product_id),
            )
            self._db.commit()
            return True
        except Exception:
            self._db.rollback()
            return False

    def remove_product(self, promo_id: int, product_id: int) -> bool:
        cur = self._db.execute(
            'DELETE FROM promotion_products WHERE promotion_id=? AND product_id=?',
            (promo_id, product_id),
        )
        self._db.commit()
        return cur.rowcount > 0

    def list_product_ids(self, promo_id: int) -> List[int]:
        rows = self._db.execute(
            'SELECT product_id FROM promotion_products WHERE promotion_id=?',
            (promo_id,),
        ).fetchall()
        return [r[0] for r in rows]
