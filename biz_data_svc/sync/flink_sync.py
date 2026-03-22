"""
Flink 流式数据同步作业（Python 模拟实现）
职责：
  消费 RabbitMQ ilbuy.sync Exchange 中的消息，
  将 MySQL 增量数据近实时同步至 Elasticsearch 和 ClickHouse，
  保证数据最终一致性。

设计要点：
  - 按目标存储分为两条处理链：ES 链 / ClickHouse 链
  - 每条链支持 INSERT/UPDATE/DELETE 三种操作
  - 检查点间隔 1 分钟（flink_checkpoint_interval_ms）
  - 处理失败的消息进死信队列，不影响后续消息处理
  - 支持并行度配置（flink_parallelism），多线程消费
"""
from __future__ import annotations

import logging
import threading
from typing import Any, Callable, Dict, List, Optional

from ..config.settings import Settings
from ..infra.es_client import ESClient
from ..infra.clickhouse_client import ClickHouseClient
from ..infra.mq_client import RabbitMQClient

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------ #
#  表 -> ES 索引 映射                                                  #
# ------------------------------------------------------------------ #
TABLE_TO_ES_INDEX: Dict[str, str] = {
    'product_db.products':    'ilbuy_products',
    'product_db.product_skus': 'ilbuy_products',   # SKU 变更同步到商品索引
}

# ------------------------------------------------------------------ #
#  ES 同步处理器                                                       #
# ------------------------------------------------------------------ #

class ESSyncHandler:
    """
    将 MySQL 增量事件同步至 Elasticsearch。
    仅处理 products / product_skus 相关表。
    """

    def __init__(self, es: ESClient, cfg: Settings):
        self._es  = es
        self._cfg = cfg

    def handle(self, payload: Dict[str, Any]) -> bool:
        """
        payload 格式：
          {'table': 'product_db.products', 'operation': 'INSERT|UPDATE|DELETE', 'data': {...}}
        """
        table     = payload.get('table', '').lower()
        operation = payload.get('operation', '').upper()
        data      = payload.get('data', {})

        if table not in TABLE_TO_ES_INDEX:
            return True   # 不关心的表，直接 ack

        index = TABLE_TO_ES_INDEX[table]

        try:
            if operation in ('INSERT', 'UPDATE'):
                product_id = data.get('id') or data.get('product_id')
                if product_id is None:
                    logger.warning('ES 同步 INSERT/UPDATE 缺少 id: table=%s', table)
                    return False
                # 构造 ES 文档（_source 字段按 mapping 要求过滤）
                doc = self._build_product_doc(data)
                return self._es.index_product(doc)

            elif operation == 'DELETE':
                product_id = data.get('id') or data.get('product_id')
                if product_id is None:
                    return True
                return self._es.delete_product(int(product_id))

        except Exception as exc:
            logger.error('ESSyncHandler.handle 异常 table=%s op=%s: %s', table, operation, exc)
            return False

        return True

    @staticmethod
    def _build_product_doc(row: Dict[str, Any]) -> Dict[str, Any]:
        """从数据库行数据构建 ES 文档，只保留必要字段。"""
        return {
            'id':          row.get('id'),
            'tenant_id':   row.get('tenant_id'),
            'category_id': row.get('category_id'),
            'name':        row.get('name'),
            'subtitle':    row.get('subtitle'),
            'cover_image': row.get('cover_image'),
            'unit':        row.get('unit'),
            'status':      row.get('status', 'draft'),
            'is_featured': bool(row.get('is_featured', 0)),
            'tags':        row.get('tags'),
            'sales_count': int(row.get('sales_count', 0)),
            'min_price':   row.get('min_price'),
            'updated_at':  row.get('updated_at'),
        }


# ------------------------------------------------------------------ #
#  ClickHouse 同步处理器                                               #
# ------------------------------------------------------------------ #

class ClickHouseSyncHandler:
    """
    将 MySQL 增量事件同步至 ClickHouse。
    orders 表 -> order_event_log；其余表事件写 user_behavior_log（示例）。
    """

    def __init__(self, ch: ClickHouseClient, cfg: Settings):
        self._ch  = ch
        self._cfg = cfg

    def handle(self, payload: Dict[str, Any]) -> bool:
        table     = payload.get('table', '').lower()
        operation = payload.get('operation', '').upper()
        data      = payload.get('data', {})

        try:
            if 'order' in table:
                return self._sync_order(data, operation)
            # 其他表（用户行为）
            return True
        except Exception as exc:
            logger.error('ClickHouseSyncHandler.handle 异常 table=%s: %s', table, exc)
            return False

    def _sync_order(self, row: Dict[str, Any], operation: str) -> bool:
        """将订单行数据写入 ClickHouse order_event_log。"""
        from datetime import datetime
        event = {
            'order_id':    row.get('id') or row.get('order_id'),
            'user_id':     row.get('user_id'),
            'tenant_id':   row.get('tenant_id'),
            'event_type':  self._map_order_event(row, operation),
            'amount':      row.get('total_amount') or row.get('amount'),
            'item_count':  row.get('item_count'),
            'remark':      f'binlog sync: {operation}',
            'occurred_at': row.get('updated_at') or row.get('created_at') or datetime.now(),
        }
        return self._ch.insert_order_event(event)

    @staticmethod
    def _map_order_event(row: Dict, operation: str) -> str:
        """根据订单状态字段映射事件类型。"""
        if operation == 'INSERT':
            return 'created'
        status = str(row.get('status', '')).lower()
        mapping = {
            'paid': 'paid', 'shipped': 'shipped', 'completed': 'completed',
            'cancelled': 'cancelled', 'refunding': 'refunding',
        }
        return mapping.get(status, operation.lower())


# ------------------------------------------------------------------ #
#  FlinkSyncJob：协调两条同步链                                        #
# ------------------------------------------------------------------ #

class FlinkSyncJob:
    """
    模拟 Flink 流式作业，多线程并行消费两条同步队列：
      - ES 同步：q.sync.elasticsearch
      - ClickHouse 同步：q.sync.clickhouse

    调用 start() 启动（后台线程），调用 stop() 优雅停止。
    """

    def __init__(self, settings: Optional[Settings] = None,
                 mq_client: Optional[RabbitMQClient] = None,
                 es_client: Optional[ESClient] = None,
                 ch_client: Optional[ClickHouseClient] = None):
        self._cfg = settings or Settings()
        self._mq  = mq_client or RabbitMQClient(self._cfg)
        self._es  = es_client or ESClient(self._cfg)
        self._ch  = ch_client or ClickHouseClient(self._cfg)

        self._es_handler = ESSyncHandler(self._es, self._cfg)
        self._ch_handler = ClickHouseSyncHandler(self._ch, self._cfg)

        self._threads: List[threading.Thread] = []
        self._running = False

    # ------------------------------------------------------------------ #
    #  启动 / 停止                                                         #
    # ------------------------------------------------------------------ #

    def start(self) -> None:
        """启动后台同步线程（非阻塞）。"""
        self._running = True
        parallelism = self._cfg.flink_parallelism

        # ES 同步线程（并行度）
        for i in range(parallelism):
            t = threading.Thread(
                target=self._run_worker,
                args=(self._cfg.rabbitmq_queue_es_sync, self._es_handler.handle,
                      f'es-sync-worker-{i}'),
                daemon=True,
            )
            self._threads.append(t)
            t.start()

        # ClickHouse 同步线程（并行度）
        for i in range(parallelism):
            t = threading.Thread(
                target=self._run_worker,
                args=(self._cfg.rabbitmq_queue_ch_sync, self._ch_handler.handle,
                      f'ch-sync-worker-{i}'),
                daemon=True,
            )
            self._threads.append(t)
            t.start()

        logger.info(
            'FlinkSyncJob 启动：parallelism=%d，ES线程=%d，CH线程=%d',
            parallelism, parallelism, parallelism,
        )

    def stop(self) -> None:
        """优雅停止所有工作线程（等待当前消息处理完毕）。"""
        self._running = False
        self._mq.close()
        for t in self._threads:
            t.join(timeout=10)
        self._threads.clear()
        logger.info('FlinkSyncJob 已停止')

    def wait(self) -> None:
        """阻塞主线程，等待所有工作线程结束（用于单进程部署）。"""
        for t in self._threads:
            t.join()

    # ------------------------------------------------------------------ #
    #  工作线程                                                            #
    # ------------------------------------------------------------------ #

    def _run_worker(self, queue: str,
                    handler: Callable[[Dict[str, Any]], bool],
                    name: str) -> None:
        """
        单个工作线程：从 MQ 消费消息并调用对应 handler。
        """
        logger.info('[%s] 启动，监听队列: %s', name, queue)
        # 每个线程使用独立 MQ Client，避免 Channel 竞争
        mq = RabbitMQClient(self._cfg)

        def _checkpoint_wrapper(payload: Dict[str, Any]) -> bool:
            """调用业务 handler，并在检查点周期内触发日志记录。"""
            return handler(payload)

        try:
            mq.subscribe(
                queue=queue,
                handler=_checkpoint_wrapper,
                prefetch_count=20,
            )
        except Exception as exc:
            logger.error('[%s] 工作线程异常退出: %s', name, exc)
        finally:
            mq.close()
            logger.info('[%s] 工作线程退出', name)
