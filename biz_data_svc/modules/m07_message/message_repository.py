"""
站内消息 Repository
继承 BaseRepository[InternalMessage]，提供 internal_messages 表完整操作。
"""
from __future__ import annotations

from typing import List, Optional, Tuple

from ...common.base_repository import BaseRepository
from ...common.db import Database
from .models import InternalMessage


class MessageRepository(BaseRepository[InternalMessage]):
    """internal_messages 表的数据访问层"""

    def __init__(self, db: Database):
        super().__init__(db)

    # ------------------------------------------------------------------ #
    #  BaseRepository 抽象方法实现                                          #
    # ------------------------------------------------------------------ #

    @property
    def table(self) -> str:
        return 'internal_messages'

    def _from_row(self, row) -> InternalMessage:
        return InternalMessage.from_row(row)

    # ------------------------------------------------------------------ #
    #  写操作                                                               #
    # ------------------------------------------------------------------ #

    def send(self, message: InternalMessage) -> InternalMessage:
        """发送单条站内消息，插入记录并返回带 id 的对象"""
        sql = '''
            INSERT INTO internal_messages
                (tenant_id, sender_id, receiver_id, msg_type, title,
                 content, biz_type, biz_id, action_url, is_read)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        '''
        with self._db.transaction():
            cur = self._db.execute(sql, (
                message.tenant_id,
                message.sender_id,
                message.receiver_id,
                message.msg_type,
                message.title,
                message.content,
                message.biz_type,
                message.biz_id,
                message.action_url,
                message.is_read,
            ))
            message.id = cur.lastrowid
        return message

    def send_batch(self, messages: List[InternalMessage]) -> List[InternalMessage]:
        """
        批量发送站内消息，使用 executemany 提升性能。
        返回插入后带 id 的消息列表（id 通过重新查询末行推算）。
        """
        if not messages:
            return []

        sql = '''
            INSERT INTO internal_messages
                (tenant_id, sender_id, receiver_id, msg_type, title,
                 content, biz_type, biz_id, action_url, is_read)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        '''
        params_seq = [
            (
                msg.tenant_id,
                msg.sender_id,
                msg.receiver_id,
                msg.msg_type,
                msg.title,
                msg.content,
                msg.biz_type,
                msg.biz_id,
                msg.action_url,
                msg.is_read,
            )
            for msg in messages
        ]
        with self._db.transaction():
            self._db.executemany(sql, params_seq)
            last_id = self._db.execute('SELECT last_insert_rowid()').fetchone()[0]

        # 回填 id：批量插入后 last_insert_rowid 为最后一条记录的 id
        first_id = last_id - len(messages) + 1
        for idx, msg in enumerate(messages):
            msg.id = first_id + idx
        return messages

    def mark_read(self, message_id: int, receiver_id: int) -> bool:
        """将指定消息标记为已读（仅限接收人本人操作）"""
        cur = self._db.execute(
            '''UPDATE internal_messages
               SET is_read = 1,
                   read_at = CURRENT_TIMESTAMP
               WHERE id = ? AND receiver_id = ?''',
            (message_id, receiver_id),
        )
        self._db.commit()
        return cur.rowcount > 0

    def mark_all_read(self, receiver_id: int) -> int:
        """将接收人所有未读消息标记为已读，返回受影响行数"""
        cur = self._db.execute(
            '''UPDATE internal_messages
               SET is_read = 1,
                   read_at = CURRENT_TIMESTAMP
               WHERE receiver_id = ? AND is_read = 0''',
            (receiver_id,),
        )
        self._db.commit()
        return cur.rowcount

    def delete(self, message_id: int) -> bool:  # noqa: A002
        """删除指定消息"""
        cur = self._db.execute(
            'DELETE FROM internal_messages WHERE id = ?',
            (message_id,),
        )
        self._db.commit()
        return cur.rowcount > 0

    # ------------------------------------------------------------------ #
    #  查询操作                                                             #
    # ------------------------------------------------------------------ #

    def find_by_receiver(
        self,
        receiver_id: int,
        is_read: Optional[int] = None,
        page: int = 1,
        size: int = 20,
    ) -> Tuple[List[InternalMessage], int]:
        """
        分页查询接收人的消息列表。
        is_read: None=全部, 0=未读, 1=已读
        返回 (items, total)
        """
        where = 'receiver_id = ?'
        params: list = [receiver_id]
        if is_read is not None:
            where += ' AND is_read = ?'
            params.append(is_read)

        total = self._scalar(
            f'SELECT COUNT(*) FROM {self.table} WHERE {where}',
            tuple(params),
        ) or 0

        offset = (page - 1) * size
        rows = self._db.execute(
            f'SELECT * FROM {self.table} WHERE {where} ORDER BY id DESC LIMIT ? OFFSET ?',
            tuple(params) + (size, offset),
        ).fetchall()
        items = [InternalMessage.from_row(r) for r in rows]
        return items, total

    def find_by_biz(self, biz_type: str, biz_id: int) -> List[InternalMessage]:
        """按业务类型和业务 ID 查询相关消息"""
        return self._fetchall(
            'SELECT * FROM internal_messages WHERE biz_type = ? AND biz_id = ? ORDER BY id',
            (biz_type, biz_id),
        )

    def count_unread(self, receiver_id: int) -> int:
        """统计接收人未读消息数量"""
        result = self._scalar(
            'SELECT COUNT(*) FROM internal_messages WHERE receiver_id = ? AND is_read = 0',
            (receiver_id,),
        )
        return int(result or 0)
