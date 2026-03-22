"""
寻源/招标 Repository
继承 BaseRepository[SourcingEvent]，管理寻源事件与供应商报价。
"""
from __future__ import annotations

from typing import List, Optional

from ...common.base_repository import BaseRepository
from ...common.db import Database
from .models import SourcingEvent, SourcingQuote


class SourcingRepository(BaseRepository[SourcingEvent]):
    """sourcing_events 表的数据访问层（兼管 sourcing_quotes）"""

    def __init__(self, db: Database):
        super().__init__(db)

    # ------------------------------------------------------------------ #
    #  BaseRepository 抽象方法实现                                          #
    # ------------------------------------------------------------------ #

    @property
    def table(self) -> str:
        return 'sourcing_events'

    def _from_row(self, row) -> SourcingEvent:
        return SourcingEvent.from_row(row)

    # ------------------------------------------------------------------ #
    #  寻源事件写操作                                                        #
    # ------------------------------------------------------------------ #

    def create(self, event: SourcingEvent) -> SourcingEvent:
        """新建寻源事件"""
        cur = self._db.execute(
            '''
            INSERT INTO sourcing_events
                (tenant_id, request_id, event_no, title, description,
                 deadline, status, winner_supplier_id, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                event.tenant_id, event.request_id, event.event_no,
                event.title, event.description, event.deadline,
                event.status, event.winner_supplier_id, event.created_by,
            ),
        )
        self._db.commit()
        event.id = cur.lastrowid
        return event

    def update_status(self, event_id: int, status: str) -> bool:
        """更新寻源事件状态"""
        cur = self._db.execute(
            "UPDATE sourcing_events SET status = ?, updated_at = datetime('now') WHERE id = ?",
            (status, event_id),
        )
        self._db.commit()
        return cur.rowcount > 0

    def publish(self, event_id: int) -> bool:
        """发布寻源事件：draft → published"""
        cur = self._db.execute(
            "UPDATE sourcing_events SET status = 'published', updated_at = datetime('now') "
            "WHERE id = ? AND status = 'draft'",
            (event_id,),
        )
        self._db.commit()
        return cur.rowcount > 0

    def close(self, event_id: int, winner_supplier_id: int) -> bool:
        """关闭寻源事件并设置中标供应商：任意状态 → closed"""
        cur = self._db.execute(
            "UPDATE sourcing_events "
            "SET status = 'closed', winner_supplier_id = ?, updated_at = datetime('now') "
            "WHERE id = ?",
            (winner_supplier_id, event_id),
        )
        self._db.commit()
        return cur.rowcount > 0

    # ------------------------------------------------------------------ #
    #  寻源事件查询                                                          #
    # ------------------------------------------------------------------ #

    def find_by_id(self, id: int) -> Optional[SourcingEvent]:  # noqa: A002
        """按主键查询寻源事件"""
        return self._fetchone(
            'SELECT * FROM sourcing_events WHERE id = ?', (id,)
        )

    def find_by_tenant(self, tenant_id: int) -> List[SourcingEvent]:
        """按租户查询所有寻源事件，倒序"""
        return self._fetchall(
            'SELECT * FROM sourcing_events WHERE tenant_id = ? ORDER BY id DESC',
            (tenant_id,),
        )

    # ------------------------------------------------------------------ #
    #  报价操作                                                              #
    # ------------------------------------------------------------------ #

    def submit_quote(self, quote: SourcingQuote) -> SourcingQuote:
        """供应商提交报价"""
        cur = self._db.execute(
            '''
            INSERT INTO sourcing_quotes
                (event_id, supplier_id, unit_price, total_price, currency,
                 delivery_days, warranty_months, note, attachments,
                 is_winner, submitted_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            ''',
            (
                quote.event_id, quote.supplier_id, quote.unit_price,
                quote.total_price, quote.currency, quote.delivery_days,
                quote.warranty_months, quote.note, quote.attachments,
                quote.is_winner,
            ),
        )
        self._db.commit()
        quote.id = cur.lastrowid
        return quote

    def list_quotes(self, event_id: int) -> List[SourcingQuote]:
        """列出某寻源事件的所有报价，按单价升序"""
        rows = self._db.execute(
            'SELECT * FROM sourcing_quotes WHERE event_id = ? ORDER BY unit_price ASC',
            (event_id,),
        ).fetchall()
        return [SourcingQuote.from_row(r) for r in rows]

    def select_winner(self, event_id: int, quote_id: int) -> bool:
        """
        事务中选定中标报价：
        1. 将该事件所有报价的 is_winner 置 0
        2. 将指定报价的 is_winner 置 1
        3. 从报价取得 supplier_id 更新事件的 winner_supplier_id
        """
        with self._db.transaction():
            # 重置同一事件所有报价
            self._db.execute(
                'UPDATE sourcing_quotes SET is_winner = 0 WHERE event_id = ?',
                (event_id,),
            )
            # 标记中标报价
            self._db.execute(
                'UPDATE sourcing_quotes SET is_winner = 1 WHERE id = ? AND event_id = ?',
                (quote_id, event_id),
            )
            # 取中标供应商 id
            row = self._db.execute(
                'SELECT supplier_id FROM sourcing_quotes WHERE id = ?',
                (quote_id,),
            ).fetchone()
            if not row:
                raise ValueError(f'quote {quote_id} not found under event {event_id}')
            supplier_id = tuple(row)[0]
            # 更新事件 winner_supplier_id
            cur = self._db.execute(
                "UPDATE sourcing_events SET winner_supplier_id = ?, updated_at = datetime('now') WHERE id = ?",
                (supplier_id, event_id),
            )
        return cur.rowcount > 0
