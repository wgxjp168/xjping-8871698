"""
Canal Binlog 消费器
职责：
  监听 MySQL Binlog（通过 canal-python 客户端），将 INSERT/UPDATE/DELETE
  增量事件转发至 RabbitMQ，供下游 Flink 作业消费同步至 ES 和 ClickHouse。

设计要点：
  - 仅监听 canal_watch_tables 中配置的库表
  - 事件格式标准化后发布到 ilbuy.sync Exchange
  - 断线自动重连（指数退避，最多 5 次）
  - 支持批量拉取（batch_size）降低 RPC 次数
"""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

try:
    from canal.client import Client as CanalClient
    from canal.protocol import EntryProtocol_pb2 as EP
    _CANAL_AVAILABLE = True
except ImportError:  # pragma: no cover
    _CANAL_AVAILABLE = False

from ..config.settings import Settings
from ..infra.mq_client import RabbitMQClient

logger = logging.getLogger(__name__)

# Canal EntryType 过滤
_ROWDATA_ENTRY_TYPES = frozenset(['ROWDATA'])
# Binlog EventType 映射
_EVENT_MAP = {1: 'INSERT', 2: 'UPDATE', 3: 'DELETE'}


class CanalConsumer:
    """
    Canal Binlog 消费器。
    调用 start() 开始阻塞式消费；调用 stop() 优雅停止。
    """

    def __init__(self, settings: Optional[Settings] = None,
                 mq_client: Optional[RabbitMQClient] = None):
        self._cfg = settings or Settings()
        self._mq = mq_client or RabbitMQClient(self._cfg)
        self._running = False
        self._client: Optional[Any] = None

        # 构建 watch_set：{schema.table, ...}（全小写，便于匹配）
        self._watch_set = frozenset(
            t.lower() for t in self._cfg.canal_watch_tables
        )

    # ------------------------------------------------------------------ #
    #  连接管理                                                            #
    # ------------------------------------------------------------------ #

    def _connect(self) -> bool:
        """连接 Canal Server，失败返回 False。"""
        if not _CANAL_AVAILABLE:
            logger.warning('canal-python 未安装，Canal 功能不可用')
            return False
        try:
            self._client = CanalClient()
            self._client.connect(
                host=self._cfg.canal_host,
                port=self._cfg.canal_port,
            )
            self._client.check_valid(
                username=self._cfg.canal_username.encode(),
                password=self._cfg.canal_password.encode(),
            )
            self._client.subscribe(
                client_id=b'1001',
                destination=self._cfg.canal_destination.encode(),
                filter=b'.*\\..*',
            )
            logger.info('Canal 连接成功: %s:%d destination=%s',
                        self._cfg.canal_host,
                        self._cfg.canal_port,
                        self._cfg.canal_destination)
            return True
        except Exception as exc:
            logger.error('Canal 连接失败: %s', exc)
            return False

    def _disconnect(self):
        try:
            if self._client:
                self._client.disconnect()
        except Exception:
            pass
        self._client = None

    # ------------------------------------------------------------------ #
    #  事件处理                                                            #
    # ------------------------------------------------------------------ #

    def _is_watched(self, schema: str, table: str) -> bool:
        """判断当前 schema.table 是否在监听列表中。"""
        return f'{schema}.{table}'.lower() in self._watch_set

    def _parse_row(self, row_data, event_type: str) -> Dict[str, Any]:
        """
        将 Canal RowData 转化为标准字典。
        event_type: INSERT | UPDATE | DELETE
        """
        if event_type in ('INSERT', 'UPDATE'):
            cols = row_data.afterColumns
        else:
            cols = row_data.beforeColumns
        return {col.name: col.value for col in cols}

    def _dispatch_event(self, schema: str, table: str,
                        event_type: str, rows: List[Dict]) -> None:
        """
        将解析后的行数据发布到 RabbitMQ ilbuy.sync Exchange。
        """
        for row in rows:
            self._mq.publish_es_sync(
                table=f'{schema}.{table}',
                operation=event_type,
                data=row,
            )
            self._mq.publish_ch_sync(
                table=f'{schema}.{table}',
                operation=event_type,
                data=row,
            )

    def _process_message(self, message) -> int:
        """
        处理一批 Canal 消息，返回处理的 RowData 条数。
        """
        count = 0
        if not message or not message.entries:
            return 0

        for entry in message.entries:
            # 仅处理 ROWDATA 类型
            if entry.entryType not in (1, 2, 3):  # TRANSACTION_BEGIN=1, TRANSACTION_END=2, ROWDATA=3
                continue
            header = entry.header
            schema = header.schemaName
            table  = header.tableName

            if not self._is_watched(schema, table):
                continue

            try:
                row_change = EP.RowChange()
                row_change.ParseFromString(entry.storeValue)
            except Exception as exc:
                logger.warning('解析 RowChange 失败 %s.%s: %s', schema, table, exc)
                continue

            event_type = _EVENT_MAP.get(row_change.eventType, 'UNKNOWN')
            if event_type == 'UNKNOWN':
                continue

            rows = [self._parse_row(r, event_type) for r in row_change.rowDatas]
            if rows:
                self._dispatch_event(schema, table, event_type, rows)
                count += len(rows)
                logger.debug('Canal 同步: %s.%s %s %d 行', schema, table, event_type, len(rows))

        return count

    # ------------------------------------------------------------------ #
    #  主循环                                                              #
    # ------------------------------------------------------------------ #

    def start(self, batch_size: int = 100, pull_timeout_ms: int = 1000) -> None:
        """
        阻塞式启动消费循环，断线自动重连（指数退避，最多重试 5 次）。
        """
        self._running = True
        max_retries = 5
        retry = 0

        while self._running:
            if not self._connect():
                retry += 1
                if retry > max_retries:
                    logger.error('Canal 重连次数超限 (%d)，停止消费', max_retries)
                    break
                wait = min(2 ** retry, 60)
                logger.info('Canal 等待 %ds 后重连 (retry=%d)', wait, retry)
                time.sleep(wait)
                continue

            retry = 0   # 连接成功，重置重试计数
            logger.info('Canal 消费器启动，监听表: %s', list(self._watch_set))

            try:
                while self._running:
                    message = self._client.get(batch_size)
                    cnt = self._process_message(message)
                    if cnt == 0:
                        time.sleep(pull_timeout_ms / 1000.0)
            except KeyboardInterrupt:
                logger.info('Canal 消费器收到停止信号')
                self._running = False
            except Exception as exc:
                logger.error('Canal 消费循环异常，准备重连: %s', exc)
            finally:
                self._disconnect()

        logger.info('Canal 消费器已停止')

    def stop(self) -> None:
        """优雅停止消费循环。"""
        self._running = False
        self._disconnect()
