"""
应用配置管理
支持从环境变量覆盖默认值
涵盖所有 L4 存储层组件：MySQL / Redis / Elasticsearch / MinIO / ClickHouse / RabbitMQ
"""
import os
from dataclasses import dataclass, field


@dataclass
class Settings:
    # ------------------------------------------------------------------ #
    #  关系型数据库 - MySQL 8.0 (主从集群)                                   #
    # ------------------------------------------------------------------ #
    db_path: str  = field(default_factory=lambda: os.getenv('DB_PATH', 'biz_mall.db'))
    db_echo: bool = field(default_factory=lambda: os.getenv('DB_ECHO', '0') == '1')

    # MySQL 主库
    mysql_host:     str = field(default_factory=lambda: os.getenv('MYSQL_HOST', '127.0.0.1'))
    mysql_port:     int = field(default_factory=lambda: int(os.getenv('MYSQL_PORT', '3306')))
    mysql_user:     str = field(default_factory=lambda: os.getenv('MYSQL_USER', 'root'))
    mysql_password: str = field(default_factory=lambda: os.getenv('MYSQL_PASSWORD', ''))
    mysql_charset:  str = 'utf8mb4'

    # MySQL 从库（读写分离）
    mysql_slave_host: str = field(default_factory=lambda: os.getenv('MYSQL_SLAVE_HOST', '127.0.0.1'))
    mysql_slave_port: int = field(default_factory=lambda: int(os.getenv('MYSQL_SLAVE_PORT', '3307')))

    # 分库配置（user_db / order_db / product_db）
    mysql_user_db:    str = 'user_db'
    mysql_order_db:   str = 'order_db'
    mysql_product_db: str = 'product_db'

    # ------------------------------------------------------------------ #
    #  缓存 - Redis 7.2 (Cluster 模式)                                    #
    # ------------------------------------------------------------------ #
    redis_nodes: str = field(
        default_factory=lambda: os.getenv(
            'REDIS_NODES', '127.0.0.1:6379,127.0.0.1:6380,127.0.0.1:6381'
        )
    )
    redis_password:        str = field(default_factory=lambda: os.getenv('REDIS_PASSWORD', ''))
    redis_max_connections: int = 50

    # TTL 策略（秒）
    redis_ttl_session:     int = 86400   # JWT 会话 24 小时
    redis_ttl_product_min: int = 300     # 热点商品最短 5 分钟
    redis_ttl_product_max: int = 1800    # 热点商品最长 30 分钟
    redis_ttl_rate_limit:  int = 60      # 限流计数器窗口 1 分钟
    redis_ttl_lock:        int = 30      # 分布式锁默认超时 30 秒

    # Key 前缀
    redis_key_prefix_session:    str = 'sess:'
    redis_key_prefix_product:    str = 'prod:'
    redis_key_prefix_rate_limit: str = 'ratelimit:'
    redis_key_prefix_lock:       str = 'lock:'

    # ------------------------------------------------------------------ #
    #  搜索引擎 - Elasticsearch 8.11 (集群)                               #
    # ------------------------------------------------------------------ #
    es_hosts: str = field(
        default_factory=lambda: os.getenv(
            'ES_HOSTS', 'http://127.0.0.1:9200,http://127.0.0.1:9201,http://127.0.0.1:9202'
        )
    )
    es_username:     str  = field(default_factory=lambda: os.getenv('ES_USERNAME', 'elastic'))
    es_password:     str  = field(default_factory=lambda: os.getenv('ES_PASSWORD', ''))
    es_verify_certs: bool = False

    # 索引名称
    es_index_product:      str = 'ilbuy_products'
    es_index_behavior_log: str = 'ilbuy_behavior_logs'

    # 商品索引分片（按类目分片，3 主分片，每分片 1 副本）
    es_product_shards:   int = 3
    es_product_replicas: int = 1

    # ------------------------------------------------------------------ #
    #  对象存储 - MinIO (集群)                                             #
    # ------------------------------------------------------------------ #
    minio_endpoint:   str  = field(default_factory=lambda: os.getenv('MINIO_ENDPOINT', '127.0.0.1:9000'))
    minio_access_key: str  = field(default_factory=lambda: os.getenv('MINIO_ACCESS_KEY', 'minioadmin'))
    minio_secret_key: str  = field(default_factory=lambda: os.getenv('MINIO_SECRET_KEY', 'minioadmin'))
    minio_secure:     bool = field(default_factory=lambda: os.getenv('MINIO_SECURE', '0') == '1')

    # Bucket 名称
    minio_bucket_reports:   str = 'ilbuy-reports'    # PDF/HTML 报告
    minio_bucket_images:    str = 'ilbuy-images'     # 用户/商品图片
    minio_bucket_contracts: str = 'ilbuy-contracts'  # 电子合同

    # 预签名 URL 有效期（秒）
    minio_presign_upload_expire:   int = 3600    # 上传 URL 有效 1 小时
    minio_presign_download_expire: int = 86400   # 下载 URL 有效 24 小时

    # ------------------------------------------------------------------ #
    #  OLAP - ClickHouse                                                  #
    # ------------------------------------------------------------------ #
    clickhouse_host:      str = field(default_factory=lambda: os.getenv('CLICKHOUSE_HOST', '127.0.0.1'))
    clickhouse_port:      int = field(default_factory=lambda: int(os.getenv('CLICKHOUSE_PORT', '9000')))
    clickhouse_http_port: int = field(default_factory=lambda: int(os.getenv('CLICKHOUSE_HTTP_PORT', '8123')))
    clickhouse_user:      str = field(default_factory=lambda: os.getenv('CLICKHOUSE_USER', 'default'))
    clickhouse_password:  str = field(default_factory=lambda: os.getenv('CLICKHOUSE_PASSWORD', ''))
    clickhouse_database:  str = field(default_factory=lambda: os.getenv('CLICKHOUSE_DATABASE', 'ilbuy_analytics'))

    # 行为日志表（MergeTree 引擎，按日期分区）
    clickhouse_table_behavior:  str = 'user_behavior_log'
    clickhouse_table_order_log: str = 'order_event_log'

    # 批量写入大小
    clickhouse_batch_size: int = 1000

    # ------------------------------------------------------------------ #
    #  消息队列 - RabbitMQ 3.12                                           #
    # ------------------------------------------------------------------ #
    rabbitmq_host:     str = field(default_factory=lambda: os.getenv('RABBITMQ_HOST', '127.0.0.1'))
    rabbitmq_port:     int = field(default_factory=lambda: int(os.getenv('RABBITMQ_PORT', '5672')))
    rabbitmq_user:     str = field(default_factory=lambda: os.getenv('RABBITMQ_USER', 'guest'))
    rabbitmq_password: str = field(default_factory=lambda: os.getenv('RABBITMQ_PASSWORD', 'guest'))
    rabbitmq_vhost:    str = field(default_factory=lambda: os.getenv('RABBITMQ_VHOST', '/'))

    # Exchange 名称（topic 类型）
    rabbitmq_exchange_async: str = 'ilbuy.async'   # 异步任务（报告生成/通知发送）
    rabbitmq_exchange_sync:  str = 'ilbuy.sync'    # 数据同步（MySQL -> ES/ClickHouse）

    # Queue 名称（持久化队列）
    rabbitmq_queue_report:  str = 'q.report.generate'
    rabbitmq_queue_notify:  str = 'q.notify.send'
    rabbitmq_queue_es_sync: str = 'q.sync.elasticsearch'
    rabbitmq_queue_ch_sync: str = 'q.sync.clickhouse'

    # 消息重试策略
    rabbitmq_max_retry:     int = 3
    rabbitmq_retry_delay_s: int = 5

    # ------------------------------------------------------------------ #
    #  Canal + Flink 数据同步                                             #
    # ------------------------------------------------------------------ #
    canal_host:        str = field(default_factory=lambda: os.getenv('CANAL_HOST', '127.0.0.1'))
    canal_port:        int = field(default_factory=lambda: int(os.getenv('CANAL_PORT', '11111')))
    canal_destination: str = field(default_factory=lambda: os.getenv('CANAL_DESTINATION', 'ilbuy'))
    canal_username:    str = field(default_factory=lambda: os.getenv('CANAL_USERNAME', 'canal'))
    canal_password:    str = field(default_factory=lambda: os.getenv('CANAL_PASSWORD', 'canal'))

    # 监听的库表（增量同步目标）
    canal_watch_tables: tuple = (
        'product_db.products',
        'product_db.product_skus',
        'order_db.orders',
        'user_db.users',
    )

    # Flink 检查点间隔（毫秒）& 并行度
    flink_checkpoint_interval_ms: int = 60_000   # 1 分钟
    flink_parallelism:            int = 2

    # ------------------------------------------------------------------ #
    #  业务通用配置                                                         #
    # ------------------------------------------------------------------ #
    default_page_size: int = 20
    max_page_size:     int = 200

    password_min_len: int = 6

    stock_warning_threshold: int = 10

    min_discount_rate: float = 0.01


# 全局单例
settings = Settings()
