"""
通知模板 Repository
继承 BaseRepository[NotificationTemplate]，提供 notification_templates 表完整操作。
"""
from __future__ import annotations

from typing import Dict, List, Optional

from ...common.base_repository import BaseRepository
from ...common.db import Database
from .models import NotificationTemplate


class TemplateRepository(BaseRepository[NotificationTemplate]):
    """notification_templates 表的数据访问层"""

    def __init__(self, db: Database):
        super().__init__(db)

    # ------------------------------------------------------------------ #
    #  BaseRepository 抽象方法实现                                          #
    # ------------------------------------------------------------------ #

    @property
    def table(self) -> str:
        return 'notification_templates'

    def _from_row(self, row) -> NotificationTemplate:
        return NotificationTemplate.from_row(row)

    # ------------------------------------------------------------------ #
    #  写操作                                                               #
    # ------------------------------------------------------------------ #

    def add(self, template: NotificationTemplate) -> NotificationTemplate:
        """新增通知模板"""
        sql = '''
            INSERT INTO notification_templates
                (tenant_id, code, name, channel, title_template,
                 content_template, variables, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        '''
        with self._db.transaction():
            cur = self._db.execute(sql, (
                template.tenant_id,
                template.code,
                template.name,
                template.channel,
                template.title_template,
                template.content_template,
                template.variables,
                template.status,
            ))
            template.id = cur.lastrowid
        return template

    def update_status(self, template_id: int, status: str) -> bool:
        """更新模板状态（active / inactive）"""
        cur = self._db.execute(
            'UPDATE notification_templates SET status = ? WHERE id = ?',
            (status, template_id),
        )
        self._db.commit()
        return cur.rowcount > 0

    # ------------------------------------------------------------------ #
    #  查询操作                                                             #
    # ------------------------------------------------------------------ #

    def find_by_code(self, code: str) -> Optional[NotificationTemplate]:
        """按模板编码查询（全局唯一）"""
        return self._fetchone(
            'SELECT * FROM notification_templates WHERE code = ?',
            (code,),
        )

    def find_by_channel(self, channel: str) -> List[NotificationTemplate]:
        """按渠道查询模板列表（sms / email / internal）"""
        return self._fetchall(
            'SELECT * FROM notification_templates WHERE channel = ? ORDER BY id',
            (channel,),
        )

    def find_by_tenant(self, tenant_id: int) -> List[NotificationTemplate]:
        """按租户查询模板列表"""
        return self._fetchall(
            'SELECT * FROM notification_templates WHERE tenant_id = ? ORDER BY id',
            (tenant_id,),
        )

    # ------------------------------------------------------------------ #
    #  渲染                                                                 #
    # ------------------------------------------------------------------ #

    def render(self, template_id: int, variables: Dict[str, str]) -> Dict[str, str]:
        """
        渲染模板，将 {{variable_name}} 替换为对应变量值。
        返回 {"title": ..., "content": ...}。
        如果模板不存在，返回空字典。
        """
        template = self.find_by_id(template_id)
        if template is None:
            return {}

        title = template.title_template or ''
        content = template.content_template or ''

        for key, value in variables.items():
            placeholder = '{{' + key + '}}'
            title = title.replace(placeholder, str(value))
            content = content.replace(placeholder, str(value))

        return {'title': title, 'content': content}
