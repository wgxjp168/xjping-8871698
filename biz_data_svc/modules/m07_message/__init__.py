"""
消息通知模块（m07_message）
导出所有领域模型和 Repository 类。
"""
from .models import NotificationTemplate, InternalMessage, SmsRecord, EmailRecord
from .template_repository import TemplateRepository
from .message_repository import MessageRepository
from .sms_repository import SmsRepository
from .email_repository import EmailRepository

__all__ = [
    'NotificationTemplate',
    'InternalMessage',
    'SmsRecord',
    'EmailRecord',
    'TemplateRepository',
    'MessageRepository',
    'SmsRepository',
    'EmailRepository',
]
