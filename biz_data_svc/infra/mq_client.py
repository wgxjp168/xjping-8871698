"""
RabbitMQ 3.12 消息队列客户端封装
职责：
  1. 异步任务：报告生成（q.report.generate）、通知发送（q.notify.send）
  2. 数据同步：MySQL -> ES（q.sync.elasticsearch）、MySQL -> ClickHouse（q.sync.clickhouse）
设计要点：
  - 持久化队列（durable=True）+ 持久化消息（delivery_mode=2）
  - 消息确认机制（manual ack），防止消费失败导致数据丢失
  - 死信队列（DLX）+ 重试延迟队列（retry delay）
  - Topic Exchange 路由，按 routing_key 灵活分发
"""
from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Any, Callable, Dict, Optional

try:
    import pika
    from pika.exceptions import AMQPConnectionError, AMQPChannelError
    _PIKA_AVAILABLE = True
except ImportError:  # pragma: no cover
    _PIKA_AVAILABLE = False

from ..config.settings import Settings

logger = logging.getLogger(__name__)


class RabbitMQClient:
    """
    RabbitMQ 生产者 + 消费者封装，惰性连接。
    不可用时降级：publish 返回 False，subscribe 直接跳过。
    """

    def __init__(self, settings: Optional[Settings] = None):
        self._cfg = settings or Settings()
        self._connection: Optional[Any] = None
        self._channel: Optional[Any] = None

    # ------------------------------------------------------------------ #
    #  连接管理                                                            #
    # ------------------------------------------------------------------ #

    def _get_channel(self, force_reconnect: bool = False):
        """获取可用 Channel，连接断开时自动重连一次。"""
        if not _PIKA_AVAILABLE:
            logger.warning('pika 未安装，RabbitMQ 功能不可用')
            return None
        if force_reconnect or self._connection is None or self._connection.is_closed:
            self._connect()
        if self._channel is None or self._channel.is_closed:
            try:
                self._channel = self._connection.channel()
                self._setup_infrastructure(self._channel)
            except Exception as exc:
                logger.error('创建 Channel 失败: %s', exc)
                return None
        return self._channel

    def _connect(self):
        """建立 AMQP 连接。"""
        params = pika.ConnectionParameters(
            host=self._cfg.rabbitmq_host,
            port=self._cfg.rabbitmq_port,
            virtual_host=self._cfg.rabbitmq_vhost,
            credentials=pika.PlainCredentials(
                self._cfg.rabbitmq_user,
                self._cfg.rabbitmq_password,
            ),
            heartbeat=60,
            blocked_connection_timeout=300,
            connection_attempts=3,
            retry_delay=2,
        )
        try:
            self._connection = pika.BlockingConnection(params)
            logger.info('RabbitMQ 连接成功: %s:%d%s',
                        self._cfg.rabbitmq_host,
                        self._cfg.rabbitmq_port,
                        self._cfg.rabbitmq_vhost)
        except AMQPConnectionError as exc:
            logger.error('RabbitMQ 连接失败: %s', exc)
            self._connection = None

    def _setup_infrastructure(self, ch):
        """
        声明 Exchange、Queue、绑定关系。
        幂等操作，可重复调用。
        """
        # --- 异步任务 Exchange ---
        ch.exchange_declare(
            exchange=self._cfg.rabbitmq_exchange_async,
            exchange_type='topic',
            durable=True,
        )
        # --- 数据同步 Exchange ---
        ch.exchange_declare(
            exchange=self._cfg.rabbitmq_exchange_sync,
            exchange_type='topic',
            durable=True,
        )
        # --- 死信 Exchange ---
        dlx_exchange = 'ilbuy.dlx'
        ch.exchange_declare(exchange=dlx_exchange, exchange_type='fanout', durable=True)
        dlq_name = 'q.dead_letter'
        ch.queue_declare(queue=dlq_name, durable=True)
        ch.queue_bind(queue=dlq_name, exchange=dlx_exchange)

        # --- 持久化队列声明 & 绑定 ---
        queue_bindings = [
            # (queue_name, exchange, routing_key)
            (self._cfg.rabbitmq_queue_report,  self._cfg.rabbitmq_exchange_async, 'report.generate'),
            (self._cfg.rabbitmq_queue_notify,  self._cfg.rabbitmq_exchange_async, 'notify.#'),
            (self._cfg.rabbitmq_queue_es_sync, self._cfg.rabbitmq_exchange_sync,  'sync.es.#'),
            (self._cfg.rabbitmq_queue_ch_sync, self._cfg.rabbitmq_exchange_sync,  'sync.ch.#'),
        ]
        for queue_name, exchange, routing_key in queue_bindings:
            ch.queue_declare(
                queue=queue_name,
                durable=True,
                arguments={
                    'x-dead-letter-exchange': dlx_exchange,
                    'x-message-ttl': 86400000,   # 消息最长存活 24 小时
                },
            )
            ch.queue_bind(queue=queue_name, exchange=exchange, routing_key=routing_key)

    def close(self):
        """关闭连接。"""
        try:
            if self._connection and not self._connection.is_closed:
                self._connection.close()
        except Exception:
            pass
        self._connection = None
        self._channel = None

    # ------------------------------------------------------------------ #
    #  生产者：发布消息                                                     #
    # ------------------------------------------------------------------ #

    def publish(self, exchange: str, routing_key: str,
                payload: Dict[str, Any],
                message_id: Optional[str] = None) -> bool:
        """
        发布持久化消息。
        payload 会被序列化为 JSON。
        返回 True 表示发布成功（publisher confirm 未启用，仅表示入队成功）。
        """
        ch = self._get_channel()
        if not ch:
            return False
        body = json.dumps(payload, ensure_ascii=False, default=str).encode('utf-8')
        props = pika.BasicProperties(
            content_type='application/json',
            delivery_mode=2,    # 持久化消息
            message_id=message_id or str(uuid.uuid4()),
        )
        try:
            ch.basic_publish(
                exchange=exchange,
                routing_key=routing_key,
                body=body,
                properties=props,
                mandatory=False,
            )
            logger.debug('publish: exchange=%s rk=%s', exchange, routing_key)
            return True
        except (AMQPChannelError, Exception) as exc:
            logger.error('publish 失败: %s', exc)
            # 尝试重连后再发一次
            ch = self._get_channel(force_reconnect=True)
            if not ch:
                return False
            try:
                ch.basic_publish(exchange=exchange, routing_key=routing_key,
                                 body=body, properties=props)
                return True
            except Exception as exc2:
                logger.error('publish 重试失败: %s', exc2)
                return False

    # ------------------------------------------------------------------ #
    #  业务快捷方法：异步任务                                               #
    # ------------------------------------------------------------------ #

    def publish_report_task(self, report_id: str, report_type: str,
                            params: Dict[str, Any]) -> bool:
        """发布报告生成任务。"""
        return self.publish(
            exchange=self._cfg.rabbitmq_exchange_async,
            routing_key='report.generate',
            payload={
                'report_id':   report_id,
                'report_type': report_type,
                'params':      params,
            },
        )

    def publish_notify_task(self, channel: str, recipients: list,
                            template_code: str, variables: Dict) -> bool:
        """
        发布通知发送任务。
        channel: sms | email | push
        """
        return self.publish(
            exchange=self._cfg.rabbitmq_exchange_async,
            routing_key=f'notify.{channel}',
            payload={
                'channel':       channel,
                'recipients':    recipients,
                'template_code': template_code,
                'variables':     variables,
            },
        )

    # ------------------------------------------------------------------ #
    #  业务快捷方法：数据同步                                               #
    # ------------------------------------------------------------------ #

    def publish_es_sync(self, table: str, operation: str,
                        data: Dict[str, Any]) -> bool:
        """
        发布 MySQL -> ES 同步消息。
        operation: INSERT | UPDATE | DELETE
        """
        return self.publish(
            exchange=self._cfg.rabbitmq_exchange_sync,
            routing_key=f'sync.es.{table}',
            payload={
                'table':     table,
                'operation': operation,
                'data':      data,
            },
        )

    def publish_ch_sync(self, table: str, operation: str,
                        data: Dict[str, Any]) -> bool:
        """发布 MySQL -> ClickHouse 同步消息。"""
        return self.publish(
            exchange=self._cfg.rabbitmq_exchange_sync,
            routing_key=f'sync.ch.{table}',
            payload={
                'table':     table,
                'operation': operation,
                'data':      data,
            },
        )

    # ------------------------------------------------------------------ #
    #  消费者                                                              #
    # ------------------------------------------------------------------ #

    def subscribe(self, queue: str,
                  handler: Callable[[Dict[str, Any]], bool],
                  prefetch_count: int = 10) -> None:
        """
        阻塞式消费指定队列。
        handler 返回 True 表示处理成功（ack），False 表示失败（nack + 重入队）。
        使用 Ctrl+C 停止。
        """
        ch = self._get_channel()
        if not ch:
            logger.error('subscribe: 无法获取 Channel，跳过消费 queue=%s', queue)
            return

        ch.basic_qos(prefetch_count=prefetch_count)

        def _callback(ch, method, properties, body):
            try:
                payload = json.loads(body.decode('utf-8'))
                success = handler(payload)
                if success:
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                else:
                    # 失败重入队一次，再次失败进死信队列
                    redelivered = method.redelivered
                    ch.basic_nack(
                        delivery_tag=method.delivery_tag,
                        requeue=not redelivered,
                    )
            except (json.JSONDecodeError, Exception) as exc:
                logger.error('subscribe handler 异常: %s', exc)
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

        ch.basic_consume(queue=queue, on_message_callback=_callback, auto_ack=False)
        logger.info('开始消费队列: %s', queue)
        try:
            ch.start_consuming()
        except KeyboardInterrupt:
            ch.stop_consuming()
            logger.info('消费者已停止: %s', queue)
