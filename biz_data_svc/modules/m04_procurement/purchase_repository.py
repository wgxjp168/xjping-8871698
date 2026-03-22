"""
采购申请 Repository
继承 BaseRepository[PurchaseRequest]，提供采购申请完整 CRUD 操作。
"""
from __future__ import annotations

from typing import List, Optional

from ...common.base_repository import BaseRepository
from ...common.db import Database
from .models import PurchaseRequest, PurchaseRequestItem


class PurchaseRepository(BaseRepository[PurchaseRequest]):
    """purchase_requests 表的数据访问层"""

    def __init__(self, db: Database):
        super().__init__(db)

    # ------------------------------------------------------------------ #
    #  BaseRepository 抽象方法实现                                          #
    # ------------------------------------------------------------------ #

    @property
    def table(self) -> str:
        return 'purchase_requests'

    def _from_row(self, row) -> PurchaseRequest:
        return PurchaseRequest.from_row(row)

    # ------------------------------------------------------------------ #
    #  私有辅助                                                             #
    # ------------------------------------------------------------------ #

    def _load_items(self, request_id: int) -> List[PurchaseRequestItem]:
        """加载采购申请明细行"""
        rows = self._db.execute(
            'SELECT * FROM purchase_request_items WHERE request_id = ? ORDER BY id',
            (request_id,),
        ).fetchall()
        return [PurchaseRequestItem.from_row(r) for r in rows]

    def _attach_items(self, pr: PurchaseRequest) -> PurchaseRequest:
        """为 PurchaseRequest 对象附加明细行"""
        pr.items = self._load_items(pr.id)
        return pr

    # ------------------------------------------------------------------ #
    #  写操作                                                               #
    # ------------------------------------------------------------------ #

    def create(self, pr: PurchaseRequest) -> PurchaseRequest:
        """在事务中插入主表及明细行，返回带 id 的 PurchaseRequest"""
        with self._db.transaction():
            cur = self._db.execute(
                '''
                INSERT INTO purchase_requests
                    (tenant_id, req_no, title, requester_id, dept, category,
                     budget, currency, priority, required_date, reason, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    pr.tenant_id, pr.req_no, pr.title, pr.requester_id,
                    pr.dept, pr.category, pr.budget, pr.currency,
                    pr.priority, pr.required_date, pr.reason, pr.status,
                ),
            )
            pr.id = cur.lastrowid
            for item in pr.items:
                item.request_id = pr.id
                item_cur = self._db.execute(
                    '''
                    INSERT INTO purchase_request_items
                        (request_id, product_name, spec, quantity, unit,
                         estimated_price, note)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''',
                    (
                        item.request_id, item.product_name, item.spec,
                        item.quantity, item.unit, item.estimated_price,
                        item.note,
                    ),
                )
                item.id = item_cur.lastrowid
        return pr

    def update_status(self, req_id: int, status: str) -> bool:
        """更新申请状态"""
        cur = self._db.execute(
            "UPDATE purchase_requests SET status = ?, updated_at = datetime('now') WHERE id = ?",
            (status, req_id),
        )
        self._db.commit()
        return cur.rowcount > 0

    def submit(self, req_id: int) -> bool:
        """提交审批：draft → submitted"""
        cur = self._db.execute(
            "UPDATE purchase_requests SET status = 'submitted', updated_at = datetime('now') "
            "WHERE id = ? AND status = 'draft'",
            (req_id,),
        )
        self._db.commit()
        return cur.rowcount > 0

    def cancel(self, req_id: int, reason: str = '') -> bool:
        """取消申请：任意状态 → cancelled"""
        cur = self._db.execute(
            "UPDATE purchase_requests SET status = 'cancelled', reason = ?, "
            "updated_at = datetime('now') WHERE id = ?",
            (reason, req_id),
        )
        self._db.commit()
        return cur.rowcount > 0

    def delete(self, id: int) -> bool:  # noqa: A002
        """删除申请记录（同时删除明细行）"""
        with self._db.transaction():
            self._db.execute(
                'DELETE FROM purchase_request_items WHERE request_id = ?', (id,)
            )
            cur = self._db.execute(
                'DELETE FROM purchase_requests WHERE id = ?', (id,)
            )
        return cur.rowcount > 0

    # ------------------------------------------------------------------ #
    #  查询操作                                                             #
    # ------------------------------------------------------------------ #

    def find_by_id(self, id: int) -> Optional[PurchaseRequest]:  # noqa: A002
        """按主键查询，附带明细行"""
        pr = self._fetchone('SELECT * FROM purchase_requests WHERE id = ?', (id,))
        if pr:
            self._attach_items(pr)
        return pr

    def find_by_tenant(
        self, tenant_id: int, status: Optional[str] = None
    ) -> List[PurchaseRequest]:
        """按租户查询，可按状态过滤"""
        if status is not None:
            rows = self._db.execute(
                'SELECT * FROM purchase_requests WHERE tenant_id = ? AND status = ? ORDER BY id DESC',
                (tenant_id, status),
            ).fetchall()
        else:
            rows = self._db.execute(
                'SELECT * FROM purchase_requests WHERE tenant_id = ? ORDER BY id DESC',
                (tenant_id,),
            ).fetchall()
        result = []
        for row in rows:
            pr = PurchaseRequest.from_row(row)
            self._attach_items(pr)
            result.append(pr)
        return result

    def find_by_requester(self, requester_id: int) -> List[PurchaseRequest]:
        """按申请人查询"""
        rows = self._db.execute(
            'SELECT * FROM purchase_requests WHERE requester_id = ? ORDER BY id DESC',
            (requester_id,),
        ).fetchall()
        result = []
        for row in rows:
            pr = PurchaseRequest.from_row(row)
            self._attach_items(pr)
            result.append(pr)
        return result
