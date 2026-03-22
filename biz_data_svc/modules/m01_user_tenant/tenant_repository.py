from typing import List, Optional
from ...common.base_repository import BaseRepository
from ...common.db import Database
from .models import Tenant


class TenantRepository(BaseRepository[Tenant]):
    """租户数据存储层"""

    def __init__(self, db: Database):
        super().__init__(db)

    @property
    def table(self) -> str:
        return 'tenants'

    def _from_row(self, row) -> Tenant:
        return Tenant.from_row(row)

    # ---- 写 ----

    def add(self, tenant: Tenant) -> Tenant:
        cur = self._db.execute(
            'INSERT INTO tenants (name, code, status, plan) VALUES (?,?,?,?)',
            (tenant.name, tenant.code, tenant.status, tenant.plan),
        )
        self._db.commit()
        tenant.id = cur.lastrowid
        return tenant

    def update_status(self, tenant_id: int, status: str) -> bool:
        cur = self._db.execute(
            'UPDATE tenants SET status=?, updated_at=CURRENT_TIMESTAMP WHERE id=?',
            (status, tenant_id),
        )
        self._db.commit()
        return cur.rowcount > 0

    def update_plan(self, tenant_id: int, plan: str) -> bool:
        cur = self._db.execute(
            'UPDATE tenants SET plan=?, updated_at=CURRENT_TIMESTAMP WHERE id=?',
            (plan, tenant_id),
        )
        self._db.commit()
        return cur.rowcount > 0

    # ---- 读 ----

    def find_by_code(self, code: str) -> Optional[Tenant]:
        return self._fetchone('SELECT * FROM tenants WHERE code=?', (code,))

    def find_by_status(self, status: str) -> List[Tenant]:
        return self._fetchall('SELECT * FROM tenants WHERE status=? ORDER BY id', (status,))
