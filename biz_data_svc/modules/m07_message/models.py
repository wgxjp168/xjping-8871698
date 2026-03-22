"""
消息通知模块 — 领域模型
所有模型均为 dataclass，提供 to_dict() 和 from_row() 方法。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


# --------------------------------------------------------------------------- #
#  NotificationTemplate                                                        #
# --------------------------------------------------------------------------- #

@dataclass
class NotificationTemplate:
    """消息通知模板"""
    tenant_id: int
    code: str
    name: str
    channel: str              # sms / email / internal
    content_template: str
    id: Optional[int] = None
    title_template: Optional[str] = None
    variables: Optional[str] = None  # JSON 字符串，描述模板变量列表
    status: str = 'active'            # active / inactive
    created_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'code': self.code,
            'name': self.name,
            'channel': self.channel,
            'title_template': self.title_template,
            'content_template': self.content_template,
            'variables': self.variables,
            'status': self.status,
            'created_at': self.created_at,
        }

    @staticmethod
    def from_row(row) -> 'NotificationTemplate':
        """
        列顺序：id, tenant_id, code, name, channel, title_template,
                content_template, variables, status, created_at
        """
        r = tuple(row)
        return NotificationTemplate(
            id=r[0],
            tenant_id=r[1],
            code=r[2],
            name=r[3],
            channel=r[4],
            title_template=r[5],
            content_template=r[6],
            variables=r[7],
            status=r[8],
            created_at=r[9],
        )


# --------------------------------------------------------------------------- #
#  InternalMessage                                                             #
# --------------------------------------------------------------------------- #

@dataclass
class InternalMessage:
    """站内消息"""
    tenant_id: int
    receiver_id: int
    msg_type: str             # system / notify / alert / business
    title: str
    content: str
    id: Optional[int] = None
    sender_id: Optional[int] = None
    biz_type: Optional[str] = None
    biz_id: Optional[int] = None
    action_url: Optional[str] = None
    is_read: int = 0
    read_at: Optional[str] = None
    created_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'sender_id': self.sender_id,
            'receiver_id': self.receiver_id,
            'msg_type': self.msg_type,
            'title': self.title,
            'content': self.content,
            'biz_type': self.biz_type,
            'biz_id': self.biz_id,
            'action_url': self.action_url,
            'is_read': self.is_read,
            'read_at': self.read_at,
            'created_at': self.created_at,
        }

    @staticmethod
    def from_row(row) -> 'InternalMessage':
        """
        列顺序：id, tenant_id, sender_id, receiver_id, msg_type,
                title, content, biz_type, biz_id, action_url,
                is_read, read_at, created_at
        """
        r = tuple(row)
        return InternalMessage(
            id=r[0],
            tenant_id=r[1],
            sender_id=r[2],
            receiver_id=r[3],
            msg_type=r[4],
            title=r[5],
            content=r[6],
            biz_type=r[7],
            biz_id=r[8],
            action_url=r[9],
            is_read=r[10],
            read_at=r[11],
            created_at=r[12],
        )


# --------------------------------------------------------------------------- #
#  SmsRecord                                                                   #
# --------------------------------------------------------------------------- #

@dataclass
class SmsRecord:
    """短信发送记录"""
    tenant_id: int
    phone: str
    content: str
    id: Optional[int] = None
    template_code: Optional[str] = None
    params: Optional[str] = None        # JSON 字符串，模板变量
    status: str = 'pending'             # pending / sent / delivered / failed
    provider: Optional[str] = None
    provider_msg_id: Optional[str] = None
    error_msg: Optional[str] = None
    sent_at: Optional[str] = None
    created_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'phone': self.phone,
            'template_code': self.template_code,
            'params': self.params,
            'content': self.content,
            'status': self.status,
            'provider': self.provider,
            'provider_msg_id': self.provider_msg_id,
            'error_msg': self.error_msg,
            'sent_at': self.sent_at,
            'created_at': self.created_at,
        }

    @staticmethod
    def from_row(row) -> 'SmsRecord':
        """
        列顺序：id, tenant_id, phone, template_code, params, content,
                status, provider, provider_msg_id, error_msg, sent_at, created_at
        """
        r = tuple(row)
        return SmsRecord(
            id=r[0],
            tenant_id=r[1],
            phone=r[2],
            template_code=r[3],
            params=r[4],
            content=r[5],
            status=r[6],
            provider=r[7],
            provider_msg_id=r[8],
            error_msg=r[9],
            sent_at=r[10],
            created_at=r[11],
        )


# --------------------------------------------------------------------------- #
#  EmailRecord                                                                 #
# --------------------------------------------------------------------------- #

@dataclass
class EmailRecord:
    """邮件发送记录"""
    tenant_id: int
    to_email: str
    subject: str
    body: str
    id: Optional[int] = None
    cc_emails: Optional[str] = None     # 逗号分隔或 JSON
    bcc_emails: Optional[str] = None
    body_type: str = 'html'             # html / text
    template_code: Optional[str] = None
    attachments: Optional[str] = None   # JSON 字符串，附件列表
    status: str = 'pending'             # pending / sent / failed / bounced
    error_msg: Optional[str] = None
    retry_count: int = 0
    sent_at: Optional[str] = None
    created_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'to_email': self.to_email,
            'cc_emails': self.cc_emails,
            'bcc_emails': self.bcc_emails,
            'subject': self.subject,
            'body': self.body,
            'body_type': self.body_type,
            'template_code': self.template_code,
            'attachments': self.attachments,
            'status': self.status,
            'error_msg': self.error_msg,
            'retry_count': self.retry_count,
            'sent_at': self.sent_at,
            'created_at': self.created_at,
        }

    @staticmethod
    def from_row(row) -> 'EmailRecord':
        """
        列顺序：id, tenant_id, to_email, cc_emails, bcc_emails, subject,
                body, body_type, template_code, attachments, status,
                error_msg, retry_count, sent_at, created_at
        """
        r = tuple(row)
        return EmailRecord(
            id=r[0],
            tenant_id=r[1],
            to_email=r[2],
            cc_emails=r[3],
            bcc_emails=r[4],
            subject=r[5],
            body=r[6],
            body_type=r[7],
            template_code=r[8],
            attachments=r[9],
            status=r[10],
            error_msg=r[11],
            retry_count=r[12],
            sent_at=r[13],
            created_at=r[14],
        )
