"""
物流 Repository
继承 BaseRepository[Logistics]，提供 logistics 表完整操作。
"""
from __future__ import annotations

import json
from typing import Optional

from ...common.base_repository import BaseRepository
from ...common.db import Database
from .models import Logistics


class LogisticsRepository(BaseRepository[Logistics]):
    """logistics 表的数据访问层"""

    def __init__(self, db: Database):
        super().__init__(db)

    # ------------------------------------------------------------------ #
    #  BaseRepository 抽象方法实现                                          #
    # ------------------------------------------------------------------ #

    @property
    def table(self) -> str:
        return 'logistics'

    def _from_row(self, row) -> Logistics:
        return Logistics.from_row(row)

    # ------------------------------------------------------------------ #
    #  写操作                                                               #
    # ------------------------------------------------------------------ #

    def create(self, logistics: Logistics) -> Logistics:
        """插入新物流记录，返回带有 id 的 Logistics 对象"""
        sql = '''
            INSERT INTO logistics (
                order_id, company, company_code, tracking_no,
                status, signed_at, receiver, traces
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        '''
        params = (
            logistics.order_id,
            logistics.company,
            logistics.company_code,
            logistics.tracking_no,
            logistics.status,
            logistics.signed_at,
            logistics.receiver,
            logistics.traces,
        )
        cur = self._db.execute(sql, params)
        self._db.commit()
        logistics.id = cur.lastrowid
        return logistics

    def update_status(self, logistics_id: int, status: str) -> bool:
        """更新物流状态，并刷新 updated_at"""
        sql = '''
            UPDATE logistics
            SET status     = ?,
                updated_at = datetime('now')
            WHERE id = ?
        '''
        cur = self._db.execute(sql, (status, logistics_id))
        self._db.commit()
        return cur.rowcount > 0

    def update_tracking(
        self,
        logistics_id: int,
        tracking_no: str,
        company: str,
        company_code: str = '',
    ) -> bool:
        """
        更新运单号与快递公司信息，同时刷新 updated_at。
        company_code 可选，默认为空字符串。
        """
        sql = '''
            UPDATE logistics
            SET tracking_no  = ?,
                company      = ?,
                company_code = ?,
                updated_at   = datetime('now')
            WHERE id = ?
        '''
        cur = self._db.execute(sql, (tracking_no, company, company_code, logistics_id))
        self._db.commit()
        return cur.rowcount > 0

    def add_trace(self, logistics_id: int, trace_info: dict) -> bool:
        """
        将新的轨迹节点追加到 traces JSON 数组中。
        读取当前 traces → 反序列化 → append → 序列化写回，同时刷新 updated_at。
        若当前 traces 为空或非合法 JSON 数组，则以新列表初始化。
        """
        # 先读取当前 traces 字段
        row = self._db.execute(
            'SELECT traces FROM logistics WHERE id = ?', (logistics_id,)
        ).fetchone()
        if row is None:
            return False

        raw = row[0] if row[0] else '[]'
        try:
            traces: list = json.loads(raw)
            if not isinstance(traces, list):
                traces = []
        except (json.JSONDecodeError, TypeError):
            traces = []

        traces.append(trace_info)
        new_traces = json.dumps(traces, ensure_ascii=False)

        sql = '''
            UPDATE logistics
            SET traces     = ?,
                updated_at = datetime('now')
            WHERE id = ?
        '''
        cur = self._db.execute(sql, (new_traces, logistics_id))
        self._db.commit()
        return cur.rowcount > 0

    def sign(self, logistics_id: int, receiver: str = '') -> bool:
        """
        确认签收：status → delivered，signed_at = now，记录签收人。
        同时刷新 updated_at。
        """
        sql = '''
            UPDATE logistics
            SET status     = 'delivered',
                signed_at  = datetime('now'),
                receiver   = ?,
                updated_at = datetime('now')
            WHERE id = ?
        '''
        cur = self._db.execute(sql, (receiver, logistics_id))
        self._db.commit()
        return cur.rowcount > 0

    # ------------------------------------------------------------------ #
    #  查询操作                                                             #
    # ------------------------------------------------------------------ #

    def find_by_id(self, id: int) -> Optional[Logistics]:  # noqa: A002
        """按主键查询物流记录"""
        return self._fetchone('SELECT * FROM logistics WHERE id = ?', (id,))

    def find_by_order(self, order_id: int) -> Optional[Logistics]:
        """
        按订单 ID 查询物流记录。
        一个订单通常只有一条物流，故返回 Optional[Logistics]。
        """
        return self._fetchone(
            'SELECT * FROM logistics WHERE order_id = ? ORDER BY id LIMIT 1',
            (order_id,),
        )
