"""
合同 Repository
继承 BaseRepository[Contract]，提供合同全生命周期管理。
"""
from __future__ import annotations

from typing import List, Optional

from ...common.base_repository import BaseRepository
from ...common.db import Database
from .models import Contract


class ContractRepository(BaseRepository[Contract]):
    """contracts 表的数据访问层"""

    def __init__(self, db: Database):
        super().__init__(db)

    # ------------------------------------------------------------------ #
    #  BaseRepository 抽象方法实现                                          #
    # ------------------------------------------------------------------ #

    @property
    def table(self) -> str:
        return 'contracts'

    def _from_row(self, row) -> Contract:
        return Contract.from_row(row)

    # ------------------------------------------------------------------ #
    #  写操作                                                               #
    # ------------------------------------------------------------------ #

    def add(self, contract: Contract) -> Contract:
        """新增合同"""
        cur = self._db.execute(
            '''
            INSERT INTO contracts
                (tenant_id, contract_no, title, contract_type,
                 party_a, party_b, supplier_id, sourcing_id,
                 amount, currency, sign_date, start_date, end_date,
                 payment_terms, status, file_url, signed_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                contract.tenant_id, contract.contract_no, contract.title,
                contract.contract_type, contract.party_a, contract.party_b,
                contract.supplier_id, contract.sourcing_id,
                contract.amount, contract.currency,
                contract.sign_date, contract.start_date, contract.end_date,
                contract.payment_terms, contract.status,
                contract.file_url, contract.signed_by,
            ),
        )
        self._db.commit()
        contract.id = cur.lastrowid
        return contract

    def find_by_id(self, id: int) -> Optional[Contract]:  # noqa: A002
        """按主键查询合同"""
        return self._fetchone('SELECT * FROM contracts WHERE id = ?', (id,))

    def find_by_tenant(
        self, tenant_id: int, status: Optional[str] = None
    ) -> List[Contract]:
        """按租户查询合同列表，可按状态过滤，倒序"""
        if status is not None:
            return self._fetchall(
                'SELECT * FROM contracts WHERE tenant_id = ? AND status = ? ORDER BY id DESC',
                (tenant_id, status),
            )
        return self._fetchall(
            'SELECT * FROM contracts WHERE tenant_id = ? ORDER BY id DESC',
            (tenant_id,),
        )

    def update_status(self, contract_id: int, status: str) -> bool:
        """更新合同状态"""
        cur = self._db.execute(
            "UPDATE contracts SET status = ?, updated_at = datetime('now') WHERE id = ?",
            (status, contract_id),
        )
        self._db.commit()
        return cur.rowcount > 0

    def activate(self, contract_id: int, signed_by: int) -> bool:
        """激活合同：设置 status=active, sign_date=today, signed_by"""
        cur = self._db.execute(
            '''
            UPDATE contracts
            SET status      = 'active',
                sign_date   = date('now'),
                signed_by   = ?,
                updated_at  = datetime('now')
            WHERE id = ?
            ''',
            (signed_by, contract_id),
        )
        self._db.commit()
        return cur.rowcount > 0

    def find_expiring(self, tenant_id: int, days: int = 30) -> List[Contract]:
        """查询即将在 days 天内到期的合同（不含已过期、不含非 active 状态）"""
        return self._fetchall(
            '''
            SELECT * FROM contracts
            WHERE tenant_id = ?
              AND status = 'active'
              AND end_date IS NOT NULL
              AND end_date >= date('now')
              AND end_date <= date('now', ? || ' days')
            ORDER BY end_date
            ''',
            (tenant_id, str(days)),
        )
