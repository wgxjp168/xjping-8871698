"""
租户 Repository
继承 BaseRepository[Tenant]，提供租户表完整 CRUD 操作。
"""
from __future__ import annotations

from typing import List, Optional

from ...common.base_repository import BaseRepository
from ...common.db import Database
from .models import Tenant


class TenantRepository(BaseRepository[Tenant]):
    """tenants 表的数据访问层"""

    def __init__(self, db: Database):
        super().__init__(db)

    # ------------------------------------------------------------------ #
    #  BaseRepository 抽象方法实现                                          #
    # ------------------------------------------------------------------ #

    @property
    def table(self) -> str:
        return 'tenants'

    def _from_row(self, row) -> Tenant:
        return Tenant.from_row(row)

    # ------------------------------------------------------------------ #
    #  写操作                                                               #
    # ------------------------------------------------------------------ #

    def add(self, tenant: Tenant) -> Tenant:
        """插入新租户，返回带 id 的 Tenant 对象"""
        sql = '''
            INSERT INTO tenants
                (name, code, status, plan,
                 contact_name, contact_phone, contact_email,
                 address, logo_url, expired_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        '''
        params = (
            tenant.name,
            tenant.code,
            tenant.status,
            tenant.plan,
            tenant.contact_name,
            tenant.contact_phone,
            tenant.contact_email,
            tenant.address,
            tenant.logo_url,
            tenant.expired_at,
        )
        cur = self._db.execute(sql, params)
        self._db.commit()
        tenant.id = cur.lastrowid
        return tenant

    def update(self, tenant: Tenant) -> bool:
        """更新 name, contact_name, contact_phone, contact_email, address, logo_url, plan"""
        sql = '''
            UPDATE tenants
            SET name          = ?,
                contact_name  = ?,
                contact_phone = ?,
                contact_email = ?,
                address       = ?,
                logo_url      = ?,
                plan          = ?
            WHERE id = ?
        '''
        params = (
            tenant.name,
            tenant.contact_name,
            tenant.contact_phone,
            tenant.contact_email,
            tenant.address,
            tenant.logo_url,
            tenant.plan,
            tenant.id,
        )
        cur = self._db.execute(sql, params)
        self._db.commit()
        return cur.rowcount > 0

    def update_status(self, tenant_id: int, status: int) -> bool:
        """仅更新租户状态"""
        sql = 'UPDATE tenants SET status = ? WHERE id = ?'
        cur = self._db.execute(sql, (status, tenant_id))
        self._db.commit()
        return cur.rowcount > 0

    def delete(self, id: int) -> bool:  # noqa: A002
        """删除租户，返回是否成功"""
        cur = self._db.execute('DELETE FROM tenants WHERE id = ?', (id,))
        self._db.commit()
        return cur.rowcount > 0

    # ------------------------------------------------------------------ #
    #  查询操作                                                             #
    # ------------------------------------------------------------------ #

    def find_by_id(self, id: int) -> Optional[Tenant]:  # noqa: A002
        """按主键查询租户"""
        return self._fetchone(
            'SELECT * FROM tenants WHERE id = ?', (id,)
        )

    def find_by_code(self, code: str) -> Optional[Tenant]:
        """按租户编码查询"""
        return self._fetchone(
            'SELECT * FROM tenants WHERE code = ?', (code,)
        )

    def find_by_status(self, status: int) -> List[Tenant]:
        """按状态查询所有租户"""
        return self._fetchall(
            'SELECT * FROM tenants WHERE status = ? ORDER BY id', (status,)
        )

    def find_all(self) -> List[Tenant]:
        """查询全部租户，按 id 排序"""
        return self._fetchall('SELECT * FROM tenants ORDER BY id')
