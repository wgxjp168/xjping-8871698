"""
L4 基础设施客户端包
包含所有外部存储/中间件的封装：
  - RedisClient     : 会话缓存 / 热点数据 / 限流 / 分布式锁
  - ESClient        : Elasticsearch 商品检索 / 行为日志分析
  - MinioClient     : 对象存储（报告 / 图片 / 合同）
  - ClickHouseClient: OLAP 行为日志写入与查询
  - RabbitMQClient  : 异步任务 / 数据同步消息队列
"""
from .redis_client import RedisClient
from .es_client import ESClient
from .minio_client import MinioClient
from .clickhouse_client import ClickHouseClient
from .mq_client import RabbitMQClient

__all__ = [
    'RedisClient',
    'ESClient',
    'MinioClient',
    'ClickHouseClient',
    'RabbitMQClient',
]
