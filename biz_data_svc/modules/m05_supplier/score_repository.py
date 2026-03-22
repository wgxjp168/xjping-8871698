"""
供应商评分 Repository
涉及表：supplier_scores
"""
from __future__ import annotations
from typing import List, Optional, Dict
from ...common.base_repository import BaseRepository
from ...common.db import Database
from .models import SupplierScore


def _calc_level(total: float) -> str:
    if total >= 90: return 'S'
    if total >= 80: return 'A'
    if total >= 70: return 'B'
    if total >= 60: return 'C'
    return 'D'


class ScoreRepository(BaseRepository[SupplierScore]):
    """供应商评分数据存储层"""

    def __init__(self, db: Database):
        super().__init__(db)

    @property
    def table(self) -> str:
        return 'supplier_scores'

    def _from_row(self, row) -> SupplierScore:
        return SupplierScore.from_row(row)

    def add(self, score: SupplierScore) -> SupplierScore:
        weights = {'quality': 0.3, 'delivery': 0.3, 'price': 0.2, 'service': 0.2}
        total = round(
            score.quality_score * weights['quality'] +
            score.delivery_score * weights['delivery'] +
            score.price_score   * weights['price']   +
            score.service_score * weights['service'],
            2,
        )
        level = _calc_level(total)
        cur = self._db.execute(
            '''INSERT INTO supplier_scores
               (supplier_id, tenant_id, period, quality_score, delivery_score,
                price_score, service_score, total_score, level, evaluator_id, note)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)''',
            (score.supplier_id, score.tenant_id, score.period,
             score.quality_score, score.delivery_score,
             score.price_score, score.service_score,
             total, level, score.evaluator_id, score.note),
        )
        self._db.commit()
        score.id = cur.lastrowid
        score.total_score = total
        score.level = level
        return score

    def find_by_supplier(self, supplier_id: int, tenant_id: int) -> List[SupplierScore]:
        return self._fetchall(
            'SELECT * FROM supplier_scores WHERE supplier_id=? AND tenant_id=? ORDER BY period DESC',
            (supplier_id, tenant_id),
        )

    def get_latest(self, supplier_id: int, tenant_id: int) -> Optional[SupplierScore]:
        return self._fetchone(
            'SELECT * FROM supplier_scores WHERE supplier_id=? AND tenant_id=? ORDER BY period DESC LIMIT 1',
            (supplier_id, tenant_id),
        )

    def get_avg(self, supplier_id: int, tenant_id: int) -> Dict[str, float]:
        row = self._db.execute(
            '''SELECT AVG(quality_score), AVG(delivery_score), AVG(price_score),
                      AVG(service_score), AVG(total_score)
               FROM supplier_scores WHERE supplier_id=? AND tenant_id=?''',
            (supplier_id, tenant_id),
        ).fetchone()
        if row:
            return {
                'quality': round(row[0] or 0, 2),
                'delivery': round(row[1] or 0, 2),
                'price': round(row[2] or 0, 2),
                'service': round(row[3] or 0, 2),
                'total': round(row[4] or 0, 2),
            }
        return {'quality': 0, 'delivery': 0, 'price': 0, 'service': 0, 'total': 0}
