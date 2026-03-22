"""
供应商资质 Repository
继承 BaseRepository[SupplierQualification]，管理供应商资质证书。
"""
from __future__ import annotations

from typing import List, Optional

from ...common.base_repository import BaseRepository
from ...common.db import Database
from .models import SupplierQualification


class QualificationRepository(BaseRepository[SupplierQualification]):
    """supplier_qualifications 表的数据访问层"""

    def __init__(self, db: Database):
        super().__init__(db)

    # ------------------------------------------------------------------ #
    #  BaseRepository 抽象方法实现                                          #
    # ------------------------------------------------------------------ #

    @property
    def table(self) -> str:
        return 'supplier_qualifications'

    def _from_row(self, row) -> SupplierQualification:
        return SupplierQualification.from_row(row)

    # ------------------------------------------------------------------ #
    #  写操作                                                               #
    # ------------------------------------------------------------------ #

    def add(self, qual: SupplierQualification) -> SupplierQualification:
        """新增资质证书"""
        cur = self._db.execute(
            '''
            INSERT INTO supplier_qualifications
                (supplier_id, qual_type, name, issue_org, issue_date,
                 expire_date, file_url, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                qual.supplier_id, qual.qual_type, qual.name, qual.issue_org,
                qual.issue_date, qual.expire_date, qual.file_url, qual.status,
            ),
        )
        self._db.commit()
        qual.id = cur.lastrowid
        return qual

    def update(self, qual: SupplierQualification) -> bool:
        """更新资质证书信息"""
        cur = self._db.execute(
            '''
            UPDATE supplier_qualifications
            SET qual_type = ?, name = ?, issue_org = ?,
                issue_date = ?, expire_date = ?,
                file_url = ?, status = ?
            WHERE id = ?
            ''',
            (
                qual.qual_type, qual.name, qual.issue_org,
                qual.issue_date, qual.expire_date,
                qual.file_url, qual.status, qual.id,
            ),
        )
        self._db.commit()
        return cur.rowcount > 0

    def update_status(self, qual_id: int, status: str) -> bool:
        """更新资质状态"""
        cur = self._db.execute(
            'UPDATE supplier_qualifications SET status = ? WHERE id = ?',
            (status, qual_id),
        )
        self._db.commit()
        return cur.rowcount > 0

    def delete(self, id: int) -> bool:  # noqa: A002
        """删除资质记录"""
        cur = self._db.execute(
            'DELETE FROM supplier_qualifications WHERE id = ?', (id,)
        )
        self._db.commit()
        return cur.rowcount > 0

    # ------------------------------------------------------------------ #
    #  查询操作                                                             #
    # ------------------------------------------------------------------ #

    def find_by_supplier(self, supplier_id: int) -> List[SupplierQualification]:
        """查询某供应商的所有资质证书"""
        return self._fetchall(
            'SELECT * FROM supplier_qualifications WHERE supplier_id = ? ORDER BY id',
            (supplier_id,),
        )

    def find_expiring(self, days: int = 30) -> List[SupplierQualification]:
        """查询在未来 days 天内即将到期的有效资质（expire_date 在今天到 today+days 之间）"""
        return self._fetchall(
            '''
            SELECT * FROM supplier_qualifications
            WHERE status = 'valid'
              AND expire_date IS NOT NULL
              AND expire_date >= date('now')
              AND expire_date <= date('now', ? || ' days')
            ORDER BY expire_date
            ''',
            (str(days),),
        )

    def find_expired(self) -> List[SupplierQualification]:
        """查询所有已过期资质（expire_date < today）"""
        return self._fetchall(
            '''
            SELECT * FROM supplier_qualifications
            WHERE expire_date IS NOT NULL
              AND expire_date < date('now')
            ORDER BY expire_date
            ''',
        )
