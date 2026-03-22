"""
短信记录 Repository
继承 BaseRepository[SmsRecord]，提供 sms_records 表完整操作。
"""
from __future__ import annotations

from typing import List, Optional, Tuple

from ...common.base_repository import BaseRepository
from ...common.db import Database
from .models import SmsRecord


class SmsRepository(BaseRepository[SmsRecord]):
    """sms_records 表的数据访问层"""

    def __init__(self, db: Database):
        super().__init__(db)

    # ------------------------------------------------------------------ #
    #  BaseRepository 抽象方法实现                                          #
    # ------------------------------------------------------------------ #

    @property
    def table(self) -> str:
        return 'sms_records'

    def _from_row(self, row) -> SmsRecord:
        return SmsRecord.from_row(row)

    # ------------------------------------------------------------------ #
    #  写操作                                                               #
    # ------------------------------------------------------------------ #

    def create(self, record: SmsRecord) -> SmsRecord:
        """创建短信发送记录（初始 status=pending）"""
        sql = '''
            INSERT INTO sms_records
                (tenant_id, phone, template_code, params, content,
                 status, provider, provider_msg_id, error_msg, sent_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        '''
        with self._db.transaction():
            cur = self._db.execute(sql, (
                record.tenant_id,
                record.phone,
                record.template_code,
                record.params,
                record.content,
                record.status,
                record.provider,
                record.provider_msg_id,
                record.error_msg,
                record.sent_at,
            ))
            record.id = cur.lastrowid
        return record

    def mark_sent(self, record_id: int, provider_msg_id: str) -> bool:
        """标记短信已发送：status=sent, sent_at=now, provider_msg_id"""
        cur = self._db.execute(
            '''UPDATE sms_records
               SET status          = 'sent',
                   sent_at         = CURRENT_TIMESTAMP,
                   provider_msg_id = ?
               WHERE id = ?''',
            (provider_msg_id, record_id),
        )
        self._db.commit()
        return cur.rowcount > 0

    def mark_delivered(self, record_id: int) -> bool:
        """标记短信已送达：status=delivered"""
        cur = self._db.execute(
            "UPDATE sms_records SET status = 'delivered' WHERE id = ?",
            (record_id,),
        )
        self._db.commit()
        return cur.rowcount > 0

    def mark_failed(self, record_id: int, error_msg: str) -> bool:
        """标记短信发送失败：status=failed, error_msg"""
        cur = self._db.execute(
            '''UPDATE sms_records
               SET status    = 'failed',
                   error_msg = ?
               WHERE id = ?''',
            (error_msg, record_id),
        )
        self._db.commit()
        return cur.rowcount > 0

    # ------------------------------------------------------------------ #
    #  查询操作                                                             #
    # ------------------------------------------------------------------ #

    def find_pending(self, limit: int = 100) -> List[SmsRecord]:
        """查询待发送短信，按创建时间升序"""
        rows = self._db.execute(
            'SELECT * FROM sms_records WHERE status = ? ORDER BY created_at ASC LIMIT ?',
            ('pending', limit),
        ).fetchall()
        return [SmsRecord.from_row(r) for r in rows]

    def find_by_phone(
        self,
        phone: str,
        page: int = 1,
        size: int = 20,
    ) -> Tuple[List[SmsRecord], int]:
        """
        按手机号分页查询短信记录。
        返回 (items, total)
        """
        total = self._scalar(
            'SELECT COUNT(*) FROM sms_records WHERE phone = ?',
            (phone,),
        ) or 0

        offset = (page - 1) * size
        rows = self._db.execute(
            'SELECT * FROM sms_records WHERE phone = ? ORDER BY id DESC LIMIT ? OFFSET ?',
            (phone, size, offset),
        ).fetchall()
        items = [SmsRecord.from_row(r) for r in rows]
        return items, total

    def find_failed_for_retry(self, max_retry: int = 3) -> List[SmsRecord]:
        """
        查询需要重试的失败短信记录（status=failed）。
        注：sms_records 表不维护 retry_count，仅按 status=failed 过滤。
        max_retry 参数保留接口兼容，不参与实际过滤。
        """
        return self._fetchall(
            "SELECT * FROM sms_records WHERE status = 'failed' ORDER BY created_at ASC",
        )
