"""
ClickHouse OLAP 客户端封装
职责：存储用户行为、点击、购买、反馈等日志，用于 BI 分析与模型训练
设计要点：
  - 行为日志表使用 MergeTree 引擎
  - 按日期（toYYYYMMDD(occurred_at)）分区
  - 批量写入（默认 1000 条/批），降低写入频率
  - DDL 建表语句内置，服务启动时自动初始化
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

try:
    import clickhouse_connect
    _CH_AVAILABLE = True
except ImportError:  # pragma: no cover
    _CH_AVAILABLE = False

from ..config.settings import Settings

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------ #
#  DDL：用户行为日志表                                                  #
# ------------------------------------------------------------------ #
DDL_USER_BEHAVIOR_LOG = """
CREATE TABLE IF NOT EXISTS {db}.user_behavior_log
(
    event_id     UUID          DEFAULT generateUUIDv4(),
    user_id      Int64,
    tenant_id    Int64,
    event_type   LowCardinality(String),  -- click/add_cart/order/search/feedback
    product_id   Nullable(Int64),
    category_id  Nullable(Int32),
    keyword      Nullable(String),
    order_id     Nullable(Int64),
    amount       Nullable(Decimal(18,2)),
    ip           Nullable(IPv4),
    ua           Nullable(String),
    occurred_at  DateTime64(3, 'Asia/Shanghai'),
    dt           Date MATERIALIZED toDate(occurred_at)
)
ENGINE = MergeTree()
PARTITION BY toYYYYMMDD(occurred_at)
ORDER BY (tenant_id, user_id, occurred_at)
TTL occurred_at + INTERVAL 365 DAY
SETTINGS index_granularity = 8192;
"""

# ------------------------------------------------------------------ #
#  DDL：订单事件日志表                                                  #
# ------------------------------------------------------------------ #
DDL_ORDER_EVENT_LOG = """
CREATE TABLE IF NOT EXISTS {db}.order_event_log
(
    event_id    UUID          DEFAULT generateUUIDv4(),
    order_id    Int64,
    user_id     Int64,
    tenant_id   Int64,
    event_type  LowCardinality(String),  -- created/paid/shipped/completed/cancelled/refunded
    amount      Nullable(Decimal(18,2)),
    item_count  Nullable(Int32),
    remark      Nullable(String),
    occurred_at DateTime64(3, 'Asia/Shanghai'),
    dt          Date MATERIALIZED toDate(occurred_at)
)
ENGINE = MergeTree()
PARTITION BY toYYYYMMDD(occurred_at)
ORDER BY (tenant_id, order_id, occurred_at)
TTL occurred_at + INTERVAL 730 DAY
SETTINGS index_granularity = 8192;
"""


class ClickHouseClient:
    """
    ClickHouse HTTP 协议客户端（clickhouse-connect），惰性初始化。
    不可用时降级：写入方法返回 False，查询方法返回空结果。
    """

    def __init__(self, settings: Optional[Settings] = None):
        self._cfg = settings or Settings()
        self._client: Optional[Any] = None

    # ------------------------------------------------------------------ #
    #  连接管理                                                            #
    # ------------------------------------------------------------------ #

    def _get_client(self):
        if self._client is not None:
            return self._client
        if not _CH_AVAILABLE:
            logger.warning('clickhouse-connect 未安装，ClickHouse 功能不可用')
            return None
        try:
            self._client = clickhouse_connect.get_client(
                host=self._cfg.clickhouse_host,
                port=self._cfg.clickhouse_http_port,
                username=self._cfg.clickhouse_user,
                password=self._cfg.clickhouse_password,
                database=self._cfg.clickhouse_database,
                connect_timeout=10,
                send_receive_timeout=60,
            )
            logger.info('ClickHouse 连接成功: %s:%d/%s',
                        self._cfg.clickhouse_host,
                        self._cfg.clickhouse_http_port,
                        self._cfg.clickhouse_database)
        except Exception as exc:
            logger.error('ClickHouse 连接失败: %s', exc)
            self._client = None
        return self._client

    def ping(self) -> bool:
        c = self._get_client()
        try:
            return bool(c and c.ping())
        except Exception:
            return False

    # ------------------------------------------------------------------ #
    #  初始化：建库建表                                                     #
    # ------------------------------------------------------------------ #

    def init_schema(self) -> bool:
        """
        自动创建数据库和两张核心日志表（幂等操作）。
        """
        c = self._get_client()
        if not c:
            return False
        db = self._cfg.clickhouse_database
        try:
            # 建库
            c.command(f'CREATE DATABASE IF NOT EXISTS {db}')
            # 建表
            c.command(DDL_USER_BEHAVIOR_LOG.format(db=db))
            c.command(DDL_ORDER_EVENT_LOG.format(db=db))
            logger.info('ClickHouse Schema 初始化完成 (db=%s)', db)
            return True
        except Exception as exc:
            logger.error('init_schema 失败: %s', exc)
            return False

    # ------------------------------------------------------------------ #
    #  写入：用户行为日志                                                   #
    # ------------------------------------------------------------------ #

    def insert_behavior(self, event: Dict[str, Any]) -> bool:
        """写入单条行为日志。生产环境建议使用 bulk_insert_behaviors 批量写入。"""
        return self.bulk_insert_behaviors([event])

    def bulk_insert_behaviors(self, events: List[Dict[str, Any]]) -> bool:
        """
        批量写入用户行为日志。
        events 字段：user_id, tenant_id, event_type, occurred_at（必填）
                      product_id, category_id, keyword, order_id, amount, ip, ua（可选）
        """
        c = self._get_client()
        if not c or not events:
            return False
        columns = [
            'user_id', 'tenant_id', 'event_type', 'product_id',
            'category_id', 'keyword', 'order_id', 'amount', 'ip', 'ua', 'occurred_at',
        ]
        rows = []
        for ev in events:
            rows.append([
                ev.get('user_id'),
                ev.get('tenant_id'),
                ev.get('event_type', 'unknown'),
                ev.get('product_id'),
                ev.get('category_id'),
                ev.get('keyword'),
                ev.get('order_id'),
                ev.get('amount'),
                ev.get('ip'),
                ev.get('ua'),
                ev.get('occurred_at', datetime.now()),
            ])
        table = f"{self._cfg.clickhouse_database}.{self._cfg.clickhouse_table_behavior}"
        try:
            c.insert(table, rows, column_names=columns)
            logger.debug('bulk_insert_behaviors: %d 条写入 %s', len(rows), table)
            return True
        except Exception as exc:
            logger.error('bulk_insert_behaviors 失败: %s', exc)
            return False

    # ------------------------------------------------------------------ #
    #  写入：订单事件日志                                                   #
    # ------------------------------------------------------------------ #

    def insert_order_event(self, event: Dict[str, Any]) -> bool:
        """写入单条订单事件。"""
        return self.bulk_insert_order_events([event])

    def bulk_insert_order_events(self, events: List[Dict[str, Any]]) -> bool:
        """批量写入订单事件日志。"""
        c = self._get_client()
        if not c or not events:
            return False
        columns = ['order_id', 'user_id', 'tenant_id', 'event_type',
                   'amount', 'item_count', 'remark', 'occurred_at']
        rows = [
            [
                ev.get('order_id'),
                ev.get('user_id'),
                ev.get('tenant_id'),
                ev.get('event_type', 'unknown'),
                ev.get('amount'),
                ev.get('item_count'),
                ev.get('remark'),
                ev.get('occurred_at', datetime.now()),
            ]
            for ev in events
        ]
        table = f"{self._cfg.clickhouse_database}.{self._cfg.clickhouse_table_order_log}"
        try:
            c.insert(table, rows, column_names=columns)
            return True
        except Exception as exc:
            logger.error('bulk_insert_order_events 失败: %s', exc)
            return False

    # ------------------------------------------------------------------ #
    #  查询：BI 分析                                                        #
    # ------------------------------------------------------------------ #

    def query_event_stats(self, tenant_id: int,
                          start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """
        按事件类型统计 PV 和 UV（每日聚合）。
        返回 [{'dt': date, 'event_type': str, 'pv': int, 'uv': int}, ...]
        """
        c = self._get_client()
        if not c:
            return []
        sql = """
            SELECT
                dt,
                event_type,
                count()        AS pv,
                uniq(user_id)  AS uv
            FROM {db}.{table}
            WHERE tenant_id = {tenant_id}
              AND dt >= '{start_date}'
              AND dt <= '{end_date}'
            GROUP BY dt, event_type
            ORDER BY dt ASC, event_type ASC
        """.format(
            db=self._cfg.clickhouse_database,
            table=self._cfg.clickhouse_table_behavior,
            tenant_id=tenant_id,
            start_date=start_date,
            end_date=end_date,
        )
        try:
            result = c.query(sql)
            return [
                {'dt': str(row[0]), 'event_type': row[1], 'pv': row[2], 'uv': row[3]}
                for row in result.result_rows
            ]
        except Exception as exc:
            logger.error('query_event_stats 失败: %s', exc)
            return []

    def query_top_products(self, tenant_id: int,
                           event_type: str = 'order',
                           start_date: str = '', end_date: str = '',
                           top_n: int = 20) -> List[Dict[str, Any]]:
        """
        查询指定事件类型下的热门商品 Top-N（按事件数排序）。
        """
        c = self._get_client()
        if not c:
            return []
        date_filter = ''
        if start_date:
            date_filter += f" AND dt >= '{start_date}'"
        if end_date:
            date_filter += f" AND dt <= '{end_date}'"
        sql = """
            SELECT
                product_id,
                count() AS cnt
            FROM {db}.{table}
            WHERE tenant_id = {tenant_id}
              AND event_type = '{event_type}'
              AND product_id IS NOT NULL
              {date_filter}
            GROUP BY product_id
            ORDER BY cnt DESC
            LIMIT {top_n}
        """.format(
            db=self._cfg.clickhouse_database,
            table=self._cfg.clickhouse_table_behavior,
            tenant_id=tenant_id,
            event_type=event_type,
            date_filter=date_filter,
            top_n=top_n,
        )
        try:
            result = c.query(sql)
            return [{'product_id': row[0], 'count': row[1]} for row in result.result_rows]
        except Exception as exc:
            logger.error('query_top_products 失败: %s', exc)
            return []

    def query_order_funnel(self, tenant_id: int,
                           start_date: str, end_date: str) -> Dict[str, int]:
        """
        订单漏斗分析：各阶段 UV。
        返回 {'created': N, 'paid': N, 'completed': N, 'cancelled': N}
        """
        c = self._get_client()
        if not c:
            return {}
        sql = """
            SELECT
                event_type,
                uniq(order_id) AS cnt
            FROM {db}.{table}
            WHERE tenant_id = {tenant_id}
              AND dt >= '{start_date}'
              AND dt <= '{end_date}'
            GROUP BY event_type
        """.format(
            db=self._cfg.clickhouse_database,
            table=self._cfg.clickhouse_table_order_log,
            tenant_id=tenant_id,
            start_date=start_date,
            end_date=end_date,
        )
        try:
            result = c.query(sql)
            return {row[0]: row[1] for row in result.result_rows}
        except Exception as exc:
            logger.error('query_order_funnel 失败: %s', exc)
            return {}
