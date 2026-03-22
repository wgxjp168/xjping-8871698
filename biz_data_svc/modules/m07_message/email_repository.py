"""
邮件记录 Repository
继承 BaseRepository[EmailRecord]，提供 email_records 表完整操作。
"""
from __future__ import annotations

from typing import List, Tuple

from ...common.base_repository import BaseRepository
from ...common.db import Database
from .models import EmailRecord


class EmailRepository(BaseRepository[EmailRecord]):
    """email_records 表的数据访问层"""

    def __init__(self, db: Database):
        super().__init__(db)

    # ------------------------------------------------------------------ #
    #  BaseRepository 抽象方法实现                                          #
    # ------------------------------------------------------------------ #

    @property
    def table(self) -> str:
        return 'email_records'

    def _from_row(self, row) -> EmailRecord:
        return EmailRecord.from_row(row)

    # ------------------------------------------------------------------ #
    #  写操作                                                               #
    # ------------------------------------------------------------------ #

    def create(self, record: EmailRecord) -> EmailRecord:
        """创建邮件发送记录（初始 status=pending）"""
        sql = '''
            INSERT INTO email_records
                (tenant_id, to_email, cc_emails, bcc_emails, subject,
                 body, body_type, template_code, attachments,
                 status, error_msg, retry_count, sent_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        '''
        with self._db.transaction():
            cur = self._db.execute(sql, (
                record.tenant_id,
                record.to_email,
                record.cc_emails,
                record.bcc_emails,
                record.subject,
                record.body,
                record.body_type,
                record.template_code,
                record.attachments,
                record.status,
                record.error_msg,
                record.retry_count,
                record.sent_at,
            ))
            record.id = cur.lastrowid
        return record

    def mark_sent(self, record_id: int) -> bool:
        """标记邮件已发送：status=sent, sent_at=now"""
        cur = self._db.execute(
            '''UPDATE email_records
               SET status  = 'sent',
                   sent_at = CURRENT_TIMESTAMP
               WHERE id = ?''',
            (record_id,),
        )
        self._db.commit()
        return cur.rowcount > 0

    def mark_failed(self, record_id: int, error_msg: str) -> bool:
        """标记邮件发送失败：status=failed, error_msg, retry_count+=1"""
        cur = self._db.execute(
            '''UPDATE email_records
               SET status      = 'failed',
                   error_msg   = ?,
                   retry_count = retry_count + 1
               WHERE id = ?''',
            (error_msg, record_id),
        )
        self._db.commit()
        return cur.rowcount > 0

    def mark_bounced(self, record_id: int) -> bool:
        """标记邮件退信：status=bounced"""
        cur = self._db.execute(
            "UPDATE email_records SET status = 'bounced' WHERE id = ?",
            (record_id,),
        )
        self._db.commit()
        return cur.rowcount > 0

    # ------------------------------------------------------------------ #
    #  查询操作                                                             #
    # ------------------------------------------------------------------ #

    def find_pending(self, limit: int = 100) -> List[EmailRecord]:
        """查询待发送邮件，按创建时间升序"""
        rows = self._db.execute(
            'SELECT * FROM email_records WHERE status = ? ORDER BY created_at ASC LIMIT ?',
            ('pending', limit),
        ).fetchall()
        return [EmailRecord.from_row(r) for r in rows]

    def find_for_retry(self, max_retry: int = 3) -> List[EmailRecord]:
        """查询需要重试的失败邮件（status=failed AND retry_count < max_retry）"""
        rows = self._db.execute(
            '''SELECT * FROM email_records
               WHERE status = 'failed' AND retry_count < ?
               ORDER BY created_at ASC''',
            (max_retry,),
        ).fetchall()
        return [EmailRecord.from_row(r) for r in rows]

    def find_by_email(
        self,
        to_email: str,
        page: int = 1,
        size: int = 20,
    ) -> Tuple[List[EmailRecord], int]:
        """
        按收件人邮箱分页查询邮件记录。
        返回 (items, total)
        """
        total = self._scalar(
            'SELECT COUNT(*) FROM email_records WHERE to_email = ?',
            (to_email,),
        ) or 0

        offset = (page - 1) * size
        rows = self._db.execute(
            'SELECT * FROM email_records WHERE to_email = ? ORDER BY id DESC LIMIT ? OFFSET ?',
            (to_email, size, offset),
        ).fetchall()
        items = [EmailRecord.from_row(r) for r in rows]
        return items, total
