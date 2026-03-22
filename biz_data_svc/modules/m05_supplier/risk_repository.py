"""
供应商风险 Repository
涉及表：supplier_risks
"""
from __future__ import annotations
from typing import List, Optional
from ...common.base_repository import BaseRepository
from ...common.db import Database
from .models import SupplierRisk


class RiskRepository(BaseRepository[SupplierRisk]):
    """供应商风险数据存储层"""

    def __init__(self, db: Database):
        super().__init__(db)

    @property
    def table(self) -> str:
        return 'supplier_risks'

    def _from_row(self, row) -> SupplierRisk:
        return SupplierRisk.from_row(row)

    def add(self, risk: SupplierRisk) -> SupplierRisk:
        cur = self._db.execute(
            '''INSERT INTO supplier_risks
               (supplier_id, risk_type, level, description, source, status,
                found_at, resolved_at, resolver_id, resolution_note)
               VALUES (?,?,?,?,?,?,CURRENT_TIMESTAMP,?,?,?)''',
            (risk.supplier_id, risk.risk_type, risk.level, risk.description,
             risk.source, risk.status, risk.resolved_at,
             risk.resolver_id, risk.resolution_note),
        )
        self._db.commit()
        risk.id = cur.lastrowid
        return risk

    def find_by_supplier(self, supplier_id: int, status: Optional[str] = None) -> List[SupplierRisk]:
        if status:
            return self._fetchall(
                'SELECT * FROM supplier_risks WHERE supplier_id=? AND status=? ORDER BY found_at DESC',
                (supplier_id, status),
            )
        return self._fetchall(
            'SELECT * FROM supplier_risks WHERE supplier_id=? ORDER BY found_at DESC',
            (supplier_id,),
        )

    def find_open_critical(self, tenant_id: Optional[int] = None) -> List[SupplierRisk]:
        """查询所有开放的严重风险"""
        if tenant_id:
            return self._fetchall(
                '''SELECT r.* FROM supplier_risks r
                   JOIN suppliers s ON s.id=r.supplier_id
                   WHERE r.status='open' AND r.level='critical' AND s.tenant_id=?
                   ORDER BY r.found_at DESC''',
                (tenant_id,),
            )
        return self._fetchall(
            "SELECT * FROM supplier_risks WHERE status='open' AND level='critical' ORDER BY found_at DESC",
        )

    def resolve(self, risk_id: int, resolver_id: int, note: str) -> bool:
        cur = self._db.execute(
            '''UPDATE supplier_risks
               SET status='resolved', resolved_at=CURRENT_TIMESTAMP,
                   resolver_id=?, resolution_note=?
               WHERE id=?''',
            (resolver_id, note, risk_id),
        )
        self._db.commit()
        return cur.rowcount > 0

    def mitigate(self, risk_id: int) -> bool:
        cur = self._db.execute(
            "UPDATE supplier_risks SET status='mitigating' WHERE id=?", (risk_id,))
        self._db.commit()
        return cur.rowcount > 0
