"""
供应商主表 Repository
继承 BaseRepository[Supplier]，提供供应商完整 CRUD 与状态管理。
"""
from __future__ import annotations

from typing import List, Optional

from ...common.base_repository import BaseRepository
from ...common.db import Database
from .models import Supplier


class SupplierRepository(BaseRepository[Supplier]):
    """suppliers 表的数据访问层"""

    def __init__(self, db: Database):
        super().__init__(db)

    # ------------------------------------------------------------------ #
    #  BaseRepository 抽象方法实现                                          #
    # ------------------------------------------------------------------ #

    @property
    def table(self) -> str:
        return 'suppliers'

    def _from_row(self, row) -> Supplier:
        return Supplier.from_row(row)

    # ------------------------------------------------------------------ #
    #  写操作                                                               #
    # ------------------------------------------------------------------ #

    def add(self, supplier: Supplier) -> Supplier:
        """新增供应商"""
        cur = self._db.execute(
            '''
            INSERT INTO suppliers
                (tenant_id, name, code, short_name, supplier_type, status,
                 contact_name, phone, email, address, website, tax_no,
                 bank_account, bank_name, payment_terms, credit_limit,
                 reviewer_id, reviewed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                supplier.tenant_id, supplier.name, supplier.code,
                supplier.short_name, supplier.supplier_type, supplier.status,
                supplier.contact_name, supplier.phone, supplier.email,
                supplier.address, supplier.website, supplier.tax_no,
                supplier.bank_account, supplier.bank_name,
                supplier.payment_terms, supplier.credit_limit,
                supplier.reviewer_id, supplier.reviewed_at,
            ),
        )
        self._db.commit()
        supplier.id = cur.lastrowid
        return supplier

    def update(self, supplier: Supplier) -> bool:
        """更新供应商基本信息"""
        cur = self._db.execute(
            '''
            UPDATE suppliers
            SET name = ?, short_name = ?, supplier_type = ?,
                contact_name = ?, phone = ?, email = ?,
                address = ?, website = ?, tax_no = ?,
                bank_account = ?, bank_name = ?,
                payment_terms = ?, credit_limit = ?,
                updated_at = datetime('now')
            WHERE id = ?
            ''',
            (
                supplier.name, supplier.short_name, supplier.supplier_type,
                supplier.contact_name, supplier.phone, supplier.email,
                supplier.address, supplier.website, supplier.tax_no,
                supplier.bank_account, supplier.bank_name,
                supplier.payment_terms, supplier.credit_limit,
                supplier.id,
            ),
        )
        self._db.commit()
        return cur.rowcount > 0

    def update_status(self, supplier_id: int, status: str) -> bool:
        """更新供应商状态"""
        cur = self._db.execute(
            "UPDATE suppliers SET status = ?, updated_at = datetime('now') WHERE id = ?",
            (status, supplier_id),
        )
        self._db.commit()
        return cur.rowcount > 0

    def review(
        self, supplier_id: int, reviewer_id: int, approved: bool
    ) -> bool:
        """
        审核供应商：
        - approved=True  → status=active
        - approved=False → status=suspended
        同时记录 reviewer_id 和 reviewed_at
        """
        status = 'active' if approved else 'suspended'
        cur = self._db.execute(
            '''
            UPDATE suppliers
            SET status      = ?,
                reviewer_id = ?,
                reviewed_at = datetime('now'),
                updated_at  = datetime('now')
            WHERE id = ?
            ''',
            (status, reviewer_id, supplier_id),
        )
        self._db.commit()
        return cur.rowcount > 0

    def blacklist(self, supplier_id: int) -> bool:
        """将供应商加入黑名单"""
        cur = self._db.execute(
            "UPDATE suppliers SET status = 'blacklisted', updated_at = datetime('now') WHERE id = ?",
            (supplier_id,),
        )
        self._db.commit()
        return cur.rowcount > 0

    def delete(self, id: int) -> bool:  # noqa: A002
        """删除供应商记录"""
        cur = self._db.execute('DELETE FROM suppliers WHERE id = ?', (id,))
        self._db.commit()
        return cur.rowcount > 0

    # ------------------------------------------------------------------ #
    #  查询操作                                                             #
    # ------------------------------------------------------------------ #

    def find_by_id(self, id: int) -> Optional[Supplier]:  # noqa: A002
        """按主键查询供应商"""
        return self._fetchone('SELECT * FROM suppliers WHERE id = ?', (id,))

    def find_by_tenant(
        self, tenant_id: int, status: Optional[str] = None
    ) -> List[Supplier]:
        """按租户查询供应商，可按状态过滤，倒序"""
        if status is not None:
            return self._fetchall(
                'SELECT * FROM suppliers WHERE tenant_id = ? AND status = ? ORDER BY id DESC',
                (tenant_id, status),
            )
        return self._fetchall(
            'SELECT * FROM suppliers WHERE tenant_id = ? ORDER BY id DESC',
            (tenant_id,),
        )

    def find_by_code(self, tenant_id: int, code: str) -> Optional[Supplier]:
        """按供应商编码查询（租户内唯一）"""
        return self._fetchone(
            'SELECT * FROM suppliers WHERE tenant_id = ? AND code = ?',
            (tenant_id, code),
        )
